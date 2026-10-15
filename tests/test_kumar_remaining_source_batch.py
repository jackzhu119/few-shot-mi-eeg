"""CPU metadata and synthetic state-machine tests; no real fits/weights/query/Pod/network."""

import copy
import fcntl
import hashlib
import io
import json
import signal
import subprocess
import tarfile
from pathlib import Path

import pytest

import run_kumar_remaining_source_batch as batch


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    root = tmp_path / "outside-git" / "state"
    jobs = [{"job_id": f"{i:064x}", "subject": f"sub-{i // 3 + 2}",
             "seed": 20261012 + i % 3, "output": str(tmp_path / "results" / str(i)),
             "training_config_sha256": "config", "split_sha256": "split",
             "result_key": f"private/{i}.tar"} for i in range(36)]
    for name in ("input.json", "receipt.json", "ledger.json"):
        (repo / name).write_text("{}\n")
    contract = {"remaining_jobs": jobs, "limits": {**batch.FIXED_LIMITS,
                 "proposed_wall_seconds": 86400}, "state_root": str(root),
                "data_root": str(tmp_path), "download_receipt": str(repo / "receipt.json"),
                "input_manifest": "input.json", "accepted_ledger": "ledger.json"}
    path = repo / "contract.json"
    path.write_bytes(batch.encoded(contract))
    start = batch.time.time() - 1
    authorization = {"schema_version": 1,
        "status": "parent_reviewed_remaining36_source_execution_authorized",
        "contract_sha256": batch.sha(path), "reviewed_commit": "fixed",
        "approved_job_ids": [j["job_id"] for j in jobs], "query_access": False,
        "accepted18_refitting_authorized": False, "not_before_unix": start,
        "deadline_unix": start + 86400, "approved_wall_seconds": 86400,
        "authorized_container_hostname": batch.proven.platform.node(),
        # Synthetic unit-test values, never an actual budget or authorization.
        "cost": {"currency": "USD", "maximum_usd": 24, "hourly_rate_usd": 1,
                 "latest_authorization_receipt": "synthetic unit test only"}}
    monkeypatch.setattr(batch, "ROOT", repo)
    monkeypatch.setattr(batch.legacy, "LOCK", tmp_path / "research-gpu.lock")
    monkeypatch.setattr(batch, "execution_gate", lambda *_a: {"accepted_preserved": 18})
    monkeypatch.setattr(batch, "disk_guard", lambda *_a: None)
    return contract, path, root, authorization


def make_state(prepared):
    contract, path, root, authorization = prepared
    state = batch.new_state(contract, batch.sha(path), "fixed", root, authorization)
    batch.write_new(root / "authorization.json", authorization)
    return state


