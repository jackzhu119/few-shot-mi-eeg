"""No-network restoration checks; tiny synthetic files never represent EEG."""

import copy
import fcntl
import hashlib
import json
from types import SimpleNamespace

import pytest

import fetch_kumar_remaining_source_https as module


def test_frozen_metadata_scope_excludes_development_and_query():
    plan = module.load_plan()
    assert len(plan["files"]) == 253
    assert sum(e["size"] for e in plan["files"]) == 196740994
    signals = [e for e in plan["files"] if e["path"].endswith(".edf")]
    assert len(signals) == 36
    assert {e["path"].split("/")[0] for e in signals} == module.SOURCE_SUBJECTS
    assert all("/ses-0/" in e["path"] for e in signals)
    assert plan["query_access"] is False


def test_current_real_manifest_blocks_download_before_any_filesystem_work(tmp_path):
    root = tmp_path / "never-created"
    receipt = tmp_path / "never-created-receipt.json"
    with pytest.raises(PermissionError, match="reviewed restoration freeze"):
        module.restore(root, receipt)
    assert not root.exists()
    assert not receipt.exists()


@pytest.fixture
def synthetic_plan(tmp_path, monkeypatch):
    payloads = {
        "dataset_description.json": json.dumps({"License": "CC-BY-4.0", "Version": "1.0.5"}).encode(),
        "synthetic.edf": b"software-validation-only-not-eeg",
    }
    files = []
    for path, body in payloads.items():
        digest = hashlib.sha256(body).hexdigest()
        files.append(dict(path=path, size=len(body), checksum_algorithm="sha256",
                          checksum=digest, expected_sha256=digest))
    config = tmp_path / "synthetic_config.json"
    config.write_text("software_validation_only")
    plan = dict(files=files, source_plan_sha256="1" * 64, timeout_seconds=60,
                execution_enabled=True)
    monkeypatch.setattr(module, "CONFIG", config)
    monkeypatch.setattr(module, "load_plan", lambda: copy.deepcopy(plan))
    root = tmp_path / "inputs"
    receipt = tmp_path / "receipt.json"
    calls = []

    def fake_fetch(target_root, entry, deadline):
        calls.append(entry["path"])
        target = target_root / entry["path"]
        target.write_bytes(payloads[entry["path"]])
        return dict(path=entry["path"], status="downloaded_sha256_verified",
                    sha256=entry["expected_sha256"])

    monkeypatch.setattr(module, "fetch_one", fake_fetch)
    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: SimpleNamespace(free=10 * 1024**3))
    return SimpleNamespace(plan=plan, root=root, receipt=receipt, calls=calls, payloads=payloads)


def test_plan_only_never_makes_directory_or_downloads(synthetic_plan, capsys):
    fixture = synthetic_plan
    module.main(["--data-root", str(fixture.root), "--receipt", str(fixture.receipt)])
    assert json.loads(capsys.readouterr().out)["status"] == "plan_only"
    assert not fixture.root.exists()
    assert not fixture.receipt.exists()
    assert not fixture.calls


def test_prepared_manifest_cannot_restore(synthetic_plan):
    fixture = synthetic_plan
    fixture.plan["execution_enabled"] = False
    with pytest.raises(PermissionError, match="reviewed restoration freeze"):
        module.restore(fixture.root, fixture.receipt)
    assert not fixture.root.exists()
    assert not fixture.calls


def test_metadata_first_complete_receipt_and_every_call_rehash(synthetic_plan, monkeypatch):
    fixture = synthetic_plan
    module.restore(fixture.root, fixture.receipt)
    assert fixture.calls == ["dataset_description.json", "synthetic.edf"]
    report = json.loads(fixture.receipt.read_text())
    assert report["status"] == module.COMPLETE
    assert report["query_access"] is False
    assert report["real_training_executed"] is False
    assert report["input_manifest_sha256"] == fixture.plan["source_plan_sha256"]
    calls = []
    real_verify = module.verify

    def tracked_verify(path, entry):
        calls.append(entry["path"])
        return real_verify(path, entry)

    monkeypatch.setattr(module, "verify", tracked_verify)
    module.verify_all(fixture.root, fixture.receipt)
    module.verify_all(fixture.root, fixture.receipt)
    assert calls == list(fixture.payloads) * 2
    before = fixture.receipt.read_bytes()
    outcome = module.restore(fixture.root, fixture.receipt)
    assert outcome["status"] == "existing_complete_receipt_and_all_files_reverified"
    assert fixture.receipt.read_bytes() == before
    assert fixture.calls == list(fixture.payloads)


