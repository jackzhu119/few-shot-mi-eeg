"""Decompose saved Kumar update gains without fitting or model inference.

This post-observation analysis keeps all three CPU contrasts and all three
cohorts. Class rates are averaged within session, sessions within participant,
and participants within cohort. It never treats pooled trials as independent
observations. The independent arithmetic check uses original CPU CSV records,
integer confusion counts and fractions, separately from the NumPy pathway.

Run with Python, NumPy, Matplotlib and Pillow. Figures require an actual Arial
or Times New Roman installation, or --font-dir pointing to licensed TTF files.
Use --no-figures for an arithmetic-only replay. Outputs must be fresh folders.
"""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib.metadata
import io
import itertools
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np


PUBLIC = Path("research_logs/kumar_submission_qc_20261015/run01/public_inputs")
CPU = Path("research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z")
FOLLOWUP = Path("research_logs/kumar_component_followup_20261016")
STATS = Path("research_logs/kumar_review_revision_20261016/run01/statistics")
FROZEN = "source_only"
LDA = "frozen_csp_lda_recalibration"
FULL = "refit_csp_lda"
NEURAL = "always_frozen_eegnet"
CPU_METHODS = (FROZEN, LDA, FULL)
CONTRASTS = (
    ("lda_minus_frozen", FROZEN, LDA),
    ("full_minus_lda", LDA, FULL),
    ("full_minus_frozen", FROZEN, FULL),
)
CONTRAST_LABELS = ("LDA − frozen", "Full − LDA", "Full − frozen")
DEVELOPMENT = tuple(f"sub-{i}" for i in (1, 4, 7, 10, 13, 16))
SUBJECTS = tuple(f"sub-{i}" for i in range(1, 19))
PRIMARY = tuple(s for s in SUBJECTS if s not in DEVELOPMENT)
COHORTS = {"primary": PRIMARY, "development": DEVELOPMENT, "all18": SUBJECTS}
SESSIONS = tuple(f"ses-{i}" for i in range(1, 6))
PIPELINES = ((FROZEN, "cpu_fixed"), (LDA, "cpu_fixed"), (FULL, "cpu_fixed")) + tuple(
    (NEURAL, str(seed)) for seed in (20261012, 20261013, 20261014)
)
COMPONENTS = (
    "corrected_pp", "introduced_pp", "net_pp", "unchanged_correct_pp",
    "unchanged_error_pp", "base_score_pct", "updated_score_pct",
)
MEASURES = ("left_recall", "right_recall", "balanced_accuracy")
SEED = 42
BOOTSTRAPS = 10000
TOLERANCE = 1e-10  # Percentage points; only arithmetic comparisons, not testing.
SOURCE_TEXTS = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_bytes(path):
    key = str(Path(path))
    return SOURCE_TEXTS[key].encode("utf-8") if key in SOURCE_TEXTS else Path(path).read_bytes()


def digest(path):
    return hashlib.sha256(source_bytes(path)).hexdigest()


def read_csv(path):
    with io.StringIO(source_bytes(path).decode("utf-8"), newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    return json.loads(source_bytes(path).decode("utf-8"))


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path, rows):
    require(bool(rows), f"Refusing empty table: {path}")
    with Path(path).open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def cohort(subject):
    return "development" if subject in DEVELOPMENT else "final_test"


def close(left, right, message):
    require(math.isclose(float(left), float(right), rel_tol=0, abs_tol=TOLERANCE), message)


def bootstrap(values):
    values = np.asarray(values, dtype=np.float64)
    require(len(values) >= 2 and np.isfinite(values).all(), "Invalid participant values")
    # A fresh identical generator for each paired vector preserves covariance
    # across metrics in a cohort. Subject order is always lexicographic.
    indices = np.random.default_rng(SEED).integers(0, len(values), (BOOTSTRAPS, len(values)))
    bounds = np.percentile(values[indices].mean(axis=1), [2.5, 97.5])
    return float(values.mean()), float(bounds[0]), float(bounds[1])


def signs(values):
    return {
        "positive": sum(float(x) > TOLERANCE for x in values),
        "zero": sum(abs(float(x)) <= TOLERANCE for x in values),
        "negative": sum(float(x) < -TOLERANCE for x in values),
    }


