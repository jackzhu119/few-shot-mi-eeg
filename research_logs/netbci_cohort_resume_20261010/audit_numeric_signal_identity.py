#!/usr/bin/env python3
"""Read-only numerical identity audit of the existing 240 NETBCI EDF derivatives.

Reads one continuous run at a time. Does not preprocess, train, download, modify
source data, or change cohort eligibility. Source task windows include all real
events, including the duration-ineligible event, without padding or truncation.
"""

from __future__ import annotations

import configparser
import csv
import gc
import hashlib
import json
import os
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[variable] = "2"
os.environ.setdefault("XDG_CACHE_HOME", "/workspace/.cache")
os.environ.setdefault("MPLCONFIGDIR", "/workspace/.cache/matplotlib")
os.environ.setdefault("MNE_DONTWRITE_HOME", "true")

import mne  # noqa: E402 -- set numerical-thread/cache environment before import
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LOG = REPO / "research_logs/netbci_cohort_resume_20261010"
DATA = REPO / "data/netbci2026/nm000305/v1.0.0"
AUDITS = LOG / "audits_full_windows"
OUTPUT = LOG / "numeric_signal_identity.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def canonical_hash(values: np.ndarray) -> tuple[str, str]:
    """SHA of dtype/shape/order plus exact little-endian float64 C-order values."""
    canonical = np.ascontiguousarray(values, dtype="<f8")
    assert np.isfinite(canonical).all()
    descriptor = json.dumps({"dtype": "<f8", "shape": list(canonical.shape),
                             "order": "C"}, sort_keys=True,
                            separators=(",", ":")).encode("ascii")
    digest = hashlib.sha256()
    digest.update(b"netbci-numeric-array-v1\0")
    digest.update(descriptor + b"\0")
    payload = memoryview(canonical).cast("B")
    digest.update(payload)
    return digest.hexdigest(), hashlib.sha256(payload).hexdigest()


def group_identities(rows: list[dict], *, unit: str) -> list[dict]:
    by_hash = defaultdict(list)
    for row in rows:
        by_hash[row["numeric_sha256"]].append(row)
    groups = []
    for digest, members in by_hash.items():
        if len(members) < 2:
            continue
        subject_sessions = {(row["subject"], row["session"]) for row in members}
        subjects = {row["subject"] for row in members}
        sessions_by_subject = defaultdict(set)
        for row in members:
            sessions_by_subject[row["subject"]].add(row["session"])
        groups.append({
            "numeric_sha256": digest, "unit": unit,
            "member_count": len(members),
            "same_person_cross_session": any(len(sessions) > 1
                                              for sessions in sessions_by_subject.values()),
            "cross_subject": len(subjects) > 1,
            "subjects": sorted(subjects),
            "subject_session_count": len(subject_sessions),
            "labels": sorted({row["label"] for row in members}) if unit == "task_window" else [],
            "members": [row["trial_id"] if unit == "task_window"
                        else f"{row['subject']}/ses-{row['session']}/run-{row['run']}"
                        for row in members],
            "source_edf_sha256": sorted({row["source_edf_sha256"] for row in members}),
        })
    return sorted(groups, key=lambda item: item["members"][0])


def original_header_evidence(header: dict) -> dict:
    path = Path(header["local_original_header"])
    actual = sha(path)
    assert actual == header["declared_original_header_sha256"]
    text = path.read_text(encoding="utf-8-sig")
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(text[text.index("[Common Infos]"):])
    channels = [value.split(",") for name, value in parser["Channel Infos"].items()
                if name.startswith("ch")]
    return {
        "original_subject": header["original_subject"],
        "original_header_file": header["original_header_file"],
        "actual_original_header_sha256": actual,
        "declared_original_header_sha256": header["declared_original_header_sha256"],
        "original_header_hash_verified": True,
        "original_header_bytes": path.stat().st_size,
        "header_data_file_field": parser["Common Infos"].get("DataFile"),
        "header_marker_file_field": parser["Common Infos"].get("MarkerFile"),
        "header_channel_names": [fields[0] for fields in channels],
        "header_reference_fields": dict(Counter(fields[1] for fields in channels)),
        "header_unit_fields": dict(Counter(fields[3] for fields in channels)),
        "header_sampling_frequency_hz": 1e6 / float(parser["Common Infos"]["SamplingInterval"]),
        "reference_interpretation": "blank header fields do not establish acquisition reference",
        "original_continuous_signal_available_or_compared": False,
        "original_marker_sequence_compared": False,
    }


