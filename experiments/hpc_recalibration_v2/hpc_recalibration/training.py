"""Resumable, offline EEGNet-style comparison for a NEW scientific version.

The compact architecture below is explicitly versioned. It is not a substitute
loader for the previously accepted Braindecode checkpoints. Existing checkpoints
from this new architecture may be reused; legacy checkpoints require their
original loader and cannot silently trigger a replacement source fit.
"""

from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import io
import json
import os
import platform
import random
import re
import signal
import time
import traceback
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .checkpoint import (
    CheckpointIdentityError,
    atomic_bytes,
    atomic_json,
    capture_rng,
    clone_state,
    load_checkpoint,
    restore_rng,
    save_checkpoint,
)

ARCHITECTURE_VERSION = "compact_eegnet_hpc_v2_1"
SCIENCE_KEYS = (
    "source_epochs", "adaptation_epochs", "batch_size", "learning_rate",
    "adaptation_learning_rate", "weight_decay", "l2sp_lambda", "budgets", "methods",
    "architecture", "amp", "normalization_scale_floor", "source_mode",
    "new_source_version", "experiment_id", "scientific_version",
)
DEFAULTS = {
    "source_epochs": 100, "adaptation_epochs": 20, "batch_size": 16,
    "learning_rate": 0.001, "adaptation_learning_rate": 0.0001,
    "weight_decay": 0.0001, "l2sp_lambda": 0.01,
    "budgets": [4, 8, 12, 16, 20], "methods": ["frozen", "head", "full", "l2sp"],
    "architecture": {"temporal_filters": 8, "depth_multiplier": 2,
                     "kernel_length": 64, "dropout": 0.25},
    "amp": False, "normalization_scale_floor": 1e-6,
    "source_mode": "new_source", "new_source_version": None,
    "checkpoint_seconds": 120, "heartbeat_seconds": 30, "torch_threads": 4,
    "device": "auto",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _extra_identity(value):
    if isinstance(value, np.ndarray):
        return {"shape": list(value.shape), "dtype": str(value.dtype),
                "sha256": hashlib.sha256(value.tobytes()).hexdigest()}
    if isinstance(value, dict):
        return {key: _extra_identity(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_extra_identity(item) for item in value]
    return value


def _safe_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", str(value)) or value in (".", ".."):
        raise ValueError("Task and session identifiers must be simple safe names")
    return str(value)


def effective_config(config: dict) -> dict:
    value = dict(DEFAULTS)
    value.update(config)
    # A nested section can coexist with the scheduler and preparation settings.
    value.update(config.get("training", {}))
    if value["source_mode"] not in ("new_source", "reuse"):
        raise ValueError("source_mode must explicitly be new_source or reuse")
    if value["source_mode"] == "new_source" and not value.get("new_source_version"):
        raise ValueError("A new source fit requires an explicit new_source_version")
    for key in ("source_epochs", "adaptation_epochs", "batch_size", "torch_threads"):
        if int(value[key]) < 1:
            raise ValueError(f"{key} must be positive")
    for key in ("checkpoint_seconds", "heartbeat_seconds", "normalization_scale_floor"):
        if float(value[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    if any(method not in ("frozen", "head", "full", "l2sp") for method in value["methods"]):
        raise ValueError("Unrecognized neural comparison method")
    if len(set(value["methods"])) != len(value["methods"]):
        raise ValueError("Methods must be unique")
    if not value["methods"] or not value["budgets"]:
        raise ValueError("At least one method and support budget are required")
    if any(int(budget) < 1 for budget in value["budgets"]):
        raise ValueError("Support budgets must be positive")
    return value


def scientific_identity(task: dict, config: dict) -> str:
    # Paths are kept relative by the prepared manifest. Relocation of data_root
    # and output_root is operational; changing declared input identities is not.
    return _hash({"architecture_version": ARCHITECTURE_VERSION, "task": task,
                  "science": {key: config.get(key) for key in SCIENCE_KEYS}})


def _load_npz(path: Path, *, allow_empty=False) -> dict:
    with np.load(path, allow_pickle=False) as data:
        required = {"x", "y", "trial_id", "run_id"}
        if not required.issubset(data.files):
            raise ValueError(f"{path.name} needs x, y, trial_id and run_id")
        result = {key: data[key] for key in required}
    x, y = result["x"], result["y"]
    if (x.dtype != np.float32 or x.ndim != 3 or (not len(x) and not allow_empty)
            or not np.isfinite(x).all()):
        raise ValueError(f"{path.name}: x must be nonempty finite float32 [trials,channels,time]")
    if y.shape != (len(x),) or y.dtype.kind not in "iu":
        raise ValueError(f"{path.name}: y must contain integer class labels")
    for key in ("trial_id", "run_id"):
        if result[key].shape != (len(x),) or result[key].dtype.kind not in "US":
            raise ValueError(f"{path.name}: {key} must be a fixed string vector")
        result[key] = result[key].astype("U")
    if len(set(result["trial_id"].tolist())) != len(x):
        raise ValueError(f"{path.name}: duplicate trial identity")
    return result


def _identity_ids(data: dict) -> str:
    return _hash({"trials": data["trial_id"].tolist(), "runs": data["run_id"].tolist(),
                  "shape": list(data["x"].shape), "labels": data["y"].tolist(),
                  "array_sha256": hashlib.sha256(data["x"].tobytes()).hexdigest()})


def _disjoint(*parts: dict) -> None:
    seen = set()
    for part in parts:
        ids = set(part["trial_id"].tolist())
        if ids & seen:
            raise ValueError("Overlapping trial identities between fitting and evaluation roles")
        seen |= ids


def _labels(y: np.ndarray, classes: np.ndarray) -> np.ndarray:
    mapping = {int(label): i for i, label in enumerate(classes)}
    if any(int(label) not in mapping for label in y):
        raise ValueError("A partition contains a class absent from source training")
    return np.asarray([mapping[int(label)] for label in y], dtype=np.int64)


class SameTemporalConv(nn.Conv2d):
    def forward(self, value):
        width = self.kernel_size[1] - 1
        return super().forward(F.pad(value, (width // 2, width - width // 2, 0, 0)))


class CompactEEGNet(nn.Module):
    """Explicit EEGNet-style architecture; no external model package dependency."""

    def __init__(self, channels: int, times: int, classes: int, architecture: dict):
        super().__init__()
        if channels < 1 or times < 32 or classes < 2:
            raise ValueError("EEGNet requires channels>=1, times>=32 and classes>=2")
        f1 = int(architecture.get("temporal_filters", 8))
        depth = int(architecture.get("depth_multiplier", 2))
        f2 = f1 * depth
        kernel = int(architecture.get("kernel_length", 64))
        dropout = float(architecture.get("dropout", 0.25))
        self.features = nn.Sequential(
            SameTemporalConv(1, f1, (1, kernel), bias=False),
            nn.BatchNorm2d(f1, eps=1e-3, momentum=0.01),
            nn.Conv2d(f1, f2, (channels, 1), groups=f1, bias=False),
            nn.BatchNorm2d(f2, eps=1e-3, momentum=0.01), nn.ELU(),
            nn.AvgPool2d((1, 4)), nn.Dropout(dropout),
            SameTemporalConv(f2, f2, (1, 16), groups=f2, bias=False),
            nn.Conv2d(f2, f2, (1, 1), bias=False),
            nn.BatchNorm2d(f2, eps=1e-3, momentum=0.01), nn.ELU(),
            nn.AvgPool2d((1, 8)), nn.Dropout(dropout), nn.Flatten(),
        )
        self.classifier = nn.Linear(f2 * (times // 32), classes)

    def forward(self, value):
        return self.classifier(self.features(value.unsqueeze(1)))


class StopRequested(Exception):
    def __init__(self, code: int):
        self.code = code


class Signals:
    def __init__(self):
        self.code = None
        self.previous = {}

    def _request(self, signum, _frame):
        # A cancellation supersedes a warning, so scancel never resurrects work.
        if signum in (signal.SIGTERM, signal.SIGINT):
            self.code = 130
        elif self.code is None:
            self.code = 75

    def __enter__(self):
        for signum in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT):
            self.previous[signum] = signal.signal(signum, self._request)
        return self

    def __exit__(self, *_args):
        for signum, previous in self.previous.items():
            signal.signal(signum, previous)


class Progress:
    def __init__(self, directory: Path, task: dict, config: dict):
        self.directory, self.config = directory, config
        self.last_emit = 0.0
        self.values = {key: task[key] for key in ("task_id", "dataset", "participant", "seed")}
        self.values.update(global_step=0, processed_samples=0, checkpoint_at=None,
                           synthetic=bool(task.get("synthetic", False)),
                           software_validation_only=bool(task.get("synthetic", False)))

    def update(self, force=False, **values):
        self.values.update(values)
        now = time.monotonic()
        if force or now - self.last_emit >= float(self.config["heartbeat_seconds"]):
            self.values["updated_at"] = utc_now()
            atomic_json(self.directory / "progress.json", self.values)
            print(json.dumps(self.values, sort_keys=True, allow_nan=False), flush=True)
            self.last_emit = now


def _normalization(train: np.ndarray, floor: float) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=(0, 2), keepdims=True, dtype=np.float64).astype(np.float32)
    scale = train.std(axis=(0, 2), keepdims=True, dtype=np.float64).astype(np.float32)
    return mean, np.maximum(scale, np.float32(floor))


def _normalized(x: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(np.asarray((x - mean) / scale, dtype=np.float32))


def _set_mode(model: CompactEEGNet, method: str) -> None:
    model.train()
    if method == "head":
        model.features.eval()  # includes both BN and dropout


def _evaluate_loss(model, x, y, device, batch_size):
    model.eval()
    total = 0.0
    with torch.inference_mode():
        for start in range(0, len(x), batch_size):
            target = y[start:start + batch_size].to(device)
            logits = model(x[start:start + batch_size].to(device))
            loss = F.cross_entropy(logits, target, reduction="sum")
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite source validation loss")
            total += float(loss)
    return total / len(x)


def train_stage(*, model, x, y, validation, directory, identity, config, device,
                signals, progress, method="source", anchor=None, extra=None,
                base_steps=0, base_samples=0, interrupt_after_step=None):
    """Fit/resume one stage; interruption hook is only for synthetic tests."""
    directory = Path(directory)
    epochs = int(config["source_epochs"] if method == "source" else config["adaptation_epochs"])
    batch_size = int(config["batch_size"])
    loaded = load_checkpoint(directory, identity)
    if loaded and _extra_identity(loaded.get("extra", {})) != _extra_identity(extra or {}):
        raise CheckpointIdentityError("Actual fitting data or normalization changed since checkpoint")
    if loaded and loaded.get("complete"):
        model.load_state_dict(loaded["best_model"] if method == "source" else loaded["model"])
        model.eval()
        return loaded
    for parameter in model.parameters():
        parameter.requires_grad_(True)
    if method == "head":
        for parameter in model.features.parameters():
            parameter.requires_grad_(False)
    lr = config["learning_rate"] if method == "source" else config["adaptation_learning_rate"]
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                  lr=float(lr), weight_decay=float(config["weight_decay"]))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    amp = bool(config["amp"]) and device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    state = {"schema_version": 1, "identity": identity, "complete": False,
             "epoch": 0, "step": 0, "processed_samples": 0, "position": 0,
             "permutation": None, "epoch_loss_sum": 0.0, "history": [],
             "best_loss": float("inf"), "best_epoch": None, "best_model": None,
             "extra": extra or {}}
    if loaded:
        state = loaded
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        for opt_state in optimizer.state.values():
            for key, value in opt_state.items():
                if isinstance(value, torch.Tensor):
                    opt_state[key] = value.to(device)
        scheduler.load_state_dict(state["scheduler"])
        scaler.load_state_dict(state["scaler"])
        restore_rng(state["rng"], device)
    last_save = time.monotonic()

    def save():
        nonlocal last_save
        state.update(model=clone_state(model), optimizer=optimizer.state_dict(),
                     scheduler=scheduler.state_dict(), scaler=scaler.state_dict(),
                     rng=capture_rng(), checkpoint_at=utc_now())
        save_checkpoint(directory, state)
        last_save = time.monotonic()
        progress.update(force=True, checkpoint_at=state["checkpoint_at"],
                        global_step=base_steps + state["step"],
                        processed_samples=base_samples + state["processed_samples"])

    def stop_if_requested():
        if signals.code is not None:
            save()
            raise StopRequested(signals.code)

    # A first checkpoint preserves the exact initialization if the first batch
    # fails or the allocation is interrupted immediately.
    if loaded is None:
        save()
    while state["epoch"] < epochs:
        stop_if_requested()
        if state["permutation"] is None:
            state["permutation"] = torch.randperm(len(x), device="cpu")
        _set_mode(model, method)
        while state["position"] < len(x):
            stop_if_requested()
            end = min(state["position"] + batch_size, len(x))
            indices = state["permutation"][state["position"]:end]
            batch, target = x[indices].to(device), y[indices].to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.split(":")[0], enabled=amp):
                logits = model(batch)
                loss = F.cross_entropy(logits, target)
                if method == "l2sp":
                    if anchor is None:
                        raise ValueError("L2-SP requires the fixed source anchor")
                    penalty = sum((p - anchor[name]).square().sum()
                                  for name, p in model.named_parameters())
                    count = sum(p.numel() for p in model.parameters())
                    loss = loss + float(config["l2sp_lambda"]) * penalty / count
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite training loss")
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            if any(p.grad is not None and not torch.isfinite(p.grad).all()
                   for p in model.parameters()):
                raise FloatingPointError("Nonfinite training gradient")
            scaler.step(optimizer)
            scaler.update()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise FloatingPointError("Nonfinite model parameter after optimizer step")
            state["step"] += 1
            state["processed_samples"] += len(batch)
            state["epoch_loss_sum"] += float(loss.detach()) * len(batch)
            state["position"] = end
            progress.update(epoch=state["epoch"], global_step=base_steps + state["step"],
                            processed_samples=base_samples + state["processed_samples"])
            if interrupt_after_step is not None and state["step"] == interrupt_after_step:
                signals.code = 75
            stop_if_requested()
            if time.monotonic() - last_save >= float(config["checkpoint_seconds"]):
                save()
        history = {"epoch": state["epoch"] + 1,
                   "train_loss": state["epoch_loss_sum"] / len(x),
                   "learning_rate": optimizer.param_groups[0]["lr"]}
        if validation is not None:
            validation_loss = _evaluate_loss(model, *validation, device, batch_size)
            history["validation_loss"] = validation_loss
            if validation_loss < state["best_loss"]:
                state.update(best_loss=validation_loss, best_epoch=state["epoch"] + 1,
                             best_model=clone_state(model))
        state["history"].append(history)
        scheduler.step()
        state.update(epoch=state["epoch"] + 1, position=0, permutation=None, epoch_loss_sum=0.0)
        if time.monotonic() - last_save >= float(config["checkpoint_seconds"]):
            save()
    state["complete"] = True
    if method != "source":
        state["best_model"] = clone_state(model)
        state["best_epoch"] = state["epoch"]
    save()
    model.load_state_dict(state["best_model"])
    model.eval()
    return state


def _model_digest(model) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def evaluate_shard(*, model, query, classes, mean, scale, directory, identity, config,
                   device, signals, progress, metadata):
    """Resume prediction batches; completed fitting is never repeated for an eval error."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / "metrics.json"
    if final.exists():
        result = json.loads(final.read_text())
        if result.get("identity") != identity:
            raise CheckpointIdentityError("Evaluation identity differs from completed result")
        if result.get("query_identity") != _identity_ids(query):
            raise CheckpointIdentityError("Completed evaluation inputs changed")
        if result.get("model_state_sha256") != _model_digest(model):
            raise CheckpointIdentityError("Completed evaluation model state changed")
        return result
    before = _model_digest(model)
    y = _labels(query["y"], classes)
    x = _normalized(query["x"], mean, scale)
    checkpoint = directory / "evaluation.partial.npz"
    position = 0
    predictions = np.zeros((len(x), len(classes)), dtype=np.float32)
    if checkpoint.exists():
        with np.load(checkpoint, allow_pickle=False) as partial:
            if str(partial["identity"].item()) != identity:
                raise CheckpointIdentityError("Evaluation partial belongs to another stage")
            if str(partial["query_identity"].item()) != _identity_ids(query):
                raise CheckpointIdentityError("Evaluation query identities changed")
            position = int(partial["position"].item())
            predictions[:] = partial["probabilities"]

    def save_partial():
        stream = io.BytesIO()
        np.savez_compressed(stream, identity=np.asarray(identity), position=np.asarray(position),
                            query_identity=np.asarray(_identity_ids(query)),
                            probabilities=predictions)
        atomic_bytes(checkpoint, stream.getvalue())

    model.eval()
    last_save = time.monotonic()
    with torch.inference_mode():
        while position < len(x):
            if signals.code is not None:
                save_partial()
                raise StopRequested(signals.code)
            end = min(position + int(config["batch_size"]), len(x))
            logits = model(x[position:end].to(device))
            if not torch.isfinite(logits).all():
                raise FloatingPointError("Nonfinite query logits")
            predictions[position:end] = logits.softmax(dim=1).cpu().numpy()
            position = end
            progress.update(evaluated_samples=position)
            if time.monotonic() - last_save >= float(config["checkpoint_seconds"]):
                save_partial()
                last_save = time.monotonic()
    if before != _model_digest(model):
        raise RuntimeError("Inference modified model parameters or BN buffers")
    predicted = predictions.argmax(axis=1)
    counts = [int(np.sum(y == label)) for label in range(len(classes))]
    recalls = [float(np.mean(predicted[y == label] == label)) if counts[label] else None
               for label in range(len(classes))]
    ba = float(np.mean(recalls)) if all(counts) else None
    result = dict(metadata, identity=identity, n_query=len(y), class_counts=counts,
                  balanced_accuracy=ba, accuracy=float(np.mean(predicted == y)) if len(y) else None,
                  recalls=recalls, missing_query_class=not all(counts),
                  prediction_class_counts=[int(np.sum(predicted == i)) for i in range(len(classes))],
                  collapse=len(set(predicted.tolist())) == 1,
                  query_identity=_identity_ids(query), inference_state_unchanged=True,
                  model_state_sha256=before,
                  completed_at=utc_now())
    # Publish predictions first; metrics is the atomic completion marker.
    stream = io.BytesIO()
    np.savez_compressed(stream, probabilities=predictions, labels=query["y"], classes=classes,
                        trial_id=query["trial_id"], run_id=query["run_id"])
    atomic_bytes(directory / "predictions.npz", stream.getvalue())
    atomic_json(final, result)
    return result


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _resolve(data_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else data_root / path


def run_task(task: dict, config: dict) -> int:
    """Execute a task on the Slurm-assigned device; source fitting is explicit."""
    config = effective_config(config)
    _safe_name(task["task_id"])
    output = Path(config["output_root"]) / "tasks" / task["task_id"]
    output.mkdir(parents=True, exist_ok=True)
    identity = scientific_identity(task, config)
    with (output / "task.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"task_id": task["task_id"], "status": "already_running"}), flush=True)
            return 73
        complete = output / "complete.json"
        if complete.exists():
            if json.loads(complete.read_text()).get("identity") != identity:
                raise CheckpointIdentityError("Completed task has a different scientific identity")
            print(json.dumps({"task_id": task["task_id"], "status": "completed_skip"}), flush=True)
            return 0
        progress = Progress(output, task, config)
        with Signals() as signals:
            try:
                return _run_task(task, config, output, identity, signals, progress)
            except StopRequested as stop:
                progress.update(force=True, phase="paused" if stop.code == 75 else "cancelled",
                                exit_code=stop.code)
                return stop.code
            except Exception as exc:
                failure = {"task_id": task["task_id"], "identity": identity,
                           "failed_at": utc_now(), "exception_type": type(exc).__name__,
                           "traceback": traceback.format_exc(), "exit_code": 1}
                print(failure["traceback"], flush=True)
                try:
                    atomic_json(output / "failures" / f"{time.time_ns()}-{os.getpid()}.json", failure)
                    progress.update(force=True, phase="failed", exit_code=1)
                except OSError:
                    traceback.print_exc()
                return 1


def _run_task(task, config, output, identity, signals, progress):
    device = config["device"]
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable in this allocated task")
    torch.set_num_threads(int(config["torch_threads"]))
    # No hard-coded GPU UUID, host, number of channels, or old experiment claims.
    _seed(int(task["seed"]))
    runtime = {"python": platform.python_version(), "torch": torch.__version__,
               "numpy": np.__version__, "device": device, "hostname": platform.node(),
               "started_at": utc_now(), "architecture_version": ARCHITECTURE_VERSION,
               "bitwise_equivalence_across_devices_or_versions_claimed": False}
    atomic_json(output / "runtime" / f"{time.time_ns()}.json", runtime)
    data_root = Path(config["data_root"])
    progress.update(force=True, phase="loading_source", stage="source", epoch=0)
    train = _load_npz(_resolve(data_root, task["source_train"]))
    validation = _load_npz(_resolve(data_root, task["source_validation"]))
    _disjoint(train, validation)
    if train["x"].shape[1:] != validation["x"].shape[1:]:
        raise ValueError("Source train/validation channel or time dimensions differ")
    classes = np.unique(train["y"])
    dims = train["x"].shape[1:]
    model = CompactEEGNet(*dims, len(classes), config["architecture"]).to(device)
    mean, scale = _normalization(train["x"], float(config["normalization_scale_floor"]))
    source_identity = _hash({"task_identity": identity, "stage": "source"})
    source_science = {key: config[key] for key in (
        "source_epochs", "batch_size", "learning_rate", "weight_decay", "architecture",
        "amp", "normalization_scale_floor", "new_source_version")}
    source_science["seed"] = int(task["seed"])
    if config["source_mode"] == "reuse":
        supplied = task.get("source_checkpoint")
        if not supplied:
            raise ValueError("source_mode=reuse requires a compatible source_checkpoint directory")
        source = load_checkpoint(_resolve(data_root, supplied), task.get("source_checkpoint_identity", ""))
        if source is None or not source.get("complete"):
            raise ValueError("Requested reusable source checkpoint is incomplete")
        context = source.get("extra", {})
        expected = {"architecture_version": ARCHITECTURE_VERSION,
                    "architecture": config["architecture"], "dims": list(dims),
                    "classes": classes.tolist(), "source_train_identity": _identity_ids(train),
                    "source_validation_identity": _identity_ids(validation),
                    "source_training_science": source_science}
        if any(context.get(k) != value for k, value in expected.items()):
            raise ValueError("Source checkpoint is incompatible; legacy54 are not silently retrained")
        if not np.array_equal(context["normalization_mean"], mean):
            raise ValueError("Source normalization mean differs")
        if not np.array_equal(context["normalization_scale"], scale):
            raise ValueError("Source normalization scale differs")
        model.load_state_dict(source["best_model"])
        model.eval()
        base_steps = base_samples = 0
        atomic_json(output / "source_reuse.json", {"checkpoint_identity": source["identity"],
                    "new_source_fit": False, "architecture_version": ARCHITECTURE_VERSION})
    else:
        progress.update(force=True, phase="source_train", stage="source")
        extra = {"architecture_version": ARCHITECTURE_VERSION,
                 "architecture": config["architecture"], "dims": list(dims),
                 "classes": classes.tolist(), "source_train_identity": _identity_ids(train),
                 "source_validation_identity": _identity_ids(validation),
                 "normalization_mean": mean, "normalization_scale": scale,
                 "new_source_version": config["new_source_version"],
                 "source_training_science": source_science}
        source = train_stage(model=model, x=_normalized(train["x"], mean, scale),
                             y=torch.from_numpy(_labels(train["y"], classes)),
                             validation=(_normalized(validation["x"], mean, scale),
                                         torch.from_numpy(_labels(validation["y"], classes))),
                             directory=output / "source", identity=source_identity,
                             config=config, device=device, signals=signals, progress=progress,
                             extra=extra)
        base_steps, base_samples = source["step"], source["processed_samples"]
    source_state = clone_state(model)
    source_query = None
    if task.get("source_query"):
        progress.update(force=True, phase="evaluation", stage="source_query",
                        global_step=base_steps, processed_samples=base_samples)
        source_query = _load_npz(_resolve(data_root, task["source_query"]), allow_empty=True)
        _disjoint(train, validation, source_query)
        if source_query["x"].shape[1:] != dims:
            raise ValueError("Source query dimensions differ from the fixed source representation")
        source_result = evaluate_shard(
            model=model, query=source_query, classes=classes, mean=mean, scale=scale,
            directory=output / "source_query", identity=_hash({"task_identity": identity,
                                                              "stage": "source_query"}),
            config=config, device=device, signals=signals, progress=progress,
            metadata={"task_id": task["task_id"], "dataset": task["dataset"],
                      "participant": task["participant"], "seed": task["seed"],
                      "session": "source", "method": "frozen", "requested_budget": 0,
                      "actual_budget": 0, "selection_use": False,
                      "synthetic": bool(task.get("synthetic", False)),
                      "software_validation_only": bool(task.get("synthetic", False))})
        atomic_json(output / "source_query.json", source_result)
    summaries = []
    for target in task["targets"]:
        session = _safe_name(target["session"])
        progress.update(force=True, phase="loading_support", stage=session)
        support = _load_npz(_resolve(data_root, target["support"]))
        _disjoint(train, validation, *([source_query] if source_query is not None else []), support)
        if support["x"].shape[1:] != dims:
            raise ValueError("Support dimensions differ from the fixed source representation")
        query = None
        for budget in config["budgets"]:
            actual = min(int(budget), len(support["x"]))
            subset = {key: value[:actual] for key, value in support.items()}
            for method in config["methods"]:
                stage = f"{session}/{method}/budget-{int(budget)}"
                directory = output / "adaptation" / session / method / f"budget-{int(budget)}"
                stage_identity = _hash({"task_identity": identity, "stage": stage,
                                       "actual_support_identity": _identity_ids(subset)})
                model.load_state_dict(source_state)
                # Independent deterministic initialization per comparison avoids
                # method ordering changing dropout and shuffle streams.
                stage_seed = int(_hash({"seed": task["seed"], "session": session,
                                       "budget": int(budget)})[:8], 16)
                _seed(stage_seed)
                if method != "frozen":
                    progress.update(force=True, phase="adaptation", stage=stage, epoch=0)
                    anchor = {name: p.detach().clone() for name, p in model.named_parameters()}
                    state = train_stage(
                        model=model, x=_normalized(subset["x"], mean, scale),
                        y=torch.from_numpy(_labels(subset["y"], classes)), validation=None,
                        directory=directory, identity=stage_identity, config=config, device=device,
                        signals=signals, progress=progress, method=method, anchor=anchor,
                        base_steps=base_steps, base_samples=base_samples,
                        extra={"actual_support_identity": _identity_ids(subset),
                               "source_state_identity": source_identity})
                    base_steps += state["step"]
                    base_samples += state["processed_samples"]
                if signals.code is not None:
                    raise StopRequested(signals.code)
                # Query is only opened after this fixed update has finished.
                progress.update(force=True, phase="evaluation", stage=stage,
                                global_step=base_steps, processed_samples=base_samples)
                if query is None:
                    # Cache only inside this session's evaluation path. No
                    # training/selection function receives this query object.
                    query = _load_npz(_resolve(data_root, target["query"]), allow_empty=True)
                    _disjoint(train, validation, *([source_query] if source_query is not None else []),
                              support, query)
                    if query["x"].shape[1:] != dims:
                        raise ValueError("Query dimensions differ from fixed fitted model")
                result = evaluate_shard(
                    model=model, query=query, classes=classes, mean=mean, scale=scale,
                    directory=output / "evaluation" / session / method / f"budget-{int(budget)}",
                    identity=stage_identity, config=config, device=device, signals=signals,
                    progress=progress, metadata={"task_id": task["task_id"], "dataset": task["dataset"],
                        "participant": task["participant"], "seed": task["seed"],
                        "session": session, "method": method, "requested_budget": int(budget),
                        "actual_budget": actual if method != "frozen" else 0,
                        "available_support": actual,
                        "synthetic": bool(task.get("synthetic", False)),
                        "software_validation_only": bool(task.get("synthetic", False))})
                summaries.append(result)
                atomic_json(output / "summary.json", {"task_id": task["task_id"],
                            "identity": identity, "results": summaries,
                            "independent_unit": "participant", "updated_at": utc_now()})
    progress.update(force=True, phase="completed", stage="all", global_step=base_steps,
                    processed_samples=base_samples)
    atomic_json(output / "complete.json", {"identity": identity, "task_id": task["task_id"],
                "dataset": task["dataset"], "participant": task["participant"], "seed": task["seed"],
                "status": "completed", "completed_at": utc_now(), "global_step": base_steps,
                "processed_samples": base_samples, "eval_shards": len(summaries),
                "synthetic": bool(task.get("synthetic", False)),
                "software_validation_only": bool(task.get("synthetic", False))})
    return 0
