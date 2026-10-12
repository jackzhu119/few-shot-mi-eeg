"""Bounded public-subset network contract, with in-memory HTTP fixtures."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "nemar_subset", Path(__file__).parents[1] / "scripts/fetch_nemar_subset.py")
download = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download)
PREFIX = download.canonical_prefix("nm000177", "v1.0.5")


def entry(data=b"abc", algorithm="sha256", path="sub-01/a.edf"):
    digest = (hashlib.sha256(data).hexdigest() if algorithm == "sha256"
              else hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest())
    return {"path": path, "size": len(data), "checksum_algorithm": algorithm,
            "checksum": digest, "bytes_url": PREFIX + path, "url": PREFIX + path}


class Response:
    def __init__(self, value, data, status=200, headers=None):
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
        assert kwargs == {"stream": True, "timeout": (20, 60), "allow_redirects": False}
        self.requests.append(url)
        return self.response


@pytest.mark.parametrize("algorithm", ["sha256", "git"])
def test_official_checksum_and_zero_network_verified_resume(tmp_path, algorithm):
    value = entry(algorithm=algorithm)
    session = Session(Response(value, b"abc", headers={"Content-Length": "3"}))
    result = download.fetch_entry(tmp_path, value, PREFIX, session_factory=lambda: session)
    assert result["status"] == "downloaded_verified"
    assert result["actual_sha256"] == hashlib.sha256(b"abc").hexdigest()
    reused = download.fetch_entry(tmp_path, value, PREFIX,
                                  session_factory=lambda: pytest.fail("unexpected network"))
    assert reused["status"] == "reused_verified"
    assert reused["transferred_bytes"] == 0


@pytest.mark.parametrize("path", ["../out.edf", "/out.edf", "a/../out.edf", "a\\out.edf",
                                   "a//out.edf", "", None])
def test_path_traversal_and_noncanonical_names(path):
    value = entry()
    value["path"] = path
    with pytest.raises(ValueError, match="Unsafe manifest path"):
        download.validate_entry(value, PREFIX)


@pytest.mark.parametrize("dataset,version", [("nm000177/escape", "v1.0.5"),
                                             ("nm000177", "latest"),
                                             ("nm000177", "v1.0.5?token=secret")])
def test_explicit_fixed_nemar_identity(dataset, version):
    with pytest.raises(ValueError, match="pinned NEMAR release"):
        download.canonical_prefix(dataset, version)


def test_unexpected_redirect_never_followed(tmp_path):
    value = entry()
    session = Session(Response(value, b"", status=302,
                               headers={"Location": "https://example.org/archive.zip"}))
    result = download.fetch_entry(tmp_path, value, PREFIX, max_attempts=1,
                                  session_factory=lambda: session)
    assert result["status"] == "failed"
    assert "Unpinned HTTP redirect" in result["attempts"][0]["error"]
    assert len(session.requests) == 1


def test_declared_signed_s3_redirect_secret_redacted(tmp_path):
    value = entry()
    value["url"] = ("https://nemar.s3.us-east-2.amazonaws.com/nm000177/objects/"
                    f"SHA256E-s3--{value['checksum']}.edf")
    target = value["url"] + "?X-Amz-Signature=SECRET&X-Amz-Credential=SECRET"
    first = Response(value, b"", status=302, headers={"Location": target})
    last = Response(value, b"abc")
    last.url = target
    session = Session(first)

    def get(url, **kwargs):
        session.requests.append(url)
        return first if len(session.requests) == 1 else last

    session.get = get
    result = download.fetch_entry(tmp_path, value, PREFIX, session_factory=lambda: session)
    assert result["status"] == "downloaded_verified"
    assert "SECRET" not in json.dumps(result)
    assert len(session.requests) == 2


@pytest.mark.parametrize("data,headers,error", [
    (b"abcd", {}, "exceeds"), (b"xyz", {}, "checksum"),
    (b"abc", {"Content-Length": "4"}, "Content-Length"),
])
def test_bounded_retry_size_checksum_and_partial_cleanup(tmp_path, data, headers, error):
    value = entry()
    session = Session(Response(value, data, headers=headers))
    result = download.fetch_entry(tmp_path, value, PREFIX, max_attempts=3,
                                  session_factory=lambda: session, retry_wait=lambda _: None)
    assert result["status"] == "failed"
    assert len(result["attempts"]) == 3
    assert error in result["attempts"][0]["error"]
    assert not (tmp_path / value["path"]).exists()
    assert not list(tmp_path.rglob("*.part"))


def test_invalid_existing_not_overwritten(tmp_path):
    value = entry()
    path = tmp_path / value["path"]
    path.parent.mkdir()
    path.write_bytes(b"xyz")
    result = download.guarded_fetch(tmp_path, value, PREFIX)
    assert result["status"] == "failed"
    assert "refusing overwrite" in result["local_error"]
    assert path.read_bytes() == b"xyz"


def test_symlink_and_existing_partial_are_refused(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "sub-01").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes|Symlink"):
        download.safe_destination(root, "sub-01/a.edf")
    value = entry(path="a.edf")
    (root / "a.edf.part").write_bytes(b"x")
    with pytest.raises(ValueError, match="Unaccounted partial"):
        download.fetch_entry(root, value, PREFIX)


def test_pinned_selection_counts_and_digest():
    path = Path(__file__).parents[1] / (
        "research_logs/public_data_expansion_20261010/kumar2024_ingestion_plan.json")
    plan = json.loads(path.read_text())
    values, prefix = download.load_selection(plan)
    assert prefix == PREFIX
    assert len(values) == 2705
    assert sum(value["path"].endswith(".edf") for value in values) == 360
    bad_plan = {**plan, "selection_manifest_sha256": "0" * 64}
    with pytest.raises(ValueError, match="digest changed"):
        download.load_selection(bad_plan)


def test_signed_query_redacted_from_failed_error():
    value = download.sanitized_error(ValueError("URL https://example.org/object?token=SECRET"))
    assert "SECRET" not in value
    assert "https://example.org/object" in value


def test_receipts_append_instead_of_mutate(tmp_path):
    path = tmp_path / "receipt.json"
    download.write_immutable(path, {"complete": True})
    download.write_immutable(path, {"complete": True})
    with pytest.raises(FileExistsError, match="Preserving"):
        download.write_immutable(path, {"complete": False})
