"""Prepare a separately authorized 36-fit source-only queue with bounded physical export.

Default operation is metadata only. No network, credential provisioning, query adapter
or acceptance writer exists here. Future execution requires a separately reviewed
fixed commit/contract and a current explicit cost/absolute-deadline authorization.
Off-Pod export is a real dot download followed by --verify-export and receipt return;
it is never an automatic upload or R2/scientific acceptance claim.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import run_kumar_development_batch as proven
import run_kumar_development_queue as legacy

ROOT = legacy.ROOT
DEFAULT_CONTRACT = ROOT / "configs/kumar_remaining_source_batch_20261015.json"
DEFAULT_PROPOSAL = ROOT / "configs/kumar_eegnet_formal_freeze_proposal_20261015.json"
# These unchanged functions already operated the original eleven-fit queue. No old
# globals are patched: generic manifest/receipt checks accept the embedded contract.
require, sha, read = proven.require, proven.sha, proven.read
encoded, write_new, atomic = proven.encoded, proven.write_new, proven.atomic
container_identity, journal, save = proven.container_identity, proven.journal, proven.save
reserve_chunk = proven.reserve_chunk
inspect_export, verify_receipt = proven.inspect_export, proven.verify_receipt
checked_lock = proven.checked_lock
FALSE_STAGES = proven.FALSE_STAGES
FIXED_LIMITS = {key: value for key, value in proven.LIMITS.items()
                if key not in {"wall_seconds", "max_new_fits", "max_epochs", "max_steps"}}
FIXED_LIMITS.update(max_new_fits=36, max_epochs=3600, max_steps=10800)
BILLING_OBSERVATION = {
    "observer": "dot_parent",
    "source": "official_RunPod_console_and_Billing",
    "observation_window_utc": ["2026-10-15T04:49Z", "2026-10-15T04:51Z"],
    "observation_window_Asia_Shanghai": ["2026-10-15T12:49+08:00", "2026-10-15T12:51+08:00"],
    "provenance": "parent_reported_actual_read_only_observation_not_this_agent_platform_access",
    "pod_id": "52ivinpjwv947i", "pod_name": "bright_ivory_bear", "pod_status": "running",
    "balance_usd": 1.27, "total_hourly_usd": 0.257,
    "compute_hourly_usd": 0.25, "storage_hourly_usd": 0.007, "storage_gb": 50,
    "estimated_time_left_hours": 5, "autopay_enabled": False,
    "payment_or_topup_changed_by_observer": False,
    "future_topup_relied_on": False, "execution_authorization": False,
}


@contextlib.contextmanager
def deadline_timeout(seconds):
    """Keep the earlier of nested deadlines without cancelling or renewing a parent."""
    if not math.isfinite(seconds) or seconds <= 0:
        raise TimeoutError("Authorized operation deadline reached; preserve state")
    previous_handler = signal.getsignal(signal.SIGALRM)
    started = time.monotonic()
    previous_seconds, previous_interval = signal.getitimer(signal.ITIMER_REAL)
    parent_deadline = started + previous_seconds if previous_seconds > 0 else None
    deadline = min(started + seconds, parent_deadline) if parent_deadline else started + seconds

    def expired(_signum, _frame):
        raise TimeoutError("Authorized operation deadline reached; preserve state")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(deadline - time.monotonic(), 1e-9))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        now = time.monotonic()
        if parent_deadline is not None and parent_deadline > now:
            signal.setitimer(signal.ITIMER_REAL, parent_deadline - now, previous_interval)
        if now >= deadline:
            raise TimeoutError("Authorized operation deadline reached; preserve state")


def chunk_timeout(seconds):
    return deadline_timeout(seconds)


def repo_file(relative):
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(), "Unsafe repository file")
    return path


def pinned(contract, key):
    path = repo_file(contract[key])
    require(sha(path) == contract[key + "_sha256"], "Frozen metadata changed: " + key)
    return path


def validate_contract(contract):
    require(contract["schema_version"] == 1 and contract["policy_revision"] ==
            "remaining-source-bounded-export-v1", "Unknown remaining-source operation")
    require(contract["status"] == "proposal_only_unapproved" and
            contract["execution_enabled"] is False and contract["cost_authorization"] is None and
            contract["authorization"] is None, "Proposal cannot silently become authorization")
    limits = contract["limits"]
    require({k: v for k, v in limits.items() if k != "proposed_wall_seconds"} == FIXED_LIMITS and
            limits["proposed_wall_seconds"] == 10800, "Frozen operational limits differ")
    require(contract["proposed_maximum_usd"] == 1 and
            contract["balance_recheck_max_age_before_start_seconds"] == 300 and
            contract["parent_reported_official_billing_observation"] == BILLING_OBSERVATION,
            "Frozen proposed cost ceiling or actual parent billing observation differs")
    proposal = read(pinned(contract, "scientific_proposal"))
    import check_kumar_checkpoint_reuse_proposal as proposal_checker
    proposal_checker.check(proposal, root=ROOT)
    expected = proposal["remaining_source_training_proposal"]["jobs"]
    jobs = contract["remaining_jobs"]
    require(len(jobs) == 36 and len({j["job_id"] for j in jobs}) == 36,
            "Exactly thirty-six unique source jobs required")
    for original, job in zip(expected, jobs):
        require({key: job[key] for key in original} == original and
                set(job) == set(original) | {"output", "result_key"},
                "Remaining job/order/scientific identity changed")
        output = Path(job["output"])
        require(output.is_absolute() and not output.resolve().is_relative_to(ROOT.resolve()) and
                output.name == f"{job['subject']}-seed-{job['seed']}", "Unsafe job output")
        require(job["result_key"].endswith(output.name + "-run01.tar") and
                "remaining-source-20261015/" in job["result_key"], "Wrong private result identity")
    require(len({j["output"] for j in jobs}) == len({j["result_key"] for j in jobs}) == 36,
            "Duplicate output/result identity")
    ledger = read(pinned(contract, "accepted_ledger"))["accepted_jobs"]
    require(len(ledger) == 18 and not ({j["job_id"] for j in ledger} &
                                      {j["job_id"] for j in jobs}) and
            not ({j["subject"] for j in ledger} & {j["subject"] for j in jobs}),
            "Accepted eighteen must be excluded entirely")
    for key in ("input_manifest", "https_manifest", "scientific_config", "split_manifest", "runtime_inventory"):
        pinned(contract, key)
    inputs = read(pinned(contract, "input_manifest"))
    files = inputs["files"]
    require(inputs["file_count"] == len(files) == 253 and
            inputs["bytes"] == sum(e["bytes"] for e in files) == 196740994 and
            inputs["query_access"] is False and inputs["query_EEG_file_count"] == 0 and
            inputs["query_label_file_count"] == 0, "Source-only input scope changed")
    require([j["subject"] for j in jobs[::3]] == inputs["selectors"]["participants"],
            "Source participants differ")
    require(all(j["training_config_sha256"] == contract["scientific_config_sha256"] and
                j["split_sha256"] == contract["split_manifest_sha256"] for j in jobs),
            "Scientific training/split hashes differ")
    for path, expected_sha in contract["frozen_files"].items():
        require(sha(repo_file(path)) == expected_sha, "Frozen source differs: " + path)
    state_root = Path(contract["state_root"])
    require(str(state_root) == "/workspace/paper2-results/remaining-source-bounded-batch-20261015"
            and not state_root.resolve().is_relative_to(ROOT.resolve()), "Unsafe canonical state")
    require(contract["data_root"] == "/workspace/paper2-data/kumar" and
            contract["download_receipt"] ==
            "/workspace/paper2-results/https-remaining-source-download-run01.json",
            "Source-only input location changed")
    return {"status": "remaining_source_proposal_valid_execution_closed", "accepted_preserved": 18,
            "source_fits_proposed": 36, "input_files": 253, "input_bytes": 196740994,
            "query_access": False, "query_adapter_required": False, "new_fits_authorized": 0,
            "fit_executed": False, "cost_authorization": None}


def authorization_check(contract, contract_sha, commit, authorization, *, now=None):
    """A prior queue's cost/deadline can never authorize this independent source run."""
    now = time.time() if now is None else now
    require(authorization is not None, "Separate current cost/deadline authorization required")
    require(authorization.get("schema_version") == 1 and authorization.get("status") ==
            "parent_reviewed_remaining36_source_execution_authorized" and
            authorization.get("contract_sha256") == contract_sha and
            authorization.get("reviewed_commit") == commit and
            authorization.get("approved_job_ids") == [j["job_id"] for j in contract["remaining_jobs"]]
            and authorization.get("query_access") is False and
            authorization.get("accepted18_refitting_authorized") is False,
            "Current exact source-only parent authorization required")
    cost = authorization.get("cost")
    require(isinstance(cost, dict) and cost.get("currency") == "USD" and
            isinstance(cost.get("maximum_usd"), (int, float)) and
            not isinstance(cost.get("maximum_usd"), bool) and
            0 < cost["maximum_usd"] <= contract["proposed_maximum_usd"] and
            isinstance(cost.get("hourly_rate_usd"), (int, float)) and
            not isinstance(cost.get("hourly_rate_usd"), bool) and cost["hourly_rate_usd"] > 0 and
            isinstance(cost.get("latest_authorization_receipt"), str) and
            bool(cost["latest_authorization_receipt"].strip()),
            "Explicit current cost/rate decision required; null cannot launch")
    require(math.isfinite(cost["maximum_usd"]) and math.isfinite(cost["hourly_rate_usd"]),
            "Finite current cost/rate limits required")
    start, deadline = authorization.get("not_before_unix"), authorization.get("deadline_unix")
    approved_seconds = authorization.get("approved_wall_seconds")
    require(isinstance(start, (int, float)) and not isinstance(start, bool) and
            isinstance(deadline, (int, float)) and not isinstance(deadline, bool) and
            math.isfinite(start) and math.isfinite(deadline) and
            isinstance(approved_seconds, int) and not isinstance(approved_seconds, bool) and
            0 < approved_seconds <= contract["limits"]["proposed_wall_seconds"] and
            deadline - start == approved_seconds and start <= now < deadline,
            "Explicit unexpired absolute deadline required; never reuse/reset prior time")
    require(cost["hourly_rate_usd"] * approved_seconds / 3600 <= cost["maximum_usd"],
            "Approved wall time exceeds current cost cap")
    balance = authorization.get("balance_recheck")
    require(isinstance(balance, dict) and
            balance.get("source") == "official_RunPod_console_or_Billing" and
            isinstance(balance.get("evidence_reference"), str) and
            bool(balance["evidence_reference"].strip()) and
            isinstance(balance.get("balance_usd"), (int, float)) and
            not isinstance(balance.get("balance_usd"), bool) and
            math.isfinite(balance["balance_usd"]) and
            balance["balance_usd"] >= cost["maximum_usd"] and
            isinstance(balance.get("observed_at_unix"), (int, float)) and
            not isinstance(balance.get("observed_at_unix"), bool) and
            math.isfinite(balance["observed_at_unix"]) and
            start - contract["balance_recheck_max_age_before_start_seconds"] <=
            balance["observed_at_unix"] <= min(start, now),
            "Current official balance recheck before authorized start must cover cost cap")
    identity = proven.container_identity()
    require(authorization.get("authorized_container_identity") == identity and
            authorization.get("authorized_container_hostname", identity["hostname"]) ==
            identity["hostname"],
            "Current complete container identity must be explicitly reviewed")
    return authorization


