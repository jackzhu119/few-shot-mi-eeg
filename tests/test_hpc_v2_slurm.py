from pathlib import Path
import importlib
import json
import os
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"
sys.path.insert(0, str(PROJECT))
from hpc_recalibration import preflight, slurm  # noqa: E402


@pytest.fixture
def config(tmp_path, monkeypatch):
    tasks = [{"task_id": "first", "family": "eegnet"},
             {"task_id": "second", "family": "eegnet"}]
    (tmp_path / "tasks.json").write_text(json.dumps(tasks))
    value = {"experiment_id": "synthetic-controller-test", "project_dir": str(tmp_path),
             "output_root": str(tmp_path / "output"), "data_root": str(tmp_path / "inputs"),
             "tasks_file": str(tmp_path / "tasks.json"), "python": sys.executable,
             "_config_path": str(tmp_path / "config.json"), "slurm": {"array_parallel": 3}}
    (tmp_path / "config.json").write_text(json.dumps(value))
    monkeypatch.setattr(slurm, "prepare_once", lambda *args, **kwargs: {"software_validation_only": True})
    sync = importlib.import_module("hpc_recalibration.github_sync")
    monkeypatch.setattr(sync, "ensure_authorized", lambda *args, **kwargs: {"authorized": True})
    monkeypatch.setattr(sync, "start_monitor", lambda path: 1234)
    return value


def response(code=0, out="", err=""):
    return SimpleNamespace(returncode=code, stdout=out, stderr=err)


def test_submit_creates_logs_and_valid_single_gpu_array(config):
    calls = []
    def run(args):
        calls.append(args)
        if args[0] == "squeue":
            return response()
        assert (Path(config["output_root"]) / "logs").is_dir()
        return response(out="765432;cluster\n")
    result = slurm.submit(config, runner=run)
    command = calls[-1]
    assert result["job_id"] == "765432"
    assert "--array=0,1%3" in command
    assert "--gres=gpu:NVIDIAA100-SXM4-80GB:1" in command
    assert "--cpus-per-task=24" in command and "--mem=128G" in command
    assert "--time=5-03:00:00" in command
    assert "--signal=B:USR1@180" in command and "--exclude=gpu3" in command
    assert all(Path(arg.split("=", 1)[1]).is_absolute()
               for arg in command if arg.startswith(("--output=", "--error=")))


def test_repeated_launch_does_not_resubmit_active_array(config):
    first = slurm.submit(config, runner=lambda a: response(out="123\n") if a[0] == "sbatch" else response())
    ledger = json.loads((Path(config["output_root"]) / ".runtime/submissions.json").read_text())
    name = ledger["batches"][0]["name"]
    calls = []
    def run(args):
        calls.append(args)
        return response(out=f"123_0|{name}|RUNNING\n123_1|{name}|PENDING\n")
    result = slurm.submit(config, runner=run)
    assert first["status"] == "submitted" and result["status"] == "already_active"
    assert len(calls) == 1 and calls[0][0] == "squeue"


def test_active_resume_restarts_only_monitor_without_auth_or_submission(config, monkeypatch):
    slurm.submit(config, runner=lambda a: response(out="123\n") if a[0] == "sbatch" else response())
    ledger = json.loads((Path(config["output_root"]) / ".runtime/submissions.json").read_text())
    name = ledger["batches"][0]["name"]
    sync = importlib.import_module("hpc_recalibration.github_sync")
    monkeypatch.setattr(sync, "ensure_authorized", lambda *a, **k: pytest.fail("active work reauthorized"))
    starts = []
    monkeypatch.setattr(sync, "start_monitor", lambda path: starts.append(path) or 5678)
    result = slurm.submit(config, runner=lambda args: response(out=f"123_0|{name}|RUNNING\n"))
    assert result["status"] == "already_active" and result["monitor_pid"] == 5678
    assert starts == [config["_config_path"]]


