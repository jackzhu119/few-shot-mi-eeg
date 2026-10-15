#!/usr/bin/env python3
"""Closed-by-default, single-run launcher for the frozen CSP CPU measurement.

Only the Python standard library and the hash-pinned stdlib input checker are
used here. Default preflight never creates files or imports scientific packages.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import re
import select
import shutil
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/kumar_csp_signed_score_operation_20261015.json"
DIAGNOSTIC = "kumar-csp-signed-score-development-run02-20261015"
PYTHON = "/workspace/.venvs/few-shot-mi-eeg/bin/python"
OUTPUT = "results/kumar_csp_signed_score_20261015/run02"
STATE = "research_logs/kumar_next_source_operations_20261015/csp_signed_score_operation_run02"
RUNTIME = {"python": "3.11.16", "numpy": "2.2.6", "scipy": "1.15.3",
           "scikit-learn": "1.7.2", "mne": "1.10.2"}
MIN_AVAILABLE_MEMORY = 3 * 1024**3
MAX_CONSUMER_RSS = 2 * 1024**3
MIN_RUNNING_CGROUP_HEADROOM = 1024**3
PINS = {
    "scripts/analyze_kumar_csp_signed_score_v1.py": "ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3",
    "scripts/check_kumar_csp_signed_score_inputs.py": "5c05a319dec16950d86885962401d5f28d2d30a07c5287d769aeb03339a94264",
    "configs/kumar_csp_signed_score_input_binding_20261015.json": "e1a103e3b3b8bcba24f15593561bcd3f7d816ff7fa0b178cf4d55915b13c0a7a",
    "docs/kumar_csp_signed_score_memory_budget_20261015.md": "c49dbcd41552e5c5199eb1c601f21eda23ab40766df3638df4101a583a0fc367",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def utc():
    return datetime.now(timezone.utc).isoformat()


def container_identity(proc_root=Path("/proc")):
    fields = (proc_root / "1/stat").read_text().rsplit(")", 1)[1].split()
    return {"hostname": platform.node(),
            "boot_id": (proc_root / "sys/kernel/random/boot_id").read_text().strip(),
            "pid1_start_ticks": fields[19]}


def command():
    return [PYTHON, "-B", "scripts/analyze_kumar_csp_signed_score_v1.py",
            "--epochs", "research_logs/kumar_cross_session_20261012/csp_development_epochs_run01_20261014",
            "--baseline-root", "results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z",
            "--baseline-r2-receipt", "research_logs/recovery_20261014/kumar_results_R2_run01.json",
            "--config", "configs/kumar_csp_reliability_20261014.json", "--output", OUTPUT]


def validate_contract(contract, root=ROOT):
    require(contract == {
        "schema_version": 1, "diagnostic_id": DIAGNOSTIC,
        "status": "proposal_only_unapproved", "execution_enabled": False,
        "cost_authorization": None, "authorization": None,
        "approved_wall_seconds": None, "not_before_unix": None, "deadline_unix": None,
        "allocation": "existing_cpu_no_new_paid_allocation", "query_access": False,
        "gpu_fit_authorized": False, "accepted18_refitting_authorized": False,
        "runtime": RUNTIME, "python_executable": PYTHON,
        "minimum_effective_available_memory_bytes": MIN_AVAILABLE_MEMORY,
        "minimum_free_output_disk_bytes": 2 * 1024**3,
        "maximum_sampled_consumer_rss_bytes": MAX_CONSUMER_RSS,
        "minimum_running_cgroup_headroom_bytes": MIN_RUNNING_CGROUP_HEADROOM,
        "minimum_running_host_available_bytes": MIN_RUNNING_CGROUP_HEADROOM,
        "resource_poll_seconds": 0.25,
        "consumer_timeout_seconds": 7200, "term_grace_seconds": 30,
        "automatic_retries": 0, "output": OUTPUT, "state_directory": STATE,
        "command": command(), "frozen_files": contract.get("frozen_files"),
    }, "Changed fixed single-diagnostic operation")
    pins = contract["frozen_files"]
    require(set(pins) == set(PINS) | {"scripts/run_kumar_csp_signed_score_operation.py"}
            and all(pins[key] == expected for key, expected in PINS.items()),
            "Changed frozen entrypoints/input binding")
    for relative, expected in pins.items():
        path = root / relative
        require(not path.is_symlink() and path.is_file() and sha(path) == expected,
                "Frozen operation source mismatch: " + relative)


def runtime_metadata():
    observed = {"python": platform.python_version()}
    for name in RUNTIME.keys() - {"python"}:
        try:
            observed[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            observed[name] = None
    return observed


def effective_memory(proc_root=Path("/proc"), cgroup_root=Path("/sys/fs/cgroup")):
    """Host availability capped by all observable governing cgroup headrooms.

    Fail closed when the Linux resource proof is unreadable. For a cgroup
    namespace, the mounted root itself can be the current container's boundary.
    """
    fields = dict(line.split(":", 1) for line in (proc_root / "meminfo").read_text().splitlines())
    host = int(fields["MemAvailable"].split()[0]) * 1024
    memberships = (proc_root / "self/cgroup").read_text().splitlines()
    observations = []
    v2 = [line.split(":", 2)[2] for line in memberships if line.startswith("0::")]
    if v2:
        base = cgroup_root.resolve()
        candidate = base / v2[0].lstrip("/")
        require(candidate.resolve().is_relative_to(base), "Unsafe cgroup membership")
        current = candidate if (candidate / "memory.max").is_file() else base
        while True:
            limit_path, used_path = current / "memory.max", current / "memory.current"
            require(limit_path.is_file() and used_path.is_file(), "Unreadable cgroup v2 memory limit")
            raw, used = limit_path.read_text().strip(), int(used_path.read_text())
            limit = None if raw == "max" else int(raw)
            observations.append({"path": str(current), "limit_bytes": limit,
                                 "current_bytes": used,
                                 "headroom_bytes": None if limit is None else max(0, limit - used)})
            if current == base:
                break
            current = current.parent
    else:
        matches = [line.split(":", 2)[2] for line in memberships
                   if "memory" in line.split(":", 2)[1].split(",")]
        require(len(matches) == 1, "No readable governing memory cgroup")
        base = (cgroup_root / "memory").resolve()
        candidate = base / matches[0].lstrip("/")
        require(candidate.resolve().is_relative_to(base), "Unsafe cgroup membership")
        current = candidate if (candidate / "memory.limit_in_bytes").is_file() else base
        while True:
            limit = int((current / "memory.limit_in_bytes").read_text())
            used = int((current / "memory.usage_in_bytes").read_text())
            observations.append({"path": str(current), "limit_bytes": limit,
                                 "current_bytes": used, "headroom_bytes": max(0, limit - used)})
            if current == base:
                break
            current = current.parent
    return {"host_available_bytes": host, "cgroups": observations,
            "effective_available_bytes": min([host] + [row["headroom_bytes"]
                for row in observations if row["headroom_bytes"] is not None])}


def resources(output, memory_reader=effective_memory):
    ancestor = output.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    memory = memory_reader()
    return {"memory": memory, "output_filesystem_path": str(ancestor),
            "free_output_disk_bytes": shutil.disk_usage(ancestor).free}


def input_check():
    path = ROOT / "scripts/check_kumar_csp_signed_score_inputs.py"
    spec = importlib.util.spec_from_file_location("csp_operation_stdlib_input_checker", path)
    module = importlib.util.module_from_spec(spec)
    # Executing a hash-pinned stdlib checker directly avoids .pyc writes even
    # when a caller forgets -B. No numerical module is imported by this checker.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module.check_inputs()


def preflight(contract, *, root=ROOT, runtime_reader=runtime_metadata,
              resource_reader=resources, inputs_reader=input_check):
    started, started_at = time.monotonic(), utc()
    validate_contract(contract, root)
    runtime = runtime_reader()
    try:
        resource = resource_reader(root / OUTPUT)
    except (OSError, KeyError, ValueError) as error:
        resource = {"memory": {"effective_available_bytes": 0}, "free_output_disk_bytes": 0,
                    "observation_failure": {"type": type(error).__name__, "message": str(error)}}
    inputs = inputs_reader()
    problems = []
    if runtime != RUNTIME:
        problems.append("Frozen Python/distribution versions differ")
    if str(Path(sys.executable).absolute()) != PYTHON:
        problems.append("Reviewed CPU venv executable differs")
    if resource["memory"]["effective_available_bytes"] < contract["minimum_effective_available_memory_bytes"]:
        problems.append("Less than 3 GiB effective available RAM")
    if resource["free_output_disk_bytes"] < contract["minimum_free_output_disk_bytes"]:
        problems.append("Less than 2 GiB free output disk")
    if any((root / relative).exists() or (root / relative).is_symlink() for relative in (OUTPUT, STATE)):
        problems.append("Prior output/state/claim exists; no retry or overwrite")
    require(inputs.get("status") == "metadata_verified_execution_closed" and
            inputs.get("numerical_arrays_deserialized") is False and
            inputs.get("execution_authorized") is False, "Invalid metadata input proof")
    return {"status": "execution_closed_not_ready" if problems else "metadata_verified_execution_closed",
            "execution_authorized": False, "ready_for_separate_parent_review": not problems,
            "problems": problems, "runtime": runtime, "resources": resource,
            "inputs": inputs, "preflight_started_at_utc": started_at,
            "preflight_finished_at_utc": utc(), "preflight_seconds": time.monotonic() - started,
            "scientific_consumer_executed": False, "query_access": False}


def authorization_check(auth, contract_sha, commit, *, now=None):
    now = time.time() if now is None else now
    require(isinstance(auth, dict), "Actual parent authorization is required")
    require(auth.get("schema_version") == 1 and auth.get("status") ==
            "parent_reviewed_csp_signed_score_cpu_execution_authorized" and
            auth.get("diagnostic_id") == DIAGNOSTIC and
            auth.get("reviewed_commit") == commit and
            auth.get("operation_contract_sha256") == contract_sha and
            auth.get("container_identity") == container_identity() and
            auth.get("allocation") == "existing_cpu_no_new_paid_allocation" and
            all(auth.get(key) is False for key in ("query_access", "gpu_fit_authorized",
                "accepted18_refitting_authorized", "paid_compute_allocation_authorized")),
            "Exact CPU-only parent authorization/identity required")
    cost = auth.get("cost_authorization")
    require(isinstance(cost, dict) and cost.get("applicable_to_this_cpu_operation") is True and
            isinstance(cost.get("existing_authorization_receipt"), str) and
            bool(cost["existing_authorization_receipt"].strip()) and
            re.fullmatch(r"[0-9a-f]{64}", str(cost.get("existing_authorization_receipt_sha256", ""))),
            "Actual current applicable existing-CPU cost authorization reference/SHA required")
    start, deadline, approved = (auth.get(key) for key in
                                ("not_before_unix", "deadline_unix", "approved_wall_seconds"))
    require(all(isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) for value in (start, deadline, approved)) and
            approved > 30 and deadline - start == approved and start <= now < deadline - 30,
            "Current explicit absolute authorization window required; no deadline reset")
    return deadline


def member_inventory(folder):
    if not folder.exists():
        return []
    rows = []
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Unexpected output symlink")
        if path.is_file():
            rows.append({"path": path.relative_to(folder).as_posix(), "bytes": path.stat().st_size,
                         "sha256": sha(path)})
    return rows


def stop_process(process, grace, observed_descendants=None):
    if observed_descendants:
        return stop_tracked_process(process, grace, observed_descendants)
    events = []
    for signum, seconds in ((signal.SIGTERM, grace), (signal.SIGKILL, 5)):
        try:
            os.killpg(process.pid, signum)
            events.append({"signal": signal.Signals(signum).name, "at_utc": utc()})
        except ProcessLookupError:
            pass
        try:
            return process.wait(timeout=max(0, seconds)), events
        except subprocess.TimeoutExpired:
            pass
    raise RuntimeError("Child process did not reap after SIGKILL")


def stop_tracked_process(process, grace, history):
    """Stop known identities via pidfds; escaped groups share the same grace."""
    deadline = time.monotonic() + max(0, grace)
    handles, failures, events = {}, [], []
    proc = Path("/proc")
    try:
        try:
            proc_visibility(proc)
            before = process_snapshot(proc)
            for pid, expected in history.items():
                if pid not in before:
                    continue  # Absence must also hold in the second full snapshot.
                try:
                    handle = os.pidfd_open(pid)
                    try:
                        require(process_record(pid, proc)["start_ticks"] == expected,
                                "Refusing signal to reused descendant PID")
                    except BaseException:
                        os.close(handle)
                        raise
                    handles[pid] = handle
                except (OSError, ValueError, IndexError, KeyError) as error:
                    failures.append(f"PID {pid}: {type(error).__name__}: {error}")
            require(process_snapshot(proc) == before, "Unstable procfs cleanup identity/topology")
        except (OSError, ValueError, IndexError, KeyError) as error:
            failures.append(type(error).__name__ + ": " + str(error))

        for signum in (signal.SIGTERM, signal.SIGKILL):
            ready = set(select.select(list(handles.values()), [], [], 0)[0])
            live = {pid: handle for pid, handle in handles.items() if handle not in ready}
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signum)
                    events.append({"signal": signal.Signals(signum).name, "at_utc": utc(),
                                   "target_process_group": process.pid})
                except OSError as error:
                    failures.append(type(error).__name__ + ": " + str(error))
            for pid, handle in live.items():
                try:
                    signal.pidfd_send_signal(handle, signum)
                    events.append({"signal": signal.Signals(signum).name, "at_utc": utc(),
                                   "target_pid": pid, "start_ticks": history[pid]})
                except ProcessLookupError:
                    pass  # This identity exited; pidfd never targets a reused PID.
                except OSError as error:
                    failures.append(type(error).__name__ + ": " + str(error))
            if signum == signal.SIGKILL:
                break
            while time.monotonic() < deadline:
                ready = set(select.select(list(handles.values()), [], [], 0)[0])
                if process.poll() is not None and len(ready) == len(handles):
                    break
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            if process.poll() is not None and len(ready) == len(handles):
                break
        code = process.wait(timeout=5)  # Reaping after the existing KILL boundary.
        if len(select.select(list(handles.values()), [], [], 0)[0]) != len(handles):
            failures.append("Tracked descendant exit not yet proven after SIGKILL")
        require(not failures, "Process cleanup proof failed: " + "; ".join(failures))
        return code, events
    except BaseException as error:
        error.signal_events = events
        raise
    finally:
        for handle in handles.values():
            os.close(handle)


@contextmanager
def deadline_guard(deadline):
    """Interrupt Python-visible blocking work without renewing a fixed deadline.

    An existing real-time alarm is not ours to cancel or reschedule. Refuse it
    before launch, and restore the original handler after our one-shot timer.
    This cannot interrupt uninterruptible kernel I/O or make Popen atomic.
    """
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
            "Existing real-time alarm prevents this operation")
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise TimeoutError("Fixed CPU operation deadline reached; preserve partial evidence")

    signal.signal(signal.SIGALRM, expired)
    try:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            expired(None, None)
        signal.setitimer(signal.ITIMER_REAL, remaining)
        yield
        if time.monotonic() >= deadline:
            expired(None, None)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def proc_visibility(proc_root):
    """Require an unfiltered proc mount for this process's PID namespace."""
    mountpoint = str(proc_root.resolve())
    matches = []
    for line in (proc_root / "self/mountinfo").read_text().splitlines():
        left, right = line.split(" - ", 1)
        fields, filesystem = left.split(), right.split()
        path = fields[4]
        if path == mountpoint:
            matches.append((fields, filesystem))
        if path.startswith(mountpoint + "/"):
            require(not path[len(mountpoint) + 1:].split("/", 1)[0].isdecimal(),
                    "Masked procfs process subtree prevents complete visibility")
    require(len(matches) == 1, "Ambiguous or missing procfs mount")
    fields, filesystem = matches[0]
    options = set(fields[5].split(",") + filesystem[2].split(","))
    require(fields[3] == "/" and filesystem[0] == "proc"
            and all(not option.startswith("subset=")
                    and (not option.startswith("hidepid=") or option == "hidepid=0")
                    for option in options), "Filtered or non-proc process visibility")
    namespace = os.readlink(proc_root / "self/ns/pid")
    require(namespace == os.readlink(proc_root / "1/ns/pid"),
            "Procfs PID namespace differs from the current namespace")
    status = dict(line.split(":", 1) for line in (proc_root / "self/status").read_text().splitlines()
                  if ":" in line)
    require(int(status["Pid"]) == os.getpid() and int(status["Tgid"]) == os.getpid(),
            "Procfs current process identity is not visible")
    return {"mountpoint": mountpoint, "mount_options": sorted(options),
            "pid_namespace": namespace, "observer_pid": os.getpid()}