def load_and_audit(repo):
    """Check textual provenance, exact identity joins and historical fit scopes."""
    inputs = {}

    def track(path):
        full_path = repo / path
        inputs[str(path)] = {"sha256": digest(full_path), "bytes": len(source_bytes(full_path))}
        return full_path

    provenance = read_json(track(PUBLIC / "public_input_provenance.json"))
    for name, identity in provenance["files"].items():
        path = track(PUBLIC / name)
        require(digest(path) == identity["sha256"] and len(source_bytes(path)) == identity["bytes"],
                f"Portable input identity mismatch: {name}")
    config = read_json(repo / PUBLIC / "frozen_analysis_configuration.json")
    require(config["subjects"] == list(SUBJECTS), "Participant set changed")
    require(config["development_subjects"] == list(DEVELOPMENT), "Development split changed")
    require(config["final_test_subjects"] == list(PRIMARY), "Primary split changed")
    require(config["synthetic"] is False, "Synthetic source inputs prohibited")
    metadata = read_json(repo / PUBLIC / "frozen_trial_metadata.json")["trials"]
    by_id = {r["trial_id"]: r for r in metadata}
    require(len(by_id) == len(metadata) == 7200, "Trial identity duplication or incompleteness")
    require(Counter(r["subject"] for r in metadata) == Counter({s: 400 for s in SUBJECTS}),
            "Original participant coverage changed")
    role_expected = {
        "source_train": 720, "source_validation": 360, "source_query": 360,
        "target_support": 1786, "target_query": 3930,
    }
    require(Counter(r["role"] for r in metadata if r["included"]) == Counter(role_expected),
            "Included-role denominators changed")
    role_count = Counter()
    identity_by_group = defaultdict(set)
    count_by_role_class = Counter()
    unflagged_classes = defaultdict(Counter)
    for row in metadata:
        subject, session, run, role = (row[k] for k in ("subject", "session", "run", "role"))
        require(row["cohort"] == cohort(subject), "Metadata cohort disagrees with allocation")
        if session == "ses-0":
            expected_role = {"run-0": "source_train", "run-1": "source_train",
                             "run-2": "source_validation", "run-3": "source_query"}[run]
        else:
            require(session in SESSIONS, "Unexpected target session")
            expected_role = "target_support" if run == "run-0" else "target_query"
        require(role == expected_role, "Whole-run partition mismatch")
        if row["included"]:
            identity_by_group[(subject, session, role)].add(row["trial_id"])
        else:
            require(row["source_row"] == 20 and session in SESSIONS
                    and row["exclusion_reason"] == "partial_source_event_under_5s",
                    "Unexpected excluded trial")
        role_count[(role, bool(row["included"]), bool(row["qc_peak_to_peak_over_250uv"]))] += 1
        count_by_role_class[(subject, session, role, row["label"], bool(row["included"]),
                             bool(row["qc_peak_to_peak_over_250uv"]))] += 1
        if row["included"] and role == "target_query" and not row["qc_peak_to_peak_over_250uv"]:
            unflagged_classes[(subject, session)][row["label"]] += 1
    included_query = {r["trial_id"] for r in metadata if r["included"]
                      and r["role"] in ("source_query", "target_query")}
    require(len(included_query) == 4290, "Query denominator changed")
    saved = read_csv(repo / PUBLIC / "saved_predictions.csv")
    require(len(saved) == 25740, "Saved prediction count changed")
    predictions = {}
    coverage = defaultdict(set)
    for row in saved:
        trial = row["trial_id"]
        require(trial in included_query, "Excluded/nonquery identity in saved predictions")
        expected = by_id[trial]
        pipeline = row["method"], row["seed"]
        require(pipeline in PIPELINES, "Unexpected method or seed")
        for field in ("subject", "cohort", "session", "run", "role"):
            require(row[field] == expected[field], f"Identity field mismatch: {field}")
        require(int(row["label"]) == (expected["label"] == "right_hand"), "True-label mismatch")
        require(row["qc_peak_to_peak_over_250uv"] == str(expected["qc_peak_to_peak_over_250uv"]),
                "QC join mismatch")
        key = trial, *pipeline
        require(key not in predictions, "Duplicated prediction")
        require(row["prediction"] in ("0", "1"), "Prediction not binary")
        predictions[key] = int(row["prediction"])
        coverage[pipeline].add(trial)
    require(set(coverage) == set(PIPELINES), "Missing pipeline")
    require(all(ids == included_query for ids in coverage.values()), "Query sets differ")
    original_cpu = read_csv(track(CPU / "query_predictions.csv"))
    require(len(original_cpu) == 12870, "Original CPU prediction count changed")
    original_keys = set()
    for row in original_cpu:
        key = row["trial_id"], row["method"], "cpu_fixed"
        require(key not in original_keys, "Duplicate original CPU prediction")
        original_keys.add(key)
        require(row["synthetic"] == "False", "Synthetic original CPU prediction")
        for field in ("subject", "cohort", "session", "run"):
            require(row[field] == by_id[row["trial_id"]][field], "Original identity mismatch")
        require(int(row["prediction"]) == predictions[key], "Portable CPU prediction changed")
        require(int(row["label"]) == (by_id[row["trial_id"]]["label"] == "right_hand"),
                "Original label mismatch")
    require(original_keys == {key for key in predictions if key[2] == "cpu_fixed"},
            "Portable/original CPU query coverage differs")

    fit_rows = []
    query_state_records = 0
    for subject in SUBJECTS:
        source_ids = identity_by_group[(subject, "ses-0", "source_train")]
        validation = identity_by_group[(subject, "ses-0", "source_validation")]
        all_query = {t for t in included_query if by_id[t]["subject"] == subject}
        require(len(source_ids) == 40 and len(validation) == 20, "Source label budget changed")
        fits = read_json(track(CPU / subject / "fit_access_audit.json"))
        models = read_json(track(CPU / subject / "model_audit.json"))
        require(len(fits) == 11 and len(models) == 18, "Historical CPU audit count changed")
        fit_index = {(r["method"], r["session"]): r for r in fits}
        require(len(fit_index) == 11, "Duplicated fit audit")
        for row in fits:
            session, method = row["session"], row["method"]
            expected_ids = source_ids if method == FROZEN else source_ids | identity_by_group[
                (subject, session, "target_support")]
            ids = set(row["trial_ids"])
            require(len(ids) == len(row["trial_ids"]) == row["n_fit"], "Duplicated fit identity")
            require(ids == expected_ids and not ids & (validation | all_query),
                    "Fit IDs violate source/current-support partition")
            require(row["query_and_validation_disjoint"] is True, "Historical disjoint flag failed")
            require(row["lda_fit"] is True and row["csp_fit"] == (method != LDA),
                    "Unexpected fitted component")
        for session in SESSIONS:
            support = identity_by_group[(subject, session, "target_support")]
            require(len(support) in (19, 20), "Support budget outside 19/20")
            left, right = fit_index[(LDA, session)], fit_index[(FULL, session)]
            require(left["trial_ids"] == right["trial_ids"]
                    and left["fit_X_y_sha256"] == right["fit_X_y_sha256"],
                    "Matched-label fitting union or array hash differs")
            fit_rows.append({
                "subject": subject, "cohort": cohort(subject), "session": session,
                "source_train_n": len(source_ids), "current_support_n": len(support),
                "support_left_n": sum(by_id[t]["label"] == "left_hand" for t in support),
                "support_right_n": sum(by_id[t]["label"] == "right_hand" for t in support),
                "combined_fit_n": left["n_fit"], "same_ordered_fit_ids": True,
                "same_fit_X_y_sha256": left["fit_X_y_sha256"],
                "query_validation_overlap_n": 0, "past_target_labels_n": 0,
                "query_n": len(identity_by_group[(subject, session, "target_query")]),
            })
        for row in models:
            session, method = row["session"], row["method"]
            role = "source_query" if session == "ses-0" else "target_query"
            require(set(row["query_trial_ids"]) == identity_by_group[(subject, session, role)],
                    "Historical model query IDs mismatch")
            expected_fit = source_ids if session == "ses-0" or method == FROZEN else (
                source_ids | identity_by_group[(subject, session, "target_support")])
            require(set(row["fit_trial_ids"]) == expected_fit, "Model/fit scope mismatch")
            require(row["parameter_sha256_before"] == row["parameter_sha256_after"]
                    and row["query_state_unchanged"] is True, "Historical model state changed")
            query_state_records += 1

    denominator_rows = [dict(zip(
        ("subject", "session", "role", "class", "included", "amplitude_flag"), key
    ), trials=count) for key, count in sorted(count_by_role_class.items())]
    class_coverage = []
    for subject in SUBJECTS:
        for session in SESSIONS:
            all_trials = identity_by_group[(subject, session, "target_query")]
            for subset in ("all_included", "unflagged"):
                counts = Counter(by_id[t]["label"] for t in all_trials if subset == "all_included"
                                 or not by_id[t]["qc_peak_to_peak_over_250uv"])
                valid = all(counts[k] > 0 for k in ("left_hand", "right_hand"))
                if subset == "all_included":
                    require(valid, "Missing original target class")
                class_coverage.append({
                    "subject": subject, "cohort": cohort(subject), "session": session,
                    "subset": subset, "left_n": counts["left_hand"],
                    "right_n": counts["right_hand"], "BA_defined": valid,
                })
    missing = [s for s in PRIMARY if any(
        not all(unflagged_classes[(s, session)][k] > 0 for k in ("left_hand", "right_hand"))
        for session in SESSIONS)]
    require(set(missing) == {"sub-8", "sub-12"}, "QC missing-endpoint set changed")
    require(sum(row["current_support_n"] == 19 for row in fit_rows) == 14,
            "Support completeness count changed")

    phase_path = FOLLOWUP / "event_mapping/timing_partial_run05/phase_timing_summary.json"
    phase = read_json(track(phase_path))
    phase_rows = read_csv(track(FOLLOWUP / "event_mapping/timing_partial_run05/"
                               "all_7200_trial_mapping_including_missing.csv"))
    require(len(phase_rows) == 7200 and {r["trial_id"] for r in phase_rows} == set(by_id),
            "Phase inventory does not cover original identities")
    mapped_runs = set()
    mapped_trials = 0
    for row in phase_rows:
        identity = by_id[row["trial_id"]]
        require(row["class"] == identity["label"] and row["frozen_role"] == identity["role"],
                "Phase metadata identity mismatch")
        if row["original_phase_metadata_available"] == "True":
            mapped_runs.add((row["subject"], row["session"], row["run"]))
            mapped_trials += 1
    require(mapped_trials == phase["phase_mapped"] == 6220 and len(mapped_runs) == 311,
            "Phase coverage differs from report")
    require(phase["decoder_executed"] is False, "Phase decoding status changed; review required")
    preflight = read_json(track(FOLLOWUP / "budget_cpu_execution/metadata_preflight.json"))
    require(preflight["scientific_inputs_loaded"] is False
            and preflight["new_scientific_evaluation"] is False, "Budget status changed")
    synthetic_path = FOLLOWUP / "budget_cpu_implementation/synthetic_selector_integration/"
    synthetic_path = synthetic_path / "run01/synthetic_integration_receipt.json"
    synthetic_receipt = read_json(track(synthetic_path))
    # Retain the entire bounded status receipt as evidence; never use its scores.
    followup_status = {
        "label_budget_EA_and_selector": "software_and_synthetic_validation_only_in_checkout",
        "metadata_preflight_scientific_inputs_loaded": preflight["scientific_inputs_loaded"],
        "phase_decoder_executed": phase["decoder_executed"],
        "phase_metadata_mapped_runs": len(mapped_runs), "phase_metadata_total_runs": 360,
        "phase_metadata_mapped_trials": mapped_trials, "phase_metadata_unknown_trials": 980,
        "five_second_original_complete_mapped": phase["complete_original_windows"],
        "mapped_complete_windows_overlapping_post_task": phase[
            "original_complete_windows_overlap_post_task"],
        "fixed_task_start_two_second_eligible_mapped": phase[
            "fixed_task2s_eligible_among_original_complete"],
        "real_new_budget_or_phase_predictions_found_in_reviewed_directories": False,
        "synthetic_integration_receipt": synthetic_receipt,
        "evidence_scope": "Repository text artifacts; no remote private workspace was inspected.",
    }
    for path in (STATS / "output/statistics_results.csv", STATS / "public_inputs/participant_inputs.csv"):
        track(path)
    audit = {
        "all_assertions_passed": True, "metadata_trials": len(metadata),
        "complete_trials": sum(r["included"] for r in metadata), "excluded_trials": 44,
        "unique_query_trials": len(included_query), "saved_prediction_rows": len(saved),
        "original_CPU_prediction_rows_reconciled": len(original_cpu),
        "identical_query_sets_across_three_CPU_methods_and_three_EEGNet_seeds": True,
        "all_participants": 18, "development_participants": 6, "primary_participants": 12,
        "primary_target_sessions": 60, "all_target_sessions": 90,
        "same_label_current_support_pairs_verified": len(fit_rows),
        "historical_fit_records_verified": 18 * 11,
        "historical_query_state_records_verified": query_state_records,
        "fit_and_model_audits_are_historical_text_records_not_new_model_replays": True,
        "role_included_counts": role_expected,
        "included_amplitude_flagged_queries": sum(
            by_id[t]["qc_peak_to_peak_over_250uv"] for t in included_query),
        "unflagged_primary_missing_five_session_endpoints": missing,
        "EEG_signals_or_weights_loaded": False, "new_estimator_fits": 0,
        "new_model_forward_passes": 0, "new_update_policy_decisions": 0,
    }
    return (by_id, predictions, original_cpu, fit_rows, denominator_rows, class_coverage,
            followup_status, audit, inputs)


