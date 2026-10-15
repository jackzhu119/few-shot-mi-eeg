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

    def run(popen, *, config=None, memory_reader=None):
        return operation.execute(config or contract, auth_fixture(), contract_sha="b" * 64,
            commit="a" * 40, auth_sha="c" * 64, root=root,
            preflight_reader=lambda *args, **kwargs: preflight(), popen=popen,
            memory_reader=memory_reader or (lambda pid: {"consumer_rss_bytes": 1024,
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


@pytest.mark.parametrize("kind", ["rss", "headroom", "host", "unreadable"])
def test_sampled_memory_limits_or_read_failure_stop_real_inert_child(launch, kind):
    _, _, run = launch

    def inert(argv, **kwargs):
        return subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"], **kwargs)

    def observed(pid):
        if kind == "unreadable":
            raise OSError("Synthetic unreadable consumer memory")
        return {"consumer_rss_bytes": 2 * 1024**3 if kind == "rss" else 1024,
                "cgroup_headroom_bytes": 1024**3 if kind == "headroom" else 4 * 1024**3,
                "host_available_bytes": 1024**3 if kind == "host" else 16 * 1024**3,
                "process_tree_pids": [pid]}

    receipt = run(inert, memory_reader=observed)
    assert receipt["returncode"] == -15
    assert receipt["status"] != "consumer_exited_zero_pending_audit"
    assert receipt["accepted"] is False
    assert receipt["resource_limit_stop"] is (kind != "unreadable")


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
