#!/usr/bin/env python3
"""Independent model replay and fixed retrospective task-information diagnostics.

No estimator is fitted and no baseline is selected. Participant-block inference
and optional raw as-stored reference diagnostics cannot change saved models.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import mne  # noqa: E402
import numpy as np  # noqa: E402
from scipy.linalg import eigvalsh  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt, welch  # noqa: E402
from scipy.stats import spearmanr, wasserstein_distance  # noqa: E402
from learning_preserving_bci.datasets.kumar import load_subject  # noqa: E402

METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def csv_rows(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def write_csv(path, rows):
    with Path(path).open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finite(value):
    return float(value) if np.isfinite(value) else None


def rank_correlation(x, y):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return finite(spearmanr(x, y).statistic)


def block_correlation(rows, feature, *, replicates=2000, seed=42):
    subjects = sorted({r["subject"] for r in rows})
    by_subject = {s: [r for r in rows if r["subject"] == s] for s in subjects}
    rng = np.random.default_rng(seed)
    observed = rank_correlation([r[feature] for r in rows], [r["delta_frozen_BA"] for r in rows])
    samples = []
    for _ in range(replicates):
        draw = [r for i in rng.integers(0, len(subjects), len(subjects)) for r in by_subject[subjects[i]]]
        value = rank_correlation([r[feature] for r in draw], [r["delta_frozen_BA"] for r in draw])
        if value is not None:
            samples.append(value)
    mean_rows = [{"x": np.mean([r[feature] for r in by_subject[s]]),
                  "y": np.mean([r["delta_frozen_BA"] for r in by_subject[s]])} for s in subjects]
    return {"participants": len(subjects), "sessions": len(rows), "spearman": observed,
            "participant_block_bootstrap_ci95": np.quantile(samples, [.025, .975]).tolist() if samples else None,
            "valid_bootstrap_draws": len(samples), "replicates": replicates, "seed": seed,
            "participant_mean_spearman": rank_correlation([r["x"] for r in mean_rows], [r["y"] for r in mean_rows]),
            "scope": "exploratory retrospective association; no selected predictor or causal interpretation"}


def epoch_power(X):
    frequency, psd = welch(X, fs=128, window="hann", nperseg=256, noverlap=128,
                           detrend="constant", scaling="density", average="mean", axis=-1)
    return np.stack([np.trapezoid(psd[..., (frequency >= lo) & (frequency <= hi)],
                                  frequency[(frequency >= lo) & (frequency <= hi)], axis=-1)
                     for lo, hi in [(8, 13), (13, 30)]], axis=-1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--as-stored-reference", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config, execution = read(args.config), read(args.results / "execution_receipt.json")
    assert execution["status"] == "completed_frozen_offline_protocol" and not execution["failures"]
    assert execution["config_sha256"] == sha(args.config) and execution["split_manifest_sha256"] == sha(args.manifest)
    for relative, expected in execution["outputs"].items():
        assert sha(args.results / relative) == expected, f"Saved result hash differs: {relative}"
    metrics, predictions = csv_rows(args.results / "metrics.csv"), csv_rows(args.results / "query_predictions.csv")
    assert len(metrics) == 324 and len(predictions) == 12870
    grouped = defaultdict(list)
    for row in predictions:
        grouped[(row["subject"], row["session"], row["method"])].append(row)
    replay_count = 0
    session_rows, sensitivities, review = [], [], []
    sos = butter(4, [8, 30], fs=512, btype="bandpass", output="sos")
    for subject in config["subjects"]:
        data = load_subject(config["data_root"], subject, config, args.manifest)
        folder = args.results / subject
        index = {t["trial_id"]: i for i, t in enumerate(data.metadata)}
        meta = read(folder / "included_trial_metadata.json")
        assert meta == data.metadata
        audits = read(folder / "model_audit.json")
        forbidden = {t["trial_id"] for t in meta if t["role"] in {"source_validation", "source_query", "target_query"}}
        for audit in audits:
            assert not set(audit["fit_trial_ids"]) & forbidden
            allowed = {t["trial_id"] for t in meta if t["role"] == "source_train" or
                       (t["role"] == "target_support" and t["session"] == audit["session"])}
            assert set(audit["fit_trial_ids"]) <= allowed
            assert sha(folder / audit["model_artifact"]) == audit["artifact_sha256"]
            rows = grouped[(subject, audit["session"], audit["method"])]
            with np.load(folder / audit["model_artifact"], allow_pickle=False) as weights:
                X = data.X[[index[r["trial_id"]] for r in rows]].astype(np.float64)
                filtered = np.einsum("kc,nct->nkt", weights["csp_filters"][:int(weights["n_components"])], X)
                log_power = np.log(np.mean(filtered ** 2, axis=-1))
                score = log_power @ weights["lda_coef"].T + weights["lda_intercept"]
                predicted = weights["lda_classes"][(score[:, 0] > 0).astype(int)]
            labels = np.asarray([int(r["label"]) for r in rows])
            assert np.array_equal(predicted, [int(r["prediction"]) for r in rows])
            assert np.array_equal(labels, data.y[[index[r["trial_id"]] for r in rows]])
            row = next(r for r in metrics if (r["subject"], r["session"], r["method"]) == (subject, audit["session"], audit["method"]))
            recall = [np.mean(predicted[labels == label] == label) for label in (0, 1)]
            assert abs(np.mean(recall) - float(row["balanced_accuracy"])) < 1e-12
            for label in (0, 1):
                for other in (0, 1):
                    assert np.sum((labels == label) & (predicted == other)) == int(row[f"confusion_{label}{other}"])
            replay_count += len(rows)
        with np.load(folder / "source_before.npz", allow_pickle=False) as before, np.load(folder / "source_after.npz", allow_pickle=False) as after:
            assert all(np.array_equal(before[k], after[k]) for k in before.files)
        with np.load(folder / "fixed_features.npz", allow_pickle=False) as f:
            features = {k: f[k].copy() for k in f.files}
        train = np.asarray([i for i, t in enumerate(meta) if t["role"] == "source_train"])
        with np.load(folder / "feature_source_fit.npz", allow_pickle=False) as fitted:
            assert int(fitted["scaler_n_samples_seen"]) == len(train) == 40
            np.testing.assert_allclose(features["log10_bandpower_44"][train].mean(axis=0), fitted["scaler_mean"], atol=1e-12)
            np.testing.assert_allclose((features["log10_bandpower_44"] - fitted["scaler_mean"]) / fitted["scaler_scale"], features["source_standardized_44"], atol=1e-12)
            np.testing.assert_allclose((features["source_standardized_44"] - fitted["pca_mean"]) @ fitted["pca_components"].T, features["source_pca4"], atol=1e-12)
            ref_cov = fitted["source_covariance_riemannian_mean"].copy()
        np.testing.assert_allclose(epoch_power(data.X.astype(float)), features["bandpower_volts_squared"], rtol=1e-10, atol=1e-24)
        np.testing.assert_allclose([np.linalg.norm(np.log(eigvalsh(c, ref_cov))) for c in features["covariance_21"]], features["covariance_distance_source"], rtol=1e-8, atol=1e-10)
        z, y = features["source_standardized_44"], data.y
        direction = z[train[y[train] == 1]].mean(axis=0) - z[train[y[train] == 0]].mean(axis=0)
        assert np.linalg.norm(direction) > 0
        direction /= np.linalg.norm(direction)
        projected = z @ direction
        def role_index(session, role):
            return np.asarray([i for i, t in enumerate(meta)
                               if t["session"] == session and t["role"] == role])
        reference = role_index("ses-0", "source_query")
        source_ba = float(next(r["balanced_accuracy"] for r in metrics if r["subject"] == subject and r["session"] == "ses-0" and r["method"] == "source_only"))
        native_power = None
        if args.as_stored_reference:
            native_power = np.zeros_like(features["bandpower_volts_squared"])
            by_file = defaultdict(list)
            for i, t in enumerate(meta):
                by_file[t["source_file"]].append((i, t))
            for relative, trials in by_file.items():
                raw = mne.io.read_raw_edf(Path(config["data_root"]) / relative, preload=False, verbose="ERROR")
                try:
                    for i, t in trials:
                        original = raw.get_data(start=t["start_sample"], stop=t["stop_sample_exclusive"])
                        transformed = resample_poly(sosfiltfilt(sos, original, axis=-1), 1, 4, axis=-1)
                        native_power[i] = epoch_power(transformed)
                finally:
                    raw.close()
        for session in config["split"]["target_sessions"]:
            target = role_index(session, "target_query")
            current = float(next(r["balanced_accuracy"] for r in metrics if r["subject"] == subject and r["session"] == session and r["method"] == "source_only"))
            session_rows.append({"subject": subject, "cohort": meta[0]["cohort"], "session": session,
                                 "delta_frozen_BA": current - source_ba,
                                 "delta_covariance_distance": float(features["covariance_distance_source"][target].mean() - features["covariance_distance_source"][reference].mean()),
                                 "source_task_axis_wasserstein": float(wasserstein_distance(projected[reference], projected[target])),
                                 "n_source_query": len(reference), "n_target_query": len(target)})
            variants = {"primary_all_included": (reference, target),
                        "unflagged_query_descriptive": (reference[[not meta[i]["qc_peak_to_peak_over_250uv"] for i in reference]], target[[not meta[i]["qc_peak_to_peak_over_250uv"] for i in target]])}
            per_class = min(np.sum(y[ids] == label) for ids in [reference, target] for label in [0, 1])
            variants["matched_reference_target_class_counts"] = tuple(np.concatenate([ids[y[ids] == label][:per_class] for label in [0, 1]]) for ids in [reference, target])
            for variant, (a, b) in variants.items():
                viable = len(a) >= 2 and len(b) >= 2 and set(y[a]) == set(y[b]) == {0, 1}
                for channel_set, channel_ids in [("all22", np.arange(22)), ("C3_Cz_C4", np.asarray([9, 10, 11]))]:
                    for ref_name, powers in [("CAR", features["bandpower_volts_squared"]), ("as_stored_derivative_reference", native_power)]:
                        if powers is None:
                            continue
                        log = np.log10(np.maximum(powers, np.finfo(float).tiny))
                        delta = log[b][:, channel_ids].mean(axis=(0, 1)) - log[a][:, channel_ids].mean(axis=(0, 1)) if viable else [np.nan, np.nan]
                        sensitivities.append({"subject": subject, "cohort": meta[0]["cohort"], "session": session,
                                              "variant": variant, "channels": channel_set, "reference": ref_name,
                                              "source_n": len(a), "target_n": len(b), "both_classes_viable": viable,
                                              "delta_mu_log10_absolute_power": finite(delta[0]), "delta_beta_log10_absolute_power": finite(delta[1])})
        review.append({"subject": subject, "model_rows": len(audits), "exact_predictions_replayed": sum(len(grouped[(subject, a["session"], a["method"])]) for a in audits), "source_state_exactly_frozen": True, "feature_fits_source_only_recomputed": True})
        print(json.dumps({"subject": subject, "independent_replay": "passed"}), flush=True)
    summary = read(args.results / "participant_bootstrap_summary.json")
    for cohort, result in summary["cohorts"].items():
        values = np.asarray([[np.mean([float(r["balanced_accuracy"]) for r in metrics if r["subject"] == s and r["method"] == method and r["session"] != "ses-0"]) for method in METHODS] for s in result["subjects"]])
        draws = np.random.default_rng(42).integers(0, len(values), size=(10000, len(values)))
        boot = values[draws].mean(axis=1)
        for i, method in enumerate(METHODS):
            np.testing.assert_allclose(values[:, i].mean(), result["methods"][method]["mean_balanced_accuracy"], atol=1e-14)
            np.testing.assert_allclose(np.quantile(boot[:, i], [.025, .975]), result["methods"][method]["ci95"], atol=1e-14)
        comparison = result["paired_comparisons"]["refit_csp_lda_minus_source_only"]
        np.testing.assert_allclose(np.quantile(boot[:, 2] - boot[:, 0], [.025, .975]), comparison["ci95"], atol=1e-14)
    association = {cohort: {feature: block_correlation([r for r in session_rows if r["cohort"] == cohort], feature) for feature in ["delta_covariance_distance", "source_task_axis_wasserstein"]} for cohort in ["development", "final_test"]}
    write_csv(args.output / "session_drift_and_performance.csv", session_rows)
    write_csv(args.output / "power_QC_channel_reference_count_sensitivity.csv", sensitivities)
    write_json(args.output / "task_information_associations.json", association)
    write_json(args.output / "independent_review_receipt.json", {"status": "passed", "finished_at_utc": datetime.now(timezone.utc).isoformat(),
               "script_sha256": sha(__file__), "execution_receipt_sha256": sha(args.results / "execution_receipt.json"),
               "participants": review, "model_rows": 324, "predictions_replayed": replay_count,
               "metrics_confusion_and_participant_bootstrap_recomputed": True,
               "new_decoder_fits": 0, "source_only_fixed_features_recomputed": True,
               "as_stored_reference_sensitivity": args.as_stored_reference,
               "reference_caveat": "as-stored derivative values vs CAR; CPz acquisition identity remains metadata-declared, not independently recovered",
               "scope": "real offline diagnostics; no algorithm or skill-retention causal effect"})


if __name__ == "__main__":
    main()
