#!/usr/bin/env python3
"""Fetch an explicitly pinned NEMAR subset; metadata precedes signal transfer.

The local plan is the default. Downloads require --download. Neither inferred
object URLs, arbitrary redirects, overwrite-on-mismatch nor full archives are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlsplit, urlunsplit

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNED_QUERY_KEYS = {
    "X-Amz-Expires", "response-content-disposition", "X-Amz-Date", "X-Amz-Algorithm",
    "X-Amz-Credential", "X-Amz-SignedHeaders", "X-Amz-Signature", "X-Amz-Security-Token",
}
ROOT_FILES = {"README.md", "dataset_description.json", "participants.json", "participants.tsv"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_prefix(dataset_id: str, version: str) -> str:
    if not re.fullmatch(r"nm\d{6}", dataset_id) or not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        raise ValueError("Dataset and version must identify a pinned NEMAR release")
    return f"https://data.nemar.org/{dataset_id}/{version}/"


def validate_entry(entry: dict, prefix: str) -> dict:
    name = entry.get("path")
    if not isinstance(name, str) or not name:
        raise ValueError("Unsafe manifest path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or str(path) != name or "\\" in name:
        raise ValueError(f"Unsafe manifest path: {name!r}")
    if type(entry.get("size")) is not int or entry["size"] <= 0:
        raise ValueError(f"Invalid declared length: {name}")
    algorithm = entry.get("checksum_algorithm")
    length = {"sha256": 64, "git": 40}.get(algorithm)
    if length is None or not re.fullmatch(rf"[0-9a-f]{{{length}}}", entry.get("checksum", "")):
        raise ValueError(f"Invalid checksum: {name}")
    if entry.get("bytes_url") != prefix + name:
        raise ValueError(f"Unpinned bytes URL: {name}")
    declared_url = entry.get("url", entry["bytes_url"])
    parsed = urlsplit(declared_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"Unsafe declared URL: {name}")
    if declared_url != entry["bytes_url"]:
        dataset_id = urlsplit(prefix).path.split("/")[1]
        expected = (f"https://nemar.s3.us-east-2.amazonaws.com/{dataset_id}/objects/"
                    f"SHA256E-s{entry['size']}--{entry['checksum']}{path.suffix}")
        if algorithm != "sha256" or declared_url != expected:
            raise ValueError(f"Unexpected official object URL: {name}")
    return dict(entry)


def digest_file(path: Path, entry: dict) -> tuple[str, str, int]:
    declared = hashlib.sha256() if entry["checksum_algorithm"] == "sha256" else hashlib.sha1()
    sha256 = hashlib.sha256()
    if entry["checksum_algorithm"] == "git":
        declared.update(f"blob {entry['size']}\0".encode())
    count = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(block)
            declared.update(block)
            sha256.update(block)
    return declared.hexdigest(), sha256.hexdigest(), count


def safe_destination(root: Path, name: str) -> Path:
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Destination escapes data root: {name}")
    if root.is_symlink() or path.is_symlink() or any(
        parent.is_symlink() for parent in path.parents
        if parent != root and parent.is_relative_to(root)
    ):
        raise ValueError(f"Symlink destination is not accepted: {name}")
    return path


def verify_existing(root: Path, entry: dict) -> dict | None:
    path = safe_destination(root, entry["path"])
    if not path.exists():
        return None
    digest, sha256, count = digest_file(path, entry)
    if count != entry["size"] or digest != entry["checksum"]:
        raise ValueError(f"Existing file fails official checksum; refusing overwrite: {entry['path']}")
    return {**entry, "status": "reused_verified", "actual_size": count,
            "actual_sha256": sha256, "actual_checksum": digest, "attempts": [],
            "transferred_bytes": 0, "new_verified_bytes": 0}


def official_response(session, entry: dict):
    response = session.get(entry["bytes_url"], stream=True, timeout=(20, 60),
                           allow_redirects=False)
    if response.status_code in {301, 302, 303, 307, 308}:
        target = response.headers.get("Location", "")
        response.close()
        parsed = urlsplit(target)
        unsigned = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        if (unsigned != entry.get("url") or unsigned == entry["bytes_url"]
                or parsed.fragment or parsed.username or parsed.password
                or not set(parse_qs(parsed.query)).issubset(SIGNED_QUERY_KEYS)):
            raise ValueError(f"Unpinned HTTP redirect: {entry['path']}")
        response = session.get(target, stream=True, timeout=(20, 60), allow_redirects=False)
    return response


def sanitized_error(error: Exception) -> str:
    # HTTP errors may mention ephemeral signed URLs; do not persist query secrets.
    message = re.sub(r"https?://[^\s'\"]+", lambda match: urlunsplit(
        (*urlsplit(match.group())[:3], "", "")), str(error))
    return f"{type(error).__name__}: {message}"


def fetch_entry(root: Path, entry: dict, prefix: str, *, max_attempts: int = 3,
                session_factory=requests.Session, retry_wait=time.sleep) -> dict:
    if max_attempts not in {1, 2, 3}:
        raise ValueError("HTTP attempts must be bounded to 1 through 3")
    entry = validate_entry(entry, prefix)
    existing = verify_existing(root, entry)
    if existing is not None:
        return existing
    path = safe_destination(root, entry["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    if temporary.exists():
        raise ValueError(f"Unaccounted partial file already exists: {entry['path']}")
    attempts = []
    for number in range(1, max_attempts + 1):
        attempt = {"attempt": number, "started_at_utc": utc_now(), "bytes_received": 0}
        try:
            with session_factory() as session:
                with official_response(session, entry) as response:
                    attempt["http_status"] = response.status_code
                    parsed = urlsplit(response.url)
                    attempt["response_url"] = urlunsplit(
                        (parsed.scheme, parsed.netloc, parsed.path, "", ""))
                    attempt["response_query_keys"] = sorted(parse_qs(parsed.query))
                    if response.status_code != 200:
                        raise ValueError(f"HTTP status {response.status_code}")
                    length = response.headers.get("Content-Length")
                    attempt["content_length"] = length
                    if length is not None and int(length) != entry["size"]:
                        raise ValueError("HTTP Content-Length differs from official size")
                    with temporary.open("xb") as stream:
                        for block in response.iter_content(chunk_size=128 * 1024):
                            if not block:
                                continue
                            attempt["bytes_received"] += len(block)
                            if attempt["bytes_received"] > entry["size"]:
                                raise ValueError("Response exceeds official declared size")
                            stream.write(block)
                        stream.flush()
                        os.fsync(stream.fileno())
            digest, sha256, count = digest_file(temporary, entry)
            if count != entry["size"] or digest != entry["checksum"]:
                raise ValueError("Downloaded size or official checksum mismatch")
            if path.exists():
                raise FileExistsError("Destination appeared during download; refusing overwrite")
            temporary.rename(path)
            attempt.update(status="verified", finished_at_utc=utc_now())
            attempts.append(attempt)
            return {**entry, "status": "downloaded_verified", "actual_size": count,
                    "actual_sha256": sha256, "actual_checksum": digest, "attempts": attempts,
                    "transferred_bytes": sum(a["bytes_received"] for a in attempts),
                    "new_verified_bytes": count}
        except (OSError, ValueError, requests.RequestException) as error:
            temporary.unlink(missing_ok=True)
            attempt.update(status="failed", error=sanitized_error(error), finished_at_utc=utc_now())
            attempts.append(attempt)
            if number < max_attempts:
                retry_wait(number)
    return {**entry, "status": "failed", "attempts": attempts,
            "transferred_bytes": sum(a["bytes_received"] for a in attempts), "new_verified_bytes": 0}


def guarded_fetch(root: Path, entry: dict, prefix: str) -> dict:
    try:
        return fetch_entry(root, entry, prefix)
    except (OSError, ValueError) as error:
        return {**entry, "status": "failed", "attempts": [], "local_error": sanitized_error(error),
                "transferred_bytes": 0, "new_verified_bytes": 0}


def load_selection(plan: dict) -> tuple[list[dict], str]:
    prefix = canonical_prefix(plan["nemar_id"], plan["version"])
    path = REPO_ROOT / plan["selection_manifest_path"]
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != plan["selection_manifest_sha256"]:
        raise ValueError("Pinned selection manifest digest changed")
    entries = [validate_entry(entry, prefix) for entry in json.loads(data)]
    if len({entry["path"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate paths in selection manifest")
    if (len(entries) != plan["selected_file_count"]
            or sum(e["size"] for e in entries) != plan["selected_bytes"]
            or not ROOT_FILES.issubset({entry["path"] for entry in entries})):
        raise ValueError("Pinned selection totals or required root metadata changed")
    if plan["license"] != "CC-BY-4.0" or not plan.get("license_verified_sources"):
        raise ValueError("This ingress requires explicitly verified CC-BY-4.0 source licensing")
    return entries, prefix


def write_immutable(path: Path, value) -> None:
    data = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Preserving existing audit artifact: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    entries, prefix = load_selection(plan)
    args.data_root.mkdir(parents=True, exist_ok=True)
    missing = sum(e["size"] for e in entries if not (args.data_root / e["path"]).exists())
    status = {"dataset": plan["dataset_id"], "nemar_id": plan["nemar_id"],
              "version": plan["version"], "license": plan["license"],
              "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
              "selection_manifest_sha256": plan["selection_manifest_sha256"],
              "official_manifest_sha256": plan["official_manifest_sha256"],
              "missing_declared_bytes": missing, "available_disk_bytes": shutil.disk_usage(
                  args.data_root).free, "workers": args.workers, "metadata_only": args.metadata_only,
              "network_requested": args.download}
    print(json.dumps(status), flush=True)
    if not args.download:
        return
    if status["available_disk_bytes"] < missing + 1024**3:
        raise ValueError("Insufficient disk for selected subset plus 1 GiB reserve")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    started = utc_now()
    outcomes = []
    failed = False
    for signals in (False, True):
        if signals and (args.metadata_only or failed):
            break
        batch = [e for e in entries if e["path"].endswith((".edf", ".bdf")) == signals]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for outcome in pool.map(lambda e: guarded_fetch(args.data_root, e, prefix), batch):
                outcomes.append(outcome)
                if signals:
                    print(json.dumps({"path": outcome["path"], "status": outcome["status"]}),
                          flush=True)
        failed = any(outcome["status"] == "failed" for outcome in outcomes)
        if not signals and not failed:
            description = json.loads((args.data_root / "dataset_description.json").read_text())
            if (description.get("License") != plan["license"]
                    or description.get("Version") != plan["version"].removeprefix("v")):
                failed = True
                status["metadata_gate_error"] = "Dataset description license or version changed"
        print(json.dumps({"phase": "signals" if signals else "metadata",
                          "verified_count": sum(o["status"] != "failed" for o in outcomes),
                          "failed_count": sum(o["status"] == "failed" for o in outcomes),
                          "metadata_gate_passed": not failed}), flush=True)
    receipt = {**status, "started_at_utc": started, "finished_at_utc": utc_now(),
               "source_commit": subprocess.check_output(
                   ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "files": outcomes, "complete": not failed and len(outcomes) == len(entries),
               "requested_scope_complete": not failed, "selected_file_count": len(entries),
               "selected_bytes": sum(e["size"] for e in entries),
               "transferred_bytes": sum(o["transferred_bytes"] for o in outcomes),
               "failed_files": [o["path"] for o in outcomes if o["status"] == "failed"]}
    write_immutable(args.output / f"download_receipt_{stamp}.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("complete", "requested_scope_complete",
                                                 "selected_file_count", "failed_files")}), flush=True)
    if failed:
        raise SystemExit("Subset incomplete; metadata gate or file failures retained in receipt")


if __name__ == "__main__":
    main()
