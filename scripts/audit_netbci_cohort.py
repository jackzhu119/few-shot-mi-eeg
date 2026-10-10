#!/usr/bin/env python3
"""Sequential local NETBCI cohort audit; no downloads, transformations or training.

Derivative signal access is audited independently from original BrainVision
access. Upstream header hashes in NEMAR provenance remain declarations when the
corresponding original header is not locally available.
"""

from __future__ import annotations

import argparse
import configparser
import csv
import gc
import json
import re
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from check_netbci_subset import audit

from learning_preserving_bci.datasets.netbci import (
    file_sha256,
    load_netbci_subset,
    save_netbci_bundle,
)
from learning_preserving_bci.utils.reproducibility import collect_provenance

REPO_ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def write_json(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_tsv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), f"Cannot save empty evidence table: {path}")
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def upstream_subject_map(provenance: dict, subject: str) -> tuple[str, list[dict]]:
    """Resolve the declared mapping from explicit provenance, never zero-padding IDs."""
    require(re.fullmatch(r"sub-[A-Za-z0-9]+", subject) is not None, "Invalid subject ID")
    matches = [item for item in provenance["files"]
               if str(item["subject"]) == subject.removeprefix("sub-")]
    require(bool(matches), f"No upstream provenance for {subject}")
    originals, run_ids, paths = set(), set(), set()
    for item in matches:
        path = PurePosixPath(item["file"])
        require(not path.is_absolute() and ".." not in path.parts, "Unsafe upstream path")
        require(len(path.parts) >= 4 and re.fullmatch(r"sub-[A-Za-z0-9]+", path.parts[0])
                is not None, "Invalid original subject path")
        match = re.fullmatch(
            r"(sub-[A-Za-z0-9]+)_ses-([^_]+)_task-MotorImageryRest_run-([^_]+)_eeg\.vhdr",
            path.name,
        )
        require(match is not None, "Unreviewed upstream header naming")
        original, session, run = match.groups()
        require(original == path.parts[0] and f"ses-{session}" == path.parts[1],
                "Conflicting original subject/session identity")
        require(path.as_posix() not in paths and (session, run) not in run_ids,
                "Duplicate upstream header/run identity")
        require(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None,
                "Invalid declared upstream SHA256")
        originals.add(original)
        run_ids.add((session, run))
        paths.add(path.as_posix())
    require(len(originals) == 1, "Ambiguous original subject mapping")
    return next(iter(originals)), matches


