"""Synthetic metadata and inert child processes only; no consumer/EEG/model run."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "csp_cpu_operation_software_test",
    Path(__file__).parents[1] / "scripts/run_kumar_csp_signed_score_operation.py")
operation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operation)


def input_proof():
    return {"status": "metadata_verified_execution_closed", "numerical_arrays_deserialized": False,
            "execution_authorized": False, "synthetic": True, "software_validation_only": True}


def resource_proof(output):
    return {"memory": {"effective_available_bytes": 16 * 1024**3},
            "free_output_disk_bytes": 4 * 1024**3, "synthetic": True}


@pytest.fixture
def prepared(tmp_path):
    contract = json.loads(operation.CONTRACT.read_text())
    for relative in contract["frozen_files"]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((operation.ROOT / relative).read_bytes())
    contract["frozen_files"]["scripts/run_kumar_csp_signed_score_operation.py"] = operation.sha(
        tmp_path / "scripts/run_kumar_csp_signed_score_operation.py")

    def preflight(**overrides):
        kwargs = {"root": tmp_path, "runtime_reader": lambda: dict(operation.RUNTIME),
                  "resource_reader": resource_proof, "inputs_reader": input_proof}
        kwargs.update(overrides)
        return operation.preflight(contract, **kwargs)

    return tmp_path, contract, preflight


def auth_fixture():
    # In-memory software fixture, never an operational authorization file.
    return {"schema_version": 1,
            "status": "parent_reviewed_csp_signed_score_cpu_execution_authorized",
            "diagnostic_id": operation.DIAGNOSTIC, "reviewed_commit": "a" * 40,
            "operation_contract_sha256": "b" * 64,
            "container_identity": operation.container_identity(),
            "allocation": "existing_cpu_no_new_paid_allocation", "query_access": False,
            "gpu_fit_authorized": False, "accepted18_refitting_authorized": False,
            "paid_compute_allocation_authorized": False,
            "cost_authorization": {"applicable_to_this_cpu_operation": True,
                "existing_authorization_receipt": "synthetic://software-validation-only",
                "existing_authorization_receipt_sha256": "c" * 64},
            "not_before_unix": 900, "deadline_unix": 9000, "approved_wall_seconds": 8100,
            "synthetic": True, "software_validation_only": True}


def test_default_preflight_is_read_only_and_closed(prepared):
    root, _, preflight = prepared
    before = {str(p): operation.sha(p) for p in root.rglob("*") if p.is_file()}
    result = preflight()
    assert result["status"] == "metadata_verified_execution_closed"
    assert result["execution_authorized"] is result["scientific_consumer_executed"] is False
    assert before == {str(p): operation.sha(p) for p in root.rglob("*") if p.is_file()}
    assert not (root / operation.STATE).exists()
    assert not (root / operation.OUTPUT).exists()


@pytest.mark.parametrize("changed", operation.RUNTIME)
def test_any_frozen_runtime_change_prevents_execution(prepared, changed):
    _, _, preflight = prepared
    runtime = dict(operation.RUNTIME, **{changed: "changed"})
    result = preflight(runtime_reader=lambda: runtime)
    assert result["status"] == "execution_closed_not_ready"


@pytest.mark.parametrize("kind", ["ram", "disk", "state", "output"])
def test_resource_shortage_or_prior_state_refuses_without_writes(prepared, kind):
    root, _, preflight = prepared
    resource = resource_proof(None)
    if kind == "ram":
        resource["memory"]["effective_available_bytes"] = 3 * 1024**3 - 1
    elif kind == "disk":
        resource["free_output_disk_bytes"] = 2 * 1024**3 - 1
    else:
        (root / (operation.STATE if kind == "state" else operation.OUTPUT)).mkdir(parents=True)
    result = preflight(resource_reader=lambda _: resource)
    assert result["status"] == "execution_closed_not_ready"


def test_changed_frozen_source_rejected_before_any_input_check(prepared):
    root, _, preflight = prepared
    (root / next(iter(operation.PINS))).write_bytes(b"SYNTHETIC TAMPER")
    with pytest.raises(ValueError, match="Frozen operation source mismatch"):
        preflight(inputs_reader=lambda: pytest.fail("Must reject before inputs"))


def test_cgroup_ancestor_headroom_caps_host_memory(tmp_path):
    proc, groups = tmp_path / "proc", tmp_path / "cgroups"
    (proc / "self").mkdir(parents=True)
    (proc / "meminfo").write_text("MemAvailable: 33554432 kB\n")
    (proc / "self/cgroup").write_text("0::/child\n")
    (groups / "child").mkdir(parents=True)
    (groups / "memory.max").write_text(str(8 * 1024**3))
    (groups / "memory.current").write_text(str(1024**3))
    (groups / "child/memory.max").write_text("max")
    (groups / "child/memory.current").write_text("0")
    result = operation.effective_memory(proc, groups)
    assert result["effective_available_bytes"] == 7 * 1024**3
    assert len(result["cgroups"]) == 2


@pytest.fixture
def procfs_tree(tmp_path, monkeypatch):
    proc = tmp_path / "proc"
    proc.mkdir()

    def member(pid, ppid, session, rss_kib, *, zombie=False):
        path = proc / str(pid)
        path.mkdir()
        fields = ["0"] * 22
        fields[0:4] = ["Z" if zombie else "S", str(ppid), str(session), str(session)]
        fields[19] = str(10000 + pid)
        (path / "stat").write_text(f"{pid} (synthetic ) process) " + " ".join(fields) + "\n")
        (path / "status").write_text(
            f"State:\t{fields[0]} (synthetic)\nPid:\t{pid}\nTgid:\t{pid}\nPPid:\t{ppid}\n"
            + ("" if zombie else f"VmRSS:\t{rss_kib} kB\n"))

    member(1, 0, 1, 512)
    (proc / "self/ns").mkdir(parents=True)
    (proc / "1/ns").mkdir()
    (proc / "self/ns/pid").symlink_to("pid:[synthetic]")
    (proc / "1/ns/pid").symlink_to("pid:[synthetic]")
    (proc / "self/status").write_text(f"Pid:\t{os.getpid()}\nTgid:\t{os.getpid()}\n")
    (proc / "self/mountinfo").write_text(f"53 52 0:30 / {proc} rw,nosuid,nodev,noexec - proc proc rw\n")
    member(100, 1, 100, 1024)  # Dedicated root, with no task/*/children files.
    member(101, 100, 100, 2048)
    member(102, 101, 200, 4096)  # Grandchild changed session but still in PPID closure.
    member(103, 1, 100, 8192)  # Reparented child remains in the dedicated session.
    member(104, 100, 100, 0, zombie=True)
    member(200, 1, 200, 16384)  # Unrelated process excluded.
    monkeypatch.setattr(operation, "effective_memory", lambda: {
        "host_available_bytes": 16 * 1024**3,
        "cgroups": [{"headroom_bytes": 4 * 1024**3}]})
    return proc


def test_procfs_snapshot_counts_full_tree_and_session_orphan_without_children_files(procfs_tree):
    observed = operation.running_memory(100, procfs_tree)
    assert observed["process_tree_pids"] == [100, 101, 102, 103, 104]
    assert observed["consumer_rss_bytes"] == (1024 + 2048 + 4096 + 8192) * 1024
    assert observed["visible_process_count"] == 7
    assert observed["process_tree_members"][-1]["zombie"] is True
    assert observed["process_tree_members"][-1]["rss_bytes"] == 0


@pytest.mark.parametrize("missing", ["101/stat", "101/status", "200/stat"])
def test_procfs_missing_member_or_census_proof_is_never_zero_or_skipped(procfs_tree, missing):
    (procfs_tree / missing).unlink()
    with pytest.raises(FileNotFoundError):
        operation.running_memory(100, procfs_tree)


def test_procfs_unreadable_stat_propagates_without_retry(procfs_tree, monkeypatch):
    original = Path.read_text
    failures = []

    def unreadable(path, *args, **kwargs):
        if path == procfs_tree / "101/stat":
            failures.append(path)
            raise PermissionError("Synthetic unreadable process identity")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(PermissionError):
        operation.running_memory(100, procfs_tree)
    assert len(failures) == 1


@pytest.mark.parametrize("change", ["new_pid", "lost_pid", "start_ticks", "ppid", "session", "zombie"])
def test_procfs_snapshot_identity_or_topology_race_fails_without_retry(procfs_tree, monkeypatch, change):
    original = operation.process_snapshot
    calls = []

    def changed(proc):
        rows = original(proc)
        calls.append(rows)
        if len(calls) == 2:
            if change == "new_pid":
                rows[999] = dict(rows[101], pid=999)
            elif change == "lost_pid":
                del rows[101]
            elif change == "zombie":
                rows[101]["zombie"] = True
            else:
                rows[101][change] += 1
        return rows

    monkeypatch.setattr(operation, "process_snapshot", changed)
    with pytest.raises(ValueError, match="Unstable procfs process identity/topology"):
        operation.running_memory(100, procfs_tree)
    assert len(calls) == 2


def test_procfs_census_change_during_single_snapshot_fails(procfs_tree, monkeypatch):
    original = Path.iterdir
    calls = []

    def changed(path):
        entries = list(original(path))
        if path == procfs_tree:
            calls.append(path)
            if len(calls) == 2:
                return iter(entries + [procfs_tree / "999"])
        return iter(entries)

    monkeypatch.setattr(Path, "iterdir", changed)
    with pytest.raises(ValueError, match="Unstable procfs PID census"):
        operation.running_memory(100, procfs_tree)
    assert len(calls) == 2


@pytest.mark.parametrize("change", ["missing_rss", "negative_rss", "wrong_unit", "wrong_ppid", "wrong_pid"])
def test_procfs_live_status_requires_readable_consistent_rss(procfs_tree, change):
    path = procfs_tree / "101/status"
    text = path.read_text()
    if change == "missing_rss":
        text = text.replace("VmRSS:\t2048 kB\n", "")
    elif change == "negative_rss":
        text = text.replace("2048 kB", "-1 kB")
    elif change == "wrong_unit":
        text = text.replace("2048 kB", "2048 B")
    elif change == "wrong_ppid":
        text = text.replace("PPid:\t100", "PPid:\t1")
    else:
        text = text.replace("Pid:\t101", "Pid:\t999")
    path.write_text(text)
    with pytest.raises((KeyError, ValueError)):
        operation.running_memory(100, procfs_tree)


def test_procfs_root_must_have_dedicated_session(procfs_tree):
    with pytest.raises(ValueError, match="dedicated process session"):
        operation.running_memory(101, procfs_tree)


def test_procfs_history_retains_live_reparented_new_session_and_group_member(procfs_tree):
    history = {}
    first = operation.running_memory(100, procfs_tree, history)
    path = procfs_tree / "102/stat"
    text = path.read_text().replace("S 101 200 200", "S 1 102 102")
    path.write_text(text)
    path = procfs_tree / "102/status"
    path.write_text(path.read_text().replace("PPid:\t101", "PPid:\t1"))
    second = operation.running_memory(100, procfs_tree, history)
    assert second["process_tree_pids"] == first["process_tree_pids"]
    assert second["consumer_rss_bytes"] == first["consumer_rss_bytes"]
    assert history[102] == 10102
    assert len({row["tgid"] for row in second["process_tree_members"]}) == 5


def test_procfs_history_rejects_reused_pid_without_inheriting_identity(procfs_tree):
    history = {}
    operation.running_memory(100, procfs_tree, history)
    path = procfs_tree / "102/stat"
    path.write_text(path.read_text().replace("10102", "99999"))
    with pytest.raises(ValueError, match="descendant PID was reused"):
        operation.running_memory(100, procfs_tree, history)
    assert history[102] == 10102


def test_procfs_prior_member_can_be_absent_only_across_complete_stable_snapshots(procfs_tree):
    history = {}
    operation.running_memory(100, procfs_tree, history)
    path = procfs_tree / "102"
    for member in path.iterdir():
        member.unlink()
    path.rmdir()
    observed = operation.running_memory(100, procfs_tree, history)
    assert observed["previously_observed_stably_absent_pids"] == [102]
    assert 102 not in observed["process_tree_pids"]
    assert history[102] == 10102  # Keep identity tombstone; later reuse is rejected.


def test_procfs_failed_rss_sample_retains_observed_identities_for_cleanup(procfs_tree):
    history = {}
    (procfs_tree / "101/status").unlink()
    with pytest.raises(FileNotFoundError):
        operation.running_memory(100, procfs_tree, history)
    assert history == {100: 10100, 101: 10101, 102: 10102, 103: 10103, 104: 10104}


def test_procfs_threads_do_not_duplicate_tgid_rss(procfs_tree):
    for tid in (100, 999):
        task = procfs_tree / "100/task" / str(tid)
        task.mkdir(parents=True)
        (task / "status").write_text("VmRSS:\t999999 kB\nTgid:\t100\n")
    observed = operation.running_memory(100, procfs_tree)
    assert observed["consumer_rss_bytes"] == (1024 + 2048 + 4096 + 8192) * 1024
    assert [row["tgid"] for row in observed["process_tree_members"]] == [100, 101, 102, 103, 104]


@pytest.mark.parametrize("change", ["hidepid", "subset", "wrong_fs", "masked_pid", "wrong_namespace"])
def test_procfs_visibility_must_prove_unfiltered_current_namespace(procfs_tree, change):
    path = procfs_tree / "self/mountinfo"
    text = path.read_text()
    if change == "hidepid":
        text = text.replace("- proc proc rw", "- proc proc rw,hidepid=2")
    elif change == "subset":
        text = text.replace("- proc proc rw", "- proc proc rw,subset=pid")
    elif change == "wrong_fs":
        text = text.replace("- proc proc rw", "- tmpfs tmpfs rw")
    elif change == "masked_pid":
        text += f"54 53 0:31 / {procfs_tree}/102 rw - tmpfs tmpfs rw\n"
    else:
        namespace = procfs_tree / "1/ns/pid"
        namespace.unlink()
        namespace.symlink_to("pid:[different]")
    path.write_text(text)
    with pytest.raises(ValueError):
        operation.running_memory(100, procfs_tree)


@pytest.mark.parametrize("change", ["absent", "query", "gpu", "cost", "deadline", "commit", "contract", "container"])
def test_no_actual_matching_cpu_authorization_cannot_execute(change):
    auth = auth_fixture()
    if change == "absent":
        auth = None
    elif change == "query":
        auth["query_access"] = True
    elif change == "gpu":
        auth["gpu_fit_authorized"] = True
    elif change == "cost":
        auth["cost_authorization"] = None
    elif change == "deadline":
        auth["deadline_unix"] = 999
    elif change == "commit":
        auth["reviewed_commit"] = "d" * 40
    elif change == "contract":
        auth["operation_contract_sha256"] = "d" * 64
    else:
        auth["container_identity"]["pid1_start_ticks"] = "changed-container"
    with pytest.raises(ValueError):
        operation.authorization_check(auth, "b" * 64, "a" * 40, now=1000)


def test_valid_in_memory_fixture_binds_original_absolute_window():
    auth = auth_fixture()
    assert operation.authorization_check(auth, "b" * 64, "a" * 40, now=1000) == 9000
    assert auth["deadline_unix"] == 9000


@pytest.fixture
def launch(prepared, monkeypatch):
    root, contract, preflight = prepared
    monkeypatch.setattr(operation.time, "time", lambda: 1000)
    monkeypatch.setattr(operation.subprocess, "check_output", lambda argv, **kw:
                        "a" * 40 + "\n" if argv[1] == "rev-parse" else "")

    def run(popen, *, config=None, memory_reader=None, use_actual_monitor=False):
        return operation.execute(config or contract, auth_fixture(), contract_sha="b" * 64,
            commit="a" * 40, auth_sha="c" * 64, root=root,
            preflight_reader=lambda *args, **kwargs: preflight(), popen=popen,
            memory_reader=None if use_actual_monitor else memory_reader or (lambda pid: {"consumer_rss_bytes": 1024,
                "process_tree_pids": [pid], "cgroup_headroom_bytes": 4 * 1024**3,
                "host_available_bytes": 16 * 1024**3}))
    return root, contract, run


@pytest.mark.parametrize("returncode", [0, 7])
def test_actual_inert_child_returncode_persisted_without_scientific_acceptance(launch, returncode):
    root, _, run = launch

    def inert(argv, **kwargs):
        assert "analyze_kumar_csp_signed_score_v1.py" in argv[2]
        return subprocess.Popen([sys.executable, "-c", f"print('SYNTHETIC SOFTWARE CHILD');raise SystemExit({returncode})"], **kwargs)

    receipt = run(inert)
    stored = operation.read(root / operation.STATE / "launcher_receipt.json")
    assert stored == receipt and stored["returncode"] == returncode
    assert stored["scientific_completion_accepted"] is stored["accepted"] is False
    assert stored["consumer_started_at_utc"] and stored["consumer_finished_at_utc"]
    assert stored["output_members"] == []


def test_actual_inert_child_timeout_is_terminated_and_persisted(launch):
    root, contract, run = launch
    changed = copy.deepcopy(contract)
    changed["consumer_timeout_seconds"] = .02  # Injected test-only wait, not a real contract.

    def inert(argv, **kwargs):
        return subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], **kwargs)

    receipt = run(inert, config=changed)
    assert receipt["timeout"] is True and receipt["returncode"] == -15
    assert receipt["signals"][0]["signal"] == "SIGTERM"
    assert operation.read(root / operation.STATE / "launcher_receipt.json")["timeout"] is True


def test_interrupt_and_partial_output_preserved_without_success(launch, monkeypatch):
    root, _, run = launch

    class InterruptedChild:
        pid = -999999

        def wait(self, timeout):
            raise KeyboardInterrupt()

        def poll(self):
            return None

    def inert(argv, **kwargs):
        folder = root / operation.OUTPUT
        folder.mkdir(parents=True)
        (folder / "partial.bin").write_bytes(b"SYNTHETIC OPAQUE PARTIAL")
        return InterruptedChild()

    monkeypatch.setattr(operation, "stop_process", lambda proc, grace: (-15, [{"signal": "SIGTERM"}]))
    receipt = run(inert)
    assert receipt["interrupted"] is True and receipt["returncode"] == -15
    assert receipt["status"] == "consumer_interrupted_preserved"
    assert receipt["output_members"][0]["path"] == "partial.bin"
    assert (root / operation.OUTPUT / "partial.bin").exists()
    assert operation.read(root / operation.STATE / "launcher_receipt.json")["accepted"] is False


def test_failed_start_is_persisted_and_old_claim_prevents_retry(launch):
    root, _, run = launch

    def fail(*args, **kwargs):
        raise OSError("Synthetic executable launch failure")

    receipt = run(fail)
    assert receipt["status"] == "launcher_failed_preserved" and receipt["returncode"] is None
    claim = operation.sha(root / operation.STATE / "claim.json")
    with pytest.raises(ValueError, match="Prior output/state/claim"):
        run(lambda *a, **kw: pytest.fail("No automatic retry"))
    assert operation.sha(root / operation.STATE / "claim.json") == claim


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGHUP])
def test_launcher_term_hup_stop_child_group_and_restore_handlers(launch, monkeypatch, signum):
    root, _, run = launch
    old_handler = signal.getsignal(signum)

    class Child:
        pid = -999999

        def poll(self):
            return None

        def wait(self, timeout):
            os.kill(os.getpid(), signum)

    killed = []
    monkeypatch.setattr(operation, "stop_process", lambda proc, grace:
                        (killed.append(proc.pid) or -15, [{"signal": "SIGTERM"}]))
    receipt = run(lambda *args, **kwargs: Child())
    assert receipt["interrupted"] is True and receipt["returncode"] == -15
    assert receipt["status"] == "consumer_interrupted_preserved" and killed == [-999999]
    assert signal.getsignal(signum) == old_handler
    assert operation.read(root / operation.STATE / "launcher_receipt.json")["interrupted"] is True


@pytest.mark.parametrize("kind", ["rss", "headroom", "host", "unreadable", "missing_proc_stat", "unstable_procfs"])
def test_sampled_memory_limits_or_read_failure_stop_real_inert_child(launch, kind):
    root, _, run = launch
    launches = []

    def inert(argv, **kwargs):
        launches.append(argv)
        return subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], **kwargs)

    def observed(pid):
        if kind == "unreadable":
            raise OSError("Synthetic unreadable consumer memory")
        if kind == "missing_proc_stat":
            raise FileNotFoundError(f"Synthetic missing /proc/{pid}/stat")
        if kind == "unstable_procfs":
            raise ValueError("Unstable procfs process identity/topology")
        return {"consumer_rss_bytes": 2 * 1024**3 if kind == "rss" else 1024,
                "cgroup_headroom_bytes": 1024**3 if kind == "headroom" else 4 * 1024**3,
                "host_available_bytes": 1024**3 if kind == "host" else 16 * 1024**3,
                "process_tree_pids": [pid]}

    receipt = run(inert, memory_reader=observed)
    assert receipt["returncode"] == -15
    assert receipt["status"] != "consumer_exited_zero_pending_audit"
    assert receipt["accepted"] is False
    assert receipt["resource_limit_stop"] is (kind in {"rss", "headroom", "host"})
    assert len(launches) == 1
    assert (root / operation.STATE / "claim.json").is_file()
    assert operation.read(root / operation.STATE / "launcher_receipt.json") == receipt


@pytest.mark.parametrize("failure", ["claim", "log_hash", "receipt"])
def test_storage_failures_preserved_and_cannot_be_scientific_success(launch, monkeypatch, failure):
    root, _, run = launch
    original_write, original_sha = operation.write_new, operation.sha

    def write(path, value):
        if (failure == "claim" and Path(path).name == "claim.json") or (
                failure == "receipt" and Path(path).name == "launcher_receipt.json"):
            raise OSError("Synthetic storage failure")
        return original_write(path, value)

    def digest(path):
        if failure == "log_hash" and Path(path).name == "consumer.log":
            raise OSError("Synthetic log hash failure")
        return original_sha(path)

    def inert(argv, **kwargs):
        return subprocess.Popen([sys.executable, "-c", "raise SystemExit(0)"], **kwargs)

    monkeypatch.setattr(operation, "write_new", write)
    monkeypatch.setattr(operation, "sha", digest)
    receipt = run(inert)
    assert receipt["status"] != "consumer_exited_zero_pending_audit"
    filename = "emergency_receipt.json" if failure == "receipt" else "launcher_receipt.json"
    assert operation.read(root / operation.STATE / filename)["accepted"] is False


def test_unreadable_resource_proof_is_closed_not_ready(prepared):
    _, _, preflight = prepared

    def unreadable(output):
        raise OSError("Synthetic missing cgroup metadata")

    result = preflight(resource_reader=unreadable)
    assert result["status"] == "execution_closed_not_ready"
    assert result["resources"]["observation_failure"]["type"] == "OSError"


def test_term_grace_exhaustion_records_kill_and_actual_reaped_code(monkeypatch):
    sent = []

    class StubbornInertMock:
        pid = -999999
        calls = 0

        def wait(self, timeout):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("SYNTHETIC MOCK ONLY", timeout)
            return -9

    monkeypatch.setattr(operation.os, "killpg", lambda pid, signum: sent.append((pid, signum)))
    code, events = operation.stop_process(StubbornInertMock(), 0)
    assert code == -9
    assert [event["signal"] for event in events] == ["SIGTERM", "SIGKILL"]
    assert [item[1] for item in sent] == [signal.SIGTERM, signal.SIGKILL]


def test_launcher_uses_only_standard_library_imports():
    tree = ast.parse(Path(operation.__file__).read_text())
    modules = {node.module.split(".")[0] for node in ast.walk(tree)
               if isinstance(node, ast.ImportFrom)}
    modules |= {alias.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names}
    assert modules <= sys.stdlib_module_names | {"__future__"}


def test_delayed_popen_return_consumes_original_budget_without_start_write(launch):
    root, contract, run = launch
    changed = copy.deepcopy(contract)
    changed["consumer_timeout_seconds"] = .02  # Synthetic elapsed budget only.
    children = []

    def delayed(argv, **kwargs):
        child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], **kwargs)
        children.append(child)
        time.sleep(.04)
        return child

    receipt = run(delayed, config=changed)
    assert len(children) == 1 and children[0].poll() == -15
    assert receipt["timeout"] is True and receipt["returncode"] == -15
    assert receipt["resource_samples"] == []
    assert not (root / operation.STATE / "consumer_start.json").exists()
    assert operation.read(root / operation.STATE / "launcher_receipt.json")["accepted"] is False


def test_blocked_start_write_expires_preserves_partial_and_stops_only_child(launch, monkeypatch):
    root, contract, run = launch
    changed = copy.deepcopy(contract)
    changed["consumer_timeout_seconds"] = .04  # Synthetic elapsed budget only.
    original_write = operation.write_new
    previous_handler = signal.getsignal(signal.SIGALRM)
    children = []

    def blocked(path, value):
        if Path(path).name == "consumer_start.json":
            with Path(path).open("xb") as stream:
                stream.write(b"SYNTHETIC PARTIAL START RECEIPT")
                stream.flush()
                time.sleep(60)  # Interruptible stand-in for blocked fsync.
        else:
            original_write(path, value)

    def inert(argv, **kwargs):
        child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(operation, "write_new", blocked)
    receipt = run(inert, config=changed)
    assert len(children) == 1 and children[0].poll() == -15
    assert receipt["timeout"] is True and receipt["failure"]["type"] == "TimeoutError"
    assert (root / operation.STATE / "consumer_start.json").read_bytes() == b"SYNTHETIC PARTIAL START RECEIPT"
    assert operation.read(root / operation.STATE / "launcher_receipt.json")["timeout"] is True
    assert signal.getsignal(signal.SIGALRM) == previous_handler
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_existing_external_alarm_fails_before_claim_without_reset(launch):
    root, _, run = launch
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.setitimer(signal.ITIMER_REAL, 30)
    try:
        with pytest.raises(ValueError, match="Existing real-time alarm"):
            run(lambda *args, **kwargs: pytest.fail("Must not launch under another timer"))
        remaining, interval = signal.getitimer(signal.ITIMER_REAL)
        assert 29 < remaining <= 30 and interval == 0
        assert signal.getsignal(signal.SIGALRM) == previous_handler
        assert not (root / operation.STATE).exists()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def test_blocked_authorized_preflight_expires_without_claim_or_consumer(launch, monkeypatch):
    root, contract, _ = launch
    monkeypatch.setattr(operation, "authorization_check", lambda *args, **kwargs: 1030.02)
    previous_handler = signal.getsignal(signal.SIGALRM)

    def blocked(*args, **kwargs):
        time.sleep(60)
        pytest.fail("Preflight must be interrupted at the fixed authorization boundary")

    with pytest.raises(TimeoutError, match="Fixed CPU operation deadline"):
        operation.execute(contract, auth_fixture(), contract_sha="b" * 64,
            commit="a" * 40, auth_sha="c" * 64, root=root,
            preflight_reader=blocked,
            popen=lambda *args, **kwargs: pytest.fail("Preflight cannot launch a consumer"))
    assert not (root / operation.STATE).exists()
    assert signal.getsignal(signal.SIGALRM) == previous_handler
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_absolute_deadline_rechecked_after_resource_read_and_cleanup_not_extended(launch, monkeypatch):
    _, _, run = launch
    clock, grace = [1000], []
    monkeypatch.setattr(operation.time, "time", lambda: clock[0])

    class InertMock:
        pid = -999999

        def poll(self):
            return None

        def wait(self, timeout):
            pytest.fail("No wait/fit may continue after the absolute deadline")

    def memory(pid):
        clock[0] = 9001
        return {"consumer_rss_bytes": 1024, "process_tree_pids": [pid],
                "cgroup_headroom_bytes": 4 * 1024**3,
                "host_available_bytes": 16 * 1024**3}

    monkeypatch.setattr(operation, "stop_process", lambda child, seconds:
                        (grace.append(seconds) or -9, [{"signal": "SIGKILL"}]))
    receipt = run(lambda *args, **kwargs: InertMock(), memory_reader=memory)
    assert receipt["timeout"] is True and receipt["returncode"] == -9
    assert grace == [0]


def test_resource_stop_does_not_restart_term_grace_at_consumer_deadline(launch, monkeypatch):
    _, contract, run = launch
    changed = copy.deepcopy(contract)
    changed["consumer_timeout_seconds"] = .02  # Synthetic elapsed budget only.
    sent, waits = [], []

    class StubbornInertMock:
        pid = -999999

        def poll(self):
            return None

        def wait(self, timeout):
            waits.append(timeout)
            if len(waits) == 1:
                time.sleep(.04)  # Cross consumer deadline during TERM cleanup.
                raise subprocess.TimeoutExpired("SYNTHETIC MOCK ONLY", timeout)
            return -9

    monkeypatch.setattr(operation.os, "killpg", lambda pid, signum: sent.append(signum))
    receipt = run(lambda *args, **kwargs: StubbornInertMock(), config=changed,
        memory_reader=lambda pid: {"consumer_rss_bytes": 2 * 1024**3,
            "process_tree_pids": [pid], "cgroup_headroom_bytes": 4 * 1024**3,
            "host_available_bytes": 16 * 1024**3})
    assert receipt["resource_limit_stop"] is True and receipt["returncode"] == -9
    assert receipt["timeout"] is False
    assert sent == [signal.SIGTERM, signal.SIGKILL] and waits == [30, 5]
    assert [event["signal"] for event in receipt["signals"]] == ["SIGTERM", "SIGKILL"]


@pytest.mark.parametrize("failure", [None, "reused_pid", "unreadable_proof"])
def test_pidfd_cleanup_stops_escaped_identity_and_root_without_killing_reused_pid(monkeypatch, failure):
    history = {500: 1000, 501: 1001, 502: 1002}
    rows = {pid: {"pid": pid, "start_ticks": start} for pid, start in history.items()}
    ready, sent, groups, closed = set(), [], [], []

    class Child:
        pid = 500
        alive = True

        def poll(self):
            return None if self.alive else -15

        def wait(self, timeout):
            assert not self.alive
            return -15

    child = Child()

    def snapshot(proc):
        if failure == "unreadable_proof":
            raise PermissionError("Synthetic unreadable cleanup proof")
        return rows

    def record(pid, proc):
        return dict(rows[pid], start_ticks=9999) if failure == "reused_pid" and pid == 501 else rows[pid]

    def killgroup(pid, signum):
        groups.append((pid, signum))
        child.alive = False
        ready.add(1500)

    def signal_fd(handle, signum):
        sent.append((handle, signum))
        ready.add(handle)

    monkeypatch.setattr(operation, "proc_visibility", lambda proc: {})
    monkeypatch.setattr(operation, "process_snapshot", snapshot)
    monkeypatch.setattr(operation, "process_record", record)
    monkeypatch.setattr(operation.os, "pidfd_open", lambda pid: pid + 1000)
    monkeypatch.setattr(operation.os, "close", closed.append)
    monkeypatch.setattr(operation.os, "killpg", killgroup)
    monkeypatch.setattr(operation.signal, "pidfd_send_signal", signal_fd)
    monkeypatch.setattr(operation.select, "select", lambda handles, _, __, timeout:
                        ([handle for handle in handles if handle in ready], [], []))
    if failure:
        with pytest.raises(ValueError, match="Process cleanup proof failed") as raised:
            operation.stop_process(child, 0, history)
        assert not any(handle == 1501 for handle, _ in sent)
        assert raised.value.signal_events[0]["target_process_group"] == 500
        if failure == "reused_pid":
            assert (1502, signal.SIGTERM) in sent  # A bad earlier identity cannot skip this one.
            assert any(event.get("target_pid") == 502 for event in raised.value.signal_events)
    else:
        code, events = operation.stop_process(child, 0, history)
        assert code == -15
        assert (1501, signal.SIGTERM) in sent
        assert any(event.get("target_pid") == 501 for event in events)
    assert groups == [(500, signal.SIGTERM)]
    assert child.poll() == -15
    if failure != "unreadable_proof":
        assert sorted(closed) == [1500, 1501, 1502]


def test_cleanup_failure_preserved_without_second_stop_or_grace(launch, monkeypatch):
    _, _, run = launch
    calls = []

    class Child:
        pid = -999999

        def poll(self):
            return None

    def failed_stop(process, grace):
        calls.append(grace)
        error = OSError("Synthetic cleanup proof failure")
        error.signal_events = [{"signal": "SIGTERM", "target_pid": process.pid}]
        raise error

    monkeypatch.setattr(operation, "stop_process", failed_stop)
    receipt = run(lambda *args, **kwargs: Child(), memory_reader=lambda pid: {
        "consumer_rss_bytes": 2 * 1024**3, "process_tree_pids": [pid],
        "cgroup_headroom_bytes": 4 * 1024**3, "host_available_bytes": 16 * 1024**3})
    assert calls == [30]
    assert receipt["stop_failure"]["type"] == "OSError"
    assert receipt["signals"] == [{"signal": "SIGTERM", "target_pid": -999999}]
    assert receipt["status"] == "launcher_failed_preserved"


@pytest.mark.parametrize("live_descendant", [False, True])
def test_natural_root_zero_requires_tracked_descendant_exit_proof(launch, monkeypatch, live_descendant):
    _, _, run = launch
    stops = []

    class Child:
        pid = 500
        done = False

        def poll(self):
            return 0 if self.done else None

        def wait(self, timeout):
            self.done = True
            return 0

    def monitor(pid, observed_descendants):
        observed_descendants.update({500: 1000, 501: 1001})
        return {"consumer_rss_bytes": 1024, "process_tree_pids": [500, 501],
                "cgroup_headroom_bytes": 4 * 1024**3, "host_available_bytes": 16 * 1024**3}

    def cleanup(process, grace, history):
        stops.append((process.poll(), grace, dict(history)))
        return 0, ([{"signal": "SIGTERM", "target_pid": 501, "start_ticks": 1001}]
                   if live_descendant else [])

    monkeypatch.setattr(operation, "running_memory", monitor)
    monkeypatch.setattr(operation, "stop_process", cleanup)
    receipt = run(lambda *args, **kwargs: Child(), use_actual_monitor=True)
    assert stops == [(0, 30, {500: 1000, 501: 1001})]
    assert receipt["returncode"] == 0
    assert receipt["descendant_cleanup_required_after_root_exit"] is live_descendant
    assert receipt["status"] == ("consumer_failed_preserved" if live_descendant
                                  else "consumer_exited_zero_pending_audit")
