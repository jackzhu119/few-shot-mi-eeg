"""Protocol checks that protect the subject/session boundary and inference unit."""

import hashlib
import json
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.base import BaseEstimator

from learning_preserving_bci.adaptation import FixedDecoderPolicy, parameter_distance
from learning_preserving_bci.evaluation import (
    bootstrap_subject_mean,
    evaluate_fixed_decoder,
    leave_one_subject_out,
    paired_subject_statistics,
    within_subject_session_split,
)
from learning_preserving_bci.utils import collect_provenance, write_result_json


def protocol_data():
    subjects = np.repeat(["s1", "s2"], 8)
    sessions = np.tile(np.repeat(["z_reference", "a_heldout"], 4), 2)
    y = np.tile([0, 1, 0, 1], 4)
    X = np.zeros((16, 2, 3))
    X[:, 0, 0] = np.repeat([1, 2], 8)
    X[:, 0, 1] = np.tile(np.repeat([0, 1], 4), 2)
    X[:, 1, 0] = y
    return SimpleNamespace(X=X, y=y, subjects=subjects, sessions=sessions, is_synthetic=True)


class AuditDecoder(BaseEstimator):
    fitted_trials = []

    def fit(self, X, y):
        self.fitted = True
        self.fitted_trials.append(X[:, 0, :2].copy())
        return self

    def predict(self, X):
        assert self.fitted
        # A perfect toy decoder checks scoring independently of training quality.
        return X[:, 1, 0].astype(int)


def test_fixed_decoder_fits_reference_once_per_subject_and_keeps_template_unfitted():
    data = protocol_data()
    template = AuditDecoder()
    AuditDecoder.fitted_trials = []
    result = evaluate_fixed_decoder(data, template, reference_session="z_reference", seed=17)
    assert not hasattr(template, "fitted")
    assert len(AuditDecoder.fitted_trials) == 2
    for seen in AuditDecoder.fitted_trials:
        assert np.unique(seen[:, 0]).size == 1
        assert np.all(seen[:, 1] == 0)
    assert result["synthetic"] is True
    assert result["subject_balanced_accuracy"] == {"s1": 1.0, "s2": 1.0}
    assert result["provenance"]["seed"] == 17
    assert len(result["per_subject_session"]) == 2
    assert "not evidence of online independent control" in result["interpretation"]
    for record in result["per_subject_session"]:
        train = record["training_trial_indices"]
        test = record["evaluation_trial_indices"]
        assert not set(train) & set(test)
        assert len(train) == record["n_training_trials"]
        assert len(test) == record["n_evaluation_trials"]
        assert set(data.subjects[train]) == {record["subject"]}
        assert set(data.subjects[test]) == {record["subject"]}
        assert set(data.sessions[train]) == {record["reference_session"]}
        assert set(data.sessions[test]) == {record["evaluation_session"]}
        assert record["y_true"] == data.y[test].tolist()
        assert record["y_pred"] == data.X[test, 1, 0].astype(int).tolist()


def test_trial_log_preserves_string_class_labels_as_strict_json():
    data = protocol_data()
    data.y = np.array(["left" if label == 0 else "right" for label in data.y])

    class StringAuditDecoder(AuditDecoder):
        def predict(self, X):
            return np.array(["left" if label == 0 else "right" for label in super().predict(X)])

    result = evaluate_fixed_decoder(data, StringAuditDecoder(), "z_reference")
    json.dumps(result, allow_nan=False)
    for record in result["per_subject_session"]:
        assert record["y_true"] == data.y[record["evaluation_trial_indices"]].tolist()
        assert record["y_pred"] == record["y_true"]


def test_fixed_protocol_rejects_uncloneable_potentially_prefitted_decoder():
    class NonCloneableDecoder:
        def fit(self, X, y):
            return self

        def predict(self, X):
            return np.zeros(len(X), dtype=int)

    with pytest.raises(TypeError, match="cloneable sklearn-style"):
        evaluate_fixed_decoder(protocol_data(), NonCloneableDecoder(), "z_reference")


