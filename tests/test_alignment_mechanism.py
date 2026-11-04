"""Software-only tests of the fixed four-arm sensitivity."""
import inspect
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from learning_preserving_bci.alignment_mechanism import (
    common_rms, fit_mechanism, helmert, numeric_digest, reference, score,
)


def synthetic():
    rng = np.random.default_rng(170)
    x = rng.normal(size=(20, 6, 96))
    y = np.arange(20) % 2
    x[y == 0, 0] *= 2
    x[y == 1, 1] *= 2
    x -= x.mean(axis=1, keepdims=True)
    return x, y


def test_helmert_effective_coordinates():
    h = helmert(22)
    np.testing.assert_allclose(h @ h.T, np.eye(21), atol=1e-14)
    np.testing.assert_allclose(h.T @ h, np.eye(22) - np.ones((22, 22)) / 22, atol=1e-14)
    np.testing.assert_allclose(h @ np.ones(22), 0, atol=1e-14)


@pytest.mark.parametrize("dataset", ["kumar", "bnci"])
@pytest.mark.parametrize("method", ["full", "rms_full", "diagonal_ea", "ea"])
def test_query_permutation_batch_and_model_state_are_fixed(dataset, method):
    x, y = synthetic()
    model = fit_mechanism(x[:12], y[:12], x[12:16], y[12:16], method, dataset)
    before = numeric_digest(model.state_arrays())
    predicted, probability = model.predict(x[16:]), model.predict_probability(x[16:])
    np.testing.assert_array_equal(model.predict(x[16:][::-1]), predicted[::-1])
    np.testing.assert_allclose(model.predict_probability(x[16:][::-1]), probability[::-1], atol=1e-12)
    np.testing.assert_array_equal(model.predict(x[16:17]), predicted[:1])
    altered = x[16:].copy()
    altered[-1] *= 30
    np.testing.assert_array_equal(model.predict(altered)[:-1], predicted[:-1])
    assert numeric_digest(model.state_arrays()) == before
    assert model.metadata["query_used_for_fitting"] is False
    assert "query" not in inspect.signature(fit_mechanism).parameters
    # Query labels are used only here, after one fixed fitted model and predictions.
    a, b = score(y[16:], predicted, probability), score(1 - y[16:], predicted, probability)
    assert a["balanced_accuracy"] == 1 - b["balanced_accuracy"]
    assert numeric_digest(model.state_arrays()) == before


def test_reference_is_spd_and_whitens_training_covariance():
    x, _ = synthetic()
    h = helmert(6)
    projected = np.einsum("kc,nct->nkt", h, x)
    matrix, inverse, info = reference(projected)
    np.testing.assert_allclose(matrix, matrix.T, atol=1e-14)
    np.testing.assert_allclose(inverse @ matrix @ inverse.T, np.eye(5), atol=1e-12)
    assert min(info["eigenvalues"]) > 0
    diagonal, _, _ = reference(projected, diagonal=True)
    np.testing.assert_array_equal(diagonal, np.diag(np.diag(matrix)))


def test_missing_source_class_nonfinite_and_empty_stop():
    x, y = synthetic()
    with pytest.raises(ValueError, match="Binary source"):
        fit_mechanism(x[:12], np.zeros(12), x[12:16], y[12:16], "full", "kumar")
    with pytest.raises(ValueError, match="nonempty"):
        fit_mechanism(x[:12], y[:12], x[:0], y[:0], "ea", "bnci")
    bad = x[:12].copy()
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        fit_mechanism(bad, y[:12], x[12:16], y[12:16], "full", "kumar")
    # The binary source supplies both classes even when the fixed support is one class.
    assert fit_mechanism(x[:12], y[:12], x[12:16], np.zeros(4), "full", "bnci")


def test_no_zero_energy_reference_and_common_scalar_rms():
    with pytest.raises(ValueError, match="RMS"):
        common_rms(np.zeros((2, 3, 20)))
    with pytest.raises(ValueError, match="Nonpositive"):
        reference(np.zeros((2, 3, 20)))
    x, _ = synthetic()
    out = common_rms(x)
    np.testing.assert_allclose(np.square(out).mean(axis=(1, 2)), 1)
    np.testing.assert_allclose(out[0] / x[0], np.full_like(x[0], out[0, 0, 0] / x[0, 0, 0]))


