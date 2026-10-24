import hashlib
import importlib.util
import io
import json
from pathlib import Path
import ssl
import urllib.error
import urllib.parse

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
        return Response(bodies[urllib.parse.urlsplit(request.full_url).path.rsplit("/", 1)[-1]])

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


def test_completed_default_inputs_can_resume_without_network(tmp_path, monkeypatch):
    payload = b"prepared input bytes"
    manifest = {"schema_version": 1, "input": record(payload) | {
        "parts": [record(payload, "inputs/part0")]}}
    monkeypatch.setattr(direct, "ARTIFACTS", ())
    monkeypatch.setattr(direct, "MANIFEST_URL", "https://example.invalid/manifest.json")
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    monkeypatch.setattr(direct, "MANIFEST_CONTENT_SHA256", digest)

    def opener(request, **kwargs):
        return Response(json.dumps(manifest).encode() if request.full_url.endswith("manifest.json") else payload)

    path = direct.prepare(tmp_path, direct.MANIFEST_URL, opener=opener)
    assert path.read_bytes() == payload
    assert direct.prepare(tmp_path, direct.MANIFEST_URL,
                          opener=lambda *a, **k: pytest.fail("completed inputs contacted the network")) == path


PINNED = direct.RAW + direct.DATA_COMMIT + "/directory/artifact"


def test_official_api_candidate_preserves_pinned_git_ref():
    api, raw = direct.to_official_candidates(PINNED)
    parsed = urllib.parse.urlsplit(api)
    assert parsed.hostname == "api.github.com"
    assert parsed.path == "/repos/jackzhu119/few-shot-mi-eeg/contents/directory/artifact"
    assert urllib.parse.parse_qs(parsed.query) == {"ref": [direct.DATA_COMMIT]}
    assert raw == PINNED


def test_api_raw_media_headers_and_connecting_log_precede_request(tmp_path, capsys):
    def opener(request, **kwargs):
        assert '"status": "connecting"' in capsys.readouterr().out
        assert urllib.parse.urlsplit(request.full_url).hostname == "api.github.com"
        assert request.get_header("Accept") == "application/vnd.github.raw+json"
        assert request.get_header("User-agent") == "paper2-hpc-direct-download"
        assert kwargs["timeout"] == 30
        return Response(b"body")

    direct.download(PINNED, tmp_path / "artifact", record(b"body"), opener=opener)


def test_timeout_rotates_api_raw_api_with_three_attempts(tmp_path):
    hosts = []

    def opener(request, **kwargs):
        hosts.append(urllib.parse.urlsplit(request.full_url).hostname)
        raise TimeoutError("read timed out")

    with pytest.raises(direct.DownloadError, match="three attempts"):
        direct.download(PINNED, tmp_path / "artifact", record(b"body"),
                        opener=opener, sleep=lambda *args: None)
    assert hosts == ["api.github.com", "raw.githubusercontent.com", "api.github.com"]


def test_read_timeout_keeps_bytes_and_raw_resumes_them(tmp_path):
    calls = []

    class Interrupted(Response):
        def read(self, size=-1):
            if self.tell():
                raise TimeoutError("body read timed out")
            return super().read(2)

    def opener(request, **kwargs):
        calls.append(request)
        if len(calls) == 1:
            return Interrupted(b"ab")
        assert urllib.parse.urlsplit(request.full_url).hostname == "raw.githubusercontent.com"
        assert request.get_header("Range") == "bytes=2-"
        return Response(b"cd", 206, {"Content-Range": "bytes 2-3/4"})

    output = tmp_path / "artifact"
    direct.download(PINNED, output, record(b"abcd"), opener=opener, sleep=lambda *args: None)
    assert output.read_bytes() == b"abcd"
    assert len(calls) == 2


