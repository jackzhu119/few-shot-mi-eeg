"""Synthetic isolation/count/failure tests for the frozen phase-window engine."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts/run_kumar_phase_window_cpu_20261016.py"
SPEC = importlib.util.spec_from_file_location("phase_window_engine", PATH)
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)


def state():
    return {"n_components": np.asarray(4), "csp_filters": np.eye(22),
            "csp_patterns": np.eye(22), "csp_mean": np.zeros(4), "csp_std": np.ones(4),
            "lda_classes": np.asarray([0, 1]), "lda_coef": np.asarray([[1, -1, 0.5, -0.5]]),
            "lda_intercept": np.asarray([0.0]), "lda_means": np.zeros((2, 4)),
            "lda_priors": np.asarray([0.5, 0.5]), "lda_covariance": np.eye(4)}


def fixture_rows():
    trials, phases = [], []
    for index in range(48):
        role = "source_train" if index < 40 else "target_support" if index < 44 else "target_query"
        session = "ses-0" if index < 40 else "ses-1"
        run = "run-0" if role != "target_query" else "run-1"
        label = "left_hand" if index % 2 == 0 else "right_hand"
        cue = index * 4096
        trial_id = f"synthetic/{session}/{role}/row-{index}"
        trials.append({"trial_id": trial_id, "subject": "synthetic", "cohort": "development",
                       "session": session, "run": run, "label": label, "role": role,
                       "included": True, "sample_count": 2560, "start_sample": cue,
                       "source_file": "synthetic.edf"})
        phases.append({"trial_id": trial_id, "subject": "synthetic", "session": session,
                       "run": run, "class": label, "cue_mapping_exact": True,
                       "phase_mapping_success": True, "cue_sample_0based": cue,
                       "task_start_sample_0based": cue + 768, "task_end_sample_0based": cue + 2304,
                       "sample_rate": 512.0,
                       "task_start_code": 7691 + 10 * (index % 2),
                       "task_end_code": 7692 + 10 * (index % 2), "recording_n_samples": 250_000})
    return trials, phases


def case(*, trials=None, phases=None):
    if trials is None:
        trials, phases = fixture_rows()
    selected, coverage = ENGINE.select_common_trials(trials, phases)
    rng = np.random.default_rng(1234)
    arrays = {window: {row["trial_id"]: rng.normal(size=(22, count)).astype(np.float32)
                       for row in selected if row["role"] in {"source_train", "target_support", "target_query"}}
              for window, count in (("cue5s", 640), ("task2s", 256))}
    source = state()
    query = [row for row in selected if row["role"] == "target_query"]
    prediction = ENGINE.predict_arrays(source, np.stack([arrays["cue5s"][row["trial_id"]] for row in query])) if query else []
    saved = {row["trial_id"]: int(value) for row, value in zip(query, prediction)}
    return {"subject": "synthetic", "cohort": "development", "selected": selected,
            "coverage": coverage, "window_arrays": arrays, "cue_source_arrays": source,
            "saved_cue_frozen_predictions": saved, "synthetic": True}


def fake_fit(monkeypatch):
    calls = []

    def fit(X, y, source_arrays=None):
        calls.append({"X_shape": X.shape, "labels": y.copy(), "fixed_csp": source_arrays is not None})
        return state()

    monkeypatch.setattr(ENGINE, "fit_arrays", fit)
    return calls


def test_preprocessing_uses_only_exact_2s_array_and_keeps_old_size():
    rng = np.random.default_rng(4)
    raw = rng.normal(size=(22, 1024)) * 1e-5
    output = ENGINE.preprocess_window(raw, "task2s")
    assert output.shape == (22, 256) and output.dtype == np.float32
    assert np.max(np.abs(output.mean(axis=0))) < 1e-10
    with pytest.raises(ValueError, match="shape"):
        ENGINE.preprocess_window(raw, "cue5s")


def test_materialization_excludes_validation_and_never_filters_across_task_end():
    trials, phases = fixture_rows()
    selected, _ = ENGINE.select_common_trials(trials, phases)
    selected[0]["role"] = "source_validation"
    calls = []

    def reader(row, start, stop):
        assert row["role"] != "source_validation"
        calls.append((row["trial_id"], start, stop))
        rng = np.random.default_rng(start)
        return rng.normal(size=(22, stop - start)) * 1e-5

    arrays = ENGINE.materialize_window_arrays(selected, reader)
    assert set(arrays["cue5s"]) == set(arrays["task2s"])
    assert len(calls) == 94
    for row in selected[1:]:
        assert (row["trial_id"], row["task_start_sample"], row["task_start_sample"] + 1024) in calls
        assert row["task_start_sample"] + 1024 <= row["task_end_sample"]


def test_verified_cached_cue_branch_reads_only_activity_intervals():
    trials, phases = fixture_rows()
    selected, _ = ENGINE.select_common_trials(trials, phases)
    cache = {row["trial_id"]: np.ones((22, 640), dtype=np.float32) for row in selected}
    calls = []

    def reader(row, start, stop):
        calls.append((start, stop))
        assert stop - start == 1024
        rng = np.random.default_rng(start)
        return rng.normal(size=(22, 1024)) * 1e-5

    arrays = ENGINE.materialize_window_arrays(selected, reader, saved_cue_epochs=cache)
    assert len(calls) == len(selected)
    assert all(arrays["cue5s"][trial_id] is cached for trial_id, cached in cache.items())


def test_mapping_clock_mismatch_stops_before_materialization():
    trials, phases = fixture_rows()
    phases[0]["sample_rate"] = 256.0
    with pytest.raises(ValueError, match="clock"):
        ENGINE.select_common_trials(trials, phases)


@pytest.mark.parametrize("kind,expected", [
    ("partial", "original_partial_remains_excluded"),
    ("unknown", "unknown_or_ambiguous_original_phase"),
    ("short", "active_phase_shorter_than_2s"),
    ("boundary", "task2s_exceeds_recording"),
])
def test_common_selection_keeps_every_exclusion_and_never_refills(kind, expected):
    trials, phases = fixture_rows()
    if kind == "partial":
        trials[-1].update(included=False, sample_count=2000)
    elif kind == "unknown":
        phases[-1]["phase_mapping_success"] = False
    elif kind == "short":
        phases[-1]["task_end_sample_0based"] = phases[-1]["task_start_sample_0based"] + 1023
    else:
        phases[-1]["recording_n_samples"] = phases[-1]["task_start_sample_0based"] + 1023
    selected, coverage = ENGINE.select_common_trials(trials, phases)
    assert len(selected) == 47 and len(coverage) == 48
    assert coverage[-1]["exclusion_reason"] == expected


def test_both_windows_same_query_fit_ids_and_source_state_unchanged(monkeypatch):
    calls = fake_fit(monkeypatch)
    inputs = case()
    before = ENGINE.arrays_hash(inputs["cue_source_arrays"])
    result = ENGINE.evaluate_participant(**inputs)
    assert len(result["metrics"]) == 30
    assert len(calls) == 5  # new task source plus two updates in each window
    for method in ENGINE.METHODS:
        group = [row for row in result["metrics"] if row["session"] == "ses-1" and row["method"] == method]
        assert len({row["query_ids_sha256"] for row in group}) == 1
        assert len({row["fit_ids_sha256"] for row in group}) == 1
    for row in result["fit_access_audit"]:
        assert not any("target_query" in trial_id for trial_id in row["fit_trial_ids"])
    assert before == ENGINE.arrays_hash(inputs["cue_source_arrays"])
    assert all(row["balanced_accuracy"] is None for row in result["metrics"] if row["session"] != "ses-1")


def test_query_label_changes_never_change_any_fit(monkeypatch):
    calls = fake_fit(monkeypatch)
    first = case()
    ENGINE.evaluate_participant(**first)
    before = [(call["X_shape"], call["labels"].tolist(), call["fixed_csp"]) for call in calls]
    calls.clear()
    second = case()
    for row in second["selected"]:
        if row["role"] == "target_query":
            row["label"] = 1 - row["label"]
    ENGINE.evaluate_participant(**second)
    after = [(call["X_shape"], call["labels"].tolist(), call["fixed_csp"]) for call in calls]
    assert before == after


def test_one_class_support_still_uses_source40_union(monkeypatch):
    calls = fake_fit(monkeypatch)
    trials, phases = fixture_rows()
    for trial, phase in zip(trials, phases):
        if trial["role"] == "target_support":
            trial["label"] = phase["class"] = "left_hand"
            phase.update(task_start_code=7691, task_end_code=7692)
    result = ENGINE.evaluate_participant(**case(trials=trials, phases=phases))
    updated = [row for row in result["metrics"] if row["session"] == "ses-1" and row["method"] != "source_only"]
    assert all(row["support_single_class"] and row["new_fit_performed"] for row in updated)
    assert all(set(call["labels"]) == {0, 1} for call in calls)


def test_empty_known_support_falls_back_without_update_fit(monkeypatch):
    calls = fake_fit(monkeypatch)
    trials, phases = fixture_rows()
    for trial, phase in zip(trials, phases):
        if trial["role"] == "target_support":
            phase["task_end_sample_0based"] = phase["task_start_sample_0based"] + 512
    result = ENGINE.evaluate_participant(**case(trials=trials, phases=phases))
    assert len(calls) == 1
    updated = [row for row in result["metrics"] if row["session"] == "ses-1" and row["method"] != "source_only"]
    assert all(row["status"] == "fallback_no_eligible_support" and not row["new_fit_performed"] for row in updated)


def test_unknown_support_is_not_treated_as_zero_known_support(monkeypatch):
    calls = fake_fit(monkeypatch)
    trials, phases = fixture_rows()
    for trial, phase in zip(trials, phases):
        if trial["role"] == "target_support":
            phase["phase_mapping_success"] = False
    result = ENGINE.evaluate_participant(**case(trials=trials, phases=phases))
    assert len(calls) == 1
    updated = [row for row in result["metrics"] if row["session"] == "ses-1" and row["method"] != "source_only"]
    assert all(row["balanced_accuracy"] is None and row["status"] == "undefined_support_phase_access_incomplete" for row in updated)


def test_one_class_query_is_undefined_not_chance_or_deleted(monkeypatch):
    fake_fit(monkeypatch)
    trials, phases = fixture_rows()
    for trial, phase in zip(trials, phases):
        if trial["role"] == "target_query" and trial["label"] == "right_hand":
            phase["task_end_sample_0based"] = phase["task_start_sample_0based"] + 512
    result = ENGINE.evaluate_participant(**case(trials=trials, phases=phases))
    group = [row for row in result["metrics"] if row["session"] == "ses-1"]
    assert len(group) == 6
    assert all(row["n_query_right"] == 0 and row["balanced_accuracy"] is None for row in group)
    aggregate = ENGINE.aggregate_participants(result["metrics"])
    assert all(row["balanced_accuracy"] is None for row in aggregate["participant_endpoints"])


@pytest.mark.parametrize("error", [OSError("synthetic disk failure"), ValueError("synthetic digest mismatch")])
def test_persist_failure_stops_before_any_following_fit(monkeypatch, error):
    calls = fake_fit(monkeypatch)

    def model_sink(arrays, context):
        raise error

    with pytest.raises(type(error), match="synthetic"):
        ENGINE.evaluate_participant(**case(), model_sink=model_sink)
    assert len(calls) == 1  # first task-source fit was the last fit


def test_partial_record_write_failure_stops_before_first_fit(monkeypatch):
    calls = fake_fit(monkeypatch)

    def emit(record):
        raise OSError("partial record cannot be written")

    with pytest.raises(OSError, match="partial record"):
        ENGINE.evaluate_participant(**case(), emit=emit)
    assert calls == []


def test_unexpected_estimator_valueerror_propagates_without_retry(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        raise ValueError("unexpected estimator error")

    monkeypatch.setattr(ENGINE, "fit_arrays", fail)
    with pytest.raises(ValueError, match="unexpected"):
        ENGINE.evaluate_participant(**case())
    assert len(calls) == 1


def test_window_id_mismatch_rejected_before_fit(monkeypatch):
    calls = fake_fit(monkeypatch)
    inputs = case()
    inputs["window_arrays"]["task2s"].pop(next(iter(inputs["window_arrays"]["task2s"])))
    with pytest.raises(ValueError, match="same eligible"):
        ENGINE.evaluate_participant(**inputs)
    assert calls == []


def test_real_execution_requires_persistent_sinks_before_fit(monkeypatch):
    calls = fake_fit(monkeypatch)
    inputs = case()
    inputs["synthetic"] = False
    with pytest.raises(ValueError, match="persistent"):
        ENGINE.evaluate_participant(**inputs)
    assert calls == []


def test_actual_csp_lda_api_on_synthetic_arrays_only():
    rng = np.random.default_rng(8)
    X = rng.normal(size=(12, 22, 256))
    X -= X.mean(axis=1, keepdims=True)
    y = np.arange(12) % 2
    arrays = ENGINE.fit_arrays(X, y)
    digest = ENGINE.arrays_hash(arrays)
    assert ENGINE.predict_arrays(arrays, X[:4]).shape == (4,)
    updated = ENGINE.fit_arrays(X, y, arrays)
    assert ENGINE.arrays_hash(arrays) == digest
    assert np.array_equal(updated["csp_filters"], arrays["csp_filters"])


def test_statistics_use_five_session_participant_endpoints_and_common_pairs():
    rows = []
    for subject in ("synthetic-1", "synthetic-2"):
        for session_index, session in enumerate(ENGINE.SESSIONS):
            for window in ENGINE.WINDOWS:
                for method_index, method in enumerate(ENGINE.METHODS):
                    value = 0.5 + session_index / 100 + method_index / 50
                    if window == "task2s":
                        value += 0.01
                    rows.append({"subject": subject, "cohort": "synthetic", "session": session,
                                 "window": window, "method": method, "balanced_accuracy": value,
                                 "n_unknown_query_phase": 0})
    aggregate = ENGINE.aggregate_participants(rows)
    assert len(aggregate["participant_endpoints"]) == 12
    paired = [row for row in aggregate["paired_contrasts"] if row["window"] == "paired_task2s_minus_cue5s"]
    assert len(paired) == 3
    assert all(row["n_participants"] == 2 and np.isclose(row["mean_difference_ba"], 0.01) for row in paired)
    rows[-1]["balanced_accuracy"] = None
    changed = ENGINE.aggregate_participants(rows)
    full = [row for row in changed["paired_contrasts"] if row["window"] == "paired_task2s_minus_cue5s" and row["contrast"] == "refit_csp_lda"][0]
    assert full["n_participants"] == 1
    assert full["paired_participants"] == ["synthetic-1"]
