"""Bounded HTTP and provenance safeguards; no real network or EEG fixture."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "netbci_download", Path(__file__).parents[1] / "scripts/fetch_netbci_cohort.py")
download = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download)


def entry(data=b"abc", algorithm="sha256", path="sub-2/a.edf"):
    digest = (hashlib.sha256(data).hexdigest() if algorithm == "sha256"
              else hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest())
    url = download.OFFICIAL_PREFIX + path
    return {"path": path, "size": len(data), "checksum_algorithm": algorithm,
            "checksum": digest, "bytes_url": url, "url": url}


class Response:
    def __init__(self, value, data, *, status=200, headers=None):
        self.status_code = status
        self.headers = {} if headers is None else headers
        self.url = value["bytes_url"]
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    def iter_content(self, chunk_size):
        yield self.data


class Session:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url, **kwargs):
        assert kwargs["stream"] is True
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (20, 60)
        assert "verify" not in kwargs  # requests default TLS validation remains enabled
        self.requests.append(url)
        return self.response


@pytest.mark.parametrize("algorithm", ["sha256", "git"])
def test_download_verifies_and_reuses_without_network(tmp_path, algorithm):
    value = entry(algorithm=algorithm)
    session = Session(Response(value, b"abc", headers={"Content-Length": "3"}))
    result = download.fetch_entry(tmp_path, value, session_factory=lambda: session)
    assert result["status"] == "downloaded_verified"
    assert result["new_verified_bytes"] == 3
    assert result["actual_sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert (tmp_path / value["path"]).read_bytes() == b"abc"
    assert not list(tmp_path.rglob("*.part"))
    reused = download.fetch_entry(tmp_path, value, session_factory=lambda: pytest.fail("network"))
    assert reused["status"] == "reused_verified"
    assert reused["transferred_bytes"] == 0


@pytest.mark.parametrize("badpath", ["../escape.edf", "/absolute.edf", "a/../b.edf",
                                        "a\\b.edf", "a//b.edf"])
def test_rejects_unsafe_relative_paths(badpath):
    with pytest.raises(ValueError, match="Unsafe manifest path"):
        download.validate_entry(entry(path=badpath))


def test_rejects_unpinned_host_and_redirect(tmp_path):
    value = entry()
    value["bytes_url"] = "https://example.org/sub-2/a.edf"
    with pytest.raises(ValueError, match="Unpinned bytes URL"):
        download.validate_entry(value)
    value = entry()
    session = Session(Response(value, b"", status=302,
                               headers={"Location": "https://example.org/archive.zip"}))
    result = download.fetch_entry(tmp_path, value, max_attempts=1,
                                  session_factory=lambda: session)
    assert result["status"] == "failed"
    assert "Unpinned HTTP redirect" in result["attempts"][0]["error"]
    assert len(session.requests) == 1


def test_accepts_only_signed_declared_object_without_recording_tokens(tmp_path):
    value = entry()
    value["url"] = ("https://nemar.s3.us-east-2.amazonaws.com/nm000305/objects/"
                    f"SHA256E-s3--{value['checksum']}.edf")
    target = value["url"] + "?X-Amz-Signature=SECRET&X-Amz-Credential=SECRET"
    first = Response(value, b"", status=302, headers={"Location": target})
    final = Response(value, b"abc")
    final.url = target
    session = Session(first)

    def get(url, **kwargs):
        session.requests.append(url)
        return first if len(session.requests) == 1 else final

    session.get = get
    result = download.fetch_entry(tmp_path, value, session_factory=lambda: session)
    assert result["status"] == "downloaded_verified"
    assert result["attempts"][0]["response_url"] == value["url"]
    assert "SECRET" not in str(result)


@pytest.mark.parametrize("data,message", [(b"abcd", "exceeds"), (b"xyz", "checksum")])
def test_rejects_oversized_or_corrupt_body_and_removes_partial(tmp_path, data, message):
    value = entry()
    session = Session(Response(value, data))
    result = download.fetch_entry(tmp_path, value, max_attempts=3,
                                  session_factory=lambda: session, retry_wait=lambda _: None)
    assert result["status"] == "failed"
    assert len(result["attempts"]) == 3
    assert message in result["attempts"][0]["error"]
    assert result["transferred_bytes"] == 3 * len(data)
    assert not (tmp_path / value["path"]).exists()
    assert not list(tmp_path.rglob("*.part"))


def test_refuses_overwriting_invalid_existing_file(tmp_path):
    value = entry()
    path = tmp_path / value["path"]
    path.parent.mkdir()
    path.write_bytes(b"xyz")
    with pytest.raises(ValueError, match="refusing overwrite"):
        download.fetch_entry(tmp_path, value, session_factory=lambda: pytest.fail("network"))
    assert path.read_bytes() == b"xyz"
    assert download.guarded_fetch(tmp_path, value)["status"] == "failed"


def test_refuses_symlink_destination(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "sub-2").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes|Symlink"):
        download.safe_destination(root, "sub-2/a.edf")


def test_checksum_pinned_manifest_and_upstream_header_url():
    path = Path(__file__).parents[1] / "research_logs/netbci2026_sources/manifest.json"
    entries = download.load_manifest(path)
    headers = [value for value in entries if value["path"].endswith(".vhdr")]
    assert len(headers) == 456
    assert all(value["checksum_algorithm"] == "sha256" for value in headers)


def test_receipts_preserve_existing_artifacts(tmp_path):
    path = tmp_path / "receipt.json"
    download.write_immutable(path, {"verified": True})
    download.write_immutable(path, {"verified": True})
    with pytest.raises(FileExistsError, match="Preserving"):
        download.write_immutable(path, {"verified": False})
