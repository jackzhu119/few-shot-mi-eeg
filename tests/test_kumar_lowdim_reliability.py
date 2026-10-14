import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "lowdim_reliability", Path(__file__).parents[1] / "scripts/analyze_kumar_lowdim_reliability.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_fold_transform_is_invariant_to_heldout_perturbations():
    rng = np.random.default_rng(8)
    train, holdout = rng.normal(size=(20, 44)), rng.normal(size=(20, 44))
    ids = [f"train-{i}" for i in range(20)]
    scaler, pca, before = module.fit_coordinates(train, ids)
    first = module.transform_coordinates(holdout, scaler, pca)
    module.transform_coordinates(holdout * 1e8 + 1000, scaler, pca)
    scaler_again, pca_again, after = module.fit_coordinates(train, ids)
    assert before == after
    np.testing.assert_allclose(scaler.var_, train.var(axis=0, ddof=0))
    for candidate, coordinates in first.items():
        np.testing.assert_array_equal(coordinates, module.transform_coordinates(
            holdout, scaler_again, pca_again)[candidate])
    np.testing.assert_array_equal(first["motor6"], first["standardized44"][:, [18, 19, 20, 21, 22, 23]])


def test_known_reversed_holdout_and_zero_source_direction():
    labels = np.repeat([0, 1], 10)
    source = np.column_stack([labels * 2 - 1, np.zeros(20)])
    reversed_score = module.centroid_probe(source, labels, -source, labels)
    assert reversed_score["balanced_accuracy"] == 0
    zero = module.centroid_probe(np.zeros_like(source), labels, source, labels)
    assert zero["balanced_accuracy"] is None
    assert zero["direction_valid"] is False
    measured = module.support_measure(source, labels, -source, labels)
    assert measured["source_support_direction_cosine"] == -1
    assert measured["support_split_half_direction_cosine"] == 1
    assert all(value < 0 for value in measured["half_scalar_signed_contrasts_source_sd"])
    assert measured["half_scalar_product"] > 0
    zero_measure = module.support_measure(np.zeros_like(source), labels, source, labels)
    assert zero_measure["source_support_direction_cosine"] is None
    assert zero_measure["half_scalar_signed_contrasts_source_sd"] == [None, None]


def test_paired_shift_counts_shared_across_folds_and_candidates():
    labels = np.tile([0, 1], 10)
    coordinates = {c: np.column_stack([labels * 2 - 1, np.arange(20) / 100])
                   for c in module.CANDIDATES}
    folds = [{"train_run_index": a, "holdout_run_index": b,
              "train": coordinates, "holdout": coordinates} for a, b in ((0, 1), (1, 0))]
    result = module.source_phase_alignment_control(folds, [labels, labels])
    assert result["shift_pair_count"] == 400
    assert result["unique_rotated_label_assignments_per_run"] == [2, 2]
    assert result["unique_paired_label_assignments"] == 4
    assert result["diagnostic_centroid_probe_fit_attempts"] == 400 * 2 * 3
    for candidate in module.CANDIDATES:
        pairs = [[row["run0_shift"], row["run1_shift"]] for row in result["null"][candidate]]
        assert pairs == result["pairs"]
        assert len(result["observed"][candidate]) == 2
        assert result["null"][candidate][0]["twofold_balanced_accuracy"] == 1
        assert result["null"][candidate][1]["twofold_balanced_accuracy"] == 0


def test_support_shift_recomputes_halves_and_counts_fixed_half_invalidity():
    labels = np.tile([0, 0, 1, 1], 5)
    x = np.column_stack([labels * 2 - 1, np.arange(20)])
    result = module.support_phase_alignment_control(x, labels, x, labels)
    assert result["shift_count"] == 20
    assert result["unique_rotated_label_assignments"] == 4
    for row in result["null"]:
        assert row["recomputed_classwise_halves"]["valid_halves"]
    original = module.classwise_halves(labels)
    shifted = np.roll(labels, 1)
    assert not np.array_equal(module.classwise_halves(shifted)[0], original[0])
    # A fixed split whose later shifted labels become single-class is retained.
    fixed_halves = [np.arange(10), np.arange(10, 20)]
    single_class_labels = np.repeat([0, 1], 10)
    invalid = module.support_measure(x, labels, x, single_class_labels, fixed_halves)
    assert invalid["single_class_half_count"] == 2
    assert invalid["support_split_half_direction_cosine"] is None
    comparison = module.null_comparison(.5, [None, .6, .4])
    assert comparison["unavailable_control_count"] == 1
    assert comparison["valid_control_count"] == 2
    assert comparison["upper_tail_fraction_descriptive"] == .5


