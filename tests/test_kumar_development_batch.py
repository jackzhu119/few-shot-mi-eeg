"""CPU-only contract and state-machine tests; no EEG, GPU, Pod or network calls."""

import contextlib
import copy
import fcntl
import hashlib
import io
import json
import signal
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

import run_kumar_development_batch as batch


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    source = tmp_path / "repo"
    (source / "configs").mkdir(parents=True)
    state_root = tmp_path / "outside-git" / "state"
    jobs = [{"job_id": f"{index:064x}", "subject": "sub-7", "seed": 20261013 + index,
             "output": str(tmp_path / "results" / str(index)),
             "training_config_sha256": "config", "split_sha256": "split",
             "result_key": f"private/{index}.tar"} for index in range(11)]
    for name in ("input.json", "source.json", "receipt.json"):
        (source / name).write_text("{}\n")
    contract = {"remaining_jobs": jobs, "limits": dict(batch.LIMITS),
                "state_root": str(state_root), "data_root": str(tmp_path),
                "download_receipt": str(source / "receipt.json"),
                "input_manifest": "input.json", "recovery_source_manifest": "source.json",
                "authorized_initial_container_hostname": batch.platform.node()}
    contract_path = source / "configs/kumar_development_batch_20261015.json"
    contract_path.write_bytes(batch.encoded(contract))
    monkeypatch.setattr(batch, "ROOT", source)
    monkeypatch.setattr(batch, "DEFAULT_CONTRACT", contract_path)
    monkeypatch.setattr(batch.single, "LOCK", tmp_path / "research-gpu.lock")
    monkeypatch.setattr(batch, "gate", lambda *_a, **_k: ({}, {"accepted_jobs": 7}))
    monkeypatch.setattr(batch, "disk_guard", lambda *_a: None)
    return contract, contract_path, state_root


def create_state(prepared):
    contract, path, root = prepared
    return batch.new_state(contract, batch.sha(path), "fixed", root)


def result_archive(job):
    checkpoint = b"unit-test-not-real-weights"
    record = {"job_id": job["job_id"], "status": "fit_saved", "query_rows_loaded": 0,
              "training_config_sha256": job["training_config_sha256"],
              "split_sha256": job["split_sha256"], "replay_absolute_tolerance": 1e-7,
              "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
              "epochs_executed": 25, "optimizer_steps": 75}
    payload = {name: b"test payload" for name in batch.single.FILES}
    payload["weights.pt"] = checkpoint
    payload["fit_result.json"] = batch.encoded(record)
    manifest = {"job_id": job["job_id"], "query_rows_loaded": 0,
                "files": [{"path": name, "bytes": len(raw),
                           "sha256": hashlib.sha256(raw).hexdigest()}
                          for name, raw in payload.items()]}
    payload["manifest.json"] = batch.encoded(manifest)
    path = Path(job["output"]).with_suffix(".tar")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w") as archive:
        for name, raw in payload.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return path


def test_real_contract_scope_and_changed_order_rejected():
    root = Path(__file__).resolve().parents[1]
    contract = batch.read(root / "configs/kumar_development_batch_20261015.json")
    plan = batch.validate_contract(contract)
    assert contract["remaining_jobs"] == plan["jobs"][7:]
    assert len(contract["remaining_jobs"]) == 11
    assert (contract["remaining_jobs"][0]["subject"],
            contract["remaining_jobs"][0]["seed"]) == ("sub-7", 20261013)
    changed = copy.deepcopy(contract)
    changed["remaining_jobs"][:2] = reversed(changed["remaining_jobs"][:2])
    with pytest.raises(ValueError, match="exact final eleven"):
        batch.validate_contract(changed)
    changed = copy.deepcopy(contract)
    changed["limits"]["automatic_retries"] = 1
    with pytest.raises(ValueError, match="limits changed"):
        batch.validate_contract(changed)


def test_pending_seventh_ack_blocks_execution(monkeypatch, tmp_path):
    jobs = [{"job_id": str(i)} for i in range(18)]
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"accepted_jobs": jobs[:6]}))
    monkeypatch.setattr(batch, "validate_contract", lambda _c: None)
    monkeypatch.setattr(batch, "source_checks", lambda _c: None)
    monkeypatch.setattr(batch.single, "check_gate",
                        lambda: ({"accepted_jobs": str(ledger)}, {"jobs": jobs}, jobs[6]))
    monkeypatch.setattr(batch.single, "checked_path", Path)
    contract = {"completed_prefix_job_ids": [j["job_id"] for j in jobs[:7]]}
    _, summary = batch.gate(contract, executing=False)
    assert summary["initial_gate_ready"] is False
    with pytest.raises(ValueError, match="actual parent acknowledgement"):
        batch.gate(contract, executing=True)


