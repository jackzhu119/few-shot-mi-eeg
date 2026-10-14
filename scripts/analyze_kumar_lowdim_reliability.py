"""Fixed development-only measurement diagnostics; no query/adaptation scoring."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from learning_preserving_bci.datasets.kumar import CHANNEL_NAMES

DEVELOPMENT_SUBJECTS = [1, 4, 7, 10, 13, 16]
CANDIDATES = ["standardized44", "pca4", "motor6"]
ALLOWED_ROLES = {"source_train", "target_support"}
ALL_ROLES = ALLOWED_ROLES | {"source_validation", "source_query", "target_query"}
MOTOR_COLUMNS = [2 * CHANNEL_NAMES.index(c) + band
                 for c in ("C3", "Cz", "C4") for band in (0, 1)]


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def array_digest(value):
    a = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(json.dumps(list(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def validate_config(config):
    expected = {"development_subjects": DEVELOPMENT_SUBJECTS,
                "candidates": CANDIDATES, "seed": 42, "bootstrap_replicates": 10000}
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"Frozen config mismatch: {key}")
    if set(config.get("allowed_roles", ALLOWED_ROLES)) != ALLOWED_ROLES:
        raise ValueError("Forbidden allowed_roles")
    for key in ("query_access", "final_cohort_access", "automatic_candidate_selection",
                "adaptation_gate_threshold_search"):
        if config.get(key, False) is not False:
            raise ValueError(f"Forbidden config access/selection: {key}")


def validate_selected_metadata(metadata, subject):
    """Reject query/final rows rather than letting caller quietly fit them."""
    if subject not in DEVELOPMENT_SUBJECTS:
        raise ValueError("Forbidden final subject")
    ids = [t["trial_id"] for t in metadata]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate trial identity")
    for t in metadata:
        if t["role"] not in ALLOWED_ROLES:
            raise ValueError("Forbidden selected role")
        if t["cohort"] != "development" or t["subject"] != f"sub-{subject}":
            raise ValueError("Forbidden cohort or subject identity")
        if t["label"] not in ("left_hand", "right_hand"):
            raise ValueError("Unknown label")
        expected_id = f"{t['subject']}/{t['session']}/{t['run']}/row-{t['source_row']}"
        if t["trial_id"] != expected_id:
            raise ValueError("Trial identity fields mismatch")
        if t["role"] == "source_train":
            valid = t["session"] == "ses-0" and t["run"] in ("run-0", "run-1")
        else:
            valid = t["session"] in [f"ses-{i}" for i in range(1, 6)] and t["run"] == "run-0"
        if not valid:
            raise ValueError("Forbidden source/support session or run")
    source = [t for t in metadata if t["role"] == "source_train"]
    if len(source) != 40:
        raise ValueError("Source budget mismatch")
    for run in ("run-0", "run-1"):
        group = [t for t in source if t["run"] == run]
        if len(group) != 20 or any(sum(t["label"] == label for t in group) != 10
                                  for label in ("left_hand", "right_hand")):
            raise ValueError("Source run/class budget mismatch")
    for session in [f"ses-{i}" for i in range(1, 6)]:
        group = [t for t in metadata if t["role"] == "target_support" and t["session"] == session]
        counts = [sum(t["label"] == label for t in group)
                  for label in ("left_hand", "right_hand")]
        if len(group) not in (19, 20) or sorted(counts) not in ([9, 10], [10, 10]):
            raise ValueError("Current support/class budget mismatch")


def chronological_indices(metadata, role, session=None, run=None):
    indices = [i for i, t in enumerate(metadata) if t["role"] == role
               and (session is None or t["session"] == session)
               and (run is None or t["run"] == run)]
    return np.asarray(sorted(indices, key=lambda i: (
        metadata[i].get("acquisition_time_utc", ""), metadata[i]["start_sample"],
        metadata[i]["source_row"])), dtype=int)


def load_allowed_subject(folder, subject):
    metadata_path = folder / "included_trial_metadata.json"
    feature_path = folder / "fixed_features.npz"
    all_metadata = json.loads(metadata_path.read_text())
    all_ids = [t["trial_id"] for t in all_metadata]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("Duplicate container trial identity")
    if any(t["role"] not in ALL_ROLES for t in all_metadata):
        raise ValueError("Unknown container role")
    if any(t["cohort"] != "development" or t["subject"] != f"sub-{subject}"
           for t in all_metadata):
        raise ValueError("Forbidden container cohort or subject identity")
    selected = [i for i, t in enumerate(all_metadata) if t["role"] in ALLOWED_ROLES]
    metadata = [all_metadata[i] for i in selected]
    validate_selected_metadata(metadata, subject)
    labels = np.asarray([int(t["label"] == "right_hand") for t in metadata], dtype=int)
    with np.load(feature_path, allow_pickle=False) as f:
        if list(f["trial_ids"]) != all_ids:
            raise ValueError("Feature/metadata identity mismatch")
        # Existing containers include queries; only these explicitly permitted rows
        # enter calculations. No saved source scaler/PCA or query scores are read.
        x = np.asarray(f["log10_bandpower_44"][selected], dtype=np.float64)
        if not np.array_equal(f["labels"][selected], labels):
            raise ValueError("Feature/metadata selected label mismatch")
    if x.shape != (len(metadata), 44) or not np.isfinite(x).all():
        raise ValueError("Invalid selected raw log-power features")
    inputs = [{"path": str(p.resolve()), "sha256": file_digest(p)}
              for p in (metadata_path, feature_path)]
    inputs[0]["container_query_row_count"] = sum(t["role"] in ("source_query", "target_query")
                                                for t in all_metadata)
    inputs[0]["selected_row_count"] = len(selected)
    return x, labels, metadata, inputs


def fit_coordinates(x, fit_ids):
    """The caller passes TRAIN only; all three candidates share these fits."""
    if x.ndim != 2 or x.shape[1] != 44 or len(x) != len(fit_ids) or len(x) < 4:
        raise ValueError("Invalid source coordinate fit budget")
    if not np.isfinite(x).all() or len(set(fit_ids)) != len(fit_ids):
        raise ValueError("Invalid source coordinate fit data/identities")
    scaler = StandardScaler().fit(x)
    standardized = scaler.transform(x)
    pca = PCA(n_components=4, svd_solver="full", whiten=False).fit(standardized)
    state = {"fit_trial_ids": list(fit_ids), "fit_n": len(x),
             "raw_fit_X_sha256": array_digest(x),
             "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
             "scaler_var_ddof0": scaler.var_.tolist(), "pca_mean": pca.mean_.tolist(),
             "pca_components": pca.components_.tolist(),
             "pca_explained_variance": pca.explained_variance_.tolist(),
             "scaler_sha256": array_digest(np.stack([scaler.mean_, scaler.scale_, scaler.var_])),
             "pca_sha256": array_digest(np.vstack([pca.mean_, pca.components_])),
             "motor_columns": MOTOR_COLUMNS, "source_only_fit": True}
    state["state_sha256"] = json_digest(state)
    return scaler, pca, state


def transform_coordinates(x, scaler, pca):
    z = scaler.transform(x)
    return {"standardized44": z, "pca4": pca.transform(z), "motor6": z[:, MOTOR_COLUMNS]}


def task_direction(x, labels):
    if any(np.count_nonzero(labels == value) == 0 for value in (0, 1)):
        return None
    return x[labels == 1].mean(axis=0) - x[labels == 0].mean(axis=0)


def cosine(a, b):
    if a is None or b is None:
        return None
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0 or not np.isfinite(norm):
        return None
    return float(np.clip(np.dot(a, b) / norm, -1, 1))


def centroid_probe(train, train_labels, holdout, holdout_labels):
    """A diagnostic centroid classifier; never an adaptation fit."""
    axis = task_direction(train, train_labels)
    if axis is None or np.linalg.norm(axis) == 0:
        return {"balanced_accuracy": None, "direction_valid": False,
                "unit_axis": None, "threshold": None, "predictions": None}
    unit = axis / np.linalg.norm(axis)
    midpoint = (train[train_labels == 0].mean(axis=0)
                + train[train_labels == 1].mean(axis=0)) / 2
    threshold = float(midpoint @ unit)
    predictions = (holdout @ unit >= threshold).astype(int)
    recalls = [float(np.mean(predictions[holdout_labels == label] == label))
               if np.any(holdout_labels == label) else None for label in (0, 1)]
    ba = float(np.mean(recalls)) if None not in recalls else None
    return {"balanced_accuracy": ba, "direction_valid": True, "unit_axis": unit.tolist(),
            "threshold": threshold, "predictions": predictions.tolist(), "class_recall": recalls}


def source_phase_alignment_control(folds, labels_by_run, candidates=CANDIDATES):
    """All 400 pairs are shared across directions and coordinates, including identity."""
    pairs = list(itertools.product(range(len(labels_by_run[0])), range(len(labels_by_run[1]))))
    observed, null = {c: [] for c in candidates}, {c: [] for c in candidates}
    fits = 0
    for shift0, shift1 in pairs:
        shifted = [np.roll(labels_by_run[0], shift0), np.roll(labels_by_run[1], shift1)]
        for candidate in candidates:
            bas = []
            for fold_index, fold in enumerate(folds):
                train_run, holdout_run = fold["train_run_index"], fold["holdout_run_index"]
                value = centroid_probe(fold["train"][candidate], shifted[train_run],
                                       fold["holdout"][candidate], shifted[holdout_run])
                fits += 1
                bas.append(value["balanced_accuracy"])
                if shift0 == 0 and shift1 == 0:
                    observed[candidate].append({"fold": fold_index, **value})
            average = None if None in bas else float(np.mean(bas))
            null[candidate].append({"run0_shift": shift0, "run1_shift": shift1,
                                    "fold_balanced_accuracy": bas,
                                    "twofold_balanced_accuracy": average})
    unique = [len({tuple(np.roll(y, k)) for k in range(len(y))}) for y in labels_by_run]
    return {"pairs": [list(pair) for pair in pairs], "shift_pair_count": len(pairs),
            "unique_rotated_label_assignments_per_run": unique,
            "unique_paired_label_assignments": int(np.prod(unique)),
            "shared_shift_pairs_sha256": json_digest(pairs), "observed": observed,
            "null": null, "diagnostic_centroid_probe_fit_attempts": fits}


def classwise_halves(labels):
    groups = [np.flatnonzero(labels == value) for value in (0, 1)]
    if min(map(len, groups)) < 4:
        return None
    return [np.sort(np.concatenate([g[:len(g) // 2] for g in groups])),
            np.sort(np.concatenate([g[len(g) // 2:] for g in groups]))]


def source_axis_reference(source, labels):
    axis = task_direction(source, labels)
    valid = bool(axis is not None and np.linalg.norm(axis) != 0)
    unit = axis / np.linalg.norm(axis) if valid else None
    return {"axis": axis, "unit": unit, "valid": valid,
            "projection_sd_ddof1": float(np.std(source @ unit, ddof=1)) if valid else None}


def support_measure(source, source_labels, support, labels, halves=None, source_reference=None):
    reference = (source_axis_reference(source, source_labels) if source_reference is None
                 else source_reference)
    source_axis = reference["axis"]
    halves = classwise_halves(labels) if halves is None else halves
    if halves is None:
        return {"valid_halves": False, "invalid_reason": "insufficient_class_counts",
                "source_support_direction_cosine": None,
                "support_split_half_direction_cosine": None,
                "half_scalar_signed_contrasts_source_sd": [None, None], "half_scalar_product": None}
    vectors = [task_direction(support[h], labels[h]) for h in halves]
    single_class = sum(v is None for v in vectors)
    source_nonzero = reference["valid"]
    source_sd = reference["projection_sd_ddof1"]
    scalars = [None, None]
    if source_nonzero and source_sd > 0:
        scalars = [None if v is None else float(v @ reference["unit"] / source_sd) for v in vectors]
    zero_vectors = sum(bool(v is not None and np.linalg.norm(v) == 0) for v in vectors)
    return {"valid_halves": single_class == 0, "single_class_half_count": single_class,
            "zero_direction_half_count": zero_vectors,
            "source_direction_valid": source_nonzero,
            "source_projection_sd_ddof1": source_sd,
            "source_support_direction_cosine": cosine(source_axis, task_direction(support, labels)),
            "support_split_half_direction_cosine": cosine(*vectors),
            "half_scalar_signed_contrasts_source_sd": scalars,
            "half_scalar_product": None if None in scalars else float(np.prod(scalars)),
            "half_indices": [h.tolist() for h in halves]}


def null_comparison(observed, values):
    valid = [v for v in values if v is not None]
    return {"observed": observed, "total_control_count": len(values),
            "valid_control_count": len(valid), "unavailable_control_count": len(values) - len(valid),
            "upper_tail_fraction_descriptive": None if observed is None or not valid else
            float(np.mean(np.asarray(valid) >= observed)),
            "interpretation": "conditional cyclic phase-alignment sensitivity, not a formal p-value"}


def support_phase_alignment_control(source, source_labels, support, labels, source_reference=None):
    reference = (source_axis_reference(source, source_labels) if source_reference is None
                 else source_reference)
    original_halves = classwise_halves(labels)
    if original_halves is None:
        raise ValueError("Insufficient original support halves")
    null = []
    for shift in range(len(labels)):
        shifted = np.roll(labels, shift)
        null.append({"shift": shift,
                     "recomputed_classwise_halves": support_measure(
                         source, source_labels, support, shifted, source_reference=reference),
                     "fixed_original_half_indices": support_measure(
                         source, source_labels, support, shifted, original_halves, reference)})
    observed = null[0]["recomputed_classwise_halves"]
    comparisons = {}
    for half_method in ("recomputed_classwise_halves", "fixed_original_half_indices"):
        comparisons[half_method] = {}
        for metric in ("source_support_direction_cosine", "support_split_half_direction_cosine",
                       "half_scalar_product"):
            comparisons[half_method][metric] = null_comparison(
                observed[metric], [r[half_method][metric] for r in null])
        comparisons[half_method]["single_class_control_count"] = sum(
            r[half_method].get("single_class_half_count", 0) > 0 for r in null)
        comparisons[half_method]["zero_half_direction_control_count"] = sum(
            r[half_method].get("zero_direction_half_count", 0) > 0 for r in null)
        comparisons[half_method]["invalid_source_direction_control_count"] = sum(
            not r[half_method].get("source_direction_valid", False) for r in null)
    return {"observed": observed, "null": null, "comparisons": comparisons,
            "shift_count": len(labels),
            "unique_rotated_label_assignments": len({tuple(np.roll(labels, k))
                                                     for k in range(len(labels))}),
            "identity_included": True}


def participant_bootstrap(values_by_subject, seed=42, replicates=10000):
    ordered = [{"subject": subject, "value": values_by_subject.get(subject)}
               for subject in DEVELOPMENT_SUBJECTS]
    if any(row["value"] is None for row in ordered):
        return {"participant_values": ordered, "mean": None, "interval95": [None, None],
                "bootstrap_draws": [], "status": "unavailable_missing_participant_value",
                "missing_participant_count": sum(row["value"] is None for row in ordered)}
    values = np.asarray([row["value"] for row in ordered], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite participant value")
    rng = np.random.default_rng(seed)
    draws = values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
    return {"participant_values": ordered, "mean": float(values.mean()),
            "interval95": np.quantile(draws, [.025, .975]).tolist(),
            "bootstrap_draws": draws.tolist(), "replicates": replicates, "seed": seed,
            "independent_unit": "participant", "status": "completed"}


def analyze_subject(x, labels, metadata, subject):
    ids = [t["trial_id"] for t in metadata]
    run_indices = [chronological_indices(metadata, "source_train", "ses-0", f"run-{run}")
                   for run in (0, 1)]
    labels_by_run = [labels[index] for index in run_indices]
    folds, fit_states = [], []
    for train_run, holdout_run in ((0, 1), (1, 0)):
        train, holdout = run_indices[train_run], run_indices[holdout_run]
        scaler, pca, state = fit_coordinates(x[train], [ids[i] for i in train])
        fit_states.append({"subject": subject, "scope": f"run{train_run}_to_run{holdout_run}",
                           "test_trial_ids": [ids[i] for i in holdout], **state})
        folds.append({"train_run_index": train_run, "holdout_run_index": holdout_run,
                      "train": transform_coordinates(x[train], scaler, pca),
                      "holdout": transform_coordinates(x[holdout], scaler, pca)})
    controls = source_phase_alignment_control(folds, labels_by_run)
    source_rows = []
    for candidate in CANDIDATES:
        fold_rows = []
        for fold_index, observed in enumerate(controls["observed"][candidate]):
            state = fit_states[fold_index]
            fold_rows.append({"subject": subject, "candidate": candidate,
                              "train_trial_ids": state["fit_trial_ids"],
                              "holdout_trial_ids": state["test_trial_ids"],
                              "coordinate_state_sha256": state["state_sha256"], **observed})
        bas = [row["balanced_accuracy"] for row in fold_rows]
        observed = None if None in bas else float(np.mean(bas))
        source_rows.append({"subject": subject, "candidate": candidate, "folds": fold_rows,
                            "twofold_balanced_accuracy": observed,
                            "phase_alignment_control": null_comparison(observed, [
                                row["twofold_balanced_accuracy"] for row in controls["null"][candidate]])})
    source = chronological_indices(metadata, "source_train", "ses-0")
    scaler, pca, state = fit_coordinates(x[source], [ids[i] for i in source])
    fit_states.append({"subject": subject, "scope": "all40_source_for_current_support", **state})
    source_features = transform_coordinates(x[source], scaler, pca)
    source_references = {candidate: source_axis_reference(source_features[candidate], labels[source])
                         for candidate in CANDIDATES}
    support_rows = []
    for session in [f"ses-{i}" for i in range(1, 6)]:
        support = chronological_indices(metadata, "target_support", session, "run-0")
        features = transform_coordinates(x[support], scaler, pca)
        for candidate in CANDIDATES:
            control = support_phase_alignment_control(
                source_features[candidate], labels[source], features[candidate], labels[support],
                source_references[candidate])
            row = {"subject": subject, "candidate": candidate, "session": session,
                   "source_trial_ids": [ids[i] for i in source],
                   "support_trial_ids": [ids[i] for i in support],
                   "support_labels": labels[support].tolist(),
                   "source_coordinate_state_sha256": state["state_sha256"],
                   "support_n": len(support),
                   "support_class_counts": [int(np.sum(labels[support] == value)) for value in (0, 1)],
                   "support_qc_flagged_count": sum(bool(metadata[i].get(
                       "qc_peak_to_peak_over_250uv", False)) for i in support), **control}
            row["selected_source_raw_feature_sha256"] = array_digest(x[source])
            row["selected_support_raw_feature_sha256"] = array_digest(x[support])
            support_rows.append(row)
    return {"source_rows": source_rows, "source_phase_alignment_control": controls,
            "support_rows": support_rows, "coordinate_fit_states": fit_states,
            "diagnostic_centroid_probe_fit_attempts": controls["diagnostic_centroid_probe_fit_attempts"],
            "support_fixed_source_axis_fit_attempts": len(CANDIDATES),
            "selected_trial_ids_sha256": json_digest(ids)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    config = json.loads(args.config.read_text())
    validate_config(config)
    args.output.mkdir(parents=True, exist_ok=False)
    subjects, inputs = {}, []
    for subject in config["development_subjects"]:
        x, labels, metadata, bound_inputs = load_allowed_subject(args.results / f"sub-{subject}", subject)
        subjects[subject] = analyze_subject(x, labels, metadata, subject)
        inputs.extend(bound_inputs)
    summaries = {}
    for candidate in CANDIDATES:
        source_values, support_values = {}, {}
        for subject, value in subjects.items():
            source_values[subject] = next(row["twofold_balanced_accuracy"]
                                          for row in value["source_rows"] if row["candidate"] == candidate)
            support = [row["observed"]["support_split_half_direction_cosine"]
                       for row in value["support_rows"] if row["candidate"] == candidate]
            support_values[subject] = None if None in support else float(np.mean(support))
        summaries[candidate] = {
            "source_twofold_balanced_accuracy": participant_bootstrap(
                source_values, config["seed"], config["bootstrap_replicates"]),
            "mean_five_support_split_half_vector_cosine": participant_bootstrap(
                support_values, config["seed"], config["bootstrap_replicates"])}
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                         cwd=Path(__file__).resolve().parents[1], check=True).stdout.strip()
    plan_path = Path(__file__).resolve().parents[1] / "docs/kumar_lowdim_reliability_plan_20261014.md"
    result = {"status": "completed_exploratory_measurement", "subjects": subjects,
              "participant_summaries": summaries, "inputs": inputs,
              "source_git_ancestor": git, "script_sha256": file_digest(Path(__file__)),
              "config_sha256": file_digest(args.config), "plan_sha256": file_digest(plan_path),
              "started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "wall_seconds": time.perf_counter() - started,
              "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                          "scikit_learn": sklearn.__version__},
              "diagnostic_centroid_probe_fit_attempts": sum(
                  v["diagnostic_centroid_probe_fit_attempts"] for v in subjects.values()),
              "support_fixed_source_axis_fit_attempts": sum(
                  v["support_fixed_source_axis_fit_attempts"] for v in subjects.values()),
              "source_rows": len(DEVELOPMENT_SUBJECTS) * len(CANDIDATES),
              "support_rows": len(DEVELOPMENT_SUBJECTS) * 5 * len(CANDIDATES),
              "query_rows_used": 0, "final_subjects_opened": 0,
              "executed_input_container_query_row_count": sum(
                  i.get("container_query_row_count", 0) for i in inputs),
              "source_coordinate_scaler_fit_count": len(DEVELOPMENT_SUBJECTS) * 3,
              "source_coordinate_pca_fit_count": len(DEVELOPMENT_SUBJECTS) * 3,
              "new_adaptation_fits": 0, "new_primary_baseline_fits": 0,
              "automatic_candidate_selected": False, "gate_threshold_selected": False,
              "shift_control_is_formal_p_value": False,
              "claim_scope": config.get("claim_scope", "exploratory development-only measurement")}
    (args.output / "measurement_receipt.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "source_rows", "support_rows",
                                           "query_rows_used", "final_subjects_opened",
                                           "diagnostic_centroid_probe_fit_attempts", "wall_seconds")}))


if __name__ == "__main__":
    main()
