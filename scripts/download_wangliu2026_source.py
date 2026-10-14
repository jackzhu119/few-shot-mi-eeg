#!/usr/bin/env python3
"""Acquire fixed official Wang/Liu v11 raw archive with a strict transport gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_URL = "https://ndownloader.figshare.com/files/64877880"
EXPECTED_BYTES = 5_175_273_351
EXPECTED_MD5 = "74dabab47f477e5bc0510b1e2e705c5a"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def file_hashes(path: Path) -> tuple[int, str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            count += len(block)
            md5.update(block)
            sha.update(block)
    return count, md5.hexdigest(), sha.hexdigest()


def enforce_transport(count: int, md5: str) -> None:
    if count != EXPECTED_BYTES or md5 != EXPECTED_MD5:
        raise ValueError("Official archive size/MD5 mismatch")


def download(destination: Path, receipt_path: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    record = {"source_url": SOURCE_URL, "figshare_article_id": 30509165,
              "version": 11, "file_id": 64877880, "license": "CC BY 4.0",
              "expected_bytes": EXPECTED_BYTES, "official_md5": EXPECTED_MD5,
              "started_at_utc": utc_now(), "status": "started",
              "redirect_urls_recorded": False}
    if destination.exists():
        count, md5, sha = file_hashes(destination)
        enforce_transport(count, md5)
        record.update(status="existing_official_transport_verified", bytes=count,
                      md5=md5, sha256=sha, finished_at_utc=utc_now())
        write_json(receipt_path, record)
        return record
    partial = destination.with_suffix(destination.suffix + ".partial")
    if partial.exists():
        raise ValueError("Unverified partial exists; it is not silently reused")
    if shutil.disk_usage(destination.parent).free < EXPECTED_BYTES + 256 * 1024 * 1024:
        raise ValueError("Insufficient bounded disk budget for raw archive + scratch")
    write_json(receipt_path, record)
    md5 = hashlib.md5(usedforsecurity=False)
    sha = hashlib.sha256()
    count = 0
    last_report = 0.0
    try:
        with requests.get(SOURCE_URL, stream=True, timeout=(30, 180)) as response:
            if response.status_code != 200:
                raise ValueError("Official full archive GET did not return HTTP 200")
            record["http_status"] = response.status_code
            with partial.open("xb") as stream:
                for block in response.iter_content(chunk_size=8 * 1024 * 1024):
                    if not block:
                        continue
                    count += len(block)
                    if count > EXPECTED_BYTES:
                        raise ValueError("Archive exceeds official byte count")
                    stream.write(block)
                    md5.update(block)
                    sha.update(block)
                    if time.monotonic() - last_report >= 15:
                        record.update(status="downloading", bytes=count)
                        write_json(receipt_path, record)
                        print(json.dumps({"status": "downloading", "bytes": count,
                                          "expected_bytes": EXPECTED_BYTES}), flush=True)
                        last_report = time.monotonic()
        enforce_transport(count, md5.hexdigest())
        os.replace(partial, destination)
        record.update(status="official_transport_verified", bytes=count,
                      md5=md5.hexdigest(), sha256=sha.hexdigest(),
                      finished_at_utc=utc_now())
        write_json(receipt_path, record)
        print(json.dumps({"status": record["status"], "bytes": count,
                          "sha256": sha.hexdigest()}), flush=True)
        return record
    except Exception as error:
        record.update(status="failed", bytes=count, error_type=type(error).__name__,
                      finished_at_utc=utc_now())
        write_json(receipt_path, record)
        # Requests exception strings may contain signed redirects: do not log them.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__,
                          "bytes": count}), flush=True)
        raise RuntimeError("Official transport acquisition failed; inspect safe receipt") from None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    download(args.destination, args.receipt)


if __name__ == "__main__":
    main()
