"""Close independent all19 review receipts and explicitly census retained failures.

No production modules or statistics helpers are imported. This reads saved tables
and hashes only; it does not load EEG arrays or refit models.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def table(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main():
    review = read(BASE / "independent_methods_review_run01.json")
    sensitivity = read(BASE / "independent_sensitivity_review_run01.json")
    summary = read(BASE / "summary_run01/cohort_summary.json")
    config = read(ROOT / "configs/netbci_cohort_all19_20261010.json")
    assert review["status"] == "passed_independent_saved_table_arithmetic_and_methods_review"
    assert sensitivity["status"] == "passed_independent_dynamic_cross_person_exact_copy_sensitivity_arithmetic"
    assert review["review_source_sha256"] == sha(BASE / "independent_review_source_v2.py")
    assert sensitivity["review_source_sha256"] == sha(BASE / "independent_sensitivity_review_v2.py")
    for entry in review["input_sha256"].values():
        assert sha(entry["path"]) == entry["sha256"], entry["path"]
    assert review["source_events"] == 14431
    assert review["eligible_analysis_trials"] == 14429
    assert review["session_joins"] == len(config["subjects"]) * len(config["session_order"]) == 76

    failures, constant_cells, unavailable, model_checks = [], [], [], []
    matching_status_rows, qc_trial_count = [], 0
    for subject in config["subjects"]:
        directory = ROOT / "results/netbci_cohort_all19_20261010" / subject / "run01"
        trial_rows = table(directory / "trial_features.tsv")
        flags = sum(row["qc_flag"] == "True" for row in trial_rows)
        qc_trial_count += flags
        assert flags == next(row["qc_flagged"] for row in review["counts"] if row["subject"] == subject)
        decoder = read(directory / "decoder_results.json")
        assert len(decoder) == len(config["session_order"])
        local_constants = [
            {"subject": subject, "session": row["session"],
             "label": "rest" if row["confusion_matrix_rest_right_hand"][0][1] == 0 else "right_hand"}
            for row in decoder if row["constant_prediction"]
        ]
        constant_cells.extend(local_constants)
        local_failures = read(directory / "failures.json")
        assert len([row for row in local_failures if row.get("type") == "constant_prediction"]) == len(local_constants)
        for cell in local_constants:
            assert len([row for row in local_failures if row.get("type") == "constant_prediction"
                        and row["session"] == cell["session"] and row["label"] == cell["label"]]) == 1
        status_rows = read(directory / "matched_variants_status.json")
        for status in status_rows:
            matching_status_rows.append({"subject": subject, **status})
            if status["status"] == "unavailable":
                assert status["preset_not_relaxed"] is True
                unavailable.append({"subject": subject, **status})
                assert len([row for row in local_failures if row["scope"] == "matched_geometry"
                            and row["variant"] == status["variant"]
                            and row["error"] == status["error"]]) == 1
        assert all(row.get("type") == "constant_prediction" or row["scope"] == "matched_geometry"
                   for row in local_failures), f"Unexpected unreviewed scientific failure: {subject}"
        failures.extend({"subject": subject, **row} for row in local_failures)
        model = read(directory / "CSP_LDA_model_audit.json")
        assert model["fit_calls"] == 1 and model["prediction_replay_exact"] is True
        assert model["query_state_unchanged"] is True
        assert model["parameter_sha256_before"] == model["parameter_sha256_after"] == sha(directory / "csp_lda.pkl")
        model_checks.append({"subject": subject, "model_sha256": model["parameter_sha256_after"],
                             "fit_calls": model["fit_calls"], "source_train_n": model["source_train_n"]})
    assert constant_cells == review["constant_prediction_sessions"]
    assert len(failures) == summary["scientific_failure_records_n"]
    assert qc_trial_count == summary["qc_flags_retained_in_primary"]
    matched_rows = table(BASE / "summary_run01/participant_matched_geometry.tsv")
    assert len(matched_rows) == len(config["subjects"]) * len(config["session_order"]) * 2 == 152
    assert len({(row["subject"], row["session"], row["variant"]) for row in matched_rows}) == len(matched_rows)
    matching_availability = {
        variant: {"available_subjects": sum(row["variant"] == variant and row["status"] == "available"
                                             for row in matching_status_rows),
                  "unavailable_subjects": [row["subject"] for row in matching_status_rows
                                            if row["variant"] == variant and row["status"] == "unavailable"]}
        for variant in ("all_six_runs", "qc_common_four_runs")
    }
    retained = set(sensitivity["retained_identities"])
    retained_matching_availability = {
        variant: {"requested_identities": len(retained),
                  "available_identities": sum(row["subject"] in retained and row["variant"] == variant
                                               and row["status"] == "available" for row in matching_status_rows),
                  "unavailable_identities": [row["subject"] for row in matching_status_rows
                                              if row["subject"] in retained and row["variant"] == variant
                                              and row["status"] == "unavailable"]}
        for variant in ("all_six_runs", "qc_common_four_runs")
    }
    replay = read(BASE / "independent_first10_replay_comparison_20261011.json")
    assert replay["comparison_count"] == replay["byte_identical_artifact_count"] == 160
    assert replay["all160_stable_artifacts_byte_identical"] is True
    for row in replay["subjects"]:
        for name, expected in (("old", row["old_receipt_sha256"]), ("new", row["new_receipt_sha256"])):
            stem = "netbci_cohort_resume_20261010" if name == "old" else "netbci_cohort_all19_20261010"
            assert sha(ROOT / "results" / stem / row["subject"] / "run01/analysis_receipt.json") == expected
    physio_base = ROOT / "research_logs/public_data_expansion_20261010/physionet_eegmmidb"
    physio_review = read(physio_base / "independent_source_validation_20261011.json")
    physio_source = read(physio_base / "audit_20261011_run02/signal_audit.json")
    assert physio_review["all_checks_passed"] is True
    assert physio_review["signal_file_count"] == len(physio_review["checks"]) == 327
    assert all(row["all_checks_passed"] for row in physio_review["checks"])
    assert physio_review["primary_audit_file_sha256"] == sha(physio_base / "audit_20261011_run02/signal_audit.json")
    qual = physio_source["source_qualification"]
    assert qual["pass_eligible_file_count"] == 315
    assert len(qual["pass_eligible_all_three_run_subjects"]) == 105
    assert {row["subject"] for row in qual["unqualified_files"]} == {"S088", "S089", "S092", "S100"}
    inputs = [BASE / "independent_methods_review_run01.json", BASE / "independent_sensitivity_review_run01.json",
              BASE / "independent_first10_replay_comparison_20261011.json", BASE / "summary_run01/cohort_summary.json",
              BASE / "summary_run01/participant_matched_geometry.tsv",
              physio_base / "independent_source_validation_20261011.json",
              physio_base / "audit_20261011_run02/signal_audit.json"]
    output = {
        "status": "closed_independent_all19_arithmetic_sensitivity_and_failure_census",
        "synthetic": False, "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configured_source_identities": 19, "independent_biological_identity_established": False,
        "source_events": review["source_events"], "eligible_analysis_trials": review["eligible_analysis_trials"],
        "session_joins": review["session_joins"], "source_short_events_retained": review["excluded_source_events"],
        "constant_prediction_session_count": len(constant_cells),
        "constant_prediction_identity_count": len({row["subject"] for row in constant_cells}),
        "constant_prediction_sessions": constant_cells, "qc_flags_retained_in_primary": qc_trial_count,
        "scientific_failure_records": len(failures),
        "scientific_failure_type_counts": dict(Counter(row.get("type", row["scope"]) for row in failures)),
        "matched_summary_rows_including_unavailable_cells": len(matched_rows),
        "matching_availability": matching_availability,
        "unavailable_matched_variants_preserved": unavailable,
        "retained_sensitivity_identities": sensitivity["retained_identities"],
        "excluded_sensitivity_identities": sensitivity["excluded_identities"],
        "retained_matching_availability": retained_matching_availability,
        "source_frozen_model_checks": model_checks,
        "all19_arithmetic_first_last_changes": [{key: value for key, value in row.items() if key != "individual_changes"}
                                                 for row in review["paired_changes"]],
        "post_observation_sensitivity_first_last_changes": sensitivity["paired_changes"],
        "first_ten_replayed_stable_outputs_byte_identical": 160,
        "physionet_independent_source_validation_closed": {
            "source_identities": 109, "source_signal_files": 327, "qualified_three_run_identities": 105,
            "qualified_signal_files": 315, "unqualified_source_identities_preserved": ["S088", "S089", "S092", "S100"],
            "new_models_fitted": False},
        "independent_of_production_helpers": True, "EEG_arrays_loaded": False, "models_refitted": False,
        "limits": ["Statistical calculations were independently recomputed from saved trial, prediction, and participant tables; EEG filtering/PSD and geometric arrays were not independently rerun.",
                   "Source training and freezing are source-reviewed and receipt/hash-checked; independent reviewer did not refit models.",
                   "Exact duplicate exclusions depend only on raw source-content identities and apply after observations; no independent replication or biological identity claim.",
                   "Behavior scores remain aggregate participant/session observations; trial outcomes and denominators are unresolved.",
                   "No causal human-learning or skill-retention inference is established."],
        "input_sha256": {str(path.relative_to(ROOT)): sha(path) for path in inputs},
        "review_source_sha256": sha(__file__),
    }
    path = BASE / "independent_methods_closeout_run01.json"
    with path.open("x") as stream:
        stream.write(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "constant_prediction_sessions": len(constant_cells),
                      "qc_flags": qc_trial_count, "retained_sensitivity_identities": len(retained)}))


if __name__ == "__main__":
    main()
