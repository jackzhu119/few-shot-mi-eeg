"""Login-node GitHub authorization and independent, restartable progress sync.

This module uses only the standard library. It never runs in the GPU worker and
never uploads checkpoints, trial data, or credentials. Network failures affect
this monitor alone; the local training outputs remain authoritative.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import getpass
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


class SyncError(RuntimeError):
    """A deliberately sanitized error: HTTP response bodies are not exposed."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _settings(config: dict) -> dict:
    supplied = config.get("git_sync", {})
    if not supplied.get("enabled", True):
        raise SyncError("GitHub progress authorization is required before submission; "
                        "set git_sync.enabled=true and authorize on the login terminal.")
    repository = supplied.get("repository", "jackzhu119/few-shot-mi-eeg")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise SyncError("git_sync.repository must be owner/repository.")
    prefix = supplied.get("status_prefix", "training_status/paper2-recalibration-v2")
    if (not isinstance(prefix, str) or not prefix.startswith("training_status/")
            or any(x in ("", ".", "..") for x in prefix.split("/"))):
        raise SyncError("Use a dedicated training_status/<paper-id> status_prefix.")
    branch = supplied.get("branch", "main")
    if not isinstance(branch, str) or not branch or any(ord(c) < 32 for c in branch):
        raise SyncError("git_sync.branch is invalid.")
    token_path = Path(supplied.get("token_file", "~/.config/paper2-hpc/github-token")).expanduser()
    config_dir = Path(config.get("_config_path", ".")).resolve().parent
    output_root = Path(config["output_root"])
    if not output_root.is_absolute():
        output_root = config_dir / output_root
    interval = float(supplied.get("interval_seconds", 180))
    if interval < 30:
        raise SyncError("Progress sync interval must be at least 30 seconds.")
    return {"repository": repository, "branch": branch, "status_prefix": prefix,
            "token_file": token_path, "explicit_token_file": "token_file" in supplied,
            "directory": output_root / "github_sync", "output_root": output_root,
            "interval_seconds": interval,
            "authorization_ttl_seconds": float(supplied.get("authorization_ttl_seconds", 86400))}


def _credential_stat(path: Path) -> dict:
    info = path.stat()
    if info.st_uid != os.getuid():
        raise SyncError("GitHub token file must belong to the current Unix user.")
    if stat.S_IMODE(info.st_mode) != 0o600:
        path.chmod(0o600)
        info = path.stat()
    return {"device": info.st_dev, "inode": info.st_ino, "size": info.st_size,
            "mtime_ns": info.st_mtime_ns}


def _load_token(path: Path) -> str:
    _credential_stat(path)
    token = path.read_text(encoding="utf-8").strip()
    if not token or any(c.isspace() or ord(c) < 32 for c in token):
        raise SyncError("GitHub token file is empty or malformed; authorize again locally.")
    return token


