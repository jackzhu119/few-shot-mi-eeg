"""Synthetic CPU checks for explicit V3 BN policies and resumable trust updates."""

from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import types

import numpy as np
import pytest
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
spec = importlib.util.spec_from_file_location(
    "hpc_v3_neural", ROOT / "experiments/hpc_recalibration_v3/neural.py"
)
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)


@pytest.fixture(autouse=True)
def cpu_threads():
    torch.set_num_threads(1)


class Progress:
    def update(self, **values):
        pass


def model():
    return v3.base.CompactEEGNet(
        2,
        64,
        2,
        {"temporal_filters": 2, "depth_multiplier": 1, "kernel_length": 4, "dropout": 0.25},
    )


def config(tmp_path, **extra):
    result = {
        "source_epochs": 2,
        "adaptation_epochs": 2,
        "batch_size": 4,
        "learning_rate": 0.001,
        "adaptation_learning_rate": 0.01,
        "weight_decay": 0.0001,
        "amp": False,
        "checkpoint_seconds": 1000.0,
        "heartbeat_seconds": 1000.0,
        "normalization_scale_floor": 1e-6,
        "trust_kl_budget": 0.001,
        "trust_backtrack_steps": 12,
        "torch_threads": 1,
        "device": "cpu",
        "architecture": {
            "temporal_filters": 2,
            "depth_multiplier": 1,
            "kernel_length": 4,
            "dropout": 0.25,
        },
        "output_root": str(tmp_path / "outputs"),
        "data_root": str(tmp_path / "data"),
        "scientific_version": "synthetic-v3",
        "science": {},
        "budgets": [2],
    }
    result.update(extra)
    return result


def stage(tmp_path, initial, method="full_fixed", interrupt=None, signals=None, **overrides):
    v3.base._seed(1337)
    m = model()
    m.load_state_dict(initial)
    x = torch.arange(8 * 2 * 64, dtype=torch.float32).reshape(8, 2, 64) / 1000
    y = torch.arange(8) % 2
    c = config(tmp_path, **overrides)
    signal = signals or types.SimpleNamespace(code=None)
    state = v3.train_adaptation(
        model=m,
        x=x,
        y=y,
        source_x=x[:6],
        directory=tmp_path / "stage",
        identity="synthetic-stage",
        config=c,
        device="cpu",
        signals=signal,
        progress=Progress(),
        method=method,
        extra={"synthetic": True},
        interrupt_after_step=interrupt,
    )
    return m, state


def test_policy_modes_separate_bn_dropout_and_weights():
    m = model()
    for method in v3.METHODS:
        v3.configure_policy(m, method)
        assert all(
            layer.training == (method == "full_adaptive_bn_dropout")
            for layer in m.modules()
            if isinstance(layer, nn.Dropout)
        )
        assert all(
            layer.training
            == (method in ("full_adaptive_bn", "full_adaptive_bn_dropout", "bn_stats_only"))
            for layer in m.modules()
            if isinstance(layer, nn.BatchNorm2d)
        )
        if method == "head_fixed":
            assert not any(p.requires_grad for p in m.features.parameters())
            assert all(p.requires_grad for p in m.classifier.parameters())
        if method == "bn_affine_fixed":
            trainable = {name for name, p in m.named_parameters() if p.requires_grad}
            expected = {
                name + "." + parameter
                for name, layer in m.named_modules()
                if isinstance(layer, nn.BatchNorm2d)
                for parameter in ("weight", "bias")
            }
            assert trainable == expected
        if method in ("frozen", "bn_stats_only"):
            assert not any(p.requires_grad for p in m.parameters())


@pytest.mark.parametrize("method", ["full_fixed", "trust_fixed", "full_adaptive_bn_dropout"])
def test_interrupted_stage_resumes_identically_without_replaying_samples(tmp_path, method):
    v3.base._seed(1)
    initial = v3.clone_state(model())
    full_model, full = stage(tmp_path / "full", initial, method)
    with pytest.raises(v3.base.StopRequested) as stop:
        stage(tmp_path / "resume", initial, method, interrupt=1)
    assert stop.value.code == 75
    saved = v3.load_checkpoint(tmp_path / "resume/stage", "synthetic-stage")
    assert saved["position"] == 4 and saved["processed_samples"] == 4
    assert all(
        key in saved
        for key in ("optimizer", "scheduler", "scaler", "rng", "sampler_rng", "permutation")
    )
    resumed_model, resumed = stage(tmp_path / "resume", initial, method)
    assert resumed["processed_samples"] == full["processed_samples"] == 16
    assert resumed["history"] == full["history"]
    for key, value in full_model.state_dict().items():
        assert torch.equal(value, resumed_model.state_dict()[key]), key
    assert (tmp_path / "resume/stage/checkpoint.previous.pt").is_file()


