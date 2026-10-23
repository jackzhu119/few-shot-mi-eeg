#!/usr/bin/env python3
"""Prepare frozen Kumar development inputs once from existing local EDFs.

This offline packaging command performs fixed preprocessing only. It does not
fit a decoder, choose a rule, infer predictions, download data, or modify the
original EDF/cache. School training consumes the prepared NumPy files and does
not need MNE/SciPy. Completed participants resume by cheap metadata checks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402
from hpc_recalibration.data import (  # noqa: E402
    Split, atomic_json, load_split, save_split, sha256_file, validate_task_inputs,
)

SUBJECTS = ("sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def file_record(path: Path, relative: Path) -> dict:
    stat = path.stat()
    return {"path": str(relative), "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(path)}


def validate_saved_participant(output: Path, receipt_path: Path, binding: dict,
                               source_root: Path) -> dict | None:
    if not receipt_path.exists():
        return None
    receipt = json.loads(receipt_path.read_text())
    if receipt["binding"] != binding:
        raise ValueError(f"Prepared scientific binding changed: {receipt_path}; use a new input version")
    for record in receipt["outputs"]:
        path = output / record["path"]
        if not path.is_file():
            raise ValueError(f"Prepared shard disappeared: {path}")
        stat = path.stat()
        if stat.st_size != record["bytes"] or stat.st_mtime_ns != record["mtime_ns"]:
            if sha256_file(path) != record["sha256"]:
                raise ValueError(f"Prepared shard changed: {path}; preserve it and restore known bytes")
    for record in receipt["source_files"]:
        path = source_root / record["path"]
        stat = path.stat()
        if stat.st_size != record["bytes"] or stat.st_mtime_ns != record["mtime_ns"]:
            if sha256_file(path) != record["sha256"]:
                raise ValueError(f"Original input changed: {path}")
    return receipt


def task_template(subject: str, paths: dict) -> dict:
    source_sessions = {s for s, role in paths if role == "source_train"}
    if len(source_sessions) != 1:
        raise ValueError("Exactly one source session is required")
    source = next(iter(source_sessions))
    result = {"task_id": f"kumar-v2-{subject}", "dataset": "Kumar2024", "participant": subject,
              "source_train": paths[(source, "source_train")],
              "source_validation": paths[(source, "source_validation")],
              "source_query": paths[(source, "source_query")], "targets": [],
              "prior_test_exposure": "all_Kumar_query_results_previously_exposed"}
    for session in sorted({s for s, role in paths if role == "target_support"},
                          key=lambda name: int(name.rsplit("-", 1)[-1])):
        result["targets"].append({"session": session,
                                  "support": paths[(session, "target_support")],
                                  "query": paths[(session, "target_query")]})
    return result


def prepare(args) -> dict:
    source_root, output = Path(args.source_root).resolve(), Path(args.output_root).resolve()
    config_path, split_path = Path(args.config).resolve(), Path(args.split_manifest).resolve()
    adapter_path = REPO / "src/learning_preserving_bci/datasets/kumar.py"
    config = json.loads(config_path.read_text())
    manifest = json.loads(split_path.read_text())
    subjects = list(args.subjects)
    if not subjects or not set(subjects) <= set(SUBJECTS) or len(subjects) != len(set(subjects)):
        raise ValueError("This preparation covers unique members of the six frozen development IDs")
    rows = [r for r in manifest["trials"] if r["subject"] in subjects]
    included = [r for r in rows if r["included"]]
    estimated_arrays = len(included) * 22 * 640 * 4
    free = shutil.disk_usage(output.parent if output.parent.exists() else REPO).free
    # One prepared tree plus archive and a modest working margin, no arbitrary walltime gate.
    estimated_space = estimated_arrays * 3 + 256 * 1024 * 1024
    if free < estimated_space:
        raise OSError(f"Need approximately {estimated_space} free bytes; observed {free}")
    print(json.dumps({"phase": "preparation_start", "utc": utcnow(), "subjects": subjects,
                      "included_windows": len(included), "partial_events": len(rows) - len(included),
                      "estimated_float32_bytes": estimated_arrays, "available_disk_bytes": free,
                      "decoder_fits": 0, "predictions": 0}), flush=True)
    output.mkdir(parents=True, exist_ok=True)
    binding = {"frozen_config_sha256": sha256_file(config_path),
               "frozen_split_manifest_sha256": sha256_file(split_path),
               "frozen_adapter_sha256": sha256_file(adapter_path),
               "prepared_version": "kumar_cue5s_v1"}
    resolved_config = dict(config)
    for key in ("source_manifest", "prior_signal_audit"):
        value = Path(config[key])
        resolved_config[key] = str(value if value.is_absolute() else REPO / value)
    receipts, templates = [], []
    for subject in subjects:
        receipt_path = output / subject / "preparation_receipt.json"
        receipt = validate_saved_participant(output, receipt_path, binding, source_root)
        if receipt is not None:
            print(json.dumps({"phase": "participant_preparation_reused", "participant": subject,
                              "utc": utcnow(), "included_windows": receipt["included_windows"]}), flush=True)
            receipts.append(receipt)
            templates.append(receipt["task_template"])
            continue
        print(json.dumps({"phase": "participant_preprocessing", "participant": subject,
                          "utc": utcnow(), "decoder_fits": 0}), flush=True)
        # Import only for preparation; the school training payload does not require this stack.
        from learning_preserving_bci.datasets.kumar import load_subject
        loaded = load_subject(source_root, subject, resolved_config, manifest)
        groups = {}
        for index, row in enumerate(loaded.metadata):
            groups.setdefault((row["session"], row["role"]), []).append(index)
        paths, output_records = {}, []
        for (session, role), indices in groups.items():
            indices.sort(key=lambda i, metadata=loaded.metadata: (
                metadata[i]["acquisition_time_utc"],
                int(metadata[i]["run"].rsplit("-", 1)[-1]),
                metadata[i]["start_sample"], metadata[i]["source_row"]))
            relative = Path(subject) / f"{session}_{role}.npz"
            ordered = [loaded.metadata[i] for i in indices]
            value = Split(loaded.X[indices].astype(np.float32, copy=False),
                          loaded.y[indices].astype(np.int64, copy=False),
                          np.asarray([r["trial_id"] for r in ordered], dtype=str),
                          np.asarray([f"{subject}/{r['session']}/{r['run']}" for r in ordered], dtype=str))
            destination = output / relative
            if destination.exists():
                old = load_split(destination)
                if not all(np.array_equal(getattr(value, key), getattr(old, key))
                           for key in ("x", "y", "trial_id", "run_id")):
                    raise ValueError(f"Existing partial preparation changed: {destination}")
            else:
                save_split(destination, value)
            paths[(session, role)] = str(relative)
            output_records.append(file_record(destination, relative))
        events_relative = Path(subject) / "source_events.json"
        atomic_json(output / events_relative, loaded.source_events)
        output_records.append(file_record(output / events_relative, events_relative))
        template = task_template(subject, paths)
        prepared_validation = validate_task_inputs(template, output, full_sha=False)
        sources = []
        for name, proof in loaded.provenance["verified_source_files"].items():
            stat = (source_root / name).stat()
            sources.append({"path": name, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                            "sha256": proof["sha256"], "official_algorithm": proof["official_algorithm"],
                            "official_checksum": proof["official_checksum"]})
        receipt = {"participant": subject, "completed_utc": utcnow(), "binding": binding,
                   "preparation_script_sha256": sha256_file(Path(__file__)),
                   "source_event_count": len(loaded.source_events), "included_windows": len(loaded.y),
                   "excluded_partial_events": len(loaded.source_events) - len(loaded.y),
                   "excluded_trial_ids": [r["trial_id"] for r in loaded.source_events if not r["included"]],
                   "task_template": template, "outputs": output_records, "source_files": sources,
                   "provenance": loaded.provenance, "prepared_validation": prepared_validation,
                   "decoder_fits": 0, "predictions": 0,
                   "processing": config["preprocessing"], "channel_names": list(loaded.channel_names),
                   "sampling_frequency": loaded.sfreq, "data_role_scope": "all_frozen_roles_of_six_development_subjects"}
        atomic_json(receipt_path, receipt)
        receipts.append(receipt)
        templates.append(template)
        print(json.dumps({"phase": "participant_prepared", "participant": subject,
                          "utc": utcnow(), "included_windows": len(loaded.y),
                          "excluded_partial_events": receipt["excluded_partial_events"],
                          "role_shards": len(groups)}), flush=True)
        del loaded
    atomic_json(output / "task_templates.json", templates)
    (output / "README_INPUTS.txt").write_text(
        "Kumar2024 NEMAR nm000177/v1.0.5 development inputs; CC BY 4.0 source data.\n"
        "Only frozen sub-1/4/7/10/13/16; source and target whole-run roles preserved.\n"
        "Cue-anchored 5s, CAR all22, 8-30Hz order4 zero-phase Butterworth, 512->128Hz polyphase, V float32.\n"
        "These are complete data windows, not evidence of sustained MI for all 5 seconds.\n"
        "44 partial events across the full 18-person manifest remain excluded; selected subset counts are in input_manifest.json.\n"
        "Preparation computed no decoder fit, no prediction and no new accuracy result.\n"
        "All previous Kumar query results were exposed; new work is retrospective exploratory.\n"
        "Keep EEG arrays/private checkpoints on shared HPC storage; public manifests and aggregate progress may go to GitHub.\n",
        encoding="utf-8")
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "mne")}
    files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "input_manifest.json" and ".tmp-" not in path.name:
            files.append({"path": str(path.relative_to(output)), "bytes": path.stat().st_size,
                          "sha256": sha256_file(path)})
    final = {"schema_version": 1, "dataset": "Kumar2024", "source_accession": "nm000177/v1.0.5",
             "prepared_version": "kumar_cue5s_v1", "created_utc": utcnow(),
             "subjects": subjects, "source_event_count": len(rows), "included_windows": len(included),
             "excluded_partial_events": len(rows) - len(included),
             "full_original_manifest_events": len(manifest["trials"]),
             "full_original_manifest_partial_events": sum(not r["included"] for r in manifest["trials"]),
             "estimated_float32_bytes": estimated_arrays, "processing_binding": binding,
             "preparation_python": sys.version.split()[0], "preparation_versions": versions,
             "files": files, "task_templates": templates, "decoder_fits": 0, "predictions": 0,
             "scientific_status": "preprocessing_only_no_new_model_results",
             "source_data_license": "CC-BY-4.0", "prior_test_exposure": True}
    atomic_json(output / "input_manifest.json", final)
    public = Path(args.public_manifest).resolve()
    atomic_json(public, final)
    archive = Path(args.archive).resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=archive.name + ".tmp-", dir=archive.parent)
    with os.fdopen(fd, "wb") as stream:
        with tarfile.open(fileobj=stream, mode="w:gz", compresslevel=3) as tar:
            for path in sorted(output.rglob("*")):
                if not path.is_file() or ".tmp-" in path.name:
                    continue
                info = tar.gettarinfo(str(path), arcname=str(Path(output.name) / path.relative_to(output)))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                with path.open("rb") as source:
                    tar.addfile(info, source)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, archive)
    archive_receipt = {"archive": archive.name, "bytes": archive.stat().st_size,
                       "sha256": sha256_file(archive), "top_directory": output.name,
                       "input_manifest_sha256": sha256_file(output / "input_manifest.json"),
                       "payload_files": len(files) + 1, "decoder_fits": 0, "predictions": 0,
                       "created_utc": utcnow()}
    atomic_json(public.with_name("input_archive_receipt.json"), archive_receipt)
    print(json.dumps({"phase": "inputs_archive_ready", **archive_receipt}), flush=True)
    return archive_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default=str(REPO / "data/public_eeg/kumar2024/nm000177/v1.0.5"))
    parser.add_argument("--output-root", default="/workspace/paper2_hpc_v2_delivery/inputs/kumar_cue5s_v1")
    parser.add_argument("--config", default=str(REPO / "configs/kumar_cross_session_20261012.json"))
    parser.add_argument("--split-manifest", default=str(REPO / "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json"))
    parser.add_argument("--public-manifest", default=str(HERE / "configs/input_manifest.json"))
    parser.add_argument("--archive", default="/workspace/paper2_hpc_v2_delivery/paper2-hpc-v2-kumar-dev-inputs.tar.gz")
    parser.add_argument("--subjects", nargs="+", default=list(SUBJECTS))
    args = parser.parse_args()
    try:
        prepare(args)
    except BaseException as exc:
        out = Path(args.output_root)
        out.mkdir(parents=True, exist_ok=True)
        atomic_json(out / f"preparation_failure_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json",
                    {"utc": utcnow(), "exception_type": type(exc).__name__, "traceback": traceback.format_exc(),
                     "decoder_fits": 0, "predictions": 0})
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
