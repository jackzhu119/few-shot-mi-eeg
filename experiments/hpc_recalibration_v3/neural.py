"""V3 neural discovery using saved V2 teachers and three pooled source fits.

Core adaptation policies use dropout-off behavior; one explicit dropout-on
control separates that factor from BN buffers and trainable weights. The functional trust constraint concerns empirical source
TRAIN predictions only and makes no target-accuracy or population guarantee.
"""

from __future__ import annotations

import copy
import fcntl
import json
from pathlib import Path
import platform
import time
import traceback

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from hpc_recalibration import training as base
from hpc_recalibration.checkpoint import (
    CheckpointIdentityError,
    atomic_json,
    capture_rng,
    clone_state,
    load_checkpoint,
    restore_rng,
    save_checkpoint,
)

METHODS = (
    "frozen",
    "head_fixed",
    "full_fixed",
    "full_adaptive_bn",
    "full_adaptive_bn_dropout",
    "bn_affine_fixed",
    "bn_stats_only",
    "trust_fixed",
)
VERSION = "v3-neural-explicit-bn-functional-trust-2"


def settings(config):
    value = dict(base.DEFAULTS)
    value.update(config)
    science = config.get("science", {})
    value.update(science)
    value.update(science.get("neural", {}))
    value["methods"] = value.get(
        "neural_methods", science.get("neural", {}).get("methods", list(METHODS))
    )
    value.setdefault("trust_kl_budget", 0.01)
    value.setdefault("trust_backtrack_steps", 12)
    if not value["methods"] or any(m not in METHODS for m in value["methods"]):
        raise ValueError("Unknown V3 neural policy")
    if not 0 < float(value["trust_kl_budget"]) < 1:
        raise ValueError("Functional source KL budget must be in (0,1)")
    if int(value["trust_backtrack_steps"]) < 1:
        raise ValueError("At least one bounded projection proposal is required")
    return value


def task_identity(task, config):
    return base._hash(
        {
            "task": task,
            "science": config.get("science", {}),
            "scientific_version": config.get("scientific_version"),
            "version": VERSION,
        }
    )


def configure_policy(model, method):
    if method not in METHODS:
        raise ValueError("Unknown adaptation policy")
    model.train()
    for parameter in model.parameters():
        parameter.requires_grad_(method not in ("frozen", "bn_stats_only"))
    if method == "head_fixed":
        for parameter in model.features.parameters():
            parameter.requires_grad_(False)
    if method == "bn_affine_fixed":
        for parameter in model.parameters():
            parameter.requires_grad_(False)
        for module in model.modules():
            if isinstance(module, nn.modules.batchnorm._BatchNorm):
                if module.weight is not None:
                    module.weight.requires_grad_(True)
                if module.bias is not None:
                    module.bias.requires_grad_(True)
    for module in model.modules():
        if isinstance(module, nn.modules.dropout._DropoutNd):
            module.train(method == "full_adaptive_bn_dropout")
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.train(
                method in ("full_adaptive_bn", "full_adaptive_bn_dropout", "bn_stats_only")
            )
    if method == "frozen":
        model.eval()


def _diagnostics(model, teacher_state):
    state = model.state_dict()
    parameter_names = set(dict(model.named_parameters()))
    squared = count = bn_squared = bn_count = batches = 0
    for name, value in state.items():
        reference = teacher_state[name].to(value.device)
        if name in parameter_names:
            squared += float((value - reference).square().sum())
            count += value.numel()
        elif name.endswith(("running_mean", "running_var")):
            bn_squared += float((value - reference).square().sum())
            bn_count += value.numel()
        elif name.endswith("num_batches_tracked"):
            batches += int((value - reference).abs())
    return {
        "parameter_update_rms": (squared / max(count, 1)) ** 0.5,
        "bn_buffer_update_rms": (bn_squared / max(bn_count, 1)) ** 0.5,
        "bn_batches_changed": batches,
    }


def source_kl(model, x, teacher_probabilities, device, batch_size):
    """Evaluate fixed source TRAIN anchors; no query or validation argument."""
    modes = {module: module.training for module in model.modules()}
    model.eval()
    total = 0.0
    try:
        with torch.inference_mode():
            for start in range(0, len(x), batch_size):
                logits = model(x[start : start + batch_size].to(device))
                reference = teacher_probabilities[start : start + batch_size].to(device)
                kl = F.kl_div(F.log_softmax(logits, dim=1), reference, reduction="sum")
                if not torch.isfinite(kl):
                    raise FloatingPointError("Nonfinite source-prediction KL")
                total += float(kl)
    finally:
        for module, mode in modes.items():
            module.training = mode
    return max(0.0, total / len(x))


