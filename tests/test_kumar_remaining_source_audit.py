"""Software-only source-package checks; no actual weights, EEG, model or Pod."""

import ast
import builtins
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

import audit_kumar_remaining_source_bundle as audit


def contract():
    return json.loads(audit.DEFAULT_CONTRACT.read_text())


def source_evidence(job):
    current = contract()
    files = json.loads(audit.pinned(current, "input_manifest").read_text())["files"]
    selected = [entry for entry in files if entry["relative_path"] ==
                "dataset_description.json" or entry["relative_path"].startswith(job["subject"] + "/")]
    inputs = {"subject": job["subject"], "verified_source_files": {
        entry["relative_path"]: {"sha256": entry["sha256"]} for entry in selected}, "runs": []}
    mapping = {entry["relative_path"]: entry for entry in files}
    for run in range(3):
        name = (f"{job['subject']}/ses-0/eeg/"
                f"{job['subject']}_ses-0_task-imagery_run-{run}_eeg.edf")
        inputs["runs"].append({"source_file": name,
            "role": "source_train" if run < 2 else "source_validation",
            "raw_file_sha256": mapping[name]["sha256"]})
    download = {"status": "all_253_full_sha256_verified",
        "records": [{"path": entry["relative_path"], "sha256": entry["sha256"],
                     "status": "reused_sha256_verified"} for entry in files],
        "manifest_sha256": current["https_manifest_sha256"],
        "input_manifest_sha256": current["input_manifest_sha256"],
        "source_plan_sha256": current["input_manifest_sha256"],
        "query_access": False, "real_training_executed": False,
        "maximum_attempts_per_file": 1}
    return current, inputs, download


def placeholder_archive(tmp_path, job):
    """No tensors: scope-rejection fixture, explicitly software-validation-only."""
    data = {name: b"synthetic=true;software_validation_only=true" for name in audit.FILES}
    data["job.json"] = json.dumps(job).encode()
    manifest = {"synthetic": True, "software_validation_only": True,
        **{key: job[key] for key in ("job_id", "subject", "seed", "result_key")},
        "files": [{"path": name, "bytes": len(raw), "sha256": audit.digest(raw)}
                  for name, raw in data.items()]}
    data["manifest.json"] = json.dumps(manifest).encode()
    path = tmp_path / "synthetic-scope-only.tar"
    with tarfile.open(path, "w") as package:
        for name, raw in data.items():
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            package.addfile(member, io.BytesIO(raw))
    return path


def test_actual_metadata_preflight_no_tensor_or_data_imports_and_no_writes(monkeypatch, capsys):
    ledger = audit.ROOT / contract()["accepted_ledger"]
    before = ledger.read_bytes()
    original = builtins.__import__

    def metadata_import(name, *args, **kwargs):
        assert name.split(".")[0] not in {"torch", "numpy", "mne", "train_kumar_eegnet"}
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", metadata_import)
    audit.main([])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "remaining_source_audit_metadata_valid_execution_closed"
    assert result["remaining_source_jobs"] == 36
    assert result["accepted_models_preserved"] == 18
    assert result["source_input_files"] == 253
    assert result["source_input_bytes"] == 196740994
    assert not result["checkpoint_tensors_loaded"]
    assert not result["EEG_or_query_loaded"]
    assert result["audit_refits"] == result["model_forward_passes"] == 0
    assert ledger.read_bytes() == before


def test_all_accepted_eighteen_rejected_before_checkpoint_import(tmp_path, monkeypatch):
    current = contract()
    accepted = json.loads(audit.pinned(current, "accepted_ledger").read_text())["accepted_jobs"]
    monkeypatch.setattr(audit, "preflight", lambda *_: (current, {}))
    for index, job in enumerate(accepted):
        target = tmp_path / str(index)
        target.mkdir()
        package = placeholder_archive(target, job)
        with pytest.raises(ValueError, match="already accepted"):
            audit.audit(package, audit.digest(package.read_bytes()), package.stat().st_size)


