"""Synthetic software checks for saved-prediction QC postprocessing only."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "saved_query_qc", Path(__file__).parents[1] / "scripts/analyze_kumar_saved_query_qc_20261015.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_rows():
    meta = {
        f"synthetic-{i}": {
            "trial_id": f"synthetic-{i}",
            "subject": "synthetic-subject",
            "session": "ses-1",
            "run": "run-1",
            "role": "target_query",
            "cohort": "synthetic",
            "label": "left_hand" if i == 0 else "right_hand",
            "qc_peak_to_peak_over_250uv": False,
        }
        for i in range(2)
    }
    rows = [
        {
            "trial_id": key,
            "subject": r["subject"],
            "session": r["session"],
            "run": r["run"],
            "label": int(r["label"] == "right_hand"),
            "prediction": 0,
        }
        for key, r in meta.items()
    ]
    return meta, rows


def test_exact_join_reordered_and_all_metadata_preserved():
    meta, rows = fixture_rows()
    joined = MODULE.exact_join(list(reversed(rows)), meta, "label", "prediction")
    assert [r["trial_id"] for r in joined] == list(reversed(meta))
    assert MODULE.score(joined)["balanced_accuracy"] == 0.5


@pytest.mark.parametrize(
    "case", ["duplicate", "missing", "unexpected", "label", "session", "prediction"]
)
def test_exact_join_rejects_identity_or_label_corruption(case):
    meta, rows = fixture_rows()
    if case == "duplicate":
        rows[1] = rows[0].copy()
    elif case == "missing":
        rows.pop()
    elif case == "unexpected":
        rows[0]["trial_id"] = "unexpected"
    elif case == "label":
        rows[0]["label"] = 1
    elif case == "session":
        rows[0]["session"] = "ses-2"
    else:
        rows[0]["prediction"] = 2
    with pytest.raises(ValueError):
        MODULE.exact_join(rows, meta, "label", "prediction")


@pytest.mark.parametrize("rows", [[], [{"label": 0, "prediction": 0}]])
def test_missing_class_stays_undefined_and_counts_retained(rows):
    value = MODULE.score(rows)
    assert value["balanced_accuracy"] is None
    assert value["undefined_reason"] == "absent_true_class"
    assert value["n_query"] == len(rows)


def test_ba_uses_equal_class_weight_and_low_counts_are_explicit():
    rows = [{"label": 0, "prediction": 0}] * 9 + [{"label": 1, "prediction": 0}]
    value = MODULE.score(rows)
    assert value["balanced_accuracy"] == 0.5
    assert value["fewer_than_5_per_class"] is True
    assert value["class_collapse"] is True


def test_seed_scores_are_averaged_without_picking_or_voting():
    rows = [
        {
            "seed": seed,
            **MODULE.score([{"label": 0, "prediction": 0}, {"label": 1, "prediction": p}]),
        }
        for seed, p in zip(["1", "2", "3"], [0, 0, 1], strict=True)
    ]
    result = MODULE.aggregate_seeds(rows, ["1", "2", "3"])
    assert result["balanced_accuracy"] == pytest.approx(2 / 3)
    assert result["n_query"] == 2
    assert result["seeds_included"] == 3
    with pytest.raises(ValueError, match="Missing seed"):
        MODULE.aggregate_seeds(rows[:2], ["1", "2", "3"])


def test_incomplete_target_session_does_not_change_endpoint_estimand():
    rows = [
        {
            "session": f"ses-{i}",
            "BA_defined": i != 3,
            "balanced_accuracy": 0.8 if i != 3 else None,
            "n_query": 10,
            "n_left": 5,
            "n_right": 5,
            "fewer_than_5_per_class": False,
        }
        for i in range(1, 6)
    ]
    result = MODULE.participant_endpoint(rows)
    assert result["target_five_session_mean_BA"] is None
    assert result["n_defined_target_sessions"] == 4
    assert result["target_undefined_sessions"] == "ses-3"


def test_bootstrap_is_participant_based_deterministic_and_handles_small_groups():
    values = [0.01, -0.03, 0.22]
    result = MODULE.bootstrap(values)
    rng = np.random.default_rng(42)
    expected = np.quantile(
        np.asarray(values)[rng.integers(0, 3, (10000, 3))].mean(axis=1), [0.025, 0.975]
    )
    assert [result["ci95_low"], result["ci95_high"]] == list(expected)
    assert MODULE.bootstrap([])["mean"] is None
    assert MODULE.bootstrap([0.1])["ci95_low"] is None


def test_portable_input_rejoins_without_private_paths(tmp_path, monkeypatch):
    meta, rows = fixture_rows()
    for row in rows:
        row.update(
            {
                "method": "source_only",
                "seed": "cpu_fixed",
                "role": "target_query",
                "qc_peak_to_peak_over_250uv": False,
            }
        )
    MODULE.write_csv(tmp_path / "saved_predictions.csv", rows)
    monkeypatch.setattr(MODULE, "SUBJECTS", ("synthetic-subject",))
    monkeypatch.setattr(MODULE, "METHODS", ("source_only",))
    joined, checks = MODULE.load_portable_predictions(
        MODULE.Reader(), tmp_path, list(meta.values())
    )
    assert len(joined) == 2
    assert checks[0]["exact_query_identity_count"] == 2
    assert all(row["qc_peak_to_peak_over_250uv"] is False for row in joined)


def test_portable_input_rejects_changed_qc_flag(tmp_path, monkeypatch):
    meta, rows = fixture_rows()
    for row in rows:
        row.update(
            {
                "method": "source_only",
                "seed": "cpu_fixed",
                "role": "target_query",
                "qc_peak_to_peak_over_250uv": True,
            }
        )
    MODULE.write_csv(tmp_path / "saved_predictions.csv", rows)
    monkeypatch.setattr(MODULE, "SUBJECTS", ("synthetic-subject",))
    monkeypatch.setattr(MODULE, "METHODS", ("source_only",))
    with pytest.raises(ValueError, match="Public QC flag differs"):
        MODULE.load_portable_predictions(MODULE.Reader(), tmp_path, list(meta.values()))
