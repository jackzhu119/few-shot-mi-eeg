"""Network-free MIND ingestion checks using a tiny synthetic BrainVision fixture."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("mind_source_audit", SCRIPTS / "audit_mind_source.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
FETCH_SPEC = importlib.util.spec_from_file_location("mind_fetch", SCRIPTS / "fetch_mind2026_r2.py")
fetch = importlib.util.module_from_spec(FETCH_SPEC)
FETCH_SPEC.loader.exec_module(fetch)


def write_tsv(path, records):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(records)


@pytest.fixture
def brainvision_run(tmp_path):
    """130 samples at 10 Hz, with native boundary and three source events."""
    relative = "sub-04/eeg/sub-04_task-motorimagery_run-1_eeg.vhdr"
    header = tmp_path / relative
    header.parent.mkdir(parents=True)
    stem = header.name.removesuffix("_eeg.vhdr")
    values = np.column_stack((np.arange(130) - 65, np.zeros(130))).astype("<f4")
    header.with_suffix(".eeg").write_bytes(values.tobytes())
    header.write_text(
        "Brain Vision Data Exchange Header File Version 1.0\n"
        "[Common Infos]\n"
        f"DataFile={header.with_suffix('.eeg').name}\n"
        f"MarkerFile={header.with_suffix('.vmrk').name}\n"
        "DataFormat=BINARY\nDataOrientation=MULTIPLEXED\n"
        "NumberOfChannels=2\nSamplingInterval=100000\n"
        "[Binary Infos]\nBinaryFormat=IEEE_FLOAT_32\n"
        "[Channel Infos]\nCh1=C3,,1,uV\nCh2=C4,,1,uV\n"
    )
    header.with_suffix(".vmrk").write_text(
        "Brain Vision Data Exchange Marker File, Version 1.0\n"
        f"[Common Infos]\nDataFile={header.with_suffix('.eeg').name}\n"
        "[Marker Infos]\n"
        "Mk1=New Segment,,1,1,0,20261012000000000000\n"
        "Mk2=Stimulus,1,1,0,0\n"
        "Mk3=Stimulus,3,11,0,0\n"
        "Mk4=Stimulus,4,11,0,0\n"
    )
    events = [
        {"onset": "0", "duration": "1", "trial_type": "rest_open", "value": "1"},
        {"onset": "1", "duration": "0", "trial_type": "mi_start", "value": "3"},
        {"onset": "1", "duration": "10", "trial_type": "mi_l2r", "value": "4"},
    ]
    write_tsv(header.parent / f"{stem}_events.tsv", events)
    write_tsv(header.parent / f"{stem}_channels.tsv", [
        {"name": name, "type": "EEG", "units": "uV", "sampling_frequency": "10"}
        for name in ("C3", "C4")
    ])
    (header.parent / f"{stem}_eeg.json").write_text(json.dumps({
        "EEGChannelCount": 2, "SamplingFrequency": 10,
    }))
    (header.parent / f"{stem}_events.json").write_text(json.dumps({
        "trial_type": {"Levels": {row["trial_type"]: row["trial_type"] for row in events}},
    }))
    return tmp_path, relative, values.T.astype(float) * 1e-6


def event_path(root, relative):
    header = root / relative
    return header.parent / (header.name.removesuffix("_eeg.vhdr") + "_events.tsv")


@pytest.mark.parametrize("value,expected", [
    ("a", "0" * 31 + "a"),
    ("0ABC", "0" * 29 + "abc"),
    ("A" * 32, "a" * 32),
])
def test_official_short_md5_is_explicitly_zero_padded(value, expected):
    assert audit.normalized_md5(value) == expected


@pytest.mark.parametrize("value", ["", "g", "a" * 33, " abc", "0xabc", "abc\n"])
def test_md5_normalization_refuses_malformed_official_identity(value):
    with pytest.raises(ValueError, match="hexadecimal"):
        audit.normalized_md5(value)


def test_source_verification_preserves_official_short_digest_and_ignores_etag(tmp_path):
    # Find a tiny fixture whose MD5 actually starts with zero; avoid a mocked hash.
    body = next(str(i).encode() for i in range(1000)
                if hashlib.md5(str(i).encode(), usedforsecurity=False).hexdigest().startswith("0"))
    path = tmp_path / "small.eeg"
    path.write_bytes(body)
    expected = hashlib.md5(body, usedforsecurity=False).hexdigest()
    result = audit.verify_source(path, {"size": len(body), "md5": expected.lstrip("0"),
                                        "etag": "opaque-multipart-etag-12"})
    assert result["official_md5_original"] == expected.lstrip("0")
    assert result["official_md5_normalized_32hex"] == expected
    assert result["official_size_and_md5_pass"] is True
    assert result["etag_used_as_checksum"] is False
    assert result["sha256"] == hashlib.sha256(body).hexdigest()
    with pytest.raises(ValueError, match="full MD5 mismatch"):
        audit.verify_source(path, {"size": len(body), "md5": "1" * 32})
    with pytest.raises(ValueError, match="length"):
        audit.verify_source(path, {"size": len(body) + 1, "md5": expected})


def test_streamed_signal_and_task_hashes_are_independent_of_block_boundaries(brainvision_run):
    root, relative, values = brainvision_run
    small, small_events = audit.audit_run(root, relative, block_samples=7)
    large, large_events = audit.audit_run(root, relative, block_samples=64)
    expected = hashlib.sha256(audit.numeric_bytes(values)).hexdigest()
    assert small["whole_signal_numeric_sha256"] == large["whole_signal_numeric_sha256"] == expected
    task_hash = hashlib.sha256(audit.numeric_bytes(values[:, 10:110])).hexdigest()
    assert small_events[-1]["source_task_numeric_sha256"] == task_hash
    assert large_events[-1]["source_task_numeric_sha256"] == task_hash
    assert small["channel_rms_volts"] == pytest.approx(large["channel_rms_volts"])
    assert small["zero_channels"] == small["constant_channels"] == ["C4"]
    assert small["preload"] is False
    assert all(row["analysis_window_selected"] is False for row in small_events)


def test_native_new_segment_is_preserved_but_excluded_from_event_comparison(brainvision_run):
    root, relative, _ = brainvision_run
    result, events = audit.audit_run(root, relative, block_samples=13)
    comparison = result["source_events"]
    assert result["all_integrity_checks_pass"] is True
    assert comparison["source_event_count"] == comparison["mne_annotation_count"] == 3
    assert comparison["native_marker_count"] == 4
    assert comparison["native_event_marker_count"] == 3
    assert comparison["native_segment_boundary_count"] == 1
    assert result["native_markers"][0] == {
        "marker_number": 1, "marker_type": "New Segment", "description": "",
        "native_position_1based": 1, "native_sample_0based": 0, "native_size_samples": 1,
        "channel": 0, "date": "20261012000000000000",
    }
    assert len(events) == 3
    assert events[-1]["source_values"]["duration"] == "10"
    assert events[-1]["native_duration_samples"] == 100
    assert events[-1]["native_stop_sample_exclusive"] == 110
    assert result["native_markers"][-1]["native_size_samples"] == 0


@pytest.mark.parametrize("field,value", [
    ("name", "wrong-channel"), ("type", "EOG"), ("units", "V"),
    ("sampling_frequency", "11"),
])
def test_channel_metadata_disagreement_refuses_signal_audit(brainvision_run, field, value):
    root, relative, _ = brainvision_run
    header = root / relative
    path = header.parent / (header.name.removesuffix("_eeg.vhdr") + "_channels.tsv")
    records = audit.rows(path)
    records[0][field] = value
    write_tsv(path, records)
    with pytest.raises(ValueError, match="metadata mismatch"):
        audit.audit_run(root, relative)


@pytest.mark.parametrize("field,value", [("EEGChannelCount", 3), ("SamplingFrequency", 11)])
def test_eeg_json_channel_count_and_clock_cannot_disagree(brainvision_run, field, value):
    root, relative, _ = brainvision_run
    header = root / relative
    path = header.with_suffix(".json")
    metadata = json.loads(path.read_text())
    metadata[field] = value
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="metadata mismatch"):
        audit.audit_run(root, relative)


def test_native_header_units_cannot_disagree_with_bids_units(brainvision_run):
    root, relative, _ = brainvision_run
    header = root / relative
    header.write_text(header.read_text().replace("Ch1=C3,,1,uV", "Ch1=C3,,1,V"))
    with pytest.raises(ValueError, match="native binary, channel, unit or clock mismatch"):
        audit.audit_run(root, relative)


def test_partial_native_sample_bytes_cannot_be_ignored(brainvision_run):
    root, relative, _ = brainvision_run
    signal = (root / relative).with_suffix(".eeg")
    signal.write_bytes(signal.read_bytes() + b"x")
    with pytest.raises(ValueError, match="native binary, channel, unit or clock mismatch"):
        audit.audit_run(root, relative)


def test_event_mismatch_retains_native_rows_and_qualifies_source_without_repair(brainvision_run):
    root, relative, _ = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records[-1].update(value="9", trial_type="mi_unknown", duration="12.1")
    write_tsv(path, records)
    result, events = audit.audit_run(root, relative, block_samples=19)
    event = events[-1]
    assert event["source_values"] == records[-1]
    assert event["native_start_sample_0based"] == 10
    assert event["native_stop_sample_exclusive"] == 131
    assert event["source_interval_complete"] is False
    assert "source_task_numeric_sha256" not in event
    assert set(event["qualification_flags"]) == {
        "source_interval_outside_signal", "source_code_label_mismatch_or_unknown",
        "label_absent_from_event_dictionary", "missing_matching_mne_annotation",
        "missing_matching_native_marker", "mi_duration_differs_from_source_dictionary_10s",
    }
    assert result["all_integrity_checks_pass"] is False
    assert result["native_markers"][-1]["description"] == "4"
    assert result["mne_annotations"][-1]["description"] == "Stimulus/4"


def test_source_duration_qualification_is_retained_separately_from_clock_alignment(brainvision_run):
    root, relative, values = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records[-1]["duration"] = "9"
    write_tsv(path, records)
    result, events = audit.audit_run(root, relative, block_samples=17)
    event = events[-1]
    assert result["all_integrity_checks_pass"] is True
    assert "integrity_pass_scope" in result
    assert event["qualification_flags"] == ["mi_duration_differs_from_source_dictionary_10s"]
    assert event["source_values"]["duration"] == "9"
    assert event["native_stop_sample_exclusive"] == 100
    assert event["source_task_numeric_sha256"] == hashlib.sha256(
        audit.numeric_bytes(values[:, 10:100])).hexdigest()
    assert event["analysis_window_selected"] is False


def test_one_sample_tsv_clock_difference_preserves_both_clocks_and_distinct_task_hashes(
        brainvision_run):
    root, relative, values = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records[-1]["onset"] = "1.1"
    write_tsv(path, records)
    original_files = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    result, events = audit.audit_run(root, relative, block_samples=17)
    event = events[-1]
    assert result["all_integrity_checks_pass"] is True
    assert result["source_TSV_exact_clock_alignment_pass"] is False
    assert "TSV_native_clock_disagreement_retained" in result["source_run_quality_flags"]
    assert result["source_events"]["source_rows_native_markers_same_ordered_codes"] is True
    assert result["source_events"]["annotation_onset_code_equals_marker_multiset"] is True
    assert result["source_events"]["TSV_native_clock_disagreement_events"] == 1
    assert event["source_values"]["onset"] == "1.1"
    assert event["native_start_sample_0based"] == 11
    assert event["native_stop_sample_exclusive"] == 111
    assert event["native_marker_start_sample_0based"] == 10
    assert event["native_marker_stop_with_TSV_duration_sample_exclusive"] == 110
    assert event["TSV_minus_native_marker_samples"] == 1
    assert event["source_task_numeric_sha256"] == hashlib.sha256(
        audit.numeric_bytes(values[:, 11:111])).hexdigest()
    assert event["native_marker_task_numeric_sha256"] == hashlib.sha256(
        audit.numeric_bytes(values[:, 10:110])).hexdigest()
    assert event["source_task_numeric_sha256"] != event["native_marker_task_numeric_sha256"]
    assert "TSV_onset_and_duration" in event["source_task_hash_convention"]
    assert "native_marker_start_with_TSV_duration" in event["native_marker_task_hash_convention"]
    assert "TSV_clock_differs_from_corresponding_native_marker" in event["qualification_flags"]
    assert event["analysis_window_selected"] is False
    assert {path: path.read_bytes() for path in original_files} == original_files


def test_row_order_code_mismatch_fails_resource_gate_even_when_onset_code_multisets_match(
        brainvision_run):
    root, relative, _ = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records[1], records[2] = records[2], records[1]
    write_tsv(path, records)
    result, events = audit.audit_run(root, relative, block_samples=17)
    assert result["all_integrity_checks_pass"] is False
    assert result["source_TSV_exact_clock_alignment_pass"] is True
    assert result["source_events"]["source_rows_native_markers_same_ordered_codes"] is False
    assert [event["source_values"] for event in events] == records
    assert "native_marker_task_numeric_sha256" not in events[1]


def test_matching_unknown_source_code_remains_qualified_without_inventing_a_task(brainvision_run):
    root, relative, _ = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records[-1].update(value="700001", trial_type="unknown", duration="0")
    write_tsv(path, records)
    header = root / relative
    marker = header.with_suffix(".vmrk")
    marker.write_text(marker.read_text().replace("Mk4=Stimulus,4,", "Mk4=Stimulus,700001,"))
    dictionary_path = path.with_suffix(".json")
    dictionary = json.loads(dictionary_path.read_text())
    dictionary["trial_type"]["Levels"]["unknown"] = "Unmapped native source annotation"
    dictionary_path.write_text(json.dumps(dictionary))
    result, events = audit.audit_run(root, relative, block_samples=17)
    assert result["all_integrity_checks_pass"] is True
    assert result["source_TSV_exact_clock_alignment_pass"] is True
    assert result["source_trial_type_counts"]["unknown"] == 1
    assert events[-1]["source_values"] == records[-1]
    assert events[-1]["qualification_flags"] == ["source_code_label_mismatch_or_unknown"]
    assert events[-1]["is_mi_execution_event"] is False
    assert "source_task_numeric_sha256" not in events[-1]
    assert "native_marker_task_numeric_sha256" not in events[-1]
    assert events[-1]["analysis_window_selected"] is False


@pytest.mark.parametrize("mi_count", [43, 58])
def test_extra_source_mi_events_and_duplicate_intervals_are_retained_and_qualified(
        brainvision_run, mi_count):
    root, relative, _ = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records.extend(dict(records[-1]) for _ in range(mi_count - 1))
    write_tsv(path, records)
    marker = (root / relative).with_suffix(".vmrk")
    with marker.open("a") as stream:
        for index in range(5, mi_count + 4):
            stream.write(f"Mk{index}=Stimulus,4,11,0,0\n")
    result, events = audit.audit_run(root, relative, block_samples=17)
    tasks = [event for event in events if event["is_mi_execution_event"]]
    assert result["all_integrity_checks_pass"] is True
    assert result["source_TSV_exact_clock_alignment_pass"] is True
    assert "MI_event_count_differs_from_design_40_retained" in result["source_run_quality_flags"]
    assert result["source_trial_type_counts"]["mi_l2r"] == mi_count
    assert len(tasks) == mi_count
    assert len({event["event_id"] for event in tasks}) == mi_count
    assert len({event["source_task_numeric_sha256"] for event in tasks}) == 1
    assert all(event["native_marker_task_numeric_sha256"] == event["source_task_numeric_sha256"]
               for event in tasks)
    assert all(event["analysis_window_selected"] is False for event in tasks)


def test_native_mne_marker_disagreement_still_fails_resource_gate(monkeypatch, brainvision_run):
    root, relative, _ = brainvision_run
    original_read = audit.mne.io.read_raw_brainvision

    def mismatched_annotations(*args, **kwargs):
        raw = original_read(*args, **kwargs)
        raw.annotations.description[-1] = "Stimulus/9"
        return raw

    monkeypatch.setattr(audit.mne.io, "read_raw_brainvision", mismatched_annotations)
    result, _ = audit.audit_run(root, relative, block_samples=17)
    assert result["all_integrity_checks_pass"] is False
    assert result["source_events"]["source_rows_native_markers_same_ordered_codes"] is True
    assert result["source_events"]["annotation_onset_code_equals_marker_multiset"] is False


def duplicate_task_audit(brainvision_run, *, shifted):
    root, relative, _ = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records.append({**records[-1], "onset": "1.1" if shifted else "1"})
    write_tsv(path, records)
    marker = (root / relative).with_suffix(".vmrk")
    with marker.open("a") as stream:
        stream.write("Mk5=Stimulus,4,11,0,0\n")
    result, events = audit.audit_run(root, relative, block_samples=17)
    log = root / "log"
    run = log / "runs" / "fixture_run"
    run.mkdir(parents=True)
    return result, events, log, run


def test_aggregate_reports_native_and_tsv_task_duplicate_groups_separately(brainvision_run):
    result, events, log, run = duplicate_task_audit(brainvision_run, shifted=True)
    (run / "audit.json").write_text(json.dumps(result))
    (run / "source_events.json").write_text(json.dumps(events))
    summary = fetch.aggregate(log, [])
    assert summary["TSV_declared_mi_interval_exact_copy_groups"] == []
    native_groups = summary["native_mi_interval_exact_copy_groups"]
    assert len(native_groups) == 1
    assert native_groups[0]["identities"] == [events[-2]["event_id"], events[-1]["event_id"]]
    assert summary["TSV_exact_clock_disagreement_runs"] == [result["source_file"]]
    assert summary["TSV_native_clock_disagreement_events"] == 1
    assert summary["prior_exact_clock_native_hash_equivalence_aliases"] == 0


@pytest.mark.parametrize("shifted", [False, True])
def test_prior_hash_equivalence_alias_requires_proven_exact_clock_and_preserves_original_ledger(
        brainvision_run, shifted):
    result, events, log, run = duplicate_task_audit(brainvision_run, shifted=shifted)
    result.pop("source_TSV_exact_clock_alignment_pass")
    for event in events:
        event.pop("native_marker_task_numeric_sha256", None)
    audit_path, events_path = run / "audit.json", run / "source_events.json"
    audit_path.write_text(json.dumps(result))
    events_path.write_text(json.dumps(events))
    original_audit, original_events = audit_path.read_bytes(), events_path.read_bytes()
    summary = fetch.aggregate(log, [])
    assert summary["prior_exact_clock_native_hash_equivalence_aliases"] == (0 if shifted else 2)
    assert len(summary["native_mi_interval_exact_copy_groups"]) == (0 if shifted else 1)
    assert audit_path.read_bytes() == original_audit
    assert events_path.read_bytes() == original_events


def test_nonfinite_event_clock_is_rejected_before_interval_access(brainvision_run):
    root, relative, _ = brainvision_run
    path = event_path(root, relative)
    records = audit.rows(path)
    records[-1]["duration"] = "nan"
    write_tsv(path, records)
    with pytest.raises(ValueError, match="Non-finite source event clock"):
        audit.audit_run(root, relative, block_samples=17)


def test_late_nonfinite_signal_block_is_detected_and_source_is_closed(monkeypatch, brainvision_run):
    root, relative, values = brainvision_run

    class FakeRaw:
        info = {"sfreq": 10.0}
        n_times = values.shape[1]
        ch_names = ["C3", "C4"]
        closed = False

        def get_channel_types(self):
            return ["eeg", "eeg"]

        def get_data(self, start, stop):
            data = values[:, start:stop].copy()
            if stop == self.n_times:
                data[0, -1] = np.nan
            return data

        def close(self):
            self.closed = True

    raw = FakeRaw()
    monkeypatch.setattr(audit.mne.io, "read_raw_brainvision", lambda *args, **kwargs: raw)
    with pytest.raises(ValueError, match="non-finite"):
        audit.audit_run(root, relative, block_samples=17)
    assert raw.closed is True


class StorageError(Exception):
    def __init__(self, code):
        super().__init__("private endpoint https://signed.example?token=secret-test-token")
        self.response = {"Error": {"Code": code}}


class MemoryStore:
    """Tiny byte store; ETags deliberately provide no scientific integrity evidence."""

    def __init__(self, *, corrupt=False):
        self.objects = {}
        self.calls = []
        self.corrupt = corrupt
        self.bodies = []

    def head_object(self, **kwargs):
        self.calls.append(("head", kwargs))
        if kwargs["Key"] not in self.objects:
            raise StorageError("404")
        body, metadata = self.objects[kwargs["Key"]]
        return {"ResponseMetadata": {"HTTPStatusCode": 200}, "ContentLength": len(body),
                "Metadata": metadata, "ETag": "opaque-etag-12"}

    def put_object(self, **kwargs):
        self.calls.append(("put", kwargs))
        assert kwargs["IfNoneMatch"] == "*"
        assert kwargs["Key"] not in self.objects
        body = b"x" * len(kwargs["Body"]) if self.corrupt else kwargs["Body"]
        self.objects[kwargs["Key"]] = (body, kwargs["Metadata"])
        return {"ResponseMetadata": {"HTTPStatusCode": 200}, "ETag": "opaque-etag-12"}

    def get_object(self, **kwargs):
        self.calls.append(("get", kwargs))
        body = io.BytesIO(self.objects[kwargs["Key"]][0])
        self.bodies.append(body)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}, "Body": body}


def official_record(relative="sub-04/eeg/sub-04_task-motorimagery_run-1_eeg.eeg",
                    body=b"synthetic source bytes"):
    return {"id": "public-object-id", "path": fetch.SOURCE_ROOT + relative,
            "size": str(len(body)), "md5": hashlib.md5(body, usedforsecurity=False).hexdigest(),
            "download_endpoint": "https://www.scidb.cn/api/file/download/public-object-id"}


@pytest.mark.parametrize("suffix", [".eeg", ".eeg.partial"])
def test_unrelated_signal_or_partial_blocks_new_signal_and_preserves_bytes(tmp_path, suffix):
    relative = fetch.relative_path(official_record())
    path = tmp_path / ("sub-05/eeg/other" + suffix)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"preserved prior bytes")
    with pytest.raises(ValueError, match="Another signal or partial"):
        fetch.check_single_signal_cache(tmp_path, relative)
    assert path.read_bytes() == b"preserved prior bytes"


@pytest.mark.parametrize("suffix", ["", ".partial"])
def test_current_signal_cache_can_be_resumed(tmp_path, suffix):
    relative = fetch.relative_path(official_record())
    path = tmp_path / (relative + suffix)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"preserved current bytes")
    fetch.check_single_signal_cache(tmp_path, relative)
    assert path.read_bytes() == b"preserved current bytes"


@pytest.fixture
def task_owned_source(tmp_path):
    cache, log, representative = (tmp_path / name for name in ("cache", "log", "representative"))
    body = b"synthetic source bytes"
    record = official_record(body=body)
    relative = fetch.relative_path(record)
    original = representative / relative
    original.parent.mkdir(parents=True)
    original.write_bytes(body)
    source = fetch.ensure_source(record, cache, log, representative)
    return cache, log, source, original


def complete_closure(source):
    return {"closed": True, "source_audit_integrity_pass": True,
            "source_audit_pair": {"completed": True, "source_binary_sha256": source["sha256"]},
            "source_relative_paths": [source["relative_path"]]}


def source_ownership(log, source):
    return fetch.checked_cache_ownership(log, source["relative_path"], source["record"])


def test_verified_representative_copy_is_owned_while_prior_result_is_preserved(task_owned_source):
    cache, log, source, original = task_owned_source
    assert source["cache_created_by_this_task"] is True
    assert source["local_origin"] == "verified_copy_of_preserved_representative"
    assert (cache / source["relative_path"]).read_bytes() == original.read_bytes()
    assert fetch.load_json(fetch.receipt_path(log, "source_receipts", source["relative_path"])) == source
    assert fetch.ensure_source(source["record"], cache, log, original.parents[2]) == source


def test_every_source_upload_requires_independent_full_readback_before_eviction(task_owned_source):
    cache, log, source, original = task_owned_source
    store = MemoryStore()
    remote = fetch.upload_source(store, "test-private", cache, log, source)
    assert remote["verification"] == fetch.FULL_GET
    assert remote["readback_bytes"] == source["bytes"]
    assert remote["source_official_md5_original"] == source["record"]["md5"]
    assert [name for name, _ in store.calls] == ["head", "put", "head", "get"]
    assert all(body.closed for body in store.bodies)
    closure = complete_closure(source)
    assert fetch.run_closed(closure, {source["relative_path"]: source},
                            {source["relative_path"]: remote}) is True
    eviction = fetch.evict_signal(cache / source["relative_path"], source, remote, closure,
                                 ownership=source_ownership(log, source))
    assert eviction["full_get_sha256_receipt_required"] is True
    assert not (cache / source["relative_path"]).exists()
    assert original.read_bytes() == b"synthetic source bytes"
    assert fetch.receipt_path(log, "source_receipts", source["relative_path"]).exists()
    assert fetch.receipt_path(log, "r2_receipts", source["relative_path"]).exists()


def test_remote_corruption_preserves_source_and_never_closes_r2_receipt(task_owned_source):
    cache, log, source, _ = task_owned_source
    store = MemoryStore(corrupt=True)
    with pytest.raises(ValueError, match="readback"):
        fetch.upload_source(store, "test-private", cache, log, source)
    assert (cache / source["relative_path"]).is_file()
    assert not fetch.receipt_path(log, "r2_receipts", source["relative_path"]).exists()
    assert all(body.closed for body in store.bodies)


@pytest.mark.parametrize("verification,readback", [
    ("head_length_and_sha256_metadata_verified", len(b"synthetic source bytes")),
    (fetch.FULL_GET, 1),
])
def test_new_r2_receipt_cannot_close_with_metadata_only_or_partial_get(
        monkeypatch, task_owned_source, verification, readback):
    cache, log, source, _ = task_owned_source
    monkeypatch.setattr(fetch, "transfer_file", lambda client, bucket, path, entry: {
        **entry, "verification": verification, "readback_bytes": readback,
    })
    with pytest.raises(ValueError, match="full GET closure"):
        fetch.upload_source(object(), "test-private", cache, log, source)
    assert (cache / source["relative_path"]).exists()
    assert not fetch.receipt_path(log, "r2_receipts", source["relative_path"]).exists()


@pytest.mark.parametrize("field,value", [
    ("verification", "head_length_and_sha256_metadata_verified"),
    ("sha256", "0" * 64), ("bytes", 1), ("readback_bytes", 1),
    ("key", "few-shot-mi-eeg/datasets/unrelated/source.eeg"),
])
def test_resumed_r2_receipt_requires_complete_matching_content_evidence(
        task_owned_source, field, value):
    cache, log, source, _ = task_owned_source
    remote = fetch.upload_source(MemoryStore(), "test-private", cache, log, source)
    remote[field] = value
    path = fetch.receipt_path(log, "r2_receipts", source["relative_path"])
    path.write_text(json.dumps(remote))
    with pytest.raises(ValueError, match="full-readback closure"):
        fetch.upload_source(object(), "test-private", cache, log, source)
    assert (cache / source["relative_path"]).exists()


@pytest.mark.parametrize("scope,field,value", [
    ("source", "cache_created_by_this_task", False),
    ("source", "official_size_and_md5_pass", False),
    ("remote", "verification", "head_length_and_sha256_metadata_verified"),
    ("remote", "sha256", "0" * 64),
    ("remote", "readback_bytes", 1),
    ("closure", "closed", False),
    ("closure", "source_audit_integrity_pass", False),
])
def test_eviction_refuses_missing_ownership_or_incomplete_closure(
        task_owned_source, scope, field, value):
    cache, log, source, _ = task_owned_source
    remote = fetch.upload_source(MemoryStore(), "test-private", cache, log, source)
    closure = complete_closure(source)
    {"source": source, "remote": remote, "closure": closure}[scope][field] = value
    with pytest.raises(ValueError, match="eviction requires"):
        fetch.evict_signal(cache / source["relative_path"], source, remote, closure,
                           ownership=source_ownership(log, source))
    assert (cache / source["relative_path"]).exists()


def test_closed_cache_changed_after_readback_is_preserved(task_owned_source):
    cache, log, source, _ = task_owned_source
    remote = fetch.upload_source(MemoryStore(), "test-private", cache, log, source)
    path = cache / source["relative_path"]
    path.write_bytes(b"changed source bytes")
    with pytest.raises(ValueError, match="changed after closure"):
        fetch.evict_signal(path, source, remote, complete_closure(source),
                           ownership=source_ownership(log, source))
    assert path.read_bytes() == b"changed source bytes"


def test_preexisting_unowned_signal_cannot_be_evicted(tmp_path):
    cache, log = tmp_path / "cache", tmp_path / "log"
    record = official_record()
    path = cache / fetch.relative_path(record)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"synthetic source bytes")
    source = fetch.ensure_source(record, cache, log, representative=None)
    assert source["cache_created_by_this_task"] is False
    remote = fetch.upload_source(MemoryStore(), "test-private", cache, log, source)
    with pytest.raises(ValueError, match="task ownership"):
        fetch.evict_signal(path, source, remote, complete_closure(source), ownership=None)
    assert path.is_file()


class DownloadResponse:
    def __init__(self, body, status=206):
        self.body = body
        self.status_code = status
        self.headers = {"Content-Range": f"bytes 3-{len(body) + 2}/{len(body) + 3}"}
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def iter_content(self, chunk_size):
        yield self.body[:4]
        yield self.body[4:]


@pytest.mark.parametrize("http_status", [206, 200])
def test_owned_metadata_partial_resume_requires_range_status_and_final_official_checksum(
        monkeypatch, tmp_path, http_status):
    cache, log = tmp_path / "cache", tmp_path / "log"
    body = b"synthetic source bytes"
    record = official_record(relative="sub-04/eeg/sub-04_task-motorimagery_run-1_events.tsv",
                             body=body)
    relative = fetch.relative_path(record)
    path = cache / relative
    path.parent.mkdir(parents=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_bytes(body[:3])
    fetch.immutable_json(fetch.receipt_path(log, "cache_ownership", relative), {
        "source_record": record, "relative_path": relative, "cache_created_by_this_task": True,
    })
    response = DownloadResponse(body[3:], status=http_status)

    def get(url, **kwargs):
        assert url == record["download_endpoint"]
        assert kwargs["headers"] == {"Range": "bytes=3-"}
        assert kwargs["stream"] is True
        return response

    monkeypatch.setattr(fetch.requests, "get", get)
    if http_status == 206:
        result = fetch.ensure_source(record, cache, log, representative=None)
        assert result["official_size_and_md5_pass"] is True
        assert result["cache_created_by_this_task"] is True
        assert path.read_bytes() == body
        assert not partial.exists()
    else:
        with pytest.raises(ValueError, match="whole/range status"):
            fetch.ensure_source(record, cache, log, representative=None)
        assert partial.read_bytes() == body[:3]
        assert not path.exists()
        assert not fetch.receipt_path(log, "source_receipts", relative).exists()
    assert response.closed is True


def test_unowned_partial_cache_is_preserved_without_network_or_ownership_adoption(
        monkeypatch, tmp_path):
    cache, log = tmp_path / "cache", tmp_path / "log"
    record = official_record()
    relative = fetch.relative_path(record)
    partial = cache / (relative + ".partial")
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b"unknown prior partial")

    def forbidden(*args, **kwargs):
        raise AssertionError("Unknown partial cache must not trigger a source request")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="Unknown partial cache ownership"):
        fetch.ensure_source(record, cache, log, representative=None)
    assert partial.read_bytes() == b"unknown prior partial"
    assert not fetch.receipt_path(log, "cache_ownership", relative).exists()


def test_owned_download_published_before_crash_can_reconstruct_source_receipt(tmp_path):
    cache, log = tmp_path / "cache", tmp_path / "log"
    record = official_record()
    relative = fetch.relative_path(record)
    path = cache / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"synthetic source bytes")
    fetch.immutable_json(fetch.receipt_path(log, "cache_ownership", relative), {
        "source_record": record, "relative_path": relative, "cache_created_by_this_task": True,
    })
    source = fetch.ensure_source(record, cache, log, representative=None)
    assert source["cache_created_by_this_task"] is True
    assert source["official_size_and_md5_pass"] is True
    assert fetch.load_json(fetch.receipt_path(log, "source_receipts", relative)) == source


@pytest.mark.parametrize("scope,field,value", [
    ("source", "official_size_and_md5_pass", False),
    ("source", "relative_path", "unrelated.eeg"),
    ("remote", "verification", "head_length_and_sha256_metadata_verified"),
    ("remote", "readback_bytes", 1), ("remote", "bytes", 1),
    ("remote", "relative_path", "unrelated.eeg"),
    ("remote", "key", "few-shot-mi-eeg/datasets/unrelated/source.eeg"),
])
def test_closed_run_requires_all_file_identity_and_full_get_evidence(
        task_owned_source, scope, field, value):
    cache, log, source, _ = task_owned_source
    remote = fetch.upload_source(MemoryStore(), "test-private", cache, log, source)
    relative = source["relative_path"]
    closure = complete_closure(source)
    {"source": source, "remote": remote}[scope][field] = value
    assert fetch.run_closed(closure, {relative: source}, {relative: remote}) is False
    assert (cache / relative).is_file()


def test_closed_run_cannot_omit_content_receipts_for_a_selected_file(task_owned_source):
    _, _, source, _ = task_owned_source
    relative = source["relative_path"]
    assert fetch.run_closed(complete_closure(source), {relative: source}, {}) is False
    assert fetch.run_closed({"closed": True, "source_audit_integrity_pass": True}, {}, {}) is False


def test_closed_run_path_list_cannot_drop_expected_files_or_repeat_a_receipt(task_owned_source):
    cache, log, source, _ = task_owned_source
    remote = fetch.upload_source(MemoryStore(), "test-private", cache, log, source)
    relative = source["relative_path"]
    closure = complete_closure(source)
    sources, remotes = {relative: source}, {relative: remote}
    assert fetch.run_closed(closure, {**sources, "missing-sidecar.tsv": {}}, remotes) is False
    assert fetch.run_closed(closure, sources, {**remotes, "missing-sidecar.tsv": {}}) is False
    closure["source_relative_paths"].append(relative)
    assert fetch.run_closed(closure, sources, remotes) is False


class RangeResponse:
    def __init__(self, body, first, last, total, *, status=206, content_range=None):
        self.body = body
        self.status_code = status
        self.headers = {"Content-Range": (f"bytes {first}-{last}/{total}"
                                          if content_range is None else content_range)}
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def iter_content(self, chunk_size):
        yield self.body[:2]
        yield b""
        yield self.body[2:]


def range_http(monkeypatch, body, *, alter=None):
    requests, responses = [], []

    def get(url, **kwargs):
        first, last = map(int, kwargs["headers"]["Range"].removeprefix("bytes=").split("-"))
        requests.append((first, last))
        assert kwargs["stream"] is True
        response = RangeResponse(body[first:last + 1], first, last, len(body))
        if alter is not None:
            alter(response)
        responses.append(response)
        return response

    monkeypatch.setattr(fetch.requests, "get", get)
    return requests, responses


def test_parallel_ranges_assemble_one_bounded_cache_without_overlap_or_duplicate_chunks(
        monkeypatch, tmp_path):
    body = b"distinct native source bytes"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    requested, responses = range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=4, range_bytes=5)
    expected_ranges = [(first, min(first + 4, len(body) - 1)) for first in range(0, len(body), 5)]
    assert sorted(requested) == expected_ranges
    assert sum(last - first + 1 for first, last in requested) == len(body)
    assert partial.read_bytes() == body
    assert partial.stat().st_size == len(body)
    assert list(tmp_path.glob("*.partial")) == [partial]
    assert all(response.closed for response in responses)
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints",
                                                  fetch.relative_path(record)))
    assert checkpoint["intervals"] == [list(interval) for interval in expected_ranges]
    assert len(checkpoint["completed"]) == len(expected_ranges)
    assert checkpoint["cache_files"] == 1
    for index, (first, last) in enumerate(expected_ranges):
        saved = checkpoint["completed"][str(index)]
        assert saved["bytes"] == last - first + 1
        assert saved["sha256"] == hashlib.sha256(body[first:last + 1]).hexdigest()


def test_parallel_range_resume_reuses_only_rehashed_completed_extents(monkeypatch, tmp_path):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    checkpoint = fetch.receipt_path(log, "range_checkpoints", fetch.relative_path(record))
    first_persisted = threading.Event()
    real_write = fetch.atomic_json

    def write(path, value):
        real_write(path, value)
        if path == checkpoint and "0" in value["completed"]:
            first_persisted.set()

    def get(url, **kwargs):
        first, last = map(int, kwargs["headers"]["Range"].removeprefix("bytes=").split("-"))
        if first:
            assert first_persisted.wait(timeout=5)
            raise StorageError("ConnectionClosed")
        return RangeResponse(body[first:last + 1], first, last, len(body))

    monkeypatch.setattr(fetch, "atomic_json", write)
    monkeypatch.setattr(fetch.requests, "get", get)
    with pytest.raises(StorageError):
        fetch.parallel_range_download(record, partial, log, workers=1, range_bytes=4)
    interrupted = fetch.load_json(checkpoint)
    assert list(interrupted["completed"]) == ["0"]
    assert partial.stat().st_size == len(body)
    assert partial.read_bytes()[:4] == body[:4]
    assert "secret-test-token" not in checkpoint.read_text()
    requested, responses = range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=3, range_bytes=4)
    assert sorted(requested) == [(4, 7), (8, 11), (12, 15)]
    assert partial.read_bytes() == body
    assert all(response.closed for response in responses)


def test_range_failure_preserves_checkpoint_for_successful_already_running_peer(
        monkeypatch, tmp_path):
    body = b"abcdefgh"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    peer_started, failed = threading.Event(), threading.Event()

    class PeerResponse(RangeResponse):
        def iter_content(self, chunk_size):
            assert failed.wait(timeout=5)
            yield self.body

    def get(url, **kwargs):
        first, last = map(int, kwargs["headers"]["Range"].removeprefix("bytes=").split("-"))
        if first == 0:
            assert peer_started.wait(timeout=5)
            failed.set()
            raise StorageError("ConnectionClosed")
        peer_started.set()
        return PeerResponse(body[first:last + 1], first, last, len(body))

    monkeypatch.setattr(fetch.requests, "get", get)
    with pytest.raises(StorageError):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints",
                                                  fetch.relative_path(record)))
    assert set(checkpoint["completed"]) == {"1"}
    assert checkpoint["completed"]["1"]["sha256"] == hashlib.sha256(body[4:]).hexdigest()
    assert partial.read_bytes()[4:] == body[4:]
    requested, _ = range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    assert requested == [(0, 3)]
    assert partial.read_bytes() == body


def test_range_resume_detects_changed_completed_bytes_before_network(monkeypatch, tmp_path):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    changed = bytearray(partial.read_bytes())
    changed[6] ^= 1
    partial.write_bytes(changed)

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed completed chunks must be refused before source HTTP")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="Completed range changed locally"):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    assert partial.read_bytes() == changed


@pytest.mark.parametrize("change", ["source_record", "partition", "cache_size"])
def test_range_checkpoint_cannot_resume_a_different_source_partition_or_cache_size(
        monkeypatch, tmp_path, change):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    range_bytes = 4
    if change == "source_record":
        record = {**record, "id": "different-official-file"}
    elif change == "partition":
        range_bytes = 5
    else:
        partial.write_bytes(body[:-1])

    def forbidden(*args, **kwargs):
        raise AssertionError("Inconsistent range checkpoints must not trigger HTTP")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="differs"):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=range_bytes)
    assert partial.is_file()


@pytest.mark.parametrize("status,mapping", [
    (200, "bytes 0-4/5"), (206, "bytes 1-5/5"),
    (206, "bytes 0-3/5"), (206, "bytes 0-4/6"), (206, ""),
])
def test_parallel_ranges_refuse_ignored_range_or_wrong_exact_mapping(
        monkeypatch, tmp_path, status, mapping):
    body = b"abcde"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"

    def alter(response):
        response.status_code = status
        response.headers["Content-Range"] = mapping

    _, responses = range_http(monkeypatch, body, alter=alter)
    with pytest.raises(ValueError, match="range status or exact mapping differs"):
        fetch.parallel_range_download(record, partial, log, workers=1, range_bytes=5)
    assert partial.stat().st_size == len(body)
    assert partial.read_bytes() == b"\0" * len(body)
    assert all(response.closed for response in responses)
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints",
                                                  fetch.relative_path(record)))
    assert checkpoint["completed"] == {}


@pytest.mark.parametrize("received,message", [
    (b"abcd", "shorter than its assigned extent"),
    (b"abcdef", "exceeds its assigned extent"),
])
def test_range_body_length_failure_never_checkpoints_or_writes_outside_extent(
        monkeypatch, tmp_path, received, message):
    record = official_record(body=b"abcde")
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    _, responses = range_http(monkeypatch, b"abcde", alter=lambda response: setattr(
        response, "body", received))
    with pytest.raises(ValueError, match=message):
        fetch.parallel_range_download(record, partial, log, workers=1, range_bytes=5)
    assert partial.stat().st_size == 5
    assert all(response.closed for response in responses)
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints",
                                                  fetch.relative_path(record)))
    assert checkpoint["completed"] == {}


@pytest.mark.parametrize("case,reason", [
    ("status", "source_http_range_response_mismatch"),
    ("mapping", "source_http_range_response_mismatch"),
    ("short", "source_range_body_shorter_than_extent"),
    ("oversized", "source_range_body_exceeds_extent"),
    ("local_write", "local_source_extent_write_incomplete"),
])
def test_controller_range_guard_retains_numeric_cause_without_headers_or_signed_url(
        monkeypatch, tmp_path, capsys, case, reason):
    body = b"native source bytes"
    record = official_record(body=body)
    cache, log = configure_main(monkeypatch, tmp_path, [record])
    response = RangeResponse(body, 0, len(body) - 1, len(body))
    response.url = "https://signed.example?token=range-secret-test-token"
    if case == "status":
        response.status_code = 503
    elif case == "mapping":
        response.headers["Content-Range"] = response.url
    elif case == "short":
        response.body = b""
    elif case == "oversized":
        response.body = body + b"extra"
    else:
        monkeypatch.setattr(fetch.os, "pwrite", lambda *args: 0)
    monkeypatch.setattr(fetch.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(fetch, "build_client", lambda: (object(), "test-private", "fixture"))
    monkeypatch.setattr(fetch.shutil, "disk_usage", lambda path: SimpleNamespace(free=2 * 1024 ** 3))

    def forbidden(*args, **kwargs):
        raise AssertionError("An unverified range cannot reach audit or R2 publication")

    monkeypatch.setattr(fetch, "audit_run", forbidden)
    monkeypatch.setattr(fetch, "transfer_file", forbidden)
    assert fetch.main() == 1
    relative = fetch.relative_path(record)
    partial = cache / (relative + ".partial")
    assert partial.stat().st_size == len(body)
    assert not (cache / relative).exists()
    assert not fetch.receipt_path(log, "source_receipts", relative).exists()
    assert not fetch.receipt_path(log, "r2_receipts", relative).exists()
    failure = fetch.load_json(next((log / "failures").glob("*.json")))
    evidence = fetch.load_json(next((log / "range_failures").rglob("*.json")))
    context = failure["source_range_failure"]
    assert failure["error_type"] == "ValueError"
    assert context["reason"] == evidence["reason"] == reason
    assert context["range_index"] == 0
    assert context["first_byte"] == 0
    assert context["last_byte_inclusive"] == len(body) - 1
    assert context["official_total_bytes"] == len(body)
    assert context["http_status"] == (503 if case == "status" else 206)
    assert context["content_range_numeric"] == (None if case == "mapping" else
                                                [0, len(body) - 1, len(body)])
    assert evidence["source_or_partial_bytes_deleted"] is False
    assert fetch.load_json(fetch.receipt_path(log, "range_checkpoints", relative))["completed"] == {}
    serialized = capsys.readouterr().out + "".join(path.read_text() for path in log.rglob("*.json"))
    assert "range-secret-test-token" not in serialized
    assert "signed.example" not in serialized


def test_disjoint_ranges_require_ownership_before_adopting_a_sequential_prefix(monkeypatch, tmp_path):
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    partial.write_bytes(b"prior sequential prefix")

    def forbidden(*args, **kwargs):
        raise AssertionError("A sequential partial must remain outside disjoint-range adoption")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="Cannot adopt a sequential partial"):
        fetch.parallel_range_download(official_record(), partial, log, workers=1, range_bytes=4)
    assert partial.read_bytes() == b"prior sequential prefix"
    assert not log.exists()


def owned_prefix(record, partial, log, prefix):
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(prefix)
    fetch.immutable_json(fetch.receipt_path(log, "cache_ownership", fetch.relative_path(record)), {
        "source_record": record, "relative_path": fetch.relative_path(record),
        "cache_created_by_this_task": True,
    })


def test_owned_sequential_prefix_is_preserved_and_only_suffix_ranges_are_written(
        monkeypatch, tmp_path):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    prefix_bytes = 7
    owned_prefix(record, partial, log, body[:prefix_bytes])
    requested, responses = range_http(monkeypatch, body)
    real_pwrite = fetch.os.pwrite
    write_offsets = []

    def pwrite(descriptor, block, offset):
        write_offsets.append(offset)
        assert offset >= prefix_bytes
        return real_pwrite(descriptor, block, offset)

    monkeypatch.setattr(fetch.os, "pwrite", pwrite)
    fetch.parallel_range_download(record, partial, log, workers=3, range_bytes=4)
    assert sorted(requested) == [(7, 10), (11, 14), (15, 15)]
    assert min(write_offsets) == prefix_bytes
    assert partial.read_bytes() == body
    assert all(response.closed for response in responses)
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints",
                                                  fetch.relative_path(record)))
    assert checkpoint["preserved_prefix_bytes"] == prefix_bytes
    assert checkpoint["allocation_completed"] is True
    assert checkpoint["intervals"] == [[0, 6], [7, 10], [11, 14], [15, 15]]
    prefix = checkpoint["completed"]["0"]
    assert prefix["sha256"] == hashlib.sha256(body[:prefix_bytes]).hexdigest()
    assert prefix["origin"] == "preserved_task_owned_sequential_prefix"
    assert prefix["official_whole_md5_still_required"] is True


@pytest.mark.parametrize("crash_stage", ["before_allocation", "after_allocation"])
def test_prefix_adoption_resumes_a_crash_without_adopting_extension_zeros_as_source(
        monkeypatch, tmp_path, crash_stage):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    prefix_bytes = 3
    owned_prefix(record, partial, log, body[:prefix_bytes])
    real_write = fetch.atomic_json

    def crash_write(path, value):
        if value.get("allocation_completed") is True and crash_stage == "after_allocation":
            raise RuntimeError("simulated allocation checkpoint crash")
        real_write(path, value)
        if value.get("allocation_completed") is False and crash_stage == "before_allocation":
            raise RuntimeError("simulated prefix checkpoint crash")

    def forbidden(*args, **kwargs):
        raise AssertionError("The simulated crash must precede source requests")

    monkeypatch.setattr(fetch, "atomic_json", crash_write)
    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(RuntimeError, match="simulated"):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    checkpoint_path = fetch.receipt_path(log, "range_checkpoints", fetch.relative_path(record))
    checkpoint = fetch.load_json(checkpoint_path)
    assert checkpoint["allocation_completed"] is False
    assert checkpoint["preserved_prefix_bytes"] == prefix_bytes
    assert checkpoint["completed"]["0"]["sha256"] == hashlib.sha256(body[:prefix_bytes]).hexdigest()
    assert partial.stat().st_size == (prefix_bytes if crash_stage == "before_allocation" else len(body))
    assert partial.read_bytes()[:prefix_bytes] == body[:prefix_bytes]
    monkeypatch.setattr(fetch, "atomic_json", real_write)
    requested, _ = range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    assert sorted(requested) == [(3, 6), (7, 10), (11, 14), (15, 15)]
    assert partial.read_bytes() == body
    assert fetch.load_json(checkpoint_path)["preserved_prefix_bytes"] == prefix_bytes


@pytest.mark.parametrize("allocated", [False, True])
def test_torn_prefix_adoption_refuses_changed_prefix_before_http_or_extension(
        monkeypatch, tmp_path, allocated):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    owned_prefix(record, partial, log, body[:3])
    checkpoint_path = fetch.receipt_path(log, "range_checkpoints", fetch.relative_path(record))
    checkpoint = {"record": record, "range_bytes": 4, "preserved_prefix_bytes": 3,
                  "allocation_completed": False,
                  "intervals": [[0, 2], [3, 6], [7, 10], [11, 14], [15, 15]],
                  "completed": {"0": {"bytes": 3, "sha256": hashlib.sha256(body[:3]).hexdigest()}}}
    fetch.immutable_json(checkpoint_path, checkpoint)
    if allocated:
        partial.write_bytes(body[:3] + b"\0" * (len(body) - 3))
    changed = b"!" + partial.read_bytes()[1:]
    partial.write_bytes(changed)

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed preserved prefixes must be refused before HTTP")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="prefix changed before allocation"):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    assert partial.read_bytes() == changed
    assert fetch.load_json(checkpoint_path)["allocation_completed"] is False


def test_complete_owned_sequential_partial_is_md5_verified_without_source_http(monkeypatch, tmp_path):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    cache, log = tmp_path / "cache", tmp_path / "log"
    relative = fetch.relative_path(record)
    partial = cache / (relative + ".partial")
    owned_prefix(record, partial, log, body)

    def forbidden(*args, **kwargs):
        raise AssertionError("Complete sequential source bytes need only local full checksum")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    source = fetch.ensure_source(record, cache, log, representative=None)
    assert source["local_origin"] == "preserved_complete_sequential_partial"
    assert source["official_size_and_md5_pass"] is True
    assert (cache / relative).read_bytes() == body
    assert not partial.exists()
    assert not fetch.receipt_path(log, "range_checkpoints", relative).exists()


def test_adopted_prefix_remains_subject_to_whole_source_md5_publication_gate(monkeypatch, tmp_path):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    cache, log = tmp_path / "cache", tmp_path / "log"
    relative = fetch.relative_path(record)
    partial = cache / (relative + ".partial")
    corrupt_prefix = b"!bc"
    owned_prefix(record, partial, log, corrupt_prefix)
    requested, _ = range_http(monkeypatch, body)
    with pytest.raises(ValueError, match="full MD5 mismatch"):
        fetch.ensure_source(record, cache, log, representative=None)
    assert requested == [(3, len(body) - 1)]
    assert partial.read_bytes() == corrupt_prefix + body[3:]
    assert not (cache / relative).exists()
    assert not fetch.receipt_path(log, "source_receipts", relative).exists()


def test_prefix_ownership_for_a_different_official_record_cannot_be_adopted(monkeypatch, tmp_path):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    owned_prefix({**record, "id": "different-source"}, partial, log, body[:3])

    def forbidden(*args, **kwargs):
        raise AssertionError("Different-source ownership must be refused before HTTP")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="ownership"):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    assert partial.read_bytes() == body[:3]
    assert not fetch.receipt_path(log, "range_checkpoints", fetch.relative_path(record)).exists()


@pytest.mark.parametrize("ownership_change", ["missing", "different_record"])
def test_adopted_prefix_resume_still_requires_original_source_ownership(
        monkeypatch, tmp_path, ownership_change):
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    owned_prefix(record, partial, log, body[:3])
    range_http(monkeypatch, body)
    fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    ownership = fetch.receipt_path(log, "cache_ownership", fetch.relative_path(record))
    if ownership_change == "missing":
        ownership.unlink()
    else:
        value = fetch.load_json(ownership)
        value["source_record"]["id"] = "different-source"
        ownership.write_text(json.dumps(value))

    def forbidden(*args, **kwargs):
        raise AssertionError("Adopted-prefix resume must retain source ownership")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="ownership"):
        fetch.parallel_range_download(record, partial, log, workers=2, range_bytes=4)
    assert partial.read_bytes() == body


@pytest.mark.parametrize("workers,range_bytes,size", [
    (0, 4, 5), (5, 4, 5), (1, 0, 5), (1, 4, 0),
    (1, 4, fetch.MAX_SIGNAL_BYTES + 1),
])
def test_invalid_range_limits_do_not_allocate_cache_or_request_source(
        monkeypatch, tmp_path, workers, range_bytes, size):
    partial, log = tmp_path / "signal.eeg.partial", tmp_path / "log"
    record = {**official_record(), "size": str(size)}

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid range limits must not make source requests")

    monkeypatch.setattr(fetch.requests, "get", forbidden)
    with pytest.raises(ValueError, match="range limits invalid"):
        fetch.parallel_range_download(record, partial, log, workers=workers, range_bytes=range_bytes)
    assert not partial.exists()
    assert not log.exists()


def test_disjoint_download_requires_whole_official_md5_before_source_publication(
        monkeypatch, tmp_path):
    cache, log = tmp_path / "cache", tmp_path / "log"
    correct, corrupt = b"native correct bytes", b"native corrupt bytes"
    assert len(correct) == len(corrupt)
    record = official_record(body=correct)
    range_http(monkeypatch, corrupt)
    with pytest.raises(ValueError, match="full MD5 mismatch"):
        fetch.ensure_source(record, cache, log, representative=None)
    relative = fetch.relative_path(record)
    assert not (cache / relative).exists()
    assert (cache / (relative + ".partial")).read_bytes() == corrupt
    assert not fetch.receipt_path(log, "source_receipts", relative).exists()
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints", relative))
    assert checkpoint["completed"]["0"]["sha256"] == hashlib.sha256(corrupt).hexdigest()


def test_verified_disjoint_signal_publishes_source_receipt_after_all_ranges(monkeypatch, tmp_path):
    cache, log = tmp_path / "cache", tmp_path / "log"
    body = b"abcdefghijklmnop"
    record = official_record(body=body)
    real_download = fetch.parallel_range_download
    monkeypatch.setattr(fetch, "parallel_range_download", lambda record, partial, log, **kwargs:
                        real_download(record, partial, log, workers=2, range_bytes=4))
    requested, responses = range_http(monkeypatch, body)
    source = fetch.ensure_source(record, cache, log, representative=None)
    relative = fetch.relative_path(record)
    assert sorted(requested) == [(0, 3), (4, 7), (8, 11), (12, 15)]
    assert all(response.closed for response in responses)
    assert source["local_origin"] == "official_public_disjoint_range_download"
    assert source["official_size_and_md5_pass"] is True
    assert source["sha256"] == hashlib.sha256(body).hexdigest()
    assert (cache / relative).read_bytes() == body
    assert not (cache / (relative + ".partial")).exists()
    assert fetch.load_json(fetch.receipt_path(log, "source_receipts", relative)) == source


@pytest.mark.parametrize("existing_checkpoint", [False, True])
def test_ensure_source_uses_four_mib_new_ranges_but_keeps_existing_eight_mib_partition(
        monkeypatch, tmp_path, existing_checkpoint):
    mib = 1024 * 1024
    body = bytes(range(256)) * (8 * mib // 256) + b"seventeen bytes!!"
    assert len(body) == 8 * mib + 17
    record = official_record(body=body)
    relative = fetch.relative_path(record)
    cache, log = tmp_path / "cache", tmp_path / "log"
    requested = []

    class ChunkedRangeResponse(RangeResponse):
        def iter_content(self, chunk_size):
            for first in range(0, len(self.body), chunk_size):
                yield self.body[first:first + chunk_size]

    def get(url, **kwargs):
        first, last = map(int, kwargs["headers"]["Range"].removeprefix("bytes=").split("-"))
        requested.append((first, last))
        if existing_checkpoint and first == 8 * mib and not resumed:
            raise fetch.requests.exceptions.ReadTimeout("synthetic interrupted tail", response=None)
        return ChunkedRangeResponse(body[first:last + 1], first, last, len(body))

    resumed = False
    monkeypatch.setattr(fetch.requests, "get", get)
    if existing_checkpoint:
        partial = cache / (relative + ".partial")
        partial.parent.mkdir(parents=True)
        fetch.immutable_json(fetch.receipt_path(log, "cache_ownership", relative), {
            "source_record": record, "relative_path": relative, "cache_created_by_this_task": True,
        })
        with pytest.raises(fetch.requests.exceptions.ReadTimeout):
            fetch.parallel_range_download(record, partial, log, workers=1, range_bytes=8 * mib)
        checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints", relative))
        assert checkpoint["range_bytes"] == 8 * mib
        assert set(checkpoint["completed"]) == {"0"}
        requested.clear()
        resumed = True
    source = fetch.ensure_source(record, cache, log, representative=None)
    expected = ([(8 * mib, len(body) - 1)] if existing_checkpoint else [
        (0, 4 * mib - 1), (4 * mib, 8 * mib - 1), (8 * mib, len(body) - 1),
    ])
    assert sorted(requested) == expected
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints", relative))
    assert checkpoint["range_bytes"] == (8 * mib if existing_checkpoint else 4 * mib)
    assert source["official_size_and_md5_pass"] is True
    assert (cache / relative).read_bytes() == body
    assert not (cache / (relative + ".partial")).exists()


def configure_main(monkeypatch, tmp_path, records):
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text("tiny test manifest fixture\n")
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps({"all_integrity_checks_pass": True, "all_values_finite": True}))
    cache, log = tmp_path / "cache", tmp_path / "log"
    monkeypatch.setattr(sys, "argv", [
        "fetch_mind2026_r2.py", "--manifest", str(manifest), "--cache", str(cache),
        "--log", str(log), "--representative-gate", str(gate), "--execute", "--max-runs", "1",
    ])
    monkeypatch.setattr(fetch, "select_manifest", lambda path: records)
    monkeypatch.setattr(fetch.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="test"))
    return cache, log


@pytest.mark.parametrize("legacy_closure", [False, True])
def test_resume_of_closed_run_does_not_redownload_read_signal_or_upload(
        monkeypatch, tmp_path, brainvision_run, legacy_closure):
    fixture_root, relative_header, _ = brainvision_run
    binary = (fixture_root / relative_header).with_suffix(".eeg")
    signal = official_record(relative=str(Path(relative_header).with_suffix(".eeg")),
                             body=binary.read_bytes())
    relative = fetch.relative_path(signal)
    stem = relative.removesuffix("_eeg.eeg")
    subject_folder = str(Path(relative).parent)
    relatives = [relative, *(stem + suffix for suffix in (
        "_eeg.vhdr", "_eeg.vmrk", "_eeg.json", "_events.tsv", "_events.json", "_channels.tsv")),
        f"{subject_folder}/sub-04_coordsystem.json", f"{subject_folder}/sub-04_electrodes.tsv"]
    metadata_bytes = {name: ((fixture_root / name).read_bytes() if (fixture_root / name).exists()
                             else name.encode()) for name in relatives[1:]}
    records = [signal, *(official_record(name, body=metadata_bytes[name]) for name in relatives[1:])]
    cache, log = configure_main(monkeypatch, tmp_path, records)
    for record in records:
        name = fetch.relative_path(record)
        if record is not signal:
            path = cache / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(metadata_bytes[name])
            source = fetch.ensure_source(record, cache, log, representative=None)
        else:
            body = binary.read_bytes()
            source = {"record": record, "relative_path": name, "bytes": len(body),
                      "sha256": hashlib.sha256(body).hexdigest(),
                      "official_size_and_md5_pass": True, "cache_created_by_this_task": True}
            fetch.immutable_json(fetch.receipt_path(log, "source_receipts", name), source)
        remote = {"relative_path": name, "key": f"{fetch.PREFIX}/MIND_BIDS/{name}",
                  "sha256": source["sha256"],
                  "bytes": source["bytes"], "verification": fetch.FULL_GET,
                  "readback_bytes": source["bytes"]}
        fetch.immutable_json(fetch.receipt_path(log, "r2_receipts", name), remote)
    run_log = log / "runs" / Path(stem).name
    audited, events = audit.audit_run(fixture_root, relative_header, block_samples=17)
    audited["source_file_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    fetch.immutable_json(run_log / "audit.json", audited)
    fetch.immutable_json(run_log / "source_events.json", events)
    signal_source = fetch.load_json(fetch.receipt_path(log, "source_receipts", relative))
    pair = fetch.checked_audit_pair(run_log, signal_source, publish_receipt=True)
    closure = {"closed": True, "source_audit_integrity_pass": True,
               "source_relative_paths": relatives}
    if not legacy_closure:
        closure["source_audit_pair"] = pair
    else:
        (run_log / "audit_pair_closed.json").unlink()
    closure_path = run_log / "closed.json"
    fetch.immutable_json(closure_path, closure)

    def forbidden(*args, **kwargs):
        raise AssertionError("Closed run must reuse saved source and full-GET receipts")

    monkeypatch.setattr(fetch, "build_client", lambda: (object(), "test-private", "fixture"))
    monkeypatch.setattr(fetch, "audit_run", forbidden)
    monkeypatch.setattr(fetch, "transfer_file", forbidden)
    monkeypatch.setattr(fetch.requests, "get", forbidden)
    assert fetch.main() == 0
    assert fetch.load_json(closure_path) == closure
    assert fetch.checked_audit_pair(run_log, signal_source)["completed"] is True
    assert not (cache / relative).exists()
    state = fetch.load_json(log / "state.json")
    assert state["completed_runs"] == 1
    assert state["resumed_closed_run"] is True
    assert state["status"] == "bounded_requested_stage_closed"


def test_controller_failure_records_safe_code_and_preserves_partial_cache(
        monkeypatch, tmp_path, capsys):
    record = official_record()
    cache, log = configure_main(monkeypatch, tmp_path, [record])
    partial = cache / (fetch.relative_path(record) + ".partial")
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b"preserved partial")

    def unavailable():
        raise StorageError("AccessDenied")

    monkeypatch.setattr(fetch, "build_client", unavailable)
    assert fetch.main() == 1
    assert partial.read_bytes() == b"preserved partial"
    failure_paths = list((log / "failures").glob("*.json"))
    assert len(failure_paths) == 1
    failure = fetch.load_json(failure_paths[0])
    assert failure["error_code"] == "AccessDenied"
    assert failure["exception_message_logged"] is False
    assert failure["partial_or_signal_deleted"] is False
    assert fetch.load_json(log / "state.json")["status"] == "failed_preserved_cache"
    serialized = capsys.readouterr().out + "".join(p.read_text() for p in log.rglob("*.json"))
    assert "secret-test-token" not in serialized
    assert "signed.example" not in serialized


@pytest.mark.parametrize("exception_type", [
    fetch.requests.exceptions.ChunkedEncodingError,
    fetch.requests.exceptions.ReadTimeout,
])
def test_requests_stream_failure_with_none_response_preserves_cache_and_redacts_secret_message(
        monkeypatch, tmp_path, capsys, exception_type):
    body = b"synthetic source bytes"
    record = official_record(body=body)
    cache, log = configure_main(monkeypatch, tmp_path, [record])
    error = exception_type(
        "private signed request https://signed.example?token=request-secret-test-token", response=None)
    assert error.response is None

    class InterruptedResponse(RangeResponse):
        def iter_content(self, chunk_size):
            yield body[:4]
            raise error

    response = InterruptedResponse(body, 0, len(body) - 1, len(body))
    monkeypatch.setattr(fetch.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(fetch, "build_client", lambda: (object(), "test-private", "fixture"))
    monkeypatch.setattr(fetch.shutil, "disk_usage", lambda path: SimpleNamespace(free=2 * 1024 ** 3))

    def forbidden(*args, **kwargs):
        raise AssertionError("An interrupted source stream cannot reach audit or R2 publication")

    monkeypatch.setattr(fetch, "audit_run", forbidden)
    monkeypatch.setattr(fetch, "transfer_file", forbidden)
    assert fetch.main() == 1
    relative = fetch.relative_path(record)
    partial = cache / (relative + ".partial")
    assert partial.stat().st_size == len(body)
    assert partial.read_bytes()[:4] == body[:4]
    assert not (cache / relative).exists()
    assert response.closed is True
    assert not fetch.receipt_path(log, "source_receipts", relative).exists()
    assert not fetch.receipt_path(log, "r2_receipts", relative).exists()
    checkpoint = fetch.load_json(fetch.receipt_path(log, "range_checkpoints", relative))
    assert checkpoint["completed"] == {}
    failure_paths = list((log / "failures").glob("*.json"))
    assert len(failure_paths) == 1
    failure = fetch.load_json(failure_paths[0])
    assert failure["error_type"] == exception_type.__name__
    assert failure["error_code"] == ""
    assert failure["exception_message_logged"] is False
    assert failure["partial_or_signal_deleted"] is False
    assert fetch.load_json(log / "state.json")["status"] == "failed_preserved_cache"
    captured = capsys.readouterr()
    assert captured.err == ""
    serialized = captured.out + "".join(path.read_text() for path in log.rglob("*.json"))
    assert "request-secret-test-token" not in serialized
    assert "signed.example" not in serialized
    assert "Traceback" not in serialized
