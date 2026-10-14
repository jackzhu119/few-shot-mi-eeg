#!/usr/bin/env python3
"""Restartable official MIND V4 EEG-only streaming census with immutable R2 readback.

One large BrainVision signal is cached at a time. Source MD5 and full R2 GET SHA256
must close each run before only its task-created .eeg cache can be evicted.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

import requests

from audit_mind_source import audit_run, duplicate_groups, file_hashes, now, verify_source
from sync_research_r2 import build_client, error_code, safe_key_prefix, transfer_file

PREFIX = "few-shot-mi-eeg/datasets/mind2026/sciencedb34326/V4/eeg-only"
SOURCE_ROOT = "/V4/MIND_BIDS/"
MAX_SIGNAL_BYTES = 512 * 1024 * 1024
FULL_GET = "full_get_sha256_verified"


def atomic_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".atomic-tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def immutable_json(path: Path, value: dict | list) -> None:
    if path.exists():
        raise FileExistsError("Prior provenance file is preserved")
    atomic_json(path, value)


def relative_path(record: dict) -> str:
    source = record["path"]
    if not source.startswith(SOURCE_ROOT):
        raise ValueError("Record is outside the pinned official V4 BIDS root")
    value = source[len(SOURCE_ROOT):]
    canonical = PurePosixPath(value)
    if canonical.is_absolute() or ".." in canonical.parts or str(canonical) != value:
        raise ValueError("Unsafe official relative path")
    return value


def read_manifest(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def select_manifest(path: Path) -> list[dict]:
    selected = [r for r in read_manifest(path)
                if "/" not in relative_path(r) or
                (len(PurePosixPath(relative_path(r)).parts) == 3 and
                 PurePosixPath(relative_path(r)).parts[1] == "eeg" and
                 PurePosixPath(relative_path(r)).parts[0].startswith("sub-"))]
    if len({r["path"] for r in selected}) != len(selected):
        raise ValueError("Duplicate manifest path")
    signals = [r for r in selected if r["path"].endswith("_eeg.eeg")]
    if len(signals) != 90 or max(int(r["size"]) for r in signals) > MAX_SIGNAL_BYTES:
        raise ValueError("Pinned MIND EEG census must have exactly 90 bounded signals")
    subjects = {PurePosixPath(relative_path(r)).parts[0] for r in signals}
    if subjects != {f"sub-{i:02d}" for i in range(1, 31)}:
        raise ValueError("Pinned census must retain all 30 published IDs")
    return sorted(selected, key=lambda r: r["path"])


def receipt_path(log: Path, kind: str, relative: str) -> Path:
    return log / kind / (relative + ".json")


def load_json(path: Path):
    return json.loads(path.read_text())


def ensure_source(record: dict, cache: Path, log: Path, representative: Path | None) -> dict:
    relative = relative_path(record)
    path = cache / relative
    receipt = receipt_path(log, "source_receipts", relative)
    ownership = receipt_path(log, "cache_ownership", relative)
    if path.exists():
        checked = verify_source(path, record)
        if receipt.exists():
            saved = load_json(receipt)
            if saved["sha256"] != checked["sha256"] or saved["record"] != record:
                raise ValueError("Existing source receipt differs from checked source")
            return saved
        result = {**checked, "record": record, "relative_path": relative,
                  "checked_at_utc": now(), "local_origin": "existing_checked_cache",
                  "cache_created_by_this_task": ownership.exists()}
        immutable_json(receipt, result)
        return result
    if int(record["size"]) > MAX_SIGNAL_BYTES:
        raise ValueError("Source file exceeds single-file cache bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    if partial.exists() and not ownership.exists():
        raise ValueError("Unknown partial cache ownership; preserve and stop")
    if not ownership.exists():
        immutable_json(ownership, {"created_at_utc": now(), "relative_path": relative,
                                   "source_record": record, "cache_created_by_this_task": True})
    elif load_json(ownership)["source_record"] != record:
        raise ValueError("Cache ownership source version differs")
    before = time.monotonic()
    reused = representative / relative if representative else None
    if reused and reused.is_file() and not partial.exists():
        # Prior result remains untouched. Only the new copy is later evictable.
        verify_source(reused, record)
        with reused.open("rb") as source, partial.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        origin = "verified_copy_of_preserved_representative"
        http_status = None
    else:
        origin = "official_public_download"
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > int(record["size"]):
            raise ValueError("Partial download exceeds official size; preserve and stop")
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        if offset < int(record["size"]):
            with requests.get(record["download_endpoint"], headers=headers, stream=True,
                              timeout=(20, 120), allow_redirects=True) as response:
                http_status = response.status_code
                expected_status = 206 if offset else 200
                if http_status != expected_status:
                    raise ValueError("Official GET did not return the expected whole/range status")
                if offset and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise ValueError("Official resume range differs from preserved partial")
                mode = "ab" if offset else "xb"
                with partial.open(mode) as output:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        output.write(block)
                        if output.tell() > int(record["size"]):
                            raise ValueError("Official GET exceeds declared size; preserve and stop")
                    output.flush()
                    os.fsync(output.fileno())
        else:
            http_status = None
    checked = verify_source(partial, record)
    if path.exists():
        raise FileExistsError("Source appeared during download; preserve both files")
    os.replace(partial, path)
    result = {**checked, "record": record, "relative_path": relative,
              "checked_at_utc": now(), "local_origin": origin, "http_status": http_status,
              "download_elapsed_seconds": time.monotonic() - before,
              "cache_created_by_this_task": True, "signed_url_logged": False}
    if receipt.exists():
        saved = load_json(receipt)
        if saved["sha256"] != result["sha256"] or saved["record"] != record:
            raise ValueError("Prior source receipt differs from resumed checked source")
        return saved
    immutable_json(receipt, result)
    return result


def upload_source(client, bucket: str, cache: Path, log: Path, source: dict) -> dict:
    relative = source["relative_path"]
    target = receipt_path(log, "r2_receipts", relative)
    entry = {"relative_path": relative, "key": f"{PREFIX}/MIND_BIDS/{relative}",
             "sha256": source["sha256"], "bytes": source["bytes"],
             "selected_for_full_readback": True, "status": "planned"}
    if target.exists():
        saved = load_json(target)
        if (saved.get("verification") != FULL_GET or saved.get("sha256") != entry["sha256"]
                or saved.get("bytes") != entry["bytes"] or saved.get("key") != entry["key"]):
            raise ValueError("Prior R2 receipt lacks matching full-readback closure")
        return saved
    result = transfer_file(client, bucket, cache / relative, entry)
    if result.get("verification") != FULL_GET or result.get("readback_bytes") != source["bytes"]:
        raise ValueError("R2 full GET closure required before source-cache eviction")
    result.update(source_official_md5_original=source["official_md5_original"],
                  source_official_md5_normalized_32hex=source["official_md5_normalized_32hex"],
                  source_file_id=source["record"]["id"], source_version="V4")
    immutable_json(target, result)
    return result


def run_closed(receipt: dict, sources: dict, remotes: dict) -> bool:
    if not receipt.get("closed") or not receipt.get("source_audit_integrity_pass"):
        return False
    for relative in receipt.get("source_relative_paths", []):
        source, remote = sources.get(relative, {}), remotes.get(relative, {})
        if (not source.get("official_size_and_md5_pass") or remote.get("verification") != FULL_GET
                or source.get("sha256") != remote.get("sha256")
                or source.get("bytes") != remote.get("readback_bytes")):
            return False
    return bool(receipt.get("source_relative_paths"))


def evict_signal(path: Path, source: dict, remote: dict, closure: dict) -> dict:
    if (path.suffix != ".eeg" or not source.get("cache_created_by_this_task")
            or not closure.get("closed") or not closure.get("source_audit_integrity_pass")
            or not source.get("official_size_and_md5_pass") or remote.get("verification") != FULL_GET
            or remote.get("sha256") != source.get("sha256")
            or remote.get("readback_bytes") != source.get("bytes")):
        raise ValueError("Cache eviction requires task ownership and complete source/R2 closure")
    checked = file_hashes(path)
    if checked["sha256"] != source["sha256"] or checked["bytes"] != source["bytes"]:
        raise ValueError("Local cache changed after closure; preserve it")
    result = {"evicted_at_utc": now(), "relative_path": source["relative_path"],
              "bytes": source["bytes"], "sha256": source["sha256"], "r2_key": remote["key"],
              "source_receipt_required": True, "full_get_sha256_receipt_required": True,
              "scope": "only new task-created large .eeg cache; metadata and prior results preserved"}
    path.unlink()
    return result


def aggregate(log: Path, records: list[dict]) -> dict:
    audits, events = [], []
    for path in sorted((log / "runs").glob("*/audit.json")):
        audits.append(load_json(path))
        events.extend(load_json(path.parent / "source_events.json"))
    summary = {"schema_version": 1, "created_at_utc": now(), "official_dataset_doi": "10.57760/sciencedb.34326",
               "paper_doi": "10.1038/s41597-026-07807-x", "release": "PUBLIC V4 / 4.0.0",
               "selected_file_count": len(records), "selected_bytes": sum(int(r["size"]) for r in records),
               "audited_runs": len(audits), "published_subject_ids": sorted({r["subject"] for r in audits}),
               "source_events": len(events), "mi_execution_events": sum(e["is_mi_execution_event"] for e in events),
               "all_audited_values_finite": all(r["all_values_finite"] for r in audits),
               "all_integrity_checks_pass": all(r["all_integrity_checks_pass"] for r in audits),
               "zero_channel_runs": [r["source_file"] for r in audits if r["zero_channels"]],
               "qualification_flags": {},
               "whole_signal_exact_copy_groups": duplicate_groups(audits, "whole_signal_numeric_sha256", "source_file"),
               "native_mi_interval_exact_copy_groups": duplicate_groups(events, "source_task_numeric_sha256", "event_id"),
               "independence_statement": "No checked exact copy is not proof of biological identity independence; published IDs remain source-specific",
               "license": {"official_repository_and_paper": "CC-BY-NC-4.0",
                           "BIDS_dataset_description": "CC BY 4.0", "conflict": "unresolved",
                           "operating_rule": "stricter noncommercial research with attribution; no unified license claim"},
               "design_boundary": "three runs in one visit, no longitudinal days/followup; direction pair confounded with acquisition half",
               "analysis_status": "complete source resource audit only; no model fits, participant tensor or human-learning claim"}
    from collections import Counter
    summary["qualification_flags"] = dict(Counter(f for e in events for f in e["qualification_flags"]))
    return summary


def archive_logs(client, bucket: str, cache: Path, log: Path) -> Path:
    # Freeze once so restart cannot silently change an immutable uploaded checkpoint.
    snapshot = log / "archive_snapshot"
    frozen = log / "archive_snapshot_frozen.json"
    if not frozen.exists():
        snapshot.mkdir(exist_ok=True)
        for folder in ["source_receipts", "r2_receipts", "runs", "evictions", "provenance",
                       "cache_ownership", "failures"]:
            if (log / folder).exists():
                shutil.copytree(log / folder, snapshot / folder, dirs_exist_ok=True)
        for name in ["plan.json", "state.json", "summary.json"]:
            if (log / name).exists():
                shutil.copy2(log / name, snapshot / name)
        immutable_json(frozen, {"frozen_at_utc": now(), "snapshot": "archive_snapshot"})
    closing = log / "archive_full_get_receipts.json"
    if not closing.exists():
        paths = sorted(p for p in snapshot.rglob("*") if p.is_file())
        def archive_file(path):
            hashes = file_hashes(path)
            relative = path.relative_to(snapshot).as_posix()
            entry = {"relative_path": relative, "key": f"{PREFIX}/audit/{relative}",
                     "sha256": hashes["sha256"], "bytes": hashes["bytes"],
                     "selected_for_full_readback": True, "status": "planned"}
            target = receipt_path(log, "archive_object_receipts", relative)
            if target.exists():
                result = load_json(target)
                if result.get("verification") != FULL_GET or result.get("sha256") != hashes["sha256"]:
                    raise ValueError("Archive resume requires matching full-GET receipt")
                return result
            result = transfer_file(client, bucket, path, entry)
            if result.get("verification") != FULL_GET:
                raise ValueError("Audit archive requires every full GET")
            immutable_json(target, result)
            return result
        receipts = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            for result in pool.map(archive_file, paths):
                receipts.append(result)
                if len(receipts) % 50 == 0 or len(receipts) == len(paths):
                    atomic_json(log / "archive_progress.json", {"completed": len(receipts),
                                                                "planned": len(paths)})
        immutable_json(closing, {"closed_at_utc": now(), "status": "closed", "files": receipts,
                                 "full_get_sha256_verified_files": len(receipts),
                                 "credential_values_logged": False})
    if not (log / "closing_receipt_r2_full_get.json").exists():
        hashes = file_hashes(closing)
        entry = {"relative_path": closing.name, "key": f"{PREFIX}/audit/{closing.name}",
                 "sha256": hashes["sha256"], "bytes": hashes["bytes"],
                 "selected_for_full_readback": True, "status": "planned"}
        immutable_json(log / "closing_receipt_r2_full_get.json",
                       transfer_file(client, bucket, closing, entry))
    return closing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--representative", type=Path)
    parser.add_argument("--representative-gate", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-runs", type=int, default=90)
    args = parser.parse_args()
    log, cache = args.log.absolute(), args.cache.absolute()
    log.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    safe_key_prefix(PREFIX)
    records = select_manifest(args.manifest)
    gate = load_json(args.representative_gate)
    if not gate.get("all_integrity_checks_pass") or not gate.get("all_values_finite"):
        raise ValueError("Representative full signal source audit must pass first")
    plan = {"created_at_utc": now(), "source_version": "V4", "source_doi": "10.57760/sciencedb.34326",
            "key_prefix": PREFIX, "selected_files": len(records),
            "selected_bytes": sum(int(r["size"]) for r in records), "eeg_signals": 90,
            "cache_policy": "one task-created signal at a time; all small metadata retained",
            "script_sha256": file_hashes(Path(__file__))["sha256"],
            "audit_script_sha256": file_hashes(Path(__file__).with_name("audit_mind_source.py"))["sha256"],
            "cache_bound_bytes": MAX_SIGNAL_BYTES, "full_get_for_every_object": True,
            "no_remote_overwrite": True, "credential_values_logged": False,
            "manifest_sha256": file_hashes(args.manifest)["sha256"],
            "source_git_commit": subprocess.run(["git", "rev-parse", "HEAD"], check=True,
                                                capture_output=True, text=True).stdout.strip(),
            "python_version": sys.version}
    if not (log / "plan.json").exists():
        immutable_json(log / "plan.json", plan)
        provenance = log / "provenance"
        provenance.mkdir()
        for script in [Path(__file__), Path(__file__).with_name("audit_mind_source.py")]:
            shutil.copy2(script, provenance / script.name)
        shutil.copy2(args.manifest, provenance / args.manifest.name)
        shutil.copy2(args.representative_gate, provenance / "representative_gate.json")
    else:
        prior = load_json(log / "plan.json")
        if prior["manifest_sha256"] != plan["manifest_sha256"] or prior["key_prefix"] != PREFIX:
            raise ValueError("Resume manifest or namespace differs from frozen plan")
    print(json.dumps({"status": "planned", "files": len(records), "eeg_signals": 90,
                      "bytes": plan["selected_bytes"]}), flush=True)
    if not args.execute:
        return 0
    started = time.monotonic()
    try:
        client, bucket, sdk = build_client()
        state = {"updated_at_utc": now(), "status": "metadata_downloading", "boto3_version": sdk,
                 "completed_runs": 0, "credential_values_logged": False}
        atomic_json(log / "state.json", state)
        metadata = [r for r in records if not r["path"].endswith("_eeg.eeg")]
        with ThreadPoolExecutor(max_workers=6) as pool:
            sources = list(pool.map(lambda r: ensure_source(r, cache, log, args.representative), metadata))
        lookup = {s["relative_path"]: s for s in sources}
        roots = [s for s in sources if "/" not in s["relative_path"]]
        for source in roots:
            upload_source(client, bucket, cache, log, source)
        signals = [r for r in records if r["path"].endswith("_eeg.eeg")]
        for run_index, signal in enumerate(signals[:args.max_runs], 1):
            relative = relative_path(signal)
            stem = relative.removesuffix("_eeg.eeg")
            run_name = Path(stem).name
            run_log = log / "runs" / run_name
            closure_path = run_log / "closed.json"
            run_relatives = [r for r in lookup if r.startswith(stem + "_")]
            subject_folder = PurePosixPath(relative).parent.as_posix()
            subject = PurePosixPath(relative).parts[0]
            run_relatives += [f"{subject_folder}/{subject}_coordsystem.json",
                              f"{subject_folder}/{subject}_electrodes.tsv"]
            all_relatives = [relative, *sorted(set(run_relatives))]
            if closure_path.exists():
                sources_known = {r: load_json(receipt_path(log, "source_receipts", r)) for r in all_relatives}
                remotes_known = {r: load_json(receipt_path(log, "r2_receipts", r)) for r in all_relatives}
                closure = load_json(closure_path)
                if not run_closed(closure, sources_known, remotes_known):
                    raise ValueError("Resume requires known matching source/audit/R2 full-GET closure")
                if (cache / relative).exists() and not receipt_path(log, "evictions", relative).exists():
                    eviction = evict_signal(cache / relative, sources_known[relative], remotes_known[relative], closure)
                    immutable_json(receipt_path(log, "evictions", relative), eviction)
                state.update(status="running", completed_runs=run_index, current_run=run_name,
                             updated_at_utc=now(), resumed_closed_run=True)
                atomic_json(log / "state.json", state)
                continue
            remaining = list(cache.rglob("*.eeg"))
            if remaining and any(p != cache / relative for p in remaining):
                raise ValueError("Another signal remains in bounded cache; preserve and stop")
            if shutil.disk_usage(cache).free < int(signal["size"]) + 1024 ** 3:
                raise ValueError("Insufficient disk for bounded signal plus 1GiB reserve")
            run_started = time.monotonic()
            state.update(status="source_downloading", current_run=run_name, updated_at_utc=now())
            atomic_json(log / "state.json", state)
            source = ensure_source(signal, cache, log, args.representative)
            lookup[relative] = source
            run_log.mkdir(parents=True, exist_ok=True)
            if (run_log / "audit.json").exists():
                audit = load_json(run_log / "audit.json")
                if audit.get("source_file_sha256") != source["sha256"]:
                    raise ValueError("Prior audit source digest differs; preserve both")
            else:
                audit, events = audit_run(cache, stem + "_eeg.vhdr")
                audit["source_file_sha256"] = source["sha256"]
                immutable_json(run_log / "audit.json", audit)
                immutable_json(run_log / "source_events.json", events)
            if not audit["all_integrity_checks_pass"]:
                raise ValueError("Native source event/annotation/marker alignment failed")
            remotes = {}
            for r in all_relatives:
                remotes[r] = upload_source(client, bucket, cache, log, lookup[r])
            closure = {"closed": True, "closed_at_utc": now(), "run_name": run_name,
                       "source_audit_integrity_pass": True, "source_relative_paths": all_relatives,
                       "all_sources_official_size_md5_pass": True, "all_objects_head_and_full_get_sha256_pass": True,
                       "elapsed_seconds": time.monotonic() - run_started,
                       "status": "completed", "files": [remotes[r] for r in all_relatives],
                       "totals": {"planned_files": len(all_relatives), "verified_files": len(all_relatives),
                                  "full_get_sha256_verified_files": len(all_relatives),
                                  "planned_bytes": sum(lookup[r]["bytes"] for r in all_relatives),
                                  "verified_bytes": sum(lookup[r]["bytes"] for r in all_relatives)}}
            immutable_json(closure_path, closure)
            eviction = evict_signal(cache / relative, source, remotes[relative], closure)
            immutable_json(receipt_path(log, "evictions", relative), eviction)
            state.update(status="running", completed_runs=run_index, current_run=run_name,
                         updated_at_utc=now(), elapsed_seconds=time.monotonic() - started)
            atomic_json(log / "state.json", state)
            print(json.dumps({"completed_runs": run_index, "total_runs": 90, "run": run_name,
                              "seconds_this_run": round(closure["elapsed_seconds"], 2),
                              "source_bytes": source["bytes"], "full_get_verified": True,
                              "cache_evicted": True}), flush=True)
        if args.max_runs < 90:
            state.update(status="bounded_requested_stage_closed", updated_at_utc=now())
            atomic_json(log / "state.json", state)
            return 0
        summary = aggregate(log, records)
        if not (log / "summary.json").exists():
            immutable_json(log / "summary.json", summary)
        state.update(status="all_runs_closed_archiving_audits", updated_at_utc=now())
        atomic_json(log / "state.json", state)
        archive_logs(client, bucket, cache, log)
        state.update(status="completed", completed_runs=90, updated_at_utc=now(),
                     total_elapsed_seconds=time.monotonic() - started)
        atomic_json(log / "state.json", state)
        print(json.dumps({"status": "completed", "runs": 90, "events": summary["source_events"]}), flush=True)
        return 0
    except Exception as error:
        failure = {"failed_at_utc": now(), "status": "failed_preserved_cache", "error_type": type(error).__name__,
                   "error_code": error_code(error), "credential_values_logged": False,
                   "exception_message_logged": False, "partial_or_signal_deleted": False}
        atomic_json(log / "state.json", {**locals().get("state", {}), **failure})
        immutable_json(log / "failures" / f"{time.time_ns()}.json", failure)
        print(json.dumps(failure), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