def process_record(pid, proc_root):
    raw = (proc_root / str(pid) / "stat").read_text()
    fields = raw.rsplit(")", 1)[1].split()
    require(int(raw.split("(", 1)[0]) == pid and len(fields) >= 22,
            "Malformed procfs process identity")
    return {"pid": pid, "ppid": int(fields[1]), "pgrp": int(fields[2]),
            "session": int(fields[3]), "start_ticks": int(fields[19]),
            "zombie": fields[0] == "Z"}


def process_snapshot(proc_root):
    """Read every visible PID, refusing process census or identity races.

    procfs reads are sampled, not atomic: processes born and gone entirely
    between observations cannot be accounted for. No missing proof is skipped.
    """
    def census():
        return {int(path.name) for path in proc_root.iterdir() if path.name.isdecimal()}

    pids = census()
    rows = {}
    for pid in sorted(pids):
        rows[pid] = process_record(pid, proc_root)
    require(census() == pids, "Unstable procfs PID census")
    return rows


def running_memory(pid, proc_root=Path("/proc"), observed_descendants=None):
    visibility = proc_visibility(proc_root)
    history = {} if observed_descendants is None else observed_descendants
    before = process_snapshot(proc_root)
    require(pid in before and before[pid]["session"] == pid,
            "Missing consumer or dedicated process session")
    for previous, start_ticks in history.items():
        require(previous not in before or before[previous]["start_ticks"] == start_ticks,
                "Previously observed descendant PID was reused")
    # PPID closure includes descendants that change sessions; the dedicated
    # session retains reparented children. History keeps a previously observed
    # live descendant even if it subsequently changes both session and parent.
    pending = [value for value, row in before.items()
               if row["session"] == pid or value in history]
    seen, members = set(), []
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(value for value, row in before.items() if row["ppid"] == current)
    absent = sorted(set(history) - set(before))
    # Preserve observed identities for fail-closed cleanup even if RSS or the
    # second snapshot fails. Cleanup revalidates each identity before signaling.
    history.update({current: before[current]["start_ticks"] for current in seen})
    for current in sorted(seen):
        row = before[current]
        fields = dict(line.split(":", 1) for line in (proc_root / str(current) / "status").read_text().splitlines()
                      if ":" in line)
        require(int(fields["Pid"]) == current and int(fields["Tgid"]) == current
                and int(fields["PPid"]) == row["ppid"]
                and fields["State"].strip().startswith("Z") == row["zombie"],
                "Changed procfs status identity/topology")
        if row["zombie"]:
            rss = 0  # Only an explicitly observed zombie has no resident memory.
        else:
            value, unit = fields["VmRSS"].split()
            require(unit == "kB" and int(value) >= 0, "Invalid procfs VmRSS")
            rss = int(value) * 1024
        members.append({**row, "tgid": current, "rss_bytes": rss})
    after = process_snapshot(proc_root)
    require(before == after, "Unstable procfs process identity/topology")
    require(proc_visibility(proc_root) == visibility, "Procfs visibility changed during sampling")
    memory = effective_memory()
    finite = [row["headroom_bytes"] for row in memory["cgroups"] if row["headroom_bytes"] is not None]
    return {"consumer_rss_bytes": sum(row["rss_bytes"] for row in members),
            "process_tree_pids": sorted(seen), "process_tree_members": members,
            "process_snapshot_method": "visible_procfs_ppid_and_dedicated_session_two_snapshots",
            "visible_process_count": len(before), "proc_visibility": visibility,
            "previously_observed_stably_absent_pids": absent,
            "host_available_bytes": memory["host_available_bytes"],
            "cgroup_headroom_bytes": min(finite) if finite else None}