def test_completed_skip_and_failed_only_manual_resume(config):
    slurm.submit(config, runner=lambda a: response(out="123\n") if a[0] == "sbatch" else response())
    done = Path(config["output_root"]) / "tasks/first/complete.json"
    done.parent.mkdir(parents=True)
    done.write_text(json.dumps({"task_id": "first", "identity": "synthetic"}))
    calls = []
    def run(args):
        calls.append(args)
        if args[0] == "sacct":
            return response(out="123_0|COMPLETED\n123_1|FAILED\n")
        return response(out="124\n") if args[0] == "sbatch" else response()
    result = slurm.submit(config, runner=run)
    assert result["submitted_indices"] == [1]
    assert "--array=1%3" in calls[-1]
    assert not any(a[0] == "scancel" for a in calls)


def test_squeue_failure_cannot_submit(config):
    calls = []
    def run(args):
        calls.append(args)
        return response(1, err="scheduler unreachable")
    with pytest.raises(RuntimeError, match="squeue failed"):
        slurm.submit(config, runner=run)
    assert len(calls) == 1


def test_unknown_accounting_does_not_duplicate(config):
    slurm.submit(config, runner=lambda a: response(out="123\n") if a[0] == "sbatch" else response())
    calls = []
    def run(args):
        calls.append(args)
        return response()
    result = slurm.submit(config, runner=run)
    assert result["status"] == "waiting_for_accounting"
    assert [x[0] for x in calls] == ["squeue", "sacct"]


def test_definite_scheduler_rejection_can_be_fixed_and_relaunched(config):
    def run(args):
        return response(1, err="Batch job submission failed: Invalid partition name") if args[0] == "sbatch" else response()
    with pytest.raises(RuntimeError, match="sbatch"):
        slurm.submit(config, runner=run)
    result = slurm.submit(config, runner=lambda a: response(out="124\n") if a[0] == "sbatch" else response())
    assert result["status"] == "submitted"


def test_ambiguous_sbatch_failure_preserves_intent_without_retry(config):
    def run(args):
        return response(1, err="Socket timed out") if args[0] == "sbatch" else response()
    with pytest.raises(RuntimeError, match="sbatch"):
        slurm.submit(config, runner=run)
    with pytest.raises(RuntimeError, match="uncertain"):
        slurm.submit(config, runner=lambda a: response())
    ledger = json.loads((Path(config["output_root"]) / ".runtime/submissions.json").read_text())
    assert len(ledger["batches"]) == 1


def test_auth_before_sbatch_and_monitor_failure_cannot_cancel_training(config, monkeypatch):
    sync = importlib.import_module("hpc_recalibration.github_sync")
    def fail(*args, **kwargs):
        raise RuntimeError("network unavailable")
    monkeypatch.setattr(sync, "ensure_authorized", fail)
    calls = []
    def run(args):
        calls.append(args)
        return response(out="124\n") if args[0] == "sbatch" else response()
    with pytest.raises(RuntimeError, match="network"):
        slurm.submit(config, runner=run)
    assert all(c[0] != "sbatch" for c in calls)
    monkeypatch.setattr(sync, "ensure_authorized", lambda *args, **kwargs: {})
    monkeypatch.setattr(sync, "start_monitor", fail)
    result = slurm.submit(config, runner=run)
    assert result["status"] == "submitted" and result["monitor_warning"]


def test_all_done_requires_no_scheduler_or_authorization(config):
    for name in ("first", "second"):
        path = Path(config["output_root"]) / "tasks" / name / "complete.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"task_id": name, "identity": "synthetic"}))
    assert slurm.submit(config, runner=lambda _: pytest.fail("scheduler called"))["status"] == "already_complete"


