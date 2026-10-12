"""Recount closed transfer receipts by immutable object key, without network IO.

This is an audit companion, not a bucket listing. A HEAD metadata check is not
counted as independent content verification. Repeated matching keys are counted
once, and conflicting bytes at any key fail the catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SUCCESS = {
    "uploaded_head_verified", "uploaded_content_verified", "reused_content_verified",
    "concurrent_create_content_verified",
}


def build_catalog(paths: list[Path]) -> dict:
    stages = []
    objects = {}
    seen_receipt_hashes = set()
    duplicate_receipt_references = []
    for path in paths:
        raw = path.read_bytes()
        receipt_sha256 = hashlib.sha256(raw).hexdigest()
        if receipt_sha256 in seen_receipt_hashes:
            duplicate_receipt_references.append({"receipt": str(path),
                                                  "receipt_sha256": receipt_sha256})
            continue
        seen_receipt_hashes.add(receipt_sha256)
        receipt = json.loads(raw)
        if receipt["status"] != "completed":
            raise ValueError(f"Transfer receipt is not closed successfully: {path}")
        entries = receipt["files"]
        if any(entry["status"] not in SUCCESS for entry in entries):
            raise ValueError(f"Transfer receipt contains unverified entries: {path}")
        prefix = receipt["key_prefix"] + "/"
        stage_keys = set()
        for entry in entries:
            key = entry["key"]
            if (not key.startswith(prefix) or key in stage_keys
                    or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
                    or not isinstance(entry["bytes"], int) or entry["bytes"] < 0):
                raise ValueError(f"Invalid or repeated receipt object: {path}")
            stage_keys.add(key)
            content = (entry["sha256"], entry["bytes"])
            existing = objects.get(key)
            full_get = entry.get("verification") == "full_get_sha256_verified"
            if existing is not None:
                if existing["content"] != content:
                    raise ValueError(f"Conflicting immutable key in receipts: {key}")
                existing["full_get_sha256_verified"] |= full_get
            else:
                objects[key] = {"content": content,
                                "full_get_sha256_verified": full_get}
        expected = {
            "planned_files": len(entries),
            "planned_bytes": sum(entry["bytes"] for entry in entries),
            "verified_files": len(entries),
            "verified_bytes": sum(entry["bytes"] for entry in entries),
            "failed_files": 0,
            "full_get_sha256_verified_files": sum(
                entry.get("verification") == "full_get_sha256_verified"
                for entry in entries),
            "uploaded_bytes": sum(entry.get("uploaded_bytes", 0) for entry in entries),
            "readback_bytes": sum(entry.get("readback_bytes", 0) for entry in entries),
        }
        if receipt["totals"] != expected:
            raise ValueError(f"Receipt aggregate does not equal its file evidence: {path}")
        stages.append({"receipt": str(path), "receipt_sha256": receipt_sha256,
                       "key_prefix": receipt["key_prefix"], "status": "completed",
                       "totals": expected, "readback_mode": receipt["readback_mode"]})
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "only explicitly supplied, completed project transfer receipts; not a full bucket inventory",
        "credential_values_logged": False,
        "public_access_policy_changed": False,
        "stages": stages,
        "duplicate_receipt_references_excluded": duplicate_receipt_references,
        "distinct_remote_objects": len(objects),
        "distinct_remote_bytes": sum(value["content"][1] for value in objects.values()),
        "distinct_full_get_sha256_verified_objects": sum(
            value["full_get_sha256_verified"] for value in objects.values()),
        "physical_uploaded_bytes_from_receipts": sum(stage["totals"]["uploaded_bytes"]
                                                      for stage in stages),
        "actual_readback_bytes_from_receipts": sum(stage["totals"]["readback_bytes"]
                                                   for stage in stages),
        "deduplication": "exact immutable key and identical SHA256/length; HEAD-only rechecks do not add objects",
        "verification_caveat": "All counted objects passed HEAD length/stored SHA256 metadata checks. Full remote content is independently verified only for the explicitly counted full GET objects.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve the previous catalog; choose another output")
    catalog = build_catalog(args.receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2) + "\n")
    print(json.dumps({key: catalog[key] for key in [
        "distinct_remote_objects", "distinct_remote_bytes",
        "distinct_full_get_sha256_verified_objects"]}))


if __name__ == "__main__":
    main()