def execute(contract, auth, *, contract_sha, commit, auth_sha, root=ROOT,
            preflight_reader=preflight, popen=subprocess.Popen, memory_reader=None):
    observed_descendants = {}
    if memory_reader is None:
        def memory_reader(pid):
            return running_memory(pid, observed_descendants=observed_descendants)
    deadline = authorization_check(auth, contract_sha, commit)
    absolute_deadline = time.monotonic() + deadline - time.time()
    with deadline_guard(absolute_deadline - 30):
        require(re.fullmatch(r"[0-9a-f]{40}", commit or ""), "Full reviewed commit required")
        require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == commit,
                "Reviewed fixed checkout differs")
        require(not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True).strip(),
                "Tracked checkout changed since review")
        checked = preflight_reader(contract, root=root)
        require(checked["ready_for_separate_parent_review"], "CPU preflight not ready: " + "; ".join(checked["problems"]))
        require(time.time() < deadline - 30, "Authorization expired during preflight")
    state = root / STATE
    state.mkdir(parents=True, exist_ok=False)
    claim = {"diagnostic_id": DIAGNOSTIC, "claimed_at_utc": utc(), "reviewed_commit": commit,
             "operation_contract_sha256": contract_sha, "authorization_sha256": auth_sha,
             "container_identity": container_identity(), "absolute_deadline_unix": deadline,
             "automatic_retries": 0, "preflight": checked}
    receipt = {**claim, "status": "launcher_started", "consumer_started_at_utc": None,
               "consumer_finished_at_utc": None, "returncode": None, "timeout": False,
               "interrupted": False, "signals": [], "output_members": [],
               "resource_samples": [], "maximum_observed_consumer_rss_bytes": None,
               "resource_limit_stop": False,
               "descendant_cleanup_required_after_root_exit": False,
               "scientific_completion_accepted": False, "independently_audited": False,
               "R2_full_GET_verified": False, "accepted": False, "query_access": False}
    process, old_handlers, stop_attempted = None, {}, False

    def remaining_grace():
        return min(30, max(0, deadline - time.time()),
                   max(0, absolute_deadline - time.monotonic()))

    def stop_consumer():
        nonlocal stop_attempted
        require(not stop_attempted, "Consumer cleanup already attempted; no renewed grace")
        stop_attempted = True
        try:
            if observed_descendants:
                return stop_process(process, remaining_grace(), observed_descendants)
            return stop_process(process, remaining_grace())
        except BaseException as error:
            receipt["signals"] = getattr(error, "signal_events", [])
            receipt["stop_failure"] = {"type": type(error).__name__, "message": str(error)}
            raise

    def interrupt(signum, frame):
        # A separate session does not receive the launcher's TERM/HUP; explicitly
        # stop the child's entire process group through the exception boundary.
        for number in old_handlers:
            signal.signal(number, signal.SIG_IGN)
        raise InterruptedError("Launcher received " + signal.Signals(signum).name)

    try:
        for number in (signal.SIGTERM, signal.SIGHUP):
            old_handlers[number] = signal.signal(number, interrupt)
        with deadline_guard(absolute_deadline - 30):
            write_new(state / "claim.json", claim)
        with (state / "consumer.log").open("xb") as log:
            launch_started = time.monotonic()
            timeout = min(contract["consumer_timeout_seconds"], deadline - time.time() - 30,
                          absolute_deadline - launch_started - 30)
            if timeout <= 0:
                raise TimeoutError("Authorization expired before consumer start")
            consumer_deadline = launch_started + timeout
            receipt["consumer_launch_attempt_started_at_utc"] = utc()
            env = dict(os.environ, PYTHONPATH=str(root / "src") + os.pathsep + str(root / "scripts"))
            # Bind elapsed time before Popen; arm the timer only after owning the
            # returned handle so an interrupted constructor cannot orphan a child.
            # OS process creation itself is not claimed to have a hard time bound.
            process = popen(command(), cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
            receipt["consumer_started_at_utc"] = utc()
            with deadline_guard(consumer_deadline):
                write_new(state / "consumer_start.json", {"started_at_utc": receipt["consumer_started_at_utc"],
                          "launch_attempt_started_at_utc": receipt["consumer_launch_attempt_started_at_utc"],
                          "pid": process.pid, "command": command(), "timeout_seconds": timeout})
                while process.poll() is None:
                    remaining = min(consumer_deadline - time.monotonic(), deadline - time.time() - 30)
                    if remaining <= 0:
                        raise TimeoutError("Authorization or consumer deadline reached")
                    try:
                        observed = memory_reader(process.pid)
                    except (OSError, KeyError, ValueError):
                        if process.poll() is None:
                            raise
                        break
                    receipt["resource_samples"].append({"at_utc": utc(), **observed})
                    peak = receipt["maximum_observed_consumer_rss_bytes"] or 0
                    receipt["maximum_observed_consumer_rss_bytes"] = max(peak, observed["consumer_rss_bytes"])
                    rss_exceeded = observed["consumer_rss_bytes"] >= contract["maximum_sampled_consumer_rss_bytes"]
                    headroom = observed["cgroup_headroom_bytes"]
                    headroom_exceeded = headroom is not None and headroom <= contract["minimum_running_cgroup_headroom_bytes"]
                    host_exceeded = observed["host_available_bytes"] <= contract["minimum_running_host_available_bytes"]
                    if rss_exceeded or headroom_exceeded or host_exceeded:
                        receipt["resource_limit_stop"] = True
                        break
                    remaining = min(consumer_deadline - time.monotonic(), deadline - time.time() - 30)
                    if remaining <= 0:
                        raise TimeoutError("Authorization or consumer deadline reached")
                    try:
                        receipt["returncode"] = process.wait(timeout=min(contract["resource_poll_seconds"], remaining))
                        break
                    except subprocess.TimeoutExpired:
                        pass
            if receipt["resource_limit_stop"]:
                # The consumer timer must not interrupt TERM grace and cause a
                # second stop attempt with a newly granted grace period.
                receipt["returncode"], receipt["signals"] = stop_consumer()
            if receipt["returncode"] is None:
                receipt["returncode"] = process.poll()
            if observed_descendants and not stop_attempted:
                # Root exit alone cannot prove a previously observed escaped
                # descendant has exited. Prove all identities, stopping any
                # survivor within the original cleanup allowance exactly once.
                receipt["returncode"], receipt["signals"] = stop_consumer()
                receipt["descendant_cleanup_required_after_root_exit"] = bool(receipt["signals"])
            receipt["status"] = "consumer_exited_zero_pending_audit" if receipt["returncode"] == 0 and not (receipt["timeout"] or receipt["resource_limit_stop"] or receipt["descendant_cleanup_required_after_root_exit"]) else "consumer_failed_preserved"
    except BaseException as error:
        receipt["interrupted"] = isinstance(error, (KeyboardInterrupt, InterruptedError))
        receipt["timeout"] = receipt["timeout"] or isinstance(error, TimeoutError)
        receipt["status"] = "consumer_interrupted_preserved" if receipt["interrupted"] else "launcher_failed_preserved"
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
        if process is not None and not stop_attempted and (process.poll() is None or observed_descendants):
            try:
                receipt["returncode"], receipt["signals"] = stop_consumer()
            except BaseException as stop_error:
                receipt["stop_failure"] = {"type": type(stop_error).__name__, "message": str(stop_error)}
        elif process is not None:
            receipt["returncode"] = process.poll()
    finally:
        receipt["consumer_finished_at_utc"] = utc()
        try:
            receipt["output_members"] = member_inventory(root / OUTPUT)
        except Exception as error:
            receipt["inventory_failure"] = {"type": type(error).__name__, "message": str(error)}
            receipt["status"] = "output_inventory_failed_preserved"
        try:
            receipt["consumer_log_sha256"] = sha(state / "consumer.log") if (state / "consumer.log").is_file() else None
        except Exception as error:
            receipt["log_hash_failure"] = {"type": type(error).__name__, "message": str(error)}
            receipt["status"] = "log_hash_failed_preserved"
        try:
            # Exclusive publication: no historical receipt or failed claim is rewritten.
            write_new(state / "launcher_receipt.json", receipt)
        except Exception as error:
            receipt["status"] = "launcher_receipt_publication_failed_preserved"
            receipt["receipt_publication_failure"] = {"type": type(error).__name__, "message": str(error)}
            try:
                write_new(state / "emergency_receipt.json", receipt)
            except Exception as emergency:
                # Disk loss, SIGKILL and machine loss cannot promise durable output.
                sys.stderr.write(json.dumps({"launcher_receipt": receipt,
                    "emergency_publication_failure": str(emergency)}, allow_nan=False) + "\n")
        finally:
            for number, previous in old_handlers.items():
                signal.signal(number, previous)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-commit")
    parser.add_argument("--reviewed-contract-sha256")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--authorization-sha256")
    args = parser.parse_args()
    contract = read(CONTRACT)
    proposal = CONTRACT.with_suffix(".proposal.sha256").read_text().split()
    require(len(proposal) == 2 and proposal[1] == CONTRACT.relative_to(ROOT).as_posix()
            and proposal[0] == sha(CONTRACT), "Operation proposal checksum differs")
    if args.execute:
        require(args.reviewed_contract_sha256 == sha(CONTRACT), "Reviewed operation contract SHA required")
        require(args.authorization is not None and args.authorization_sha256 is not None and
                sha(args.authorization) == args.authorization_sha256, "Actual authorization file/SHA required")
        result = execute(contract, read(args.authorization), contract_sha=sha(CONTRACT),
                         commit=args.expected_commit, auth_sha=args.authorization_sha256)
    else:
        result = preflight(contract)
    print(json.dumps(result, indent=2, allow_nan=False))
    if args.execute and result["status"] != "consumer_exited_zero_pending_audit":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
