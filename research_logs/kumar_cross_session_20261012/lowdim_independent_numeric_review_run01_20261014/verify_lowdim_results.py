"""Independent NumPy replay of restricted development measurement results.

No producer functions, original result containers or query rows are loaded.
This verifies stored measurement arithmetic; it does not fit primary decoders.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SUBJECTS = [1, 4, 7, 10, 13, 16]
CANDIDATES = ["standardized44", "pca4", "motor6"]
MOTOR_COLUMNS = [18, 19, 20, 21, 22, 23]
PRODUCER_SHA = "c3f19cac305cb72fdbfb539172b198bc67836ec6499730fad8829fe16f27a964"
TOLERANCE = 1e-9
ERRORS: dict[str, float] = {}
COUNTS: dict[str, int] = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def array_sha(value):
    a = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(json.dumps(list(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def require(condition, label):
    if not condition:
        raise AssertionError(label)
    COUNTS[label] = COUNTS.get(label, 0) + 1


def close(actual, expected, label):
    if actual is None or expected is None:
        require(actual is None and expected is None, label + "_availability")
        return
    if isinstance(actual, (list, tuple)) and any(v is None for v in actual):
        require(len(actual) == len(expected), label + "_length")
        for a, b in zip(actual, expected, strict=True):
            close(a, b, label)
        return
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    require(a.shape == b.shape, label + "_shape")
    require(np.isfinite(a).all() and np.isfinite(b).all(), label + "_finite")
    error = float(np.max(np.abs(a - b))) if a.size else 0.0
    ERRORS[label] = max(ERRORS.get(label, 0.0), error)
    require(error <= TOLERANCE, label + "_tolerance")


def indices(metadata, role, session=None, run=None):
    selected = [i for i, t in enumerate(metadata) if t["role"] == role
                and (session is None or t["session"] == session)
                and (run is None or t["run"] == run)]
    return np.asarray(sorted(selected, key=lambda i: (
        metadata[i].get("acquisition_time_utc", ""), metadata[i]["start_sample"],
        metadata[i]["source_row"])), dtype=int)


def transformed(raw, state):
    z = (raw - np.asarray(state["scaler_mean"])) / np.asarray(state["scaler_scale"])
    basis = np.asarray(state["pca_components"])
    projected = z @ basis.T - np.asarray(state["pca_mean"]) @ basis.T
    return {"standardized44": z, "pca4": projected, "motor6": z[:, MOTOR_COLUMNS]}


def verify_state(raw, trial_ids, state):
    require(state["fit_trial_ids"] == trial_ids, "coordinate_fit_identities")
    require(state["fit_n"] == len(raw), "coordinate_fit_count")
    require(state["raw_fit_X_sha256"] == array_sha(raw), "coordinate_raw_hash")
    require(state["motor_columns"] == MOTOR_COLUMNS, "anatomical_columns")
    require(state["source_only_fit"] is True, "source_only_state")
    mean = np.mean(raw, axis=0)
    var = np.mean((raw - mean) ** 2, axis=0)
    scale = np.sqrt(var)
    scale[scale == 0] = 1
    close(state["scaler_mean"], mean, "scaler_mean")
    close(state["scaler_var_ddof0"], var, "scaler_var_ddof0")
    close(state["scaler_scale"], scale, "scaler_scale")
    z = (raw - mean) / scale
    zmean = z.mean(axis=0)
    centered = z - zmean
    covariance = centered.T @ centered / (len(raw) - 1)
    eigenvalues = np.linalg.eigvalsh(covariance)[::-1][:4]
    basis = np.asarray(state["pca_components"])
    close(state["pca_mean"], zmean, "pca_center")
    close(basis @ basis.T, np.eye(4), "pca_orthonormality")
    close(state["pca_explained_variance"], eigenvalues, "pca_top_eigenvalues")
    close(covariance @ basis.T, basis.T * eigenvalues, "pca_eigenvector_residual")
    require(state["scaler_sha256"] == array_sha(np.asarray([
        state["scaler_mean"], state["scaler_scale"], state["scaler_var_ddof0"]])),
        "scaler_state_hash")
    require(state["pca_sha256"] == array_sha(np.vstack([
        state["pca_mean"], state["pca_components"]])), "pca_state_hash")
    fitting_state = {k: v for k, v in state.items()
                     if k not in {"subject", "scope", "test_trial_ids", "state_sha256"}}
    require(json_sha(fitting_state) == state["state_sha256"], "coordinate_state_hash")


def difference(x, y):
    if not np.any(y == 0) or not np.any(y == 1):
        return None
    weights = (y == 1) / np.count_nonzero(y == 1) - (y == 0) / np.count_nonzero(y == 0)
    return weights @ x


def direction_cosine(a, b):
    if a is None or b is None:
        return None
    norm = np.sqrt(a @ a) * np.sqrt(b @ b)
    return None if norm == 0 else float(np.clip((a @ b) / norm, -1, 1))


def probe(train, train_y, holdout, holdout_y):
    vector = difference(train, train_y)
    norm = np.sqrt(vector @ vector)
    if norm == 0:
        return {"balanced_accuracy": None, "unit_axis": None, "threshold": None,
                "predictions": None, "direction_valid": False}
    axis = vector / norm
    centroids = np.stack([train[train_y == c].sum(axis=0) / np.count_nonzero(train_y == c)
                          for c in (0, 1)])
    threshold = float((centroids[0] + centroids[1]) @ axis / 2)
    predictions = (holdout @ axis >= threshold).astype(int)
    recalls = [float(np.count_nonzero(predictions[holdout_y == c] == c) /
                     np.count_nonzero(holdout_y == c)) for c in (0, 1)]
    return {"balanced_accuracy": float(sum(recalls) / 2), "unit_axis": axis,
            "threshold": threshold, "predictions": predictions,
            "direction_valid": True, "class_recall": recalls}


def halves(labels):
    groups = [np.flatnonzero(labels == c) for c in (0, 1)]
    return [np.sort(np.concatenate([g[:len(g) // 2] for g in groups])),
            np.sort(np.concatenate([g[len(g) // 2:] for g in groups]))]


def support_metrics(source, source_y, support, labels, half_ids):
    axis = difference(source, source_y)
    valid_axis = bool(np.sqrt(axis @ axis) != 0)
    unit = axis / np.sqrt(axis @ axis) if valid_axis else None
    projected = source @ unit if valid_axis else None
    sd = float(np.sqrt(np.sum((projected - projected.mean()) ** 2) /
                       (len(source) - 1))) if valid_axis else None
    vectors = [difference(support[h], labels[h]) for h in half_ids]
    contrasts = [None if v is None or not valid_axis or sd == 0 else float(v @ unit / sd)
                 for v in vectors]
    return {"valid_halves": all(v is not None for v in vectors),
            "single_class_half_count": sum(v is None for v in vectors),
            "zero_direction_half_count": sum(bool(v is not None and v @ v == 0) for v in vectors),
            "source_direction_valid": valid_axis,
            "source_projection_sd_ddof1": sd,
            "source_support_direction_cosine": direction_cosine(axis, difference(support, labels)),
            "support_split_half_direction_cosine": direction_cosine(*vectors),
            "half_scalar_signed_contrasts_source_sd": contrasts,
            "half_scalar_product": None if None in contrasts else float(np.prod(contrasts)),
            "half_indices": [h.tolist() for h in half_ids]}


def verify_measure(saved, reconstructed):
    exact = {"valid_halves", "single_class_half_count", "zero_direction_half_count",
             "source_direction_valid", "half_indices"}
    for key, expected in reconstructed.items():
        if key in exact:
            require(saved[key] == expected, "support_" + key)
        else:
            close(saved[key], expected, "support_" + key)


def verify_tail(saved, observed, values):
    valid = [v for v in values if v is not None]
    close(saved["observed"], observed, "tail_observed")
    require(saved["total_control_count"] == len(values), "tail_total_denominator")
    require(saved["valid_control_count"] == len(valid), "tail_valid_denominator")
    require(saved["unavailable_control_count"] == len(values) - len(valid), "tail_invalid_denominator")
    expected = None if observed is None or not valid else sum(v >= observed for v in valid) / len(valid)
    close(saved["upper_tail_fraction_descriptive"], expected, "tail_fraction")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    start = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parents[3]
    require(args.inputs.name.startswith("lowdim_development_inputs"), "restricted_input_path")
    receipt = json.loads(args.result.read_text())
    require(receipt["script_sha256"] == PRODUCER_SHA, "executed_producer_hash")
    require(sha(root / "scripts/analyze_kumar_lowdim_reliability.py") == PRODUCER_SHA,
            "current_producer_hash")
    require(receipt["query_rows_used"] == receipt["final_subjects_opened"] ==
            receipt["executed_input_container_query_row_count"] == 0, "executed_access_declaration")
    require(set(receipt["subjects"]) == set(map(str, SUBJECTS)), "six_subject_scope")
    bound = {record["path"]: record["sha256"] for record in receipt["inputs"]}
    for field, relative in [("config_sha256", "configs/kumar_lowdim_reliability_20261014.json"),
                            ("plan_sha256", "docs/kumar_lowdim_reliability_plan_20261014.md")]:
        require(sha(root / relative) == receipt[field], "executed_" + field)
    reconstructed_source = {c: {} for c in CANDIDATES}
    reconstructed_support = {c: {} for c in CANDIDATES}
    input_records = []
    source_prediction_count = source_null_fold_count = support_control_count = 0
    for subject in SUBJECTS:
        folder = args.inputs / f"sub-{subject}"
        mp, fp = folder / "included_trial_metadata.json", folder / "fixed_features.npz"
        for p in (mp, fp):
            digest = sha(p)
            require(bound[str(p.resolve())] == digest, "executed_restricted_input_hash")
            input_records.append({"path": str(p.resolve()), "sha256": digest})
        metadata = json.loads(mp.read_text())
        require(all(t["cohort"] == "development" and t["subject"] == f"sub-{subject}" and
                    t["role"] in {"source_train", "target_support"} for t in metadata),
                "physically_restricted_metadata")
        ids = [t["trial_id"] for t in metadata]
        require(len(set(ids)) == len(ids), "unique_trial_ids")
        labels = np.asarray([int(t["label"] == "right_hand") for t in metadata])
        with np.load(fp, allow_pickle=False) as features:
            require(features.files == ["trial_ids", "labels", "log10_bandpower_44"],
                    "physically_restricted_feature_keys")
            require(features["trial_ids"].tolist() == ids, "feature_trial_ids")
            require(np.array_equal(features["labels"], labels), "feature_labels")
            raw = np.asarray(features["log10_bandpower_44"], dtype=np.float64)
        require(raw.shape == (len(ids), 44) and np.isfinite(raw).all(), "restricted_feature_shape")
        saved = receipt["subjects"][str(subject)]
        require(saved["selected_trial_ids_sha256"] == json_sha(ids), "selected_identity_hash")
        states = saved["coordinate_fit_states"]
        require(len(states) == 3, "three_coordinate_states")
        source_indices = [indices(metadata, "source_train", "ses-0", f"run-{i}") for i in (0, 1)]
        all_source = indices(metadata, "source_train", "ses-0")
        require([len(v) for v in source_indices] == [20, 20] and len(all_source) == 40,
                "source_budgets")
        for ix in source_indices:
            require(np.bincount(labels[ix], minlength=2).tolist() == [10, 10], "source_class_budgets")
        for ix, state in zip([*source_indices, all_source], states, strict=True):
            verify_state(raw[ix], [ids[i] for i in ix], state)
        folds = []
        for train_run, holdout_run in ((0, 1), (1, 0)):
            train, holdout = source_indices[train_run], source_indices[holdout_run]
            require(states[train_run]["test_trial_ids"] == [ids[i] for i in holdout],
                    "source_holdout_identity")
            folds.append((transformed(raw[train], states[train_run]),
                          transformed(raw[holdout], states[train_run]), labels[train], labels[holdout]))
        pairs = [list(p) for p in itertools.product(range(20), repeat=2)]
        phase = saved["source_phase_alignment_control"]
        require(phase["pairs"] == pairs and phase["shift_pair_count"] == 400, "all_source_phase_pairs")
        require(phase["shared_shift_pairs_sha256"] == json_sha(pairs), "shared_phase_pair_hash")
        unique = [len({tuple(np.roll(labels[ix], k)) for k in range(20)}) for ix in source_indices]
        require(phase["unique_rotated_label_assignments_per_run"] == unique and
                phase["unique_paired_label_assignments"] == int(np.prod(unique)),
                "unique_source_phase_assignments")
        source_rows = {row["candidate"]: row for row in saved["source_rows"]}
        for candidate in CANDIDATES:
            reconstructed_ba = []
            for fold_index, (train, holdout, train_y, holdout_y) in enumerate(folds):
                value = probe(train[candidate], train_y, holdout[candidate], holdout_y)
                observed = source_rows[candidate]["folds"][fold_index]
                require(observed["train_trial_ids"] == states[fold_index]["fit_trial_ids"] and
                        observed["holdout_trial_ids"] == states[fold_index]["test_trial_ids"],
                        "observed_fold_identities")
                require(observed["coordinate_state_sha256"] == states[fold_index]["state_sha256"],
                        "observed_fold_state_binding")
                require(np.array_equal(observed["predictions"], value["predictions"]),
                        "observed_source_predictions_exact")
                source_prediction_count += len(holdout_y)
                for field in ("balanced_accuracy", "unit_axis", "threshold", "class_recall"):
                    close(observed[field], value[field], "observed_source_" + field)
                    close(phase["observed"][candidate][fold_index][field], value[field],
                          "phase_identity_observed_" + field)
                reconstructed_ba.append(value["balanced_accuracy"])
            participant_ba = float(np.mean(reconstructed_ba))
            reconstructed_source[candidate][subject] = participant_ba
            close(source_rows[candidate]["twofold_balanced_accuracy"], participant_ba,
                  "source_twofold_mean")
            require(len(phase["null"][candidate]) == 400, "source_null_count")
            for pair, null in zip(pairs, phase["null"][candidate], strict=True):
                require([null["run0_shift"], null["run1_shift"]] == pair, "source_null_shared_pair")
                bas = []
                for fold_index, (train, holdout, _, _) in enumerate(folds):
                    train_y = np.roll(labels[source_indices[fold_index]], pair[fold_index])
                    other = 1 - fold_index
                    holdout_y = np.roll(labels[source_indices[other]], pair[other])
                    bas.append(probe(train[candidate], train_y, holdout[candidate],
                                     holdout_y)["balanced_accuracy"])
                    source_null_fold_count += 1
                close(null["fold_balanced_accuracy"], bas, "source_null_fold_BA")
                close(null["twofold_balanced_accuracy"], float(np.mean(bas)), "source_null_mean_BA")
            verify_tail(source_rows[candidate]["phase_alignment_control"],
                        source_rows[candidate]["twofold_balanced_accuracy"],
                        [row["twofold_balanced_accuracy"] for row in phase["null"][candidate]])
        source_features = transformed(raw[all_source], states[2])
        support_cosines = {c: [] for c in CANDIDATES}
        require(len(saved["support_rows"]) == 15, "support_rows_per_participant")
        for row in saved["support_rows"]:
            candidate = row["candidate"]
            ix = indices(metadata, "target_support", row["session"], "run-0")
            require(len(ix) in (19, 20), "support_budget")
            require(row["support_trial_ids"] == [ids[i] for i in ix] and
                    row["source_trial_ids"] == [ids[i] for i in all_source], "support_identities")
            require(row["source_coordinate_state_sha256"] == states[2]["state_sha256"],
                    "support_source_state_binding")
            y = labels[ix]
            support = transformed(raw[ix], states[2])[candidate]
            require(row["support_labels"] == y.tolist(), "support_saved_labels")
            require(row["support_n"] == len(ix) and row["support_class_counts"] ==
                    np.bincount(y, minlength=2).tolist(), "support_saved_counts")
            require(row["support_qc_flagged_count"] == sum(bool(metadata[i].get(
                    "qc_peak_to_peak_over_250uv", False)) for i in ix), "support_QC_retention")
            require(row["selected_source_raw_feature_sha256"] == array_sha(raw[all_source]) and
                    row["selected_support_raw_feature_sha256"] == array_sha(raw[ix]),
                    "support_raw_hashes")
            original_halves = halves(y)
            observed = support_metrics(source_features[candidate], labels[all_source],
                                       support, y, original_halves)
            verify_measure(row["observed"], observed)
            support_cosines[candidate].append(observed["support_split_half_direction_cosine"])
            require(row["shift_count"] == len(y) and len(row["null"]) == len(y), "support_phase_count")
            require(row["unique_rotated_label_assignments"] == len({
                    tuple(np.roll(y, shift)) for shift in range(len(y))}), "unique_support_assignments")
            require(row["identity_included"] is True, "support_identity_included")
            for shift, control in enumerate(row["null"]):
                require(control["shift"] == shift, "support_shift_order")
                shifted = np.roll(y, shift)
                for name, split in [("recomputed_classwise_halves", halves(shifted)),
                                    ("fixed_original_half_indices", original_halves)]:
                    reconstructed = support_metrics(source_features[candidate], labels[all_source],
                                                    support, shifted, split)
                    verify_measure(control[name], reconstructed)
                    support_control_count += 1
            for name in ("recomputed_classwise_halves", "fixed_original_half_indices"):
                comparison = row["comparisons"][name]
                values = [control[name] for control in row["null"]]
                for metric in ("source_support_direction_cosine", "support_split_half_direction_cosine",
                               "half_scalar_product"):
                    verify_tail(comparison[metric], row["observed"][metric], [v[metric] for v in values])
                require(comparison["single_class_control_count"] == sum(
                    v["single_class_half_count"] > 0 for v in values), "single_class_denominator")
                require(comparison["zero_half_direction_control_count"] == sum(
                    v["zero_direction_half_count"] > 0 for v in values), "zero_direction_denominator")
                require(comparison["invalid_source_direction_control_count"] == sum(
                    not v["source_direction_valid"] for v in values), "invalid_source_denominator")
        for candidate, values in support_cosines.items():
            require(len(values) == 5, "five_sessions_per_participant_candidate")
            reconstructed_support[candidate][subject] = None if None in values else float(np.mean(values))
        require(saved["diagnostic_centroid_probe_fit_attempts"] == 2400 and
                phase["diagnostic_centroid_probe_fit_attempts"] == 2400,
                "participant_source_probe_attempt_count")
        require(saved["support_fixed_source_axis_fit_attempts"] == 3, "participant_fixed_axis_count")
    for candidate in CANDIDATES:
        for key, mapping in [("source_twofold_balanced_accuracy", reconstructed_source[candidate]),
                             ("mean_five_support_split_half_vector_cosine", reconstructed_support[candidate])]:
            summary = receipt["participant_summaries"][candidate][key]
            expected = [mapping[s] for s in SUBJECTS]
            require([r["subject"] for r in summary["participant_values"]] == SUBJECTS,
                    "bootstrap_participant_order")
            close([r["value"] for r in summary["participant_values"]], expected, "bootstrap_participant_values")
            if None in expected:
                require(summary["bootstrap_draws"] == [] and summary["mean"] is None,
                        "missing_participant_summary_retained")
                continue
            values = np.asarray(expected)
            random = np.random.default_rng(42)
            draws = values[random.integers(0, 6, size=(10000, 6))].mean(axis=1)
            close(summary["bootstrap_draws"], draws, "all_participant_bootstrap_draws")
            close(summary["mean"], values.mean(), "participant_summary_mean")
            close(summary["interval95"], np.quantile(draws, [.025, .975]), "participant_summary_interval")
            require(summary["independent_unit"] == "participant" and summary["replicates"] == 10000
                    and summary["seed"] == 42, "bootstrap_unit_and_seed")
    require(source_prediction_count == 720, "observed_prediction_count")
    require(source_null_fold_count == receipt["diagnostic_centroid_probe_fit_attempts"] == 14400,
            "all_source_null_attempt_count")
    require(receipt["support_fixed_source_axis_fit_attempts"] == 18 and
            receipt["source_coordinate_scaler_fit_count"] == receipt["source_coordinate_pca_fit_count"] == 18,
            "all_source_coordinate_counts")
    require(receipt["source_rows"] == 18 and receipt["support_rows"] == 90, "all_result_row_counts")
    require(receipt["new_adaptation_fits"] == receipt["new_primary_baseline_fits"] == 0 and
            not receipt["automatic_candidate_selected"] and not receipt["gate_threshold_selected"] and
            not receipt["shift_control_is_formal_p_value"], "frozen_scope_declarations")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"status": "passed_independent_numerical_review", "started_at_utc": started_at,
              "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "wall_seconds": time.perf_counter() - start,
              "executed_verifier_sha256": sha(__file__), "reviewed_result_sha256": sha(args.result),
              "producer_sha256": PRODUCER_SHA, "source_git_ancestor": receipt["source_git_ancestor"],
              "input_files": input_records, "absolute_numeric_tolerance": TOLERANCE,
              "maximum_absolute_errors_by_endpoint": ERRORS,
              "checks_passed_by_type": COUNTS, "coordinate_states_verified": 18,
              "observed_source_folds_verified": 36, "observed_source_predictions_verified_exactly": 720,
              "source_phase_twofold_values_verified": 7200,
              "source_phase_centroid_reconstructions": 14400,
              "support_rows_verified": 90, "support_phase_measurements_verified": support_control_count,
              "participant_bootstrap_arrays_verified": 6, "independent_participants": 6,
              "producer_functions_imported": False, "original_full_containers_opened": False,
              "query_data_opened": False, "final_participant_data_opened": False,
              "new_primary_decoder_fits": 0, "new_adaptation_fits": 0,
              "feature_construction_from_original_EEG_reverified": False,
              "claim_scope": "Independent arithmetic/provenance replay of exploratory measurements; no efficacy claim",
              "runtime": {"python": platform.python_version(), "numpy": np.__version__}}
    with (args.output / "receipt.json").open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: report[k] for k in ("status", "wall_seconds", "coordinate_states_verified",
                                           "source_phase_centroid_reconstructions", "support_rows_verified",
                                           "support_phase_measurements_verified")}))


if __name__ == "__main__":
    main()