def _teacher_probabilities(model, x, device, batch_size):
    model.eval()
    with torch.inference_mode():
        result = torch.cat(
            [
                model(x[s : s + batch_size].to(device)).softmax(1).cpu()
                for s in range(0, len(x), batch_size)
            ]
        )
    if not torch.isfinite(result).all():
        raise FloatingPointError("Nonfinite teacher source prediction")
    return result


def _project_proposal(
    model,
    optimizer,
    before,
    proposed,
    optimizer_before,
    source_x,
    teacher_probabilities,
    config,
    device,
):
    """Accept a bounded interpolation or roll back parameters AND Adam state."""
    parameters = list(model.parameters())
    budget = float(config["trust_kl_budget"])
    for trial in range(int(config["trust_backtrack_steps"]) + 1):
        fraction = 0.5**trial
        with torch.no_grad():
            for parameter, old, candidate in zip(parameters, before, proposed):
                parameter.copy_(old + fraction * (candidate - old))
        divergence = source_kl(
            model, source_x, teacher_probabilities, device, int(config["batch_size"])
        )
        if divergence <= budget:
            return True, divergence, trial, fraction
    with torch.no_grad():
        for parameter, old in zip(parameters, before):
            parameter.copy_(old)
    optimizer.load_state_dict(optimizer_before)
    divergence = source_kl(
        model, source_x, teacher_probabilities, device, int(config["batch_size"])
    )
    if divergence > budget + 1e-10:
        raise RuntimeError("Restored source-feasible state violates the KL budget")
    return False, divergence, int(config["trust_backtrack_steps"]) + 1, 0.0


def write_history(directory, state):
    """Public text diagnostics alongside private checkpoint tensors."""
    fields = (
        "schema_version",
        "identity",
        "method",
        "complete",
        "epoch",
        "step",
        "processed_samples",
        "proposal_count",
        "rejected_proposals",
        "backtracking_trials",
        "best_epoch",
        "checkpoint_at",
        "source_anchor_kl",
        "diagnostics",
        "support_passes",
        "sampler_seed",
        "history",
    )
    metadata = {key: state[key] for key in fields if key in state}
    best_loss = state.get("best_loss")
    if best_loss is not None:
        metadata["best_validation_loss"] = float(best_loss) if np.isfinite(best_loss) else None
    metadata["tensor_payload_included"] = False
    atomic_json(Path(directory) / "training_history.json", metadata)


