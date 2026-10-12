#!/usr/bin/env python3
"""Pinned PhysioNet hand-imagery subset: metadata plan, verified fetch, signal census.

The 109 participants' runs 04/08/12 are imagery of opening/closing the left or
right fist. No execution/both-hand/foot runs, epoch padding, training, pooling,
behavioral scores, or retention endpoints are introduced by this script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PREFIX = "https://physionet.org/files/eegmmidb/1.0.0/"
ARCHIVE_PREFIX = "https://archive.physionet.org/physiobank/database/eegmmidb/"
METADATA_ROOT = REPO_ROOT / "research_logs/public_data_expansion_20261010/large_training_metadata"
LOG_ROOT = REPO_ROOT / "research_logs/public_data_expansion_20261010/physionet_eegmmidb"
DATA_ROOT = REPO_ROOT / "data/public_eeg/physionet_eegmmidb/1.0.0"
METADATA_HASHES = {
    "physionet_records.txt": "02d1de9c00511d3b7548a6b59bdf209c819db025518ddcc52b21fd3b2b9de4a8",
    "physionet_sha256sums.txt": "7f5d16957d8ee7bce86cc7ccba0e5994f63f33781607eb3f838392d49311a208",
    "physionet_license.html": "384d5752e897c6da4d220ce6b729a1e33185eb6a7565a23b346d1ff414e3eb2e",
}
PATH_PATTERN = re.compile(r"(S\d{3})/\1R(04|08|12)\.edf(?:\.event)?")
TASK_LABELS = {"T0": "rest", "T1": "left_hand_imagery", "T2": "right_hand_imagery"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_new(path: Path, value: dict) -> None:
    """Preserve existing receipts, including incomplete or failed attempts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def source_selection(metadata_root: Path = METADATA_ROOT) -> list[dict]:
    for name, expected in METADATA_HASHES.items():
        if sha256(metadata_root / name) != expected:
            raise ValueError(f"Pinned source metadata changed: {name}")
    records = (metadata_root / "physionet_records.txt").read_text().splitlines()
    hashes = {}
    for line in (metadata_root / "physionet_sha256sums.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name in hashes:
            raise ValueError(f"Duplicate official checksum entry: {name}")
        hashes[name] = digest
    expected_records = {f"S{s:03d}/S{s:03d}R{r:02d}.edf"
                        for s in range(1, 110) for r in (4, 8, 12)}
    selected = [name for name in records if PATH_PATTERN.fullmatch(name)]
    if len(selected) != 327 or set(selected) != expected_records:
        raise ValueError("Official RECORDS does not contain the exact 109-by-3 imagery subset")
    entries = []
    for name in sorted(expected_records):
        for path in (name, name + ".event"):
            if path not in hashes or not re.fullmatch(r"[0-9a-f]{64}", hashes[path]):
                raise ValueError(f"Official SHA256SUMS lacks a valid checksum: {path}")
            entries.append({"path": path, "url": SOURCE_PREFIX + path,
                            "sha256": hashes[path], "subject": path[:4],
                            "run": int(path[10:12]),
                            "type": "edf" if path.endswith(".edf") else "wfdb_event"})
    return entries


def checked_entry(entry: dict) -> dict:
    match = PATH_PATTERN.fullmatch(entry["path"])
    if match is None or not 1 <= int(match.group(1)[1:]) <= 109:
        raise ValueError("Manifest path is outside the pinned hand-imagery subset")
    if entry["url"] != SOURCE_PREFIX + entry["path"]:
        raise ValueError("Manifest URL is not the canonical pinned PhysioNet URL")
    if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
        raise ValueError("Invalid official SHA256")
    if type(entry["size"]) is not int or entry["size"] <= 0:
        raise ValueError("Invalid official HEAD content length")
    identity = {"subject": match.group(1), "run": int(match.group(2)),
                "type": "edf" if entry["path"].endswith(".edf") else "wfdb_event"}
    if any(key in entry and entry[key] != value for key, value in identity.items()):
        raise ValueError("Manifest identity disagrees with the official relative path")
    return entry


def prepare_manifest(output: Path, workers: int) -> None:
    entries = source_selection()

    def probe(entry: dict) -> dict:
        response = requests.head(entry["url"], timeout=(20, 45), allow_redirects=False)
        try:
            if response.status_code != 200:
                raise ValueError(f"Official HEAD status {response.status_code}: {entry['path']}")
            size = response.headers.get("Content-Length", "")
            if not size.isdigit() or int(size) <= 0:
                raise ValueError(f"Official HEAD has no exact positive size: {entry['path']}")
            return checked_entry({**entry, "size": int(size), "head_status": 200})
        finally:
            response.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        sized = list(pool.map(probe, entries))
    save_new(output, {"prepared_at_utc": now(), "version": "1.0.0",
                      "dataset": "PhysioNet EEG Motor Movement/Imagery Database",
                      "license": "ODC-By-1.0", "subject_count": 109, "edf_count": 327,
                      "task": "left/right fist motor imagery; source rest retained",
                      "selection": "only original source runs 04, 08, 12",
                      "source_metadata_sha256": METADATA_HASHES,
                      "total_bytes": sum(e["size"] for e in sized), "files": sized})


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if (manifest.get("version") != "1.0.0" or manifest.get("license") != "ODC-By-1.0"
            or manifest.get("subject_count") != 109 or manifest.get("edf_count") != 327):
        raise ValueError("Manifest version, license or advertised subset count changed")
    expected = {e["path"]: e for e in source_selection()}
    entries = manifest["files"]
    if len(entries) != 654 or {e["path"] for e in entries} != set(expected):
        raise ValueError("Manifest is not the exact 327 EDF plus 327 official annotations")
    for entry in entries:
        checked_entry(entry)
        if entry["sha256"] != expected[entry["path"]]["sha256"]:
            raise ValueError("Manifest checksum disagrees with pinned official SHA256SUMS")
    if manifest["total_bytes"] != sum(e["size"] for e in entries):
        raise ValueError("Manifest total size disagrees with entries")
    return manifest


def destination(root: Path, name: str) -> Path:
    target = root / name
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Destination escapes the data root")
    if root.is_symlink() or any(p.is_symlink() for p in (target, *target.parents)
                                if p == root or p.is_relative_to(root)):
        raise ValueError("Symlinks are not valid data destinations")
    return target


def fetch_file(root: Path, entry: dict, *, session_factory=requests.Session,
               transport: str = "canonical") -> dict:
    checked_entry(entry)
    if transport not in ("canonical", "official_archive"):
        raise ValueError("Transport is outside the two official PhysioNet hosts")
    transport_url = entry["url"] if transport == "canonical" else ARCHIVE_PREFIX + entry["path"]
    target = destination(root, entry["path"])
    if target.exists():
        if target.stat().st_size != entry["size"] or sha256(target) != entry["sha256"]:
            raise ValueError(f"Existing file mismatches official checksum: {entry['path']}")
        return {**entry, "status": "reused_verified", "transferred_bytes": 0}
    target.parent.mkdir(parents=True, exist_ok=True)
    attempts = []
    invocation = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for attempt in range(1, 3):
        temporary = target.with_name(target.name + f".{invocation}.attempt{attempt}.part")
        try:
            if temporary.exists():
                raise ValueError(f"Prior partial download retained: {temporary.name}")
            with session_factory() as session:
                response = session.get(transport_url, stream=True, timeout=(20, 60),
                                       allow_redirects=False)
                try:
                    if response.status_code != 200:
                        raise ValueError(f"HTTP status {response.status_code}")
                    if response.headers.get("Content-Length") != str(entry["size"]):
                        raise ValueError("HTTP body content length differs from pinned HEAD")
                    digest = hashlib.sha256()
                    count = 0
                    with temporary.open("xb") as stream:
                        for block in response.iter_content(chunk_size=1024 * 1024):
                            count += len(block)
                            if count > entry["size"]:
                                raise ValueError("Body exceeds the declared length")
                            stream.write(block)
                            digest.update(block)
                    if count != entry["size"] or digest.hexdigest() != entry["sha256"]:
                        raise ValueError("Downloaded size or official SHA256 mismatch")
                finally:
                    response.close()
            temporary.rename(target)
            return {**entry, "status": "downloaded_verified", "attempts": attempts,
                    "transferred_bytes": count, "actual_sha256": digest.hexdigest(),
                    "actual_transport_url": transport_url}
        except (requests.RequestException, ValueError, OSError) as error:
            attempts.append({"attempt": attempt, "error": str(error),
                             "partial_file": str(temporary.relative_to(root)),
                             "partial_bytes": temporary.stat().st_size if temporary.exists() else 0})
            if attempt == 1:
                time.sleep(1)
    return {**entry, "status": "failed", "attempts": attempts}


def fetch_manifest(manifest: dict, root: Path, output: Path, workers: int,
                   transport: str = "canonical") -> None:
    root.mkdir(parents=True, exist_ok=True)
    required = manifest["total_bytes"] + 512 * 1024 * 1024
    if shutil.disk_usage(root).free < required:
        raise ValueError("Insufficient disk space for pinned subset plus 512 MiB reserve")
    results = []

    def fetch_safely(entry: dict) -> dict:
        try:
            return fetch_file(root, entry, transport=transport)
        except (ValueError, OSError) as error:
            return {**entry, "status": "failed", "attempts": [], "error": str(error)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(fetch_safely, manifest["files"]):
            results.append(result)
            if len(results) % 50 == 0:
                print(f"verified {len(results)}/{len(manifest['files'])} files", flush=True)
    failures = [r for r in results if r["status"] == "failed"]
    save_new(output, {"completed_at_utc": now(), "all_verified": not failures,
                      "transport": transport,
                      "version_identity": "official v1.0.0 SHA256SUMS and exact canonical HEAD lengths",
                      "manifest_sha256": hashlib.sha256(
                          json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
                      "manifest_digest_convention": "JSON sorted keys, default separators",
                      "script_sha256": sha256(Path(__file__)),
                      "verified_file_count": len(results) - len(failures),
                      "verified_bytes": sum(r["size"] for r in results
                                            if r["status"] != "failed"),
                      "files": results, "failure_count": len(failures)})
    if failures:
        raise ValueError(f"{len(failures)} files failed; complete receipt and partial bytes retained")


def compare_sidecar_annotations(onsets, durations, labels, samples, notes, symbols, sfreq):
    """Verify source annotation agreement without manufacturing a WFDB onset-zero event.

    The observed official WFDB files omit the initial EDF T0 segment at zero.
    Permit that one explicit difference, or complete equality, and reject all
    other identities, durations and timing discrepancies.
    """
    if len(onsets) != len(durations) or len(onsets) != len(labels):
        raise ValueError("EDF annotation axes differ")
    if len(samples) != len(notes) or len(samples) != len(symbols):
        raise ValueError("WFDB annotation axes differ")
    expected = list(zip(onsets, durations, labels, strict=True))
    omitted = []
    if (len(expected) == len(samples) + 1 and expected
            and abs(float(expected[0][0])) < 0.5 / sfreq
            and str(expected[0][2]) == "T0" and float(expected[0][1]) > 0):
        omitted = [{"edf_annotation_index": 0, "onset_seconds": float(expected[0][0]),
                    "duration_seconds": float(expected[0][1]), "source_label": "T0"}]
        expected = expected[1:]
    if len(expected) != len(samples):
        raise ValueError("WFDB/EDF annotation counts differ beyond the initial zero-onset T0")
    for (onset, duration, label), sample, note, symbol in zip(
            expected, samples, notes, symbols, strict=True):
        match = re.fullmatch(r"(T[012]) duration: (\d+(?:\.\d+)?)", note)
        if match is None or symbol != '"':
            raise ValueError("Unexpected WFDB source annotation syntax or symbol")
        if (match.group(1) != str(label)
                or abs(float(sample) / sfreq - float(onset)) > 0.5 / sfreq
                or abs(float(match.group(2)) - float(duration)) > 0.5 / sfreq):
            raise ValueError("WFDB/EDF source label, onset or duration mismatch")
    return {"sidecar_annotation_count": len(samples),
            "edf_annotation_count": len(onsets), "all_nonzero_edf_annotations_match": True,
            "edf_zero_onset_rest_missing_from_sidecar": omitted,
            "no_missing_event_was_invented": True}


def annotation_difference_inventory(onsets, durations, labels, samples, notes, symbols, sfreq):
    """Describe unmatched source identities; never fill, relabel or fix any stream."""
    matched_edf = set()
    unmatched_wfdb = []
    for index, (sample, note, symbol) in enumerate(zip(samples, notes, symbols, strict=True)):
        match = re.fullmatch(r"(T[012]) duration: (\d+(?:\.\d+)?)", note)
        candidates = []
        if match is not None and symbol == '"':
            candidates = [i for i, (onset, duration, label) in enumerate(
                zip(onsets, durations, labels, strict=True))
                if i not in matched_edf and str(label) == match.group(1)
                and abs(float(onset) - int(sample) / sfreq) <= 0.5 / sfreq
                and abs(float(duration) - float(match.group(2))) <= 0.5 / sfreq]
        if len(candidates) == 1:
            matched_edf.add(candidates[0])
        else:
            unmatched_wfdb.append({"wfdb_annotation_index": index, "sample": int(sample),
                                   "original_aux_note": note, "symbol": symbol})
    unmatched_edf = [{"edf_annotation_index": i, "onset_seconds": float(onset),
                      "duration_seconds": float(duration), "source_label": str(label)}
                     for i, (onset, duration, label) in enumerate(
                         zip(onsets, durations, labels, strict=True)) if i not in matched_edf]
    missing_nonzero = [r for r in unmatched_edf
                       if not (r["edf_annotation_index"] == 0 and r["onset_seconds"] == 0
                               and r["source_label"] == "T0")]
    return {"matched_annotation_count": len(matched_edf),
            "unmatched_edf_annotations": unmatched_edf,
            "unmatched_wfdb_annotations": unmatched_wfdb,
            "missing_nonzero_edf_annotation_count": len(missing_nonzero),
            "missing_nonzero_edf_annotation_counts_by_label": {
                label: sum(r["source_label"] == label for r in missing_nonzero)
                for label in TASK_LABELS},
            "comparison_clock_hz": sfreq, "source_streams_modified": False}


def audit_signals(manifest: dict, root: Path, output: Path) -> None:
    """Read every source sample and annotation without creating analysis epochs."""
    import mne
    import numpy as np
    import wfdb

    output.mkdir(parents=True, exist_ok=False)
    signals, annotations, sidecar_annotations, annotation_disagreements, failures = [], [], [], [], []
    for entry in manifest["files"]:
        if entry["type"] != "edf":
            continue
        try:
            path = destination(root, entry["path"])
            if path.stat().st_size != entry["size"] or sha256(path) != entry["sha256"]:
                raise ValueError("Local signal fails pinned official checksum")
            raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
            try:
                sfreq = float(raw.info["sfreq"])
                duration = raw.n_times / sfreq
                sidecar_entry = next(e for e in manifest["files"]
                                     if e["path"] == entry["path"] + ".event")
                sidecar_path = destination(root, sidecar_entry["path"])
                if (sidecar_path.stat().st_size != sidecar_entry["size"]
                        or sha256(sidecar_path) != sidecar_entry["sha256"]):
                    raise ValueError("Local annotation sidecar fails pinned official checksum")
                sidecar = wfdb.rdann(str(path), "event")
                annotation_error = None
                try:
                    if sidecar.fs != sfreq:
                        raise ValueError("WFDB source clock differs from EDF clock")
                    sidecar_agreement = compare_sidecar_annotations(
                        raw.annotations.onset, raw.annotations.duration,
                        raw.annotations.description, sidecar.sample, sidecar.aux_note,
                        sidecar.symbol, sfreq)
                except ValueError as error:
                    annotation_error = str(error)
                    sidecar_agreement = {
                        "sidecar_annotation_count": len(sidecar.sample),
                        "edf_annotation_count": len(raw.annotations),
                        "all_nonzero_edf_annotations_match": False,
                        "strict_comparison_error": annotation_error,
                        "no_missing_event_was_invented": True,
                        **annotation_difference_inventory(
                            raw.annotations.onset, raw.annotations.duration,
                            raw.annotations.description, sidecar.sample, sidecar.aux_note,
                            sidecar.symbol, sfreq),
                    }
                    annotation_disagreements.append({"path": entry["path"],
                        "edf_sampling_rate_hz": sfreq, "wfdb_sampling_rate_hz": sidecar.fs,
                        **sidecar_agreement,
                        "fixed_4s_training_availability": "unavailable_pending_source_resolution"})
                for index, (sample, note, symbol) in enumerate(zip(
                        sidecar.sample, sidecar.aux_note, sidecar.symbol, strict=True)):
                    sidecar_annotations.append({"source_file": entry["path"] + ".event",
                        "subject": entry["subject"], "run": entry["run"],
                        "source_annotation_index": index, "sample": int(sample),
                        "sampling_rate_hz": sidecar.fs,
                        "onset_seconds": None if not sidecar.fs else int(sample) / sidecar.fs,
                        "symbol": symbol, "original_aux_note": note})
                digest = hashlib.sha256()
                peak_v = 0.0
                channel_square_sum = np.zeros(len(raw.ch_names))
                for start in range(0, raw.n_times, 4096):
                    data = raw.get_data(start=start, stop=min(start + 4096, raw.n_times))
                    if not np.isfinite(data).all():
                        raise ValueError("Nonfinite source signal")
                    # Time-major bytes make the digest independent of read chunk size.
                    digest.update(np.asarray(data.T, dtype="<f8").tobytes(order="C"))
                    peak_v = max(peak_v, float(np.abs(data).max()))
                    channel_square_sum += (data * data).sum(axis=1)
                flags = []
                if annotation_error:
                    flags.append("EDF_WFDB_annotation_disagreement_pending_source_resolution")
                if sfreq != 160.0:
                    flags.append("sampling_rate_differs_from_advertised_160Hz")
                if len(raw.ch_names) != 64:
                    flags.append("channel_count_differs_from_advertised_64")
                if set(raw._orig_units.values()) != {"µV"}:
                    flags.append("original_unit_differs_from_microvolts")
                labels = {}
                last_end = 0.0
                for index, (onset, length, label) in enumerate(zip(
                        raw.annotations.onset, raw.annotations.duration,
                        raw.annotations.description, strict=True)):
                    notes = []
                    if annotation_error:
                        notes.append("EDF_WFDB_annotation_disagreement_pending_source_resolution")
                    if label not in TASK_LABELS:
                        notes.append("unknown_annotation_label")
                    if onset < -1 / sfreq or onset + length > duration + 1 / sfreq:
                        notes.append("annotation_outside_signal")
                    if length <= 0:
                        notes.append("nonpositive_annotation_duration")
                    if onset < last_end - 1 / sfreq:
                        notes.append("overlapping_annotations")
                    last_end = float(onset + length)
                    labels[str(label)] = labels.get(str(label), 0) + 1
                    annotations.append({"source_file": entry["path"],
                                        "subject": entry["subject"], "run": entry["run"],
                                        "source_annotation_index": index,
                                        "onset_seconds": float(onset),
                                        "duration_seconds": float(length),
                                        "source_label": str(label),
                                        "task": TASK_LABELS.get(str(label), "unknown"),
                                        "complete_4s_window_available": bool(
                                            label in ("T1", "T2") and not notes
                                            and length >= 4.0
                                            and onset + 4.0 <= duration + 0.5 / sfreq),
                                        "flags": ";".join(notes)})
                    flags.extend(notes)
                record = {"path": entry["path"], "subject": entry["subject"],
                          "run": entry["run"], "official_sha256": entry["sha256"],
                          "signal_content_sha256": digest.hexdigest(),
                          "content_digest_convention": "time-major little-endian float64 volts",
                          "n_samples": int(raw.n_times), "sampling_rate_hz": sfreq,
                          "n_channels": len(raw.ch_names), "channel_order": raw.ch_names,
                          "original_units": raw._orig_units,
                          "mne_signal_unit": "V", "duration_seconds": duration,
                          "all_samples_finite": True, "peak_absolute_V": peak_v,
                          "channel_rms_V": np.sqrt(channel_square_sum / raw.n_times).tolist(),
                          "official_sidecar_sha256": sidecar_entry["sha256"],
                          "sidecar_annotation_agreement": sidecar_agreement,
                          "annotation_counts": labels, "flags": sorted(set(flags))}
                signals.append(record)
            finally:
                raw.close()
        except (OSError, ValueError, RuntimeError) as error:
            failures.append({"path": entry["path"], "error": str(error)})
        if len(signals) % 30 == 0:
            print(f"read {len(signals)}/327 EEG files; failures={len(failures)}", flush=True)
    duplicate_groups = []
    for key in ("official_sha256", "signal_content_sha256"):
        groups = {}
        for row in signals:
            # Same float values only count as same signal under identical axes.
            identity = (row[key], row["sampling_rate_hz"], tuple(row["channel_order"]))
            groups.setdefault(identity, []).append(row["path"])
        duplicate_groups.extend({"method": key, "files": files}
                                for files in groups.values() if len(files) > 1)
    for group in duplicate_groups:
        for row in signals:
            if row["path"] in group["files"]:
                row["flags"] = sorted(set(row["flags"] + ["duplicate_complete_source_signal"]))
    counts = {label: sum(r["source_label"] == label for r in annotations)
              for label in TASK_LABELS}
    duration_histograms = {}
    for label in TASK_LABELS:
        histogram = {}
        for row in annotations:
            if row["source_label"] == label:
                value = str(row["duration_seconds"])
                histogram[value] = histogram.get(value, 0) + 1
        duration_histograms[label] = histogram
    summary = {"completed_at_utc": now(), "synthetic": False, "analysis_status": "source_audit_only",
               "dataset": manifest["dataset"], "version": manifest["version"],
               "license": manifest["license"],
               "manifest_sha256": hashlib.sha256(
                   json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
               "manifest_digest_convention": "JSON sorted keys, default separators",
               "official_source_metadata_sha256": METADATA_HASHES,
               "script_sha256": sha256(Path(__file__)),
               "manifest_subject_count": 109,
               "read_subject_count": len({r["subject"] for r in signals}),
               "read_signal_count": len(signals), "source_annotation_count": len(annotations),
               "source_annotation_counts": counts,
               "source_duration_histograms_seconds": duration_histograms,
               "sidecar_annotation_count": sum(r["sidecar_annotation_agreement"][
                   "sidecar_annotation_count"] for r in signals),
               "annotation_integrity_disagreements": annotation_disagreements,
               "source_disagreement_policy": "retain both official annotation streams and all signal samples; no event repair, no signal resampling, no training approval for disagreeing source files",
               "all_nonzero_edf_annotations_match_official_sidecars": all(
                   r["sidecar_annotation_agreement"]["all_nonzero_edf_annotations_match"]
                   for r in signals),
               "fixed_4s_hand_imagery_inventory": {
                   "meaning": "source-window availability census only; no epochs or training inclusion",
                   "available_event_count": sum(r["complete_4s_window_available"]
                                                for r in annotations),
                   "unavailable_hand_imagery_events": [r for r in annotations
                       if r["source_label"] in ("T1", "T2")
                       and not r["complete_4s_window_available"]],
               },
               "sampling_rates_hz": sorted({r["sampling_rate_hz"] for r in signals}),
               "channel_counts": sorted({r["n_channels"] for r in signals}),
               "identical_channel_order": len({tuple(r["channel_order"]) for r in signals}) == 1,
               "duplicate_signal_groups": duplicate_groups, "failures": failures,
               "resource_audit_status": (
                   "incomplete_signal_read" if failures or len(signals) != 327 else
                   "complete_with_source_flags" if annotation_disagreements
                   or any(r["flags"] for r in signals) else "complete_without_source_flags"),
               "source_qualification": {
                   "definition": "full-source finite/SHA256/unit/64-channel/160Hz/annotation-integrity/boundary gates; resource eligibility only, model approval remains unset",
                   "pass_eligible_files": [r["path"] for r in signals if not r["flags"]],
                   "pass_eligible_file_count": sum(not r["flags"] for r in signals),
                   "pass_eligible_4s_event_count": sum(r["complete_4s_window_available"]
                       for r in annotations if r["source_file"] in {
                           f["path"] for f in signals if not f["flags"]}),
                   "pass_eligible_any_run_subjects": sorted({r["subject"] for r in signals
                                                             if not r["flags"]}),
                   "pass_eligible_all_three_run_subjects": sorted({r["subject"] for r in signals
                       if len([f for f in signals if f["subject"] == r["subject"]
                               and not f["flags"]]) == 3}),
                   "unqualified_files": [{"path": r["path"], "subject": r["subject"],
                       "run": r["run"], "sampling_rate_hz": r["sampling_rate_hz"],
                       "flags": r["flags"]} for r in signals if r["flags"]],
                   "handling_of_unqualified_files": "all official source bytes retained; source resolution/selection for later models remains undecided",
                   "model_training_performed": False,
               },
               "flagged_signals": [{"path": r["path"], "flags": r["flags"]}
                                   for r in signals if r["flags"]],
               "flagged_annotations": [r for r in annotations if r["flags"]],
               "exclusions": [], "new_epochs_created": False,
               "scope": "single-session imagery resource; not longitudinal human retention evidence",
               "runtime": {"mne": mne.__version__, "numpy": np.__version__,
                           "wfdb": wfdb.__version__},
               "files": signals}
    save_new(output / "signal_audit.json", summary)
    if annotations:
        with (output / "source_annotations.tsv").open("x") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(annotations[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(annotations)
    if sidecar_annotations:
        with (output / "source_wfdb_annotations.tsv").open("x") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(sidecar_annotations[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(sidecar_annotations)
    if failures or len(signals) != 327:
        raise ValueError("Incomplete source signal audit; failure records retained")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "download", "audit"))
    parser.add_argument("--manifest", type=Path, default=LOG_ROOT / "selection_manifest.json")
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--transport", choices=("canonical", "official_archive"),
                        default="canonical", help="Download host only; official pinned hashes are unchanged")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare_manifest(args.manifest, args.workers)
        print(f"Pinned metadata-only selection saved: {args.manifest}")
        return
    manifest = load_manifest(args.manifest)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if args.action == "download":
        output = args.output or LOG_ROOT / f"download_receipt_{stamp}.json"
        fetch_manifest(manifest, args.data_root, output, args.workers, args.transport)
    else:
        output = args.output or LOG_ROOT / f"audit_{stamp}"
        audit_signals(manifest, args.data_root, output)
    print(f"Completed {args.action}: {output}", flush=True)


if __name__ == "__main__":
    main()
