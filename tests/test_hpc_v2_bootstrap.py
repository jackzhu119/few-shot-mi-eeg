import hashlib
import importlib.util
import io
from pathlib import Path
import urllib.error

import pytest

PATH = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2/school_bootstrap.py"
spec = importlib.util.spec_from_file_location("school_bootstrap", PATH)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.fixture
def payload(monkeypatch):
    data = b"print('synthetic software validation only')\n"
    monkeypatch.setattr(bootstrap, "COMMIT", "a" * 40)
    monkeypatch.setattr(bootstrap, "SHA256", hashlib.sha256(data).hexdigest())
    return data


def test_timeout_falls_back_and_announces_before_request(tmp_path, payload, capsys):
    calls = []

    def opener(request, **kwargs):
        assert "connecting" in capsys.readouterr().out
        calls.append(request.full_url)
        assert kwargs["timeout"] == 25
        assert request.get_header("Accept") == "application/vnd.github.raw+json"
        if len(calls) == 1:
            raise TimeoutError("simulated waiting for HTTP headers")
        return io.BytesIO(payload)

    path = bootstrap.fetch(tmp_path, opener=opener, sleep=lambda _: None)
    assert path.read_bytes() == payload
    assert calls[0].startswith("https://api.github.com/")
    assert calls[0].endswith("?ref=" + "a" * 40)
    assert calls[1].startswith("https://raw.githubusercontent.com/")


def test_cached_verified_downloader_needs_no_network(tmp_path, payload, monkeypatch):
    cached = bootstrap.fetch(tmp_path, opener=lambda *a, **k: io.BytesIO(payload))
    result = bootstrap.fetch(tmp_path, opener=lambda *a, **k: pytest.fail("network called for cache"))
    assert result == cached


def test_wrong_download_hash_stops_before_execution_or_retry(tmp_path, payload):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(b"different code")

    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        bootstrap.fetch(tmp_path, opener=opener, sleep=lambda _: None)
    assert calls == [1]
    assert not (tmp_path / ".paper2-hpc-bootstrap").exists()


def test_exactly_three_attempts_when_both_routes_fail(tmp_path, payload):
    hosts = []

    def opener(request, **kwargs):
        hosts.append(request.full_url.split("/")[2])
        raise urllib.error.URLError("simulated network outage")

    with pytest.raises(RuntimeError, match="Both official"):
        bootstrap.fetch(tmp_path, opener=opener, sleep=lambda _: None)
    assert hosts == ["api.github.com", "raw.githubusercontent.com", "api.github.com"]


def test_local_entry_saved_even_when_first_remote_request_fails(tmp_path, payload, monkeypatch):
    monkeypatch.setenv("PAPER2_BOOTSTRAP_ROOT", str(tmp_path))
    monkeypatch.setattr(bootstrap, "BOOTSTRAP_SOURCE", b"# local starter\n", raising=False)
    monkeypatch.setattr(bootstrap, "trusted_ca", lambda: None)
    monkeypatch.setattr(bootstrap, "fetch", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(RuntimeError, match="offline"):
        bootstrap.main()
    assert (tmp_path / "paper2_start.py").read_bytes() == b"# local starter\n"


def test_storage_failure_is_not_retried_as_a_network_problem(tmp_path, payload, monkeypatch):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(payload)

    def fail(*args):
        raise OSError("simulated fsync failure")

    monkeypatch.setattr(bootstrap.os, "fsync", fail)
    with pytest.raises(OSError, match="fsync failure"):
        bootstrap.fetch(tmp_path, opener=opener)
    assert calls == [1]


def test_private_authorization_is_separate_from_saved_source(tmp_path, payload, monkeypatch):
    monkeypatch.setenv("PAPER2_BOOTSTRAP_ROOT", str(tmp_path))
    monkeypatch.setenv("PAPER2_GITHUB_TOKEN_FILE", "")
    source = b"# public bootstrap without credential\n"
    monkeypatch.setattr(bootstrap, "BOOTSTRAP_SOURCE", source, raising=False)
    vars(bootstrap)["BOOTSTRAP_TOKEN"] = "synthetic-test-authorization"
    monkeypatch.setattr(bootstrap, "trusted_ca", lambda: None)
    monkeypatch.setattr(bootstrap, "fetch", lambda *a, **k: tmp_path / "fake.py")
    monkeypatch.setattr(bootstrap.runpy, "run_path", lambda *a, **k: None)
    bootstrap.main()
    token_file = tmp_path / ".config/paper2-hpc/github-token"
    assert token_file.read_text() == "synthetic-test-authorization\n"
    assert token_file.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "paper2_start.py").read_bytes() == source
    assert "synthetic-test-authorization" not in (tmp_path / "paper2_start.py").read_text()
    assert bootstrap.os.environ["PAPER2_GITHUB_TOKEN_FILE"] == str(token_file)
    assert "BOOTSTRAP_TOKEN" not in vars(bootstrap)


def test_ca_selection_preserves_existing_environment(monkeypatch, tmp_path):
    ca = tmp_path / "system-ca.pem"
    ca.write_text("mock public CA")
    monkeypatch.setenv("SSL_CERT_FILE", str(ca))
    class Context:
        def cert_store_stats(self):
            return {"x509_ca": 1}
    monkeypatch.setattr(bootstrap.ssl, "create_default_context", lambda: Context())
    bootstrap.trusted_ca()
    assert bootstrap.os.environ["SSL_CERT_FILE"] == str(ca)


def test_empty_ca_store_fails_without_disabling_tls(monkeypatch):
    class Context:
        def cert_store_stats(self):
            return {"x509_ca": 0}
    monkeypatch.setattr(bootstrap.ssl, "create_default_context", lambda: Context())
    with pytest.raises(RuntimeError, match="No trusted CA"):
        bootstrap.trusted_ca()
