#!/usr/bin/env python3
"""Read-only pre-model numerical identity audit of configured NETBCI EDF derivatives.

Reads one continuous run at a time. Does not preprocess, train, download, modify
source data, or change cohort eligibility. Source task windows include all real
events, including the duration-ineligible event, without padding or truncation.
"""

from __future__ import annotations

import argparse
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
        if row["planned_role"] == "source_train":
            training[(row["subject"], row["numeric_sha256"])].append(row)
        if row["planned_role"] == "source_reference_query":
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    data = REPO / config["source_root"]
    audits = REPO / config["output_root"]
    output = args.output.resolve()
    assert not output.exists(), "Preserve prior audit: output already exists"
    assert set(config["source_train_runs"]).isdisjoint(config["source_query_runs"])
    assert set(config["source_train_runs"]) | set(config["source_query_runs"]) == set(config["expected_runs"])
    assert config["later_query_runs"] == config["expected_runs"]
    manifest_path = REPO / config["official_manifest"]
    official = {row["path"]: row for row in json.loads(manifest_path.read_text())}
    started = time.monotonic()
    runs, windows, source_audits = [], [], []
    # Keep the configured subject order. No outcome-based selection is used.
    subject_order = config["subjects"]
    for subject in subject_order:
        subject_audit_path = audits / subject / "audit.json"
        audit = json.loads(subject_audit_path.read_text())
        inventory_path = audits / subject / "source_events.tsv"
        events = table(inventory_path)
        assert len(events) == audit["summary"]["total_source_trials"]
        assert len({row["trial_id"] for row in events}) == len(events)
        run_inventory = {(row["session"], row["run"]): row for row in
                         table(audits / subject / "run_inventory.tsv")}
        headers = {(row["session"], row["run"]): row for row in audit["original_header_audits"]}
        assert audit["configuration"]["sha256"] == sha(config_path)
        subject_manifest_path = REPO / config["download_root"] / subject / "download_manifest.json"
        subject_manifest = {row["path"]: row for row in json.loads(subject_manifest_path.read_text())}
        planned_roles = {}
        for event in events:
            if event["fixed_window_eligible"] != "True":
                continue
            if event["session"] == config["session_order"][0]:
                if event["run"] in config["source_train_runs"]:
                    role = "source_train"
                else:
                    assert event["run"] in config["source_query_runs"]
                    role = "source_reference_query"
            else:
                assert event["run"] in config["later_query_runs"]
                role = "validation_no_selection" if event["session"] == config["session_order"][1] else "test_exploratory"
            planned_roles[event["trial_id"]] = role
        assert len(planned_roles) == sum(row["fixed_window_eligible"] == "True" for row in events)
        source_audits.append({
            "subject": subject, "audit_file": str(subject_audit_path.relative_to(REPO)),
            "audit_sha256": sha(subject_audit_path),
            "source_event_inventory_file": str(inventory_path.relative_to(REPO)),
            "source_event_inventory_sha256": sha(inventory_path),
            "download_manifest_sha256": audit["manifest_sha256"],
            "planned_partition_roles": "derived directly from configuration before expanded models; no fitted partitions required",
            "subject_download_manifest_file": str(subject_manifest_path.relative_to(REPO)),
            "subject_download_manifest_sha256": sha(subject_manifest_path),
        })
        for oldrun in sorted(audit["runs"], key=lambda row: (row["session"], row["run"])):
            session, run = oldrun["session"], oldrun["run"]
            file = data / oldrun["file"]
            file_sha = sha(file)
            assert file_sha == run_inventory[(session, run)]["source_edf_sha256"]
            for declaration in (official[oldrun["file"]], subject_manifest[oldrun["file"]]):
                assert declaration["checksum_algorithm"] == "sha256"
                assert declaration["checksum"] == file_sha
                assert declaration["size"] == file.stat().st_size
            event_file = file.with_name(file.name.replace("_eeg.edf", "_events.tsv"))
            event_sha = sha(event_file)
            event_relative = str(event_file.relative_to(data))
            for declaration in (official[event_relative], subject_manifest[event_relative]):
                assert declaration["checksum_algorithm"] == "sha256"
                assert declaration["checksum"] == event_sha
                assert declaration["size"] == event_file.stat().st_size
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
                "source_event_file": str(event_file.relative_to(data)),
                "source_event_sha256": event_sha,
                "shape": list(signal.shape), "dtype": "<f8", "order": "C",
                "signal_unit": "V", "sampling_frequency_hz": raw.info["sfreq"],
                "channel_names": raw.ch_names, "numeric_sha256": full_hash,
                "value_payload_sha256": values_hash,
                "event_count": len(source_rows),
                "edf_measurement_date": str(raw.info["meas_date"]),
                "official_manifest_match": True, "per_subject_manifest_match": True,
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
                    "planned_role": planned_roles.get(event["trial_id"], "excluded_fixed_window_duration"),
                    "source_file": oldrun["file"], "source_edf_sha256": file_sha,
                    "source_event_file": str(event_file.relative_to(data)),
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
    assert len(runs) == len(subject_order) * len(config["expected_sessions"]) * len(config["expected_runs"])
    assert len(windows) == sum(len(table(audits / subject / "source_events.tsv")) for subject in subject_order)
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
        "configuration_file": str(config_path.relative_to(REPO)), "configuration_sha256": sha(config_path),
        "official_manifest_file": str(manifest_path.relative_to(REPO)), "official_manifest_sha256": sha(manifest_path),
        "timing": "raw numerical-content audit required before any expanded nineteen-ID model fitting",
        "role_source": "fixed configuration; source session train runs01-04/query05-06; later all runs; no model output read",
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
            "subjects": len(subject_order), "continuous_runs": len(runs), "source_task_windows": len(windows),
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
            "official_manifest_matches": sum(row["official_manifest_match"] for row in runs),
            "per_subject_manifest_matches": sum(row["per_subject_manifest_match"] for row in runs),
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
        "upstream_provenance_sha256": sha(data / "sourcedata/sourcedata_provenance.json"),
        "continuous_runs": runs, "source_task_windows": windows,
        "continuous_duplicate_groups": full_groups, "task_window_duplicate_groups": window_groups,
        "planned_partition_content_overlap": leakage_evidence(windows),
        "elapsed_seconds": time.monotonic() - started,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(output), "summary": result["summary"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
