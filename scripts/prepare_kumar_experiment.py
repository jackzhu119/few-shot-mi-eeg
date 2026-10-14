#!/usr/bin/env python3
"""Freeze and audit the pinned local Kumar split before any performance call.

All participants are processed serially; tensors are released after each subject.
Writes small immutable JSON/CSV evidence only, never a model or raw tensor.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

import numpy as np  # noqa: E402 -- cap BLAS threads before numerical imports

from learning_preserving_bci.datasets.kumar import (  # noqa: E402
    CHANNEL_NAMES, LABELS, ROLES, load_subject, require, sha256_file, tsv,
    validate_split_trials,
)

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), "Empty evidence table")
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_all_pinned_files(data_root: Path, manifest_path: Path) -> list[dict]:
    """Verify the complete authorized selection, not only adapter-used files."""
    entries = json.loads(manifest_path.read_text())
    require(len(entries) == 2705, "Pinned file coverage changed")
    require(len({e["path"] for e in entries}) == len(entries), "Duplicate pinned source path")
    receipts = []
    for entry in entries:
        relative = entry["path"]
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
                "Unsafe pinned source path")
        path = data_root / relative
        require(path.is_file() and path.stat().st_size == entry["size"],
                f"Pinned file missing or size changed: {relative}")
        sha = sha256_file(path)
        if entry["checksum_algorithm"] == "sha256":
            official = sha
        elif entry["checksum_algorithm"] == "git":
            data = path.read_bytes()
            official = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        else:
            raise ValueError("Unsupported pinned checksum algorithm")
        require(official == entry["checksum"], f"Official pinned checksum mismatch: {relative}")
        receipts.append({"path": relative, "bytes": path.stat().st_size,
                         "sha256": sha, "official_algorithm": entry["checksum_algorithm"],
                         "official_checksum": official, "verified": True})
    require(sum(p["bytes"] for p in receipts) == 1781052841, "Pinned byte coverage changed")
    require(sum(p["path"].endswith(".edf") for p in receipts) == 360, "EDF coverage changed")
    return receipts


def validate_budget_and_class_coverage(trials: list[dict], config: dict) -> dict:
    """Audit budgets before exclusions and two-class viability without performance."""
    groups = defaultdict(list)
    for trial in trials:
        groups[(trial["subject"], trial["session"], trial["role"])].append(trial)
    expected = {(s, "ses-0", r) for s in config["subjects"]
                for r in ("source_train", "source_validation", "source_query")}
    expected |= {(s, session, role) for s in config["subjects"]
                 for session in config["split"]["target_sessions"]
                 for role in ("target_support", "target_query")}
    require(set(groups) == expected, "Missing or extra frozen subject/session/role")
    for (_, _, role), rows in groups.items():
        source_counts = Counter(r["label"] for r in rows)
        included_counts = Counter(r["label"] for r in rows if r["included"])
        require(set(source_counts) == set(included_counts) == set(LABELS),
                "Frozen analysis role lacks a task class")
        if role == "target_support":
            require(len(rows) <= config["split"]["target_support_source_budget"],
                    "Support source-event budget exceeded")
            require(max(source_counts.values()) <= config["split"]["target_support_max_per_class"],
                    "Support per-class budget exceeded")
            require({r["run"] for r in rows} == set(config["split"]["target_support_runs"]),
                    "Support is not the frozen complete first run")
    return {"all_subject_session_roles_present": True, "all_roles_have_both_included_classes": True,
            "support_source_budget_at_most20": True, "support_source_per_class_at_most10": True,
            "support_whole_first_run_only": True, "partial_support_not_replaced": True}


def count_matched_diagnostic(trials: list[dict]) -> list[dict]:
    """Deterministic descriptive subset; never replaces the primary split."""
    groups = defaultdict(list)
    for trial in trials:
        if trial["included"]:
            groups[(trial["subject"], trial["session"], trial["role"])].append(trial)
    records = []
    for (subject, session, role), rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda r: (r["acquisition_time_utc"], r["start_sample"]))
        by_class = {label: [r for r in ordered if r["label"] == label] for label in LABELS}
        minimum = min(len(v) for v in by_class.values())
        records.append({"subject": subject, "session": session, "role": role,
                        "n_per_class": minimum, "available_class_counts": {
                            k: len(v) for k, v in by_class.items()},
                        "trial_ids": [r["trial_id"] for r in ordered if r["trial_id"] in {
                            r["trial_id"] for values in by_class.values() for r in values[:minimum]}],
                        "use": "diagnostic_only_primary_data_unchanged"})
    return records


def role_count_rows(trials: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for trial in trials:
        groups[(trial["subject"], trial["cohort"], trial["session"], trial["role"])].append(trial)
    result = []
    for (subject, cohort, session, role), rows in sorted(groups.items()):
        included = [r for r in rows if r["included"]]
        result.append({"subject": subject, "cohort": cohort, "session": session, "role": role,
                       "source_events": len(rows), "included_trials": len(included),
                       "excluded_partial": len(rows) - len(included),
                       "source_left_hand": sum(r["label"] == "left_hand" for r in rows),
                       "source_right_hand": sum(r["label"] == "right_hand" for r in rows),
                       "included_left_hand": sum(r["label"] == "left_hand" for r in included),
                       "included_right_hand": sum(r["label"] == "right_hand" for r in included),
                       "qc_flagged_source": sum(r["qc_peak_to_peak_over_250uv"] for r in rows),
                       "qc_flagged_included": sum(r["qc_peak_to_peak_over_250uv"] for r in included)})
    return result


def duplicate_groups(records: list[dict], field: str, id_field: str) -> list[list[str]]:
    groups = defaultdict(list)
    for record in records:
        groups[record[field]].append(record[id_field])
    return [ids for ids in groups.values() if len(ids) > 1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True,
                        help="Already verified checkpoint; preparation performs no Git command")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    require(config["synthetic"] is False, "Real-source gate cannot qualify synthetic data")
    require(set(config["subjects"]) == {f"sub-{i}" for i in range(1, 19)}, "Frozen cohort changed")
    require(set(config["development_subjects"]) == {f"sub-{i}" for i in (1, 4, 7, 10, 13, 16)},
            "Frozen development assignment changed")
    data_root = args.data_root or Path(config["data_root"])
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    source_manifest = Path(config["source_manifest"])
    snapshot = args.output / "source_snapshot"
    snapshot.mkdir()
    bound_inputs = {"config": args.config, "protocol": args.protocol,
                    "adapter": ROOT / "src/learning_preserving_bci/datasets/kumar.py",
                    "preparation_script": Path(__file__), "source_manifest": source_manifest}
    hashes = {f"{key}_sha256": sha256_file(path) for key, path in bound_inputs.items()}
    for path in bound_inputs.values():
        shutil.copyfile(path, snapshot / path.name)
    write_json(args.output / "freeze_receipt.json", {
        "status": "frozen_before_source_preparation_and_any_model_performance",
        "started_at_utc": started_at, "source_commit": args.source_commit,
        "source_commit_provenance": "existing_checkpoint_supplied_by_root_no_git_action",
        "synthetic": False, "model_fit_performed": False, "performance_computed": False,
        **hashes, "input_paths": {k: str(v) for k, v in bound_inputs.items()}})
    try:
        pinned_files = verify_all_pinned_files(data_root, source_manifest)
        write_json(args.output / "verified_pinned_files.json", pinned_files)
        print(json.dumps({"status": "all_pinned_files_verified", "files": len(pinned_files)}),
              flush=True)
        trials, subjects, runs = [], [], []
        for subject in config["subjects"]:
            bundle = load_subject(data_root, subject, config)
            require(bundle.X.shape == (len(bundle.metadata), 22, 640)
                    and bundle.X.dtype == np.float32 and bundle.sfreq == 128.0
                    and bundle.channel_names == CHANNEL_NAMES, "Prepared tensor contract changed")
            validate_budget_and_class_coverage(bundle.source_events, {
                **config, "subjects": [subject]})
            write_json(args.output / "subjects" / f"{subject}.json", bundle.provenance)
            trials.extend(bundle.source_events)
            subjects.append({"subject": subject, "cohort": bundle.provenance["cohort"],
                             "source_events": len(bundle.source_events),
                             "included_trials": len(bundle.metadata),
                             "excluded_partial": len(bundle.source_events) - len(bundle.metadata),
                             "chronology_strictly_increasing": True})
            runs.extend(bundle.provenance["runs"])
            print(json.dumps({"status": "participant_prepared", **subjects[-1]}), flush=True)
            del bundle
        require(len(trials) == 7200 and len(runs) == 360, "Incomplete source coverage")
        require(sum(r["included"] for r in trials) == 7156, "Full-window coverage changed")
        require(sum(not r["included"] for r in trials) == 44, "Partial-window coverage changed")
        checks = validate_split_trials(trials, config)
        checks.update(validate_budget_and_class_coverage(trials, config))
        whole_duplicates = duplicate_groups(runs, "whole_signal_numeric_sha256", "source_file")
        require(not whole_duplicates, "Exact whole-signal duplicate found")
        checks.update({"all2705_pinned_files_official_checksums_passed": True,
                       "all360_continuous_signals_finite_and_historical_hash_equal": True,
                       "all108_sessions_and7200_source_rows_present": True,
                       "full7156_partial44_preserved": True,
                       "edf_tsv_timing_labels_annotations_units_reference_verified": True,
                       "nominal_order_matches_strictly_increasing_reported_acq_times": True,
                       "whole_signal_numeric_duplicate_groups": whole_duplicates,
                       "no_model_fit_or_performance_call": True})
        require({r["role"] for r in trials} == ROLES, "Frozen roles incomplete")
        manifest = {"schema_version": 1, "experiment": config["experiment"], "synthetic": False,
                    "config_sha256": hashes["config_sha256"],
                    "protocol_sha256": hashes["protocol_sha256"],
                    "source_manifest_sha256": hashes["source_manifest_sha256"],
                    "adapter_sha256": hashes["adapter_sha256"],
                    "trials": trials, "subjects": subjects, "checks": checks,
                    "excluded_rows_retained": True, "fit_or_performance_performed": False}
        split_path = args.output / "split_manifest.json"
        write_json(split_path, manifest)
        write_json(args.output / "count_matched_diagnostic.json", count_matched_diagnostic(trials))
        count_rows = role_count_rows(trials)
        write_csv(args.output / "role_counts.csv", count_rows)
        write_csv(args.output / "run_metadata.csv", runs)
        prior_root = Path(config["prior_signal_audit"])
        prior = json.loads((prior_root / "aggregate.json").read_text())
        participants = tsv(data_root / "participants.tsv")
        write_json(args.output / "source_gate_receipt.json", {
            "schema_version": 1, "status": "strict_eligibility_passed_with_source_qualifications",
            "strict_eligibility_passed": True, "synthetic": False,
            "started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": time.monotonic() - started, "source_commit": args.source_commit,
            **hashes, "split_manifest_path": str(split_path),
            "split_manifest_sha256": sha256_file(split_path),
            "freeze_receipt_sha256": sha256_file(args.output / "freeze_receipt.json"),
            "verified_pinned_files_sha256": sha256_file(args.output / "verified_pinned_files.json"),
            "prior_signal_audit_aggregate_sha256": sha256_file(prior_root / "aggregate.json"),
            "prior_source_events_sha256": sha256_file(prior_root / "source_events.json"),
            "participants_planned": config["subjects"], "participants_completed": subjects,
            "source_files": len(pinned_files), "source_bytes": sum(p["bytes"] for p in pinned_files),
            "EDF_count": len(runs), "sessions": len({(r["subject"], r["session"]) for r in trials}),
            "source_events": len(trials), "included_trials": 7156, "excluded_partial": 44,
            "source_class_counts": dict(Counter(r["label"] for r in trials)),
            "included_class_counts": dict(Counter(r["label"] for r in trials if r["included"])),
            "source_role_counts": dict(Counter(r["role"] for r in trials)),
            "included_role_counts": dict(Counter(r["role"] for r in trials if r["included"])),
            "qc_flagged_source_windows": sum(r["qc_peak_to_peak_over_250uv"] for r in trials),
            "qc_flagged_included_windows": sum(r["qc_peak_to_peak_over_250uv"] for r in trials
                                               if r["included"]),
            "peak_to_peak_threshold_volts": config["quality_control"]["peak_to_peak_threshold_volts"],
            "qc_primary_removal": False, "strict_checks": checks,
            "historical_central4KiB_duplicate_groups": prior["central4KiB_duplicate_groups"],
            "central_fingerprints_status": "historical_verified_source_receipts_not_newly_recomputed",
            "reported_participant_age_values": dict(Counter(r["age"] for r in participants)),
            "source_quality_qualifications": config["source_qualifications"],
            "model_fit_performed": False, "performance_computed": False,
            "baseline_execution_requires_root_hash_bound_approval": True,
            "runtime_versions": {"python": platform.python_version(), **{
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "mne", "scikit-learn")}}})
        print(json.dumps({"status": "prepared_no_model_fit", "source_events": len(trials),
                          "included": 7156, "excluded_partial": 44,
                          "split_manifest_sha256": sha256_file(split_path)}), flush=True)
    except Exception as error:
        write_json(args.output / "preparation_failure.json", {
            "status": "strict_gate_failed_no_fit_authorized", "synthetic": False,
            "type": type(error).__name__, "message": str(error),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(), **hashes,
            "model_fit_performed": False, "performance_computed": False})
        raise


if __name__ == "__main__":
    main()
