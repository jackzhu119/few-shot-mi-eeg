"""Software-only checks for selecting the current job instead of a stale ID."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"
spec = importlib.util.spec_from_file_location("hpc_auto_switch", ROOT / "single_pool/switch.py")
switch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(switch)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    tasks = tmp_path / "tasks.json"
    tasks.write_text(json.dumps([{"task_id": "synthetic-auto-task", "synthetic": True}]))
    old = {"experiment_id": "synthetic-auto-migration", "project_dir": str(tmp_path),
           "output_root": str(tmp_path / "output"), "data_root": str(tmp_path / "data"),
           "tasks_file": str(tasks), "python": "/existing/python",
           "slurm": {"partition": "hpc_gpu1", "cpus_per_task": 16,
                     "mem": "64G", "pool_workers": 2, "gres": "gpu:1"}}
    old_path = tmp_path / "old32.json"
    old_path.write_text(json.dumps(old))
    target = old | {"slurm": old["slurm"] | {"cpus_per_task": 12}}
    target_path = tmp_path / "target24.json"
    target_path.write_text(json.dumps(target))
    config = switch.load_config(target_path)
    runtime = tmp_path / "output/.runtime"
    runtime.mkdir(parents=True)
    prefix = switch._safe_slug(config["experiment_id"]) + "-" + hashlib.sha256(
        str(Path(config["output_root"]).resolve()).encode()).hexdigest()[:8]
    name = prefix + "-current"
    command = switch.pool_submit._pool_command(switch.load_config(old_path), [0], name)
    ledger = {"experiment_id": config["experiment_id"], "batches": [
        {"job_id": "771099", "name": name, "status": "submitted", "command": command}]}
    ledger_path = runtime / "submissions.json"
    ledger_path.write_text(json.dumps(ledger))
    monkeypatch.setattr(switch, "_monitor_start", lambda _: (456, None))
    return SimpleNamespace(config=config, old=old_path, runtime=runtime, name=name,
                           ledger=ledger, ledger_path=ledger_path)


class Scheduler:
    def __init__(self, setup, rows=None):
        self.events = []
        self.rows = rows if rows is not None else [("771099", setup.name, "PENDING")]

    def __call__(self, args):
        self.events.append(args)
        output = "" if args[0] != "squeue" else "".join("|".join(row) + "\n" for row in self.rows)
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    def authorize(self, _):
        self.events.append(["MANUAL_AUTHORIZATION"])


def test_auto_uses_current_recorded_job_and_original_config_not_stale_id(setup):
    scheduler = Scheduler(setup)
    old_science = switch.preparation_key(switch.load_config(setup.old))
    result = switch.migrate(setup.config, job_id="auto", runner=scheduler,
                            authorize=scheduler.authorize)
    assert result["status"] == "migrated_existing_job" and result["job_id"] == "771099"
    assert result["new_slurm_jobs_submitted"] == 0
    assert ["scontrol", "update", "JobId=771099", "Partition=hpc_gpu1",
            "NumCPUs=24", "CPUsPerTask=24"] in scheduler.events
    assert not any("771075" in str(row) or row[0] in ("scancel", "sbatch") for row in scheduler.events)
    assert json.loads(setup.old.read_text())["slurm"]["cpus_per_task"] == 12
    assert switch.preparation_key(switch.load_config(setup.old)) == old_science
    receipt = json.loads(next(setup.runtime.glob("migration-*.json")).read_text())
    assert receipt["from_config"] == str(setup.old)


def test_auto_already_matching24_core_job_is_not_interrupted_or_reauthorized(setup):
    setup.ledger["batches"][0]["command"] = switch.pool_submit._pool_command(setup.config, [0], setup.name)
    setup.ledger_path.write_text(json.dumps(setup.ledger))
    scheduler = Scheduler(setup, [("771099", setup.name, "RUNNING")])
    result = switch.migrate(setup.config, job_id="auto", runner=scheduler,
                            authorize=lambda _: pytest.fail("matching job prompted"))
    assert result["status"] == "already_matches_requested_resources"
    assert result["monitor_pid"] == 456
    assert [row[0] for row in scheduler.events] == ["squeue"]
    assert not list(setup.runtime.glob("migration-*.json"))


def test_auto_no_active_job_authorizes_before_single_existing_submission(setup, monkeypatch):
    scheduler = Scheduler(setup, [])
    def submit(config, *, runner):
        scheduler.events.append(["SUBMIT"])
        assert config["slurm"]["cpus_per_task"] == 12
        return {"status": "submitted", "job_id": "synthetic-new-job"}
    monkeypatch.setattr(switch.pool_submit, "submit", submit)
    result = switch.migrate(setup.config, job_id="auto", runner=scheduler,
                            authorize=scheduler.authorize)
    assert result["status"] == "submitted"
    assert scheduler.events[-2:] == [["MANUAL_AUTHORIZATION"], ["SUBMIT"]]


def test_auto_multiple_project_jobs_never_mutates_or_prompts(setup):
    scheduler = Scheduler(setup, [("771099", setup.name, "PENDING"),
                                  ("771100", setup.name + "-second", "RUNNING")])
    before = setup.old.read_bytes(), setup.ledger_path.read_bytes()
    with pytest.raises(RuntimeError, match="More than one project job"):
        switch.migrate(setup.config, job_id="auto", runner=scheduler,
                       authorize=lambda _: pytest.fail("ambiguous jobs prompted"))
    assert [row[0] for row in scheduler.events] == ["squeue"]
    assert before == (setup.old.read_bytes(), setup.ledger_path.read_bytes())


def test_auto_unrecorded_active_job_never_mutates_or_prompts(setup):
    setup.ledger["batches"] = []
    setup.ledger_path.write_text(json.dumps(setup.ledger))
    scheduler = Scheduler(setup)
    before = setup.old.read_bytes(), setup.ledger_path.read_bytes()
    with pytest.raises(RuntimeError, match="not uniquely recorded"):
        switch.migrate(setup.config, job_id="auto", runner=scheduler,
                       authorize=lambda _: pytest.fail("unrecorded job prompted"))
    assert [row[0] for row in scheduler.events] == ["squeue"]
    assert before == (setup.old.read_bytes(), setup.ledger_path.read_bytes())
