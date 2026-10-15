"""Bounded source-only queue; browser export receipts pause execution, never accept fits.

No network transport is implemented. dot downloads each intent/result artifact through
the existing authenticated browser/Jupyter route and runs --verify-export off-Pod.
The resulting receipt is an explicit dot attestation of off-Pod possession, rather
than cryptographic proof of the machine's physical location.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import signal
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import run_kumar_development_queue as single

ROOT = single.ROOT
DEFAULT_CONTRACT = ROOT / "configs/kumar_development_batch_20261015.json"
LIMITS = {
    "chunk_fits": 2,
    "fit_timeout_seconds": 1800,
    "chunk_timeout_seconds": 3600,
    "term_grace_seconds": 30,
    "wait_seconds_max": 600,
    "wall_seconds": 19800,
    "min_free_bytes": 5 * 1024**3,
    "result_archive_max_bytes": 16 * 1024**2,
    "export_archive_max_bytes": 64 * 1024**2,
    "max_epochs": 1100,
    "max_steps": 3300,
    "max_new_fits": 11,
    "max_local_unexported_fits": 2,
    "automatic_retries": 0,
}
FALSE_STAGES = ("independently_audited", "R2_full_GET_verified", "accepted")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def atomic(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".new")
    write_new(temporary, value)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def container_identity():
    return {
        "hostname": platform.node(),
        "pid1_start_ticks": Path("/proc/1/stat").read_text().rsplit(")", 1)[1].split()[19],
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    }


def repo_file(relative):
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(), "Unsafe source path")
    return path


def validate_contract(contract):
    require(contract["schema_version"] == 1, "Unknown batch schema")
    require(contract["policy_revision"] == "bounded-export-v1", "Unknown operation revision")
    require(contract["limits"] == LIMITS, "Frozen operating limits changed")
    require(contract["initial_accepted_jobs"] == 7, "Initial acceptance must be seven")
    require(sha(repo_file(contract["queue_plan"])) == contract["queue_plan_sha256"],
            "Queue plan hash changed")
    plan = read(repo_file(contract["queue_plan"]))
    require(len(plan["jobs"]) == 18, "Unexpected frozen queue")
    require(contract["completed_prefix_job_ids"] == [j["job_id"] for j in plan["jobs"][:7]],
            "Completed seven-job prefix changed")
    require(contract["remaining_jobs"] == plan["jobs"][7:], "Only exact final eleven are allowed")
    require(len({j["job_id"] for j in contract["remaining_jobs"]}) == 11,
            "Remaining job identity is not unique")
    require(contract["data_root"] == "/workspace/paper2-data/kumar", "Frozen data root changed")
    require(contract["download_receipt"] ==
            "/workspace/paper2-results/https-development-download-run01.json",
            "Frozen input receipt path changed")
    state_root = Path(contract["state_root"])
    require(state_root.is_absolute() and not state_root.resolve().is_relative_to(ROOT.resolve()),
            "State and binary artifacts must remain outside Git")
    require(str(state_root) == "/workspace/paper2-results/bounded-batch-20261015",
            "Canonical state root changed")
    return plan


def source_checks(contract):
    for relative, expected in contract["frozen_files"].items():
        require(sha(repo_file(relative)) == expected, "Frozen source changed: " + relative)
    for key in ("input_manifest", "recovery_source_manifest", "runtime_inventory"):
        require(sha(repo_file(contract[key])) == contract[key + "_sha256"],
                "Frozen manifest changed: " + key)
    manifest = read(repo_file(contract["recovery_source_manifest"]))
    require(len(manifest["required_files"]) == 149, "Source closure is not 149 files")
    ledger = read(single.RUNTIME)["accepted_jobs"]
    checked = []
    for entry in manifest["required_files"]:
        if entry["path"] == ledger:
            continue  # Old snapshot contains ledger6; current ledger is checked by the ACK gate.
        path = repo_file(entry["path"])
        require(path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"],
                "Frozen recovery source changed: " + entry["path"])
        checked.append(entry["path"])
    require(len(checked) == 148, "Unexpected mutable source exception")
    return {"frozen_recovery_files_verified": 148, "active_ledger_checked_by_original_gate": True}


def gate(contract, *, executing):
    validate_contract(contract)
    source_checks(contract)
    runtime, plan, _ = single.check_gate()
    accepted = read(single.checked_path(runtime["accepted_jobs"]))["accepted_jobs"]
    require([j["job_id"] for j in accepted] ==
            [j["job_id"] for j in plan["jobs"][:len(accepted)]], "Noncontiguous ordered ledger")
    ready = len(accepted) >= 7
    if executing:
        require(ready, "Seventh fit still awaits actual parent acknowledgement; execution blocked")
        require([j["job_id"] for j in accepted[:7]] == contract["completed_prefix_job_ids"],
                "Accepted prefix differs from the frozen seven")
        baseline = subprocess.check_output(
            ["git", "show", contract["initial_accepted_baseline_commit"] + ":" +
             runtime["accepted_jobs"]], cwd=ROOT)
        require(hashlib.sha256(baseline).hexdigest() == contract["initial_accepted_ledger_sha256"] and
                accepted[:7] == json.loads(baseline)["accepted_jobs"],
                "Initial seven acceptances differ from fixed actual parent acknowledgements")
    return runtime, {"accepted_jobs": len(accepted), "initial_gate_ready": ready,
                     "query_access": False, "formal_gate": False}


def runtime_checks():
    inventory = read(ROOT / "research_logs/kumar_pod_rebuild_recovery_20261014/runtime_inventory.json")
    require(platform.python_version() == inventory["scientific_runtime_observed_in_old_fit6"]["python"],
            "Frozen Python runtime differs")
    versions = inventory["target_environment"]["linux_x86_64_python311_selected_versions"]
    require(len(versions) == 91, "Unexpected runtime package closure")
    for name, version in versions.items():
        require(importlib.metadata.version(name) == version, "Frozen package differs: " + name)
    for name, expected in {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                           "CUBLAS_WORKSPACE_CONFIG": ":4096:8"}.items():
        require(os.environ.get(name) == expected, "Frozen numerical environment differs: " + name)
    import torch

    require(torch.__version__ == "2.8.0+cu128" and torch.version.cuda == "12.8" and
            torch.cuda.is_available(), "Frozen Torch/CUDA runtime unavailable")
    gpu = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
        text=True).strip()
    require(gpu.count("\n") == 0 and tuple(part.strip() for part in gpu.split(",")) ==
            ("NVIDIA RTX A4500", "580.159.04"),
            "Observed GPU/driver differs from reviewed recovered runtime")
    return {"python": platform.python_version(), "locked_packages_verified": versions,
            "torch_cuda": torch.version.cuda, "GPU_driver_live": gpu,
            "numerical_environment": {name: os.environ[name] for name in
               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "CUBLAS_WORKSPACE_CONFIG")}}


def journal(state_root, event, **details):
    with (state_root / "journal.jsonl").open("a") as stream:
        stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                                 "event": event, **details}, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def save(state_root, state, event, **details):
    atomic(state_root / "state.json", state)
    journal(state_root, event, **details)


def budget(state, contract, *, now=None):
    now = time.time() if now is None else now
    require(state["started_unix"] <= now < state["deadline_unix"], "Absolute queue deadline reached")
    require(state["deadline_unix"] - state["started_unix"] == LIMITS["wall_seconds"],
            "Absolute queue budget changed")
    jobs = state["jobs"].values()
    require(sum(j["trained"] and not j["off_Pod_exported"] for j in jobs) <= 2,
            "More than two fits lack durable export")
    require(sum(j.get("epochs", 0) for j in state["jobs"].values()) <= LIMITS["max_epochs"] and
            sum(j.get("steps", 0) for j in state["jobs"].values()) <= LIMITS["max_steps"],
            "Remaining scientific budget exceeded")
    require(len(state["jobs"]) <= contract["limits"]["max_new_fits"], "Too many new fits")


def disk_guard(contract, state_root):
    required = LIMITS["min_free_bytes"] + 2 * LIMITS["result_archive_max_bytes"] + \
        LIMITS["export_archive_max_bytes"]
    paths = [Path(contract["data_root"]), state_root]
    for job in contract["remaining_jobs"]:
        path = Path(job["output"]).parent
        while not path.exists():
            path = path.parent
        paths.append(path)
    for path in paths:
        require(shutil.disk_usage(path).free >= required, "Insufficient disk reserve; preserve and stop")


def new_state(contract, contract_sha, expected_commit, root):
    require(not root.exists(), "Canonical batch state exists; never replace claims or start afresh")
    require(platform.node() == contract["authorized_initial_container_hostname"],
            "New container is not authorized for fresh execution; recovery review required")
    for job in contract["remaining_jobs"]:
        output = Path(job["output"])
        require(not output.exists() and not output.with_suffix(".tar").exists(),
                "Existing fit/output reservation; never automatically refit")
    root.mkdir(parents=True, exist_ok=False)
    for name in ("claims", "workers", "exports", "inbox"):
        (root / name).mkdir()
    now = time.time()
    state = {"schema_version": 1, "run_id": uuid.uuid4().hex,
             "contract_sha256": contract_sha, "fixed_commit": expected_commit,
             "container_identity": container_identity(), "started_unix": now,
             "deadline_unix": now + LIMITS["wall_seconds"], "status": "running",
             "pending_export": None, "jobs": {}}
    save(root, state, "run_created")
    return state


def resume_state(contract_sha, expected_commit, root):
    require((root / "state.json").is_file(), "Missing canonical run state; recovery review required")
    state = read(root / "state.json")
    require(state["contract_sha256"] == contract_sha and state["fixed_commit"] == expected_commit,
            "Run identity/version changed")
    require(state["container_identity"] == container_identity(),
            "Container changed; no automatic execution recovery or claim deletion")
    require(state["status"] in {"running", "awaiting_dot_export_receipt", "complete_exported"},
            "Failed/ambiguous run cannot resume automatically")
    for job_id, record in state["jobs"].items():
        require(read(root / "claims" / (job_id + ".json"))["job_id"] == job_id,
                "Missing immutable claim")
        require(record["stage"] not in {"starting", "failed"},
                "Started/partial job is ambiguous; never automatically retry")
        require(all(record[key] is False for key in FALSE_STAGES), "Runner cannot claim acceptance")
    return state


def reserve_chunk(root, state, jobs):
    ids = [job["job_id"] for job in jobs]
    require(len(ids) <= 2 and len(set(ids)) == len(ids), "Invalid chunk size")
    for job in jobs:
        job_id = job["job_id"]
        require(job_id not in state["jobs"], "Existing claim cannot be reserved or retrained")
        output = Path(job["output"])
        require(not output.exists() and not output.with_suffix(".tar").exists(),
                "Existing output/partial reservation cannot be retrained")
        claim = {"run_id": state["run_id"], "contract_sha256": state["contract_sha256"],
                 "fixed_commit": state["fixed_commit"], "job_id": job_id, "job": job,
                 "status": "immutable_reserved_intent_never_delete"}
        write_new(root / "claims" / (job_id + ".json"), claim)
        state["jobs"][job_id] = {"stage": "reserved", "trained": False,
                                  "off_Pod_exported": False,
                                  **{key: False for key in FALSE_STAGES}}
    save(root, state, "chunk_claims_reserved", job_ids=ids)


def build_export(root, state, jobs, kind, gate_summary):
    disk_guard(read(DEFAULT_CONTRACT), root)
    ids = [j["job_id"] for j in jobs]
    export_name = f"{kind}-{ids[0]}-{ids[-1]}"
    path = root / "exports" / (export_name + ".tar")
    require(not path.exists(), "Export already exists; preserve and inspect")
    files = {"contract.json": ROOT / "configs/kumar_development_batch_20261015.json",
             "state_snapshot.json": root / "state.json",
             "journal.jsonl": root / "journal.jsonl",
             "frozen_input_manifest.json": repo_file(read(DEFAULT_CONTRACT)["input_manifest"]),
             "frozen_source_manifest.json": repo_file(read(DEFAULT_CONTRACT)["recovery_source_manifest"]),
             "input_receipt.json": Path(read(DEFAULT_CONTRACT)["download_receipt"])}
    for job in jobs:
        job_id = job["job_id"]
        files[f"claims/{job_id}.json"] = root / "claims" / (job_id + ".json")
        if kind == "results":
            files[f"results/{job_id}.tar"] = Path(state["jobs"][job_id]["archive"])
            for suffix in ("stdout.log", "stderr.log", "timing.json", "entered.json"):
                files[f"workers/{job_id}.{suffix}"] = root / "workers" / f"{job_id}.{suffix}"
    payload = {name: source.read_bytes() for name, source in files.items()}
    require(hashlib.sha256(payload["contract.json"]).hexdigest() == state["contract_sha256"],
            "Exported contract changed")
    payload["gate_summary.json"] = encoded(gate_summary)
    manifest = {"schema_version": 1, "kind": kind, "run_id": state["run_id"],
                "contract_sha256": state["contract_sha256"], "fixed_commit": state["fixed_commit"],
                "job_ids": ids, "files": [{"path": name, "bytes": len(raw),
                  "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in payload.items()]}
    require(sum(len(raw) for raw in payload.values()) < LIMITS["export_archive_max_bytes"] - 1048576,
            "Export exceeds bound")
    payload["manifest.json"] = encoded(manifest)
    with path.open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as archive:
        for name, raw in payload.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o600, 0
            archive.addfile(info, io.BytesIO(raw))
    require(path.stat().st_size <= LIMITS["export_archive_max_bytes"], "Export exceeds bound")
    state["pending_export"] = {"kind": kind, "archive": str(path), "bytes": path.stat().st_size,
                               "sha256": sha(path), "job_ids": ids,
                               "receipt": str(root / "inbox" / (export_name + ".receipt.json")),
                               "wait_deadline_unix": None}
    state["status"] = "awaiting_dot_export_receipt"
    save(root, state, "export_ready", **state["pending_export"])
    print(json.dumps({"status": "awaiting_dot_export_receipt", "run_id": state["run_id"],
                      "export": state["pending_export"]}), flush=True)


def inspect_export(path):
    path = Path(path)
    require(path.is_file() and path.stat().st_size <= LIMITS["export_archive_max_bytes"],
            "Missing/oversized export")
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        require(len(members) <= 128 and sum(member.size for member in members) <=
                LIMITS["export_archive_max_bytes"] and
                len(names) == len(set(names)) and all(member.isfile() for member in members),
                "Unsafe/duplicate export members")
        require(all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in names),
                "Unsafe export paths")
        require("manifest.json" in names, "Missing export manifest")
        manifest = json.load(archive.extractfile("manifest.json"))
        entries = manifest["files"]
        require(len({entry["path"] for entry in entries}) == len(entries) and
                set(names) == {entry["path"] for entry in entries} | {"manifest.json"},
                "Export manifest member set mismatch")
        for entry in entries:
            raw = archive.extractfile(entry["path"]).read()
            require(len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"],
                    "Export member length/SHA mismatch")
        contract_raw = archive.extractfile("contract.json").read()
        require(hashlib.sha256(contract_raw).hexdigest() == manifest["contract_sha256"],
                "Export contract identity mismatch")
        jobs = {job["job_id"]: job for job in json.loads(contract_raw)["remaining_jobs"]}
        require(manifest["kind"] in {"intent", "results"} and
                1 <= len(manifest["job_ids"]) <= 2 and
                len(set(manifest["job_ids"])) == len(manifest["job_ids"]) and
                all(job_id in jobs for job_id in manifest["job_ids"]), "Export job scope mismatch")
        result_archives = []
        for job_id in manifest["job_ids"]:
            claim = json.load(archive.extractfile(f"claims/{job_id}.json"))
            require(claim["job"] == jobs[job_id] and claim["run_id"] == manifest["run_id"] and
                    claim["contract_sha256"] == manifest["contract_sha256"] and
                    claim["fixed_commit"] == manifest["fixed_commit"], "Export intent differs")
            if manifest["kind"] == "results":
                raw = archive.extractfile(f"results/{job_id}.tar").read()
                record = validate_result(raw, jobs[job_id])
                result_archives.append({"job_id": job_id, "archive_bytes": len(raw),
                                        "archive_sha256": hashlib.sha256(raw).hexdigest(),
                                        "checkpoint_sha256": record["checkpoint_sha256"],
                                        "all_14_payload_member_hashes_verified": True})
    return {"schema_version": 1, "status": "dot_off_Pod_full_member_SHA256_verified",
            "physical_location_is_dot_attestation_not_machine_proof": True,
            "run_id": manifest["run_id"], "contract_sha256": manifest["contract_sha256"],
            "fixed_commit": manifest["fixed_commit"], "kind": manifest["kind"],
            "job_ids": manifest["job_ids"], "archive_bytes": path.stat().st_size,
            "archive_sha256": sha(path), "files": entries, "result_archives": result_archives,
            "verified_at_utc": datetime.now(timezone.utc).isoformat()}


def verify_receipt(pending, state, receipt):
    expected = inspect_export(pending["archive"])
    for key in ("status", "physical_location_is_dot_attestation_not_machine_proof", "run_id",
                "contract_sha256", "fixed_commit", "kind", "job_ids", "archive_bytes",
                "archive_sha256", "files", "result_archives"):
        require(receipt.get(key) == expected[key], "Off-Pod receipt mismatch: " + key)
    require(expected["archive_sha256"] == pending["sha256"] and
            expected["archive_bytes"] == pending["bytes"] and
            expected["job_ids"] == pending["job_ids"] and
            expected["run_id"] == state["run_id"] and
            expected["contract_sha256"] == state["contract_sha256"], "Pending artifact changed")


def await_export(root, state, contract, wait_seconds, *, clock=time.time, sleeper=time.sleep):
    pending = state["pending_export"]
    require(0 <= wait_seconds <= LIMITS["wait_seconds_max"], "Export wait exceeds frozen bound")
    if pending["wait_deadline_unix"] is None:
        pending["wait_deadline_unix"] = min(clock() + wait_seconds, state["deadline_unix"])
        save(root, state, "export_wait_started")
    while True:
        budget(state, contract, now=clock())
        receipt_path = Path(pending["receipt"])
        if receipt_path.exists():
            receipt = read(receipt_path)
            verify_receipt(pending, state, receipt)
            archived = root / "exports" / (Path(pending["archive"]).stem + ".verified-receipt.json")
            write_new(archived, receipt)
            for job_id in pending["job_ids"]:
                record = state["jobs"][job_id]
                if pending["kind"] == "intent":
                    record["intent_off_Pod_exported"] = True
                else:
                    require(record["trained"], "Cannot export untrained result")
                    record["off_Pod_exported"] = True
                    record["stage"] = "exported"
                    record["exported_at_utc"] = receipt["verified_at_utc"]
            state["pending_export"] = None
            state["status"] = "running"
            save(root, state, "dot_export_receipt_verified", kind=pending["kind"],
                 archive_sha256=pending["sha256"])
            return True
        if clock() >= pending["wait_deadline_unix"]:
            journal(root, "export_wait_expired_safe_pause_no_retry")
            return False
        sleeper(min(1.0, pending["wait_deadline_unix"] - clock()))


def validate_result(path, job):
    if isinstance(path, bytes):
        require(len(path) <= LIMITS["result_archive_max_bytes"], "Oversized nested result archive")
        opened = tarfile.open(fileobj=io.BytesIO(path), mode="r:")
    else:
        path = Path(path)
        require(path.is_file() and path.stat().st_size <= LIMITS["result_archive_max_bytes"],
                "Missing/oversized result archive; preserve and stop")
        opened = tarfile.open(path, "r:")
    with opened as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        require(len(names) == len(single.FILES) + 1 and len(set(names)) == len(names) and
                sum(member.size for member in members) <= LIMITS["result_archive_max_bytes"] and
                set(names) == set(single.FILES) | {"manifest.json"} and
                all(member.isfile() for member in members), "Result member set differs")
        manifest = json.load(archive.extractfile("manifest.json"))
        require(manifest["job_id"] == job["job_id"] and manifest["query_rows_loaded"] == 0,
                "Result identity/query mismatch")
        require(len(manifest["files"]) == len(single.FILES) and
                {entry["path"] for entry in manifest["files"]} == set(single.FILES),
                "Result manifest set differs")
        for entry in manifest["files"]:
            raw = archive.extractfile(entry["path"]).read()
            require(len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"],
                    "Result member length/SHA mismatch")
        record = json.load(archive.extractfile("fit_result.json"))
        checkpoint = archive.extractfile("weights.pt").read()
        require(record["job_id"] == job["job_id"] and record["status"] == "fit_saved" and
                record["query_rows_loaded"] == 0 and
                record["training_config_sha256"] == job["training_config_sha256"] and
                record["split_sha256"] == job["split_sha256"] and
                record["replay_absolute_tolerance"] == 1e-7 and
                hashlib.sha256(checkpoint).hexdigest() == record["checkpoint_sha256"] and
                1 <= record["epochs_executed"] <= 100 and 1 <= record["optimizer_steps"] <= 300,
                "Saved fit identity/checkpoint/budget mismatch")
    return record


def checked_lock(fd):
    require(fd >= 3, "Worker requires inherited GPU lock descriptor")
    require(os.fstat(fd).st_ino == single.LOCK.stat().st_ino and
            os.fstat(fd).st_dev == single.LOCK.stat().st_dev, "Wrong inherited GPU lock")
    with single.LOCK.open("a") as independent:
        try:
            fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        fcntl.flock(independent, fcntl.LOCK_UN)
        raise ValueError("Inherited shared GPU lock is not held")


@contextlib.contextmanager
def chunk_timeout(seconds):
    """Bound input checks, both workers and result packaging; worker cleanup adds <=30s."""
    def expired(_signum, _frame):
        raise TimeoutError("Active chunk deadline reached; preserve claims, no retry")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def worker(contract_path, contract_sha, expected_commit, root, job_id, fd):
    checked_lock(fd)
    require(sha(contract_path) == contract_sha, "Worker contract changed")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            == expected_commit, "Worker source commit changed")
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
            "Worker requires clean frozen source checkout")
    contract = read(contract_path)
    runtime, _ = gate(contract, executing=True)
    live_runtime = runtime_checks()
    state = read(root / "state.json")
    require(state["fixed_commit"] == expected_commit and state["contract_sha256"] == contract_sha and
            state["container_identity"] == container_identity(), "Worker run identity changed")
    budget(state, contract)
    record = state["jobs"][job_id]
    require(record["stage"] == "starting" and record.get("intent_off_Pod_exported") and
            not record["trained"], "Worker requires unused durable intent")
    claim = read(root / "claims" / (job_id + ".json"))
    require(claim["run_id"] == state["run_id"] and claim["contract_sha256"] == contract_sha,
            "Worker immutable claim differs")
    job = next(job for job in contract["remaining_jobs"] if job["job_id"] == job_id)
    require(claim["job"] == job, "Worker claim job differs")
    output = Path(job["output"])
    require(not output.exists() and not output.with_suffix(".tar").exists(),
            "Existing output cannot be executed again")
    disk_guard(contract, root)
    write_new(root / "workers" / f"{job_id}.entered.json",
              {"run_id": state["run_id"], "job_id": job_id, "pid": os.getpid(),
               "utc": datetime.now(timezone.utc).isoformat(), "GPU_lock_inherited": True,
               "fresh_runtime_verification": live_runtime})
    result = single.execute(job, runtime, Path(contract["data_root"]),
                            Path(contract["download_receipt"]))
    print(json.dumps(result), flush=True)
    return 75


def launch_worker(root, state, contract_path, job, lock_fd, timeout_seconds):
    job_id = job["job_id"]
    started = time.time()
    prefix = root / "workers" / job_id
    require(shutil.which("timeout") is not None, "Existing GNU timeout watchdog is required")
    command = ["timeout", "--signal=TERM", "--kill-after=30s", f"{timeout_seconds}s",
               sys.executable, str(Path(__file__).resolve()), "--contract", str(contract_path),
               "--reviewed-contract-sha256", state["contract_sha256"], "--expected-commit",
               state["fixed_commit"], "--worker-job", job_id, "--inherited-lock-fd", str(lock_fd)]
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
                code = process.wait(timeout=LIMITS["term_grace_seconds"])
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
    write_new(Path(str(prefix) + ".timing.json"),
              {"started_unix": started, "finished_unix": time.time(), "returncode": code,
               "timed_out": timed_out, "automatic_retries": 0})
    require(not timed_out and code == 75, "Fit failed/timed out; preserve claim, no retry")


def run_batch(contract, contract_path, state, root, wait_seconds, *, worker_call=launch_worker):
    while True:
        budget(state, contract)
        if state["pending_export"]:
            if not await_export(root, state, contract, wait_seconds):
                return 76
        pending = [job for job in contract["remaining_jobs"]
                   if not state["jobs"].get(job["job_id"], {}).get("off_Pod_exported", False)]
        if not pending:
            state["status"] = "complete_exported"
            save(root, state, "all_eleven_trained_and_exported_acceptance_pending")
            return 75
        chunk = pending[:LIMITS["chunk_fits"]]
        require(all(not state["jobs"].get(job["job_id"], {}).get("trained", False)
                    for job in chunk), "Trained result missing export boundary; no retry")
        _, summary = gate(contract, executing=True)
        disk_guard(contract, root)
        if chunk[0]["job_id"] not in state["jobs"]:
            reserve_chunk(root, state, chunk)
            build_export(root, state, chunk, "intent", summary)
            continue
        require(all(state["jobs"][j["job_id"]]["stage"] == "reserved" and
                    state["jobs"][j["job_id"]].get("intent_off_Pod_exported") for j in chunk),
                "Existing partial claim cannot run or retry")
        # The parent owns the shared lock for the active chunk; workers inherit this exact fd.
        chunk_deadline = min(time.time() + LIMITS["chunk_timeout_seconds"],
                             state["deadline_unix"])
        with single.LOCK.open("a") as lock, chunk_timeout(chunk_deadline - time.time()):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            journal(root, "active_chunk_started", chunk_deadline_unix=chunk_deadline,
                    job_ids=[job["job_id"] for job in chunk])
            for job in chunk:
                budget(state, contract)
                gate(contract, executing=True)
                disk_guard(contract, root)
                record = state["jobs"][job["job_id"]]
                record["stage"] = "starting"
                save(root, state, "fit_starting", job_id=job["job_id"])
                remaining = min(state["deadline_unix"], chunk_deadline) - time.time() - \
                    LIMITS["term_grace_seconds"]
                require(remaining > 0, "No time for safe process termination")
                worker_call(root, state, contract_path, job, lock.fileno(),
                            min(LIMITS["fit_timeout_seconds"], remaining))
                result_path = Path(job["output"]).with_suffix(".tar")
                result = validate_result(result_path, job)
                record.update(stage="trained", trained=True, archive=str(result_path),
                              archive_bytes=result_path.stat().st_size, archive_sha256=sha(result_path),
                              epochs=result["epochs_executed"], steps=result["optimizer_steps"],
                              trained_at_utc=datetime.now(timezone.utc).isoformat())
                save(root, state, "fit_trained_not_accepted", job_id=job["job_id"])
                budget(state, contract)
            build_export(root, state, chunk, "results", summary)
            require(time.time() < chunk_deadline, "Chunk packaging exceeded its deadline")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--new-run", action="store_true")
    mode.add_argument("--resume", action="store_true")
    parser.add_argument("--expected-commit")
    parser.add_argument("--reviewed-contract-sha256")
    parser.add_argument("--wait-seconds", type=int, default=600)
    parser.add_argument("--verify-export", type=Path)
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--attest-off-pod-possession", action="store_true")
    parser.add_argument("--worker-job", help=argparse.SUPPRESS)
    parser.add_argument("--inherited-lock-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.verify_export:
        require(args.attest_off_pod_possession and args.receipt_output is not None,
                "dot must explicitly attest off-Pod possession and name a new receipt")
        write_new(args.receipt_output, inspect_export(args.verify_export))
        print(json.dumps({"status": "export_verified", "receipt": str(args.receipt_output)}))
        return 0
    contract = read(args.contract)
    require(args.contract.resolve() == DEFAULT_CONTRACT.resolve(),
            "Use the canonical frozen batch contract path")
    if args.worker_job:
        return worker(args.contract, args.reviewed_contract_sha256, args.expected_commit,
                      Path(contract["state_root"]), args.worker_job, args.inherited_lock_fd)
    _, summary = gate(contract, executing=False)
    if not args.execute or args.plan_only:
        print(json.dumps({"status": "plan_only", **summary, "fit_executed": False,
                          "remaining_jobs": contract["remaining_jobs"], "limits": LIMITS}))
        return 0
    require(args.expected_commit and args.reviewed_contract_sha256,
            "Explicit fixed commit and reviewed contract SHA256 required")
    require(sha(args.contract) == args.reviewed_contract_sha256, "Reviewed contract SHA256 differs")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            == args.expected_commit, "Fixed source commit differs")
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
            "Require clean fixed checkout")
    require(args.new_run or args.resume, "Explicit --new-run or --resume is required")
    require(0 <= args.wait_seconds <= LIMITS["wait_seconds_max"], "Wait limit changed")
    _, initial_gate = gate(contract, executing=True)
    if args.new_run:
        require(initial_gate["accepted_jobs"] == 7,
                "Fresh run requires exactly the acknowledged seven; later jobs must never restart")
    runtime_checks()
    root = Path(contract["state_root"])
    # A distinct supervisor lock prevents two runner processes racing on the same WAL.
    root.parent.mkdir(parents=True, exist_ok=True)
    with (root.parent / (root.name + ".supervisor.lock")).open("a") as supervisor:
        fcntl.flock(supervisor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = new_state(contract, args.reviewed_contract_sha256, args.expected_commit, root) \
            if args.new_run else resume_state(args.reviewed_contract_sha256, args.expected_commit, root)
        def interrupted(_signum, _frame):
            raise InterruptedError("Supervisor terminated; preserve active claim and stop")

        old_term = signal.signal(signal.SIGTERM, interrupted)
        old_hup = signal.signal(signal.SIGHUP, interrupted)
        try:
            return run_batch(contract, args.contract, state, root, args.wait_seconds)
        except BaseException as error:
            state["status"] = "failed_preserved_no_automatic_retry"
            save(root, state, "failed_preserved_no_automatic_retry", error_type=type(error).__name__)
            raise
        finally:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGHUP, old_hup)


if __name__ == "__main__":
    raise SystemExit(main())
