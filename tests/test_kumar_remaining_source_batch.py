"""CPU metadata and synthetic state-machine tests; no real fits/weights/query/Pod/network."""

import copy
import fcntl
import hashlib
import io
import json
import signal
import subprocess
import tarfile
import time
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
                 "proposed_wall_seconds": 10800},
                "financial_execution_preconditions": "superseded-by-user", "state_root": str(root),
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
        "deadline_unix": start + 10800, "approved_wall_seconds": 10800,
        "authorized_container_hostname": batch.proven.platform.node(),
        "authorized_container_identity": batch.proven.container_identity(),
        "financial_execution_preconditions": "superseded-by-user"}
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
    assert contract["limits"]["proposed_wall_seconds"] == 10800
    assert contract["financial_execution_preconditions"] == "superseded-by-user"
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
    changed = copy.deepcopy(contract)
    del changed["financial_execution_preconditions"]
    with pytest.raises(ValueError, match="user supersession"):
        batch.validate_contract(changed)
    # Historical billing values are preserved evidence, never execution gates.
    changed = copy.deepcopy(contract)
    for field in ("proposed_maximum_usd", "balance_recheck_max_age_before_start_seconds",
                  "parent_reported_official_billing_observation", "cost_authorization"):
        changed.pop(field, None)
    assert batch.validate_contract(changed)["new_fits_authorized"] == 0


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


def test_execute_without_actual_container_deadline_record_stops_before_runtime(prepared, monkeypatch):
    _contract, path, root, _authorization = prepared
    monkeypatch.setattr(batch, "validate_contract", lambda _c: {})
    monkeypatch.setattr(batch.proven, "runtime_checks", lambda: pytest.fail("GPU/runtime called"))
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--contract", str(path), "--execute", "--new-run"])
    with pytest.raises(ValueError, match="authorization bytes"):
        batch.main()
    assert not root.exists()
    assert not batch.legacy.LOCK.exists()


