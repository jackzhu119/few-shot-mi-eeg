#!/usr/bin/env python3
"""Audit pinned Leeuwis2021 concatenated trial EEG, preserving source boundaries.

This is resource acceptance, not model training or evidence of human learning.
Every sample is scanned in bounded blocks; no NETBCI window rule is applied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

from fetch_nemar_subset import digest_file, load_selection, safe_destination, write_immutable

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANNELS = (
    "F3", "Fz", "F4", "FC5", "FC1", "FC2", "FC6", "T7", "C3", "C4", "Cz", "T8",
    "CP5", "CP1", "CP2", "CP6",
)
STORED_CODES = {"EDGE boundary": 1, "left_hand": 2, "right_hand": 3}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def validate_events(rows: list[dict], *, sfreq: float, n_times: int) -> list[dict]:
    """Retain task and EDGE rows, and check each task against its stored segment."""
    require(sfreq == 250.0 and n_times > 0, "Unexpected pinned source sampling rate or length")
    n_times = int(n_times)
    require(bool(rows), "Empty source event table")
    starts, ends, labels = [], [], []
    durations, onsets = [], []
    for row in rows:
        label = row["trial_type"]
        require(label in STORED_CODES and int(row["value"]) == STORED_CODES[label],
                "Source label/code mapping differs from verified derivative")
        onset, duration = float(row["onset"]), float(row["duration"])
        require(np.isfinite(onset) and np.isfinite(duration) and duration >= 0,
                "Nonfinite or negative source event time")
        start = int(row["sample"])
        require(abs(onset * sfreq - start) <= 1e-6, "Event onset/sample identity mismatch")
        length = int(round(duration * sfreq))
        require(abs(duration * sfreq - length) <= 1e-6,
                "Source duration is not aligned to samples")
        require(0 <= start < n_times and start + length <= n_times,
                "Source event outside EDF sample boundary")
        require((label == "EDGE boundary" and length == 0)
                or (label != "EDGE boundary" and length > 0),
                "EDGE must have zero duration; task event must have positive duration")
        starts.append(start)
        ends.append(start + length)
        labels.append(label)
        durations.append(duration)
        onsets.append(onset)
    require(all(a < b for a, b in zip(starts, starts[1:])),
            "Source rows unordered or share a sample identity")
    edges = [start for start, label in zip(starts, labels) if label == "EDGE boundary"]
    boundaries = [0, *edges, n_times]
    task_indices = [i for i, label in enumerate(labels) if label != "EDGE boundary"]
    require(len(task_indices) == len(boundaries) - 1,
            "Concatenated segments and task events are not one-to-one")
    events = []
    task_number = 0
    for index, (start, end, label) in enumerate(zip(starts, ends, labels)):
        item = {"source_row": index + 1, "label": label, "stored_value": STORED_CODES[label],
                "onset_seconds": onsets[index], "duration_seconds": durations[index],
                "start_sample": start, "stop_sample_exclusive": end,
                "source_duration_sample_count": end - start,
                "event_kind": "boundary" if label == "EDGE boundary" else "motor_imagery",
                "analysis_eligibility": "not_selected_no_model_window_policy_yet"}
        if label != "EDGE boundary":
            segment_start, segment_end = boundaries[task_number:task_number + 2]
            require(segment_start <= start < end <= segment_end,
                    "Task event crosses a concatenated-trial EDGE boundary")
            item.update(trial_number_in_run=task_number + 1,
                        segment_start_sample=segment_start,
                        segment_stop_sample_exclusive=segment_end,
                        cue_sample_within_segment=start - segment_start,
                        segment_sample_count=segment_end - segment_start,
                        samples_after_source_event=segment_end - end)
            task_number += 1
        events.append(item)
    return events


def scan_numeric(raw) -> dict:
    """Full chronological block scan in MNE volts; exact duplicate fingerprints."""
    digest = hashlib.sha256()
    minima = np.full(len(raw.ch_names), np.inf)
    maxima = np.full(len(raw.ch_names), -np.inf)
    square_sum, count = 0.0, 0
    for start in range(0, raw.n_times, 16384):
        data = raw.get_data(start=start, stop=min(start + 16384, raw.n_times))
        require(np.isfinite(data).all(), "Nonfinite continuous EEG sample")
        digest.update(np.asarray(data, dtype="<f8").tobytes(order="C"))
        minima = np.minimum(minima, data.min(axis=1))
        maxima = np.maximum(maxima, data.max(axis=1))
        square_sum += float(np.square(data).sum())
        count += data.size
    center = max(0, int(raw.n_times) // 2 - 128)
    sample = raw.get_data(picks=[0, 1], start=center, stop=center + 256)
    require(sample.shape == (2, 256), "Insufficient length for central 4 KiB fingerprint")
    return {"all_continuous_samples_finite": True, "continuous_numeric_values": count,
            "whole_signal_numeric_sha256": digest.hexdigest(),
            "whole_signal_hash_convention": "all16 channels; float64 little-endian C-order; "
            "16384-sample chronological blocks; MNE volts",
            "central_4KiB_numeric_sha256": hashlib.sha256(
                np.asarray(sample, dtype="<f8").tobytes(order="C")).hexdigest(),
            "central_fingerprint_start_sample": center,
            "central_fingerprint_convention": "first2 channels x256 central samples; "
            "float64 little-endian C-order; MNE volts",
            "peak_absolute_volts": float(max(abs(minima.min()), abs(maxima.max()))),
            "global_rms_volts": float(np.sqrt(square_sum / count)),
            "flatline_channel_names": [name for name, low, high in zip(
                raw.ch_names, minima, maxima) if low == high]}


def audit_run(root: Path, relative: str, entries: dict) -> tuple[dict, list[dict]]:
    match = re.fullmatch(r"(sub-\d+)/(ses-0)/eeg/\1_\2_task-imagery_"
                         r"acq-(calib|feedback[123])_(run-[0123])_eeg.edf", relative)
    require(match is not None, "Unexpected pinned run filename identity")
    subject, session, acquisition, run = match.groups()
    require({"calib": "run-0", "feedback1": "run-1", "feedback2": "run-2",
             "feedback3": "run-3"}[acquisition] == run, "Acquisition/run identity mismatch")
    prefix = relative.removesuffix("_eeg.edf")
    verified = {}

    def verify(name: str) -> Path:
        require(name in entries, f"Required source sidecar missing: {name}")
        path = safe_destination(root, name)
        digest, sha256, count = digest_file(path, entries[name])
        require(digest == entries[name]["checksum"] and count == entries[name]["size"],
                f"Official checksum/length mismatch: {name}")
        verified[name] = {"actual_sha256": sha256, "official_checksum": digest,
                          "official_algorithm": entries[name]["checksum_algorithm"],
                          "bytes": count}
        return path

    signal = verify(relative)
    metadata = json.loads(verify(prefix + "_eeg.json").read_text())
    events_metadata = json.loads(verify(prefix + "_events.json").read_text())
    rows = read_tsv(verify(prefix + "_events.tsv"))
    channels = read_tsv(verify(prefix + "_channels.tsv"))
    require(events_metadata["onset"]["Units"] == events_metadata["duration"]["Units"] == "s",
            "Source event seconds units unspecified")
    require("First sample is 0" in events_metadata["sample"]["Description"],
            "Zero-based source sample indices unspecified")
    raw = mne.io.read_raw_edf(signal, preload=False, verbose="ERROR")
    try:
        require(raw.first_samp == 0 and raw.info["sfreq"] == metadata["SamplingFrequency"] == 250,
                "EDF sample origin/rate differs from source metadata")
        require(tuple(raw.ch_names) == tuple(c["name"] for c in channels) == CHANNELS,
                "Pinned channel order or expected16 channels differs")
        require(metadata["EEGChannelCount"] == 16 and raw.get_channel_types() == ["eeg"] * 16,
                "Expected EEG channel types/count differs")
        require(all(c["type"] == "EEG" and float(c["sampling_frequency"]) == 250
                    and c["units"] == raw._orig_units[c["name"]] == "µV" for c in channels),
                "Physical EDF/sidecar units or channel rates differ")
        events = validate_events(rows, sfreq=250, n_times=raw.n_times)
        require(len(raw.annotations) == len(events)
                and list(raw.annotations.description) == [e["label"] for e in events]
                and np.allclose(raw.annotations.onset, [e["onset_seconds"] for e in events],
                                rtol=0, atol=1e-6)
                and np.allclose(raw.annotations.duration, [e["duration_seconds"] for e in events],
                                rtol=0, atol=1e-6), "EDF annotation and source TSV differ")
        for event in events:
            event.update(dataset="Leeuwis2021", subject=subject, session=session, run=run,
                         acquisition=acquisition, source_file=relative,
                         event_id=f"{subject}/{session}/{run}/row-{event['source_row']}")
            if event["event_kind"] == "motor_imagery":
                values = raw.get_data(start=event["start_sample"],
                                      stop=event["stop_sample_exclusive"])
                event["source_task_numeric_sha256"] = hashlib.sha256(
                    np.asarray(values, dtype="<f8").tobytes(order="C")).hexdigest()
        task_events = [e for e in events if e["event_kind"] == "motor_imagery"]
        numeric = scan_numeric(raw)
        return ({"status": "passed", "dataset": "Leeuwis2021", "subject": subject,
                 "session": session, "run": run, "acquisition": acquisition,
                 "source_file": relative, "n_times": int(raw.n_times), "sfreq": 250,
                 "channel_names": raw.ch_names, "n_channels": 16,
                 "EDF_duration_seconds": raw.n_times / 250,
                 "sidecar_recording_duration_seconds": metadata.get("RecordingDuration"),
                 "reference": metadata.get("EEGReference"), "stored_physical_unit": "µV",
                 "MNE_numeric_unit": "V", "source_event_count": len(events),
                 "source_class_counts": dict(Counter(e["label"] for e in events)),
                 "task_duration_seconds_counts": dict(Counter(str(e["duration_seconds"])
                                                               for e in task_events)),
                 "segment_sample_count_counts": dict(Counter(str(e["segment_sample_count"])
                                                               for e in task_events)),
                 "verified_source_files": verified, **numeric}, events)
    finally:
        raw.close()


def duplicate_groups(items: list[dict], field: str, identity: str) -> list[dict]:
    groups = defaultdict(list)
    for item in items:
        if item.get(field):
            groups[item[field]].append(item)
    result = []
    for digest, group in groups.items():
        if len(group) > 1:
            result.append({"numeric_sha256": digest,
                           "identities": [item[identity] for item in group],
                           "subjects": sorted({item["subject"] for item in group}),
                           "cross_subject": len({item["subject"] for item in group}) > 1,
                           "labels": sorted({item.get("label", "continuous") for item in group})})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--available-only", action="store_true",
                        help="Audit available official files without claiming full source acceptance")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    require(plan["nemar_id"] == "nm000327" and plan["version"] == "v1.0.0",
            "Audit applies only to pinned Leeuwis2021 nm000327 v1.0.0")
    official = (REPO_ROOT / plan["official_manifest_path"]).read_bytes()
    require(hashlib.sha256(official).hexdigest() == plan["official_manifest_sha256"],
            "Official manifest snapshot changed")
    selection, _ = load_selection(plan)
    lookup = {item["path"]: item for item in selection}
    official_lookup = {item["path"]: item for item in json.loads(official)}
    require(all(item == official_lookup.get(item["path"]) for item in selection),
            "Selected entries differ from official pinned manifest")
    started = datetime.now(timezone.utc).isoformat()
    all_verified = []
    missing_files = []
    for item in selection:
        source_path = safe_destination(args.data_root, item["path"])
        if not source_path.exists() and args.available_only:
            missing_files.append(item["path"])
            continue
        digest, sha256, count = digest_file(source_path, item)
        require(digest == item["checksum"] and count == item["size"],
                f"Official selected source mismatch: {item['path']}")
        all_verified.append({"path": item["path"], "actual_sha256": sha256, "bytes": count})
    participants = read_tsv(args.data_root / "participants.tsv")
    require(len(participants) == 55 and {p["participant_id"] for p in participants}
            == {f"sub-{i}" for i in range(1, 56)}, "Pinned55 resource identities changed")
    expected_paths = sorted(item["path"] for item in selection if item["path"].endswith("_eeg.edf"))
    require(len(expected_paths) == 220, "Pinned220 EDF identities changed")
    paths = [p for p in expected_paths if p not in missing_files]
    args.output.mkdir(parents=True, exist_ok=True)
    runs, events = [], []
    for relative in paths:
        try:
            result, source_events = audit_run(args.data_root, relative, lookup)
            events.extend(source_events)
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            result = {"status": "failed", "source_file": relative,
                      "error": f"{type(error).__name__}: {error}"}
        runs.append(result)
        write_immutable(args.output / "runs" / (relative.replace("/", "__") + ".json"), result)
        print(json.dumps({"source_file": relative, "status": result["status"]}), flush=True)
    tasks = [e for e in events if e["event_kind"] == "motor_imagery"]
    continuous_duplicates = duplicate_groups(runs, "whole_signal_numeric_sha256", "source_file")
    task_duplicates = duplicate_groups(tasks, "source_task_numeric_sha256", "event_id")
    cross_subject_affected = sorted({subject for group in [*continuous_duplicates, *task_duplicates]
                                     if group["cross_subject"] for subject in group["subjects"]})
    summary = {
        "dataset": "Leeuwis2021", "nemar_id": "nm000327", "version": "v1.0.0",
        "license": plan["license"], "publication_year": 2021,
        "nemar_deposit_date": "2026-10-08; reformatted older study, not new acquisition",
        "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                  cwd=REPO_ROOT, text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
        "selection_manifest_sha256": plan["selection_manifest_sha256"],
        "official_manifest_sha256": plan["official_manifest_sha256"],
        "runtime_versions": {"mne": mne.__version__, "numpy": np.__version__},
        "verified_source_file_count": len(all_verified),
        "verified_source_bytes": sum(item["bytes"] for item in all_verified),
        "expected_selected_file_count": len(selection), "expected_EDF_count": len(expected_paths),
        "available_only": args.available_only, "missing_source_files": missing_files,
        "passed_run_count": sum(r["status"] == "passed" for r in runs),
        "failed_runs": [r for r in runs if r["status"] == "failed"],
        "subject_count": len({r["subject"] for r in runs if r["status"] == "passed"}),
        "session_identity_count": len({(r["subject"], r["session"]) for r in runs
                                       if r["status"] == "passed"}),
        "source_event_count_including_EDGE": len(events), "task_event_count": len(tasks),
        "source_class_counts": dict(Counter(e["label"] for e in events)),
        "task_duration_seconds_counts": dict(Counter(str(e["duration_seconds"]) for e in tasks)),
        "task_sample_count_counts": dict(Counter(str(e["source_duration_sample_count"])
                                                 for e in tasks)),
        "stored_codes": STORED_CODES, "upstream_codes": {"left_hand": 1, "right_hand": 2},
        "demographics": {"age_values": dict(Counter(p["age"] for p in participants)),
                         "age_covariate_usable": False,
                         "age_note": "20.71 is published group mean, repeated per row; "
                         "not individual age", "sex_values": dict(Counter(p["sex"]
                                                                          for p in participants))},
        "whole_signal_exact_duplicate_groups": continuous_duplicates,
        "task_window_exact_duplicate_groups": task_duplicates,
        "cross_subject_exact_duplicate_affected_ids": cross_subject_affected,
        "flatline_run_count": sum(bool(r.get("flatline_channel_names")) for r in runs),
        "all_source_task_and_boundary_rows_retained": True,
        "task_window_hash_convention": "all16 channels x original source duration sample "
        "count; float64 little-endian C-order; MNE volts; half-open [start,stop)",
        "requested_available_scope_passed": all(r["status"] == "passed" for r in runs),
        "source_acceptance_complete": not missing_files and len(runs) == len(expected_paths)
        and all(r["status"] == "passed" for r in runs),
        "training_models_fitted": False, "analysis_windows_selected": False,
        "independence_limit": "Exact numeric checks apply within this pinned resource; "
        "absence of detected duplicates does not establish biological identity independence "
        "or global cross-dataset uniqueness. Original CSV and other mirrors not downloaded.",
        "scope_limit": "One visit with calibration+feedback runs; not longitudinal days, "
        "not task hit labels, not evidence of learning or retention.",
    }
    write_immutable(args.output / "source_audit_summary.json", summary)
    write_immutable(args.output / "continuous_run_ledger.json", runs)
    write_immutable(args.output / "source_event_ledger.json", events)
    write_immutable(args.output / "verified_source_files.json", all_verified)
    print(json.dumps({key: summary[key] for key in ["source_acceptance_complete",
                                                   "passed_run_count", "subject_count",
                                                   "task_event_count"]}), flush=True)
    if not summary["requested_available_scope_passed"]:
        raise SystemExit("Source audit incomplete; original errors and rows preserved")


if __name__ == "__main__":
    main()