def test_trust_backtracking_meets_empirical_source_budget(tmp_path):
    v3.base._seed(2)
    initial = v3.clone_state(model())
    _, state = stage(
        tmp_path, initial, "trust_fixed", adaptation_learning_rate=1.0, trust_kl_budget=1e-5
    )
    assert state["source_anchor_kl"] <= 1e-5 + 1e-10
    assert state["backtracking_trials"] > 0
    assert all(row["source_anchor_kl"] <= 1e-5 + 1e-10 for row in state["history"])


def test_rejected_trust_proposal_restores_adam_and_parameters(monkeypatch):
    m = nn.Linear(2, 2)
    optimizer = torch.optim.AdamW(m.parameters(), lr=0.1)
    before = [p.detach().clone() for p in m.parameters()]
    old = copy.deepcopy(optimizer.state_dict())
    m(torch.ones(2, 2)).sum().backward()
    optimizer.step()
    proposed = [p.detach().clone() for p in m.parameters()]

    def divergence(*args):
        return 0.0 if all(torch.equal(p, b) for p, b in zip(m.parameters(), before)) else 1.0

    monkeypatch.setattr(v3, "source_kl", divergence)
    accepted, kl, _, fraction = v3._project_proposal(
        m,
        optimizer,
        before,
        proposed,
        old,
        None,
        None,
        {"trust_kl_budget": 0.01, "trust_backtrack_steps": 2, "batch_size": 2},
        "cpu",
    )
    assert not accepted and kl == 0 and fraction == 0
    assert optimizer.state_dict() == old
    assert all(torch.equal(p, b) for p, b in zip(m.parameters(), before))


def test_bn_statistics_only_changes_buffers_not_weights_or_optimizer(tmp_path, monkeypatch):
    v3.base._seed(3)
    m = model()
    before = v3.clone_state(m)

    def forbidden(*args, **kwargs):
        raise AssertionError("BN statistics-only created an optimizer")

    monkeypatch.setattr(torch.optim, "AdamW", forbidden)
    state = v3.adapt_bn_statistics(
        model=m,
        x=torch.ones(4, 2, 64) * 5,
        directory=tmp_path,
        identity="synthetic-bn",
        config=config(tmp_path),
        device="cpu",
        signals=types.SimpleNamespace(code=None),
        progress=Progress(),
        extra={"synthetic": True},
    )
    assert state["step"] == 0 and state["optimizer"] is None
    assert state["diagnostics"]["bn_batches_changed"] > 0
    assert all(torch.equal(p, before[name]) for name, p in m.named_parameters())
    assert state["diagnostics"]["parameter_update_rms"] == 0


def save_split(path, prefix, n=4):
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(sum(prefix.encode()))
    np.savez_compressed(
        path,
        x=rng.normal(size=(n, 2, 64)).astype("float32"),
        y=np.arange(n, dtype=np.int64) % 2,
        trial_id=np.array([f"{prefix}/{i}" for i in range(n)]),
        run_id=np.array([prefix] * n),
    )


def test_pooled_source_uses_only_declared_train_validation_and_reuses_complete(
    tmp_path, monkeypatch
):
    c = config(tmp_path)
    inputs = []
    for person in ["a", "b"]:
        for role in ["train", "validation"]:
            save_split(Path(c["data_root"]) / f"{person}-{role}.npz", person + role)
        inputs.append(
            {
                "participant": person,
                "source_train": f"{person}-train.npz",
                "source_validation": f"{person}-validation.npz",
            }
        )
    task = {
        "task_id": "synthetic-pool",
        "dataset": "synthetic",
        "participant": "pooled",
        "seed": 5,
        "source_inputs": inputs,
        "family": "pooled_pretrain",
        "synthetic": True,
    }
    assert v3.run_pretrain(task, c) == 0
    marker = json.loads((Path(c["output_root"]) / "tasks/synthetic-pool/complete.json").read_text())
    assert marker["source_train_trials"] == marker["source_validation_trials"] == 8
    assert marker["query_used_for_fitting"] is False

    def no_fit(**kwargs):
        raise AssertionError("Completed pooled source was retrained")

    monkeypatch.setattr(v3.base, "train_stage", no_fit)
    assert v3.run_pretrain(task, c) == 0


