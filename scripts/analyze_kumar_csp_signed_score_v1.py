#!/usr/bin/env python3
"""Development-only supervised CSP measurement; no query or adaptation access.

Source-run cyclic controls refit the *whole* label-dependent CSP/LDA pipeline.
Twenty train rotations per fold are cached, then crossed with twenty held-out
label rotations. Existing all40 source models are verified and replayed only.
"""

# ruff: noqa: E402 -- set CPU caps before importing numerical libraries.
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"

import mne
import numpy as np
import sklearn
from sklearn.preprocessing import StandardScaler

from learning_preserving_bci.decoders.csp_lda import make_csp_lda

ROOT = Path(__file__).resolve().parents[1]


def _load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lowdim = _load_helper("kumar_csp_lowdim_dependency", "analyze_kumar_lowdim_reliability.py")
baseline = _load_helper("kumar_csp_baseline_dependency", "run_kumar_baselines.py")
DEVELOPMENT_SUBJECTS = lowdim.DEVELOPMENT_SUBJECTS
file_digest = lowdim.file_digest
json_digest = lowdim.json_digest
validate_selected_metadata = lowdim.validate_selected_metadata
chronological_indices = lowdim.chronological_indices


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def _resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def validate_config(config):
    for key, expected in {"development_subjects": DEVELOPMENT_SUBJECTS, "seed": 42,
                          "bootstrap_replicates": 10000}.items():
        if config.get(key) != expected:
            raise ValueError(f"Frozen measurement config mismatch: {key}")
    if set(config.get("allowed_roles", [])) != lowdim.ALLOWED_ROLES:
        raise ValueError("Forbidden allowed_roles")
    for key in ("query_access", "final_cohort_access", "automatic_candidate_selection",
                "adaptation_gate_threshold_search"):
        if config.get(key) is not False:
            raise ValueError(f"Forbidden measurement access/selection: {key}")
    bindings = []
    for prefix in ("frozen_config", "plan"):
        path = _resolve(config[f"{prefix}_path"])
        actual = file_digest(path)
        if actual != config[f"{prefix}_sha256"]:
            raise ValueError(f"Frozen {prefix} SHA mismatch")
        bindings.append({"path": str(path), "sha256": actual})
    frozen = json.loads(_resolve(config["frozen_config_path"]).read_text())
    expected_csp = {"n_components": 4, "reg": "ledoit_wolf", "log": True,
                    "norm_trace": False}
    if frozen["baseline"]["csp"] != expected_csp or frozen["baseline"]["lda"] != {
            "solver": "lsqr", "shrinkage": "auto"}:
        raise ValueError("Original frozen CSP/LDA configuration mismatch")
    return bindings


def load_restricted_subject(folder, subject):
    if subject not in DEVELOPMENT_SUBJECTS:
        raise ValueError("Forbidden final subject")
    metadata_path = folder / "included_trial_metadata.json"
    epoch_path = folder / "restricted_epochs.npz"
    receipt_path = folder / "subject_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    for path, keys in ((metadata_path, ("metadata_sha256", "included_trial_metadata_sha256")),
                       (epoch_path, ("epochs_sha256", "restricted_epochs_sha256"))):
        bound = [receipt[key] for key in keys if key in receipt]
        if not bound or any(value != file_digest(path) for value in bound):
            raise ValueError(f"Restricted preparation SHA mismatch: {path.name}")
    metadata = json.loads(metadata_path.read_text())
    validate_selected_metadata(metadata, subject)
    labels = np.asarray([int(t["label"] == "right_hand") for t in metadata], dtype=np.int64)
    ids = [t["trial_id"] for t in metadata]
    with np.load(epoch_path, allow_pickle=False) as data:
        if set(data.files) != {"X", "y", "trial_ids"}:
            raise ValueError("Unexpected restricted epoch fields")
        X = data["X"].copy()
        if list(data["trial_ids"]) != ids or not np.array_equal(data["y"], labels):
            raise ValueError("Restricted epoch identity or label mismatch")
    if X.dtype.str != "<f4" or X.shape != (len(metadata), 22, 640) or not np.isfinite(X).all():
        raise ValueError("Invalid frozen float32 22x640 epochs")
    for epoch, row in zip(X, metadata, strict=True):
        actual = hashlib.sha256(epoch.tobytes(order="C")).hexdigest()
        if actual != row.get("processed_window_numeric_sha256"):
            raise ValueError("Processed epoch numeric SHA mismatch")
        if row.get("processed_numeric_unit") != "V" or row.get("processed_sample_count") != 640:
            raise ValueError("Processed epoch units or length mismatch")
    inputs = [{"path": str(path.resolve()), "sha256": file_digest(path)}
              for path in (metadata_path, epoch_path, receipt_path)]
    return X, labels, metadata, inputs


