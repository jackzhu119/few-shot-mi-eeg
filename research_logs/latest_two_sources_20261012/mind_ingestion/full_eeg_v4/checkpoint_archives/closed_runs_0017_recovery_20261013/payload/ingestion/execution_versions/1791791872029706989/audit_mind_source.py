#!/usr/bin/env python3
"""Stream BrainVision EEG and retain every native MIND V4 source event; no fitting."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

BLOCK_SAMPLES = 16384
SOURCE_ROOT = "/V4/MIND_BIDS/"
CODE_LABEL = {"1": "rest_open", "2": "rest_closed", "3": "mi_start", "4": "mi_l2r",
              "5": "mi_t2b", "6": "mi_ul2lr", "7": "mi_ur2ll"}
MANUAL_FNIRS_IDS = {4, 5, 6, 7, 8, 9, 13, 14, 15, 29, 30}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalized_md5(value: str) -> str:
    """ScienceDB occasionally omits leading zeroes; retain its original separately."""
    if not re.fullmatch(r"[0-9a-fA-F]{1,32}", value):
        raise ValueError("Official MD5 must be a hexadecimal digest of at most 32 digits")
    return value.lower().zfill(32)


def file_hashes(path: Path) -> dict:
    md5 = hashlib.md5(usedforsecurity=False)
    sha = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(block)
            md5.update(block)
            sha.update(block)
    return {"bytes": count, "md5_actual": md5.hexdigest(), "sha256": sha.hexdigest()}


def verify_source(path: Path, record: dict) -> dict:
    hashes = file_hashes(path)
    original = str(record["md5"])
    expected = normalized_md5(original)
    if hashes["bytes"] != int(record["size"]) or hashes["md5_actual"] != expected:
        raise ValueError("Official source length or full MD5 mismatch")
    return {**hashes, "official_md5_original": original,
            "official_md5_normalized_32hex": expected,
            "md5_normalization": "explicit left-zero-padding to 32 hexadecimal digits",
            "official_size_and_md5_pass": True, "etag_used_as_checksum": False}


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def numeric_bytes(data: np.ndarray) -> bytes:
    # Sample-major means the digest is independent of streaming block boundaries.
    return np.asarray(data.T, dtype="<f8", order="C").tobytes(order="C")


def marker_rows(path: Path) -> list[dict]:
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"Mk(\d+)=(.*)", line)
        if not match:
            continue
        fields = match[2].split(",")
        result.append({"marker_number": int(match[1]), "marker_type": fields[0],
                       "description": fields[1], "native_position_1based": int(fields[2]),
                       "native_sample_0based": int(fields[2]) - 1,
                       "native_size_samples": int(fields[3]), "channel": int(fields[4]),
                       "date": fields[5] if len(fields) > 5 else ""})
    return result


def brainvision_header(path: Path) -> dict:
    sections = {}
    section = ""
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            sections[section] = {}
        elif section and line and not line.startswith(";") and "=" in line:
            key, value = line.split("=", 1)
            sections[section][key] = value
    channel_rows = []
    for key, value in sections.get("Channel Infos", {}).items():
        if re.fullmatch(r"Ch\d+", key):
            fields = value.split(",")
            channel_rows.append({"header_channel": key, "name": fields[0].replace("\\1", ","),
                                 "reference": fields[1], "resolution": float(fields[2]),
                                 "unit": fields[3]})
    return {"common": sections.get("Common Infos", {}),
            "binary": sections.get("Binary Infos", {}), "channels": channel_rows}


def interval_digest(raw, start: int, stop: int, block_samples: int) -> str:
    digest = hashlib.sha256()
    for first in range(start, stop, block_samples):
        data = raw.get_data(start=first, stop=min(first + block_samples, stop))
        if not np.isfinite(data).all():
            raise ValueError("Non-finite values in a native source interval")
        digest.update(numeric_bytes(data))
    return digest.hexdigest()


def audit_run(root: Path, relative_header: str, *, block_samples: int = BLOCK_SAMPLES):
    header = root / relative_header
    subject = re.search(r"(sub-\d+)", relative_header)[1]
    run_id = re.search(r"run-\d+", header.name)[0]
    stem = header.name.removesuffix("_eeg.vhdr")
    folder = header.parent
    events = rows(folder / f"{stem}_events.tsv")
    channels = rows(folder / f"{stem}_channels.tsv")
    eeg_meta = json.loads((folder / f"{stem}_eeg.json").read_text())
    event_meta = json.loads((folder / f"{stem}_events.json").read_text())
    markers = marker_rows(header.with_suffix(".vmrk"))
    header_meta = brainvision_header(header)
    raw = mne.io.read_raw_brainvision(header, preload=False, verbose="ERROR")
    try:
        sfreq = float(raw.info["sfreq"])
        count = int(raw.n_times)
        names = raw.ch_names
        common = header_meta["common"]
        if (common.get("DataFile") != header.with_suffix(".eeg").name
                or common.get("MarkerFile") != header.with_suffix(".vmrk").name
                or common.get("DataFormat") != "BINARY"
                or common.get("DataOrientation") != "MULTIPLEXED"
                or header_meta["binary"].get("BinaryFormat") != "IEEE_FLOAT_32"
                or int(common["NumberOfChannels"]) != len(names)
                or 1e6 / float(common["SamplingInterval"]) != sfreq
                or [c["name"] for c in header_meta["channels"]] != names
                or any(c["unit"] not in {"uV", "µV", "μV"} for c in header_meta["channels"])
                or any(c["resolution"] <= 0 for c in header_meta["channels"])
                or header.with_suffix(".eeg").stat().st_size != count * len(names) * 4):
            raise ValueError("BrainVision native binary, channel, unit or clock mismatch")
        if (names != [r["name"] for r in channels]
                or len(names) != int(eeg_meta["EEGChannelCount"])
                or sfreq != float(eeg_meta["SamplingFrequency"])
                or any(float(r["sampling_frequency"]) != sfreq for r in channels)
                or any(r["type"] != "EEG" for r in channels)
                or any(r["units"] not in {"uV", "µV", "μV"} for r in channels)
                or raw.get_channel_types() != ["eeg"] * len(names)):
            raise ValueError("Source channel, unit or sampling metadata mismatch")
        digest = hashlib.sha256()
        minimum = np.full(len(names), np.inf)
        maximum = np.full(len(names), -np.inf)
        sum_squares = np.zeros(len(names))
        zero = np.ones(len(names), dtype=bool)
        for start in range(0, count, block_samples):
            data = raw.get_data(start=start, stop=min(count, start + block_samples))
            if data.shape[0] != len(names) or not np.isfinite(data).all():
                raise ValueError("Raw EEG contains non-finite values or wrong channel shape")
            digest.update(numeric_bytes(data))
            minimum = np.minimum(minimum, data.min(axis=1))
            maximum = np.maximum(maximum, data.max(axis=1))
            sum_squares += np.square(data).sum(axis=1)
            zero &= (data == 0).all(axis=1)
        annotations = [{"annotation_index": i, "onset_seconds": float(a["onset"]),
                        "duration_seconds": float(a["duration"]),
                        "description": str(a["description"]),
                        "native_sample_0based": int(round(float(a["onset"]) * sfreq))}
                       for i, a in enumerate(raw.annotations)]
        annotation_counts = Counter((a["native_sample_0based"], a["description"].split("/")[-1])
                                    for a in annotations)
        event_markers = [m for m in markers if m["marker_type"] != "New Segment"]
        marker_counts = Counter((m["native_sample_0based"], m["description"]) for m in event_markers)
        ledger = []
        previous_end = None
        for index, row in enumerate(events):
            onset, duration = float(row["onset"]), float(row["duration"])
            if not math.isfinite(onset) or not math.isfinite(duration):
                raise ValueError("Non-finite source event clock")
            start, samples = int(round(onset * sfreq)), int(round(duration * sfreq))
            stop = start + samples
            label, code = row["trial_type"], row["value"]
            flags = []
            if onset < 0 or duration < 0 or start < 0 or stop > count:
                flags.append("source_interval_outside_signal")
            if abs(onset * sfreq - start) > 1e-6:
                flags.append("onset_not_exact_native_sample")
            if abs(duration * sfreq - samples) > 1e-6:
                flags.append("duration_not_exact_native_sample")
            if CODE_LABEL.get(code) != label:
                flags.append("source_code_label_mismatch_or_unknown")
            if label not in event_meta.get("trial_type", {}).get("Levels", {}):
                flags.append("label_absent_from_event_dictionary")
            if not annotation_counts[(start, code)]:
                flags.append("missing_matching_mne_annotation")
            if not marker_counts[(start, code)]:
                flags.append("missing_matching_native_marker")
            if label.startswith("mi_") and label != "mi_start" and duration != 10.0:
                flags.append("mi_duration_differs_from_source_dictionary_10s")
            if previous_end is not None and start < previous_end:
                flags.append("overlaps_previous_source_event")
            previous_end = max(stop, previous_end or stop)
            task = label.startswith("mi_") and label != "mi_start"
            complete = samples > 0 and 0 <= start < stop <= count
            event = {"event_id": f"{subject}/{run_id}/source-row-{index + 1:04d}",
                     "subject": subject, "published_subject_id": subject, "run": run_id,
                     "source_row_1based": index + 1, "source_values": dict(row),
                     "onset_seconds": onset, "duration_seconds": duration,
                     "native_start_sample_0based": start, "native_stop_sample_exclusive": stop,
                     "native_duration_samples": samples, "trial_type": label, "source_code": code,
                     "is_mi_execution_event": task, "source_interval_complete": complete,
                     "qualification_flags": flags,
                     "analysis_window_selected": False,
                     "gap_after_previous_event_seconds": ((start - ledger[-1]["native_stop_sample_exclusive"])
                                                           / sfreq) if ledger else None,
                     "acquisition_half": ("first_horizontal_vertical" if label in {"mi_l2r", "mi_t2b"}
                                          else "second_diagonal" if label in {"mi_ul2lr", "mi_ur2ll"}
                                          else "non_mi_execution")}
            if task and complete:
                event["source_task_numeric_sha256"] = interval_digest(raw, start, stop, block_samples)
                event["source_task_hash_convention"] = "all_channels/native_TSV_duration/volts/sample_major_le_f64"
            ledger.append(event)
        source_counts = Counter((e["native_start_sample_0based"], e["source_code"]) for e in ledger)
        comparison = {"source_event_count": len(ledger), "mne_annotation_count": len(annotations),
                      "native_marker_count": len(markers), "native_event_marker_count": len(event_markers),
                      "native_segment_boundary_count": len(markers) - len(event_markers),
                      "source_onset_code_equals_mne_multiset": source_counts == annotation_counts,
                      "source_onset_code_equals_marker_multiset": source_counts == marker_counts,
                      "annotation_onset_code_equals_marker_multiset": annotation_counts == marker_counts,
                      "native_marker_sizes_samples": dict(Counter(str(m["native_size_samples"])
                                                                   for m in markers)),
                      "duration_convention": "TSV durations retained; zero-size native markers do not define task duration"}
        result = {"schema_version": 1, "audited_at_utc": now(), "synthetic": False,
                  "status": "source_signal_stream_scan_completed", "source_file": relative_header,
                  "subject": subject, "published_subject_id": subject, "run": run_id,
                  "sampling_frequency_hz": sfreq, "n_channels": len(names), "n_samples": count,
                  "recording_seconds": count / sfreq, "channel_names": names,
                  "channel_types": raw.get_channel_types(), "mne_data_units": "volts",
                  "source_channel_units": [r["units"] for r in channels],
                  "native_brainvision_header": header_meta,
                  "mne_measurement_date_utc": str(raw.info["meas_date"]) if raw.info["meas_date"] else None,
                  "mne_annotations_origin_utc": str(raw.annotations.orig_time) if raw.annotations.orig_time else None,
                  "stream_block_samples": block_samples, "preload": False,
                  "all_values_finite": True,
                  "integrity_pass_scope": "finite signal, channel/unit/sfreq metadata and complete onset-code multisets; event qualification flags remain separate",
                  "whole_signal_numeric_sha256": digest.hexdigest(),
                  "numeric_hash_convention": "all_channels/volts/sample_major_le_f64",
                  "zero_channels": [n for n, z in zip(names, zero, strict=True) if z],
                  "constant_channels": [n for n, lo, hi in zip(names, minimum, maximum, strict=True) if lo == hi],
                  "channel_minimum_volts": minimum.tolist(), "channel_maximum_volts": maximum.tolist(),
                  "channel_rms_volts": np.sqrt(sum_squares / count).tolist(),
                  "source_events": comparison, "source_trial_type_counts": dict(Counter(e["trial_type"] for e in ledger)),
                  "qualification_flag_counts": dict(Counter(f for e in ledger for f in e["qualification_flags"])),
                  "native_markers": markers, "mne_annotations": annotations,
                  "fnirs_marker_origin_as_declared_in_README": "manual" if int(subject[4:]) in MANUAL_FNIRS_IDS else "automatic",
                  "marker_origin_scope": "README fNIRS grouping only; not an inferred EEG marker method",
                  "mne_version": mne.__version__, "numpy_version": np.__version__,
                  "analysis_status": "source_integrity_only_no_model_fits_or_trial_selection",
                  "design_boundary": "three ordered runs in one visit; direction pair confounded with run half; no followup or millisecond fNIRS synchronization claim"}
        result["all_integrity_checks_pass"] = all(comparison[f] for f in (
            "source_onset_code_equals_mne_multiset", "source_onset_code_equals_marker_multiset",
            "annotation_onset_code_equals_marker_multiset"))
        return result, ledger
    finally:
        raw.close()


def duplicate_groups(records: list[dict], digest_field: str, identity_field: str) -> list[dict]:
    grouped = defaultdict(list)
    for record in records:
        if record.get(digest_field):
            grouped[record[digest_field]].append(record)
    return [{"numeric_sha256": sha, "identities": [x[identity_field] for x in group],
             "published_subject_ids": sorted({x["subject"] for x in group}),
             "cross_published_subject": len({x["subject"] for x in group}) > 1}
            for sha, group in sorted(grouped.items()) if len(group) > 1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--header", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Prior audit output is preserved")
    result, ledger = audit_run(args.data_root, args.header)
    args.output.mkdir(parents=True)
    (args.output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output / "source_events.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"subject": result["subject"], "run": result["run"],
                      "integrity_checks_pass": result["all_integrity_checks_pass"],
                      "events": len(ledger), "n_samples": result["n_samples"]}))
    return 0 if result["all_integrity_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
