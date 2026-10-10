"""One NETBCI participant: preset longitudinal features and a frozen CPU CSP/LDA.

Only a checksum-verified local adapter bundle is read. No downloads, EEGNet,
target fitting, hyperparameter selection, behavioral trial labels, or overwrite.
Session-02 evaluation is descriptive validation with no parameter selection;
session-03/04 evaluation is exploratory test evaluation. A participant remains
the independent statistical unit in any subsequent cohort summary.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import mne
import numpy as np
from scipy.linalg import helmert
from scipy.signal import butter, sosfiltfilt, welch
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from learning_preserving_bci.datasets.netbci import file_sha256, load_netbci_bundle
from learning_preserving_bci.decoders.csp_lda import make_csp_lda
from learning_preserving_bci.neural_geometry import covariance_distance, fit_pca, subspace_distance
from learning_preserving_bci.utils.reproducibility import collect_provenance

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("rest", "right_hand")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_table(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def partition_trials(trials, config):
    """Exhaustive chronological roles; fit only source-session runs 01 through 04."""
    sessions = config["session_order"]
    if len(sessions) != 4 or len(set(sessions)) != 4:
        raise ValueError("Exactly four distinct protocol sessions are required")
    if len({t["subject"] for t in trials}) != 1:
        raise ValueError("Expected exactly one participant")
    if len({t["trial_id"] for t in trials}) != len(trials):
        raise ValueError("Duplicate trial identity")
    if {t["session"] for t in trials} != set(sessions):
        raise ValueError("Session coverage does not match the preset four sessions")
    train_runs, query_runs = set(config["source_train_runs"]), set(config["source_query_runs"])
    if train_runs & query_runs or train_runs | query_runs != {f"{i:02}" for i in range(1, 7)}:
        raise ValueError("Source run sets must be disjoint and cover all six runs")
    if train_runs != {"01", "02", "03", "04"} or query_runs != {"05", "06"}:
        raise ValueError("Preset source-training chronology is runs 01..04, query 05..06")
    for session in sessions:
        if {t["run"] for t in trials if t["session"] == session} != train_runs | query_runs:
            raise ValueError(f"Incomplete six-run coverage for session {session}")
    roles = {"source_train": [], "source_reference_query": [],
             "validation_no_selection": [], "test_exploratory": []}
    role_by_trial = {}
    for i, t in enumerate(trials):
        if t["label"] not in LABELS:
            raise ValueError("Unexpected task label")
        if t["session"] == sessions[0]:
            role = "source_train" if t["run"] in train_runs else "source_reference_query"
        elif t["session"] == sessions[1]:
            role = "validation_no_selection"
        else:
            role = "test_exploratory"
        roles[role].append(i)
        role_by_trial[t["trial_id"]] = role
    if set(trials[i]["label"] for i in roles["source_train"]) != set(LABELS):
        raise ValueError("Source training needs both task classes")
    return {key: np.asarray(indices, dtype=int) for key, indices in roles.items()}, role_by_trial


def fit_source_qc(X, train, multiplier, flat_threshold_uv=0.1):
    """Fit amplitude screening only on source training; retain every trial."""
    peak_uv = np.ptp(X, axis=-1).max(axis=1) * 1e6
    log_peak = np.log10(np.maximum(peak_uv, 1e-12))
    center = float(np.median(log_peak[train]))
    scaled_mad = float(1.4826 * np.median(np.abs(log_peak[train] - center)))
    threshold = center + multiplier * max(scaled_mad, 1e-12)
    flat = (X.std(axis=-1) * 1e6 < flat_threshold_uv).any(axis=1)
    return peak_uv, (log_peak > threshold) | flat, {
        "median_log10_peak_uv": center, "scaled_MAD_log10_peak_uv": scaled_mad,
        "threshold_log10_peak_uv": threshold, "flat_threshold_uv": flat_threshold_uv,
        "source_fit_n": len(train), "no_trials_automatically_removed": True,
    }


def balanced_indices(trials, sessions, runs, per_class_run, seed, eligible=None):
    """Select the same preset cells/counts, or fail with the missing-cell evidence."""
    rng = np.random.default_rng(seed)
    chosen, shortages = {}, []
    for session in sessions:
        indices = []
        for run in runs:
            for label in LABELS:
                pool = [i for i, t in enumerate(trials) if t["session"] == session
                        and t["run"] == run and t["label"] == label
                        and (eligible is None or eligible[i])]
                if len(pool) < per_class_run:
                    shortages.append({"session": session, "run": run, "label": label,
                                      "n_available": len(pool), "n_required": per_class_run})
                else:
                    indices.extend(rng.choice(pool, per_class_run, replace=False).tolist())
        chosen[session] = np.asarray(indices, dtype=int)
    if shortages:
        raise ValueError("Insufficient preset matched cells: " + json.dumps(shortages))
    return chosen


def run_bootstrap_ci(y, prediction, runs, seed, repetitions):
    """Resample complete runs conditionally within this participant, never people."""
    groups = np.unique(runs)
    if len(groups) < 2 or repetitions < 1:
        return None
    rng = np.random.default_rng(seed)
    lookup = {run: np.flatnonzero(runs == run) for run in groups}
    scores = []
    for _ in range(repetitions):
        indices = np.concatenate([lookup[r] for r in rng.choice(groups, len(groups), replace=True)])
        if len(np.unique(y[indices])) == 2:
            scores.append(float(balanced_accuracy_score(y[indices], prediction[indices])))
    return np.quantile(scores, [.025, .975]).tolist() if scores else None


def model_digest(model):
    return hashlib.sha256(pickle.dumps(model)).hexdigest()


def frozen_decoder(X, y, trials, roles, flagged, config, output, factory=None):
    """Fit once to the preset source role, then verify immutable/replayed queries."""
    train = roles["source_train"]
    factory = factory or (lambda: make_csp_lda(config["csp_components"]))
    model = factory().fit(X[train], y[train])
    before = model_digest(model)
    evaluation, predictions, failures = [], [], []
    sessions = config["session_order"]
    for position, session in enumerate(sessions):
        role = ("source_reference_query" if position == 0 else
                "validation_no_selection" if position == 1 else "test_exploratory")
        indices = np.array([i for i in roles[role] if trials[i]["session"] == session], dtype=int)
        truth = y[indices]
        prediction = model.predict(X[indices])
        if not np.array_equal(prediction, model.predict(X[indices])):
            raise AssertionError("Frozen prediction replay changed")
        if model_digest(model) != before:
            raise AssertionError("Query prediction changed fitted model parameters")
        groups = np.array([trials[i]["run"] for i in indices])
        clean = ~flagged[indices]
        two_classes = len(np.unique(truth)) == 2
        score = float(balanced_accuracy_score(truth, prediction)) if two_classes else None
        clean_score = (float(balanced_accuracy_score(truth[clean], prediction[clean]))
                       if len(np.unique(truth[clean])) == 2 else None)
        constant = len(np.unique(prediction)) == 1
        if constant:
            failures.append({"scope": "CSP_LDA_query", "session": session,
                             "type": "constant_prediction", "label": str(prediction[0]),
                             "interpretation": "retained classifier failure, not human skill loss"})
        if not two_classes:
            failures.append({"scope": "CSP_LDA_query", "session": session,
                             "type": "missing_query_class", "counts": dict(Counter(truth))})
        evaluation.append({"subject": trials[0]["subject"], "session": session,
                           "role": role, "decoder": "CSP_LDA", "n_test": len(indices),
                           "n_runs": len(np.unique(groups)), "n_rest": int((truth == "rest").sum()),
                           "n_right_hand": int((truth == "right_hand").sum()),
                           "balanced_accuracy": score,
                           "conditional_run_bootstrap_CI95": run_bootstrap_ci(
                               truth, prediction, groups, config["seed"],
                               config["bootstrap_run_repetitions"]) if two_classes else None,
                           "confusion_matrix_rest_right_hand": confusion_matrix(
                               truth, prediction, labels=list(LABELS)).tolist(),
                           "constant_prediction": constant, "n_qc_flagged_query": int((~clean).sum()),
                           "qc_unflagged_n": int(clean.sum()), "qc_unflagged_BA": clean_score,
                           "train_n": len(train), "participant_n": 1,
                           "CI_scope": "conditional run clusters; excludes source-fit uncertainty; not population CI"})
        predictions.extend({"subject": trials[i]["subject"], "trial_id": trials[i]["trial_id"],
                            "session": session, "run": trials[i]["run"], "role": role,
                            "true_label": str(y[i]), "prediction": str(p)}
                           for i, p in zip(indices, prediction, strict=True))
    info = {"family": "CSP_LDA", "fit_calls": 1, "query_state_unchanged": True,
            "parameter_sha256_before": before, "parameter_sha256_after": model_digest(model),
            "prediction_replay_exact": True,
            "source_train_trial_ids": [trials[i]["trial_id"] for i in train],
            "source_train_n": len(train), "parameters_predefined_no_target_selection": True,
            "target_transforms_fitted_for_prediction": False}
    (output / "csp_lda.pkl").write_bytes(pickle.dumps(model))
    write_json(output / "CSP_LDA_model_audit.json", info)
    return evaluation, predictions, failures


def matched_geometry(trials, covariance, standardized, bands, roi, config, flagged):
    rows, spectral, statuses = [], [], []
    sessions = config["session_order"]
    variants = {"all_six_runs": ([f"{i:02}" for i in range(1, 7)], None),
                "qc_common_four_runs": (config["qc_matched_runs"], ~flagged)}
    for variant, (runs, eligible) in variants.items():
        try:
            for repetition in range(config["matched_repetitions"]):
                chosen = balanced_indices(trials, sessions, runs,
                                          config["matched_trials_per_class_per_run"],
                                          config["seed"] + repetition, eligible)
                source = chosen[sessions[0]]
                source_cov = covariance[source].mean(axis=0)
                source_space = fit_pca(standardized[source], config["pca_components"]).components_
                for session, indices in chosen.items():
                    means = {run: covariance[[i for i in indices if trials[i]["run"] == run]].mean(axis=0)
                             for run in runs}
                    within = [covariance_distance(means[a], means[b], regularization=0)
                              for position, a in enumerate(runs) for b in runs[position + 1:]]
                    target_space = fit_pca(standardized[indices], config["pca_components"]).components_
                    rows.append({"subject": trials[0]["subject"], "variant": variant,
                                 "repetition": repetition, "session": session, "n_matched": len(indices),
                                 "AIRM_to_session01": covariance_distance(
                                     source_cov, covariance[indices].mean(axis=0), regularization=0),
                                 "within_session_run_AIRM_mean": float(np.mean(within)),
                                 "PCA_subspace_distance": subspace_distance(source_space, target_space),
                                 "mu_ROI_V2": float(bands[0][indices][:, roi].mean()),
                                 "beta_ROI_V2": float(bands[1][indices][:, roi].mean())})
                    for band_name, band in zip(("mu", "beta"), bands, strict=True):
                        values = band[:, roi].mean(axis=1)
                        logs = {label: float(np.log10(np.maximum(
                            values[[i for i in indices if trials[i]["label"] == label]],
                            np.finfo(float).tiny)).mean()) for label in LABELS}
                        spectral.append({"subject": trials[0]["subject"], "variant": variant,
                                         "repetition": repetition, "session": session, "band": band_name,
                                         "n_matched": len(indices),
                                         "MI_minus_rest_log_power_dB": 10 * (logs["right_hand"] - logs["rest"]),
                                         "interpretation": "task_window_contrast_not_baseline_ERD"})
            statuses.append({"variant": variant, "status": "available", "runs": runs,
                             "repetitions": config["matched_repetitions"]})
        except ValueError as error:
            # The preset counts/run set never silently decrease to make a metric available.
            rows = [r for r in rows if r["variant"] != variant]
            spectral = [r for r in spectral if r["variant"] != variant]
            statuses.append({"variant": variant, "status": "unavailable", "runs": runs,
                             "error": str(error), "preset_not_relaxed": True})
    return rows, spectral, statuses


def analyze(bundle, config, output):
    subset = load_netbci_bundle(bundle)
    trials = [asdict(item) for item in subset.trials]
    roles, by_trial = partition_trials(trials, config)
    train = roles["source_train"]
    X, y = subset.dataset.X, subset.dataset.y
    sfreq, names = subset.dataset.sfreq, list(subset.dataset.channel_names)
    if sfreq != config["expected_sfreq_hz"] or len(names) != 74:
        raise ValueError("Unexpected cohort sampling rate or channel count")
    if config.get("expected_channel_names") and names != config["expected_channel_names"]:
        raise ValueError("Channel mapping differs from pinned cohort coordinate order")
    if len(set(names)) != len(names) or not set(config["roi_channels"]).issubset(names):
        raise ValueError("Duplicate channels or absent preset ROI channel")
    if X.shape[-1] != round(5 * sfreq) or not np.isfinite(X).all():
        raise ValueError("Unexpected event-window length or nonfinite EEG")
    cut = round(config["edge_crop_seconds"] * sfreq)
    if cut <= 0 or 2 * cut >= X.shape[-1]:
        raise ValueError("Invalid preset epoch-edge crop")
    events = [dict(t, analysis_role=by_trial[t["trial_id"]],
                   trial_behavior_outcome="unresolved", acquisition_date="anonymized_actual_date_unresolved")
              for t in trials]
    write_table(output / "event_inventory.tsv", events)
    run_inventory = subset.run_table()
    write_table(output / "run_inventory.tsv", run_inventory)
    partitions = {"subject": trials[0]["subject"], "session_order": config["session_order"],
                  "partition_trial_ids": {role: [trials[i]["trial_id"] for i in indices]
                                          for role, indices in roles.items()},
                  "all_trials_assigned_once": True, "source_train_runs": config["source_train_runs"],
                  "source_query_runs": config["source_query_runs"],
                  "later_query_runs": [f"{i:02}" for i in range(1, 7)],
                  "validation_selection_performed": False, "status": "preset_exploratory_analysis"}
    write_json(output / "partitions.json", partitions)
    peak, flagged, qc = fit_source_qc(X, train, config["artifact_log_peak_MAD_multiplier"])
    car = X - X.mean(axis=1, keepdims=True)
    kwargs = {"fs": sfreq, "window": "hann", "nperseg": config["welch_segment_samples"],
              "noverlap": config["welch_overlap_samples"], "detrend": "constant", "scaling": "density"}
    freq, psd = welch(car[..., cut:-cut], **kwargs)
    _, raw_psd = welch(X[..., cut:-cut], **kwargs)
    bands, raw_bands = [], []
    for low, high in (config["mu_hz"], config["beta_hz"]):
        mask = (freq >= low) & (freq <= high)
        if mask.sum() < 2:
            raise ValueError("Band integration requires at least two Welch bins")
        bands.append(np.trapezoid(psd[..., mask], freq[mask], axis=-1))
        raw_bands.append(np.trapezoid(raw_psd[..., mask], freq[mask], axis=-1))
    roi = [names.index(channel) for channel in config["roi_channels"]]
    feature_rows = [dict(t, analysis_role=by_trial[t["trial_id"]],
                         peak_to_peak_max_uv=float(peak[i]), qc_flag=bool(flagged[i]),
                         mu_ROI_V2=float(bands[0][i, roi].mean()),
                         beta_ROI_V2=float(bands[1][i, roi].mean()),
                         mu_source_reference_ROI_V2=float(raw_bands[0][i, roi].mean()),
                         beta_source_reference_ROI_V2=float(raw_bands[1][i, roi].mean()))
                    for i, t in enumerate(trials)]
    write_table(output / "trial_features.tsv", feature_rows)
    spectra = []
    for session in config["session_order"]:
        for label in LABELS:
            indices = np.array([i for i, t in enumerate(trials) if t["session"] == session
                                and t["label"] == label], dtype=int)
            if not len(indices):
                continue
            means = psd[indices][:, roi].mean(axis=(0, 1))
            raw_means = raw_psd[indices][:, roi].mean(axis=(0, 1))
            spectra.extend({"subject": trials[0]["subject"], "session": session, "label": label,
                            "n_trials": len(indices), "frequency_hz": float(frequency),
                            "CAR_ROI_PSD_V2_per_Hz": float(means[j]),
                            "source_reference_ROI_PSD_V2_per_Hz": float(raw_means[j])}
                           for j, frequency in enumerate(freq))
    write_table(output / "spectra.tsv", spectra)
    del psd, raw_psd
    features = np.log10(np.maximum(np.concatenate(bands, axis=1), np.finfo(float).tiny))
    scaler = StandardScaler().fit(features[train])
    standardized = scaler.transform(features)
    pca = fit_pca(standardized[train], config["pca_components"])
    projected = pca.transform(standardized)
    sos = butter(4, config["decoder_band_hz"], fs=sfreq, btype="bandpass", output="sos")
    filtered = sosfiltfilt(sos, car, axis=-1)[..., cut:-cut].copy()
    del car
    basis = helmert(len(names), full=False)
    covariance = []
    alpha = config["covariance_trace_shrinkage"]
    if not 0 < alpha < 1:
        raise ValueError("Trace covariance shrinkage must be strictly between zero and one")
    for epoch in filtered:
        coordinates = basis @ epoch
        coordinates -= coordinates.mean(axis=1, keepdims=True)
        cov = coordinates @ coordinates.T / (coordinates.shape[1] - 1)
        trace = float(np.trace(cov))
        if trace <= 0 or not np.isfinite(trace):
            raise ValueError("Invalid covariance trace; do not reconstruct missing EEG")
        covariance.append((1 - alpha) * cov / trace + alpha * np.eye(len(basis)) / len(basis))
    covariance = np.asarray(covariance)
    reference_cov = covariance[train].mean(axis=0)
    run_rows = []
    for row in run_inventory:
        indices = np.array([i for i, t in enumerate(trials) if (t["session"], t["run"])
                            == (row["session"], row["run"])], dtype=int)
        run_rows.append(dict(row, n_qc_flagged=int(flagged[indices].sum()),
                             mu_ROI_V2=float(bands[0][indices][:, roi].mean()),
                             beta_ROI_V2=float(bands[1][indices][:, roi].mean()),
                             AIRM_to_source_fit=covariance_distance(
                                 reference_cov, covariance[indices].mean(axis=0), regularization=0),
                             PCA_mean_distance_to_source=float(np.linalg.norm(
                                 projected[indices].mean(axis=0) - projected[train].mean(axis=0)))))
    write_table(output / "run_features.tsv", run_rows)
    geometry, contrasts, statuses = matched_geometry(
        trials, covariance, standardized, bands, roi, config, flagged)
    write_table(output / "matched_geometry.tsv", geometry)
    write_table(output / "matched_spectral_contrasts.tsv", contrasts)
    write_json(output / "matched_variants_status.json", statuses)
    decoder_input = np.einsum("kc,nct->nkt", basis, filtered)
    del filtered
    failures = []
    try:
        scores, predictions, failures = frozen_decoder(
            decoder_input, y, trials, roles, flagged, config, output)
        write_json(output / "decoder_results.json", scores)
        write_table(output / "predictions.tsv", predictions)
    except Exception as error:
        failures.append({"scope": "CSP_LDA_fit_or_query", "type": type(error).__name__,
                         "message": str(error)})
        write_json(output / "decoder_results.json", [])
    failures.extend({"scope": "matched_geometry", **status}
                    for status in statuses if status["status"] == "unavailable")
    write_json(output / "failures.json", failures)
    np.savez(output / "reference_geometry.npz", pca_components=pca.components_,
             scaler_mean=scaler.mean_, scaler_scale=scaler.scale_, helmert=basis,
             reference_covariance=reference_cov)
    write_json(output / "transform_audit.json", {
        "source_train_trial_ids": [trials[i]["trial_id"] for i in train],
        "scaler_fit_source_only": True, "reference_PCA_fit_source_only": True,
        "target_PCA_descriptive_only": True, "target_prediction_transforms_fitted": False,
        "CAR_Helmert_basis": "fixed_analytical_not_learned", "channel_names": names,
        "QC": qc, "covariance_units": "trace_normalized_relative_identity_shrinkage",
        "covariance_trace_shrinkage": alpha,
        "bandpower_units": "V^2", "PSD_units": "V^2/Hz",
        "window_seconds": [cut / sfreq, (X.shape[-1] - cut) / sfreq],
        "no_prestimulus_baseline_or_ERD_claim": True,
    })
    return {"status": "completed_exploratory" if not failures else "completed_with_scientific_failures",
            "synthetic": False, "subject": trials[0]["subject"], "participants": 1,
            "trials": len(trials), "shape": list(X.shape), "sampling_frequency_hz": sfreq,
            "channel_names": names, "qc_flagged_total": int(flagged.sum()), "QC": qc,
            "failures_n": len(failures), "no_target_parameter_selection": True,
            "matched_variants": statuses, "limitations": [
                "offline observational data, no causal human learning inference",
                "behavioral EEG run order/denominator/trial outcome unresolved",
                "session chronology known, real acquisition dates anonymized",
                "source-only QC screen is not expert artifact-free certification",
                "validation and test labels do not select or fit model parameters"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    config = json.loads(args.config.read_text())
    mne.set_log_level("ERROR")
    try:
        with threadpool_limits(limits=config["threads"]):
            result = analyze(args.bundle, config, args.output)
    except Exception as error:
        result = {"status": "failed", "synthetic": False, "participants": 0,
                  "error": {"type": type(error).__name__, "message": str(error)}}
    metadata_path = args.bundle / "metadata.json"
    try:
        source_metadata = json.loads(metadata_path.read_text()).get("provenance")
    except (OSError, ValueError, AttributeError):
        source_metadata = None
    result.update({"config": config, "config_sha256": file_sha256(args.config),
                   "script_sha256": file_sha256(Path(__file__)),
                   "bundle_sha256": (file_sha256(args.bundle / "epochs.npz")
                                     if (args.bundle / "epochs.npz").is_file() else None),
                   "metadata_sha256": file_sha256(metadata_path) if metadata_path.is_file() else None,
                   "source_metadata_provenance": source_metadata,
                   "provenance": collect_provenance(config["seed"], ROOT),
                   "duration_seconds": time.monotonic() - start,
                   "outputs": {p.name: file_sha256(p) for p in args.output.iterdir() if p.is_file()}})
    write_json(args.output / "analysis_receipt.json", result)
    print(json.dumps({"output": str(args.output), "status": result["status"],
                      "trials": result.get("trials"), "duration_seconds": result["duration_seconds"]}))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
