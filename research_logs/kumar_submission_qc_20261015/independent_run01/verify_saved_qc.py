#!/usr/bin/env python3
"""Independent arithmetic audit of text-only QC inputs and outputs.

No producer helpers, model library, EEG arrays, optimizer or inference imported.
"""

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research_logs/kumar_submission_qc_20261015/run01"
OUT = Path(__file__).resolve().parent
PUBLIC = BASE / "public_inputs"
SUBJECTS = [f"sub-{i}" for i in range(1, 19)]
DEVELOPMENT = {"sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16"}
COHORTS = {
    "development6": DEVELOPMENT,
    "remaining12": set(SUBJECTS) - DEVELOPMENT,
    "all18_secondary": set(SUBJECTS),
}
METHODS = ["source_only", "frozen_csp_lda_recalibration", "refit_csp_lda", "always_frozen_eegnet"]
CONTRASTS = {
    "refit_minus_frozen": ("refit_csp_lda", "source_only"),
    "refit_minus_lda_only": ("refit_csp_lda", "frozen_csp_lda_recalibration"),
}
SUBSETS = ["all_included", "unflagged"]
SCOPES = [*(f"ses-{i}" for i in range(6)), "pooled_target_queries", "pooled_all_queries"]
READS = {}
CHECKS = Counter()
MAX_NUMERICAL_ERROR = 0.0


def require(condition, category):
    CHECKS[category] += 1
    if not condition:
        raise AssertionError(category)


def read(path):
    data = path.read_bytes()
    READS[str(path.relative_to(ROOT))] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return data


def csv_rows(path):
    return list(csv.DictReader(read(path).decode("utf-8").splitlines()))


def same(actual, expected, category):
    global MAX_NUMERICAL_ERROR
    if expected is None:
        require(actual == "" or actual is None, category)
    elif isinstance(expected, bool):
        require(actual == str(expected), category)
    elif isinstance(expected, (float, np.floating)):
        error = abs(float(actual) - expected)
        MAX_NUMERICAL_ERROR = max(MAX_NUMERICAL_ERROR, error)
        require(error < 1e-14, category)
    elif isinstance(expected, int):
        require(int(actual) == expected, category)
    else:
        require(actual == expected, category)


def checked_table(filename, keys):
    rows = csv_rows(BASE / filename)
    indexed = {tuple(r[k] for k in keys): r for r in rows}
    require(len(indexed) == len(rows), "unique_table_keys")
    return indexed


def average(values):
    return math.fsum(values) / len(values)


def uncertainty(values):
    if not values:
        return None, None, None
    mu = average(values)
    if len(values) < 2:
        return mu, None, None
    values = np.asarray(values, dtype=np.float64)
    # Exact frozen convention, independently applied to reconstructed participants.
    random = np.random.default_rng(42)
    choices = random.integers(len(values), size=(10000, len(values)))
    resampled = np.take(values, choices).sum(axis=1) / len(values)
    lower, upper = np.percentile(resampled, [2.5, 97.5])
    return mu, float(lower), float(upper)


def metrics(rows):
    class_rows = [[r for r in rows if r[0] == label] for label in (0, 1)]
    counts = list(map(len, class_rows))
    correct = [sum(y == prediction for y, prediction in group) for group in class_rows]
    predicted = [sum(prediction == label for _, prediction in rows) for label in (0, 1)]
    defined = all(counts)
    return {
        "n_query": len(rows),
        "n_left": counts[0],
        "n_right": counts[1],
        "predicted_left": predicted[0],
        "predicted_right": predicted[1],
        "confusion_00": correct[0],
        "confusion_01": counts[0] - correct[0],
        "confusion_10": counts[1] - correct[1],
        "confusion_11": correct[1],
        "balanced_accuracy": average([correct[k] / counts[k] for k in (0, 1)]) if defined else None,
        "BA_defined": bool(defined),
        "undefined_reason": "" if defined else "absent_true_class",
        "fewer_than_5_per_class": min(counts) < 5,
        "class_collapse": min(predicted) == 0 if rows else None,
    }


