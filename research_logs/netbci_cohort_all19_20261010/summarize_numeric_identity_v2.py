"""Preserve the full raw audit and write its compact inspectable content summary."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
    overlap_counts["source_training_reference_query_affected_subjects"] = overlap[
        "source_training_reference_query_affected_subjects"]
    overlap_counts["affected_subject_sessions"] = [row for row in overlap["by_subject_session"]
                                                   if row["exact_source_training_overlap_count"] or
                                                   row["exact_source_reference_query_overlap_count"]]
    continuous_affected = {subject for group in groups if group["cross_subject"] for subject in group["subjects"]}
    task_affected = {subject for group in record["task_window_duplicate_groups"]
                     if group["cross_subject"] for subject in group["subjects"]}
    affected = continuous_affected | task_affected
    window_by_id = {row["trial_id"]: row for row in record["source_task_windows"]}
    assert len(window_by_id) == record["summary"]["source_task_windows"]
    same_session_counts = defaultdict(Counter)
    task_cross_subject_locations = set()
    for group in record["task_window_duplicate_groups"]:
        location_members = defaultdict(list)
        for identifier in group["members"]:
            row = window_by_id[identifier]
            assert row["numeric_sha256"] == group["numeric_sha256"]
            location = row["subject"], row["session"]
            location_members[location].append(row)
            if group["cross_subject"]:
                task_cross_subject_locations.add(location)
        for location, rows in location_members.items():
            if len(rows) < 2:
                continue
            counter = same_session_counts[location]
            counter["numeric_groups_repeated_within_subject_session"] += 1
            counter["repeated_window_members"] += len(rows)
            if any(count > 1 for count in Counter(row["run"] for row in rows).values()):
                counter["numeric_groups_repeated_within_same_run"] += 1
    subject_key = lambda value: int(value.split("-")[-1])  # noqa: E731
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
        "cross_subject_affected_identities": sorted(affected, key=subject_key),
        "cross_subject_continuous_affected_identities": sorted(continuous_affected, key=subject_key),
        "cross_subject_task_window_affected_identities": sorted(task_affected, key=subject_key),
        "cross_subject_task_window_affected_subject_sessions": [
            {"subject": subject, "session": session} for subject, session in
            sorted(task_cross_subject_locations, key=lambda pair: (subject_key(pair[0]), pair[1]))],
        "identities_without_detected_cross_subject_exact_continuous_copies":
            [subject for subject in record["subject_order"] if subject not in continuous_affected],
        "identities_without_detected_cross_subject_exact_signal_copies":
            [subject for subject in record["subject_order"] if subject not in affected],
        "same_subject_session_task_repeat_flags": [
            {"subject": subject, "session": session, **dict(counts)}
            for (subject, session), counts in sorted(
                same_session_counts.items(), key=lambda pair: (subject_key(pair[0][0]), pair[0][1]))],
        "duplicate_flags_change_cohort_membership": False,
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