def inspect_original_headers(
    provenance: dict, subject: str, derivative_runs: list[dict], original_roots: list[Path]
) -> tuple[str, list[dict]]:
    """Hash cached original headers when present; distinguish missing from verified."""
    original_subject, matches = upstream_subject_map(provenance, subject)
    derivative = {(item["session"], item["run"]): item for item in derivative_runs}
    require(len(derivative) == len(derivative_runs), "Duplicate derivative run")
    header_rows = []
    for item in matches:
        match = re.search(r"_ses-([^_]+)_task-MotorImageryRest_run-([^_]+)_eeg\.vhdr$",
                          item["file"])
        session, run = match.groups()
        require((session, run) in derivative, "Unmatched original header run")
        row = {
            "subject": subject, "original_subject": original_subject,
            "session": session, "run": run, "original_header_file": item["file"],
            "declared_original_header_sha256": item["sha256"],
            "declared_original_header_bytes": item["bytes"],
            "local_original_header": "not_locally_available",
            "actual_original_header_sha256": "unresolved",
            "original_header_hash_verified": False,
            "original_sampling_frequency_hz": "unresolved",
            "original_channel_count": "unresolved",
            "original_channel_units_json": "unresolved",
            "original_reference_fields_json": "unresolved",
            "original_reference_interpretation": "unresolved",
            "original_derivative_channel_order_matches": "unresolved",
            "derivative_sampling_frequency_hz": derivative[(session, run)]["sampling_frequency_hz"],
            "original_signal_equality_verified": False,
            "original_marker_sequence_verified": False,
        }
        candidates = [root / item["file"] for root in original_roots
                      if (root / item["file"]).is_file()]
        if candidates:
            digests = [file_sha256(path) for path in candidates]
            require(all(digest == item["sha256"] for digest in digests),
                    "Local original header differs from declared upstream SHA256")
            path = candidates[0]
            require(path.stat().st_size == item["bytes"], "Original header byte count mismatch")
            parser = configparser.ConfigParser(interpolation=None)
            text = path.read_text(encoding="utf-8-sig")
            parser.read_string(text[text.index("[Common Infos]"):])
            frequency = 1e6 / float(parser["Common Infos"]["SamplingInterval"])
            channel_fields = [value.split(",") for key, value in parser["Channel Infos"].items()
                              if key.startswith("ch")]
            channels = [fields[0] for fields in channel_fields]
            require(len(channels) == int(parser["Common Infos"]["NumberOfChannels"]),
                    "Original header channel count mismatch")
            require(all(len(fields) >= 4 for fields in channel_fields),
                    "Unreviewed original channel field format")
            require(channels == derivative[(session, run)]["channel_names"],
                    "Original/derivative channel order mismatch")
            row.update({
                "local_original_header": str(path.resolve()),
                "actual_original_header_sha256": digests[0],
                "original_header_hash_verified": True,
                "original_sampling_frequency_hz": frequency,
                "original_channel_count": len(channels),
                "original_channel_units_json": json.dumps(dict(Counter(fields[3] for fields in channel_fields))),
                "original_reference_fields_json": json.dumps(dict(Counter(fields[1] for fields in channel_fields))),
                "original_reference_interpretation": "blank header fields do not establish acquisition reference",
                "original_derivative_channel_order_matches": True,
            })
        header_rows.append(row)
    require({(item["session"], item["run"]) for item in header_rows} == set(derivative),
            "Original provenance and derivative run coverage differ")
    return original_subject, sorted(header_rows, key=lambda item: (item["session"], item["run"]))