@pytest.mark.parametrize("sent_signal,expected_code,requeue", [(signal.SIGUSR1, 0, True), (signal.SIGTERM, 130, False)])
def test_real_bash_signal_forwarding_and_user_cancel(tmp_path, sent_signal, expected_code, requeue):
    (tmp_path / "job.sh").write_bytes((PROJECT / "job.sh").read_bytes())
    (tmp_path / "bootstrap.py").write_text('''import signal,time,sys
from pathlib import Path
root=Path(__file__).parent
def saved(code):
 root.joinpath("checkpoint_saved").write_text(str(code))
 raise SystemExit(code)
signal.signal(signal.SIGUSR1, lambda *_: saved(75))
signal.signal(signal.SIGTERM, lambda *_: saved(130))
root.joinpath("ready").write_text("ready")
while True: time.sleep(.01)
''')
    control = tmp_path / "scontrol"
    control.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "' + str(tmp_path / 'requeue') + '"\n')
    control.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               SLURM_JOB_ID="123", SLURM_ARRAY_JOB_ID="123", SLURM_ARRAY_TASK_ID="0")
    with (tmp_path / "shell.log").open("w") as log:
        process = subprocess.Popen(["bash", str(tmp_path / "job.sh"), "config.json", sys.executable],
                                   stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            until = time.monotonic() + 5
            while not (tmp_path / "ready").exists() and time.monotonic() < until:
                time.sleep(.02)
            assert (tmp_path / "ready").exists()
            process.send_signal(sent_signal)
            assert process.wait(timeout=5) == expected_code
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert (tmp_path / "checkpoint_saved").exists()
    assert (tmp_path / "requeue").exists() is requeue
    if requeue:
        assert (tmp_path / "requeue").read_text().strip() == "requeue 123_0"
    assert (tmp_path / "shell.log").read_text().startswith("shell_start job=123 task=0")


def test_patch_version_changes_are_recorded_not_a_hard_gate(monkeypatch):
    monkeypatch.setattr(preflight.importlib.metadata, "version", lambda name: "2.8.1" if name == "torch" else "2.2.7")
    signature = preflight.runtime_signature({"runtime": {"expected_versions": {"torch": "2.5.1+cu121", "numpy": "2.2.6"}}})
    assert signature["versions"]["numpy"] == "2.2.7"


def test_preparation_cached_per_input_and_mtime_touch_does_not_rehash_all(tmp_path, monkeypatch):
    import numpy as np
    from hpc_recalibration import data
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for name in ("train", "validation", "support", "query"):
        np.savez(inputs / (name + ".npz"), x=np.zeros((6, 3, 32), dtype=np.float32),
                 y=np.array([0, 1] * 3), trial_id=np.array([f"{name}-{i}" for i in range(6)]),
                 run_id=np.array([name] * 6))
    task = {"task_id": "seed1", "dataset": "synthetic", "participant": "one", "family": "eegnet",
            "source_train": "train.npz", "source_validation": "validation.npz",
            "targets": [{"session": "s2", "support": "support.npz", "query": "query.npz"}]}
    tasks = [task, dict(task, task_id="seed2", seed=2)]
    (tmp_path / "tasks.json").write_text(json.dumps(tasks))
    cfg = {"experiment_id": "preflight-synthetic", "output_root": str(tmp_path / "output"),
           "data_root": str(inputs), "tasks_file": str(tmp_path / "tasks.json")}
    real_validator = data.validate_task_inputs
    called = []
    def validate(*args, **kwargs):
        called.append(args[0]["task_id"])
        return real_validator(*args, **kwargs)
    monkeypatch.setattr(data, "validate_task_inputs", validate)
    initial = preflight.prepare_once(cfg)
    assert called == ["seed1"]
    assert preflight.prepare_once(cfg) == initial
    assert called == ["seed1"]
    path = inputs / "support.npz"
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    updated = preflight.prepare_once(cfg)
    assert called == ["seed1", "seed1"]
    assert updated["file_stats"] != initial["file_stats"]
    receipt = Path(cfg["output_root"]) / ".runtime/prepared.json"
    before = receipt.read_bytes()
    with np.load(path) as archive:
        changed = {name: archive[name] for name in archive.files}
    changed["x"] = changed["x"] + np.float32(.25)
    np.savez(path, **changed)
    with pytest.raises(RuntimeError, match="Input bytes changed"):
        preflight.prepare_once(cfg)
    assert receipt.read_bytes() == before


def test_isolated_entrypoint_finds_existing_venv_site_packages():
    command = [sys.executable, "-I", "-S", "-c",
               "import runpy,sys; d=runpy.run_path(sys.argv[1],run_name='bootstrap_import'); "
               "import importlib.metadata; print(importlib.metadata.version('numpy'))",
               str(PROJECT / "bootstrap.py")]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_same_paths_with_different_expected_hashes_are_not_cached_as_equivalent(tmp_path):
    import hashlib
    import numpy as np
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    hashes = {}
    for name in ("train.npz", "validation.npz"):
        path = inputs / name
        np.savez(path, x=np.zeros((4, 3, 32), dtype=np.float32), y=np.array([0, 1, 0, 1]),
                 trial_id=np.array([f"{name}-{i}" for i in range(4)]), run_id=np.array([name] * 4))
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    task = {"task_id": "first", "source_train": "train.npz", "source_validation": "validation.npz",
            "targets": [], "input_sha256": hashes}
    different = dict(task, task_id="second", input_sha256=dict(hashes, **{"train.npz": "0" * 64}))
    (tmp_path / "tasks.json").write_text(json.dumps([task, different]))
    cfg = {"experiment_id": "expected-sha-cache-test", "output_root": str(tmp_path / "output"),
           "data_root": str(inputs), "tasks_file": str(tmp_path / "tasks.json")}
    with pytest.raises(ValueError, match="Frozen input SHA256 mismatch"):
        preflight.prepare_once(cfg)
    assert not (Path(cfg["output_root"]) / ".runtime/prepared.json").exists()


def test_runtime_changes_do_not_change_preparation_identity_but_science_does(config):
    identity = preflight.preparation_key(config)
    config["runtime"] = {"torch_threads": 2, "checkpoint_seconds": 10}
    config["slurm"]["time_limit"] = "1-00:00:00"
    assert preflight.preparation_key(config) == identity
    config["learning_rate"] = .002
    assert preflight.preparation_key(config) != identity


def test_runtime_code_observation_records_change_without_invalidating_preparation(tmp_path, monkeypatch):
    (tmp_path / "tasks.json").write_text(json.dumps([{"task_id": "one"}]))
    cfg = {"experiment_id": "code-observation", "output_root": str(tmp_path / "output"),
           "data_root": str(tmp_path / "inputs"), "tasks_file": str(tmp_path / "tasks.json")}
    directory = Path(cfg["output_root"]) / ".runtime"
    directory.mkdir(parents=True)
    receipt = {"preparation_key": preflight.preparation_key(cfg),
               "runtime": preflight.runtime_signature(cfg), "file_stats": [],
               "code_provenance": {"fingerprint": "old-runtime"}}
    preflight.atomic_json(directory / "prepared.json", receipt)
    monkeypatch.setattr(preflight, "code_provenance", lambda: {"fingerprint": "patched-runtime", "files": []})
    assert preflight.lightweight_ready(cfg) == receipt
    assert preflight.lightweight_ready(cfg) == receipt
    history = json.loads((directory / "code_observations.json").read_text())
    assert len(history) == 1 and history[0]["checkpoint_invalidation_requested"] is False
    assert json.loads((directory / "prepared.json").read_text()) == receipt


def test_corrupt_completion_is_not_treated_as_success(config):
    path = Path(config["output_root"]) / "tasks/first/complete.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    with pytest.raises(ValueError, match="Malformed completion"):
        slurm.submit(config, runner=lambda _: pytest.fail("scheduler called"))
