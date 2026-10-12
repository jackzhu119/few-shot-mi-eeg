#!/usr/bin/env python3
"""Audit two pinned single-visit external EEG resources, without model fitting.

The MILimb derivative concatenates separately recorded segments. Its original
zero-duration EDGE annotations are retained as boundaries, never training trials.
Liu is a clinical, preprocessed 29-channel derivative, not a healthy cohort.
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

ROOT = Path(__file__).resolve().parents[1]
POLICIES = {
    "nm000328": {
        "version": "v1.0.0", "dataset": "MILimbEEG", "participants": 60,
        "sfreq": 125.0, "unit": "µV", "suffix": ".edf",
        "channels": ["FC5", "F3", "Fz", "F4", "FC6", "FC1", "FC2", "Cz",
                     "T7", "CP5", "C3", "CP1", "CP2", "C4", "CP6", "T8"],
        "labels": {"EDGE boundary", "beo", "clh", "crh", "dlf", "drf", "plf", "prf", "rest"},
        "population": "mixed; source study includes healthy, amputee, hydrocephalus and post-COVID participants",
        "scope": "concatenated imagery segment derivative; no longitudinal feedback learning",
    },
    "nm000158": {
        "version": "v1.0.3", "dataset": "Liu2024", "participants": 50,
        "sfreq": 500.0, "unit": "V", "suffix": ".bdf",
        "channels": ["FP1", "FP2", "Fz", "F3", "F4", "F7", "F8", "FCz", "FC3", "FC4",
                     "FT7", "FT8", "Cz", "C3", "C4", "T3", "T4", "CP3", "CP4", "TP7",
                     "TP8", "Pz", "P3", "P4", "T5", "T6", "Oz", "O1", "O2"],
        "labels": {"left_hand", "right_hand"}, "mapping": {"left_hand": 1, "right_hand": 2},
        "population": "acute stroke patients 1–30 days post-stroke",
        "scope": "single-visit video-guided imagery; preprocessed derivative, no treatment/retention intervention",
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def validate_events(rows, *, policy, n_times, source_file):
    require(bool(rows), "Source event table is empty")
    subject, session = source_file.split("/")[:2]
    events, mapping = [], defaultdict(set)
    last_onset, last_positive_stop = -1, -1
    for index, row in enumerate(rows, 1):
        label = row["trial_type"]
        require(label in policy["labels"], f"Unknown source label: {label}")
        onset, duration = float(row["onset"]), float(row["duration"])
        sample, value = int(row["sample"]), int(row["value"])
        require(np.isfinite(onset) and np.isfinite(duration) and onset >= 0 and duration >= 0,
                "Invalid source times")
        require(abs(onset * policy["sfreq"] - sample) <= 1e-3,
                "Source onset/sample mismatch")
        length = round(duration * policy["sfreq"])
        require(abs(duration * policy["sfreq"] - length) <= 1e-3,
                "Source duration not sample aligned")
        require(sample >= 0 and sample + length <= n_times, "Source event outside signal boundary")
        require(sample >= last_onset, "Unordered source events")
        last_onset = sample
        boundary = label == "EDGE boundary"
        require((boundary and duration == 0) or (not boundary and duration > 0),
                "Zero duration requires explicit EDGE boundary")
        if not boundary:
            require(sample >= last_positive_stop, "Overlapping positive source event windows")
            last_positive_stop = sample + length
        require(value > 0, "Invalid stored source event code")
        if "mapping" in policy:
            require(value == policy["mapping"][label], "Stored class/value mismatch")
        mapping[label].add(value)
        events.append({"dataset": policy["dataset"], "subject": subject, "session": session,
                       "source_file": source_file, "source_row": index,
                       "source_event_id": f"{subject}/{session}/run-0/row-{index}",
                       "label": label, "stored_value": value, "onset_seconds": onset,
                       "duration_seconds": duration, "start_sample": sample,
                       "duration_samples_as_stored": length, "stop_sample_exclusive": sample + length,
                       "source_event_kind": "concatenation_boundary" if boundary else "positive_duration_task",
                       "analysis_eligibility": "unselected;no_model_window_policy"})
    require(all(len(values) == 1 for values in mapping.values()), "Inconsistent within-file label codes")
    if policy["dataset"] == "Liu2024":
        require(Counter(e["label"] for e in events) == {"left_hand": 20, "right_hand": 20},
                "Liu source class counts changed")
    return events


def numeric_scan(raw):
    count, energy, peak = 0, 0.0, 0.0
    digest = hashlib.sha256()
    n_times = int(raw.n_times)
    for start in range(0, n_times, 16384):
        values = raw.get_data(start=start, stop=min(start + 16384, n_times))
        require(np.isfinite(values).all(), "Nonfinite continuous signal")
        digest.update(np.asarray(values, dtype="<f8").tobytes(order="C"))
        count += values.size
        energy += float(np.square(values).sum())
        peak = max(peak, float(np.max(np.abs(values))))
    start = max(0, n_times // 2 - 128)
    values = raw.get_data(picks=[0, 1], start=start, stop=start + 256)
    require(values.shape == (2, 256), "Too few signal samples for4KiB fingerprint")
    return {"all_continuous_samples_finite": True, "continuous_numeric_values": count,
            "peak_absolute_volts": peak, "global_rms_volts": float(np.sqrt(energy / count)),
            "whole_signal_numeric_sha256": digest.hexdigest(),
            "whole_signal_hash_convention": "all channels; float64 little-endian C-order; "
            "chronological16384-sample blocks; MNE volts",
            "central4KiB_numeric_sha256": hashlib.sha256(
                np.asarray(values, dtype="<f8").tobytes(order="C")).hexdigest(),
            "central_fingerprint_start_sample": start}


def audit_run(root, relative, entries, policy):
    require(re.fullmatch(r"(sub-\d+)/ses-0/eeg/\1_ses-0_task-imagery_run-0_eeg\.(edf|bdf)", relative)
            is not None and relative.endswith(policy["suffix"]), "Unexpected signal identity")
    prefix = relative.removesuffix("_eeg" + policy["suffix"])
    verified = {}

    def verify(name):
        require(name in entries, f"Missing official sidecar: {name}")
        path = safe_destination(root, name)
        declared, sha256, size = digest_file(path, entries[name])
        require(declared == entries[name]["checksum"] and size == entries[name]["size"],
                f"Official source checksum mismatch: {name}")
        verified[name] = {"sha256": sha256, "bytes": size, "official_checksum": declared}
        return path

    path = verify(relative)
    metadata = json.loads(verify(prefix + "_eeg.json").read_text())
    events_meta = json.loads(verify(prefix + "_events.json").read_text())
    channels = tsv(verify(prefix + "_channels.tsv"))
    rows = tsv(verify(prefix + "_events.tsv"))
    require(events_meta["onset"]["Units"] == events_meta["duration"]["Units"] == "s"
            and "First sample is 0" in events_meta["sample"]["Description"], "Event units/origin changed")
    reader = mne.io.read_raw_edf if policy["suffix"] == ".edf" else mne.io.read_raw_bdf
    raw = reader(path, preload=False, verbose="ERROR")
    try:
        require(raw.first_samp == 0 and raw.info["sfreq"] == metadata["SamplingFrequency"]
                == policy["sfreq"], "Signal sample origin/rate mismatch")
        require(raw.ch_names == [c["name"] for c in channels] == policy["channels"],
                "Channel order or identity mismatch")
        require(metadata["EEGChannelCount"] == len(channels)
                and raw.get_channel_types() == ["eeg"] * len(channels), "Channel type/count mismatch")
        require(all(c["type"] == "EEG" and float(c["sampling_frequency"]) == policy["sfreq"]
                    and c["units"] == raw._orig_units[c["name"]] == policy["unit"]
                    for c in channels), "Physical units/TSV rate mismatch")
        events = validate_events(rows, policy=policy, n_times=int(raw.n_times), source_file=relative)
        require(len(raw.annotations) == len(events)
                and list(raw.annotations.description) == [e["label"] for e in events]
                and np.allclose(raw.annotations.onset, [e["onset_seconds"] for e in events], rtol=0, atol=1e-6)
                and np.allclose(raw.annotations.duration, [e["duration_seconds"] for e in events],
                                rtol=0, atol=1e-6), "Native signal annotations/TSV mismatch")
        return {"status": "passed", "source_file": relative, "n_times": int(raw.n_times),
                "channels": raw.ch_names, "sfreq": policy["sfreq"], "stored_unit": policy["unit"],
                "MNE_numeric_unit": "V", "EEG_reference": metadata.get("EEGReference"),
                "recording_type_from_sidecar": metadata.get("RecordingType"),
                "source_event_count": len(events), "source_label_counts": dict(Counter(e["label"] for e in events)),
                "verified_source_files": verified, **numeric_scan(raw)}, events
    finally:
        raw.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--representative-only", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    policy = POLICIES[plan["nemar_id"]]
    require(plan["version"] == policy["version"], "Pinned source version changed")
    selection, _ = load_selection(plan)
    entries = {e["path"]: e for e in selection}
    paths = sorted(e["path"] for e in selection if e["path"].endswith(policy["suffix"]))
    require(len(paths) == policy["participants"], "Fixed signal coverage changed")
    if args.representative_only:
        paths = paths[:1]
    started = datetime.now(timezone.utc).isoformat()
    runs, events = [], []
    for path in paths:
        try:
            record, source_events = audit_run(args.data_root, path, entries, policy)
            events.extend(source_events)
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            record = {"status": "failed", "source_file": path, "error": f"{type(error).__name__}: {error}"}
        write_immutable(args.output / "runs" / (path.replace("/", "__") + ".json"), record)
        runs.append(record)
        print(json.dumps({k: record[k] for k in ("status", "source_file")}), flush=True)
    duplicates = {}
    for field in ["whole_signal_numeric_sha256", "central4KiB_numeric_sha256"]:
        groups = defaultdict(list)
        for run in runs:
            if run["status"] == "passed":
                groups[run[field]].append(run["source_file"])
        duplicates[field] = [group for group in groups.values() if len(group) > 1]
    aggregate = {"dataset": policy["dataset"], "nemar_id": plan["nemar_id"], "version": plan["version"],
                 "license": plan["license"], "scope": policy["scope"], "population": policy["population"],
                 "complete": all(r["status"] == "passed" for r in runs),
                 "representative_only": args.representative_only,
                 "signal_file_count": len(runs), "passed_signal_files": sum(r["status"] == "passed" for r in runs),
                 "source_identity_count": len({e["subject"] for e in events}), "source_event_count": len(events),
                 "source_label_counts": dict(Counter(e["label"] for e in events)),
                 "source_duration_counts": dict(Counter(str(e["duration_seconds"]) for e in events)),
                 "source_event_kind_counts": dict(Counter(e["source_event_kind"] for e in events)),
                 "exact_numeric_duplicate_groups": duplicates,
                 "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                 "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                 "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                 "selection_manifest_sha256": plan["selection_manifest_sha256"],
                 "runtime_versions": {"python": sys.version.split()[0], "mne": mne.__version__, "numpy": np.__version__},
                 "failed_signals": [r for r in runs if r["status"] != "passed"],
                 "analysis_status": "source_resource_audit_only;no_model_training_or_window_selection"}
    write_immutable(args.output / "source_events.json", events)
    write_immutable(args.output / "aggregate.json", aggregate)
    print(json.dumps({k: aggregate[k] for k in ("complete", "signal_file_count", "source_identity_count",
                                              "source_event_count")}), flush=True)
    if not aggregate["complete"]:
        raise SystemExit("Source audit incomplete; original failures retained")


if __name__ == "__main__":
    main()