def main():
    started = datetime.now(timezone.utc).isoformat()
    read(BASE / "POST_OBSERVATION_PROTOCOL.md")
    read(ROOT / "scripts/analyze_kumar_saved_query_qc_20261015.py")
    read(Path(__file__).resolve())
    provenance = json.loads(read(PUBLIC / "public_input_provenance.json"))
    for filename, expected in provenance["files"].items():
        data = read(PUBLIC / filename)
        require(len(data) == expected["bytes"], "public_input_lengths")
        require(hashlib.sha256(data).hexdigest() == expected["sha256"], "public_input_hashes")
    config = json.loads(read(PUBLIC / "frozen_analysis_configuration.json"))
    require(
        config["quality_control"]["peak_to_peak_threshold_volts"] == 0.00025, "frozen_threshold"
    )
    require(config["statistics"]["bootstrap_replicates"] == 10000, "bootstrap_draws")
    require(config["statistics"]["seed"] == 42, "bootstrap_seed")
    metadata = json.loads(read(PUBLIC / "frozen_trial_metadata.json"))["trials"]
    meta = {r["trial_id"]: r for r in metadata}
    require(len(meta) == len(metadata) == 7200, "event_identity_count")
    complete = [r for r in metadata if r["included"]]
    require(len(complete) == 7156, "complete_window_count")
    for row in complete:
        require(type(row["qc_peak_to_peak_over_250uv"]) is bool, "qc_boolean")
        require(
            row["qc_peak_to_peak_over_250uv"] == (row["raw_peak_to_peak_max_volts"] > 0.00025),
            "qc_fixed_amplitude_rule",
        )
    require(sum(r["qc_peak_to_peak_over_250uv"] for r in complete) == 1512, "qc_complete_total")
    events = {i: r for i, r in meta.items() if r["role"] in {"source_query", "target_query"}}
    queries = {i: r for i, r in events.items() if r["included"]}
    require(len(events) == 4320 and len(queries) == 4290, "query_counts_and_30_exclusions")
    require(
        sum(r["qc_peak_to_peak_over_250uv"] for r in queries.values()) == 922, "query_flagged_count"
    )
    predictions = csv_rows(PUBLIC / "saved_predictions.csv")
    require(len(predictions) == 25740, "prediction_count")
    identities = set()
    grouped = defaultdict(list)
    for row in predictions:
        identity = (row["trial_id"], row["method"], row["seed"])
        require(identity not in identities, "unique_prediction_identity")
        identities.add(identity)
        require(row["trial_id"] in queries, "prediction_is_complete_query")
        frozen = queries[row["trial_id"]]
        for field in ("subject", "cohort", "session", "run", "role"):
            same(row[field], frozen[field], "prediction_metadata_join")
        same(
            row["qc_peak_to_peak_over_250uv"],
            frozen["qc_peak_to_peak_over_250uv"],
            "prediction_qc_join",
        )
        same(row["label"], int(frozen["label"] == "right_hand"), "prediction_label_join")
        require(row["prediction"] in {"0", "1"}, "binary_predictions")
        grouped[(row["subject"], row["method"], row["seed"])].append(row)
    require(len(grouped) == 108, "participant_method_seed_groups")
    expected_groups = {
        (s, m, seed)
        for s in SUBJECTS
        for m in METHODS
        for seed in (
            ["20261012", "20261013", "20261014"] if m == "always_frozen_eegnet" else ["cpu_fixed"]
        )
    }
    require(set(grouped) == expected_groups, "all_three_seeds_no_selection")
    seed_result = {}
    published_seed = checked_table(
        "per_seed_session_and_pooled_metrics.csv",
        ["subject", "method", "seed", "subset", "session"],
    )
    for (subject, method, seed), rows in grouped.items():
        require(
            {r["trial_id"] for r in rows}
            == {i for i, r in queries.items() if r["subject"] == subject},
            "exact_each_seed_query_set",
        )
        for subset in SUBSETS:
            retained = [
                r
                for r in rows
                if subset == "all_included" or r["qc_peak_to_peak_over_250uv"] == "False"
            ]
            for scope in SCOPES:
                selected = [
                    r
                    for r in retained
                    if scope == "pooled_all_queries"
                    or (scope == "pooled_target_queries" and r["session"] != "ses-0")
                    or r["session"] == scope
                ]
                key = subject, method, seed, subset, scope
                scored = metrics([(int(r["label"]), int(r["prediction"])) for r in selected])
                seed_result[key] = scored
                for field, expected in scored.items():
                    same(published_seed[key][field], expected, "seed_metric_fields")
    require(set(published_seed) == set(seed_result), "all_seed_metric_keys")
    combined = {}
    published_combined = checked_table(
        "per_participant_session_metrics.csv", ["subject", "method", "subset", "session"]
    )
    for subject in SUBJECTS:
        for method in METHODS:
            seeds = (
                ["20261012", "20261013", "20261014"]
                if method == "always_frozen_eegnet"
                else ["cpu_fixed"]
            )
            for subset in SUBSETS:
                for scope in SCOPES:
                    values = [seed_result[subject, method, seed, subset, scope] for seed in seeds]
                    key = subject, method, subset, scope
                    result = {
                        k: values[0][k]
                        for k in (
                            "n_query",
                            "n_left",
                            "n_right",
                            "BA_defined",
                            "undefined_reason",
                            "fewer_than_5_per_class",
                        )
                    }
                    require(
                        all(
                            (v["n_left"], v["n_right"]) == (result["n_left"], result["n_right"])
                            for v in values
                        ),
                        "seed_unique_trial_counts",
                    )
                    result["balanced_accuracy"] = (
                        average([v["balanced_accuracy"] for v in values])
                        if result["BA_defined"]
                        else None
                    )
                    result["seeds_included"] = len(seeds)
                    result["class_collapsed_seed_groups"] = sum(
                        v["class_collapse"] is True for v in values
                    )
                    combined[key] = result
                    for field, expected in result.items():
                        same(published_combined[key][field], expected, "seed_BA_averaging_fields")
    require(set(combined) == set(published_combined), "all_combined_metric_keys")
    endpoints = {}
    published_endpoints = checked_table(
        "participant_endpoints.csv", ["subject", "method", "subset"]
    )
    for subject in SUBJECTS:
        for method in METHODS:
            for subset in SUBSETS:
                target = [combined[subject, method, subset, f"ses-{i}"] for i in range(1, 6)]
                missing = [f"ses-{i + 1}" for i, r in enumerate(target) if not r["BA_defined"]]
                result = {
                    "target_five_session_mean_BA": average([r["balanced_accuracy"] for r in target])
                    if not missing
                    else None,
                    "target_endpoint_defined": not missing,
                    "target_undefined_sessions": ";".join(missing),
                    "n_defined_target_sessions": 5 - len(missing),
                    "target_query_trials": sum(r["n_query"] for r in target),
                    "target_left": sum(r["n_left"] for r in target),
                    "target_right": sum(r["n_right"] for r in target),
                    "low_count_target_sessions": sum(r["fewer_than_5_per_class"] for r in target),
                    "source_query_BA": combined[subject, method, subset, "ses-0"][
                        "balanced_accuracy"
                    ],
                    "pooled_all_query_BA": combined[subject, method, subset, "pooled_all_queries"][
                        "balanced_accuracy"
                    ],
                    "pooled_target_query_BA": combined[
                        subject, method, subset, "pooled_target_queries"
                    ]["balanced_accuracy"],
                }
                endpoints[subject, method, subset] = result
                for field, expected in result.items():
                    same(
                        published_endpoints[subject, method, subset][field],
                        expected,
                        "equal_five_target_session_fields",
                    )
    for row in csv_rows(PUBLIC / "original_participant_endpoints.csv"):
        for field in ("source_query_BA", "target_five_session_mean_BA"):
            same(
                row[field],
                endpoints[row["subject"], row["method"], "all_included"][field],
                "historical_original_endpoint_preserved",
            )
    eligibility = {}
    summaries = checked_table(
        "cohort_method_sensitivity_summary.csv", ["cohort", "method", "subset", "endpoint"]
    )
    for key, published in summaries.items():
        cohort, method, subset, endpoint = key
        eligible = sorted(
            s for s in COHORTS[cohort] if endpoints[s, method, subset][endpoint] is not None
        )
        same(published["eligible_subjects"], ";".join(eligible), "cohort_eligibility_identity")
        same(published["n_eligible_participants"], len(eligible), "cohort_eligibility_count")
        same(
            published["ineligible_subjects"],
            ";".join(sorted(COHORTS[cohort] - set(eligible))),
            "cohort_ineligible_identity",
        )
        for field, expected in zip(
            ["mean", "ci95_low", "ci95_high"],
            uncertainty([endpoints[s, method, subset][endpoint] for s in eligible]),
        ):
            same(published[field], expected, "method_cohort_bootstrap")
        if endpoint == "target_five_session_mean_BA":
            eligibility[cohort, method, subset] = eligible
    for method in METHODS:
        require(
            set(eligibility["remaining12", method, "unflagged"])
            == COHORTS["remaining12"] - {"sub-8", "sub-12"},
            "same10_unflagged_all_methods",
        )

    def pair(s, c, subset):
        a, b = [
            endpoints[s, method, subset]["target_five_session_mean_BA"] for method in CONTRASTS[c]
        ]
        return None if a is None or b is None else a - b

    published_pairs = checked_table(
        "paired_participant_contrasts.csv", ["subject", "contrast", "subset"]
    )
    for (subject, contrast, subset), row in published_pairs.items():
        value = pair(subject, contrast, subset)
        same(row["paired_endpoint_defined"], value is not None, "paired_endpoint_defined")
        same(row["mean_difference"], value, "participant_paired_contrasts")
    published_session_pairs = checked_table(
        "paired_session_contrasts.csv", ["subject", "contrast", "subset", "session"]
    )
    for (subject, contrast, subset, scope), row in published_session_pairs.items():
        a, b = [combined[subject, m, subset, scope] for m in CONTRASTS[contrast]]
        expected = (
            a["balanced_accuracy"] - b["balanced_accuracy"]
            if a["BA_defined"] and b["BA_defined"]
            else None
        )
        same(row["paired_difference"], expected, "session_paired_contrasts")
        same(row["paired_BA_defined"], expected is not None, "session_pair_eligibility")
        for field in ("n_left", "n_right"):
            same(row[field], a[field], "session_pair_class_counts")
    contrast_summary = checked_table(
        "cohort_paired_contrasts.csv", ["cohort", "contrast", "subset"]
    )
    consequential = []
    for (cohort, contrast, subset), row in contrast_summary.items():
        eligible = sorted(s for s in COHORTS[cohort] if pair(s, contrast, subset) is not None)
        values = [pair(s, contrast, subset) for s in eligible]
        same(row["eligible_subjects"], ";".join(eligible), "contrast_eligible_ids")
        same(row["n_eligible_participants"], len(eligible), "contrast_eligible_count")
        for field, expected in zip(["mean", "ci95_low", "ci95_high"], uncertainty(values)):
            same(row[field], expected, "contrast_bootstrap")
        for field, expected in [
            ("participants_positive", sum(v > 0 for v in values)),
            ("participants_zero", sum(v == 0 for v in values)),
            ("participants_negative", sum(v < 0 for v in values)),
        ]:
            same(row[field], expected, "contrast_sign_counts")
        consequential.append(
            {
                "cohort": cohort,
                "contrast": contrast,
                "subset": subset,
                "n": len(values),
                "independent_mean_and_CI": uncertainty(values),
            }
        )
    cross_summary = checked_table("paired_cross_subset_summary.csv", ["cohort", "contrast"])
    for (cohort, contrast), row in cross_summary.items():
        eligible = sorted(
            s
            for s in COHORTS[cohort]
            if all(pair(s, contrast, subset) is not None for subset in SUBSETS)
        )
        values = [
            pair(s, contrast, "unflagged") - pair(s, contrast, "all_included") for s in eligible
        ]
        same(row["eligible_subjects"], ";".join(eligible), "same_participants_across_subsets")
        same(row["n_eligible_participants"], len(eligible), "cross_subset_eligible_count")
        for field, expected in zip(["mean", "ci95_low", "ci95_high"], uncertainty(values)):
            same(row[field], expected, "cross_subset_paired_bootstrap")
    cross_rows = checked_table(
        "participant_cross_subset_changes.csv", ["cohort", "contrast", "subject"]
    )
    for (cohort, contrast, subject), row in cross_rows.items():
        require(subject in COHORTS[cohort], "cross_subset_cohort_identity")
        before, after = [pair(subject, contrast, subset) for subset in SUBSETS]
        valid = before is not None and after is not None
        for field, expected in [
            ("paired_across_subsets_defined", valid),
            ("all_included_difference", before),
            ("unflagged_difference", after),
            ("unflagged_minus_all_difference", after - before if valid else None),
        ]:
            same(row[field], expected, "participant_cross_subset_fields")
    loo_rows = csv_rows(BASE / "leave_one_participant_out_influence.csv")
    for row in loo_rows:
        cohort, contrast, subset, omitted = [
            row[f] for f in ("cohort", "contrast", "subset", "omitted_subject")
        ]
        eligible = sorted(s for s in COHORTS[cohort] if pair(s, contrast, subset) is not None)
        require(omitted in eligible, "loo_omits_existing_eligible_identity")
        values = [pair(s, contrast, subset) for s in eligible]
        leave = average([pair(s, contrast, subset) for s in eligible if s != omitted])
        for field, expected in [
            ("leave_one_out_mean", leave),
            ("full_eligible_mean", average(values)),
            ("n_retained", len(values) - 1),
            ("change_in_mean_when_omitted", leave - average(values)),
        ]:
            same(row[field], expected, "leave_one_participant_out_fields")
    role_counts = checked_table("all_role_qc_counts.csv", ["subject", "session", "role"])
    for (subject, session, role), row in role_counts.items():
        selected = [
            r
            for r in metadata
            if (r["subject"], r["session"], r["role"]) == (subject, session, role)
        ]
        kept = [r for r in selected if r["included"]]
        flagged = sum(r["qc_peak_to_peak_over_250uv"] for r in kept)
        for field, expected in [
            ("n_events", len(selected)),
            ("n_complete", len(kept)),
            ("n_incomplete", len(selected) - len(kept)),
            ("n_flagged_complete", flagged),
            ("n_unflagged_complete", len(kept) - flagged),
        ]:
            same(row[field], expected, "all_role_qc_counts")
    ledger = checked_table("query_identity_qc_ledger.csv", ["trial_id"])
    require(set(ledger) == {(i,) for i in events}, "query_ledger_complete_with_exclusions")
    for (identity,), row in ledger.items():
        for field in (
            "subject",
            "session",
            "cohort",
            "run",
            "role",
            "label",
            "included",
            "exclusion_reason",
            "qc_peak_to_peak_over_250uv",
            "raw_peak_to_peak_max_volts",
        ):
            same(row[field], events[identity][field], "query_ledger_identity_fields")
    require(
        read(BASE / "joined_saved_predictions_qc.csv") == read(PUBLIC / "saved_predictions.csv"),
        "published_prediction_bytes_equal_public_inputs",
    )
    for path, original in list(READS.items()):
        data = (ROOT / path).read_bytes()
        require(
            {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == original,
            "read_only_bytes_unchanged",
        )
    original_loo = [
        float(r["leave_one_out_mean"])
        for r in loo_rows
        if r["cohort"] == "remaining12"
        and r["subset"] == "all_included"
        and r["contrast"] == "refit_minus_frozen"
    ]
    unflagged_loo = [
        float(r["leave_one_out_mean"])
        for r in loo_rows
        if r["cohort"] == "remaining12"
        and r["subset"] == "unflagged"
        and r["contrast"] == "refit_minus_frozen"
    ]
    report = {
        "status": "passed",
        "started_utc": started,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "independent saved CSV/JSON arithmetic; no producer imports, model fitting, EEG arrays or inference",
        "numpy": np.__version__,
        "check_count": sum(CHECKS.values()),
        "checks_by_category": dict(CHECKS),
        "maximum_numeric_difference": MAX_NUMERICAL_ERROR,
        "absolute_numeric_tolerance": 1e-14,
        "fixed_bootstrap_draws": 10000,
        "fixed_bootstrap_seed": 42,
        "participant_order": "lexicographic",
        "original_queries": 4290,
        "unflagged_queries": 3368,
        "flagged_queries": 922,
        "joined_prediction_rows": 25740,
        "participant_method_seed_groups": 108,
        "unflagged_target_remaining_complete_cases": eligibility[
            "remaining12", "source_only", "unflagged"
        ],
        "excluded_from_unflagged_target_endpoint": ["sub-8", "sub-12"],
        "consequential_contrasts": consequential,
        "remaining12_original_primary_LOO_range": [min(original_loo), max(original_loo)],
        "remaining10_unflagged_primary_LOO_range": [min(unflagged_loo), max(unflagged_loo)],
        "all_read_bytes_unchanged": True,
        "no_critical_issue_found": True,
        "limitations": [
            "Conditioning queries on fixed amplitude QC changes sample composition; complete-case n10 differs from original n12.",
            "The cross-subset change is checked on the same eligible ten participants, not by subtracting n12 and n10 cohort means.",
            "Unflagged is not artifact-free; historical fitting and support data, including flagged examples, remain unchanged.",
            "One true example per class is mathematically sufficient for BA but unstable; low-count rows remain flagged and are not deleted.",
            "New post-observation descriptive analysis cannot establish a policy, validate continuous MI or become a new primary endpoint.",
        ],
        "failures": [],
    }
    with (OUT / "independent_validation.json").open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write("\n")
    with (OUT / "input_hashes.json").open("x") as f:
        json.dump(READS, f, indent=2)
        f.write("\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": sum(CHECKS.values()),
                "maximum_difference": MAX_NUMERICAL_ERROR,
                "remaining_original_LOO": report["remaining12_original_primary_LOO_range"],
            }
        )
    )


if __name__ == "__main__":
    main()
