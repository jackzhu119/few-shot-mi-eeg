"""Synthetic operation tests only: no real checkpoint, EEG or query is read."""
from __future__ import annotations

from contextlib import nullcontext
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("frozen_query_operation", ROOT / "scripts/run_kumar_frozen_query_evaluation.py")
operation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operation)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def authorization(jobs, monitor, *, now=100):
    return dict(status="parent_reviewed_frozen_checkpoint_query_evaluation_authorized",
        scope="accepted54_always_frozen_query_only", reviewed_commit="a" * 40,
        contract_sha256="b" * 64, accepted_ledger_sha256=operation.LEDGER_SHA,
        source_plan_sha256=operation.PLAN_SHA, split_manifest_sha256=operation.SPLIT_SHA,
        query_input_manifest_sha256=operation.INPUTS_SHA,
        approved_job_ids=[j["job_id"] for j in jobs], query_evaluation_authorized=True,
        authorized_container_identity=monitor.container_identity(),
        not_before_unix=now - 1, deadline_unix=now + 100,
        **{key: False for key in operation.FALSE_PERMISSIONS})


@pytest.fixture
def identity():
    return SimpleNamespace(container_identity=lambda: {"hostname": "synthetic-cpu", "boot_id": "synthetic",
                                                       "pid1_start_ticks": "1"})


@pytest.mark.parametrize("change", ["scope", "job_order", "job_subset", "contract", "host",
    "query_closed", "training", "optimizer", "support", "strategy", "resource", "future",
    "expired", "oversized", "nan"])
def test_authorization_denies_changed_scope_or_deadline(identity, change):
    jobs = [{"job_id": "one"}, {"job_id": "two"}]
    auth = authorization(jobs, identity)
    key = {"training": "training_authorized", "optimizer": "optimizer_updates_authorized",
           "support": "target_support_access_authorized", "strategy": "new_strategy_authorized",
           "resource": "new_resources_authorized"}.get(change)
    if key:
        auth[key] = True
    elif change == "scope":
        auth["scope"] = "different"
    elif change == "job_order":
        auth["approved_job_ids"].reverse()
    elif change == "job_subset":
        auth["approved_job_ids"].pop()
    elif change == "contract":
        auth["contract_sha256"] = "c" * 64
    elif change == "host":
        auth["authorized_container_identity"]["boot_id"] = "rebuilt"
    elif change == "query_closed":
        auth["query_evaluation_authorized"] = False
    elif change == "future":
        auth["not_before_unix"] = 101
    elif change == "expired":
        auth["deadline_unix"] = 120  # Thirty-second cleanup reserve cannot be consumed.
    elif change == "oversized":
        auth["deadline_unix"] = 9999
    else:
        auth["not_before_unix"] = float("nan")
    with pytest.raises(ValueError):
        operation.authorization_check(auth, "b" * 64, "a" * 40, jobs, identity, now=100)


def test_exact_authorization_does_not_extend_original_window(identity):
    jobs = [{"job_id": "one"}]
    auth = authorization(jobs, identity)
    assert operation.authorization_check(auth, "b" * 64, "a" * 40, jobs, identity, now=100) == 200
    with pytest.raises(ValueError):
        operation.authorization_check(auth, "b" * 64, "a" * 40, jobs, identity, now=171)


@pytest.fixture
def synthetic_jobs(tmp_path):
    archive_root, output = tmp_path / "archives", tmp_path / "output"
    archive_root.mkdir()
    output.mkdir()
    jobs, entries = [], []
    for subject in ("sub-1", "sub-4"):
        for seed in (20261012, 20261013, 20261014):
            name = f"{subject}-seed-{seed}.tar"
            raw = f"SYNTHETIC SOFTWARE FIXTURE ONLY {name}".encode()
            (archive_root / name).write_bytes(raw)
            job = dict(job_id=name, subject=subject, seed=seed, result_key="synthetic/" + name)
            jobs.append(job)
            entries.append(dict(job, archive_sha256=digest(raw), archive_bytes=len(raw)))
    events = []

    def subject_loader(root, subject, protocol, split, *, allowed_roles):
        events.append(("subject", subject))
        assert allowed_roles == {"source_query", "target_query"}
        return SimpleNamespace(X=[[1]], y=[0], metadata=[{"role": "source_query"}])

    def checkpoint_loader(path, *, job_id, **kwargs):
        events.append(("checkpoint", job_id))
        return SimpleNamespace(evaluate_queries=lambda X, y, metadata: {"synthetic": True, "job_id": job_id})

    kwargs = dict(data_root=tmp_path / "never-opened", archive_root=archive_root, output=output,
                  inputs={"protocol_path": "synthetic.json"}, subject_loader=subject_loader,
                  checkpoint_loader=checkpoint_loader, checkpoint_kwargs={}, guard=lambda: events.append(("guard",)))
    return jobs, entries, kwargs, events


