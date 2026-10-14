"""No GPU/network: enforce scope, duplicate prevention, receipt and archive integrity."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_kumar_development_queue_https as transfer  # noqa: E402
import run_kumar_development_queue as queue  # noqa: E402


def test_actual_gates_reuse_first_and_select_only_next_frozen_job():
    runtime, plan, job = queue.check_gate()
    assert runtime["maximum_new_fits"] == 17
    assert len(plan["jobs"]) == 18
    assert (job["subject"], job["seed"]) == ("sub-1", 20261013)
    assert not runtime["formal_gate"]


def test_source_manifest_exactly_18_source_edfs_no_query():
    p = transfer.load_plan()
    edfs = [e["path"] for e in p["files"] if e["path"].endswith(".edf")]
    assert len(edfs) == 18 and len(p["files"]) == 127
    assert all("/ses-0/" in e and e.split("_run-")[1][0] in "012" for e in edfs)
    assert {e.split("/")[0] for e in edfs} == {
        "sub-1",
        "sub-4",
        "sub-7",
        "sub-10",
        "sub-13",
        "sub-16",
    }


@pytest.mark.parametrize(
    "field,value", [("verification", "head_only"), ("readback_bytes", 1), ("sha256", "wrong")]
)
def test_backup_gate_rejects_unverified_or_different_bytes(tmp_path, field, value):
    f = dict(
        key="key",
        sha256="expected",
        verification="full_get_sha256_verified",
        bytes=10,
        readback_bytes=10,
    )
    f[field] = value
    p = tmp_path / "receipt.json"
    p.write_text(json.dumps(dict(status="completed", totals=dict(failed_files=0), files=[f])))
    with pytest.raises(ValueError, match="mismatch"):
        queue.verified_receipt(p, "key", "expected")


def test_partial_reservation_blocks_before_cuda_or_fit(tmp_path):
    _, _, job = queue.check_gate()
    output = tmp_path / "reserved"
    output.mkdir()
    job = dict(job, output=str(output))
    with pytest.raises(RuntimeError, match="never automatically refit"):
        queue.execute(job, {}, tmp_path / "no-data", tmp_path / "no-receipt")


def fake_complete_output(tmp_path):
    _, _, job = queue.check_gate()
    output = tmp_path / "complete"
    output.mkdir()
    for name in queue.FILES:
        (output / name).write_bytes(b"software-validation-fixture")
    record = dict(
        job_id=job["job_id"],
        status="fit_saved",
        query_rows_loaded=0,
        checkpoint_sha256=queue.digest(output / "weights.pt"),
    )
    (output / "fit_result.json").write_text(json.dumps(record))
    return output, dict(job, output=str(output))


def test_complete_reservation_only_repackages_no_gpu_fit(tmp_path):
    output, job = fake_complete_output(tmp_path)
    first = queue.execute(job, {}, tmp_path / "no-data", tmp_path / "no-receipt")
    second = queue.execute(job, {}, tmp_path / "no-data", tmp_path / "no-receipt")
    assert first == second
    assert first["status"] == "fit_saved_private_backup_pending"
    assert first["R2_backup_verified"] is False


def test_existing_archive_corruption_never_overwritten(tmp_path):
    output, job = fake_complete_output(tmp_path)
    result = queue.package(output, job)
    archive = Path(result["archive"])
    archive.write_bytes(b"preserved corrupt archive")
    with pytest.raises(Exception):
        queue.package(output, job)
    assert archive.read_bytes() == b"preserved corrupt archive"


def test_unexpected_failure_files_block_success_packaging(tmp_path):
    output, job = fake_complete_output(tmp_path)
    (output / "failure_traceback.txt").write_text("failed; inspect")
    with pytest.raises(ValueError, match="Unexpected"):
        queue.package(output, job)


def test_actual_runtime_rejects_extra_fit_scope(tmp_path, monkeypatch):
    config = queue.json_file(queue.RUNTIME)
    config["maximum_new_fits"] = 18
    changed = tmp_path / "runtime.json"
    changed.write_text(json.dumps(config))
    monkeypatch.setattr(queue, "RUNTIME", changed)
    with pytest.raises(ValueError, match="scope gate"):
        queue.check_gate()


def test_shared_gpu_lock_blocks_dispatch_before_gate_or_training(tmp_path, monkeypatch):
    import fcntl
    import sys

    lock = tmp_path / "gpu.lock"
    monkeypatch.setattr(queue, "LOCK", lock)
    monkeypatch.setattr(
        sys, "argv", ["queue", "--execute-next", "--parent-acknowledge-replay-backup"]
    )
    monkeypatch.setattr(queue.subprocess, "check_output", lambda *a, **k: "")
    monkeypatch.setattr(queue, "check_gate", lambda: pytest.fail("Gate reached while GPU locked"))
    with lock.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            queue.main()


def test_parent_replay_backup_ack_is_required_before_execution(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["queue", "--execute-next"])
    with pytest.raises(ValueError, match="Parent must review"):
        queue.main()


def test_changed_checkpoint_blocks_repackaging(tmp_path):
    output, job = fake_complete_output(tmp_path)
    (output / "weights.pt").write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="Checkpoint changed"):
        queue.package(output, job)
    assert not output.with_suffix(".tar").exists()
