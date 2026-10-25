from pathlib import Path
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2/single_pool"
spec = importlib.util.spec_from_file_location("single_pool_controller", ROOT / "controller.py")
pool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pool)


@pytest.fixture
def config(tmp_path):
    return {"project_dir": str(tmp_path), "output_root": str(tmp_path / "output"),
            "_config_path": str(tmp_path / "config.json"), "python": sys.executable,
            "slurm": {"pool_workers": 2, "cpus_per_task": 16},
            "runtime": {"heartbeat_seconds": 30}}


def tasks(count=24):
    return [{"task_id": f"task-{i}", "family": "eegnet", "synthetic": True} for i in range(count)]


def mark_complete(config, task):
    path = Path(config["output_root"]) / "tasks" / task["task_id"] / "complete.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"task_id": task["task_id"], "identity": "software-validation-only"}))


class Harness:
    def __init__(self, config, tasklist, *, failures=(), stop=None, stop_after=None):
        self.config, self.tasks = config, tasklist
        self.failures, self.stop, self.stop_after = set(failures), stop, stop_after
        self.processes, self.calls, self.signals = {}, [], []
        self.alive, self.maximum = set(), 0

    def popen(self, command, **kwargs):
        index = int(command[-1])
        owner = self
        class Process:
            pid = 10000 + len(owner.calls)
            ticks = 0
            code = None
            counted = False
            def poll(self):
                self.ticks += 1
                if self.code is None and self.ticks >= 2:
                    self.code = 1 if index in owner.failures else 0
                if self.code is not None and not self.counted:
                    self.counted = True
                    owner.alive.discard(self.pid)
                    if self.code == 0:
                        mark_complete(owner.config, owner.tasks[index])
                return self.code
        process = Process()
        self.calls.append({"index": index, "command": command, **kwargs})
        self.processes[process.pid] = process
        self.alive.add(process.pid)
        self.maximum = max(self.maximum, len(self.alive))
        if self.stop_after == len(self.calls):
            self.stop.request(signal.SIGUSR1)
        return process

    def signal_group(self, pid, sig):
        self.signals.append((pid, sig))
        self.processes[pid].code = 130 if sig == signal.SIGTERM else 75

    def run(self, **kwargs):
        return pool.run_pool(self.config, self.tasks, popen=self.popen, sleep=lambda _: None,
                             signal_group=self.signal_group, bindings=["GPU-allocated-a", "GPU-allocated-b"],
                             stop=self.stop, **kwargs)


def test_all_24_tasks_run_once_in_fixed_dispatch_order_with_two_workers(config):
    tasklist = tasks()
    harness = Harness(config, tasklist)
    assert harness.run() == 0
    assert [r["index"] for r in harness.calls] == list(range(24))
    assert harness.maximum == 2
    assert all(r["start_new_session"] for r in harness.calls)
    assert {r["env"]["CUDA_VISIBLE_DEVICES"] for r in harness.calls} == {"GPU-allocated-a", "GPU-allocated-b"}
    assert all(r["command"][2] == str(Path(config["project_dir"]) / "bootstrap.py") for r in harness.calls)


def test_complete_skip_and_explicit_subset_do_not_touch_finished_tasks(config):
    tasklist = tasks(5)
    mark_complete(config, tasklist[1])
    harness = Harness(config, tasklist)
    assert harness.run(indices=[1, 3, 4]) == 0
    assert [r["index"] for r in harness.calls] == [3, 4]
    second = Harness(config, tasklist)
    assert second.run(indices=[1, 3, 4]) == 0
    assert not second.calls


