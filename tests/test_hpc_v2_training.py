"""Synthetic software tests; these are not new real EEG experiments."""

import copy
import json
import os
import signal
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"))

from hpc_recalibration import checkpoint as cp
from hpc_recalibration import training as tr


@pytest.fixture(autouse=True)
def small_threads():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def config(tmp_path):
    return tr.effective_config({
        "data_root": str(tmp_path / "data"), "output_root": str(tmp_path / "output"),
        "experiment_id": "software_validation_only", "new_source_version": "synthetic_v2",
        "source_epochs": 3, "adaptation_epochs": 2, "batch_size": 4, "torch_threads": 1,
        "architecture": {"temporal_filters": 2, "depth_multiplier": 1,
                         "kernel_length": 8, "dropout": 0.25},
        "budgets": [4], "methods": ["frozen", "head", "full", "l2sp"], "device": "cpu",
        "heartbeat_seconds": 3600, "checkpoint_seconds": 3600,
    })


def tensors():
    generator = torch.Generator().manual_seed(123)
    return torch.randn(12, 3, 64, generator=generator), torch.arange(12) % 2


def model(configuration):
    return tr.CompactEEGNet(3, 64, 2, configuration["architecture"])


def fit(tmp_path, config_value, interrupt=None):
    tr._seed(27)
    value = model(config_value)
    x, y = tensors()
    progress = tr.Progress(tmp_path, {"task_id": "test", "dataset": "synthetic",
                                   "participant": "p1", "seed": 27, "synthetic": True}, config_value)
    return value, tr.train_stage(
        model=value, x=x, y=y, validation=(x[:4], y[:4]), directory=tmp_path,
        identity="fixed-synthetic-stage", config=config_value, device="cpu",
        signals=tr.Signals(), progress=progress, interrupt_after_step=interrupt)