def test_class_balanced_probability_metrics_and_undefined():
    y = np.array([0, 0, 0, 1])
    result = score(y, np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.7]))
    assert result["balanced_accuracy"] == (2 / 3 + 1) / 2
    expected = ((0.1**2 + 0.2**2 + 0.8**2) / 3 + 0.3**2) / 2
    assert result["balanced_brier_single_coordinate"] == pytest.approx(expected)
    assert result["weak_recall"] == pytest.approx(result["balanced_accuracy"] - result["recall_gap"] / 2)
    assert score(np.array([0]), np.array([1]))["balanced_accuracy"] is None


@pytest.mark.parametrize("error", [OSError("disk write failed"), ValueError("model hash integrity failure")])
def test_storage_or_hash_failure_preserves_claim_and_does_not_refit(tmp_path, monkeypatch, error):
    path = Path(__file__).parents[1] / "scripts/run_paper2_alignment_mechanisms_20261104.py"
    spec = importlib.util.spec_from_file_location("mechanism_runner_test", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    run = runner.Run(tmp_path / "out", tmp_path / "models", 60)
    attempts = []
    class Dummy:
        metadata = {}
        def state_arrays(self):
            return {"state": np.eye(2)}
        def predict(self, x):
            return np.asarray([0, 1])
        def predict_probability(self, x):
            return np.asarray([.1, .9])
    def fit():
        attempts.append(1)
        return Dummy()
    def fail(*args):
        raise error
    monkeypatch.setattr(runner, "model_write", fail)
    context = {"query_ids": ["q0", "q1"]}
    with pytest.raises(type(error), match=str(error)):
        run.cell("cell", context, fit, np.zeros((2, 2, 10)), np.asarray([0, 1]))
    assert len(attempts) == 1
    assert (run.output / "claims/cell.json").exists()
    assert not (run.output / "cells/cell.json").exists()
    with pytest.raises(RuntimeError, match="Unresolved prior attempt"):
        run.cell("cell", context, fit, np.zeros((2, 2, 10)), np.asarray([0, 1]))
    assert len(attempts) == 1


def test_phase_undefined_query_is_explicit_without_a_fit():
    path = Path(__file__).parents[1] / "scripts/run_paper2_alignment_mechanisms_20261104.py"
    spec = importlib.util.spec_from_file_location("mechanism_runner_phase_test", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    support = [{"label": 0}, {"label": 1}]
    assert runner.phase_undefined_status(support, [{"label": 0}]) == "undefined_query_missing_class"
    assert runner.phase_undefined_status(support, []) == "undefined_query_missing_class"
    assert runner.phase_undefined_status([], support) == "undefined_empty_support"
    assert runner.phase_undefined_status(support, support) is None
    assert runner.phase_undefined_status(support, support, original_status="undefined_support_phase_access_incomplete") == "undefined_support_phase_access_incomplete"
    assert runner.phase_undefined_status(support, support, original_status="undefined_source_model") == "undefined_source_model"


def test_resume_window_uses_original_time_and_cannot_extend(tmp_path, monkeypatch):
    import json
    path = Path(__file__).parents[1] / "scripts/run_paper2_alignment_mechanisms_20261104.py"
    spec = importlib.util.spec_from_file_location("mechanism_runner_clock_test", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    output = tmp_path / "run01"
    output.mkdir()
    (tmp_path / "dispatch_run01.json").write_text(json.dumps({"spawned_at_utc": "2026-11-04T06:00:00+00:00", "command": ["python", "runner"]}))
    window = runner.operation_window(output, 7200, resume=True)
    assert window["deadline_epoch"] - window["first_dispatch_epoch"] == 7200
    monkeypatch.setattr(runner.time, "time", lambda: window["deadline_epoch"] + 1)
    assert runner.operation_window(output, 7200, resume=True) == window
    with pytest.raises(ValueError, match="cannot extend"):
        runner.operation_window(output, 8000, resume=True)
    run = runner.Run(output, tmp_path / "models", 7200, resume=True)
    attempts = []
    def fit():
        attempts.append(1)
        raise AssertionError("Expired operation must not fit")
    with pytest.raises(TimeoutError, match="bounded"):
        run.cell("new", {"query_ids": ["q"]}, fit, np.zeros((1, 2, 10)), np.asarray([0]))
    assert not attempts