def test_existing_partial_tries_range_host_then_api_200_safely_restarts(tmp_path):
    output = tmp_path / "artifact"
    output.with_name("artifact.part").write_bytes(b"ab")
    hosts = []

    def opener(request, **kwargs):
        hosts.append(urllib.parse.urlsplit(request.full_url).hostname)
        if len(hosts) == 1:
            assert request.get_header("Range") == "bytes=2-"
            raise TimeoutError("raw unavailable")
        return Response(b"abcd", 200)

    direct.download(PINNED, output, record(b"abcd"), opener=opener, sleep=lambda *args: None)
    assert hosts == ["raw.githubusercontent.com", "api.github.com"]
    assert output.read_bytes() == b"abcd"


@pytest.mark.parametrize("status", [401, 403, 429, 502])
def test_api_http_limit_or_unavailable_switches_to_raw(tmp_path, status):
    calls = []

    def opener(request, **kwargs):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, status, "unavailable", {}, None)
        return Response(b"body")

    direct.download(PINNED, tmp_path / "artifact", record(b"body"),
                    opener=opener, sleep=lambda *args: None)
    assert len(calls) == 2
    assert urllib.parse.urlsplit(calls[1]).hostname == "raw.githubusercontent.com"


@pytest.mark.parametrize("wrapped", [False, True])
def test_tls_certificate_failure_is_distinct_and_not_retried(tmp_path, wrapped):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        error = ssl.SSLCertVerificationError(1, "certificate verify failed")
        raise urllib.error.URLError(error) if wrapped else error

    with pytest.raises(direct.DownloadError, match="TLS certificate verification"):
        direct.download(PINNED, tmp_path / "artifact", record(b"body"),
                        opener=opener, sleep=lambda *args: pytest.fail("TLS must not retry"))
    assert calls == [1]


def test_fixed_source_404_stops_without_file_replacement(tmp_path):
    calls = []

    def opener(request, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)

    with pytest.raises(direct.DownloadError, match="HTTP 404"):
        direct.download(PINNED, tmp_path / "artifact", record(b"body"), opener=opener)
    assert calls == [1]


def test_storage_timeout_error_is_not_a_network_retry(tmp_path, monkeypatch):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        return Response(b"body")

    def fail_fsync(*args):
        raise TimeoutError("NFS write timeout")

    monkeypatch.setattr(direct.os, "fsync", fail_fsync)
    with pytest.raises(TimeoutError, match="NFS write"):
        direct.download(PINNED, tmp_path / "artifact", record(b"body"), opener=opener)
    assert calls == [1]


def test_manifest_timeout_fallback_does_not_lose_part_git_refs(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "ARTIFACTS", ())
    part = record(b"body", "inputs/part0")
    manifest = {"schema_version": 1, "input": record(b"body") | {"parts": [part]}}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    monkeypatch.setattr(direct, "MANIFEST_CONTENT_SHA256", digest)
    seen = []

    def opener(request, **kwargs):
        seen.append(request.full_url)
        parsed = urllib.parse.urlsplit(request.full_url)
        if len(seen) == 1:
            raise TimeoutError("api unavailable")
        if parsed.path.endswith("input_download_manifest.json"):
            return Response(json.dumps(manifest).encode())
        assert parsed.hostname == "api.github.com"
        assert parsed.path.endswith("/inputs/part0")
        assert urllib.parse.parse_qs(parsed.query) == {"ref": [direct.DATA_COMMIT]}
        return Response(b"body")

    monkeypatch.setattr(direct.time, "sleep", lambda *args: None)
    assert direct.prepare(tmp_path, opener=opener).read_bytes() == b"body"
    assert urllib.parse.urlsplit(seen[1]).hostname == "raw.githubusercontent.com"


def test_configured_timeout_applies_to_network_open(tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER2_DOWNLOAD_TIMEOUT_SECONDS", "45")

    def opener(request, **kwargs):
        assert kwargs["timeout"] == 45
        return Response(b"body")

    direct.download(PINNED, tmp_path / "artifact", record(b"body"), opener=opener)
