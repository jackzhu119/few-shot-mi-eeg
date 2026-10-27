"""Synthetic endpoints validate the fixed external analysis, without EEG."""

from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
from external_validation_20261027.statistics import (  # noqa: E402
    exact_sign_flip,
    holm_adjust,
    summarize,
)


def records(participants=tuple(str(i) for i in range(1, 10))):
    return [
        {"participant": participant, "session": "session-2", "method": method,
         "balanced_accuracy": value, "n_query": 120, "class_counts": {"0": 60, "1": 60},
         "synthetic": True, "software_validation_only": True}
        for participant in participants
        for method, value in (("frozen", 0.5), ("lda_only", 0.55),
                              ("full_csp", 0.65), ("ea_csp", 0.7))
    ]


def test_constant_gain_exact_probability_units_and_holm():
    result = summarize(records())
    assert result["status"] == "complete"
    primary = result["contrasts"]["full_csp_minus_lda_only"]
    assert primary["mean_difference_pp"] == pytest.approx(10)
    assert primary["bootstrap_ci95_pp"] == pytest.approx([10, 10])
    assert primary["p_exact_sign_flip"] == 2 / 512
    assert primary["p_holm_secondary"] is None
    assert primary["positive_participants"] == 9
    assert primary["leave_one_out_mean_range_pp"] == pytest.approx([10, 10])
    for key, value in result["contrasts"].items():
        if value["role"] == "secondary":
            assert value["p_holm_secondary"] == 6 / 512, key
    assert result["cohort_balanced_accuracy"]["full_csp"]["mean_percent"] == pytest.approx(65)


def test_sign_flip_preserves_magnitudes_and_zeros():
    values = np.asarray([0.4, 0.02, -0.01])
    result = exact_sign_flip(values)
    assert result["extreme_assignments"] == 4
    assert result["total_assignments"] == 8
    assert exact_sign_flip(np.zeros(9))["p_value"] == 1
    # Same signs, different magnitudes can give a different exact statistic.
    assert exact_sign_flip(np.asarray([0.01, 0.01, -0.4]))["p_value"] == 1


def test_missing_participant_or_method_never_gives_cohort_inference():
    incomplete = records()[:-1]
    result = summarize(incomplete)
    assert result["status"] == "partial"
    assert result["complete_participants"] == [str(i) for i in range(1, 9)]
    assert result["missing_cells"] == [{"participant": "9", "method": "ea_csp"}]
    assert result["contrasts"] == {}
    assert result["cohort_balanced_accuracy"] == {}


@pytest.mark.parametrize("bad_value", [None, float("nan"), 55, -0.1])
def test_invalid_ba_preserves_incomplete_status(bad_value):
    rows = records()
    rows[0]["balanced_accuracy"] = bad_value
    result = summarize(rows)
    assert result["status"] == "partial"
    assert len(result["participant_results"]) == 36
    assert result["invalid_records"]
    assert not result["contrasts"]


def test_missing_query_class_and_method_query_count_mismatch():
    rows = records()
    rows[0]["class_counts"] = {"0": 120, "1": 0}
    assert summarize(rows)["status"] == "partial"
    rows = records()
    rows[0]["n_query"] = 118
    rows[0]["class_counts"] = {"0": 59, "1": 59}
    result = summarize(rows)
    assert result["status"] == "partial"
    assert result["invalid_records"][0]["reasons"] == ["methods_have_different_query_counts"]


def test_duplicate_or_changed_session_is_rejected():
    rows = records()
    with pytest.raises(ValueError, match="duplicate"):
        summarize(rows + [rows[0]])
    rows[1]["session"] = "wrong-session"
    with pytest.raises(ValueError, match="same target session"):
        summarize(rows)


def test_deterministic_resampling_and_holm_order():
    rows = records()
    for index, row in enumerate(rows):
        row["balanced_accuracy"] += (index // 4) * 0.001 * (index % 4)
    assert summarize(rows) == summarize(list(reversed(rows)))
    assert holm_adjust([0.04, 0.001, 0.03]) == pytest.approx([0.06, 0.003, 0.06])


def test_nondefault_expected_identity_is_explicit():
    result = summarize(records(("1", "2")), expected_participants=("1", "2"))
    assert result["status"] == "complete"
    assert result["analysis"]["participant_order"] == ["1", "2"]
    assert result["contrasts"]["full_csp_minus_lda_only"]["exact_sign_flip"]["total_assignments"] == 4