def execution_gate(contract, contract_path, commit, reviewed_sha, authorization):
    summary = validate_contract(contract)
    require(reviewed_sha and sha(contract_path) == reviewed_sha, "Reviewed contract SHA256 required")
    require(commit and subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
            text=True).strip() == commit, "Reviewed fixed source commit required")
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT,
            text=True).strip(), "Future execution requires clean fixed checkout")
    authorization_check(contract, reviewed_sha, commit, authorization)
    runtime, plan, next_job = legacy.check_gate()
    ledger = read(legacy.checked_path(runtime["accepted_jobs"]))["accepted_jobs"]
    require(next_job is None and len(ledger) == 18 and
            [j["job_id"] for j in ledger] == [j["job_id"] for j in plan["jobs"]],
            "All eighteen original acceptances must remain intact")
    return summary


def verify_source_inputs(contract):
    """Full byte/SHA recheck before each future fit; never reads query signal/labels."""
    pinned(contract, "input_manifest")
    https_path = pinned(contract, "https_manifest")
    import fetch_kumar_remaining_source_https as inputs
    require(inputs.CONFIG.resolve() == https_path.resolve(), "Input verifier manifest differs")
    inputs.verify_all(Path(contract["data_root"]), Path(contract["download_receipt"]))
    return {"source_input_files_verified": 253, "source_input_bytes_verified": 196740994,
            "query_rows_loaded": 0}


