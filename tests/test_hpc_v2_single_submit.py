import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"
spec = importlib.util.spec_from_file_location("single_submit", ROOT / "single_pool/submit.py")
single = importlib.util.module_from_spec(spec)
spec.loader.exec_module(single)

QOS = ("sbatch: error: QOSMaxSubmitJobPerUserLimit\n"
       "sbatch: error: Batch job submission failed: Job violates accounting/QOS policy "
       "(job submit limit, user's size and/or time limits)")


def reply(code=0, out="", err=""):
    return SimpleNamespace(returncode=code, stdout=out, stderr=err)


@pytest.fixture
def config(tmp_path, monkeypatch):
    tasks = [{"task_id": "task-" + str(i), "family": "eegnet"} for i in range(24)]
    (tmp_path / "tasks.json").write_text(json.dumps(tasks))
    cfg = {"experiment_id": "synthetic-single-pool", "project_dir": str(tmp_path),
           "output_root": str(tmp_path / "output"), "data_root": str(tmp_path / "inputs"),
           "tasks_file": str(tmp_path / "tasks.json"), "python": "/existing/venv/bin/python",
           "_config_path": str(tmp_path / "config.json"),
           "slurm": {"account": "zhuziyuan", "partition": "hpc_gpu", "gres": "gpu:1",
                     "cpus_per_task": 16, "mem": "128G", "pool_workers": 2, "exclude": ""}}
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    monkeypatch.setattr(single, "prepare_once", lambda *a, **k: {"software_validation_only": True})
    monkeypatch.setattr(single, "ensure_authorized", lambda *a, **k: {"authorized": True})
    monkeypatch.setattr(single, "_monitor_start", lambda *a, **k: (123, None))
    return cfg


def ledger_path(config):
    path = Path(config["output_root"]) / ".runtime/submissions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_all_24_tasks_use_one_allocation_not_an_array(config):
    calls = []

    def runner(args):
        calls.append(args)
        return reply() if args[0] == "squeue" else reply(out="12345;cluster\n")

    result = single.submit(config, runner=runner)
    commands = [c for c in calls if c[0] == "sbatch"]
    assert len(commands) == 1
    cmd = commands[0]
    assert not any(a.startswith("--array") for a in cmd)
    for value in ("--nodes=1", "--ntasks=1", "--gres=gpu:2", "--cpus-per-task=32",
                  "--mem=256G", "--partition=hpc_gpu", "--signal=B:USR1@180"):
        assert value in cmd
    assert not any(a.startswith("--exclude") for a in cmd)
    assert result["slurm_jobs_submitted"] == 1
    assert result["submitted_indices"] == list(range(24))
    assert cmd[-1] == ",".join(str(i) for i in range(24))
    stored = json.loads(ledger_path(config).read_text())["batches"][0]
    assert stored["command"] == cmd and stored["job_id"] == "12345"


def test_latest_allocation_is_one_job_two_gpus_36_cpus_128g(config):
    science_key = single.preparation_key(config)
    config["slurm"].update(cpus_per_task=18, mem="64G", pool_workers=2)
    calls = []

    def runner(args):
        calls.append(args)
        assert args[0] in ("squeue", "sbatch"), "submission invoked an unexpected process"
        return reply() if args[0] == "squeue" else reply(out="31415\n")

    result = single.submit(config, runner=runner)
    commands = [args for args in calls if args[0] == "sbatch"]
    assert len(commands) == 1
    assert result["slurm_jobs_submitted"] == 1
    assert result["submitted_indices"] == list(range(24))
    assert not any(arg.startswith("--array") for arg in commands[0])
    for value in ("--nodes=1", "--ntasks=1", "--gres=gpu:2", "--cpus-per-task=36", "--mem=128G"):
        assert value in commands[0]
    assert single.preparation_key(config) == science_key


def test_gpu1_one_node_two_gpus_total_24_cpus_and_128g(config):
    before = single.preparation_key(config)
    config["slurm"].update(partition="hpc_gpu1", cpus_per_task=12, mem="64G", pool_workers=2)
    commands = []

    def runner(args):
        commands.append(args)
        return reply() if args[0] == "squeue" else reply(out="99124\n")

    result = single.submit(config, runner=runner)
    batches = [args for args in commands if args[0] == "sbatch"]
    assert len(batches) == result["slurm_jobs_submitted"] == 1
    assert all(v in batches[0] for v in ("--nodes=1", "--ntasks=1", "--partition=hpc_gpu1",
                                         "--gres=gpu:2", "--cpus-per-task=24", "--mem=128G"))
    assert not any(v.startswith("--array=") for v in batches[0])
    assert single.preparation_key(config) == before


