import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments/hpc_recalibration_v2/download_on_hpc.py"
spec = importlib.util.spec_from_file_location("hpc_runtime_profile", MODULE)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


@pytest.fixture
def project(tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    source = ROOT / "experiments/hpc_recalibration_v2/configs"
    for name in ("kumar_dev.json", "tasks_kumar_dev.json"):
        (configs / name).write_bytes((source / name).read_bytes())
    return tmp_path


def test_partition_override_preserves_every_scientific_field(project):
    original = project / "configs/kumar_dev.json"
    before = original.read_bytes()
    old = json.loads(before)
    effective_path = profile.prepare_profile(project)
    effective = json.loads(effective_path.read_bytes())
    assert original.read_bytes() == before
    assert effective["slurm"] == old["slurm"] | {
        "partition": "hpc_gpu", "gres": "gpu:1", "exclude": "",
        "cpus_per_task": 18, "mem": "64G", "array_parallel": 2,
        "submission_mode": "single_pool", "pool_workers": 2}
    assert {k: v for k, v in effective.items() if k != "slurm"} == {
        k: v for k, v in old.items() if k != "slurm"}
    assert "nodelist" not in effective["slurm"]
    assert "A100" not in effective["slurm"]["gres"]


def test_preparation_and_source_model_identity_remain_equal(project):
    sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
    from hpc_recalibration.preflight import load_config, load_tasks, preparation_key
    from hpc_recalibration.training import effective_config, scientific_identity
    original = load_config(project / "configs/kumar_dev.json")
    effective = load_config(profile.prepare_profile(project))
    assert preparation_key(effective) == preparation_key(original)
    task = load_tasks(original)[-1]
    assert scientific_identity(task, effective_config(effective)) == scientific_identity(
        task, effective_config(original))


def test_private_credential_path_is_explicit_without_reading_value(project, tmp_path):
    token = tmp_path / "private-token"
    token.write_text("software-validation-placeholder\n")
    effective_path = profile.prepare_profile(project, token)
    result = json.loads(effective_path.read_bytes())
    assert result["git_sync"]["token_file"] == str(token.resolve())
    provenance = json.loads(effective_path.with_suffix(".provenance.json").read_bytes())
    assert not provenance["token_value_read_or_recorded"]
    assert "software-validation-placeholder" not in effective_path.read_text()
    assert "software-validation-placeholder" not in json.dumps(provenance)
    assert not provenance["scientific_configuration_changed"]


def test_missing_optional_token_file_keeps_existing_interactive_authorization(project):
    path = profile.prepare_profile(project, project / "not-created")
    assert "token_file" not in json.loads(path.read_bytes())["git_sync"]


def test_same_profile_reuses_files_without_rewriting(project):
    path = profile.prepare_profile(project)
    receipt = path.with_suffix(".provenance.json")
    before = path.stat().st_mtime_ns, receipt.stat().st_mtime_ns
    assert profile.prepare_profile(project) == path
    assert before == (path.stat().st_mtime_ns, receipt.stat().st_mtime_ns)


def test_existing_outputs_and_claims_are_not_touched(project):
    evidence = project / "outputs" / "old-claim"
    evidence.parent.mkdir()
    evidence.write_bytes(b"preserved-running-or-failed-claim")
    profile.prepare_profile(project)
    assert evidence.read_bytes() == b"preserved-running-or-failed-claim"


def test_installer_cannot_submit_before_operational_profile(project, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    monkeypatch.setattr(profile, "prepare", lambda *a, **k: None)
    monkeypatch.setattr(profile.sys, "argv", ["entry", "--incoming", str(incoming), "--project-dir", str(project)])
    commands = []
    monkeypatch.setattr(profile, "install_runtime_bundle", lambda *a, **k: project / ".hpc_runtime/fixed")
    monkeypatch.setattr(profile.subprocess, "call", lambda cmd, **kwargs: commands.append(cmd) or 0)
    assert profile.main() == 0
    assert commands[0][-1] == "--no-launch"
    assert commands[1] == [sys.executable, "-u", str(project / ".hpc_runtime/fixed/submit.py"),
                           "--config", str(project / "configs/kumar_dev_hpc_gpu.json")]
    config = json.loads((project / "configs/kumar_dev_hpc_gpu.json").read_bytes())
    assert config["slurm"]["array_parallel"] == 2
    assert config["slurm"]["cpus_per_task"] == 18
    assert config["slurm"]["mem"] == "64G"


def test_no_launch_never_runs_the_training_launcher(project, tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "prepare", lambda *a, **k: None)
    monkeypatch.setattr(profile.sys, "argv", ["entry", "--incoming", str(tmp_path / "incoming"),
                                             "--project-dir", str(project), "--no-launch"])
    commands = []
    monkeypatch.setattr(profile, "install_runtime_bundle", lambda *a, **k: project / ".hpc_runtime/fixed")
    monkeypatch.setattr(profile.subprocess, "call", lambda cmd, **kwargs: commands.append(cmd) or 0)
    assert profile.main() == 0
    assert len(commands) == 1
    assert commands[0][-1] == "--no-launch"
