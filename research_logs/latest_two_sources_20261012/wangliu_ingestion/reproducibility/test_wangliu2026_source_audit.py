"""Source-only Wang/Liu safeguards, exercised with tiny local synthetic fixtures."""

import hashlib
import importlib.util
import io
import json
import stat
import struct
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import scipy.io

SCRIPTS = Path(__file__).parents[1] / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


download = load_script("download_wangliu2026_source")
audit = load_script("audit_wangliu2026_source")


class Response:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, chunk_size):
        yield self.body[:1]
        yield b""
        yield self.body[1:]


def fake_official_bytes(monkeypatch, body=b"abc"):
    monkeypatch.setattr(download, "EXPECTED_BYTES", len(body))
    monkeypatch.setattr(download, "EXPECTED_MD5", hashlib.md5(body).hexdigest())
    return body


def test_official_fixed_archive_identity_and_checksum_gate():
    assert download.SOURCE_URL == "https://ndownloader.figshare.com/files/64877880"
    assert download.EXPECTED_BYTES == 5_175_273_351
    assert download.EXPECTED_MD5 == "74dabab47f477e5bc0510b1e2e705c5a"
    download.enforce_transport(download.EXPECTED_BYTES, download.EXPECTED_MD5)
    with pytest.raises(ValueError, match="size/MD5 mismatch"):
        download.enforce_transport(download.EXPECTED_BYTES - 1, download.EXPECTED_MD5)
    with pytest.raises(ValueError, match="size/MD5 mismatch"):
        download.enforce_transport(download.EXPECTED_BYTES, "0" * 32)


def test_streamed_checksum_match_atomically_finalizes_then_reuses_without_network(
    tmp_path, monkeypatch,
):
    body = fake_official_bytes(monkeypatch)
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response(body)

    monkeypatch.setattr(download.requests, "get", get)
    destination = tmp_path / "sourcedata.zip"
    receipt = tmp_path / "receipt.json"
    result = download.download(destination, receipt)
    assert destination.read_bytes() == body
    assert not destination.with_suffix(".zip.partial").exists()
    assert result["status"] == "official_transport_verified"
    assert result["sha256"] == hashlib.sha256(body).hexdigest()
    assert result["md5"] == hashlib.md5(body).hexdigest()
    assert calls == [(download.SOURCE_URL, {"stream": True, "timeout": (30, 180)})]
    assert json.loads(receipt.read_text())["version"] == 11
    monkeypatch.setattr(download.requests, "get", lambda *_args, **_kwargs: pytest.fail("network"))
    reused = download.download(destination, receipt)
    assert reused["status"] == "existing_official_transport_verified"
    assert reused["sha256"] == result["sha256"]


@pytest.mark.parametrize("body", [b"xyz", b"ab", b"abcd"])
def test_wrong_digest_truncated_or_oversize_body_cannot_finalize(tmp_path, monkeypatch, body):
    fake_official_bytes(monkeypatch)
    monkeypatch.setattr(download.requests, "get", lambda *_args, **_kwargs: Response(body))
    destination = tmp_path / "sourcedata.zip"
    receipt = tmp_path / "receipt.json"
    with pytest.raises(RuntimeError, match="transport acquisition failed"):
        download.download(destination, receipt)
    assert not destination.exists()
    result = json.loads(receipt.read_text())
    assert result["status"] == "failed"
    assert "sha256" not in result


def test_invalid_existing_archive_and_unverified_partial_are_not_reused(tmp_path, monkeypatch):
    fake_official_bytes(monkeypatch)
    monkeypatch.setattr(download.requests, "get", lambda *_args, **_kwargs: pytest.fail("network"))
    destination = tmp_path / "sourcedata.zip"
    receipt = tmp_path / "receipt.json"
    destination.write_bytes(b"xyz")
    with pytest.raises(ValueError, match="size/MD5 mismatch"):
        download.download(destination, receipt)
    assert destination.read_bytes() == b"xyz"
    assert not receipt.exists()
    destination.unlink()
    partial = destination.with_suffix(".zip.partial")
    partial.write_bytes(b"abc")
    with pytest.raises(ValueError, match="Unverified partial"):
        download.download(destination, receipt)
    assert partial.read_bytes() == b"abc"
    assert not destination.exists()