def audit_subject(subject: str, config: dict, config_path: Path) -> dict:
    """Audit all source signals, save a new exact-slice bundle, retain trial identities."""
    started = time.monotonic()
    data_root = REPO_ROOT / config.get("source_root", "data/netbci2026/nm000305/v1.0.0")
    download_root = REPO_ROOT / config.get(
        "download_root", "research_logs/netbci_cohort_20261010/downloads")
    output_root = REPO_ROOT / config.get(
        "output_root", "research_logs/netbci_cohort_20261010/audits")
    bundle_root = REPO_ROOT / config.get("bundle_root", "data/netbci2026/cohort_v1.0.0")
    manifest_path = download_root / subject / "download_manifest.json"
    output = output_root / subject
    bundle = bundle_root / subject
    require(not output.exists() and not bundle.exists(),
            "Prior audit/bundle exists; choose new output roots to preserve evidence")
    output.mkdir(parents=True)
    try:
        result = audit(data_root, manifest_path)
        require(result["summary"]["subject"] == subject, "Manifest contains wrong subject")
        sessions = config.get("expected_sessions", ["01", "02", "03", "04"])
        runs = config.get("expected_runs", ["01", "02", "03", "04", "05", "06"])
        require({item["session"] for item in result["runs"]} == set(sessions),
                "Incomplete or unexpected derivative sessions")
        for session in sessions:
            require({item["run"] for item in result["runs"] if item["session"] == session}
                    == set(runs), "Incomplete or unexpected derivative run structure")
        upstream_path = data_root / "sourcedata/sourcedata_provenance.json"
        manifest = json.loads(manifest_path.read_text())
        require("sourcedata/sourcedata_provenance.json" in {item["path"] for item in manifest},
                "Upstream subject mapping is not pinned by the subject manifest")
        upstream = json.loads(upstream_path.read_text())
        original_roots = [REPO_ROOT / path for path in config.get(
            "original_header_roots", ["data/netbci2026/original_v2.2_metadata",
                                      "data/netbci2026/nm000305/v1.0.0/sourcedata"])]
        original_subject, headers = inspect_original_headers(
            upstream, subject, result["runs"], original_roots)
        verified = sum(item["original_header_hash_verified"] for item in headers)
        require(verified == len(headers), "Original headers expected for this phase are unavailable")
        require(all(f"sourcedata/{item['original_header_file']}" in
                    {entry["path"] for entry in manifest} for item in headers),
                "Original headers absent from the pinned per-subject manifest")
        if "expected_sfreq_hz" in config:
            require(all(item["sampling_frequency_hz"] == config["expected_sfreq_hz"]
                        for item in result["runs"]),
                    "Actual derivative sampling rate differs from approved pipeline")
        result["synthetic"] = False
        result["scope"].update({"whole_dataset_validated": False,
                                "original_signals_compared": False,
                                "behavior_trial_outcomes_verified": False})
        result["upstream_mapping"] = {
            "derivative_subject": subject, "original_subject": original_subject,
            "mapping_evidence": "explicit subject and original file fields in pinned provenance",
            "provenance_sha256": file_sha256(upstream_path),
            "declared_original_headers": len(headers), "actual_headers_hash_verified": verified,
            "original_metadata_access_status": "verified_cached_headers" if verified == len(headers)
            else "upstream_header_hashes_declared_only_or_partial",
            "run_score_order_verified": False, "score_denominator_verified": False,
            "trial_behavior_mapping": "unresolved",
        }
        result["original_header_audits"] = headers
        result["cohort_audit_script_sha256"] = file_sha256(Path(__file__))
        result["configuration"] = {"path": str(config_path), "sha256": file_sha256(config_path),
                                    "parameters": config}
        result["limitations"] = [
            "The EDF/BIDS derivative is the actual signal source; original signals were not compared.",
            "Unavailable original headers/rates remain unresolved; provenance hashes are declarations.",
            "Subject/session scores can be linked, but score vector run order and denominator are unresolved.",
            "No behavior percentages are broadcast to EEG trials or converted to hit/miss labels.",
            "Finite signals and stable channel order do not establish artifact-free EEG or learning.",
            "Four protocol session IDs do not establish verified real dates or retention intervals.",
        ]
        write_tsv(output / "original_header_inventory.tsv", headers)
        subset = load_netbci_subset(data_root, manifest_path, subject=subject)
        require(subset.dataset.n_trials == result["summary"]["total_trials"],
                "Audit and adapter trial counts disagree")
        header_by_run = {(row["session"], row["run"]): row for row in headers}
        event_rows = []
        for item in subset.trials:
            header = header_by_run[(item.session, item.run)]
            event_rows.append({
                **asdict(item), "original_subject": original_subject,
                "signal_unit": "V", "onset_unit": "s", "duration_unit": "s",
                "sample_origin": 0, "original_header_file": header["original_header_file"],
                "declared_original_header_sha256": header["declared_original_header_sha256"],
                "original_header_hash_verified": header["original_header_hash_verified"],
                "behavior_trial_outcome": "unresolved", "behavior_score_denominator": "unresolved",
            })
        require(len({row["trial_id"] for row in event_rows}) == len(event_rows),
                "Duplicate trial identity")
        write_tsv(output / "events.tsv", event_rows)
        run_rows = []
        for item in result["runs"]:
            header = header_by_run[(item["session"], item["run"])]
            run_rows.append({
                "subject": subject, "original_subject": original_subject,
                "session": item["session"], "run": item["run"], "source_file": item["file"],
                "source_edf_sha256": file_sha256(data_root / item["file"]),
                "trial_count": item["trial_count"],
                "right_hand_count": item["class_counts"].get("right_hand", 0),
                "rest_count": item["class_counts"].get("rest", 0),
                "channel_count": item["channel_count"],
                "channel_names_json": json.dumps(item["channel_names"]),
                "sampling_frequency_hz": item["sampling_frequency_hz"],
                "signal_samples": item["signal_samples"],
                "continuous_duration_s": item["signal_samples"] / item["sampling_frequency_hz"],
                "trial_durations_s_json": json.dumps(item["trial_durations_s"]),
                "trial_lengths_samples_json": json.dumps(item["trial_lengths_samples"]),
                "edf_physical_units_json": json.dumps(item["physical_units"]),
                "mne_signal_unit": "V", "whole_signal_finite": item["whole_signal_finite"],
                "original_header_hash_verified": header["original_header_hash_verified"],
                "original_sampling_frequency_hz": header["original_sampling_frequency_hz"],
                "behavior_run_score": "unresolved", "behavior_trial_outcomes": "unresolved",
            })
        write_tsv(output / "run_inventory.tsv", run_rows)
        shape = list(subset.dataset.X.shape)
        save_netbci_bundle(bundle, subset)
        # Metadata save hashes the NPZ and retains explicit per-trial source identity.
        metadata = json.loads((bundle / "metadata.json").read_text())
        require(metadata["epochs_sha256"] == file_sha256(bundle / "epochs.npz"),
                "Saved NPZ checksum mismatch")
        adapter_receipt = {
            "status": "passed_real_derivative_exact_slice_adapter_and_saved_checksum",
            "synthetic": False, "subject": subject, "original_subject": original_subject,
            "shape": shape, "sampling_frequency_hz": subset.dataset.sfreq,
            "channel_names": list(subset.dataset.channel_names), "signal_unit": "V",
            "trial_count": len(subset.trials), "bundle_directory": str(bundle.resolve()),
            "epochs_sha256": metadata["epochs_sha256"],
            "metadata_sha256": file_sha256(bundle / "metadata.json"),
            "source_manifest_sha256": file_sha256(manifest_path),
            "cohort_script_sha256": file_sha256(Path(__file__)),
            "provenance": collect_provenance(int(config.get("seed", 42)), REPO_ROOT),
            "behavior_values_broadcast_to_trials": False, "training_performed": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        del subset
        gc.collect()
        write_json(output / "adapter_receipt.json", adapter_receipt)
        result["elapsed_seconds"] = time.monotonic() - started
        result["output_artifact_sha256"] = {
            path.name: file_sha256(path) for path in sorted(output.iterdir()) if path.is_file()}
        write_json(output / "audit.json", result)
        print(json.dumps({"subject": subject, "status": result["status"],
                          "n_trials": result["summary"]["total_trials"], "shape": shape,
                          "original_headers_hash_verified": verified,
                          "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
        return result
    except Exception as error:
        write_json(output / "failure.json", {
            "synthetic": False, "subject": subject, "status": "failed_real_subject_audit",
            "error_type": type(error).__name__, "error": str(error),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_sha256": file_sha256(config_path),
            "script_sha256": file_sha256(Path(__file__)),
            "elapsed_seconds": time.monotonic() - started,
            "training_performed": False,
        })
        raise


def cohort_summary(audits: list[dict], requested_subjects: list[str]) -> dict:
    """Aggregate only successfully audited participants, retaining actual channel orders."""
    actual_subjects = [result["summary"]["subject"] for result in audits]
    require(len(actual_subjects) == len(set(actual_subjects)), "Duplicate audited participant")
    require(set(actual_subjects) <= set(requested_subjects), "Unexpected audited participant")
    require(bool(audits), "No successful real audits")
    mappings = {result["summary"]["subject"]: result["upstream_mapping"]["original_subject"]
                for result in audits}
    require(len(set(mappings.values())) == len(mappings), "Duplicate original participant mapping")
    require(all(result["summary"]["all_checks_pass"] is True for result in audits),
            "Cannot aggregate failed audit")
    orders = {result["summary"]["subject"]: result["runs"][0]["channel_names"]
              for result in audits}
    first_order = next(iter(orders.values()))
    intersection = set(first_order)
    for order in orders.values():
        intersection &= set(order)
    common_order = [name for name in first_order if name in intersection]
    counts = Counter()
    sessions = []
    for result in audits:
        counts.update(result["summary"]["class_counts"])
        for session in result["summary"]["sessions"]:
            sessions.append({"subject": result["summary"]["subject"],
                             "original_subject": result["upstream_mapping"]["original_subject"],
                             **session})
    runs = [row for result in audits for row in result["runs"]]
    return {
        "synthetic": False, "status": "real_derivative_cohort_audit_summary",
        "requested_subjects": requested_subjects,
        "successfully_audited_subjects": actual_subjects,
        "unvalidated_subjects": [subject for subject in requested_subjects
                                 if subject not in actual_subjects],
        "subject_count": len(audits), "subject_map": mappings,
        "subject_map_evidence": "explicit fields in pinned NEMAR sourcedata provenance",
        "session_count": len(sessions), "run_count": len(runs),
        "total_trials": sum(counts.values()), "class_counts": dict(counts),
        "sessions": sessions, "channel_orders_by_subject": orders,
        "all_channel_orders_equal": all(order == first_order for order in orders.values()),
        "common_channel_order": common_order,
        "common_channel_count": len(common_order),
        "channel_selection_or_reordering_performed": False,
        "sampling_frequencies_hz": sorted({row["sampling_frequency_hz"] for row in runs}),
        "eeg_channel_counts": sorted({row["channel_count"] for row in runs}),
        "original_sampling_frequencies_hz": sorted({
            header["original_sampling_frequency_hz"] for result in audits
            for header in result.get("original_header_audits", [])
            if isinstance(header["original_sampling_frequency_hz"], (float, int))}),
        "total_continuous_seconds": sum(row["signal_samples"] / row["sampling_frequency_hz"]
                                        for row in runs),
        "total_exact_task_window_seconds": sum(row["trial_count"] * row["trial_durations_s"][0]
                                               for row in runs),
        "original_headers_hash_verified": sum(result["upstream_mapping"]["actual_headers_hash_verified"]
                                               for result in audits),
        "declared_original_headers": sum(result["upstream_mapping"]["declared_original_headers"]
                                         for result in audits),
        "whole_dataset_validated": False, "original_signals_compared": False,
        "behavior_trial_outcomes_verified": False, "training_performed": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs/netbci_cohort.json")
    parser.add_argument("--subjects", nargs="+", required=True)
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--aggregate-output", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    require(len(args.subjects) == len(set(args.subjects)), "Duplicate requested participant")
    require(set(args.subjects) <= set(config["subjects"]), "Subject outside approved config")
    audit_root = REPO_ROOT / config.get("output_root", "research_logs/netbci_cohort_20261010/audits")
    results, failures = [], []
    for subject in args.subjects:
        if args.aggregate_only:
            path = audit_root / subject / "audit.json"
            if path.exists():
                results.append(json.loads(path.read_text()))
            else:
                failures.append({"subject": subject, "error": "No successful audit receipt"})
            continue
        try:
            results.append(audit_subject(subject, config, args.config))
        except Exception as error:
            failures.append({"subject": subject, "error_type": type(error).__name__,
                             "error": str(error)})
            print(json.dumps(failures[-1]), flush=True)
    if args.aggregate_output:
        summary = cohort_summary(results, args.subjects)
        summary["failures"] = failures
        summary["config_sha256"] = file_sha256(args.config)
        summary["script_sha256"] = file_sha256(Path(__file__))
        summary["input_audit_sha256"] = {
            subject: file_sha256(audit_root / subject / "audit.json")
            for subject in summary["successfully_audited_subjects"]}
        write_json(args.aggregate_output, summary)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
