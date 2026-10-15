"""Guarded, one-attempt CPU evaluation of the accepted54 frozen checkpoints.

Default checking reads code and frozen JSON metadata only. The private worker
is reachable only through a live parent claim and inherited CPU lock. No fit,
optimizer, model search, data download or credentials are implemented here.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/kumar_frozen_query_operation_20261015.json"
ENTRY = "scripts/run_kumar_frozen_query_evaluation.py"
KERNEL = "scripts/evaluate_kumar_frozen_queries.py"
HELPER = "scripts/run_kumar_csp_signed_score_operation.py"
HELPER_SHA = "215ec7ec6cb199f2d70c485969583f9b09cfc8346ed7f316448bc92bfdadbf56"
LEDGER = "research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json"
LEDGER_SHA = "013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670"
PLAN = "research_logs/kumar_remaining36_acceptance_20261015/run01/source_model_plan_all54.json"
PLAN_SHA = "28232bfa53515ae3e66acadefa39ee025320cfda0196a5d785631bf4d8f8abcd"
SPLIT = "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json"
SPLIT_SHA = "ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28"
INPUTS = "configs/kumar_frozen_query_inputs_20261015.json"
INPUTS_SHA = "4636a83e6be52c8e06de089ec2cc866e2008f6f17412b8d820dc62234999f76f"
CHECKPOINTS = "configs/kumar_frozen_query_checkpoints_20261015.json"
CHECKPOINTS_SHA = "12e2565c4a1d6e83809e6e513907fce53af47a9b37b4214ba8e62922fb54a6d9"
STATE = "research_logs/kumar_frozen_query_evaluation_20261015/run01"
LOCK = "/workspace/.locks/few-shot-mi-eeg-cpu.lock"
DIAGNOSTIC = "kumar-accepted54-always-frozen-query-evaluation-run01-20261015"
PYTHON = "/workspace/.venvs/few-shot-mi-eeg/bin/python"
RUNTIME = {"python": "3.11.16", "torch": "2.8.0+cpu", "numpy": "2.2.6",
           "scipy": "1.15.3", "scikit-learn": "1.7.2", "mne": "1.10.2",
           "braindecode": "1.2.0", "torchaudio": "2.8.0+cpu"}
THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "CUBLAS_WORKSPACE_CONFIG": ":4096:8"}
LIMITS = {"maximum_wall_seconds": 7200, "cleanup_reserve_seconds": 30,
          "resource_poll_seconds": 0.25, "minimum_free_disk_bytes": 2 * 1024**3,
          "minimum_effective_available_memory_bytes": 3 * 1024**3,
          "maximum_process_tree_rss_bytes": 2 * 1024**3,
          "minimum_running_headroom_bytes": 1024**3, "automatic_retries": 0}
FALSE_PERMISSIONS = ("training_authorized", "optimizer_updates_authorized",
                     "target_support_access_authorized", "new_strategy_authorized",
                     "new_resources_authorized")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def publish(path, value):
    """Preserve incomplete temporary bytes; publish exclusively and atomically."""
    path = Path(path)
    temporary = path.with_name(path.name + ".partial")
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)  # Existing evidence is never replaced.
    temporary.unlink()
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def helper(root=ROOT):
    path = root / HELPER
    require(sha(path) == HELPER_SHA, "Frozen process monitor changed")
    spec = importlib.util.spec_from_file_location("frozen_query_cpu_monitor", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def checked_path(root, relative):
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == relative,
            "Unsafe frozen relative path")
    result = root / relative
    require(result.resolve().is_relative_to(root.resolve()) and not result.is_symlink(),
            "Input escaped its bound root")
    return result


def metadata_check(contract, root=ROOT):
    require(contract["schema_version"] == 1 and contract["diagnostic_id"] == DIAGNOSTIC
            and contract["status"] == "proposal_only_separate_query_execution_review_required"
            and contract["scope"] == "accepted54_always_frozen_query_only"
            and contract["execution_enabled"] is False and contract["authorization"] is None
            and contract["not_before_unix"] is None and contract["deadline_unix"] is None
            and contract["query_evaluation_authorized"] is False
            and all(contract[key] is False for key in FALSE_PERMISSIONS)
            and contract["limits"] == LIMITS and contract["runtime"] == RUNTIME
            and contract["thread_environment"] == THREAD_ENV and contract["torch_threads"] == 1
            and contract["state_directory"] == STATE and contract["shared_cpu_lock"] == LOCK,
            "Frozen query operation scope changed")
    pins = contract["frozen_files"]
    for path, expected in {HELPER: HELPER_SHA, LEDGER: LEDGER_SHA, PLAN: PLAN_SHA,
                           SPLIT: SPLIT_SHA, INPUTS: INPUTS_SHA,
                           CHECKPOINTS: CHECKPOINTS_SHA}.items():
        require(pins.get(path) == expected, "Frozen metadata binding changed")
    require({ENTRY, KERNEL} <= pins.keys(), "Missing frozen entrypoint bindings")
    for path, expected in pins.items():
        require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected)
                and sha(checked_path(root, path)) == expected, "Frozen file changed: " + path)
    ledger, plan, inputs = read(root / LEDGER), read(root / PLAN), read(root / INPUTS)
    jobs, accepted = plan["jobs"], ledger["accepted_jobs"]
    require(len(jobs) == len(accepted) == 54 and len({j["job_id"] for j in jobs}) == 54,
            "Exactly54 accepted identities required")
    require([j["job_id"] for j in jobs] == [j["job_id"] for j in accepted],
            "Accepted identity order changed")
    for job, entry in zip(jobs, accepted):
        require(all(job[k] == entry[k] for k in ("job_id", "subject", "seed", "result_key")),
                "Accepted checkpoint identity changed")
    require(len({PurePosixPath(j["result_key"]).name for j in jobs}) == 54,
            "Ambiguous archive filenames")
    checkpoint_inventory = read(root / CHECKPOINTS)
    originals = checkpoint_inventory["models"]
    require(len(originals) == 54 and [row["job_id"] for row in originals]
            == [j["job_id"] for j in jobs], "Original checkpoint deployment order differs")
    for entry, original in zip(accepted, originals):
        require(all(entry[key] == original[key] for key in
                    ("job_id", "subject", "seed", "result_key", "archive_sha256"))
                and original["filename"] == PurePosixPath(entry["result_key"]).name,
                "Original checkpoint deployment identity differs")
    accepted = [dict(entry, archive_bytes=original["archive_bytes"])
                for entry, original in zip(accepted, originals)]
    require(inputs["file_count"] == len(inputs["files"]) == 1189
            and inputs["bytes"] == sum(row["bytes"] for row in inputs["files"]) == 1043686331
            and inputs["edf_count"] == 216 and inputs["included_row_count"] == 4290
            and inputs["excluded_partial_row_count"] == 30
            and set(inputs["allowed_roles"]) == {"source_query", "target_query"},
            "Frozen query inventory changed")
    for row in inputs["dependencies"] + checkpoint_inventory["dependencies"]:
        path = checked_path(root, row["path"])
        require(path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                "Frozen query/acceptance metadata dependency changed")
    observed = {"python": platform.python_version(), **{
        name: importlib.metadata.version(name) for name in RUNTIME if name != "python"}}
    threads = {name: os.environ.get(name) for name in THREAD_ENV}
    problems = []
    if observed != RUNTIME or str(Path(sys.executable).absolute()) != PYTHON:
        problems.append("Frozen CPU runtime/executable differs")
    if threads != THREAD_ENV or os.environ.get("MKL_NUM_THREADS") not in {None, "1"}:
        problems.append("Existing numerical thread environment differs; launcher never mutates it")
    if (root / STATE).exists():
        problems.append("Historical attempt/state exists; no retry or overwrite")
    return {"status": "metadata_verified_execution_closed", "execution_authorized": False,
            "runtime": observed, "thread_environment": threads, "problems": problems,
            "query_files_opened": False, "checkpoint_archives_opened": False,
            "models_constructed": False, "accepted_models": 54,
            "query_input_files": 1189, "query_input_bytes": 1043686331,
            "query_included_rows": 4290, "jobs": jobs, "accepted": accepted, "inputs": inputs}


def authorization_check(auth, contract_sha, commit, jobs, monitor, now=None):
    now = time.time() if now is None else now
    bindings = {"reviewed_commit": commit, "contract_sha256": contract_sha,
                "accepted_ledger_sha256": LEDGER_SHA, "source_plan_sha256": PLAN_SHA,
                "split_manifest_sha256": SPLIT_SHA, "query_input_manifest_sha256": INPUTS_SHA}
    require(auth.get("status") == "parent_reviewed_frozen_checkpoint_query_evaluation_authorized"
            and auth.get("scope") == "accepted54_always_frozen_query_only"
            and auth.get("query_evaluation_authorized") is True
            and all(auth.get(key) is False for key in FALSE_PERMISSIONS)
            and all(auth.get(key) == value for key, value in bindings.items())
            and auth.get("approved_job_ids") == [j["job_id"] for j in jobs]
            and auth.get("authorized_container_identity") == monitor.container_identity(),
            "Exact external query-only authorization and current host identity required")
    start, deadline = auth.get("not_before_unix"), auth.get("deadline_unix")
    require(all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
                for v in (start, deadline)) and 30 < deadline - start <= 7200
            and start <= now < deadline - 30, "Absolute query window invalid; no deadline reset")
    return deadline


def verify_query_bytes(inputs, data_root):
    observed = []
    for row in inputs["files"]:
        path = checked_path(data_root, row["relative_path"])
        require(path.is_file() and path.stat().st_size == row["bytes"]
                and sha(path) == row["sha256"], "Frozen query input bytes changed: " + row["relative_path"])
        observed.append({"relative_path": row["relative_path"], "bytes": row["bytes"],
                         "sha256": row["sha256"]})
    return {"file_count": len(observed), "bytes": sum(r["bytes"] for r in observed),
            "files": observed, "verification": "local_full_bytes_sha256"}


def evaluate_subjects(jobs, accepted, *, data_root, archive_root, output, inputs,
                      subject_loader, checkpoint_loader, checkpoint_kwargs, guard):
    """One complete subject tensor at a time; every fixed seed, no retries."""
    results, expected_order = [], [j["job_id"] for j in jobs]
    subjects = list(dict.fromkeys(j["subject"] for j in jobs))
    entries = {entry["job_id"]: entry for entry in accepted}
    for subject in subjects:
        guard()
        loaded = subject_loader(data_root, subject, ROOT / inputs["protocol_path"],
                                ROOT / SPLIT, allowed_roles={"source_query", "target_query"})
        require(all(row["role"] in {"source_query", "target_query"} for row in loaded.metadata),
                "Adapter returned a forbidden role")
        subject_results = []
        for job in (j for j in jobs if j["subject"] == subject):
            guard()
            archive = checked_path(archive_root, PurePosixPath(job["result_key"]).name)
            require(archive.is_file() and archive.stat().st_size == entries[job["job_id"]]["archive_bytes"]
                    and sha(archive) == entries[job["job_id"]]["archive_sha256"],
                    "Original accepted checkpoint archive bytes differ")
            handle = checkpoint_loader(archive, job_id=job["job_id"], **checkpoint_kwargs)
            result = handle.evaluate_queries(loaded.X, loaded.y, loaded.metadata)
            guard()
            require(sha(archive) == entries[job["job_id"]]["archive_sha256"],
                    "Checkpoint archive changed during evaluation")
            path = output / (job["subject"] + "-seed-" + str(job["seed"]) + ".json")
            publish(path, result)
            row = {"job_id": job["job_id"], "subject": subject, "seed": job["seed"],
                   "path": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            results.append(row)
            subject_results.append(row)
            del handle, result
        publish(output / (subject + "-complete.json"), {"subject": subject, "jobs": subject_results})
        del loaded
    require([row["job_id"] for row in results] == expected_order,
            "Sequential fixed job order or completeness changed")
    return results


def worker(args, contract, checked, monitor):
    """Private subprocess, inheriting the live parent's already-held CPU lock."""
    state, output = ROOT / STATE, args.output.resolve()
    require(checked["problems"] == ["Historical attempt/state exists; no retry or overwrite"],
            "Private worker metadata/runtime or existing claim differs")
    claim = read(state / "claim.json")
    require(args.worker_fd is not None and claim["launcher_pid"] == os.getppid()
            and monitor.process_record(os.getppid(), Path("/proc"))["start_ticks"]
            == claim["launcher_start_ticks"], "Private worker requires its actual live launcher")
    lock_stat, inherited = Path(LOCK).stat(), os.fstat(args.worker_fd)
    require((lock_stat.st_dev, lock_stat.st_ino) == (inherited.st_dev, inherited.st_ino),
            "Private worker did not inherit the shared CPU lock")
    fcntl.flock(args.worker_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(claim["output"] == str(output) and claim["data_root"] == str(args.data_root.resolve())
            and claim["archive_root"] == str(args.archive_root.resolve()), "Claimed input/output roots differ")
    require(claim["reviewed_commit"] == args.expected_commit
            and claim["contract_sha256"] == args.reviewed_contract_sha256 == sha(CONTRACT)
            and claim["authorization_sha256"] == args.authorization_sha256
            and claim["container_identity"] == monitor.container_identity(),
            "Private worker claim authorization/contract/host differs")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            == args.expected_commit and not subprocess.check_output(
            ["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).strip(),
            "Private worker fixed checkout differs")
    auth_path = args.authorization.resolve()

    def guard():
        require(sha(auth_path) == args.authorization_sha256, "External authorization changed")
        deadline = authorization_check(read(auth_path), sha(CONTRACT), args.expected_commit,
                                       checked["jobs"], monitor)
        require(time.time() < deadline - 30, "Query deadline reached; preserve partial output")
        require(shutil.disk_usage(output).free >= LIMITS["minimum_free_disk_bytes"],
                "Output disk reserve exhausted")

    guard()
    archive_verification = []
    for entry in checked["accepted"]:
        path = checked_path(args.archive_root.resolve(), PurePosixPath(entry["result_key"]).name)
        require(path.is_file() and path.stat().st_size == entry["archive_bytes"]
                and sha(path) == entry["archive_sha256"], "Original accepted checkpoint archive bytes differ")
        archive_verification.append({"job_id": entry["job_id"], "filename": path.name,
            "bytes": entry["archive_bytes"], "sha256": entry["archive_sha256"], "result_key": entry["result_key"]})
    publish(output / "checkpoint_archive_full_sha256_before.json", {"files": archive_verification,
        "verification": "local_original_full_bytes_sha256", "file_count": len(archive_verification)})
    guard()
    verification = verify_query_bytes(checked["inputs"], args.data_root.resolve())
    publish(output / "input_full_sha256_before.json", verification)
    guard()
    import torch
    require(torch.__version__ == RUNTIME["torch"] and torch.get_num_threads() == 1
            and not torch.cuda.is_available(), "Frozen CPU/torch thread state differs")
    from learning_preserving_bci.datasets.kumar import load_subject
    from evaluate_kumar_frozen_queries import load_frozen_query_checkpoint
    kwargs = dict(ledger_path=ROOT / LEDGER, expected_ledger_sha256=LEDGER_SHA,
                  plan_path=ROOT / PLAN, expected_plan_sha256=PLAN_SHA,
                  split_path=ROOT / SPLIT, expected_split_sha256=SPLIT_SHA,
                  query_manifest_path=ROOT / INPUTS, expected_query_manifest_sha256=INPUTS_SHA,
                  operation_contract_sha256=sha(CONTRACT), expected_commit=args.expected_commit,
                  authorization_path=auth_path, expected_authorization_sha256=args.authorization_sha256,
                  evidence_root=ROOT, software_validation_only=False)
    results = evaluate_subjects(checked["jobs"], checked["accepted"], data_root=args.data_root.resolve(),
        archive_root=args.archive_root.resolve(), output=output, inputs=checked["inputs"],
        subject_loader=load_subject, checkpoint_loader=load_frozen_query_checkpoint,
        checkpoint_kwargs=kwargs, guard=guard)
    guard()
    require(verify_query_bytes(checked["inputs"], args.data_root.resolve()) == verification,
            "Query input bytes changed during evaluation")
    require(len(results) == 54, "Incomplete frozen query baseline")
    from aggregate_kumar_frozen_queries import aggregate_query_results
    aggregate = aggregate_query_results([read(output / row["path"]) for row in results], checked["jobs"],
        expected_query_ids=checked["inputs"]["included_query_trial_ids"], synthetic=False)
    guard()
    publish(output / "aggregate_summary.json", aggregate)
    publish(output / "worker_complete.json", {"status": "all54_evaluated_pending_independent_audit",
        "job_count": 54, "jobs": results, "query_input_bytes_unchanged": True,
        "new_fits": 0, "optimizer_instances": 0, "accepted": False,
        "independently_audited": False, "R2_full_GET_verified": False})


def execute(args, contract, checked, monitor):
    require(not checked["problems"], "Metadata/runtime preflight failed: " + "; ".join(checked["problems"]))
    require(args.authorization is not None and sha(args.authorization) == args.authorization_sha256,
            "External authorization exact bytes required")
    require(args.reviewed_contract_sha256 == sha(CONTRACT), "Reviewed contract SHA differs")
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_commit or ""), "Full fixed commit required")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            == args.expected_commit and not subprocess.check_output(
            ["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).strip(),
            "Reviewed checkout changed")
    deadline = authorization_check(read(args.authorization), sha(CONTRACT), args.expected_commit,
                                   checked["jobs"], monitor)
    absolute = time.monotonic() + deadline - time.time()
    require(args.data_root is not None and args.archive_root is not None and args.output is not None,
            "Explicit existing data/archive roots and new output path required")
    data_root, archive_root, output = (p.resolve() for p in (args.data_root, args.archive_root, args.output))
    require(data_root.is_dir() and archive_root.is_dir() and not output.exists(),
            "Input roots absent or output already exists")
    resource = monitor.resources(output)
    require(resource["memory"]["effective_available_bytes"] >= LIMITS["minimum_effective_available_memory_bytes"]
            and resource["free_output_disk_bytes"] >= LIMITS["minimum_free_disk_bytes"],
            "Actual CPU memory/disk preflight failed")
    lock_path = Path(LOCK)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_descriptor, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = ROOT / STATE
        state.mkdir(parents=True, exist_ok=False)
        receipt = {"diagnostic_id": DIAGNOSTIC, "status": "claimed_not_complete",
                   "query_evaluation_completed": False, "accepted": False,
                   "independently_audited": False, "R2_full_GET_verified": False,
                   "resource_samples": [], "signals": [], "new_fits": 0}
        process, history, stopped, handlers = None, {}, False, {}

        def stop():
            nonlocal stopped
            require(not stopped, "Cleanup already attempted; no renewed grace")
            stopped = True
            for installed in handlers:
                signal.signal(installed, signal.SIG_IGN)
            grace = min(30, max(0, deadline - time.time()), max(0, absolute - time.monotonic()))
            try:
                if not history and process.poll() is not None:
                    receipt["returncode"], receipt["signals"] = process.poll(), []
                    return  # No known live identity; never signal a possibly recycled PGID.
                code, events = monitor.stop_process(process, grace, history)
                receipt["returncode"], receipt["signals"] = code, events
            except BaseException as error:
                receipt["signals"] = getattr(error, "signal_events", [])
                raise

        def interrupted(number, frame):
            for installed in handlers:
                signal.signal(installed, signal.SIG_IGN)
            raise InterruptedError("Query launcher received " + signal.Signals(number).name)

        try:
            for number in (signal.SIGTERM, signal.SIGHUP):
                handlers[number] = signal.signal(number, interrupted)
            with monitor.deadline_guard(absolute - 30):
                output.mkdir(parents=True, exist_ok=False)
                claim = {"diagnostic_id": DIAGNOSTIC, "launcher_pid": os.getpid(),
                    "launcher_start_ticks": monitor.process_record(os.getpid(), Path("/proc"))["start_ticks"],
                    "claimed_at_utc": monitor.utc(), "container_identity": monitor.container_identity(),
                    "reviewed_commit": args.expected_commit, "contract_sha256": sha(CONTRACT),
                    "authorization_sha256": args.authorization_sha256, "deadline_unix": deadline,
                    "data_root": str(data_root), "archive_root": str(archive_root), "output": str(output),
                    "resource_preflight": resource, "automatic_retries": 0}
                publish(state / "claim.json", claim)
            argv = [PYTHON, "-B", str(ROOT / ENTRY), "--worker-internal", "--worker-fd", str(lock.fileno()),
                "--expected-commit", args.expected_commit, "--reviewed-contract-sha256", args.reviewed_contract_sha256,
                "--authorization", str(args.authorization.resolve()), "--authorization-sha256", args.authorization_sha256,
                "--data-root", str(data_root), "--archive-root", str(archive_root), "--output", str(output)]
            with (state / "worker.log").open("xb") as log:
                require(time.monotonic() < absolute - 30, "Original deadline exhausted before launch")
                receipt["launch_attempt_at_utc"] = monitor.utc()
                process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT / "scripts")),
                    start_new_session=True, pass_fds=(lock.fileno(),))
                receipt["pid"], receipt["started_at_utc"] = process.pid, monitor.utc()
                with monitor.deadline_guard(absolute - 30):
                    publish(state / "worker_start.json", {"pid": process.pid,
                        "started_at_utc": receipt["started_at_utc"], "deadline_unix": deadline})
                    while process.poll() is None:
                        observation = monitor.running_memory(process.pid, observed_descendants=history)
                        receipt["resource_samples"].append({"at_utc": monitor.utc(), **observation})
                        require(observation["consumer_rss_bytes"] < LIMITS["maximum_process_tree_rss_bytes"]
                            and observation["host_available_bytes"] > LIMITS["minimum_running_headroom_bytes"]
                            and (observation["cgroup_headroom_bytes"] is None or observation["cgroup_headroom_bytes"]
                                 > LIMITS["minimum_running_headroom_bytes"])
                            and shutil.disk_usage(output).free >= LIMITS["minimum_free_disk_bytes"],
                            "Running CPU memory/disk reserve exceeded")
                        try:
                            process.wait(timeout=min(0.25, max(0, absolute - 30 - time.monotonic())))
                        except subprocess.TimeoutExpired:
                            pass
                require(bool(history), "No complete live process-tree sample captured")
                stop()  # Also proves previously observed descendants exited after root exit.
                require(receipt["returncode"] == 0 and not receipt["signals"],
                        "Worker failed or required descendant cleanup; preserve partial")
                complete = read(output / "worker_complete.json")
                require(complete["job_count"] == 54 and [r["job_id"] for r in complete["jobs"]]
                        == [j["job_id"] for j in checked["jobs"]], "Missing complete54 worker evidence")
                receipt["status"] = "all54_evaluated_pending_independent_audit"
                receipt["query_evaluation_completed"] = True
        except BaseException as error:
            receipt["status"] = "failed_partial_preserved"
            receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
            if process is not None and not stopped:
                try:
                    stop()
                except BaseException as cleanup_error:
                    receipt["cleanup_failure"] = {"type": type(cleanup_error).__name__, "message": str(cleanup_error)}
        finally:
            receipt["finished_at_utc"] = monitor.utc()
            try:
                receipt["output_members"] = monitor.member_inventory(output)
                receipt["log_sha256"] = sha(state / "worker.log") if (state / "worker.log").exists() else None
            except BaseException as error:
                receipt["status"] = "failed_partial_preserved"
                receipt["inventory_failure"] = {"type": type(error).__name__, "message": str(error)}
            try:
                publish(state / "launcher_receipt.json", receipt)
            except BaseException as error:
                receipt["status"] = "failed_partial_preserved"
                receipt["receipt_publication_failure"] = str(error)
                sys.stderr.write(json.dumps(receipt, allow_nan=False) + "\n")
            for number, previous in handlers.items():
                signal.signal(number, previous)
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--worker-internal", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-fd", type=int, help=argparse.SUPPRESS)
    for name in ("data-root", "archive-root", "output", "authorization"):
        parser.add_argument("--" + name, type=Path)
    for name in ("authorization-sha256", "expected-commit", "reviewed-contract-sha256"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    expected, relative = CONTRACT.with_suffix(".sha256").read_text().split()
    require(relative == str(CONTRACT.relative_to(ROOT)) and sha(CONTRACT) == expected,
            "Frozen contract checksum differs")
    contract = read(CONTRACT)
    checked = metadata_check(contract)
    if args.worker_internal:
        worker(args, contract, checked, helper())
        return
    if args.execute:
        result = execute(args, contract, checked, helper())
    else:
        result = {key: value for key, value in checked.items() if key not in {"jobs", "accepted", "inputs"}}
    print(json.dumps(result, indent=2, allow_nan=False))
    if args.execute and result["status"] != "all54_evaluated_pending_independent_audit":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
