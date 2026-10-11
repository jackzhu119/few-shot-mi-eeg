"""Software fixtures for participant statistics and cohort evidence integrity."""
import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_netbci_cohort import (
    equal_run_spectral,
    load_participant,
    participant_statistics,
    summarize_matching,
    verify_event_selection,
    verify_hashes,
    verify_predictions,
)


def trajectory_rows(values, subjects=("a", "b", "c"), sessions=("01", "02", "03", "04")):
    return [{"subject": subject, "session": session, "metric": values[i][j],
             "n_EEG_trials": 10000 if i == 0 else 1}
            for i, subject in enumerate(subjects) for j, session in enumerate(sessions)]


def test_paired_bootstrap_preserves_subject_pairing_and_ignores_trial_weights():
    rows = trajectory_rows([[100, 102, 103, 104], [0, 2, 3, 4], [50, 52, 53, 54]])
    summary, changes, individual, matrices = participant_statistics(
        rows[::-1], ["a", "b", "c"], ["01", "02", "03", "04"], ["metric"], 42, 1000)
    assert [row["mean"] for row in summary] == [50, 52, 53, 54]
    assert changes[0]["mean_change"] == 4
    assert changes[0]["subject_bootstrap_CI95_low"] == 4
    assert changes[0]["subject_bootstrap_CI95_high"] == 4
    assert changes[0]["n_paired_subjects"] == 3
    assert [row["subject"] for row in individual] == ["a", "b", "c"]
    assert matrices["metric"][0, 0] == 100


def test_bootstrap_matches_an_independent_participant_trajectory_oracle():
    values = [[10, 20, 40, 30], [20, 30, 20, 15], [40, 30, 40, 50]]
    summary, changes, _, _ = participant_statistics(
        trajectory_rows(values), ["a", "b", "c"], ["01", "02", "03", "04"], ["metric"], 8, 400)
    rng = np.random.default_rng(8)
    draws = rng.integers(0, 3, (400, 3))
    first_means = [sum(values[i][0] for i in draw) / 3 for draw in draws]
    paired_means = [sum(values[i][-1] - values[i][0] for i in draw) / 3 for draw in draws]
    assert [summary[0]["subject_bootstrap_CI95_low"], summary[0]["subject_bootstrap_CI95_high"]] == pytest.approx(
        np.quantile(first_means, [.025, .975]))
    assert [changes[0]["subject_bootstrap_CI95_low"], changes[0]["subject_bootstrap_CI95_high"]] == pytest.approx(
        np.quantile(paired_means, [.025, .975]))
    assert changes[0]["n_increased"] == 2 and changes[0]["n_decreased"] == 1


def test_missing_metrics_retain_all_subjects_and_require_both_endpoints_for_pairing():
    rows = trajectory_rows([[1, 2, 3, 5], [None, 2, 3, 500], [10, 20, 30, 12]])
    summary, changes, individual, _ = participant_statistics(
        rows, ["a", "b", "c"], ["01", "02", "03", "04"], ["metric", "absent"], 42, 500)
    assert [row["n_available_subjects"] for row in summary[:4]] == [2, 3, 3, 3]
    assert changes[0]["mean_change"] == 3
    assert changes[0]["n_paired_subjects"] == 2
    assert changes[0]["unavailable_subjects"] == "b"
    assert individual[1]["last_session_value"] == 500
    assert individual[1]["last_minus_first"] is None
    assert individual[1]["status"] == "unavailable_retained"
    assert changes[1]["mean_change"] is None
    assert changes[1]["subject_bootstrap_CI95_low"] is None
    assert all(row["mean"] is None for row in summary[4:])


@pytest.mark.parametrize("error", ["duplicate_key", "missing_key", "unexpected_subject", "nonfinite"])
def test_participant_statistics_rejects_invalid_identity_or_silent_nonfinite_metrics(error):
    rows = trajectory_rows([[1, 2, 3, 4]] * 3)
    if error == "duplicate_key":
        rows.append(rows[0].copy())
    elif error == "missing_key":
        rows.pop()
    elif error == "unexpected_subject":
        rows[-1]["subject"] = "unverified"
    else:
        rows[-1]["metric"] = np.nan
    with pytest.raises(ValueError):
        participant_statistics(rows, ["a", "b", "c"], ["01", "02", "03", "04"], ["metric"], 42, 50)


