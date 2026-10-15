"""Prepare exact query input identities from frozen metadata, never raw query data.

This standard-library-only command has no download or evaluation entry point.
The generated inventory is preparation, with execution_enabled=false. Its query
trial order references the existing split; labels and signal arrays are not copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "configs/kumar_frozen_query_inputs_20261015.json"
PROTOCOL = "configs/kumar_cross_session_20261012.json"
SPLIT = "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json"
OFFICIAL = "research_logs/public_data_expansion_20261010/kumar2024_nm000177_v1.0.5_selection_manifest.json"
FORMAL = "research_logs/gpu_preparation_20261014/formal_data_plan.json"
RAW_RECEIPT = "research_logs/public_data_expansion_20261010/r2/kumar2024_raw_20261011_run01.json"
ADAPTER = "src/learning_preserving_bci/datasets/kumar.py"
PRIOR = "research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run02"
PINS = {
    PROTOCOL: "f1b2d0fa870493cc2aaab906fe6d8b1227e45b2a270e06700e3ca137fbfe9c89",
    SPLIT: "ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28",
    OFFICIAL: "377eb25e0938fde905b023a309b8b7adebd1a4779fd48c3d2a2d6ce22cb16750",
    FORMAL: "6d1461720eda23287d93614e28205bdb0feabeaed71d49fec2a4f9659e70548d",
    RAW_RECEIPT: "0eb79f83138fb9e07ec7fd22cb7527bacde8f815f5b987b50e504e5e099a5071",
    ADAPTER: "48e382dc770f48b8a7418ac196974949afabdc038c069550bcffbb618864fd07",
    PRIOR + "/source_events.json": "bbf46eec8ffdd739084b685582b91636a786ed4febb1fb6b0ee773710467be37",
}
QUERY_ROLES = ("source_query", "target_query")
SUFFIXES = ("channels.tsv", "eeg.edf", "eeg.json", "events.json", "events.tsv")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def indexed(entries, key):
    result = {entry[key]: entry for entry in entries}
    require(len(result) == len(entries), "Duplicate metadata input identity")
    return result


def expected_query_files(config):
    """Fixed whole-run role scope; no labels or measured performance are used."""
    split = config["split"]
    require(split["source_session"] == "ses-0"
            and split["source_train_runs"] == ["run-0", "run-1"]
            and split["source_validation_runs"] == ["run-2"]
            and split["source_query_runs"] == ["run-3"]
            and split["target_sessions"] == [f"ses-{i}" for i in range(1, 6)]
            and split["target_support_runs"] == ["run-0"]
            and split["target_query_runs"] == "all_remaining_runs",
            "Frozen whole-run split changed")
    require(len(set(config["subjects"])) == len(config["subjects"]), "Duplicate participant")
    result = {}
    for subject in config["subjects"]:
        require(re.fullmatch(r"sub-\d+", subject) is not None, "Unsafe subject identity")
        for session in range(6):
            runs = [3] if session == 0 else range(1, 4 if session == 1 else 3)
            for run in runs:
                path = f"{subject}/ses-{session}/eeg/{subject}_ses-{session}_task-imagery_run-{run}_eeg.edf"
                result[path] = "source_query" if session == 0 else "target_query"
    return result


def select_scope(config, split, official_entries, historical_entries, receipt_entries):
    """Pure metadata join, also used with synthetic fixtures in software tests."""
    query_edfs = expected_query_files(config)
    official = indexed(official_entries, "path")
    historical = indexed(historical_entries, "relative_path")
    receipts = indexed(receipt_entries, "relative_path")
    trials = split["trials"]
    require(len({t["trial_id"] for t in trials}) == len(trials), "Duplicate frozen trial")
    query = [t for t in trials if t["role"] in QUERY_ROLES]
    require({t["source_file"] for t in query} == set(query_edfs), "Incomplete query run scope")
    for trial in trials:
        if trial["source_file"] in query_edfs:
            require(trial["role"] == query_edfs[trial["source_file"]], "Mixed or changed run role")
    for trial in query:
        require(trial["subject"] == trial["source_file"].split("/")[0], "Trial subject differs from file")
        require(trial["raw_file_sha256"] == historical[trial["source_file"]]["sha256"],
                "Split and archived raw identity disagree")
    wanted = {"dataset_description.json": "dataset_metadata"}
    for subject in config["subjects"]:
        for session in range(6):
            wanted[f"{subject}/ses-{session}/{subject}_ses-{session}_scans.tsv"] = "acquisition_metadata"
    for edf, role in query_edfs.items():
        prefix = edf.removesuffix("_eeg.edf")
        wanted.update({prefix + "_" + suffix: role for suffix in SUFFIXES})
    files = []
    for path, role in sorted(wanted.items()):
        require(path in official and path in historical and path in receipts,
                "Missing official or prior trusted input identity: " + path)
        published, old, receipt = official[path], historical[path], receipts[path]
        require(not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts,
                "Unsafe input path")
        require(re.fullmatch(r"[0-9a-f]{64}", old.get("sha256", "")) is not None,
                "Missing historical SHA256; never infer a new one")
        require(old["bytes"] == published["size"] == receipt["bytes"]
                and old["sha256"] == receipt["sha256"] and old["key"] == receipt["key"],
                "Conflicting historical input identities")
        full_get = (receipt["verification"] == "full_get_sha256_verified"
                    and receipt["readback_bytes"] == receipt["bytes"]
                    and receipt["selected_for_full_readback"] is True)
        archived_identity = (receipt["verification"] == "head_length_and_sha256_metadata_verified"
                             and receipt["status"] == "uploaded_head_verified"
                             and receipt["uploaded_bytes"] == receipt["bytes"]
                             and receipt["selected_for_full_readback"] is False)
        require(full_get or archived_identity, "Invalid historical source-byte provenance")
        require(published["checksum_algorithm"] in {"git", "sha256"}, "Unknown official checksum")
        if published["checksum_algorithm"] == "sha256":
            require(published["checksum"] == old["sha256"], "Official SHA256 conflict")
        files.append({
            "relative_path": path, "bytes": old["bytes"], "sha256": old["sha256"],
            "key": old["key"], "checksum_algorithm": published["checksum_algorithm"],
            "checksum": published["checksum"], "url": published["url"], "role": role,
            "historical_R2_verification": receipt["verification"],
            "historical_R2_full_GET_verified": full_get,
        })
    return files, query


def build_manifest(root=ROOT):
    """Read only the pinned metadata dependencies, never the configured data root."""
    raw = {}
    dependencies = []
    for path, expected in PINS.items():
        content = (root / path).read_bytes()
        require(digest(content) == expected, "Frozen metadata dependency changed: " + path)
        raw[path] = content
        dependencies.append({"path": path, "bytes": len(content), "sha256": expected})
    config, split = json.loads(raw[PROTOCOL]), json.loads(raw[SPLIT])
    require(config["subjects"] == [f"sub-{i}" for i in range(1, 19)], "Frozen 18-subject scope changed")
    formal, receipt = json.loads(raw[FORMAL]), json.loads(raw[RAW_RECEIPT])
    require(formal["source_receipt_sha256"] == PINS[RAW_RECEIPT]
            and formal["split_sha256"] == PINS[SPLIT], "Historical manifest provenance changed")
    files, query = select_scope(config, split, json.loads(raw[OFFICIAL]), formal["files"], receipt["files"])
    require(len(files) == 1189 and sum(e["bytes"] for e in files) == 1043686331
            and len(query) == 4320 and sum(t["included"] for t in query) == 4290,
            "Frozen query inventory totals changed")
    for edf in sorted(expected_query_files(config)):
        path = PRIOR + "/runs/" + edf.replace("/", "__") + ".json"
        content = (root / path).read_bytes()
        run = json.loads(content)
        require(run["status"] == "passed" and run["source_file"] == edf,
                "Prior numerical receipt identity changed")
        require(re.fullmatch(r"[0-9a-f]{64}", run["whole_signal_numeric_sha256"]) is not None,
                "Missing prior whole-signal numerical hash")
        dependencies.append({"path": path, "bytes": len(content), "sha256": digest(content)})
    return {
        "schema_version": 1, "status": "frozen_query_input_metadata_preparation_only",
        "execution_enabled": False, "raw_query_files_read": False,
        "query_arrays_loaded": False, "query_labels_loaded_from_raw_files": False,
        "downloads_performed": False, "fits_executed": 0,
        "allowed_roles": list(QUERY_ROLES), "subjects": config["subjects"],
        "development_subjects": config["development_subjects"],
        "final_test_subjects": config["final_test_subjects"],
        "source_scope": "ses-0/run-3 only",
        "target_scope": "ses-1/runs-1,2,3; ses-2,3,4,5/runs-1,2 only",
        "target_support_files_included": False,
        "acquisition_metadata_scope": "all six scans.tsv per participant for unchanged adapter chronology checks",
        "source_plan_path": FORMAL, "source_plan_sha256": PINS[FORMAL],
        "historical_R2_source_receipt_path": RAW_RECEIPT,
        "historical_R2_source_receipt_sha256": PINS[RAW_RECEIPT],
        "historical_SHA256_provenance": "Existing archived local-byte SHA256 and official checksums; historical HEAD metadata is not full GET proof",
        "current_raw_input_verification": "not_performed; authorization required before full-byte query input verification",
        "split_manifest_path": SPLIT, "split_manifest_sha256": PINS[SPLIT],
        "adapter_path": ADAPTER, "adapter_sha256": PINS[ADAPTER],
        "protocol_path": PROTOCOL, "protocol_sha256": PINS[PROTOCOL],
        "file_count": len(files), "bytes": sum(e["bytes"] for e in files),
        "edf_count": sum(e["relative_path"].endswith(".edf") for e in files),
        "row_count": len(query), "included_row_count": sum(t["included"] for t in query),
        "excluded_partial_row_count": sum(not t["included"] for t in query),
        "rows_by_role": dict(Counter(t["role"] for t in query)),
        "included_rows_by_role": dict(Counter(t["role"] for t in query if t["included"])),
        "ordered_query_trial_ids": [t["trial_id"] for t in query],
        "included_query_trial_ids": [t["trial_id"] for t in query if t["included"]],
        "trial_labels_and_numeric_hashes": "Use unchanged pinned split metadata; not duplicated here",
        "dependencies": sorted(dependencies, key=lambda e: e["path"]), "files": files,
    }


def encoded(manifest):
    return (json.dumps(manifest, indent=2) + "\n").encode()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--write", action="store_true", help="Exclusively create metadata manifest")
    args = parser.parse_args(argv)
    manifest = build_manifest()
    content = encoded(manifest)
    if args.write:
        with args.output.open("xb") as stream:
            stream.write(content)
    else:
        require(args.output.read_bytes() == content, "Prepared inventory differs from frozen metadata")
    print(json.dumps({"status": "metadata_inventory_created" if args.write else "metadata_inventory_verified",
                      "manifest_sha256": digest(content), "files": manifest["file_count"],
                      "bytes": manifest["bytes"], "query_EDFs": manifest["edf_count"],
                      "execution_enabled": False, "raw_query_files_read": False}))


if __name__ == "__main__":
    main()
