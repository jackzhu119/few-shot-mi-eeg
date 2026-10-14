#!/usr/bin/env python3
"""Serial CPU Kumar baselines with guarded fits and pickle-free model replay.

Formal execution requires an independent, hash-bound approval receipt. Tests use
``run_participant`` on synthetic arrays and never satisfy the real-source gate.
Only the current target session's preassigned support may update a decoder.
"""

# ruff: noqa: E402 -- CPU thread caps must be set before importing numerical libraries.

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

import mne
import numpy as np
from scipy.integrate import trapezoid
from scipy.linalg import eigh, helmert
from scipy.signal import welch
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_info

from learning_preserving_bci.decoders.csp_lda import make_csp_lda

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda")
LABEL_NAMES = {0: "left_hand", 1: "right_hand"}
ROLE_ALIASES = {
    "source_train": "source_train", "reference_train": "source_train",
    "source_validation": "source_validation", "reference_validation": "source_validation",
    "source_query": "source_query", "reference_query": "source_query",
    "target_support": "target_support", "target_query": "target_query",
}


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty evidence table")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def array_digest(arrays: dict[str, np.ndarray]) -> str:
    """Canonical content hash, independent of ZIP timestamp or Python pickle."""
    digest = hashlib.sha256()
    for name, value in sorted(arrays.items()):
        value = np.ascontiguousarray(value)
        if value.dtype.hasobject:
            raise ValueError("Object arrays are forbidden in model artifacts")
        descriptor = json.dumps([name, value.dtype.str, list(value.shape)], separators=(",", ":"))
        digest.update(descriptor.encode())
        digest.update(b"\0")
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def model_arrays(csp, lda) -> dict[str, np.ndarray]:
    """Record learned CSP/LDA state using arrays readable with allow_pickle=False."""
    result = {"n_components": np.asarray(csp.n_components, dtype=np.int64)}
    for prefix, estimator, fields in (
        ("csp", csp, ("filters_", "patterns_", "mean_", "std_")),
        ("lda", lda, ("classes_", "coef_", "intercept_", "means_", "priors_", "covariance_")),
    ):
        for field in fields:
            result[f"{prefix}_{field.removesuffix('_')}"] = np.asarray(
                getattr(estimator, field)
            ).copy()
    return result


def predict_from_arrays(arrays: dict[str, np.ndarray], X: np.ndarray) -> np.ndarray:
    """Replay the frozen MNE average-power/log CSP and sklearn binary LDA."""
    filters = arrays["csp_filters"][:int(arrays["n_components"])]
    features = np.asarray([np.dot(filters, epoch) for epoch in np.asarray(X, dtype=float)])
    features = np.log(np.square(features).mean(axis=2))
    score = features @ arrays["lda_coef"].T + arrays["lda_intercept"]
    if score.shape[1] != 1 or len(arrays["lda_classes"]) != 2:
        raise ValueError("This frozen experiment supports binary LDA only")
    return arrays["lda_classes"][(score[:, 0] > 0).astype(int)]


def summarize_predictions(y: np.ndarray, prediction: np.ndarray) -> dict:
    matrix = confusion_matrix(y, prediction, labels=[0, 1])
    counts = matrix.sum(axis=1)
    if np.any(counts == 0):
        raise ValueError("Both task classes must be represented in every query")
    recall = matrix.diagonal() / counts
    ratios = np.bincount(prediction.astype(int), minlength=2) / len(prediction)
    return {
        "n_query": int(len(y)), "n_left_hand": int(counts[0]),
        "n_right_hand": int(counts[1]), "balanced_accuracy": float(recall.mean()),
        "recall_left_hand": float(recall[0]), "recall_right_hand": float(recall[1]),
        "confusion_00": int(matrix[0, 0]), "confusion_01": int(matrix[0, 1]),
        "confusion_10": int(matrix[1, 0]), "confusion_11": int(matrix[1, 1]),
        "prediction_ratio_left_hand": float(ratios[0]),
        "prediction_ratio_right_hand": float(ratios[1]),
        "class_collapse": bool(np.unique(prediction).size < 2),
    }