def reconstruct_endpoints(by_id, predictions, original):
    sessions = []
    for subject in SUBJECTS:
        for session in ("ses-0",) + SESSIONS:
            ids = sorted(t for t in by_id if by_id[t]["subject"] == subject
                         and by_id[t]["session"] == session and by_id[t]["included"]
                         and by_id[t]["role"] in ("source_query", "target_query"))
            labels = np.asarray([int(by_id[t]["label"] == "right_hand") for t in ids])
            for method, seed in PIPELINES:
                pred = np.asarray([predictions[(t, method, seed)] for t in ids])
                n = [int(sum(labels == c)) for c in (0, 1)]
                correct = [int(sum((labels == c) & (pred == c))) for c in (0, 1)]
                recalls = [correct[c] / n[c] for c in (0, 1)]
                sessions.append({
                    "subject": subject, "cohort": cohort(subject), "session": session,
                    "method": method, "seed": seed, "left_n": n[0], "right_n": n[1],
                    "left_correct": correct[0], "right_correct": correct[1],
                    "left_recall": recalls[0], "right_recall": recalls[1],
                    "BA": float(np.mean(recalls)), "query_n": len(ids),
                    "prediction_single_class": len(set(pred)) == 1,
                })
    rebuilt = []
    old = {(r["subject"], r["method"]): r for r in original}
    max_difference = 0.0
    for subject in SUBJECTS:
        for method in CPU_METHODS + (NEURAL,):
            selected = [r for r in sessions if r["subject"] == subject and r["method"] == method]
            by_session = {session: float(np.mean([r["BA"] for r in selected
                                                  if r["session"] == session]))
                          for session in ("ses-0",) + SESSIONS}
            target = float(np.mean([by_session[s] for s in SESSIONS]))
            source = by_session["ses-0"]
            saved = old[(subject, method)]
            for value, field in ((source, "source_query_BA"), (target, "target_five_session_mean_BA")):
                difference = abs(value - float(saved[field]))
                require(difference < 5e-15, "Original participant endpoint failed reconstruction")
                max_difference = max(max_difference, difference)
            rebuilt.append({"subject": subject, "cohort": cohort(subject), "method": method,
                            "source_query_BA": source, "target_five_session_mean_BA": target})
    return sessions, rebuilt, max_difference


