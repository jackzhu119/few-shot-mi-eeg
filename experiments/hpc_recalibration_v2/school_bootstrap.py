"""Local, restartable school entry: trusted CA, pinned code, official endpoints."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import runpy
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request

COMMIT = "e50ef7d9d75a6af731e955d027df90ab79530e2d"
SHA256 = "6ff4d246cba9b2269860ce433d39efea773e07f0f8c3f115d897715b457a96b6"
RELATIVE = "experiments/hpc_recalibration_v2/download_on_hpc.py"
SYSTEM_CA = ("/etc/pki/tls/certs/ca-bundle.crt",
             "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",
             "/etc/ssl/certs/ca-certificates.crt")


def atomic_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def trusted_ca():
    paths = (os.environ.get("SSL_CERT_FILE"),) + SYSTEM_CA
    selected = next((p for p in paths if p and Path(p).is_file()), None)
    if selected:
        os.environ["SSL_CERT_FILE"] = selected
    context = ssl.create_default_context()
    if not context.cert_store_stats()["x509_ca"]:
        raise RuntimeError("No trusted CA loaded; request the school CA bundle")
    return context


def fetch(root, *, opener=None, sleep=time.sleep):
    opener = opener or urllib.request.urlopen
    cached = root / ".paper2-hpc-bootstrap" / ("download_" + SHA256 + ".py")
    if cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == SHA256:
        print("[paper2] verified local downloader: reusing", flush=True)
        return cached
    api = "https://api.github.com/repos/jackzhu119/few-shot-mi-eeg/contents/" + RELATIVE + "?ref=" + COMMIT
    raw = "https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/" + COMMIT + "/" + RELATIVE
    for index, url in enumerate((api, raw, api), 1):
        host = "api.github.com" if index != 2 else "raw.githubusercontent.com"
        print("[paper2] connecting " + host + " attempt " + str(index) + "/3", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper2-hpc-bootstrap",
                                                      "Accept": "application/vnd.github.raw+json"})
            with opener(req, timeout=25) as response:
                data = response.read(256 * 1024)
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLCertVerificationError) as error:
            reason = "TLS certificate verification" if (
                isinstance(error, ssl.SSLCertVerificationError)
                or isinstance(getattr(error, "reason", None), ssl.SSLCertVerificationError)) else type(error).__name__
            print("[paper2] connection failed: " + reason, flush=True)
            if index < 3:
                sleep(index)
            continue
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise RuntimeError("Downloader SHA256 mismatch; code was not executed")
        atomic_file(cached, data)
        return cached
    raise RuntimeError("Both official GitHub routes failed; local entry is saved. Rerun the local command to retry")


def main():
    root = Path(os.environ.get("PAPER2_BOOTSTRAP_ROOT", "/public/home/zhuziyuan"))
    root.mkdir(parents=True, exist_ok=True)
    source = globals().get("BOOTSTRAP_SOURCE")
    if source is not None:
        atomic_file(root / "paper2_start.py", source)
    print("[paper2] local entry: " + str(root / "paper2_start.py"), flush=True)
    token_file = root / ".config" / "paper2-hpc" / "github-token"
    token = globals().pop("BOOTSTRAP_TOKEN", None)
    if token is not None:
        token = token.strip()
        if not token or any(c.isspace() for c in token):
            raise RuntimeError("Invalid supplied GitHub authorization")
        atomic_file(token_file, (token + "\n").encode())
        print("[paper2] GitHub authorization saved locally with mode0600", flush=True)
    if token_file.is_file():
        os.environ["PAPER2_GITHUB_TOKEN_FILE"] = str(token_file)
    trusted_ca()
    cached = fetch(root)
    sys.argv[0] = str(cached)
    runpy.run_path(str(cached), run_name="__main__")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as error:
        print("[paper2] " + str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)