def validate_roles(trials: list[dict], y: np.ndarray) -> dict[str, np.ndarray]:
    identifiers = [item["trial_id"] for item in trials]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate trial identities")
    roles = {}
    for index, item in enumerate(trials):
        if item["role"] not in ROLE_ALIASES:
            raise ValueError(f"Unknown analysis role: {item['role']}")
        role = ROLE_ALIASES[item["role"]]
        roles.setdefault(role, []).append(index)
    expected = set(ROLE_ALIASES.values())
    if set(roles) != expected:
        raise ValueError(f"Missing frozen role: {expected - set(roles)}")
    roles = {role: np.asarray(index, dtype=int) for role, index in roles.items()}
    for role, indices in roles.items():
        if set(y[indices].tolist()) != {0, 1}:
            raise ValueError(f"Role {role} lacks both task classes")
    source_sessions = {
        trials[index]["session"] for role in ("source_train", "source_validation", "source_query")
        for index in roles[role]
    }
    if len(source_sessions) != 1:
        raise ValueError("Source roles must belong to one reference session")
    source_session = next(iter(source_sessions))
    if any(trials[i]["session"] == source_session
           for role in ("target_support", "target_query") for i in roles[role]):
        raise ValueError("Target data overlap source session")
    # A complete run belongs to one role, preventing overlapping-window/run leakage.
    by_run = {}
    for item in trials:
        run = (item["session"], item["run"])
        role = ROLE_ALIASES[item["role"]]
        if run in by_run and by_run[run] != role:
            raise ValueError("A run spans more than one analysis role")
        by_run[run] = role
    return roles


def symmetric_function(matrix: np.ndarray, function) -> np.ndarray:
    eigenvalues, eigenvectors = eigh((matrix + matrix.T) / 2)
    return (eigenvectors * function(eigenvalues)) @ eigenvectors.T


def riemannian_mean(covariances: np.ndarray) -> tuple[np.ndarray, dict]:
    """Fixed affine-invariant mean; only explicitly supplied source training trials."""
    mean = covariances.mean(axis=0)
    for iteration in range(1, 101):
        root = symmetric_function(mean, np.sqrt)
        inverse_root = symmetric_function(mean, lambda value: 1 / np.sqrt(value))
        tangent = np.mean([
            symmetric_function(inverse_root @ covariance @ inverse_root, np.log)
            for covariance in covariances
        ], axis=0)
        residual = float(np.linalg.norm(tangent, ord="fro"))
        if residual <= 1e-10:
            return mean, {"iterations": iteration, "residual": residual, "converged": True}
        mean = root @ symmetric_function(tangent, np.exp) @ root
        mean = (mean + mean.T) / 2
    raise ValueError(f"SourceTRAIN Riemann mean did not converge: residual={residual}")


