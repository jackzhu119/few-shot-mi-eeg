"""Prepare once; continuation checks metadata and file stats, not full EEG hashes."""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextlib.contextmanager
def file_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def load_config(path):
    path = Path(path).expanduser().resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    config["_config_path"] = str(path)
    for key in ("project_dir", "output_root", "data_root", "tasks_file"):
        value = Path(config[key]).expanduser()
        config[key] = str((path.parent / value).resolve() if not value.is_absolute() else value)
    return config


def load_tasks(config):
    payload = json.loads(Path(config["tasks_file"]).read_text(encoding="utf-8"))
    tasks = payload["tasks"] if isinstance(payload, dict) else payload
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks_file must contain a non-empty tasks list")
    names = [task["task_id"] for task in tasks]
    if len(set(names)) != len(names):
        raise ValueError("duplicate task_id")
    for name in names:
        if not name or name in (".", "..") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in name):
            raise ValueError("task_id must be a safe single directory name")
    return tasks


def runtime_signature(config):
    versions = {"python": platform.python_version()}
    for package in ("torch", "numpy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(f"Required package {package} is unavailable in {sys.executable}") from error
    if sys.version_info < (3, 11):
        raise RuntimeError("This entry point requires Python 3.11 or later")
    # User-reported patch versions are provenance, not a reason to invalidate
    # a useful checkpoint. Actual imports/API checks run in the compute context.
    return {"executable": sys.executable, "versions": versions}


def code_provenance():
    """Hash only this small workload, for attribution rather than a resume gate."""
    root = Path(__file__).resolve().parents[1]
    paths = [root / name for name in ("bootstrap.py", "launch.sh", "job.sh")]
    paths.extend(sorted((root / "hpc_recalibration").glob("*.py")))
    files = [{"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in paths if path.is_file()]
    record = {"files": files, "runtime_code_change_invalidates_scientific_checkpoint": False}
    record["fingerprint"] = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if manifest_path.is_file():
        payload = manifest_path.read_bytes()
        manifest = json.loads(payload)
        record["offline_package"] = {"manifest_sha256": hashlib.sha256(payload).hexdigest(),
                                     "base_git_commit": manifest.get("base_git_commit"),
                                     "content_identity": manifest.get("content_identity"),
                                     "exact_runtime_contents": "files SHA256 above"}
    return record


def preparation_key(config):
    tasks = load_tasks(config)
    science_keys = ("science", "training", "classical", "budgets", "classical_methods",
                    "source_epochs", "adaptation_epochs", "batch_size", "learning_rate",
                    "adaptation_learning_rate", "weight_decay", "l2sp_lambda", "methods",
                    "architecture", "amp", "normalization_scale_floor", "source_mode",
                    "new_source_version", "scientific_version")
    scientific = {"experiment_id": config["experiment_id"], "tasks": tasks,
                  "science": {key: config.get(key) for key in science_keys},
                  "data_root": config["data_root"]}
    return hashlib.sha256(json.dumps(scientific, sort_keys=True).encode()).hexdigest()


def _input_paths(task, data_root):
    values = [task[key] for key in ("source_train", "source_validation", "source_query") if task.get(key)]
    for target in task.get("targets", []):
        values.extend(target[key] for key in ("support", "query") if target.get(key))
    paths = []
    for value in values:
        value = value["path"] if isinstance(value, dict) else value
        path = Path(value)
        if not path.is_absolute():
            path = Path(data_root) / path
        paths.append(path.resolve())
    return paths


def _current_stats(config):
    paths = sorted({p for task in load_tasks(config) for p in _input_paths(task, config["data_root"])})
    return [{"path": str(path), "bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns} for path in paths]


def _receipt_path(config):
    return Path(config["output_root"]) / ".runtime" / "prepared.json"


def lightweight_ready(config):
    path = _receipt_path(config)
    if not path.is_file():
        raise RuntimeError("No prepared input/runtime record. Run launch.sh once on login1 to prepare and submit.")
    receipt = json.loads(path.read_text())
    if receipt["preparation_key"] != preparation_key(config):
        raise RuntimeError("Task/input identity changed. Prepare the new experiment version explicitly.")
    observed_runtime = runtime_signature(config)
    if receipt["runtime"] != observed_runtime:
        atomic_json(Path(config["output_root"]) / ".runtime" / "runtime_observation.json",
                    {"observed_at": utc_now(), "prepared_runtime": receipt["runtime"],
                     "current_runtime": observed_runtime,
                     "bitwise_cross_version_equivalence_claimed": False})
    observed_code = code_provenance()
    if receipt.get("code_provenance", {}).get("fingerprint") != observed_code["fingerprint"]:
        history_path = Path(config["output_root"]) / ".runtime" / "code_observations.json"
        with file_lock(history_path.with_suffix(".lock")):
            history = json.loads(history_path.read_text()) if history_path.exists() else []
            if not history or history[-1]["code_provenance"]["fingerprint"] != observed_code["fingerprint"]:
                history.append({"observed_at": utc_now(), "code_provenance": observed_code,
                                "checkpoint_invalidation_requested": False})
                atomic_json(history_path, history)
    if receipt["file_stats"] != _current_stats(config):
        raise RuntimeError("Input file metadata changed; run --refresh-preflight once to validate changed inputs.")
    return receipt


def prepare_once(config, refresh=False):
    output = Path(config["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    # Slurm opens these files before job.sh starts.
    (output / "logs").mkdir(exist_ok=True)
    with file_lock(output / ".runtime" / "prepare.lock"):
        previous = json.loads(_receipt_path(config).read_text()) if _receipt_path(config).exists() else None
        if previous and previous["preparation_key"] != preparation_key(config):
            raise RuntimeError("Scientific task/input identity changed; use a new experiment output_root")
        current_stats = _current_stats(config)
        if previous and not refresh and previous["file_stats"] == current_stats:
            return lightweight_ready(config)
        tasks = load_tasks(config)
        observed = runtime_signature(config)
        from hpc_recalibration.data import validate_task_inputs
        validations = []
        validated_inputs = {}
        previous_results = {r["task_id"]: r["result"] for r in previous.get("input_validation", [])} if previous else {}
        old_stats = {r["path"]: r for r in previous.get("file_stats", [])} if previous else {}
        changed_paths = {r["path"] for r in current_stats if old_stats.get(r["path"]) != r}
        old_hashes = {f["path"]: f["sha256"] for r in previous_results.values()
                      for f in r.get("files", []) if f.get("sha256")}
        for task in tasks:
            # Methods and seeds sharing the exact same split inputs are checked
            # once, not once per GPU task.
            identity = json.dumps({key: task.get(key) for key in
                                   ("source_train", "source_validation", "source_query", "targets", "input_sha256")}, sort_keys=True)
            if identity not in validated_inputs:
                affected = any(str(path) in changed_paths for path in _input_paths(task, config["data_root"]))
                if previous and not refresh and not affected and task["task_id"] in previous_results:
                    validated_inputs[identity] = previous_results[task["task_id"]]
                else:
                    result = validate_task_inputs(task, config["data_root"], full_sha=True)
                    for item in result.get("files", []):
                        if item["path"] in old_hashes and item.get("sha256") != old_hashes[item["path"]]:
                            raise RuntimeError("Input bytes changed after preparation; preserve old results and use a new experiment output_root")
                    validated_inputs[identity] = result
            validations.append({"task_id": task["task_id"],
                                "result": validated_inputs[identity]})
        record = {"prepared_at": utc_now(), "preparation_key": preparation_key(config),
                  "runtime": observed, "hostname": platform.node(),
                  "code_provenance": code_provenance(),
                  "user_reported_versions": config.get("runtime", {}).get("expected_versions", {}),
                  "kernel": platform.release(), "file_stats": current_stats,
                  "input_validation": validations,
                  "free_disk_bytes_observed": shutil.disk_usage(output).free,
                  "gpu_smoke_completed": False,
                  "scope": "CPU metadata/input preparation; GPU smoke runs once in allocated compute context"}
        atomic_json(_receipt_path(config), record)
        return record


def gpu_smoke_once(config):
    import torch
    from hpc_recalibration.training import ARCHITECTURE_VERSION, CompactEEGNet
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable: run GPU checks and training inside a Slurm GPU allocation")
    capability = torch.cuda.get_device_capability(0)
    identity = {"runtime": runtime_signature(config), "torch_cuda_build": torch.version.cuda,
                "smoke_revision": 2, "architecture_version": ARCHITECTURE_VERSION,
                "device_capability": list(capability), "device_name": torch.cuda.get_device_name(0)}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    root = Path(config["output_root"]) / ".runtime"
    path = root / f"gpu_smoke_{key}.json"
    with file_lock(root / "gpu_smoke.lock"):
        if path.exists():
            return json.loads(path.read_text())
        print(json.dumps({"event": "gpu_smoke_start", "device": "cuda:0", "pid": os.getpid()}), flush=True)
        device = torch.device("cuda:0")
        torch.manual_seed(4242)
        architecture = {"temporal_filters": 8, "depth_multiplier": 2,
                        "kernel_length": 64, "dropout": 0.25}
        model = CompactEEGNet(4, 128, 2, architecture).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.9)
        x = torch.randn(8, 4, 128, device=device)
        y = torch.arange(8, device=device) % 2
        def step(net, opt, sched):
            opt.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(net(x), y)
            if not torch.isfinite(loss):
                raise FloatingPointError("Non-finite GPU smoke loss")
            loss.backward()
            opt.step()
            sched.step()
            return float(loss.detach())
        first_loss = step(model, optimizer, scheduler)
        # Surface asynchronous device errors before publishing the saved state.
        torch.cuda.synchronize()
        state = {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                 "scheduler": scheduler.state_dict(), "rng": torch.get_rng_state(),
                 "cuda_rng": torch.cuda.get_rng_state_all()}
        fd, temporary = tempfile.mkstemp(prefix=".gpu-smoke-", dir=root)
        saved = root / f"gpu_smoke_{key}.pt"
        try:
            with os.fdopen(fd, "wb") as stream:
                torch.save(state, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, saved)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        reloaded = torch.load(saved, map_location=device, weights_only=False)
        resumed = CompactEEGNet(4, 128, 2, architecture).to(device)
        resumed.load_state_dict(reloaded["model"])
        resumed_optimizer = torch.optim.Adam(resumed.parameters(), lr=0.001)
        resumed_optimizer.load_state_dict(reloaded["optimizer"])
        resumed_scheduler = torch.optim.lr_scheduler.StepLR(resumed_optimizer, step_size=1, gamma=0.9)
        resumed_scheduler.load_state_dict(reloaded["scheduler"])
        torch.set_rng_state(reloaded["rng"].cpu())
        torch.cuda.set_rng_state_all([value.cpu() for value in reloaded["cuda_rng"]])
        second_loss = step(model, optimizer, scheduler)
        torch.set_rng_state(reloaded["rng"].cpu())
        torch.cuda.set_rng_state_all([value.cpu() for value in reloaded["cuda_rng"]])
        resumed_loss = step(resumed, resumed_optimizer, resumed_scheduler)
        torch.cuda.synchronize()
        pairs = list(zip(model.state_dict().values(), resumed.state_dict().values()))
        exact = all(torch.equal(a, b) for a, b in pairs)
        close = all(torch.allclose(a, b, rtol=1e-5, atol=1e-6) for a, b in pairs)
        max_difference = max(float((a.double() - b.double()).abs().max()) for a, b in pairs)
        if not close:
            raise RuntimeError("GPU checkpoint restore failed the one-step continuation comparison")
        record = {"checked_at": utc_now(), "identity": identity,
                  "forward_backward_save_restore": True, "continuation_state_bitwise_equal": exact,
                  "continuation_state_allclose": close, "max_state_difference": max_difference,
                  "software_smoke_tolerance": {"rtol": 1e-5, "atol": 1e-6},
                  "losses": [first_loss, second_loss, resumed_loss],
                  "synthetic": True, "software_validation_only": True,
                  "gpu_uuid_is_resume_requirement": False}
        atomic_json(path, record)
        print(json.dumps({"event": "gpu_smoke_pass", "receipt": str(path)}), flush=True)
        return record