def transition_tables(by_id, predictions):
    trial_rows, session_rows = [], []
    for subject in SUBJECTS:
        for session in SESSIONS:
            ids = sorted(t for t, r in by_id.items() if r["subject"] == subject
                         and r["session"] == session and r["role"] == "target_query"
                         and r["included"])
            labels = np.asarray([int(by_id[t]["label"] == "right_hand") for t in ids])
            pred = {m: np.asarray([predictions[(t, m, "cpu_fixed")] for t in ids])
                    for m in CPU_METHODS}
            for index, trial in enumerate(ids):
                trial_rows.append({
                    "subject": subject, "cohort": cohort(subject), "session": session,
                    "trial_id": trial, "true_label": int(labels[index]),
                    "frozen_prediction": int(pred[FROZEN][index]),
                    "LDA_prediction": int(pred[LDA][index]), "full_prediction": int(pred[FULL][index]),
                    "frozen_correct": bool(pred[FROZEN][index] == labels[index]),
                    "LDA_correct": bool(pred[LDA][index] == labels[index]),
                    "full_correct": bool(pred[FULL][index] == labels[index]),
                    "class_query_n": int(sum(labels == labels[index])),
                    "participant_BA_weight_pp": 100 / (5 * 2 * sum(labels == labels[index])),
                })
            for name, base, updated in CONTRASTS:
                class_rows = []
                for c, measure in enumerate(MEASURES[:2]):
                    select = labels == c
                    baseline_correct = pred[base][select] == labels[select]
                    update_correct = pred[updated][select] == labels[select]
                    n = int(sum(select))
                    corrected = int(sum(~baseline_correct & update_correct))
                    introduced = int(sum(baseline_correct & ~update_correct))
                    stable_correct = int(sum(baseline_correct & update_correct))
                    stable_error = int(sum(~baseline_correct & ~update_correct))
                    require(corrected + introduced + stable_correct + stable_error == n,
                            "Transition states do not partition query class")
                    row = {
                        "subject": subject, "cohort": cohort(subject), "session": session,
                        "contrast": name, "measure": measure, "query_n": n,
                        "corrected_count": corrected, "introduced_count": introduced,
                        "unchanged_correct_count": stable_correct, "unchanged_error_count": stable_error,
                        "corrected_pp": 100 * corrected / n, "introduced_pp": 100 * introduced / n,
                        "net_pp": 100 * (corrected - introduced) / n,
                        "unchanged_correct_pp": 100 * stable_correct / n,
                        "unchanged_error_pp": 100 * stable_error / n,
                        "base_score_pct": 100 * float(baseline_correct.mean()),
                        "updated_score_pct": 100 * float(update_correct.mean()),
                    }
                    close(row["net_pp"], row["updated_score_pct"] - row["base_score_pct"],
                          "Recall delta differs from transition decomposition")
                    class_rows.append(row)
                    session_rows.append(row)
                balanced = {"subject": subject, "cohort": cohort(subject), "session": session,
                            "contrast": name, "measure": "balanced_accuracy"}
                for key in ("query_n", "corrected_count", "introduced_count",
                            "unchanged_correct_count", "unchanged_error_count"):
                    balanced[key] = sum(row[key] for row in class_rows)
                for key in COMPONENTS:
                    balanced[key] = float(np.mean([row[key] for row in class_rows]))
                session_rows.append(balanced)
    participants = []
    for subject in SUBJECTS:
        for name, _, _ in CONTRASTS:
            for measure in MEASURES:
                select = [r for r in session_rows if r["subject"] == subject
                          and r["contrast"] == name and r["measure"] == measure]
                require(len(select) == 5, "Participant transition endpoint lacks a session")
                row = {"subject": subject, "cohort": cohort(subject), "contrast": name,
                       "measure": measure, "session_n": len(select),
                       "query_n": sum(r["query_n"] for r in select)}
                for key in COMPONENTS:
                    row[key] = float(np.mean([r[key] for r in select]))
                close(row["corrected_pp"] - row["introduced_pp"], row["net_pp"],
                      "Participant additive decomposition failed")
                participants.append(row)
    return trial_rows, session_rows, participants


def summarize_transitions(participants, sessions, rebuilt):
    summary, influence, profiles = [], [], []
    for label, members in COHORTS.items():
        for name, _, _ in CONTRASTS:
            for measure in MEASURES:
                selected = sorted((r for r in participants if r["subject"] in members
                                   and r["contrast"] == name and r["measure"] == measure),
                                  key=lambda r: r["subject"])
                require(len(selected) == len(members), "Missing cohort transition endpoint")
                for component in COMPONENTS:
                    vector = [r[component] for r in selected]
                    mean, low, high = bootstrap(vector)
                    summary.append({
                        "cohort": label, "n_participants": len(members), "n_sessions": len(members) * 5,
                        "contrast": name, "measure": measure, "component": component,
                        "mean_pp_or_pct": mean, "ci95_low": low, "ci95_high": high,
                        "bootstrap_n": BOOTSTRAPS, "bootstrap_seed": SEED,
                        "bootstrap_unit": "participant", "participant_order": "lexicographic",
                        "analysis_status": "post_observation_exploratory_decomposition",
                    })
                for leave in selected:
                    remaining = [r["net_pp"] for r in selected if r is not leave]
                    influence.append({
                        "cohort": label, "contrast": name, "measure": measure,
                        "excluded_subject": leave["subject"], "remaining_n": len(remaining),
                        "mean_net_pp": float(np.mean(remaining)),
                        "analysis_status": "descriptive_influence_not_independent_validation",
                    })
            for session in SESSIONS:
                selected = sorted((r for r in sessions if r["subject"] in members
                                   and r["contrast"] == name and r["measure"] == "balanced_accuracy"
                                   and r["session"] == session), key=lambda r: r["subject"])
                vector = [r["net_pp"] for r in selected]
                mean, low, high = bootstrap(vector)
                profiles.append({
                    "cohort": label, "contrast": name, "session": session,
                    "n_participants": len(members), "mean_net_pp": mean,
                    "ci95_low": low, "ci95_high": high, **signs(vector),
                    "bootstrap_unit": "participant", "bootstrap_n": BOOTSTRAPS,
                    "bootstrap_seed": SEED, "inference": "descriptive_no_session_hypothesis_test",
                })
    gain_pairs = []
    endpoint_index = {(r["subject"], r["method"]): r["target_five_session_mean_BA"] for r in rebuilt}
    for subject in SUBJECTS:
        frozen, lda, full = (100 * endpoint_index[(subject, method)] for method in CPU_METHODS)
        gain_pairs.append({
            "subject": subject, "cohort": cohort(subject), "frozen_BA_pct": frozen,
            "LDA_BA_pct": lda, "full_BA_pct": full, "lda_minus_frozen_pp": lda - frozen,
            "full_minus_lda_pp": full - lda, "full_minus_frozen_pp": full - frozen,
        })
    return summary, influence, profiles, gain_pairs


