#!/usr/bin/env python3
"""Read-only lineage check: exact original saved text to compact public inputs."""

import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "research_logs/kumar_submission_qc_20261015/run01"
PUBLIC = BASE / "public_inputs"
SAVED = Path("/workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results")
CHECKS = Counter()
READS = {}


def check(value, category):
    CHECKS[category] += 1
    if not value:
        raise AssertionError(category)


def read(path):
    data = path.read_bytes()
    READS[str(path)] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return data


def rows(path):
    return list(csv.DictReader(io.StringIO(read(path).decode("utf-8"))))


def main():
    provenance = json.loads(read(PUBLIC / "public_input_provenance.json"))
    for record in provenance["original_sources"]:
        path = (ROOT if record["kind"] == "repository_text_input" else SAVED) / record[
            "relative_path"
        ]
        data = read(path)
        check(len(data) == record["bytes"], "original_text_length")
        check(hashlib.sha256(data).hexdigest() == record["sha256"], "original_text_sha256")
    original = json.loads(
        read(ROOT / "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json")
    )["trials"]
    compact = json.loads(read(PUBLIC / "frozen_trial_metadata.json"))["trials"]
    check(len(original) == len(compact) == 7200, "original_metadata_identity_count")
    for a, b in zip(original, compact):
        for field, value in b.items():
            check(a.get(field) == value, "compact_metadata_exact_original_fields")
    public = rows(PUBLIC / "saved_predictions.csv")
    index = {(r["trial_id"], r["method"], r["seed"]): r for r in public}
    check(len(index) == len(public) == 25740, "unique_public_prediction_keys")
    consumed = set()
    for subject in range(1, 19):
        cpu = rows(
            ROOT
            / f"research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z/sub-{subject}/query_predictions.csv"
        )
        for row in cpu:
            key = row["trial_id"], row["method"], "cpu_fixed"
            check(key in index and key not in consumed, "original_cpu_prediction_unique_identity")
            consumed.add(key)
            for field in (
                "subject",
                "cohort",
                "session",
                "run",
                "method",
                "trial_id",
                "label",
                "prediction",
            ):
                check(row[field] == index[key][field], "cpu_prediction_exact_original_fields")
            check(row["synthetic"] == "False", "cpu_predictions_real")
        for seed in (20261012, 20261013, 20261014):
            saved = json.loads(read(SAVED / f"sub-{subject}-seed-{seed}.json"))
            check(saved["identity"]["subject"] == f"sub-{subject}", "original_eeg_subject_identity")
            check(saved["identity"]["seed"] == seed, "original_eeg_seed_identity")
            check(
                saved["new_fit"] is False and saved["optimizer_steps"] == 0,
                "historical_query_no_fit_receipt",
            )
            check(
                saved["state_before_sha256"] == saved["state_after_sha256"],
                "historical_query_state_unchanged_receipt",
            )
            for row in saved["predictions"]:
                key = row["trial_id"], "always_frozen_eegnet", str(seed)
                check(
                    key in index and key not in consumed, "original_eeg_prediction_unique_identity"
                )
                consumed.add(key)
                for field in ("subject", "session", "run", "role", "trial_id"):
                    check(row[field] == index[key][field], "eeg_prediction_exact_original_fields")
                check(row["y_true"] == int(index[key]["label"]), "eeg_saved_true_label_exact")
                check(row["y_pred"] == int(index[key]["prediction"]), "eeg_saved_prediction_exact")
    check(consumed == set(index), "every_public_prediction_matches_original")
    expected_rows = {
        "all_role_qc_counts.csv": 540,
        "cohort_method_sensitivity_summary.csv": 96,
        "cohort_paired_contrasts.csv": 12,
        "joined_saved_predictions_qc.csv": 25740,
        "leave_one_participant_out_influence.csv": 136,
        "paired_cross_subset_summary.csv": 6,
        "paired_participant_contrasts.csv": 72,
        "paired_session_contrasts.csv": 432,
        "participant_cross_subset_changes.csv": 72,
        "participant_endpoints.csv": 144,
        "per_participant_session_metrics.csv": 1152,
        "per_seed_session_and_pooled_metrics.csv": 1728,
        "query_identity_qc_ledger.csv": 4320,
    }
    coverage = []
    for name, expected in expected_rows.items():
        count = len(rows(BASE / name))
        check(count == expected, "complete_expected_table_row_counts")
        coverage.append(
            {"file": name, "observed_rows": count, "independent_expected_rows": expected}
        )
    for filename, expected in READS.items():
        data = Path(filename).read_bytes()
        check(
            {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == expected,
            "all_read_inputs_unchanged",
        )
    output = {
        "status": "passed",
        "utc": datetime.now(timezone.utc).isoformat(),
        "scope": "actual original saved JSON/CSV and split metadata bytes only; no EEG arrays or weights",
        "check_count": sum(CHECKS.values()),
        "checks_by_category": dict(CHECKS),
        "all_7200_public_trial_rows_match_original_projected_fields": True,
        "all_25740_public_predictions_match_original_saved_text": True,
        "original_text_manifest_records": len(provenance["original_sources"]),
        "table_coverage": coverage,
        "no_new_inference": True,
        "no_new_fits": True,
        "no_new_R2_GET_claimed": True,
        "all_read_inputs_unchanged": True,
        "read_input_hashes": READS,
        "failures": [],
    }
    with (OUT / "lineage_and_coverage_validation.json").open("x") as f:
        json.dump(output, f, indent=2)
        f.write("\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": sum(CHECKS.values()),
                "public_prediction_rows_matched_to_original": len(consumed),
                "tables": len(coverage),
            }
        )
    )


if __name__ == "__main__":
    main()