def descriptive_features(
    X: np.ndarray, y: np.ndarray, trials: list[dict], *, subject: str, cohort: str,
    output: Path, synthetic: bool = False,
) -> dict:
    """Frozen task-window features; all learned reference state fits sourceTRAIN only.

    The power features have no prestimulus baseline and are not ERD/ERS. Geometry
    never enters decoder prediction or adaptation. Artifacts contain numeric or
    Unicode arrays and can be read with ``allow_pickle=False``.
    """
    from learning_preserving_bci.datasets.kumar import CHANNEL_NAMES

    if X.shape[1:] != (22, 640):
        raise ValueError("Descriptive features require frozen22-channel5-second128-Hz epochs")
    roles = validate_roles(trials, y)
    train = roles["source_train"]
    frequencies, psd = welch(X, fs=128, window="hann", nperseg=256, noverlap=128,
                             detrend="constant", scaling="density", average="mean", axis=-1)
    bands = (("mu", 8.0, 13.0), ("beta", 13.0, 30.0))
    power = np.stack([
        trapezoid(psd[..., (frequencies >= low) & (frequencies <= high)],
                  x=frequencies[(frequencies >= low) & (frequencies <= high)], axis=-1)
        for _, low, high in bands
    ], axis=-1)
    log_power = np.log10(np.maximum(power, np.finfo(np.float64).tiny))
    features = log_power.reshape(len(X), 44)
    basis = helmert(22, full=False)
    projected = basis @ X
    centered = projected - projected.mean(axis=-1, keepdims=True)
    covariance = centered @ centered.swapaxes(-1, -2) / (X.shape[-1] - 1)
    trace = np.trace(covariance, axis1=-2, axis2=-1)
    if np.any(trace <= 0):
        raise ValueError("Cannot trace-normalize a zero-power covariance")
    covariance = 0.9 * covariance / trace[:, None, None] + 0.1 * np.eye(21) / 21
    reference, convergence = riemannian_mean(covariance[train])
    scaler = StandardScaler().fit(features[train])
    pca = PCA(n_components=4, svd_solver="full", whiten=False).fit(
        scaler.transform(features[train]))
    state = {
        "helmert_basis": basis, "source_covariance_riemannian_mean": reference,
        "scaler_mean": scaler.mean_, "scaler_scale": scaler.scale_,
        "scaler_var": scaler.var_, "scaler_n_samples_seen": np.asarray(scaler.n_samples_seen_),
        "pca_components": pca.components_, "pca_mean": pca.mean_,
        "pca_explained_variance": pca.explained_variance_,
        "pca_explained_variance_ratio": pca.explained_variance_ratio_,
        "pca_singular_values": pca.singular_values_,
    }
    before = array_digest(state)
    standardized = scaler.transform(features)
    coordinates = pca.transform(standardized)
    inverse_root = symmetric_function(reference, lambda value: 1 / np.sqrt(value))
    covariance_distance = np.asarray([
        np.linalg.norm(np.log(eigh(inverse_root @ item @ inverse_root, eigvals_only=True)))
        for item in covariance
    ])
    after = array_digest(state)
    if before != after:
        raise AssertionError("Descriptive query transform changed source fit state")
    np.savez_compressed(output / "fixed_features.npz",
                        trial_ids=np.asarray([trial["trial_id"] for trial in trials]),
                        labels=y, bandpower_volts_squared=power, log10_bandpower_44=features,
                        source_standardized_44=standardized, source_pca4=coordinates,
                        covariance_21=covariance,
                        covariance_distance_source=covariance_distance)
    np.savez_compressed(output / "feature_source_fit.npz", **state)
    diagnostic_rows = []
    sensorimotor = [CHANNEL_NAMES.index(channel) for channel in ("C3", "Cz", "C4")]
    for index, trial in enumerate(trials):
        row = {"subject": subject, "cohort": cohort, "trial_id": trial["trial_id"],
               "session": trial["session"], "run": trial["run"],
               "role": ROLE_ALIASES[trial["role"]], "label": int(y[index]),
               "synthetic": synthetic,
               "mean_mu_log10_absolute_power_all22": float(log_power[index, :, 0].mean()),
               "mean_beta_log10_absolute_power_all22": float(log_power[index, :, 1].mean()),
               "mean_mu_log10_absolute_power_sensorimotor": float(
                   log_power[index, sensorimotor, 0].mean()),
               "mean_beta_log10_absolute_power_sensorimotor": float(
                   log_power[index, sensorimotor, 1].mean()),
               "covariance_airm_from_source_train": float(covariance_distance[index]),
               **{f"source_pca_coordinate_{axis + 1}": float(coordinates[index, axis])
                  for axis in range(4)},
               "raw_peak_to_peak_max_volts": trial.get("raw_peak_to_peak_max_volts", ""),
               "qc_peak_to_peak_over_250uv": trial.get("qc_peak_to_peak_over_250uv", ""),
               "qc_primary_removed": False}
        diagnostic_rows.append(row)
    write_csv(output / "trial_feature_diagnostics.csv", diagnostic_rows)
    class_rows = []
    groups = sorted({(trial["session"], ROLE_ALIASES[trial["role"]]) for trial in trials})
    for session, role in groups:
        group = [index for index, trial in enumerate(trials)
                 if trial["session"] == session and ROLE_ALIASES[trial["role"]] == role]
        by_class = {label: sorted([index for index in group if y[index] == label], key=lambda i: (
            trials[i].get("acquisition_time_utc", ""), trials[i].get("start_sample", i)))
                    for label in (0, 1)}
        matched_count = min(map(len, by_class.values()))
        for selection in ("all_included", "chronological_class_count_matched_diagnostic"):
            for label, indices in by_class.items():
                selected = indices if selection == "all_included" else indices[:matched_count]
                class_rows.append({
                    "subject": subject, "cohort": cohort, "session": session, "role": role,
                    "selection": selection, "label": label, "n_trials": len(selected),
                    "synthetic": synthetic,
                    "n_qc_flagged": sum(bool(trials[i].get("qc_peak_to_peak_over_250uv", False))
                                        for i in selected),
                    "mean_mu_log10_absolute_power_all22": float(log_power[selected, :, 0].mean()),
                    "mean_beta_log10_absolute_power_all22": float(log_power[selected, :, 1].mean()),
                    "mean_covariance_airm_from_source_train": float(
                        covariance_distance[selected].mean()),
                    **{f"source_standardized_mean_{axis + 1}": float(
                        standardized[selected, axis].mean()) for axis in range(44)},
                    **{f"source_pca_mean_{axis + 1}": float(coordinates[selected, axis].mean())
                       for axis in range(4)},
                    "trial_ids": json.dumps([trials[i]["trial_id"] for i in selected]),
                })
    write_csv(output / "session_role_class_feature_summary.csv", class_rows)
    write_json(output / "included_trial_metadata.json", trials)
    receipt = {
        "subject": subject, "cohort": cohort, "synthetic": synthetic,
        "status": "software_validation_only" if synthetic else "descriptive_offline_features",
        "fit_trial_ids": [trials[index]["trial_id"] for index in train],
        "fit_X_sha256": array_digest({"X": X[train]}),
        "source_fit_parameter_sha256_before": before,
        "source_fit_parameter_sha256_after": after, "query_state_unchanged": True,
        "source_train_only_fit": True, "target_support_and_query_never_fitted": True,
        "feature_order": [f"{channel}_{name}" for channel in CHANNEL_NAMES
                          for name, _, _ in bands],
        "power_description": "log10 absolute task-window Welch bandpower in V^2; no ERD baseline",
        "covariance_description": "fixed HelmertCAR21; centered sample covariance; trace normalized; .1I/21 shrinkage",
        "riemannian_mean_convergence": convergence,
        "pca": "sourceTRAIN StandardScaler44 and PCA4 fullSVD whitenFalse; no feature selection",
        "feature_artifact_sha256": file_sha256(output / "fixed_features.npz"),
        "fit_artifact_sha256": file_sha256(output / "feature_source_fit.npz"),
    }
    write_json(output / "feature_fit_audit.json", receipt)
    return receipt