def metadata_fixture():
    rows = []
    for session, runs, role in [(0, [0, 1], "source_train")] + [
            (i, [0], "target_support") for i in range(1, 6)]:
        for run in runs:
            for row in range(1, 21):
                rows.append({"subject": "sub-1", "session": f"ses-{session}",
                             "run": f"run-{run}", "source_row": row,
                             "trial_id": f"sub-1/ses-{session}/run-{run}/row-{row}",
                             "role": role, "cohort": "development",
                             "label": "left_hand" if row <= 10 else "right_hand",
                             "start_sample": row * 100})
    return rows


@pytest.mark.parametrize("field,value,match", [
    ("role", "target_query", "Forbidden selected role"),
    ("cohort", "final_test", "Forbidden cohort"),
    ("subject", "sub-2", "Forbidden cohort"),
    ("session", "ses-2", "identity fields mismatch"),
])
def test_selected_query_final_and_identity_rows_rejected(field, value, match):
    metadata = metadata_fixture()
    module.validate_selected_metadata(metadata, 1)
    altered = copy.deepcopy(metadata)
    altered[0][field] = value
    with pytest.raises(ValueError, match=match):
        module.validate_selected_metadata(altered, 1)
    with pytest.raises(ValueError, match="Forbidden final"):
        module.validate_selected_metadata(metadata, 2)


def test_source_budget_and_duplicate_identity_rejected():
    metadata = metadata_fixture()
    with pytest.raises(ValueError, match="Source budget"):
        module.validate_selected_metadata(metadata[1:], 1)
    with pytest.raises(ValueError, match="Duplicate"):
        module.validate_selected_metadata(metadata + [metadata[0]], 1)


def test_bootstrap_uses_participant_means_and_preserves_missing_participant():
    values = dict(zip(module.DEVELOPMENT_SUBJECTS, [.1, .2, .3, .4, .5, .6], strict=True))
    result = module.participant_bootstrap(values)
    assert result["mean"] == pytest.approx(.35)
    assert len(result["bootstrap_draws"]) == 10000
    rng = np.random.default_rng(42)
    expected = np.array(list(values.values()))[rng.integers(0, 6, size=(10000, 6))].mean(axis=1)
    np.testing.assert_array_equal(result["bootstrap_draws"], expected)
    values[1] = None
    unavailable = module.participant_bootstrap(values)
    assert unavailable["status"] == "unavailable_missing_participant_value"
    assert unavailable["bootstrap_draws"] == []
    assert len(unavailable["participant_values"]) == 6


def test_complete_synthetic_subject_audit_is_json_serializable():
    metadata = metadata_fixture()
    labels = np.asarray([int(t["label"] == "right_hand") for t in metadata])
    rng = np.random.default_rng(4)
    x = rng.normal(size=(len(metadata), 44))
    x[:, 0] += labels
    result = module.analyze_subject(x, labels, metadata, 1)
    json.dumps(result, allow_nan=False)
    assert len(result["source_rows"]) == 3
    assert len(result["support_rows"]) == 15
    assert result["diagnostic_centroid_probe_fit_attempts"] == 2400
    assert result["support_fixed_source_axis_fit_attempts"] == 3
    states = result["coordinate_fit_states"]
    assert [state["fit_n"] for state in states] == [20, 20, 40]
    for row in result["support_rows"]:
        assert len(row["source_trial_ids"]) == 40
        assert len(row["support_trial_ids"]) == 20
        assert row["source_coordinate_state_sha256"] == states[-1]["state_sha256"]