def independently_verify(original_cpu, participants, rebuilt, repo):
    """Separate exact rational calculation directly from original CPU predictions."""
    table = defaultdict(dict)
    confusion = defaultdict(Counter)
    for row in original_cpu:
        identity = row["subject"], row["session"], row["trial_id"], int(row["label"])
        table[identity][row["method"]] = int(row["prediction"])
        confusion[(row["subject"], row["session"], row["method"], int(row["label"]))][
            int(row["prediction"]) == int(row["label"])] += 1
    exact_sessions = defaultdict(dict)
    for subject in SUBJECTS:
        for method in CPU_METHODS:
            for session in ("ses-0",) + SESSIONS:
                recalls = []
                for c in (0, 1):
                    counts = confusion[(subject, session, method, c)]
                    recalls.append(Fraction(counts[True], sum(counts.values())))
                exact_sessions[(subject, method)][session] = sum(recalls) / 2
    original_index = {(r["subject"], r["method"]): r for r in rebuilt}
    max_endpoint_error = 0.0
    for (subject, method), values in exact_sessions.items():
        exact_target = sum(values[s] for s in SESSIONS) / 5
        original = original_index[(subject, method)]
        error = abs(float(exact_target) - original["target_five_session_mean_BA"])
        require(error < 5e-15, "Independent rational endpoint disagrees")
        max_endpoint_error = max(max_endpoint_error, error)
    exact_counts = defaultdict(Counter)
    for (subject, session, _, c), actions in table.items():
        if session not in SESSIONS:
            continue
        require(set(actions) == set(CPU_METHODS), "Independent verifier lacks a CPU action")
        for name, base, updated in CONTRASTS:
            before, after = actions[base] == c, actions[updated] == c
            exact_counts[(subject, session, name, c)][(before, after)] += 1
    max_transition_error = 0.0
    for row in participants:
        classes = (0, 1) if row["measure"] == "balanced_accuracy" else (
            (0,) if row["measure"] == "left_recall" else (1,))
        for component, state in (("corrected_pp", (False, True)),
                                 ("introduced_pp", (True, False))):
            values = []
            for session in SESSIONS:
                class_fractions = []
                for c in classes:
                    counts = exact_counts[(row["subject"], session, row["contrast"], c)]
                    class_fractions.append(Fraction(counts[state], sum(counts.values())))
                values.append(sum(class_fractions) / len(classes))
            exact_pp = 100 * sum(values) / 5
            error = abs(float(exact_pp) - row[component])
            require(error < TOLERANCE, "Independent transition rate disagrees")
            max_transition_error = max(max_transition_error, error)
    # Re-enumerate the original four-check family, including its QC contrast.
    # This reproduces existing tests; it does not add or change the test family.
    paired = read_csv(repo / STATS / "public_inputs/participant_inputs.csv")
    previous = read_csv(repo / STATS / "output/statistics_results.csv")
    checked_tests = []
    for old in previous:
        rows = [r for r in paired if r["contrast_id"] == old["contrast_id"]]
        vector = [float(r["paired_difference_BA_original_decimal"]) for r in rows]
        observed = abs(math.fsum(vector) / len(vector))
        numerator = sum(abs(math.fsum(x * s for x, s in zip(vector, pattern, strict=True))
                            / len(vector)) >= observed - 1e-12
                        for pattern in itertools.product((-1, 1), repeat=len(vector)))
        p = numerator / (2 ** len(vector))
        close(p, old["signflip_p_two_sided"], "Existing sign-flip probability changed")
        checked_tests.append({"contrast_id": old["contrast_id"], "n": len(vector),
                              "tail_numerator": numerator, "denominator": 2 ** len(vector),
                              "unadjusted_p": p})
    order = sorted(range(4), key=lambda i: checked_tests[i]["unadjusted_p"])
    current = 0.0
    for rank, index in enumerate(order):
        current = min(1.0, max(current, (4 - rank) * checked_tests[index]["unadjusted_p"]))
        checked_tests[index]["Holm_p_family4"] = current
        close(current, previous[index]["signflip_holm_adjusted_p_family4"],
              "Existing Holm adjustment changed")
    return {
        "performed": True, "method": "original CPU CSV + integer counts + exact Fraction arithmetic",
        "CPU_participant_endpoints_checked": 54, "transition_rate_checks": len(participants) * 2,
        "max_endpoint_absolute_error_BA": max_endpoint_error,
        "max_transition_absolute_error_pp": max_transition_error,
        "existing_four_signflip_checks_reenumerated": checked_tests,
        "new_hypothesis_tests": 0, "human_review_claimed": False,
    }


def figure_lookup(summary, group, contrast, measure, component="net_pp"):
    return next(r for r in summary if r["cohort"] == group and r["contrast"] == contrast
                and r["measure"] == measure and r["component"] == component)


