"""No fitting/network: one-fit gates and pending-bundle integrity."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "parent_fit", ROOT / "scripts/run_kumar_parent_first_fit.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_actual_gate_requires_verified_checkpoint_relay():
    c = runner.check_gate()
    assert c["subject"] == "sub-1" and c["seed"] == 20261012
    assert c["maximum_real_fits"] == 1 and c["mandatory_R2_backup"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("ready_for_first_fit", False),
        ("subject", "sub-4"),
        ("seed", 20261013),
        ("mandatory_R2_backup", False),
        ("maximum_real_fits", 2),
        ("query_access", True),
    ],
)
def test_scope_changes_fail_closed(tmp_path, monkeypatch, field, value):
    c = json.loads(runner.CONTRACT.read_text())
    c[field] = value
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(c))
    monkeypatch.setattr(runner, "CONTRACT", p)
    with pytest.raises(ValueError):
        runner.check_gate()


def test_acceptance_receipt_hash_is_required(tmp_path, monkeypatch):
    c = json.loads(runner.CONTRACT.read_text())
    c["synthetic_checkpoint_acceptance_sha256"] = "0" * 64
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(c))
    monkeypatch.setattr(runner, "CONTRACT", p)
    with pytest.raises(ValueError, match="acceptance receipt changed"):
        runner.check_gate()


def test_bundle_stays_pending_and_rejects_changed_archive(tmp_path):
    p = tmp_path / "fit"
    p.mkdir()
    names = [
        "weights.pt",
        "weights.json",
        "fit_result.json",
        "training.log",
        "download_receipt.json",
        "training_config.json",
        "relay_contract.json",
        "input_audit.json",
        "run_source.py",
        "train_source.py",
        "adapter_source.py",
    ]
    for name in names:
        (p / name).write_bytes(b"synthetic software test only")
    r = runner.bundle(p)
    assert r["status"] == "fit_finished_backup_pending"
    assert not r["R2_backup_verified"] and not r["parent_acknowledged"] and not r["stop_Pod"]
    assert runner.bundle(p)["archive_sha256"] == r["archive_sha256"]
    archive = Path(r["archive"])
    raw = bytearray(archive.read_bytes())
    raw[520] ^= 1
    archive.write_bytes(raw)
    assert hashlib.sha256(raw).hexdigest() != r["archive_sha256"]
    with pytest.raises(ValueError, match="content hash mismatch"):
        runner.bundle(p)


def test_reserved_incomplete_job_cannot_refit(tmp_path, monkeypatch):
    import torch
    import train_kumar_eegnet

    output = tmp_path / "existing-job"
    output.mkdir()
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"job": runner.JOB, "output": str(output)}))
    monkeypatch.setattr(runner, "STATE", state)
    monkeypatch.setattr(runner, "validate_inputs", lambda *args: None)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    monkeypatch.setattr(
        train_kumar_eegnet.SourceOnlyEEGNet,
        "fit_source",
        lambda *args: pytest.fail("Incomplete job was refit"),
    )
    with pytest.raises(RuntimeError, match="no automatic refit"):
        runner.execute(tmp_path, tmp_path / "unused-receipt.json", output)