@pytest.mark.parametrize("change", ["query_role", "wrong_source_run", "missing_input",
    "wrong_input_hash", "duplicate_receipt", "wrong_receipt_hash", "old_127_status",
    "query_true", "retry_true", "wrong_manifest", "wrong_raw_manifest"])
def test_source_only_evidence_rejects_incomplete_or_wrong_identity(change):
    job = contract()["remaining_jobs"][0]
    current, inputs, download = source_evidence(job)
    if change == "query_role":
        inputs["runs"][0]["role"] = "target_query"
    elif change == "wrong_source_run":
        inputs["runs"][0]["source_file"] = inputs["runs"][0]["source_file"].replace("run-0", "run-3")
    elif change == "missing_input":
        inputs["verified_source_files"].pop("dataset_description.json")
    elif change == "wrong_input_hash":
        inputs["verified_source_files"]["dataset_description.json"]["sha256"] = "0" * 64
    elif change == "duplicate_receipt":
        download["records"][-1] = copy.deepcopy(download["records"][0])
    elif change == "wrong_receipt_hash":
        download["records"][0]["sha256"] = "0" * 64
    elif change == "old_127_status":
        download["status"] = "all_127_full_sha256_verified"
    elif change == "query_true":
        download["query_access"] = True
    elif change == "retry_true":
        download["maximum_attempts_per_file"] = 2
    elif change == "wrong_manifest":
        download["manifest_sha256"] = "0" * 64
    else:
        download["input_manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        audit.verify_source_evidence(inputs, download, job, current)


def test_all_thirty_six_source_evidence_scopes_accept_exact253_only():
    for job in contract()["remaining_jobs"]:
        current, inputs, download = source_evidence(job)
        audit.verify_source_evidence(inputs, download, job, current)
        assert len(inputs["verified_source_files"]) == 22
        assert len(download["records"]) == 253


def test_checkpoint_history_labels_and_numerical_checks_are_exact_old_block():
    old = (audit.ROOT / "scripts/audit_kumar_queue_bundle.py").read_text()
    new = Path(audit.__file__).read_text()
    start = '    config = json.loads(data["training_config.json"])'
    end = '    inputs = json.loads(data["input_audit.json"])'
    assert old.split(start, 1)[1].split(end, 1)[0] == new.split(start, 1)[1].split(end, 1)[0]
    assert "abs(float(loss.mean()) - best) <= 1e-7" in new
    assert "and record[\"replay_absolute_tolerance\"] == 1e-7" in new
    assert "and np.max(np.abs(loss - n[\"loss_float64\"])) < 1e-14" in new
    tree = ast.parse(new)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    forbidden = {"fit", "fit_source", "formal_train", "forward", "predict_proba", "Adam", "SGD"}
    assert not any(isinstance(node.func, ast.Attribute) and node.func.attr in forbidden
                   for node in calls)
    loads = [node for node in calls if isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name) and node.func.value.id == "torch"
             and node.func.attr == "load"]
    assert len(loads) == 1
    keywords = {item.arg: ast.literal_eval(item.value) for item in loads[0].keywords}
    assert keywords == {"map_location": "cpu", "weights_only": True}


def test_archive_hash_length_and_member_bytes_checked_without_loading_tensor(tmp_path):
    package = placeholder_archive(tmp_path, contract()["remaining_jobs"][0])
    raw = package.read_bytes()
    _, data = audit.archive(package, hashlib.sha256(raw).hexdigest(), len(raw))
    assert set(data) == set(audit.FILES) | {"manifest.json"}
    with pytest.raises(ValueError, match="hash"):
        audit.archive(package, "0" * 64, len(raw))
    with pytest.raises(ValueError, match="length"):
        audit.archive(package, audit.digest(raw), len(raw) + 1)
    with pytest.raises(ValueError, match="size bound"):
        audit.archive(package, audit.digest(raw), audit.MAX_ARCHIVE_BYTES + 1)


@pytest.mark.parametrize("arguments", [["--sha256", "0" * 64], ["--archive", "/nonexistent"],
                                      ["--archive", "/nonexistent", "--bytes", "1"]])
def test_actual_audit_requires_full_explicit_identity_before_reading_package(arguments):
    with pytest.raises(ValueError):
        audit.main(arguments)