def csp_features_and_scores(arrays, X):
    if int(arrays["n_components"]) != 4 or not np.array_equal(arrays["lda_classes"], [0, 1]):
        raise ValueError("Frozen CSP4/binary class state mismatch")
    projected = np.asarray(arrays["csp_filters"][:4], dtype=float) @ np.asarray(X, dtype=float)
    power = np.square(projected).mean(axis=-1)
    if np.any(power <= 0) or not np.isfinite(power).all():
        raise ValueError("Invalid frozen CSP power")
    features = np.log(power)
    scores = features @ arrays["lda_coef"].T + arrays["lda_intercept"]
    if scores.shape != (len(X), 1) or not np.isfinite(scores).all():
        raise ValueError("Invalid frozen LDA score")
    return features, scores[:, 0]


def score_summary(scores, labels):
    scores, labels = np.asarray(scores), np.asarray(labels)
    predictions = (scores > 0).astype(int)
    recalls = [float(np.mean(predictions[labels == value] == value))
               if np.any(labels == value) else None for value in (0, 1)]
    return {"balanced_accuracy": None if None in recalls else float(np.mean(recalls)),
            "class_recall": recalls, "prediction_ratio": [float(np.mean(predictions == value))
                                                         for value in (0, 1)],
            "class_collapse": len(np.unique(predictions)) < 2,
            "score_mean": float(np.mean(scores)), "score_sd_ddof1": float(np.std(scores, ddof=1)),
            "score_class_means": [float(np.mean(scores[labels == value]))
                                  if np.any(labels == value) else None for value in (0, 1)]}