def validate_result(path, job):
    record = proven.validate_result(path, job)
    require(record["subject"] == job["subject"] and record["seed"] == job["seed"] and
            record["source_train_rows"] == 40 and record["source_validation_rows"] == 20,
            "Saved source participant/seed/count identity differs")
    return record


def budget(state, contract, *, now=None):
    now = time.time() if now is None else now
    auth = state["authorization"]
    authorization_check(contract, state["contract_sha256"], state["fixed_commit"], auth, now=now)
    require(state["started_unix"] == auth["not_before_unix"] and
            state["deadline_unix"] == auth["deadline_unix"], "Absolute authorized budget changed")
    require(sum(r["trained"] and not r["off_Pod_exported"] for r in state["jobs"].values()) <= 2,
            "More than two fits lack durable export")
    require(len(state["jobs"]) <= 36 and
            sum(r.get("epochs", 0) for r in state["jobs"].values()) <= 3600 and
            sum(r.get("steps", 0) for r in state["jobs"].values()) <= 10800,
            "Source-only count budget exceeded")
    allowed = {j["job_id"] for j in contract["remaining_jobs"]}
    require(set(state["jobs"]) <= allowed and
            all(all(record[k] is False for k in FALSE_STAGES) for record in state["jobs"].values()),
            "Runner may neither refit accepted eighteen nor write acceptance")


