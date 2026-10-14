"""Recovery evidence must reject corrupt bytes and unsupported completion claims."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("download_recovery", ROOT / "scripts/audit_download_recovery.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def evidence(tmp_path):
    relative = "sub-01/eeg/sub-01_task-mi2d_run-01_eeg.eeg"
    entry = {"relative_path": relative, "key": MODULE.MIND_PREFIX + "/MIND_BIDS/" + relative,
             "status": "uploaded_content_verified", "verification": "full_get_sha256_verified",
             "head_http_status": 200, "get_http_status": 200, "bytes": 7,
             "readback_bytes": 7, "uploaded_bytes": 7, "sha256": "a" * 64}
    source = {"official_size_and_md5_pass": True, "relative_path": relative, "sha256": "a" * 64,
              "bytes": 7, "md5_actual": "0" * 31 + "1", "official_md5_original": "1",
              "official_md5_normalized_32hex": "0" * 31 + "1",
              "record": {"path": "/V4/MIND_BIDS/" + relative, "size": "7"}}
    dump(tmp_path / "source_receipts" / (relative + ".json"), source)
    receipt = tmp_path / "r2_receipts" / (relative + ".json")
    dump(receipt, entry)
    return relative, entry, receipt


def test_complete_get_requires_actual_readback_length(tmp_path):
    _, entry, path = evidence(tmp_path)
    bad = {**entry, "readback_bytes": 6}
    with pytest.raises(ValueError, match="complete readback"):
        MODULE.normalize_mind([(path, bad)], source_root=tmp_path)


@pytest.mark.parametrize("change", [{"status": "failed"}, {"head_http_status": 404},
                                    {"verification": "head_length_and_sha256_metadata_verified"},
                                    {"get_http_status": 503}])
def test_remote_failures_and_head_only_are_not_complete(tmp_path, change):
    _, entry, path = evidence(tmp_path)
    with pytest.raises(ValueError):
        MODULE.normalize_mind([(path, {**entry, **change})], source_root=tmp_path)


def test_changed_key_identity_and_duplicate_key_are_rejected(tmp_path):
    _, entry, path = evidence(tmp_path)
    with pytest.raises(ValueError, match="identity"):
        MODULE.normalize_mind([(path, {**entry, "key": entry["key"].replace("sub-01/eeg/", "sub-02/eeg/")})], source_root=tmp_path)
    with pytest.raises(ValueError, match="unique"):
        MODULE.normalize_mind([(path, entry), (path, copy.deepcopy(entry))], source_root=tmp_path)


def test_official_digest_left_zero_is_checked_not_etag(tmp_path):
    relative, entry, path = evidence(tmp_path)
    result = MODULE.normalize_mind([(path, entry)], source_root=tmp_path)
    assert result["totals"]["verified_files"] == 1
    source_path = tmp_path / "source_receipts" / (relative + ".json")
    source = json.loads(source_path.read_text())
    source["official_md5_original"] = "2"
    dump(source_path, source)
    with pytest.raises(ValueError, match="official source"):
        MODULE.normalize_mind([(path, entry)], source_root=tmp_path)


def test_original_receipt_hash_and_local_bytes_are_independent_checks(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"good")
    expected = MODULE.sha256(path)
    assert MODULE.local_check((path, {"bytes": 4, "sha256": expected}))["classification"] == "A"
    path.write_bytes(b"evil")
    assert MODULE.local_check((path, {"bytes": 4, "sha256": expected}))["classification"] == "E"
    with pytest.raises(ValueError, match="Historical evidence hash"):
        MODULE.verify_reference(path, expected)
    path.unlink()
    assert MODULE.local_check((path, {"bytes": 4, "sha256": expected}))["classification"] == "C"


def test_missing_event_ledger_never_establishes_closed_run(tmp_path):
    relative, entry, _ = evidence(tmp_path)
    run = tmp_path / "runs" / "run01"
    closure = {"closed": True, "status": "completed", "run_name": "run01",
               "all_sources_official_size_md5_pass": True,
               "all_objects_head_and_full_get_sha256_pass": True,
               "source_relative_paths": [relative]}
    dump(run / "closed.json", closure)
    dump(run / "audit.json", {"all_integrity_checks_pass": True, "all_values_finite": True,
                               "source_file_sha256": "a" * 64, "source_events": {"source_event_count": 2}})
    with pytest.raises(FileNotFoundError):
        MODULE.closed_run_check(run / "closed.json", {relative: entry}, source_root=tmp_path)
    dump(run / "source_events.json", [{"event_id": "same"}, {"event_id": "same"}])
    with pytest.raises(ValueError, match="event"):
        MODULE.closed_run_check(run / "closed.json", {relative: entry}, source_root=tmp_path)