def source_phase_alignment_control(folds, labels_by_run, *, model_factory=make_csp_lda,
                                   state_extractor=None, output=None):
    """Cross saved predictions exactly; held-out rotations never change fitted X/y."""
    if state_extractor is None:
        def state_extractor(model):
            return baseline.model_arrays(model.named_steps["csp"], model.named_steps["lda"])
    sizes = [len(y) for y in labels_by_run]
    if sizes != [20, 20]:
        raise ValueError("Frozen source rotation budget requires two 20-trial runs")
    pairs = list(itertools.product(range(20), range(20)))
    cache, fit_rows, successful = {}, [], 0
    for fold_index, fold in enumerate(folds):
        train_run, holdout_run = fold["train_run_index"], fold["holdout_run_index"]
        if (train_run, holdout_run) not in ((0, 1), (1, 0)):
            raise ValueError("Invalid source LORO fold")
        for train_shift in range(20):
            shifted = np.roll(labels_by_run[train_run], train_shift)
            row = {"fold": fold_index, "train_run_index": train_run,
                   "holdout_run_index": holdout_run, "train_shift": train_shift,
                   "train_trial_ids": fold["train_trial_ids"],
                   "heldout_trial_ids": fold["heldout_trial_ids"],
                   "fit_n": len(shifted), "shifted_train_labels": shifted.tolist(),
                   "fit_X_y_sha256": baseline.array_digest({
                       "X": np.asarray(fold["train"], dtype=float), "y": shifted}),
                   "train_labels_sha256": lowdim.array_digest(shifted),
                   "heldout_X_sha256": lowdim.array_digest(fold["holdout"]),
                   "holdout_prediction_only": True, "fit_status": "failed",
                   "failure": None, "heldout_predictions": None, "heldout_scores": None,
                   "heldout_CSP_log_power4": None,
                   "model_parameter_sha256": None, "model_artifact": None}
            started = time.perf_counter()
            try:
                model = model_factory(n_components=4, random_state=42)
                model.fit(fold["train"], shifted)
                arrays = state_extractor(model)
                before = baseline.array_digest(arrays)
                predictions = np.asarray(model.predict(fold["holdout"]), dtype=int)
                if predictions.shape != (20,) or not set(predictions.tolist()) <= {0, 1}:
                    raise ValueError("Invalid source-heldout predictions")
                if baseline.array_digest(state_extractor(model)) != before:
                    raise ValueError("Heldout prediction changed model state")
                row.update({"fit_status": "completed", "heldout_predictions": predictions.tolist(),
                            "model_parameter_sha256": before})
                if "csp_filters" in arrays:
                    heldout_features, scores = csp_features_and_scores(arrays, fold["holdout"])
                    if not np.array_equal((scores > 0).astype(int), predictions):
                        raise ValueError("Source-heldout pickle-free replay mismatch")
                    row["heldout_scores"] = scores.tolist()
                    row["heldout_CSP_log_power4"] = heldout_features.tolist()
                if output is not None:
                    model_path = output / f"fold-{fold_index}_train-shift-{train_shift:02d}.npz"
                    np.savez_compressed(model_path, **arrays)
                    row["model_artifact"] = str(model_path.resolve())
                    row["model_artifact_sha256"] = file_digest(model_path)
                successful += 1
            except Exception as error:
                row.update({"fit_status": "failed", "failure": {
                    "type": type(error).__name__, "message": str(error)},
                    "heldout_predictions": None, "heldout_scores": None,
                    "heldout_CSP_log_power4": None})
            row["fit_and_predict_seconds"] = time.perf_counter() - started
            fit_rows.append(row)
            cache[(fold_index, train_shift)] = row
    null, observed = [], []
    for shift0, shift1 in pairs:
        values, diagnostics = [], []
        shifts = [shift0, shift1]
        for fold_index, fold in enumerate(folds):
            row = cache[(fold_index, shifts[fold["train_run_index"]])]
            y = np.roll(labels_by_run[fold["holdout_run_index"]], shifts[fold["holdout_run_index"]])
            prediction = row["heldout_predictions"]
            if prediction is None:
                summary = {"balanced_accuracy": None, "class_recall": [None, None],
                           "prediction_ratio": [None, None], "class_collapse": None}
            else:
                prediction = np.asarray(prediction)
                recalls = [float(np.mean(prediction[y == value] == value)) for value in (0, 1)]
                summary = {"balanced_accuracy": float(np.mean(recalls)), "class_recall": recalls,
                           "prediction_ratio": [float(np.mean(prediction == value)) for value in (0, 1)],
                           "class_collapse": len(np.unique(prediction)) < 2}
            values.append(summary["balanced_accuracy"])
            diagnostics.append({"fold": fold_index, "train_shift": row["train_shift"],
                                "heldout_shift": shifts[fold["holdout_run_index"]],
                                "model_parameter_sha256": row["model_parameter_sha256"],
                                "fit_status": row["fit_status"], **summary})
        null.append({"run0_shift": shift0, "run1_shift": shift1,
                     "fold_balanced_accuracy": values, "fold_diagnostics": diagnostics,
                     "twofold_balanced_accuracy": None if None in values else float(np.mean(values))})
        if shift0 == shift1 == 0:
            observed = diagnostics
    unique = [len({tuple(np.roll(y, k)) for k in range(20)}) for y in labels_by_run]
    return {"pairs": [list(pair) for pair in pairs], "shared_shift_pairs_sha256": json_digest(pairs),
            "shift_pair_count": 400, "identity_included": True,
            "unique_rotated_label_assignments_per_run": unique,
            "unique_paired_label_assignments": int(np.prod(unique)),
            "original_labels_by_run": [labels.tolist() for labels in labels_by_run],
            "pipeline_fit_attempts": len(fit_rows), "pipeline_fit_successes": successful,
            "pipeline_fit_failures": len(fit_rows) - successful,
            "observed_pipeline_fit_attempts_included_in_total": 2,
            "nominal_csp_and_lda_estimator_fit_attempts": 2 * len(fit_rows),
            "heldout_prediction_rows": sum(20 for row in fit_rows if row["heldout_predictions"] is not None),
            "fit_rows": fit_rows, "observed": observed, "null": null,
            "interpretation": "cyclic phase sensitivity; not an exchangeable formal permutation p-value"}


