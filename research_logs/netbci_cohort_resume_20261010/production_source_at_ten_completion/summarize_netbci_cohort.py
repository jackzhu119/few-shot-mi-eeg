"""Summarize verified NETBCI participant trajectories without downloads or fitting.

Each participant is an independent unit. Session scores are unweighted means of
published run percentages, never trial outcomes. Task-window power contrasts are
not baseline ERD; frozen-decoder failure is not human skill loss. Figures retain
individual participants and explicitly report metric availability.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from learning_preserving_bci.datasets.netbci import file_sha256
from learning_preserving_bci.datasets.netbci_behavior import join_verified_sessions, read_behavior_sessions
from learning_preserving_bci.utils.reproducibility import collect_provenance

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = ("01", "02", "03", "04")
LABELS = ("rest", "right_hand")
BEHAVIOR_ROOT = ROOT / "research_logs/netbci2026_sources/original_dataverse"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_table(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_table(path, rows):
    if not rows:
        return
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def finite_or_none(value):
    if value is None or value == "unavailable":
        return None
    number = float(value)
    require(np.isfinite(number), "Nonfinite metric must be explicitly unavailable")
    return number


def participant_statistics(rows, subjects, sessions, metrics, seed, repetitions):
    """Resample complete subject trajectories; never trials or repeated subsamples."""
    require(len(subjects) == len(set(subjects)) and bool(subjects), "Duplicate/empty participant list")
    require(len(sessions) >= 2 and len(sessions) == len(set(sessions)), "Duplicate/short session list")
    index = {(row["subject"], row["session"]): row for row in rows}
    require(len(index) == len(rows), "Duplicate participant/session key")
    require(set(index) == {(subject, session) for subject in subjects for session in sessions},
            "Incomplete or unexpected participant/session coverage")
    require(repetitions >= 1, "Positive participant bootstrap count required")
    summary, changes, individual, matrices = [], [], [], {}
    for metric in metrics:
        matrix = np.array([[np.nan if finite_or_none(index[s, t].get(metric)) is None
                            else float(index[s, t][metric]) for t in sessions] for s in subjects])
        matrices[metric] = matrix
        # A single draw matrix keeps within-person and cross-session dependence.
        rng = np.random.default_rng(seed)
        draws = rng.integers(0, len(subjects), (repetitions, len(subjects)))
        for position, session in enumerate(sessions):
            values = matrix[:, position]
            available = np.isfinite(values)
            valid = values[available]
            # All requested subjects are retained in the draws, with missing metric
            # cells omitted only from that metric's descriptive mean. Report n.
            samples = values[draws]
            denominators = np.isfinite(samples).sum(axis=1)
            boot = np.nansum(samples, axis=1)[denominators > 0] / denominators[denominators > 0]
            interval = np.quantile(boot, [.025, .975]).tolist() if len(boot) else [None, None]
            summary.append({"metric": metric, "session": session, "n_requested_subjects": len(subjects),
                            "n_available_subjects": len(valid), "mean": float(valid.mean()) if len(valid) else None,
                            "median": float(np.median(valid)) if len(valid) else None,
                            "subject_bootstrap_CI95_low": interval[0], "subject_bootstrap_CI95_high": interval[1],
                            "unavailable_subjects": ",".join(np.array(subjects)[~available]),
                            "CI_scope": "participant-resampling conditional on first-ten-ID sample; not causal"})
        delta = matrix[:, -1] - matrix[:, 0]
        valid = np.isfinite(delta)
        values = delta[valid]
        # Paired changes are computed before resampling; no subtraction of two
        # independently bootstrapped session means and no trial pseudoreplication.
        samples = delta[draws]
        denominators = np.isfinite(samples).sum(axis=1)
        boot = np.nansum(samples, axis=1)[denominators > 0] / denominators[denominators > 0]
        interval = np.quantile(boot, [.025, .975]).tolist() if len(boot) else [None, None]
        change = {"metric": metric, "contrast": f"session{sessions[-1]}_minus_session{sessions[0]}",
                  "n_requested_subjects": len(subjects), "n_paired_subjects": len(values),
                  "mean_change": float(values.mean()) if len(values) else None,
                  "median_change": float(np.median(values)) if len(values) else None,
                  "min_change": float(values.min()) if len(values) else None,
                  "max_change": float(values.max()) if len(values) else None,
                  "n_increased": int((values > 1e-10).sum()), "n_decreased": int((values < -1e-10).sum()),
                  "n_unchanged": int((np.abs(values) <= 1e-10).sum()),
                  "subject_bootstrap_CI95_low": interval[0], "subject_bootstrap_CI95_high": interval[1],
                  "unavailable_subjects": ",".join(np.array(subjects)[~valid]),
                  "bootstrap_repetitions": repetitions,
                  "CI_scope": "paired participants; exploratory observational contrast"}
        changes.append(change)
        individual.extend({"subject": subject, "metric": metric,
                           "first_session_value": finite_or_none(matrix[i, 0]) if np.isfinite(matrix[i, 0]) else None,
                           "last_session_value": finite_or_none(matrix[i, -1]) if np.isfinite(matrix[i, -1]) else None,
                           "last_minus_first": float(delta[i]) if valid[i] else None,
                           "status": "available" if valid[i] else "unavailable_retained"}
                          for i, subject in enumerate(subjects))
    return summary, changes, individual, matrices


def equal_run_spectral(trials, sessions, runs, exclude_flagged=False, reference="CAR"):
    """Equal run weighting within each task; preserve absent cells as unavailable."""
    rows = []
    require(reference in ("CAR", "source_reference"), "Unknown spectral reference")
    require(bool(runs) and len(runs) == len(set(runs)), "Duplicate/empty spectral run list")
    suffix = "ROI_V2" if reference == "CAR" else "source_reference_ROI_V2"
    for session in sessions:
        for band in ("mu", "beta"):
            means, powers, counts, missing = {}, {}, {}, []
            for label in LABELS:
                log_means, arithmetic, ns = [], [], []
                for run in runs:
                    selected = [row for row in trials if row["session"] == session and row["run"] == run
                                and row["label"] == label and (not exclude_flagged or row["qc_flag"] == "False")]
                    if not selected:
                        missing.append(f"{session}/{run}/{label}")
                        continue
                    values = np.array([float(row[f"{band}_{suffix}"]) for row in selected])
                    require(np.isfinite(values).all() and (values > 0).all(), "Invalid positive spectral power")
                    log_means.append(float(np.log10(values).mean()))
                    arithmetic.append(float(values.mean()) * 1e12)
                    ns.append(len(values))
                means[label] = float(np.mean(log_means)) if len(log_means) == len(runs) else None
                powers[label] = float(np.mean(arithmetic)) if len(arithmetic) == len(runs) else None
                counts[label] = sum(ns)
            rows.append({"session": session, "band": band, "reference": reference,
                         "runs": ",".join(runs), "exclude_qc_flagged": exclude_flagged,
                         "status": "unavailable_missing_cell" if missing else "available",
                         "missing_cells": ",".join(missing), "n_rest": counts["rest"], "n_MI": counts["right_hand"],
                         "MI_minus_rest_log_power_dB": None if missing else 10*(means["right_hand"]-means["rest"]),
                         "rest_equal_run_arithmetic_power_uV2": powers["rest"],
                         "MI_equal_run_arithmetic_power_uV2": powers["right_hand"],
                         "interpretation": "task_window_contrast_not_baseline_ERD_or_neural_learning"})
    return rows


def expected_trial_roles(events, config):
    """Derive source/query identity from the audited chronology, not saved flags."""
    sessions = config["session_order"]
    require(set(config["source_train_runs"]) == {"01", "02", "03", "04"} and
            set(config["source_query_runs"]) == {"05", "06"} and
            set(config["later_query_runs"]) == set(config["expected_runs"]),
            "Source/query runs differ from the fixed cohort protocol")
    require(len({row["subject"] for row in events}) == 1, "Mixed event participants")
    require(len({row["trial_id"] for row in events}) == len(events), "Duplicate event ID")
    require({row["session"] for row in events} == set(sessions), "Session coverage mismatch")
    for session in sessions:
        require({row["run"] for row in events if row["session"] == session} == set(config["expected_runs"]),
                "Audited run coverage differs from preset cohort protocol")
    roles = {}
    for row in events:
        require(row["label"] in LABELS, "Unexpected audited task label")
        if row["session"] == sessions[0]:
            role = "source_train" if row["run"] in config["source_train_runs"] else "source_reference_query"
        else:
            role = "validation_no_selection" if row["session"] == sessions[1] else "test_exploratory"
        roles[row["trial_id"]] = role
    return roles


def verify_predictions(predictions, decoder, events, config, trials=None):
    """Reject accidentally reused pilot partitions and retain constant predictions."""
    event_index = {row["trial_id"]: row for row in events}
    require(len(event_index) == len(events), "Duplicate event ID")
    require(len({row["trial_id"] for row in predictions}) == len(predictions), "Duplicate prediction ID")
    roles = expected_trial_roles(events, config)
    require({row["trial_id"] for row in predictions} ==
            {trial_id for trial_id, role in roles.items() if role != "source_train"},
            "Prediction coverage contains missing or unexpected query trials")
    require({row["session"] for row in predictions} <= set(config["session_order"]),
            "Unexpected prediction session")
    subject = events[0]["subject"]
    train_n = sum(role == "source_train" for role in roles.values())
    qc_by_trial = {row["trial_id"]: row["qc_flag"] == "True" for row in trials} if trials is not None else None
    scores = {row["session"]: row for row in decoder}
    require(len(scores) == len(decoder), "Duplicate decoder session")
    require(set(scores) == set(config["session_order"]), "Incomplete decoder session coverage")
    for session in config["session_order"]:
        runs = config["source_query_runs"] if session == config["session_order"][0] else config["later_query_runs"]
        expected = {row["trial_id"] for row in events if row["session"] == session and row["run"] in runs}
        selected = [row for row in predictions if row["session"] == session]
        require({row["trial_id"] for row in selected} == expected,
                "Frozen query coverage differs from preset cohort partition; do not reuse pilot targets")
        for row in selected:
            event = event_index[row["trial_id"]]
            require(all(row[key] == event[key] for key in ("subject", "session", "run")), "Prediction identity mismatch")
            require(row["true_label"] == event["label"] and row["prediction"] in LABELS, "Prediction label mismatch")
            require(row["role"] == roles[row["trial_id"]], "Prediction partition role mismatch")
        matrix = np.array([[sum(row["true_label"] == truth and row["prediction"] == pred for row in selected)
                            for pred in LABELS] for truth in LABELS])
        score = scores[session]
        expected_role = "source_reference_query" if session == config["session_order"][0] else (
            "validation_no_selection" if session == config["session_order"][1] else "test_exploratory")
        require(score["subject"] == subject and score["role"] == expected_role and score["decoder"] == "CSP_LDA",
                "Decoder identity/role mismatch")
        require(score["train_n"] == train_n and score["participant_n"] == 1,
                "Decoder training count or independent unit mismatch")
        require(score["n_runs"] == len({row["run"] for row in selected}) and
                score["n_rest"] == int(matrix[0].sum()) and score["n_right_hand"] == int(matrix[1].sum()),
                "Saved decoder run/class count mismatch")
        require(matrix.tolist() == score["confusion_matrix_rest_right_hand"], "Saved confusion matrix mismatch")
        require(len(selected) == score["n_test"], "Saved decoder sample count mismatch")
        constant = len({row["prediction"] for row in selected}) == 1
        require(constant == score["constant_prediction"], "Constant prediction flag mismatch")
        if (matrix.sum(axis=1) > 0).all():
            ba = float(np.mean(np.diag(matrix) / matrix.sum(axis=1)))
            require(np.isclose(ba, score["balanced_accuracy"], rtol=0, atol=1e-12), "Saved BA mismatch")
        else:
            require(score["balanced_accuracy"] is None, "Missing query class cannot support BA")
        interval = score["conditional_run_bootstrap_CI95"]
        if interval is not None:
            require(len(interval) == 2 and all(value is not None and 0 <= finite_or_none(value) <= 1 for value in interval)
                    and interval[0] <= interval[1], "Conditional BA interval must be ordered fractions")
        if qc_by_trial is not None:
            clean = [row for row in selected if not qc_by_trial[row["trial_id"]]]
            require(score["n_qc_flagged_query"] == len(selected) - len(clean) and
                    score["qc_unflagged_n"] == len(clean), "Saved decoder QC count mismatch")
            clean_recalls = [np.mean([row["prediction"] == label for row in clean if row["true_label"] == label])
                             for label in LABELS if any(row["true_label"] == label for row in clean)]
            if len(clean_recalls) == 2:
                require(np.isclose(np.mean(clean_recalls), score["qc_unflagged_BA"], rtol=0, atol=1e-12),
                        "Saved QC-unflagged BA mismatch")
            else:
                require(score["qc_unflagged_BA"] is None, "Missing QC query class cannot support BA")


def verify_hashes(directory, receipt, required):
    for name in required:
        require(name in receipt["outputs"], f"Missing output hash: {name}")
        require(file_sha256(directory / name) == receipt["outputs"][name], f"Analysis output hash mismatch: {name}")


def summarize_matching(subject, geometry, spectral, statuses, config):
    """Check each preset repetition/cell before averaging within participants."""
    runs_by_variant = {"all_six_runs": config["expected_runs"], "qc_common_four_runs": config["qc_matched_runs"]}
    status_index = {row["variant"]: row for row in statuses}
    require(len(status_index) == len(statuses) and set(status_index) == set(runs_by_variant),
            "Duplicate/missing/unexpected matching variant status")
    repetitions = set(range(config["matched_repetitions"]))
    require(bool(repetitions), "Positive matched repetition count required")
    sessions = config["session_order"]
    for rows in (geometry, spectral):
        require(all(row["subject"] == subject and row["variant"] in runs_by_variant and
                    row["session"] in sessions for row in rows), "Matched result identity mismatch")
    result = []
    fields = ("AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance")
    for variant, runs in runs_by_variant.items():
        status = status_index[variant]
        require(status["runs"] == runs and status["status"] in ("available", "unavailable"),
                "Matching variant differs from preset runs/status")
        expected_n = len(runs) * len(LABELS) * config["matched_trials_per_class_per_run"]
        for session in sessions:
            chosen = [row for row in geometry if row["variant"] == variant and row["session"] == session]
            selected_spectral = [row for row in spectral if row["variant"] == variant and row["session"] == session]
            if status["status"] == "available":
                require(status["repetitions"] == config["matched_repetitions"] and
                        len(chosen) == len(repetitions) and {int(row["repetition"]) for row in chosen} == repetitions,
                        "Matched geometry repetitions mismatch")
                expected_spectral = {(repetition, band) for repetition in repetitions for band in ("mu", "beta")}
                require(len(selected_spectral) == len(expected_spectral) and
                        {(int(row["repetition"]), row["band"]) for row in selected_spectral} == expected_spectral,
                        "Matched spectral repetitions/cells mismatch")
                require(all(int(row["n_matched"]) == expected_n for row in chosen + selected_spectral),
                        "Matched trial count differs from fixed preset")
                require(all(finite_or_none(row[field]) is not None and float(row[field]) >= -1e-10
                            for row in chosen for field in fields), "Nonfinite/negative matched geometry")
                require(all(finite_or_none(row["MI_minus_rest_log_power_dB"]) is not None for row in selected_spectral),
                        "Nonfinite matched spectral contrast")
            else:
                require(not chosen and not selected_spectral, "Unavailable matching variant contains partial results")
                require(status.get("preset_not_relaxed") is True and bool(status.get("error")),
                        "Unavailable matching variant lacks preset failure evidence")
            result.append({"subject": subject, "session": session, "variant": variant,
                           "status": status["status"], "error": status.get("error", ""),
                           "n_subsample_repetitions": len(chosen),
                           "n_matched_trials_per_repetition": expected_n if chosen else 0,
                           **{field: float(np.mean([float(row[field]) for row in chosen])) if chosen else None for field in fields},
                           **{f"{band}_MI_minus_rest_dB": float(np.mean([
                               float(row["MI_minus_rest_log_power_dB"]) for row in selected_spectral if row["band"] == band]))
                               if chosen else None for band in ("mu", "beta")}})
    return result


def verify_event_selection(source, eligible, excluded, subject, original, audit_summary):
    """Every source event must remain eligible or carry an explicit exclusion."""
    source_index = {row["trial_id"]: row for row in source}
    eligible_ids = {row["trial_id"] for row in eligible}
    excluded_ids = {row["trial_id"] for row in excluded}
    require(len(source_index) == len(source) and len(eligible_ids) == len(eligible) and
            len(excluded_ids) == len(excluded), "Duplicate source/eligible/excluded event ID")
    require(not eligible_ids & excluded_ids and eligible_ids | excluded_ids == set(source_index),
            "Source event eligibility/exclusion is not disjoint and exhaustive")
    require(len(source) == audit_summary["total_source_trials"] and
            len(eligible) == audit_summary["total_trials"] and len(excluded) == audit_summary["excluded_trial_count"],
            "Source/eligible/excluded audit counts disagree")
    for row in source + eligible + excluded:
        require(row["subject"] == subject and row["original_subject"] == original and row["label"] in LABELS,
                "Source/eligible/excluded participant or label mismatch")
        original_row = source_index[row["trial_id"]]
        require(all(row[key] == original_row[key] for key in
                    ("subject", "session", "run", "label", "source_file", "trial_id", "tsv_row",
                     "stored_event_value", "onset_s", "duration_s", "start_sample", "stop_sample_exclusive")
                    if key in original_row),
                "Selected/excluded source event identity mismatch")
    for rows, field in ((source, "source_class_counts"), (eligible, "class_counts"),
                        (excluded, "excluded_class_counts")):
        actual = Counter(row["label"] for row in rows)
        require(all(actual[label] == audit_summary[field].get(label, 0) for label in LABELS),
                "Source/eligible/excluded class counts disagree")
    if source and "fixed_window_eligible" in source[0]:
        require(all(row["fixed_window_eligible"] == "True" for row in eligible) and
                all(row["fixed_window_eligible"] == "False" and bool(row.get("exclusion_reason")) for row in excluded),
                "Window eligibility flags or exclusion reasons disagree")


def load_participant(subject, config_path, config, analysis_root, audit_root):
    inputs = {}
    analysis_dir = analysis_root / subject
    if not (analysis_dir / "analysis_receipt.json").is_file():
        analysis_dir = analysis_dir / "run01"
    audit_dir = audit_root / subject
    inputs["analysis_receipt"] = analysis_dir / "analysis_receipt.json"
    inputs["audit"] = audit_dir / "audit.json"
    audit = json.loads(inputs["audit"].read_text())
    require(audit["summary"]["subject"] == subject and audit["summary"]["all_checks_pass"] is True,
            "Failed or wrong-subject data audit")
    require(audit["synthetic"] is False, "Synthetic audit cannot enter actual cohort summary")
    mapping = audit["upstream_mapping"]
    require(mapping["derivative_subject"] == subject and
            mapping["actual_headers_hash_verified"] == mapping["declared_original_headers"] == 24,
            "Original header identity not fully verified")
    original = mapping["original_subject"]
    analysis = json.loads(inputs["analysis_receipt"].read_text())
    require(analysis["synthetic"] is False and analysis["subject"] == subject, "Analysis subject/synthetic mismatch")
    require(analysis["status"] in ("completed_exploratory", "completed_with_scientific_failures"),
            "EEG analysis incomplete; report failure before cohort interpretation")
    require(analysis["config_sha256"] == file_sha256(config_path), "Analysis config SHA mismatch")
    for name in ("adapter_receipt.json", "events.tsv", "run_inventory.tsv"):
        inputs[f"audit/{name}"] = audit_dir / name
        require(file_sha256(inputs[f"audit/{name}"]) == audit["output_artifact_sha256"][name],
                f"Audit artifact hash mismatch: {name}")
    if "total_source_trials" in audit["summary"]:
        for name in ("source_events.tsv", "excluded_events.tsv"):
            inputs[f"audit/{name}"] = audit_dir / name
            require(file_sha256(inputs[f"audit/{name}"]) == audit["output_artifact_sha256"][name],
                    f"Audit artifact hash mismatch: {name}")
    adapter = json.loads(inputs["audit/adapter_receipt.json"].read_text())
    require(adapter["synthetic"] is False and adapter["subject"] == subject and
            adapter["original_subject"] == original and adapter["signal_unit"] == "V",
            "Adapter participant/unit mismatch")
    require(analysis["bundle_sha256"] == adapter["epochs_sha256"] and
            analysis["metadata_sha256"] == adapter["metadata_sha256"], "Analysis bundle differs from audited adapter")
    require(analysis["trials"] == audit["summary"]["total_trials"] == adapter["trial_count"], "EEG trial counts disagree")
    require(analysis["channel_names"] == adapter["channel_names"], "EEG channel mapping differs")
    require(analysis["sampling_frequency_hz"] == adapter["sampling_frequency_hz"] == config["expected_sfreq_hz"],
            "Analysis sampling frequency differs from audited/preset data")
    required = ["event_inventory.tsv", "trial_features.tsv", "matched_variants_status.json",
                "failures.json", "decoder_results.json", "transform_audit.json", "partitions.json"]
    for name in ("matched_geometry.tsv", "matched_spectral_contrasts.tsv", "predictions.tsv", "CSP_LDA_model_audit.json"):
        if (analysis_dir / name).exists():
            required.append(name)
    verify_hashes(analysis_dir, analysis, required)
    verify_hashes(analysis_dir, analysis, analysis["outputs"])
    for name in analysis["outputs"]:
        inputs[name] = analysis_dir / name
    events = read_table(inputs["audit/events.tsv"])
    source_events = read_table(inputs["audit/source_events.tsv"]) if "audit/source_events.tsv" in inputs else events
    exclusions = read_table(inputs["audit/excluded_events.tsv"]) if "audit/excluded_events.tsv" in inputs else []
    if "total_source_trials" in audit["summary"]:
        verify_event_selection(source_events, events, exclusions, subject, original, audit["summary"])
        require(adapter["total_source_trials"] == len(source_events) and adapter["excluded_trial_count"] == len(exclusions),
                "Adapter source/eligible/excluded counts disagree with audit")
    trials = read_table(inputs["trial_features.tsv"])
    analyzed_events = read_table(inputs["event_inventory.tsv"])
    require(len(events) == len(trials) == len(analyzed_events) == analysis["trials"], "Feature/event count mismatch")
    event_ids = [row["trial_id"] for row in events]
    require(len(set(event_ids)) == len(event_ids), "Duplicate audited event ID")
    require(event_ids == [row["trial_id"] for row in trials] == [row["trial_id"] for row in analyzed_events],
            "Feature/event identity order mismatch")
    for event, trial, analyzed in zip(events, trials, analyzed_events, strict=True):
        require(event["original_subject"] == original and event["subject"] == subject, "Original subject identity mismatch")
        require(all(event[key] == trial[key] == analyzed[key] for key in
                    ("subject", "session", "run", "label", "source_file", "trial_id", "tsv_row",
                     "stored_event_value", "onset_s", "duration_s", "start_sample", "stop_sample_exclusive")
                    if key in event), "Feature/event metadata mismatch")
        require(trial["qc_flag"] in ("True", "False"), "Invalid saved QC flag")
    expected_roles = expected_trial_roles(events, config)
    require(all(row["analysis_role"] == expected_roles[row["trial_id"]] for row in trials + analyzed_events),
            "Saved event/feature partition role differs from audited chronology")
    train_ids = [row["trial_id"] for row in events if expected_roles[row["trial_id"]] == "source_train"]
    partition = json.loads(inputs["partitions.json"].read_text())
    expected_partitions = {role: [row["trial_id"] for row in events if expected_roles[row["trial_id"]] == role]
                           for role in ("source_train", "source_reference_query", "validation_no_selection", "test_exploratory")}
    require(partition["subject"] == subject and partition["partition_trial_ids"] == expected_partitions and
            partition["all_trials_assigned_once"] is True and partition["validation_selection_performed"] is False,
            "Saved partitions differ from preset chronology")
    transform = json.loads(inputs["transform_audit.json"].read_text())
    require(transform["source_train_trial_ids"] == train_ids and transform["scaler_fit_source_only"] is True and
            transform["reference_PCA_fit_source_only"] is True and transform["target_PCA_descriptive_only"] is True and
            transform["target_prediction_transforms_fitted"] is False and transform["channel_names"] == adapter["channel_names"],
            "Transform source-training/coordinate evidence differs from preset")
    failures = json.loads(inputs["failures.json"].read_text())
    require(len(failures) == analysis["failures_n"], "Analysis failure count mismatch")
    decoder = json.loads(inputs["decoder_results.json"].read_text())
    if decoder:
        require("predictions.tsv" in inputs and "CSP_LDA_model_audit.json" in inputs, "Decoder lacks immutable model evidence")
        verify_predictions(read_table(inputs["predictions.tsv"]), decoder, events, config, trials)
        model = json.loads(inputs["CSP_LDA_model_audit.json"].read_text())
        require(model["query_state_unchanged"] is True and model["prediction_replay_exact"] is True and
                model["parameter_sha256_before"] == model["parameter_sha256_after"] and model["fit_calls"] == 1,
                "Frozen model state verification failed")
        require(model["source_train_trial_ids"] == train_ids and model["source_train_n"] == len(train_ids) and
                model["parameters_predefined_no_target_selection"] is True and model["target_transforms_fitted_for_prediction"] is False,
                "Frozen model training IDs differ from preset source partition")
        require("csp_lda.pkl" in inputs and file_sha256(inputs["csp_lda.pkl"]) == model["parameter_sha256_after"],
                "Saved frozen model bytes differ from audited state digest")
        for score in decoder:
            if score["constant_prediction"]:
                require(any(row["scope"] == "CSP_LDA_query" and row.get("session") == score["session"] and
                            row.get("type") == "constant_prediction" for row in failures),
                        "Constant prediction lacks retained failure evidence")
            if score["balanced_accuracy"] is None:
                require(any(row["scope"] == "CSP_LDA_query" and row.get("session") == score["session"] and
                            row.get("type") == "missing_query_class" for row in failures),
                        "Unavailable query BA lacks retained failure evidence")
    else:
        require(any(row["scope"] == "CSP_LDA_fit_or_query" for row in failures),
                "Unavailable decoder lacks recorded failure evidence")
    scores = {row["session"]: row for row in decoder}
    spectral = equal_run_spectral(trials, config["session_order"], config["expected_runs"])
    sensitivity = []
    for reference in ("CAR", "source_reference"):
        for name, runs, clean in (("all_six_runs_all_trials", config["expected_runs"], False),
                                  ("common_four_runs_all_trials", config["qc_matched_runs"], False),
                                  ("common_four_runs_qc_unflagged", config["qc_matched_runs"], True)):
            sensitivity.extend(dict(row, subject=subject, variant=name) for row in equal_run_spectral(
                trials, config["session_order"], runs, clean, reference))
    by_spectral = {(row["session"], row["band"]): row for row in spectral}
    sessions = []
    for session in config["session_order"]:
        selected = [row for row in trials if row["session"] == session]
        session_source = [row for row in source_events if row["session"] == session]
        session_exclusions = [row for row in exclusions if row["session"] == session]
        score = scores.get(session)
        sessions.append({"subject": subject, "session": session, "original_subject_from_audit": original,
                         "n_EEG_trials": len(selected), "n_EEG_runs": len({row["run"] for row in selected}),
                         "n_EEG_source_events": len(session_source), "n_EEG_excluded_events": len(session_exclusions),
                         "n_source_rest": sum(row["label"] == "rest" for row in session_source),
                         "n_source_MI": sum(row["label"] == "right_hand" for row in session_source),
                         "n_rest": sum(row["label"] == "rest" for row in selected),
                         "n_MI": sum(row["label"] == "right_hand" for row in selected),
                         "n_qc_flagged": sum(row["qc_flag"] == "True" for row in selected),
                         "CSP_BA_percent": 100*score["balanced_accuracy"] if score and score["balanced_accuracy"] is not None else None,
                         "CSP_constant_prediction": score["constant_prediction"] if score else "unavailable",
                         "CSP_query_n": score["n_test"] if score else 0,
                         "CSP_query_n_runs": score["n_runs"] if score else 0,
                         "CSP_conditional_run_CI95_percent": json.dumps(
                             [100 * value for value in score["conditional_run_bootstrap_CI95"]]
                             if score and score["conditional_run_bootstrap_CI95"] is not None else None),
                         "CSP_status": "available" if score and score["balanced_accuracy"] is not None else "unavailable_retained",
                         **{f"{band}_MI_minus_rest_dB": by_spectral[session, band]["MI_minus_rest_log_power_dB"] for band in ("mu", "beta")},
                         **{f"{band}_{label}_power_uV2": by_spectral[session, band][f"{label}_equal_run_arithmetic_power_uV2"]
                            for band in ("mu", "beta") for label in ("rest", "MI")}})
    geometry = read_table(inputs["matched_geometry.tsv"]) if "matched_geometry.tsv" in inputs else []
    matched_spectral = read_table(inputs["matched_spectral_contrasts.tsv"]) if "matched_spectral_contrasts.tsv" in inputs else []
    statuses = json.loads(inputs["matched_variants_status.json"].read_text())
    matching_rows = summarize_matching(subject, geometry, matched_spectral, statuses, config)
    for status in statuses:
        if status["status"] == "unavailable":
            require(any(row["scope"] == "matched_geometry" and row.get("variant") == status["variant"] and
                        row.get("status") == "unavailable" for row in failures),
                    "Unavailable matching variant lacks retained failure record")
    return original, sessions, sensitivity, matching_rows, inputs, analysis


def plot_results(output, subjects, sessions, trajectories, changes, individuals, matching):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    figure_dir = output / "figures"
    figure_dir.mkdir()
    x = np.arange(len(sessions)) + 1
    colors = plt.get_cmap("tab10")(np.arange(len(subjects)) % 10)
    layouts = [("mean_run_hit_percent", "Published online hit score (%)"),
               ("CSP_BA_percent", "Frozen CSP balanced accuracy (%)"),
               ("mu_MI_minus_rest_dB", "Mu MI − rest log-power (dB)"),
               ("beta_MI_minus_rest_dB", "Beta MI − rest log-power (dB)")]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for ax, (metric, title) in zip(axes.flat, layouts, strict=True):
        matrix = trajectories[metric]
        for i, subject in enumerate(subjects):
            ax.plot(x, matrix[i], "o-", color=colors[i], alpha=.65, linewidth=1, markersize=3, label=subject)
        n_available = np.isfinite(matrix).sum(axis=0)
        means = np.divide(np.nansum(matrix, axis=0), n_available,
                          out=np.full(matrix.shape[1], np.nan), where=n_available > 0)
        ax.plot(x, means, "D-", color="black", linewidth=2.5, markersize=5, label="participant mean")
        ax.set(title=title, xticks=x, xticklabels=sessions, xlabel="Protocol session")
        ax.text(.02, .02, "available n=" + "/".join(map(str, np.isfinite(matrix).sum(axis=0))),
                transform=ax.transAxes, fontsize=8)
    axes[0, 1].axhline(50, linestyle="--", color="grey", linewidth=1)
    axes[1, 0].axhline(0, linestyle="--", color="grey", linewidth=1)
    axes[1, 1].axhline(0, linestyle="--", color="grey", linewidth=1)
    axes[0, 0].legend(fontsize=7, ncol=3)
    fig.suptitle(f"NETBCI: {len(subjects)} audited participants; exploratory longitudinal trajectories")
    fig.text(.5, .01, "Behavior: mean of six published run percentages, not pooled hit rate. CSP: session 01 query runs 05–06; later sessions all six.\n"
             "Power: equal run-weighted task-window contrast; no baseline ERD or human skill-retention inference.",
             ha="center", fontsize=8)
    fig.tight_layout(rect=[0, .055, 1, .95])
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"cohort_trajectories.{extension}", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, (metric, title) in zip(axes, layouts[:3], strict=True):
        selected = [row for row in individuals if row["metric"] == metric]
        values = np.array([np.nan if row["last_minus_first"] is None else row["last_minus_first"] for row in selected])
        for i in range(len(subjects)):
            ax.scatter(values[i], i, color=colors[i], s=35)
        change = next(row for row in changes if row["metric"] == metric)
        ax.axvline(0, color="grey", linestyle="--", linewidth=1)
        if change["mean_change"] is not None:
            ax.errorbar(change["mean_change"], len(subjects), xerr=np.array([
                [change["mean_change"]-change["subject_bootstrap_CI95_low"]],
                [change["subject_bootstrap_CI95_high"]-change["mean_change"]]]), fmt="D", color="black", capsize=3)
        ax.set(yticks=range(len(subjects)+1), yticklabels=subjects+["mean ± CI"],
               xlabel="Session 04 − session 01", title=title)
        ax.text(.02, .02, f"paired n={change['n_paired_subjects']}/{len(subjects)}", transform=ax.transAxes, fontsize=8)
    fig.suptitle("All individual changes retained; 95% percentile CI resamples paired participants")
    fig.tight_layout()
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"cohort_paired_changes.{extension}", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
    for row_number, variant in enumerate(("all_six_runs", "qc_common_four_runs")):
        for ax, field in zip(axes[row_number], ("AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance"), strict=True):
            index = {(row["subject"], row["session"]): row for row in matching if row["variant"] == variant}
            matrix = np.array([[np.nan if index[s, t][field] is None else index[s, t][field]
                                for t in sessions] for s in subjects])
            for i in range(len(subjects)):
                ax.plot(x, matrix[i], "o-", color=colors[i], alpha=.65, linewidth=1, markersize=3)
            if np.isfinite(matrix).any():
                n_available = np.isfinite(matrix).sum(axis=0)
                mean = np.divide(np.nansum(matrix, axis=0), n_available,
                                 out=np.full(matrix.shape[1], np.nan), where=n_available > 0)
                ax.plot(x, mean, "D-", color="black", linewidth=2, markersize=4)
            ax.set(title=field, ylabel=variant, xticks=x, xticklabels=sessions, xlabel="Protocol session")
            ax.text(.02, .02, "available n=" + "/".join(map(str, np.isfinite(matrix).sum(axis=0))), transform=ax.transAxes, fontsize=8)
    fig.suptitle("Descriptive geometry; matched repetitions averaged within each participant")
    fig.text(.5, .01, "QC-common-four run matching uses preset cells/counts; unavailable participants remain recorded. Geometry change does not identify learning.", ha="center", fontsize=8)
    fig.tight_layout(rect=[0, .035, 1, .95])
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"cohort_geometry.{extension}", dpi=180)
    plt.close(fig)


def summarize(config_path, analysis_root, audit_root, output):
    started = time.monotonic()
    require(not output.exists(), "Prior summary exists; choose a new output directory")
    config = json.loads(config_path.read_text())
    subjects, sessions = config["subjects"], config["session_order"]
    require(bool(subjects) and len(subjects) == len(set(subjects)), "Duplicate/empty participant list")
    require(tuple(sessions) == SESSIONS, "Protocol session order differs")
    inputs = {"config": config_path, "summary_script": Path(__file__),
              "behavior_source": BEHAVIOR_ROOT/"participants.tsv",
              "behavior_dictionary": BEHAVIOR_ROOT/"participants.json",
              "behavior_receipt": BEHAVIOR_ROOT/"behavior_receipt.json"}
    source_receipt = json.loads(inputs["behavior_receipt"].read_text())
    for key, checksum in (("behavior_source", source_receipt["official_checksum"]),
                          ("behavior_dictionary", source_receipt["behavior_dictionary"]["checksum"])):
        require(checksum["type"].upper() == "MD5" and
                hashlib.md5(inputs[key].read_bytes()).hexdigest() == checksum["value"], "Official behavior source MD5 mismatch")
    columns = {session: f"BCI-Performance-session{int(session)}" for session in sessions}
    dictionary = inputs["behavior_dictionary"].read_text()
    require(all(f'"{column}"' in dictionary for column in columns.values()), "Missing source session dictionary field")
    try:
        json.loads(dictionary)
        dictionary_status = "valid_strict_JSON"
    except json.JSONDecodeError as error:
        dictionary_status = f"invalid_strict_JSON_preserved: {error.msg}; line {error.lineno}"
    behavior, _ = read_behavior_sessions(inputs["behavior_source"], columns, 6)
    require(len({row["original_subject"] for row in behavior}) == 19, "Behavior source cohort count changed")
    mapping, eeg_sessions, spectral, matching, receipts, scientific_failures, data_exclusions = {}, [], [], [], [], [], []
    for subject in subjects:
        original, rows, bands, geometry, files, receipt = load_participant(
            subject, config_path, config, analysis_root, audit_root)
        require(original not in mapping.values(), "Duplicate original participant mapping")
        mapping[subject] = original
        eeg_sessions.extend(rows)
        spectral.extend(bands)
        matching.extend(geometry)
        inputs.update({f"{subject}/{key}": value for key, value in files.items()})
        receipts.append(receipt)
        scientific_failures.extend(dict(row, subject=subject) for row in json.loads(files["failures.json"].read_text()))
        if "audit/excluded_events.tsv" in files:
            data_exclusions.extend(read_table(files["audit/excluded_events.tsv"]))
    require(len({row["script_sha256"] for row in receipts}) == 1, "Mixed analysis script versions")
    require(len({tuple(row["channel_names"]) for row in receipts}) == 1 and
            len({row["sampling_frequency_hz"] for row in receipts}) == 1,
            "Participant analyses do not share audited channel coordinates/sampling frequency")
    joined = join_verified_sessions(behavior, eeg_sessions, mapping)
    require(len(joined) == len(subjects)*len(sessions), "Subject/session join count changed")
    metrics = ["mean_run_hit_percent", "CSP_BA_percent", "mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB",
               "mu_rest_power_uV2", "mu_MI_power_uV2", "beta_rest_power_uV2", "beta_MI_power_uV2"]
    statistics, changes, individuals, matrices = participant_statistics(
        joined, subjects, sessions, metrics, config["seed"], config["bootstrap_subject_repetitions"])
    matching_stats = []
    for variant in ("all_six_runs", "qc_common_four_runs"):
        selected = [row for row in matching if row["variant"] == variant]
        stats, _, _, _ = participant_statistics(selected, subjects, sessions,
            ["AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance",
             "mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB"], config["seed"], config["bootstrap_subject_repetitions"])
        matching_stats.extend(dict(row, variant=variant) for row in stats)
    # Validate everything before making this new output directory. No partial prior
    # output is rewritten if data/source integrity fails.
    output.mkdir(parents=True)
    write_table(output / "participant_session_join.tsv", joined)
    write_table(output / "cohort_session_statistics.tsv", statistics)
    write_table(output / "participant_first_last_changes.tsv", individuals)
    write_table(output / "cohort_paired_changes.tsv", changes)
    write_table(output / "spectral_reference_QC_sensitivity.tsv", spectral)
    write_table(output / "participant_matched_geometry.tsv", matching)
    write_table(output / "cohort_matched_statistics.tsv", matching_stats)
    plot_results(output, subjects, sessions, matrices, changes, individuals, matching)
    summary = {"status": "actual_audited_first_ten_ID_cohort_exploratory", "synthetic": False,
               "subjects": subjects, "subject_map": mapping, "participants": len(subjects),
               "sessions": len(joined), "runs": sum(row["n_EEG_runs"] for row in joined),
               "trials": sum(row["n_EEG_trials"] for row in joined),
               "source_events": sum(row["n_EEG_source_events"] for row in joined),
               "excluded_source_events_n": sum(row["n_EEG_excluded_events"] for row in joined),
               "excluded_source_events": data_exclusions,
               "source_class_counts": {"rest": sum(row["n_source_rest"] for row in joined),
                    "right_hand": sum(row["n_source_MI"] for row in joined)},
               "class_counts": {"rest": sum(row["n_rest"] for row in joined), "right_hand": sum(row["n_MI"] for row in joined)},
               "qc_flags_retained_in_primary": sum(row["n_qc_flagged"] for row in joined),
               "constant_prediction_sessions_by_session": dict(Counter(row["session"] for row in joined if row["CSP_constant_prediction"] is True)),
               "constant_prediction_participants": [s for s in subjects if any(row["subject"] == s and row["CSP_constant_prediction"] is True for row in joined)],
               "unavailable_decoder_sessions": [{"subject": row["subject"], "session": row["session"]}
                    for row in joined if row["CSP_status"] != "available"],
               "scientific_failures": scientific_failures,
               "scientific_failure_records_n": len(scientific_failures),
               "metric_units": {"mean_run_hit_percent": "percent; changes in percentage points",
                    "CSP_BA_percent": "percent; changes in percentage points",
                    "CSP_conditional_run_CI95_percent": "percent; conditional within-participant run clusters",
                    "spectral_task_contrast": "dB; differences of equal-run mean log10 task-window power",
                    "arithmetic_ROI_power": "microvolt squared (uV2)"},
               "behavior_dictionary_syntax": dictionary_status, "behavior_source_subjects": 19,
               "behavior_analyzed_EEG_linked_subjects_only": len(subjects),
               "source_selection": config["selection"], "pilot_previously_seen": config["pilot_subject_previously_observed"],
               "behavior_grain": "verified_subject_session_unweighted_mean_of_six_reported_percentages",
               "score_run_order_denominator_trial_outcomes": "unresolved_no_broadcast",
               "session_statistics": statistics, "paired_changes": changes,
               "matching_availability": [{"subject": s, "variant": variant,
                    "status": next(row["status"] for row in matching if row["subject"] == s and row["variant"] == variant),
                    "error": next(row["error"] for row in matching if row["subject"] == s and row["variant"] == variant)}
                    for s in subjects for variant in ("all_six_runs", "qc_common_four_runs")],
               "interpretation": "observational spectral/geometry/decoder contrasts; no causal neural-learning or skill-retention conclusion"}
    write_json(output / "cohort_summary.json", summary)
    outputs = {path.relative_to(output).as_posix(): file_sha256(path) for path in sorted(output.rglob("*")) if path.is_file()}
    write_json(output / "summary_receipt.json", {"status": "actual_data_summary_completed", "synthetic": False,
               "config_sha256": file_sha256(config_path), "script_sha256": file_sha256(Path(__file__)),
               "input_sha256": {key: {"path": str(path.resolve()), "sha256": file_sha256(path)} for key, path in inputs.items()},
               "output_sha256": outputs, "provenance": collect_provenance(config["seed"], ROOT),
               "duration_seconds": time.monotonic()-started,
               "bootstrap_unit": "whole participant", "source_reference_and_QC_sensitivity_saved": True,
               "new_EEG_downloads": False, "new_model_fits": False, "figures_native_rendered": True,
               "figure_visual_inspection": "pending_view_image_review"})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.config, args.analysis_root, args.audit_root, args.output)
    print(json.dumps({"output": str(args.output), "participants": result["participants"], "trials": result["trials"]}))


if __name__ == "__main__":
    main()
