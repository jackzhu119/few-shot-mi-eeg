"""Three persistent Slurm workers; minimal cached preparation and task resumption.

The science runner owns task checkpoints and signal-aware interruption. It must
return 75 after a saved USR1 pause, 130 after cancellation, and write a complete
marker before returning zero. This runtime never selects scientific parameters.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL",
            "OUT_OF_MEMORY", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}
SLOTS = 3


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def emit(event, **values):
    print(json.dumps({"event": event, "utc": utc_now(), **values}), flush=True)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_tasks(config):
    value = config.get("tasks")
    if value is None:
        value = json.loads(Path(config["tasks_file"]).read_text())
    tasks = value["tasks"] if isinstance(value, dict) else value
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("A nonempty fixed task list is required")
    names = [t["task_id"] for t in tasks]
    if len(names) != len(set(names)) or any(
            not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", n)
            or n in (".", "..") for n in names):
        raise ValueError("Task IDs must be unique ordinary directory names")
    return tasks


def complete(output, task):
    path = Path(output) / "tasks" / task["task_id"] / "complete.json"
    if not path.is_file():
        return False
    value = json.loads(path.read_text())
    if (value.get("task_id") != task["task_id"] or value.get("status") != "completed"
            or not (value.get("identity") or value.get("task_identity"))):
        raise ValueError("Malformed completion marker; retained: " + str(path))
    return True


def prepare_once(config):
    """Cache declared science/task identity, not repeated EEG/venv/pilot scans."""
    tasks = load_tasks(config)
    output = Path(config["output_root"]).resolve()
    (output / "logs").mkdir(parents=True, exist_ok=True)
    runtime = output / ".runtime"
    runtime.mkdir(exist_ok=True)
    identity = {"experiment_id": config["experiment_id"],
                "scientific_version": config.get("scientific_version"),
                "science": config.get("science", {}), "tasks": tasks}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = runtime / "prepared.json"
    if path.is_file():
        if json.loads(path.read_text())["scientific_fingerprint"] != fingerprint:
            raise ValueError("Science/task identity changed; retain this output and use a new version")
        return {"status": "prepared_reused", "scientific_fingerprint": fingerprint}
    project = Path(config["project_dir"]).resolve()
    if not (project / "bootstrap.py").is_file():
        raise FileNotFoundError("Installed absolute bootstrap.py is missing")
    if config.get("data_root") and not Path(config["data_root"]).is_dir():
        raise FileNotFoundError("Prepared input directory is missing; stage data on login1 first")
    value = {"prepared_at": utc_now(), "scientific_fingerprint": fingerprint,
             "checks": ["task identity", "installed bootstrap", "input directory"],
             "full_input_hash_scan_repeated": False}
    atomic_json(path, value)
    return {"status": "prepared", "scientific_fingerprint": fingerprint}


def run_command(arguments):
    return subprocess.run(arguments, text=True, capture_output=True, timeout=45, check=False)


def queue_entries(user, runner=run_command):
    reply = runner(["squeue", "--noheader", "--user", user, "--format=%i|%j|%T"])
    if reply.returncode:
        raise RuntimeError("Cannot read current Slurm jobs; no duplicate submission attempted")
    entries = []
    for line in reply.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split("|", 2)
        if len(parts) != 3:
            raise RuntimeError("Unparseable Slurm queue reply")
        entries.append({"job_id": parts[0], "name": parts[1],
                        "state": parts[2].split()[0].rstrip("+")})
    return entries


def job_prefix(config):
    slug = re.sub(r"[^A-Za-z0-9_-]", "-", config["experiment_id"])[:30]
    suffix = hashlib.sha256(str(Path(config["output_root"]).resolve()).encode()).hexdigest()[:8]
    return slug + "-" + suffix


def slot_command(config, slot, name):
    settings = config.get("slurm", {})
    output = Path(config["output_root"]).resolve()
    project = Path(config["project_dir"]).resolve()
    gres = settings.get("gres", "gpu:NVIDIAA100-SXM4-80GB:1")
    if not re.fullmatch(r"gpu(?::[^:]+)?:1", gres):
        raise ValueError("Each of the three jobs must allocate exactly one GPU")
    args = ["sbatch", "--parsable", "--nodes=1", "--ntasks=1", "--export=ALL",
            "--account=" + settings.get("account", "zhuziyuan"),
            "--partition=" + settings.get("partition", "hpc_gpu1"),
            "--gres=" + gres, "--cpus-per-task=16", "--mem=64G",
            "--time=" + settings.get("time_limit", "5-03:00:00"),
            "--signal=B:USR1@180", "--requeue", "--job-name=" + name,
            "--chdir=" + str(project),
            "--output=" + str(output / "logs/%x-%j.out"),
            "--error=" + str(output / "logs/%x-%j.err")]
    if settings.get("exclude"):
        args.append("--exclude=" + str(settings["exclude"]))
    args.extend([str(Path(__file__).resolve().with_name("job.sh")),
                 str(Path(config["_config_path"]).resolve()),
                 config.get("python", sys.executable), str(project / "bootstrap.py"), str(slot)])
    return args


def _authorize(config):
    from hpc_recalibration.github_sync import ensure_authorized
    return ensure_authorized(config, interactive=True)


def submit(config, *, dry_run=False, runner=run_command, authorize=None, monitor_start=None):
    """Submit at most one job per slot; explicit scheduler rejection is not retried."""
    prepared = prepare_once(config)
    tasks = load_tasks(config)
    output = Path(config["output_root"]).resolve()
    runtime = output / ".runtime"
    prefix = job_prefix(config)
    with (runtime / "submit.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        pending_slots = [s for s in range(SLOTS) if any(
            not complete(output, t) for i, t in enumerate(tasks) if i % SLOTS == s)]
        if not pending_slots:
            return {"status": "already_complete", "submitted_jobs": [], "completed_tasks": len(tasks)}
        entries = [] if dry_run else queue_entries(config.get("slurm", {}).get("user", "zhuziyuan"), runner)
        active = {s: [e for e in entries if e["name"].startswith(prefix + "-s" + str(s) + "-")
                      and e["state"] not in TERMINAL] for s in pending_slots}
        slots = [s for s in pending_slots if not active[s]]
        path = runtime / "submissions.json"
        ledger = json.loads(path.read_text()) if path.is_file() else {"experiment_id": config["experiment_id"], "attempts": []}
        if ledger["experiment_id"] != config["experiment_id"]:
            raise ValueError("Submission ledger belongs to a different experiment")
        for prior in ledger["attempts"]:
            if not prior.get("job_id") and prior.get("status") in ("submitting", "reply_uncertain"):
                matches = [e for e in entries if e["name"] == prior["name"]]
                if len(matches) == 1:
                    prior.update(job_id=matches[0]["job_id"], status="submitted",
                                 reply_recovered_from_queue=True, observed_at=utc_now())
                    atomic_json(path, ledger)
            if prior["slot"] not in slots or prior.get("job_id") or prior.get("status") == "rejected":
                continue
            if prior.get("status") in ("submitting", "reply_uncertain"):
                raise RuntimeError("A previous submission reply was uncertain; preserve its unique job name and verify it before submitting that slot again")
        if dry_run:
            return {"status": "dry_run", "preparation": prepared,
                    "commands": [slot_command(config, s, prefix + "-s" + str(s) + "-dry") for s in slots],
                    "jobs": len(slots), "time_limit_is_not_verified_partition_maximum": True}
        if slots:
            (authorize or _authorize)(config)
        submitted, failures = [], []
        for slot in slots:
            name = prefix + "-s" + str(slot) + "-" + uuid.uuid4().hex[:6]
            command = slot_command(config, slot, name)
            record = {"slot": slot, "name": name, "command": command, "created_at": utc_now(),
                      "status": "submitting", "job_id": None}
            ledger["attempts"].append(record)
            atomic_json(path, ledger)
            try:
                reply = runner(command)
            except Exception as error:
                record.update(status="reply_uncertain", exception_type=type(error).__name__)
                atomic_json(path, ledger)
                raise
            record.update(returncode=reply.returncode, stdout=reply.stdout, stderr=reply.stderr)
            match = re.fullmatch(r"\s*(\d+)(?:;[^\s]+)?\s*", reply.stdout)
            if reply.returncode != 0 or not match:
                rejected = reply.returncode > 0 and "sbatch:" in reply.stderr.lower() and "error:" in reply.stderr.lower()
                record["status"] = "rejected" if rejected else "reply_uncertain"
                failures.append({"slot": slot, "status": record["status"], "stderr": reply.stderr})
                atomic_json(path, ledger)
                # Other accepted jobs keep running; no automatic submit retry.
                break
            record.update(status="submitted", job_id=match.group(1), submitted_at=utc_now())
            submitted.append({"slot": slot, "job_id": match.group(1)})
            atomic_json(path, ledger)
        warning = None
        monitor_pid = None
        if monitor_start is not None and (submitted or any(active.values())):
            try:
                monitor_pid = monitor_start(config["_config_path"])
            except Exception as error:
                warning = type(error).__name__ + ": independent GitHub monitor startup failed"
                try:
                    atomic_json(runtime / ("monitor_start_failure-" + str(time.time_ns()) + ".json"),
                                {"observed_at": utc_now(), "warning": warning})
                except OSError:
                    traceback.print_exc()
        return {"status": "partial_submission" if failures else "submitted" if submitted else "already_active",
                "submitted_jobs": submitted, "active_slots": {str(s):v for s,v in active.items() if v},
                "submission_failures": failures, "monitor_pid": monitor_pid, "monitor_warning": warning,
                "resources_per_job": {"gpus":1, "cpus":16, "memory":"64G"},
                "evidence_note":"Inspect actual steps/checkpoints; scheduler acceptance is not training completion"}


class StopState:
    def __init__(self):
        self.code = None

    def request(self, number):
        if number in (signal.SIGTERM, signal.SIGINT):
            self.code = 130
        elif self.code is None:
            self.code = 75


def worker_slot(config, slot, *, task_runner, stop=None):
    """Each slot runs its fixed tasks once; checkpoint reuse belongs to task_runner."""
    if slot not in range(SLOTS):
        raise ValueError("slot must be0,1,2")
    tasks = load_tasks(config)
    output = Path(config["output_root"]).resolve()
    runtime = output / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / ("slot-" + str(slot) + ".lock")).open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            emit("slot_already_running", slot=slot)
            return 73
        path = runtime / ("slot-" + str(slot) + ".json")
        history = json.loads(path.read_text()) if path.is_file() else {"runs":[]}
        stop = stop or StopState()
        previous = {n: signal.getsignal(n) for n in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT)}
        for number in previous:
            signal.signal(number, lambda n, frame: stop.request(n))
        job_id = os.environ.get("SLURM_JOB_ID")
        restart = int(os.environ.get("SLURM_RESTART_COUNT", "0") or 0)
        blocked = {r["task_id"] for run in history["runs"] if run.get("job_id") == job_id
                   for r in run.get("finished", []) if r.get("status") == "failed"} if restart else set()
        run = {"slot":slot, "job_id":job_id, "restart_count":restart, "pid":os.getpid(),
               "started_at":utc_now(), "finished":[], "status":"running", "active_task":None}
        history["runs"].append(run)

        def save():
            run["updated_at"] = utc_now()
            atomic_json(path, history)

        save()
        failures = []
        try:
            for index, task in enumerate(tasks):
                if index % SLOTS != slot:
                    continue
                if stop.code:
                    break
                if complete(output, task):
                    emit("task_complete_reused", slot=slot, task_id=task["task_id"])
                    continue
                if task["task_id"] in blocked:
                    failures.append(task["task_id"])
                    emit("failed_task_not_automatically_retried", task_id=task["task_id"])
                    continue
                run["active_task"] = task["task_id"]
                save()
                emit("task_start", slot=slot, index=index, task_id=task["task_id"])
                record = {"task_id":task["task_id"], "index":index, "started_at":utc_now()}
                try:
                    code = task_runner(task, config)
                    if code in (75,130):
                        stop.code = 130 if code == 130 or stop.code == 130 else 75
                        record.update(status="paused" if stop.code ==75 else "cancelled", exit_code=stop.code)
                    elif code != 0 or not complete(output, task):
                        record.update(status="failed", exit_code=code or 1,
                                      missing_completion_marker=code==0)
                        failures.append(task["task_id"])
                    else:
                        record.update(status="completed", exit_code=0)
                except (OSError, MemoryError) as error:
                    record.update(status="storage_or_memory_failure", exception_type=type(error).__name__,
                                  traceback=traceback.format_exc(), exit_code=1)
                    run["finished"].append(record)
                    run.update(status="failed", exit_code=1, finished_at=utc_now())
                    save()
                    raise
                except Exception as error:
                    record.update(status="failed", exception_type=type(error).__name__,
                                  traceback=traceback.format_exc(), exit_code=1)
                    failures.append(task["task_id"])
                record["finished_at"] = utc_now()
                run["finished"].append(record)
                run["active_task"] = None
                save()
                emit("task_exit", slot=slot, task_id=task["task_id"], status=record["status"], exit_code=record["exit_code"])
            code = stop.code or (1 if failures else 0)
            run.update(status="complete" if code==0 else "paused" if code==75 else "cancelled" if code==130 else "failed",
                       exit_code=code, finished_at=utc_now(), active_task=None)
            save()
            emit("slot_exit", slot=slot, status=run["status"], exit_code=code)
            return code
        except BaseException as error:
            code = 130 if isinstance(error, KeyboardInterrupt) else 1
            if isinstance(error, SystemExit) and isinstance(error.code, int):
                code = error.code
            run.update(status="cancelled" if code == 130 else "worker_failed",
                       exception_type=type(error).__name__, traceback=traceback.format_exc(),
                       exit_code=code, finished_at=utc_now())
            try:
                save()
            except OSError:
                # A storage failure may prevent its own receipt; the original
                # exception and full traceback still reach the Slurm log.
                traceback.print_exc()
            raise
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
