"""Software-only tests: GitHub is always mocked; no actual token or remote write."""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import urllib.error

import pytest


MODULE_PATH = (Path(__file__).resolve().parents[1] / "experiments" /
               "hpc_recalibration_v2" / "hpc_recalibration" / "github_sync.py")
SPEC = importlib.util.spec_from_file_location("hpc_v2_github_sync", MODULE_PATH)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


@pytest.fixture
def config(tmp_path):
    tasks = tmp_path / "tasks.json"
    tasks.write_text(json.dumps([{"task_id": "t0", "dataset": "synthetic",
                                  "participant": "s0", "seed": 1}]))
    return {"experiment_id": "software-validation-only", "output_root": str(tmp_path / "out"),
            "tasks_file": str(tasks), "_config_path": str(tmp_path / "config.json"),
            "git_sync": {"repository": "example/test", "branch": "main",
                         "status_prefix": "training_status/paper2-test",
                         "token_file": str(tmp_path / "token"), "interval_seconds": 180}}


def write_token(config, value="software_test_placeholder"):
    path = Path(config["git_sync"]["token_file"])
    path.write_text(value + "\n")
    path.chmod(0o600)
    return path


def fake_authorization(monkeypatch):
    calls = []

    def request(self, method, path, body=None):
        calls.append((method, path, body))
        if path == "/user":
            return {"login": "software-test-account"}
        if path == "/repos/example/test":
            return {"permissions": {"push": True}}
        if method == "GET":
            raise sync.SyncError("not found", 404)
        return {"commit": {"sha": "test-commit"}}

    monkeypatch.setattr(sync.GitHubClient, "request", request)
    return calls


def test_first_authorization_requires_terminal_when_no_token(config, monkeypatch):
    monkeypatch.setattr(sync.sys.stdin, "isatty", lambda: False)
    with pytest.raises(sync.SyncError, match="school login terminal"):
        sync.ensure_authorized(config)
    assert not Path(config["output_root"]).joinpath("tasks").exists()


def test_token_prompt_write_probe_and_scoped_cached_receipt(config, monkeypatch):
    calls = fake_authorization(monkeypatch)
    secret = "synthetic_secret_not_a_real_token"
    monkeypatch.setattr(sync.sys.stdin, "isatty", lambda: True)
    prompts = []
    monkeypatch.setattr(sync.getpass, "getpass", lambda prompt: prompts.append(prompt) or secret)
    first = sync.ensure_authorized(config)
    second = sync.ensure_authorized(config)
    assert first == second
    assert len(prompts) == 1
    assert sum(method == "PUT" for method, _, _ in calls) == 1
    assert first["write_probe_passed"] is True
    assert stat.S_IMODE(Path(config["git_sync"]["token_file"]).stat().st_mode) == 0o600
    receipt = Path(config["output_root"]) / "github_sync" / "authorization.json"
    assert secret not in receipt.read_text()
    assert "Authorization" not in receipt.read_text()


def test_explicit_token_file_is_rechecked_after_token_changes(config, monkeypatch):
    calls = fake_authorization(monkeypatch)
    path = write_token(config)
    sync.ensure_authorized(config, interactive=False)
    path.write_text("replacement_software_placeholder\n")
    sync.ensure_authorized(config, interactive=False)
    assert sum(method == "PUT" for method, _, _ in calls) == 2


def test_403_before_training_preserves_no_false_authorization(config, monkeypatch):
    write_token(config)

    def request(self, method, path, body=None):
        if path == "/user":
            return {"login": "read-only"}
        return {"permissions": {"push": False}}

    monkeypatch.setattr(sync.GitHubClient, "request", request)
    with pytest.raises(sync.SyncError, match="Contents read/write"):
        sync.ensure_authorized(config, interactive=False)
    assert not (Path(config["output_root"]) / "github_sync" / "authorization.json").exists()


