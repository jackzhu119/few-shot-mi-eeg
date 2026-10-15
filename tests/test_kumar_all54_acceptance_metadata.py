"""Acceptance metadata gates only: no tensors, EEG, model construction or fit."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

import evaluate_kumar_checkpoint_reuse as reuse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "research_logs/kumar_remaining36_acceptance_20261015/run01"
LEDGER_SHA = "013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670"
PLAN_SHA = "28232bfa53515ae3e66acadefa39ee025320cfda0196a5d785631bf4d8f8abcd"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arguments(job_id):
    return dict(job_id=job_id, ledger_path=BASE / "accepted_jobs_all54.json",
                expected_ledger_sha256=LEDGER_SHA,
                plan_path=BASE / "source_model_plan_all54.json",
                expected_plan_sha256=PLAN_SHA, evidence_root=ROOT)


def forbidden(*args, **kwargs):
    raise AssertionError("Acceptance metadata must never read weights or construct a model")


def test_all54_metadata_preserves_old18_and_never_loads_weights(monkeypatch):
    monkeypatch.setattr(reuse.torch, "load", forbidden)
    monkeypatch.setattr(reuse, "_build_cpu_model", forbidden)
    monkeypatch.setattr(reuse, "_archive", forbidden)
    ledger = json.loads((BASE / "accepted_jobs_all54.json").read_bytes())
    old = json.loads((ROOT / "research_logs/kumar_development_queue_20261014/accepted_jobs.json")
                     .read_bytes())["accepted_jobs"]
    assert ledger["accepted_jobs"][:18] == old
    assert len(ledger["accepted_jobs"]) == 54
    assert len({e["job_id"] for e in ledger["accepted_jobs"]}) == 54
    for expected in ledger["accepted_jobs"]:
        entry, job, size, _ = reuse.check_reuse_identity(**arguments(expected["job_id"]))
        assert entry == expected and job["job_id"] == expected["job_id"] and size > 0


@pytest.mark.parametrize("violation", ["ack_status", "ack_job", "receipt_sha", "full_get"])
def test_new_acceptance_rejects_missing_parent_or_damaged_receipt(tmp_path, violation):
    ledger = json.loads((BASE / "accepted_jobs_all54.json").read_bytes())
    entry = ledger["accepted_jobs"][18]
    ack = json.loads((ROOT / entry["parent_acknowledgement"]).read_bytes())
    receipt = json.loads((ROOT / entry["receipt"]).read_bytes())
    if violation == "ack_status":
        ack["status"] = "awaiting_parent"
    elif violation == "ack_job":
        ack["job_id"] = ledger["accepted_jobs"][19]["job_id"]
    elif violation == "full_get":
        row = next(r for r in receipt["files"] if r["key"] == entry["result_key"])
        row["verification"] = "head_only"
    receipt_path = tmp_path / entry["receipt"]
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt) + "\n")
    ack["receipt_sha256"] = "0" * 64 if violation == "receipt_sha" else digest(receipt_path)
    ack_path = tmp_path / entry["parent_acknowledgement"]
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    ack_path.write_text(json.dumps(ack) + "\n")
    kwargs = arguments(entry["job_id"])
    kwargs["evidence_root"] = tmp_path
    with pytest.raises(ValueError):
        reuse.check_reuse_identity(**kwargs)


@pytest.mark.parametrize("violation", ["ledger_hash", "plan_order", "unaccepted_job"])
def test_frozen_identity_binding_rejects_changes(tmp_path, violation):
    ledger = json.loads((BASE / "accepted_jobs_all54.json").read_bytes())
    kwargs = arguments(ledger["accepted_jobs"][18]["job_id"])
    if violation == "ledger_hash":
        kwargs["expected_ledger_sha256"] = "0" * 64
    elif violation == "unaccepted_job":
        kwargs["job_id"] = "unapproved-new-fit"
    else:
        plan = copy.deepcopy(json.loads((BASE / "source_model_plan_all54.json").read_bytes()))
        plan["jobs"][18], plan["jobs"][19] = plan["jobs"][19], plan["jobs"][18]
        path = tmp_path / "reordered-plan.json"
        path.write_text(json.dumps(plan) + "\n")
        kwargs.update(plan_path=path, expected_plan_sha256=digest(path))
    with pytest.raises(ValueError):
        reuse.check_reuse_identity(**kwargs)
