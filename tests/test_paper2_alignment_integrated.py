"""Targeted software-only checks for saved-prediction reanalysis."""
from __future__ import annotations

import numpy as np
import pytest

from learning_preserving_bci.paper2_alignment_integrated import (
    binary_metrics, group_records, paired_summary, paired_transition, pair_predictions,
    participant_tables, run_tables, signed, summarize_participants,
)


def test_unequal_class_transition_denominators():
    y = [0, 0, 0, 1]
    ref = [0, 1, 1, 0]
    new = [1, 0, 1, 1]
    result = paired_transition(y, ref, new)
    assert result["corrected"] == pytest.approx(2 / 3)
    assert result["introduced"] == pytest.approx(1 / 6)
    assert result["delta_ba"] == pytest.approx(0.5)
    assert result["disagreement"] == pytest.approx(5 / 6)


def test_metric_identity_and_missing_classes():
    result = binary_metrics([0, 0, 1, 1], [0, 0, 0, 1])
    assert result["weak_recall"] == result["ba"] - result["recall_gap"] / 2
    missing = binary_metrics([0, 0], [0, 1])
    assert missing["recall_left"] == 0.5 and missing["recall_right"] is None
    assert missing["ba"] is missing["weak_recall"] is missing["recall_gap"] is None
    assert binary_metrics([], [])["status"] == "undefined_missing_class"


@pytest.mark.parametrize("truth,prediction", [([0, 2], [0, 1]), ([0], [0, 1]), ([[0]], [[0]])])
def test_invalid_labels_or_shapes_stop(truth, prediction):
    with pytest.raises(ValueError):
        binary_metrics(truth, prediction)


def test_pairing_rejects_duplicates_reorder_missing_and_label_change():
    rows = [{"trial_id": "a", "label": 0, "prediction": 1},
            {"trial_id": "b", "label": 1, "prediction": 1}]
    for other in [rows + [rows[0]], rows[::-1], rows[:1],
                  [rows[0], {**rows[1], "label": 0}]]:
        with pytest.raises(ValueError):
            pair_predictions(rows, other)


def test_method_budget_grid_joins_cannot_hide_label_difference():
    common = dict(dataset="x", participant="s1", session="E", budget="full", run="r1")
    rows = [{**common, "method": "frozen", "trial_id": "a", "label": 0, "prediction": 0},
            {**common, "method": "full_csp", "trial_id": "a", "label": 1, "prediction": 0}]
    with pytest.raises(ValueError, match="identities, order or labels"):
        group_records(rows)


def test_nonlinear_metrics_are_averaged_after_scoring_endpoint():
    cells = []
    for i in range(1, 6):
        left, right = (1.0, 0.0) if i < 4 else (0.0, 1.0)
        cells.append(dict(dataset="Kumar2024", participant="sub-1", budget="full", method="frozen",
                          subset="all_query", session=f"ses-{i}", status="ok", n_query=4,
                          ba=0.5, weak_recall=0.0, recall_gap=1.0, recall_left=left, recall_right=right))
    participant = participant_tables(cells, [])[0][0]
    assert participant["weak_recall"] == 0.0
    assert participant["recall_gap"] == 1.0
    assert min(participant["recall_left"], participant["recall_right"]) == 0.4
    assert abs(participant["recall_left"] - participant["recall_right"]) == pytest.approx(0.2)


def test_incomplete_session_is_not_silently_averaged():
    cell = dict(dataset="Kumar2024", participant="sub-1", budget="full", method="frozen",
                subset="all_query", session="ses-1", status="ok", n_query=2,
                ba=0.5, weak_recall=0.0, recall_gap=1.0, recall_left=0.0, recall_right=1.0)
    with pytest.raises(ValueError, match="Missing or repeated"):
        participant_tables([cell], [])


def test_bootstrap_uses_people_and_fixed_paired_differences():
    values = [-0.2, 0.1, 0.4]
    a, b = paired_summary(values), paired_summary(values)
    assert a == b and a["n"] == 3
    assert a["mean"] == pytest.approx(0.1)
    assert a["positive"] == 2 and a["negative"] == 1 and a["zero"] == 0
    assert a["leave_one_out_min"] == pytest.approx(-0.05)
    assert a["leave_one_out_max"] == pytest.approx(0.25)
    assert paired_summary([])["mean"] is None


def test_ties_are_separate_from_benefit_or_decline():
    assert signed(0) == signed(5e-13) == signed(-5e-13) == "zero"
    assert signed(2e-12) == "positive" and signed(-2e-12) == "negative"


def test_binary_transition_identity_on_many_unequal_class_synthetic_cases():
    rng = np.random.default_rng(7)
    for _ in range(25):
        y = np.r_[np.zeros(3, dtype=int), np.ones(13, dtype=int)]
        a, b = rng.integers(0, 2, (2, len(y)))
        r = paired_transition(y, a, b)
        assert r["corrected"] - r["introduced"] == pytest.approx(r["delta_ba"])
        assert r["corrected"] + r["introduced"] == pytest.approx(r["disagreement"])


def test_run_negative_fractions_weight_people_before_cohort():
    records = []
    for person in range(1, 10):
        for run in range(1, 4 if person == 1 else 3):
            for method in ("frozen", "lda_only", "full_csp", "ea_csp"):
                for label in (0, 1):
                    prediction = 1 - label if person == run == 1 and method == "ea_csp" else label
                    records.append(dict(dataset="BNCI2014-001", participant=f"sub-{person:02d}",
                                        session="E", run=f"run-{run}", method=method, budget="full",
                                        trial_id=f"sub-{person}/run-{run}/trial-{label}",
                                        label=label, prediction=prediction))
    _, _, people, cohort = run_tables(records)
    negative = next(r for r in cohort if r["contrast"] == "ea_minus_full"
                    and r["run_effect_sign"] == "negative")
    assert negative["mean"] == pytest.approx(1 / 27)
    assert negative["mean"] != pytest.approx(1 / 19)
    assert next(r for r in people if r["participant"] == "sub-01"
                and r["contrast"] == "ea_minus_full")["negative_fraction"] == pytest.approx(1 / 3)


def test_joint_distribution_retains_all_nine_categories_and_ties():
    rows = []
    for person in range(1, 10):
        ba, weak = {1: (0.1, 0.2), 2: (0.1, 0), 3: (-0.1, 0.1)}.get(person, (0, 0))
        rows.append(dict(dataset="BNCI2014-001", participant=f"sub-{person:02d}",
                         budget="full", contrast="ea_minus_full", subset="all_query", status="ok",
                         delta_ba=ba, delta_weak_recall=weak, delta_recall_gap=0,
                         delta_recall_left=0, delta_recall_right=0, corrected=0,
                         introduced=0, disagreement=0, endpoint_positive_fraction=0,
                         endpoint_zero_fraction=0, endpoint_negative_fraction=0))
    _, _, joint = summarize_participants([], rows)
    assert len(joint) == 9 and sum(r["count"] for r in joint) == 9
    count = {(r["ba_sign"], r["weak_recall_sign"]): r["count"] for r in joint}
    assert count["positive", "positive"] == count["positive", "zero"] == count["negative", "positive"] == 1
    assert count["zero", "zero"] == 6