def disk_guard(contract, root):
    reserve = FIXED_LIMITS["min_free_bytes"] + 2 * FIXED_LIMITS["result_archive_max_bytes"] + \
        FIXED_LIMITS["export_archive_max_bytes"]
    paths = [Path(contract["data_root"]), root]
    paths.extend(Path(j["output"]).parent for j in contract["remaining_jobs"])
    for path in paths:
        while not path.exists():
            path = path.parent
        require(shutil.disk_usage(path).free >= reserve,
                "Insufficient disk reserve; preserve every claim/artifact and stop")


def new_state(contract, contract_sha, commit, root, authorization):
    authorization_check(contract, contract_sha, commit, authorization)
    balance_age = time.time() - authorization["balance_recheck"]["observed_at_unix"]
    require(0 <= balance_age <= contract["balance_recheck_max_age_before_start_seconds"],
            "First run creation requires a current official balance recheck")
    require(not root.exists(), "Canonical state exists; never replace old claims or reset time")
    for job in contract["remaining_jobs"]:
        output = Path(job["output"])
        require(not output.exists() and not output.with_suffix(".tar").exists(),
                "Existing output/reservation; never automatically refit")
    root.mkdir(parents=True, exist_ok=False)
    for name in ("claims", "workers", "exports", "inbox"):
        (root / name).mkdir()
    state = {"schema_version": 1, "run_id": proven.uuid.uuid4().hex,
             "contract_sha256": contract_sha, "fixed_commit": commit,
             "container_identity": container_identity(), "authorization": authorization,
             "started_unix": authorization["not_before_unix"],
             "deadline_unix": authorization["deadline_unix"], "status": "running",
             "pending_export": None, "jobs": {}}
    save(root, state, "independent_remaining36_run_created_authorized_absolute_deadline")
    return state


def resume_state(contract, contract_sha, commit, root, authorization):
    state = proven.resume_state(contract_sha, commit, root)
    require(state["authorization"] == authorization, "Resume authorization changed; no reset")
    budget(state, contract)
    return state