def leakage_evidence(windows: list[dict]) -> dict:
    training = defaultdict(list)
    reference_query = defaultdict(list)
    for row in windows:
        if row["production_role"] == "source_train":
            training[(row["subject"], row["numeric_sha256"])].append(row)
        if row["production_role"] == "source_reference_query":
            reference_query[(row["subject"], row["numeric_sha256"])].append(row)
    bridges, reference_bridges = [], []
    later_counts = defaultdict(Counter)
    for row in windows:
        if not row["fixed_window_eligible"]:
            continue
        key = (row["subject"], row["numeric_sha256"])
        if row["session"] != "01":
            counter = later_counts[(row["subject"], row["session"])]
            counter["later_query_count"] += 1
            source_train = training.get(key, [])
            source_reference = reference_query.get(key, [])
            if source_train:
                same_label = [source["trial_id"] for source in source_train
                              if source["label"] == row["label"]]
                conflicting_label = [source["trial_id"] for source in source_train
                                     if source["label"] != row["label"]]
                bridges.append({
                    "query_trial_id": row["trial_id"], "query_label": row["label"],
                    "subject": row["subject"], "session": row["session"],
                    "numeric_sha256": row["numeric_sha256"],
                    "same_label_source_train_trial_ids": same_label,
                    "conflicting_label_source_train_trial_ids": conflicting_label,
                })
                counter["exact_source_training_overlap_count"] += 1
                counter["same_label_training_overlap_count"] += bool(same_label)
                counter["conflicting_label_training_overlap_count"] += bool(conflicting_label)
            if source_reference:
                reference_bridges.append({
                    "query_trial_id": row["trial_id"], "subject": row["subject"],
                    "session": row["session"], "numeric_sha256": row["numeric_sha256"],
                    "source_reference_query_trial_ids": [source["trial_id"] for source in source_reference],
                })
                counter["exact_source_reference_query_overlap_count"] += 1
    return {
        "interpretation": "Exact content overlap between source training and later queries despite distinct source event IDs; affected later-session model scores are not independent cross-session generalization evidence.",
        "source_training_later_query_bridges": bridges,
        "source_reference_later_query_bridges": reference_bridges,
        "source_training_later_query_affected_trials": len(bridges),
        "source_reference_later_query_affected_trials": len(reference_bridges),
        "source_training_later_query_affected_numeric_groups": len({row["numeric_sha256"] for row in bridges}),
        "source_training_later_query_same_label_affected_trials": sum(bool(row["same_label_source_train_trial_ids"]) for row in bridges),
        "source_training_later_query_conflicting_label_affected_trials": sum(bool(row["conflicting_label_source_train_trial_ids"]) for row in bridges),
        "by_subject_session": [
            {"subject": subject, "session": session,
             **{name: count.get(name, 0) for name in (
                 "later_query_count", "exact_source_training_overlap_count",
                 "same_label_training_overlap_count", "conflicting_label_training_overlap_count",
                 "exact_source_reference_query_overlap_count")}}
            for (subject, session), count in sorted(later_counts.items())
        ],
    }


