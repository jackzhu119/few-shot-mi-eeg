"""Audit saved event metadata and prior header receipts; never open EEG or models."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "data/public_eeg/kumar2024/nm000177/v1.0.5"
PRIOR = ROOT / "research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run02"
MANIFEST = (
    ROOT
    / "research_logs/public_data_expansion_20261010/kumar2024_nm000177_v1.0.5_selection_manifest.json"
)
PROVENANCE = DATA / "sourcedata/sourcedata_provenance.json"
LEGACY = ROOT / "research_logs/public_data_expansion_20261010/longitudinal_receipts"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT,
        help="Output directory; every report is published exclusively, without overwrite.",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = 0
    inputs = {}

    def require(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            raise ValueError(message)

    def read(path):
        path = Path(path)
        require(
            path.suffix not in {".edf", ".gdf", ".npy", ".npz", ".pt", ".tar"},
            "Forbidden signal/model input",
        )
        payload = path.read_bytes()
        key = str(path.relative_to(ROOT))
        record = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        require(key not in inputs or inputs[key] == record, "Input changed during audit")
        inputs[key] = record
        return payload

    def obj(path):
        return json.loads(read(path))

    official = {row["path"]: row for row in obj(MANIFEST)}

    def official_bytes(relative):
        payload = read(DATA / relative)
        entry = official[relative]
        require(len(payload) == entry["size"], "Official metadata size mismatch")
        if entry["checksum_algorithm"] == "git":
            digest = hashlib.sha1(
                b"blob " + str(len(payload)).encode() + b"\0" + payload
            ).hexdigest()
        else:
            require(entry["checksum_algorithm"] == "sha256", "Unsupported metadata checksum")
            digest = hashlib.sha256(payload).hexdigest()
        require(digest == entry["checksum"], "Official metadata digest mismatch")
        return payload

    source = obj(PRIOR / "source_events.json")
    require(len(source) == 7200, "Source event inventory changed")
    require(len({e["trial_id"] for e in source}) == 7200, "Duplicate event identity")
    by_file = defaultdict(list)
    for event in source:
        by_file[event["source_file"]].append(event)
    require(len(by_file) == 360, "Run inventory changed")
    partial = []
    fields, labels, values, counts_by_session = Counter(), Counter(), Counter(), Counter()
    all_stops_inside = True
    intervals_overlapping_next_event = []
    for filename, expected in sorted(by_file.items()):
        require(filename.endswith("_eeg.edf"), "Unexpected source receipt identity")
        prefix = filename.removesuffix("_eeg.edf")
        rows = list(
            csv.DictReader(
                io.StringIO(official_bytes(prefix + "_events.tsv").decode()), delimiter="\t"
            )
        )
        description = json.loads(official_bytes(prefix + "_events.json"))
        sidecar = json.loads(official_bytes(prefix + "_eeg.json"))
        receipt = obj(PRIOR / "runs" / (filename.replace("/", "__") + ".json"))
        require(
            receipt["status"] == "passed" and receipt["source_file"] == filename,
            "Prior signal/header audit identity not passed",
        )
        require(len(rows) == len(expected) == 20, "Run event coverage changed")
        require(sidecar["SamplingFrequency"] == receipt["sfreq"] == 512.0, "Sampling rate changed")
        require(
            description["onset"]["Units"] == description["duration"]["Units"] == "s",
            "Sidecar time units changed",
        )
        fields.update(rows[0].keys())
        for idx, (row, event) in enumerate(zip(rows, expected), 1):
            require(event["source_row"] == idx, "Event row mismatch")
            require(
                event["label"] == row["trial_type"] and event["stored_value"] == int(row["value"]),
                "Class identity changed",
            )
            require(
                (event["label"], event["stored_value"]) in {("left_hand", 1), ("right_hand", 2)},
                "Unexpected retained event type",
            )
            require(event["start_sample"] == int(row["sample"]), "Event sample changed")
            require(
                event["onset_seconds"] == float(row["onset"])
                and event["duration_seconds"] == float(row["duration"]),
                "Event times changed",
            )
            require(
                abs(event["onset_seconds"] * 512 - event["start_sample"]) < 1e-6,
                "Onset/sample mapping mismatch",
            )
            require(
                abs(event["duration_seconds"] * 512 - event["sample_count"]) < 1e-3,
                "Duration/sample-count mapping mismatch",
            )
            require(
                event["stop_sample_exclusive"] - event["start_sample"] == event["sample_count"],
                "End sample identity mismatch",
            )
            inside = (
                0 <= event["start_sample"] < event["stop_sample_exclusive"] <= receipt["n_times"]
            )
            require(inside, "Stored interval exceeds prior-audited recording boundary")
            all_stops_inside = all_stops_inside and inside
            labels[event["label"]] += 1
            values[event["stored_value"]] += 1
            counts_by_session[event["session"]] += 1
            if idx < 20 and event["stop_sample_exclusive"] > expected[idx]["start_sample"]:
                intervals_overlapping_next_event.append(event["trial_id"])
            if event["sample_count"] != 2560:
                partial.append(
                    {
                        **event,
                        "prior_audited_recording_n_times": receipt["n_times"],
                        "is_last_retained_class_event": idx == 20,
                        "stop_equals_recording_end": event["stop_sample_exclusive"]
                        == receipt["n_times"],
                        "end_boundary_evidence_source": str(
                            (PRIOR / "runs" / (filename.replace("/", "__") + ".json")).relative_to(
                                ROOT
                            )
                        ),
                        "causal_reason_for_truncation": "not_established_from_derivative_metadata",
                    }
                )
            else:
                require(event["duration_seconds"] == 5.0, "Full window duration changed")
    require(len(partial) == 44, "Partial inventory changed")
    require(all(e["is_last_retained_class_event"] for e in partial), "Partial is not final row")
    require(
        all(e["stop_equals_recording_end"] for e in partial), "Partial does not meet recording end"
    )
    require(all(e["session"] != "ses-0" for e in partial), "Unexpected offline partial")

    description = json.loads(official_bytes("dataset_description.json"))
    readme = official_bytes("README.md").decode()
    provenance = json.loads(official_bytes("sourcedata/sourcedata_provenance.json"))
    require(
        description["Version"] == "1.0.5" and description["DatasetType"] == "derivative",
        "Frozen derivative metadata changed",
    )
    require(
        provenance["moabb_class"] == "Kumar2024"
        and provenance["moabb_version_used"] == "1.5.0dev0",
        "Exporter identification changed",
    )
    adapter_bytes = read(LEGACY / "moabb_kumar_source.py")
    access = obj(LEGACY / "license_code_receipts.json")["moabb_kumar_source"]
    require(
        hashlib.sha256(adapter_bytes).hexdigest() == access["sha256"],
        "Saved adapter digest changed",
    )
    require(
        len(adapter_bytes) == access["bytes"] == 19771 and access["status"] == 200,
        "Saved adapter acquisition receipt mismatch",
    )
    adapter = adapter_bytes.decode()
    require("interval=[0, 5]" in adapter, "Saved adapter interval not found")
    require(
        'raw.annotations.rename({"769": "left_hand", "770": "right_hand"})' in adapter,
        "Saved adapter class-trigger mapping not found",
    )

    pdf = read(OUT / "original_dataset_description.pdf")
    fetch = obj(OUT / "original_codebook_github_fetch.json")
    require(
        hashlib.sha1(b"blob " + str(len(pdf)).encode() + b"\0" + pdf).hexdigest() == fetch["sha"],
        "Original codebook Git blob digest mismatch",
    )
    require(
        hashlib.sha256(pdf).hexdigest()
        == "4c4c2f773c90fb5ee903c40aed65b57c5f36aaa63ed0e7dab7860fa7db058889",
        "Original codebook SHA256 mismatch",
    )
    text = read(OUT / "original_dataset_description.txt").decode()
    require(
        all(
            token in text
            for token in ["Cue Left/Right", "Task perios starts", "7691/7701", "7693/7703"]
        ),
        "Actual codebook text missing marker descriptions",
    )
    epoch = obj(OUT / "original_epoching_github_fetch.json")["structuredContent"]
    code = epoch["content"].encode()
    require(
        hashlib.sha1(b"blob " + str(len(code)).encode() + b"\0" + code).hexdigest() == epoch["sha"],
        "Original task-bounded extraction source digest mismatch",
    )
    require(
        "type(n)==7691 || type(n)==7701" in epoch["content"],
        "Original extraction task-start code missing",
    )

    summary = {
        "status": "saved_metadata_timing_audit_passed_with_phase_coverage_unresolved",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "metadata and prior header-audit receipts only; no signal, model, query prediction or fitting read",
        "checks": checks,
        "source_events": len(source),
        "runs": len(by_file),
        "full_5s_windows": len(source) - len(partial),
        "partial_windows": len(partial),
        "class_counts": dict(labels),
        "retained_value_counts": dict(values),
        "retained_event_columns": sorted(fields),
        "events_per_session": dict(sorted(counts_by_session.items())),
        "all_stored_intervals_inside_prior_audited_edf_bounds": all_stops_inside,
        "partial_source_row_counts": dict(Counter(e["source_row"] for e in partial)),
        "partial_session_counts": dict(sorted(Counter(e["session"] for e in partial).items())),
        "all_partial_final_class_event_and_stop_at_recording_end": True,
        "partial_duration_seconds_min_max": [
            min(e["duration_seconds"] for e in partial),
            max(e["duration_seconds"] for e in partial),
        ],
        "stored_intervals_overlapping_next_retained_event": intervals_overlapping_next_event,
        "cue_anchor_chain": {
            "original_author_codebook_fixed_commit": "548470542e63f97ab777684c1f5e4f1cace4b8ed",
            "codebook_769_770": "Cue Left/Right",
            "codebook_7691_7701": "Task period starts (PDF has typographical 'perios')",
            "codebook_7692_7702": "Timeout/Incorrect Hit for Online, Trial End for Offline",
            "codebook_online_7693_7703": "Cue Left/Right Delivered",
            "saved_official_moabb_adapter_sha256": access["sha256"],
            "adapter_retained_class_events": {"769": "left_hand", "770": "right_hand"},
            "adapter_interval_seconds": [0, 5],
            "nemar_version": description["Version"],
            "nemar_generated_by": description["GeneratedBy"],
            "provenance_declared_moabb_version": provenance["moabb_version_used"],
            "conclusion": "Published derivative task-label windows follow the documented cue-code/[0,5] convention; sustained MI over all five seconds is not established.",
            "not_claimed": [
                "all original GDF marker arrays decoded",
                "exact historical exporter commit pinned",
                "trial-specific cue-to-task or end latencies verified",
                "all online intervals overlap result/rest",
                "44 partial events represent 44 early MI terminations",
            ],
        },
        "minimal_missing_evidence": [
            "Exact historical NEMAR conversion code/commit and options, or maintainer-confirmed cue-to-derivative sample mapping",
            "Original bar-task marker POS/TYP arrays for all 360 runs, preserving 769/770,7691/7701,7692/7702,7693/7703 and recording end",
            "Trial linkage and marker clock/sample-origin mapping sufficient to compare exported onset/end to original task onset/end",
        ],
        "source_provenance_file_inventory": {
            "files": len(provenance["files"]),
            "extension_counts": dict(Counter(Path(e["file"]).suffix for e in provenance["files"])),
            "original_bytes_not_read": True,
        },
        "readme_trial_length_claim_present": "| Trial length | 5 s |" in readme,
        "input_files": len(inputs),
        "new_fits": 0,
        "new_model_forward_passes": 0,
        "window_or_protocol_changes": 0,
    }
    for rel, expected in inputs.items():
        payload = (ROOT / rel).read_bytes()
        require(
            len(payload) == expected["bytes"]
            and hashlib.sha256(payload).hexdigest() == expected["sha256"],
            "Read-only input hash changed",
        )
    summary["checks"] = checks
    summary["all_input_hashes_unchanged_after_audit"] = True
    outputs = {
        "saved_metadata_timing_audit.json": summary,
        "partial_boundary_inventory.json": partial,
        "input_sha256_manifest.json": inputs,
    }
    for filename, payload in outputs.items():
        with (output_dir / filename).open("x") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "checks": checks,
                "input_files": len(inputs),
                "events": len(source),
                "partials_at_recording_end": len(partial),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