def test_actual_write_probe_required_even_when_push_permission_true(config, monkeypatch):
    write_token(config)

    def request(self, method, path, body=None):
        if method == "PUT":
            raise sync.SyncError("GitHub request failed with HTTP 403", 403)
        if "/contents/" in path:
            raise sync.SyncError("not found", 404)
        return {"permissions": {"push": True}, "login": "test"}

    monkeypatch.setattr(sync.GitHubClient, "request", request)
    with pytest.raises(sync.SyncError, match="403"):
        sync.ensure_authorized(config, interactive=False)
    assert not (Path(config["output_root"]) / "github_sync" / "authorization.json").exists()


def test_error_response_body_and_token_never_appear_in_error(monkeypatch):
    secret = "do_not_print_synthetic_token"

    def failure(*args, **kwargs):
        raise urllib.error.HTTPError("https://api.github.com/user", 403,
                                     secret, {}, io.BytesIO(secret.encode()))

    monkeypatch.setattr(sync.urllib.request, "urlopen", failure)
    with pytest.raises(sync.SyncError) as error:
        sync.GitHubClient(secret, "example/test", "main").request("GET", "/user")
    assert secret not in str(error.value)
    assert error.value.status == 403


def test_conflict_reloads_latest_content_sha(monkeypatch):
    calls = []

    def request(self, method, path, body=None):
        calls.append((method, body))
        if method == "GET":
            return {"sha": "old" if len(calls) == 1 else "current"}
        if len(calls) == 2:
            raise sync.SyncError("conflict", 409)
        assert body["sha"] == "current"
        return {"commit": {"sha": "written"}}

    monkeypatch.setattr(sync.GitHubClient, "request", request)
    result = sync.GitHubClient("software", "example/test", "main").put_status(
        "training_status/paper/STATUS.json", {"step": 4})
    assert result["commit"]["sha"] == "written"
    assert [method for method, _ in calls] == ["GET", "PUT", "GET", "PUT"]


def test_monitor_keeps_local_pending_snapshot_on_upload_failure(config, monkeypatch):
    write_token(config)
    task = Path(config["output_root"]) / "tasks" / "t0"
    task.mkdir(parents=True)
    (task / "progress.json").write_text(json.dumps({"phase": "source_train", "global_step": 17}))
    original = (task / "progress.json").read_bytes()

    def failure(*args, **kwargs):
        raise sync.SyncError("GitHub request failed with HTTP 429", 429)

    monkeypatch.setattr(sync.GitHubClient, "put_status", failure)
    outcome = sync.sync_once(config)
    assert outcome["ok"] is False
    assert outcome["http_status"] == 429
    assert outcome["training_affected"] is False
    assert (task / "progress.json").read_bytes() == original
    pending = json.loads((Path(config["output_root"]) / "github_sync" / "pending_snapshot.json").read_text())
    assert pending["tasks"][0]["global_step"] == 17


def test_completed_statistics_only_and_no_model_arrays(config):
    task = Path(config["output_root"]) / "tasks" / "t0"
    task.mkdir(parents=True)
    (task / "progress.json").write_text(json.dumps({
        "phase": "completed", "global_step": 9, "model": [1, 2],
        "checkpoint_at": "2026-10-23T01:00:00Z", "synthetic": True,
        "software_validation_only": True}))
    (task / "complete.json").write_text(json.dumps({"status": "completed", "global_step": 9}))
    (task / "summary.json").write_text(json.dumps([{
        "method": "full", "session": "s2", "requested_budget": 20, "actual_budget": 19,
        "balanced_accuracy": 0.5, "n_query": 8, "predictions": [0, 1],
        "checkpoint": "private.pt", "trial_id": ["a", "b"]}]))
    snapshot = sync.collect_snapshot(config)
    assert snapshot["completed_tasks"] == 1
    assert snapshot["tasks"][0]["synthetic"] is True
    assert snapshot["completed_statistics"][0]["actual_budget"] == 19
    text = json.dumps(snapshot)
    assert "predictions" not in text and "private.pt" not in text and "trial_id" not in text
    assert "\"model\"" not in text


