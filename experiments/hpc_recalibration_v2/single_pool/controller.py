"""One allocation, a fixed queue, and at most two isolated GPU workers."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import uuid


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
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


class StopState:
    def __init__(self):
        self.code = None

    def request(self, number):
        if number in (signal.SIGTERM, signal.SIGINT):
            self.code = 130
        elif self.code is None:
            self.code = 75


def complete(output, task):
    path = output / "tasks" / task["task_id"] / "complete.json"
    if not path.is_file():
        return False
    value = json.loads(path.read_text())
    if value.get("task_id") != task["task_id"] or not (value.get("identity") or value.get("task_identity")):
        raise RuntimeError("Malformed task completion marker: " + task["task_id"])
    return True


def gpu_bindings(count, value=None):
    value = os.environ.get("CUDA_VISIBLE_DEVICES", "") if value is None else value
    tokens = [part.strip() for part in value.split(",") if part.strip()]
    if len(tokens) < count or len(set(tokens)) != len(tokens) or "-1" in tokens:
        raise RuntimeError("Slurm CUDA_VISIBLE_DEVICES does not identify the allocated worker GPUs")
    return tokens[:count]


def run_pool(config, tasks, *, indices=None, bindings=None, popen=subprocess.Popen,
             sleep=time.sleep, stop=None, signal_group=os.killpg, poll_seconds=0.2):
    """Run each pending index once per invocation; only explicit resumes retry failures."""
    output = Path(config["output_root"])
    runtime = output / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(parents=True, exist_ok=True)
    count = int(config.get("slurm", {}).get("pool_workers", 2))
    if not 1 <= count <= 2:
        raise ValueError("single-pool workers must be one or two")
    selected = list(range(len(tasks))) if indices is None else list(indices)
    if len(set(selected)) != len(selected) or any(type(i) is not int or not 0 <= i < len(tasks) for i in selected):
        raise ValueError("indices must be distinct valid task indices")
    selected.sort()
    stop = stop or StopState()
    with (runtime / "pool.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"event": "pool_already_running", "utc": utc_now()}), flush=True)
            return 73
        skipped = [i for i in selected if complete(output, tasks[i])]
        pending = [i for i in selected if i not in skipped]
        if not pending:
            print(json.dumps({"event": "pool_already_complete", "skipped": skipped}), flush=True)
            return 0
        bindings = list(bindings) if bindings is not None else gpu_bindings(count)
        if len(bindings) < count or len(set(bindings[:count])) != count:
            raise ValueError("worker GPU bindings must be distinct")
        return _run_locked(config, tasks, selected, pending, skipped, bindings[:count],
                           popen, sleep, stop, signal_group, poll_seconds)


def _run_locked(config, tasks, selected, pending, skipped, bindings, popen, sleep,
                stop, signal_group, poll_seconds):
    output = Path(config["output_root"])
    path = output / ".runtime" / "single_pool_state.json"
    history = json.loads(path.read_text()) if path.is_file() else {"schema_version": 1, "runs": []}
    job_id = os.environ.get("SLURM_JOB_ID")
    restart_count = int(os.environ.get("SLURM_RESTART_COUNT", "0") or "0")
    if restart_count > 0 and not job_id:
        raise RuntimeError("Automatic requeue lacks its Slurm job identity; no task was dispatched")
    previous_failures = {index for run in history["runs"] if run.get("job_id") == job_id
                         for index in run.get("failed_indices", [])} if restart_count > 0 else set()
    blocked = sorted(set(pending) & previous_failures)
    pending = [index for index in pending if index not in previous_failures]
    current = {"run_id": uuid.uuid4().hex, "job_id": job_id,
               "controller_pid": os.getpid(), "started_at": utc_now(), "indices": selected,
               "skipped_complete": skipped, "dispatches": [], "finished": [],
               "failed_indices": [], "blocked_failed_indices": blocked,
               "slurm_restart_count": restart_count, "status": "running"}
    history["runs"].append(current)
    active = {}
    signaled = {}
    last_heartbeat = 0.0
    heartbeat = float(config.get("runtime", {}).get("heartbeat_seconds", 30))

    def save(event):
        current["pending_indices"] = list(pending)
        current["active"] = [{"slot": slot, "index": item["index"], "pid": item["process"].pid}
                             for slot, item in sorted(active.items())]
        current["updated_at"] = utc_now()
        atomic_json(path, history)
        print(json.dumps({"event": event, "utc": current["updated_at"],
                          "active": current["active"], "pending": len(pending)}), flush=True)

    def forward():
        if stop.code is None:
            return
        sig = signal.SIGTERM if stop.code == 130 else signal.SIGUSR1
        for item in active.values():
            process = item["process"]
            if signaled.get(process.pid) == sig:
                continue
            try:
                signal_group(process.pid, sig)
            except ProcessLookupError:
                pass
            signaled[process.pid] = sig

    save("pool_start")
    try:
        while pending or active:
            forward()
            for slot, item in list(active.items()):
                code = item["process"].poll()
                if code is None:
                    continue
                item["log"].close()
                index = item["index"]
                current["finished"].append({"index": index, "task_id": tasks[index]["task_id"],
                                            "exit_code": code, "finished_at": utc_now()})
                if code == 75:
                    stop.request(signal.SIGUSR1)
                elif code == 130:
                    stop.request(signal.SIGTERM)
                elif ((code == -signal.SIGUSR1 and stop.code == 75
                       and signaled.get(item["process"].pid) == signal.SIGUSR1)
                      or (code == -signal.SIGTERM and stop.code == 130
                          and signaled.get(item["process"].pid) == signal.SIGTERM)):
                    current["finished"][-1].update(
                        interruption_boundary="forwarded_signal_before_or_after_worker_handler",
                        execution_before_signal_unknown=True)
                elif code != 0:
                    current["failed_indices"].append(index)
                elif not complete(output, tasks[index]):
                    # A clean process exit alone cannot establish task completion.
                    current["failed_indices"].append(index)
                    current["finished"][-1]["missing_completion_marker"] = True
                del active[slot]
                save("worker_exit")
            forward()
            if stop.code is not None:
                if not active:
                    break
            else:
                for slot in range(len(bindings)):
                    if stop.code is not None:
                        break
                    if slot in active or not pending:
                        continue
                    index = pending.pop(0)
                    # Completion could arrive between startup and dispatch.
                    if complete(output, tasks[index]):
                        current["skipped_complete"].append(index)
                        continue
                    task = tasks[index]
                    filename = f"pool-{current['job_id'] or 'local'}-{task['task_id']}-{time.time_ns()}.log"
                    logfile = output / "logs" / filename
                    log = logfile.open("xb")
                    env = os.environ.copy()
                    env["CUDA_VISIBLE_DEVICES"] = bindings[slot]
                    env["PYTHONUNBUFFERED"] = "1"
                    command = [config.get("python", sys.executable), "-u",
                               str(Path(config["project_dir"]) / "bootstrap.py"), "worker",
                               "--config", config["_config_path"], "--index", str(index)]
                    record = {"index": index, "task_id": task["task_id"], "slot": slot,
                              "visible_gpu": bindings[slot], "log": str(logfile),
                              "command": command, "intent_at": utc_now()}
                    current["dispatches"].append(record)
                    save("worker_launch_intent")
                    try:
                        process = popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                        start_new_session=True)
                    except BaseException:
                        log.close()
                        raise
                    record.update(pid=process.pid, started_at=utc_now())
                    active[slot] = {"index": index, "process": process, "log": log}
                    save("worker_started")
                    forward()
            if time.monotonic() - last_heartbeat >= heartbeat:
                save("pool_heartbeat")
                last_heartbeat = time.monotonic()
            if active:
                sleep(poll_seconds)
        code = 130 if stop.code == 130 else 1 if (
            current["failed_indices"] or current["blocked_failed_indices"]) else stop.code or 0
        current.update(status="complete" if code == 0 else "paused" if code == 75 else "cancelled" if code == 130 else "failed",
                       exit_code=code, finished_at=utc_now())
        save("pool_exit")
        return code
    except BaseException as error:
        exception_code = 130 if isinstance(error, KeyboardInterrupt) else 1
        if isinstance(error, SystemExit) and isinstance(error.code, int):
            exception_code = error.code
        current.update(status="controller_failed", exception=traceback.format_exc(),
                       exit_code=exception_code, finished_at=utc_now())
        stop.request(signal.SIGTERM)
        forward()
        deadline = time.monotonic() + 30
        while active and time.monotonic() < deadline:
            for slot, item in list(active.items()):
                if item["process"].poll() is not None:
                    item["log"].close()
                    del active[slot]
            if active:
                sleep(min(poll_seconds, 0.1))
        for item in active.values():
            try:
                signal_group(item["process"].pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            item["log"].close()
        try:
            save("pool_exception")
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--indices")
    args = parser.parse_args()
    raw = json.loads(Path(args.config).read_text())
    sys.path.insert(0, raw["project_dir"])
    from hpc_recalibration.preflight import load_config, load_tasks, lightweight_ready
    config = load_config(args.config)
    lightweight_ready(config)
    stop = StopState()
    for number in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT):
        signal.signal(number, lambda value, frame: stop.request(value))
    indices = [int(i) for i in args.indices.split(",")] if args.indices else None
    return run_pool(config, load_tasks(config), indices=indices, stop=stop)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
