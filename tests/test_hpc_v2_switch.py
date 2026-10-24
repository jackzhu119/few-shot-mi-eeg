import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"
spec = importlib.util.spec_from_file_location("hpc_pool_switch", ROOT / "single_pool/switch.py")
switch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(switch)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    tasks = tmp_path / "tasks.json"
    tasks.write_text(json.dumps([{"task_id": "synthetic-task", "synthetic": True}]))
    old = {"experiment_id": "synthetic-migration", "project_dir": str(tmp_path),
           "output_root": str(tmp_path / "output"), "data_root": str(tmp_path / "data"),
           "tasks_file": str(tasks), "slurm": {"partition": "hpc_gpu", "cpus_per_task": 18,
                                                "mem": "64G", "pool_workers": 2},
           "git_sync": {"enabled": True, "repository": "test/repository", "branch": "research/test",
                        "status_prefix": "training_status/test", "token_file": str(tmp_path / "private-token")}}
    old_path = tmp_path / "old.json"
    old_path.write_text(json.dumps(old))
    target = old | {"slurm": old["slurm"] | {"partition": "hpc_gpu1", "cpus_per_task": 16}}
    target_path = tmp_path / "target.json"
    target_path.write_text(json.dumps(target))
    config = switch.load_config(target_path)
    runtime = tmp_path / "output/.runtime"
    runtime.mkdir(parents=True)
    prefix = switch._safe_slug(config["experiment_id"]) + "-" + hashlib.sha256(
        str(Path(config["output_root"]).resolve()).encode()).hexdigest()[:8]
    job_name = prefix + "-existing"
    ledger = {"experiment_id": config["experiment_id"], "batches": [
        {"job_id": "771075", "name": job_name, "status": "submitted"}]}
    (runtime / "submissions.json").write_text(json.dumps(ledger))
    monkeypatch.setattr(switch, "_monitor_start", lambda _: (123, None))
    return SimpleNamespace(config=config, old=old_path, runtime=runtime, job_name=job_name)


class Scheduler:
    def __init__(self, setup, state="PENDING", *, remain_running=False, accounting="CANCELLED", fail=None):
        self.setup, self.state = setup, state
        self.remain_running, self.accounting, self.fail = remain_running, accounting, fail
        self.events = []

    def __call__(self, args):
        self.events.append(args)
        if self.fail and args[:len(self.fail)] == self.fail:
            return SimpleNamespace(returncode=1, stdout="", stderr="synthetic scheduler refusal")
        text = ""
        if args[0] == "squeue" and self.state:
            text = "771075|" + self.setup.job_name + "|" + self.state + "\n"
        elif args[0] == "sacct":
            text = "771075|" + self.accounting + "|\n"
        elif args[0] == "scancel" and not self.remain_running:
            self.state = None
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    def authorize(self, _):
        self.events.append(["MANUAL_AUTHORIZATION"])


def receipts(setup):
    return [json.loads(p.read_text()) for p in setup.runtime.glob("migration-*.json")]


def test_pending_job_held_then_manual_authorized_updated_and_released(setup):
    scheduler = Scheduler(setup)
    original = setup.old.read_bytes()
    result = switch.migrate(setup.config, from_config=setup.old, job_id="771075",
                            runner=scheduler, authorize=scheduler.authorize)
    assert result["status"] == "migrated_existing_job"
    assert result["new_slurm_jobs_submitted"] == 0
    ops = [r for r in scheduler.events if r[0] not in ("squeue", "sacct")]
    assert ops == [["scontrol", "hold", "771075"], ["MANUAL_AUTHORIZATION"],
                   ["scontrol", "update", "JobId=771075", "Partition=hpc_gpu1", "NumCPUs=32", "CPUsPerTask=32"],
                   ["scontrol", "release", "771075"]]
    effective = json.loads(setup.old.read_text())
    assert effective["slurm"]["cpus_per_task"] == 16
    assert effective["slurm"]["mem"] == "64G"
    assert switch.preparation_key(switch.load_config(setup.old)) == switch.preparation_key(setup.config)
    receipt = receipts(setup)[0]
    assert Path(receipt["original_config_backup"]).read_bytes() == original
    assert not any(r[0] == "sbatch" for r in scheduler.events)


