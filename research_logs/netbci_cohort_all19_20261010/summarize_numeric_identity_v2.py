"""Preserve the full raw audit and write its compact inspectable content summary."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Preserve prior summary"
    record = json.loads(args.ledger.read_text())
    assert record["status"] == "complete_exact_numeric_identity_audit"
    assert record["synthetic"] is False
    by_id = {f"{row['subject']}/ses-{row['session']}/run-{row['run']}": row
             for row in record["continuous_runs"]}
    assert len(by_id) == record["summary"]["continuous_runs"]
    assert record["summary"]["official_manifest_matches"] == len(by_id)
    groups = []
    for group in record["continuous_duplicate_groups"]:
        members = []
        for identifier in group["members"]:
            row = by_id[identifier]
            assert row["numeric_sha256"] == group["numeric_sha256"]
            members.append({"identity": identifier, "source_file": row["source_file"],
                            "numeric_sha256": row["numeric_sha256"],
                            "source_edf_sha256": row["source_edf_sha256"],
                            "source_event_sha256": row["source_event_sha256"],
                            "original_header_sha256": row["original_header"]["actual_original_header_sha256"],
                            "official_manifest_match": row["official_manifest_match"],
                            "per_subject_manifest_match": row["per_subject_manifest_match"]})
        groups.append({**{key: value for key, value in group.items() if key != "members"},
                       "members": members,
                       "distinct_whole_edf_sha256": len({row["source_edf_sha256"] for row in members})})
    overlap = record["planned_partition_content_overlap"]
    overlap_counts = {key: value for key, value in overlap.items() if not isinstance(value, list)}
    overlap_counts["affected_subject_sessions"] = [row for row in overlap["by_subject_session"]
                                                   if row["exact_source_training_overlap_count"] or
                                                   row["exact_source_reference_query_overlap_count"]]
    affected = {subject for group in groups if group["cross_subject"] for subject in group["subjects"]}
    output = {
        "status": "compact_verified_pre_model_numeric_identity_summary",
        "synthetic": False, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "full_ledger_file": str(args.ledger.resolve()), "full_ledger_sha256": sha(args.ledger),
        "full_ledger_bytes": args.ledger.stat().st_size, "full_ledger_preserved": True,
        "summary": record["summary"], "method": record["method"],
        "configuration_file": record["configuration_file"],
        "configuration_sha256": record["configuration_sha256"],
        "official_manifest_file": record["official_manifest_file"],
        "official_manifest_sha256": record["official_manifest_sha256"],
        "timing": record["timing"], "role_source": record["role_source"],
        "continuous_duplicate_groups": groups,
        "cross_subject_affected_identities": sorted(affected, key=lambda x: int(x.split("-")[-1])),
        "identities_without_detected_cross_subject_exact_continuous_copies":
            [subject for subject in record["subject_order"] if subject not in affected],
        "planned_partition_content_overlap": overlap_counts,
        "limitations": record["limitations"],
        "audit_script_file": record["script_file"], "audit_script_sha256": record["script_sha256"],
        "summary_source_sha256": sha(Path(__file__)),
    }
    with args.output.open("x") as stream:
        stream.write(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "summary": output["summary"],
                      "cross_subject_affected_identities": output["cross_subject_affected_identities"]}))


if __name__ == "__main__":
    main()