def build_export(contract, contract_path, root, state, jobs, kind, summary):
    disk_guard(contract, root)
    ids = [j["job_id"] for j in jobs]
    path = root / "exports" / (f"{kind}-{ids[0]}-{ids[-1]}.tar")
    files = {"contract.json": contract_path, "state_snapshot.json": root / "state.json",
             "journal.jsonl": root / "journal.jsonl", "frozen_input_manifest.json":
             repo_file(contract["input_manifest"]), "input_receipt.json":
             Path(contract["download_receipt"]), "frozen_accepted18_ledger.json":
             repo_file(contract["accepted_ledger"])}
    for job in jobs:
        job_id = job["job_id"]
        files[f"claims/{job_id}.json"] = root / "claims" / (job_id + ".json")
        if kind == "results":
            files[f"results/{job_id}.tar"] = Path(state["jobs"][job_id]["archive"])
            for suffix in ("stdout.log", "stderr.log", "timing.json", "entered.json"):
                files[f"workers/{job_id}.{suffix}"] = root / "workers" / f"{job_id}.{suffix}"
    payload = {name: source.read_bytes() for name, source in files.items()}
    require(hashlib.sha256(payload["contract.json"]).hexdigest() == state["contract_sha256"],
            "Export contract changed")
    payload["gate_summary.json"] = encoded(summary)
    manifest = {"schema_version": 1, "kind": kind, "run_id": state["run_id"],
                "contract_sha256": state["contract_sha256"], "fixed_commit": state["fixed_commit"],
                "job_ids": ids, "files": [{"path": name, "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in payload.items()]}
    require(sum(map(len, payload.values())) < FIXED_LIMITS["export_archive_max_bytes"] - 1048576,
            "Export exceeds bound")
    payload["manifest.json"] = encoded(manifest)
    import io
    import tarfile
    with path.open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as archive:
        for name, raw in payload.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o600, 0
            archive.addfile(info, io.BytesIO(raw))
    require(path.stat().st_size <= FIXED_LIMITS["export_archive_max_bytes"], "Export exceeds bound")
    state["pending_export"] = {"kind": kind, "archive": str(path), "bytes": path.stat().st_size,
        "sha256": sha(path), "job_ids": ids, "receipt": str(root / "inbox" /
        (path.stem + ".receipt.json")), "wait_deadline_unix": None}
    state["status"] = "awaiting_dot_export_receipt"
    save(root, state, "export_ready", **state["pending_export"])
    print(json.dumps({"status": state["status"], "export": state["pending_export"]}), flush=True)


def await_export(root, state, contract, wait_seconds, *, clock=time.time, sleeper=time.sleep):
    pending = state["pending_export"]
    require(0 <= wait_seconds <= FIXED_LIMITS["wait_seconds_max"], "Export wait exceeds bound")
    if pending["wait_deadline_unix"] is None:
        pending["wait_deadline_unix"] = min(clock() + wait_seconds, state["deadline_unix"])
        save(root, state, "export_wait_started")
    while True:
        budget(state, contract, now=clock())
        receipt_path = Path(pending["receipt"])
        if receipt_path.exists():
            receipt = read(receipt_path)
            verify_receipt(pending, state, receipt)
            write_new(root / "exports" / (Path(pending["archive"]).stem +
                                         ".verified-receipt.json"), receipt)
            for job_id in pending["job_ids"]:
                record = state["jobs"][job_id]
                if pending["kind"] == "intent":
                    record["intent_off_Pod_exported"] = True
                else:
                    require(record["trained"], "Untrained result cannot be exported")
                    record.update(off_Pod_exported=True, stage="exported",
                                  exported_at_utc=receipt["verified_at_utc"])
            state["pending_export"], state["status"] = None, "running"
            save(root, state, "dot_export_receipt_verified", kind=pending["kind"],
                 archive_sha256=pending["sha256"])
            return True
        if clock() >= pending["wait_deadline_unix"]:
            journal(root, "export_wait_expired_safe_pause_no_training_retry")
            return False
        sleeper(min(1.0, pending["wait_deadline_unix"] - clock()))


def launch_worker(root, state, contract_path, job, lock_fd, timeout_seconds):
    job_id = job["job_id"]
    prefix, started = root / "workers" / job_id, time.time()
    require(shutil.which("timeout"), "Existing GNU timeout watchdog required")
    command = ["timeout", "--signal=TERM", "--kill-after=30s", f"{timeout_seconds}s",
        sys.executable, str(Path(__file__).resolve()), "--contract", str(contract_path),
        "--reviewed-contract-sha256", state["contract_sha256"], "--expected-commit",
        state["fixed_commit"], "--authorization", str(root / "authorization.json"),
        "--authorization-sha256", sha(root / "authorization.json"), "--worker-job", job_id,
        "--inherited-lock-fd", str(lock_fd)]
    timed_out = False
    with Path(str(prefix) + ".stdout.log").open("x") as stdout, \
            Path(str(prefix) + ".stderr.log").open("x") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                   start_new_session=True, pass_fds=(lock_fd,))
        try:
            code = process.wait(timeout=timeout_seconds)
        except BaseException:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                cleanup_seconds = min(FIXED_LIMITS["term_grace_seconds"],
                                      state["deadline_unix"] - time.time())
                if cleanup_seconds <= 0:
                    raise subprocess.TimeoutExpired(command, 0)
                code = process.wait(timeout=cleanup_seconds)
            except BaseException:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
    write_new(Path(str(prefix) + ".timing.json"), {"started_unix": started,
              "finished_unix": time.time(), "returncode": code, "timed_out": timed_out,
              "automatic_retries": 0})
    require(not timed_out and code == 75, "Worker failed/timed out; preserve claim, no retry")


def run_batch(contract, contract_path, state, root, wait_seconds, *, worker_call=launch_worker):
    while True:
        budget(state, contract)
        if state["pending_export"]:
            if not await_export(root, state, contract, wait_seconds):
                return 76
        pending = [j for j in contract["remaining_jobs"]
                   if not state["jobs"].get(j["job_id"], {}).get("off_Pod_exported", False)]
        if not pending:
            state["status"] = "complete_exported"
            save(root, state, "all36_trained_and_exported_audit_R2_and_acceptance_pending")
            return 75
        chunk = pending[:2]
        require(all(not state["jobs"].get(j["job_id"], {}).get("trained", False) for j in chunk),
                "Trained result lacks boundary; preserve, never retry")
        summary = execution_gate(contract, contract_path, state["fixed_commit"],
                                 state["contract_sha256"], state["authorization"])
        disk_guard(contract, root)
        if chunk[0]["job_id"] not in state["jobs"]:
            reserve_chunk(root, state, chunk)
            build_export(contract, contract_path, root, state, chunk, "intent", summary)
            continue
        require(all(state["jobs"][j["job_id"]]["stage"] == "reserved" and
                    state["jobs"][j["job_id"]].get("intent_off_Pod_exported") for j in chunk),
                "Partial/ambiguous claim cannot automatically retry")
        # Keep the shared global GPU lock from input recheck through both sequential
        # workers and results packaging. The off-Pod wait occurs after lock release.
        deadline = min(time.time() + 3600, state["deadline_unix"])
        with legacy.LOCK.open("a") as lock, chunk_timeout(deadline - time.time()):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            journal(root, "active_chunk_started", chunk_deadline_unix=deadline,
                    job_ids=[j["job_id"] for j in chunk])
            for job in chunk:
                budget(state, contract)
                execution_gate(contract, contract_path, state["fixed_commit"],
                               state["contract_sha256"], state["authorization"])
                disk_guard(contract, root)
                record = state["jobs"][job["job_id"]]
                record["stage"] = "starting"
                save(root, state, "fit_starting", job_id=job["job_id"])
                remaining = min(deadline, state["deadline_unix"]) - time.time() - 30
                require(remaining > 0, "No time for safe termination")
                worker_call(root, state, contract_path, job, lock.fileno(), min(1800, remaining))
                result_path = Path(job["output"]).with_suffix(".tar")
                result = validate_result(result_path, job)
                record.update(stage="trained", trained=True, archive=str(result_path),
                    archive_bytes=result_path.stat().st_size, archive_sha256=sha(result_path),
                    epochs=result["epochs_executed"], steps=result["optimizer_steps"],
                    trained_at_utc=datetime.now(timezone.utc).isoformat())
                save(root, state, "fit_trained_not_audited_or_accepted", job_id=job["job_id"])
                budget(state, contract)
            build_export(contract, contract_path, root, state, chunk, "results", summary)
            require(time.time() < deadline, "Chunk packaging exceeded deadline")


def source_fit(job, contract, contract_path):
    """Future source-only execution; never called by preparation/default metadata mode.

    Same frozen scientific kernel, source adapter and save/replay/package semantics
    as the accepted18. Deliberately does not call legacy.execute (127-input scope)
    or the generic formal_train (would refit accepted models).
    """
    require(job in contract["remaining_jobs"], "Only exact remaining36 source jobs may fit")
    verify_source_inputs(contract)
    import numpy as np
    import torch
    from learning_preserving_bci.datasets.kumar import load_subject
    from learning_preserving_bci.utils.reproducibility import collect_provenance
    from replay_kumar_first_fit import independent_eval
    from train_kumar_eegnet import SourceOnlyEEGNet, load_checkpoint, save_checkpoint, source_arrays

    output = Path(job["output"])
    require(not output.exists() and not output.with_suffix(".tar").exists(),
            "Existing reservation/output must never refit")
    require(torch.cuda.is_available() and os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8",
            "Frozen CUDA/numerical environment required")
    require(not subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid",
            "--format=csv,noheader,nounits"], text=True).strip(), "GPU busy; stop")
    config = read(pinned(contract, "scientific_config"))
    torch.set_num_threads(config["threads"])
    torch.cuda.reset_peak_memory_stats()
    output.mkdir(parents=True, exist_ok=False)
    legacy.event(output, "reserved")
    try:
        for source, name in ((pinned(contract, "scientific_config"), "training_config.json"),
            (Path(contract["download_receipt"]), "input_receipt.json"),
            (contract_path, "queue_runtime.json"), (Path(__file__), "run_source.py"),
            (ROOT / "scripts/train_kumar_eegnet.py", "train_source.py"),
            (ROOT / "src/learning_preserving_bci/datasets/kumar.py", "adapter_source.py")):
            (output / name).write_bytes(source.read_bytes())
        (output / "job.json").write_bytes(encoded(job))
        started = time.monotonic()
        with (output / "training.log").open("x") as log, \
                contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            subject = load_subject(Path(contract["data_root"]), job["subject"],
                ROOT / config["protocol_config"], split_manifest=ROOT / config["split_manifest"],
                allowed_roles={"source_train", "source_validation"})
            source = source_arrays(subject)
            require((len(source[0]), len(source[2])) == (40, 20), "Frozen source counts differ")
            (output / "input_audit.json").write_bytes(encoded(subject.provenance))
            legacy.event(output, "fitting")
            model = SourceOnlyEEGNet(config, job["seed"]).fit_source(*source)
            saved = save_checkpoint(model, output / "weights.pt", synthetic=False,
                                    software_validation_only=False)
            restored = load_checkpoint(output / "weights.pt",
                                       expected_sha256=saved["checkpoint_sha256"])
            require(np.array_equal(model.predict_proba(source[2]),
                                   restored.predict_proba(source[2])), "Checkpoint replay differs")
            x = np.asarray((source[2].astype(np.float32) - restored.channel_mean_) /
                           restored.channel_scale_, dtype=np.float32)
            logits, losses, torch_loss = independent_eval(restored, x, source[3], 16)
            require(abs(torch_loss - model.selected_validation_loss_) <= 1e-7 and
                    abs(float(losses.mean()) - model.selected_validation_loss_) <= 1e-7,
                    "Frozen source replay tolerance exceeded; preserve checkpoint")
            np.savez(output / "source_validation_predictions.npz", logits=logits,
                     labels=source[3], loss_float64=losses,
                     trial_ids=np.asarray(restored.source_validation_ids_))
            torch.cuda.synchronize()
            record = dict(status="fit_saved", job_id=job["job_id"], subject=job["subject"],
                seed=job["seed"], query_rows_loaded=0, source_train_rows=40,
                source_validation_rows=20, checkpoint_sha256=saved["checkpoint_sha256"],
                training_config_sha256=job["training_config_sha256"], split_sha256=job["split_sha256"],
                selected_epoch=model.selected_epoch_, epochs_executed=len(model.history_),
                optimizer_steps=model.optimizer_steps_, selected_validation_loss=
                model.selected_validation_loss_, replay_torch_loss=torch_loss,
                replay_numpy_loss=float(losses.mean()), replay_absolute_tolerance=1e-7,
                runtime_seconds=time.monotonic() - started,
                peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
                provenance=collect_provenance(job["seed"], ROOT),
                accepted18_baseline_verified=True, execution_cost_deadline_authorized=True,
                parent_result_acceptance_pending=True, R2_backup_verified=False,
                synthetic=False)
            require(record["epochs_executed"] <= 100 and record["optimizer_steps"] <= 300,
                    "Frozen source-fit count budget exceeded")
            write_new(output / "fit_result.json", record)
        legacy.event(output, "fit_saved")
        return legacy.package(output, job)
    except BaseException:
        legacy.event(output, "failed_preserved_no_automatic_retry")
        (output / "failure_traceback.txt").write_text(traceback.format_exc())
        raise


