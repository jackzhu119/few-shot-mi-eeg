"""Kumar frozen-protocol safeguards on synthetic software-validation fixtures only.

These checks do not read real EEG, fit decoders, or compute decoding performance.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from learning_preserving_bci.datasets.kumar import (
    allowed_fit_trial_ids,
    preprocess_epoch,
    role_for,
    validate_split_trials,
)

ROOT = Path(__file__).resolve().parents[1]
HASH_FIELDS = ("raw_window_numeric_sha256", "processed_window_numeric_sha256")
COMPONENTS = ("csp", "lda", "scaler", "pca", "normalizer", "riemann_reference")
METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda")


@pytest.fixture(scope="module")
def preparation():
    spec = importlib.util.spec_from_file_location(
        "prepare_kumar_experiment", ROOT / "scripts/prepare_kumar_experiment.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def config():
    return json.loads((ROOT / "configs/kumar_cross_session_20261012.json").read_text())


def synthetic_trial(config, *, subject="sub-1", session="ses-0", run="run-0", row=1,
                    sample_count=2560):
    """An explicit source identity with no claim to be real EEG evidence."""
    identity = f"{subject}/{session}/{run}/row-{row}"
    trial = {
        "trial_id": identity,
        "subject": subject,
        "session": session,
        "run": run,
        "acquisition_time_utc": (
            f"2024-01-{int(session.split('-')[1]) + 1:02d}"
            f"T{int(run.split('-')[1]):02d}:00:00+00:00"
        ),
        "source_row": row,
        "source_file": f"{subject}/{session}/{subject}_{session}_{run}_eeg.edf",
        "start_sample": (row - 1) * 2560,
        "stop_sample_exclusive": (row - 1) * 2560 + sample_count,
        "sample_count": sample_count,
        "duration_seconds": sample_count / 512,
        "role": role_for(session, run, config),
        "cohort": "development" if subject in config["development_subjects"] else "final_test",
        "included": sample_count == 2560,
        "label": "left_hand" if row % 2 else "right_hand",
        "synthetic": True,
        "status": "software_validation_only",
    }
    for field in HASH_FIELDS:
        trial[field] = hashlib.sha256(f"synthetic/{field}/{identity}".encode()).hexdigest()
    if not trial["included"]:
        trial.pop("processed_window_numeric_sha256")
    return trial


@pytest.fixture
def trials(config):
    rows = [synthetic_trial(config, row=1), synthetic_trial(config, row=2)]
    rows.extend(synthetic_trial(config, run=run) for run in ("run-2", "run-3"))
    for session in config["split"]["target_sessions"]:
        rows.extend(synthetic_trial(config, session=session, run=run)
                    for run in ("run-0", "run-1"))
    rows.append(synthetic_trial(config, subject="sub-2"))
    rows.append(synthetic_trial(config, subject="sub-2", session="ses-5", sample_count=2559))
    return rows


@pytest.fixture
def budget_config(config):
    config["subjects"] = ["sub-1"]
    return config


@pytest.fixture
def budget_trials(budget_config):
    rows = [synthetic_trial(budget_config, run=run, row=row)
            for run in ("run-0", "run-2", "run-3") for row in (1, 2)]
    for session in budget_config["split"]["target_sessions"]:
        rows.extend(synthetic_trial(budget_config, session=session, row=row)
                    for row in range(1, 21))
        rows.extend(synthetic_trial(budget_config, session=session, run="run-1", row=row)
                    for row in (1, 2))
    return rows


def test_preprocessing_is_epoch_local_deterministic_and_does_not_mutate_input(config):
    rng = np.random.default_rng(42)
    epoch = rng.normal(scale=12e-6, size=(22, 2560))
    original = epoch.copy()
    first = preprocess_epoch(epoch, config)
    preprocess_epoch(rng.normal(scale=2e-3, size=epoch.shape), config)
    repeated = preprocess_epoch(epoch, config)

    assert first.shape == (22, 640)
    assert first.dtype == np.float32
    assert np.isfinite(first).all()
    np.testing.assert_array_equal(first, repeated)
    np.testing.assert_array_equal(epoch, original)
    np.testing.assert_allclose(first.mean(axis=0), 0, atol=1e-12, rtol=0)


def test_preprocessing_preserves_volts_and_removes_shared_channel_reference(config):
    time = np.arange(2560) / 512
    epoch = np.zeros((22, 2560))
    epoch[0] = 10e-6 * np.sin(2 * np.pi * 12 * time)
    processed = preprocess_epoch(epoch, config)

    # An in-band 10-microvolt signal must remain on a volts scale after reference.
    peak_volts = np.abs(processed[0, 128:-128]).max()
    assert 8e-6 < peak_volts < 11e-6
    common_reference = 50e-6 * np.sin(2 * np.pi * 18 * time) + 100e-6
    shifted = preprocess_epoch(epoch + common_reference, config)
    np.testing.assert_allclose(shifted, processed, atol=1e-12, rtol=1e-6)
    np.testing.assert_allclose(processed.mean(axis=0), 0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        preprocess_epoch(np.broadcast_to(common_reference, epoch.shape), config),
        np.zeros((22, 640), dtype=np.float32),
        atol=1e-18,
        rtol=0,
    )


def test_preprocessing_attenuates_frequencies_outside_frozen_band(config):
    time = np.arange(2560) / 512
    rms_volts = {}
    for frequency in (2, 12, 80):
        epoch = np.zeros((22, 2560))
        epoch[0] = 10e-6 * np.sin(2 * np.pi * frequency * time)
        interior = preprocess_epoch(epoch, config)[0, 128:-128]
        rms_volts[frequency] = np.sqrt(np.square(interior).mean())
    assert rms_volts[2] < 0.01 * rms_volts[12]
    assert rms_volts[80] < 0.01 * rms_volts[12]


@pytest.mark.parametrize("shape", [(21, 2560), (23, 2560), (22, 2559), (22, 2561)])
def test_preprocessing_rejects_partial_padding_and_changed_channel_count(config, shape):
    with pytest.raises(ValueError, match="exact 5-second"):
        preprocess_epoch(np.zeros(shape), config)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_preprocessing_rejects_nonfinite_samples(config, value):
    epoch = np.zeros((22, 2560))
    epoch[3, 1000] = value
    with pytest.raises(ValueError, match="Nonfinite epoch"):
        preprocess_epoch(epoch, config)


@pytest.mark.parametrize("field,value", [
    ("window_seconds", 4.0),
    ("input_sfreq", 500.0),
    ("output_sfreq", 256.0),
    ("band_hz", [4.0, 40.0]),
])
def test_preprocessing_rejects_unreviewed_numerical_settings(config, field, value):
    config["preprocessing"][field] = value
    with pytest.raises(ValueError, match="Unreviewed preprocessing"):
        preprocess_epoch(np.zeros((22, 2560)), config)


def test_split_accepts_touching_windows_and_retains_partial_identity(config, trials):
    receipt = validate_split_trials(trials, config)
    assert receipt["trial_identity_unique"]
    assert receipt["source_windows_disjoint"]
    assert receipt["whole_runs_assigned_single_role"]
    assert receipt["cohorts_disjoint"]
    assert receipt["numerical_duplicate_groups"] == {field: [] for field in HASH_FIELDS}
    assert trials[0]["stop_sample_exclusive"] == trials[1]["start_sample"]
    partial = trials[-1]
    assert not partial["included"] and partial["sample_count"] == 2559
    assert "processed_window_numeric_sha256" not in partial


def test_split_rejects_repeated_trial_identity_even_across_files(config, trials):
    trials[-2]["trial_id"] = trials[0]["trial_id"]
    with pytest.raises(ValueError, match="Duplicate trial identity"):
        validate_split_trials(trials, config)


def test_split_rejects_one_sample_overlap_without_relying_on_hashes(config, trials):
    trials[1]["start_sample"] -= 1
    trials[1]["stop_sample_exclusive"] -= 1
    with pytest.raises(ValueError, match="Overlapping source windows"):
        validate_split_trials(trials, config, require_hashes=False)


def test_split_rejects_inconsistent_sample_boundaries(config, trials):
    trials[0]["stop_sample_exclusive"] += 1
    with pytest.raises(ValueError, match="Window sample identity"):
        validate_split_trials(trials, config)


@pytest.mark.parametrize("index,included", [(0, False), (-1, True)])
def test_split_rejects_changed_full_or_partial_eligibility(config, trials, index, included):
    trials[index]["included"] = included
    with pytest.raises(ValueError, match="Partial eligibility mismatch"):
        validate_split_trials(trials, config)


def test_split_rejects_duration_change_even_at_full_sample_count(config, trials):
    trials[0]["duration_seconds"] = 4.999
    with pytest.raises(ValueError, match="Partial eligibility mismatch"):
        validate_split_trials(trials, config)


@pytest.mark.parametrize("index,role", [(0, "source_query"), (4, "target_query")])
def test_split_rejects_role_reassignment(config, trials, index, role):
    trials[index]["role"] = role
    with pytest.raises(ValueError, match="Frozen role mismatch"):
        validate_split_trials(trials, config)


def test_split_rejects_source_file_spanning_frozen_roles(config, trials):
    trials[2]["source_file"] = trials[0]["source_file"]
    trials[2]["start_sample"] = trials[1]["stop_sample_exclusive"]
    trials[2]["stop_sample_exclusive"] = trials[2]["start_sample"] + 2560
    with pytest.raises(ValueError, match="Run crosses split roles"):
        validate_split_trials(trials, config)


def test_role_assignment_rejects_unfrozen_session_and_ambiguous_source_run(config):
    with pytest.raises(ValueError, match="Unfrozen session"):
        role_for("ses-99", "run-0", config)
    with pytest.raises(ValueError, match="exactly one frozen role"):
        role_for("ses-0", "run-99", config)
    config["split"]["source_query_runs"].append("run-0")
    with pytest.raises(ValueError, match="exactly one frozen role"):
        role_for("ses-0", "run-0", config)


@pytest.mark.parametrize("cohort_change", ["overlap", "missing"])
def test_split_rejects_cohort_overlap_or_missing_subject(config, trials, cohort_change):
    if cohort_change == "overlap":
        config["development_subjects"].append(config["final_test_subjects"][0])
    else:
        config["final_test_subjects"].pop()
    with pytest.raises(ValueError, match="cohort overlap or missing identity"):
        validate_split_trials(trials, config)


@pytest.mark.parametrize("index,cohort", [(0, "final_test"), (-2, "development")])
def test_split_rejects_cohort_reassignment(config, trials, index, cohort):
    trials[index]["cohort"] = cohort
    with pytest.raises(ValueError, match="Frozen cohort mismatch"):
        validate_split_trials(trials, config)


def test_split_rejects_subject_outside_frozen_cohort(config, trials):
    trials[-2]["subject"] = "sub-999"
    with pytest.raises(ValueError, match="[Ss]ubject|[Cc]ohort|[Ii]dentity"):
        validate_split_trials(trials, config)


@pytest.mark.parametrize("field", HASH_FIELDS)
def test_split_rejects_identical_numerical_content_across_cohorts(config, trials, field):
    trials[-2][field] = trials[0][field]
    with pytest.raises(ValueError, match=f"Exact numerical window duplicate: {field}"):
        validate_split_trials(trials, config)


@pytest.mark.parametrize("field", HASH_FIELDS)
def test_split_requires_each_included_numerical_window_hash(config, trials, field):
    trials[0].pop(field)
    with pytest.raises(ValueError, match="Missing numerical window hash"):
        validate_split_trials(trials, config)


def test_split_requires_raw_numerical_identity_for_excluded_partial(config, trials):
    trials[-1].pop("raw_window_numeric_sha256")
    with pytest.raises(ValueError, match="Missing numerical window hash"):
        validate_split_trials(trials, config)


def test_split_rejects_partial_raw_window_copy_of_included_trial(config, trials):
    trials[-1]["raw_window_numeric_sha256"] = trials[0]["raw_window_numeric_sha256"]
    with pytest.raises(ValueError, match="Exact numerical window duplicate: raw_window"):
        validate_split_trials(trials, config)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("component", COMPONENTS)
def test_fit_access_excludes_queries_validation_and_other_session_support(
    trials, method, component,
):
    metadata = [row for row in trials if row["subject"] == "sub-1" and row["included"]]
    session = "ses-3"
    allowed = allowed_fit_trial_ids(metadata, method=method, session=session, component=component)
    source_ids = [row["trial_id"] for row in metadata if row["role"] == "source_train"]
    support_ids = [row["trial_id"] for row in metadata
                   if row["role"] == "target_support" and row["session"] == session]
    adapts_component = (method == "refit_csp_lda" and component in {"csp", "lda"}) or (
        method == "frozen_csp_lda_recalibration" and component == "lda"
    )
    assert allowed == source_ids + (support_ids if adapts_component else [])
    forbidden = {row["trial_id"] for row in metadata if (
        row["role"] in {"source_validation", "source_query", "target_query"}
        or (row["role"] == "target_support" and row["session"] != session)
    )}
    assert set(allowed).isdisjoint(forbidden)
    assert {row["session"] for row in metadata
            if row["role"] == "target_support" and row["session"] != session} == {
                "ses-1", "ses-2", "ses-4", "ses-5"
            }


def test_fit_access_is_unchanged_by_query_labels_or_metadata_order(trials):
    metadata = [row for row in trials if row["subject"] == "sub-1" and row["included"]]
    changed = deepcopy(metadata)
    for row in changed:
        if row["role"] in {"source_validation", "source_query", "target_query"}:
            row["label"] = "altered_forbidden_label"
    changed.reverse()
    for method in METHODS:
        for component in COMPONENTS:
            original_ids = allowed_fit_trial_ids(
                metadata, method=method, session="ses-3", component=component,
            )
            changed_ids = allowed_fit_trial_ids(
                changed, method=method, session="ses-3", component=component,
            )
            assert set(original_ids) == set(changed_ids)


@pytest.mark.parametrize("component", ["scaler", "pca", "normalizer", "riemann_reference"])
def test_frozen_feature_transform_never_fits_target_support_for_any_method(trials, component):
    metadata = [row for row in trials if row["subject"] == "sub-1" and row["included"]]
    source_ids = [row["trial_id"] for row in metadata if row["role"] == "source_train"]
    for session in ("ses-1", "ses-2", "ses-3", "ses-4", "ses-5"):
        for method in METHODS:
            assert allowed_fit_trial_ids(
                metadata, method=method, session=session, component=component,
            ) == source_ids


@pytest.mark.parametrize("method,component,message", [
    ("new_unfrozen_method", "csp", "Unknown baseline"),
    ("source_only", "new_unfrozen_component", "Unknown component"),
])
def test_fit_access_rejects_unfrozen_method_or_component(trials, method, component, message):
    with pytest.raises(ValueError, match=message):
        allowed_fit_trial_ids(trials, method=method, session="ses-3", component=component)


def test_support_budget_accepts_partial_without_replacement_or_primary_changes(
    preparation, budget_config, budget_trials,
):
    partial_index = next(i for i, row in enumerate(budget_trials)
                         if row["session"] == "ses-1" and row["role"] == "target_support"
                         and row["source_row"] == 20)
    budget_trials[partial_index] = synthetic_trial(
        budget_config, session="ses-1", row=20, sample_count=2559,
    )
    original = deepcopy(budget_trials)
    checks = preparation.validate_budget_and_class_coverage(budget_trials, budget_config)
    assert all(checks.values())
    support = [row for row in budget_trials
               if row["session"] == "ses-1" and row["role"] == "target_support"]
    assert len(support) == 20
    assert sum(row["included"] for row in support) == 19
    assert sum(row["label"] == "left_hand" for row in support) == 10
    assert sum(row["label"] == "right_hand" for row in support) == 10
    assert budget_trials == original


def test_support_budget_counts_excluded_source_events_toward_total_limit(
    preparation, budget_config, budget_trials,
):
    budget_trials.append(synthetic_trial(
        budget_config, session="ses-1", row=21, sample_count=2559,
    ))
    support = [row for row in budget_trials
               if row["session"] == "ses-1" and row["role"] == "target_support"]
    assert sum(row["included"] for row in support) == 20
    with pytest.raises(ValueError, match="Support source-event budget exceeded"):
        preparation.validate_budget_and_class_coverage(budget_trials, budget_config)


def test_support_budget_counts_excluded_source_events_toward_class_limit(
    preparation, budget_config, budget_trials,
):
    for index, row in enumerate(budget_trials):
        if row["session"] == "ses-1" and row["role"] == "target_support" \
                and row["source_row"] == 20:
            budget_trials[index] = synthetic_trial(
                budget_config, session="ses-1", row=20, sample_count=2559,
            )
            budget_trials[index]["label"] = "left_hand"
            break
    support = [row for row in budget_trials
               if row["session"] == "ses-1" and row["role"] == "target_support"]
    assert len(support) == 20
    assert sum(row["label"] == "left_hand" for row in support) == 11
    assert sum(row["label"] == "left_hand" and row["included"] for row in support) == 10
    with pytest.raises(ValueError, match="Support per-class budget exceeded"):
        preparation.validate_budget_and_class_coverage(budget_trials, budget_config)


@pytest.mark.parametrize("role", [
    "source_train", "source_validation", "source_query", "target_support", "target_query",
])
def test_class_coverage_requires_both_included_classes_in_every_role(
    preparation, budget_config, budget_trials, role,
):
    session = "ses-0" if role.startswith("source_") else "ses-1"
    for row in budget_trials:
        if row["session"] == session and row["role"] == role and row["label"] == "right_hand":
            row["included"] = False
    with pytest.raises(ValueError, match="analysis role lacks a task class"):
        preparation.validate_budget_and_class_coverage(budget_trials, budget_config)


@pytest.mark.parametrize("role", [
    "source_train", "source_validation", "source_query", "target_support", "target_query",
])
def test_budget_validation_rejects_missing_frozen_role(
    preparation, budget_config, budget_trials, role,
):
    session = "ses-0" if role.startswith("source_") else "ses-3"
    remaining = [row for row in budget_trials
                 if not (row["session"] == session and row["role"] == role)]
    with pytest.raises(ValueError, match="Missing or extra frozen subject/session/role"):
        preparation.validate_budget_and_class_coverage(remaining, budget_config)


def test_support_budget_rejects_replacement_from_another_run(
    preparation, budget_config, budget_trials,
):
    support = next(row for row in budget_trials if row["role"] == "target_support")
    support["run"] = "run-1"
    with pytest.raises(ValueError, match="frozen complete first run"):
        preparation.validate_budget_and_class_coverage(budget_trials, budget_config)


def test_count_matching_selects_first_per_class_in_acquisition_order_without_primary_mutation(
    preparation, config,
):
    early_left = synthetic_trial(config, row=1)
    early_right = synthetic_trial(config, row=2)
    second_left = synthetic_trial(config, row=3)
    excluded_right = synthetic_trial(config, row=4, sample_count=2559)
    later_left = synthetic_trial(config, run="run-1", row=1)
    later_right = synthetic_trial(config, run="run-1", row=2)
    rows = [later_left, excluded_right, second_left, later_right, early_right, early_left]
    original = deepcopy(rows)

    records = preparation.count_matched_diagnostic(rows)
    assert records == [{
        "subject": "sub-1", "session": "ses-0", "role": "source_train", "n_per_class": 2,
        "available_class_counts": {"left_hand": 3, "right_hand": 2},
        "trial_ids": [row["trial_id"] for row in
                      (early_left, early_right, second_left, later_right)],
        "use": "diagnostic_only_primary_data_unchanged",
    }]
    assert rows == original
    assert preparation.count_matched_diagnostic(list(reversed(rows))) == records
    shuffled = [rows[i] for i in np.random.default_rng(42).permutation(len(rows))]
    assert preparation.count_matched_diagnostic(shuffled) == records


def test_count_matching_balances_each_subject_session_role_independently(preparation, config):
    source = [synthetic_trial(config, row=row) for row in (1, 2, 3)]
    target = [synthetic_trial(config, session="ses-2", run="run-1", row=row)
              for row in (1, 2, 4, 6)]
    other_subject = [synthetic_trial(config, subject="sub-2", row=row) for row in (1, 2, 3, 4)]
    rows = list(reversed(target + other_subject + source))
    original = deepcopy(rows)
    records = preparation.count_matched_diagnostic(rows)
    assert [(r["subject"], r["session"], r["role"], r["n_per_class"]) for r in records] == [
        ("sub-1", "ses-0", "source_train", 1),
        ("sub-1", "ses-2", "target_query", 1),
        ("sub-2", "ses-0", "source_train", 2),
    ]
    expected = [source[:2], target[:2], other_subject]
    for record, selected in zip(records, expected, strict=True):
        assert record["trial_ids"] == [row["trial_id"] for row in selected]
        assert len(record["trial_ids"]) == 2 * record["n_per_class"]
    assert rows == original
