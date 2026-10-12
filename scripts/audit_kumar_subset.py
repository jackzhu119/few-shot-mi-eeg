#!/usr/bin/env python3
"""Audit pinned Kumar2024 EEG and every source event, without fitting models.

All raw samples are checked in bounded blocks. Partial events retain identities;
no window, padding, exclusion, tensor concatenation or preprocessing is applied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

from fetch_nemar_subset import digest_file, load_selection, safe_destination, write_immutable

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING = {"left_hand": 1, "right_hand": 2}
EXPECTED_CHANNELS = (
    "F7", "F3", "Fz", "F4", "F8", "FC5", "FC1", "FC2", "FC6", "C3", "Cz", "C4",
    "CP5", "CP1", "CP2", "CP6", "P7", "P3", "Pz", "P4", "P8", "POz",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def validate_events(rows: list[dict], *, sfreq: float, n_times: int,
                    subject: str, session: str, run: str, source_file: str) -> list[dict]:
    """Validate every original time/label identity; permit documented partial events."""
    require(len(rows) == 20, "Pinned Kumar run must retain exactly20 source events")
    onsets = np.array([float(item["onset"]) for item in rows])
    durations = np.array([float(item["duration"]) for item in rows])
    starts = np.array([int(item["sample"]) for item in rows])
    require(np.isfinite(onsets).all() and np.isfinite(durations).all()
            and (durations > 0).all(), "Invalid event times")
    require(np.allclose(onsets * sfreq, starts, rtol=0, atol=1e-6),
            "Event onset seconds/sample mismatch")
    # Six-decimal duration exports incur <=0.000256 sample rounding at512Hz.
    lengths = np.rint(durations * sfreq).astype(int)
    require(np.allclose(durations * sfreq, lengths, rtol=0, atol=1e-3),
            "Duration is not sample-aligned within export precision")
    stops = starts + lengths
    require((starts >= 0).all() and (stops <= n_times).all(), "Source event outside EDF boundary")
    require((np.diff(starts) > 0).all() and (stops[:-1] <= starts[1:]).all(),
            "Source events duplicate, unordered or overlapping")
    require(Counter(item["trial_type"] for item in rows) == {"left_hand": 10, "right_hand": 10},
            "Unknown labels or class counts changed")
    events = []
    for index, item in enumerate(rows):
        require(int(item["value"]) == MAPPING[item["trial_type"]], "Stored label/value mismatch")
        events.append({"dataset": "Kumar2024", "subject": subject, "session": session, "run": run,
                       "source_row": index + 1, "trial_id": f"{subject}/{session}/{run}/row-{index+1}",
                       "label": item["trial_type"], "stored_value": int(item["value"]),
                       "onset_seconds": float(onsets[index]), "duration_seconds": float(
                           durations[index]), "start_sample": int(starts[index]),
                       "stop_sample_exclusive": int(stops[index]), "sample_count": int(lengths[index]),
                       "source_duration_exactly5s": bool(durations[index] == 5.0),
                       "source_file": source_file,
                       "analysis_eligibility": "not_selected_no_model_window_policy_yet"})
    return events


def numeric_scan(raw) -> dict:
    """Scan all channels/samples in volts, retain exact numeric and small fingerprints."""
    whole = hashlib.sha256()
    peak = 0.0
    sum_squares = 0.0
    count = 0
    for start in range(0, raw.n_times, 16384):
        data = raw.get_data(start=start, stop=min(start + 16384, raw.n_times))
        require(np.isfinite(data).all(), "Nonfinite continuous EEG signal")
        whole.update(np.asarray(data, dtype="<f8").tobytes(order="C"))
        peak = max(peak, float(np.max(np.abs(data))))
        sum_squares += float(np.square(data).sum())
        count += data.size
    center_start = max(0, int(raw.n_times) // 2 - 128)
    center = raw.get_data(picks=[0, 1], start=center_start, stop=center_start + 256)
    require(center.shape == (2, 256), "Too few samples for declared4KiB fingerprint")
    return {"all_continuous_samples_finite": True, "continuous_numeric_values": count,
            "peak_absolute_volts": peak, "global_rms_volts": float(np.sqrt(sum_squares / count)),
            "whole_signal_numeric_sha256": whole.hexdigest(),
            "whole_signal_hash_convention": "all22channels; float64 little-endian C-order; "
            "16384-sample blocks in chronological order; volts",
            "central_4KiB_numeric_sha256": hashlib.sha256(
                np.asarray(center, dtype="<f8").tobytes(order="C")).hexdigest(),
            "central_fingerprint_start_sample": center_start,
            "central_fingerprint_convention": "first2channels x256 central samples; "
            "float64 little-endian C-order; volts"}


def audit_run(root: Path, relative: str, entries: dict) -> tuple[dict, list[dict]]:
    match = re.fullmatch(r"(sub-\d+)/(ses-\d+)/eeg/\1_\2_task-imagery_(run-\d+)_eeg.edf", relative)
    require(match is not None, f"Unexpected pinned signal identity: {relative}")
    subject, session, run = match.groups()
    prefix = relative.removesuffix("_eeg.edf")
    verified = {}

    def verify(name: str) -> Path:
        require(name in entries, f"Missing source sidecar: {name}")
        path = safe_destination(root, name)
        digest, sha256, count = digest_file(path, entries[name])
        require(count == entries[name]["size"] and digest == entries[name]["checksum"],
                f"Source checksum mismatch: {name}")
        verified[name] = {"sha256": sha256, "official_checksum": digest,
                          "official_algorithm": entries[name]["checksum_algorithm"], "bytes": count}
        return path

    signal = verify(relative)
    metadata = json.loads(verify(prefix + "_eeg.json").read_text())
    events_metadata = json.loads(verify(prefix + "_events.json").read_text())
    rows = tsv(verify(prefix + "_events.tsv"))
    channels = tsv(verify(prefix + "_channels.tsv"))
    require(events_metadata["onset"]["Units"] == events_metadata["duration"]["Units"] == "s",
            "Event seconds units unspecified")
    require("First sample is 0" in events_metadata["sample"]["Description"],
            "Zero-based sample index unspecified")
    raw = mne.io.read_raw_edf(signal, preload=False, verbose="ERROR")
    try:
        require(raw.first_samp == 0, "Unexpected EDF sample origin")
        require(raw.info["sfreq"] == metadata["SamplingFrequency"] == 512.0, "Sampling rate changed")
        require(tuple(raw.ch_names) == tuple(c["name"] for c in channels) == EXPECTED_CHANNELS,
                "Channel order or expected22channels changed")
        require(metadata["EEGChannelCount"] == 22 and raw.get_channel_types() == ["eeg"] * 22,
                "Channel count or EEG type changed")
        require(all(c["type"] == "EEG" and float(c["sampling_frequency"]) == 512.0
                    and c["units"] == raw._orig_units[c["name"]] == "µV" for c in channels),
                "Physical channel units or rate differ from EDF/TSV")
        events = validate_events(rows, sfreq=512.0, n_times=raw.n_times,
                                 subject=subject, session=session, run=run, source_file=relative)
        require(len(raw.annotations) == len(events)
                and list(raw.annotations.description) == [e["label"] for e in events]
                and np.allclose(raw.annotations.onset, [e["onset_seconds"] for e in events],
                                rtol=0, atol=1e-6)
                and np.allclose(raw.annotations.duration, [e["duration_seconds"] for e in events],
                                rtol=0, atol=1e-6), "EDF annotation and TSV identity/time mismatch")
        numeric = numeric_scan(raw)
        return ({"status": "passed", "dataset": "Kumar2024", "subject": subject,
                 "session": session, "run": run, "source_file": relative, "n_channels": 22,
                 "channel_names": raw.ch_names, "sfreq": 512.0, "n_times": int(raw.n_times),
                 "EDF_duration_seconds": raw.n_times / 512.0,
                 "sidecar_recording_duration_seconds": metadata.get("RecordingDuration"),
                 "EEG_reference": metadata.get("EEGReference"), "stored_physical_unit": "µV",
                 "MNE_numeric_unit": "V", "source_event_count": len(events),
                 "source_class_counts": dict(Counter(e["label"] for e in events)),
                 "shorter_than5s_source_events": sum(e["duration_seconds"] < 5 for e in events),
                 "verified_source_files": verified, **numeric}, events)
    finally:
        raw.close()


def duplicate_groups(runs: list[dict], field: str) -> list[list[str]]:
    groups = defaultdict(list)
    for item in runs:
        if item["status"] == "passed":
            groups[item[field]].append(item["source_file"])
    return [paths for paths in groups.values() if len(paths) > 1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    require(plan["nemar_id"] == "nm000177" and plan["version"] == "v1.0.5",
            "This audit is source-specific to Kumar2024 nm000177 v1.0.5")
    selection, _ = load_selection(plan)
    lookup = {entry["path"]: entry for entry in selection}
    participants_path = safe_destination(args.data_root, "participants.tsv")
    participant_digest, participant_sha256, participant_size = digest_file(
        participants_path, lookup["participants.tsv"])
    require(participant_digest == lookup["participants.tsv"]["checksum"]
            and participant_size == lookup["participants.tsv"]["size"],
            "Official participant metadata checksum changed")
    participants = tsv(participants_path)
    require({p["participant_id"] for p in participants} == {f"sub-{i}" for i in range(1, 19)}
            and len(participants) == 18, "Published participant identity set changed")
    participant_text = participants_path.read_text()
    participant_metadata = {
        "sha256": participant_sha256, "row_count": len(participants),
        "age_field_values": dict(Counter(p["age"] for p in participants)),
        "age_covariate_usable": False,
        "age_problem": "All ages are2020; cannot use as human age",
        "physical_tab_count": participant_text.count("\t"),
        "physical_newline_count": participant_text.count("\n"),
        "literal_escaped_tab_count": participant_text.count("\\t"),
        "literal_escaped_newline_count": participant_text.count("\\n"),
        "group_field_values": dict(Counter(p["group"] for p in participants)),
        "GR_PAR_mapping_status": "Generic healthy group does not establish historical treatment group",
    }
    paths = sorted(e["path"] for e in selection if e["path"].endswith("_eeg.edf"))
    require(len(paths) == 360, "Pinned EDF count changed")
    args.output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    runs, events = [], []
    for relative in paths:
        try:
            result, source_events = audit_run(args.data_root, relative, lookup)
            events.extend(source_events)
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            result = {"status": "failed", "source_file": relative,
                      "error": f"{type(error).__name__}: {error}"}
        runs.append(result)
        artifact = args.output / "runs" / (relative.replace("/", "__") + ".json")
        write_immutable(artifact, result)
        print(json.dumps({k: result[k] for k in ("status", "source_file")}), flush=True)
    subjects = sorted({e["subject"] for e in events}, key=lambda s: int(s.removeprefix("sub-")))
    sessions = []
    for subject in subjects:
        for session in [f"ses-{i}" for i in range(6)]:
            rows = [e for e in events if e["subject"] == subject and e["session"] == session]
            sessions.append({"subject": subject, "session": session, "source_events": len(rows),
                             "class_counts": dict(Counter(e["label"] for e in rows)),
                             "runs": len({e["run"] for e in rows}),
                             "shorter_than5s_source_events": sum(e["duration_seconds"] < 5 for e in rows)})
    if all(r["status"] == "passed" for r in runs):
        require(subjects == [f"sub-{i}" for i in range(1, 19)] and len(events) == 7200,
                "Complete signal set disagrees with18 participants7200 source events")
        require(len(sessions) == 108 and all(
            s["runs"] == (4 if s["session"] in {"ses-0", "ses-1"} else 3)
            and s["source_events"] == s["runs"] * 20 for s in sessions),
            "Published six-session/run coverage changed")
    aggregate = {"schema_version": 1, "dataset": "Kumar2024", "nemar_id": "nm000177",
                 "version": "v1.0.5", "license": plan["license"], "started_at_utc": started,
                 "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                 "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                           cwd=REPO_ROOT, text=True).strip(),
                 "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                 "runtime_versions": {"python": sys.version.split()[0], "mne": mne.__version__,
                                      "numpy": np.__version__},
                 "selection_manifest_sha256": plan["selection_manifest_sha256"],
                 "complete": all(r["status"] == "passed" for r in runs), "EDF_count": len(runs),
                 "passed_EDF_count": sum(r["status"] == "passed" for r in runs),
                 "participants": len(subjects), "subject_session_pairs": len(sessions),
                 "source_events": len(events), "source_class_counts": dict(Counter(
                     e["label"] for e in events)), "duration_exactly5s_count": sum(
                     e["source_duration_exactly5s"] for e in events),
                 "partial_source_event_count": sum(e["duration_seconds"] < 5 for e in events),
                 "minimum_source_duration_seconds": min((e["duration_seconds"] for e in events),
                                                        default=None),
                 "channel_names": list(EXPECTED_CHANNELS), "sfreq": 512.0,
                 "participant_metadata": participant_metadata,
                 "whole_signal_exact_numeric_duplicate_groups": duplicate_groups(
                     runs, "whole_signal_numeric_sha256"),
                 "central4KiB_duplicate_groups": duplicate_groups(
                     runs, "central_4KiB_numeric_sha256"),
                 "session_counts": sessions, "failed_runs": [r for r in runs if r["status"] != "passed"],
                 "analysis_status": "signal_resource_audited_only_no_model_training_or_window_selection",
                 "scope_limits": ["No hit/miss or racing outcomes inferred from MI class labels",
                                  "No age covariate used; participants ages contain invalid2020 values",
                                  "GR/PAR mapping requires explicit upstream subject provenance",
                                  "No pooled independent participant count across datasets established",
                                  "Partial events retained; no padding, extension or removal performed"]}
    write_immutable(args.output / "source_events.json", events)
    write_immutable(args.output / "aggregate.json", aggregate)
    print(json.dumps({k: aggregate[k] for k in ("complete", "passed_EDF_count", "participants",
                                              "source_events", "partial_source_event_count")}), flush=True)
    if not aggregate["complete"]:
        raise SystemExit("Signal audit incomplete; individual failure records retained")


if __name__ == "__main__":
    main()