def test_default_plan_never_creates_claim_or_calls_gpu(prepared, monkeypatch, capsys):
    contract, path, root = prepared
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--contract", str(path)])
    monkeypatch.setattr(batch, "runtime_checks", lambda: pytest.fail("GPU runtime called"))
    assert batch.main() == 0
    assert not root.exists()
    assert json.loads(capsys.readouterr().out)["fit_executed"] is False


def test_new_run_cannot_rebuild_or_replace_existing_claims(prepared, monkeypatch):
    contract, path, root = prepared
    monkeypatch.setattr(batch.platform, "node", lambda: "unexpected-rebuilt-container")
    with pytest.raises(ValueError, match="not authorized"):
        batch.new_state(contract, batch.sha(path), "fixed", root)
    assert not root.exists()
    monkeypatch.setattr(batch.platform, "node",
                        lambda: contract["authorized_initial_container_hostname"])
    state = create_state(prepared)
    batch.reserve_chunk(root, state, contract["remaining_jobs"][:2])
    old_claims = {p.name: p.read_bytes() for p in (root / "claims").iterdir()}
    with pytest.raises(ValueError, match="state exists"):
        batch.new_state(contract, batch.sha(path), "fixed", root)
    assert old_claims == {p.name: p.read_bytes() for p in (root / "claims").iterdir()}


def test_existing_output_or_partial_claim_never_retrained(prepared):
    contract, path, root = prepared
    output = Path(contract["remaining_jobs"][0]["output"])
    output.mkdir(parents=True)
    with pytest.raises(ValueError, match="Existing fit/output"):
        batch.new_state(contract, batch.sha(path), "fixed", root)
    output.rmdir()
    state = create_state(prepared)
    batch.reserve_chunk(root, state, contract["remaining_jobs"][:2])
    state["jobs"][contract["remaining_jobs"][0]["job_id"]]["stage"] = "starting"
    batch.save(root, state, "unit_test_crash")
    with pytest.raises(ValueError, match="ambiguous"):
        batch.resume_state(batch.sha(path), "fixed", root)


def test_resume_deadline_and_container_identity_are_fixed(prepared, monkeypatch):
    contract, path, root = prepared
    state = create_state(prepared)
    old = state["deadline_unix"]
    resumed = batch.resume_state(batch.sha(path), "fixed", root)
    assert resumed["deadline_unix"] == old
    with pytest.raises(ValueError, match="deadline reached"):
        batch.budget(resumed, contract, now=old)
    monkeypatch.setattr(batch, "container_identity", lambda: {"new": "container"})
    with pytest.raises(ValueError, match="Container changed"):
        batch.resume_state(batch.sha(path), "fixed", root)


@pytest.mark.parametrize("field", ["run_id", "contract_sha256", "archive_sha256", "job_ids", "files"])
def test_export_receipt_binds_identity_and_members(prepared, field):
    contract, _path, root = prepared
    state = create_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    batch.build_export(root, state, jobs, "intent", {"accepted_jobs": 7})
    pending = state["pending_export"]
    valid = batch.inspect_export(pending["archive"])
    batch.verify_receipt(pending, state, valid)
    changed = copy.deepcopy(valid)
    changed[field] = [] if isinstance(changed[field], list) else "wrong"
    with pytest.raises(ValueError, match="receipt mismatch"):
        batch.verify_receipt(pending, state, changed)


def test_wait_timeout_preserves_deadline_and_claims_receipt_allows_resume(prepared):
    contract, path, root = prepared
    state = create_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    batch.build_export(root, state, jobs, "intent", {})
    now = state["started_unix"] + 1
    assert batch.await_export(root, state, contract, 0, clock=lambda: now) is False
    deadline = state["pending_export"]["wait_deadline_unix"]
    claim_bytes = {p.name: p.read_bytes() for p in (root / "claims").iterdir()}
    resumed = batch.resume_state(batch.sha(path), "fixed", root)
    assert batch.await_export(root, resumed, contract, 600, clock=lambda: now + 1) is False
    assert resumed["pending_export"]["wait_deadline_unix"] == deadline
    receipt = batch.inspect_export(resumed["pending_export"]["archive"])
    batch.write_new(resumed["pending_export"]["receipt"], receipt)
    assert batch.await_export(root, resumed, contract, 600, clock=lambda: now + 2)
    assert claim_bytes == {p.name: p.read_bytes() for p in (root / "claims").iterdir()}
    assert all(not r["trained"] and not r["off_Pod_exported"] for r in resumed["jobs"].values())