def run_participant(
    X: np.ndarray, y: np.ndarray, trials: list[dict], *, subject: str, cohort: str,
    output: Path, seed: int = 20261012, n_components: int = 4, synthetic: bool = False,
    save_descriptive_features: bool = False,
) -> dict:
    """Execute fixed config; every fitting call is guarded against all query IDs."""
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=np.int64)
    if X.ndim != 3 or X.shape[0] != len(y) or len(y) != len(trials):
        raise ValueError("Epoch, label and frozen trial identity dimensions differ")
    if not np.isfinite(X).all() or set(y.tolist()) != {0, 1}:
        raise ValueError("Nonfinite EEG or unexpected label vocabulary")
    if n_components != 4:
        raise ValueError("Formal baseline has one frozen CSP configuration: 4 components")
    roles = validate_roles(trials, y)
    if save_descriptive_features:
        descriptive_features(X, y, trials, subject=subject, cohort=cohort,
                             output=output, synthetic=synthetic)
    train = roles["source_train"]
    validation = roles["source_validation"]
    all_query = np.r_[roles["source_query"], roles["target_query"]]
    forbidden = set(all_query.tolist()) | set(validation.tolist())
    fit_events = []

    def guarded_fit(csp, lda, indices, method, session, *, fit_csp):
        indices = np.asarray(indices, dtype=int)
        if len(set(indices.tolist())) != len(indices) or set(indices.tolist()) & forbidden:
            raise ValueError("Fit access includes duplicate, validation or held-out query data")
        allowed = set(train.tolist()) | {
            int(i) for i in roles["target_support"] if trials[i]["session"] == session
        }
        if not set(indices.tolist()) <= allowed:
            raise ValueError("Fit includes future or previous-session target support")
        if fit_csp:
            features = csp.fit_transform(X[indices], y[indices])
        else:
            features = csp.transform(X[indices])
        lda.fit(features, y[indices])
        fit_events.append({
            "method": method, "session": session, "n_fit": int(len(indices)),
            "csp_fit": fit_csp, "lda_fit": True,
            "trial_ids": [trials[i]["trial_id"] for i in indices],
            "fit_X_y_sha256": array_digest({"X": X[indices], "y": y[indices]}),
            "query_and_validation_disjoint": True,
            "target_access": "none" if method == "source_only" else "current_session_support_only",
        })

    source_session = trials[int(train[0])]["session"]
    pipeline = make_csp_lda(n_components=n_components, random_state=seed)
    source_csp, source_lda = pipeline.named_steps["csp"], pipeline.named_steps["lda"]
    guarded_fit(source_csp, source_lda, train, "source_only", source_session, fit_csp=True)
    source_before = model_arrays(source_csp, source_lda)
    source_hash = array_digest(source_before)
    np.savez_compressed(output / "source_before.npz", **source_before)
    val_predictions = pipeline.predict(X[validation])
    write_json(output / "source_validation.json", {
        "subject": subject, "cohort": cohort, "synthetic": synthetic,
        "configuration_selection": "none_single_prefixed_config",
        "validation_never_refitted": True,
        "validation_trial_ids": [trials[i]["trial_id"] for i in validation],
        "predictions": val_predictions.tolist(), "labels": y[validation].tolist(),
        **summarize_predictions(y[validation], val_predictions),
    })
    results, predictions, audits = [], [], []
    sessions = [source_session] + sorted({trials[i]["session"] for i in roles["target_query"]})
    for session in sessions:
        is_source = session == source_session
        query_role = "source_query" if is_source else "target_query"
        query = np.asarray([i for i in roles[query_role] if trials[i]["session"] == session])
        support = np.asarray([] if is_source else [
            i for i in roles["target_support"] if trials[i]["session"] == session
        ], dtype=int)
        if not is_source and (not len(support) or len(support) > 20):
            raise ValueError("Current-session target support exceeds frozen20-event budget")
        combined = np.r_[train, support]
        for method in METHODS:
            fit_start = time.monotonic()
            if method == "source_only" or is_source:
                csp, lda = source_csp, source_lda
                fit_ids = train
                method_support = np.asarray([], dtype=int)
            elif method == "frozen_csp_lda_recalibration":
                csp = source_csp
                lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
                fit_ids, method_support = combined, support
                guarded_fit(csp, lda, combined, method, session, fit_csp=False)
            else:
                adapted = make_csp_lda(n_components=n_components, random_state=seed)
                csp, lda = adapted.named_steps["csp"], adapted.named_steps["lda"]
                fit_ids, method_support = combined, support
                guarded_fit(csp, lda, combined, method, session, fit_csp=True)
            fit_seconds = time.monotonic() - fit_start
            arrays = model_arrays(csp, lda)
            before = array_digest(arrays)
            prediction = lda.predict(csp.transform(X[query]))
            replay = predict_from_arrays(arrays, X[query])
            if not np.array_equal(prediction, replay):
                raise AssertionError("Pickle-free model replay differs from fitted estimator")
            after = array_digest(model_arrays(csp, lda))
            if before != after:
                raise AssertionError("Query prediction changed model parameters")
            model_name = f"{session}_{method}_model.npz"
            np.savez_compressed(output / model_name, **arrays)
            row = {
                "subject": subject, "cohort": cohort, "session": session,
                "method": method, "synthetic": synthetic, "n_source_train": int(len(train)),
                "n_target_support": int(len(method_support)), "n_fit": int(len(fit_ids)),
                **summarize_predictions(y[query], prediction),
                "model_parameter_sha256": before, "fit_seconds": fit_seconds,
            }
            results.append(row)
            predictions.extend({
                "subject": subject, "cohort": cohort, "session": session, "run": trials[i]["run"],
                "method": method, "trial_id": trials[i]["trial_id"],
                "label": int(y[i]), "prediction": int(value),
                "label_name": LABEL_NAMES[int(y[i])], "prediction_name": LABEL_NAMES[int(value)],
                "synthetic": synthetic,
            } for i, value in zip(query, prediction, strict=True))
            audits.append({
                "subject": subject, "cohort": cohort, "session": session, "method": method,
                "model_artifact": model_name, "artifact_sha256": file_sha256(output / model_name),
                "parameter_sha256_before": before, "parameter_sha256_after": after,
                "query_state_unchanged": True, "pickle_free_prediction_replay_exact": True,
                "source_csp_parameter_sha256": array_digest({
                    key: value for key, value in source_before.items() if key.startswith("csp_")
                }),
                "fit_trial_ids": [trials[i]["trial_id"] for i in fit_ids],
                "target_support_trial_ids": [trials[i]["trial_id"] for i in method_support],
                "query_trial_ids": [trials[i]["trial_id"] for i in query],
                "target_budget_current_session_only": True, "query_never_used_for_fit": True,
            })
    source_after = model_arrays(source_csp, source_lda)
    if source_hash != array_digest(source_after):
        raise AssertionError("Source parameters changed during target evaluation or adaptation")
    np.savez_compressed(output / "source_after.npz", **source_after)
    write_csv(output / "metrics.csv", results)
    write_csv(output / "query_predictions.csv", predictions)
    write_json(output / "fit_access_audit.json", fit_events)
    write_json(output / "model_audit.json", audits)
    write_json(output / "participant_receipt.json", {
        "status": "software_validation_only" if synthetic else "completed_frozen_offline_protocol",
        "synthetic": synthetic, "subject": subject, "cohort": cohort,
        "seed": seed, "shape": list(X.shape), "duration_seconds": time.monotonic() - started,
        "source_parameter_sha256_before": source_hash,
        "source_parameter_sha256_after": array_digest(source_after), "source_frozen": True,
        "source_validation_trial_ids": [trials[i]["trial_id"] for i in validation],
        "n_fit_events": len(fit_events), "query_never_used_for_fit": True,
        "config_selection": "none; fixed4CSP LedoitWolf and lsqr-auto LDA",
        "label_names": LABEL_NAMES,
    })
    return {"metrics": results, "predictions": predictions, "audits": audits,
            "fit_events": fit_events, "source_hash": source_hash}


