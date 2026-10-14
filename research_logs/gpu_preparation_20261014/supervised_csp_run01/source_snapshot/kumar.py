"""Pinned local Kumar EDF adapter and performance-independent split safeguards.

Signals remain MNE volts. Every source row is retained, including partial rows
excluded from the fixed tensor. Fixed, epoch-local preprocessing fits no state.
No model, download, label-dependent support selection or artifact removal occurs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import mne
import numpy as np
from scipy.signal import butter, resample_poly, sosfiltfilt

CHANNEL_NAMES = (
    "F7", "F3", "Fz", "F4", "F8", "FC5", "FC1", "FC2", "FC6", "C3", "Cz", "C4",
    "CP5", "CP1", "CP2", "CP6", "P7", "P3", "Pz", "P4", "P8", "POz",
)
LABELS = {"left_hand": 0, "right_hand": 1}
ROLES = {"source_train", "source_validation", "source_query", "target_support", "target_query"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(value: str | Path | dict) -> dict:
    return value if isinstance(value, dict) else json.loads(Path(value).read_text())


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_hash(data: np.ndarray, *, dtype: str = "<f8") -> str:
    return hashlib.sha256(np.asarray(data, dtype=dtype).tobytes(order="C")).hexdigest()


def tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def role_for(session: str, run: str, config: dict) -> str:
    split = config["split"]
    if session == split["source_session"]:
        matches = [role for role in ("source_train", "source_validation", "source_query")
                   if run in split[role + "_runs"]]
        require(len(matches) == 1, "Source run must have exactly one frozen role")
        return matches[0]
    require(session in split["target_sessions"], "Unfrozen session")
    return "target_support" if run in split["target_support_runs"] else "target_query"


def preprocess_epoch(epoch: np.ndarray, config: dict) -> np.ndarray:
    """Deterministic transform of this epoch only; no fitting or other trials."""
    p = config["preprocessing"]
    require(epoch.shape == (22, 2560), "Only exact 5-second 512-Hz epochs are allowed")
    require(np.isfinite(epoch).all(), "Nonfinite epoch")
    require(p["window_seconds"] == 5.0 and p["input_sfreq"] == 512.0
            and p["output_sfreq"] == 128.0 and p["band_hz"] == [8.0, 30.0],
            "Unreviewed preprocessing change")
    referenced = epoch - epoch.mean(axis=0, keepdims=True)
    sos = butter(4, [8, 30], btype="bandpass", fs=512, output="sos")
    filtered = sosfiltfilt(sos, referenced, axis=-1)
    result = resample_poly(filtered, up=1, down=4, axis=-1).astype(np.float32)
    require(result.shape == (22, 640) and np.isfinite(result).all(), "Invalid processed epoch")
    return result


def validate_split_trials(trials: list[dict], config: dict, *, require_hashes: bool = True) -> dict:
    """Reject identity, sample, role, cohort or exact-content leakage before fit."""
    require(len({t["trial_id"] for t in trials}) == len(trials), "Duplicate trial identity")
    development, final = set(config["development_subjects"]), set(config["final_test_subjects"])
    require(not development & final and development | final == set(config["subjects"]),
            "Development/final cohort overlap or missing identity")
    groups = defaultdict(list)
    for t in trials:
        require(t["subject"] in config["subjects"], "Unfrozen trial subject")
        require(t["role"] == role_for(t["session"], t["run"], config), "Frozen role mismatch")
        require(t["cohort"] == ("development" if t["subject"] in development else "final_test"),
                "Frozen cohort mismatch")
        require(t["included"] == (t["sample_count"] == 2560
                                 and t["duration_seconds"] == 5.0), "Partial eligibility mismatch")
        require(t["stop_sample_exclusive"] - t["start_sample"] == t["sample_count"],
                "Window sample identity mismatch")
        groups[t["source_file"]].append(t)
    for items in groups.values():
        items = sorted(items, key=lambda t: t["start_sample"])
        require(all(a["stop_sample_exclusive"] <= b["start_sample"]
                    for a, b in zip(items, items[1:])), "Overlapping source windows")
        require(len({t["role"] for t in items}) == 1, "Run crosses split roles")
    duplicate_checks = {}
    if require_hashes:
        for field in ("raw_window_numeric_sha256", "processed_window_numeric_sha256"):
            hashes = defaultdict(list)
            for t in trials:
                if field == "raw_window_numeric_sha256" or t["included"]:
                    require(len(t.get(field, "")) == 64, "Missing numerical window hash")
                    hashes[t[field]].append(t["trial_id"])
            duplicates = [ids for ids in hashes.values() if len(ids) > 1]
            duplicate_checks[field] = duplicates
            require(not duplicates, f"Exact numerical window duplicate: {field}")
    return {"trial_identity_unique": True, "source_windows_disjoint": True,
            "whole_runs_assigned_single_role": True, "cohorts_disjoint": True,
            "numerical_duplicate_groups": duplicate_checks}


def allowed_fit_trial_ids(metadata: list[dict], *, method: str, session: str,
                          component: str) -> list[str]:
    """Explicit learned-component access, excluding validation and every query."""
    require(method in {"source_only", "frozen_csp_lda_recalibration", "refit_csp_lda"},
            "Unknown baseline")
    require(component in {"csp", "lda", "scaler", "pca", "normalizer", "riemann_reference"},
            "Unknown component")
    adaptive = (method == "refit_csp_lda" and component in {"csp", "lda"}) or (
        method == "frozen_csp_lda_recalibration" and component == "lda")
    return [t["trial_id"] for t in metadata if t["role"] == "source_train" or (
        adaptive and t["role"] == "target_support" and t["session"] == session)]


@dataclass(frozen=True)
class KumarSubject:
    X: np.ndarray
    y: np.ndarray
    metadata: list[dict]
    source_events: list[dict]
    channel_names: tuple[str, ...]
    sfreq: float
    provenance: dict


def load_subject(data_root: str | Path, subject: str, config: str | Path | dict,
                 split_manifest: str | Path | dict | None = None, *,
                 allowed_roles: set[str] | None = None) -> KumarSubject:
    """Serially load one participant and verify frozen identities/content hashes.

    Config paths are repository-relative when the caller runs from the checkout.
    The tensor contains only included rows, aligned to metadata and y. Provenance
    retains all source identities, official hashes, CPz and actual acquisition UTC.
    """
    config = read_json(config)
    if allowed_roles is not None:
        require(bool(allowed_roles) and allowed_roles <= ROLES, "Invalid role allowlist")
    require(re.fullmatch(r"sub-\d+", subject) is not None and subject in config["subjects"],
            "Unfrozen subject")
    root = Path(data_root)
    entries_list = json.loads(Path(config["source_manifest"]).read_text())
    entries = {e["path"]: e for e in entries_list}
    require(len(entries) == len(entries_list), "Duplicate pinned source paths")
    verified = {}

    def verify(relative: str) -> Path:
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
                "Unsafe source path")
        require(relative in entries, f"Unpinned source file: {relative}")
        path, entry = root / relative, entries[relative]
        require(path.is_file() and path.stat().st_size == entry["size"], "Source file size changed")
        sha = sha256_file(path)
        if entry["checksum_algorithm"] == "sha256":
            digest = sha
        elif entry["checksum_algorithm"] == "git":
            data = path.read_bytes()
            digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        else:
            raise ValueError("Unsupported official checksum")
        require(digest == entry["checksum"], f"Official source checksum mismatch: {relative}")
        verified[relative] = {"sha256": sha, "official_checksum": digest,
                              "official_algorithm": entry["checksum_algorithm"]}
        return path

    description = json.loads(verify("dataset_description.json").read_text())
    require(description["Version"] == "1.0.5" and description["DatasetType"] == "derivative"
            and description["License"] == "CC-BY-4.0", "Unexpected source version/license")
    prior_root = Path(config["prior_signal_audit"])
    prior = json.loads((prior_root / "source_events.json").read_text())
    source_rows = [dict(e) for e in prior if e["subject"] == subject]
    require(len(source_rows) == 400, "Pinned subject source-event coverage changed")
    if allowed_roles is not None:
        source_rows = [e for e in source_rows
                       if role_for(e["session"], e["run"], config) in allowed_roles]
    by_file = defaultdict(list)
    for e in source_rows:
        by_file[e["source_file"]].append(e)
    chunks, metadata, runs, acquisition_times = [], [], [], []
    cohort = "development" if subject in config["development_subjects"] else "final_test"
    for session in [f"ses-{i}" for i in range(6)]:
        scan_relative = f"{subject}/{session}/{subject}_{session}_scans.tsv"
        scan_rows = tsv(verify(scan_relative))
        expected_runs = 4 if session in {"ses-0", "ses-1"} else 3
        require(len(scan_rows) == expected_runs, "Actual scan run count changed")
        for run_index, scan in enumerate(scan_rows):
            run = f"run-{run_index}"
            if allowed_roles is not None and role_for(session, run, config) not in allowed_roles:
                continue
            relative = f"{subject}/{session}/{scan['filename']}"
            require(relative.endswith(f"_{run}_eeg.edf"), "Run ordering differs from scans.tsv")
            timestamp = datetime.fromisoformat(scan["acq_time"].replace("Z", "+00:00"))
            require(timestamp.tzinfo is not None, "Acquisition timezone unspecified")
            acquisition_times.append(timestamp)
            prefix = relative.removesuffix("_eeg.edf")
            info = json.loads(verify(prefix + "_eeg.json").read_text())
            event_info = json.loads(verify(prefix + "_events.json").read_text())
            rows, channels = tsv(verify(prefix + "_events.tsv")), tsv(verify(prefix + "_channels.tsv"))
            expected = by_file[relative]
            require(len(rows) == len(expected) == 20, "Source rows changed")
            require(info["EEGReference"] == "CPz" and info["EEGChannelCount"] == 22
                    and info["SamplingFrequency"] == 512.0, "Acquisition metadata changed")
            require(event_info["onset"]["Units"] == event_info["duration"]["Units"] == "s"
                    and "First sample is 0" in event_info["sample"]["Description"],
                    "Event convention changed")
            raw = mne.io.read_raw_edf(verify(relative), preload=False, verbose="ERROR")
            try:
                require(raw.first_samp == 0 and raw.info["sfreq"] == 512
                        and tuple(raw.ch_names) == CHANNEL_NAMES
                        and raw.get_channel_types() == ["eeg"] * 22, "EDF channels/rate changed")
                require(tuple(c["name"] for c in channels) == CHANNEL_NAMES and all(
                    c["units"] == raw._orig_units[c["name"]] == "µV" for c in channels),
                    "Physical unit/channel order changed")
                require(len(raw.annotations) == 20 and list(raw.annotations.description)
                        == [r["trial_type"] for r in rows], "EDF cue annotation changed")
                whole_hash = hashlib.sha256()
                peak, squares, values = 0.0, 0.0, 0
                for start in range(0, int(raw.n_times), 16384):
                    block = raw.get_data(start=start, stop=min(start + 16384, int(raw.n_times)))
                    require(np.isfinite(block).all(), "Nonfinite continuous source signal")
                    whole_hash.update(np.asarray(block, dtype="<f8").tobytes(order="C"))
                    peak = max(peak, float(np.abs(block).max()))
                    squares += float(np.square(block).sum())
                    values += block.size
                receipt = json.loads((prior_root / "runs" / (
                    relative.replace("/", "__") + ".json")).read_text())
                require(whole_hash.hexdigest() == receipt["whole_signal_numeric_sha256"],
                        "Whole continuous numerical source identity changed")
                role = role_for(session, run, config)
                for i, (row, e) in enumerate(zip(rows, expected)):
                    require(e["source_row"] == i + 1 and e["label"] == row["trial_type"]
                            and e["stored_value"] == int(row["value"]) == LABELS[e["label"]] + 1
                            and e["start_sample"] == int(row["sample"])
                            and e["onset_seconds"] == float(row["onset"])
                            and e["duration_seconds"] == float(row["duration"]),
                            "Stored source-event identity changed")
                    require(abs(e["onset_seconds"] * 512 - e["start_sample"]) < 1e-6
                            and abs(e["duration_seconds"] * 512 - e["sample_count"]) < 1e-3
                            and 0 <= e["start_sample"] < e["stop_sample_exclusive"] <= raw.n_times,
                            "Source sample/window boundary changed")
                    require(abs(float(raw.annotations.onset[i]) - e["onset_seconds"]) < 1e-6
                            and abs(float(raw.annotations.duration[i]) - e["duration_seconds"]) < 1e-6,
                            "EDF annotation time changed")
                    e.update(role=role, cohort=cohort, acquisition_time_utc=scan["acq_time"],
                             included=e["sample_count"] == 2560 and e["duration_seconds"] == 5.0,
                             raw_file_sha256=verified[relative]["sha256"],
                             raw_numeric_unit="V", processed_numeric_unit="V")
                    e["exclusion_reason"] = None if e["included"] else "partial_source_event_under_5s"
                    e["analysis_eligibility"] = "included_full_5s" if e["included"] else "excluded_partial"
                    epoch = raw.get_data(start=e["start_sample"], stop=e["stop_sample_exclusive"])
                    e["raw_window_numeric_sha256"] = numeric_hash(epoch)
                    e["raw_peak_to_peak_max_volts"] = float(np.ptp(epoch, axis=-1).max())
                    e["qc_peak_to_peak_over_250uv"] = e["raw_peak_to_peak_max_volts"] > 250e-6
                    e["qc_primary_action"] = "retain_flagged_no_artifact_certification"
                    if e["included"]:
                        processed = preprocess_epoch(epoch, config)
                        e["processed_window_numeric_sha256"] = numeric_hash(processed, dtype="<f4")
                        e["processed_sample_count"] = 640
                        chunks.append(processed)
                        metadata.append(e)
                runs.append({"subject": subject, "session": session, "run": run,
                             "source_file": relative, "role": role,
                             "acquisition_time_utc": scan["acq_time"],
                             "raw_file_sha256": verified[relative]["sha256"],
                             "whole_signal_numeric_sha256": whole_hash.hexdigest(),
                             "peak_absolute_volts": peak, "global_rms_volts": (squares / values)**0.5,
                             "all_continuous_samples_finite": True, "n_times": int(raw.n_times)})
            finally:
                raw.close()
    require(all(a < b for a, b in zip(acquisition_times, acquisition_times[1:])),
            "Acquisition chronology does not support nominal session/run order")
    validate_split_trials(source_rows, config)
    if split_manifest is not None:
        frozen = {t["trial_id"]: t for t in read_json(split_manifest)["trials"]
                  if t["subject"] == subject}
        require(len(frozen) == 400, "Frozen split source-event coverage changed")
        for t in source_rows:
            require(t == frozen[t["trial_id"]], "Frozen trial metadata or content hash changed")
    return KumarSubject(np.stack(chunks), np.array([LABELS[t["label"]] for t in metadata]),
                        metadata, source_rows, CHANNEL_NAMES, 128.0,
                        {"subject": subject, "cohort": cohort, "synthetic": False,
                         "raw_reference": "CPz", "processed_reference": "average_all22",
                         "numeric_unit": "V", "runs": runs, "verified_source_files": verified,
                         "source_events": len(source_rows), "included_trials": len(metadata),
                         "excluded_trials": len(source_rows) - len(metadata),
                         "class_counts": dict(Counter(t["label"] for t in metadata)),
                         "learned_preprocessing": False, "chronology_strictly_increasing": True})