def test_failure_is_not_retried_and_other_independent_tasks_continue(config):
    tasklist = tasks(8)
    harness = Harness(config, tasklist, failures={1})
    assert harness.run() == 1
    assert [r["index"] for r in harness.calls] == list(range(8))
    assert sum(r["index"] == 1 for r in harness.calls) == 1
    state = json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())
    assert state["runs"][-1]["failed_indices"] == [1]
    # A user-invoked resume starts only the unfinished failure, preserving history.
    resumed = Harness(config, tasklist)
    assert resumed.run() == 0
    assert [r["index"] for r in resumed.calls] == [1]
    assert len(json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())["runs"]) == 2


def test_same_job_automatic_requeue_blocks_recorded_failure_but_continues_unfinished(config, monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "original-job")
    monkeypatch.setenv("SLURM_RESTART_COUNT", "0")
    tasklist = tasks(4)
    first = Harness(config, tasklist, failures={0})
    assert first.run(indices=[0, 1]) == 1
    monkeypatch.setenv("SLURM_RESTART_COUNT", "1")
    resumed = Harness(config, tasklist)
    assert resumed.run() == 1
    assert [row["index"] for row in resumed.calls] == [2, 3]
    runs = json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())["runs"]
    assert runs[0]["failed_indices"] == [0]
    assert runs[-1]["failed_indices"] == []
    assert runs[-1]["blocked_failed_indices"] == [0]
    assert runs[-1]["slurm_restart_count"] == 1


def test_new_job_explicit_resume_can_retry_old_failure(config, monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "original-job")
    monkeypatch.setenv("SLURM_RESTART_COUNT", "0")
    tasklist = tasks(3)
    assert Harness(config, tasklist, failures={0}).run(indices=[0, 1]) == 1
    monkeypatch.setenv("SLURM_JOB_ID", "new-manual-job")
    resumed = Harness(config, tasklist)
    assert resumed.run() == 0
    assert [row["index"] for row in resumed.calls] == [0, 2]
    runs = json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())["runs"]
    assert runs[-1]["job_id"] == "new-manual-job"
    assert runs[-1]["blocked_failed_indices"] == []


def test_usr1_during_dispatch_does_not_start_a_third_task(config):
    stop = pool.StopState()
    harness = Harness(config, tasks(7), stop=stop, stop_after=2)
    assert harness.run() == 75
    assert [r["index"] for r in harness.calls] == [0, 1]
    assert len(harness.signals) == 2
    assert all(sig == signal.SIGUSR1 for _, sig in harness.signals)


def test_term_overrides_usr1_and_never_requeues(config):
    stop = pool.StopState()
    stop.request(signal.SIGUSR1)
    stop.request(signal.SIGTERM)
    harness = Harness(config, tasks(), stop=stop)
    assert harness.run() == 130
    assert not harness.calls


def test_forwarded_usr1_default_exit_is_preemption_not_scientific_failure(config):
    stop = pool.StopState()
    harness = Harness(config, tasks(4), stop=stop, stop_after=2)
    def raw_signal(pid, sig):
        harness.signals.append((pid, sig))
        harness.processes[pid].code = -sig
    harness.signal_group = raw_signal
    assert harness.run() == 75
    state = json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())["runs"][-1]
    assert state["failed_indices"] == []
    assert all(row["exit_code"] == -signal.SIGUSR1 and row["execution_before_signal_unknown"]
               for row in state["finished"])
    assert len(harness.calls) == 2


def test_unrequested_negative_signal_remains_a_failure(config):
    tasklist = tasks(1)
    harness = Harness(config, tasklist)
    original = harness.popen
    def killed(*args, **kwargs):
        process = original(*args, **kwargs)
        process.code = -signal.SIGUSR1
        return process
    harness.popen = killed
    assert harness.run() == 1
    state = json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())["runs"][-1]
    assert state["failed_indices"] == [0]