def test_evaluation_seeds_global_rng_per_subject_and_fills_only_unset_estimator_seeds():
    class RandomProbeDecoder(BaseEstimator):
        training_random_numbers = []

        def __init__(self, random_state=None):
            self.random_state = random_state

        def fit(self, X, y):
            self.training_random_numbers.append(np.random.random(8))
            return self

        def predict(self, X):
            return np.random.RandomState(self.random_state).randint(0, 2, len(X))

    data = protocol_data()
    RandomProbeDecoder.training_random_numbers = []
    np.random.seed(900)
    first = evaluate_fixed_decoder(data, RandomProbeDecoder(), "z_reference", seed=31)
    np.random.seed(1001)
    second = evaluate_fixed_decoder(data, RandomProbeDecoder(), "z_reference", seed=31)
    assert first == second
    draws = RandomProbeDecoder.training_random_numbers
    assert len(draws) == 4
    assert all(np.array_equal(draws[0], draw) for draw in draws[1:])
    assert all(
        record["effective_decoder_configuration"]["random_state"] == 31
        for record in first["per_subject_session"]
    )
    explicit = evaluate_fixed_decoder(
        data, RandomProbeDecoder(random_state=17), "z_reference", seed=31
    )
    assert all(
        record["effective_decoder_configuration"]["random_state"] == 17
        for record in explicit["per_subject_session"]
    )


def test_explicit_reference_session_does_not_follow_lexical_order():
    data = protocol_data()
    split = within_subject_session_split(data, "s1", "z_reference", "a_heldout")
    assert set(data.sessions[split.train_indices]) == {"z_reference"}
    assert set(data.sessions[split.test_indices]) == {"a_heldout"}
    assert not np.intersect1d(split.train_indices, split.test_indices).size
    with pytest.raises(ValueError, match="differ"):
        within_subject_session_split(data, "s1", "z_reference", "z_reference")


def test_leave_one_subject_out_excludes_all_held_out_sessions():
    data = protocol_data()
    folds = list(leave_one_subject_out(data))
    assert len(folds) == 2
    for split in folds:
        assert not set(data.subjects[split.train_indices]) & set(data.subjects[split.test_indices])
        assert set(data.sessions[split.test_indices]) == {"z_reference", "a_heldout"}


def test_fixed_protocol_rejects_reference_leakage_and_missing_class():
    data = protocol_data()
    with pytest.raises(ValueError, match="exclude"):
        evaluate_fixed_decoder(data, AuditDecoder(), "z_reference", ["z_reference"])
    data.y[(data.subjects == "s1") & (data.sessions == "a_heldout")] = 0
    with pytest.raises(ValueError, match="same classes"):
        evaluate_fixed_decoder(data, AuditDecoder(), "z_reference")


def test_subject_specific_reference_mapping():
    result = evaluate_fixed_decoder(
        protocol_data(), AuditDecoder(), {"s1": "z_reference", "s2": "a_heldout"}
    )
    assert result["per_subject_session"][1]["reference_session"] == "a_heldout"


def test_exact_paired_sign_flip_and_bootstrap_use_subjects():
    first = {"s1": 0.8, "s2": 0.8, "s3": 0.8, "s4": 0.8}
    second = dict(reversed([(subject, 0.6) for subject in first]))
    result = paired_subject_statistics(first, second, n_resamples=200, seed=3)
    assert result["unit"] == "subject"
    assert result["n_subjects"] == 4
    assert result["mean_difference_a_minus_b"] == pytest.approx(0.2)
    assert result["confidence_interval"] == pytest.approx([0.2, 0.2])
    assert result["p_value_two_sided"] == pytest.approx(2 / 16)
    assert result["n_permutations_tested"] == 16
    zero = paired_subject_statistics(first, first, n_resamples=200)
    assert zero["p_value_two_sided"] == 1
    assert zero["confidence_interval"] == [0, 0]


def test_paired_subject_alignment_is_independent_of_second_mapping_insertion_order():
    scores_a = {1: 0.85, "2": 0.65, 3: 0.75}
    scores_b = {3: 0.6, "2": 0.55, 1: 0.7}
    reversed_b = dict(reversed(list(scores_b.items())))
    first = paired_subject_statistics(scores_a, scores_b, n_resamples=200, seed=3)
    second = paired_subject_statistics(scores_a, reversed_b, n_resamples=200, seed=3)
    assert first == second
    assert first["mean_difference_a_minus_b"] == pytest.approx((0.15 + 0.1 + 0.15) / 3)


def test_subject_statistics_reject_ambiguous_string_identifiers_in_any_insertion_order():
    scores_a = {1: 0.9, "1": 0.7, "s3": 0.8}
    scores_b = {1: 0.6, "1": 0.65, "s3": 0.7}
    for paired in (scores_b, dict(reversed(list(scores_b.items())))):
        with pytest.raises(ValueError, match="ambiguous"):
            paired_subject_statistics(scores_a, paired, n_resamples=200)
    with pytest.raises(ValueError, match="ambiguous"):
        bootstrap_subject_mean(scores_a, n_resamples=200)


