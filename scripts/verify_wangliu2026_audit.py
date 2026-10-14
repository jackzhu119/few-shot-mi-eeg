#!/usr/bin/env python3
"""Reconcile durable Wang/Liu source ledgers and emit source constraints."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from download_wangliu2026_source import write_json


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as stream:
        return [json.loads(line) for line in stream]


def verify(output: Path) -> dict:
    records = read_jsonl(output / "source_record_ledger.jsonl")
    events = read_jsonl(output / "source_event_ledger.jsonl")
    members = read_jsonl(output / "source_member_sha256_ledger.jsonl")
    summary = json.loads((output / "source_audit_summary.json").read_text())
    duplicates = json.loads((output / "source_exact_content_duplicates.json").read_text())
    assert len(records) == summary["recordings"] == 268
    assert len(events) == summary["source_event_count"] == 10697
    assert len(members) == summary["member_crc_and_sha256_verified_count"] == 536
    assert len({r["source_id"] for r in records}) == len(records)
    assert len({e["event_id"] for e in events}) == len(events)
    assert len({m["member"] for m in members}) == len(members)
    assert all(m["crc32_verified"] and m["crc32"] == m["central_directory_crc32"] for m in members)
    assert dict(collections.Counter(e["native_type"] for e in events)) == summary["source_event_type_counts"]
    assert all(e["duration_samples"] is None and not e["native_window_eligible"]
               and not e["analysis_window_inferred"] for e in events)
    assert all(r["preprocessing_performed"] == [] and not r["future_analysis_qualified"] for r in records)
    record_map = {r["source_id"]: r for r in records}
    member_map = {m["member"]: m for m in members}
    event_map = collections.defaultdict(list)
    for event in events:
        event_map[event["source_id"]].append(event)
    for record in records:
        assert len(event_map[record["source_id"]]) == record["source_event_count"]
        assert dict(collections.Counter(e["native_type"] for e in event_map[record["source_id"]])) == record["source_event_type_counts"]
    comparisons = []
    for group in duplicates["scalp59_numeric_sha256"]:
        base_id = group["source_ids"][0]
        base = record_map[base_id]
        base_events = [e["native_fields"] for e in event_map[base_id]]
        for other_id in group["source_ids"][1:]:
            other = record_map[other_id]
            comparisons.append({"source_ids": [base_id, other_id],
                                "scalp59_numeric_sha256_equal": base["scalp59_numeric_sha256"] == other["scalp59_numeric_sha256"],
                                "all64_numeric_sha256_equal": base["all64_numeric_sha256"] == other["all64_numeric_sha256"],
                                "paired_fdt_byte_sha256_equal": member_map[base["fdt_member"]]["sha256"] == member_map[other["fdt_member"]]["sha256"],
                                "all_native_event_fields_equal": base_events == [e["native_fields"] for e in event_map[other_id]],
                                "cross_published_identity": base["subject_id"] != other["subject_id"],
                                "within_person_cross_phase": base["subject_id"] == other["subject_id"] and base["phase"] != other["phase"]})
    gate = {"status": "full_source_ingested_audited_not_model_qualified",
            "ledger_reconciliation_passed": True,
            "member_verification_terms": "536 member CRC/size checks verified; member SHA256 values locally computed and recorded. Figshare publishes the whole-archive MD5, not separate per-member SHA256 references. Whole ZIP official MD5 passed; R2 full GET SHA256 verifies identical local-to-remote bytes.",
            "bounded_resource_terms": "64 MiB is the disk scratch-pair cap. EEG values are read one recording in 16,384-sample blocks; aggregate record/event metadata remains in RAM. No corpus-wide participant EEG tensors are created.",
            "native_markers_are_validated_task_windows": False,
            "all_native_durations_absent": True,
            "source_point_markers_retained": len(events),
            "actual_native_marker_counts": summary["source_event_type_counts"],
            "paper_reported_totals": {"rest": 5360, "MI_combined": 5360},
            "observed_native_marker_totals": {"rest": 5351, "MI_combined": 5346},
            "native_event_anomalies_against_nominal40": [
                {k: r[k] for k in ("source_id", "subject_id", "phase", "run", "n_times", "source_event_count", "source_event_type_counts")}
                for r in records if r["source_event_count"] != 40],
            "cross_identity_exact_copy_subject_union": sorted({subject for group in duplicates["scalp59_numeric_sha256"] if group["cross_published_identity"] for subject in group["subject_ids"]}),
            "within_person_cross_phase_exact_copy_subject_union": sorted({subject for group in duplicates["scalp59_numeric_sha256"] if group["within_subject_cross_phase_reuse"] for subject in group["subject_ids"]}),
            "duplicate_comparisons": comparisons,
            "scalp_constant_channel_records": [
                {"source_id": r["source_id"], "channels": [c["name"] for c in r["per_channel"] if c["verified_label_type"] == "eeg" and c["exact_constant"]]}
                for r in records if any(c["verified_label_type"] == "eeg" and c["exact_constant"] for c in r["per_channel"])],
            "source_declared_phase_order": ["pre", "post", "follow"],
            "actual_recording_dates_present_or_validated": False,
            "within_person_train_test_content_reuse": "sub-02 post/follow full recording copies would leak content across a split assigning those phases to opposite sides; no analysis split assigned or model fitted",
            "train_test_splits_frozen": False,
            "source_physical_units": "native EEGLAB float32 convention and MNE microvolt-to-volt conversion preserved; independent hardware physical calibration not established",
            "reference": "native SET common; paper CPz description and root average metadata separately preserved; no rereference applied",
            "qc_interpretation": "Constant channels, large DC offsets and amplitude flags are descriptive source issues, not expert artifact rejection or quality certification.",
            "source_independence_interpretation": "Cross-ID exact copies invalidate treating their EEG as independent published identities; correct original ownership unresolved. No detected copy does not prove biological independence.",
            "processed_variant": "only prior representative preserved for43-channel/average/ICA/boundary contrast; no processed whole archive downloaded or substitute raw channel count/reference used",
            "qualification": {"raw_source_integrity": True, "model_analysis": False, "algorithm_causal_evidence": False,
                              "human_skill_retention": False, "clinical_outcome_benefit": False},
            "next_gates": summary["future_analysis_gates"]}
    assert len(comparisons) == 8
    assert sum(c["cross_published_identity"] for c in comparisons) == 4
    assert sum(c["within_person_cross_phase"] for c in comparisons) == 4
    assert all(c["paired_fdt_byte_sha256_equal"] and c["all64_numeric_sha256_equal"]
               and c["all_native_event_fields_equal"] for c in comparisons)
    write_json(output / "source_constraints_and_reconciliation.json", gate)
    return gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.output)
    print(json.dumps({"ledger_reconciliation_passed": result["ledger_reconciliation_passed"],
                      "source_point_markers_retained": result["source_point_markers_retained"],
                      "duplicate_comparisons": len(result["duplicate_comparisons"])}))


if __name__ == "__main__":
    main()