def train_adaptation(
    *,
    model,
    x,
    y,
    source_x,
    directory,
    identity,
    config,
    device,
    signals,
    progress,
    method,
    extra=None,
    interrupt_after_step=None,
):
    """Save/resume the actual sampler, optimizer, RNG and accepted trust steps."""
    if method not in METHODS or method in ("frozen", "bn_stats_only"):
        raise ValueError("This stage requires an optimizer adaptation policy")
    directory = Path(directory)
    teacher_state = clone_state(model)
    teacher_probabilities = _teacher_probabilities(
        model, source_x, device, int(config["batch_size"])
    )
    configure_policy(model, method)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=float(config["adaptation_learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=int(config["adaptation_epochs"])
    )
    amp = bool(config.get("amp", False)) and device.startswith("cuda")
    if method == "trust_fixed" and amp:
        raise ValueError("This frozen projected-trust implementation uses AMP=false")
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    sampler_seed = int(
        (extra or {}).get(
            "sampler_seed",
            int(base._hash({"identity": identity, "sampler": "independent"})[:8], 16),
        )
    )
    sampler = torch.Generator(device="cpu").manual_seed(sampler_seed)
    state = {
        "schema_version": 1,
        "identity": identity,
        "method": method,
        "complete": False,
        "epoch": 0,
        "step": 0,
        "position": 0,
        "processed_samples": 0,
        "permutation": None,
        "sampler_seed": sampler_seed,
        "sampler_rng": sampler.get_state(),
        "epoch_loss_sum": 0.0,
        "history": [],
        "proposal_count": 0,
        "rejected_proposals": 0,
        "backtracking_trials": 0,
        "best_loss": float("inf"),
        "best_epoch": None,
        "best_model": None,
        "extra": extra or {},
    }
    loaded = load_checkpoint(directory, identity)
    if loaded:
        if loaded.get("method") != method or base._extra_identity(
            loaded.get("extra", {})
        ) != base._extra_identity(extra or {}):
            raise CheckpointIdentityError("Adaptation inputs/policy changed since checkpoint")
        state = loaded
        model.load_state_dict(state["model"])
        if state["complete"]:
            model.eval()
            write_history(directory, state)
            return state
        optimizer.load_state_dict(state["optimizer"])
        for item in optimizer.state.values():
            for key, value in item.items():
                if isinstance(value, torch.Tensor):
                    item[key] = value.to(device)
        scheduler.load_state_dict(state["scheduler"])
        scaler.load_state_dict(state["scaler"])
        restore_rng(state["rng"], device)
        sampler.set_state(state["sampler_rng"].cpu())
    last_save = time.monotonic()

    def save():
        nonlocal last_save
        state.update(
            model=clone_state(model),
            optimizer=optimizer.state_dict(),
            scheduler=scheduler.state_dict(),
            scaler=scaler.state_dict(),
            rng=capture_rng(),
            sampler_rng=sampler.get_state(),
            checkpoint_at=base.utc_now(),
        )
        save_checkpoint(directory, state)
        write_history(directory, state)
        last_save = time.monotonic()
        progress.update(
            force=True,
            checkpoint_at=state["checkpoint_at"],
            global_step=state["step"],
            processed_samples=state["processed_samples"],
        )

    def stop():
        if signals.code is not None:
            save()
            raise base.StopRequested(signals.code)

    if loaded is None:
        save()
    while state["epoch"] < int(config["adaptation_epochs"]):
        stop()
        if state["permutation"] is None:
            state["permutation"] = torch.randperm(len(x), generator=sampler)
            state["sampling_order_identity"] = base._hash(
                {"epoch": state["epoch"] + 1, "indices": state["permutation"].tolist()}
            )
        configure_policy(model, method)
        while state["position"] < len(x):
            stop()
            end = min(state["position"] + int(config["batch_size"]), len(x))
            indices = state["permutation"][state["position"] : end]
            batch, target = x[indices].to(device), y[indices].to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.split(":")[0], enabled=amp):
                loss = F.cross_entropy(model(batch), target)
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite support loss")
            optimizer_before = (
                copy.deepcopy(optimizer.state_dict()) if method == "trust_fixed" else None
            )
            before = (
                [p.detach().clone() for p in model.parameters()]
                if method == "trust_fixed"
                else None
            )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            if any(
                p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()
            ):
                raise FloatingPointError("Nonfinite support gradient")
            scaler.step(optimizer)
            scaler.update()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise FloatingPointError("Nonfinite proposed parameter")
            accepted, divergence, attempts, fraction = True, None, 0, 1.0
            if method == "trust_fixed":
                proposed = [p.detach().clone() for p in model.parameters()]
                accepted, divergence, attempts, fraction = _project_proposal(
                    model,
                    optimizer,
                    before,
                    proposed,
                    optimizer_before,
                    source_x,
                    teacher_probabilities,
                    config,
                    device,
                )
            state["proposal_count"] += 1
            state["step"] += int(accepted)
            state["rejected_proposals"] += int(not accepted)
            state["backtracking_trials"] += attempts
            state["processed_samples"] += len(batch)
            state["epoch_loss_sum"] += float(loss.detach()) * len(batch)
            state["position"] = end
            state["last_step_fraction"] = fraction
            if divergence is not None:
                state["source_anchor_kl"] = divergence
            progress.update(
                epoch=state["epoch"],
                global_step=state["step"],
                proposals=state["proposal_count"],
                processed_samples=state["processed_samples"],
                source_anchor_kl=state.get("source_anchor_kl"),
            )
            if interrupt_after_step is not None and state["proposal_count"] == interrupt_after_step:
                signals.code = 75
            stop()
            if time.monotonic() - last_save >= float(config["checkpoint_seconds"]):
                save()
        divergence = source_kl(
            model, source_x, teacher_probabilities, device, int(config["batch_size"])
        )
        diagnostics = _diagnostics(model, teacher_state)
        state["history"].append(
            {
                "epoch": state["epoch"] + 1,
                "train_loss": state["epoch_loss_sum"] / len(x),
                "learning_rate": optimizer.param_groups[0]["lr"],
                "source_anchor_kl": divergence,
                **diagnostics,
                "accepted_optimizer_steps": state["step"],
                "proposed_optimizer_steps": state["proposal_count"],
                "rejected_proposals": state["rejected_proposals"],
                "backtracking_trials": state["backtracking_trials"],
                "sampling_order_identity": state["sampling_order_identity"],
            }
        )
        scheduler.step()
        state.update(epoch=state["epoch"] + 1, position=0, permutation=None, epoch_loss_sum=0.0)
        if time.monotonic() - last_save >= float(config["checkpoint_seconds"]):
            save()
    state.update(
        complete=True,
        best_epoch=state["epoch"],
        best_model=clone_state(model),
        source_anchor_kl=source_kl(
            model, source_x, teacher_probabilities, device, int(config["batch_size"])
        ),
        diagnostics=_diagnostics(model, teacher_state),
    )
    if (
        method == "trust_fixed"
        and state["source_anchor_kl"] > float(config["trust_kl_budget"]) + 1e-10
    ):
        raise RuntimeError("Completed trust stage violates its empirical source KL constraint")
    save()
    model.eval()
    return state


