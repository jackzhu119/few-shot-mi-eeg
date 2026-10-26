"""Login-side GitHub reporting; reporting/network errors never stop a GPU worker."""

from __future__ import annotations

import fcntl
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from hpc_recalibration.github_sync import GitHubClient, _load_token, _settings, _store_token
from .configuration import load_config
from .runtime import atomic_json, load_tasks, utc_now


def authorize(config):
    options = _settings(config)
    directory = options["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "authorization.json"
    if receipt.is_file() and options["token_file"].is_file() and not config.get("_reauthorize"):
        old = json.loads(receipt.read_text())
        if (
            old.get("repository") == options["repository"]
            and old.get("branch") == options["branch"]
            and old.get("status_prefix") == options["status_prefix"]
        ):
            print(
                "GitHub authorization: reusing this V3 scope; reporting retries independently.",
                flush=True,
            )
            return old
    token_path = options["token_file"]
    if not sys.stdin.isatty():
        if not token_path.is_file():
            raise ValueError("Enter GitHub authorization in the interactive school login terminal")
        token = _load_token(token_path)
    else:
        print(
            "GitHub authorization for this new round; token is hidden and never uploaded.",
            flush=True,
        )
        supplied = getpass.getpass(
            "GitHub token (Enter reuses the existing private server token): "
        ).strip()
        token = supplied or (_load_token(token_path) if token_path.is_file() else "")
    if not token or any(c.isspace() or ord(c) < 32 for c in token):
        raise ValueError("A valid GitHub token with repository Contents read/write is required")
    value = {
        "repository": options["repository"],
        "branch": options["branch"],
        "status_prefix": options["status_prefix"],
        "authorized_at": utc_now(),
        "scope": "V3 progress and saved derived results; no secrets, weights or EEG",
        "this_authorization_did_not_start_a_fit": True,
    }
    client = GitHubClient(token, options["repository"], options["branch"])
    client.put_status(options["status_prefix"] + "/AUTHORIZATION.json", value)
    _store_token(token_path, token)
    atomic_json(receipt, value)
    return value


def snapshot(config):
    output = Path(config["output_root"])
    tasks = load_tasks(config)
    task_rows, statistics = [], []
    safe = (
        "phase",
        "stage",
        "epoch",
        "global_step",
        "step",
        "proposals",
        "processed_samples",
        "evaluated_samples",
        "source_anchor_kl",
        "updated_at",
        "checkpoint_at",
        "exit_code",
    )
    for task in tasks:
        folder = output / "tasks" / task["task_id"]
        row = {
            k: task[k]
            for k in (
                "task_id",
                "family",
                "participant",
                "seed",
                "source_regime",
                "variant",
                "dataset",
                "synthetic",
                "software_validation_only",
            )
            if k in task
        }
        row["status"] = "not_started"
        try:
            if (folder / "progress.json").is_file():
                progress = json.loads((folder / "progress.json").read_text())
                row.update({k: progress[k] for k in safe if k in progress})
                row["status"] = progress.get("phase", "running")
            if (folder / "complete.json").is_file():
                done = json.loads((folder / "complete.json").read_text())
                if done.get("status") == "completed":
                    row["status"] = "completed"
                    row["completed_at"] = done.get("completed_at")
            if (folder / "summary.json").is_file():
                summary = json.loads((folder / "summary.json").read_text())
                cells = summary.get("results", []) if isinstance(summary, dict) else []
                groups = {}
                for cell in cells:
                    score = cell.get("balanced_accuracy")
                    if score is not None:
                        key = (cell.get("method"), cell.get("requested_budget"))
                        groups.setdefault(key, []).append(score)
                for (method, budget), values in groups.items():
                    statistics.append(
                        {
                            "task_id": task["task_id"],
                            "method": method,
                            "budget": budget,
                            "saved_cells": len(values),
                            "mean_of_available_cells": sum(values) / len(values),
                            "partial_progress_not_final_participant_endpoint": True,
                        }
                    )
        except (OSError, ValueError, TypeError):
            row["reporting_read_error"] = True
        task_rows.append(row)
    return {
        "experiment_id": config["experiment_id"],
        "observed_at": utc_now(),
        "independent_unit": "participant",
        "scope": "discovery; progress is not scientific acceptance",
        "total_tasks": len(tasks),
        "completed_tasks": sum(r["status"] == "completed" for r in task_rows),
        "tasks": task_rows,
        "completed_statistics": statistics,
    }


def slots_finished(config):
    output = Path(config["output_root"])
    ledger = output / ".runtime/submissions.json"
    expected = {}
    if ledger.is_file():
        for entry in json.loads(ledger.read_text()).get("attempts", []):
            if entry.get("job_id"):
                expected[entry["slot"]] = str(entry["job_id"])
    for slot in range(3):
        path = output / ".runtime" / f"slot-{slot}.json"
        if not path.is_file():
            return False
        runs = json.loads(path.read_text()).get("runs", [])
        if not runs or runs[-1].get("status") not in (
            "complete",
            "failed",
            "cancelled",
            "worker_failed",
        ):
            return False
        if slot in expected and str(runs[-1].get("job_id")) != expected[slot]:
            return False  # A newly submitted job has not yet replaced an old terminal run.
    return True


def monitor(config_path, lock_fd=None, once=False):
    config = load_config(config_path)
    options = _settings(config)
    directory = options["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    if lock_fd is None:
        lock_fd = os.open(directory / "monitor.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(lock_fd)
            return 0
    failures = 0
    try:
        while True:
            try:
                value = snapshot(config)
                atomic_json(directory / "pending_snapshot.json", value)
                client = GitHubClient(
                    _load_token(options["token_file"]), options["repository"], options["branch"]
                )
                response = client.put_status(options["status_prefix"] + "/STATUS.json", value)
                outcome = {
                    "ok": True,
                    "synced_at": utc_now(),
                    "commit": response.get("commit", {}).get("sha"),
                    "completed_tasks": value["completed_tasks"],
                    "total_tasks": value["total_tasks"],
                }
                failures = 0
                all_complete = value["completed_tasks"] == value["total_tasks"]
                slots_terminal = slots_finished(config)
                if all_complete or slots_terminal:
                    from .summarize import summarize
                    from .publish_results import publish

                    summarize(config)
                    publication = publish(config)
                    atomic_json(directory / "final_publication.json", publication)
                    if publication.get("status") == "uploaded_unreviewed" and not publication.get(
                        "failed_objects"
                    ):
                        complete_export = all_complete and not publication.get("history_errors")
                        atomic_json(
                            directory / "sync_status.json",
                            {
                                **outcome,
                                "full_saved_result_export_complete": complete_export,
                                "partial_saved_result_export_published": not complete_export,
                            },
                        )
                        return 0
                    outcome.update(ok=False, full_saved_result_export_complete=False)
            except Exception as error:
                outcome = {
                    "ok": False,
                    "error_type": type(error).__name__,
                    "http_status": getattr(error, "status", None),
                    "training_affected": False,
                    "observed_at": utc_now(),
                }
            try:
                atomic_json(directory / "sync_status.json", outcome)
            except OSError:
                print(
                    "Monitor status write failed; reporting will retry; workers are independent.",
                    flush=True,
                )
            print(json.dumps(outcome), flush=True)
            if once:
                return 0 if outcome["ok"] else 1
            failures = 0 if outcome["ok"] else failures + 1
            time.sleep(
                options["interval_seconds"]
                if outcome["ok"]
                else min(180, 15 * 2 ** min(failures, 4))
            )
    finally:
        os.close(lock_fd)


def start_monitor(config_path):
    config = load_config(config_path)
    directory = _settings(config)["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(directory / "monitor.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        old = directory / "monitor.json"
        return json.loads(old.read_text()).get("pid", 0) if old.is_file() else 0
    try:
        with (directory / "monitor.log").open("ab", buffering=0) as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    str(Path(config["project_dir"]) / "bootstrap.py"),
                    "monitor",
                    "--config",
                    str(config_path),
                    "--lock-fd",
                    str(fd),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
                close_fds=True,
                pass_fds=(fd,),
            )
        atomic_json(directory / "monitor.json", {"pid": child.pid, "started_at": utc_now()})
        return child.pid
    finally:
        os.close(fd)