def worker(contract_path, contract_sha, commit, root, job_id, fd, authorization):
    checked_lock(fd)
    contract = read(contract_path)
    execution_gate(contract, contract_path, commit, contract_sha, authorization)
    runtime = proven.runtime_checks()
    # Supervisor resume rejects any starting claim. Its dedicated child must check
    # that exact starting claim without calling the supervisor resume scheduler.
    state = read(root / "state.json")
    require(state["contract_sha256"] == contract_sha and state["fixed_commit"] == commit and
            state["container_identity"] == container_identity() and
            state["authorization"] == authorization and state["status"] == "running",
            "Worker run/container/authorization identity changed")
    budget(state, contract)
    record = state["jobs"][job_id]
    require(record["stage"] == "starting" and record.get("intent_off_Pod_exported") and
            not record["trained"], "Worker requires unused durably exported intent")
    claim = read(root / "claims" / (job_id + ".json"))
    job = next(j for j in contract["remaining_jobs"] if j["job_id"] == job_id)
    require(claim["job"] == job and claim["run_id"] == state["run_id"] and
            claim["contract_sha256"] == contract_sha, "Worker claim identity differs")
    disk_guard(contract, root)
    write_new(root / "workers" / f"{job_id}.entered.json", {"run_id": state["run_id"],
        "job_id": job_id, "pid": os.getpid(), "GPU_lock_inherited": True,
        "utc": datetime.now(timezone.utc).isoformat(), "fresh_runtime_verification": runtime})
    print(json.dumps(source_fit(job, contract, contract_path)), flush=True)
    return 75