def teacher_fixture(tmp_path):
    c = config(tmp_path, science={"neural_methods": ["frozen", "head_fixed"]})
    paths = {}
    for role, n in [
        ("train", 4),
        ("validation", 4),
        ("sourcequery", 4),
        ("support", 4),
        ("query", 4),
    ]:
        path = Path(c["data_root"]) / (role + ".npz")
        save_split(path, role, n)
        paths[role] = path
    train = v3.base._load_npz(paths["train"])
    val = v3.base._load_npz(paths["validation"])
    mean, scale = v3.base._normalization(train["x"], 1e-6)
    v3.base._seed(4)
    m = model()
    source = tmp_path / "old_v2_teacher"
    state = {
        "schema_version": 1,
        "identity": "synthetic-original-v2",
        "complete": True,
        "epoch": 100,
        "model": v3.clone_state(m),
        "best_model": v3.clone_state(m),
        "extra": {
            "architecture_version": v3.base.ARCHITECTURE_VERSION,
            "architecture": c["architecture"],
            "dims": [2, 64],
            "classes": [0, 1],
            "source_train_identity": v3.base._identity_ids(train),
            "source_validation_identity": v3.base._identity_ids(val),
            "normalization_mean": mean,
            "normalization_scale": scale,
        },
    }
    v3.save_checkpoint(source, state)
    task = {
        "task_id": "synthetic-consumer",
        "dataset": "synthetic",
        "participant": "a",
        "seed": 4,
        "source_regime": "reuse_v2",
        "source_checkpoint_directory": str(source),
        "source_checkpoint_identity": state["identity"],
        "source_train": "train.npz",
        "source_validation": "validation.npz",
        "source_query": "sourcequery.npz",
        "targets": [{"session": "ses-1", "support": "support.npz", "query": "query.npz"}],
        "family": "neural",
        "synthetic": True,
    }
    return task, c, source


def test_v2_teacher_read_only_end_to_end_and_completed_adapt_reuse(tmp_path, monkeypatch):
    task, c, source = teacher_fixture(tmp_path)
    before = hashlib.sha256((source / "checkpoint.pt").read_bytes()).hexdigest()

    def forbidden(**kwargs):
        raise AssertionError("Consumer attempted source retraining")

    monkeypatch.setattr(v3.base, "train_stage", forbidden)
    assert v3.run_task(task, c) == 0
    folder = Path(c["output_root"]) / "tasks" / task["task_id"]
    assert (folder / "complete.json").is_file()
    metrics = json.loads((folder / "evaluation/ses-1/head_fixed/budget-2/metrics.json").read_text())
    assert metrics["synthetic"] and metrics["software_validation_only"]
    assert metrics["inference_state_unchanged"]
    assert metrics["diagnostics"]["bn_buffer_update_rms"] == 0
    assert hashlib.sha256((source / "checkpoint.pt").read_bytes()).hexdigest() == before

    def no_adaptation(**kwargs):
        raise AssertionError("Completed consumer repeated adaptation")

    monkeypatch.setattr(v3, "train_adaptation", no_adaptation)
    assert v3.run_task(task, c) == 0


def test_teacher_identity_error_never_triggers_replacement_fit(tmp_path, monkeypatch):
    task, c, source = teacher_fixture(tmp_path)
    task["source_checkpoint_identity"] = "different"

    def forbidden(**kwargs):
        raise AssertionError("Invalid teacher triggered source fit")

    monkeypatch.setattr(v3.base, "train_stage", forbidden)
    assert v3.run_task(task, c) == 1
    folder = Path(c["output_root"]) / "tasks" / task["task_id"]
    assert not (folder / "complete.json").exists()
    assert list((folder / "failures").glob("*.json"))


def test_storage_error_propagates_to_stop_slot(tmp_path, monkeypatch):
    task, c, _ = teacher_fixture(tmp_path)

    def disk_failure(*args, **kwargs):
        raise OSError("synthetic storage failure")

    monkeypatch.setattr(v3, "atomic_json", disk_failure)
    with pytest.raises(OSError, match="storage failure"):
        v3.run_task(task, c)


def test_torch_allocation_failure_stops_slot_instead_of_starting_more_fits(tmp_path):
    task = {
        "task_id": "synthetic-oom",
        "seed": 7,
        "dataset": "synthetic",
        "participant": "synthetic-1",
        "synthetic": True,
        "software_validation_only": True,
    }

    def action(*unused):
        raise torch.OutOfMemoryError("synthetic allocation failure, no memory allocated")

    with pytest.raises(MemoryError, match="Torch allocation exhausted") as caught:
        v3._wrapped(task, config(tmp_path), action)
    assert isinstance(caught.value.__cause__, torch.OutOfMemoryError)