def test_forwarded_term_default_exit_is_cancellation(config):
    stop = pool.StopState()
    harness = Harness(config, tasks(4), stop=stop)
    original = harness.popen
    def start_then_cancel(*args, **kwargs):
        process = original(*args, **kwargs)
        if len(harness.calls) == 2:
            stop.request(signal.SIGTERM)
        return process
    def raw_signal(pid, sig):
        harness.processes[pid].code = -sig
    harness.popen, harness.signal_group = start_then_cancel, raw_signal
    assert harness.run() == 130
    state = json.loads((Path(config["output_root"]) / ".runtime/single_pool_state.json").read_text())["runs"][-1]
    assert state["failed_indices"] == []
    assert len(harness.calls) == 2


def test_earlier_scientific_failure_prevents_automatic_requeue(config):
    tasklist = tasks(6)
    stop = pool.StopState()
    harness = Harness(config, tasklist, failures={0}, stop=stop, stop_after=4)
    assert harness.run() == 1
    assert [r["index"] for r in harness.calls] == [0, 1, 2, 3]


def test_gpu_mapping_is_only_from_the_assigned_visible_tokens():
    assert pool.gpu_bindings(2, "3,7") == ["3", "7"]
    assert pool.gpu_bindings(2, "GPU-foo,MIG-GPU-bar/1/0") == ["GPU-foo", "MIG-GPU-bar/1/0"]
    for value in ("", "-1", "0", "0,0"):
        with pytest.raises(RuntimeError, match="CUDA_VISIBLE_DEVICES"):
            pool.gpu_bindings(2, value)


def test_duplicate_controller_does_not_start_any_worker(config):
    import fcntl
    runtime = Path(config["output_root"]) / ".runtime"
    runtime.mkdir(parents=True)
    with (runtime / "pool.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        harness = Harness(config, tasks(2))
        assert harness.run() == 73
        assert not harness.calls


def test_zero_worker_exit_without_complete_marker_is_not_success(config):
    class Process:
        pid = 30000
        def poll(self):
            return 0
    assert pool.run_pool(config, tasks(1), bindings=["a", "b"],
                         popen=lambda *a, **k: Process(), sleep=lambda _: None) == 1


@pytest.mark.parametrize("number,expected,requeues,handler", [
    (signal.SIGUSR1, 0, True, True), (signal.SIGTERM, 130, False, True),
    (signal.SIGUSR1, 0, True, False)])
def test_actual_bash_signal_forward_and_requeue_boundary(tmp_path, number, expected, requeues, handler):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "job.sh").write_bytes((ROOT / "job.sh").read_bytes())
    worker = runtime / "controller.py"
    worker.write_text("import os,signal,time,sys\nfrom pathlib import Path\n"
                      + ("signal.signal(signal.SIGUSR1,lambda *a:sys.exit(75))\n"
                         "signal.signal(signal.SIGTERM,lambda *a:sys.exit(130))\n" if handler else "")
                      + "Path(os.environ['READY']).write_text(str(os.getpid()))\n"
                      "while True:time.sleep(.02)\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    control = binary / "scontrol"
    control.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$REQUEUE_LOG"\n')
    control.chmod(0o755)
    env = os.environ.copy()
    env.update(SLURM_JOB_ID="123456", READY=str(tmp_path / "ready"),
               PAPER2_POOL_RUNTIME=str(runtime),
               REQUEUE_LOG=str(tmp_path / "requeue.log"), PATH=str(binary) + os.pathsep + env["PATH"])
    process = subprocess.Popen(["bash", str(runtime / "job.sh"), "fake.json", sys.executable, "0,1"],
                               env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.monotonic() + 5
    while not (tmp_path / "ready").exists() and time.monotonic() < deadline:
        time.sleep(.02)
    assert (tmp_path / "ready").exists()
    process.send_signal(number)
    output = process.communicate(timeout=5)[0]
    assert process.returncode == expected, output
    assert (tmp_path / "requeue.log").exists() == requeues
    if requeues:
        assert (tmp_path / "requeue.log").read_text().strip() == "requeue 123456"
    if not handler:
        assert "observed_code=" + str(128 + signal.SIGUSR1) in output
        assert "execution before signal is unknown" in output