def execute_authorized(args, contract, authorization):
    """Every runtime/checkout/state/export step runs under the absolute watchdog."""
    execution_gate(contract, args.contract, args.expected_commit,
                   args.reviewed_contract_sha256, authorization)
    root = Path(contract["state_root"])
    if args.worker_job:
        return worker(args.contract, args.reviewed_contract_sha256, args.expected_commit,
                      root, args.worker_job, args.inherited_lock_fd, authorization)
    require(args.new_run or args.resume, "Explicit new-run or same-run resume required")
    require(0 <= args.wait_seconds <= 600, "Export wait exceeds bound")
    proven.runtime_checks()
    disk_guard(contract, root)
    root.parent.mkdir(parents=True, exist_ok=True)
    with (root.parent / (root.name + ".supervisor.lock")).open("a") as supervisor:
        fcntl.flock(supervisor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.new_run:
            state = new_state(contract, args.reviewed_contract_sha256, args.expected_commit,
                              root, authorization)
            write_new(root / "authorization.json", authorization)
        else:
            state = resume_state(contract, args.reviewed_contract_sha256, args.expected_commit,
                                 root, authorization)
        def interrupted(_signum, _frame):
            raise InterruptedError("Supervisor interrupted; preserve active claim")
        old_term, old_hup = signal.signal(signal.SIGTERM, interrupted), \
            signal.signal(signal.SIGHUP, interrupted)
        try:
            return run_batch(contract, args.contract, state, root, args.wait_seconds)
        except BaseException as error:
            state["status"] = "failed_preserved_no_automatic_retry"
            save(root, state, "failed_preserved_no_automatic_retry", error_type=type(error).__name__)
            raise
        finally:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGHUP, old_hup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--new-run", action="store_true")
    mode.add_argument("--resume", action="store_true")
    parser.add_argument("--expected-commit")
    parser.add_argument("--reviewed-contract-sha256")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--authorization-sha256")
    parser.add_argument("--wait-seconds", type=int, default=600)
    parser.add_argument("--verify-export", type=Path)
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--attest-off-pod-possession", action="store_true")
    parser.add_argument("--worker-job", help=argparse.SUPPRESS)
    parser.add_argument("--inherited-lock-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.verify_export:
        require(args.attest_off_pod_possession and args.receipt_output,
                "dot must explicitly attest actual full off-Pod possession")
        write_new(args.receipt_output, inspect_export(args.verify_export))
        print(json.dumps({"status": "export_verified", "receipt": str(args.receipt_output)}))
        return 0
    contract = read(args.contract)
    if not args.execute and not args.worker_job or args.plan_only:
        summary = validate_contract(contract)
        print(json.dumps({**summary, "limits": contract["limits"],
                          "remaining_jobs": contract["remaining_jobs"]}, indent=2))
        return 0
    require(args.authorization and args.authorization_sha256 and
            sha(args.authorization) == args.authorization_sha256,
            "Separate current authorization bytes/SHA256 required")
    authorization = read(args.authorization)
    authorization_check(contract, args.reviewed_contract_sha256, args.expected_commit,
                        authorization)
    try:
        with deadline_timeout(authorization["deadline_unix"] - time.time()):
            return execute_authorized(args, contract, authorization)
    except BaseException as error:
        root = Path(contract["state_root"])
        root.parent.mkdir(parents=True, exist_ok=True)
        failure = root.parent / (root.name + ".attempt-failure-" + proven.uuid.uuid4().hex + ".json")
        write_new(failure, {"schema_version": 1,
            "status": "supervisor_attempt_failed_preserve_all_state_no_retry",
            "contract_sha256": args.reviewed_contract_sha256,
            "fixed_commit": args.expected_commit,
            "authorization_sha256": args.authorization_sha256,
            "absolute_deadline_unix": authorization["deadline_unix"],
            "state_exists": (root / "state.json").is_file(),
            "error_type": type(error).__name__, "automatic_training_retries": 0,
            "utc": datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