def main() -> None:
    assert not OUTPUT.exists(), "Preserve prior audit: output already exists"
    started = time.monotonic()
    runs, windows, source_audits = [], [], []
    # Inspect the flagged participant first, then remaining participants serially.
    subject_order = ["sub-7", *[f"sub-{i}" for i in range(1, 11) if i != 7]]
    for subject in subject_order:
        subject_audit_path = AUDITS / subject / "audit.json"
        audit = json.loads(subject_audit_path.read_text())
        inventory_path = AUDITS / subject / "source_events.tsv"
        events = table(inventory_path)
        assert len(events) == audit["summary"]["total_source_trials"]
        assert len({row["trial_id"] for row in events}) == len(events)
        run_inventory = {(row["session"], row["run"]): row for row in
                         table(AUDITS / subject / "run_inventory.tsv")}
        headers = {(row["session"], row["run"]): row for row in audit["original_header_audits"]}
        partition_path = REPO / "results/netbci_cohort_resume_20261010" / subject / "run01/partitions.json"
        partitions = json.loads(partition_path.read_text())
        production_roles = {trial_id: role for role, trial_ids in partitions["partition_trial_ids"].items()
                            for trial_id in trial_ids}
        assert len(production_roles) == sum(row["fixed_window_eligible"] == "True" for row in events)
        assert set(production_roles) == {row["trial_id"] for row in events
                                         if row["fixed_window_eligible"] == "True"}
        source_audits.append({
            "subject": subject, "audit_file": str(subject_audit_path.relative_to(REPO)),
            "audit_sha256": sha(subject_audit_path),
            "source_event_inventory_file": str(inventory_path.relative_to(REPO)),
            "source_event_inventory_sha256": sha(inventory_path),
            "download_manifest_sha256": audit["manifest_sha256"],
            "production_partition_file": str(partition_path.relative_to(REPO)),
            "production_partition_sha256": sha(partition_path),
        })
        for oldrun in sorted(audit["runs"], key=lambda row: (row["session"], row["run"])):
            session, run = oldrun["session"], oldrun["run"]
            file = DATA / oldrun["file"]
            file_sha = sha(file)
            assert file_sha == run_inventory[(session, run)]["source_edf_sha256"]
            event_file = file.with_name(file.name.replace("_eeg.edf", "_events.tsv"))
            event_sha = sha(event_file)
            source_rows = table(event_file)
            selected_events = [row for row in events if row["session"] == session
                               and row["run"] == run]
            assert len(selected_events) == len(source_rows) == oldrun["source_trial_count"]
            raw = mne.io.read_raw_edf(file, preload=False, verbose="ERROR")
            assert raw.ch_names == oldrun["channel_names"]
            assert raw.info["sfreq"] == oldrun["sampling_frequency_hz"]
            assert raw.n_times == oldrun["signal_samples"]
            signal = raw.get_data()
            full_hash, values_hash = canonical_hash(signal)
            runrow = {
                "subject": subject, "session": session, "run": run,
                "source_file": oldrun["file"], "source_edf_sha256": file_sha,
                "source_event_file": str(event_file.relative_to(DATA)),
                "source_event_sha256": event_sha,
                "shape": list(signal.shape), "dtype": "<f8", "order": "C",
                "signal_unit": "V", "sampling_frequency_hz": raw.info["sfreq"],
                "channel_names": raw.ch_names, "numeric_sha256": full_hash,
                "value_payload_sha256": values_hash,
                "event_count": len(source_rows),
                "edf_measurement_date": str(raw.info["meas_date"]),
                "original_header": original_header_evidence(headers[(session, run)]),
            }
            runs.append(runrow)
            for event in selected_events:
                tsv_row = int(event["tsv_row"])
                source = source_rows[tsv_row - 1]
                assert event["trial_id"] == f"{subject}/ses-{session}/run-{run}/tsv-row-{tsv_row}"
                assert event["label"] == source["trial_type"]
                assert int(event["stored_event_value"]) == int(source["value"])
                assert float(event["onset_s"]) == float(source["onset"])
                assert float(event["duration_s"]) == float(source["duration"])
                start = int(event["start_sample"])
                stop = int(event["stop_sample_exclusive"])
                assert start == int(source["sample"])
                assert stop - start == round(float(source["duration"]) * raw.info["sfreq"])
                assert 0 <= start < stop <= raw.n_times
                window_hash, window_values_hash = canonical_hash(signal[:, start:stop])
                windows.append({
                    "subject": subject, "session": session, "run": run,
                    "trial_id": event["trial_id"], "tsv_row": tsv_row,
                    "label": event["label"], "stored_event_value": int(event["stored_event_value"]),
                    "onset_s": float(source["onset"]), "duration_s": float(source["duration"]),
                    "start_sample": start, "stop_sample_exclusive": stop,
                    "fixed_window_eligible": event["fixed_window_eligible"] == "True",
                    "exclusion_reason": event["exclusion_reason"],
                    "production_role": production_roles.get(event["trial_id"], "excluded_fixed_window_duration"),
                    "source_file": oldrun["file"], "source_edf_sha256": file_sha,
                    "source_event_file": str(event_file.relative_to(DATA)),
                    "source_event_sha256": event_sha,
                    "original_header_file": event["original_header_file"],
                    "actual_original_header_sha256": runrow["original_header"]["actual_original_header_sha256"],
                    "shape": [signal.shape[0], stop - start], "signal_unit": "V",
                    "numeric_sha256": window_hash,
                    "value_payload_sha256": window_values_hash,
                })
            del signal
            raw.close()
            del raw
            gc.collect()
        print(json.dumps({"subject": subject, "runs_hashed": len(runs),
                          "source_task_windows_hashed": len(windows)}, sort_keys=True), flush=True)
        if subject == "sub-7":
            print(json.dumps({"sub7_full_signal_duplicate_groups": group_identities(runs, unit="continuous_run")}, sort_keys=True), flush=True)
    assert len(runs) == 240 and len(windows) == 7577
    full_groups = group_identities(runs, unit="continuous_run")
    window_groups = group_identities(windows, unit="task_window")
    result = {
        "status": "complete_exact_numeric_identity_audit",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "synthetic": False, "signal_source": "NEMAR nm000305 v1.0.0 EDF/BIDS derivative",
        "script_file": str(Path(__file__).relative_to(REPO)), "script_sha256": sha(Path(__file__)),
        "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "runtime_versions": {"mne": mne.__version__, "numpy": np.__version__},
        "threads": 2, "subject_order": subject_order,
        "method": {
            "reader": "mne.io.read_raw_edf(preload=False); raw.get_data() one continuous run at a time",
            "signal_unit": "V", "transformations": "none: no filtering, reference change, rounding or scaling beyond MNE EDF decoding",
            "canonical_numeric_hash": "SHA256 of netbci-numeric-array-v1 NUL, sorted compact JSON dtype <f8/shape/order C, NUL, little-endian float64 C-order values",
            "value_payload_hash": "SHA256 of little-endian float64 C-order values, with no EDF header/annotation bytes",
            "identity_scope": "bitwise identical canonical returned numerical arrays; dimensions included; channel order separately validated",
            "task_window_policy": "all actual labeled source [start_sample, stop_sample_exclusive) intervals, including the real short event",
            "near_similarity_assessed": False,
            "near_similarity_note": "This is an exact numerical identity audit. Different hashes do not rule out near similarity; no correlation/distance threshold is used.",
            "hash_comparison_note": "Identity uses cryptographic numerical fingerprints; EDF file SHA is recorded independently and includes metadata.",
        },
        "summary": {
            "subjects": 10, "continuous_runs": len(runs), "source_task_windows": len(windows),
            "fixed_window_eligible_task_windows": sum(row["fixed_window_eligible"] for row in windows),
            "unique_continuous_numeric_hashes": len({row["numeric_sha256"] for row in runs}),
            "unique_task_window_numeric_hashes": len({row["numeric_sha256"] for row in windows}),
            "continuous_duplicate_groups": len(full_groups),
            "continuous_duplicate_members": sum(row["member_count"] for row in full_groups),
            "same_person_cross_session_continuous_groups": sum(row["same_person_cross_session"] for row in full_groups),
            "cross_subject_continuous_groups": sum(row["cross_subject"] for row in full_groups),
            "task_window_duplicate_groups": len(window_groups),
            "task_window_duplicate_members": sum(row["member_count"] for row in window_groups),
            "same_person_cross_session_task_window_groups": sum(row["same_person_cross_session"] for row in window_groups),
            "cross_subject_task_window_groups": sum(row["cross_subject"] for row in window_groups),
            "multi_label_task_window_duplicate_groups": sum(len(row["labels"]) > 1 for row in window_groups),
        },
        "limitations": [
            "Exact identity applies to the available EDF derivative numeric arrays, not independently read original BrainVision EEG.",
            "Original header paths, data/marker filename fields and hashes establish distinct metadata identities; they cannot establish distinct or identical underlying original signal contents.",
            "A blank acquisition-reference field does not identify the acquisition reference.",
            "No cause (conversion, provenance mapping, acquisition, human physiology or behavior) is inferred from exact derivative repetition.",
            "Existing numerical analysis and cohort membership are preserved; no participant or event is excluded by this audit.",
            "Near-zero geometry or identical spectral summaries of repeated derivatives are not independent biological-stability evidence.",
        ],
        "source_audits": source_audits,
        "upstream_provenance_file": "sourcedata/sourcedata_provenance.json",
        "upstream_provenance_sha256": sha(DATA / "sourcedata/sourcedata_provenance.json"),
        "continuous_runs": runs, "source_task_windows": windows,
        "continuous_duplicate_groups": full_groups, "task_window_duplicate_groups": window_groups,
        "production_partition_content_overlap": leakage_evidence(windows),
        "elapsed_seconds": time.monotonic() - started,
    }
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(OUTPUT), "summary": result["summary"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