def assert_nested_equal(left, right):
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, np.ndarray):
        assert np.array_equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            assert_nested_equal(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for x, y in zip(left, right):
            assert_nested_equal(x, y)
    else:
        assert left == right


def test_interrupt_resume_matches_uninterrupted_optimizer_rng(tmp_path):
    settings = config(tmp_path)
    full_model, full = fit(tmp_path / "full", settings)
    with pytest.raises(tr.StopRequested) as stopped:
        fit(tmp_path / "resumed", settings, interrupt=2)
    assert stopped.value.code == 75
    partial = cp.load_checkpoint(tmp_path / "resumed", "fixed-synthetic-stage")
    assert partial["position"] == 8
    assert partial["epoch"] == 0
    resumed_model, resumed = fit(tmp_path / "resumed", settings)
    for key in ("model", "best_model", "optimizer", "scheduler", "scaler", "history", "rng",
                "step", "processed_samples", "epoch", "best_epoch"):
        assert_nested_equal(full[key], resumed[key])
    assert_nested_equal(full_model.state_dict(), resumed_model.state_dict())
    assert (tmp_path / "resumed/checkpoint.previous.pt").exists()


def test_checkpoint_identity_is_not_recovered_as_corruption(tmp_path):
    state = {"schema_version": 1, "identity": "a", "value": 1}
    cp.save_checkpoint(tmp_path, state)
    with pytest.raises(cp.CheckpointIdentityError):
        cp.load_checkpoint(tmp_path, "b")


def test_corrupt_current_uses_previous_without_overwriting_good_generation(tmp_path):
    cp.save_checkpoint(tmp_path, {"schema_version": 1, "identity": "a", "value": 1})
    cp.save_checkpoint(tmp_path, {"schema_version": 1, "identity": "a", "value": 2})
    (tmp_path / "checkpoint.pt").write_bytes(b"invalid torch file")
    assert cp.load_checkpoint(tmp_path, "a")["value"] == 1
    cp.save_checkpoint(tmp_path, {"schema_version": 1, "identity": "a", "value": 3})
    assert cp.load_checkpoint(tmp_path, "a")["value"] == 3
    assert (tmp_path / "checkpoint.corrupt.0.pt").read_bytes() == b"invalid torch file"
    assert torch.load(tmp_path / "checkpoint.previous.pt", weights_only=False)["value"] == 1


def test_storage_save_failure_keeps_last_checkpoint(tmp_path, monkeypatch):
    cp.save_checkpoint(tmp_path, {"schema_version": 1, "identity": "a", "value": 1})
    before = (tmp_path / "checkpoint.pt").read_bytes()

    def broken(*_args, **_kwargs):
        raise OSError("simulated storage write failure")

    monkeypatch.setattr(torch, "save", broken)
    with pytest.raises(OSError, match="storage"):
        cp.save_checkpoint(tmp_path, {"schema_version": 1, "identity": "a", "value": 2})
    assert (tmp_path / "checkpoint.pt").read_bytes() == before


def test_signal_cancel_overrides_requeue_warning():
    with tr.Signals() as state:
        os.kill(os.getpid(), signal.SIGUSR1)
        assert state.code == 75
        os.kill(os.getpid(), signal.SIGTERM)
        assert state.code == 130
        os.kill(os.getpid(), signal.SIGUSR1)
        assert state.code == 130


def write_npz(path, prefix, n=8):
    path.parent.mkdir(parents=True, exist_ok=True)
    generator = np.random.default_rng(sum(prefix.encode()))
    np.savez_compressed(path, x=generator.normal(size=(n, 3, 64)).astype(np.float32),
                        y=np.arange(n, dtype=np.int64) % 2,
                        trial_id=np.asarray([f"{prefix}/{i}" for i in range(n)], dtype="U64"),
                        run_id=np.asarray([prefix] * n, dtype="U64"))


def task_data(tmp_path):
    settings = config(tmp_path)
    for name in ("train", "validation", "source_query", "support", "query"):
        write_npz(tmp_path / "data" / f"{name}.npz", name)
    task = {"task_id": "p1-seed27", "family": "eegnet", "dataset": "synthetic",
            "participant": "p1", "seed": 27, "synthetic": True,
            "source_train": "train.npz", "source_validation": "validation.npz",
            "source_query": "source_query.npz",
            "targets": [{"session": "s2", "support": "support.npz", "query": "query.npz"}]}
    return task, settings


def test_task_e2e_and_completed_skip_without_source_retrain(tmp_path, monkeypatch):
    task, settings = task_data(tmp_path)
    assert tr.run_task(task, settings) == 0
    root = tmp_path / "output/tasks/p1-seed27"
    complete = json.loads((root / "complete.json").read_text())
    assert complete["eval_shards"] == 4
    assert complete["synthetic"] and complete["software_validation_only"]
    assert json.loads((root / "source_query.json").read_text())["selection_use"] is False
    results = json.loads((root / "summary.json").read_text())["results"]
    assert {r["method"] for r in results} == {"frozen", "head", "full", "l2sp"}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("completed tasks must not open arrays")

    monkeypatch.setattr(tr, "_load_npz", forbidden)
    assert tr.run_task(task, settings) == 0


def test_head_finetuning_preserves_all_feature_parameters_and_bn(tmp_path):
    settings = config(tmp_path)
    value = model(settings)
    before = copy.deepcopy(value.features.state_dict())
    x, y = tensors()
    progress = tr.Progress(tmp_path, {"task_id": "test", "dataset": "synthetic",
                                   "participant": "p1", "seed": 27, "synthetic": True}, settings)
    tr.train_stage(model=value, x=x, y=y, validation=None, directory=tmp_path,
                   identity="head", config=settings, device="cpu", signals=tr.Signals(),
                   progress=progress, method="head")
    assert_nested_equal(before, value.features.state_dict())


def test_evaluation_failure_reuses_trained_checkpoint(tmp_path, monkeypatch):
    task, settings = task_data(tmp_path)
    settings["methods"] = ["full"]
    task.pop("source_query")
    original = tr.evaluate_shard

    def fail_once(**_kwargs):
        raise OSError("simulated prediction output failure")

    monkeypatch.setattr(tr, "evaluate_shard", fail_once)
    assert tr.run_task(task, settings) == 1
    root = tmp_path / "output/tasks/p1-seed27"
    source_bytes = (root / "source/checkpoint.pt").read_bytes()
    adapt_bytes = (root / "adaptation/s2/full/budget-4/checkpoint.pt").read_bytes()
    assert list((root / "failures").glob("*.json"))
    monkeypatch.setattr(tr, "evaluate_shard", original)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("an already trained stage must not construct an optimizer")

    monkeypatch.setattr(torch.optim, "AdamW", forbidden)
    assert tr.run_task(task, settings) == 0
    assert (root / "source/checkpoint.pt").read_bytes() == source_bytes
    assert (root / "adaptation/s2/full/budget-4/checkpoint.pt").read_bytes() == adapt_bytes


def test_evaluation_missing_class_retains_undefined_ba(tmp_path):
    task, settings = task_data(tmp_path)
    settings["methods"] = ["frozen"]
    path = tmp_path / "data/query.npz"
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    arrays["y"][:] = 0
    np.savez_compressed(path, **arrays)
    assert tr.run_task(task, settings) == 0
    result = json.loads((tmp_path / "output/tasks/p1-seed27/summary.json").read_text())["results"][0]
    assert result["balanced_accuracy"] is None
    assert result["missing_query_class"]


def test_science_change_rejects_completed_task_operational_change_skips(tmp_path):
    task, settings = task_data(tmp_path)
    settings["methods"] = ["frozen"]
    assert tr.run_task(task, settings) == 0
    changed_runtime = dict(settings, heartbeat_seconds=25, checkpoint_seconds=60)
    assert tr.run_task(task, changed_runtime) == 0
    with pytest.raises(cp.CheckpointIdentityError):
        tr.run_task(task, dict(settings, source_epochs=4))


def test_absent_new_source_version_fails_instead_of_retraining_legacy(tmp_path):
    with pytest.raises(ValueError, match="new_source_version"):
        tr.effective_config({"output_root": str(tmp_path)})


def test_overlap_ids_fails_and_preserves_failure_record(tmp_path):
    task, settings = task_data(tmp_path)
    task["source_validation"] = task["source_train"]
    assert tr.run_task(task, settings) == 1
    root = tmp_path / "output/tasks/p1-seed27"
    assert not (root / "complete.json").exists()
    assert list((root / "failures").glob("*.json"))


def test_empty_query_is_retained_without_fabricated_accuracy(tmp_path):
    task, settings = task_data(tmp_path)
    settings["methods"] = ["frozen"]
    write_npz(tmp_path / "data/query.npz", "query", n=0)
    assert tr.run_task(task, settings) == 0
    result = json.loads((tmp_path / "output/tasks/p1-seed27/summary.json").read_text())["results"][0]
    assert result["n_query"] == 0
    assert result["balanced_accuracy"] is None
    assert result["accuracy"] is None


def test_compatible_v2_source_reuse_constructs_no_optimizer(tmp_path, monkeypatch):
    task, settings = task_data(tmp_path)
    settings["methods"] = ["frozen"]
    assert tr.run_task(task, settings) == 0
    directory = tmp_path / "output/tasks/p1-seed27/source"
    source = torch.load(directory / "checkpoint.pt", weights_only=False)
    reuse_task = dict(task, task_id="reuse", source_checkpoint=str(directory),
                      source_checkpoint_identity=source["identity"])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source reuse must not construct an optimizer")

    monkeypatch.setattr(torch.optim, "AdamW", forbidden)
    assert tr.run_task(reuse_task, dict(settings, source_mode="reuse")) == 0
    receipt = json.loads((tmp_path / "output/tasks/reuse/source_reuse.json").read_text())
    assert receipt["new_source_fit"] is False


def test_resume_detects_changed_actual_source_arrays(tmp_path, monkeypatch):
    task, settings = task_data(tmp_path)
    settings["methods"] = ["frozen"]
    task.pop("source_query")
    original = tr.evaluate_shard
    monkeypatch.setattr(tr, "evaluate_shard", lambda **_kwargs: (_ for _ in ()).throw(OSError("stop")))
    assert tr.run_task(task, settings) == 1
    path = tmp_path / "data/train.npz"
    with np.load(path, allow_pickle=False) as value:
        arrays = {key: value[key] for key in value.files}
    arrays["x"] += 0.01
    np.savez_compressed(path, **arrays)
    monkeypatch.setattr(tr, "evaluate_shard", original)
    assert tr.run_task(task, settings) == 1
    failures = list((tmp_path / "output/tasks/p1-seed27/failures").glob("*.json"))
    assert any(json.loads(f.read_text())["exception_type"] == "CheckpointIdentityError"
               for f in failures)
