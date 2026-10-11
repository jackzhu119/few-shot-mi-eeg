"""R2 transfer invariants: immutable objects and independent content evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_research_r2.py"
SPEC = importlib.util.spec_from_file_location("sync_research_r2", SCRIPT)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class StorageError(Exception):
    def __init__(self, code):
        super().__init__("must never log this secret https://signed.example?token=private")
        self.response = {"Error": {"Code": code}}


def ok(**values):
    return {"ResponseMetadata": {"HTTPStatusCode": 200}, **values}


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.parts = {}
        self.calls = []
        self.racing_body = None
        self.corrupt_after_put = False

    def head_object(self, **kwargs):
        self.calls.append(("head", kwargs))
        if kwargs["Key"] not in self.objects:
            raise StorageError("404")
        body, metadata = self.objects[kwargs["Key"]]
        return ok(ContentLength=len(body), Metadata=metadata)

    def get_object(self, **kwargs):
        self.calls.append(("get", kwargs))
        return ok(Body=io.BytesIO(self.objects[kwargs["Key"]][0]))

    def put_object(self, **kwargs):
        self.calls.append(("put", kwargs))
        assert kwargs["IfNoneMatch"] == "*"
        assert kwargs["ContentMD5"] == sync.transport_md5(kwargs["Body"])
        if self.racing_body is not None:
            self.objects[kwargs["Key"]] = (self.racing_body, kwargs["Metadata"])
        if kwargs["Key"] in self.objects:
            raise StorageError("PreconditionFailed")
        body = kwargs["Body"]
        if self.corrupt_after_put:
            body = b"X" * len(body)
        self.objects[kwargs["Key"]] = (body, kwargs["Metadata"])
        return ok()

    def create_multipart_upload(self, **kwargs):
        self.calls.append(("create", kwargs))
        self.parts["temporary"] = {"metadata": kwargs["Metadata"], "data": []}
        return ok(UploadId="temporary")

    def upload_part(self, **kwargs):
        self.calls.append(("part", kwargs))
        assert kwargs["ContentMD5"] == sync.transport_md5(kwargs["Body"])
        self.parts[kwargs["UploadId"]]["data"].append(kwargs["Body"])
        return ok(ETag=f"opaque-etag-{kwargs['PartNumber']}")

    def complete_multipart_upload(self, **kwargs):
        self.calls.append(("complete", kwargs))
        assert kwargs["IfNoneMatch"] == "*"
        if kwargs["Key"] in self.objects:
            raise StorageError("PreconditionFailed")
        parts = self.parts.pop(kwargs["UploadId"])
        self.objects[kwargs["Key"]] = (b"".join(parts["data"]), parts["metadata"])
        return ok()

    def abort_multipart_upload(self, **kwargs):
        self.calls.append(("abort", kwargs))
        self.parts.pop(kwargs["UploadId"], None)
        return ok()


def file_entry(tmp_path, body=b"real participant data", readback=True):
    path = tmp_path / "participant.edf"
    path.write_bytes(body)
    return path, {"relative_path": path.name, "key": "few-shot-mi-eeg/datasets/test/participant.edf",
                  "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                  "status": "planned", "selected_for_full_readback": readback}


@pytest.mark.parametrize("value", ["", "/few-shot-mi-eeg/data", "other/data",
                                  "few-shot-mi-eeg/../private", "few-shot-mi-eeg//data",
                                  "few-shot-mi-eeg/data/", "few-shot-mi-eeg/evil\\data"])
def test_noncanonical_or_outside_project_prefix_is_refused(value):
    with pytest.raises(ValueError):
        sync.safe_key_prefix(value)


@pytest.mark.parametrize("name", [".env", ".env.production", ".ENV.PRODUCTION",
                                 "credentials.json", "x.pem",
                                 "auth.json", "id_ed25519"])
def test_secret_file_names_are_refused(tmp_path, name):
    (tmp_path / name).write_text("private")
    with pytest.raises(ValueError, match="protected"):
        sync.make_plan(tmp_path, "few-shot-mi-eeg/datasets/test", "all")


def test_symlinks_are_refused_including_directory_links(tmp_path):
    (tmp_path / "outside-link").symlink_to("/tmp", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        sync.safe_source_files(tmp_path)


def test_sample_plan_selects_largest_file_for_each_format(tmp_path):
    for name, body in {"small.edf": b"a", "large.edf": b"abcdef", "events.tsv": b"abc"}.items():
        (tmp_path / name).write_bytes(body)
    plan = sync.make_plan(tmp_path, "few-shot-mi-eeg/datasets/test", "sample")
    assert {e["relative_path"] for e in plan if e["selected_for_full_readback"]} == {
        "large.edf", "events.tsv"}
    assert sum(e["bytes"] for e in plan) == 10


def test_incremental_include_selects_only_requested_new_participants(tmp_path):
    for subject in ["sub-1", "sub-11"]:
        path = tmp_path / subject / "ses-01" / "data.edf"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"EEG")
    plan = sync.make_plan(tmp_path, "few-shot-mi-eeg/datasets/test", "sample", ["sub-11/**"])
    assert [e["relative_path"] for e in plan] == ["sub-11/ses-01/data.edf"]


def test_mistyped_include_pattern_fails_instead_of_reporting_empty_success(tmp_path):
    file_entry(tmp_path)
    with pytest.raises(ValueError, match="select"):
        sync.make_plan(tmp_path, "few-shot-mi-eeg/datasets/test", "sample", ["sub-missing/**"])


def test_new_object_has_conditional_create_and_independent_get_sha(tmp_path):
    path, entry = file_entry(tmp_path)
    store = MemoryStore()
    result = sync.transfer_file(store, "private", path, entry)
    assert result["status"] == "uploaded_content_verified"
    assert result["verification"] == "full_get_sha256_verified"
    assert result["readback_bytes"] == entry["bytes"]
    assert store.objects[entry["key"]][0] == path.read_bytes()


def test_head_metadata_check_is_not_reported_as_content_readback(tmp_path):
    path, entry = file_entry(tmp_path, readback=False)
    store = MemoryStore()
    result = sync.transfer_file(store, "private", path, entry)
    assert result["verification"] == "head_length_and_sha256_metadata_verified"
    assert result["readback_bytes"] == 0
    assert not any(name == "get" for name, _ in store.calls)


def test_reuse_requires_full_get_even_when_sample_did_not_select_file(tmp_path):
    path, entry = file_entry(tmp_path, readback=False)
    store = MemoryStore()
    store.objects[entry["key"]] = (path.read_bytes(), {"sha256": entry["sha256"]})
    result = sync.transfer_file(store, "private", path, entry)
    assert result["status"] == "reused_content_verified"
    assert result["uploaded_bytes"] == 0
    assert result["readback_bytes"] == entry["bytes"]
    assert not any(name == "put" for name, _ in store.calls)


@pytest.mark.parametrize("metadata", [{}, {"sha256": "0" * 64}])
def test_conflicting_existing_key_is_never_overwritten(tmp_path, metadata):
    path, entry = file_entry(tmp_path)
    store = MemoryStore()
    original = b"Z" * entry["bytes"]
    store.objects[entry["key"]] = (original, metadata)
    with pytest.raises(ValueError, match="new version"):
        sync.transfer_file(store, "private", path, entry)
    assert store.objects[entry["key"]][0] == original
    assert not any(name in {"put", "create"} for name, _ in store.calls)


def test_full_readback_detects_corruption_despite_matching_metadata(tmp_path):
    path, entry = file_entry(tmp_path)
    store = MemoryStore()
    store.corrupt_after_put = True
    with pytest.raises(ValueError, match="readback"):
        sync.transfer_file(store, "private", path, entry)


def test_changed_local_source_is_refused_before_single_put(tmp_path):
    path, entry = file_entry(tmp_path)
    path.write_bytes(b"changed after plan")
    store = MemoryStore()
    with pytest.raises(ValueError, match="changed"):
        sync.transfer_file(store, "private", path, entry)
    assert not store.objects
    assert not any(name == "put" for name, _ in store.calls)


def test_racing_create_verifies_winner_and_never_overwrites(tmp_path):
    path, entry = file_entry(tmp_path)
    store = MemoryStore()
    store.racing_body = path.read_bytes()
    result = sync.transfer_file(store, "private", path, entry)
    assert result["status"] == "concurrent_create_content_verified"
    assert result["readback_bytes"] == entry["bytes"]


def test_multipart_completion_is_conditional_and_opaque_etags_are_not_hashes(tmp_path):
    path, entry = file_entry(tmp_path, b"a" * (6 * sync.MIB))
    store = MemoryStore()
    result = sync.transfer_file(store, "private", path, entry,
                                multipart_threshold=sync.MIB, part_size=5 * sync.MIB)
    assert result["multipart_parts"] == 2
    assert result["verification"] == "full_get_sha256_verified"
    assert any(name == "complete" and values["IfNoneMatch"] == "*"
               for name, values in store.calls)
    assert not store.parts


def test_multipart_changed_source_aborts_without_publishing_partial_object(tmp_path):
    path, entry = file_entry(tmp_path, b"a" * (6 * sync.MIB))
    path.write_bytes(b"b" * entry["bytes"])
    store = MemoryStore()
    with pytest.raises(ValueError, match="changed"):
        sync.transfer_file(store, "private", path, entry,
                           multipart_threshold=sync.MIB, part_size=5 * sync.MIB)
    assert not store.parts
    assert not store.objects
    assert any(name == "abort" for name, _ in store.calls)
    assert not any(name == "complete" for name, _ in store.calls)


def test_multipart_completion_race_preserves_winner_and_aborts_parts(tmp_path):
    path, entry = file_entry(tmp_path, b"a" * (6 * sync.MIB))

    class ConcurrentStore(MemoryStore):
        def complete_multipart_upload(self, **kwargs):
            self.objects[kwargs["Key"]] = (b"original winning bytes", {"sha256": "different"})
            return super().complete_multipart_upload(**kwargs)

    store = ConcurrentStore()
    with pytest.raises(StorageError):
        sync.transfer_file(store, "private", path, entry,
                           multipart_threshold=sync.MIB, part_size=5 * sync.MIB)
    assert store.objects[entry["key"]][0] == b"original winning bytes"
    assert not store.parts
    assert any(name == "abort" for name, _ in store.calls)


def test_error_receipt_redacts_exception_text_and_signed_url(tmp_path):
    _, entry = file_entry(tmp_path)

    class Unavailable(MemoryStore):
        def head_object(self, **kwargs):
            raise StorageError("AccessDenied")

    result = sync.guarded_transfer(Unavailable(), "private", tmp_path, entry)
    serialized = json.dumps(result)
    assert result["status"] == "failed"
    assert result["error_code"] == "AccessDenied"
    assert "secret" not in serialized and "signed.example" not in serialized


def test_receipt_distinguishes_sha_readback_from_metadata_evidence(tmp_path):
    path, entry = file_entry(tmp_path, readback=False)
    record = sync.transfer_file(MemoryStore(), "private", path, entry)
    receipt = {"files": [record]}
    output = tmp_path / "receipt.json"
    sync.write_receipt(output, receipt)
    saved = json.loads(output.read_text())
    assert saved["totals"]["verified_files"] == 1
    assert saved["totals"]["full_get_sha256_verified_files"] == 0
    assert saved["totals"]["readback_bytes"] == 0
    assert not output.with_suffix(".json.partial").exists()