def spectral_trials():
    rows = []
    for run, rest, imagery in (("01", [1, 9], [4]), ("02", [100] * 4, [400] * 2)):
        for label, powers in (("rest", rest), ("right_hand", imagery)):
            rows.extend({"session": "01", "run": run, "label": label, "qc_flag": "False",
                         "mu_ROI_V2": power * 1e-12, "beta_ROI_V2": power * 1e-12,
                         "mu_source_reference_ROI_V2": power * 2e-12,
                         "beta_source_reference_ROI_V2": power * 2e-12} for power in powers)
    return rows


def test_power_contrast_uses_equal_run_mean_of_trial_logs_and_correct_voltage_units():
    row = equal_run_spectral(spectral_trials(), ["01"], ["01", "02"])[0]
    # Geometric trial mean for run-01 rest is 3 uV2, its arithmetic mean is 5 uV2.
    expected_dB = 5 * np.log10((4 * 400) / (3 * 100))
    assert row["MI_minus_rest_log_power_dB"] == pytest.approx(expected_dB)
    assert row["rest_equal_run_arithmetic_power_uV2"] == pytest.approx(52.5)
    assert row["MI_equal_run_arithmetic_power_uV2"] == pytest.approx(202)
    assert row["n_rest"] == 6 and row["n_MI"] == 3
    source = equal_run_spectral(spectral_trials(), ["01"], ["01", "02"], reference="source_reference")[0]
    assert source["rest_equal_run_arithmetic_power_uV2"] == pytest.approx(105)
    assert source["MI_minus_rest_log_power_dB"] == pytest.approx(expected_dB)


def test_missing_qc_spectral_cell_marks_contrast_unavailable_without_reducing_runs():
    rows = spectral_trials()
    for row in rows:
        if row["run"] == "02" and row["label"] == "right_hand":
            row["qc_flag"] = "True"
    original = equal_run_spectral(rows, ["01"], ["01", "02"])[0]
    clean = equal_run_spectral(rows, ["01"], ["01", "02"], exclude_flagged=True)[0]
    assert original["status"] == "available"
    assert clean["status"] == "unavailable_missing_cell"
    assert clean["missing_cells"] == "01/02/right_hand"
    assert clean["runs"] == "01,02"
    assert clean["MI_minus_rest_log_power_dB"] is None
    assert clean["MI_equal_run_arithmetic_power_uV2"] is None
    assert clean["rest_equal_run_arithmetic_power_uV2"] == pytest.approx(52.5)


def fixture_config():
    return {"session_order": ["01", "02", "03", "04"],
            "expected_runs": ["01", "02", "03", "04", "05", "06"],
            "source_train_runs": ["01", "02", "03", "04"], "source_query_runs": ["05", "06"],
            "later_query_runs": ["01", "02", "03", "04", "05", "06"],
            "qc_matched_runs": ["03", "04", "05", "06"], "matched_repetitions": 2,
            "matched_trials_per_class_per_run": 12}


def prediction_fixture():
    config = fixture_config()
    events, predictions, decoder = [], [], []
    for position, session in enumerate(config["session_order"]):
        role = ("source_reference_query" if position == 0 else
                "validation_no_selection" if position == 1 else "test_exploratory")
        n_runs = 2 if position == 0 else 6
        for run in config["expected_runs"]:
            for label in ("rest", "right_hand"):
                row = {"subject": "software_fixture", "session": session, "run": run,
                       "trial_id": f"fixture/{session}/{run}/{label}", "label": label}
                events.append(row)
                if position > 0 or run in config["source_query_runs"]:
                    predictions.append({key: row[key] for key in ("subject", "session", "run", "trial_id")} |
                                       {"true_label": label, "prediction": "rest", "role": role})
        decoder.append({"subject": "software_fixture", "session": session, "role": role,
                        "decoder": "CSP_LDA", "train_n": 8, "participant_n": 1,
                        "n_runs": n_runs, "n_rest": n_runs, "n_right_hand": n_runs,
                        "confusion_matrix_rest_right_hand": [[n_runs, 0], [n_runs, 0]],
                        "n_test": 2 * n_runs, "constant_prediction": True, "balanced_accuracy": .5,
                        "conditional_run_bootstrap_CI95": [.5, .5],
                        "n_qc_flagged_query": 0, "qc_unflagged_n": 2 * n_runs, "qc_unflagged_BA": .5})
    return predictions, decoder, events, config


