"""Network-free checks of genuine download integrity and subset boundaries."""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fetch_physionet_imagery import (
    checked_entry,
    annotation_difference_inventory,
    compare_sidecar_annotations,
    destination,
    fetch_file,
    source_selection,
)


def entry(data=b"official waveform bytes"):
    return {"path": "S001/S001R04.edf", "size": len(data),
            "url": "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf",
            "sha256": hashlib.sha256(data).hexdigest()}


class Response:
    def __init__(self, data, length, status=200):
        self.data = data
        self.status_code = status
        self.headers = {"Content-Length": str(length)}
        self.closed = False

    def iter_content(self, chunk_size):
        yield self.data[:3]
        yield self.data[3:]

    def close(self):
        self.closed = True


class Session:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url, **kwargs):
        assert kwargs["allow_redirects"] is False
        self.url = url
        return self.response


@pytest.mark.parametrize("bad_path", ["../S001/S001R04.edf", "/S001/S001R04.edf",
                                      "S001/S002R04.edf", "S001/S001R03.edf",
                                      "S001/S001R06.edf", "S110/S110R04.edf",
                                      "S001/S001R04.edf.zip"])
def test_paths_cannot_escape_or_include_execution_and_other_task_runs(bad_path):
    value = entry()
    value["path"] = bad_path
    with pytest.raises(ValueError):
        checked_entry(value)


@pytest.mark.parametrize("url", ["http://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf",
                                 "https://example.org/S001/S001R04.edf",
                                 "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf?x=1"])
def test_endpoint_and_version_are_pinned(url):
    value = entry()
    value["url"] = url
    with pytest.raises(ValueError):
        checked_entry(value)


@pytest.mark.parametrize("key,value", [("subject", "S002"), ("run", 3), ("type", "execution")])
def test_participant_and_run_metadata_cannot_disagree_with_original_file_identity(key, value):
    record = entry()
    record[key] = value
    with pytest.raises(ValueError, match="identity disagrees"):
        checked_entry(record)


def test_pinned_actual_metadata_covers_every_subject_without_other_run_types():
    files = source_selection()
    assert len(files) == 654
    assert len({r["subject"] for r in files}) == 109
    assert {r["run"] for r in files} == {4, 8, 12}
    assert sum(r["type"] == "edf" for r in files) == 327
    assert all(r["sha256"] for r in files)


def test_verified_body_is_published_and_reused_without_network(tmp_path):
    data = b"official waveform bytes"
    value = entry(data)
    response = Response(data, len(data))
    result = fetch_file(tmp_path, value, session_factory=lambda: Session(response))
    assert result["status"] == "downloaded_verified"
    assert result["actual_sha256"] == value["sha256"]
    assert response.closed
    assert (tmp_path / value["path"]).read_bytes() == data

    def forbidden_network():
        raise AssertionError("Existing verified bytes must not trigger HTTP")

    assert fetch_file(tmp_path, value, session_factory=forbidden_network)["status"] == "reused_verified"


def test_official_archive_transport_keeps_canonical_version_and_sha_identity(tmp_path):
    data = b"official waveform bytes"
    value = entry(data)
    session = Session(Response(data, len(data)))
    result = fetch_file(tmp_path, value, session_factory=lambda: session,
                        transport="official_archive")
    assert result["status"] == "downloaded_verified"
    assert result["url"] == value["url"]
    assert result["actual_sha256"] == value["sha256"]
    assert session.url == "https://archive.physionet.org/physiobank/database/eegmmidb/S001/S001R04.edf"


def test_transport_cannot_be_replaced_with_an_unverified_mirror(tmp_path):
    with pytest.raises(ValueError, match="two official"):
        fetch_file(tmp_path, entry(), transport="https://example.org/")


def test_mismatched_existing_bytes_are_retained_and_not_overwritten(tmp_path):
    value = entry()
    path = tmp_path / value["path"]
    path.parent.mkdir()
    path.write_bytes(b"different scientific data")
    with pytest.raises(ValueError, match="Existing file mismatches"):
        fetch_file(tmp_path, value)
    assert path.read_bytes() == b"different scientific data"


@pytest.mark.parametrize("data,length", [(b"corrupted waveform", 23),
                                        (b"official waveform byteX", 23),
                                        (b"official waveform bytes!", 23),
                                        (b"official waveform bytes", 22)])
