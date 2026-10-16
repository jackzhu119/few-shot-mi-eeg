"""Synthetic metadata and inert launcher mocks; no real signal/model execution."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_kumar_component_budget_cpu_20261016.py"


@pytest.fixture(scope="module")
def operation():
    spec = importlib.util.spec_from_file_location("component_budget_operation_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def prepared(operation, tmp_path, monkeypatch):
    """Self-contained hashes describe synthetic text, never historical files."""
    monkeypatch.setattr(operation, "ROOT", tmp_path)
    monkeypatch.setattr(operation, "git_head", lambda: "a" * 40)
    subjects = [f"sub-{index}" for index in range(1, 19)]
    pins = {}
    for relative in operation.REQUIRED_PINS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic=true; software_validation_only; never imported\n")
        pins[relative] = operation.sha256_file(path)
    old = tmp_path / "configs/old.json"
    source_manifest = tmp_path / "source_manifest.json"
    write_json(source_manifest, {"synthetic": True, "software_validation_only": True})
    source_events = tmp_path / "synthetic_audit/source_events.json"
    events = [{"subject": "sub-1", "session": session, "run": run,
               "source_file": f"synthetic/sub-1/{session}/{run}_eeg.edf"}
              for session, run in (("ses-0", "run-0"), ("ses-1", "run-0"),
                                   ("ses-1", "run-1"))]
    write_json(source_events, events)
    input_paths = [source_manifest, source_events]
    for event in events:
        path = source_events.parent / "runs" / (event["source_file"].replace("/", "__") + ".json")
        write_json(path, {"synthetic": True, "software_validation_only": True})
        input_paths.append(path)
    write_json(old, {"subjects": subjects, "data_root": "synthetic-never-opened",
                     "source_manifest": "source_manifest.json", "prior_signal_audit": "synthetic_audit",
                     "synthetic_fixture": True, "software_validation_only": True})
    split, protocol = tmp_path / "split.json", tmp_path / "protocol.md"
    write_json(split, {"synthetic": True, "software_validation_only": True, "trials": []})
    protocol.write_text("synthetic=true; software_validation_only\n")
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    predictions = baseline / "query_predictions.csv"
    predictions.write_text("synthetic,software_validation_only\ntrue,true\n")
    receipt = baseline / "execution_receipt.json"
    write_json(receipt, {"status": "completed_frozen_offline_protocol", "synthetic": False,
                         "synthetic_fixture": True, "software_validation_only": True,
                         "outputs": {"query_predictions.csv": operation.sha256_file(predictions)}})
    config = {
        "schema_version": 1, "synthetic": False, "subjects": subjects,
        "synthetic_fixture": True, "software_validation_only": True,
        "budgets": [4, 8, 12, 16, "full"], "seed": 42, "threads": 1,
        "max_seconds": 3600, "source_code_pins": pins,
        "input_text_pins": {str(path.relative_to(tmp_path)): operation.sha256_file(path)
                            for path in input_paths},
        "old_config": "configs/old.json", "old_config_sha256": operation.sha256_file(old),
        "data_root": "synthetic-never-opened", "split_manifest_sha256": operation.sha256_file(split),
        "protocol_sha256": operation.sha256_file(protocol),
        "baseline_execution_receipt_sha256": operation.sha256_file(receipt),
    }
    config_path = tmp_path / "config.json"
    write_json(config_path, config)
    args = SimpleNamespace(
        config=config_path, protocol=protocol, split_manifest=split, baseline_root=baseline,
        saved_predictions=predictions, output=tmp_path / "fresh-scientific-output",
        authorization=tmp_path / "authorization.json")
    host = {"hostname": "synthetic-existing-cpu", "boot_id": "synthetic", "pid1_start_ticks": "1"}
    observed = {"memory": {"effective_available_bytes": 16 * operation.GIB},
                "free_output_disk_bytes": 4 * operation.GIB,
                "synthetic": True, "software_validation_only": True}
    calls = []

    def resources(path):
        calls.append(("resources", path))
        return copy.deepcopy(observed)

    monitor = SimpleNamespace(
        resources=resources, container_identity=lambda: copy.deepcopy(host),
        runtime_metadata=lambda: {"synthetic": True, "software_validation_only": True})
    monkeypatch.setattr(operation, "load_module", lambda *args: monitor)

    def forbidden(*args, **kwargs):
        pytest.fail("Metadata preflight must never load scientific arrays")

    monkeypatch.setattr(operation, "load_verified_source_model", forbidden)
    monkeypatch.setattr(operation, "run_budget_subject", forbidden)
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Synthetic authorization fixture only; no real execution authorized.\n")
    auth = {
        "schema_version": 1, "status": "direct_user_authorized",
        "config_sha256": operation.sha256_file(config_path),
        "protocol_sha256": operation.sha256_file(protocol), "source_code_pins": pins,
        "host_identity": host, "output": str(args.output.resolve()),
        "prompt_path": str(prompt), "prompt_sha256": operation.sha256_file(prompt),
        "synthetic": True, "software_validation_only": True,
    }
    write_json(args.authorization, auth)
    return SimpleNamespace(root=tmp_path, config=config, args=args, monitor=monitor,
                           observed=observed, calls=calls, auth=auth, prompt=prompt)


def test_module_import_needs_only_stdlib():
    source = (
        "import importlib.util, sys; "
        f"s = importlib.util.spec_from_file_location('stdlib_only_budget', {str(SCRIPT)!r}); "
        "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "assert not {'numpy', 'scipy', 'sklearn', 'mne'} & set(sys.modules)"
    )
    result = subprocess.run([sys.executable, "-S", "-c", source], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_default_preflight_is_read_only_metadata_without_authorization(operation, prepared):
    fixture = prepared
    fixture.args.authorization.unlink()
    before = {str(path): path.read_bytes() for path in fixture.root.rglob("*") if path.is_file()}
    config, report = operation.preflight(fixture.args)
    assert config == fixture.config
    assert report["status"] == "metadata_only_preflight"
    assert report["scientific_inputs_loaded"] is report["new_scientific_evaluation"] is False
    assert "authorization_sha256" not in report
    assert before == {str(path): path.read_bytes() for path in fixture.root.rglob("*")
                      if path.is_file()}
    assert not fixture.args.output.exists()
    assert not fixture.args.output.with_name(fixture.args.output.name + ".operation").exists()


def test_direct_user_authorization_requires_no_cost_or_parent_ack_artifact(operation, prepared):
    _, report = operation.preflight(prepared.args, authorization=True)
    assert report["authorization_sha256"] == operation.sha256_file(prepared.args.authorization)
    assert report["new_scientific_evaluation"] is False
    assert not prepared.args.output.exists()


def test_unknown_scientific_dispatch_mode_is_rejected(operation, prepared):
    config = copy.deepcopy(prepared.config)
    config["analysis_mode"] = "arbitrary_consumer"
    with pytest.raises(ValueError, match="Unknown fixed scientific consumer"):
        operation.validate_config(config)


def test_phase_dispatch_requires_its_fixed_consumer_pin(operation, prepared):
    config = copy.deepcopy(prepared.config)
    config["analysis_mode"] = "phase_window"
    assert operation.PHASE_SCRIPT not in config["source_code_pins"]
    with pytest.raises(ValueError, match="Phase consumer source pin missing"):
        operation.validate_config(config)
    config["source_code_pins"][operation.PHASE_SCRIPT] = "f" * 64
    operation.validate_config(config)


def test_default_and_explicit_budget_need_no_phase_dependency(operation, prepared):
    config = copy.deepcopy(prepared.config)
    assert "analysis_mode" not in config
    assert operation.PHASE_SCRIPT not in config["source_code_pins"]
    assert not (prepared.root / operation.PHASE_SCRIPT).exists()
    operation.validate_config(config)
    config["analysis_mode"] = "budget"
    operation.validate_config(config)


@pytest.mark.parametrize("change", ["config", "protocol", "code", "host", "output", "prompt",
                                    "status"])
def test_authorization_rejects_changed_bindings_before_execution(operation, prepared, change):
    auth = copy.deepcopy(prepared.auth)
    if change in {"config", "protocol"}:
        auth[change + "_sha256"] = "f" * 64
    elif change == "code":
        auth["source_code_pins"][operation.REQUIRED_PINS[0]] = "f" * 64
    elif change == "host":
        auth["host_identity"]["boot_id"] = "different"
    elif change == "output":
        auth["output"] = str(prepared.root / "different-output")
    elif change == "prompt":
        prepared.prompt.write_text("Changed synthetic prompt")
    else:
        auth["status"] = "parent_acknowledged"
    write_json(prepared.args.authorization, auth)
    with pytest.raises(ValueError, match="binding|authorization"):
        operation.preflight(prepared.args, authorization=True)
    assert not prepared.args.output.exists()


@pytest.mark.parametrize("kind", ["source", "split", "protocol", "baseline_receipt", "predictions"])
def test_preflight_rejects_tampered_pins_and_saved_metadata(operation, prepared, kind):
    path = {"source": prepared.root / operation.REQUIRED_PINS[0],
            "split": prepared.args.split_manifest, "protocol": prepared.args.protocol,
            "baseline_receipt": prepared.args.baseline_root / "execution_receipt.json",
            "predictions": prepared.args.saved_predictions}[kind]
    path.write_bytes(path.read_bytes() + b"\nSYNTHETIC TAMPER\n")
    with pytest.raises(ValueError, match="pin|changed"):
        operation.preflight(prepared.args)
    assert not prepared.args.output.exists()


@pytest.mark.parametrize("resource", ["memory", "disk"])
def test_preflight_resource_shortage_refuses_before_any_scientific_write(
        operation, prepared, resource):
    if resource == "memory":
        prepared.observed["memory"]["effective_available_bytes"] = 3 * operation.GIB - 1
    else:
        prepared.observed["free_output_disk_bytes"] = 2 * operation.GIB - 1
    with pytest.raises(ValueError, match="memory|Disk"):
        operation.preflight(prepared.args)
    assert not prepared.args.output.exists()


@pytest.mark.parametrize("occupied", ["directory", "file", "dangling_symlink"])
def test_preflight_refuses_any_existing_output(operation, prepared, occupied):
    output = prepared.args.output
    if occupied == "directory":
        output.mkdir()
    elif occupied == "file":
        output.write_text("SYNTHETIC PRESERVE")
    else:
        output.symlink_to(prepared.root / "absent")
    with pytest.raises(ValueError, match="fresh"):
        operation.preflight(prepared.args)
    assert prepared.calls == []  # Refuse before even collecting resource metadata.


@pytest.fixture
def launcher(operation, prepared, monkeypatch):
    """Popen is inert and all resource observations describe invented processes."""
    monkeypatch.setattr(operation, "LOCK", prepared.root / "synthetic-cpu.lock")
    samples, cleanup_calls, guards, popen_calls = [], [], [], []
    process = SimpleNamespace(pid=987654, returncode=None)

    def poll():
        return process.returncode

    def wait(timeout=None):
        process.returncode = 0
        return process.returncode

    process.poll, process.wait = poll, wait
    observed = {"consumer_rss_bytes": operation.GIB, "host_available_bytes": 8 * operation.GIB,
                "cgroup_headroom_bytes": 4 * operation.GIB, "synthetic": True,
                "software_validation_only": True}

    def running_memory(pid, *, observed_descendants):
        assert pid == process.pid
        samples.append(copy.deepcopy(observed))
        observed_descendants[pid] = {"synthetic": True}
        return copy.deepcopy(observed)

    def stop_tracked_process(child, timeout, history):
        assert child is process
        cleanup_calls.append((timeout, copy.deepcopy(history)))
        process.returncode = 0
        return 0, []

    @contextmanager
    def deadline_guard(deadline):
        guards.append(deadline)
        yield

    def popen(command, **kwargs):
        assert kwargs["start_new_session"] is True
        assert len(kwargs["pass_fds"]) == 1
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            assert kwargs["env"][name] == "1"
        assert "--worker-internal" in command
        assert "--execute" not in command
        os.fstat(kwargs["pass_fds"][0])
        popen_calls.append((command, kwargs))
        return process

    prepared.monitor.process_record = lambda pid, proc_root: {"start_ticks": "synthetic-ticks"}
    prepared.monitor.running_memory = running_memory
    prepared.monitor.stop_tracked_process = stop_tracked_process
    prepared.monitor.deadline_guard = deadline_guard
    monkeypatch.setattr(operation.subprocess, "Popen", popen)
    state = prepared.args.output.with_name(prepared.args.output.name + ".operation")
    return SimpleNamespace(prepared=prepared, process=process, observed=observed, samples=samples,
                           cleanup_calls=cleanup_calls, guards=guards, popen_calls=popen_calls,
                           state=state)


def assert_launcher_lock_closed(launcher):
    descriptor = launcher.popen_calls[0][1]["pass_fds"][0]
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_launcher_zero_exit_remains_unaccepted_until_independent_audit(operation, launcher):
    operation.execute(launcher.prepared.args)
    receipt = json.loads((launcher.state / "operation_receipt.json").read_text())
    assert receipt["status"] == "consumer_exited_zero_pending_independent_audit"
    assert receipt["scientific_completion_accepted"] is receipt["independently_audited"] is False
    assert receipt["automatic_retries"] == 0
    assert len(launcher.popen_calls) == len(launcher.cleanup_calls) == 1
    assert launcher.samples and len(launcher.guards) == 2
    assert 0 < launcher.cleanup_calls[0][0] <= 30
    assert launcher.process.pid in launcher.cleanup_calls[0][1]
    assert not launcher.prepared.args.output.exists()  # The invented child writes no science.
    assert_launcher_lock_closed(launcher)


@pytest.mark.parametrize("failure", ["rss", "host_memory", "cgroup_memory", "disk", "monitor"])
def test_launcher_resource_or_monitor_failure_stops_once_and_preserves_receipt(
        operation, launcher, monkeypatch, failure):
    if failure == "rss":
        launcher.observed["consumer_rss_bytes"] = 2 * operation.GIB + 1
    elif failure == "host_memory":
        launcher.observed["host_available_bytes"] = operation.GIB - 1
    elif failure == "cgroup_memory":
        launcher.observed["cgroup_headroom_bytes"] = operation.GIB - 1
    elif failure == "disk":
        monkeypatch.setattr(operation.shutil, "disk_usage",
                            lambda _: SimpleNamespace(free=2 * operation.GIB - 1))
    else:
        def fail_observation(*args, **kwargs):
            raise ValueError("synthetic unstable process census")

        launcher.prepared.monitor.running_memory = fail_observation
    with pytest.raises(ValueError):
        operation.execute(launcher.prepared.args)
    receipt = json.loads((launcher.state / "operation_receipt.json").read_text())
    assert receipt["failure"]["type"] == "ValueError"
    assert receipt["new_scientific_evaluation"] is True
    assert receipt["scientific_completion_accepted"] is False
    assert len(launcher.popen_calls) == len(launcher.cleanup_calls) == 1
    assert_launcher_lock_closed(launcher)


def test_cleanup_failure_retains_receipt_and_closes_lock(operation, launcher):
    def cleanup_failure(child, timeout, history):
        launcher.cleanup_calls.append((timeout, history))
        raise OSError("synthetic cleanup failure")

    launcher.prepared.monitor.stop_tracked_process = cleanup_failure
    with pytest.raises(OSError, match="cleanup failure"):
        operation.execute(launcher.prepared.args)
    receipt = json.loads((launcher.state / "operation_receipt.json").read_text())
    assert receipt["status"] == "cleanup_failed_preserved"
    assert receipt["cleanup_failure"]["type"] == "OSError"
    assert len(launcher.cleanup_calls) == 1
    assert receipt["scientific_completion_accepted"] is False
    assert_launcher_lock_closed(launcher)


def test_successful_root_with_remaining_descendants_is_never_accepted(operation, launcher):
    def descendants(child, timeout, history):
        launcher.cleanup_calls.append((timeout, history))
        return 0, [{"pid": 987655, "signal": "SIGTERM", "synthetic": True}]

    launcher.prepared.monitor.stop_tracked_process = descendants
    with pytest.raises(RuntimeError, match="Descendants required cleanup"):
        operation.execute(launcher.prepared.args)
    receipt = json.loads((launcher.state / "operation_receipt.json").read_text())
    assert receipt["status"] == "descendant_cleanup_required_preserved"
    assert receipt["signals"] and receipt["scientific_completion_accepted"] is False
    assert len(launcher.cleanup_calls) == 1
    assert_launcher_lock_closed(launcher)


def test_lock_conflict_cannot_create_or_mutate_operation_state(operation, launcher, monkeypatch):
    def unavailable(*args):
        raise BlockingIOError("synthetic existing CPU consumer")

    monkeypatch.setattr(operation.fcntl, "flock", unavailable)
    with pytest.raises(BlockingIOError):
        operation.execute(launcher.prepared.args)
    assert not launcher.state.exists()
    assert not launcher.popen_calls
    assert not launcher.cleanup_calls


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGHUP])
def test_signal_interruption_performs_one_cleanup_and_restores_handlers(
        operation, launcher, monkeypatch, signum):
    original_handlers = {number: object() for number in (signal.SIGTERM, signal.SIGHUP)}
    handlers = dict(original_handlers)

    def install(number, handler):
        previous = handlers[number]
        handlers[number] = handler
        return previous

    def interrupted_observation(*args, **kwargs):
        handlers[signum](signum, None)

    monkeypatch.setattr(operation.signal, "signal", install)
    launcher.prepared.monitor.running_memory = interrupted_observation
    with pytest.raises(InterruptedError, match=signal.Signals(signum).name):
        operation.execute(launcher.prepared.args)
    receipt = json.loads((launcher.state / "operation_receipt.json").read_text())
    assert receipt["failure"]["type"] == "InterruptedError"
    assert handlers == original_handlers
    assert len(launcher.cleanup_calls) == 1
    assert_launcher_lock_closed(launcher)


@pytest.mark.parametrize("flags", [[], ["-u"], ["-B", "-u"], ["-W", "ignore"],
                                   ["-X", "faulthandler"], ["-Wignore", "-Xdev"], ["--"]])
def test_launcher_identity_accepts_interpreter_options(operation, flags):
    assert operation.is_launcher_command(
        [sys.executable, *flags, str(SCRIPT), "--config", "synthetic.json", "--execute"], ROOT)
    assert operation.is_launcher_command(
        [sys.executable, *flags, "scripts/" + SCRIPT.name, "--execute"], ROOT)


@pytest.mark.parametrize("command", [[], ["python"], ["python", "-c", "pass", "--execute"],
                                    ["python", "-m", "pytest", "--execute"],
                                    ["python", str(SCRIPT), "--worker-internal"],
                                    ["python", str(SCRIPT)],
                                    ["python", str(SCRIPT), "--execute", "--worker-internal"]])
def test_generic_python_or_worker_process_cannot_impersonate_launcher(operation, command):
    assert operation.is_launcher_command(command, ROOT) is False


def test_worker_rejects_actual_generic_parent_before_lock_or_scientific_inputs(
        operation, prepared, monkeypatch):
    claim_path = prepared.args.output.with_name(prepared.args.output.name + ".operation") / "claim.json"
    write_json(claim_path, {"output": str(prepared.args.output.resolve()),
                            "synthetic": True, "software_validation_only": True})
    prepared.args.claim = claim_path
    prepared.args.lock_fd = "-999"
    # The actual parent of this pytest process is not the monitored --execute script.
    with pytest.raises(ValueError, match="not this monitored"):
        operation._worker(prepared.args)
    assert prepared.calls == []
    assert not prepared.args.output.exists()