def test_eleven_sequential_workers_chunk_lock_export_bounds_and_no_acceptance(prepared, monkeypatch):
    contract, path, root = prepared
    state = create_state(prepared)
    calls = []
    boundaries = []

    def automatically_attest_for_test(root, state, contract, wait_seconds):
        pending = state["pending_export"]
        boundaries.append((pending["kind"], list(pending["job_ids"])))
        receipt = batch.inspect_export(pending["archive"])
        batch.write_new(pending["receipt"], receipt)
        return original_await(root, state, contract, wait_seconds)

    def fake_worker(root, state, contract_path, job, lock_fd, timeout_seconds):
        assert 0 < timeout_seconds <= 1800
        assert state["jobs"][job["job_id"]]["intent_off_Pod_exported"]
        with batch.single.LOCK.open("a") as other:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        batch.checked_lock(lock_fd)
        assert sum(r["trained"] and not r["off_Pod_exported"] for r in state["jobs"].values()) < 2
        calls.append(job["job_id"])
        result_archive(job)
        for suffix in ("stdout.log", "stderr.log", "timing.json", "entered.json"):
            (root / "workers" / f"{job['job_id']}.{suffix}").write_text("{}\n")

    original_await = batch.await_export
    original_build = batch.build_export

    def inspect_packaging_lock(root, state, jobs, kind, summary):
        if kind == "results":
            assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
            with batch.single.LOCK.open("a") as other:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return original_build(root, state, jobs, kind, summary)

    monkeypatch.setattr(batch, "await_export", automatically_attest_for_test)
    monkeypatch.setattr(batch, "build_export", inspect_packaging_lock)
    assert batch.run_batch(contract, path, state, root, 600, worker_call=fake_worker) == 75
    assert calls == [job["job_id"] for job in contract["remaining_jobs"]]
    assert len(boundaries) == 12
    assert all(len(job_ids) <= 2 for _kind, job_ids in boundaries)
    assert all(r["trained"] and r["off_Pod_exported"] for r in state["jobs"].values())
    assert all(r[key] is False for r in state["jobs"].values() for key in batch.FALSE_STAGES)
    assert not list(root.rglob("parent_acknowledged.json"))
    assert not list(root.rglob("accepted_jobs.json"))
    # An exported completed run is idempotent and cannot launch another worker.
    assert batch.run_batch(contract, path, state, root, 600,
                           worker_call=lambda *_: pytest.fail("trained fit retried")) == 75