def adapt_bn_statistics(
    *, model, x, directory, identity, config, device, signals, progress, extra=None
):
    loaded = load_checkpoint(directory, identity)
    if loaded:
        if not loaded.get("complete") or loaded.get("method") != "bn_stats_only":
            raise ValueError("Malformed BN-only completion")
        model.load_state_dict(loaded["model"])
        model.eval()
        write_history(directory, loaded)
        return loaded
    if signals.code is not None:
        raise base.StopRequested(signals.code)
    teacher = clone_state(model)
    configure_policy(model, "bn_stats_only")
    with torch.inference_mode():
        model(x.to(device))  # one complete current-support batch; no optimizer
    state = {
        "schema_version": 1,
        "identity": identity,
        "method": "bn_stats_only",
        "complete": True,
        "epoch": 0,
        "step": 0,
        "processed_samples": len(x),
        "position": len(x),
        "history": [],
        "extra": extra or {},
        "model": clone_state(model),
        "best_model": clone_state(model),
        "optimizer": None,
        "scheduler": None,
        "scaler": None,
        "rng": capture_rng(),
        "checkpoint_at": base.utc_now(),
        "diagnostics": _diagnostics(model, teacher),
        "source_query_used": False,
        "support_passes": 1,
    }
    save_checkpoint(directory, state)
    write_history(directory, state)
    progress.update(
        force=True, global_step=0, processed_samples=len(x), stage="bn_stats_only_saved"
    )
    model.eval()
    if signals.code is not None:
        raise base.StopRequested(signals.code)
    return state


def _combine(parts):
    return {
        key: np.concatenate([part[key] for part in parts], axis=0)
        for key in ("x", "y", "trial_id", "run_id")
    }


def _resolve(config, name):
    path = Path(name)
    return path if path.is_absolute() else Path(config["data_root"]) / path


def _runtime(output, config):
    device = str(config.get("device", "cuda:0"))
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable in the allocated worker")
    torch.set_num_threads(int(config.get("torch_threads", 4)))
    atomic_json(
        output / "runtime" / f"{time.time_ns()}.json",
        {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "device": device,
            "hostname": platform.node(),
            "started_at": base.utc_now(),
            "version": VERSION,
            "bitwise_cross_version_equivalence_claimed": False,
        },
    )
    return device


