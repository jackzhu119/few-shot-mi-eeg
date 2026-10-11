#!/usr/bin/env python3
"""Copy explicit research directories to immutable Cloudflare R2 object keys.

Planning is the default. Transfer requires ``--execute`` and existing runtime
credentials; credential values, endpoint and bucket are never written to logs.
Each key is conditionally created. A conflicting remote object stops that file;
it is never overwritten. Multipart completion is also conditional.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

MIB = 1024 * 1024
PROTECTED_NAMES = {
    ".git", ".aws", ".ssh", ".env", "credentials", "credentials.json",
    "auth.json", "secrets.json", "id_rsa", "id_ed25519",
}
PROTECTED_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_key_prefix(value: str) -> str:
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or ".." in path.parts or "\\" in value
            or str(path) != value or not value.startswith("few-shot-mi-eeg/")):
        raise ValueError("Key prefix must be a canonical path below few-shot-mi-eeg/")
    return value


def safe_source_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Source must be an existing directory, not a symlink")
    files = []
    for path in sorted(root.rglob("*")):
        parts = path.relative_to(root).parts
        if (path.is_symlink() or any(p.lower() in PROTECTED_NAMES or p.startswith(".env.")
                                     for p in parts)
                or path.suffix.lower() in PROTECTED_SUFFIXES):
            raise ValueError(f"Refusing protected or symlink source path: {path.relative_to(root)}")
        if path.is_file():
            files.append(path)
    if not files:
        raise ValueError("No source files found")
    return files


def file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(MIB), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def make_plan(root: Path, prefix: str, readback_mode: str) -> list[dict]:
    prefix = safe_key_prefix(prefix)
    entries = []
    for path in safe_source_files(root):
        relative = path.relative_to(root).as_posix()
        digest, size = file_digest(path)
        entries.append({"relative_path": relative, "key": f"{prefix}/{relative}",
                        "sha256": digest, "bytes": size, "status": "planned"})
    selected = set()
    if readback_mode == "all":
        selected = {entry["key"] for entry in entries}
    elif readback_mode == "sample":
        # One largest file per extension: deterministic coverage of format types.
        by_suffix = {}
        for entry in entries:
            suffix = Path(entry["relative_path"]).suffix.lower()
            if suffix not in by_suffix or entry["bytes"] > by_suffix[suffix]["bytes"]:
                by_suffix[suffix] = entry
        selected = {entry["key"] for entry in by_suffix.values()}
    elif readback_mode != "none":
        raise ValueError("Unknown readback mode")
    for entry in entries:
        entry["selected_for_full_readback"] = entry["key"] in selected
    return entries


def response_status(response: dict) -> int:
    return response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)


def error_code(error: Exception) -> str:
    # Never serialize SDK exception messages: they may expose signed URLs.
    value = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    return str(value) if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", str(value)) else ""


def object_head(client, bucket: str, key: str) -> dict | None:
    try:
        result = client.head_object(Bucket=bucket, Key=key)
    except Exception as error:
        if error_code(error) in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    if response_status(result) != 200:
        raise ValueError("Object HEAD did not return HTTP 200")
    return result


def verify_head(head: dict, entry: dict) -> None:
    if (head["ContentLength"] != entry["bytes"]
            or head.get("Metadata", {}).get("sha256") != entry["sha256"]):
        raise ValueError("Existing key has different length or SHA256 metadata; use a new version")


def verify_readback(client, bucket: str, entry: dict) -> dict:
    result = client.get_object(Bucket=bucket, Key=entry["key"])
    digest = hashlib.sha256()
    count = 0
    body = result["Body"]
    try:
        for block in iter(lambda: body.read(MIB), b""):
            digest.update(block)
            count += len(block)
            if count > entry["bytes"]:
                raise ValueError("Remote readback exceeds expected length")
    finally:
        body.close()
    if (response_status(result) != 200 or count != entry["bytes"]
            or digest.hexdigest() != entry["sha256"]):
        raise ValueError("Full remote readback SHA256 or length mismatch")
    return {"verification": "full_get_sha256_verified", "readback_bytes": count,
            "get_http_status": response_status(result)}


def transport_md5(block: bytes) -> str:
    # S3 Content-MD5 protects transport bytes; it is never used as scientific SHA256.
    return base64.b64encode(hashlib.md5(block, usedforsecurity=False).digest()).decode()


def transfer_file(client, bucket: str, path: Path, entry: dict, *,
                  multipart_threshold: int = 32 * MIB, part_size: int = 32 * MIB) -> dict:
    output = {**entry, "started_at_utc": utc_now(), "uploaded_bytes": 0,
              "readback_bytes": 0}
    remote = object_head(client, bucket, entry["key"])
    if remote is not None:
        verify_head(remote, entry)
        # Existing object reuse requires content verification, not self-declared metadata.
        output.update(verify_readback(client, bucket, entry), status="reused_content_verified",
                      head_http_status=response_status(remote), finished_at_utc=utc_now())
        return output
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    common = {"Bucket": bucket, "Key": entry["key"],
              "Metadata": {"sha256": entry["sha256"]}, "ContentType": content_type}
    if entry["bytes"] < multipart_threshold:
        block = path.read_bytes()
        if len(block) != entry["bytes"] or hashlib.sha256(block).hexdigest() != entry["sha256"]:
            raise ValueError("Source changed after planning; refusing upload")
        try:
            result = client.put_object(**common, Body=block, ContentLength=len(block),
                                       ContentMD5=transport_md5(block), IfNoneMatch="*")
        except Exception as error:
            if error_code(error) in {"PreconditionFailed", "412", "ConditionalRequestConflict"}:
                # Another writer won; verify that its bytes match without overwriting them.
                head = object_head(client, bucket, entry["key"])
                if head is None:
                    raise
                verify_head(head, entry)
                output.update(verify_readback(client, bucket, entry),
                              status="concurrent_create_content_verified",
                              head_http_status=response_status(head), finished_at_utc=utc_now())
                return output
            raise
        output["upload_method"] = "conditional_put"
        output["put_http_status"] = response_status(result)
        if response_status(result) != 200:
            raise ValueError("Conditional PUT did not return HTTP 200")
    else:
        if not 5 * MIB <= part_size <= 128 * MIB or entry["bytes"] > part_size * 10000:
            raise ValueError("Multipart part size or count is outside supported bounds")
        created = client.create_multipart_upload(**common)
        upload_id = created["UploadId"]
        completed = False
        digest = hashlib.sha256()
        count = 0
        parts = []
        try:
            with path.open("rb") as stream:
                for number, block in enumerate(iter(lambda: stream.read(part_size), b""), 1):
                    if number > 10000:
                        raise ValueError("Source expanded beyond multipart limit")
                    digest.update(block)
                    count += len(block)
                    result = client.upload_part(Bucket=bucket, Key=entry["key"],
                                                UploadId=upload_id, PartNumber=number, Body=block,
                                                ContentLength=len(block),
                                                ContentMD5=transport_md5(block))
                    if response_status(result) != 200:
                        raise ValueError("Multipart part did not return HTTP 200")
                    parts.append({"PartNumber": number, "ETag": result["ETag"]})
            if count != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError("Source changed after planning; aborting multipart upload")
            result = client.complete_multipart_upload(
                Bucket=bucket, Key=entry["key"], UploadId=upload_id,
                MultipartUpload={"Parts": parts}, IfNoneMatch="*")
            if response_status(result) != 200:
                raise ValueError("Conditional multipart completion did not return HTTP 200")
            completed = True
            output.update(upload_method="conditional_multipart", multipart_parts=len(parts),
                          complete_http_status=response_status(result))
        finally:
            if not completed:
                client.abort_multipart_upload(Bucket=bucket, Key=entry["key"], UploadId=upload_id)
    output["uploaded_bytes"] = entry["bytes"]
    head = object_head(client, bucket, entry["key"])
    if head is None:
        raise ValueError("New object absent after upload")
    verify_head(head, entry)
    output.update(status="uploaded_head_verified", head_http_status=response_status(head),
                  verification="head_length_and_sha256_metadata_verified")
    if entry["selected_for_full_readback"]:
        output.update(verify_readback(client, bucket, entry), status="uploaded_content_verified")
    output["finished_at_utc"] = utc_now()
    return output


def guarded_transfer(client, bucket: str, root: Path, entry: dict, **kwargs) -> dict:
    try:
        return transfer_file(client, bucket, root / entry["relative_path"], entry, **kwargs)
    except Exception as error:
        return {**entry, "status": "failed", "error_type": type(error).__name__,
                "error_code": error_code(error), "finished_at_utc": utc_now()}


def write_receipt(path: Path, receipt: dict) -> None:
    records = receipt["files"]
    verified = [e for e in records if e["status"] in {
        "uploaded_head_verified", "uploaded_content_verified", "reused_content_verified",
        "concurrent_create_content_verified"}]
    receipt["updated_at_utc"] = utc_now()
    receipt["totals"] = {
        "planned_files": len(records), "planned_bytes": sum(e["bytes"] for e in records),
        "verified_files": len(verified), "verified_bytes": sum(e["bytes"] for e in verified),
        "failed_files": sum(e["status"] == "failed" for e in records),
        "full_get_sha256_verified_files": sum(e.get("verification") == "full_get_sha256_verified"
                                              for e in records),
        "uploaded_bytes": sum(e.get("uploaded_bytes", 0) for e in records),
        "readback_bytes": sum(e.get("readback_bytes", 0) for e in records),
    }
    temporary = path.with_suffix(path.suffix + ".partial")
    data = json.dumps(receipt, ensure_ascii=False, indent=2).encode() + b"\n"
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def build_client():
    import boto3
    from botocore.config import Config

    needed = ["R2_ENDPOINT", "R2_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    if any(not os.environ.get(name) for name in needed):
        raise ValueError("Required R2 runtime credential variables are missing")
    endpoint = urlsplit(os.environ["R2_ENDPOINT"])
    if (endpoint.scheme != "https" or not endpoint.hostname
            or not endpoint.hostname.endswith(".r2.cloudflarestorage.com")
            or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
            or endpoint.path not in {"", "/"}):
        raise ValueError("R2 endpoint must be a canonical Cloudflare HTTPS endpoint")
    client = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"],
                         region_name=os.environ.get("AWS_DEFAULT_REGION", "auto"),
                         config=Config(signature_version="s3v4", connect_timeout=20,
                                       read_timeout=120, max_pool_connections=8,
                                       retries={"mode": "standard", "total_max_attempts": 3},
                                       request_checksum_calculation="when_required",
                                       response_checksum_validation="when_required"))
    return client, os.environ["R2_BUCKET"], boto3.__version__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--key-prefix", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--readback-mode", choices=["all", "sample", "none"], default="sample")
    parser.add_argument("--multipart-part-mib", type=int, default=32, choices=range(5, 129))
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError("Use a new receipt filename; prior audit receipts are preserved")
    root = args.source.absolute()
    # Never collect a receipt from within its own source tree while it is changing.
    if args.receipt.absolute().is_relative_to(root):
        raise ValueError("Receipt must be outside the uploaded source directory")
    records = make_plan(root, args.key_prefix, args.readback_mode)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 1, "started_at_utc": utc_now(), "source_root": str(root),
        "key_prefix": args.key_prefix, "status": "planned", "workers": args.workers,
        "readback_mode": args.readback_mode,
        "full_readback_selection": "all files" if args.readback_mode == "all" else
            "largest file per extension" if args.readback_mode == "sample" else "no new file GET",
        "immutable_create": "IfNoneMatch=* on PutObject and CompleteMultipartUpload",
        "existing_reuse_requires": "HEAD length/SHA256 metadata plus full GET SHA256",
        "etag_is_not_a_sha256": True, "credential_values_logged": False,
        "remote_overwrite_enabled": False, "files": records,
    }
    write_receipt(args.receipt, receipt)
    print(json.dumps({"status": "planned", **receipt["totals"]}), flush=True)
    if not args.execute:
        return 0
    try:
        client, bucket, sdk_version = build_client()
        receipt.update(status="transferring", boto3_version=sdk_version)
        write_receipt(args.receipt, receipt)
        indexes = {entry["key"]: index for index, entry in enumerate(records)}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {pool.submit(guarded_transfer, client, bucket, root, entry,
                                   part_size=args.multipart_part_mib * MIB) for entry in records}
            finished = 0
            for task in as_completed(pending):
                result = task.result()
                records[indexes[result["key"]]] = result
                finished += 1
                # Only this controlling thread mutates/atomically replaces the receipt.
                write_receipt(args.receipt, receipt)
                if finished % 50 == 0 or result["status"] == "failed" or finished == len(records):
                    print(json.dumps({"completed": finished, **receipt["totals"]}), flush=True)
        receipt["status"] = "failed" if receipt["totals"]["failed_files"] else "completed"
        receipt["finished_at_utc"] = utc_now()
        write_receipt(args.receipt, receipt)
        return 1 if receipt["status"] == "failed" else 0
    except Exception as error:
        receipt.update(status="failed", error_type=type(error).__name__,
                       error_code=error_code(error), finished_at_utc=utc_now())
        write_receipt(args.receipt, receipt)
        print(json.dumps({"status": "failed", "error_type": type(error).__name__,
                          "error_code": error_code(error)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