def test_subject_sequential_all_seeds_and_exclusive_atomic_outputs(synthetic_jobs):
    jobs, entries, kwargs, events = synthetic_jobs
    result = operation.evaluate_subjects(jobs, entries, **kwargs)
    assert [r["job_id"] for r in result] == [j["job_id"] for j in jobs]
    assert [e for e in events if e[0] != "guard"] == [
        ("subject", "sub-1"), *[("checkpoint", j["job_id"]) for j in jobs[:3]],
        ("subject", "sub-4"), *[("checkpoint", j["job_id"]) for j in jobs[3:]]]
    assert len(list(kwargs["output"].glob("*.json"))) == 8
    assert not list(kwargs["output"].glob("*.partial"))


@pytest.mark.parametrize("failure", ["archive_hash", "evaluation", "publication", "deadline"])
def test_any_job_failure_stops_before_next_job_and_preserves_partial(synthetic_jobs, monkeypatch, failure):
    jobs, entries, kwargs, events = synthetic_jobs
    original_loader, original_publish = kwargs["checkpoint_loader"], operation.publish
    calls = []

    def loader(path, *, job_id, **kw):
        calls.append(job_id)
        if job_id == jobs[1]["job_id"] and failure == "evaluation":
            raise RuntimeError("Synthetic read-only evaluation failure")
        return original_loader(path, job_id=job_id, **kw)

    def publish(path, value):
        if str(path).endswith("seed-20261013.json") and failure == "publication":
            raise OSError("Synthetic full output disk")
        return original_publish(path, value)

    def guard():
        if failure == "deadline" and len(calls) == 1:
            raise TimeoutError("Original absolute deadline exhausted")

    kwargs.update(checkpoint_loader=loader, guard=guard)
    monkeypatch.setattr(operation, "publish", publish)
    if failure == "archive_hash":
        (kwargs["archive_root"] / Path(jobs[1]["result_key"]).name).write_bytes(b"corrupted synthetic archive")
    with pytest.raises((ValueError, RuntimeError, OSError, TimeoutError)):
        operation.evaluate_subjects(jobs, entries, **kwargs)
    assert len(calls) <= 2 and jobs[2]["job_id"] not in calls
    if failure != "deadline":
        assert (kwargs["output"] / "sub-1-seed-20261012.json").is_file()
    assert not (kwargs["output"] / "sub-1-complete.json").exists()


def test_atomic_publication_retains_incomplete_bytes_on_storage_failure(tmp_path, monkeypatch):
    destination = tmp_path / "evidence.json"
    monkeypatch.setattr(operation.os, "link", lambda *args: (_ for _ in ()).throw(OSError("Synthetic ENOSPC")))
    with pytest.raises(OSError):
        operation.publish(destination, {"synthetic": True})
    assert not destination.exists()
    assert json.loads(destination.with_name("evidence.json.partial").read_text()) == {"synthetic": True}


def test_query_full_hash_stops_on_first_bad_file(tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"wrong")
    second.write_bytes(b"SYNTHETIC")
    manifest = {"files": [{"relative_path": "first", "bytes": 5, "sha256": "0" * 64},
                           {"relative_path": "second", "bytes": 9, "sha256": digest(b"SYNTHETIC")}]}
    original, opened = operation.sha, []

    def checked(path):
        opened.append(Path(path).name)
        return original(path)

    monkeypatch.setattr(operation, "sha", checked)
    with pytest.raises(ValueError, match="input bytes changed"):
        operation.verify_query_bytes(manifest, tmp_path)
    assert opened == ["first"]


@pytest.mark.parametrize("relative", ["../escape", "/absolute", "a/../escape"])
def test_input_root_escape_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        operation.checked_path(tmp_path, relative)


def test_default_metadata_reads_no_archive_or_signal(monkeypatch):
    original = operation.sha
    paths = []

    def metadata_only(path):
        paths.append(str(path))
        assert Path(path).suffix not in {".tar", ".edf", ".npz", ".pt"}
        return original(path)

    for key, value in operation.THREAD_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("MKL_NUM_THREADS", raising=False)
    monkeypatch.setattr(operation, "sha", metadata_only)
    result = operation.metadata_check(operation.read(operation.CONTRACT))
    assert result["accepted_models"] == 54
    assert result["query_files_opened"] is result["checkpoint_archives_opened"] is False
    assert result["models_constructed"] is False
    assert result["problems"] == []
    assert paths


