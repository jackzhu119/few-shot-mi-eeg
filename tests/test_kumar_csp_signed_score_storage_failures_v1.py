"""Synthetic failure boundaries only; no real EEG arrays, estimators or fits."""
from __future__ import annotations

import errno
import importlib.util
import re
from pathlib import Path

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location(
    "csp_signed_storage_boundary_consumer",
    Path(__file__).parents[1] / "scripts/analyze_kumar_csp_signed_score_v1.py",
)
consumer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consumer)


@pytest.fixture
def mock_control():
    """Track every constructor/fit/prediction using an explicit software fixture."""
    calls = {"constructed": 0, "fit": 0, "predict": 0, "extract": 0}
    labels = [np.tile([0, 1], 10), np.tile([1, 0], 10)]
    X = [np.ones((20, 3)), np.full((20, 3), 2.0)]
    folds = [{
        "train_run_index": a, "holdout_run_index": b,
        "train": X[a], "holdout": X[b],
        "train_trial_ids": [f"synthetic-run{a}-{i}" for i in range(20)],
        "heldout_trial_ids": [f"synthetic-run{b}-{i}" for i in range(20)],
    } for a, b in ((0, 1), (1, 0))]

    class MockPipeline:
        def __init__(self, **kwargs):
            calls["constructed"] += 1
            self.serial = calls["constructed"]

        def fit(self, X, y):
            calls["fit"] += 1
            return self

        def predict(self, X):
            calls["predict"] += 1
            return np.tile([0, 1], 10)

    def state(model):
        calls["extract"] += 1
        return {"mock_serial": np.asarray(model.serial),
                "synthetic": np.asarray(True),
                "software_validation_only": np.asarray(True)}

    def run(*, factory=MockPipeline, extractor=state, output=None):
        return consumer.source_phase_alignment_control(
            folds, labels, model_factory=factory, state_extractor=extractor, output=output)

    return calls, MockPipeline, state, run


def test_partial_write_failure_stops_before_a_third_fit(tmp_path, monkeypatch, mock_control):
    calls, _, _, run = mock_control
    save = consumer.np.savez_compressed
    writes = []

    def interrupted_write(path, **arrays):
        writes.append(Path(path))
        if len(writes) == 2:
            Path(path).write_bytes(b"synthetic=true; software_validation_only=true; partial")
            raise OSError(errno.ENOSPC, "Synthetic full output filesystem")
        return save(path, **arrays)

    monkeypatch.setattr(consumer.np, "savez_compressed", interrupted_write)
    with pytest.raises(OSError, match="Synthetic full output filesystem"):
        run(output=tmp_path)
    assert calls["constructed"] == calls["fit"] == calls["predict"] == 2
    assert len(writes) == 2
    assert writes[0].stat().st_size > 0
    assert writes[1].read_bytes().endswith(b"partial")
    assert len(list(tmp_path.glob("*.npz"))) == 2


@pytest.mark.parametrize("error", [
    OSError(errno.EIO, "Synthetic hash read I/O failure"),
    ValueError("Synthetic hash integrity failure"),
    np.linalg.LinAlgError("Synthetic unexpected hash error"),
])
def test_digest_failure_stops_before_a_third_fit_and_preserves_files(
        tmp_path, monkeypatch, mock_control, error):
    calls, _, _, run = mock_control
    digest, hashed = consumer.file_digest, []

    def failed_digest(path):
        hashed.append(Path(path))
        if len(hashed) == 2:
            raise error
        return digest(path)

    monkeypatch.setattr(consumer, "file_digest", failed_digest)
    with pytest.raises(type(error), match=re.escape(str(error))):
        run(output=tmp_path)
    assert calls["constructed"] == calls["fit"] == calls["predict"] == 2
    assert len(hashed) == 2
    assert len(list(tmp_path.glob("*.npz"))) == 2
    assert all(path.stat().st_size > 0 for path in hashed)