def test_worker_timeout_kills_process_group_no_retry(prepared, monkeypatch):
    contract, path, root = prepared
    state = create_state(prepared)
    calls, killed = [], []

    class Process:
        pid = 54321

        def wait(self, timeout=None):
            calls.append(timeout)
            if len(calls) < 3:
                raise subprocess.TimeoutExpired("mock", timeout)
            return -9

    monkeypatch.setattr(batch.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(batch.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    job = contract["remaining_jobs"][0]
    with pytest.raises(ValueError, match="no retry"):
        batch.launch_worker(root, state, path, job, 8, 0.01)
    assert killed == [(54321, signal.SIGTERM), (54321, signal.SIGKILL)]
    assert calls == [0.01, 30, None]
    timing = batch.read(root / "workers" / f"{job['job_id']}.timing.json")
    assert timing["timed_out"] and timing["automatic_retries"] == 0


def test_worker_interruption_also_terminates_group(prepared, monkeypatch):
    contract, path, root = prepared
    state = create_state(prepared)
    killed, waits = [], []

    class Process:
        pid = 54322

        def wait(self, timeout=None):
            waits.append(timeout)
            if len(waits) == 1:
                raise InterruptedError("mock SIGTERM")
            return -15

    monkeypatch.setattr(batch.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(batch.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    with pytest.raises(ValueError, match="no retry"):
        batch.launch_worker(root, state, path, contract["remaining_jobs"][0], 8, 100)
    assert killed == [(54322, signal.SIGTERM)]


def test_chunk_deadline_wraps_workers_and_packaging(prepared, monkeypatch):
    contract, path, root = prepared
    state = create_state(prepared)
    active = []

    @contextlib.contextmanager
    def mocked_timer(seconds):
        assert 0 < seconds <= 3600
        active.append(True)
        try:
            yield
        finally:
            active.pop()

    def fake_worker(root, state, contract_path, job, lock_fd, timeout_seconds):
        assert active
        raise TimeoutError("unit test active chunk timeout")

    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    for record in state["jobs"].values():
        record["intent_off_Pod_exported"] = True
    monkeypatch.setattr(batch, "chunk_timeout", mocked_timer)
    with pytest.raises(TimeoutError, match="active chunk"):
        batch.run_batch(contract, path, state, root, 600, worker_call=fake_worker)
    assert not active
    assert state["jobs"][jobs[0]["job_id"]]["stage"] == "starting"
    assert state["jobs"][jobs[1]["job_id"]]["stage"] == "reserved"


def test_result_hash_and_checkpoint_are_checked(prepared):
    contract, _path, _root = prepared
    job = contract["remaining_jobs"][0]
    archive = result_archive(job)
    assert batch.validate_result(archive, job)["epochs_executed"] == 25
    changed = {**job, "job_id": "another"}
    with pytest.raises(ValueError, match="identity"):
        batch.validate_result(archive, changed)


def test_budget_rejects_third_unexported_fit_and_excess_epochs(prepared):
    contract, _path, _root = prepared
    state = create_state(prepared)
    state["jobs"] = {str(i): {"trained": True, "off_Pod_exported": False,
                              "epochs": 100, "steps": 300} for i in range(3)}
    with pytest.raises(ValueError, match="More than two"):
        batch.budget(state, contract)
    for record in state["jobs"].values():
        record["off_Pod_exported"] = True
        record["epochs"] = 400
    with pytest.raises(ValueError, match="scientific budget"):
        batch.budget(state, contract)


def test_offline_verifier_needs_explicit_attestation_before_gpu_gate(prepared, monkeypatch):
    contract, _path, root = prepared
    state = create_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    batch.build_export(root, state, jobs, "intent", {})
    exported = state["pending_export"]["archive"]
    receipt = root / "outside.receipt.json"
    monkeypatch.setattr(batch, "gate", lambda *_a, **_k: pytest.fail("GPU gate called off-Pod"))
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--verify-export", exported,
                        "--receipt-output", str(receipt)])
    with pytest.raises(ValueError, match="explicitly attest"):
        batch.main()
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--verify-export", exported,
                        "--receipt-output", str(receipt), "--attest-off-pod-possession"])
    assert batch.main() == 0
    assert batch.read(receipt)["physical_location_is_dot_attestation_not_machine_proof"] is True


def test_uncompressed_export_rejects_oversized_declared_members(tmp_path):
    path = tmp_path / "declared-too-large.tar"
    # Header-only malformed archive: reject declared size before reading/allocating payload.
    info = tarfile.TarInfo("large.bin")
    info.size = batch.LIMITS["export_archive_max_bytes"] + 1
    path.write_bytes(info.tobuf() + b"\0" * 1024)
    with pytest.raises((ValueError, tarfile.ReadError)):
        batch.inspect_export(path)


def test_compressed_export_is_not_supported(tmp_path):
    path = tmp_path / "compressed.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        raw = b"{}"
        info = tarfile.TarInfo("manifest.json")
        info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))
    with pytest.raises(tarfile.ReadError):
        batch.inspect_export(path)


def test_real_timeout_wrapper_preserves_GPU_lock_fd_and_bounds_CPU_child(tmp_path):
    """Exercise the actual OS watchdog/FD handoff without any GPU or model code."""
    watchdog = shutil.which("timeout")
    if watchdog is None:
        pytest.skip("GNU timeout unavailable on this CPU test host")
    lock_path = tmp_path / "real-watchdog.lock"
    child = (
        "import json,sys;from pathlib import Path;"
        "import run_kumar_development_batch as b;"
        "b.single.LOCK=Path(sys.argv[2]);"
        "b.checked_lock(int(sys.argv[1]));"
        "print(json.dumps({'inherited_lock_verified':True}))"
    )
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed = subprocess.run(
            [watchdog, "--signal=TERM", "--kill-after=30s", "2s",
             batch.sys.executable, "-B", "-c", child, str(lock.fileno()), str(lock_path)],
            cwd=Path(__file__).resolve().parents[1], pass_fds=(lock.fileno(),),
            start_new_session=True, capture_output=True, text=True, timeout=5,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["inherited_lock_verified"] is True
    expired = subprocess.run(
        [watchdog, "--signal=TERM", "--kill-after=30s", "0.1s", batch.sys.executable,
         "-B", "-c", "import time;time.sleep(10)"],
        start_new_session=True, capture_output=True, timeout=5,
    )
    assert expired.returncode == 124
