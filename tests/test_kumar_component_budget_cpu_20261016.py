"""Synthetic-only checks for the isolated component/budget CPU replay.

Every array in this module is generated locally.  These checks never load real
EEG, historical model NPZ files, weights, or a historical query tensor.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.linalg import helmert
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_kumar_component_budget_cpu_20261016.py"


@pytest.fixture(scope="module")
def budget():
    spec = importlib.util.spec_from_file_location("component_budget_cpu_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SyntheticCSP:
    """A four-feature estimator with observable fits and immutable transforms."""

    def __init__(self, events, n_components=4):
        self.events = events
        self.n_components = n_components

    def fit(self, X, y):
        self.events.append(("csp_fit", np.asarray(X).copy(), np.asarray(y).copy()))
        self.filters_ = np.eye(X.shape[1])
        self.patterns_ = np.eye(X.shape[1])
        self.mean_ = np.zeros(self.n_components)
        self.std_ = np.ones(self.n_components)
        return self

    def transform(self, X):
        self.events.append(("csp_transform", np.asarray(X).copy(), None))
        return np.log(np.square(np.asarray(X)[:, :self.n_components]).mean(axis=2))

    def fit_transform(self, X, y):
        return self.fit(X, y).transform(X)


def synthetic_source_arrays():
    """A hand-constructed frozen state, never read from a historical artifact."""
    return {
        "n_components": np.asarray(4, dtype=np.int64),
        "csp_filters": np.eye(22), "csp_patterns": np.eye(22),
        "csp_mean": np.zeros(4), "csp_std": np.ones(4),
        "lda_classes": np.asarray([0, 1]),
        "lda_coef": np.asarray([[-1., 1., 0., 0.]]),
        "lda_intercept": np.asarray([0.]),
        "lda_means": np.asarray([[1., 0., 0., 0.], [0., 1., 0., 0.]]),
        "lda_priors": np.asarray([.5, .5]), "lda_covariance": np.eye(4),
    }


def synthetic_input():
    rng = np.random.default_rng(20261016)
    data, labels, trials = [], [], []
    for session, run, role, count in [
        ("ses-0", "run-0", "source_train", 20),
        ("ses-0", "run-1", "source_train", 20),
        ("ses-1", "run-0", "target_support", 20),
        ("ses-1", "run-1", "target_query", 8),
        ("ses-2", "run-0", "target_support", 20),
        ("ses-2", "run-1", "target_query", 8),
    ]:
        for row in range(1, count + 1):
            label = 0 if role == "target_support" and row <= 4 else row % 2
            epoch = rng.normal(size=(22, 96))
            epoch[label] *= 3
            epoch -= epoch.mean(axis=0, keepdims=True)
            data.append(epoch)
            labels.append(label)
            trials.append({
                "trial_id": f"sub-1/{session}/{run}/row-{row}",
                "subject": "sub-1", "cohort": "development", "session": session,
                "run": run, "role": role, "source_row": row, "start_sample": row * 100,
                "acquisition_time_utc": "2020-01-01T00:00:00+00:00",
                "synthetic": True, "software_validation_only": True,
            })
    # Numeric acquisition order must win over input/lexicographic identity order.
    order = rng.permutation(len(trials))
    return (np.asarray(data)[order], np.asarray(labels, dtype=np.int64)[order],
            [trials[index] for index in order])


def synthetic_factory(events):
    def make_model(*, n_components=4, random_state=None, **kwargs):
        return SimpleNamespace(named_steps={
            "csp": SyntheticCSP(events, n_components=n_components),
            "lda": LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
        })

    return make_model


def test_chronological_prefix_uses_acquisition_order_without_class_topup(budget):
    _, labels, trials = synthetic_input()
    selected = budget.chronological_indices(trials, "target_support", session="ses-1")
    expected = [index for index, row in enumerate(trials)
                if row["role"] == "target_support" and row["session"] == "ses-1"]
    expected.sort(key=lambda index: trials[index]["source_row"])
    assert list(selected) == expected
    assert [trials[index]["source_row"] for index in selected[:4]] == [1, 2, 3, 4]
    assert labels[selected[:4]].tolist() == [0, 0, 0, 0]
    assert all(trials[index]["session"] == "ses-1" for index in selected)


def test_chronological_selection_does_not_inspect_labels(budget):
    _, _, trials = synthetic_input()
    initial = budget.chronological_indices(trials, "target_support", session="ses-1")
    changed = copy.deepcopy(trials)
    for row in changed:
        row["label"] = object()
    np.testing.assert_array_equal(
        initial, budget.chronological_indices(changed, "target_support", session="ses-1"))


def exact_full_rank_car_trials(scale=1.):
    """An exactly centered, nonsingular design in the 21-dimensional CAR space."""
    basis = helmert(22)
    coordinates = np.concatenate([np.eye(21), -np.eye(21)], axis=1)
    coordinates *= np.linspace(.8, 1.2, 21)[:, None] * scale
    epoch = basis.T @ coordinates
    return np.repeat(epoch[None], 4, axis=0)


def synthetic_saved_predictions(labels, trials):
    rows = []
    for method in ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda"):
        for index, trial in enumerate(trials):
            if trial["role"] != "target_query":
                continue
            predicted = {"source_only": 0, "frozen_csp_lda_recalibration": 1 - labels[index],
                         "refit_csp_lda": labels[index]}[method]
            rows.append({
                "subject": trial["subject"], "session": trial["session"], "run": trial["run"],
                "method": method, "trial_id": trial["trial_id"], "label": int(labels[index]),
                "prediction": int(predicted), "synthetic": True,
                "software_validation_only": True,
            })
    rows.extend({"subject": "sub-1", "session": "ses-0", "run": "run-3",
                 "method": "source_only", "trial_id": f"synthetic/source-query/{label}",
                 "label": label, "prediction": label, "synthetic": True,
                 "software_validation_only": True} for label in (0, 1))
    return rows


def execute_synthetic(budget, *, X=None, y=None, trials=None, saved=None, output=None,
                      factory=None):
    if X is None:
        X, y, trials = synthetic_input()
    if saved is None:
        saved = synthetic_saved_predictions(y, trials)
    events = []
    arrays = synthetic_source_arrays()
    config = {"budgets": [4, 8, 12, 16, "full"], "synthetic": True, "seed": 42}
    result = budget.run_budget_subject(
        X, y, trials, arrays, saved, config, output=output,
        model_factory=factory or synthetic_factory(events))
    return result, events


def test_ea_whitens_21_basis_and_reembeds_the_22_car_projector(budget):
    X = exact_full_rank_car_trials()
    H = budget.helmert_matrix()
    np.testing.assert_allclose(H @ H.T, np.eye(21), atol=1e-14)
    np.testing.assert_allclose(H @ np.ones(22), 0, atol=1e-14)
    reference = budget.ea_reference(X)
    np.testing.assert_allclose(
        reference["reference"], np.mean([np.cov(H @ epoch) for epoch in X], axis=0),
        atol=1e-14)
    whitened = budget.ea_transform(X, reference)
    covariance_21 = np.mean([np.cov(H @ epoch) for epoch in whitened], axis=0)
    covariance_22 = np.mean([np.cov(epoch) for epoch in whitened], axis=0)
    np.testing.assert_allclose(covariance_21, np.eye(21), atol=3e-14)
    np.testing.assert_allclose(covariance_22, np.eye(22) - np.ones((22, 22)) / 22,
                               atol=3e-14)
    np.testing.assert_allclose(whitened.sum(axis=1), 0, atol=1e-14)


def test_ea_retains_raw_covariance_scale_and_removes_common_mode(budget):
    X = exact_full_rank_car_trials()
    reference = budget.ea_reference(X)
    scaled_reference = budget.ea_reference(3 * X)
    np.testing.assert_allclose(scaled_reference["reference"], 9 * reference["reference"],
                               rtol=1e-13, atol=1e-14)
    np.testing.assert_allclose(scaled_reference["inverse_sqrt"], reference["inverse_sqrt"] / 3,
                               rtol=1e-13, atol=1e-14)
    common = np.linspace(-3, 5, X.shape[-1])[None, None, :]
    np.testing.assert_allclose(budget.ea_transform(X + common, reference),
                               budget.ea_transform(X, reference), atol=3e-14)
    np.testing.assert_allclose(budget.ea_transform(3 * X, scaled_reference),
                               budget.ea_transform(X, reference), atol=3e-14)


@pytest.mark.parametrize("case", ["zero", "ill_conditioned"])
def test_ea_unestimable_reference_is_explicit_fallback_without_ridge(budget, case):
    X = exact_full_rank_car_trials()
    if case == "zero":
        X.fill(0)
    else:
        H = helmert(22)
        coordinates = np.einsum("kc,nct->nkt", H, X)
        coordinates[:, 0] *= 1e-7
        X = np.einsum("ck,nkt->nct", H.T, coordinates)
    with pytest.raises(budget.ScientificFallback, match="nonpositive|condition"):
        budget.ea_reference(X)


def test_all_budgets_use_exact_current_prefix_and_immutable_inputs(budget, tmp_path):
    X, y, trials = synthetic_input()
    arrays = synthetic_source_arrays()
    original = (X.copy(), y.copy(), copy.deepcopy(trials),
                {key: value.copy() for key, value in arrays.items()})
    events = []
    result = budget.run_budget_subject(
        X, y, trials, arrays, synthetic_saved_predictions(y, trials),
        {"budgets": [4, 8, 12, 16, "full"], "synthetic": True, "seed": 42},
        output=tmp_path / "synthetic", model_factory=synthetic_factory(events))
    np.testing.assert_array_equal(X, original[0])
    np.testing.assert_array_equal(y, original[1])
    assert trials == original[2]
    for key, value in arrays.items():
        np.testing.assert_array_equal(value, original[3][key])
    assert result["source_parameter_sha256_before"] == result["source_parameter_sha256_after"]
    source = {row["trial_id"] for row in trials if row["role"] == "source_train"}
    query = {row["trial_id"] for row in trials if row["role"] == "target_query"}
    for audit in result["fit_audits"]:
        session = audit["session"]
        support = sorted([row for row in trials if row["role"] == "target_support"
                          and row["session"] == session], key=lambda row: row["source_row"])
        size = 10 if audit["budget"] == "support_half_CV" else (
            20 if audit["budget"] == "full" else int(audit["budget"]))
        prefix = {row["trial_id"] for row in support[:size]}
        if audit["historical_predictions_reused"]:
            assert audit["fit_attempted_in_this_replay"] is False
            assert audit["fit_completed_in_this_replay"] is False
            assert audit["fit_ids_scope"] == "original_historical_fit"
            assert set(audit["fit_trial_ids"]) == (source if audit["method"] == "source_only"
                                                    else source | prefix)
        else:
            assert set(audit["fit_trial_ids"]) == source | prefix
            assert len(audit["fit_trial_ids"]) == 40 + size
        for field in ("fit_trial_ids", "reference_source_trial_ids", "reference_target_trial_ids"):
            assert query.isdisjoint(audit[field])
        if audit["method"] == "ea_csp_lda":
            assert set(audit["reference_source_trial_ids"]) == source
            assert set(audit["reference_target_trial_ids"]) == prefix
    # A single-class target prefix is preserved; the two-class source union is estimable.
    first_budget = [row for row in result["metrics"] if row["budget"] == "4"]
    assert len(first_budget) == 8
    assert all(row["support_missing_class"] and row["support_left"] == 4
               and row["support_right"] == 0 and not row["fallback"] for row in first_budget)
    for feature in result["features"]:
        assert feature["holdout_defined"] is True
        assert feature["support_cv_lda_gain"] == pytest.approx(
            feature["holdout_BA_lda_only"] - feature["holdout_BA_frozen"])
        assert feature["support_cv_full_gain"] == pytest.approx(
            feature["holdout_BA_full_refit"] - feature["holdout_BA_frozen"])
    for proof in result["provenance"]["rows"]:
        assert set(proof["source_trial_ids"]) == source
        assert query.isdisjoint(value for values in proof.values() if isinstance(values, list)
                                for value in values)
        assert set(proof["support_train_half_trial_ids"]).isdisjoint(
            proof["support_holdout_trial_ids"])
        assert set(proof["support_trial_ids"]) == (set(proof["support_train_half_trial_ids"])
                                                    | set(proof["support_holdout_trial_ids"]))
    receipt = json.loads((tmp_path / "synthetic/subject_receipt.json").read_text())
    assert receipt["synthetic"] and receipt["software_validation_only"]
    assert result["synthetic"] and result["software_validation_only"]


def test_frozen_and_full_old_three_reuse_saved_predictions_without_fit_or_forward(
        budget, monkeypatch):
    X, y, trials = synthetic_input()
    saved = synthetic_saved_predictions(y, trials)
    calls = []
    original = budget._fit_predict

    def observed(method, X, y, fit_indices, eval_indices, *args, **kwargs):
        calls.append((method, len(fit_indices), len(eval_indices)))
        return original(method, X, y, fit_indices, eval_indices, *args, **kwargs)

    monkeypatch.setattr(budget, "_fit_predict", observed)
    result, _ = execute_synthetic(budget, X=X, y=y, trials=trials, saved=saved)
    assert not any(method == "source_only" for method, _, _ in calls)
    assert not any(method in budget.OLD_METHODS and count == 60 for method, count, _ in calls)
    saved_by_identity = {(row["method"], row["trial_id"]): row["prediction"] for row in saved}
    for row in result["predictions"]:
        reused = row["method"] == "source_only" or (
            row["budget"] == "full" and row["method"] in budget.OLD_METHODS)
        assert row["historical_predictions_reused"] is reused
        if reused:
            assert row["prediction"] == saved_by_identity[row["method"], row["trial_id"]]
    full = [row for row in result["metrics"] if row["budget"] == "full"]
    assert {row["balanced_accuracy"] for row in full if row["method"] == "source_only"} == {.5}
    assert {row["balanced_accuracy"] for row in full
            if row["method"] == "frozen_csp_lda_recalibration"} == {0.}
    assert {row["balanced_accuracy"] for row in full if row["method"] == "refit_csp_lda"} == {1.}


def test_query_signal_and_labels_cannot_change_fits_features_or_provenance(budget):
    X, y, trials = synthetic_input()
    first, first_events = execute_synthetic(budget, X=X, y=y, trials=trials)
    query = [index for index, row in enumerate(trials) if row["role"] == "target_query"]
    X[query] *= 500
    y[query] = 1 - y[query]
    changed, changed_events = execute_synthetic(budget, X=X, y=y, trials=trials)
    assert first["features"] == changed["features"]
    assert first["provenance"] == changed["provenance"]
    assert first["fit_audits"] == changed["fit_audits"]
    original_fits = [event for event in first_events if event[0] == "csp_fit"]
    changed_fits = [event for event in changed_events if event[0] == "csp_fit"]
    assert len(original_fits) == len(changed_fits) > 0
    for left, right in zip(original_fits, changed_fits, strict=True):
        np.testing.assert_array_equal(left[1], right[1])
        np.testing.assert_array_equal(left[2], right[2])


def test_missing_holdout_class_remains_missing_and_marks_fallback(budget):
    X, y, trials = synthetic_input()
    for index, row in enumerate(trials):
        if row["role"] == "target_support" and row["source_row"] > 10:
            y[index] = 0
    result, _ = execute_synthetic(budget, X=X, y=y, trials=trials)
    for feature in result["features"]:
        assert feature["holdout_defined"] is False
        assert feature["holdout_fallback_frozen"] is True
        assert feature["holdout_missing_reason"] == "holdout_missing_true_class"
        assert [feature[key] for key in ("holdout_BA_frozen", "holdout_BA_lda_only",
                                         "holdout_BA_full_refit")] == [None, None, None]
        assert feature["support_cv_lda_gain"] == feature["support_cv_full_gain"] == 0
    assert not any(row["budget"] == "support_half_CV" for row in result["fit_audits"])


def test_predefined_scientific_failure_falls_back_but_unexpected_errors_propagate(
        budget, monkeypatch):
    def unestimable(*args, **kwargs):
        raise budget.ScientificFallback("synthetic_predefined_unestimable")

    monkeypatch.setattr(budget, "_fit_predict", unestimable)
    result, _ = execute_synthetic(budget)
    for row in result["metrics"]:
        if not row["historical_predictions_reused"]:
            assert row["fallback"]
            assert row["fallback_reason"] == "synthetic_predefined_unestimable"
            assert row["balanced_accuracy"] == .5
    for audit in result["fit_audits"]:
        assert audit["fit_completed_in_this_replay"] is False
        assert audit["fit_attempted_in_this_replay"] is (not audit["historical_predictions_reused"])

    def unexpected(*args, **kwargs):
        raise ValueError("synthetic unexpected estimator failure")

    monkeypatch.setattr(budget, "_fit_predict", unexpected)
    with pytest.raises(ValueError, match="unexpected estimator failure"):
        execute_synthetic(budget)


def test_covariance_drift_weights_trials_equally_before_averaging(budget):
    source = exact_full_rank_car_trials()[:2].copy()
    source[1, :4] *= 20
    support = exact_full_rank_car_trials()[:2].copy()
    support[0, 5:8] *= 3

    def independently_average_normalized(epochs):
        covariances = [np.cov(epoch) for epoch in epochs]
        return sum(covariance / np.trace(covariance) for covariance in covariances) / len(epochs)

    expected = np.linalg.norm(independently_average_normalized(source)
                              - independently_average_normalized(support), "fro")
    actual = budget.trace_normalized_covariance_drift(source, support)
    assert actual == pytest.approx(expected, abs=1e-14)
    wrong_source = np.mean([np.cov(epoch) for epoch in source], axis=0)
    wrong_support = np.mean([np.cov(epoch) for epoch in support], axis=0)
    wrong = np.linalg.norm(wrong_source / np.trace(wrong_source)
                           - wrong_support / np.trace(wrong_support), "fro")
    assert abs(actual - wrong) > .01


@pytest.mark.parametrize("occupied", ["directory", "file", "dangling_symlink"])
def test_fresh_output_is_required_before_any_fit(budget, tmp_path, occupied):
    output = tmp_path / "occupied"
    if occupied == "directory":
        output.mkdir()
    elif occupied == "file":
        output.write_bytes(b"SYNTHETIC PRESERVE ME")
    else:
        output.symlink_to(tmp_path / "absent")

    def forbidden_factory(**kwargs):
        pytest.fail("Existing output must be refused before fitting")

    with pytest.raises((FileExistsError, ValueError), match="fresh|exist"):
        execute_synthetic(budget, output=output, factory=forbidden_factory)
    if occupied == "file":
        assert output.read_bytes() == b"SYNTHETIC PRESERVE ME"
    if occupied == "dangling_symlink":
        assert output.is_symlink()


def test_source_model_hash_failure_precedes_any_array_deserialization(budget, tmp_path, monkeypatch):
    subject = tmp_path / "sub-1"
    subject.mkdir()
    participant = subject / "participant_receipt.json"
    participant.write_text(json.dumps({
        "source_frozen": True, "source_parameter_sha256_before": "a" * 64,
        "source_parameter_sha256_after": "a" * 64,
    }))
    artifact = subject / "source_before.npz"
    artifact.write_bytes(b"SYNTHETIC OPAQUE CORRUPT BYTES, NEVER AN NPZ MODEL")
    (tmp_path / "execution_receipt.json").write_text(json.dumps({"outputs": {
        "sub-1/participant_receipt.json": budget.sha256_file(participant),
        "sub-1/source_before.npz": "b" * 64,
    }}))

    def forbidden_load(*args, **kwargs):
        pytest.fail("A hash-mismatched model must not be deserialized")

    monkeypatch.setattr(np, "load", forbidden_load)
    with pytest.raises(ValueError, match="SHA|hash"):
        budget.load_verified_source_model(tmp_path, "sub-1")


@pytest.mark.parametrize("change", ["duplicate", "missing", "session", "run", "label", "synthetic"])
def test_saved_predictions_require_exact_identity_and_scope(budget, change):
    X, y, trials = synthetic_input()
    saved = synthetic_saved_predictions(y, trials)
    if change == "duplicate":
        saved.append(saved[0].copy())
    elif change == "missing":
        saved.pop(0)
    elif change == "label":
        saved[0]["label"] = 1 - saved[0]["label"]
    else:
        saved[0][change] = {"session": "ses-9", "run": "run-9", "synthetic": False}[change]
    with pytest.raises((ValueError, KeyError)):
        execute_synthetic(budget, X=X, y=y, trials=trials, saved=saved)


@pytest.fixture
def synthetic_model_directory(budget, tmp_path):
    arrays = synthetic_source_arrays()
    directory = tmp_path / "sub-1"
    directory.mkdir()
    for name in ("source_before.npz", "source_after.npz"):
        np.savez_compressed(directory / name, **arrays)
    participant = directory / "participant_receipt.json"
    participant.write_text(json.dumps({
        "source_frozen": True, "synthetic": True, "software_validation_only": True,
        "source_parameter_sha256_before": budget.array_digest(arrays),
        "source_parameter_sha256_after": budget.array_digest(arrays),
    }))

    def reseal():
        receipt = {"synthetic": True, "software_validation_only": True,
                   "outputs": {f"sub-1/{path.name}": budget.sha256_file(path)
                               for path in directory.iterdir()}}
        (tmp_path / "execution_receipt.json").write_text(json.dumps(receipt))

    reseal()
    return tmp_path, arrays, reseal


def test_synthetic_source_before_after_are_hash_bound_and_pickle_free(
        budget, synthetic_model_directory, monkeypatch):
    root, expected, _ = synthetic_model_directory
    original = np.load
    opened = []

    def observed(path, *args, **kwargs):
        assert Path(path).parent == root / "sub-1"
        assert kwargs.get("allow_pickle") is False
        opened.append(Path(path).name)
        return original(path, *args, **kwargs)

    before = {path.name: path.read_bytes() for path in (root / "sub-1").iterdir()}
    monkeypatch.setattr(np, "load", observed)
    loaded = budget.load_verified_source_model(root, "sub-1")
    assert opened == ["source_before.npz", "source_after.npz"]
    assert loaded.keys() == expected.keys()
    for key in expected:
        np.testing.assert_array_equal(loaded[key], expected[key])
    assert before == {path.name: path.read_bytes() for path in (root / "sub-1").iterdir()}


@pytest.mark.parametrize("change", ["after_parameters", "schema", "participant_hash"])
def test_source_loader_rejects_changed_after_state_schema_or_receipt(
        budget, synthetic_model_directory, change):
    root, arrays, reseal = synthetic_model_directory
    if change == "after_parameters":
        arrays["lda_intercept"] = np.asarray([100.])
        np.savez_compressed(root / "sub-1/source_after.npz", **arrays)
        reseal()  # Byte integrity is insufficient if learned state differs.
    elif change == "schema":
        arrays["n_components"] = np.asarray(2, dtype=np.int64)
        np.savez_compressed(root / "sub-1/source_before.npz", **arrays)
        reseal()
    else:
        path = root / "sub-1/participant_receipt.json"
        path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="digest|four components|hash"):
        budget.load_verified_source_model(root, "sub-1")


def test_one_real_mne_fit_accepts_ea_reembedded_synthetic_car22(budget):
    import mne
    from learning_preserving_bci.decoders.csp_lda import make_csp_lda

    X, y, trials = synthetic_input()
    original_X = X.copy()
    source = budget.chronological_indices(trials, "source_train")
    support = budget.chronological_indices(trials, "target_support", "ses-1")[:4]
    query = budget.chronological_indices(trials, "target_query", "ses-1")
    fitted, checkpoint = [], []

    def real_factory(**kwargs):
        model = make_csp_lda(**kwargs)
        fitted.append(model)
        return model

    with mne.use_log_level("ERROR"):
        prediction = budget._fit_predict(
            "ea_csp_lda", X, y, source + support, query, synthetic_source_arrays(),
            real_factory, 42, source, support, model_sink=checkpoint.append)
    assert len(fitted) == 1
    assert prediction.shape == (8,) and set(prediction.tolist()) <= {0, 1}
    csp, lda = fitted[0].named_steps["csp"], fitted[0].named_steps["lda"]
    assert csp.n_components == 4 and csp.filters_.shape[1] == 22
    assert csp.reg == "ledoit_wolf" and csp.norm_trace is False and csp.log is True
    transformed_query = budget.ea_transform(X[query], budget.ea_reference(X[support]))
    features = csp.transform(transformed_query)
    assert features.shape == (8, 4) and np.isfinite(features).all()
    assert lda.coef_.shape == (1, 4)
    np.testing.assert_array_equal(prediction, lda.predict(features))
    assert len(checkpoint) == 1
    np.testing.assert_array_equal(prediction, replay_checkpoint_with_numpy(checkpoint[0], X[query]))
    np.testing.assert_array_equal(X, original_X)


def replay_checkpoint_with_numpy(arrays, X):
    """Independent binary CSP/LDA replay, including the saved EA target map."""
    if "ea_helmert" in arrays:
        H = arrays["ea_helmert"]
        mapping = H.T @ arrays["ea_target_inverse_sqrt"] @ H
        X = np.einsum("kc,nct->nkt", mapping, X)
    projected = np.einsum("kc,nct->nkt", arrays["csp_filters"][:int(arrays["n_components"])], X)
    features = np.log(np.square(projected).mean(axis=2))
    score = features @ arrays["lda_coef"].T + arrays["lda_intercept"]
    return arrays["lda_classes"][(score[:, 0] > 0).astype(int)]


def test_every_successful_synthetic_fit_has_one_exact_replayable_checkpoint(
        budget, tmp_path, monkeypatch):
    X, y, trials = synthetic_input()
    states = tmp_path / "private_synthetic_model_states"
    events, captured, opened = [], {}, []
    original_fit, original_load = budget._fit_predict, np.load

    def observe_fit(method, X, y, fit_indices, eval_indices, *args, **kwargs):
        predicted = original_fit(method, X, y, fit_indices, eval_indices, *args, **kwargs)
        key = (method, tuple(trials[index]["trial_id"] for index in fit_indices),
               tuple(trials[index]["trial_id"] for index in eval_indices))
        assert key not in captured
        captured[key] = predicted.copy()
        return predicted

    def only_created_checkpoints(path, *args, **kwargs):
        assert Path(path).parent == states
        assert kwargs.get("allow_pickle") is False
        opened.append(Path(path))
        return original_load(path, *args, **kwargs)

    monkeypatch.setattr(budget, "_fit_predict", observe_fit)
    monkeypatch.setattr(np, "load", only_created_checkpoints)
    result = budget.run_budget_subject(
        X, y, trials, synthetic_source_arrays(), synthetic_saved_predictions(y, trials),
        {"budgets": [4, 8, 12, 16, "full"], "synthetic": True, "seed": 42},
        output=tmp_path / "synthetic_results", model_factory=synthetic_factory(events),
        model_sink=lambda context, arrays: budget.save_model_state(states, context, arrays))
    base_keys = set(synthetic_source_arrays())
    ea_keys = {"ea_helmert", "ea_source_reference", "ea_source_inverse_sqrt",
               "ea_target_reference", "ea_target_inverse_sqrt"}
    trial_index = {trial["trial_id"]: index for index, trial in enumerate(trials)}
    completed = [audit for audit in result["fit_audits"] if audit["fit_completed_in_this_replay"]]
    assert len(completed) == len(captured) == len(list(states.glob("*.npz"))) == 30
    assert all(not audit["fallback"] for audit in result["fit_audits"])
    replayed_cv = 0
    for audit in result["fit_audits"]:
        if audit["historical_predictions_reused"]:
            assert audit["model_states"] == []
            continue
        assert len(audit["model_states"]) == 1
        record = audit["model_states"][0]
        path = Path(record["path"])
        assert path.is_file() and path.stat().st_size == record["bytes"]
        assert record["sha256"] == budget.sha256_file(path)
        assert record["allow_pickle"] is False and record["private_model_state"] is True
        with np.load(path, allow_pickle=False) as archive:
            arrays = {key: archive[key].copy() for key in archive.files}
        assert all(not array.dtype.hasobject for array in arrays.values())
        expected_keys = base_keys | (ea_keys if audit["method"] == "ea_csp_lda" else set())
        assert set(arrays) == expected_keys == set(record["array_keys"])
        assert budget.array_digest(arrays) == record["array_sha256"]
        evaluation_ids = (audit["support_holdout_trial_ids"] if audit["budget"] == "support_half_CV"
                          else audit["query_trial_ids"])
        selected = [trial_index[identifier] for identifier in evaluation_ids]
        predicted = replay_checkpoint_with_numpy(arrays, X[selected])
        key = (audit["method"], tuple(audit["fit_trial_ids"]), tuple(evaluation_ids))
        np.testing.assert_array_equal(predicted, captured[key])
        if audit["budget"] == "support_half_CV":
            replayed_cv += 1
            feature = next(row for row in result["features"] if row["session"] == audit["session"])
            field = {"frozen_csp_lda_recalibration": "holdout_BA_lda_only",
                     "refit_csp_lda": "holdout_BA_full_refit"}[audit["method"]]
            assert budget.balanced_accuracy(y[selected], predicted) == feature[field]
        else:
            saved = [row["prediction"] for row in result["predictions"]
                     if row["session"] == audit["session"] and row["budget"] == audit["budget"]
                     and row["method"] == audit["method"]]
            np.testing.assert_array_equal(predicted, saved)
    assert replayed_cv == 4
    assert len(opened) == 60  # Thirty fresh readbacks and thirty independent replays.


@pytest.mark.parametrize("failure", ["storage", "hash"])
def test_checkpoint_storage_or_hash_failure_propagates_and_stops_fitting(
        budget, tmp_path, monkeypatch, failure):
    X, y, trials = synthetic_input()
    states, output = tmp_path / "private_synthetic_model_states", tmp_path / "uncreated_results"
    calls, hash_calls = [], []
    original_fit, original_hash = budget._fit_predict, budget.sha256_file

    def observed_fit(method, *args, **kwargs):
        calls.append(method)
        return original_fit(method, *args, **kwargs)

    monkeypatch.setattr(budget, "_fit_predict", observed_fit)
    if failure == "storage":
        def storage_failure(*args, **kwargs):
            raise OSError("synthetic checkpoint storage failure")

        monkeypatch.setattr(np, "savez_compressed", storage_failure)
        error, message = OSError, "checkpoint storage failure"
    else:
        def changed_readback_hash(path):
            assert Path(path).parent == states
            hash_calls.append(Path(path))
            return original_hash(path) if len(hash_calls) == 1 else "f" * 64

        monkeypatch.setattr(budget, "sha256_file", changed_readback_hash)
        error, message = ValueError, "Checkpoint fresh readback/hash mismatch"
    with pytest.raises(error, match=message):
        budget.run_budget_subject(
            X, y, trials, synthetic_source_arrays(), synthetic_saved_predictions(y, trials),
            {"budgets": [4, 8, 12, 16, "full"], "synthetic": True, "seed": 42},
            output=output, model_factory=synthetic_factory([]),
            model_sink=lambda context, arrays: budget.save_model_state(states, context, arrays))
    assert calls == ["frozen_csp_lda_recalibration"]
    assert len(list(states.glob("*.npz"))) == 1  # Preserve failed persistence evidence.
    assert not output.exists()  # No fallback result or later fit can be published.
    if failure == "hash":
        assert len(hash_calls) == 2