def load_verified_source_model(folder, subject, source_X, source_y, source_ids, r2_receipt):
    if subject not in DEVELOPMENT_SUBJECTS:
        raise ValueError("Forbidden final subject")
    if r2_receipt.get("status") != "completed" or r2_receipt.get("readback_mode") != "all":
        raise ValueError("Baseline R2 receipt is not all-object closed")
    inputs = []
    for name in ("source_before.npz", "source_after.npz", "participant_receipt.json",
                 "fit_access_audit.json"):
        relative = f"sub-{subject}/{name}"
        entries = [row for row in r2_receipt["files"] if row["relative_path"] == relative]
        path = folder / name
        if len(entries) != 1:
            raise ValueError("Baseline R2 artifact identity mismatch")
        row = entries[0]
        if (row.get("verification") != "full_get_sha256_verified" or
                row.get("head_http_status") != 200 or row.get("get_http_status") != 200 or
                row.get("readback_bytes") != row["bytes"] or path.stat().st_size != row["bytes"] or
                file_digest(path) != row["sha256"]):
            raise ValueError(f"Baseline artifact SHA/readback mismatch: {relative}")
        inputs.append({"path": str(path.resolve()), "sha256": row["sha256"],
                       "r2_closed_full_get_verified": True})
    with np.load(folder / "source_before.npz", allow_pickle=False) as data:
        before = {key: data[key].copy() for key in data.files}
    with np.load(folder / "source_after.npz", allow_pickle=False) as data:
        after = {key: data[key].copy() for key in data.files}
    state_sha = baseline.array_digest(before)
    if set(before) != set(after) or any(not np.array_equal(before[key], after[key]) for key in before):
        raise ValueError("Frozen source before/after arrays differ")
    participant = json.loads((folder / "participant_receipt.json").read_text())
    if (participant.get("subject") != f"sub-{subject}" or participant.get("cohort") != "development" or
            participant.get("synthetic") is not False or participant.get("source_frozen") is not True or
            participant.get("source_parameter_sha256_before") != state_sha or
            participant.get("source_parameter_sha256_after") != state_sha):
        raise ValueError("Frozen source participant parameter SHA mismatch")
    audits = json.loads((folder / "fit_access_audit.json").read_text())
    source = [row for row in audits if row["method"] == "source_only"]
    if (len(source) != 1 or source[0]["trial_ids"] != source_ids or source[0]["n_fit"] != 40 or
            source[0]["session"] != "ses-0" or source[0].get("target_access") != "none" or
            source[0].get("fit_X_y_sha256") != baseline.array_digest({
                "X": np.asarray(source_X, dtype=float), "y": np.asarray(source_y, dtype=np.int64)})):
        raise ValueError("Frozen model source-only fit identity/data mismatch")
    csp_features_and_scores(before, source_X)
    return before, {"parameter_sha256": state_sha, "source_fit_trial_ids": source_ids,
                    "source_fit_n": 40, "loaded_frozen_model_no_refit": True,
                    "source_before_after_array_equal": True, "inputs": inputs}