def render_figures(folder, font_dir, summary, profiles, gain_pairs, influence):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from PIL import Image

    if font_dir:
        for path in sorted(Path(font_dir).glob("*.TTF")):
            fm.fontManager.addfont(str(path))
    chosen = None
    for name in ("Arial", "Times New Roman"):
        try:
            path = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
        except ValueError:
            continue
        if fm.FontProperties(fname=path).get_name() == name:
            chosen = name, path
            break
    require(chosen is not None, "Actual Arial/Times New Roman required; supply --font-dir")
    plt.rcParams.update({
        "font.family": chosen[0], "font.size": 9, "axes.titlesize": 10,
        "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8.5,
        "legend.fontsize": 8, "axes.linewidth": 0.7, "pdf.fonttype": 42,
        "ps.fonttype": 42, "figure.facecolor": "white", "axes.facecolor": "white",
        "text.color": "#222222", "axes.labelcolor": "#222222",
        "xtick.color": "#333333", "ytick.color": "#333333", "axes.spines.top": False,
        "axes.spines.right": False,
    })
    blue, orange, charcoal = "#176B9A", "#C77724", "#222222"
    fig_records = []

    def export(fig, basename):
        fig.canvas.draw()
        all_text = [item for item in fig.findobj(matplotlib.text.Text)
                    if item.get_visible() and item.get_text()]
        sizes = sorted({item.get_fontsize() for item in all_text})
        require(all(8 <= size <= 12 for size in sizes), "Figure text outside 8–12 pt")
        require(all(item.get_fontfamily() == [chosen[0]] for item in all_text),
                "Figure text does not use the actual selected font")
        png = folder / f"{basename}.png"
        pdf = folder / f"{basename}.pdf"
        tif = folder / f"{basename}.tif"
        fig.savefig(png, dpi=600, facecolor="white")
        fig.savefig(pdf, facecolor="white", metadata={"Creator": Path(__file__).name,
                                                      "CreationDate": None, "ModDate": None})
        with Image.open(png) as source:
            source.convert("RGB").save(tif, dpi=(600, 600), compression="tiff_lzw")
        with Image.open(tif) as check:
            require(check.mode == "RGB" and tuple(check.info["dpi"]) == (600.0, 600.0),
                    "TIFF color mode or resolution mismatch")
            size = list(check.size)
        fig_records.append({"figure": basename, "font_family": chosen[0],
                            "font_file_sha256": digest(chosen[1]), "dpi": 600,
                            "actual_text_sizes_pt": sizes, "nonempty_visible_text_count": len(all_text),
                            "all_visible_text_fonts_and_sizes_checked": True,
                            "pixel_dimensions": size, "TIFF_mode": "RGB",
                            "TIFF_compression": "LZW", "files": {
                                p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                                for p in (png, pdf, tif)}})
        plt.close(fig)

    fig, axes = plt.subplots(3, 2, figsize=(7.5, 7.0))
    fig.subplots_adjust(left=0.155, right=0.985, bottom=0.10, top=0.90,
                        hspace=0.65, wspace=0.22)
    group_labels = {"primary": "Primary cohort (n = 12)",
                    "development": "Development cohort (n = 6)",
                    "all18": "All participants (n = 18; secondary)"}
    for row_index, group in enumerate(COHORTS):
        left, right = axes[row_index]
        for axis in (left, right):
            axis.axvline(0, color="#777777", linewidth=0.8, zorder=0)
            axis.grid(axis="x", color="#E5E5E5", linewidth=0.45, zorder=0)
            axis.set_axisbelow(True)
            axis.set_yticks([2, 1, 0])
            axis.set_ylim(-0.6, 2.6)
        left.set_yticklabels(CONTRAST_LABELS)
        right.set_yticklabels([])
        left.set_xlim(-21, 31)
        left.set_xticks([-20, -10, 0, 10, 20, 30])
        right.set_xlim(-18, 22)
        right.set_xticks([-10, 0, 10, 20])
        left.set_title(f"{chr(65 + row_index * 2)}  {group_labels[group]}", loc="left", pad=10)
        right.set_title(f"{chr(66 + row_index * 2)}  Left and right recall", loc="left", pad=10)
        for contrast_index, (name, _, _) in enumerate(CONTRASTS):
            y = 2 - contrast_index
            corrected = figure_lookup(summary, group, name, "balanced_accuracy", "corrected_pp")
            introduced = figure_lookup(summary, group, name, "balanced_accuracy", "introduced_pp")
            net = figure_lookup(summary, group, name, "balanced_accuracy")
            left.barh(y, corrected["mean_pp_or_pct"], height=0.42, color=blue, alpha=0.78)
            left.barh(y, -introduced["mean_pp_or_pct"], height=0.42, color=orange,
                      edgecolor=orange, hatch="///", alpha=0.66)
            mean = net["mean_pp_or_pct"]
            left.errorbar(mean, y, xerr=[[mean - net["ci95_low"]], [net["ci95_high"] - mean]],
                          fmt="D", color=charcoal, markersize=3.8, capsize=2.6, linewidth=1.1)
            left.text(30, y, f"{mean:+.2f}", fontsize=8, ha="right", va="center")
            for measure, offset, color, marker in (("left_recall", 0.14, blue, "o"),
                                                   ("right_recall", -0.14, orange, "s")):
                result = figure_lookup(summary, group, name, measure)
                mean = result["mean_pp_or_pct"]
                right.errorbar(mean, y + offset,
                               xerr=[[mean - result["ci95_low"]], [result["ci95_high"] - mean]],
                               fmt=marker, color=color, markersize=4, capsize=2.5, linewidth=1)
        if row_index == 2:
            left.set_xlabel("BA contribution (percentage points)")
            right.set_xlabel("Recall change (percentage points)")
    fig.legend(handles=[Patch(facecolor=blue, alpha=0.78, label="Corrected old errors"),
                        Patch(facecolor=orange, alpha=0.66, hatch="///", label="New errors (negative)"),
                        Line2D([], [], color=charcoal, marker="D", linestyle="none",
                               markersize=4, label="Net gain and 95% interval"),
                        Line2D([], [], color=blue, marker="o", linestyle="none", label="Left"),
                        Line2D([], [], color=orange, marker="s", linestyle="none", label="Right")],
               loc="upper center", bbox_to_anchor=(0.52, 0.985), ncol=3, frameon=False,
               columnspacing=1.4, handlelength=1.4)
    export(fig, "Fig5_prediction_transitions")

    fig = plt.figure(figsize=(7.5, 6.4))
    grid = fig.add_gridspec(2, 2, height_ratios=(1.25, 0.75))
    left, right, bottom = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, :])
    fig.subplots_adjust(left=0.095, right=0.985, bottom=0.105, top=0.93, wspace=0.35, hspace=0.64)
    for axis in (left, right, bottom):
        axis.axhline(0, color="#777777", linewidth=0.8, zorder=0)
        axis.grid(color="#E5E5E5", linewidth=0.45)
        axis.set_axisbelow(True)
    left.axvline(0, color="#777777", linewidth=0.8, zorder=0)
    left.plot([-12, 16], [12, -16], color="#888888", linestyle="--", linewidth=0.8,
              label="Full − frozen = 0")
    for rows, color, marker, label in (
        ([r for r in gain_pairs if r["cohort"] == "final_test"], blue, "o", "Primary (n = 12)"),
        ([r for r in gain_pairs if r["cohort"] == "development"], orange, "s", "Development (n = 6)"),
    ):
        left.scatter([r["lda_minus_frozen_pp"] for r in rows], [r["full_minus_lda_pp"] for r in rows],
                     s=24, marker=marker, edgecolor=color,
                     facecolor=color if marker == "o" else "white", linewidth=1.1, label=label)
        for row in rows:
            offsets = {"sub-1": (-10, 8), "sub-6": (-9, -11), "sub-15": (-12, 8),
                       "sub-17": (5, 8), "sub-14": (7, 8), "sub-16": (-10, -12),
                       "sub-13": (5, -11)}
            offset = offsets.get(row["subject"], (4, 4))
            left.annotate(row["subject"].replace("sub-", ""),
                          (row["lda_minus_frozen_pp"], row["full_minus_lda_pp"]),
                          xytext=offset, textcoords="offset points", fontsize=8, color=charcoal,
                          ha="right" if offset[0] < 0 else "left")
    xvalues = [r["lda_minus_frozen_pp"] for r in gain_pairs]
    yvalues = [r["full_minus_lda_pp"] for r in gain_pairs]
    left.set_xlim(min(-8, min(xvalues) - 3), max(13, max(xvalues) + 3))
    left.set_ylim(min(-13, min(yvalues) - 3), max(18, max(yvalues) + 4))
    left.set_title("A  Participant update gains", loc="left", pad=10)
    left.set_xlabel("LDA − frozen BA\n(percentage points)")
    left.set_ylabel("Full − LDA BA (percentage points)")
    left.legend(loc="lower left", frameon=False, fontsize=8, handlelength=1.2)
    for name, color, marker, offset, label in (
        ("full_minus_frozen", blue, "o", -0.075, "Full − frozen"),
        ("full_minus_lda", orange, "s", 0.075, "Full − LDA"),
    ):
        rows = [next(r for r in profiles if r["cohort"] == "primary"
                     and r["contrast"] == name and r["session"] == session)
                for session in SESSIONS]
        means = np.asarray([r["mean_net_pp"] for r in rows])
        errors = np.asarray([[m - r["ci95_low"] for m, r in zip(means, rows, strict=True)],
                             [r["ci95_high"] - m for m, r in zip(means, rows, strict=True)]])
        right.errorbar(np.arange(1, 6) + offset, means, yerr=errors, color=color, marker=marker,
                       markersize=4, capsize=3, linewidth=1, label=label)
    right.set_title("B  Primary cohort (n = 12)", loc="left", pad=10)
    right.set_xticks(range(1, 6))
    right.set_xlim(0.6, 5.4)
    right.set_xlabel("Target session")
    right.set_ylabel("BA change (percentage points)")
    right.legend(loc="upper center", frameon=False, ncol=1)
    for name, color, marker, offset, label in (
        ("full_minus_frozen", blue, "o", -0.10, "Full − frozen"),
        ("full_minus_lda", orange, "s", 0.10, "Full − LDA"),
    ):
        rows = [next(r for r in influence if r["cohort"] == "primary"
                     and r["contrast"] == name and r["measure"] == "balanced_accuracy"
                     and r["excluded_subject"] == subject) for subject in PRIMARY]
        bottom.scatter(np.arange(len(PRIMARY)) + offset, [r["mean_net_pp"] for r in rows],
                       s=24, color=color, marker=marker, label=label)
        original_mean = figure_lookup(summary, "primary", name, "balanced_accuracy")["mean_pp_or_pct"]
        bottom.axhline(original_mean, color=color, linestyle="--", linewidth=0.8)
    bottom.set_title("C  Primary-cohort influence after omitting one participant", loc="left", pad=9)
    bottom.set_xticks(range(len(PRIMARY)), [s.replace("sub-", "") for s in PRIMARY])
    bottom.set_xlabel("Excluded participant (published ID)")
    bottom.set_ylabel("Mean BA change\n(percentage points)")
    bottom.set_ylim(0, 10.6)
    bottom.legend(loc="upper right", frameon=False, ncol=2)
    bottom.text(0.02, 0.06, "Dashed lines: original 12-participant means", transform=bottom.transAxes,
                fontsize=8, va="bottom", ha="left")
    export(fig, "Fig6_component_consistency")
    return {"font_family": chosen[0], "font_path_used": chosen[1], "renderer_script_sha256": digest(__file__),
            "font_file_sha256": digest(chosen[1]), "figures": fig_records,
            "programmatic_export_checks_passed": True,
            "visual_review_status": "requires_separate_visual_inspection"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inputs", type=Path, help="Portable S1 Data inputs folder; no repository needed")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    parser.add_argument("--font-dir", type=Path)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    portable_bundle = None
    if args.inputs:
        portable_bundle = read_json(args.inputs / "update_mechanism_source_texts.json")
        require(portable_bundle["schema_version"] == 1, "Unsupported portable audit bundle")
        repo = Path("/__kumar_portable__")
        for name, record in portable_bundle["sources"].items():
            require(not Path(name).is_absolute() and ".." not in Path(name).parts,
                    "Invalid portable source name")
            text = record["text"]
            require(hashlib.sha256(text.encode("utf-8")).hexdigest() == record["sha256"],
                    "Portable source-text hash mismatch")
            SOURCE_TEXTS[str(repo / name)] = text
        for name in ("public_input_provenance.json", "frozen_analysis_configuration.json",
                     "frozen_trial_metadata.json", "saved_predictions.csv", "original_participant_endpoints.csv"):
            SOURCE_TEXTS[str(repo / PUBLIC / name)] = source_bytes(args.inputs / name).decode("utf-8")
    make_figures = args.figures is not None and not args.no_figures
    require(not output.exists(), "Output directory must be fresh")
    if make_figures:
        names = [f"{figure}.{suffix}" for figure in ("Fig5_prediction_transitions", "Fig6_component_consistency")
                 for suffix in ("png", "tif", "pdf")]
        names += ["Fig5_Fig6_manifest.json", "Fig5_Fig6_CAPTIONS.md", "Fig5_source_data.csv",
                  "Fig6_participant_source_data.csv", "Fig6_session_source_data.csv",
                  "Fig6_influence_source_data.csv"]
        require(all(not (args.figures / name).exists() for name in names), "New figure outputs already exist")
    loaded = load_and_audit(repo)
    (by_id, predictions, original_cpu, fit_rows, denominators, class_coverage,
     followup, audit, input_manifest) = loaded
    old = read_csv(repo / PUBLIC / "original_participant_endpoints.csv")
    seed_sessions, rebuilt, error = reconstruct_endpoints(by_id, predictions, old)
    audit["rebuilt_participant_endpoints"] = len(rebuilt)
    audit["maximum_original_endpoint_error_BA"] = error
    trials, sessions, participants = transition_tables(by_id, predictions)
    summary, influence, profiles, gain_pairs = summarize_transitions(participants, sessions, rebuilt)
    independent = independently_verify(original_cpu, participants, rebuilt, repo)
    key_findings = {}
    for label, members in COHORTS.items():
        key_findings[label] = {}
        for name, _, _ in CONTRASTS:
            rate = {component: figure_lookup(summary, label, name, "balanced_accuracy", component)
                    for component in ("corrected_pp", "introduced_pp", "net_pp")}
            selected = [r for r in influence if r["cohort"] == label and r["contrast"] == name
                        and r["measure"] == "balanced_accuracy"]
            net_values = [r["net_pp"] for r in participants if r["subject"] in members
                          and r["contrast"] == name and r["measure"] == "balanced_accuracy"]
            session_values = [r["net_pp"] for r in sessions if r["subject"] in members
                              and r["contrast"] == name and r["measure"] == "balanced_accuracy"]
            key_findings[label][name] = {
                "n_participants": len(members),
                **{k: {f: v[f] for f in ("mean_pp_or_pct", "ci95_low", "ci95_high")}
                   for k, v in rate.items()},
                "left_recall_change": {k: figure_lookup(summary, label, name, "left_recall")[k]
                                       for k in ("mean_pp_or_pct", "ci95_low", "ci95_high")},
                "right_recall_change": {k: figure_lookup(summary, label, name, "right_recall")[k]
                                        for k in ("mean_pp_or_pct", "ci95_low", "ci95_high")},
                "participant_sign_counts": signs(net_values), "session_sign_counts": signs(session_values),
                "leave_one_participant_out_mean_range_pp": [min(r["mean_net_pp"] for r in selected),
                                                            max(r["mean_net_pp"] for r in selected)],
                "target_session_mean_changes_pp": [next(
                    r["mean_net_pp"] for r in profiles if r["cohort"] == label
                    and r["contrast"] == name and r["session"] == session) for session in SESSIONS],
            }
    key_findings["primary_spatial_stage_share_of_total_mean_contrast_pct"] = (
        100 * key_findings["primary"]["full_minus_lda"]["net_pp"]["mean_pp_or_pct"]
        / key_findings["primary"]["full_minus_frozen"]["net_pp"]["mean_pp_or_pct"])
    key_findings["share_interpretation"] = "Arithmetic stage decomposition; no ratio interval or causal attribution."
    protocol = {
        "analysis_status": "post_observation_exploratory", "synthetic": False,
        "purpose": "Describe trial transitions and component-gain structure from saved predictions.",
        "comparisons": [dict(contrast=name, baseline=base, updated=updated)
                        for name, base, updated in CONTRASTS],
        "cohorts": {k: sorted(v) for k, v in COHORTS.items()},
        "weighting": "Each class 1/2 within session; each of five sessions 1/5; each participant 1/n.",
        "corrected_definition": "Baseline incorrect and update correct, divided by the full same-class query n.",
        "introduced_definition": "Baseline correct and update incorrect, divided by the full same-class query n.",
        "identity": "Updated BA minus baseline BA equals balanced corrected rate minus introduced rate.",
        "uncertainty": "10,000 participant bootstrap resamples, seed 42, lexicographic participant order; percentile 95%.",
        "existing_hypothesis_test_family": "Original four post-review sign-flip/Holm checks retained and re-enumerated.",
        "new_hypothesis_tests": 0, "new_fits": 0, "new_model_inference": 0,
        "development_and_all18_results_retained": True,
        "session_profiles_and_leave_one_out": "Descriptive sensitivity, not independent confirmation or policy evaluation.",
        "source_or_support_measurements_used_to_select_actions": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    files = {
        "trial_action_transitions.csv": trials, "session_class_transition_decomposition.csv": sessions,
        "participant_class_transition_decomposition.csv": participants,
        "cohort_transition_bootstrap.csv": summary, "participant_gain_pairs.csv": gain_pairs,
        "session_contrast_profiles.csv": profiles, "leave_one_participant_out.csv": influence,
        "reconstructed_seed_session_scores.csv": seed_sessions,
        "reconstructed_participant_endpoints.csv": rebuilt, "matched_label_fit_audit.csv": fit_rows,
        "trial_role_class_counts.csv": denominators, "query_class_coverage.csv": class_coverage,
    }
    for name, rows in files.items():
        write_csv(output / name, rows)
    write_json(output / "analysis_definition.json", protocol)
    write_json(output / "summary.json", key_findings)
    write_json(output / "input_completeness_audit.json", audit)
    write_json(output / "independent_arithmetic_check.json", independent)
    write_json(output / "followup_completion_status.json", followup)
    if make_figures:
        args.figures.mkdir(parents=True, exist_ok=True)
        figures = render_figures(args.figures, args.font_dir, summary, profiles, gain_pairs, influence)
        write_json(args.figures / "Fig5_Fig6_manifest.json", figures)
        write_csv(args.figures / "Fig5_source_data.csv", summary)
        write_csv(args.figures / "Fig6_participant_source_data.csv", gain_pairs)
        write_csv(args.figures / "Fig6_session_source_data.csv", profiles)
        write_csv(args.figures / "Fig6_influence_source_data.csv", influence)
        (args.figures / "Fig5_Fig6_CAPTIONS.md").write_text(
            "# Figure captions\n\n"
            "**Fig 5. Class-balanced error transitions separate correction from newly introduced errors.** "
            "Rows show the predefined primary cohort (12 participants), development cohort (6), and "
            "secondary all-participant summary (18). The contrasts are LDA-only recalibration minus "
            "frozen decoding, full refitting minus LDA-only recalibration, and full refitting minus "
            "frozen decoding. In A, C and E, blue bars show contributions from baseline errors "
            "corrected by the updated model; hatched orange bars show newly introduced errors with "
            "negative sign. Each rate uses the full same-class query denominator before averaging "
            "the two classes, five sessions and participants equally. Their sum equals the BA change. "
            "Black diamonds and bars show net BA changes and descriptive 95% participant-bootstrap "
            "intervals. B, D and F show left- and right-class recall changes with the same participant "
            "weighting and bootstrap method (10,000 resamples; seed 42). The all-18 row includes the "
            "other two cohorts and is not an independent replication. These decompositions were "
            "computed from saved predictions after observation of the original results.\n\n"
            "**Fig 6. Joint component gains and target-session profiles.** "
            "(A) Each point is one participant's equally weighted mean over five target sessions. "
            "The horizontal coordinate is LDA-only minus frozen BA; the vertical coordinate is "
            "full-refit minus LDA-only BA. Numbers identify the published participant IDs. Circles "
            "show the primary cohort and open squares the development cohort. The dashed line "
            "marks zero total full-refit-minus-frozen gain. (B) Primary-cohort session means for the "
            "total refit contrast and the same-label component contrast. Bars are descriptive 95% "
            "participant-bootstrap intervals (12 participants; 10,000 resamples; seed 42); the same "
            "participants appear in all sessions. Session profiles are exploratory descriptions, "
            "without separate session-level hypothesis tests. (C) Primary-cohort mean changes "
            "after leaving out each indicated participant (11 participants per point). Dashed lines "
            "mark the original 12-participant means; leave-one-out points are dependent influence "
            "summaries, not confidence limits or validation folds. Exact values for all three cohorts "
            "are supplied in the source-data tables.\n",
            encoding="utf-8",
        )
    for name, identity in input_manifest.items():
        require(digest(repo / name) == identity["sha256"], "Input changed during analysis")
    write_json(output / "input_sha256_manifest.json", input_manifest)
    commit = portable_bundle["source_git_commit"] if portable_bundle else subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    portable_folder = output / "portable_inputs"
    portable_folder.mkdir(exist_ok=False)
    if portable_bundle is None:
        portable_bundle = {"schema_version": 1, "source_git_commit": commit, "sources": {
            name: {"sha256": identity["sha256"], "text": source_bytes(repo / name).decode("utf-8")}
            for name, identity in input_manifest.items() if not name.startswith(str(PUBLIC) + "/")
        }}
    write_json(portable_folder / "update_mechanism_source_texts.json", portable_bundle)
    packages = {}
    for name in ("numpy", "matplotlib", "Pillow"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not_installed"
    receipt = {
        "completed_utc": datetime.now(timezone.utc).isoformat(), "source_git_commit": commit,
        "script_sha256": digest(__file__), "python": platform.python_version(),
        "platform": platform.platform(), "packages": packages, "seed": SEED,
        "bootstrap_replicates": BOOTSTRAPS, "input_hashes_unchanged_after_analysis": True,
        "new_model_fits": 0, "new_model_forward_passes": 0,
        "output_tables": {name: {"rows": len(rows), "sha256": digest(output / name)}
                          for name, rows in files.items()},
        "independent_arithmetic_check_performed": True,
        "original_scientific_results_modified": False,
        "analysis_status": "post_observation_exploratory",
    }
    write_json(output / "execution_receipt.json", receipt)
    print(json.dumps({"output": str(output), "figures": str(args.figures),
                      "primary": key_findings["primary"], "all_assertions_passed": True}, indent=2))


if __name__ == "__main__":
    main()
