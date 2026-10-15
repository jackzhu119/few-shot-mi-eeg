"""Synthetic guards for supervised cache equivalence and signed diagnostics."""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "kumar_csp_reliability", Path(__file__).parents[1] / "scripts/analyze_kumar_csp_signed_score_v1.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MockSupervisedPipeline:
    """Bounded label-dependent substitute, never a claimed EEG estimator."""
    fits = 0
    predicts = 0

    def __init__(self, **kwargs):
        self.axis = None

    def fit(self, X, y):
        type(self).fits += 1
        self.axis = X[y == 1].mean(axis=0) - X[y == 0].mean(axis=0)
        self.threshold = float((X[y == 1].mean(axis=0) + X[y == 0].mean(axis=0)) @ self.axis / 2)
        return self

    def predict(self, X):
        type(self).predicts += 1
        return (X @ self.axis > self.threshold).astype(int)


def mock_state(model):
    return {"axis": model.axis, "threshold": np.asarray(model.threshold)}


def source_fixture():
    rng = np.random.default_rng(17)
    y0 = np.asarray([0, 1, 0, 0, 1, 1, 0, 1, 1, 0] * 2)
    y1 = np.roll(y0, 3)
    X0, X1 = rng.normal(size=(20, 3)), rng.normal(size=(20, 3))
    X0[:, 0] += y0 * 2
    X1[:, 0] += y1 * 2
    X = [X0, X1]
    folds = [{"train_run_index": a, "holdout_run_index": b,
              "train": X[a], "holdout": X[b],
              "train_trial_ids": [f"run{a}-{i}" for i in range(20)],
              "heldout_trial_ids": [f"run{b}-{i}" for i in range(20)]}
             for a, b in ((0, 1), (1, 0))]
    return folds, [y0, y1]


def test_cached_joint_control_exactly_matches_naive_label_dependent_refits(tmp_path):
    folds, labels = source_fixture()
    MockSupervisedPipeline.fits = MockSupervisedPipeline.predicts = 0
    result = module.source_phase_alignment_control(
        folds, labels, model_factory=MockSupervisedPipeline,
        state_extractor=mock_state, output=tmp_path)
    assert MockSupervisedPipeline.fits == 40
    assert MockSupervisedPipeline.predicts == 40
    assert result["pipeline_fit_attempts"] == result["pipeline_fit_successes"] == 40
    assert result["nominal_csp_and_lda_estimator_fit_attempts"] == 80
    assert result["heldout_prediction_rows"] == 800
    assert len(list(tmp_path.glob("*.npz"))) == 40
    states = {row["model_parameter_sha256"] for row in result["fit_rows"]}
    assert len(states) > 2  # Label changes alter supervised fitted state.
    for row, (shift0, shift1) in zip(result["null"], itertools.product(range(20), repeat=2), strict=True):
        shifted = [np.roll(labels[0], shift0), np.roll(labels[1], shift1)]
        expected = []
        for fold in folds:
            model = MockSupervisedPipeline().fit(fold["train"], shifted[fold["train_run_index"]])
            prediction = model.predict(fold["holdout"])
            heldout_y = shifted[fold["holdout_run_index"]]
            expected.append(np.mean([np.mean(prediction[heldout_y == k] == k) for k in (0, 1)]))
        np.testing.assert_array_equal(row["fold_balanced_accuracy"], expected)
        assert row["twofold_balanced_accuracy"] == np.mean(expected)
    assert result["null"][0]["twofold_balanced_accuracy"] == np.mean(
        [r["balanced_accuracy"] for r in result["observed"]])
    for row in result["fit_rows"]:
        with np.load(row["model_artifact"], allow_pickle=False) as saved:
            assert module.baseline.array_digest({k: saved[k] for k in saved.files}) == row["model_parameter_sha256"]


def test_cached_failures_preserve_400_rows_and_missing_denominators():
    folds, labels = source_fixture()

    class FailsOneShift(MockSupervisedPipeline):
        def fit(self, X, y):
            if np.array_equal(y, labels[0]):
                raise ValueError("synthetic singular fit")
            return super().fit(X, y)

    result = module.source_phase_alignment_control(
        folds, labels, model_factory=FailsOneShift, state_extractor=mock_state)
    assert len(result["null"]) == 400
    assert result["pipeline_fit_failures"] > 0
    assert any(row["twofold_balanced_accuracy"] is None for row in result["null"])
    comparison = module.lowdim.null_comparison(.5, [row["twofold_balanced_accuracy"] for row in result["null"]])
    assert comparison["total_control_count"] == 400
    assert comparison["unavailable_control_count"] > 0
    failures = [row for row in result["fit_rows"] if row["fit_status"] == "failed"]
    assert all(row["heldout_predictions"] is None and row["failure"]["type"] == "ValueError" for row in failures)


def test_signed_margin_keeps_offset_and_collapse_even_positive_contrast():
    labels = np.tile([0, 1], 10)
    source = np.column_stack([2 * labels - 1, np.arange(20) / 100, np.zeros((20, 2))])
    scores = 100 + 2 * labels - 1
    result = module.support_measure(source, labels, source, labels, scores, 1.0)
    assert result["support_split_half_direction_cosine"] == pytest.approx(1)
    assert all(x > 0 for x in result["half_LDA_signed_contrasts_source_sd"])
    for row in result["half_score_diagnostics"]:
        assert row["balanced_accuracy"] == .5
        assert row["class_collapse"] is True
        assert row["prediction_ratio"] == [0, 1]
        assert row["left_signed_score_mean_source_sd"] < 0
        assert row["right_signed_score_mean_source_sd"] > 0
        assert row["score_bias_mean_source_sd"] > 90
    assert result["target_score_centering_or_scaling"] is False