def test_memory_refusal_is_preserved_before_one_later_manual_submission(config):
    memory_error = ("sbatch: error: Memory specification can not be satisfied\n"
                    "sbatch: error: Batch job submission failed: Requested node configuration is not available\n")
    calls = []
    submission_count = 0

    def runner(args):
        nonlocal submission_count
        calls.append(args)
        assert args[0] in ("squeue", "sbatch"), "submission invoked a scientific worker"
        if args[0] == "squeue":
            return reply()
        submission_count += 1
        return reply(1, err=memory_error) if submission_count == 1 else reply(out="27182\n")

    with pytest.raises(RuntimeError, match="Memory specification can not be satisfied"):
        single.submit(config, runner=runner)
    assert submission_count == 1
    first = json.loads(ledger_path(config).read_text())["batches"][0]
    assert first["status"] == "rejected_before_acceptance"
    assert first["resolved_terminal"] and first["job_id"] is None
    assert first["stderr"] == memory_error
    assert "--mem=256G" in first["command"]
    assert not (Path(config["output_root"]) / "tasks").exists()

    config["slurm"].update(cpus_per_task=18, mem="64G", pool_workers=2)
    result = single.submit(config, runner=runner)
    assert result["job_id"] == "27182"
    assert submission_count == 2
    ledger = json.loads(ledger_path(config).read_text())
    assert len(ledger["batches"]) == 2
    assert ledger["batches"][0] == first
    assert "--mem=128G" in ledger["batches"][1]["command"]
    assert ledger["batches"][1]["status"] == "submitted"
    assert [args[0] for args in calls] == ["squeue", "sbatch", "squeue", "sbatch"]
    assert not (Path(config["output_root"]) / "tasks").exists()


def test_exact_prior_qos_refusal_is_resolved_without_erasing_original(config):
    path = ledger_path(config)
    original_batch = {"status": "submission_reply_uncertain", "job_id": None,
                      "returncode": 1, "stderr": QOS, "command": ["sbatch", "--array=0-23%2"]}
    original = json.dumps({"experiment_id": config["experiment_id"], "batches": [original_batch]},
                          separators=(",", ":")).encode()
    path.write_bytes(original)
    calls = []

    def runner(args):
        calls.append(args)
        return reply() if args[0] == "squeue" else reply(out="8899\n")

    result = single.submit(config, runner=runner)
    assert result["job_id"] == "8899"
    ledger = json.loads(path.read_text())
    old = ledger["batches"][0]
    assert all(old[k] == value for k, value in original_batch.items())
    assert old["resolved_terminal"]
    resolution = old["resolution_history"][0]
    assert Path(resolution["prior_ledger_backup"]).read_bytes() == original
    assert resolution["prior_ledger_sha256"] == hashlib.sha256(original).hexdigest()
    assert len([c for c in calls if c[0] == "sbatch"]) == 1


def test_unknown_prior_reply_remains_blocked_and_byte_identical(config):
    path = ledger_path(config)
    old = {"experiment_id": config["experiment_id"], "batches": [
        {"status": "submission_reply_uncertain", "job_id": None, "exception_type": "TimeoutExpired"}]}
    before = json.dumps(old).encode()
    path.write_bytes(before)
    calls = []

    def runner(args):
        calls.append(args)
        return reply()

    with pytest.raises(RuntimeError, match="no explicit scheduler refusal"):
        single.submit(config, runner=runner)
    assert path.read_bytes() == before
    assert [c[0] for c in calls] == ["squeue"]
    assert not list(path.parent.glob("submissions.before-*"))


def test_new_qos_failure_is_recorded_once_as_not_accepted(config):
    calls = []

    def runner(args):
        calls.append(args)
        return reply() if args[0] == "squeue" else reply(1, err=QOS)

    with pytest.raises(RuntimeError, match="still has no submission slot"):
        single.submit(config, runner=runner)
    assert len([c for c in calls if c[0] == "sbatch"]) == 1
    batch = json.loads(ledger_path(config).read_text())["batches"][0]
    assert batch["status"] == "rejected_before_acceptance"
    assert batch["resolved_terminal"] and batch["stderr"] == QOS
    assert batch["job_id"] is None


def test_active_array_or_pool_prevents_another_job(config):
    prefix = single._safe_slug(config["experiment_id"]) + "-" + hashlib.sha256(
        str(Path(config["output_root"]).resolve()).encode()).hexdigest()[:8]
    calls = []

    def runner(args):
        calls.append(args)
        return reply(out="99|" + prefix + "-old|RUNNING\n")

    result = single.submit(config, runner=runner)
    assert result["status"] == "already_active"
    assert [c[0] for c in calls] == ["squeue"]


def test_all_completed_tasks_skip_slurm_and_authorization(config, monkeypatch):
    output = Path(config["output_root"])
    for task in single.load_tasks(config):
        destination = output / "tasks" / task["task_id"] / "complete.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"task_id": task["task_id"], "identity": "synthetic-complete"}))
    monkeypatch.setattr(single, "ensure_authorized", lambda *a, **k: pytest.fail("completed work was reauthorized"))
    result = single.submit(config, runner=lambda *a: pytest.fail("completed work called Slurm"))
    assert result["status"] == "already_complete" and result["completed"] == 24