@pytest.fixture
def mocked_execution(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    contract_path = root / "contract.json"
    contract_path.write_text("{}\n")
    jobs = [{"job_id": str(i)} for i in range(54)]
    monitor = SimpleNamespace(container_identity=lambda: {"hostname": "synthetic", "boot_id": "x", "pid1_start_ticks": "1"},
        process_record=lambda *args: {"start_ticks": 9}, utc=lambda: "SYNTHETIC_UTC",
        resources=lambda output: {"memory": {"effective_available_bytes": 4 * 1024**3},
                                  "free_output_disk_bytes": 4 * 1024**3},
        deadline_guard=lambda deadline: nullcontext(), member_inventory=lambda output: [])
    calls = []
    def memory(pid, observed_descendants):
        observed_descendants[pid] = 9
        return {"consumer_rss_bytes": 1024, "host_available_bytes": 4 * 1024**3,
                "cgroup_headroom_bytes": 4 * 1024**3}
    monitor.running_memory = memory
    monitor.stop_process = lambda child, grace, history: (child.poll(), [])
    archive_root, data_root, output = (root / name for name in ("archives", "data", "output"))
    archive_root.mkdir()
    data_root.mkdir()
    args = SimpleNamespace(authorization=root / "auth.json", expected_commit="a" * 40,
        reviewed_contract_sha256=operation.sha(contract_path), authorization_sha256=None,
        data_root=data_root, archive_root=archive_root, output=output)
    auth = authorization(jobs, monitor, now=operation.time.time())
    auth["contract_sha256"] = args.reviewed_contract_sha256
    args.authorization.write_text(json.dumps(auth))
    args.authorization_sha256 = operation.sha(args.authorization)
    monkeypatch.setattr(operation, "ROOT", root)
    monkeypatch.setattr(operation, "CONTRACT", contract_path)
    monkeypatch.setattr(operation, "STATE", "state")
    monkeypatch.setattr(operation, "LOCK", str(root / "shared.lock"))
    monkeypatch.setattr(operation.subprocess, "check_output", lambda command, **kwargs:
                        "a" * 40 + "\n" if command[1] == "rev-parse" else "")
    monkeypatch.setattr(operation.shutil, "disk_usage", lambda path: SimpleNamespace(free=4 * 1024**3))

    class Child:
        pid = -999999
        done = False

        def poll(self):
            return 0 if self.done else None

        def wait(self, timeout):
            self.done = True
            (output / "worker_complete.json").write_text(json.dumps({"job_count": 54, "jobs": jobs}))
            return 0

    def spawn(*args, **kwargs):
        calls.append((args, kwargs))
        return Child()

    monkeypatch.setattr(operation.subprocess, "Popen", spawn)
    return root, args, {"problems": [], "jobs": jobs}, monitor, calls


def test_execute_claim_precedes_single_child_and_duplicate_cannot_restart(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    result = operation.execute(args, {}, checked, monitor)
    assert len(calls) == 1 and result["query_evaluation_completed"] is True
    assert result["accepted"] is result["independently_audited"] is result["R2_full_GET_verified"] is False
    claim = (root / "state/claim.json").read_bytes()
    with pytest.raises(ValueError):
        operation.execute(args, {}, checked, monitor)
    assert len(calls) == 1 and (root / "state/claim.json").read_bytes() == claim


def test_resource_failure_prevents_child_or_claim(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    monitor.resources = lambda output: {"memory": {"effective_available_bytes": 0}, "free_output_disk_bytes": 0}
    with pytest.raises(ValueError, match="preflight failed"):
        operation.execute(args, {}, checked, monitor)
    assert not calls and not (root / "state").exists()


def test_shared_cpu_lock_conflict_never_launches_or_claims(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    with (root / "shared.lock").open("a+b") as held:
        operation.fcntl.flock(held.fileno(), operation.fcntl.LOCK_EX | operation.fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            operation.execute(args, {}, checked, monitor)
    assert not calls and not (root / "state").exists()


def test_shared_cpu_lock_symlink_rejected(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    target = root / "unrelated"
    target.write_bytes(b"preserve")
    (root / "shared.lock").symlink_to(target)
    with pytest.raises(OSError):
        operation.execute(args, {}, checked, monitor)
    assert not calls and target.read_bytes() == b"preserve"


def test_monitor_failure_preserves_actual_failed_claim_without_retry(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    monitor.running_memory = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Synthetic unreadable procfs"))
    stops = []
    monitor.stop_process = lambda child, grace, history: (stops.append(grace) or -15, [{"signal": "SIGTERM"}])
    result = operation.execute(args, {}, checked, monitor)
    assert len(calls) == len(stops) == 1 and result["status"] == "failed_partial_preserved"
    assert result["failure"]["type"] == "PermissionError"
    assert (root / "state/claim.json").is_file() and (root / "state/launcher_receipt.json").is_file()


@pytest.mark.parametrize("initial_failure", ["signal", "monitor"])
def test_repeated_termination_cannot_interrupt_single_cleanup(mocked_execution, initial_failure):
    root, args, checked, monitor, calls = mocked_execution
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGHUP)}
    stops = []

    def first_signal(*args, **kwargs):
        if initial_failure == "monitor":
            raise OSError("Synthetic procfs failure before any signal")
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

    def cleanup(child, grace, history):
        stops.append(grace)
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
        os.kill(os.getpid(), signal.SIGTERM)  # Inert test interpreter; verified ignored above.
        os.kill(os.getpid(), signal.SIGHUP)
        return -15, [{"signal": "SIGTERM", "synthetic": True}]

    monitor.running_memory, monitor.stop_process = first_signal, cleanup
    result = operation.execute(args, {}, checked, monitor)
    assert len(calls) == len(stops) == 1
    assert result["failure"]["type"] == ("InterruptedError" if initial_failure == "signal" else "OSError")
    assert result["returncode"] == -15 and result["status"] == "failed_partial_preserved"
    assert all(signal.getsignal(number) == handler for number, handler in previous.items())


def test_completion_inventory_failure_never_marks_operation_success(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    monitor.member_inventory = lambda output: (_ for _ in ()).throw(OSError("Synthetic failed output hash"))
    result = operation.execute(args, {}, checked, monitor)
    assert len(calls) == 1
    assert result["status"] == "failed_partial_preserved"
    assert result["inventory_failure"]["type"] == "OSError"
    assert result["accepted"] is False


def test_worker_exit_without_live_monitor_sample_cannot_be_success(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    monitor.running_memory = lambda *args, **kwargs: {"consumer_rss_bytes": 1024,
        "host_available_bytes": 4 * 1024**3, "cgroup_headroom_bytes": 4 * 1024**3}
    monitor.stop_process = lambda *args: (_ for _ in ()).throw(AssertionError("Do not signal a reaped untracked PID"))
    result = operation.execute(args, {}, checked, monitor)
    assert len(calls) == 1 and result["status"] == "failed_partial_preserved"
    assert result["failure"]["message"] == "No complete live process-tree sample captured"
    assert result["signals"] == []


def test_expired_authorization_cannot_open_lock_claim_or_child(mocked_execution):
    root, args, checked, monitor, calls = mocked_execution
    auth = operation.read(args.authorization)
    auth["deadline_unix"] = operation.time.time() - 1
    args.authorization.write_text(json.dumps(auth))
    args.authorization_sha256 = operation.sha(args.authorization)
    with pytest.raises(ValueError, match="Absolute query window"):
        operation.execute(args, {}, checked, monitor)
    assert not calls and not (root / "state").exists() and not (root / "shared.lock").exists()


def test_worker_direct_invocation_requires_live_parent_claim(tmp_path, monkeypatch, identity):
    monkeypatch.setattr(operation, "ROOT", tmp_path)
    args = SimpleNamespace(output=tmp_path / "output", worker_fd=None)
    with pytest.raises(FileNotFoundError):
        operation.worker(args, {}, {"problems": ["Historical attempt/state exists; no retry or overwrite"]}, identity)


def test_thread_environment_is_verified_never_mutated(monkeypatch):
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    before = copy.deepcopy(dict(os.environ))
    result = operation.metadata_check(operation.read(operation.CONTRACT))
    assert any("thread environment" in problem for problem in result["problems"])
    assert dict(os.environ) == before


def test_default_metadata_rejects_changed_parent_acceptance_chain(monkeypatch):
    inventory = operation.read(operation.ROOT / operation.CHECKPOINTS)
    target = next(row["path"] for row in inventory["dependencies"] if "parent_acknowledged" in row["path"])
    original = operation.sha

    def altered_ack(path):
        return "0" * 64 if Path(path) == operation.ROOT / target else original(path)

    monkeypatch.setattr(operation, "sha", altered_ack)
    with pytest.raises(ValueError, match="acceptance metadata dependency changed"):
        operation.metadata_check(operation.read(operation.CONTRACT))