def test_reversed_support_preserves_both_negative_margins_positive_product():
    labels = np.tile([0, 1], 10)
    source = np.column_stack([2 * labels - 1, np.zeros((20, 3))])
    result = module.support_measure(source, labels, -source, labels, -(2 * labels - 1), 1.0)
    assert result["source_support_direction_cosine"] == -1
    assert result["support_split_half_direction_cosine"] == 1
    assert result["half_LDA_signed_contrasts_source_sd"] == [-1, -1]
    assert result["half_LDA_signed_contrast_product"] == 1
    assert all(row["balanced_accuracy"] == 0 for row in result["half_score_diagnostics"])


def test_phase_control_invalid_fixed_half_and_zero_source_sd_retained():
    labels = np.repeat([0, 1], 10)
    source = np.column_stack([2 * labels - 1, np.zeros((20, 3))])
    result = module.support_phase_alignment_control(source, labels, source, labels,
                                                   2 * labels - 1, 0.0)
    assert result["shift_count"] == 20
    assert len(result["null"]) == 20
    assert result["comparisons"]["recomputed_classwise_halves"]["invalid_source_score_sd_control_count"] == 20
    assert all(row["recomputed_classwise_halves"]["half_LDA_signed_contrasts_source_sd"] == [None, None]
               for row in result["null"])
    # Force a sensitivity split that is single-class, retained rather than rebalanced.
    measure = module.support_measure(source, labels, source, labels, labels.astype(float), 1,
                                     [np.arange(10), np.arange(10, 20)])
    assert measure["single_class_half_count"] == 2
    assert measure["half_LDA_signed_contrasts_source_sd"] == [None, None]


def metadata_fixture():
    rows = []
    for session, runs, role in [(0, [0, 1], "source_train")] + [(i, [0], "target_support") for i in range(1, 6)]:
        for run in runs:
            for i in range(1, 21):
                rows.append({"subject": "sub-1", "session": f"ses-{session}", "run": f"run-{run}",
                             "source_row": i, "start_sample": i * 100,
                             "trial_id": f"sub-1/ses-{session}/run-{run}/row-{i}",
                             "label": "left_hand" if i <= 10 else "right_hand",
                             "cohort": "development", "role": role,
                             "processed_numeric_unit": "V", "processed_sample_count": 640})
    return rows


def save_restricted(folder, metadata, X):
    folder.mkdir(exist_ok=True)
    metadata = copy.deepcopy(metadata)
    for epoch, row in zip(X, metadata, strict=True):
        row["processed_window_numeric_sha256"] = hashlib.sha256(epoch.tobytes(order="C")).hexdigest()
    meta_path, epoch_path = folder / "included_trial_metadata.json", folder / "restricted_epochs.npz"
    meta_path.write_text(json.dumps(metadata))
    np.savez_compressed(epoch_path, X=X,
                        y=np.asarray([int(t["label"] == "right_hand") for t in metadata], dtype=np.int64),
                        trial_ids=np.asarray([t["trial_id"] for t in metadata]))
    (folder / "subject_receipt.json").write_text(json.dumps({"metadata_sha256": module.file_digest(meta_path),
                                                          "epochs_sha256": module.file_digest(epoch_path)}))
    return metadata


@pytest.mark.parametrize("alteration", ["query", "final", "epoch_sha", "file_sha", "dtype"])
def test_restricted_access_and_tampering_rejected(tmp_path, alteration):
    metadata = metadata_fixture()
    X = np.random.default_rng(2).normal(size=(140, 22, 640)).astype("<f4")
    if alteration == "query":
        metadata[0]["role"] = "target_query"
    if alteration == "final":
        metadata[0]["cohort"] = "final_test"
    if alteration == "dtype":
        X = X.astype("<f8")
    saved = save_restricted(tmp_path, metadata, X)
    if alteration == "epoch_sha":
        saved[0]["processed_window_numeric_sha256"] = "0" * 64
        path = tmp_path / "included_trial_metadata.json"
        path.write_text(json.dumps(saved))
        receipt = json.loads((tmp_path / "subject_receipt.json").read_text())
        receipt["metadata_sha256"] = module.file_digest(path)
        (tmp_path / "subject_receipt.json").write_text(json.dumps(receipt))
    if alteration == "file_sha":
        with (tmp_path / "restricted_epochs.npz").open("ab") as handle:
            handle.write(b"corruption")
    with pytest.raises(ValueError):
        module.load_restricted_subject(tmp_path, 1)


def test_final_subject_rejected_before_opening_input(tmp_path):
    with pytest.raises(ValueError, match="Forbidden final"):
        module.load_restricted_subject(tmp_path, 2)


def test_source_state_replay_requires_exact_orientation_and_strict_zero_threshold():
    X = np.tile(np.arange(1, 5, dtype=float)[None, :, None], (3, 1, 8))
    arrays = {"n_components": np.asarray(4), "csp_filters": np.eye(4),
              "lda_classes": np.asarray([0, 1]), "lda_coef": np.zeros((1, 4)),
              "lda_intercept": np.asarray([0.0])}
    features, scores = module.csp_features_and_scores(arrays, X)
    np.testing.assert_allclose(features, np.log(np.square(X).mean(axis=-1)))
    assert module.score_summary(scores, np.asarray([0, 0, 1]))["prediction_ratio"] == [1, 0]
    arrays["lda_classes"] = np.asarray([1, 0])
    with pytest.raises(ValueError, match="binary class"):
        module.csp_features_and_scores(arrays, X)