def test_dry_run_calls_neither_scheduler_nor_auth_and_preserves_identity(config, monkeypatch):
    runtime = dict(config)
    runtime["slurm"] = config["slurm"] | {"submission_mode": "single_pool", "pool_workers": 2}
    assert single.preparation_key(runtime) == single.preparation_key(config)
    monkeypatch.setattr(single, "ensure_authorized", lambda *a, **k: pytest.fail("dry run authorized"))
    result = single.submit(runtime, dry_run=True, runner=lambda *a: pytest.fail("dry run called Slurm"))
    assert result["slurm_jobs_to_submit"] == 1
    assert result["remaining_indices"] == list(range(24))
    assert not ledger_path(config).is_file()


def test_completed_subset_is_not_dispatched_again(config):
    task = single.load_tasks(config)[0]
    destination = Path(config["output_root"]) / "tasks" / task["task_id"] / "complete.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"task_id": task["task_id"], "identity": "synthetic-complete"}))
    result = single.submit(config, dry_run=True, runner=lambda *a: pytest.fail("dry run scheduler"))
    assert result["remaining_indices"] == list(range(1, 24))


def test_existing_prepared_science_change_is_not_bypassed(config):
    prepared = Path(config["output_root"]) / ".runtime/prepared.json"
    prepared.parent.mkdir(parents=True, exist_ok=True)
    prepared.write_text(json.dumps({"preparation_key": "different-science"}))
    with pytest.raises(RuntimeError, match="Scientific task/input identity changed"):
        single.submit(config, dry_run=True)


def test_versioned_deployed_entry_runs_cpu_dry_run_without_slurm(tmp_path):
    import numpy as np
    project = tmp_path / "project"
    package = project / "hpc_recalibration"
    package.mkdir(parents=True)
    for name in ("__init__.py", "preflight.py", "slurm.py", "github_sync.py", "data.py"):
        shutil.copyfile(ROOT / "hpc_recalibration" / name, package / name)
    inputs = project / "inputs"
    inputs.mkdir()
    for role in ("train", "validation", "support", "query"):
        np.savez(inputs / (role + ".npz"), x=np.ones((2, 3, 32), dtype=np.float32),
                 y=np.array([0, 1]), trial_id=np.array([role + "0", role + "1"]),
                 run_id=np.array([role, role]))
    tasks = [{"task_id": "synthetic-one", "synthetic": True,
              "source_train": "train.npz", "source_validation": "validation.npz",
              "targets": [{"session": "target", "support": "support.npz", "query": "query.npz"}]}]
    tasks_file = project / "tasks.json"
    tasks_file.write_text(json.dumps(tasks))
    config = {"experiment_id": "synthetic-deployed-check", "project_dir": str(project),
              "output_root": str(project / "outputs"), "data_root": str(inputs),
              "tasks_file": str(tasks_file), "python": sys.executable,
              "slurm": {"partition": "hpc_gpu", "cpus_per_task": 16, "mem": "128G", "pool_workers": 2}}
    config_file = project / "config.json"
    config_file.write_text(json.dumps(config))
    runtime = project / ".hpc_runtime" / "fixed-revision"
    runtime.mkdir(parents=True)
    shutil.copyfile(ROOT / "single_pool/submit.py", runtime / "submit.py")
    result = subprocess.run([sys.executable, "-u", str(runtime / "submit.py"), "--config", str(config_file),
                             "--dry-run"], text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert '"status": "dry_run"' in result.stdout
    assert '"--gres=gpu:2"' in result.stdout
    assert '"--array=' not in result.stdout
    assert not (project / "outputs/.runtime/submissions.json").exists()


@pytest.mark.parametrize("batch", [
    {"job_id": "123", "returncode": 1, "stderr": QOS},
    {"job_id": None, "returncode": 0, "stderr": QOS},
    {"job_id": None, "returncode": -9, "stderr": QOS},
    {"job_id": None, "returncode": 1, "stdout": "987654\n", "stderr": QOS},
    {"job_id": None, "returncode": 1, "stderr": "connection lost"},
    {"job_id": None, "returncode": 1, "stderr": "sbatch: error: Batch job submission failed: Socket timed out on send/recv operation"},
    {"job_id": None, "returncode": 1, "stderr": "sbatch: error: QOSMaxSubmitJobPerUserLimit"},
])
def test_incomplete_or_conflicting_refusal_evidence_is_not_inferred(batch):
    assert single.explicit_rejection_reason(batch) is None


def test_complete_generic_accounting_policy_refusal_is_recognized():
    batch = {"job_id": None, "returncode": 1, "stdout": "",
             "stderr": "sbatch: error: Batch job submission failed: Job violates accounting/QOS policy (user's size and/or time limits)"}
    assert single.explicit_rejection_reason(batch) == "explicit Slurm refusal: accounting/qos policy"