@pytest.mark.parametrize("change", ["duplicate", "bad_hash", "wrong_input_manifest", "failed", "query"])
def test_full_receipt_identity_is_required(synthetic_plan, change):
    fixture = synthetic_plan
    module.restore(fixture.root, fixture.receipt)
    report = json.loads(fixture.receipt.read_text())
    if change == "duplicate":
        report["records"].append(report["records"][0])
    elif change == "bad_hash":
        report["records"][0]["sha256"] = "0" * 64
    elif change == "wrong_input_manifest":
        report["input_manifest_sha256"] = "0" * 64
    elif change == "failed":
        report["status"] = "failed_preserved_inputs"
    else:
        report["query_access"] = True
    fixture.receipt.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="receipt|Receipt"):
        module.verify_all(fixture.root, fixture.receipt)


def test_file_changed_after_complete_receipt_fails_and_is_preserved(synthetic_plan):
    fixture = synthetic_plan
    module.restore(fixture.root, fixture.receipt)
    before = fixture.receipt.read_bytes()
    (fixture.root / "synthetic.edf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="mismatch"):
        module.restore(fixture.root, fixture.receipt)
    assert fixture.receipt.read_bytes() == before
    assert (fixture.root / "synthetic.edf").read_bytes() == b"changed"


def test_symlink_input_is_rejected_even_when_bytes_match(synthetic_plan, tmp_path):
    fixture = synthetic_plan
    module.restore(fixture.root, fixture.receipt)
    target = fixture.root / "synthetic.edf"
    outside = tmp_path / "outside"
    target.rename(outside)
    target.symlink_to(outside)
    with pytest.raises(ValueError, match="Symlink|escapes data root"):
        module.verify_all(fixture.root, fixture.receipt)


def test_bad_license_stops_before_any_signal_and_has_no_retry(synthetic_plan):
    fixture = synthetic_plan
    fixture.payloads["dataset_description.json"] = b'{"License":"wrong","Version":"1.0.5"}'
    with pytest.raises(SystemExit, match="No automatic retry"):
        module.restore(fixture.root, fixture.receipt)
    assert fixture.calls == ["dataset_description.json"]
    report = json.loads(fixture.receipt.read_text())
    assert report["status"] == "failed_preserved_inputs"
    assert (fixture.root / "dataset_description.json").exists()
    before = fixture.receipt.read_bytes()
    with pytest.raises(ValueError, match="complete"):
        module.restore(fixture.root, fixture.receipt)
    assert fixture.receipt.read_bytes() == before


def test_failure_preserves_partial_and_sanitizes_url_secrets(synthetic_plan, monkeypatch):
    fixture = synthetic_plan

    def interrupted(root, entry, deadline):
        partial = root / (entry["path"] + ".partial")
        partial.write_bytes(b"software-validation-only-partial")
        raise ValueError("HTTPS failed https://example.invalid/object?secret=never-store")

    monkeypatch.setattr(module, "fetch_one", interrupted)
    with pytest.raises(SystemExit, match="preserve"):
        module.restore(fixture.root, fixture.receipt)
    assert (fixture.root / "dataset_description.json.partial").exists()
    report_bytes = fixture.receipt.read_text()
    assert "never-store" not in report_bytes
    assert json.loads(report_bytes)["status"] == "failed_preserved_inputs"


def test_shared_download_lock_and_low_disk_block_before_download(synthetic_plan, monkeypatch):
    fixture = synthetic_plan
    fixture.root.mkdir()
    with (fixture.root / ".queue-download.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            module.restore(fixture.root, fixture.receipt)
    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(RuntimeError, match="2 GiB"):
        module.restore(fixture.root, fixture.receipt)
    assert not fixture.calls
    assert not fixture.receipt.exists()


def test_timeout_preserves_receipt_without_starting_fetch(synthetic_plan, monkeypatch):
    fixture = synthetic_plan
    times = iter([0, 100])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(times))
    with pytest.raises(SystemExit):
        module.restore(fixture.root, fixture.receipt)
    assert not fixture.calls
    assert json.loads(fixture.receipt.read_text())["status"] == "failed_preserved_inputs"


def test_pending_receipt_is_not_erased(synthetic_plan):
    fixture = synthetic_plan
    pending = fixture.receipt.with_name(fixture.receipt.name + ".pending")
    pending.write_text("preserved interrupted atomic publication")
    with pytest.raises(FileExistsError, match="pending receipt"):
        module.restore(fixture.root, fixture.receipt)
    assert pending.read_text() == "preserved interrupted atomic publication"
    assert not fixture.calls
