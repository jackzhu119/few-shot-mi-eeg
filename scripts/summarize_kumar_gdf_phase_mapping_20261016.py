"""Summarize actual task-marker timing and coverage, without decoding EEG."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def quantile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (position - low) * (values[high] - values[low])


def distribution(values):
    values = list(values)
    return {"n": len(values), "min": min(values) if values else None,
            "p05": quantile(values, 0.05), "p25": quantile(values, 0.25),
            "median": quantile(values, 0.5), "p75": quantile(values, 0.75),
            "p95": quantile(values, 0.95), "max": max(values) if values else None,
            "mean": sum(values) / len(values) if values else None}


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def summarize(rows):
    valid = [row for row in rows if row["phase_mapping_success"] == "True"]
    complete = [row for row in valid if row["original_window_complete_5s"] == "True"]
    partial = [row for row in valid if row["original_window_complete_5s"] != "True"]
    by_session = defaultdict(list)
    for row in rows:
        by_session[row["session"]].append(row)
    result = {
        "trial_count": len(rows), "phase_mapped": len(valid), "complete_original_windows": len(complete),
        "partial_original_windows": len(partial),
        "source_class_counts": dict(Counter(row["class"] for row in rows)),
        "cue_to_task_seconds": distribution(float(row["cue_to_task_start_seconds"]) for row in valid),
        "active_duration_seconds": distribution(float(row["task_active_seconds"]) for row in valid),
        "end_codes": dict(Counter(row["task_end_code"] for row in valid)),
        "original_complete_window_composition": {
            name: distribution(float(row[key]) for row in complete)
            for name, key in {
                "pre_task_seconds": "original_window_pre_task_seconds",
                "active_seconds": "original_window_active_seconds",
                "post_task_seconds": "original_window_post_task_seconds",
            }.items()
        },
        "original_complete_windows_overlap_post_task": sum(row["original_window_overlaps_post_task"] == "True" for row in complete),
        "original_partial_windows_end_at_recording_boundary": sum(row["original_window_ends_at_recording_boundary"] == "True" for row in partial),
        "partial_also_task_below_7s": sum(row["task_duration_below_7s_online"] == "True" for row in partial),
        "fixed_task2s_eligible_all_events": sum(row["task_start_2s_eligible"] == "True" for row in rows),
        "fixed_task2s_eligible_among_original_complete": sum(row["task_start_2s_eligible"] == "True" for row in complete),
        "variable_active_minimum1s_eligible_all_events": sum(row["variable_active_minimum1s_eligible"] == "True" for row in rows),
        "session_summaries": {},
    }
    for session, group in sorted(by_session.items()):
        mapped = [row for row in group if row["phase_mapping_success"] == "True"]
        result["session_summaries"][session] = {
            "events": len(group), "mapped": len(mapped),
            "duration_seconds": distribution(float(row["task_active_seconds"]) for row in mapped),
            "end_codes": dict(Counter(row["task_end_code"] for row in mapped)),
            "active_less_than_2s": sum(float(row["task_active_seconds"]) < 2 for row in mapped),
            "active_less_than_1s": sum(float(row["task_active_seconds"]) < 1 for row in mapped),
            "complete_cue_windows": sum(row["original_window_complete_5s"] == "True" for row in group),
            "complete_cue_windows_overlap_post_task": sum(row["original_window_complete_5s"] == "True" and row["original_window_overlaps_post_task"] == "True" for row in group),
            "fixed_task2s_common_with_original_complete": sum(row["original_window_complete_5s"] == "True" and row["task_start_2s_eligible"] == "True" for row in group),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true", help="Explicitly summarize an incomplete metadata acquisition")
    args = parser.parse_args()
    args.input_dir = args.input_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    mapping = args.input_dir / "trial_event_mapping.csv"
    rows = list(csv.DictReader(mapping.open(encoding="utf-8")))
    frozen_path = ROOT / "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json"
    frozen = {row["trial_id"]: row for row in json.loads(frozen_path.read_bytes())["trials"]}
    if len(frozen) != 7200 or len(rows) != len({row["trial_id"] for row in rows}):
        raise ValueError("Frozen 7200-trial inventory or unique mapped identities changed")
    if len(rows) != 7200 and not args.allow_partial:
        raise ValueError("Incomplete mapping requires explicit --allow-partial")
    for row in rows:
        trial = frozen[row["trial_id"]]
        if trial["label"] != row["class"] or trial["start_sample"] != int(row["cue_sample_0based"]):
            raise ValueError("Frozen trial/class/sample identity mismatch")
        row["frozen_role"] = trial["role"]
        row["frozen_cohort"] = trial["cohort"]
        row["frozen_original_included"] = trial["included"]
        row["original_phase_metadata_available"] = True
    observed = {row["trial_id"]: row for row in rows}
    complete_inventory = []
    for trial_id, trial in frozen.items():
        if trial_id in observed:
            complete_inventory.append(observed[trial_id])
            continue
        missing = {field: "" for field in rows[0]}
        missing.update({
            "trial_id": trial_id, "subject": trial["subject"], "session": trial["session"],
            "run": trial["run"], "source_row": trial["source_row"], "class": trial["label"],
            "source_file": trial["source_file"], "cue_sample_0based": trial["start_sample"],
            "frozen_role": trial["role"], "frozen_cohort": trial["cohort"],
            "frozen_original_included": trial["included"], "original_phase_metadata_available": False,
            "original_window_complete_5s": str(trial["sample_count"] == 2560),
            "phase_mapping_success": "False", "cue_mapping_exact": "False",
            "task_start_2s_eligible": "False", "variable_active_minimum1s_eligible": "False",
            "ambiguity_or_exclusion": "original_gdf_metadata_not_acquired_or_not_mapped",
        })
        complete_inventory.append(missing)
    result = summarize(rows)
    result.update(
        created_utc=datetime.now(timezone.utc).isoformat(),
        decoder_executed=False,
        exploratory_phase_window_not_decoding_results=True,
        all_7200_trials_covered=len(rows) == 7200,
        unmapped_source_trials=7200 - len(rows),
        coverage_denominator_includes_all_7200_frozen_source_events=True,
        original_window_rule_preserved=True,
        interpretation={
            "activity": "Task/feedback marker phase; not proof of uninterrupted imagery or freedom from feedback, eye or muscle signals.",
            "7693_7703": "Codebook literal: Cue Left/Right Delivered; not recoded as correct hit.",
            "7692_7702_online": "Codebook combines timeout and incorrect hit; these cannot be separated from this code alone.",
            "early_end": "A duration below the nominal 7s ceiling is descriptive; no causal outcome label is inferred.",
            "partial": "Original 44 partial windows remain excluded; recording-boundary truncation is distinct from task ending.",
            "range_integrity": "Range-body SHA256 and consistent HTTP206/ETag prove acquired byte slices; whole original GDF SHA256 was not recomputed.",
        },
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.output_dir / "phase_timing_summary.json", result)
    with (args.output_dir / "all_7200_trial_mapping_including_missing.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(complete_inventory)
    group_rows = defaultdict(list)
    for row in complete_inventory:
        group_rows[(row["subject"], row["session"], row["run"], row["frozen_role"], row["class"])].append(row)
    coverage = []
    for (subject, session, run, role, label), group in sorted(group_rows.items(), key=lambda item: str(item[0])):
        coverage.append({
            "subject": subject, "session": session, "run": run, "frozen_role": role,
            "class": label, "all_source_events": len(group),
            "original_complete_5s": sum(row["original_window_complete_5s"] == "True" for row in group),
            "phase_mapped": sum(row["phase_mapping_success"] == "True" for row in group),
            "fixed_task2s_eligible_all": sum(row["task_start_2s_eligible"] == "True" for row in group),
            "fixed_task2s_common_with_original_complete": sum(row["task_start_2s_eligible"] == "True" and row["original_window_complete_5s"] == "True" for row in group),
            "variable_minimum1s_eligible_all": sum(row["variable_active_minimum1s_eligible"] == "True" for row in group),
        })
    with (args.output_dir / "coverage_subject_session_run_role_class.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coverage[0]))
        writer.writeheader()
        writer.writerows(coverage)
    write_json(args.output_dir / "input_sha256_manifest.json", [
        {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in (mapping, frozen_path)
    ])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