def test_archive_gate_runs_before_output_or_scratch_mutation(tmp_path):
    archive = tmp_path / "sourcedata.zip"
    archive.write_bytes(b"not official")
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    with pytest.raises(ValueError, match="size/MD5 mismatch"):
        audit.audit_archive(archive, output, scratch)
    assert not output.exists()
    assert not scratch.exists()


@pytest.mark.parametrize("name", [
    "../outside.fdt", "/outside.fdt", "a/../outside.fdt", "a\\outside.fdt",
    "a//outside.fdt", "a/./outside.fdt", "C:/outside.fdt",
])
def test_unsafe_zip_paths_are_rejected_without_extraction(tmp_path, name):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr(name, b"data")
    with zipfile.ZipFile(archive) as source, pytest.raises(ValueError, match="Unsafe ZIP"):
        audit.safe_members(source)
    assert list(tmp_path.iterdir()) == [archive]


def test_duplicate_zip_names_and_symlink_members_are_rejected(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr("a.fdt", b"abc")
        with pytest.warns(UserWarning, match="Duplicate name"):
            source.writestr("a.fdt", b"xyz")
    with zipfile.ZipFile(archive) as source, pytest.raises(ValueError, match="Duplicate ZIP"):
        audit.safe_members(source)
    link = zipfile.ZipInfo("link.fdt")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr(link, "outside")
    with zipfile.ZipFile(archive) as source, pytest.raises(ValueError, match="Unsafe ZIP"):
        audit.safe_members(source)


def test_member_crc_sha_receipt_and_corruption_cleanup(tmp_path):
    archive = tmp_path / "source.zip"
    body = b"synthetic member payload"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as source:
        source.writestr("a.fdt", body)
    destination = tmp_path / "a.fdt"
    with zipfile.ZipFile(archive) as source:
        info = source.getinfo("a.fdt")
        receipt = audit.extract_member(source, info, destination)
        payload_offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    assert destination.read_bytes() == body
    assert receipt["sha256"] == hashlib.sha256(body).hexdigest()
    assert receipt["crc32_verified"]
    assert receipt["crc32"] == receipt["central_directory_crc32"]
    corrupted = bytearray(archive.read_bytes())
    corrupted[payload_offset] ^= 1
    archive.write_bytes(corrupted)
    destination.unlink()
    with zipfile.ZipFile(archive) as source, pytest.raises(zipfile.BadZipFile, match="CRC"):
        audit.extract_member(source, source.getinfo("a.fdt"), destination)
    assert not destination.exists()


def test_refused_extraction_preserves_an_existing_destination(tmp_path):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr("a.fdt", b"new bytes")
    destination = tmp_path / "a.fdt"
    destination.write_bytes(b"prior bytes")
    with zipfile.ZipFile(archive) as source, pytest.raises(FileExistsError):
        audit.extract_member(source, source.getinfo("a.fdt"), destination)
    assert destination.read_bytes() == b"prior bytes"


@pytest.mark.parametrize("member", [
    "sub-01/pre/sub-02_B_pre_01_original.set",
    "sub-01/pre/sub-01_B_post_01_original.set",
    "sub-01/pre/sub-01_B_pre_05_original.set",
    "sub-01/pre/sub-01_Z_pre_01_original.set",
])
def test_source_identity_keeps_directory_subject_phase_group_and_run(member):
    with pytest.raises(ValueError, match="published raw recording path"):
        audit.source_identity(member)
    identity = audit.source_identity("sub-01/follow/sub-01_T_follow_04_original.set")
    assert (identity["subject_id"], identity["phase"], identity["group_code"], identity["run"]) == (
        "sub-01", "follow", "T", 4,
    )


def test_zero_and_absent_native_durations_keep_source_fields_without_inferred_windows():
    eeg = {"srate": 250, "pnts": 85000, "event": [
        {"type": "1", "latency": np.float64(5685), "urevent": np.int64(1)},
        {"type": "2", "latency": 7827, "duration": 0, "source_note": "unchanged"},
        {"type": "3", "latency": 11815, "duration": 0},
    ]}
    rows = audit.native_events(eeg, "sub-01/pre/sub-01_B_pre_01_original")
    assert len(rows) == 3
    assert rows[0]["onset_sample_0based"] == 5684
    assert rows[0]["onset_seconds"] == pytest.approx(22.736)
    assert rows[1]["onset_seconds"] == pytest.approx(31.304)
    assert rows[0]["duration_samples"] is None
    assert rows[0]["duration_seconds"] is None
    assert rows[1]["duration_samples"] == 0
    assert rows[1]["native_fields"]["source_note"] == "unchanged"
    assert rows[0]["native_fields"]["urevent"] == 1
    assert all(not row["native_window_eligible"] for row in rows)
    assert all(not row["analysis_window_inferred"] for row in rows)
    assert all("no_window_inferred" in row["window_status"] for row in rows)
    assert all("scalp59_native_window_sha256" not in row for row in rows)
    json.dumps(rows, allow_nan=False)


@pytest.mark.parametrize("label,latency,duration,eligible", [
    ("2", 1, 10, True), ("2", 91, 10, True), ("2", 92, 10, False),
    ("2", 0, 10, False), ("2", 1.5, 10, False), ("2", 1, 0.5, False),
    ("2", 1, -1, False), ("unknown", 1, 10, False),
])
def test_only_complete_integral_positive_native_windows_are_eligible(
    label, latency, duration, eligible,
):
    row = audit.native_events({"srate": 250, "pnts": 100, "event": {
        "type": label, "latency": latency, "duration": duration,
    }}, "source")[0]
    assert row["native_window_eligible"] is eligible
    assert not row["analysis_window_inferred"]


def test_auxiliary_labels_never_inherit_mne_eeg_default_or_unknown_brain_type():
    labels = audit.SCALP_LABELS + ["ECG", "HEOR", "HEOL", "VEOU", "VEOL", "unverified"]
    types = audit.channel_types(labels)
    assert len(audit.SCALP_LABELS) == 59
    assert types[:59] == ["eeg"] * 59
    assert types[59:] == ["ecg", "eog", "eog", "eog", "eog", "misc"]


class Raw:
    def __init__(self, values, names=("C3", "C4", "ECG")):
        self.values = values
        self.ch_names = list(names)
        self.n_times = np.int64(values.shape[1])
        self.ranges = []

    def get_data(self, *, start, stop):
        self.ranges.append((start, stop))
        return self.values[:, start:stop]


def canonical_block_hash(values):
    # This independent oracle constructs the exact documented bytes with struct.
    digest = hashlib.sha256()
    for start in range(0, values.shape[1], 16384):
        block = values[:, start:start + 16384]
        scalars = [float(value) for channel in block for value in channel]
        digest.update(struct.pack(f"<{len(scalars)}d", *scalars))
    return digest.hexdigest()


def test_full_numeric_hash_uses_fixed_chronological_blocks_little_f64_and_channel_order():
    values = np.vstack((np.arange(16401) * 1e-6, np.arange(16401)[::-1] * 2e-6,
                        np.full(16401, -0.37500003125)))
    raw = Raw(values.astype(">f8"))
    result = audit.audit_signal(raw, [0, 1])
    assert raw.ranges == [(0, 16384), (16384, 16401)]
    assert result["all64_numeric_sha256"] == canonical_block_hash(values)
    assert result["scalp59_numeric_sha256"] == canonical_block_hash(values[:2])
    assert result["all64_numeric_sha256"] != canonical_block_hash(values[[1, 0, 2]])
    assert audit.audit_signal(Raw(values.astype("<f8")), [0, 1])["all64_numeric_sha256"] == result[
        "all64_numeric_sha256"
    ]
    assert result["numeric_hash_channel_labels_scalp"] == ["C3", "C4"]
    assert result["continuous_numeric_values"] == 3 * 16401
    assert result["constant_channels"] == ["ECG"]
    ecg = result["per_channel"][2]
    assert ecg["std_volts"] == 0
    assert ecg["large_absolute_mean_flag"]
    assert not ecg["scalp_peak_over_1mV_flag"]
    json.dumps(result, allow_nan=False)


def test_last_nonfinite_continuous_sample_is_recorded_without_event_window_selection():
    values = np.zeros((3, 16401))
    values[0, -1] = np.inf
    result = audit.audit_signal(Raw(values), [0, 1])
    assert not result["all_continuous_samples_finite"]
    assert result["per_channel"][0]["nonfinite_samples"] == 1
    assert result["per_channel"][0]["finite_samples"] == 16400
    assert result["continuous_numeric_values"] == 3 * 16401
    json.dumps(result, allow_nan=False)


def duplicate_row(source, subject, phase, run, **updates):
    return {"source_id": source, "subject_id": subject, "phase": phase, "run": run,
            "all64_numeric_sha256": "a" * 64, "scalp59_numeric_sha256": "b" * 64,
            "n_times": 100, "sampling_rate_hz": 250,
            "numeric_hash_channel_labels_all": ["C3", "ECG"],
            "numeric_hash_channel_labels_scalp": ["C3"], **updates}


def test_exact_duplicates_keep_cross_identity_phase_and_run_reuse_distinct():
    rows = [duplicate_row("a", "sub-01", "pre", 1),
            duplicate_row("b", "sub-01", "pre", 2),
            duplicate_row("c", "sub-01", "post", 1),
            duplicate_row("d", "sub-02", "pre", 1)]
    groups = audit.duplicate_groups(rows, "all64_numeric_sha256", "source_id")
    assert len(groups) == 1
    assert groups[0]["source_ids"] == ["a", "b", "c", "d"]
    assert groups[0]["subject_ids"] == ["sub-01", "sub-02"]
    assert groups[0]["cross_published_identity"]
    assert groups[0]["within_subject_cross_phase_reuse"]
    assert groups[0]["within_subject_same_phase_run_reuse"]
    within_phase = audit.duplicate_groups(rows[:2], "all64_numeric_sha256", "source_id")[0]
    assert not within_phase["cross_published_identity"]
    assert not within_phase["within_subject_cross_phase_reuse"]
    assert within_phase["within_subject_same_phase_run_reuse"]


def test_duplicate_keys_require_equal_labels_order_shape_rate_and_valid_digest():
    rows = [duplicate_row("a", "sub-01", "pre", 1),
            duplicate_row("b", "sub-02", "pre", 1, numeric_hash_channel_labels_all=["ECG", "C3"]),
            duplicate_row("c", "sub-03", "pre", 1, n_times=101),
            duplicate_row("d", "sub-04", "pre", 1, sampling_rate_hz=500),
            duplicate_row("e", "sub-05", "pre", 1, all64_numeric_sha256=None),
            duplicate_row("f", "sub-06", "pre", 1, all64_numeric_sha256=None)]
    assert audit.duplicate_groups(rows, "all64_numeric_sha256", "source_id") == []
    # A scalp fingerprint ignores auxiliary column order but retains its own labels.
    assert len(audit.duplicate_groups(rows[:2], "scalp59_numeric_sha256", "source_id")) == 1


def test_positive_native_window_duplicate_groups_use_event_identity():
    rows = [duplicate_row("a", "sub-01", "pre", 1, event_id="a/event-001",
                          scalp59_native_window_sha256="c" * 64),
            duplicate_row("b", "sub-02", "post", 2, event_id="b/event-002",
                          scalp59_native_window_sha256="c" * 64)]
    group = audit.duplicate_groups(rows, "scalp59_native_window_sha256", "event_id")[0]
    assert group["source_ids"] == ["a/event-001", "b/event-002"]
    assert group["cross_published_identity"]


def test_pair_scratch_is_cleaned_after_invalid_native_fdt_reference(tmp_path):
    member = "sub-01/pre/sub-01_B_pre_01_original.set"
    header = {"nbchan": 1, "pnts": 10, "trials": 1, "srate": 250,
              "chanlocs": {"labels": "C3"}, "data": "../outside.fdt"}
    set_bytes = io.BytesIO()
    scipy.io.savemat(set_bytes, {"EEG": header})
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr(member, set_bytes.getvalue())
        source.writestr(member.replace(".set", ".fdt"), np.zeros(10, dtype="<f4").tobytes())
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    with zipfile.ZipFile(archive) as source, pytest.raises(ValueError, match="paired FDT basename"):
        audit.audit_pair(source, source.getinfo(member),
                         source.getinfo(member.replace(".set", ".fdt")), scratch)
    assert list(scratch.iterdir()) == []
    assert not (tmp_path / "outside.fdt").exists()


def tiny_eeglab_pair(tmp_path):
    member = "sub-01/pre/sub-01_B_pre_01_original.set"
    labels = audit.SCALP_LABELS + list(audit.AUX_TYPES)
    chanlocs = np.empty(len(labels), dtype=[("labels", "O")])
    for index, label in enumerate(labels):
        chanlocs[index]["labels"] = label
    events = np.empty(2, dtype=[("type", "O"), ("latency", "O")])
    events[0] = ("1", 1)
    events[1] = ("2", 5)
    n_times = 10
    values = (np.arange(len(labels) * n_times).reshape(len(labels), n_times) - 320).astype("<f4")
    header = {"nbchan": len(labels), "pnts": n_times, "trials": 1, "srate": 250,
              "xmin": 0, "xmax": (n_times - 1) / 250, "chanlocs": chanlocs,
              "data": Path(member).with_suffix(".fdt").name,
              "datfile": Path(member).with_suffix(".fdt").name,
              "event": events, "ref": "common", "history": "unchanged source history"}
    set_bytes = io.BytesIO()
    scipy.io.savemat(set_bytes, {"EEG": header})
    fdt_bytes = values.tobytes(order="F")
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr(member, set_bytes.getvalue())
        source.writestr(member.replace(".set", ".fdt"), fdt_bytes)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    return archive, member, scratch, values, fdt_bytes


def test_real_tiny_eeglab_pair_preserves_source_scaling_and_preprocessing_boundary(tmp_path):
    archive, member, scratch, values, fdt_bytes = tiny_eeglab_pair(tmp_path)
    with zipfile.ZipFile(archive) as source:
        report, rows, receipts = audit.audit_pair(
            source, source.getinfo(member), source.getinfo(member.replace(".set", ".fdt")), scratch,
        )
    expected_volts = values.astype(np.float64) * 1e-6
    assert report["all64_numeric_sha256"] == canonical_block_hash(expected_volts)
    assert report["scalp59_numeric_sha256"] == canonical_block_hash(expected_volts[:59])
    assert report["channel_type_counts_from_labels"] == {"eeg": 59, "ecg": 1, "eog": 4}
    assert report["mne_default_channel_type_counts"] == {"eeg": 64}
    assert report["channel_layout_matches_verified_59_scalp_plus5_aux"]
    assert report["preprocessing_performed"] == []
    assert report["native_reference_field"] == "common"
    assert report["native_history_text"] == "unchanged source history"
    assert report["mne_native_unit_scale"].startswith("EEGLAB microvolts to volts, 1e-6")
    assert not report["future_analysis_qualified"]
    assert not report["expert_artifact_quality_certified"]
    assert report["native_events_match_mne_annotations"]
    assert report["native_positive_duration_window_count"] == 0
    assert [row["onset_sample_0based"] for row in rows] == [0, 4]
    assert all(row["duration_samples"] is None for row in rows)
    assert all("scalp59_native_window_sha256" not in row for row in rows)
    assert receipts[1]["sha256"] == hashlib.sha256(fdt_bytes).hexdigest()
    assert all(receipt["crc32_verified"] for receipt in receipts)
    assert report["scratch_deleted_on_exit"]
    assert list(scratch.iterdir()) == []


def test_reader_closes_and_pair_scratch_is_deleted_after_injected_scan_failure(tmp_path, monkeypatch):
    archive, member, scratch, *_ = tiny_eeglab_pair(tmp_path)
    read_original = audit.mne.io.read_raw_eeglab
    closed = []

    def read(*args, **kwargs):
        raw = read_original(*args, **kwargs)
        close_original = raw.close

        def close():
            closed.append(raw)
            close_original()

        monkeypatch.setattr(raw, "close", close)
        return raw

    def fail_scan(*args, **kwargs):
        raise ValueError("injected full scan failure")

    monkeypatch.setattr(audit.mne.io, "read_raw_eeglab", read)
    monkeypatch.setattr(audit, "audit_signal", fail_scan)
    with zipfile.ZipFile(archive) as source, pytest.raises(ValueError, match="injected full scan"):
        audit.audit_pair(source, source.getinfo(member),
                         source.getinfo(member.replace(".set", ".fdt")), scratch)
    assert len(closed) == 1
    assert list(scratch.iterdir()) == []
