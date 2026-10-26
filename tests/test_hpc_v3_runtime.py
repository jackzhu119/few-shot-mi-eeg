"""Runtime-only synthetic tests: no EEG, scientific fit, GPU or scheduler calls."""

from pathlib import Path
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/hpc_recalibration_v3/runtime.py"
spec = importlib.util.spec_from_file_location("hpc_v3_runtime", SOURCE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@pytest.fixture
def config(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "bootstrap.py").write_text("# synthetic entry\n")
    data = tmp_path / "data"
    data.mkdir()
    tasks = [{"task_id": "task-" + str(i), "parameter": i} for i in range(9)]
    return {
        "experiment_id": "v3-synthetic-runtime",
        "scientific_version": "synthetic1",
        "science": {"fixed_setting": 1},
        "tasks": tasks,
        "project_dir": str(project),
        "data_root": str(data),
        "output_root": str(tmp_path / "results"),
        "_config_path": str(project / "config.json"),
        "python": sys.executable,
        "slurm": {"account": "zhuziyuan", "partition": "hpc_gpu1"},
    }


def mark(config, task):
    runtime.atomic_json(
        Path(config["output_root"]) / "tasks" / task["task_id"] / "complete.json",
        {"task_id": task["task_id"], "identity": "synthetic", "status": "completed"},
    )


def reply(code=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)


def test_three_single_gpu_commands_and_absolute_bootstrap(config):
    commands = runtime.submit(config, dry_run=True)["commands"]
    assert len(commands) == 3
    for slot, command in enumerate(commands):
        assert "--gres=gpu:NVIDIAA100-SXM4-80GB:1" in command
        assert "--cpus-per-task=16" in command and "--mem=64G" in command
        assert "--partition=hpc_gpu1" in command
        assert not any(part.startswith("--array") for part in command)
        assert command[-2] == str(Path(config["project_dir"]) / "bootstrap.py")
        assert command[-1] == str(slot)
        assert "--signal=B:USR1@180" in command and "--requeue" in command


def test_cached_preparation_ignores_runtime_resources_not_science(config):
    assert runtime.prepare_once(config)["status"] == "prepared"
    config["slurm"]["exclude"] = "gpu3"
    config["runtime"] = {"heartbeat_seconds": 30}
    assert runtime.prepare_once(config)["status"] == "prepared_reused"
    config["science"]["fixed_setting"] = 2
    with pytest.raises(ValueError, match="Science/task identity changed"):
        runtime.prepare_once(config)


def test_submit_three_jobs_authorize_once_then_skip_active(config):
    calls, auth = [], []
    running = []

    def runner(command):
        calls.append(command)
        if command[0] == "squeue":
            return reply(stdout="\n".join(running))
        name = next(c.split("=", 1)[1] for c in command if c.startswith("--job-name="))
        job = str(100 + len(running))
        running.append(job + "|" + name + "|RUNNING")
        return reply(stdout=job + "\n")

    result = runtime.submit(config, runner=runner, authorize=lambda c: auth.append(c))
    assert len(result["submitted_jobs"]) == 3 and len(auth) == 1
    again = runtime.submit(config, runner=runner, authorize=lambda c: auth.append(c))
    assert again["status"] == "already_active" and again["submitted_jobs"] == []
    assert len([c for c in calls if c[0] == "sbatch"]) == 3 and len(auth) == 1


def test_all_complete_needs_no_scheduler_or_auth(config):
    for task in config["tasks"]:
        mark(config, task)
    result = runtime.submit(
        config,
        runner=lambda c: pytest.fail("No scheduler query needed"),
        authorize=lambda c: pytest.fail("No authorization needed"),
    )
    assert result["status"] == "already_complete"


def test_partial_qos_refusal_keeps_accepted_job_and_resume_submits_only_other_slots(config):
    running = []
    accepted = []
    refuse = [True]

    def runner(command):
        if command[0] == "squeue":
            return reply(stdout="\n".join(running))
        if len(accepted) == 1 and refuse[0]:
            refuse[0] = False
            return reply(
                1,
                stderr="sbatch: error: QOSMaxSubmitJobPerUserLimit\nsbatch: error: Batch job submission failed\n",
            )
        name = next(c.split("=", 1)[1] for c in command if c.startswith("--job-name="))
        job = str(200 + len(accepted))
        accepted.append(command)
        running.append(job + "|" + name + "|PENDING")
        return reply(stdout=job)

    first = runtime.submit(config, runner=runner, authorize=lambda c: None)
    assert first["status"] == "partial_submission" and len(first["submitted_jobs"]) == 1
    second = runtime.submit(config, runner=runner, authorize=lambda c: None)
    assert [x["slot"] for x in second["submitted_jobs"]] == [1, 2]
    assert len(accepted) == 3
    ledger = json.loads((Path(config["output_root"]) / ".runtime/submissions.json").read_text())
    assert len(ledger["attempts"]) == 4 and ledger["attempts"][1]["status"] == "rejected"


def test_uncertain_submit_is_preserved_and_not_retried(config):
    def runner(command):
        if command[0] == "squeue":
            return reply()
        raise TimeoutError("synthetic lost scheduler reply")

    with pytest.raises(TimeoutError):
        runtime.submit(config, runner=runner, authorize=lambda c: None)
    with pytest.raises(RuntimeError, match="reply was uncertain"):
        runtime.submit(
            config, runner=runner, authorize=lambda c: pytest.fail("No second authorization")
        )


def test_lost_reply_can_be_recovered_by_exact_queue_name(config):
    def lost(command):
        if command[0] == "squeue":
            return reply()
        raise TimeoutError()

    with pytest.raises(TimeoutError):
        runtime.submit(config, runner=lost, authorize=lambda c: None)
    path = Path(config["output_root"]) / ".runtime/submissions.json"
    name = json.loads(path.read_text())["attempts"][0]["name"]
    ids = iter(["502", "503"])

    def recovered(command):
        return reply(stdout="501|" + name + "|RUNNING" if command[0] == "squeue" else next(ids))

    result = runtime.submit(config, runner=recovered, authorize=lambda c: None)
    assert [r["slot"] for r in result["submitted_jobs"]] == [1, 2]
    ledger = json.loads(path.read_text())
    assert (
        ledger["attempts"][0]["job_id"] == "501"
        and ledger["attempts"][0]["reply_recovered_from_queue"]
    )


def test_network_monitor_failure_does_not_cancel_training(config):
    ids = iter(["301", "302", "303"])

    def runner(command):
        return reply(stdout="" if command[0] == "squeue" else next(ids))

    def failed_monitor(path):
        raise ConnectionError("network unavailable")

    result = runtime.submit(
        config, runner=runner, authorize=lambda c: None, monitor_start=failed_monitor
    )
    assert len(result["submitted_jobs"]) == 3 and result["monitor_warning"]


def test_slot_sequence_complete_reuse_failure_continues_and_manual_resume(config):
    calls = []
    mark(config, config["tasks"][0])

    def task_runner(task, cfg):
        calls.append(task["task_id"])
        if task["task_id"] == "task-3":
            raise ValueError("synthetic numerical issue")
        mark(cfg, task)
        return 0

    assert runtime.worker_slot(config, 0, task_runner=task_runner) == 1
    assert calls == ["task-3", "task-6"]
    calls.clear()

    def recovery(task, cfg):
        calls.append(task["task_id"])
        mark(cfg, task)
        return 0

    assert runtime.worker_slot(config, 0, task_runner=recovery) == 0
    assert calls == ["task-3"]
    history = json.loads((Path(config["output_root"]) / ".runtime/slot-0.json").read_text())
    assert history["runs"][0]["finished"][0]["traceback"].endswith(
        "ValueError: synthetic numerical issue\n"
    )


def test_storage_failure_stops_that_slot_before_next_fit(config):
    calls = []

    def task_runner(task, cfg):
        calls.append(task["task_id"])
        raise OSError("synthetic full disk")

    with pytest.raises(OSError, match="full disk"):
        runtime.worker_slot(config, 0, task_runner=task_runner)
    assert calls == ["task-0"]


def test_preemption_returns_pause_without_another_task(config):
    calls = []

    def task_runner(task, cfg):
        calls.append(task["task_id"])
        return 75

    assert runtime.worker_slot(config, 1, task_runner=task_runner) == 75
    assert calls == ["task-1"]


def test_task_base_exception_preserves_real_exit_and_traceback(config):
    def interrupted(task, cfg):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        runtime.worker_slot(config, 1, task_runner=interrupted)
    state = json.loads((Path(config["output_root"]) / ".runtime/slot-1.json").read_text())["runs"][
        -1
    ]
    assert state["status"] == "cancelled" and state["exit_code"] == 130
    assert state["exception_type"] == "KeyboardInterrupt" and state["active_task"] == "task-1"


def test_auto_requeue_does_not_retry_a_failed_task(config, monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "400")
    calls = []

    def task_runner(task, cfg):
        calls.append(task["task_id"])
        return 1 if task["task_id"] == "task-0" else 75

    assert runtime.worker_slot(config, 0, task_runner=task_runner) == 75
    monkeypatch.setenv("SLURM_RESTART_COUNT", "1")
    calls.clear()

    def resumed(task, cfg):
        calls.append(task["task_id"])
        mark(cfg, task)
        return 0

    assert runtime.worker_slot(config, 0, task_runner=resumed) == 1
    assert calls == ["task-3", "task-6"]


def test_zero_exit_requires_completion_marker(config):
    assert runtime.worker_slot(config, 2, task_runner=lambda t, c: 0) == 1
    record = json.loads((Path(config["output_root"]) / ".runtime/slot-2.json").read_text())
    assert all(row["missing_completion_marker"] for row in record["runs"][0]["finished"])


@pytest.mark.parametrize(
    "interrupt, expected_code, requeue",
    [(None, 0, False), (signal.SIGUSR1, 0, True), (signal.SIGTERM, 130, False)],
)
def test_copied_slurm_spool_uses_absolute_entry_and_forwards_signals(
    tmp_path, interrupt, expected_code, requeue
):
    project = tmp_path / "shared"
    project.mkdir()
    bootstrap = project / "bootstrap.py"
    bootstrap.write_text(
        "import os,signal,time,sys\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGUSR1,lambda n,f:sys.exit(75))\n"
        "signal.signal(signal.SIGTERM,lambda n,f:sys.exit(130))\n"
        "Path(os.environ['READY']).write_text('ready')\n"
        "time.sleep(3) if os.environ.get('WAIT') else None\n"
    )
    spool = tmp_path / "slurm_spool"
    spool.mkdir()
    shell = spool / "slurm_script"
    shell.write_bytes(SOURCE.with_name("job.sh").read_bytes())
    tools = tmp_path / "bin"
    tools.mkdir()
    scontrol = tools / "scontrol"
    scontrol.write_text('#!/bin/bash\nprintf "%s\\n" "$*" > "$REQUEUE_LOG"\n')
    scontrol.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "SLURM_JOB_ID": "synthetic",
            "PATH": str(tools) + ":" + env["PATH"],
            "READY": str(tmp_path / "ready"),
            "REQUEUE_LOG": str(tmp_path / "requeue"),
        }
    )
    if interrupt is not None:
        env["WAIT"] = "1"
    proc = subprocess.Popen(
        ["bash", str(shell), str(project / "config.json"), sys.executable, str(bootstrap), "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    limit = time.monotonic() + 5
    while not (tmp_path / "ready").exists() and proc.poll() is None and time.monotonic() < limit:
        time.sleep(0.01)
    assert (tmp_path / "ready").is_file()
    if interrupt is not None:
        proc.send_signal(interrupt)
    output = proc.communicate(timeout=6)[0]
    assert proc.returncode == expected_code, output
    assert (tmp_path / "requeue").exists() == requeue, output
    assert "shell_start" in output and "worker_start" in output
    assert "can't open file" not in output
