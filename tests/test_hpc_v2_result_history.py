"""Own synthetic local artifacts only; no model fitting or remote access."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

PATH = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2/result_history_export.py"
spec = importlib.util.spec_from_file_location("result_history_export", PATH)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


@pytest.fixture(autouse=True)
def restore_threads():
    previous = torch.get_num_threads()
    yield
    torch.set_num_threads(previous)


def checkpoint(tmp_path, **changes):
    state = {"schema_version": 1, "identity": "synthetic-only", "complete": True,
             "epoch": 2, "step": 4, "processed_samples": 8, "position": 0,
             "best_loss": 0.65, "best_epoch": 1, "checkpoint_at": "synthetic-time",
             "history": [{"epoch": 1, "train_loss": 0.7, "validation_loss": 0.65,
                          "learning_rate": 0.001}],
             "model": {"weights": torch.ones(3)}, "best_model": {"weights": torch.ones(3)},
             "optimizer": {"state": {"momentum": torch.ones(3)}},
             "rng": torch.get_rng_state(), "permutation": torch.arange(3),
             "extra": {"architecture_version": "synthetic", "dims": [3, 32],
                       "source_train_identity": "train-identity",
                       "normalization_mean": np.ones(3), "normalization_scale": np.ones(3)}}
    state.update(changes)
    path = tmp_path / "checkpoint.pt"
    torch.save(state, path)
    return path


def test_history_export_is_read_only_cpu_and_excludes_parameter_state(tmp_path, monkeypatch):
    path = checkpoint(tmp_path)
    before = path.read_bytes(), path.stat().st_mtime_ns
    load = torch.load
    calls = []

    def checked_load(item, **kwargs):
        calls.append(kwargs)
        return load(item, **kwargs)

    monkeypatch.setattr(torch, "load", checked_load)
    monkeypatch.setattr(torch.optim, "AdamW", lambda *a, **k: pytest.fail("optimizer constructed"))
    monkeypatch.setattr(torch.nn.Module, "__init__", lambda *a, **k: pytest.fail("model constructed"))
    result = history.extract_checkpoint(path)
    assert calls == [{"map_location": "cpu", "weights_only": False}]
    assert result["history"][0]["validation_loss"] == 0.65
    assert result["best_epoch"] == 1 and result["best_loss_status"] == "recorded"
    assert not ({"model", "best_model", "optimizer", "scheduler", "scaler", "rng", "permutation"} & result.keys())
    assert "normalization_mean" not in result["extra"]
    assert "normalization_scale" not in result["extra"]
    assert result["source_file"]["sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert result["source_file"]["bytes"] == len(before[0])
    assert before == (path.read_bytes(), path.stat().st_mtime_ns)
    json.dumps(result, allow_nan=False)


def test_adaptation_infinity_is_explicit_no_validation_null(tmp_path):
    path = checkpoint(tmp_path, best_loss=float("inf"),
                      history=[{"epoch": 1, "train_loss": 0.6, "learning_rate": 0.001}])
    result = history.extract_checkpoint(path)
    assert result["best_loss"] is None
    assert result["best_loss_status"] == "not_applicable_no_validation"
    json.dumps(result, allow_nan=False)


def test_initial_source_generation_distinguishes_pending_validation(tmp_path):
    path = checkpoint(tmp_path, complete=False, epoch=0, history=[], best_loss=float("inf"),
                      extra={"source_validation_identity": "synthetic-validation"})
    result = history.extract_checkpoint(path)
    assert result["best_loss"] is None
    assert result["best_loss_status"] == "not_yet_observed_validation"


@pytest.mark.parametrize("changes", [
    {"best_loss": float("inf")},
    {"best_loss": float("nan")},
    {"history": [{"epoch": 1, "train_loss": float("nan")}]},
    {"extra": {"source_training_science": {"learning_rate": float("inf")}}},
])
def test_unexpected_nonfinite_values_are_not_silently_sanitized(tmp_path, changes):
    with pytest.raises(ValueError, match="Nonfinite"):
        history.extract_checkpoint(checkpoint(tmp_path, **changes))


def test_classical_export_reads_metadata_without_filter_arrays(tmp_path):
    path = tmp_path / "source_model.npz"
    metadata = {"method": "frozen", "fit_trial_ids": ["a", "b"], "fit_identity": "synthetic-fit",
                "settings": {"n_components": 4, "covariance_shrinkage": 0.1,
                             "weights": [100, 200]}, "filters": [1, 2], "weights": [3, 4]}
    # Deliberately unreadable pickle-only arrays prove that the extractor does
    # not request any model-array member with allow_pickle=False.
    np.savez(path, metadata_json=np.asarray(json.dumps(metadata)), filters=np.array([object()], dtype=object),
             weights=np.array([object()], dtype=object), bias=np.array([object()], dtype=object))
    before = path.read_bytes(), path.stat().st_mtime_ns
    result = history.extract_classical_metadata(path)
    assert result["metadata"]["fit_identity"] == "synthetic-fit"
    assert "filters" not in result["metadata"] and "weights" not in result["metadata"]
    assert "weights" not in result["metadata"]["settings"]
    assert result["source_file"]["sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert before == (path.read_bytes(), path.stat().st_mtime_ns)


def test_source_change_during_extraction_is_detected(tmp_path, monkeypatch):
    path = checkpoint(tmp_path)
    original = history._stamp
    calls = []

    def changed(item):
        value = original(item)
        calls.append(value)
        return value if len(calls) == 1 else value[:-1] + (value[-1] + 1,)

    monkeypatch.setattr(history, "_stamp", changed)
    with pytest.raises(RuntimeError, match="changed during"):
        history.extract_checkpoint(path)