def test_no_complete_claim_from_slurm_or_placeholder_file(config):
    task = Path(config["output_root"]) / "tasks" / "t0"
    task.mkdir(parents=True)
    (task / "complete.json").write_text(json.dumps({"status": "failed"}))
    snapshot = sync.collect_snapshot(config)
    assert snapshot["completed_tasks"] == 0
    assert snapshot["tasks"][0]["status"] == "no_progress_record"


def test_completed_shards_published_while_later_training_runs(config):
    task = Path(config["output_root"]) / "tasks" / "t0"
    task.mkdir(parents=True)
    (task / "progress.json").write_text(json.dumps({"phase": "adaptation", "global_step": 8}))
    (task / "summary.json").write_text(json.dumps({"results": [
        {"method": "frozen", "session": "s1", "balanced_accuracy": 0.5, "n_query": 20}]}))
    snapshot = sync.collect_snapshot(config)
    assert snapshot["completed_tasks"] == 0
    assert len(snapshot["completed_statistics"]) == 1
    assert snapshot["tasks"][0]["phase"] == "adaptation"


def test_classical_budget_names_and_completion_retained(config):
    task = Path(config["output_root"]) / "tasks" / "t0"
    task.mkdir(parents=True)
    (task / "complete.json").write_text(json.dumps({"status": "completed"}))
    (task / "summary.json").write_text(json.dumps({"results": [{
        "method": "csp_shrinkage", "session": "s1", "budget_requested": 20,
        "n_support_actual": 19, "balanced_accuracy": 0.55, "n_query": 20}]}))
    snapshot = sync.collect_snapshot(config)
    assert snapshot["completed_tasks"] == 1
    assert snapshot["completed_statistics"][0]["budget_requested"] == 20
    assert snapshot["completed_statistics"][0]["n_support_actual"] == 19


def test_duplicate_monitor_does_not_spawn_second_process(config, monkeypatch):
    path = Path(config["_config_path"])
    path.write_text(json.dumps(config))
    retained = []
    calls = []

    def spawn(command, **kwargs):
        calls.append(command)
        retained.append(os.dup(kwargs["pass_fds"][0]))
        assert "-u" in command and "--lock-fd" in command
        assert kwargs["start_new_session"] is True
        return type("Process", (), {"pid": 54321})()

    monkeypatch.setattr(sync.subprocess, "Popen", spawn)
    try:
        assert sync.start_monitor(str(path)) == 54321
        assert sync.start_monitor(str(path)) == 54321
        assert len(calls) == 1
    finally:
        for descriptor in retained:
            os.close(descriptor)


def test_monitor_failure_once_exits_without_training_action(config, monkeypatch):
    path = Path(config["_config_path"])
    path.write_text(json.dumps(config))
    monkeypatch.setattr(sync, "sync_once", lambda _: {"ok": False, "training_affected": False})
    assert sync.monitor(str(path), once=True) == 1
    assert not (Path(config["output_root"]) / "tasks").exists()


def test_monitor_exits_after_final_successful_complete_snapshot(config, monkeypatch):
    path = Path(config["_config_path"])
    path.write_text(json.dumps(config))
    monkeypatch.setattr(sync, "sync_once", lambda _: {
        "ok": True, "completed_tasks": 1, "total_tasks": 1})
    monkeypatch.setattr(sync.time, "sleep", lambda _: pytest.fail("must stop after final upload"))
    assert sync.monitor(str(path)) == 0


def test_status_write_cannot_escape_training_namespace():
    with pytest.raises(sync.SyncError, match="restricted"):
        sync.GitHubClient("software", "example/test", "main").put_status("README.md", {})


def test_disabled_sync_does_not_bypass_required_initial_authorization(config):
    config["git_sync"]["enabled"] = False
    with pytest.raises(sync.SyncError, match="required"):
        sync.ensure_authorized(config)
