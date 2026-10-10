#!/usr/bin/env python3
"""Audit an already-downloaded NETBCI subset. No network access or training."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit(data_root: Path, manifest_path: Path) -> dict:
    """Derive units, classes, trial lengths and structure from real files."""
    manifest = json.loads(manifest_path.read_text())
    description = json.loads((data_root / "dataset_description.json").read_text())
    files_checked = []
    for entry in manifest:
        relative = Path(entry["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe path")
        path = data_root / relative
        data = path.read_bytes()
        algorithm = entry["checksum_algorithm"]
        if algorithm == "sha256":
            digest = hashlib.sha256(data).hexdigest()
        elif algorithm == "git":
            header = b"blob " + str(len(data)).encode() + b"\0"
            digest = hashlib.sha1(header + data).hexdigest()
        else:
            raise ValueError(f"Unsupported checksum algorithm: {algorithm}")
        require(len(data) == entry["size"], f"Size mismatch: {relative}")
        require(digest == entry["checksum"], f"Checksum mismatch: {relative}")
        files_checked.append({"path": str(relative), "size": len(data), "verified": True})

    eeg_files = sorted(entry["path"] for entry in manifest if entry["path"].endswith(".edf"))
    require(bool(eeg_files), "No EDF files in local subset manifest")
    subjects = {Path(name).parts[0] for name in eeg_files}
    require(len(subjects) == 1, "This access check is bounded to exactly one subject")
    subject = next(iter(subjects))
    local_edfs = {str(path.relative_to(data_root)) for path in (data_root / subject).rglob("*.edf")}
    require(local_edfs == set(eeg_files), "EDF directory and pinned subset manifest differ")

    runs = []
    labels_to_values: dict[str, set[int]] = defaultdict(set)
    channel_orders = []
    for relative in eeg_files:
        path = data_root / relative
        match = re.search(r"_ses-([^_]+)_task-([^_]+)_run-([^_]+)_eeg\.edf$", path.name)
        require(match is not None, f"Missing session/run identity: {path.name}")
        session, task, run = match.groups()
        prefix = path.name.removesuffix("_eeg.edf")
        eeg_json = json.loads((path.parent / f"{prefix}_eeg.json").read_text())
        event_json = json.loads((path.parent / f"{prefix}_events.json").read_text())
        channels = read_tsv(path.parent / f"{prefix}_channels.tsv")
        rows = read_tsv(path.parent / f"{prefix}_events.tsv")
        require(bool(rows), f"Empty events: {path.name}")
        require(event_json["onset"]["Units"] == "s", "Unresolved event onset units")
        require(event_json["duration"]["Units"] == "s", "Unresolved duration units")
        require("First sample is 0" in event_json["sample"]["Description"],
                "Sample origin not explicitly documented")

        raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
        sfreq = float(raw.info["sfreq"])
        require(sfreq == float(eeg_json["SamplingFrequency"]), "EDF/JSON sampling mismatch")
        require(raw.ch_names == [channel["name"] for channel in channels], "Channel order mismatch")
        require(len(raw.ch_names) == int(eeg_json["EEGChannelCount"]), "Channel count mismatch")
        require(all(channel["type"] == "EEG" for channel in channels), "Unexpected channel type")
        require(all(float(channel["sampling_frequency"]) == sfreq for channel in channels),
                "Channel sampling mismatch")
        require(set(raw.get_channel_types()) == {"eeg"}, "MNE channel types mismatch")
        units = dict(raw._orig_units)
        require(all(units[channel["name"]] == channel["units"] for channel in channels),
                "EDF/channel physical units mismatch")
        channel_orders.append(raw.ch_names)

        onsets = np.asarray([float(row["onset"]) for row in rows])
        durations = np.asarray([float(row["duration"]) for row in rows])
        samples = np.asarray([int(row["sample"]) for row in rows], dtype=np.int64)
        values = np.asarray([int(row["value"]) for row in rows], dtype=np.int64)
        names = [row["trial_type"] for row in rows]
        require(np.isfinite(onsets).all() and np.isfinite(durations).all(), "Nonfinite events")
        require((durations > 0).all(), "Nonpositive trial duration")
        require((np.diff(samples) > 0).all(), "Duplicate or unordered event samples")
        error = float(np.max(np.abs(onsets * sfreq - samples)))
        require(error < 1e-6, "Seconds/sample alignment failed")
        epoch_lengths_float = durations * sfreq
        require(np.allclose(epoch_lengths_float, np.rint(epoch_lengths_float), rtol=0, atol=1e-6),
                "Duration is not an integral number of samples")
        epoch_lengths = np.rint(epoch_lengths_float).astype(np.int64)
        require((samples >= 0).all() and (samples + epoch_lengths <= raw.n_times).all(),
                "A trial extends outside the recording")
        require(len(raw.annotations) == len(rows), "EDF/TSV event count mismatch")
        require(list(raw.annotations.description) == names, "EDF/TSV event labels mismatch")
        require(np.allclose(raw.annotations.onset, onsets, rtol=0, atol=1e-6),
                "EDF/TSV annotation onset mismatch")
        require(np.allclose(raw.annotations.duration, durations, rtol=0, atol=1e-6),
                "EDF/TSV annotation duration mismatch")
        for name, value in zip(names, values, strict=True):
            labels_to_values[name].add(int(value))

        # Read the complete signal one run at a time; no learned transforms.
        signal = raw.get_data()
        require(np.isfinite(signal).all(), "Nonfinite EEG signal")
        signal_range = [float(signal.min()), float(signal.max())]
        del signal
        run_mapping = {name: int(value) for name, value in zip(names, values, strict=True)}
        annotation_events, _ = mne.events_from_annotations(raw, event_id=run_mapping, verbose="ERROR")
        require(np.array_equal(annotation_events[:, 0], samples), "MNE event samples mismatch")
        require(np.array_equal(annotation_events[:, 2], values), "MNE event values mismatch")
        runs.append({
            "subject": subject, "session": session, "run": run, "task": task,
            "file": relative, "trial_count": len(rows), "class_counts": dict(Counter(names)),
            "channel_count": len(raw.ch_names), "channel_names": raw.ch_names,
            "channel_types": dict(Counter(raw.get_channel_types())),
            "sampling_frequency_hz": sfreq, "signal_samples": int(raw.n_times),
            "physical_units": dict(Counter(units.values())), "mne_signal_unit": "V",
            "signal_range_v": signal_range, "whole_signal_finite": True,
            "onset_units": event_json["onset"]["Units"],
            "duration_units": event_json["duration"]["Units"], "sample_origin": 0,
            "event_sample_alignment_max_error": error,
            "trial_durations_s": sorted(set(durations.tolist())),
            "trial_lengths_samples": sorted(set(epoch_lengths.tolist())),
            "first_event_sample": int(samples[0]), "last_event_sample": int(samples[-1]),
            "edf_tsv_annotations_match": True, "mne_events_match": True,
            "all_trials_inside_recording": True,
        })
        raw.close()

    require(all(order == channel_orders[0] for order in channel_orders), "Channel order changes across runs")
    require(all(len(values) == 1 for values in labels_to_values.values()), "Event mapping changes across runs")
    mapping = {name: next(iter(values)) for name, values in labels_to_values.items()}
    require(len(set(mapping.values())) == len(mapping), "Event values are not class-specific")
    require(len({(run["session"], run["run"]) for run in runs}) == len(runs), "Duplicate run identity")
    sessions = []
    class_totals = Counter()
    for session in sorted({run["session"] for run in runs}):
        selected = [run for run in runs if run["session"] == session]
        counts = Counter()
        for run in selected:
            counts.update(run["class_counts"])
        class_totals.update(counts)
        sessions.append({"session": session, "runs": len(selected), "run_ids": [run["run"] for run in selected],
                         "trial_count": sum(counts.values()), "class_counts": dict(counts)})
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_commit = None
    return {
        "status": "passed_local_subset_access_and_structure_checks",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "client_timezone": "Asia/Shanghai", "dataset_id": "nm000305",
        "version": description["Version"], "dataset_type": description["DatasetType"],
        "license": description["License"], "data_root": str(data_root.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_git_commit": git_commit,
        "runtime_versions": {"python": platform.python_version(), **{
            name: importlib.metadata.version(name) for name in ["mne", "numpy", "scipy", "moabb"]}},
        "summary": {
            "subject": subject, "session_count": len(sessions), "run_count": len(runs),
            "eeg_channel_counts": sorted({run["channel_count"] for run in runs}),
            "sampling_frequencies_hz": sorted({run["sampling_frequency_hz"] for run in runs}),
            "total_trials": sum(class_totals.values()), "class_counts": dict(class_totals),
            "sessions": sessions, "event_value_mapping": mapping, "channel_order_stable": True,
            "files_verified": len(files_checked), "bytes_verified": sum(item["size"] for item in files_checked),
            "all_checks_pass": True,
        },
        "runs": runs, "file_checks": files_checked,
        "scope": {"local_only": True, "downloaded_by_this_script": False,
                  "training_performed": False, "whole_dataset_validated": False},
        "limitations": [
            "README numeric event mapping differs from actual TSV value mapping.",
            "README cohort trial counts are not validated by this one-subject check.",
            "No trial-level hit/miss, cursor, feedback-onset or behavior records in this subset.",
            "Original Dataverse/NEMAR signal equality and behavior joins require separate checks.",
            "Finite signal and metadata channel status do not prove artifact-free EEG.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=REPO_ROOT / "data/netbci2026/nm000305/v1.0.0")
    parser.add_argument("--manifest", type=Path,
                        default=REPO_ROOT / "research_logs/netbci2026_sources/download_manifest.json")
    parser.add_argument("--output", type=Path,
                        default=REPO_ROOT / "research_logs/netbci2026_subject1_audit.json")
    args = parser.parse_args()
    result = audit(args.data_root, args.manifest)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Preserve historical receipts; overwrite only an explicitly selected output.
    if args.output.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        args.output.replace(args.output.with_name(f"{args.output.stem}.{stamp}.json"))
    args.output.write_text(serialized)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"Audit saved: {args.output.resolve()}")


if __name__ == "__main__":
    main()
