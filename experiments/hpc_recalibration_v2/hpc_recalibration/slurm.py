"""Small Slurm array submitter: persistent intent, duplicate exclusion and resume."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

from .preflight import atomic_json, file_lock, load_tasks, preparation_key, prepare_once, utc_now

ACTIVE = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "SUSPENDED", "RESIZING",
          "REQUEUED", "REQUEUE_FED", "REQUEUE_HOLD", "RESV_DEL_HOLD", "SIGNALING", "STAGE_OUT"}
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY",
            "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}


def run_command(args):
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=45, check=False)
    except FileNotFoundError as error:
        raise RuntimeError(f"{args[0]} is unavailable; submit on the school's login1 node") from error


def _state(value):
    return value.strip().split()[0].rstrip("+") if value.strip() else "UNKNOWN"


def queue_entries(user, runner=run_command):
    result = runner(["squeue", "--noheader", "--array", "--states=all", "--user", user,
                     "--format=%i|%j|%T"])
    if result.returncode:
        raise RuntimeError("squeue failed; no new submission attempted: " + result.stderr.strip())
    entries = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split("|", 2)
        if len(parts) != 3:
            raise RuntimeError("Unparseable squeue output; refusing a duplicate submission")
        entries.append({"id": parts[0], "name": parts[1], "state": _state(parts[2])})
    return entries


def accounting_states(job_id, runner=run_command):
    result = runner(["sacct", "--noheader", "--parsable2", "--allocations",
                     "--jobs", str(job_id), "--format=JobIDRaw,State"])
    if result.returncode:
        raise RuntimeError("sacct cannot establish whether an earlier job finished; no duplicate submitted: " + result.stderr.strip())
    states = []
    for line in result.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 2 and parts[0]:
            states.append(_state(parts[1]))
    return states


def _safe_slug(value):
    clean = re.sub(r"[^A-Za-z0-9_-]", "-", value)[:38]
    return clean or "paper2"


def _complete(output, task):
    path = output / "tasks" / task["task_id"] / "complete.json"
    if not path.is_file():
        return False
    value = json.loads(path.read_text())
    if value.get("task_id") != task["task_id"] or not (value.get("identity") or value.get("task_identity")):
        raise ValueError(f"Malformed completion record for {task['task_id']}; preserve it for diagnosis")
    return True


def _base_command(config, indices, job_name):
    settings = config.get("slurm", {})
    output = Path(config["output_root"]).resolve()
    here = Path(__file__).resolve().parents[1]
    parallel = int(settings.get("array_parallel", 3))
    if parallel < 1:
        raise ValueError("array_parallel must be positive")
    args = ["sbatch", "--parsable", "--account=" + settings.get("account", "zhuziyuan"),
            "--partition=" + settings.get("partition", "hpc_gpu1"),
            "--gres=" + settings.get("gres", "gpu:NVIDIAA100-SXM4-80GB:1"),
            "--cpus-per-task=" + str(settings.get("cpus_per_task", 24)),
            "--mem=" + str(settings.get("mem", "128G")),
            "--time=" + str(settings.get("time_limit", "5-03:00:00")),
            "--array=" + ",".join(map(str, indices)) + "%" + str(parallel),
            "--signal=B:USR1@180", "--requeue", "--job-name=" + job_name,
            "--chdir=" + config["project_dir"],
            "--output=" + str(output / "logs" / "%x-%A_%a.out"),
            "--error=" + str(output / "logs" / "%x-%A_%a.err")]
    exclude = settings.get("exclude", "gpu3")
    if exclude:
        args.append("--exclude=" + str(exclude))
    args.extend([str(here / "job.sh"), config["_config_path"],
                 config.get("python", "/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python")])
    return args


def _monitor_start(config):
    from hpc_recalibration.github_sync import start_monitor
    try:
        return start_monitor(config["_config_path"]), None
    except Exception as error:
        # Reporting has an independent lifetime and cannot cancel submitted work.
        warning = f"{type(error).__name__}: progress monitor startup failed; training remains submitted"
        try:
            atomic_json(Path(config["output_root"]) / ".runtime" / "monitor_start_failure.json",
                        {"observed_at": utc_now(), "warning": warning})
        except OSError:
            pass
        return None, warning


def submit(config, refresh_preflight=False, dry_run=False, runner=run_command):
    output = Path(config["output_root"]).resolve()
    (output / "logs").mkdir(parents=True, exist_ok=True)
    (output / ".runtime").mkdir(exist_ok=True)
    tasks = load_tasks(config)
    existing_preparation = output / ".runtime" / "prepared.json"
    if existing_preparation.is_file():
        prior = json.loads(existing_preparation.read_text())
        if prior["preparation_key"] != preparation_key(config):
            raise RuntimeError("Scientific task/input identity changed; use a new experiment output_root")
    remaining = [i for i, task in enumerate(tasks) if not _complete(output, task)]
    if not remaining:
        return {"status": "already_complete", "submitted_indices": [], "completed": len(tasks)}
    prefix = _safe_slug(config["experiment_id"]) + "-" + hashlib.sha256(str(output).encode()).hexdigest()[:8]
    with file_lock(output / ".runtime" / "submit.lock"):
        # Re-read completion while holding the submit lock; another process may
        # have finished or submitted a task since this function was entered.
        remaining = [i for i, task in enumerate(tasks) if not _complete(output, task)]
        if not remaining:
            return {"status": "already_complete", "submitted_indices": [], "completed": len(tasks)}
        ledger_path = output / ".runtime" / "submissions.json"
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"experiment_id": config["experiment_id"], "batches": []}
        if ledger["experiment_id"] != config["experiment_id"]:
            raise RuntimeError("output_root belongs to a different experiment; choose its own output directory")
        if not dry_run:
            user = config.get("slurm", {}).get("user", "zhuziyuan")
            active = [e for e in queue_entries(user, runner)
                      if e["name"].startswith(prefix) and e["state"] not in TERMINAL]
            if active:
                # Never add a second independent %3 array while an earlier array
                # is active: that could exceed the user's global 3-GPU preference.
                monitor_pid, monitor_warning = _monitor_start(config)
                return {"status": "already_active", "active_jobs": active,
                        "submitted_indices": [], "remaining_tasks": len(remaining),
                        "monitor_pid": monitor_pid, "monitor_warning": monitor_warning}
            for batch in ledger["batches"]:
                if batch.get("resolved_terminal"):
                    continue
                job_id = batch.get("job_id")
                if not job_id:
                    raise RuntimeError("An earlier sbatch reply was uncertain. Its intent is retained in submissions.json; confirm job state before resolving it. No automatic resubmission was attempted.")
                states = accounting_states(job_id, runner)
                if not states or any(s not in TERMINAL for s in states):
                    return {"status": "waiting_for_accounting", "job_id": job_id,
                            "observed_states": states, "submitted_indices": []}
                batch["resolved_terminal"] = True
                batch["terminal_states"] = states
                batch["resolved_at"] = utc_now()
            atomic_json(ledger_path, ledger)
        prepare_once(config, refresh=refresh_preflight)
        job_name = prefix + "-" + uuid.uuid4().hex[:7]
        command = _base_command(config, remaining, job_name)
        if dry_run:
            return {"status": "dry_run", "command": command, "remaining_indices": remaining,
                    "time_limit_is_user_candidate_not_verified_partition_maximum": True}
        from hpc_recalibration.github_sync import ensure_authorized
        ensure_authorized(config, interactive=True)
        # Network reporting errors after this authorization never stop workers.
        batch = {"created_at": utc_now(), "name": job_name, "indices": remaining,
                 "task_ids": [tasks[i]["task_id"] for i in remaining],
                 "status": "submitting", "job_id": None, "command": command}
        ledger["batches"].append(batch)
        atomic_json(ledger_path, ledger)
        try:
            result = runner(command)
        except Exception as error:
            batch["status"] = "submission_reply_uncertain"
            batch["exception_type"] = type(error).__name__
            atomic_json(ledger_path, ledger)
            raise
        batch["returncode"] = result.returncode
        match = re.fullmatch(r"\s*(\d+)(?:;[^\s]+)?\s*", result.stdout)
        if result.returncode != 0 or not match:
            rejection = any(text in result.stderr.lower() for text in (
                "invalid account", "invalid partition", "invalid generic resource",
                "invalid qos", "invalid time limit", "requested time limit",
                "requested node configuration is not available", "invalid node name"))
            batch["status"] = "rejected_before_acceptance" if rejection else "submission_reply_uncertain"
            if rejection:
                batch["resolved_terminal"] = True
            batch["stderr"] = result.stderr.strip()
            atomic_json(ledger_path, ledger)
            raise RuntimeError("sbatch did not return a confirmed job ID; no retry was made. " + result.stderr.strip())
        batch.update({"status": "submitted", "job_id": match.group(1), "submitted_at": utc_now()})
        atomic_json(ledger_path, ledger)
        monitor_pid, monitor_warning = _monitor_start(config)
        return {"status": "submitted", "job_id": batch["job_id"], "submitted_indices": remaining,
                "monitor_pid": monitor_pid, "logs": str(output / "logs"),
                "monitor_warning": monitor_warning,
                "evidence_note": "A job ID is submission evidence; actual step/progress/checkpoints establish training."}
