"""Synthetic saved-stage and independent-reporting integration checks."""

from pathlib import Path
import json
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
sys.path.insert(0, str(ROOT / "experiments"))
from hpc_recalibration.data import Split, save_split  # noqa: E402
from hpc_recalibration_v3 import workers, monitor  # noqa: E402


def synthetic(tmp_path):
    rng = np.random.default_rng(932)
    data = tmp_path / "data"
    for name, n in [("train", 8), ("support", 4), ("query", 6), ("sourcequery", 4)]:
        labels = np.arange(n) % 2
        x = rng.normal(size=(n, 2, 64)).astype(np.float32)
        x[:, 0] *= 1 + labels[:, None]
        split = Split(
            x,
            labels,
            np.array([f"synthetic/{name}/{i}" for i in range(n)]),
            np.array([f"synthetic/{name}/run"] * n),
        )
        save_split(data / (name + ".npz"), split)
    task = {
        "task_id": "synthetic-geometry",
        "family": "geometry",
        "dataset": "synthetic",
        "participant": "synthetic-1",
        "source_train": "train.npz",
        "source_query": "sourcequery.npz",
        "targets": [{"session": "session1", "support": "support.npz", "query": "query.npz"}],
        "synthetic": True,
        "software_validation_only": True,
    }
    config = {
        "output_root": str(tmp_path / "outputs"),
        "data_root": str(data),
        "project_dir": str(tmp_path),
        "scientific_version": "synthetic1",
        "experiment_id": "synthetic1",
        "science": {
            "budgets": [2, 4],
            "geometry": {
                "covariance_shrinkage": 0.1,
                "feature_shrinkage": 0.1,
                "numerical_floor": 1e-8,
            },
            "geometry_methods": ["source_tangent_frozen", "tangent_refit", "eb_predictive"],
        },
    }
    return task, config


def test_geometry_saved_fit_and_evaluation_reused_without_fitting_again(tmp_path, monkeypatch):
    task, config = synthetic(tmp_path)
    assert workers.run_geometry(task, config) == 0
    output = Path(config["output_root"]) / "tasks" / task["task_id"]
    assert len(list((output / "evaluation").rglob("metrics.json"))) == 7
    assert len(list((output / "model_diagnostics").glob("*.json"))) == 5
    from hpc_recalibration_v3 import geometry

    monkeypatch.setattr(
        geometry, "fit", lambda *a, **kw: pytest.fail("Completed fits must not repeat")
    )
    (
        output / "complete.json"
    ).unlink()  # Simulate interrupted final task marker, not a new experiment.
    assert workers.run_geometry(task, config) == 0
    assert json.loads((output / "complete.json").read_text())["synthetic"] is True


def test_missing_saved_prediction_repairs_evaluation_without_retraining(tmp_path, monkeypatch):
    task, config = synthetic(tmp_path)
    workers.run_geometry(task, config)
    output = Path(config["output_root"]) / "tasks" / task["task_id"]
    path = next((output / "evaluation").rglob("predictions.npz"))
    path.unlink()
    (output / "complete.json").unlink()
    from hpc_recalibration_v3 import geometry

    monkeypatch.setattr(
        geometry, "fit", lambda *a, **kw: pytest.fail("Do not retrain after evaluation loss")
    )
    workers.run_geometry(task, config)
    assert path.is_file()


def test_geometry_diagnostics_keep_joint_uncertainty_and_query_flags(tmp_path):
    task, config = synthetic(tmp_path)
    workers.run_geometry(task, config)
    folder = Path(config["output_root"]) / "tasks" / task["task_id"]
    path = next((folder / "model_diagnostics").glob("*eb_predictive.json"))
    metadata = json.loads(path.read_text())
    assert metadata["query_used_for_fitting"] is False
    assert metadata["source_reference_uncertainty_propagated"] is False
    assert metadata["posterior_trace"] >= 0
    assert not any(
        "/query/" in trial or "/sourcequery/" in trial for trial in metadata["fit_trial_ids"]
    )