def test_failed_update_keeps_job_held_and_original_config(setup):
    scheduler = Scheduler(setup, fail=["scontrol", "update"])
    before = setup.old.read_bytes()
    with pytest.raises(RuntimeError, match="Scheduler command failed"):
        switch.migrate(setup.config, from_config=setup.old, job_id="771075",
                       runner=scheduler, authorize=scheduler.authorize)
    assert setup.old.read_bytes() == before
    assert ["scontrol", "release", "771075"] not in scheduler.events
    assert not any(r[0] in ("sbatch", "scancel") for r in scheduler.events)
    assert receipts(setup)[0]["status"] == "failed_preserved"


def test_repeated_explicit_migration_never_interrupts_already_migrated_running_job(setup):
    scheduler = Scheduler(setup)
    first = switch.migrate(setup.config, from_config=setup.old, job_id="771075",
                           runner=scheduler, authorize=scheduler.authorize)
    assert first["status"] == "migrated_existing_job"
    scheduler.state = "RUNNING"
    scheduler.events.clear()
    repeated = switch.migrate(setup.config, from_config=setup.old, job_id="771075", runner=scheduler,
                              authorize=lambda _: pytest.fail("already migrated job prompted again"))
    assert repeated["status"] == "already_migrated"
    assert repeated["monitor_pid"] == 123
    assert [r[0] for r in scheduler.events] == ["squeue"]


def test_authorization_failure_never_updates_releases_or_submits(setup):
    scheduler = Scheduler(setup)

    def fail(_):
        raise switch.SyncError("synthetic authorization failure", 403)

    with pytest.raises(switch.SyncError):
        switch.migrate(setup.config, from_config=setup.old, job_id="771075", runner=scheduler, authorize=fail)
    assert not any(r[0] == "sbatch" or r[:2] in (["scontrol", "update"], ["scontrol", "release"])
                   for r in scheduler.events)
    assert receipts(setup)[0]["status"] == "failed_preserved"


def test_pending_race_stops_before_prompt_and_config_change(setup):
    scheduler = Scheduler(setup)
    before = setup.old.read_bytes()

    def runner(args):
        result = scheduler(args)
        if args[:2] == ["scontrol", "hold"]:
            scheduler.state = "RUNNING"
        return result

    with pytest.raises(RuntimeError, match="did not remain PENDING"):
        switch.migrate(setup.config, from_config=setup.old, job_id="771075", runner=runner,
                       authorize=lambda _: pytest.fail("raced job prompted"))
    assert setup.old.read_bytes() == before
    assert not any(r[0] == "scancel" for r in scheduler.events)


def test_running_saves_with_term_and_only_resumes_after_terminal_accounting(setup, monkeypatch):
    scheduler = Scheduler(setup, state="RUNNING")
    before = setup.old.read_bytes()

    def submit(config, *, runner):
        scheduler.events.append(["RESUME_SUBMIT"])
        assert config["slurm"]["partition"] == "hpc_gpu1"
        return {"status": "submitted", "job_id": "new-synthetic-job"}

    monkeypatch.setattr(switch.pool_submit, "submit", submit)
    result = switch.migrate(setup.config, from_config=setup.old, job_id="771075",
                            runner=scheduler, authorize=scheduler.authorize)
    assert result["previous_job_id"] == "771075"
    assert ["scancel", "--signal=TERM", "--batch", "771075"] in scheduler.events
    assert scheduler.events.index(["MANUAL_AUTHORIZATION"]) < scheduler.events.index(["RESUME_SUBMIT"])
    assert setup.old.read_bytes() == before
    assert not any("KILL" in str(r) or "USR1" in str(r) for r in scheduler.events)
    assert receipts(setup)[0]["status"] == "resumed_after_migration"


def test_running_timeout_preserves_field_and_never_submits(setup, monkeypatch):
    scheduler = Scheduler(setup, state="RUNNING", remain_running=True)
    monkeypatch.setattr(switch.pool_submit, "submit", lambda *a, **k: pytest.fail("still running job resubmitted"))
    now = [0]
    result = switch.migrate(setup.config, from_config=setup.old, job_id="771075", runner=scheduler,
                            authorize=lambda _: pytest.fail("still running job prompted"),
                            clock=lambda: now[0], sleep=lambda _: now.__setitem__(0, now[0] + 50))
    assert result["status"] == "waiting_for_checkpoint_exit"
    assert len([r for r in scheduler.events if r[0] == "scancel"]) == 1