def test_only_fit_linear_algebra_failure_is_an_unavailable_attempt(mock_control):
    calls, MockPipeline, _, run = mock_control

    class SingularFirstFit(MockPipeline):
        def fit(self, X, y):
            super().fit(X, y)
            if calls["fit"] == 1:
                raise np.linalg.LinAlgError("Synthetic singular covariance eigensystem")
            return self

    result = run(factory=SingularFirstFit)
    assert calls["constructed"] == calls["fit"] == 40
    assert calls["predict"] == 39
    assert result["pipeline_fit_attempts"] == 40
    assert result["pipeline_fit_successes"] == 39
    assert result["pipeline_fit_failures"] == 1
    assert result["heldout_prediction_rows"] == 780
    first = result["fit_rows"][0]
    assert first["fit_status"] == "failed"
    assert first["failure"] == {"type": "LinAlgError",
                                "message": "Synthetic singular covariance eigensystem"}
    for key in ("heldout_predictions", "heldout_scores", "heldout_CSP_log_power4",
                "model_parameter_sha256", "model_artifact"):
        assert first[key] is None
    assert len(result["null"]) == 400
    assert sum(row["twofold_balanced_accuracy"] is None for row in result["null"]) == 20
    assert result["observed"][0]["balanced_accuracy"] is None


@pytest.mark.parametrize("error", [
    ValueError("Synthetic invalid fit input"),
    RuntimeError("Synthetic unexpected estimator error"),
    OSError(errno.ENOSPC, "Synthetic estimator storage failure"),
    MemoryError("Synthetic estimator memory exhaustion"),
])
def test_unexpected_fit_error_propagates_without_another_fit(mock_control, error):
    calls, MockPipeline, _, run = mock_control

    class UnexpectedFit(MockPipeline):
        def fit(self, X, y):
            super().fit(X, y)
            raise error

    with pytest.raises(type(error), match=re.escape(str(error))):
        run(factory=UnexpectedFit)
    assert calls["constructed"] == calls["fit"] == 1
    assert calls["predict"] == calls["extract"] == 0


@pytest.mark.parametrize("error", [
    ValueError("Synthetic invalid prediction"),
    np.linalg.LinAlgError("Synthetic prediction numerical error"),
    RuntimeError("Synthetic unexpected prediction error"),
])
def test_prediction_error_propagates_without_another_fit(mock_control, error):
    calls, MockPipeline, _, run = mock_control

    class UnexpectedPredict(MockPipeline):
        def predict(self, X):
            super().predict(X)
            raise error

    with pytest.raises(type(error), match=re.escape(str(error))):
        run(factory=UnexpectedPredict)
    assert calls["constructed"] == calls["fit"] == calls["predict"] == 1


def test_state_integrity_failure_propagates_without_another_fit(mock_control):
    calls, _, state, run = mock_control

    def changed_state(model):
        arrays = state(model)
        arrays["mock_serial"] = np.asarray(calls["extract"])
        return arrays

    with pytest.raises(ValueError, match="Heldout prediction changed model state"):
        run(extractor=changed_state)
    assert calls["constructed"] == calls["fit"] == calls["predict"] == 1


@pytest.mark.parametrize("mode", ["error", "mismatch"])
def test_replay_failure_propagates_without_another_fit(monkeypatch, mock_control, mode):
    calls, _, state, run = mock_control

    def replay_state(model):
        return {**state(model), "csp_filters": np.eye(3)}

    def replay(*args):
        if mode == "error":
            raise ValueError("Synthetic invalid frozen replay state")
        return np.ones((20, 4)), np.zeros(20)

    monkeypatch.setattr(consumer, "csp_features_and_scores", replay)
    with pytest.raises(ValueError, match=("Synthetic invalid" if mode == "error" else
                                          "pickle-free replay mismatch")):
        run(extractor=replay_state)
    assert calls["constructed"] == calls["fit"] == calls["predict"] == 1


def test_factory_numerical_error_is_not_a_fit_failure(mock_control):
    calls, _, _, run = mock_control

    def invalid_factory(**kwargs):
        raise np.linalg.LinAlgError("Synthetic constructor failure")

    with pytest.raises(np.linalg.LinAlgError, match="Synthetic constructor failure"):
        run(factory=invalid_factory)
    assert calls["fit"] == 0
