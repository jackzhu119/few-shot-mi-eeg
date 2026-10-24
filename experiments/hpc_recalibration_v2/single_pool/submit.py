"""Submit one allocation for the fixed task queue; preserve prior submission evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import traceback
import uuid


def _project_imports():
    source = Path(__file__).resolve().parent.parent
    if (source / "hpc_recalibration").is_dir():
        sys.path.insert(0, str(source))
    elif __name__ == "__main__":
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config", required=True)
        args, _ = parser.parse_known_args()
        raw = json.loads(Path(args.config).expanduser().read_text())
        sys.path.insert(0, str(Path(raw["project_dir"]).expanduser().resolve()))


_project_imports()
from hpc_recalibration.preflight import (  # noqa: E402
    atomic_json, file_lock, load_config, load_tasks, preparation_key, prepare_once, utc_now,
)
from hpc_recalibration.slurm import (  # noqa: E402
    TERMINAL, _complete, _monitor_start, _safe_slug, accounting_states, queue_entries, run_command,
)
from hpc_recalibration.github_sync import ensure_authorized  # noqa: E402


def _atomic_bytes(path, data):
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def explicit_rejection_reason(batch):
    """Recognize an actual negative scheduler reply, never a missing network reply."""
    if batch.get("job_id") or not isinstance(batch.get("returncode"), int) or batch["returncode"] <= 0:
        return None
    if re.fullmatch(r"\s*\d+(?:;[^\s]+)?\s*", batch.get("stdout", "")):
        return None
    error = batch.get("stderr", "").lower()
    if "sbatch:" not in error or "error:" not in error:
        return None
    if "batch job submission failed" in error:
        for signature in ("qosmaxsubmitjobperuserlimit", "qosmaxsubmitjobperaccountlimit",
                          "assocmaxsubmitjoblimit", "qosmaxjobsperuserlimit"):
            if signature in error:
                return "explicit Slurm refusal: " + signature
        if "job violates accounting/qos policy" in error:
            return "explicit Slurm refusal: accounting/qos policy"
    for signature in ("invalid account", "invalid partition", "invalid generic resource",
                      "invalid qos", "invalid time limit", "requested time limit",
                      "requested node configuration is not available", "invalid node name"):
        if signature in error:
            return "explicit Slurm refusal: " + signature
    return None


def _resolve_prior_rejection(path, ledger, batch, reason):
    # Preserve the original complete UTF-8 bytes before appending resolution.
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = path.with_name("submissions.before-single-pool-" + digest[:20] + ".json")
    if backup.exists():
        if backup.read_bytes() != original:
            raise RuntimeError("Submission evidence backup conflict; original ledger retained")
    else:
        _atomic_bytes(backup, original)
    resolution = {"resolved_at": utc_now(), "kind": "explicit_scheduler_rejection",
                  "reason": reason, "returncode": batch["returncode"],
                  "stderr_sha256": hashlib.sha256(batch["stderr"].encode()).hexdigest(),
                  "prior_ledger_backup": str(backup), "prior_ledger_sha256": digest,
                  "original_status_and_stderr_preserved": True,
                  "a_job_was_not_accepted": True}
    batch.setdefault("resolution_history", []).append(resolution)
    batch["resolved_terminal"] = True
    # Do not relabel the historical status or replace its original error.
    atomic_json(path, ledger)


def _pool_command(config, indices, job_name):
    settings = config.get("slurm", {})
    workers = int(settings.get("pool_workers", 2))
    cores = int(settings.get("cpus_per_task", 16))
    if workers < 1 or cores < 1:
        raise ValueError("pool_workers and per-worker cpus_per_task must be positive")
    memory = re.fullmatch(r"([1-9][0-9]*)([KMGTP]?)", str(settings.get("mem", "128G")).upper())
    if not memory:
        raise ValueError("Per-worker Slurm memory must be an integer with K/M/G/T/P suffix")
    total_memory = str(int(memory.group(1)) * workers) + memory.group(2)
    gres = str(settings.get("gres", "gpu:1"))
    if not re.fullmatch(r"gpu(?::[^:]+)?:1", gres):
        raise ValueError("Each pool worker requires exactly one Slurm GPU")
    total_gres = gres.rsplit(":", 1)[0] + ":" + str(workers)
    output = Path(config["output_root"]).resolve()
    args = ["sbatch", "--parsable", "--nodes=1", "--ntasks=1",
            "--account=" + settings.get("account", "zhuziyuan"),
            "--partition=" + settings.get("partition", "hpc_gpu"),
            "--gres=" + total_gres, "--cpus-per-task=" + str(cores * workers),
            "--mem=" + total_memory,
            "--time=" + str(settings.get("time_limit", "5-03:00:00")),
            "--signal=B:USR1@180", "--requeue", "--job-name=" + job_name,
            "--chdir=" + config["project_dir"],
            "--output=" + str(output / "logs" / "%x-%j.out"),
            "--error=" + str(output / "logs" / "%x-%j.err")]
    if settings.get("exclude"):
        args.append("--exclude=" + str(settings["exclude"]))
    args.extend([str(Path(__file__).resolve().with_name("job.sh")), config["_config_path"],
                 config.get("python", "/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python"),
                 ",".join(str(i) for i in indices)])
    return args


def submit(config, *, refresh_preflight=False, dry_run=False, runner=run_command):
    output = Path(config["output_root"]).resolve()
    (output / "logs").mkdir(parents=True, exist_ok=True)
    (output / ".runtime").mkdir(exist_ok=True)
    tasks = load_tasks(config)
    prepared = output / ".runtime" / "prepared.json"
    if prepared.is_file() and json.loads(prepared.read_text())["preparation_key"] != preparation_key(config):
        raise RuntimeError("Scientific task/input identity changed; preserve results and use a new experiment version")
    prefix = _safe_slug(config["experiment_id"]) + "-" + hashlib.sha256(str(output).encode()).hexdigest()[:8]
    with file_lock(output / ".runtime" / "submit.lock"):
        remaining = [i for i, task in enumerate(tasks) if not _complete(output, task)]
        if not remaining:
            return {"status": "already_complete", "submitted_indices": [], "completed": len(tasks)}
        path = output / ".runtime" / "submissions.json"
        ledger = json.loads(path.read_text()) if path.exists() else {"experiment_id": config["experiment_id"], "batches": []}
        if ledger.get("experiment_id") != config["experiment_id"]:
            raise RuntimeError("Submission ledger belongs to a different experiment")
        if not dry_run:
            user = config.get("slurm", {}).get("user", "zhuziyuan")
            active = [e for e in queue_entries(user, runner)
                      if e["name"].startswith(prefix) and e["state"] not in TERMINAL]
            if active:
                monitor, warning = _monitor_start(config)
                return {"status": "already_active", "active_jobs": active, "submitted_indices": [],
                        "monitor_pid": monitor, "monitor_warning": warning}
            for batch in ledger["batches"]:
                if batch.get("resolved_terminal"):
                    continue
                job_id = batch.get("job_id")
                if not job_id:
                    reason = explicit_rejection_reason(batch)
                    if reason is None:
                        raise RuntimeError("An earlier submission has no confirmed job ID and no explicit scheduler refusal. Its evidence is retained; confirm its state before submitting again")
                    _resolve_prior_rejection(path, ledger, batch, reason)
                    continue
                states = accounting_states(job_id, runner)
                if not states or any(state not in TERMINAL for state in states):
                    return {"status": "waiting_for_accounting", "job_id": job_id,
                            "observed_states": states, "submitted_indices": []}
                batch.update(resolved_terminal=True, terminal_states=states, resolved_at=utc_now())
            atomic_json(path, ledger)
        prepare_once(config, refresh=refresh_preflight)
        name = prefix + "-" + uuid.uuid4().hex[:7]
        command = _pool_command(config, remaining, name)
        if dry_run:
            return {"status": "dry_run", "command": command, "remaining_indices": remaining,
                    "slurm_jobs_to_submit": 1, "submission_mode": "single_pool"}
        ensure_authorized(config, interactive=True)
        batch = {"created_at": utc_now(), "name": name, "indices": remaining,
                 "task_ids": [tasks[i]["task_id"] for i in remaining], "status": "submitting",
                 "job_id": None, "command": command, "submission_mode": "single_pool",
                 "pool_workers": int(config.get("slurm", {}).get("pool_workers", 2))}
        ledger["batches"].append(batch)
        atomic_json(path, ledger)
        try:
            result = runner(command)
        except Exception as error:
            batch.update(status="submission_reply_uncertain", exception_type=type(error).__name__)
            atomic_json(path, ledger)
            raise
        batch.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        match = re.fullmatch(r"\s*(\d+)(?:;[^\s]+)?\s*", result.stdout)
        if result.returncode != 0 or not match:
            reason = explicit_rejection_reason(batch)
            batch["status"] = "rejected_before_acceptance" if reason else "submission_reply_uncertain"
            if reason:
                batch.update(resolved_terminal=True, rejection_reason=reason)
            atomic_json(path, ledger)
            if reason and "submit" in reason:
                raise RuntimeError("Slurm refused the single job because the account still has no submission slot. No other job was cancelled and no retry was made; rerun after an existing job finishes. " + result.stderr.strip())
            raise RuntimeError("Single-job sbatch did not return a confirmed job ID; evidence retained and no retry made. " + result.stderr.strip())
        batch.update(status="submitted", job_id=match.group(1), submitted_at=utc_now())
        atomic_json(path, ledger)
        monitor, warning = _monitor_start(config)
        return {"status": "submitted", "job_id": batch["job_id"], "submitted_indices": remaining,
                "submission_mode": "single_pool", "slurm_jobs_submitted": 1,
                "pool_workers": batch["pool_workers"], "monitor_pid": monitor,
                "monitor_warning": warning, "logs": str(output / "logs"),
                "evidence_note": "Submission is not evidence of model updates; inspect per-task steps and checkpoints"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh-preflight", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"event": "python_start", "pid": os.getpid(), "command": "single_pool_submit", "utc": utc_now()}), flush=True)
    config = load_config(args.config)
    try:
        result = submit(config, dry_run=args.dry_run, refresh_preflight=args.refresh_preflight)
        print(json.dumps(result, indent=2), flush=True)
        return 0
    except Exception:
        detail = traceback.format_exc()
        print(detail, file=sys.stderr, flush=True)
        try:
            atomic_json(Path(config["output_root"]) / ".runtime" / ("single_submit_failure-" + str(time.time_ns()) + ".json"),
                        {"observed_at": utc_now(), "traceback": detail, "exit_code": 1})
        except OSError:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