def support_measure(source_z, source_labels, support_z, labels, scores, source_score_sd,
                    halves=None, source_reference=None):
    vector = lowdim.support_measure(source_z, source_labels, support_z, labels, halves,
                                    source_reference)
    halves = lowdim.classwise_halves(labels) if halves is None else halves
    valid_sd = bool(np.isfinite(source_score_sd) and source_score_sd > 0)
    half_rows = []
    for index in halves if halves is not None else []:
        y, value = labels[index], scores[index]
        summary = score_summary(value, y)
        left, right = summary["score_class_means"]
        contrast = None if left is None or right is None or not valid_sd else (right - left) / 2 / source_score_sd
        half_rows.append({"indices": index.tolist(), "class_counts": [int(np.sum(y == k)) for k in (0, 1)],
                          "class_balanced_true_class_signed_margin_source_sd": contrast,
                          "right_signed_score_mean_source_sd": None if right is None or not valid_sd else right / source_score_sd,
                          "left_signed_score_mean_source_sd": None if left is None or not valid_sd else -left / source_score_sd,
                          "score_bias_mean_source_sd": None if not valid_sd else float(np.mean(value) / source_score_sd),
                          **summary})
    contrasts = [row["class_balanced_true_class_signed_margin_source_sd"] for row in half_rows]
    if len(contrasts) != 2:
        contrasts = [None, None]
    return {**vector, "source_LDA_score_sd_ddof1": source_score_sd,
            "source_LDA_score_sd_valid": valid_sd, "half_score_diagnostics": half_rows,
            "half_LDA_signed_contrasts_source_sd": contrasts,
            "half_LDA_signed_contrast_product": None if None in contrasts else float(np.prod(contrasts)),
            "full_support_score_diagnostics": score_summary(scores, labels),
            "source_intercept_preserved": True, "target_score_centering_or_scaling": False}


def support_phase_alignment_control(source_z, source_labels, support_z, labels, scores,
                                    source_score_sd):
    original = lowdim.classwise_halves(labels)
    if original is None:
        raise ValueError("Insufficient original support halves")
    reference = lowdim.source_axis_reference(source_z, source_labels)
    rows = []
    for shift in range(len(labels)):
        shifted = np.roll(labels, shift)
        rows.append({"shift": shift, "shifted_labels": shifted.tolist(),
                     "recomputed_classwise_halves": support_measure(
                         source_z, source_labels, support_z, shifted, scores, source_score_sd,
                         source_reference=reference),
                     "fixed_original_half_indices": support_measure(
                         source_z, source_labels, support_z, shifted, scores, source_score_sd,
                         original, reference)})
    observed = rows[0]["recomputed_classwise_halves"]
    comparisons = {}
    for mode in ("recomputed_classwise_halves", "fixed_original_half_indices"):
        comparisons[mode] = {metric: lowdim.null_comparison(
            observed[metric], [row[mode][metric] for row in rows]) for metric in (
                "source_support_direction_cosine", "support_split_half_direction_cosine",
                "half_scalar_product", "half_LDA_signed_contrast_product")}
        comparisons[mode].update({
            "single_class_control_count": sum(row[mode].get("single_class_half_count", 0) > 0 for row in rows),
            "zero_half_direction_control_count": sum(row[mode].get("zero_direction_half_count", 0) > 0 for row in rows),
            "invalid_source_direction_control_count": sum(not row[mode].get("source_direction_valid", False) for row in rows),
            "invalid_source_score_sd_control_count": sum(not row[mode]["source_LDA_score_sd_valid"] for row in rows)})
    return {"observed": observed, "null": rows, "comparisons": comparisons,
            "shift_count": len(labels), "identity_included": True,
            "unique_rotated_label_assignments": len({tuple(np.roll(labels, k)) for k in range(len(labels))})}


