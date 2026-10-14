#!/usr/bin/env python3
"""Audit every fixed-v11 raw SET/FDT pair with bounded, temporary extraction.

The source events remain point markers unless their own positive durations define
a window. This program neither preprocesses EEG nor fits a model.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import warnings
import zipfile
import zlib
from pathlib import Path, PurePosixPath

import mne
import numpy as np
import scipy
import scipy.io

from download_wangliu2026_source import enforce_transport, file_hashes, utc_now, write_json

BLOCK_SAMPLES = 16_384
SCALP_LABELS = ("Fpz Fp1 Fp2 AF3 AF4 AF7 AF8 Fz F1 F2 F3 F4 F5 F6 F7 F8 "
                "FCz FC1 FC2 FC3 FC4 FC5 FC6 FT7 FT8 Cz C1 C2 C3 C4 C5 C6 T7 T8 "
                "CP1 CP2 CP3 CP4 CP5 CP6 TP7 TP8 Pz P3 P4 P5 P6 P7 P8 POz PO3 "
                "PO4 PO5 PO6 PO7 PO8 Oz O1 O2").split()
AUX_TYPES = {"ECG": "ecg", "HEOR": "eog", "HEOL": "eog", "VEOU": "eog", "VEOL": "eog"}
PHASE_ORDER = {"pre": 0, "post": 1, "follow": 2}
EVENT_LABELS = {"1": "rest", "2": "affected_hand_motor_imagery", "3": "sixth_finger_motor_imagery"}
HASH_CONVENTION = ("MNE volts; little-endian float64; C-order channels-by-samples in "
                   "chronological fixed 16384-sample blocks (final block shorter); "
                   "channel labels/order and sample count are separate comparison keys")


def plain(value):
    if isinstance(value, np.ndarray):
        return [plain(x) for x in value.tolist()]
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(x) for x in value]
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    return value


def dict_list(value) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, np.ndarray):
        return list(value.flat) if value.size else []
    return list(value) if value is not None else []


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    entries = archive.infolist()
    names = set()
    for entry in entries:
        name = entry.filename
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or ".." in path.parts or "\\" in name
                or re.match(r"^[A-Za-z]:", name)
                or name.rstrip("/") != str(path) or "\x00" in name
                or stat.S_ISLNK(entry.external_attr >> 16)):
            raise ValueError("Unsafe ZIP entry")
        if name in names:
            raise ValueError("Duplicate ZIP entry name")
        names.add(name)
    return entries


def extract_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, destination: Path) -> dict:
    digest = hashlib.sha256()
    count = crc = 0
    try:
        with archive.open(info) as source, destination.open("xb") as target:
            for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
                target.write(block)
                digest.update(block)
                count += len(block)
                crc = zlib.crc32(block, crc)
                if count > info.file_size:
                    raise ValueError("ZIP member exceeds directory size")
        if count != info.file_size or crc != info.CRC:
            raise ValueError("ZIP member CRC/size mismatch")
        return {"member": info.filename, "bytes": count, "sha256": digest.hexdigest(),
                "crc32": f"{crc:08x}", "central_directory_crc32": f"{info.CRC:08x}",
                "crc32_verified": True, "extraction": "one-pair temporary cache"}
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def channel_types(labels: list[str]) -> list[str]:
    return [AUX_TYPES.get(name, "eeg" if name in SCALP_LABELS else "misc") for name in labels]


def source_identity(member: str) -> dict:
    match = re.fullmatch(r"(sub-\d{2})/(pre|post|follow)/\1_([BT])_\2_(0[1-4])_original\.set", member)
    if not match:
        raise ValueError("Unexpected published raw recording path")
    subject, phase, group, run = match.groups()
    return {"source_id": member.removesuffix(".set"), "subject_id": subject,
            "phase": phase, "phase_order": PHASE_ORDER[phase], "group_code": group,
            "run": int(run), "set_member": member,
            "fdt_member": member.removesuffix(".set") + ".fdt"}


def native_events(eeg: dict, source_id: str) -> list[dict]:
    sfreq, n_times = float(eeg["srate"]), int(eeg["pnts"])
    events = []
    for index, event in enumerate(dict_list(eeg.get("event")), 1):
        label = str(event.get("type", ""))
        latency = float(event["latency"])
        duration = float(event["duration"]) if "duration" in event else None
        onset = latency - 1.0
        integral_onset = np.isfinite(onset) and abs(onset - round(onset)) <= 1e-8
        integral_duration = (duration is not None and np.isfinite(duration)
                             and abs(duration - round(duration)) <= 1e-8)
        eligible = bool(integral_onset and integral_duration and duration > 0
                        and onset >= 0 and onset + duration <= n_times and label in EVENT_LABELS)
        if duration is None:
            reason = "native_duration_absent_point_marker_no_window_inferred"
        elif duration == 0:
            reason = "native_duration_zero_point_marker_no_window_inferred"
        elif not eligible:
            reason = "native_window_nonintegral_unknown_label_or_outside_recording"
        else:
            reason = "positive_native_duration_complete_window"
        events.append({"event_id": f"{source_id}/event-{index:03d}",
                       "source_id": source_id, "source_event_index_1based": index,
                       "native_fields": plain(event), "native_type": label,
                       "task_label": EVENT_LABELS.get(label, "unmapped_native_event"),
                       "latency_1based": latency, "onset_sample_0based": onset,
                       "onset_seconds": onset / sfreq, "duration_samples": duration,
                       "duration_seconds": None if duration is None else duration / sfreq,
                       "point_marker_within_recording": bool(np.isfinite(onset) and 0 <= onset < n_times),
                       "native_window_eligible": eligible, "window_status": reason,
                       "analysis_window_inferred": False})
    return events


def numeric_digest(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype="<f8").tobytes(order="C")).hexdigest()


def audit_signal(raw, eeg_picks: list[int]) -> dict:
    n_channels = len(raw.ch_names)
    whole, scalp = hashlib.sha256(), hashlib.sha256()
    low, high = np.full(n_channels, np.inf), np.full(n_channels, -np.inf)
    mean, m2, counts = np.zeros(n_channels), np.zeros(n_channels), np.zeros(n_channels, dtype=np.int64)
    nonfinite, zeros = np.zeros(n_channels, dtype=np.int64), np.zeros(n_channels, dtype=np.int64)
    for start in range(0, raw.n_times, BLOCK_SAMPLES):
        data = raw.get_data(start=start, stop=min(start + BLOCK_SAMPLES, raw.n_times))
        whole.update(np.asarray(data, dtype="<f8").tobytes(order="C"))
        scalp.update(np.asarray(data[eeg_picks], dtype="<f8").tobytes(order="C"))
        finite = np.isfinite(data)
        nonfinite += (~finite).sum(axis=1)
        zeros += (data == 0).sum(axis=1)
        # Stable blockwise moments: a large DC offset must not hide a constant channel.
        for channel in range(n_channels):
            values = data[channel, finite[channel]]
            size = len(values)
            if not size:
                continue
            low[channel] = min(low[channel], float(values.min()))
            high[channel] = max(high[channel], float(values.max()))
            block_mean = float(values.mean())
            total = int(counts[channel]) + size
            delta = block_mean - mean[channel]
            m2[channel] += float(np.square(values - block_mean).sum()) + delta ** 2 * counts[channel] * size / total
            mean[channel] += delta * size / total
            counts[channel] = total
    per_channel = []
    types = channel_types(raw.ch_names)
    for index, name in enumerate(raw.ch_names):
        valid = counts[index] > 0
        offset_threshold = 0.001 if types[index] == "eeg" else 0.1
        per_channel.append({"name": name, "native_column_index_0based": index,
                            "verified_label_type": types[index],
                            "finite_samples": int(counts[index]), "nonfinite_samples": int(nonfinite[index]),
                            "exact_zero_samples": int(zeros[index]),
                            "minimum_volts": float(low[index]) if valid else None,
                            "maximum_volts": float(high[index]) if valid else None,
                            "mean_volts": float(mean[index]) if valid else None,
                            "std_volts": float(np.sqrt(m2[index] / counts[index])) if valid else None,
                            "exact_constant": bool(valid and low[index] == high[index]),
                            "large_absolute_mean_flag": bool(valid and abs(mean[index]) > offset_threshold),
                            "mean_flag_threshold_volts": offset_threshold,
                            "scalp_peak_over_1mV_flag": bool(types[index] == "eeg" and valid
                                                            and max(abs(low[index]), abs(high[index])) > 0.001)})
    return {"all_continuous_samples_finite": bool(not nonfinite.any()),
            "all64_numeric_sha256": whole.hexdigest(), "scalp59_numeric_sha256": scalp.hexdigest(),
            "numeric_hash_convention": HASH_CONVENTION,
            "numeric_hash_channel_labels_all": list(raw.ch_names),
            "numeric_hash_channel_labels_scalp": [raw.ch_names[i] for i in eeg_picks],
            "continuous_numeric_values": int(raw.n_times) * n_channels,
            "per_channel": per_channel,
            "constant_channels": [x["name"] for x in per_channel if x["exact_constant"]],
            "large_absolute_mean_channels": [x["name"] for x in per_channel if x["large_absolute_mean_flag"]],
            "scalp_peak_over_1mV_channels": [x["name"] for x in per_channel if x["scalp_peak_over_1mV_flag"]],
            "qc_flags_are_descriptive": True, "expert_artifact_quality_certified": False}


def duplicate_groups(rows: list[dict], field: str, id_field: str) -> list[dict]:
    groups = collections.defaultdict(list)
    for row in rows:
        if row.get(field):
            labels = row.get("numeric_hash_channel_labels_scalp" if field.startswith("scalp") else "numeric_hash_channel_labels_all", [])
            key = (row[field], tuple(labels), row.get("n_times"), row.get("sampling_rate_hz"))
            groups[key].append(row)
    output = []
    for (digest, labels, n_times, sfreq), group in groups.items():
        if len(group) < 2:
            continue
        subjects = {r["subject_id"] for r in group}
        phases_by_subject = collections.defaultdict(set)
        for row in group:
            phases_by_subject[row["subject_id"]].add(row["phase"])
        output.append({"numeric_sha256": digest, "channel_labels": list(labels),
                       "n_times": n_times, "sampling_rate_hz": sfreq,
                       "source_ids": [r[id_field] for r in group], "subject_ids": sorted(subjects),
                       "cross_published_identity": len(subjects) > 1,
                       "within_subject_cross_phase_reuse": any(len(x) > 1 for x in phases_by_subject.values()),
                       "within_subject_same_phase_run_reuse": len(group) > len(set((r["subject_id"], r["phase"]) for r in group)),
                       "scope": "exact numerical content; correct source ownership and biological independence unresolved"})
    return output


def audit_pair(archive: zipfile.ZipFile, set_info: zipfile.ZipInfo,
               fdt_info: zipfile.ZipInfo, scratch_root: Path) -> tuple[dict, list[dict], list[dict]]:
    identity = source_identity(set_info.filename)
    budget = set_info.file_size + fdt_info.file_size
    if budget > 64 * 1024 * 1024:
        raise ValueError("One-pair scratch exceeds fixed 64 MiB budget")
    if shutil.disk_usage(scratch_root).free < budget + 64 * 1024 * 1024:
        raise ValueError("Insufficient one-pair scratch space")
    with tempfile.TemporaryDirectory(prefix="wangliu-pair-", dir=scratch_root) as directory:
        temporary = Path(directory)
        set_path, fdt_path = temporary / Path(set_info.filename).name, temporary / Path(fdt_info.filename).name
        members = [extract_member(archive, set_info, set_path), extract_member(archive, fdt_info, fdt_path)]
        mat = scipy.io.loadmat(set_path, simplify_cells=True, uint16_codec="latin1")
        eeg = mat.get("EEG", mat)
        labels = [str(channel["labels"]) for channel in dict_list(eeg["chanlocs"])]
        if len(labels) != len(set(labels)):
            raise ValueError("Duplicate native channel labels")
        n_channels, n_times, sfreq = int(eeg["nbchan"]), int(eeg["pnts"]), float(eeg["srate"])
        if n_channels != len(labels) or int(eeg["trials"]) != 1 or sfreq <= 0:
            raise ValueError("Native header dimensions invalid")
        if fdt_info.file_size != n_channels * n_times * 4:
            raise ValueError("FDT byte dimensions differ from native SET")
        reference = str(eeg["data"])
        if reference != fdt_path.name or str(eeg.get("datfile", reference)) != fdt_path.name:
            raise ValueError("Native SET data reference is not its published paired FDT basename")
        types = channel_types(labels)
        eeg_picks = [index for index, kind in enumerate(types) if kind == "eeg"]
        events = native_events(eeg, identity["source_id"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            raw = mne.io.read_raw_eeglab(set_path, preload=False, uint16_codec="latin1", verbose="ERROR")
            reader_defaults = dict(collections.Counter(raw.get_channel_types()))
            raw.set_channel_types(dict(zip(labels, types)), verbose="ERROR")
            if raw.n_times != n_times or raw.info["sfreq"] != sfreq or raw.ch_names != labels:
                raise ValueError("Native MNE reader/header disagreement")
            annotations = [{"onset_seconds": float(a["onset"]), "duration_seconds": float(a["duration"]),
                            "description": str(a["description"])} for a in raw.annotations]
            aligned = len(annotations) == len(events) and all(
                event["native_type"] == annotation["description"]
                and abs(event["onset_seconds"] - annotation["onset_seconds"]) < 1e-8
                and abs((event["duration_seconds"] or 0.0) - annotation["duration_seconds"]) < 1e-8
                for event, annotation in zip(events, annotations))
            signal = audit_signal(raw, eeg_picks)
            for event in events:
                event.update({k: identity[k] for k in ("subject_id", "phase", "phase_order", "group_code", "run")})
                if event["native_window_eligible"]:
                    start, count = round(event["onset_sample_0based"]), round(event["duration_samples"])
                    digest = hashlib.sha256()
                    for offset in range(start, start + count, BLOCK_SAMPLES):
                        values = raw.get_data(picks=eeg_picks, start=offset, stop=min(offset + BLOCK_SAMPLES, start + count))
                        digest.update(np.asarray(values, dtype="<f8").tobytes(order="C"))
                    event.update(scalp59_native_window_sha256=digest.hexdigest(), n_times=count,
                                 sampling_rate_hz=sfreq, numeric_hash_channel_labels_scalp=[labels[i] for i in eeg_picks])
            raw.close()
        history = str(eeg.get("history", ""))
        report = {**identity, **signal, "n_times": n_times, "sampling_rate_hz": sfreq,
                  "native_channels": n_channels, "channel_type_counts_from_labels": dict(collections.Counter(types)),
                  "channel_layout_matches_verified_59_scalp_plus5_aux": labels == SCALP_LABELS + list(AUX_TYPES),
                  "mne_default_channel_type_counts": reader_defaults,
                  "mne_aux_type_assignment": "explicit native verified labels; samples unchanged",
                  "native_reference_field": plain(eeg.get("ref")),
                  "native_channel_locations": plain(dict_list(eeg["chanlocs"])),
                  "native_data_reference": reference, "native_datfile": plain(eeg.get("datfile")),
                  "mne_physical_units": "volts", "native_fdt_dtype": "little-endian float32 EEGLAB microvolt values",
                  "mne_native_unit_scale": "EEGLAB microvolts to volts, 1e-6; no extra calibration/reference/filter applied",
                  "set_header_fields": sorted(k for k in eeg if not k.startswith("__")),
                  "native_subject_field": plain(eeg.get("subject")), "native_group_field": plain(eeg.get("group")),
                  "native_session_field": plain(eeg.get("session")),
                  "native_history_text": history, "native_history_sha256": hashlib.sha256(history.encode()).hexdigest(),
                  "native_ica_shapes": {k: list(np.asarray(eeg.get(k, [])).shape) for k in ("icaweights", "icasphere", "icawinv")},
                  "source_variant": "official original continuous raw; processed whole archive not downloaded",
                  "preprocessing_performed": [], "source_event_count": len(events),
                  "source_event_type_counts": dict(collections.Counter(e["native_type"] for e in events)),
                  "mne_annotations": annotations, "native_events_match_mne_annotations": aligned,
                  "native_positive_duration_window_count": sum(e["native_window_eligible"] for e in events),
                  "reader_warning_types": sorted({type(w.message).__name__ for w in caught}),
                  "scratch_pair_bytes": budget, "scratch_deleted_on_exit": True,
                  "all_source_bytes_crc_verified": True, "future_analysis_qualified": False,
                  "future_analysis_status": "source ingested; scientific task-window/reference/artifact/split gates still required"}
    return report, events, members


def audit_archive(archive_path: Path, output: Path, scratch_root: Path) -> dict:
    # Whole-source transport is rechecked before any audit output or scratch mutation.
    count, md5, sha = file_hashes(archive_path)
    enforce_transport(count, md5)
    if output.exists() and any(output.glob("source_*.json*")):
        raise ValueError("Use a new audit output; preserve prior ledgers")
    output.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    records, all_events, members = [], [], []
    with zipfile.ZipFile(archive_path) as archive:
        entries = safe_members(archive)
        by_name = {entry.filename: entry for entry in entries}
        sets = sorted((entry for entry in entries if entry.filename.endswith(".set")),
                      key=lambda entry: (source_identity(entry.filename)["subject_id"],
                                         source_identity(entry.filename)["phase_order"],
                                         source_identity(entry.filename)["run"]))
        files = [entry for entry in entries if not entry.is_dir()]
        if len(sets) != 268 or len(files) != 536 or len(entries) != 627:
            raise ValueError("Fixed-v11 archive directory coverage mismatch")
        write_json(output / "source_archive_directory.json", {
            "whole_archive_bytes": count, "official_md5": md5, "sha256": sha,
            "entries": [{"member": x.filename, "directory": x.is_dir(), "bytes": x.file_size,
                         "compressed_bytes": x.compress_size, "crc32": f"{x.CRC:08x}"} for x in entries],
            "entry_names_unique_and_safe": True, "entry_count": len(entries),
            "file_count": len(files), "uncompressed_file_bytes": sum(x.file_size for x in files)})
        with (output / "source_record_ledger.jsonl").open("x") as record_stream, \
                (output / "source_event_ledger.jsonl").open("x") as event_stream, \
                (output / "source_member_sha256_ledger.jsonl").open("x") as member_stream:
            for index, set_info in enumerate(sets, 1):
                fdt_name = set_info.filename.removesuffix(".set") + ".fdt"
                if fdt_name not in by_name:
                    raise ValueError("Missing paired FDT")
                report, events, pair_members = audit_pair(archive, set_info, by_name[fdt_name], scratch_root)
                records.append(report)
                all_events.extend(events)
                members.extend(pair_members)
                record_stream.write(json.dumps(report, allow_nan=False) + "\n")
                for event in events:
                    event_stream.write(json.dumps(event, allow_nan=False) + "\n")
                for member in pair_members:
                    member_stream.write(json.dumps(member, allow_nan=False) + "\n")
                for stream in (record_stream, event_stream, member_stream):
                    stream.flush()
                write_json(output / "progress.json", {"status": "auditing", "records_completed": index,
                           "records_expected": len(sets), "source_events_retained": len(all_events),
                           "last_source_id": report["source_id"], "updated_at_utc": utc_now()})
                if index % 10 == 0 or index == len(sets):
                    print(json.dumps({"records_completed": index, "events": len(all_events)}), flush=True)
    identities = sorted({r["subject_id"] for r in records})
    missing = [subject for subject in identities if not any(r["subject_id"] == subject and r["phase"] == "follow" for r in records)]
    duplicates = {field: duplicate_groups(records, field, "source_id") for field in ("all64_numeric_sha256", "scalp59_numeric_sha256")}
    duplicates["scalp59_native_window_sha256"] = duplicate_groups(all_events, "scalp59_native_window_sha256", "event_id")
    write_json(output / "source_exact_content_duplicates.json", duplicates)
    summary = {"status": "completed_full_source_audit", "started_at_utc": started,
               "finished_at_utc": utc_now(), "official_archive_md5_verified": True,
               "archive_bytes": count, "archive_md5": md5, "archive_sha256": sha,
               "subject_count": len(identities), "recordings": len(records), "source_event_count": len(all_events),
               "member_crc_and_sha256_verified_count": len(members),
               "group_subject_counts": dict(collections.Counter(next(r["group_code"] for r in records if r["subject_id"] == subject) for subject in identities)),
               "recording_count_by_phase": dict(collections.Counter(r["phase"] for r in records)),
               "subject_count_by_phase": {phase: len({r["subject_id"] for r in records if r["phase"] == phase}) for phase in PHASE_ORDER},
               "missing_followup_ids": missing, "missing_followup_reason": "published absence; no recordings invented",
               "all_present_subject_phases_have_runs_1to4": all(sorted(r["run"] for r in records if r["subject_id"] == subject and r["phase"] == phase) == [1, 2, 3, 4] for subject in identities for phase in PHASE_ORDER if any(r["subject_id"] == subject and r["phase"] == phase for r in records)),
               "all_raw_64columns_59scalp_1ECG_4EOG_verified": all(r["channel_layout_matches_verified_59_scalp_plus5_aux"] for r in records),
               "all_raw_250Hz_verified": all(r["sampling_rate_hz"] == 250 for r in records),
               "all_source_samples_finite": all(r["all_continuous_samples_finite"] for r in records),
               "records_with_nonfinite_samples": [r["source_id"] for r in records if not r["all_continuous_samples_finite"]],
               "all_native_events_match_mne_annotations": all(r["native_events_match_mne_annotations"] for r in records),
               "source_event_type_counts": dict(collections.Counter(e["native_type"] for e in all_events)),
               "native_duration_status_counts": dict(collections.Counter(e["window_status"] for e in all_events)),
               "positive_native_duration_windows_audited": sum(e["native_window_eligible"] for e in all_events),
               "task_window_duplicate_check_scope": "only positive complete source-defined native durations; absent/zero duration point markers yield no invented windows",
               "exact_duplicate_group_counts": {key: len(value) for key, value in duplicates.items()},
               "exact_cross_identity_duplicate_groups": {key: sum(x["cross_published_identity"] for x in value) for key, value in duplicates.items()},
               "within_person_cross_phase_content_reuse_groups": {key: sum(x["within_subject_cross_phase_reuse"] for x in value) for key, value in duplicates.items()},
               "records_with_constant_channels": sum(bool(r["constant_channels"]) for r in records),
               "constant_channel_record_counts": dict(collections.Counter(name for r in records for name in r["constant_channels"])),
               "records_with_large_absolute_mean_flags": sum(bool(r["large_absolute_mean_channels"]) for r in records),
               "records_with_scalp_peak_over_1mV_flags": sum(bool(r["scalp_peak_over_1mV_channels"]) for r in records),
               "observed_reference_fields": sorted({str(r["native_reference_field"]) for r in records}),
               "numeric_hash_convention": HASH_CONVENTION, "block_samples": BLOCK_SAMPLES,
               "scratch_max_pair_bytes": max(r["scratch_pair_bytes"] for r in records),
               "scratch_budget_bytes": 64 * 1024 * 1024, "scratch_leftover_pair_directories": len(list(scratch_root.glob("wangliu-pair-*"))),
               "whole_raw_extraction_retained": False, "processed_whole_archive_downloaded": False,
               "preprocessing_performed": [], "model_fits_performed": False,
               "root_metadata_conflicts_preserved": ["events.json trailing comma", "events.tsv generic example, not run timing", "root 60EEG/average/0EOG differs from raw64/common/5aux", "participants.json names differ from actual TSV"],
               "future_analysis_qualified": False,
               "future_analysis_gates": ["freeze native-event task windows explicitly", "source units/reference and artifact QC sensitivity", "freeze dataset-specific subject/run/phase splits after duplicate audit", "clinical outcome and decoder-update linkage remain absent"],
               "scientific_boundary": "Stroke longitudinal observational source audit. Exact-copy absence does not prove biological independence. Offline decoding, algorithm causality, human skill retention and clinical outcome benefit are not established."}
    write_json(output / "source_audit_summary.json", summary)
    provenance = {"python": sys.version, "mne": mne.__version__, "numpy": np.__version__,
                  "scipy": scipy.__version__, "source_git_commit": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
                  "auditor_sha256": file_hashes(Path(__file__))[2],
                  "downloader_sha256": file_hashes(Path(__file__).with_name("download_wangliu2026_source.py"))[2],
                  "archive_sha256": sha, "author_code_executed": False,
                  "external_model_fit": False, "whole_archive_bytes_rehashed_before_audit": True}
    write_json(output / "runtime_provenance.json", provenance)
    write_json(output / "progress.json", {"status": "completed", "records_completed": len(records), "source_events_retained": len(all_events), "updated_at_utc": utc_now()})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    args = parser.parse_args()
    result = audit_archive(args.archive, args.output, args.scratch_root)
    print(json.dumps({key: result[key] for key in ("status", "recordings", "source_event_count", "archive_sha256")}), flush=True)


if __name__ == "__main__":
    main()