@pytest.mark.parametrize("field,value,match", [
    ("financial_execution_preconditions", None, "user supersession"),
    ("financial_execution_preconditions", "historical_cost_gate_passed", "user supersession"),
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


@pytest.mark.parametrize("field,value", [
    ("not_before_unix", float("inf")), ("deadline_unix", float("nan")),
    ("approved_wall_seconds", 0), ("approved_wall_seconds", True),
])
def test_nonfinite_or_invalid_absolute_window_fail_closed(prepared, field, value):
    contract, path, _root, authorization = prepared
    changed = copy.deepcopy(authorization)
    changed[field] = value
    with pytest.raises(ValueError, match="deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", changed)


def test_expired_deadline_or_missing_binding_fail_closed(prepared):
    contract, path, _root, authorization = prepared
    with pytest.raises(ValueError, match="deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", authorization,
                                  now=authorization["deadline_unix"])
    with pytest.raises(ValueError, match="current container/deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", None)


def test_no_cost_or_balance_fields_required_to_create_bound_state(prepared):
    contract, path, root, authorization = prepared
    assert "cost" not in authorization and "balance_recheck" not in authorization
    state = batch.new_state(contract, batch.sha(path), "fixed", root, authorization)
    assert state["authorization"] == authorization
    assert state["jobs"] == {}
    assert not list((root / "claims").iterdir())
    assert all(not Path(job["output"]).exists() for job in contract["remaining_jobs"])


@pytest.mark.parametrize("historical", [None, {}, {"historical_unknown": True}])
def test_historical_financial_fields_do_not_block_or_authorize(prepared, historical):
    contract, path, _root, authorization = prepared
    changed = copy.deepcopy(authorization)
    changed.update(cost=historical, balance_recheck=historical)
    assert batch.authorization_check(contract, batch.sha(path), "fixed", changed) == changed
    changed["deadline_unix"] = changed["not_before_unix"]
    with pytest.raises(ValueError, match="deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", changed)


def test_three_hour_proposal_cannot_be_enlarged(prepared):
    contract, path, _root, authorization = prepared
    changed = copy.deepcopy(authorization)
    changed["approved_wall_seconds"] = 10801
    changed["deadline_unix"] = changed["not_before_unix"] + 10801
    with pytest.raises(ValueError, match="deadline"):
        batch.authorization_check(contract, batch.sha(path), "fixed", changed)


def test_delayed_first_start_uses_remaining_original_window_without_balance(prepared):
    contract, path, root, authorization = prepared
    authorization = copy.deepcopy(authorization)
    authorization["not_before_unix"] = time.time() - 7200
    authorization["deadline_unix"] = authorization["not_before_unix"] + 10800
    batch.authorization_check(contract, batch.sha(path), "fixed", authorization)
    state = batch.new_state(contract, batch.sha(path), "fixed", root, authorization)
    assert state["started_unix"] == authorization["not_before_unix"]
    assert state["deadline_unix"] == authorization["deadline_unix"]
    assert 0 < state["deadline_unix"] - time.time() < 3600
    assert state["jobs"] == {}
    assert all(not Path(job["output"]).exists() for job in contract["remaining_jobs"])


def test_hostname_only_authorization_cannot_start_new_run(prepared):
    contract, path, root, authorization = prepared
    incomplete = copy.deepcopy(authorization)
    del incomplete["authorized_container_identity"]
    with pytest.raises(ValueError, match="complete container identity"):
        batch.new_state(contract, batch.sha(path), "fixed", root, incomplete)
    assert not root.exists()
    assert all(not Path(job["output"]).exists() for job in contract["remaining_jobs"])


@pytest.mark.parametrize("field", ["boot_id", "pid1_start_ticks"])
def test_same_hostname_rebuilt_container_cannot_start_new_run(prepared, monkeypatch, field):
    contract, path, root, authorization = prepared
    rebuilt = copy.deepcopy(authorization["authorized_container_identity"])
    rebuilt[field] += "-rebuilt"
    assert rebuilt["hostname"] == authorization["authorized_container_hostname"]
    monkeypatch.setattr(batch.proven, "container_identity", lambda: rebuilt)
    with pytest.raises(ValueError, match="complete container identity"):
        batch.new_state(contract, batch.sha(path), "fixed", root, authorization)
    assert not root.exists()
    assert all(not Path(job["output"]).exists() for job in contract["remaining_jobs"])


def test_completed_chunk_keeps_global_deadline_armed():
    previous = signal.getsignal(signal.SIGALRM)
    with pytest.raises(TimeoutError, match="operation deadline"):
        with batch.deadline_timeout(0.15):
            before = signal.getitimer(signal.ITIMER_REAL)[0]
            with batch.chunk_timeout(0.1):
                time.sleep(0.01)
            remaining = signal.getitimer(signal.ITIMER_REAL)[0]
            assert 0 < remaining < before
            time.sleep(0.5)
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0
    assert signal.getsignal(signal.SIGALRM) == previous


def test_nested_chunk_never_extends_earlier_global_deadline():
    with pytest.raises(TimeoutError, match="operation deadline"):
        with batch.deadline_timeout(0.05), batch.chunk_timeout(0.5):
            time.sleep(0.5)
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_earlier_chunk_timeout_restores_unexpired_global_deadline():
    with batch.deadline_timeout(0.2):
        with pytest.raises(TimeoutError, match="operation deadline"):
            with batch.chunk_timeout(0.02):
                time.sleep(0.5)
        assert 0 < signal.getitimer(signal.ITIMER_REAL)[0] < 0.2
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_global_deadline_covers_runtime_and_preserves_new_failure_record(prepared, monkeypatch):
    contract, path, root, authorization = prepared
    authorization = copy.deepcopy(authorization)
    authorization["deadline_unix"] = time.time() + 0.1
    authorization["not_before_unix"] = authorization["deadline_unix"] - 1
    authorization["approved_wall_seconds"] = 1
    auth_path = path.parent / "synthetic-authorization.json"
    batch.write_new(auth_path, authorization)
    monkeypatch.setattr(batch, "validate_contract", lambda _c: {})
    monkeypatch.setattr(batch.proven, "runtime_checks", lambda: time.sleep(0.5))
    monkeypatch.setattr(batch, "run_batch", lambda *_a: pytest.fail("fit scheduler reached"))
    monkeypatch.setattr(batch.sys, "argv", ["runner", "--contract", str(path), "--execute",
        "--new-run", "--expected-commit", "fixed", "--reviewed-contract-sha256", batch.sha(path),
        "--authorization", str(auth_path), "--authorization-sha256", batch.sha(auth_path)])
    with pytest.raises(TimeoutError, match="operation deadline"):
        batch.main()
    assert not root.exists()
    failures = list(root.parent.glob(root.name + ".attempt-failure-*.json"))
    assert len(failures) == 1
    failure = batch.read(failures[0])
    assert failure["error_type"] == "TimeoutError"
    assert failure["state_exists"] is False
    assert failure["absolute_deadline_unix"] == authorization["deadline_unix"]
    assert failure["automatic_training_retries"] == 0
    assert all(not Path(job["output"]).exists() for job in contract["remaining_jobs"])


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


def test_expired_global_deadline_does_not_add_termination_grace(prepared, monkeypatch):
    contract, path, root, _authorization = prepared
    state = make_state(prepared)
    state["deadline_unix"] = time.time() - 1
    calls, killed = [], []

    class Process:
        pid = 54321

        def wait(self, timeout=None):
            calls.append(timeout)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("synthetic", timeout)
            return -9

    monkeypatch.setattr(batch.subprocess, "Popen", lambda *_a, **_k: Process())
    monkeypatch.setattr(batch.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    with pytest.raises(ValueError, match="no retry"):
        batch.launch_worker(root, state, path, contract["remaining_jobs"][0], 8, 0.01)
    assert calls == [0.01, None]
    assert killed == [(54321, signal.SIGTERM), (54321, signal.SIGKILL)]


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
