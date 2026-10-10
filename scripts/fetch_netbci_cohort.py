#!/usr/bin/env python3
"""Fetch only pinned NETBCI participant files, with bounded validated HTTP IO.

The default is a local plan. ``--download`` is required for network transfers.
No archive downloads, inferred URLs, credentials, or checksum bypasses are used.
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
MANIFEST_SHA256 = "7e50f5281e91bec97791a84f5f3dbe20dc443b37c10d4bc6bcda96bed08c092c"
OFFICIAL_PREFIX = "https://data.nemar.org/nm000305/v1.0.0/"
ROOT_FILES = (
    "README.md", "dataset_description.json", "participants.json", "participants.tsv",
    "sourcedata/sourcedata_provenance.json",
)
SIGNED_QUERY_KEYS = {
    "X-Amz-Expires", "response-content-disposition", "X-Amz-Date", "X-Amz-Algorithm",
    "X-Amz-Credential", "X-Amz-SignedHeaders", "X-Amz-Signature", "X-Amz-Security-Token",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_entry(entry: dict) -> dict:
    """Require a canonical relative path and its explicitly declared HTTPS URL."""
    name = entry["path"]
    path = PurePosixPath(name)
    if (not isinstance(name, str) or path.is_absolute() or ".." in path.parts
            or str(path) != name or "\\" in name or not name):
        raise ValueError(f"Unsafe manifest path: {name!r}")
    if not isinstance(entry["size"], int) or entry["size"] <= 0:
        raise ValueError(f"Invalid declared length: {name}")
    algorithm = entry["checksum_algorithm"]
    length = {"sha256": 64, "git": 40}.get(algorithm)
    if length is None or not re.fullmatch(rf"[0-9a-f]{{{length}}}", entry["checksum"]):
        raise ValueError(f"Invalid checksum: {name}")
    if entry["bytes_url"] != OFFICIAL_PREFIX + name:
        raise ValueError(f"Unpinned bytes URL: {name}")
    declared_url = entry.get("url", entry["bytes_url"])
    parsed = urlsplit(declared_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"Unsafe declared URL: {name}")
    if declared_url != entry["bytes_url"]:
        suffix = PurePosixPath(name).suffix
        expected_s3 = (
            "https://nemar.s3.us-east-2.amazonaws.com/nm000305/objects/"
            f"SHA256E-s{entry['size']}--{entry['checksum']}{suffix}"
        )
        if algorithm != "sha256" or suffix not in {".edf", ".vhdr"} or declared_url != expected_s3:
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
    resolved_root = root.resolve()
    if path.resolve().is_relative_to(resolved_root) is False:
        raise ValueError(f"Destination escapes data root: {name}")
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents
                                if parent != root and parent.is_relative_to(root)):
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
    """Only follow the object URL already present in the pinned manifest."""
    response = session.get(entry["bytes_url"], stream=True, timeout=(20, 60),
                           allow_redirects=False)
    if response.status_code in {301, 302, 303, 307, 308}:
        target = response.headers.get("Location", "")
        response.close()
        parsed = urlsplit(target)
        unsigned = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        query_keys = set(parse_qs(parsed.query))
        if (unsigned != entry.get("url") or unsigned == entry["bytes_url"]
                or parsed.fragment or parsed.username or parsed.password
                or not query_keys.issubset(SIGNED_QUERY_KEYS)):
            raise ValueError(f"Unpinned HTTP redirect: {entry['path']}")
        response = session.get(target, stream=True, timeout=(20, 60), allow_redirects=False)
    return response


def fetch_entry(root: Path, entry: dict, *, max_attempts: int = 3,
                session_factory=requests.Session, retry_wait=time.sleep) -> dict:
    if max_attempts not in {1, 2, 3}:
        raise ValueError("HTTP attempts must be bounded to 1 through 3")
    entry = validate_entry(entry)
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
                # Inherited proxy, CA trust and TLS verification are retained.
                with official_response(session, entry) as response:
                    attempt["http_status"] = response.status_code
                    parsed = urlsplit(response.url)
                    attempt["response_url"] = urlunsplit(
                        (parsed.scheme, parsed.netloc, parsed.path, "", ""))
                    attempt["response_query_keys"] = sorted(parse_qs(parsed.query))
                    if response.status_code != 200:
                        raise ValueError(f"HTTP status {response.status_code}")
                    content_length = response.headers.get("Content-Length")
                    attempt["content_length"] = content_length
                    if content_length is not None and int(content_length) != entry["size"]:
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
            # requests exception messages can contain ephemeral signed URLs.
            message = re.sub(r"https?://[^\s'\"]+", lambda match: urlunsplit(
                (*urlsplit(match.group())[:3], "", "")), str(error))
            attempt.update(status="failed", error=f"{type(error).__name__}: {message}",
                           finished_at_utc=utc_now())
            attempts.append(attempt)
            if number < max_attempts:
                retry_wait(number)
    return {**entry, "status": "failed", "attempts": attempts,
            "transferred_bytes": sum(a["bytes_received"] for a in attempts),
            "new_verified_bytes": 0}


def guarded_fetch(root: Path, entry: dict) -> dict:
    """Retain local refusal records without losing the participant receipt."""
    try:
        return fetch_entry(root, entry)
    except (OSError, ValueError) as error:
        return {**entry, "status": "failed", "attempts": [],
                "local_error": f"{type(error).__name__}: {error}",
                "transferred_bytes": 0, "new_verified_bytes": 0}


def load_manifest(path: Path) -> list[dict]:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != MANIFEST_SHA256:
        raise ValueError("Official cached v1.0.0 manifest digest changed")
    entries = [validate_entry(entry) for entry in json.loads(data)]
    if len({entry["path"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate paths in official manifest")
    return entries


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
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs/netbci_cohort.json")
    parser.add_argument("--subjects", nargs="+", type=int)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    config = json.loads(args.config.read_text()) if args.config.exists() else {}
    config_sha256 = (hashlib.sha256(args.config.read_bytes()).hexdigest()
                     if args.config.exists() else None)
    approved = config.get("subjects", list(range(1, 11)))
    approved = [int(str(subject).removeprefix("sub-")) for subject in approved]
    if any(subject not in range(1, 11) for subject in approved):
        raise ValueError("This research expansion is bounded to participants 1 through 10")
    subjects = args.subjects or approved
    if len(set(subjects)) != len(subjects) or not set(subjects).issubset(approved):
        raise ValueError("Requested participants differ from the approved cohort")
    manifest_path = REPO_ROOT / "research_logs/netbci2026_sources/manifest.json"
    data_root = REPO_ROOT / "data/netbci2026/nm000305/v1.0.0"
    output = REPO_ROOT / "research_logs/netbci_cohort_20261010/downloads"
    entries = load_manifest(manifest_path)
    root_entries = [entry for entry in entries if entry["path"] in ROOT_FILES]
    roots = [verify_existing(data_root, entry) for entry in root_entries]
    if len(roots) != len(ROOT_FILES) or any(entry is None for entry in roots):
        raise ValueError("All five already-validated dataset root metadata files are required")
    description = json.loads((data_root / "dataset_description.json").read_text())
    if description.get("License") != "CC-BY-4.0" or description.get("Version") != "1.0.0":
        raise ValueError("License or source version changed")
    provenance = json.loads((data_root / "sourcedata/sourcedata_provenance.json").read_text())
    lookup = {entry["path"]: entry for entry in entries}
    selection = {}
    for subject in subjects:
        files = [entry for entry in entries if entry["path"].startswith(f"sub-{subject}/")]
        headers = [item for item in provenance["files"] if item["subject"] == str(subject)]
        if len(headers) != 24:
            raise ValueError("Exactly 24 explicitly subject-mapped upstream headers are required")
        for header in headers:
            entry = lookup["sourcedata/" + header["file"]]
            if (entry["size"] != header["bytes"] or entry["checksum"] != header["sha256"]
                    or entry["checksum_algorithm"] != "sha256"):
                raise ValueError("Upstream header provenance and official manifest disagree")
            files.append(entry)
        selection[subject] = files
    if any(len(files) != 188 or sum(e["path"].endswith(".edf") for e in files) != 24
           for files in selection.values()):
        raise ValueError("Pinned cohort needs 164 derivative files + 24 upstream headers")
    missing_bytes = sum(entry["size"] for files in selection.values() for entry in files
                        if not (data_root / entry["path"]).exists())
    plan = {"dataset": "nm000305", "version": "1.0.0", "license": "CC-BY-4.0",
            "manifest_sha256": MANIFEST_SHA256, "subjects": subjects,
            "missing_declared_bytes": missing_bytes,
            "available_disk_bytes": shutil.disk_usage(data_root).free,
            "workers": args.workers, "network_requested": args.download}
    plan["config_sha256"] = config_sha256
    print(json.dumps(plan), flush=True)
    if not args.download:
        return
    if plan["available_disk_bytes"] < missing_bytes + 1024**3:
        raise ValueError("Insufficient disk for selected cohort plus 1 GiB reserve")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    failed = False
    for subject, files in selection.items():
        folder = output / f"sub-{subject}"
        write_immutable(folder / "download_manifest.json", root_entries + files)
        started = utc_now()
        # Metadata completes before any EDF transfer for this participant.
        outcomes = []
        for signals in (False, True):
            batch = [entry for entry in files if entry["path"].endswith(".edf") == signals]
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                outcomes.extend(pool.map(lambda entry: guarded_fetch(data_root, entry), batch))
        subject_failed = [entry for entry in outcomes if entry["status"] == "failed"]
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                         text=True).strip()
        receipt = {**plan, "subject": f"sub-{subject}", "started_at_utc": started,
                   "finished_at_utc": utc_now(), "source_commit": commit,
                   "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "root_metadata": roots, "files": outcomes,
                   "complete": not subject_failed, "subject_file_count": len(files),
                   "edf_file_count": sum(entry["path"].endswith(".edf") for entry in files),
                   "upstream_header_count": sum(entry["path"].endswith(".vhdr") for entry in files),
                   "subject_declared_bytes": sum(entry["size"] for entry in files),
                   "transferred_bytes": sum(entry["transferred_bytes"] for entry in outcomes),
                   "new_verified_bytes": sum(entry["new_verified_bytes"] for entry in outcomes),
                   "failed_files": [entry["path"] for entry in subject_failed]}
        write_immutable(folder / f"download_receipt_{stamp}.json", receipt)
        print(json.dumps({key: receipt[key] for key in (
            "subject", "complete", "subject_file_count", "edf_file_count",
            "subject_declared_bytes", "transferred_bytes", "new_verified_bytes", "failed_files"
        )}), flush=True)
        failed = failed or bool(subject_failed)
    if failed:
        raise SystemExit("One or more files failed; receipts retained and cohort is incomplete")


if __name__ == "__main__":
    main()