def test_queue_gone_without_terminal_accounting_does_not_resume(setup, monkeypatch):
    scheduler = Scheduler(setup, state=None, accounting="RUNNING")
    monkeypatch.setattr(switch.pool_submit, "submit", lambda *a, **k: pytest.fail("missing accounting resubmitted"))
    result = switch.migrate(setup.config, from_config=setup.old, job_id="771075", runner=scheduler,
                            authorize=lambda _: pytest.fail("missing accounting prompted"))
    assert result["status"] == "waiting_for_terminal_accounting"
    assert not any(r[0] in ("scancel", "scontrol", "sbatch") for r in scheduler.events)


def test_no_job_normal_resume_never_duplicates_active_queue(setup, monkeypatch):
    scheduler = Scheduler(setup, state="RUNNING")
    monkeypatch.setattr(switch.pool_submit, "submit", lambda *a, **k: pytest.fail("active duplicate"))
    result = switch.migrate(setup.config, runner=scheduler,
                            authorize=lambda _: pytest.fail("active job prompted"))
    assert result["status"] == "already_active"
    assert result["monitor_pid"] == 123
    assert [r[0] for r in scheduler.events] == ["squeue"]


def test_no_job_new_submission_requires_manual_auth_before_existing_submit(setup, monkeypatch):
    scheduler = Scheduler(setup, state=None)
    monkeypatch.setattr(switch.pool_submit, "submit", lambda *a, **k: scheduler.events.append(["SUBMIT"]) or {"status": "submitted"})
    result = switch.migrate(setup.config, runner=scheduler, authorize=scheduler.authorize)
    assert result["status"] == "submitted"
    assert scheduler.events[-2:] == [["MANUAL_AUTHORIZATION"], ["SUBMIT"]]


def test_unrecorded_job_never_runs_scheduler_mutation(setup):
    scheduler = Scheduler(setup)
    with pytest.raises(RuntimeError, match="not uniquely recorded"):
        switch.migrate(setup.config, from_config=setup.old, job_id="999", runner=scheduler,
                       authorize=lambda _: pytest.fail("wrong job prompted"))
    assert scheduler.events == []


def test_real_manual_entry_probes_before_replacing_old_secret_and_ignores_cache(setup):
    options = switch._settings(setup.config)
    token_path = options["token_file"]
    token_path.write_text("synthetic-old-token")
    options["directory"].mkdir(parents=True)
    (options["directory"] / "authorization.json").write_text('{"valid_cached_receipt": true}')
    events = []

    class Client:
        def __init__(self, token, repository, branch):
            assert token == "synthetic-new-token"

        def request(self, method, path):
            events.append(path)
            assert token_path.read_text() == "synthetic-old-token"
            return {"login": "synthetic-author"} if path == "/user" else {"permissions": {"push": True}}

        def put_status(self, path, payload):
            events.append(path)
            assert "no fit started" not in payload["purpose"].lower()
            assert token_path.read_text() == "synthetic-old-token"
            return {"commit": {"sha": "synthetic-probe-commit"}}

    result = switch.prompt_authorization(setup.config, tty=lambda: True,
                                         prompt=lambda _: events.append("PROMPT") or "synthetic-new-token",
                                         client_factory=Client)
    assert events[0] == "PROMPT" and len(events) == 4
    assert token_path.read_text() == "synthetic-new-token\n"
    assert token_path.stat().st_mode & 0o777 == 0o600
    assert result["write_probe_passed"] and result["manual_entry_required_and_completed"]
    assert "synthetic-new-token" not in json.dumps(result)
    assert "synthetic-old-token" not in json.dumps(result)


def test_failed_actual_write_probe_preserves_previous_secret(setup):
    token_path = switch._settings(setup.config)["token_file"]
    token_path.write_text("synthetic-old-token")

    class Client:
        def __init__(self, *args):
            pass

        def request(self, *args):
            return {}

        def put_status(self, *args):
            raise switch.SyncError("synthetic write rejection", 403)

    with pytest.raises(switch.SyncError):
        switch.prompt_authorization(setup.config, tty=lambda: True, prompt=lambda _: "synthetic-rejected", client_factory=Client)
    assert token_path.read_text() == "synthetic-old-token"


def test_noninteractive_input_never_falls_back_to_echoed_secret(setup):
    with pytest.raises(switch.SyncError, match="interactive terminal"):
        switch.prompt_authorization(setup.config, tty=lambda: False,
                                     prompt=lambda _: pytest.fail("echo fallback attempted"))
