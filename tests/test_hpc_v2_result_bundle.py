"""Synthetic saved-result packets only; no training, inference or GitHub calls."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments/hpc_recalibration_v2"
sys.path.insert(0, str(EXPERIMENT))
spec = importlib.util.spec_from_file_location("hpc_saved_result_bundle", EXPERIMENT / "export_saved_results.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


@pytest.fixture
def saved(tmp_path, monkeypatch):
    project = tmp_path / "project"
    output = project / "outputs/run"
    configs = project / "configs"
    configs.mkdir(parents=True)
    tasks = [{"task_id": "classic", "family": "classical", "dataset": "synthetic",
              "participant": "synthetic-1", "synthetic": True, "targets": []},
             {"task_id": "neural", "family": "eegnet", "dataset": "synthetic",
              "participant": "synthetic-1", "seed": 1, "synthetic": True, "targets": []}]
    task_path = configs / "tasks.json"
    task_path.write_text(json.dumps(tasks))
    for task in tasks:
        folder = output / "tasks" / task["task_id"]
        folder.mkdir(parents=True)
        (folder / "complete.json").write_text(json.dumps({"task_id": task["task_id"],
                                                          "status": "completed", "synthetic": True}))
    query = output / "tasks/neural/source_query"
    query.mkdir()
    prediction = query / "predictions.npz"
    np.savez_compressed(prediction, probabilities=np.array([[0.7, 0.3], [0.2, 0.8]]),
                        labels=np.array([0, 1]), classes=np.array([0, 1]),
                        trial_id=np.array(["synthetic-0", "synthetic-1"]),
                        run_id=np.array(["synthetic-run", "synthetic-run"]))
    metric = query / "metrics.json"
    metric.write_text('{"synthetic":true,"balanced_accuracy":1.0,"n_query":2}\n')
    checkpoint = output / "tasks/neural/source/checkpoint.pt"
    checkpoint.parent.mkdir()
    checkpoint.write_bytes(b"DO_NOT_PUBLISH_MODEL_WEIGHTS")
    model = output / "tasks/classic/source_model.npz"
    model.write_bytes(b"DO_NOT_PUBLISH_CLASSICAL_WEIGHTS")
    inputs = project / "data"
    inputs.mkdir()
    (inputs / "eeg.npz").write_bytes(b"DO_NOT_PUBLISH_EEG")
    token = tmp_path / "private-token"
    secret = "github_pat_" + "S" * 28
    token.write_text(secret)
    config = {"experiment_id": "synthetic-result-export", "project_dir": str(project),
              "output_root": str(output), "data_root": str(inputs), "tasks_file": str(task_path),
              "budgets": [4], "methods": ["frozen"], "classical_methods": ["frozen"],
              "git_sync": {"token_file": str(token), "api_token": secret}}
    config_path = configs / "run.json"
    config_path.write_text(json.dumps(config))
    config["_config_path"] = str(config_path)
    logs = output / "logs"
    logs.mkdir()
    (logs / "job.out").write_text("old supplied token=" + secret + "\nAuthorization: Bearer short-secret\n")
    calls = {"extract": 0, "summarize": 0}

    def extractor(path):
        calls["extract"] += 1
        data = path.read_bytes()
        return {"history": [{"epoch": 1, "train_loss": 0.6}], "best_epoch": 1,
                "source_file": {"path": str(path), "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest()}}

    def summarizer(config, destination):
        calls["summarize"] += 1
        destination.mkdir(parents=True)
        (destination / "analysis.csv").write_text("synthetic,score\ntrue,1.0\n")
        return {"tasks_expected": 2, "tasks_complete": 2,
                "cells_expected": 0, "cells_with_defined_ba": 0}

    monkeypatch.setattr(bundle, "extract_checkpoint", extractor)
    monkeypatch.setattr(bundle, "extract_classical_metadata", extractor)
    return {"config": config, "destination": project / "exports/test", "prediction": prediction,
            "metric": metric, "checkpoint": checkpoint, "model": model,
            "token": token, "secret": secret, "calls": calls, "summarizer": summarizer}


def packet_members(saved, packet):
    destination = saved["destination"]
    parts = []
    for row in packet["parts"]:
        data = (destination / row["file"]).read_bytes()
        assert len(data) == row["bytes"]
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        parts.append(data)
    body = b"".join(parts)
    assert len(body) == packet["archive_bytes"]
    assert hashlib.sha256(body).hexdigest() == packet["archive_sha256"]
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
        return {row.name.removeprefix("paper2_results/"): archive.extractfile(row).read()
                for row in archive.getmembers() if row.isfile()}


def test_packet_sha_manifest_and_original_prediction_bytes(saved):
    packet = bundle.prepare_bundle(saved["config"], saved["destination"], summarizer=saved["summarizer"])
    members = packet_members(saved, packet)
    manifest = json.loads(members["MANIFEST.json"])
    assert manifest["no_training_or_inference"] is True
    for row in manifest["files"]:
        assert len(members[row["path"]]) == row["bytes"]
        assert hashlib.sha256(members[row["path"]]).hexdigest() == row["sha256"]
    prediction = "results/tasks/neural/source_query/predictions.npz"
    assert members[prediction] == saved["prediction"].read_bytes()
    assert members["results/tasks/neural/source_query/metrics.json"] == saved["metric"].read_bytes()
    assert members["analysis/analysis.csv"].startswith(b"synthetic,score")
    assert not any(name.endswith(".pt") or name.startswith("source_code/data/") for name in members)
    assert not any(value in members.values() for value in
                   (saved["checkpoint"].read_bytes(), saved["model"].read_bytes(), b"DO_NOT_PUBLISH_EEG"))
    assert len([row for row in manifest["excluded"] if row["reason"] == "model_binary_stays_local"]) == 2


def test_private_config_and_logs_are_redacted_without_changing_originals(saved):
    before = saved["token"].read_bytes(), saved["metric"].read_bytes()
    packet = bundle.prepare_bundle(saved["config"], saved["destination"], summarizer=saved["summarizer"])
    members = packet_members(saved, packet)
    public = json.loads(members["source_code/configs/run.json"])
    assert public["git_sync"]["token_file"] == "[REDACTED]"
    assert public["git_sync"]["api_token"] == "[REDACTED]"
    log = members["results/logs/job.out"].decode()
    assert saved["secret"] not in log and "short-secret" not in log
    assert "[REDACTED]" in log
    assert not any(saved["secret"].encode() in body for body in members.values())
    assert before == (saved["token"].read_bytes(), saved["metric"].read_bytes())


def test_repeat_reuses_packet_without_checkpoint_extraction_or_resummarizing(saved):
    first = bundle.prepare_bundle(saved["config"], saved["destination"], summarizer=saved["summarizer"])
    before = saved["calls"].copy()
    second = bundle.prepare_bundle(saved["config"], saved["destination"], summarizer=saved["summarizer"])
    assert first == second
    assert saved["calls"] == before == {"extract": 2, "summarize": 1}


def test_prediction_archive_with_signal_tensor_is_rejected(saved):
    np.savez_compressed(saved["prediction"], x=np.ones((2, 22, 640)), labels=np.array([0, 1]))
    with pytest.raises(ValueError, match="Unexpected prediction archive"):
        bundle.prepare_bundle(saved["config"], saved["destination"], summarizer=saved["summarizer"])
    assert not (saved["destination"] / "prepared_packet.json").exists()


def test_source_change_before_and_during_copy_stops_without_publishing(saved, monkeypatch):
    source = saved["metric"]
    original = source.read_bytes()
    entry = {"path": str(source), "target": "metric.json", "kind": "json", "stat": bundle.stamp(source)}
    source.write_bytes(original + b" ")
    target = saved["destination"] / "must-not-publish.json"
    with pytest.raises(RuntimeError, match="Result changed during export"):
        bundle.copy_public(entry, target)
    assert not target.exists()
    source.write_bytes(original)
    entry["stat"] = bundle.stamp(source)
    real_stamp = bundle.stamp
    calls = [0]

    def mutate_on_second_stat(path):
        calls[0] += 1
        if calls[0] == 2:
            source.write_bytes(original + b" ")
        return real_stamp(path)

    monkeypatch.setattr(bundle, "stamp", mutate_on_second_stat)
    with pytest.raises(RuntimeError, match="Result changed while being read"):
        bundle.copy_public(entry, target)
    assert not target.exists()