def result_archive(job):
    checkpoint = b"synthetic test placeholder; never loaded as tensors"
    record = {"job_id": job["job_id"], "status": "fit_saved", "query_rows_loaded": 0,
              "subject": job["subject"], "seed": job["seed"],
              "source_train_rows": 40, "source_validation_rows": 20,
              "training_config_sha256": job["training_config_sha256"],
              "split_sha256": job["split_sha256"], "replay_absolute_tolerance": 1e-7,
              "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
              "epochs_executed": 25, "optimizer_steps": 75}
    payload = {name: b"synthetic software test" for name in batch.legacy.FILES}
    payload.update({"weights.pt": checkpoint, "fit_result.json": batch.encoded(record)})
    manifest = {"job_id": job["job_id"], "query_rows_loaded": 0, "files": [
        {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
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


def test_actual_contract_excludes_all_accepted18_and_query():
    contract = batch.read(batch.DEFAULT_CONTRACT)
    summary = batch.validate_contract(contract)
    assert summary["new_fits_authorized"] == 0
    assert summary["query_adapter_required"] is False
    assert contract["cost_authorization"] is None
    assert contract["limits"]["proposed_wall_seconds"] == 86400
    jobs = contract["remaining_jobs"]
    assert len(jobs) == 36
    assert [(j["subject"], j["seed"]) for j in jobs] == [
        (s, seed) for s in ("sub-2", "sub-3", "sub-5", "sub-6", "sub-8", "sub-9",
                           "sub-11", "sub-12", "sub-14", "sub-15", "sub-17", "sub-18")
        for seed in (20261012, 20261013, 20261014)]
    changed = copy.deepcopy(contract)
    changed["remaining_jobs"][:2] = reversed(changed["remaining_jobs"][:2])
    with pytest.raises(ValueError, match="job/order"):
        batch.validate_contract(changed)
    changed = copy.deepcopy(contract)
    changed["limits"]["automatic_retries"] = 1
    with pytest.raises(ValueError, match="limits"):
        batch.validate_contract(changed)
    changed = copy.deepcopy(contract)
    changed["execution_enabled"] = True
    with pytest.raises(ValueError, match="silently"):
        batch.validate_contract(changed)


def test_default_metadata_never_reads_signals_or_runtime(prepared, monkeypatch, capsys):
    _contract, path, root, _authorization = prepared
    monkeypatch.setattr(batch, "validate_contract", lambda _c: {"fit_executed": False})
    monkeypatch.setattr(batch.proven, "runtime_checks", lambda: pytest.fail("GPU/runtime called"))
    monkeypatch.setattr(batch, "verify_source_inputs", lambda _c: pytest.fail("Signals read"))
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--contract", str(path)])
    assert batch.main() == 0
    assert json.loads(capsys.readouterr().out)["fit_executed"] is False
    assert not root.exists()
    assert not batch.legacy.LOCK.exists()


def test_execute_without_actual_cost_deadline_record_stops_before_runtime(prepared, monkeypatch):
    _contract, path, root, _authorization = prepared
    monkeypatch.setattr(batch, "validate_contract", lambda _c: {})
    monkeypatch.setattr(batch.proven, "runtime_checks", lambda: pytest.fail("GPU/runtime called"))
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--contract", str(path), "--execute", "--new-run"])
    with pytest.raises(ValueError, match="authorization bytes"):
        batch.main()
    assert not root.exists()
    assert not batch.legacy.LOCK.exists()


@pytest.mark.parametrize("field,value,match", [
    ("cost", None, "cost/rate"),
    ("cost", {"currency": "USD", "maximum_usd": None}, "cost/rate"),
    ("query_access", True, "source-only"),
    ("accepted18_refitting_authorized", True, "source-only"),
    ("contract_sha256", "old unrelated queue", "source-only"),
    ("reviewed_commit", "old unrelated commit", "source-only"),
    ("approved_job_ids", [], "source-only"),
    ("authorized_container_hostname", "rebuilt-container", "container"),
    ("approved_wall_seconds", 19800, "deadline"),
])
def test_explicit_authorization_scope_is_not_inferred(prepared, field, value, match):
    contract, path, _root, authorization = prepared
    changed = copy.deepcopy(authorization)
    changed[field] = value
    with pytest.raises(ValueError, match=match):
        batch.authorization_check(contract, batch.sha(path), "fixed", changed)


def test_finite_cost_cap_and_expired_deadline_fail_closed(prepared):
    contract, path, _root, authorization = prepared
    for cap in (0, 1, float("inf"), float("nan")):
        changed = copy.deepcopy(authorization)
        changed["cost"]["maximum_usd"] = cap
        with pytest.raises(ValueError):
            batch.authorization_check(contract, batch.sha(path), "fixed", changed)
    with pytest.raises(ValueError, match="deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", authorization,
                                  now=authorization["deadline_unix"])
    with pytest.raises(ValueError, match="current cost/deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", None)


def test_claims_existing_outputs_and_partial_results_never_retry(prepared):
    contract, path, root, authorization = prepared
    output = Path(contract["remaining_jobs"][0]["output"])
    output.mkdir(parents=True)
    with pytest.raises(ValueError, match="Existing output"):
        batch.new_state(contract, batch.sha(path), "fixed", root, authorization)
    output.rmdir()
    state = make_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    claims = {p.name: p.read_bytes() for p in (root / "claims").iterdir()}
    with pytest.raises(ValueError, match="state exists"):
        batch.new_state(contract, batch.sha(path), "fixed", root, authorization)
    state["jobs"][jobs[0]["job_id"]]["stage"] = "starting"
    batch.save(root, state, "synthetic interrupted worker")
    with pytest.raises(ValueError, match="ambiguous"):
        batch.resume_state(contract, batch.sha(path), "fixed", root, authorization)
    assert claims == {p.name: p.read_bytes() for p in (root / "claims").iterdir()}


def test_resume_never_resets_deadline_or_changes_authorization_or_container(prepared, monkeypatch):
    contract, path, root, authorization = prepared
    state = make_state(prepared)
    resumed = batch.resume_state(contract, batch.sha(path), "fixed", root, authorization)
    assert resumed["deadline_unix"] == state["deadline_unix"] == authorization["deadline_unix"]
    changed = copy.deepcopy(authorization)
    changed["deadline_unix"] += 1
    with pytest.raises(ValueError, match="Resume authorization"):
        batch.resume_state(contract, batch.sha(path), "fixed", root, changed)
    monkeypatch.setattr(batch.proven, "container_identity", lambda: {"unexpected": "new container"})
    with pytest.raises(ValueError, match="Container changed"):
        batch.resume_state(contract, batch.sha(path), "fixed", root, authorization)


def test_real_receipt_bytes_and_member_hashes_bound_and_wait_resumes_same_run(prepared):
    contract, path, root, authorization = prepared
    state = make_state(prepared)
    batch.reserve_chunk(root, state, contract["remaining_jobs"][:2])
    batch.build_export(contract, path, root, state, contract["remaining_jobs"][:2], "intent", {})
    now = state["started_unix"] + 2
    assert batch.await_export(root, state, contract, 0, clock=lambda: now) is False
    old_deadline = state["pending_export"]["wait_deadline_unix"]
    old_run = state["run_id"]
    resumed = batch.resume_state(contract, batch.sha(path), "fixed", root, authorization)
    assert batch.await_export(root, resumed, contract, 600, clock=lambda: now + 1) is False
    assert resumed["pending_export"]["wait_deadline_unix"] == old_deadline
    pending = resumed["pending_export"]
    receipt = batch.inspect_export(pending["archive"])
    bad = copy.deepcopy(receipt)
    bad["archive_sha256"] = "wrong"
    with pytest.raises(ValueError, match="receipt mismatch"):
        batch.verify_receipt(pending, resumed, bad)
    batch.write_new(pending["receipt"], receipt)
    assert batch.await_export(root, resumed, contract, 600, clock=lambda: now + 2)
    assert resumed["run_id"] == old_run
    assert all(not r["trained"] for r in resumed["jobs"].values())


def test_all36_sequential_under_chunk_lock_36_boundaries_no_acceptance(prepared, monkeypatch):
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    calls, boundaries = [], []
    original_await, original_build = batch.await_export, batch.build_export

    def synthetic_receipt(root, state, contract, wait_seconds):
        pending = state["pending_export"]
        boundaries.append((pending["kind"], pending["job_ids"]))
        batch.write_new(pending["receipt"], batch.inspect_export(pending["archive"]))
        return original_await(root, state, contract, wait_seconds)

    def fake_worker(root, state, contract_path, job, lock_fd, timeout_seconds):
        assert 0 < timeout_seconds <= 1800
        assert state["jobs"][job["job_id"]]["intent_off_Pod_exported"]
        batch.checked_lock(lock_fd)
        with batch.legacy.LOCK.open("a") as independent:
            with pytest.raises(BlockingIOError):
                fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
        calls.append(job["job_id"])
        result_archive(job)
        for suffix in ("stdout.log", "stderr.log", "timing.json", "entered.json"):
            (root / "workers" / f"{job['job_id']}.{suffix}").write_text("{}\n")

    def check_packaging_lock(contract, path, root, state, jobs, kind, summary):
        if kind == "results":
            assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
            with batch.legacy.LOCK.open("a") as independent:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return original_build(contract, path, root, state, jobs, kind, summary)

    monkeypatch.setattr(batch, "await_export", synthetic_receipt)
    monkeypatch.setattr(batch, "build_export", check_packaging_lock)
    assert batch.run_batch(contract, path, state, root, 600, worker_call=fake_worker) == 75
    assert calls == [j["job_id"] for j in contract["remaining_jobs"]]
    assert len(boundaries) == 36
    assert all(len(ids) == 2 for _kind, ids in boundaries)
    assert all(r["trained"] and r["off_Pod_exported"] for r in state["jobs"].values())
    assert all(r[k] is False for r in state["jobs"].values() for k in batch.FALSE_STAGES)
    assert not list(root.rglob("accepted_jobs.json"))
    assert batch.run_batch(contract, path, state, root, 600,
                           worker_call=lambda *_: pytest.fail("completed job retrained")) == 75


def test_missing_receipt_no_worker_and_failure_preserves_starting_claim(prepared, monkeypatch):
    contract, path, root, authorization = prepared
    state = make_state(prepared)
    assert batch.run_batch(contract, path, state, root, 0,
                           worker_call=lambda *_: pytest.fail("no durable intent")) == 76
    pending = state["pending_export"]
    batch.write_new(pending["receipt"], batch.inspect_export(pending["archive"]))
    calls = []

    def failed_worker(*args):
        calls.append(1)
        raise TimeoutError("synthetic worker timeout")

    with pytest.raises(TimeoutError):
        batch.run_batch(contract, path, state, root, 0, worker_call=failed_worker)
    assert len(calls) == 1
    assert len(list((root / "claims").iterdir())) == 2
    with pytest.raises(ValueError, match="ambiguous"):
        batch.resume_state(contract, batch.sha(path), "fixed", root, authorization)


def test_disk_stop_before_claims_or_fit(prepared, monkeypatch):
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    def no_disk(*_a):
        raise ValueError("Insufficient disk reserve")
    monkeypatch.setattr(batch, "disk_guard", no_disk)
    with pytest.raises(ValueError, match="disk"):
        batch.run_batch(contract, path, state, root, 0,
                        worker_call=lambda *_: pytest.fail("fit launched"))
    assert not list((root / "claims").iterdir())


def test_shared_global_lock_blocks_other_paper_worker(prepared):
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    batch.reserve_chunk(root, state, contract["remaining_jobs"][:2])
    for record in state["jobs"].values():
        record["intent_off_Pod_exported"] = True
    with batch.legacy.LOCK.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            batch.run_batch(contract, path, state, root, 0,
                            worker_call=lambda *_: pytest.fail("GPU concurrently launched"))
    assert all(r["stage"] == "reserved" for r in state["jobs"].values())


def test_worker_watchdog_TERM_then_KILL_no_retry(prepared, monkeypatch):
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    killed, calls = [], []
    class Process:
        pid = 54321
        def wait(self, timeout=None):
            calls.append(timeout)
            if len(calls) < 3:
                raise subprocess.TimeoutExpired("synthetic", timeout)
            return -9
    monkeypatch.setattr(batch.subprocess, "Popen", lambda *_a, **_k: Process())
    monkeypatch.setattr(batch.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    with pytest.raises(ValueError, match="no retry"):
        batch.launch_worker(root, state, path, contract["remaining_jobs"][0], 8, 0.01)
    assert killed == [(54321, signal.SIGTERM), (54321, signal.SIGKILL)]
    assert calls == [0.01, 30, None]
    assert batch.read(root / "workers" /
                      f"{contract['remaining_jobs'][0]['job_id']}.timing.json")["automatic_retries"] == 0


def test_source_input_recheck_uses_new253_verifier_every_call(prepared, monkeypatch):
    import fetch_kumar_remaining_source_https as source
    contract, _path, _root, _authorization = prepared
    config = Path(source.CONFIG)
    monkeypatch.setattr(batch, "pinned", lambda _c, key: config if key == "https_manifest" else Path("p"))
    calls = []
    monkeypatch.setattr(source, "verify_all", lambda root, receipt: calls.append((root, receipt)))
    assert batch.verify_source_inputs(contract)["source_input_files_verified"] == 253
    assert batch.verify_source_inputs(contract)["query_rows_loaded"] == 0
    assert calls == [(Path(contract["data_root"]), Path(contract["download_receipt"]))] * 2


def test_worker_reads_exact_starting_claim_without_supervisor_resume(prepared, monkeypatch, capsys):
    contract, path, root, authorization = prepared
    state = make_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    record = state["jobs"][jobs[0]["job_id"]]
    record.update(stage="starting", intent_off_Pod_exported=True)
    batch.save(root, state, "synthetic launch")
    monkeypatch.setattr(batch.proven, "runtime_checks", lambda: {"synthetic": True})
    monkeypatch.setattr(batch, "checked_lock", lambda _fd: None)
    monkeypatch.setattr(batch, "resume_state", lambda *_a: pytest.fail("supervisor resume called"))
    called = []
    monkeypatch.setattr(batch, "source_fit", lambda job, *_a: called.append(job["job_id"]) or {})
    assert batch.worker(path, batch.sha(path), "fixed", root, jobs[0]["job_id"], 8,
                        authorization) == 75
    assert called == [jobs[0]["job_id"]]
    assert json.loads(capsys.readouterr().out) == {}
    assert batch.read(root / "state.json")["jobs"][jobs[0]["job_id"]]["trained"] is False


def test_unplanned_job_and_third_unexported_fit_fail_before_training(prepared, monkeypatch):
    contract, path, _root, _authorization = prepared
    monkeypatch.setattr(batch, "verify_source_inputs", lambda _c: pytest.fail("input touched"))
    with pytest.raises(ValueError, match="exact remaining36"):
        batch.source_fit({"job_id": "accepted previous fit"}, contract, path)
    state = make_state(prepared)
    batch.reserve_chunk(Path(contract["state_root"]), state, contract["remaining_jobs"][:2])
    state["jobs"][contract["remaining_jobs"][2]["job_id"]] = {
        "trained": True, "off_Pod_exported": False,
        **{k: False for k in batch.FALSE_STAGES}}
    for record in state["jobs"].values():
        record.update(trained=True, off_Pod_exported=False)
    with pytest.raises(ValueError, match="More than two"):
        batch.budget(state, contract)


def test_final_accepted_flags_and_epoch_budgets_cannot_be_fabricated(prepared):
    contract, _path, root, _authorization = prepared
    state = make_state(prepared)
    job = contract["remaining_jobs"][0]
    batch.reserve_chunk(root, state, [job])
    state["jobs"][job["job_id"]]["accepted"] = True
    with pytest.raises(ValueError, match="write acceptance"):
        batch.budget(state, contract)
    state["jobs"][job["job_id"]]["accepted"] = False
    state["jobs"][job["job_id"]]["epochs"] = 3601
    with pytest.raises(ValueError, match="count budget"):
        batch.budget(state, contract)


def test_corrupted_result_checkpoint_or_wrong_subject_preserved(prepared):
    contract, _path, _root, _authorization = prepared
    job = contract["remaining_jobs"][0]
    archive = result_archive(job)
    assert batch.validate_result(archive, job)["source_train_rows"] == 40
    changed = {**job, "subject": "sub-1"}
    with pytest.raises(ValueError, match="participant"):
        batch.validate_result(archive, changed)
    raw = archive.read_bytes()
    archive.write_bytes(raw.replace(b"synthetic test placeholder; never loaded as tensors",
                                   b"changed!! test placeholder; never loaded as tensors"))
    with pytest.raises(ValueError, match="SHA"):
        batch.validate_result(archive, job)


def test_active_chunk_timeout_wraps_workers_and_preserves_claim(prepared, monkeypatch):
    import contextlib
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    for record in state["jobs"].values():
        record["intent_off_Pod_exported"] = True
    active = []
    @contextlib.contextmanager
    def bounded(seconds):
        assert 0 < seconds <= 3600
        active.append(True)
        try:
            yield
        finally:
            active.pop()
    def fake_worker(*_a):
        assert active
        raise TimeoutError("synthetic active chunk deadline")
    monkeypatch.setattr(batch, "chunk_timeout", bounded)
    with pytest.raises(TimeoutError, match="active chunk"):
        batch.run_batch(contract, path, state, root, 600, worker_call=fake_worker)
    assert not active
    assert state["jobs"][jobs[0]["job_id"]]["stage"] == "starting"
    assert state["jobs"][jobs[1]["job_id"]]["stage"] == "reserved"


def test_offline_export_verifier_needs_full_possession_attestation(prepared, monkeypatch):
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    jobs = contract["remaining_jobs"][:2]
    batch.reserve_chunk(root, state, jobs)
    batch.build_export(contract, path, root, state, jobs, "intent", {})
    destination = root / "off-Pod.synthetic.receipt.json"
    args = ["runner", "--verify-export", state["pending_export"]["archive"],
            "--receipt-output", str(destination)]
    monkeypatch.setattr(batch.sys, "argv", args)
    monkeypatch.setattr(batch, "validate_contract", lambda *_a: pytest.fail("GPU-side gate"))
    with pytest.raises(ValueError, match="actual full off-Pod"):
        batch.main()
    monkeypatch.setattr(batch.sys, "argv", args + ["--attest-off-pod-possession"])
    assert batch.main() == 0
    assert batch.read(destination)["status"] == "dot_off_Pod_full_member_SHA256_verified"
    with pytest.raises(FileExistsError):
        batch.main()
