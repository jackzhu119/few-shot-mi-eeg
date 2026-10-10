"""Leakage guards and reported-percentage checks; no models or EEG downloads."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_script("prepare_netbci_analysis").prepare
compatible = load_script("check_netbci_behavior_link").compatible_percentage


def fixture_trials(config):
    return [{"subject": "sub-1", "session": session, "run": f"{run:02d}",
             "trial_id": f"s{session}-r{run}-t{trial}", "label": label}
            for session in config["session_order"] for run in range(1, 7)
            for label in ["right_hand", "rest"] for trial in range(10)]


def test_frozen_plan_is_deterministic_and_never_reuses_query_runs():
    config = json.loads((ROOT / "configs/netbci_cross_session.json").read_text())
    trials = fixture_trials(config)
    # Give each class a distinct trial identity in the software fixture.
    for trial in trials:
        trial["trial_id"] += "-" + trial["label"]
    first, second = prepare(config, trials), prepare(config, trials)
    assert first == second
    all_ids = [identity for role in first["partitions"].values() for identity in role["trial_ids"]]
    assert len(all_ids) == len(set(all_ids)) == len(trials)
    query = set(first["partitions"]["target_query"]["trial_ids"])
    assert all(not query.intersection(ids) for ids in first["optional_calibration_trial_ids"].values())
    assert first["trained_model"] is False
    config["target_query_runs"].append("01")
    with pytest.raises(ValueError, match="multiple partitions"):
        prepare(config, trials)


def test_plan_rejects_missing_sessions_and_insufficient_label_budget():
    config = json.loads((ROOT / "configs/netbci_cross_session.json").read_text())
    trials = fixture_trials(config)
    for trial in trials:
        trial["trial_id"] += "-" + trial["label"]
    with pytest.raises(ValueError, match="sessions differ"):
        prepare(config, [trial for trial in trials if trial["session"] != "04"])
    config["optional_calibration_trials_per_class"] = 11
    with pytest.raises(ValueError, match="class coverage"):
        prepare(config, trials)


def test_percentage_compatibility_does_not_identify_the_denominator():
    assert not compatible("64.3", 30)
    assert compatible("64.3", 28)
    assert compatible("64.3", 56)
    assert not compatible("75", 30)
    assert compatible("100", 29)
