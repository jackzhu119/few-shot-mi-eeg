#!/usr/bin/env python3
"""Download pinned public artifacts directly on login1, then run the installer.

Standard library only. HTTP retries apply to downloads, never to training.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


RAW = "https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/"
DATA_COMMIT = "b971e79dbf5bf8a1452634046b6e186fe298b6a9"
CODE_COMMIT = "cddb6aa2b73a169e5386ff981d93fd6f6bf43f28"
RELEASE = "releases/paper2-hpc-v2-20261023/"
MANIFEST_URL = RAW + DATA_COMMIT + "/" + RELEASE + "input_download_manifest.json"
ARTIFACTS = (
    {"file": "paper2-hpc-v2-code.tar.gz", "bytes": 86282,
     "sha256": "dd6fa2f293943d8b574655bc6f74c5b5d73b6559f5853d709515240c19fdc8ce"},
    {"file": "install_offline.sh", "bytes": 2049,
     "sha256": "3476346c1c71c92b91517aafdb08803a06a85b09de06f7c9562f6012f4fac508"},
)


class DownloadError(RuntimeError):
    pass


def _https(url):
    if urllib.parse.urlsplit(url).scheme != "https":
        raise DownloadError("Only verified HTTPS download URLs are accepted")
    return url


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp(path):
    stat = Path(path).stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "inode": stat.st_ino, "device": stat.st_dev}


def _atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _receipt(path):
    return path.with_name("." + path.name + ".download.json")


def verified_existing(path, spec):
    """Stat-only reuse after a successful original SHA check."""
    if not path.exists():
        return False
    expected = {"bytes": int(spec["bytes"]), "sha256": spec["sha256"]}
    receipt = _receipt(path)
    if receipt.is_file():
        try:
            old = json.loads(receipt.read_text())
            if old.get("expected") == expected and old.get("stat") == _stamp(path):
                return True
        except (OSError, ValueError):
            pass
    if path.stat().st_size != expected["bytes"] or _sha(path) != expected["sha256"]:
        raise DownloadError("Existing file differs; preserved without overwrite: " + path.name)
    _atomic_json(receipt, {"expected": expected, "stat": _stamp(path)})
    return True


def _publish(partial, destination, spec):
    if partial.stat().st_size != int(spec["bytes"]) or _sha(partial) != spec["sha256"]:
        raise DownloadError("Length/SHA256 mismatch; partial retained: " + destination.name)
    os.replace(partial, destination)
    _atomic_json(_receipt(destination), {
        "expected": {"bytes": int(spec["bytes"]), "sha256": spec["sha256"]},
        "stat": _stamp(destination)})


def download(url, destination, spec, *, opener=None, sleep=time.sleep):
    """Three bounded network attempts; retain resumable .part and old finals."""
    opener = opener or urllib.request.urlopen
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if verified_existing(destination, spec):
        print(json.dumps({"file": destination.name, "status": "already_verified"}), flush=True)
        return
    _https(url)
    partial = destination.with_name(destination.name + ".part")
    expected = int(spec["bytes"])
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > expected:
            raise DownloadError("Oversized partial retained: " + destination.name)
        if offset == expected:
            _publish(partial, destination, spec)
            return
        headers = {"User-Agent": "paper2-hpc-direct-download", "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = "bytes=" + str(offset) + "-"
        try:
            request = urllib.request.Request(url, headers=headers)
            with opener(request, timeout=60) as response:
                _https(response.geturl())
                status = response.status
                if status not in (200, 206):
                    raise DownloadError("Unexpected download HTTP status: " + str(status))
                if status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    try:
                        unit, interval = content_range.split(" ", 1)
                        span, total = interval.split("/")
                        start, end = (int(s) for s in span.split("-"))
                        valid = unit == "bytes" and start == offset and int(total) == expected and start <= end < expected
                    except ValueError:
                        valid = False
                    if not valid:
                        raise DownloadError("Incorrect HTTP Range response; partial retained")
                else:
                    # A server that ignores Range returned the full object.
                    offset = 0
                mode = "ab" if offset else "wb"
                processed = offset
                next_report = processed + 8 * 1024 * 1024
                print(json.dumps({"file": destination.name, "status": "downloading",
                                  "resumed_bytes": offset, "attempt": attempt + 1}), flush=True)
                with partial.open(mode) as stream:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        if processed + len(block) > expected:
                            raise DownloadError("Download exceeds declared bytes; partial retained")
                        stream.write(block)
                        processed += len(block)
                        if processed >= next_report:
                            print(json.dumps({"file": destination.name, "bytes": processed,
                                              "total_bytes": expected}), flush=True)
                            next_report = processed + 8 * 1024 * 1024
                    stream.flush()
                    os.fsync(stream.fileno())
                if processed < expected:
                    raise ConnectionError("Incomplete response")
            _publish(partial, destination, spec)
            print(json.dumps({"file": destination.name, "status": "sha256_verified",
                              "bytes": expected}), flush=True)
            return
        except urllib.error.HTTPError as error:
            if error.code not in (408, 429, 500, 502, 503, 504):
                raise DownloadError("Download HTTP " + str(error.code) + "; no file overwritten") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        if attempt < 2:
            sleep(2 ** attempt)
    raise DownloadError("Network download failed after three attempts; rerun the same command to resume")


def read_manifest(url, *, opener=None):
    opener = opener or urllib.request.urlopen
    _https(url)
    for attempt in range(3):
        try:
            with opener(urllib.request.Request(url), timeout=60) as response:
                _https(response.geturl())
                value = json.loads(response.read(1024 * 1024))
            if value.get("schema_version") != 1 or not value.get("input", {}).get("parts"):
                raise DownloadError("Unrecognized input download manifest")
            return value
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise DownloadError("Could not download input manifest; rerun the same command") from None
            time.sleep(2 ** attempt)


def assemble(parts, destination, spec):
    if verified_existing(destination, spec):
        return
    partial = destination.with_name(destination.name + ".assembling")
    with partial.open("wb") as outgoing:
        for source in parts:
            with source.open("rb") as incoming:
                shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    _publish(partial, destination, spec)
    print(json.dumps({"file": destination.name, "status": "assembled_sha256_verified",
                      "bytes": int(spec["bytes"])}), flush=True)


def prepare(incoming, manifest_url=MANIFEST_URL, *, opener=None):
    incoming = Path(incoming)
    incoming.mkdir(parents=True, exist_ok=True)
    for spec in ARTIFACTS:
        download(RAW + CODE_COMMIT + "/" + RELEASE + spec["file"],
                 incoming / spec["file"], spec, opener=opener)
    manifest = read_manifest(manifest_url, opener=opener)
    spec = manifest["input"]
    if Path(spec["file"]).name != spec["file"]:
        raise DownloadError("Invalid input archive filename")
    final = incoming / spec["file"]
    if verified_existing(final, spec):
        return final
    parts = []
    for part in spec["parts"]:
        relative = PurePosixPath(part["file"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in part["file"]:
            raise DownloadError("Invalid part filename")
        path = incoming / relative
        download(urllib.parse.urljoin(manifest_url, part["file"]), path, part, opener=opener)
        parts.append(path)
    assemble(parts, final, spec)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incoming", default="/public/home/zhuziyuan/incoming")
    parser.add_argument("--project-dir", default="/public/home/zhuziyuan/projects/paper2-recalibration-v2")
    parser.add_argument("--manifest-url", default=MANIFEST_URL)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    incoming = Path(args.incoming).expanduser().resolve()
    incoming.mkdir(parents=True, exist_ok=True)
    with (incoming / ".paper2-direct-download.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        prepare(incoming, args.manifest_url)
    if not args.download_only:
        env = os.environ.copy()
        env.update(HPC_V2_INCOMING=str(incoming), HPC_V2_PROJECT_DIR=args.project_dir,
                   HPC_V2_PYTHON=sys.executable)
        command = ["bash", str(incoming / "install_offline.sh")]
        if args.no_launch:
            command.append("--no-launch")
        return subprocess.call(command, env=env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DownloadError as error:
        print(str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)
