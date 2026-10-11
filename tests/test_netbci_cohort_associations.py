"""Independent numerical and evidence-grain checks; software fixtures only."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_netbci_cohort_associations import (
    PAIRS,
    SESSIONS,
    SUBJECTS,
    analyze,
    association_statistics,
    participant_values,
)


def association_rows(x, y):
    return [{"subject": f"fixture-{i}", "CSP_BA_change_pp": a, "behavior_change_pp": b,
             "mu_task_contrast_change_dB": i + 1., "all_six_AIRM_session04": i + .5,
             "all_six_PCA_subspace_session04": (i + 1) / 10}
            for i, (a, b) in enumerate(zip(x, y, strict=True))]


def test_perfect_paired_correlation_stays_perfect_when_subjects_are_resampled():
    rows = association_rows([1, 2, 3, 4], [13, 16, 19, 22])
    subjects = [row["subject"] for row in rows]
    estimates = association_statistics(rows[::-1], subjects, seed=42, repetitions=300)
    assert len(estimates) == 10
    for row in estimates[:2]:
        assert row["estimate"] == pytest.approx(1)
        assert row["participant_bootstrap_CI95_low"] == pytest.approx(1)
        assert row["participant_bootstrap_CI95_high"] == pytest.approx(1)
        assert row["n_complete_paired_participants"] == 4
        assert row["complete_subjects"] == ",".join(subjects)
        assert row["bootstrap_valid_draws"] + row["bootstrap_degenerate_draws"] == 300


def test_pearson_and_tied_spearman_match_independent_accepted_estimators():
    x, y = [1, 1, 2, 3], [1, 2, 2, 4]
    rows = association_rows(x, y)
    estimates = association_statistics(rows, [row["subject"] for row in rows], 8, 100)
    assert estimates[0]["estimate"] == pytest.approx(np.corrcoef(x, y)[0, 1])
    assert estimates[1]["estimate"] == pytest.approx(spearmanr(x, y).statistic)
    assert estimates[0]["estimate"] != pytest.approx(estimates[1]["estimate"])


def test_paired_bootstrap_intervals_match_an_independent_scalar_oracle():
    x, y = np.array([0., 2., 5., 7.]), np.array([4., 2., 3., 9.])
    rows = association_rows(x, y)
    estimates = association_statistics(rows, [row["subject"] for row in rows], 18, 200)
    draws = np.random.default_rng(18).integers(0, 4, (200, 4))
    for method, saved in zip(("Pearson_r", "Spearman_rho"), estimates[:2], strict=True):
        bootstrap = []
        for draw in draws:
            sampled_x, sampled_y = x[draw], y[draw]
            if len(set(draw)) < 2 or np.ptp(sampled_x) == 0 or np.ptp(sampled_y) == 0:
                continue
            statistic = (np.corrcoef(sampled_x, sampled_y)[0, 1] if method == "Pearson_r"
                         else spearmanr(sampled_x, sampled_y).statistic)
            bootstrap.append(statistic)
        assert [saved["participant_bootstrap_CI95_low"], saved["participant_bootstrap_CI95_high"]] == pytest.approx(
            np.quantile(bootstrap, [.025, .975]))
        assert saved["bootstrap_valid_draws"] == len(bootstrap)
        assert saved["bootstrap_degenerate_draws"] == 200 - len(bootstrap)


def test_constant_variable_is_unavailable_and_every_degenerate_draw_is_counted():
    rows = association_rows([2, 2, 2], [1, 2, 3])
    estimates = association_statistics(rows, [row["subject"] for row in rows], 42, 100)
    for saved in estimates[:2]:
        assert saved["estimate"] is None
        assert saved["participant_bootstrap_CI95_low"] is None
        assert saved["participant_bootstrap_CI95_high"] is None
        assert saved["bootstrap_valid_draws"] == 0
        assert saved["bootstrap_degenerate_draws"] == 100
        assert saved["bootstrap_fewer_than_two_distinct_subject_draws"] + saved["bootstrap_zero_variance_other_draws"] == 100


def test_missing_variables_retain_subjects_and_two_person_degeneracy_is_explicit():
    rows = association_rows([None, 2, 4], [1000, 3, 5])
    estimates = association_statistics(rows, [row["subject"] for row in rows], 42, 200)
    draws = np.random.default_rng(42).integers(0, 2, (200, 2))
    for saved in estimates[:2]:
        assert saved["n_requested_participants"] == 3
        assert saved["n_complete_paired_participants"] == 2
        assert saved["unavailable_subjects"] == "fixture-0"
        assert saved["complete_subjects"] == "fixture-1,fixture-2"
        assert saved["estimate"] == pytest.approx(1)
        assert saved["bootstrap_degenerate_draws"] == int((draws[:, 0] == draws[:, 1]).sum())
    rows[1]["CSP_BA_change_pp"] = rows[2]["CSP_BA_change_pp"] = None
    unavailable = association_statistics(rows, [row["subject"] for row in rows], 42, 200)[0]
    assert unavailable["estimate"] is None and unavailable["n_complete_paired_participants"] == 0
    assert unavailable["bootstrap_repetitions_attempted"] == 0
    assert unavailable["bootstrap_degenerate_draws"] == 0


@pytest.mark.parametrize("error", ["duplicate", "missing", "unexpected", "nonfinite", "boolean"])
def test_association_statistics_rejects_invalid_participant_or_metric_evidence(error):
    rows = association_rows([1, 2, 3], [2, 3, 4])
    subjects = [row["subject"] for row in rows]
    if error == "duplicate":
        rows.append(rows[0].copy())
    elif error == "missing":
        rows.pop()
    elif error == "unexpected":
        rows[0]["subject"] = "unverified"
    else:
        rows[0]["CSP_BA_change_pp"] = np.nan if error == "nonfinite" else True
    with pytest.raises(ValueError):
        association_statistics(rows, subjects, 42, 10)


def session_fixture(subjects=SUBJECTS):
    joined, matching = [], []
    for i, subject in enumerate(subjects):
        for position, session in enumerate(SESSIONS):
            joined.append({"subject": subject, "session": session,
                "join_grain": "verified_participant_session_only", "mean_run_hit_percent": 10 + i + position,
                "CSP_BA_percent": 50 + i + 2 * position, "mu_MI_minus_rest_dB": -.1 * i - position})
            for variant in ("all_six_runs", "qc_common_four_runs"):
                matching.append({"subject": subject, "session": session, "variant": variant,
                    "status": "available", "AIRM_to_session01": position * (i + 1),
                    "PCA_subspace_distance": position / 10})
    return joined, matching


def test_changes_are_computed_within_identity_and_missing_endpoint_is_not_imputed():
    subjects = ("fixture-a", "fixture-b")
    joined, matching = session_fixture(subjects)
    joined[0]["CSP_BA_percent"] = ""
    values = participant_values(joined[::-1], matching[::-1], subjects)
    assert values[0]["subject"] == subjects[0]
    assert values[0]["CSP_BA_session01_percent"] is None
    assert values[0]["CSP_BA_change_pp"] is None
    assert values[0]["behavior_change_pp"] == 3
    assert values[0]["mu_task_contrast_change_dB"] == -3
    assert values[1]["CSP_BA_change_pp"] == 6
    assert values[1]["all_six_AIRM_session04"] == 6


@pytest.mark.parametrize("error", ["duplicate_session", "missing_session", "bad_grain", "trial_broadcast",
                                  "nonfinite_session", "fraction_confusion", "duplicate_geometry", "missing_geometry",
                                  "wrong_variant", "nonzero_source_drift", "unavailable_with_value", "PCA_range"])
def test_summary_grain_geometry_and_metric_integrity_are_required(error):
    subjects = ("fixture-a", "fixture-b")
    joined, matching = session_fixture(subjects)
    if error == "duplicate_session":
        joined.append(joined[0].copy())
    elif error == "missing_session":
        joined.pop()
    elif error == "bad_grain":
        joined[0]["join_grain"] = "trial"
    elif error == "trial_broadcast":
        joined[0]["trial_id"] = "invented_behavior_trial"
    elif error == "nonfinite_session":
        joined[0]["mu_MI_minus_rest_dB"] = "nan"
    elif error == "fraction_confusion":
        joined[0]["CSP_BA_percent"] = 5000
    elif error == "duplicate_geometry":
        matching.append(matching[0].copy())
    elif error == "missing_geometry":
        matching.pop()
    elif error == "wrong_variant":
        matching[0]["variant"] = "unverified"
    elif error == "nonzero_source_drift":
        matching[0]["AIRM_to_session01"] = 1
    elif error == "unavailable_with_value":
        matching[0]["status"] = "unavailable"
    else:
        matching[-1]["PCA_subspace_distance"] = 1.01
    with pytest.raises(ValueError):
        participant_values(joined, matching, subjects)


def summary_fixture(tmp_path):
    source = tmp_path / "software_summary"
    source.mkdir()
    joined, matching = session_fixture()
    for name, rows in (("participant_session_join.tsv", joined), ("participant_matched_geometry.tsv", matching)):
        with (source / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
    (source / "cohort_summary.json").write_text(json.dumps({"synthetic": False, "subjects": list(SUBJECTS), "participants": 10}))
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source.iterdir()}
    (source / "summary_receipt.json").write_text(json.dumps({"status": "actual_data_summary_completed",
                                                           "synthetic": False, "output_sha256": hashes}))
    plan = {"pairs": [pair[0] for pair in PAIRS], "estimators": ["Pearson_r", "Spearman_rho"],
            "n_requested": 10, "bootstrap": {"seed": 42, "repetitions": 10000},
            "changes": "session04_minus_session01", "p_values": False, "hypothesis_confirmation": False, "causal_claims": False}
    plan_path = tmp_path / "software_estimator_plan.json"
    plan_path.write_text(json.dumps(plan))
    return source, plan_path


def test_hash_verified_run_saves_all_participants_unavailable_correlations_and_output_hashes(tmp_path):
    source, plan = summary_fixture(tmp_path)
    output = tmp_path / "software_associations"
    result = analyze(source, output, plan)
    assert len(result["participants"]) == 10 and len(result["association_estimates"]) == 10
    assert all(row["estimate"] is None for row in result["association_estimates"])
    receipt = json.loads((output / "association_receipt.json").read_text())
    assert receipt["bootstrap_unit"] == "paired whole participant"
    assert receipt["p_values"] is False and receipt["causal_claims"] is False
    for name, expected in receipt["output_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    with pytest.raises(ValueError, match="Prior association output"):
        analyze(source, output, plan)


@pytest.mark.parametrize("error", ["changed_bytes", "rehashed_duplicate", "changed_plan"])
def test_source_hash_or_semantic_failure_does_not_create_partial_output(tmp_path, error):
    source, plan = summary_fixture(tmp_path)
    path = source / "participant_session_join.tsv"
    if error == "changed_plan":
        changed = json.loads(plan.read_text())
        changed["bootstrap"]["seed"] = 17
        plan.write_text(json.dumps(changed))
    else:
        lines = path.read_text().splitlines(keepends=True)
        path.write_text("".join(lines + [lines[1]]))
        if error == "rehashed_duplicate":
            receipt_path = source / "summary_receipt.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["output_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            receipt_path.write_text(json.dumps(receipt))
    output = tmp_path / "must_not_exist"
    with pytest.raises(ValueError):
        analyze(source, output, plan)
    assert not output.exists()
