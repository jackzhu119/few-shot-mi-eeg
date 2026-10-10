"""Guard against scientifically misleading grain and identity conversions."""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from learning_preserving_bci.datasets.netbci_behavior import (
    join_verified_sessions,
    read_behavior_sessions,
)


def table(tmp_path, vector="[20, 40, 60, 80, 100, 0]", subjects=("sub-01",)):
    path = tmp_path / "participants.tsv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, ["participant_id", "score1", "score2"], delimiter="\t")
        writer.writeheader()
        for subject in subjects:
            writer.writerow({"participant_id": subject, "score1": vector, "score2": vector})
    return path


def test_source_vector_order_does_not_change_session_summary(tmp_path):
    path = table(tmp_path)
    summaries, positions = read_behavior_sessions(path, {"01": "score1", "02": "score2"}, 6)
    assert summaries[0]["mean_run_hit_percent"] == 50
    reordered = table(tmp_path, "[100, 0, 60, 20, 80, 40]")
    other, _ = read_behavior_sessions(reordered, {"01": "score1", "02": "score2"}, 6)
    assert other[0]["mean_run_hit_percent"] == summaries[0]["mean_run_hit_percent"]
    assert all(x["EEG_run"] == x["EEG_trial"] == "unresolved" for x in positions)
    assert summaries[0]["score_denominator"] == "unresolved"


@pytest.mark.parametrize("vector", ["[1, 2]", "[1, 2, 3, 4, 5, -1]",
                                    "[1, 2, 3, 4, 5, 101]", "[1, 2, 3, 4, 5, True]",
                                    "[1, 2, 3, 4, 5, 'NA']", "__import__('os').getcwd()"])
def test_invalid_source_scores_fail_closed(tmp_path, vector):
    with pytest.raises(ValueError):
        read_behavior_sessions(table(tmp_path, vector), {"01": "score1"}, 6)


def test_duplicate_subject_is_not_an_independent_observation(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        read_behavior_sessions(table(tmp_path, subjects=("sub-01", "sub-01")), {"01": "score1"}, 6)


def test_session_join_never_imputes_behavior_to_trial_or_run(tmp_path):
    behavior, _ = read_behavior_sessions(table(tmp_path), {"01": "score1", "02": "score2"}, 6)
    eeg = [{"subject": "sub-1", "session": "02", "n_EEG_trials": 123}]
    joined = join_verified_sessions(behavior, eeg, {"sub-1": "sub-01"})
    assert len(joined) == 1 and joined[0]["n_EEG_trials"] == 123
    assert np.isfinite(joined[0]["mean_run_hit_percent"])
    for extra in ({"trial_id": "unrelated"}, {"run": "01"}):
        with pytest.raises(ValueError, match="broadcast"):
            join_verified_sessions(behavior, [{**eeg[0], **extra}], {"sub-1": "sub-01"})
    with pytest.raises(ValueError, match="mapping"):
        join_verified_sessions(behavior, eeg, {})
    with pytest.raises(ValueError, match="no matching"):
        join_verified_sessions(behavior, [{"subject": "sub-1", "session": "03"}], {"sub-1": "sub-01"})
    with pytest.raises(ValueError, match="Duplicate behavior"):
        join_verified_sessions(behavior+behavior, eeg, {"sub-1": "sub-01"})
    with pytest.raises(ValueError, match="Duplicate EEG"):
        join_verified_sessions(behavior, eeg+eeg, {"sub-1": "sub-01"})


def test_float_roundoff_does_not_turn_equal_scores_into_behavioral_decline():
    script = Path(__file__).resolve().parents[1]/"scripts/analyze_netbci_behavior_sessions.py"
    spec = importlib.util.spec_from_file_location("behavior_analysis", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scores = [50.0, 50.0-7.1e-15, 50.0, 60.0]
    behavior = [{"original_subject": "sub-01", "session": f"{i+1:02}",
                 "mean_run_hit_percent": value} for i, value in enumerate(scores)]
    behavior += [{"original_subject": "sub-02", "session": f"{i+1:02}",
                  "mean_run_hit_percent": 50.0} for i in range(4)]
    _, change, _, _ = module.cohort_statistics(behavior, ["01", "02", "03", "04"], 42, 10)
    assert change["n_with_any_decrease"] == 0
    assert change["n_nondecreasing_all_sessions"] == 2
    # The reporting-precision check is separate from a purely numerical tolerance.
    behavior[1]["mean_run_hit_percent"] = 49.99833333333333
    _, change, _, _ = module.cohort_statistics(behavior, ["01", "02", "03", "04"], 42, 10)
    assert change["n_with_any_decrease"] == 1
    assert change["n_with_any_decrease_larger_than_reporting_sensitivity"] == 0