def test_length_and_checksum_failure_never_publish_a_file(tmp_path, monkeypatch, data, length):
    monkeypatch.setattr("fetch_physionet_imagery.time.sleep", lambda _: None)
    value = entry()
    response = Response(data, length)
    result = fetch_file(tmp_path, value, session_factory=lambda: Session(response))
    assert result["status"] == "failed"
    assert len(result["attempts"]) == 2
    assert not (tmp_path / value["path"]).exists()
    assert response.closed


def test_redirect_is_refused_even_if_other_body_looks_correct(tmp_path, monkeypatch):
    monkeypatch.setattr("fetch_physionet_imagery.time.sleep", lambda _: None)
    value = entry()
    response = Response(b"official waveform bytes", value["size"], status=302)
    result = fetch_file(tmp_path, value, session_factory=lambda: Session(response))
    assert result["status"] == "failed"
    assert not (tmp_path / value["path"]).exists()


def test_symlink_destination_cannot_write_outside_data_root(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "S001").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        destination(root, "S001/S001R04.edf")


def test_official_wfdb_initial_rest_omission_is_explicit_without_inventing_an_event():
    result = compare_sidecar_annotations(
        [0.0, 4.1, 8.2], [4.1, 4.1, 4.1], ["T0", "T1", "T0"],
        [656, 1312], ["T1 duration: 4.1", "T0 duration: 4.1"], ['"', '"'], 160.0)
    assert result["sidecar_annotation_count"] == 2
    assert result["edf_annotation_count"] == 3
    assert result["edf_zero_onset_rest_missing_from_sidecar"][0]["edf_annotation_index"] == 0
    assert result["no_missing_event_was_invented"] is True


def test_complete_annotation_agreement_is_allowed_when_zero_onset_is_present():
    result = compare_sidecar_annotations(
        [0.0, 4.1], [4.1, 4.1], ["T0", "T1"], [0, 656],
        ["T0 duration: 4.1", "T1 duration: 4.1"], ['"', '"'], 160.0)
    assert result["edf_zero_onset_rest_missing_from_sidecar"] == []


@pytest.mark.parametrize("samples,notes,symbols", [
    ([657, 1312], ["T1 duration: 4.1", "T0 duration: 4.1"], ['"', '"']),
    ([656, 1312], ["T2 duration: 4.1", "T0 duration: 4.1"], ['"', '"']),
    ([656, 1312], ["T1 duration: 3.1", "T0 duration: 4.1"], ['"', '"']),
    ([656, 1312], ["T9 duration: 4.1", "T0 duration: 4.1"], ['"', '"']),
    ([656, 1312], ["T1 duration: 4.1", "T0 duration: 4.1"], ["N", '"']),
    ([656], ["T1 duration: 4.1"], ['"']),
])
def test_label_time_duration_syntax_and_missing_event_disagreements_are_rejected(
        samples, notes, symbols):
    with pytest.raises(ValueError):
        compare_sidecar_annotations(
            [0.0, 4.1, 8.2], [4.1, 4.1, 4.1], ["T0", "T1", "T0"],
            samples, notes, symbols, 160.0)


def test_initial_movement_cannot_be_treated_as_permitted_missing_rest():
    with pytest.raises(ValueError, match="counts differ"):
        compare_sidecar_annotations(
            [0.0, 4.1], [4.1, 4.1], ["T1", "T0"], [656],
            ["T0 duration: 4.1"], ['"'], 160.0)


def test_missing_imagery_remains_identified_without_being_repaired():
    result = annotation_difference_inventory(
        [0.0, 4.1, 8.2, 12.3], [4.1, 4.1, 4.1, 4.1], ["T0", "T1", "T0", "T2"],
        [656, 1312], ["T1 duration: 4.1", "T0 duration: 4.1"], ['"', '"'], 160.0)
    assert result["missing_nonzero_edf_annotation_count"] == 1
    assert result["missing_nonzero_edf_annotation_counts_by_label"] == {"T0": 0, "T1": 0, "T2": 1}
    assert [r["edf_annotation_index"] for r in result["unmatched_edf_annotations"]] == [0, 3]
    assert result["unmatched_wfdb_annotations"] == []
    assert result["source_streams_modified"] is False


def test_conflicting_sidecar_label_remains_two_unmatched_source_identities():
    result = annotation_difference_inventory(
        [0.0, 4.1], [4.1, 4.1], ["T0", "T1"], [656],
        ["T2 duration: 4.1"], ['"'], 160.0)
    assert result["matched_annotation_count"] == 0
    assert result["missing_nonzero_edf_annotation_counts_by_label"]["T1"] == 1
    assert result["unmatched_wfdb_annotations"][0]["wfdb_annotation_index"] == 0