def test_task_specific_discovery_overrides_do_not_mutate_frozen_core(monkeypatch, tmp_path):
    import types

    task = {
        "task_id": "synthetic-dose",
        "family": "neural",
        "science_overrides": {"trust_kl_budget": 0.001, "neural_methods": ["trust_fixed"]},
    }
    config = {"science": {"trust_kl_budget": 0.01}}
    seen = []
    monkeypatch.setitem(
        sys.modules,
        "hpc_recalibration_v3.neural",
        types.SimpleNamespace(run_task=lambda t, c: seen.append(c) or 0),
    )
    # Relative import may already be cached as a package attribute in other tests.
    import hpc_recalibration_v3 as package

    monkeypatch.setattr(
        package, "neural", sys.modules["hpc_recalibration_v3.neural"], raising=False
    )
    assert workers.run_task(task, config) == 0
    assert seen[0]["science"]["trust_kl_budget"] == 0.001
    assert config["science"]["trust_kl_budget"] == 0.01


def test_monitor_network_failure_is_reported_without_touching_worker(tmp_path, monkeypatch):
    config = {
        "project_dir": str(tmp_path),
        "output_root": str(tmp_path / "outputs"),
        "experiment_id": "synthetic",
        "tasks_file": str(tmp_path / "tasks.json"),
        "science": {},
        "git_sync": {
            "enabled": True,
            "repository": "example/test",
            "branch": "main",
            "status_prefix": "training_status/synthetic",
        },
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "tasks.json").write_text(
        json.dumps([{"task_id": "never-started", "family": "geometry"}])
    )
    monkeypatch.setattr(monitor, "_load_token", lambda p: "not-a-real-credential")
    monkeypatch.setattr(
        monitor.GitHubClient,
        "put_status",
        lambda *a: (_ for _ in ()).throw(TimeoutError("synthetic network failure")),
    )
    assert monitor.monitor(str(tmp_path / "config.json"), once=True) == 1
    assert not (tmp_path / "outputs/tasks").exists()
    status = json.loads((tmp_path / "outputs/github_sync/sync_status.json").read_text())
    assert status["training_affected"] is False


def test_old_terminal_slot_records_cannot_stop_monitor_for_new_pending_jobs(tmp_path):
    config = {"output_root": str(tmp_path)}
    runtime = tmp_path / ".runtime"
    runtime.mkdir()
    for slot in range(3):
        (runtime / f"slot-{slot}.json").write_text(
            json.dumps({"runs": [{"job_id": str(slot + 10), "status": "failed"}]})
        )
    assert monitor.slots_finished(config)
    (runtime / "submissions.json").write_text(
        json.dumps({"attempts": [{"slot": 0, "job_id": "99"}]})
    )
    assert not monitor.slots_finished(config)
    (runtime / "slot-0.json").write_text(
        json.dumps({"runs": [{"job_id": "99", "status": "failed"}]})
    )
    assert monitor.slots_finished(config)


def test_cached_authorization_with_existing_private_file_needs_no_network(tmp_path, monkeypatch):
    token = tmp_path / "private-token"
    token.write_text("synthetic-test-only")
    config = {
        "output_root": str(tmp_path / "output"),
        "git_sync": {
            "enabled": True,
            "repository": "example/test",
            "branch": "main",
            "status_prefix": "training_status/synthetic",
            "token_file": str(token),
        },
    }
    folder = Path(config["output_root"]) / "github_sync"
    folder.mkdir(parents=True)
    receipt = {
        "repository": "example/test",
        "branch": "main",
        "status_prefix": "training_status/synthetic",
    }
    (folder / "authorization.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(
        monitor.GitHubClient,
        "put_status",
        lambda *a: pytest.fail("No repeat network authorization gate"),
    )
    assert monitor.authorize(config) == receipt


def test_missing_private_file_does_not_falsely_reuse_authorization(tmp_path, monkeypatch):
    config = {
        "output_root": str(tmp_path / "output"),
        "git_sync": {
            "enabled": True,
            "repository": "example/test",
            "branch": "main",
            "status_prefix": "training_status/synthetic",
            "token_file": str(tmp_path / "missing-token"),
        },
    }
    folder = Path(config["output_root"]) / "github_sync"
    folder.mkdir(parents=True)
    (folder / "authorization.json").write_text(
        json.dumps(
            {
                "repository": "example/test",
                "branch": "main",
                "status_prefix": "training_status/synthetic",
            }
        )
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="interactive school login terminal"):
        monitor.authorize(config)
