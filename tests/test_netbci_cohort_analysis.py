"""Software-only checks for cohort chronology, source-only QC and frozen fitting."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_netbci_cohort_subject import (
    balanced_indices,
    fit_source_qc,
    frozen_decoder,
    model_digest,
    partition_trials,
    run_bootstrap_ci,
)


def fixture_trials():
    return [{"subject": "software_fixture", "session": session, "run": run,
             "label": label, "trial_id": f"fixture/{session}/{run}/{label}/{index}"}
            for session in ("01", "02", "03", "04")
            for run in ("01", "02", "03", "04", "05", "06")
            for label in ("rest", "right_hand") for index in range(2)]


def fixture_config():
    return {"session_order": ["01", "02", "03", "04"],
            "source_train_runs": ["01", "02", "03", "04"],
            "source_query_runs": ["05", "06"], "csp_components": 2,
            "seed": 42, "bootstrap_run_repetitions": 20}


def test_temporal_partition_is_exhaustive_and_no_later_day_enters_source_fit():
    trials = fixture_trials()
    roles, by_trial = partition_trials(trials, fixture_config())
    assigned = np.concatenate(list(roles.values()))
    assert len(assigned) == len(trials) == len(np.unique(assigned))
    assert len(roles["source_train"]) == 16
    assert len(roles["source_reference_query"]) == 8
    assert len(roles["validation_no_selection"]) == 24
    assert len(roles["test_exploratory"]) == 48
    assert {trials[i]["session"] for i in roles["source_train"]} == {"01"}
    assert {trials[i]["run"] for i in roles["source_train"]} == {"01", "02", "03", "04"}
    assert len(by_trial) == len(trials)


@pytest.mark.parametrize("change", ["duplicate", "missing_run", "other_participant", "bad_class"])
def test_invalid_identity_or_coverage_is_rejected(change):
    trials = fixture_trials()
    if change == "duplicate":
        trials[-1]["trial_id"] = trials[0]["trial_id"]
    elif change == "missing_run":
        trials = [t for t in trials if not (t["session"] == "04" and t["run"] == "06")]
    elif change == "other_participant":
        trials[-1]["subject"] = "another_fixture"
    else:
        trials[-1]["label"] = "invented_hit"
    with pytest.raises(ValueError):
        partition_trials(trials, fixture_config())


def test_qc_threshold_is_unchanged_by_target_amplitude():
    rng = np.random.default_rng(8)
    X = rng.normal(size=(20, 3, 40)) * 2e-6
    _, initial, audit = fit_source_qc(X, np.arange(6), 6)
    changed = X.copy()
    changed[6:] *= 1e8
    _, flagged, new_audit = fit_source_qc(changed, np.arange(6), 6)
    assert new_audit == audit
    assert np.array_equal(initial[:6], flagged[:6])
    assert flagged[6:].all()


def test_matched_sampling_reports_the_actual_missing_cell_and_keeps_preset():
    trials = fixture_trials()
    runs = ["03", "04", "05", "06"]
    sampled = balanced_indices(trials, ["01", "02", "03", "04"], runs, 2, 1)
    assert all(len(indices) == 16 for indices in sampled.values())
    eligible = np.ones(len(trials), dtype=bool)
    first_bad = next(i for i, t in enumerate(trials) if t["session"] == "04"
                     and t["run"] == "05" and t["label"] == "rest")
    eligible[first_bad] = False
    with pytest.raises(ValueError, match='"n_available": 1, "n_required": 2'):
        balanced_indices(trials, ["01", "02", "03", "04"], runs, 2, 1, eligible)


class RecordingDecoder:
    """Simple deterministic software fixture; no scientific classification result."""
    def fit(self, X, y):
        self.train_values = X.copy()
        self.fit_calls = getattr(self, "fit_calls", 0) + 1
        self.threshold = float(X[:, 0, 0].mean())
        return self

    def predict(self, X):
        return np.where(X[:, 0, 0] > self.threshold, "right_hand", "rest")


def test_frozen_decoder_fits_once_source_only_and_uses_all_six_later_runs(tmp_path):
    trials = fixture_trials()
    config = fixture_config()
    roles, _ = partition_trials(trials, config)
    X = np.array([0. if t["label"] == "rest" else 2. for t in trials])[:, None, None]
    X[24:] += 100
    y = np.array([t["label"] for t in trials])
    flagged = np.zeros(len(trials), dtype=bool)
    model = RecordingDecoder()
    scores, predictions, failures = frozen_decoder(
        X, y, trials, roles, flagged, config, tmp_path, factory=lambda: model)
    assert model.fit_calls == 1
    assert np.array_equal(model.train_values, X[roles["source_train"]])
    before = model_digest(model)
    model.predict(X[-12:])
    assert model_digest(model) == before
    assert [r["n_runs"] for r in scores] == [2, 6, 6, 6]
    assert [r["n_test"] for r in scores] == [8, 24, 24, 24]
    assert len(predictions) == 80
    assert all(r["constant_prediction"] for r in scores[1:])
    assert len([r for r in failures if r["type"] == "constant_prediction"]) == 3
    assert (tmp_path / "CSP_LDA_model_audit.json").is_file()


def test_conditional_ci_resamples_complete_runs():
    truth = np.array(["rest", "right_hand"] * 4)
    prediction = truth.copy()
    prediction[4:] = np.where(truth[4:] == "rest", "right_hand", "rest")
    ci = run_bootstrap_ci(truth, prediction, np.array(["a"] * 4 + ["b"] * 4), 42, 200)
    assert ci == [0., 1.]
    assert run_bootstrap_ci(truth, truth, np.array(["one"] * 8), 42, 200) is None