def test_valid_constant_predictions_are_retained_and_independently_recomputed():
    predictions, decoder, events, config = prediction_fixture()
    trials = [dict(row, qc_flag="False") for row in events]
    verify_predictions(predictions, decoder, events, config, trials)
    assert len(predictions) == 40
    assert all(score["constant_prediction"] for score in decoder)


@pytest.mark.parametrize("error", ["extra_session", "pilot_later_run_omission", "duplicate_prediction",
                                  "wrong_subject", "wrong_label", "wrong_role", "score_identity",
                                  "score_run_count", "score_class_count", "score_BA", "score_confusion",
                                  "constant_flag", "training_count", "CI_percent_not_fraction", "QC_count"])
def test_prediction_integrity_rejects_identity_partition_or_metric_mismatches(error):
    predictions, decoder, events, config = prediction_fixture()
    if error == "extra_session":
        predictions.append(dict(predictions[0], session="99", trial_id="unverified/trial"))
    elif error == "pilot_later_run_omission":
        predictions = [row for row in predictions if not (row["session"] == "02" and row["run"] == "01")]
    elif error == "duplicate_prediction":
        predictions.append(predictions[0].copy())
    elif error in ("wrong_subject", "wrong_label", "wrong_role"):
        field = {"wrong_subject": "subject", "wrong_label": "true_label", "wrong_role": "role"}[error]
        predictions[0][field] = "incorrect"
    else:
        field, value = {"score_identity": ("subject", "wrong_subject"), "score_run_count": ("n_runs", 6),
                        "score_class_count": ("n_rest", 4), "score_BA": ("balanced_accuracy", .75),
                        "score_confusion": ("confusion_matrix_rest_right_hand", [[1, 1], [2, 0]]),
                        "constant_flag": ("constant_prediction", False), "training_count": ("train_n", 9),
                        "CI_percent_not_fraction": ("conditional_run_bootstrap_CI95", [50, 50]),
                        "QC_count": ("n_qc_flagged_query", 2)}[error]
        decoder[0][field] = value
    trials = [dict(row, qc_flag="False") for row in events]
    with pytest.raises(ValueError):
        verify_predictions(predictions, decoder, events, config, trials)


