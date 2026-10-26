"""Synthetic V3 exports; no model loading, inference or real network writes."""

from pathlib import Path
import hashlib
import importlib.util
import io
import json
import sys
import tarfile

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
spec = importlib.util.spec_from_file_location(
    "v3_saved_publisher", ROOT / "experiments/hpc_recalibration_v3/publish_results.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def saved(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "bootstrap.py").write_text("# synthetic software only\n")
    own_source = project / "hpc_recalibration_v3"
    own_source.mkdir()
    (own_source / "protocol.py").write_text("# complete V3 science provenance\n")
    configs = project / "configs"
    configs.mkdir()
    data = project / "data"
    data.mkdir()
    (data / "eeg.npz").write_bytes(b"NEVER_PUBLISH_RAW_EEG")
    output = project / "output"
    task = output / "tasks/synthetic"
    task.mkdir(parents=True)
    (task / "complete.json").write_text(
        json.dumps({"task_id": "synthetic", "status": "completed", "identity": "software-only"})
    )
    (task / "training_history.json").write_text(
        json.dumps(
            {"synthetic": True, "complete": True, "history": [{"epoch": 1, "train_loss": 0.5}]}
        )
    )
    diagnostics = task / "model_diagnostics"
    diagnostics.mkdir()
    (diagnostics / "fit.json").write_text(
        json.dumps(
            {
                "new_science_field": {
                    "source_noise": 0.1,
                    "target_noise": 0.2,
                    "precision_trace": 3.0,
                }
            }
        )
    )
    (task / "checkpoint.pt").write_bytes(b"NEVER_PUBLISH_TORCH_CHECKPOINT")
    (task / "model.npz").write_bytes(b"NEVER_PUBLISH_CLASSICAL_WEIGHTS")
    evaluation = task / "evaluation"
    evaluation.mkdir()
    (evaluation / "metrics.json").write_text(
        json.dumps({"synthetic": True, "balanced_accuracy": 1.0})
    )
    np.savez_compressed(
        evaluation / "predictions.npz",
        probabilities=np.array([[0.8, 0.2], [0.2, 0.8]]),
        labels=np.array([0, 1]),
        classes=np.array([0, 1]),
        trial_id=np.array(["synthetic-0", "synthetic-1"]),
        run_id=np.array(["run0", "run0"]),
    )
    config = {
        "experiment_id": "v3-synthetic-export",
        "project_dir": str(project),
        "output_root": str(output),
        "data_root": str(data),
        "tasks": [{"task_id": "synthetic", "synthetic": True}],
        "_config_path": str(configs / "actual.json"),
        "git_sync": {
            "enabled": True,
            "repository": "example/synthetic",
            "branch": "synthetic",
            "status_prefix": "training_status/paper2-v3",
            "token_file": str(tmp_path / "private-token"),
        },
    }
    secret = "github_pat_" + "TESTONLY_" * 5
    config["api_token"] = secret
    Path(config["_config_path"]).write_text(json.dumps(config))
    token = Path(config["git_sync"]["token_file"])
    token.write_text(secret)
    logs = output / "logs"
    logs.mkdir()
    (logs / "worker.out").write_text(
        "private=" + secret + "\nAuthorization: Bearer synthetic-private\n"
    )
    sync = output / "github_sync"
    sync.mkdir()
    (sync / "authorization.json").write_text("NEVER_PUBLISH_PRIVATE_AUTH")
    return {
        "config": config,
        "project": project,
        "output": output,
        "task": task,
        "evaluation": evaluation,
        "secret": secret,
        "token": token,
    }


def members(saved, packet):
    base = saved["output"] / "exports" / module.VERSION
    data = b"".join((base / p["file"]).read_bytes() for p in packet["parts"])
    assert (
        len(data) == packet["archive_bytes"]
        and hashlib.sha256(data).hexdigest() == packet["archive_sha256"]
    )
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as stream:
        return {
            m.name.removeprefix("paper2_results/"): stream.extractfile(m).read()
            for m in stream.getmembers()
        }


def test_original_predictions_histories_model_hashes_and_no_eeg_weights_tokens(saved):
    originals = {str(p): p.read_bytes() for p in saved["task"].rglob("*") if p.is_file()}
    packet = module.prepare_bundle(saved["config"])
    values = members(saved, packet)
    assert packet["export_status"] == "complete_exported_unreviewed" and not packet["accepted"]
    manifest = json.loads(values["MANIFEST.json"])
    assert manifest["accepted"] is False and manifest["independently_audited"] is False
    assert (
        values["results/tasks/synthetic/evaluation/predictions.npz"]
        == (saved["evaluation"] / "predictions.npz").read_bytes()
    )
    assert "results/tasks/synthetic/training_history.json" in values
    assert (
        json.loads(values["results/tasks/synthetic/model_diagnostics/fit.json"])[
            "new_science_field"
        ]["precision_trace"]
        == 3.0
    )
    assert (
        values["source_code/hpc_recalibration_v3/protocol.py"]
        == b"# complete V3 science provenance\n"
    )
    assert not any(name.endswith(".pt") or name.endswith("/model.npz") for name in values)
    assert not any("github_sync/" in name or "/data/" in name for name in values)
    body = b"\n".join(values.values())
    for private in [
        b"NEVER_PUBLISH_RAW_EEG",
        b"NEVER_PUBLISH_TORCH_CHECKPOINT",
        b"NEVER_PUBLISH_CLASSICAL_WEIGHTS",
        saved["secret"].encode(),
        b"synthetic-private",
    ]:
        assert private not in body
    model = next(x for x in manifest["excluded"] if x["path"].endswith("/checkpoint.pt"))
    assert model["sha256"] == hashlib.sha256(b"NEVER_PUBLISH_TORCH_CHECKPOINT").hexdigest()
    for row in manifest["files"]:
        assert (
            len(values[row["path"]]) == row["bytes"]
            and hashlib.sha256(values[row["path"]]).hexdigest() == row["sha256"]
        )
    assert originals == {str(p): p.read_bytes() for p in saved["task"].rglob("*") if p.is_file()}


def test_reuses_packet_and_repairs_small_index_without_rehashing_models(saved, monkeypatch):
    first = module.prepare_bundle(saved["config"])
    base = saved["output"] / "exports" / module.VERSION
    (base / "README.md").write_text("damaged metadata")
    monkeypatch.setattr(
        module, "_model_inventory", lambda *a: pytest.fail("No repeated model scan")
    )
    again = module.prepare_bundle(saved["config"])
    assert first == again and "Saved V3 results" in (base / "README.md").read_text()
    assert "18neural" not in (base / "README.md").read_text()


def test_incomplete_declared_tasks_are_explicit_unreviewed_partial(saved):
    saved["config"]["tasks"].append({"task_id": "missing", "synthetic": True})
    packet = module.prepare_bundle(saved["config"])
    assert packet["export_status"] == "partial_exported_unreviewed" and not packet["accepted"]
    assert any("missing" in error["path"] for error in packet["history_errors"])


def test_signal_arrays_are_not_exported_under_predictions_name(saved):
    np.savez_compressed(
        saved["evaluation"] / "predictions.npz", x=np.ones((2, 22, 640)), labels=np.array([0, 1])
    )
    packet = module.prepare_bundle(saved["config"])
    values = members(saved, packet)
    assert packet["history_errors"] and packet["export_status"] == "partial_exported_unreviewed"
    assert "results/tasks/synthetic/evaluation/predictions.npz" not in values


class FakePublisher:
    def __init__(self, *args, fail_call=None):
        self.calls = []
        self.fail_call = fail_call

    def publish(self, files, message):
        self.calls.append({key: path.read_bytes() for key, path in files.items()})
        failed = [next(iter(files))] if len(self.calls) == self.fail_call else []
        return {
            "commit": "synthetic-commit-" + str(len(self.calls)),
            "verified_objects": len(files) - len(failed),
            "failed_objects": failed,
            "object_count": len(files),
            "total_bytes": sum(p.stat().st_size for p in files.values()),
        }


def test_full_get_receipt_and_receipt_readback_without_acceptance(saved):
    publisher = FakePublisher()
    result = module.publish(
        saved["config"],
        publisher_factory=lambda *a: publisher,
        token_loader=lambda p: "synthetic-only",
    )
    assert result["status"] == "uploaded_unreviewed" and result["failed_objects"] == []
    assert len(publisher.calls) == 2 and result["accepted"] is False
    receipt = json.loads(next(iter(publisher.calls[1].values())))
    assert receipt["failed_objects"] == [] and receipt["verified_objects"] == 3


@pytest.mark.parametrize("failed_call", [1, 2])
def test_any_full_get_failure_remains_failure(saved, failed_call):
    publisher = FakePublisher(fail_call=failed_call)
    result = module.publish(
        saved["config"],
        publisher_factory=lambda *a: publisher,
        token_loader=lambda p: "synthetic-only",
    )
    assert result["status"] == "verification_failed" and result["accepted"] is False
    assert len(publisher.calls) == failed_call
