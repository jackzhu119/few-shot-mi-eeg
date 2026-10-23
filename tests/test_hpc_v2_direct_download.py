import hashlib
import importlib.util
import io
import json
from pathlib import Path
import urllib.error

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2/download_on_hpc.py"
spec = importlib.util.spec_from_file_location("hpc_direct", MODULE_PATH)
direct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(direct)


def record(payload, name="input.tar.gz"):
    return {"file": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


class Response(io.BytesIO):
    def __init__(self, payload, status=200, headers=None):
        super().__init__(payload)
        self.status = status
        self.headers = headers or {}

    def geturl(self):
        return "https://example.invalid/artifact"


def test_complete_download_sha_and_stat_cache(tmp_path, monkeypatch):
    payload = b"complete artifact"
    output = tmp_path / "artifact"
    direct.download("https://example.invalid/a", output, record(payload),
                    opener=lambda *a, **k: Response(payload))
    assert output.read_bytes() == payload
    monkeypatch.setattr(direct, "_sha", lambda *a: pytest.fail("cached file was rehashed"))
    direct.download("https://example.invalid/a", output, record(payload),
                    opener=lambda *a, **k: pytest.fail("cached file was downloaded"))


def test_range_resume_preserves_existing_partial(tmp_path):
    output = tmp_path / "artifact"
    output.with_name("artifact.part").write_bytes(b"abcd")
    seen = []

    def opener(request, **kwargs):
        seen.append(request.get_header("Range"))
        return Response(b"efgh", 206, {"Content-Range": "bytes 4-7/8"})

    direct.download("https://example.invalid/a", output, record(b"abcdefgh"), opener=opener)
    assert seen == ["bytes=4-"]
    assert output.read_bytes() == b"abcdefgh"


def test_server_ignoring_range_restarts_only_partial(tmp_path):
    output = tmp_path / "artifact"
    output.with_name("artifact.part").write_bytes(b"abcd")
    direct.download("https://example.invalid/a", output, record(b"abcdefgh"),
                    opener=lambda *a, **k: Response(b"abcdefgh"))
    assert output.read_bytes() == b"abcdefgh"


def test_wrong_range_stops_and_keeps_partial(tmp_path):
    output = tmp_path / "artifact"
    output.with_name("artifact.part").write_bytes(b"abcd")
    with pytest.raises(direct.DownloadError, match="Range"):
        direct.download("https://example.invalid/a", output, record(b"abcdefgh"),
                        opener=lambda *a, **k: Response(b"efgh", 206, {"Content-Range": "bytes 3-6/8"}))
    assert output.with_name("artifact.part").read_bytes() == b"abcd"
    assert not output.exists()


def test_hash_mismatch_not_published_or_automatically_retried(tmp_path):
    output = tmp_path / "artifact"
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        return Response(b"invalid")

    with pytest.raises(direct.DownloadError, match="SHA256"):
        direct.download("https://example.invalid/a", output, record(b"correct"), opener=opener)
    assert calls == [1]
    assert not output.exists()
    assert output.with_name("artifact.part").read_bytes() == b"invalid"


def test_existing_different_final_never_overwritten(tmp_path):
    output = tmp_path / "artifact"
    output.write_bytes(b"old")
    with pytest.raises(direct.DownloadError, match="preserved"):
        direct.download("https://example.invalid/a", output, record(b"new"),
                        opener=lambda *a, **k: pytest.fail("should not download"))
    assert output.read_bytes() == b"old"


def test_three_network_attempts_and_partial_retained(tmp_path):
    output = tmp_path / "artifact"
    output.with_name("artifact.part").write_bytes(b"ab")
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        raise urllib.error.URLError("temporary failure")

    with pytest.raises(direct.DownloadError, match="three attempts"):
        direct.download("https://example.invalid/a", output, record(b"abcd"),
                        opener=opener, sleep=lambda *args: None)
    assert len(calls) == 3
    assert output.with_name("artifact.part").read_bytes() == b"ab"


def test_download_incomplete_response_resumes_next_attempt(tmp_path):
    output = tmp_path / "artifact"
    ranges = []

    def opener(request, **kwargs):
        ranges.append(request.get_header("Range"))
        if len(ranges) == 1:
            return Response(b"ab")
        return Response(b"cd", 206, {"Content-Range": "bytes 2-3/4"})

    direct.download("https://example.invalid/a", output, record(b"abcd"),
                    opener=opener, sleep=lambda *args: None)
    assert ranges == [None, "bytes=2-"]
    assert output.read_bytes() == b"abcd"


def test_full_parts_manifest_prepares_original_archive(tmp_path, monkeypatch):
    code = record(b"code", "code.tar.gz")
    installer = record(b"installer", "install.sh")
    monkeypatch.setattr(direct, "ARTIFACTS", (code, installer))
    payload = b"abcdefgh"
    parts = [record(b"abcd", "inputs/part0"), record(b"efgh", "inputs/part1")]
    manifest = {"schema_version": 1, "input": record(payload) | {"parts": parts}}
    bodies = {"code.tar.gz": b"code", "install.sh": b"installer", "manifest.json": json.dumps(manifest).encode(),
              "part0": b"abcd", "part1": b"efgh"}

    def opener(request, **kwargs):
        return Response(bodies[request.full_url.rsplit("/", 1)[-1]])

    path = direct.prepare(tmp_path, "https://example.invalid/manifest.json", opener=opener)
    assert path.read_bytes() == payload
    # Completed assembled archive skips all part downloads on continuation.
    (tmp_path / "inputs/part0").unlink()
    assert direct.prepare(tmp_path, "https://example.invalid/manifest.json", opener=opener) == path
    assert not (tmp_path / "inputs/part0").exists()


def test_assembled_mismatch_preserves_unpublished_parts(tmp_path):
    parts = [tmp_path / "part0", tmp_path / "part1"]
    parts[0].write_bytes(b"ab")
    parts[1].write_bytes(b"cd")
    output = tmp_path / "final"
    with pytest.raises(direct.DownloadError, match="SHA256"):
        direct.assemble(parts, output, record(b"efgh"))
    assert not output.exists()
    assert all(p.exists() for p in parts)


def test_http_error_does_not_print_private_url(tmp_path):
    url = "https://example.invalid/a?secret=PRIVATE"

    def opener(*args, **kwargs):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    with pytest.raises(direct.DownloadError) as error:
        direct.download(url, tmp_path / "artifact", record(b"body"), opener=opener)
    assert "PRIVATE" not in str(error.value)


def test_http_url_rejected(tmp_path):
    with pytest.raises(direct.DownloadError, match="HTTPS"):
        direct.download("http://example.invalid/a", tmp_path / "artifact", record(b"body"))


def test_storage_fsync_error_stops_without_network_retry(tmp_path, monkeypatch):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        return Response(b"body")

    def fail_fsync(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(direct.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="disk failure"):
        direct.download("https://example.invalid/a", tmp_path / "artifact", record(b"body"), opener=opener)
    assert calls == [1]
    assert not (tmp_path / "artifact").exists()