def test_output_hashes_detect_modified_and_unaccounted_evidence(tmp_path):
    path = tmp_path / "events.tsv"
    path.write_bytes(b"verified software fixture\n")
    receipt = {"outputs": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}
    verify_hashes(tmp_path, receipt, [path.name])
    path.write_bytes(b"changed trial identity\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_hashes(tmp_path, receipt, [path.name])
    with pytest.raises(ValueError, match="Missing output hash"):
        verify_hashes(tmp_path, receipt, ["undeclared.tsv"])


def matching_fixture():
    config = fixture_config()
    geometry, spectral = [], []
    statuses = [{"variant": "all_six_runs", "status": "available", "runs": config["expected_runs"], "repetitions": 2},
                {"variant": "qc_common_four_runs", "status": "unavailable", "runs": config["qc_matched_runs"],
                 "error": "preset cell has 11 trials; 12 required", "preset_not_relaxed": True}]
    for session in config["session_order"]:
        for repetition in range(2):
            identity = {"subject": "software_fixture", "session": session, "variant": "all_six_runs",
                        "repetition": str(repetition), "n_matched": "144"}
            geometry.append(dict(identity, AIRM_to_session01=repetition,
                                 within_session_run_AIRM_mean=2 + repetition, PCA_subspace_distance=.5))
            for band in ("mu", "beta"):
                spectral.append(dict(identity, band=band, MI_minus_rest_log_power_dB=-1 - repetition))
    return geometry, spectral, statuses, config


def test_matching_averages_within_subject_and_retains_unavailable_variants():
    geometry, spectral, statuses, config = matching_fixture()
    rows = summarize_matching("software_fixture", geometry, spectral, statuses, config)
    assert len(rows) == 8
    assert rows[0]["AIRM_to_session01"] == .5
    assert rows[0]["mu_MI_minus_rest_dB"] == -1.5
    assert rows[0]["n_subsample_repetitions"] == 2
    assert rows[0]["n_matched_trials_per_repetition"] == 144
    assert all(row["status"] == "unavailable" and row["AIRM_to_session01"] is None
               and row["n_subsample_repetitions"] == 0 for row in rows[4:])


@pytest.mark.parametrize("error", ["missing_spectral_cell", "duplicate_spectral_cell", "unexpected_repetition",
                                  "trial_count", "wrong_participant", "missing_variant", "partial_unavailable",
                                  "nonfinite", "relaxed_preset"])
def test_matched_result_integrity_requires_every_preset_cell_or_explicit_failure(error):
    geometry, spectral, statuses, config = matching_fixture()
    if error == "missing_spectral_cell":
        spectral.pop()
    elif error == "duplicate_spectral_cell":
        spectral[-1] = copy.deepcopy(spectral[-2])
    elif error == "unexpected_repetition":
        geometry[-1]["repetition"] = "2"
    elif error == "trial_count":
        geometry[0]["n_matched"] = "142"
    elif error == "wrong_participant":
        spectral[0]["subject"] = "unverified"
    elif error == "missing_variant":
        statuses.pop()
    elif error == "partial_unavailable":
        spectral.append(dict(spectral[0], variant="qc_common_four_runs"))
    elif error == "nonfinite":
        spectral[0]["MI_minus_rest_log_power_dB"] = "nan"
    else:
        statuses[-1]["preset_not_relaxed"] = False
    with pytest.raises(ValueError):
        summarize_matching("software_fixture", geometry, spectral, statuses, config)


def participant_evidence_fixture(tmp_path, decoder_failed=False):
    """Only temporary software evidence; no EEG signal or scientific fit is created."""
    predictions, decoder, events, config = prediction_fixture()
    config["expected_sfreq_hz"] = 250
    config_path = tmp_path / "software_config.json"
    config_path.write_text(json.dumps(config))
    analysis_root, audit_root = tmp_path / "analysis", tmp_path / "audit"
    analysis_dir, audit_dir = analysis_root / "software_fixture", audit_root / "software_fixture"
    analysis_dir.mkdir(parents=True)
    audit_dir.mkdir(parents=True)

    def save_json(path, value):
        path.write_text(json.dumps(value))

    def save_table(path, rows):
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    roles, trials = {}, []
    for event in events:
        event["original_subject"] = "original_software_fixture"
        event["source_file"] = "software_fixture_no_EEG.edf"
        event["duration_s"] = "5.0"
        event["fixed_window_eligible"] = True
        event["exclusion_reason"] = ""
        role = ("source_train" if event["run"] in config["source_train_runs"] else "source_reference_query") if event["session"] == "01" else (
            "validation_no_selection" if event["session"] == "02" else "test_exploratory")
        roles[event["trial_id"]] = role
        power = 1e-12 if event["label"] == "rest" else 4e-12
        trials.append(dict(event, analysis_role=role, qc_flag="False",
                           mu_ROI_V2=power, beta_ROI_V2=power,
                           mu_source_reference_ROI_V2=power, beta_source_reference_ROI_V2=power))
    save_table(audit_dir / "events.tsv", events)
    save_table(audit_dir / "source_events.tsv", events)
    with (audit_dir / "excluded_events.tsv").open("w", newline="") as stream:
        csv.DictWriter(stream, list(events[0]), delimiter="\t").writeheader()
    save_table(audit_dir / "run_inventory.tsv", [{"subject": "software_fixture", "n_runs": 24}])
    names = ["C3", "Cz", "C4"]
    adapter = {"synthetic": False, "subject": "software_fixture", "original_subject": "original_software_fixture",
               "signal_unit": "V", "trial_count": 48, "channel_names": names, "sampling_frequency_hz": 250,
               "total_source_trials": 48, "excluded_trial_count": 0,
               "epochs_sha256": "temporary_software_fixture_epochs_identity",
               "metadata_sha256": "temporary_software_fixture_metadata_identity"}
    save_json(audit_dir / "adapter_receipt.json", adapter)
    save_json(audit_dir / "audit.json", {
        "synthetic": False, "summary": {"subject": "software_fixture", "all_checks_pass": True, "total_trials": 48,
            "total_source_trials": 48, "excluded_trial_count": 0, "source_class_counts": {"rest": 24, "right_hand": 24},
            "class_counts": {"rest": 24, "right_hand": 24}, "excluded_class_counts": {}},
        "upstream_mapping": {"derivative_subject": "software_fixture", "actual_headers_hash_verified": 24,
                             "declared_original_headers": 24, "original_subject": "original_software_fixture"},
        "output_artifact_sha256": {name: sha(audit_dir / name) for name in
                                  ("adapter_receipt.json", "events.tsv", "source_events.tsv", "excluded_events.tsv", "run_inventory.tsv")}})
    save_table(analysis_dir / "trial_features.tsv", trials)
    save_table(analysis_dir / "event_inventory.tsv", [dict(event, analysis_role=roles[event["trial_id"]]) for event in events])
    partitions = {role: [event["trial_id"] for event in events if roles[event["trial_id"]] == role]
                  for role in ("source_train", "source_reference_query", "validation_no_selection", "test_exploratory")}
    save_json(analysis_dir / "partitions.json", {"subject": "software_fixture", "partition_trial_ids": partitions,
        "all_trials_assigned_once": True, "validation_selection_performed": False})
    save_json(analysis_dir / "transform_audit.json", {"source_train_trial_ids": partitions["source_train"],
        "scaler_fit_source_only": True, "reference_PCA_fit_source_only": True,
        "target_PCA_descriptive_only": True, "target_prediction_transforms_fitted": False, "channel_names": names})
    statuses = [{"variant": variant, "status": "unavailable", "runs": runs,
                 "error": "preset cell has 1 trial; 12 required", "preset_not_relaxed": True}
                for variant, runs in (("all_six_runs", config["expected_runs"]), ("qc_common_four_runs", config["qc_matched_runs"]))]
    save_json(analysis_dir / "matched_variants_status.json", statuses)
    failures = [{"scope": "matched_geometry", **status} for status in statuses]
    if decoder_failed:
        save_json(analysis_dir / "decoder_results.json", [])
        failures.append({"scope": "CSP_LDA_fit_or_query", "type": "software_fixture_failure", "message": "fixture"})
    else:
        save_json(analysis_dir / "decoder_results.json", decoder)
        save_table(analysis_dir / "predictions.tsv", predictions)
        failures.extend({"scope": "CSP_LDA_query", "session": session, "type": "constant_prediction"}
                        for session in config["session_order"])
        model_path = analysis_dir / "csp_lda.pkl"
        # Opaque bytes are hashed; summary must never unpickle input model evidence.
        model_path.write_bytes(b"opaque software fixture model state")
        save_json(analysis_dir / "CSP_LDA_model_audit.json", {"query_state_unchanged": True,
            "prediction_replay_exact": True, "parameter_sha256_before": sha(model_path),
            "parameter_sha256_after": sha(model_path), "fit_calls": 1,
            "source_train_trial_ids": partitions["source_train"], "source_train_n": 8,
            "parameters_predefined_no_target_selection": True, "target_transforms_fitted_for_prediction": False})
    save_json(analysis_dir / "failures.json", failures)
    save_json(analysis_dir / "analysis_receipt.json", {"synthetic": False, "subject": "software_fixture",
        "status": "completed_with_scientific_failures", "config_sha256": sha(config_path),
        "bundle_sha256": adapter["epochs_sha256"], "metadata_sha256": adapter["metadata_sha256"],
        "trials": 48, "channel_names": names, "sampling_frequency_hz": 250, "failures_n": len(failures),
        "outputs": {path.name: sha(path) for path in analysis_dir.iterdir()}})
    return config_path, config, analysis_root, audit_root


@pytest.mark.parametrize("decoder_failed", [False, True])
def test_load_participant_keeps_constant_or_failed_decoder_and_failed_matching(tmp_path, decoder_failed):
    args = participant_evidence_fixture(tmp_path, decoder_failed)
    original, sessions, sensitivity, matching, _, analysis = load_participant("software_fixture", *args)
    assert original == "original_software_fixture"
    assert len(sessions) == 4 and len(sensitivity) == 48 and len(matching) == 8
    assert sum(row["n_EEG_trials"] for row in sessions) == 48
    assert all(row["status"] == "unavailable" for row in matching)
    if decoder_failed:
        assert all(row["CSP_BA_percent"] is None and row["CSP_status"] == "unavailable_retained" for row in sessions)
        assert analysis["failures_n"] == 3
    else:
        assert all(row["CSP_BA_percent"] == 50 and row["CSP_constant_prediction"] for row in sessions)
        assert all(json.loads(row["CSP_conditional_run_CI95_percent"]) == [50, 50] for row in sessions)
        assert analysis["failures_n"] == 6


@pytest.mark.parametrize("artifact", ["partitions.json", "transform_audit.json", "CSP_LDA_model_audit.json",
                                     "failures.json", "matched_variants_status.json"])
def test_rehashed_semantically_wrong_source_or_failure_evidence_is_rejected(tmp_path, artifact):
    args = participant_evidence_fixture(tmp_path)
    analysis_dir = args[2] / "software_fixture"
    path = analysis_dir / artifact
    value = json.loads(path.read_text())
    if artifact == "partitions.json":
        value["partition_trial_ids"]["source_train"][0] = "target_trial_wrongly_fit"
    elif artifact in ("transform_audit.json", "CSP_LDA_model_audit.json"):
        value["source_train_trial_ids"][0] = "target_trial_wrongly_fit"
    elif artifact == "failures.json":
        value[-1]["type"] = "unrelated"
    else:
        value[0]["preset_not_relaxed"] = False
    path.write_text(json.dumps(value))
    receipt_path = analysis_dir / "analysis_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["outputs"][artifact] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        load_participant("software_fixture", *args)


def selection_fixture():
    _, _, events, _ = prediction_fixture()
    source = [dict(event, original_subject="original_software_fixture", source_file="fixture.edf",
                   duration_s="5.0") for event in events]
    source[0]["duration_s"] = "2.968"
    excluded = [dict(source[0], exclusion_reason="shorter_than_fixed_5_second_window")]
    summary = {"total_source_trials": 48, "total_trials": 47, "excluded_trial_count": 1,
               "source_class_counts": {"rest": 24, "right_hand": 24},
               "class_counts": {"rest": 23, "right_hand": 24}, "excluded_class_counts": {"rest": 1}}
    return source, source[1:], excluded, summary


def test_source_event_selection_preserves_real_short_trial_without_padding_or_losing_identity():
    source, eligible, excluded, summary = selection_fixture()
    verify_event_selection(source, eligible, excluded, "software_fixture", "original_software_fixture", summary)
    assert len(source) == len(eligible) + len(excluded)
    assert excluded[0]["duration_s"] == "2.968"
    assert excluded[0]["trial_id"] == source[0]["trial_id"]
    assert all(row["duration_s"] == "5.0" for row in eligible)


@pytest.mark.parametrize("error", ["overlap", "lost_source", "wrong_original", "wrong_duration", "wrong_count", "wrong_class_count"])
def test_source_eligibility_requires_disjoint_exhaustive_identity_and_count_evidence(error):
    source, eligible, excluded, summary = copy.deepcopy(selection_fixture())
    if error == "overlap":
        eligible.append(source[0].copy())
    elif error == "lost_source":
        excluded = []
    elif error == "wrong_original":
        excluded[0]["original_subject"] = "other_participant"
    elif error == "wrong_duration":
        excluded[0]["duration_s"] = "5.0"
    elif error == "wrong_count":
        summary["total_source_trials"] = 50
    else:
        summary["excluded_class_counts"] = {"right_hand": 1}
    with pytest.raises(ValueError):
        verify_event_selection(source, eligible, excluded, "software_fixture", "original_software_fixture", summary)
