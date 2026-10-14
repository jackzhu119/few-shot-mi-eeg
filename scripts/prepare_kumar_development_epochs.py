"""Reconstruct only development source-training and target-support EEG windows.

The input metadata is already physically restricted. This script never calls the
full-cohort adapter or reads a query, validation, final-cohort or partial window.
It repeats the frozen epoch-local transform and requires exact numerical hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import mne
import numpy as np

from learning_preserving_bci.datasets.kumar import (
    CHANNEL_NAMES, LABELS, numeric_hash, preprocess_epoch, require, role_for,
    sha256_file, validate_split_trials,
)

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_SUBJECTS = ("sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16")
ALLOWED_ROLES = {"source_train", "target_support"}
FROZEN_CONFIG_SHA256 = "f1b2d0fa870493cc2aaab906fe6d8b1227e45b2a270e06700e3ca137fbfe9c89"


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def repository_path(path: str | Path) -> Path:
    result = Path(path)
    return result if result.is_absolute() else ROOT / result


def expected_source_file(subject: str, session: str, run: str) -> str:
    return f"{subject}/{session}/eeg/{subject}_{session}_task-imagery_{run}_eeg.edf"


def validate_selected_metadata(metadata: list[dict], subject: str, config: dict) -> None:
    """Reject forbidden identities/roles before opening any EEG source file."""
    require(subject in DEVELOPMENT_SUBJECTS, "Forbidden final-cohort subject")
    require(isinstance(metadata, list) and bool(metadata), "Missing restricted metadata")
    require(tuple(config["development_subjects"]) == DEVELOPMENT_SUBJECTS,
            "Changed development cohort")
    for trial in metadata:
        require(trial["subject"] == subject and trial["cohort"] == "development",
                "Forbidden cohort or subject identity")
        require(trial["role"] in ALLOWED_ROLES, "Forbidden selected role")
        require(trial["role"] == role_for(trial["session"], trial["run"], config),
                "Frozen role mismatch")
        row = trial["source_row"]
        require(type(row) is int and 1 <= row <= 20, "Invalid source row identity")
        require(trial["trial_id"] == (
            f"{subject}/{trial['session']}/{trial['run']}/row-{row}"
        ), "Trial identity fields mismatch")
        require(trial["source_file"] == expected_source_file(
            subject, trial["session"], trial["run"]
        ), "Unexpected source file identity")
        require(trial["included"] is True and trial["sample_count"] == 2560
                and trial["duration_seconds"] == 5.0
                and trial["processed_sample_count"] == 640,
                "Partial or changed epoch forbidden")
        require(type(trial["start_sample"]) is int
                and type(trial["stop_sample_exclusive"]) is int
                and trial["start_sample"] >= 0
                and trial["stop_sample_exclusive"] - trial["start_sample"] == 2560,
                "Window sample identity mismatch")
        require(trial["onset_seconds"] == trial["start_sample"] / 512,
                "Onset sample identity mismatch")
        require(trial["raw_numeric_unit"] == trial["processed_numeric_unit"] == "V",
                "Changed numeric unit")
        require(trial["label"] in LABELS
                and trial["stored_value"] == LABELS[trial["label"]] + 1,
                "Unknown or changed label")
        require(trial["analysis_eligibility"] == "included_full_5s"
                and trial["exclusion_reason"] is None,
                "Changed eligibility")
        for field in ("raw_file_sha256", "raw_window_numeric_sha256",
                      "processed_window_numeric_sha256"):
            require(re.fullmatch(r"[0-9a-f]{64}", trial.get(field, "")) is not None,
                    f"Missing valid hash: {field}")
    validate_split_trials(metadata, config)
    groups = defaultdict(list)
    for trial in metadata:
        groups[(trial["session"], trial["run"])].append(trial)
    expected = {(config["split"]["source_session"], run)
                for run in config["split"]["source_train_runs"]}
    expected |= {(session, "run-0") for session in config["split"]["target_sessions"]}
    require(set(groups) == expected and len(groups) == 7, "Source/support coverage mismatch")
    for (session, _), trials in groups.items():
        counts = sorted(Counter(t["label"] for t in trials).values())
        if session == config["split"]["source_session"]:
            require(len(trials) == 20 and counts == [10, 10]
                    and {t["source_row"] for t in trials} == set(range(1, 21)),
                    "Source training budget mismatch")
        else:
            require((len(trials), counts) in ((19, [9, 10]), (20, [10, 10])),
                    "Target support budget mismatch")
    for trials in groups.values():
        require(len({t["raw_file_sha256"] for t in trials}) == 1,
                "Conflicting raw file identity")


def verify_source_file(data_root: Path, relative: str, entries: dict,
                       trials: list[dict]) -> tuple[Path, dict]:
    """Bind the allowed EDF to official bytes and all selected metadata rows."""
    require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
            "Unsafe source path")
    require(relative in entries, f"Unpinned source file: {relative}")
    path = data_root / relative
    require(path.resolve().is_relative_to(data_root.resolve()), "Source escapes data root")
    entry = entries[relative]
    require(path.is_file() and path.stat().st_size == entry["size"],
            "Source file size changed")
    digest = sha256_file(path)
    if entry["checksum_algorithm"] == "sha256":
        official = digest
    elif entry["checksum_algorithm"] == "git":
        h = hashlib.sha1(b"blob " + str(entry["size"]).encode() + b"\0")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        official = h.hexdigest()
    else:
        raise ValueError("Unsupported official checksum")
    require(official == entry["checksum"], "Official source checksum mismatch")
    require(all(t["source_file"] == relative and t["raw_file_sha256"] == digest
                for t in trials), "Selected raw file SHA256 mismatch")
    return path, {"source_file": relative, "bytes": entry["size"], "sha256": digest,
                  "official_checksum": official,
                  "official_algorithm": entry["checksum_algorithm"]}


def validate_raw_header(raw, audit: dict, source_proof: dict) -> None:
    require(audit["status"] == "passed" and audit["source_file"] == source_proof["source_file"],
            "Invalid pinned run audit")
    audited_file = audit["verified_source_files"][source_proof["source_file"]]
    require(audited_file["sha256"] == source_proof["sha256"]
            and audited_file["bytes"] == source_proof["bytes"], "Pinned run bytes changed")
    require(raw.first_samp == 0 and raw.info["sfreq"] == audit["sfreq"] == 512
            and tuple(raw.ch_names) == tuple(audit["channel_names"]) == CHANNEL_NAMES
            and raw.get_channel_types() == ["eeg"] * 22
            and audit["n_channels"] == 22, "EDF channels/rate changed")
    require(type(audit["n_times"]) is int and raw.n_times == audit["n_times"] > 0,
            "EDF sample count changed")
    require(all(raw._orig_units[c] == "µV" for c in CHANNEL_NAMES)
            and audit["stored_physical_unit"] == "µV"
            and audit["MNE_numeric_unit"] == "V", "EDF physical unit changed")


def reconstruct_epoch(raw, trial: dict, config: dict) -> tuple[np.ndarray, dict]:
    """Read exactly one allowed full window, with no surrounding signal access."""
    start, stop = trial["start_sample"], trial["stop_sample_exclusive"]
    require(0 <= start < stop <= raw.n_times and stop - start == 2560,
            "Selected epoch outside source bounds")
    epoch = raw.get_data(start=start, stop=stop)
    require(epoch.shape == (22, 2560) and np.isfinite(epoch).all(),
            "Invalid allowed raw epoch")
    raw_hash = numeric_hash(epoch)
    require(raw_hash == trial["raw_window_numeric_sha256"], "Raw window hash mismatch")
    peak_to_peak = float(np.ptp(epoch, axis=-1).max())
    require(peak_to_peak == trial["raw_peak_to_peak_max_volts"]
            and (peak_to_peak > 250e-6) == trial["qc_peak_to_peak_over_250uv"]
            and trial["qc_primary_action"] == "retain_flagged_no_artifact_certification",
            "Frozen QC identity changed")
    processed = preprocess_epoch(epoch, config)
    processed_hash = numeric_hash(processed, dtype="<f4")
    require(processed_hash == trial["processed_window_numeric_sha256"],
            "Processed window hash mismatch")
    return processed, {"trial_id": trial["trial_id"], "source_file": trial["source_file"],
                       "start_sample": start, "stop_sample_exclusive": stop,
                       "raw_window_numeric_sha256": raw_hash,
                       "processed_window_numeric_sha256": processed_hash,
                       "qc_peak_to_peak_over_250uv": trial["qc_peak_to_peak_over_250uv"]}


def prepare_subject(data_root: Path, metadata_path: Path, subject: str, config: dict,
                    entries: dict, output: Path) -> dict:
    metadata_bytes = metadata_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    validate_selected_metadata(metadata, subject, config)
    output.mkdir(parents=True, exist_ok=False)
    grouped = defaultdict(list)
    for index, trial in enumerate(metadata):
        grouped[trial["source_file"]].append((index, trial))
    X = np.empty((len(metadata), 22, 640), dtype=np.float32)
    trial_proofs, file_proofs = [None] * len(metadata), []
    for relative, indexed in grouped.items():
        path, proof = verify_source_file(data_root, relative, entries, [t for _, t in indexed])
        audit_path = repository_path(config["prior_signal_audit"]) / "runs" / (
            relative.replace("/", "__") + ".json"
        )
        audit = json.loads(audit_path.read_text())
        raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
        try:
            validate_raw_header(raw, audit, proof)
            for index, trial in indexed:
                X[index], trial_proofs[index] = reconstruct_epoch(raw, trial, config)
        finally:
            raw.close()
        proof.update(pinned_run_audit_sha256=sha256_file(audit_path),
                     n_times=audit["n_times"], selected_windows=len(indexed))
        file_proofs.append(proof)
    y = np.asarray([LABELS[t["label"]] for t in metadata], dtype=np.int64)
    trial_ids = np.asarray([t["trial_id"] for t in metadata], dtype=str)
    tensor_path = output / "restricted_epochs.npz"
    np.savez_compressed(tensor_path, X=X, y=y, trial_ids=trial_ids)
    saved_metadata = output / "included_trial_metadata.json"
    with saved_metadata.open("xb") as stream:
        stream.write(metadata_bytes)
    receipt = {"schema_version": 1, "status": "passed", "subject": subject,
               "cohort": "development", "synthetic": any(t.get("synthetic", False)
                                                               for t in metadata),
               "metadata_input_sha256": sha256_file(metadata_path),
               "metadata_saved_sha256": sha256_file(saved_metadata),
               "metadata_sha256": sha256_file(saved_metadata),
               "metadata_byte_identity_preserved": True,
               "tensor_file": tensor_path.name, "tensor_sha256": sha256_file(tensor_path),
               "epochs_sha256": sha256_file(tensor_path),
               "tensor_shape": list(X.shape), "tensor_dtype": str(X.dtype),
               "tensor_numeric_sha256": numeric_hash(X, dtype="<f4"),
               "numeric_hash_convention": "float32 little-endian C-order volts",
               "trial_count": len(metadata), "trial_order": trial_ids.tolist(),
               "role_counts": dict(Counter(t["role"] for t in metadata)),
               "quality_flags_retained": sum(t["qc_peak_to_peak_over_250uv"] for t in metadata),
               "source_file_count": len(file_proofs), "source_files": file_proofs,
               "trial_proofs": trial_proofs,
               "preload": False, "read_access": "only_exact_selected_5s_windows",
               "query_windows_read": 0, "validation_windows_read": 0,
               "final_cohort_access": False, "partial_windows_read": 0,
               "learned_transform_fits": 0, "decoder_fits": 0}
    write_json(output / "subject_receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    require(sha256_file(args.config) == FROZEN_CONFIG_SHA256, "Changed frozen config bytes")
    config = json.loads(args.config.read_text())
    require(tuple(config["development_subjects"]) == DEVELOPMENT_SUBJECTS,
            "Changed development cohort")
    manifest_path = repository_path(config["source_manifest"])
    manifest = json.loads(manifest_path.read_text())
    entries = {e["path"]: e for e in manifest}
    require(len(entries) == len(manifest), "Duplicate pinned source paths")
    # Validate every restricted input before creating outputs or opening any EDF.
    metadata_paths = {s: args.metadata_root / s / "included_trial_metadata.json"
                      for s in DEVELOPMENT_SUBJECTS}
    for subject, path in metadata_paths.items():
        validate_selected_metadata(json.loads(path.read_text()), subject, config)
    args.output.mkdir(parents=True, exist_ok=False)
    script_path = Path(__file__).resolve()
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    receipts = [prepare_subject(args.data_root, path, subject, config, entries,
                                args.output / subject)
                for subject, path in metadata_paths.items()]
    adapter_path = ROOT / "src/learning_preserving_bci/datasets/kumar.py"
    receipt = {"schema_version": 1, "status": "passed", "started_at": started,
               "finished_at": datetime.now(timezone.utc).isoformat(),
               "runtime_seconds": time.monotonic() - clock,
               "synthetic": any(r["synthetic"] for r in receipts),
               "development_subjects": list(DEVELOPMENT_SUBJECTS),
               "allowed_roles": sorted(ALLOWED_ROLES), "subject_count": len(receipts),
               "trial_count": sum(r["trial_count"] for r in receipts),
               "source_file_count": sum(r["source_file_count"] for r in receipts),
               "source_ancestor_commit": source_commit,
               "executed_script_sha256": sha256_file(script_path),
               "adapter_sha256": sha256_file(adapter_path),
               "frozen_config_sha256": sha256_file(args.config),
               "pinned_source_manifest_sha256": sha256_file(manifest_path),
               "metadata_root": str(args.metadata_root.resolve()),
               "data_root": str(args.data_root.resolve()),
               "subject_receipts": [{"subject": s, "path": f"{s}/subject_receipt.json",
                                     "sha256": sha256_file(args.output / s / "subject_receipt.json")}
                                    for s in DEVELOPMENT_SUBJECTS],
               "runtime_versions": {"python": platform.python_version(),
                                    **{p: version(p) for p in ("numpy", "scipy", "mne")}},
               "all_metadata_bytes_and_trial_order_preserved": True,
               "query_windows_read": 0, "validation_windows_read": 0,
               "final_cohort_access": False, "partial_windows_read": 0,
               "learned_transform_fits": 0, "decoder_fits": 0}
    write_json(args.output / "preparation_receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "subject_count", "trial_count",
                                            "source_file_count", "runtime_seconds")}))


if __name__ == "__main__":
    main()
