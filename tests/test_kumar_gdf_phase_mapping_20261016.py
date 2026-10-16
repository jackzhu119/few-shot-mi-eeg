"""Synthetic metadata checks; no decoder or real EEG is executed."""

import importlib.util
import io
import json
import struct
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_kumar_gdf_phase_mapping_20261016.py"
SPEC = importlib.util.spec_from_file_location("gdf_phase_mapping", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def metadata():
    return {"sample_rate": 512.0, "n_samples": 10_000}


def events(codes=(770, 7701, 7702), positions=(100, 868, 2_000)):
    return [
        {"event_row": index + 1, "original_pos_1based": position + 1,
         "sample_0based": position, "code": code}
        for index, (position, code) in enumerate(zip(positions, codes))
    ]


def trials():
    return [{"trial_id": "synthetic/ses-1/run-0/row-1", "subject": "synthetic",
             "session": "ses-1", "run": "run-0", "source_row": 1,
             "label": "right_hand", "source_file": "synthetic.edf", "start_sample": 100,
             "stop_sample_exclusive": 2660, "sample_count": 2560}]


def test_exact_sample_and_class_mapping_precedes_phase_association():
    rows = MODULE.phase_rows(events(), trials(), metadata(), True)
    assert rows[0]["cue_mapping_exact"] and rows[0]["phase_mapping_success"]
    assert rows[0]["original_window_active_seconds"] == (2000 - 868) / 512
    assert rows[0]["original_window_pre_task_seconds"] == 1.5
    assert rows[0]["original_window_post_task_seconds"] == 660 / 512
    assert rows[0]["task_start_2s_eligible"]


@pytest.mark.parametrize("field,value", [("start_sample", 101), ("label", "left_hand")])
def test_sample_or_class_mismatch_stops(field, value):
    trial = trials()
    trial[0][field] = value
    with pytest.raises(ValueError, match="correspondence"):
        MODULE.phase_rows(events(), trial, metadata(), True)


def test_missing_end_is_ambiguous_not_inferred_from_next_cue_or_boundary():
    row = MODULE.phase_rows(events((770, 7701), (100, 868)), trials(), metadata(), True)[0]
    assert not row["phase_mapping_success"]
    assert row["task_active_seconds"] is None
    assert not row["task_start_2s_eligible"]
    assert row["ambiguity_or_exclusion"] == "task_end_count_0"


def test_cross_class_end_is_not_accepted():
    row = MODULE.phase_rows(events((770, 7701, 7692)), trials(), metadata(), True)[0]
    assert not row["phase_mapping_success"]
    assert "task_end_class_disagrees" in row["ambiguity_or_exclusion"]


def test_duplicate_start_is_ambiguous():
    row = MODULE.phase_rows(events((770, 7701, 7701, 7702), (100, 868, 900, 2000)), trials(), metadata(), True)[0]
    assert not row["phase_mapping_success"]
    assert "task_start_count_2" in row["ambiguity_or_exclusion"]


def test_short_task_kept_with_explicit_window_exclusion():
    row = MODULE.phase_rows(events(positions=(100, 868, 1100)), trials(), metadata(), True)[0]
    assert row["phase_mapping_success"]
    assert not row["task_start_2s_eligible"]
    assert not row["variable_active_minimum1s_eligible"]
    assert row["task_active_seconds"] == 232 / 512


def test_online_7693_wording_does_not_invent_correct_hit():
    row = MODULE.phase_rows(events((770, 7701, 7703)), trials(), metadata(), True)[0]
    assert row["task_end_literal_category"] == "online_cue_delivered_codebook_wording"


def test_rest_and_recording_triggers_are_kept_distinct_from_physical_boundary():
    stream = events((32766, 1000, 770, 7701, 7702, 1000, 32766),
                    (1, 20, 100, 868, 2000, 2500, 9000))
    row = MODULE.phase_rows(stream, trials(), metadata(), True)[0]
    assert row["preceding_trial_rest_1000_sample_0based"] == 20
    assert row["following_trial_rest_1000_sample_0based"] == 2500
    assert row["first_recording_trigger_32766_sample_0based"] == 1
    assert row["last_recording_trigger_32766_sample_0based"] == 9000
    assert row["recording_stop_sample_exclusive"] == 10000
    assert row["original_window_crosses_following_trial_rest_marker"]
    assert row["task_start_2s_eligible"]


def test_event_parser_one_based_index_conversion():
    payload = b"\x01\x02\x00\x00" + struct.pack("<fIIHH", 512, 101, 2001, 770, 7701)
    result = MODULE.parse_events(payload, metadata())
    assert [row["sample_0based"] for row in result["events"]] == [100, 2000]


@pytest.mark.parametrize("variant", ["truncated", "trailing", "clock", "outside", "nonmonotone"])
def test_event_parser_fails_closed(variant):
    rate = 256 if variant == "clock" else 512
    positions = (2001, 101) if variant == "nonmonotone" else (101, 20_001 if variant == "outside" else 2001)
    payload = b"\x01\x02\x00\x00" + struct.pack("<fIIHH", rate, *positions, 770, 7701)
    if variant == "truncated":
        payload = payload[:-1]
    if variant == "trailing":
        payload += b"\x00"
    with pytest.raises(ValueError):
        MODULE.parse_events(payload, metadata())


def test_fixed_header_requires_reviewed_version():
    with pytest.raises(ValueError, match="GDF 2.00"):
        MODULE.parse_fixed_header(b"GDF 2.51" + bytes(248))


def test_server_ignoring_range_is_not_downloaded(monkeypatch, tmp_path):
    class Response:
        status_code = 200
        headers = {"Content-Length": "10000000"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        @property
        def raw(self):
            raise AssertionError("A non-206 body must never be read")

    monkeypatch.setattr(MODULE.requests, "get", lambda *args, **kwargs: Response())
    reader = MODULE.RangeReader(tmp_path, 1000)
    row = {"size": 10_000_000, "url": "https://example.invalid/synthetic.gdf",
           "path": "synthetic.gdf", "checksum": "0" * 64}
    with pytest.raises(ValueError, match="HTTP range"):
        reader.fetch(row, 0, 255, tmp_path / "header.bin")
    assert not (tmp_path / "header.bin").exists()


def test_global_metadata_budget_stops_before_request(monkeypatch, tmp_path):
    def unexpected(*args, **kwargs):
        raise AssertionError("No HTTP request is permitted after budget failure")

    monkeypatch.setattr(MODULE.requests, "get", unexpected)
    reader = MODULE.RangeReader(tmp_path, 255)
    with pytest.raises(ValueError, match="budget"):
        reader.fetch({"size": 10_000_000}, 0, 255, tmp_path / "header.bin")


def make_saved_run(tmp_path):
    fixed = bytearray(256)
    fixed[:8] = b"GDF 2.00"
    struct.pack_into("<Q", fixed, 168, 738000 * 2**32)
    struct.pack_into("<H", fixed, 184, 2)
    struct.pack_into("<qIIH", fixed, 236, 10, 1, 1, 1)
    variable = bytearray(256)
    variable[:16] = b"C3              "
    struct.pack_into("<II", variable, 216, 512, 16)
    meta = MODULE.parse_variable_header(variable, MODULE.parse_fixed_header(fixed))
    tail = b"\x01\x02\x00\x00" + struct.pack("<fIIHH", 512, 101, 2001, 770, 7701)
    row = {"path": "synthetic.gdf", "url": "https://example.invalid/synthetic.gdf",
           "size": meta["event_table_offset"] + len(tail), "checksum": "0" * 64}
    decoded = {"index": 0, "source": row, "metadata": meta,
               "event_table": MODULE.parse_events(tail, meta)}
    spans = [("fixed_header", bytes(fixed), 0), ("variable_header", bytes(variable), 256),
             ("event_table", tail, meta["event_table_offset"])]
    for name, payload, start in spans:
        end = start + len(payload) - 1
        (tmp_path / f"{name}.bin").write_bytes(payload)
        MODULE.exclusive_json(tmp_path / f"{name}.receipt.json", {
            "status": 206, "url": row["url"], "official_path": row["path"],
            "expected_total_bytes": row["size"], "range_start": start, "range_end": end,
            "official_whole_file_sha256_not_verified_by_ranges": row["checksum"],
            "content_range": f"bytes {start}-{end}/{row['size']}", "range_bytes": len(payload),
            "range_sha256": MODULE.sha256(payload), "etag": '"synthetic"',
        })
    MODULE.exclusive_json(tmp_path / "decoded_metadata.json", decoded)
    return row, decoded


def test_saved_complete_run_rehashes_and_reparses_without_network(tmp_path, monkeypatch):
    row, expected = make_saved_run(tmp_path)
    monkeypatch.setattr(MODULE.requests, "get", lambda *args, **kwargs: pytest.fail("offline reuse requested HTTP"))
    observed, amount = MODULE.validate_saved_run(tmp_path, row, 0)
    assert observed == expected
    assert amount == 532


@pytest.mark.parametrize("corruption", ["body", "etag", "range", "whole_checksum", "decoded"])
def test_saved_evidence_corruption_fails_closed(tmp_path, corruption):
    row, _ = make_saved_run(tmp_path)
    if corruption == "body":
        (tmp_path / "event_table.bin").write_bytes(b"\0" * 20)
    elif corruption == "decoded":
        path = tmp_path / "decoded_metadata.json"
        decoded = json.loads(path.read_bytes())
        decoded["metadata"]["n_samples"] = 20_000
        path.write_text(json.dumps(decoded))
    else:
        path = tmp_path / "event_table.receipt.json"
        receipt = json.loads(path.read_bytes())
        if corruption == "etag":
            receipt["etag"] = '"different"'
        elif corruption == "range":
            receipt["range_start"] -= 1
            receipt["range_end"] -= 1
            receipt["content_range"] = f"bytes {receipt['range_start']}-{receipt['range_end']}/{row['size']}"
        else:
            receipt["official_whole_file_sha256_not_verified_by_ranges"] = "f" * 64
        path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        MODULE.validate_saved_run(tmp_path, row, 0)


def network_policy():
    return {"maximum_attempts_per_range": 3, "maximum_operation_seconds": 600,
            "retryable_http_statuses": [502, 503, 504], "backoff_seconds": [1, 3],
            "retry_transport_exceptions": True, "scientific_fit_retries": 0}


def response(status, *, content_range="bytes 0-255/1000", length="256", etag='"stable"'):
    class Response:
        status_code = status
        headers = {"Content-Range": content_range, "Content-Length": length, "ETag": etag}
        raw = io.BytesIO(bytes(256))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    return Response()


def network_row():
    return {"size": 1000, "url": "https://example.invalid/synthetic.gdf",
            "path": "synthetic.gdf", "checksum": "0" * 64}


def test_versioned_transport_retries_only_transient_statuses_then_exact206(monkeypatch, tmp_path):
    replies = iter([response(503), response(502), response(206)])
    calls, delays = [], []

    def get(*args, **kwargs):
        calls.append(True)
        return next(replies)

    monkeypatch.setattr(MODULE.requests, "get", get)
    monkeypatch.setattr(MODULE.time, "sleep", delays.append)
    reader = MODULE.RangeReader(tmp_path, 1024, network_policy())
    payload, receipt = reader.fetch(network_row(), 0, 255, tmp_path / "range.bin")
    assert len(payload) == 256 and receipt["attempt"] == 3
    assert len(calls) == 3 and delays == [1, 3]
    assert len(list(tmp_path.glob("*.attempt*.json"))) == 3
    assert reader.http_requests == 3 and reader.acquired_body_bytes == 256


@pytest.mark.parametrize("bad", [response(200), response(403), response(206, content_range="bytes 1-256/1000"), response(206, length="257"), response(206, etag=None)])
def test_transport_policy_never_retries_access_or_integrity_failures(monkeypatch, tmp_path, bad):
    calls = []

    def get(*args, **kwargs):
        calls.append(True)
        return bad

    monkeypatch.setattr(MODULE.requests, "get", get)
    reader = MODULE.RangeReader(tmp_path, 1024, network_policy())
    with pytest.raises(ValueError):
        reader.fetch(network_row(), 0, 255, tmp_path / "range.bin")
    assert len(calls) == 1
    assert not (tmp_path / "range.bin").exists()


def test_transient_transport_stops_after_three_actual_attempts(monkeypatch, tmp_path):
    calls = []

    def get(*args, **kwargs):
        calls.append(True)
        raise MODULE.requests.exceptions.ConnectTimeout("synthetic transient")

    monkeypatch.setattr(MODULE.requests, "get", get)
    monkeypatch.setattr(MODULE.time, "sleep", lambda seconds: None)
    reader = MODULE.RangeReader(tmp_path, 1024, network_policy())
    with pytest.raises(ValueError, match="transport"):
        reader.fetch(network_row(), 0, 255, tmp_path / "range.bin")
    assert len(calls) == 3
    assert len(list(tmp_path.glob("*.attempt*.json"))) == 3
    assert not (tmp_path / "range.bin").exists()


def test_expired_metadata_deadline_makes_no_request(monkeypatch, tmp_path):
    reader = MODULE.RangeReader(tmp_path, 1024, network_policy())
    reader.deadline = MODULE.time.monotonic() - 1
    monkeypatch.setattr(MODULE.requests, "get", lambda *args, **kwargs: pytest.fail("deadline ignored"))
    with pytest.raises(TimeoutError):
        reader.fetch(network_row(), 0, 255, tmp_path / "range.bin")
