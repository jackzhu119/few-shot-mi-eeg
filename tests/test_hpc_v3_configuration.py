"""Synthetic staging checks; no EEG, checkpoint deserialization or Slurm."""

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
from hpc_recalibration_v3 import configuration as config  # noqa: E402


def matrix(tmp_path):
    original = json.loads(
        (ROOT / "experiments/hpc_recalibration_v2/configs/tasks_kumar_dev.json").read_text()
    )["tasks"]
    checkpoints = json.loads(
        (ROOT / "experiments/hpc_recalibration_v3/v2_source_checkpoints.json").read_text()
    )
    science = json.loads((ROOT / "experiments/hpc_recalibration_v3/science.json").read_text())
    base = {
        "project_dir": str(tmp_path / "v2"),
        "output_root": str(tmp_path / "v2/results"),
        "data_root": str(tmp_path / "v2/data"),
        "python": sys.executable,
    }
    return config.generate(base, original, checkpoints, tmp_path / "v3", science)


def test_matrix_126_and_three_slot_source_dependencies(tmp_path):
    settings, tasks = matrix(tmp_path)
    assert len(tasks) == 126
    assert [t["family"] for t in tasks[:3]] == ["pooled_pretrain"] * 3
    assert sum(t["family"] == "geometry" for t in tasks) == 6
    assert sum(t["family"] == "neural" and t["variant"] == "core" for t in tasks) == 36
    assert sum(t["family"] == "neural" and t["variant"] != "core" for t in tasks) == 72
    assert sum(t["family"] == "simulation" for t in tasks) == 9
    for index, task in enumerate(tasks):
        if task["family"] == "neural" and task["source_regime"] == "pooled_source":
            assert tasks[index % 3]["task_id"] == task["pretrain_task_id"]
    assert settings["slurm"]["partition"] == "hpc_gpu1"
    assert len(settings["science"]["neural_methods"]) == 8
    assert len({t["task_id"] for t in tasks}) == 126
    assert sorted(
        i for t in tasks if t["family"] == "simulation" for i in t["scenario_indices"]
    ) == list(range(384))


def test_discovery_doses_do_not_repeat_reference_or_change_core(tmp_path):
    _, tasks = matrix(tmp_path)
    for task in tasks:
        if task["family"] == "neural" and task["variant"] != "core":
            assert "source_query" not in task
            assert task["science_overrides"]["neural_methods"] == ["trust_fixed"]
            assert task["science_overrides"]["trust_kl_budget"] in (0.001, 0.1)
        if task["family"] == "neural" and task["source_regime"] == "reuse_v2":
            assert task["source_checkpoint_identity"] and task["original_checkpoint_sha256"]
    assert all("targets" not in t for t in tasks if t["family"] == "pooled_pretrain")


def cache_fixture(tmp_path):
    path = tmp_path / "data/input.npz"
    path.parent.mkdir()
    path.write_bytes(b"synthetic fixture only")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    c = {
        "data_root": str(path.parent),
        "output_root": str(tmp_path / "v3"),
        "v2_output_root": str(tmp_path / "v2"),
    }
    tasks = [{"input_sha256": {"input.npz": sha}}]
    return c, tasks, path, sha


def test_inherited_cache_avoids_full_input_scan(tmp_path, monkeypatch):
    c, tasks, path, sha = cache_fixture(tmp_path)
    inherited = Path(c["v2_output_root"]) / ".runtime/prepared.json"
    inherited.parent.mkdir(parents=True)
    inherited.write_text(
        json.dumps(
            {
                "file_stats": [
                    {
                        "path": str(path),
                        "bytes": path.stat().st_size,
                        "mtime_ns": path.stat().st_mtime_ns,
                    }
                ],
                "input_validation": [{"result": {"files": [{"path": str(path), "sha256": sha}]}}],
            }
        )
    )
    monkeypatch.setattr(
        config, "_sha", lambda path: pytest.fail("Do not scan unchanged verified bytes")
    )
    first = config.prepare_inputs(c, tasks)
    assert first["new_full_hash_reads"] == 0 and first["verified_files"] == 1
    assert config.prepare_inputs(c, tasks)["new_full_hash_reads"] == 0


def test_metadata_touch_rehashes_only_changed_file_and_accepts_same_bytes(tmp_path):
    c, tasks, path, sha = cache_fixture(tmp_path)
    assert config.prepare_inputs(c, tasks)["new_full_hash_reads"] == 1
    path.touch()
    result = config.prepare_inputs(c, tasks)
    assert result["new_full_hash_reads"] == 1
    assert config.prepare_inputs(c, tasks)["new_full_hash_reads"] == 0


def test_changed_real_input_bytes_are_not_a_cosmetic_resume_issue(tmp_path):
    c, tasks, path, sha = cache_fixture(tmp_path)
    config.prepare_inputs(c, tasks)
    path.write_bytes(b"changed actual input")
    with pytest.raises(ValueError, match="Actual frozen input bytes changed"):
        config.prepare_inputs(c, tasks)


def test_generation_preserves_original_tasks(tmp_path):
    original = json.loads(
        (ROOT / "experiments/hpc_recalibration_v2/configs/tasks_kumar_dev.json").read_text()
    )["tasks"]
    before = copy.deepcopy(original)
    matrix(tmp_path)
    assert original == before