def _store_token(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".github-token.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


class GitHubClient:
    def __init__(self, token: str, repository: str, branch: str):
        self._token = token
        self.repository = repository
        self.branch = branch

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        headers = {"Authorization": "Bearer " + self._token,
                   "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "paper2-hpc-progress"}
        data = None
        if body is not None:
            data = json.dumps(body, allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request("https://api.github.com" + path,
                                         data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Never print a response body or request object: either may contain secrets.
            raise SyncError("GitHub request failed with HTTP " + str(exc.code), exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SyncError("GitHub connection failed; local training continues.") from None
        except (ValueError, TypeError):
            raise SyncError("GitHub returned an invalid JSON response.") from None

    def put_status(self, path: str, payload: dict) -> dict:
        if not path.startswith("training_status/") or ".." in path.split("/"):
            raise SyncError("GitHub writes are restricted to the dedicated status directory.")
        endpoint = "/repos/" + self.repository + "/contents/" + urllib.parse.quote(path, safe="/")
        body_bytes = (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False) + "\n").encode("utf-8")
        content = base64.b64encode(body_bytes).decode("ascii")
        for attempt in range(3):
            try:
                current = self.request("GET", endpoint + "?ref=" + urllib.parse.quote(self.branch, safe=""))
            except SyncError as exc:
                if exc.status != 404:
                    raise
                current = {}
            body = {"message": "Update paper2 HPC progress", "content": content,
                    "branch": self.branch}
            if current.get("sha"):
                body["sha"] = current["sha"]
            try:
                return self.request("PUT", endpoint, body)
            except SyncError as exc:
                if exc.status not in (409, 422) or attempt == 2:
                    raise
        raise AssertionError("unreachable")


def ensure_authorized(config: dict, interactive: bool = True) -> dict:
    """Prompt locally before first submission, then reuse a scoped 24h receipt.

    Explicit git_sync.token_file permits reuse of a user-configured account. A
    default token file without a receipt does not silently authorize a new paper.
    """
    options = _settings(config)
    directory = options["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    receipt_path = directory / "authorization.json"
    receipt = _read_json(receipt_path, {})
    scope = {k: options[k] for k in ("repository", "branch", "status_prefix")}
    same_scope = all(receipt.get(k) == v for k, v in scope.items())
    token_path = options["token_file"]
    if same_scope and token_path.is_file():
        if (receipt.get("credential_stat") == _credential_stat(token_path)
                and time.time() - receipt.get("authorized_unix", 0)
                < options["authorization_ttl_seconds"]):
            return receipt
    use_file = token_path.is_file() and (options["explicit_token_file"] or same_scope)
    if use_file:
        token = _load_token(token_path)
    else:
        if not interactive or not sys.stdin.isatty():
            raise SyncError("Before training, run launch.sh from the school login terminal "
                            "to enter a GitHub token privately, or configure an explicit "
                            "0600 git_sync.token_file. Do not paste tokens into chat.")
        print("GitHub authorization before training: enter a token for "
              + options["repository"] + " with repository Contents read/write permission.",
              flush=True)
        token = getpass.getpass("GitHub token (hidden, stored locally with mode 0600): ").strip()
        if not token or any(c.isspace() or ord(c) < 32 for c in token):
            raise SyncError("No valid token entered; no training was submitted.")
    client = GitHubClient(token, options["repository"], options["branch"])
    try:
        identity = client.request("GET", "/user")
        repository = client.request("GET", "/repos/" + options["repository"])
        if repository.get("permissions", {}).get("push") is False:
            raise SyncError("The authorized account has no push permission for this repository.", 403)
        probe = client.put_status(options["status_prefix"] + "/AUTHORIZATION.json",
                                  {"schema_version": 1, "authorized_at": utc_now(),
                                   "experiment_id": config.get("experiment_id"),
                                   "account": identity.get("login"),
                                   "purpose": "Permission probe before training; no fit started."})
    except SyncError as exc:
        raise SyncError("GitHub authorization failed before submission: " + str(exc)
                        + ". Grant Contents read/write for this repository and rerun launch.sh.",
                        exc.status) from None
    if not use_file:
        _store_token(token_path, token)
    receipt = {"schema_version": 1, **scope, "account": identity.get("login"),
               "authorized_at": utc_now(), "authorized_unix": time.time(),
               "credential_stat": _credential_stat(token_path),
               "write_probe_commit": probe.get("commit", {}).get("sha"),
               "write_probe_passed": True,
               "token_value_or_hash_recorded": False}
    _atomic_json(receipt_path, receipt)
    return receipt


_PROGRESS_KEYS = {"status", "phase", "stage", "step", "global_step", "optimizer_step",
                  "epoch", "samples_processed", "processed_samples", "updated_at",
                  "updated_utc", "checkpoint_at", "checkpoint_utc", "last_checkpoint_at",
                  "session", "method", "budget", "elapsed_seconds", "synthetic",
                  "software_validation_only"}
_METRIC_KEYS = {"method", "budget", "session", "seed", "balanced_accuracy", "accuracy",
                "n_query", "n_samples", "samples", "loss", "source_validation_loss",
                "selected_epoch", "epochs", "steps", "defined", "status", "requested_budget",
                "actual_budget", "budget_requested", "n_support_actual",
                "recall_left", "recall_right", "synthetic",
                "software_validation_only"}


def _safe_fields(value, keys: set) -> dict:
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items() if k in keys
            and (v is None or isinstance(v, (str, int, float, bool)))
            and not (isinstance(v, float) and not (-float("inf") < v < float("inf")))}


def collect_snapshot(config: dict) -> dict:
    options = _settings(config)
    config_dir = Path(config.get("_config_path", ".")).resolve().parent
    task_path = Path(config["tasks_file"])
    if not task_path.is_absolute():
        task_path = config_dir / task_path
    tasks = _read_json(task_path)
    if isinstance(tasks, dict):
        tasks = tasks["tasks"]
    if not isinstance(tasks, list):
        raise SyncError("tasks_file must contain a task list.")
    rows, metrics = [], []
    for task in tasks:
        task_id = str(task["task_id"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", task_id) or task_id in (".", ".."):
            raise SyncError("Task ID is not a safe directory name.")
        directory = options["output_root"] / "tasks" / task_id
        row = {"task_id": task_id, "dataset": task.get("dataset"),
               "participant": task.get("participant"), "seed": task.get("seed"),
               "status": "no_progress_record"}
        try:
            progress = _read_json(directory / "progress.json", {})
            row.update(_safe_fields(progress, _PROGRESS_KEYS))
            if row["status"] == "no_progress_record" and row.get("phase"):
                row["status"] = row["phase"]
            complete = _read_json(directory / "complete.json")
            if complete is not None:
                row["completion_record_present"] = True
            if isinstance(complete, dict) and complete.get("status") == "completed":
                row["status"] = "completed"
                row["completed_at"] = complete.get("completed_at", complete.get("completed_utc"))
                row.update(_safe_fields(complete, _PROGRESS_KEYS))
            # The worker publishes only completed evaluation rows, even when
            # later sessions are still running. Do not wait for whole-task completion.
            summary = _read_json(directory / "summary.json", [])
            if isinstance(summary, dict):
                summary = summary.get("rows", summary.get("results", []))
            for metric in summary:
                safe = _safe_fields(metric, _METRIC_KEYS)
                if safe:
                    metrics.append({"task_id": task_id, "dataset": task.get("dataset"),
                                    "participant": task.get("participant"),
                                    "synthetic": row.get("synthetic", task.get("synthetic", False)),
                                    "software_validation_only": row.get("software_validation_only", False),
                                    **safe})
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            row["monitor_read_status"] = "unreadable_local_record"
        rows.append(row)
    return {"schema_version": 1, "experiment_id": config.get("experiment_id"),
            "observed_at": utc_now(), "source": "local_worker_progress_and_completion_records",
            "scheduler_running_is_not_training_evidence": True,
            "total_tasks": len(rows),
            "completed_tasks": sum(r.get("status") == "completed" for r in rows),
            "tasks": rows, "completed_statistics": metrics}


def sync_once(config: dict) -> dict:
    """Persist the pending snapshot first. Failure is a returned monitor result."""
    options = _settings(config)
    directory = options["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    try:
        snapshot = collect_snapshot(config)
        _atomic_json(directory / "pending_snapshot.json", snapshot)
        token = _load_token(options["token_file"])
        client = GitHubClient(token, options["repository"], options["branch"])
        response = client.put_status(options["status_prefix"] + "/STATUS.json", snapshot)
        outcome = {"ok": True, "observed_at": snapshot["observed_at"],
                   "synced_at": utc_now(), "commit": response.get("commit", {}).get("sha"),
                   "completed_tasks": snapshot["completed_tasks"],
                   "total_tasks": snapshot["total_tasks"]}
    except Exception as exc:
        # The independent monitor must keep retrying; never forward this to a worker.
        outcome = {"ok": False, "observed_at": utc_now(),
                   "error_type": type(exc).__name__, "http_status": getattr(exc, "status", None),
                   "training_affected": False}
    _atomic_json(directory / "sync_status.json", outcome)
    return outcome


def monitor(config_path: str, lock_fd: int | None = None, once: bool = False) -> int:
    config = _read_json(Path(config_path))
    config["_config_path"] = str(Path(config_path).resolve())
    options = _settings(config)
    directory = options["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    if lock_fd is None:
        lock_fd = os.open(directory / "monitor.lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(lock_fd)
            return 0
    _atomic_json(directory / "monitor.json", {"pid": os.getpid(), "host": socket.gethostname(),
                                               "started_at": utc_now()})
    failures = 0
    try:
        while True:
            try:
                outcome = sync_once(config)
            except Exception as exc:
                # Even local reporting/storage errors must not terminate or cancel training.
                outcome = {"ok": False, "error_type": type(exc).__name__, "training_affected": False}
            print(json.dumps({"monitor_at": utc_now(), **outcome}), flush=True)
            failures = 0 if outcome["ok"] else failures + 1
            if once:
                return 0 if outcome["ok"] else 1
            if (outcome["ok"] and outcome.get("total_tasks", 0) > 0
                    and outcome.get("completed_tasks") == outcome["total_tasks"]):
                return 0
            delay = options["interval_seconds"] if outcome["ok"] else min(
                options["interval_seconds"], 15 * 2 ** min(failures - 1, 6))
            time.sleep(delay)
    finally:
        os.close(lock_fd)


def start_monitor(config_path: str) -> int:
    """Start at most one detached login-side monitor; inherited flock closes races."""
    path = Path(config_path).resolve()
    config = _read_json(path)
    config["_config_path"] = str(path)
    options = _settings(config)
    directory = options["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(directory / "monitor.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock_fd)
        return int(_read_json(directory / "monitor.json", {}).get("pid", 0))
    try:
        with (directory / "monitor.log").open("ab", buffering=0) as log:
            process = subprocess.Popen(
                [sys.executable, "-u", str(Path(__file__).resolve()), "monitor", "--config", str(path),
                 "--lock-fd", str(lock_fd)], stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=True, close_fds=True, pass_fds=(lock_fd,))
        _atomic_json(directory / "monitor.json", {"pid": process.pid, "host": socket.gethostname(),
                                                   "started_at": utc_now()})
        return process.pid
    finally:
        os.close(lock_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["authorize", "monitor"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.command == "monitor":
        return monitor(args.config, args.lock_fd, args.once)
    config = _read_json(Path(args.config))
    config["_config_path"] = str(Path(args.config).resolve())
    receipt = ensure_authorized(config)
    print(json.dumps({"authorized": True, "repository": receipt["repository"],
                      "account": receipt.get("account")}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SyncError as error:
        print(str(error), file=sys.stderr, flush=True)
        raise SystemExit(2)