def analyze_subject(X, labels, metadata, subject, model_arrays, model_audit, output):
    validate_selected_metadata(metadata, subject)
    output.mkdir(parents=True, exist_ok=False)
    ids = [row["trial_id"] for row in metadata]
    runs = [chronological_indices(metadata, "source_train", "ses-0", f"run-{run}") for run in (0, 1)]
    folds = [{"train_run_index": a, "holdout_run_index": b, "train": X[runs[a]],
              "holdout": X[runs[b]], "train_trial_ids": [ids[i] for i in runs[a]],
              "heldout_trial_ids": [ids[i] for i in runs[b]]} for a, b in ((0, 1), (1, 0))]
    model_output = output / "source_loro_models"
    model_output.mkdir()
    controls = source_phase_alignment_control(folds, [labels[run] for run in runs], output=model_output)
    source = chronological_indices(metadata, "source_train", "ses-0")
    features, scores = csp_features_and_scores(model_arrays, X)
    scaler = StandardScaler().fit(features[source])
    z = scaler.transform(features)
    source_sd = float(np.std(scores[source], ddof=1))
    fit_state = {"source_fit_trial_ids": [ids[i] for i in source], "fit_n": 40,
                 "fit_source_CSP_features_sha256": lowdim.array_digest(features[source]),
                 "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
                 "scaler_var_ddof0": scaler.var_.tolist(), "source_LDA_score_sd_ddof1": source_sd,
                 "source_LDA_score_mean": float(scores[source].mean()),
                 "decoder_parameter_sha256": baseline.array_digest(model_arrays),
                 "source_only_scaler_fit": True, "new_full40_decoder_fit": False}
    fit_state["state_sha256"] = json_digest(fit_state)
    np.savez_compressed(output / "selected_CSP_features_and_frozen_scores.npz",
                        trial_ids=np.asarray(ids), labels=labels, log_CSP_power4=features,
                        source_standardized_CSP4=z, frozen_source_LDA_scores=scores,
                        scaler_mean=scaler.mean_, scaler_scale=scaler.scale_, scaler_var=scaler.var_)
    support_rows = []
    for session in [f"ses-{i}" for i in range(1, 6)]:
        index = chronological_indices(metadata, "target_support", session, "run-0")
        control = support_phase_alignment_control(z[source], labels[source], z[index], labels[index],
                                                 scores[index], source_sd)
        support_rows.append({"subject": subject, "session": session,
                             "source_trial_ids": [ids[i] for i in source],
                             "support_trial_ids": [ids[i] for i in index],
                             "support_labels": labels[index].tolist(), "support_n": len(index),
                             "support_class_counts": [int(np.sum(labels[index] == k)) for k in (0, 1)],
                             "support_qc_flagged_count": sum(bool(metadata[i].get("qc_peak_to_peak_over_250uv", False)) for i in index),
                             "selected_support_epoch_sha256": lowdim.array_digest(X[index]),
                             "source_coordinate_state_sha256": fit_state["state_sha256"], **control})
    observed_values = [row["balanced_accuracy"] for row in controls["observed"]]
    observed_ba = None if None in observed_values else float(np.mean(observed_values))
    result = {"subject": subject, "source_twofold_balanced_accuracy": observed_ba,
              "source_phase_alignment_control": controls,
              "source_phase_alignment_comparison": lowdim.null_comparison(observed_ba, [
                  row["twofold_balanced_accuracy"] for row in controls["null"]]),
              "source_model_audit": model_audit, "source_coordinate_fit_state": fit_state,
              "support_rows": support_rows, "query_rows_used": 0, "new_adaptation_fits": 0,
              "source_fit_access_ids": [ids[i] for i in source],
              "selected_trial_ids_sha256": json_digest(ids)}
    write_json(output / "subject_measurement.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--baseline-r2-receipt", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started, started_at = time.perf_counter(), datetime.now(timezone.utc).isoformat()
    config = json.loads(args.config.read_text())
    bindings = validate_config(config)
    r2 = json.loads(args.baseline_r2_receipt.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    subjects, inputs = {}, bindings + [{"path": str(args.baseline_r2_receipt.resolve()),
                                      "sha256": file_digest(args.baseline_r2_receipt)}]
    for subject in DEVELOPMENT_SUBJECTS:
        X, labels, metadata, subject_inputs = load_restricted_subject(args.epochs / f"sub-{subject}", subject)
        source = chronological_indices(metadata, "source_train", "ses-0")
        arrays, audit = load_verified_source_model(args.baseline_root / f"sub-{subject}", subject,
                                                  X[source], labels[source],
                                                  [metadata[i]["trial_id"] for i in source], r2)
        subjects[subject] = analyze_subject(X, labels, metadata, subject, arrays, audit,
                                            args.output / f"sub-{subject}")
        inputs.extend(subject_inputs + audit["inputs"])
        print(json.dumps({"subject": subject, "status": "completed", "pipeline_fit_attempts": 40}), flush=True)
    source_values = {subject: row["source_twofold_balanced_accuracy"] for subject, row in subjects.items()}
    support_values = {}
    for subject, row in subjects.items():
        values = [r["observed"]["support_split_half_direction_cosine"] for r in row["support_rows"]]
        support_values[subject] = None if None in values else float(np.mean(values))
    controls = [row["source_phase_alignment_control"] for row in subjects.values()]
    failures = sum(row["pipeline_fit_failures"] for row in controls)
    dependencies = [ROOT / "scripts/analyze_kumar_lowdim_reliability.py",
                    ROOT / "scripts/run_kumar_baselines.py",
                    ROOT / "src/learning_preserving_bci/decoders/csp_lda.py"]
    receipt = {"status": "completed_exploratory_measurement" if not failures else "completed_with_explicit_source_fit_failures",
               "synthetic": False, "subjects": subjects,
               "participant_summaries": {"source_twofold_balanced_accuracy": lowdim.participant_bootstrap(source_values),
                                         "mean_five_support_split_half_vector_cosine": lowdim.participant_bootstrap(support_values)},
               "inputs": inputs, "executed_dependency_sources": [{"path": str(p), "sha256": file_digest(p)} for p in dependencies],
               "script_sha256": file_digest(Path(__file__)), "config_sha256": file_digest(args.config),
               "plan_sha256": config["plan_sha256"],
               "source_git_ancestor": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                     text=True, capture_output=True, check=True).stdout.strip(),
               "started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.perf_counter() - started,
               "runtime": {"python": platform.python_version(), "numpy": np.__version__, "mne": mne.__version__,
                           "scikit_learn": sklearn.__version__},
               "pipeline_fit_attempts": sum(row["pipeline_fit_attempts"] for row in controls),
               "pipeline_fit_successes": sum(row["pipeline_fit_successes"] for row in controls),
               "pipeline_fit_failures": failures,
               "nominal_csp_and_lda_estimator_fit_attempts": sum(row["nominal_csp_and_lda_estimator_fit_attempts"] for row in controls),
               "observed_pipeline_fit_attempts_included_in_total": 12,
               "cached_heldout_prediction_rows": sum(row["heldout_prediction_rows"] for row in controls),
               "joint_shift_twofold_rows": 2400, "shared_source_shift_pairs_sha256": controls[0]["shared_shift_pairs_sha256"],
               "source_coordinate_scaler_fit_count": 6, "loaded_existing_full40_source_models": 6,
               "source_rows": 6, "support_rows": 30,
               "query_rows_used": 0, "final_subjects_opened": 0,
               "new_adaptation_fits": 0, "new_primary_baseline_fits": 0, "new_full40_source_decoder_fits": 0,
               "gate_threshold_selected": False, "shift_control_is_formal_p_value": False,
               "claim_scope": "exploratory development-only measurement; no validated adaptation gate or neural retention claim"}
    write_json(args.output / "measurement_receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "pipeline_fit_attempts", "pipeline_fit_failures",
                                                   "cached_heldout_prediction_rows", "wall_seconds")}))


if __name__ == "__main__":
    main()