@pytest.mark.parametrize(
    "method",
    ["head_fixed", "full_fixed", "full_adaptive_bn", "full_adaptive_bn_dropout", "bn_affine_fixed"],
)
def test_actual_updates_match_factorial_policy(tmp_path, method):
    v3.base._seed(7)
    initial = v3.clone_state(model())
    adapted, state = stage(tmp_path, initial, method)
    values = adapted.state_dict()
    changed = {name for name, p in adapted.named_parameters() if not torch.equal(p, initial[name])}
    assert changed
    if method == "head_fixed":
        assert all(name.startswith("classifier.") for name in changed)
    if method == "bn_affine_fixed":
        bn_names = {
            name + "." + parameter
            for name, layer in adapted.named_modules()
            if isinstance(layer, nn.BatchNorm2d)
            for parameter in ("weight", "bias")
        }
        assert changed <= bn_names
    if method in ("full_adaptive_bn", "full_adaptive_bn_dropout"):
        assert state["diagnostics"]["bn_buffer_update_rms"] > 0
        assert state["diagnostics"]["bn_batches_changed"] > 0
    else:
        assert state["diagnostics"]["bn_buffer_update_rms"] == 0
        assert all(
            torch.equal(value, initial[name])
            for name, value in values.items()
            if name.endswith(("running_mean", "running_var", "num_batches_tracked"))
        )


def test_pause_before_update_saves_initial_sampler_state(tmp_path):
    v3.base._seed(9)
    initial = v3.clone_state(model())
    with pytest.raises(v3.base.StopRequested):
        stage(tmp_path, initial, signals=types.SimpleNamespace(code=75))
    state = v3.load_checkpoint(tmp_path / "stage", "synthetic-stage")
    assert state["step"] == state["processed_samples"] == state["position"] == 0
    assert state["optimizer"]["state"] == {}


def test_missing_pooled_dependency_does_not_start_source_fit(tmp_path, monkeypatch):
    task, c, _ = teacher_fixture(tmp_path)
    task.update(source_regime="pooled_source", pretrain_task_id="missing-pool")

    def forbidden(**kwargs):
        raise AssertionError("Missing teacher triggered a new fit")

    monkeypatch.setattr(v3.base, "train_stage", forbidden)
    assert v3.run_task(task, c) == 1


def test_explicit_nested_neural_method_scope_is_respected():
    assert v3.settings({"science": {"neural": {"methods": ["frozen", "bn_stats_only"]}}})[
        "methods"
    ] == ["frozen", "bn_stats_only"]


def test_history_json_is_finite_and_excludes_checkpoint_tensor_payload(tmp_path):
    v3.base._seed(11)
    initial = v3.clone_state(model())
    _, state = stage(tmp_path, initial, "trust_fixed")
    public = json.loads((tmp_path / "stage/training_history.json").read_text())
    assert public["complete"] and public["history"] == state["history"]
    assert public["source_anchor_kl"] <= 0.001 + 1e-10
    assert public["best_validation_loss"] is None
    assert public["tensor_payload_included"] is False
    assert not {
        "model",
        "best_model",
        "optimizer",
        "scheduler",
        "scaler",
        "rng",
        "permutation",
    } & set(public)
    json.dumps(public, allow_nan=False)


def test_bn_stats_public_history_written_without_tensor_payload(tmp_path):
    v3.base._seed(12)
    m = model()
    v3.adapt_bn_statistics(
        model=m,
        x=torch.ones(4, 2, 64),
        directory=tmp_path,
        identity="synthetic-bn-history",
        config=config(tmp_path),
        device="cpu",
        signals=types.SimpleNamespace(code=None),
        progress=Progress(),
    )
    public = json.loads((tmp_path / "training_history.json").read_text())
    assert public["complete"] and public["support_passes"] == 1 and public["step"] == 0
    assert public["tensor_payload_included"] is False
    json.dumps(public, allow_nan=False)


def test_dropout_does_not_change_epoch_sampling_order(tmp_path):
    v3.base._seed(23)
    initial = v3.clone_state(model())
    orders = []
    for method in ("full_fixed", "full_adaptive_bn", "full_adaptive_bn_dropout"):
        _, state = stage(tmp_path / method, initial, method)
        orders.append([row["sampling_order_identity"] for row in state["history"]])
    assert orders[0] == orders[1] == orders[2]
    assert len(set(orders[0])) == 2


def test_explicit_sampler_seed_overrides_model_rng(tmp_path):
    seed = 12345
    initial = v3.clone_state(model())

    def execute(folder, model_seed):
        v3.base._seed(model_seed)
        m = model()
        m.load_state_dict(initial)
        return v3.train_adaptation(
            model=m,
            x=torch.randn(8, 2, 64),
            y=torch.arange(8) % 2,
            source_x=torch.ones(6, 2, 64),
            directory=folder,
            identity="synthetic-explicit-sampler",
            config=config(tmp_path),
            device="cpu",
            signals=types.SimpleNamespace(code=None),
            progress=Progress(),
            method="full_adaptive_bn_dropout",
            extra={"sampler_seed": seed, "synthetic": True},
        )

    a = execute(tmp_path / "a", 2)
    b = execute(tmp_path / "b", 999)
    assert a["sampler_seed"] == b["sampler_seed"] == seed
    assert [r["sampling_order_identity"] for r in a["history"]] == [
        r["sampling_order_identity"] for r in b["history"]
    ]