def test_subject_statistics_reject_trial_vectors_nonfinite_and_unpaired_subjects():
    with pytest.raises(TypeError, match="mapping"):
        bootstrap_subject_mean([0.6, 0.7])
    with pytest.raises(ValueError, match="finite"):
        bootstrap_subject_mean({"s1": np.nan, "s2": 0.7})
    with pytest.raises(ValueError, match="matching"):
        paired_subject_statistics({"s1": 0.6, "s2": 0.7}, {"s2": 0.7, "s3": 0.8})


def test_subject_bootstrap_is_reproducible_and_contains_nonconstant_mean():
    scores = {"s1": 0.55, "s2": 0.65, "s3": 0.8, "s4": 0.9}
    first = bootstrap_subject_mean(scores, n_resamples=300, seed=7)
    second = bootstrap_subject_mean(scores, n_resamples=300, seed=7)
    assert first == second
    low, high = first["confidence_interval"]
    assert low < first["mean"] < high


def test_result_json_requires_synthetic_flag_and_rejects_nonfinite(tmp_path):
    path = tmp_path / "result.json"
    with pytest.raises(ValueError, match="synthetic"):
        write_result_json(path, {"value": 1})
    with pytest.raises(ValueError):
        write_result_json(path, {"synthetic": True, "value": np.nan})
    assert not path.exists()
    write_result_json(path, {"synthetic": True, "subject": np.int64(2), "values": np.array([0.5])})
    assert '"synthetic": true' in path.read_text()


def test_result_json_rejects_overwrite_without_altering_evidence(tmp_path):
    path = tmp_path / "result.json"
    original = {"synthetic": False, "balanced_accuracy": 0.7}
    write_result_json(path, original)
    evidence = path.read_bytes()
    with pytest.raises(FileExistsError, match="already exists"):
        write_result_json(path, {"synthetic": False, "balanced_accuracy": 0.9})
    assert path.read_bytes() == evidence
    with pytest.raises(ValueError):
        write_result_json(path, {"synthetic": False, "balanced_accuracy": np.inf}, overwrite=True)
    assert path.read_bytes() == evidence
    assert list(tmp_path.iterdir()) == [path]


def test_provenance_hashes_current_sources_and_configs_without_a_commit(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    source = tmp_path / "src" / "example" / "decoder.py"
    config = tmp_path / "configs" / "nested" / "test.json"
    source.parent.mkdir(parents=True)
    config.parent.mkdir(parents=True)
    source.write_text("threshold = 0.5\n", encoding="utf-8")
    config.write_text('{"seed": 42}\n', encoding="utf-8")
    # Input data and unrelated files are outside the declared code/config scope.
    (tmp_path / "data.json").write_text('{"not": "configuration"}\n', encoding="utf-8")
    provenance = collect_provenance(42, tmp_path)
    assert provenance["git_commit"] is None
    assert provenance["git_dirty"] is True
    assert provenance["source_config_sha256"] == {
        "src/example/decoder.py": hashlib.sha256(source.read_bytes()).hexdigest(),
        "configs/nested/test.json": hashlib.sha256(config.read_bytes()).hexdigest(),
    }
    previous_digest = provenance["source_config_sha256"]["src/example/decoder.py"]
    source.write_text("threshold = 0.7\n", encoding="utf-8")
    updated = collect_provenance(42, tmp_path)
    assert updated["source_config_sha256"]["src/example/decoder.py"] != previous_digest
    assert (
        updated["source_config_sha256"]["configs/nested/test.json"]
        == provenance["source_config_sha256"]["configs/nested/test.json"]
    )


def test_parameter_distance_and_fixed_policy_copy():
    distance = parameter_distance({"w": np.array([3.0, 4.0])}, {"w": np.array([3.0, 8.0])})
    assert distance["relative_l2_distance"] == pytest.approx(4 / 5)
    assert parameter_distance({"w": np.zeros(2)}, {"w": np.ones(2)})["relative_l2_distance"] is None
    with pytest.raises(ValueError, match="identical"):
        parameter_distance({"a": np.ones(2)}, {"b": np.ones(2)})
    fitted = AuditDecoder()
    fitted.fitted = True
    policy = FixedDecoderPolicy(fitted)
    fitted.fitted = False
    assert np.array_equal(policy.predict(protocol_data().X[:4]), [0, 1, 0, 1])