def _wrapped(task, config, action):
    config = settings(config)
    output = Path(config["output_root"]) / "tasks" / base._safe_name(task["task_id"])
    output.mkdir(parents=True, exist_ok=True)
    identity = task_identity(task, config)
    with (output / "neural.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 73
        if (output / "complete.json").is_file():
            old = json.loads((output / "complete.json").read_text())
            if old.get("identity") != identity:
                raise CheckpointIdentityError("Completed task scientific identity differs")
            return 0
        progress = base.Progress(output, task, config)
        with base.Signals() as signals:
            try:
                device = _runtime(output, config)
                base._seed(int(task["seed"]))
                return action(task, config, output, identity, device, signals, progress)
            except base.StopRequested as stop:
                progress.update(
                    force=True,
                    phase="paused" if stop.code == 75 else "cancelled",
                    exit_code=stop.code,
                )
                return stop.code
            except (OSError, MemoryError):
                # Storage/resource failure stops this slot rather than starting another fit.
                raise
            except torch.OutOfMemoryError as error:
                # Torch OOM subclasses RuntimeError, not Python MemoryError.
                # Preserve its chained traceback and stop this allocation.
                raise MemoryError(
                    "Torch allocation exhausted; preserve this slot checkpoint"
                ) from error
            except Exception:
                text = traceback.format_exc()
                atomic_json(
                    output / "failures" / f"{time.time_ns()}.json",
                    {
                        "task_id": task["task_id"],
                        "identity": identity,
                        "exception_at": base.utc_now(),
                        "traceback": text,
                        "exit_code": 1,
                    },
                )
                print(text, flush=True)
                progress.update(force=True, phase="failed", exit_code=1)
                return 1


def run_pretrain(task, config):
    return _wrapped(task, config, _pretrain)


def _pretrain(task, config, output, identity, device, signals, progress):
    trains, validations = [], []
    for row in task["source_inputs"]:
        trains.append(
            base._load_npz(_resolve(config, row.get("source_train", row.get("trainpath"))))
        )
        validations.append(
            base._load_npz(_resolve(config, row.get("source_validation", row.get("valpath"))))
        )
    base._disjoint(*trains, *validations)
    train, validation = _combine(trains), _combine(validations)
    if train["x"].shape[1:] != validation["x"].shape[1:]:
        raise ValueError("Pooled source dimensions differ")
    classes = np.unique(train["y"])
    dims = train["x"].shape[1:]
    model = base.CompactEEGNet(*dims, len(classes), config["architecture"]).to(device)
    mean, scale = base._normalization(train["x"], float(config["normalization_scale_floor"]))
    extra = {
        "architecture_version": base.ARCHITECTURE_VERSION,
        "architecture": config["architecture"],
        "classes": classes.tolist(),
        "dims": list(dims),
        "normalization_mean": mean,
        "normalization_scale": scale,
        "source_train_identity": base._identity_ids(train),
        "source_validation_identity": base._identity_ids(validation),
        "source_train_trial_ids": train["trial_id"].tolist(),
        "source_validation_trial_ids": validation["trial_id"].tolist(),
        "new_source_version": "v3-pooled-source-only-1",
        "source_training_science": {
            k: config[k]
            for k in (
                "source_epochs",
                "batch_size",
                "learning_rate",
                "weight_decay",
                "architecture",
                "amp",
            )
        },
    }
    progress.update(
        force=True,
        phase="pooled_source_fit",
        source_train_trials=len(train["y"]),
        source_validation_trials=len(validation["y"]),
    )
    state = base.train_stage(
        model=model,
        x=base._normalized(train["x"], mean, scale),
        y=torch.from_numpy(base._labels(train["y"], classes)),
        validation=(
            base._normalized(validation["x"], mean, scale),
            torch.from_numpy(base._labels(validation["y"], classes)),
        ),
        directory=output / "source",
        identity=base._hash({"task_identity": identity, "stage": "pooled_source"}),
        config=config,
        device=device,
        signals=signals,
        progress=progress,
        extra=extra,
    )
    write_history(output / "source", state)
    atomic_json(
        output / "complete.json",
        {
            "task_id": task["task_id"],
            "identity": identity,
            "status": "completed",
            "family": "pooled_pretrain",
            "seed": task["seed"],
            "participant": task["participant"],
            "source_checkpoint_identity": state["identity"],
            "source_train_trials": len(train["y"]),
            "source_validation_trials": len(validation["y"]),
            "query_used_for_fitting": False,
            "synthetic": bool(task.get("synthetic", False)),
            "software_validation_only": bool(task.get("synthetic", False)),
            "completed_at": base.utc_now(),
        },
    )
    progress.update(force=True, phase="completed", global_step=state["step"])
    return 0


def _teacher(task, config, train, validation, device):
    if task["source_regime"] == "pooled_source":
        directory = (
            Path(config["output_root"])
            / "tasks"
            / base._safe_name(task["pretrain_task_id"])
            / "source"
        )
        marker_path = directory.parent / "complete.json"
        if not marker_path.is_file():
            raise ValueError("Pooled source dependency is incomplete; no replacement source fit")
        marker = json.loads(marker_path.read_text())
        expected = marker["source_checkpoint_identity"]
    elif task["source_regime"] == "reuse_v2":
        directory = Path(task.get("source_checkpoint_directory", task.get("source_checkpoint", "")))
        if not directory.is_absolute():
            directory = Path(config.get("v2_project_dir", config["data_root"])) / directory
        expected = task.get("source_checkpoint_identity")
        if not expected:
            # Only own trusted local checkpoints are read. No token or external binary loader.
            header = torch.load(directory / "checkpoint.pt", map_location="cpu", weights_only=False)
            expected = header["identity"]
    else:
        raise ValueError("Unknown source regime")
    state = load_checkpoint(directory, expected)
    if not state or not state.get("complete"):
        raise ValueError("Required source teacher is incomplete; source fitting is not a fallback")
    context = state["extra"]
    classes = np.unique(train["y"])
    dims = list(train["x"].shape[1:])
    if (
        context.get("architecture_version") != base.ARCHITECTURE_VERSION
        or context.get("architecture") != config["architecture"]
        or context.get("dims") != dims
        or context.get("classes") != classes.tolist()
    ):
        raise CheckpointIdentityError("Teacher representation differs from current source")
    if task["source_regime"] == "reuse_v2":
        if context.get("source_train_identity") != base._identity_ids(train) or context.get(
            "source_validation_identity"
        ) != base._identity_ids(validation):
            raise CheckpointIdentityError("V2 source teacher trial identity differs")
    else:
        if not set(train["trial_id"].tolist()) <= set(context["source_train_trial_ids"]) or not set(
            validation["trial_id"].tolist()
        ) <= set(context["source_validation_trial_ids"]):
            raise CheckpointIdentityError("Pooled teacher lacks declared own source inputs")
    model = base.CompactEEGNet(*dims, len(classes), config["architecture"]).to(device)
    model.load_state_dict(state["best_model"])
    model.eval()
    mean, scale = context["normalization_mean"], context["normalization_scale"]
    return model, classes, mean, scale, state, directory


def run_task(task, config):
    return _wrapped(task, config, _neural_task)


def _neural_task(task, config, output, identity, device, signals, progress):
    train = base._load_npz(_resolve(config, task["source_train"]))
    validation = base._load_npz(_resolve(config, task["source_validation"]))
    base._disjoint(train, validation)
    model, classes, mean, scale, source, directory = _teacher(
        task, config, train, validation, device
    )
    teacher_state = clone_state(model)
    source_x = base._normalized(train["x"], mean, scale)
    atomic_json(
        output / "source_reuse.json",
        {
            "source_regime": task["source_regime"],
            "source_checkpoint_identity": source["identity"],
            "source_checkpoint_directory": str(directory),
            "source_checkpoint_bytes": (directory / "checkpoint.pt").stat().st_size,
            "teacher_model_state_sha256": base._model_digest(model),
            "new_source_fit": False,
            "own_source_anchor_trials": len(train["y"]),
        },
    )
    source_query = None
    if task.get("source_query"):
        source_query = base._load_npz(_resolve(config, task["source_query"]), allow_empty=True)
        base._disjoint(train, validation, source_query)
        result = base.evaluate_shard(
            model=model,
            query=source_query,
            classes=classes,
            mean=mean,
            scale=scale,
            directory=output / "source_query",
            identity=base._hash({"task_identity": identity, "stage": "source_query"}),
            config=config,
            device=device,
            signals=signals,
            progress=progress,
            metadata={
                "task_id": task["task_id"],
                "dataset": task["dataset"],
                "participant": task["participant"],
                "seed": task["seed"],
                "session": "source",
                "method": "frozen",
                "requested_budget": 0,
                "actual_budget": 0,
                "selection_use": False,
                "source_regime": task["source_regime"],
                "synthetic": bool(task.get("synthetic", False)),
                "software_validation_only": bool(task.get("synthetic", False)),
            },
        )
        atomic_json(output / "source_query.json", result)
    summaries = []
    for target in task["targets"]:
        session = base._safe_name(target["session"])
        support = base._load_npz(_resolve(config, target["support"]))
        base._disjoint(
            train, validation, *([source_query] if source_query is not None else []), support
        )
        query = None
        for budget in config["budgets"]:
            actual = min(int(budget), len(support["y"]))
            subset = {key: value[:actual] for key, value in support.items()}
            for method in config["methods"]:
                if signals.code is not None:
                    raise base.StopRequested(signals.code)
                model.load_state_dict(teacher_state)
                stage_seed = int(
                    base._hash({"seed": task["seed"], "session": session, "budget": int(budget)})[
                        :8
                    ],
                    16,
                )
                base._seed(stage_seed)
                fit_identity = base._hash(
                    {
                        "task_identity": identity,
                        "session": session,
                        "budget": int(budget),
                        "method": method,
                        "support": base._identity_ids(subset),
                        "teacher": source["identity"],
                    }
                )
                extra = {
                    "actual_support_identity": base._identity_ids(subset),
                    "source_state_identity": source["identity"],
                    "source_anchor_identity": base._identity_ids(train),
                    "source_regime": task["source_regime"],
                    "dropout_adaptation": "enabled"
                    if method == "full_adaptive_bn_dropout"
                    else "disabled",
                    "sampler_seed": stage_seed,
                    "method": method,
                }
                stage = output / "adaptation" / session / method / f"budget-{int(budget)}"
                progress.update(
                    force=True,
                    phase="adaptation",
                    stage=f"{session}/{method}/budget-{budget}",
                    epoch=0,
                )
                if method == "bn_stats_only":
                    state = adapt_bn_statistics(
                        model=model,
                        x=base._normalized(subset["x"], mean, scale),
                        directory=stage,
                        identity=fit_identity,
                        config=config,
                        device=device,
                        signals=signals,
                        progress=progress,
                        extra=extra,
                    )
                elif method != "frozen":
                    state = train_adaptation(
                        model=model,
                        x=base._normalized(subset["x"], mean, scale),
                        y=torch.from_numpy(base._labels(subset["y"], classes)),
                        source_x=source_x,
                        directory=stage,
                        identity=fit_identity,
                        config=config,
                        device=device,
                        signals=signals,
                        progress=progress,
                        method=method,
                        extra=extra,
                    )
                else:
                    state = {
                        "step": 0,
                        "diagnostics": {
                            "parameter_update_rms": 0.0,
                            "bn_buffer_update_rms": 0.0,
                            "bn_batches_changed": 0,
                        },
                    }
                if signals.code is not None:
                    raise base.StopRequested(signals.code)
                if query is None:
                    query = base._load_npz(_resolve(config, target["query"]), allow_empty=True)
                    base._disjoint(
                        train,
                        validation,
                        *([source_query] if source_query is not None else []),
                        support,
                        query,
                    )
                progress.update(
                    force=True, phase="evaluation", stage=f"{session}/{method}/budget-{budget}"
                )
                result = base.evaluate_shard(
                    model=model,
                    query=query,
                    classes=classes,
                    mean=mean,
                    scale=scale,
                    directory=output / "evaluation" / session / method / f"budget-{int(budget)}",
                    identity=fit_identity,
                    config=config,
                    device=device,
                    signals=signals,
                    progress=progress,
                    metadata={
                        "task_id": task["task_id"],
                        "dataset": task["dataset"],
                        "participant": task["participant"],
                        "seed": task["seed"],
                        "session": session,
                        "method": method,
                        "requested_budget": int(budget),
                        "actual_budget": actual if method != "frozen" else 0,
                        "available_support": actual,
                        "source_regime": task["source_regime"],
                        "selection_use": False,
                        "optimizer_steps": state["step"],
                        "diagnostics": state.get("diagnostics", {}),
                        "source_anchor_kl": state.get("source_anchor_kl"),
                        "synthetic": bool(task.get("synthetic", False)),
                        "software_validation_only": bool(task.get("synthetic", False)),
                    },
                )
                summaries.append(result)
                atomic_json(
                    output / "summary.json",
                    {
                        "task_id": task["task_id"],
                        "identity": identity,
                        "results": summaries,
                        "independent_unit": "participant",
                        "updated_at": base.utc_now(),
                    },
                )
    atomic_json(
        output / "complete.json",
        {
            "task_id": task["task_id"],
            "identity": identity,
            "status": "completed",
            "family": "neural",
            "participant": task["participant"],
            "seed": task["seed"],
            "source_regime": task["source_regime"],
            "synthetic": bool(task.get("synthetic", False)),
            "software_validation_only": bool(task.get("synthetic", False)),
            "result_count": len(summaries),
            "source_new_fit": False,
            "completed_at": base.utc_now(),
        },
    )
    progress.update(force=True, phase="completed", result_count=len(summaries))
    return 0