def approval_gate(config_path: Path, manifest_path: Path, approval_path: Path) -> dict:
    """Bind scientific approval to exactly the executable frozen inputs."""
    approval = json.loads(approval_path.read_text())
    if approval.get("status") != "approved_for_baseline_execution":
        raise ValueError("Independent formal baseline approval has not passed")
    for key, path in (("config_sha256", config_path), ("split_manifest_sha256", manifest_path)):
        if approval.get(key) != file_sha256(path):
            raise ValueError(f"Frozen approval mismatch: {key}")
    for prefix in ("protocol", "source_gate_receipt"):
        path = Path(approval[f"{prefix}_path"])
        if not path.is_absolute():
            path = ROOT / path
        if approval.get(f"{prefix}_sha256") != file_sha256(path):
            raise ValueError(f"Frozen approval mismatch: {prefix}")
    return approval


def runtime_provenance() -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                            capture_output=True, check=True).stdout.strip()
    versions = {name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "scikit-learn", "mne")}
    return {"source_commit": commit, "versions": versions,
            "thread_environment": {name: os.environ[name] for name in (
                "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
            "thread_pools": threadpool_info(),
            "script_sha256": file_sha256(Path(__file__)),
            "decoder_source_sha256": file_sha256(
                ROOT / "src/learning_preserving_bci/decoders/csp_lda.py"),
            "execution": "CPU; serial one participant; no EEGNet; one fixed configuration"}


def validate_effective_configuration(config: dict) -> None:
    """Reject any configuration whose algorithm differs from these frozen constants."""
    expected = {
        "methods": list(METHODS),
        "csp": {"n_components": 4, "reg": "ledoit_wolf", "log": True, "norm_trace": False},
        "lda": {"solver": "lsqr", "shrinkage": "auto"},
    }
    for key, value in expected.items():
        if config["baseline"].get(key) != value:
            raise ValueError(f"Unimplemented baseline configuration: {key}")
    features = config["descriptive_features"]
    expected_features = {
        "welch": {"sfreq": 128.0, "window": "hann", "nperseg": 256, "noverlap": 128,
                  "detrend": "constant", "scaling": "density", "average": "mean",
                  "return_onesided": True},
        "bands_hz": {"mu": [8.0, 13.0], "beta": [13.0, 30.0]},
        "power": "absolute_V_squared_trapezoid_including_edge_bins",
        "power_transform": "log10_max_power_float64_tiny",
        "power_feature_order": "channel_major_mu_then_beta_in_CHANNEL_NAMES_order_44_dimensions",
        "covariance": {"basis": "scipy.linalg.helmert_22_full_false_fixed_21_by_22",
                       "time_center": True, "estimator": "unbiased_sample_covariance_n_minus_1",
                       "trace_normalize_before_shrinkage": True, "identity_shrinkage": 0.1,
                       "formula": "0.9_C_trace_normalized_plus_0.1_I_divided_by_21", "dimension": 21},
        "riemann_reference": {"fit_role": "source_train_only", "metric": "affine_invariant",
                              "initializer": "arithmetic_mean", "max_iterations": 100,
                              "tolerance": 1e-10, "step": 1.0,
                              "target_access": "distance_transform_only_no_refit"},
        "standard_scaler": {"fit_role": "source_train_only", "with_mean": True, "with_std": True},
        "pca": {"fit_role": "source_train_only", "n_components": 4, "svd_solver": "full",
                "whiten": False, "target_access": "transform_only_no_refit"},
    }
    for key, value in expected_features.items():
        if features.get(key) != value:
            raise ValueError(f"Unimplemented descriptive feature configuration: {key}")


def participant_bootstrap_summary(rows: list[dict], *, seed: int = 42,
                                  replicates: int = 10000) -> tuple[list[dict], dict]:
    """Each participant contributes one equally session-weighted target endpoint."""
    endpoints = []
    subjects = sorted({row["subject"] for row in rows},
                      key=lambda subject: int(subject.removeprefix("sub-")))
    for subject in subjects:
        participant = [row for row in rows if row["subject"] == subject]
        for method in METHODS:
            target = [row for row in participant if row["method"] == method
                      and row["session"] != "ses-0"]
            source = [row for row in participant if row["method"] == method
                      and row["session"] == "ses-0"]
            if len(target) != 5 or len(source) != 1:
                raise ValueError("Participant endpoint requires all five target sessions and reference")
            endpoints.append({
                "subject": subject, "cohort": participant[0]["cohort"], "method": method,
                "n_target_sessions": 5,
                "mean_target_balanced_accuracy": float(np.mean([
                    row["balanced_accuracy"] for row in target])),
                "reference_query_balanced_accuracy": source[0]["balanced_accuracy"],
                "n_target_queries": sum(row["n_query"] for row in target),
                "n_target_class_collapsed_sessions": sum(row["class_collapse"] for row in target),
            })
    summary = {"independent_unit": "participant", "bootstrap_seed": seed,
               "bootstrap_replicates": replicates,
               "interval": "percentile95_participant_bootstrap",
               "target_session_weight": "equal_within_each_participant",
               "primary_comparison": "refit_csp_lda_minus_source_only",
               "primary_cohort": "final_test", "cohorts": {}}
    for cohort in ("development", "final_test", "all_published_ids_descriptive"):
        selected = [row for row in endpoints if cohort == "all_published_ids_descriptive"
                    or row["cohort"] == cohort]
        cohort_subjects = sorted({row["subject"] for row in selected})
        if not cohort_subjects:
            continue
        values = np.asarray([[next(row["mean_target_balanced_accuracy"] for row in selected
                                   if row["subject"] == subject and row["method"] == method)
                              for method in METHODS] for subject in cohort_subjects])
        rng = np.random.default_rng(seed)
        indices = rng.integers(0, len(values), size=(replicates, len(values)))
        means = values[indices].mean(axis=1)
        comparisons = {"frozen_csp_lda_recalibration_minus_source_only": (1, 0),
                       "refit_csp_lda_minus_source_only": (2, 0),
                       "refit_csp_lda_minus_frozen_csp_lda_recalibration": (2, 1)}
        cohort_summary = {"n_participants": len(values), "subjects": cohort_subjects,
                          "methods": {}, "paired_comparisons": {}}
        for index, method in enumerate(METHODS):
            cohort_summary["methods"][method] = {
                "mean_balanced_accuracy": float(values[:, index].mean()),
                "median_balanced_accuracy": float(np.median(values[:, index])),
                "ci95": np.quantile(means[:, index], [0.025, 0.975]).tolist(),
                "participant_values": values[:, index].tolist(),
            }
        for name, (left, right) in comparisons.items():
            difference = values[:, left] - values[:, right]
            cohort_summary["paired_comparisons"][name] = {
                "mean_difference": float(difference.mean()),
                "median_difference": float(np.median(difference)),
                "ci95": np.quantile(means[:, left] - means[:, right], [0.025, 0.975]).tolist(),
                "participants_positive": int(np.count_nonzero(difference > 0)),
                "participants_zero": int(np.count_nonzero(difference == 0)),
                "participants_negative": int(np.count_nonzero(difference < 0)),
                "participant_differences": difference.tolist(),
            }
        summary["cohorts"][cohort] = cohort_summary
    return endpoints, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--approval-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mirror", type=Path, required=True)
    parser.add_argument("--data-root", type=Path,
                        default=ROOT / "data/public_eeg/kumar2024/nm000177/v1.0.5")
    args = parser.parse_args()
    approval = approval_gate(args.config, args.split_manifest, args.approval_receipt)
    config, manifest = json.loads(args.config.read_text()), json.loads(args.split_manifest.read_text())
    if "descriptive_features" not in config:
        raise ValueError("Approved configuration must freeze descriptive features before performance")
    validate_effective_configuration(config)
    # Import only after qualification; adapter owns source-specific window/preprocessing rules.
    from learning_preserving_bci.datasets.kumar import load_subject
    args.output.mkdir(parents=True, exist_ok=False)
    args.mirror.mkdir(parents=True, exist_ok=False)
    mne.set_log_level("ERROR")
    started = time.monotonic()
    provenance = runtime_provenance()
    provenance["adapter_source_sha256"] = file_sha256(
        ROOT / "src/learning_preserving_bci/datasets/kumar.py")
    rows, predictions, failures = [], [], []
    participants = config["subjects"]
    seed = int(config.get("seed", 20261012))
    for subject in participants:
        try:
            bundle = load_subject(args.data_root, subject, config, split_manifest=manifest)
            cohort = str(bundle.metadata[0]["cohort"])
            result = run_participant(bundle.X, bundle.y, bundle.metadata, subject=subject,
                                     cohort=cohort, output=args.output / subject, seed=seed,
                                     save_descriptive_features=True)
            write_json(args.output / subject / "source_event_metadata.json", bundle.source_events)
            write_json(args.output / subject / "adapter_provenance.json", bundle.provenance)
            rows.extend(result["metrics"])
            predictions.extend(result["predictions"])
            print(json.dumps({"subject": subject, "status": "completed", "cohort": cohort,
                              "rows": len(result["metrics"])}), flush=True)
            # Preserve every small evidence artifact, without large weights or raw tensors.
            destination = args.mirror / subject
            destination.mkdir()
            for path in (args.output / subject).iterdir():
                if path.suffix in (".json", ".csv"):
                    shutil.copyfile(path, destination / path.name)
            del bundle, result
        except Exception as error:
            failures.append({"subject": subject, "type": type(error).__name__, "message": str(error)})
            print(json.dumps({"subject": subject, "status": "failed", **failures[-1]}), flush=True)
    if rows:
        write_csv(args.output / "metrics.csv", rows)
        write_csv(args.output / "query_predictions.csv", predictions)
        endpoints, summary = participant_bootstrap_summary(
            rows, seed=int(config["statistics"]["seed"]),
            replicates=int(config["statistics"]["bootstrap_replicates"]))
        write_csv(args.output / "participant_endpoints.csv", endpoints)
        write_json(args.output / "participant_bootstrap_summary.json", summary)
    write_json(args.output / "failures.json", failures)
    receipt = {
        "status": "completed_frozen_offline_protocol" if not failures else "completed_with_failures",
        "synthetic": False, "participants_planned": participants,
        "participants_completed": sorted({row["subject"] for row in rows}),
        "config_sha256": file_sha256(args.config),
        "split_manifest_sha256": file_sha256(args.split_manifest),
        "approval_receipt_sha256": file_sha256(args.approval_receipt),
        "independent_approval": approval, "provenance": provenance,
        "seed": seed, "duration_seconds": time.monotonic() - started,
        "fixed_methods": list(METHODS), "source_validation_used_for_selection": False,
        "descriptive_features": config["descriptive_features"],
        "target_query_never_fitted": True, "adaptation_support": "current_session_only",
        "no_online_skill_or_retention_claim": True, "failures": failures,
        "outputs": {path.relative_to(args.output).as_posix(): file_sha256(path)
                    for path in sorted(args.output.rglob("*")) if path.is_file()},
    }
    write_json(args.output / "execution_receipt.json", receipt)
    for path in args.output.iterdir():
        if path.is_file() and path.suffix in (".csv", ".json"):
            shutil.copyfile(path, args.mirror / path.name)
    snapshots = args.mirror / "source_snapshot"
    snapshots.mkdir()
    for path in (Path(__file__), args.config, args.split_manifest, args.approval_receipt,
                 ROOT / "src/learning_preserving_bci/datasets/kumar.py",
                 ROOT / "src/learning_preserving_bci/decoders/csp_lda.py",
                 ROOT / "tests/test_kumar_baselines.py"):
        shutil.copyfile(path, snapshots / path.name)
    if failures:
        raise SystemExit("Formal baseline failures recorded; do not infer complete-cohort results")


if __name__ == "__main__":
    main()
