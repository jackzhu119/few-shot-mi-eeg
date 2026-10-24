"""Move the existing school queue and require a fresh hidden GitHub authorization."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback


def _imports():
    if __name__ == "__main__":
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config", required=True)
        args, _ = parser.parse_known_args()
        raw = json.loads(Path(args.config).expanduser().read_text())
        sys.path.insert(0, str(Path(raw["project_dir"]).expanduser().resolve()))
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_imports()
from hpc_recalibration.github_sync import (  # noqa: E402
    GitHubClient, SyncError, _credential_stat, _settings, _store_token,
)
from hpc_recalibration.preflight import (  # noqa: E402
    atomic_json, file_lock, load_config, load_tasks, preparation_key, utc_now,
)
from hpc_recalibration.slurm import (  # noqa: E402
    TERMINAL, _complete, _monitor_start, _safe_slug, accounting_states, queue_entries, run_command,
)

_spec = importlib.util.spec_from_file_location("paper2_pool_submit", Path(__file__).with_name("submit.py"))
pool_submit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pool_submit)


def prompt_authorization(config, *, prompt=None, tty=None, client_factory=None):
    """Always prompt, probe actual repository writes, then publish the private token."""
    if not (sys.stdin.isatty() if tty is None else tty()):
        raise SyncError("Run this command in the school interactive terminal to enter the GitHub token privately")
    options = _settings(config)
    token = (prompt or getpass.getpass)("GitHub token (hidden; repository Contents read/write): ").strip()
    if not token or any(c.isspace() or ord(c) < 32 for c in token):
        raise SyncError("No valid token entered; the queue was not released or submitted")
    client = (client_factory or GitHubClient)(token, options["repository"], options["branch"])
    identity = client.request("GET", "/user")
    repository = client.request("GET", "/repos/" + options["repository"])
    if repository.get("permissions", {}).get("push") is False:
        raise SyncError("The entered GitHub account cannot write to this repository", 403)
    probe = client.put_status(options["status_prefix"] + "/AUTHORIZATION.json", {
        "schema_version": 1, "authorized_at": utc_now(), "account": identity.get("login"),
        "experiment_id": config["experiment_id"],
        "purpose": "Fresh manual write authorization before releasing or resuming the existing training queue."})
    _store_token(options["token_file"], token)
    receipt = {"schema_version": 1, **{k: options[k] for k in ("repository", "branch", "status_prefix")},
               "account": identity.get("login"), "authorized_at": utc_now(),
               "authorized_unix": time.time(), "credential_stat": _credential_stat(options["token_file"]),
               "write_probe_commit": probe.get("commit", {}).get("sha"),
               "write_probe_passed": True, "manual_entry_required_and_completed": True,
               "token_value_or_hash_recorded": False}
    atomic_json(options["directory"] / "authorization.json", receipt)
    return receipt


def migrate(config, *, from_config=None, job_id=None, runner=run_command,
            authorize=prompt_authorization, sleep=time.sleep, clock=time.monotonic):
    output = Path(config["output_root"])
    runtime = output / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    prefix = _safe_slug(config["experiment_id"]) + "-" + hashlib.sha256(str(output.resolve()).encode()).hexdigest()[:8]
    user = config.get("slurm", {}).get("user", "zhuziyuan")
    with file_lock(runtime / "migration.lock"):
        if job_id == "auto":
            active = [r for r in queue_entries(user, runner)
                      if r["name"].startswith(prefix) and r["state"] not in TERMINAL]
            if len(active) > 1:
                raise RuntimeError("More than one project job is active; no job was changed")
            job_id = active[0]["id"] if active else None
        if job_id and from_config is None:
            recorded = json.loads((runtime / "submissions.json").read_text())
            matches = [r for r in recorded["batches"] if str(r.get("job_id")) == str(job_id)]
            if (recorded.get("experiment_id") != config["experiment_id"] or len(matches) != 1
                    or not matches[0]["name"].startswith(prefix)):
                raise RuntimeError("The active job is not uniquely recorded for this project")
            command = matches[0].get("command", [])
            expected = pool_submit._pool_command(config, [], "resource-comparison")
            resource_prefixes = ("--nodes=", "--ntasks=", "--partition=", "--gres=", "--cpus-per-task=", "--mem=")
            if all(value in command for value in expected if value.startswith(resource_prefixes)):
                monitor, warning = _monitor_start(config)
                return {"status": "already_matches_requested_resources", "job_id": str(job_id),
                        "monitor_pid": monitor, "monitor_warning": warning,
                        "new_slurm_jobs_submitted": 0}
            if len(command) < 4 or Path(command[-4]).name != "job.sh":
                raise RuntimeError("The existing batch configuration cannot be identified; no job was changed")
            from_config = command[-3]
        if not job_id:
            active = [r for r in queue_entries(user, runner) if r["name"].startswith(prefix) and r["state"] not in TERMINAL]
            if active:
                monitor, warning = _monitor_start(config)
                return {"status": "already_active", "active_jobs": active,
                        "monitor_pid": monitor, "monitor_warning": warning,
                        "note": "No new job or token prompt; use --job-id to request a partition migration"}
            if all(_complete(output, task) for task in load_tasks(config)):
                return {"status": "already_complete", "submitted_indices": []}
            authorize(config)
            return pool_submit.submit(config, runner=runner)
        if not str(job_id).isdigit() or from_config is None:
            raise ValueError("Migration requires a numeric --job-id and its existing --from-config")
        old = load_config(from_config)
        if (old["output_root"] != config["output_root"] or old["project_dir"] != config["project_dir"]
                or preparation_key(old) != preparation_key(config)):
            raise RuntimeError("Migration changes the saved scientific queue or output identity")
        ledger = json.loads((runtime / "submissions.json").read_text())
        batches = [r for r in ledger["batches"] if str(r.get("job_id")) == str(job_id)]
        if (ledger.get("experiment_id") != config["experiment_id"] or len(batches) != 1
                or not batches[0]["name"].startswith(prefix)):
            raise RuntimeError("The requested job is not uniquely recorded for this project")
        receipt_path = runtime / ("migration-" + str(job_id) + "-" + str(time.time_ns()) + ".json")
        target_hash = hashlib.sha256(json.dumps({k: v for k, v in config.items() if k != "_config_path"},
                                               sort_keys=True).encode()).hexdigest()
        receipt = {"job_id": str(job_id), "started_at": utc_now(), "events": [], "status": "checking",
                   "from_config": str(Path(from_config).resolve()), "target_config": config["_config_path"],
                   "target_configuration_sha256": target_hash}

        def save(status, **fields):
            receipt.update(status=status, observed_at=utc_now(), **fields)
            atomic_json(receipt_path, receipt)

        def call(args):
            receipt["events"].append({"command": args, "started_at": utc_now()})
            save("scheduler_operation")
            result = runner(args)
            receipt["events"][-1].update(returncode=result.returncode, stdout=result.stdout,
                                          stderr=result.stderr, ended_at=utc_now())
            save("scheduler_operation")
            return result

        def required(args):
            result = call(args)
            if result.returncode:
                raise RuntimeError("Scheduler command failed; no replacement job submitted: " + result.stderr.strip())

        def observe():
            rows = [r for r in queue_entries(user, call) if r["id"] == str(job_id)]
            if len(rows) > 1 or (rows and rows[0]["name"] != batches[0]["name"]):
                raise RuntimeError("Requested scheduler job identity differs from its project ledger")
            return rows[0] if rows else None

        try:
            save("checking")
            current = observe()
            if current and current["state"] not in TERMINAL:
                for previous_path in sorted(runtime.glob("migration-" + str(job_id) + "-*.json")):
                    previous = json.loads(previous_path.read_text())
                    if (previous.get("status") == "migrated_existing_job"
                            and previous.get("job_id") == str(job_id)
                            and previous.get("target_config") == config["_config_path"]
                            and previous.get("target_configuration_sha256") == target_hash
                            and any(event.get("command") == ["scontrol", "release", str(job_id)]
                                    and event.get("returncode") == 0 for event in previous.get("events", []))):
                        monitor, warning = _monitor_start(config)
                        save("already_migrated", previous_migration_receipt=str(previous_path))
                        return {"status": "already_migrated", "job_id": str(job_id),
                                "monitor_pid": monitor, "monitor_warning": warning,
                                "receipt": str(receipt_path), "new_slurm_jobs_submitted": 0}
            if current and current["state"] == "PENDING":
                required(["scontrol", "hold", str(job_id)])
                current = observe()
                if current is None or current["state"] != "PENDING":
                    raise RuntimeError("Job did not remain PENDING after hold; no resource/configuration change made")
                save("held_awaiting_manual_authorization")
                authorize(config)
                settings = config["slurm"]
                total_cores = str(int(settings["cpus_per_task"]) * int(settings["pool_workers"]))
                required(["scontrol", "update", "JobId=" + str(job_id), "Partition=" + settings["partition"],
                          "NumCPUs=" + total_cores, "CPUsPerTask=" + total_cores])
                source = Path(from_config).resolve()
                original = source.read_bytes()
                backup = source.with_name(source.name + ".before-migration-" + hashlib.sha256(original).hexdigest()[:16])
                if backup.exists() and backup.read_bytes() != original:
                    raise RuntimeError("Existing migration backup differs; job remains held")
                if not backup.exists():
                    pool_submit._atomic_bytes(backup, original)
                atomic_json(source, {k: v for k, v in config.items() if k != "_config_path"})
                save("resources_changed_held", original_config_backup=str(backup),
                     original_config_sha256=hashlib.sha256(original).hexdigest())
                required(["scontrol", "release", str(job_id)])
                monitor, warning = _monitor_start(config)
                save("migrated_existing_job", monitor_pid=monitor, monitor_warning=warning)
                return {"status": "migrated_existing_job", "job_id": str(job_id),
                        "new_slurm_jobs_submitted": 0, "receipt": str(receipt_path)}
            if current:
                if current["state"] != "RUNNING":
                    save("waiting_for_existing_job_state", scheduler_state=current["state"])
                    return {"status": receipt["status"], "job_id": str(job_id), "receipt": str(receipt_path)}
                save("checkpoint_pause_requested", note="TERM is forwarded for saving; never USR1, KILL or automatic requeue")
                required(["scancel", "--signal=TERM", "--batch", str(job_id)])
                deadline = clock() + 45
                while observe() is not None and clock() < deadline:
                    print(json.dumps({"status": "waiting_for_checkpoint_exit", "job_id": str(job_id), "utc": utc_now()}), flush=True)
                    sleep(2)
                if observe() is not None:
                    save("waiting_for_checkpoint_exit")
                    return {"status": receipt["status"], "job_id": str(job_id), "receipt": str(receipt_path)}
            states = accounting_states(job_id, call)
            if not states or any(state not in TERMINAL for state in states):
                save("waiting_for_terminal_accounting", accounting_states=states)
                return {"status": receipt["status"], "job_id": str(job_id), "receipt": str(receipt_path)}
            save("prior_job_terminal_awaiting_manual_authorization", accounting_states=states)
            authorize(config)
            result = pool_submit.submit(config, runner=call)
            save("resumed_after_migration", submission=result)
            return {**result, "migration_receipt": str(receipt_path), "previous_job_id": str(job_id)}
        except BaseException:
            save("failed_preserved", traceback=traceback.format_exc(),
                 note="No cleanup, KILL, automatic release or additional training attempt was made")
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--from-config")
    parser.add_argument("--job-id")
    args = parser.parse_args()
    result = migrate(load_config(args.config), from_config=args.from_config, job_id=args.job_id)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
