#!/usr/bin/env python3
"""Verify recorded source bytes and merge closed R2 evidence without retransfers.

HEAD revalidation establishes current length and stored hash metadata only. It
does not count as new full GET evidence or new upload. Snapshot outputs are new
directories so historical catalogs and failed transfers remain intact.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sync_research_r2 import build_client, verify_head

BASE = Path("research_logs/public_data_expansion_20261010/r2/storage_catalog_final_20261012_run01.json")
NEW = Path("research_logs/latest_two_sources_20261012")
MIND = NEW / "mind_ingestion/full_eeg_v4"
MIND_PREFIX = "few-shot-mi-eeg/datasets/mind2026/sciencedb34326/V4/eeg-only"
SUCCESS = {"uploaded_content_verified", "reused_content_verified", "concurrent_create_content_verified"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def catalog_module():
    path = BASE.parent / "build_recorded_storage_catalog.py"
    spec = importlib.util.spec_from_file_location("recorded_storage_catalog", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_reference(path: Path, expected_sha256: str) -> dict:
    if sha256(path) != expected_sha256:
        raise ValueError("Historical evidence hash changed")
    return read(path)


def local_check(item: tuple[Path, dict]) -> dict:
    path, entry = item
    result = {"path": str(path), "bytes": entry["bytes"], "expected_sha256": entry["sha256"]}
    if not path.exists():
        return {**result, "classification": "C", "status": "local_missing_recorded_remote_copy"}
    if not path.is_file() or path.is_symlink():
        return {**result, "classification": "F", "status": "unsafe_local_source"}
    if path.stat().st_size != entry["bytes"]:
        return {**result, "classification": "E", "status": "local_length_mismatch"}
    actual = sha256(path)
    return {**result, "actual_sha256": actual,
            "classification": "A" if actual == entry["sha256"] else "E",
            "status": "local_sha256_verified" if actual == entry["sha256"] else "local_sha256_mismatch"}


def normalize_mind(entries: list[tuple[Path, dict]], *, source_root: Path = MIND) -> dict:
    records, references, keys = [], [], set()
    for path, entry in entries:
        key = entry.get("key", "")
        if (not key.startswith(MIND_PREFIX + "/") or key in keys
                or entry.get("status") not in SUCCESS
                or entry.get("verification") != "full_get_sha256_verified"
                or entry.get("head_http_status") != 200 or entry.get("get_http_status") != 200
                or type(entry.get("bytes")) is not int or entry["bytes"] < 0
                or entry.get("readback_bytes") != entry["bytes"]
                or not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", ""))):
            raise ValueError("MIND entry lacks unique immutable identity and complete readback")
        if "/MIND_BIDS/" in key:
            relative = entry["relative_path"]
            if key != MIND_PREFIX + "/MIND_BIDS/" + relative or ".." in Path(relative).parts:
                raise ValueError("MIND source key identity differs")
            source = read(source_root / "source_receipts" / (relative + ".json"))
            if (source.get("official_size_and_md5_pass") is not True
                    or source.get("relative_path") != relative
                    or source["sha256"] != entry["sha256"] or source["bytes"] != entry["bytes"]
                    or source["md5_actual"] != source["official_md5_normalized_32hex"]
                    or source["md5_actual"] != source["official_md5_original"].lower().zfill(32)
                    or source["record"]["path"] != "/V4/MIND_BIDS/" + relative
                    or int(source["record"]["size"]) != entry["bytes"]):
                raise ValueError("MIND official source and remote identity differ")
        elif key != MIND_PREFIX + "/audit-stages/metadata-only/checked_metadata_r2_closed.json":
            raise ValueError("Unknown MIND audit object outside explicit snapshot scope")
        keys.add(key)
        records.append(entry)
        references.append({"path": str(path), "sha256": sha256(path)})
    totals = {"planned_files": len(records), "planned_bytes": sum(x["bytes"] for x in records),
              "verified_files": len(records), "verified_bytes": sum(x["bytes"] for x in records),
              "failed_files": 0, "full_get_sha256_verified_files": len(records),
              "uploaded_bytes": sum(x.get("uploaded_bytes", 0) for x in records),
              "readback_bytes": sum(x["readback_bytes"] for x in records)}
    return {"schema_version": 1, "status": "completed", "key_prefix": MIND_PREFIX,
            "readback_mode": "all", "scope": "closed per-object receipts captured at snapshot time; unfinished signals excluded",
            "credential_values_logged": False, "files": records, "totals": totals,
            "original_receipt_references": references}


def closed_run_check(path: Path, remote: dict[str, dict], *, source_root: Path = MIND) -> dict:
    closure = read(path)
    audit, events = read(path.parent / "audit.json"), json.loads((path.parent / "source_events.json").read_text())
    relative = next(x for x in closure["source_relative_paths"] if x.endswith("_eeg.eeg"))
    entry = remote[relative]
    if (closure.get("closed") is not True or closure.get("status") != "completed"
            or closure.get("all_sources_official_size_md5_pass") is not True
            or closure.get("all_objects_head_and_full_get_sha256_pass") is not True
            or audit.get("all_integrity_checks_pass") is not True
            or audit.get("all_values_finite") is not True
            or audit["source_file_sha256"] != entry["sha256"]
            or len(events) != audit["source_events"]["source_event_count"]
            or len({e["event_id"] for e in events}) != len(events)
            or any(p not in remote for p in closure["source_relative_paths"])):
        raise ValueError("Closed run lacks complete matching source/event/remote evidence")
    return {"run": closure["run_name"], "subject": relative.split("/")[0],
            "signal_relative_path": relative, "signal_bytes": entry["bytes"],
            "audit_sha256": sha256(path.parent / "audit.json"),
            "event_ledger_sha256": sha256(path.parent / "source_events.json"),
            "closure_path": str(path), "closure_sha256": sha256(path)}


def head_check(client, bucket: str, entry: dict) -> dict:
    result = {"key": entry["key"], "bytes": entry["bytes"], "sha256": entry["sha256"]}
    try:
        head = client.head_object(Bucket=bucket, Key=entry["key"])
        verify_head(head, entry)
        if head.get("ResponseMetadata", {}).get("HTTPStatusCode") != 200:
            raise ValueError("HEAD did not return HTTP 200")
        return {**result, "status": "current_head_length_sha256_metadata_verified", "head_http_status": 200}
    except Exception as error:
        return {**result, "status": "failed", "error_type": type(error).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--head-all-recorded", action="store_true")
    parser.add_argument("--extra-receipt", action="append", type=Path, default=[])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    now = datetime.now(timezone.utc).isoformat()
    # Capture the closed-run set before object receipts: a concurrently closing
    # later run belongs to the next snapshot, never an incomplete joined snapshot.
    closed_paths = sorted((MIND / "runs").glob("*/closed.json"))
    baseline = read(BASE)
    previous = [Path(s["receipt"]) for s in baseline["stages"]]
    receipts = [verify_reference(p, s["receipt_sha256"]) for p, s in zip(previous, baseline["stages"])]
    sources = read(Path("research_logs/public_data_expansion_20261010/resource_inventory_20261011.json"))["sources"]
    roots = {str(Path(s["data_root"]).resolve()): s for s in sources}
    local_items, source_summaries = [], []
    for root, source in roots.items():
        selected = {entry["relative_path"]: entry for receipt in receipts
                    if receipt.get("source_root") == root for entry in receipt["files"]}
        if (len(selected) != source["necessary_official_file_count"]
                or sum(x["bytes"] for x in selected.values()) != source["necessary_official_bytes"]):
            raise ValueError("Recorded source subset count differs from frozen inventory")
        local_items.extend((Path(root) / relative, entry) for relative, entry in selected.items())
        source_summaries.append({"name": source["name"], "version": source["fixed_version"],
                                 "data_root": root, "expected_files": len(selected),
                                 "expected_bytes": source["necessary_official_bytes"],
                                 "official_manifest": source.get("official_manifest"),
                                 "existing_scope_authorized": True})
    with ThreadPoolExecutor(max_workers=4) as pool:
        local = list(pool.map(local_check, local_items))
    for summary in source_summaries:
        items = [x for x in local if x["path"].startswith(summary["data_root"] + "/")]
        summary.update(verified_local_files=sum(x["classification"] == "A" for x in items),
                       missing_files=sum(x["classification"] == "C" for x in items),
                       corrupted_files=sum(x["classification"] == "E" for x in items))
    write_new(args.output / "historical_source_local_sha256.json", {"captured_at_utc": now, "sources": source_summaries, "files": local})
    new_standard = [NEW / "r2/wangliu2026_raw_run01.json", NEW / "r2/wangliu2026_source_audit_run01.json", *args.extra_receipt]
    single_paths = sorted((MIND / "r2_receipts").rglob("*.json"))
    closing = MIND / "checked_metadata_closing_r2_full_get.json"
    if closing.exists():
        single_paths.append(closing)
    mind = normalize_mind([(p, read(p)) for p in single_paths])
    normalized_path = args.output / "mind_closed_objects_normalized_receipt.json"
    write_new(normalized_path, mind)
    catalog = catalog_module().build_catalog([*previous, *new_standard, normalized_path])
    write_new(args.output / "storage_catalog.json", catalog)
    source_remote = {x["relative_path"]: x for x in mind["files"] if "/MIND_BIDS/" in x["key"]}
    runs = [closed_run_check(p, source_remote) for p in closed_paths]
    counts = {x["subject"]: sum(y["subject"] == x["subject"] for y in runs) for x in runs}
    progress = {"captured_at_utc": now, "historical_sources": source_summaries,
                "historical_sources_not_redownloaded_or_reuploaded": True,
                "historical_local_verified_files": sum(x["classification"] == "A" for x in local),
                "historical_source_missing_or_corrupt_files": sum(x["classification"] != "A" for x in local),
                "wangliu": {"published_IDs": 24, "recordings": 268, "raw_archive_and_metadata_R2_complete": True,
                             "official_raw_files": 10, "official_raw_bytes": 5175298549, "model_qualified": False},
                "mind": {"planned_files": 695, "planned_bytes": 31972856102, "planned_runs": 90,
                         "planned_IDs": 30, "verified_remote_source_files": len(source_remote),
                         "verified_remote_source_bytes": sum(x["bytes"] for x in source_remote.values()),
                         "completed_source_and_audit_runs": len(runs), "runs": runs,
                         "IDs_with_some_complete_runs": sorted(counts),
                         "IDs_with_all_three_complete_runs": sorted(s for s, n in counts.items() if n == 3),
                         "full_source_download_complete": len(runs) == 90,
                         "remaining_source_files": 695 - len(source_remote),
                         "remaining_full_file_bytes": 31972856102 - sum(x["bytes"] for x in source_remote.values()),
                         "remaining_bytes_caveat": "full-file deficit; verified partial extent bytes are preserved separately in range checkpoints"},
                "global_unique_independent_training_N": None, "new_source_model_training_performed": False,
                "catalog": {k: catalog[k] for k in ["distinct_remote_objects", "distinct_remote_bytes", "distinct_full_get_sha256_verified_objects"]},
                "new_objects_since_historical_catalog": catalog["distinct_remote_objects"] - baseline["distinct_remote_objects"],
                "new_bytes_since_historical_catalog": catalog["distinct_remote_bytes"] - baseline["distinct_remote_bytes"],
                "credential_values_logged": False}
    write_new(args.output / "acquisition_progress.json", progress)
    if args.head_all_recorded:
        client, bucket, sdk = build_client()
        identities = {x["key"]: x for r in [*receipts, *(read(p) for p in new_standard), mind] for x in r["files"]}
        for receipt in [*receipts, *(read(p) for p in new_standard), mind]:
            for entry in receipt["files"]:
                saved = identities[entry["key"]]
                if (saved["sha256"], saved["bytes"]) != (entry["sha256"], entry["bytes"]):
                    raise ValueError("Conflicting immutable object identity")
        results = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            for result in pool.map(lambda x: head_check(client, bucket, x), identities.values()):
                results.append(result)
                if len(results) % 500 == 0:
                    print(json.dumps({"current_head_checked": len(results), "failed": sum(x["status"] == "failed" for x in results)}), flush=True)
        failed = sum(x["status"] == "failed" for x in results)
        write_new(args.output / "current_remote_head_revalidation.json", {"status": "completed" if failed == 0 else "completed_with_failures",
                  "captured_at_utc": datetime.now(timezone.utc).isoformat(), "boto3_version": sdk,
                  "objects_checked": len(results), "failed_objects": failed,
                  "new_uploads_performed": 0, "remote_full_GET_revalidation_performed": False,
                  "scope": "current HEAD length and SHA256 metadata; historic/new full GET receipts remain distinct", "files": results})
        if failed:
            return 1
    print(json.dumps({"output": str(args.output), "historical_local_verified_files": progress["historical_local_verified_files"],
                      "mind_complete_runs": len(runs), "new_R2_objects": progress["new_objects_since_historical_catalog"]}), flush=True)
    return int(progress["historical_source_missing_or_corrupt_files"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
