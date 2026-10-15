"""Second implementation: saved compact data only; no imports of analysis entry."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CHECKS = 0
MAXIMUM_ERROR = 0.0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(message)


def equal_number(actual, expected, message):
    global MAXIMUM_ERROR
    if expected is None:
        check(actual == "", message)
    else:
        error = abs(float(actual) - float(expected))
        MAXIMUM_ERROR = max(MAXIMUM_ERROR, error)
        check(error < 2e-15, message)


def table(filename):
    with (HERE / filename).open() as handle:
        return list(csv.DictReader(handle))


def main():
    metadata = json.loads((HERE / "public_inputs/frozen_trial_metadata.json").read_text())["trials"]
    identity = {row["trial_id"]: row for row in metadata}
    check(len(identity) == len(metadata) == 7200, "Unique complete frozen metadata")
    predictions = table("public_inputs/saved_predictions.csv")
    group = defaultdict(list)
    for row in predictions:
        key = (row["subject"], row["method"], row["seed"])
        group[key].append(row)
        expected = identity[row["trial_id"]]
        check(expected["included"] is True, "Scored incomplete identity")
        check(int(row["label"]) == (expected["label"] == "right_hand"), "Stored label mismatch")
        check(
            row["qc_peak_to_peak_over_250uv"] == str(expected["qc_peak_to_peak_over_250uv"]),
            "QC join mismatch",
        )
    for key, rows in group.items():
        expected_ids = {
            r["trial_id"]
            for r in metadata
            if r["subject"] == key[0]
            and r["included"]
            and r["role"] in ("source_query", "target_query")
        }
        check(
            len(rows) == len({r["trial_id"] for r in rows}) == len(expected_ids),
            "Complete unique query set",
        )
        check({r["trial_id"] for r in rows} == expected_ids, "Exact identity coverage")
    measured = {}
    for row in table("per_seed_session_and_pooled_metrics.csv"):
        rows = group[(row["subject"], row["method"], row["seed"])]
        selected = [
            r
            for r in rows
            if row["subset"] == "all_included" or r["qc_peak_to_peak_over_250uv"] == "False"
        ]
        if row["session"] == "pooled_target_queries":
            selected = [r for r in selected if r["session"] != "ses-0"]
        elif row["session"] != "pooled_all_queries":
            selected = [r for r in selected if r["session"] == row["session"]]
        cells = Counter((int(r["label"]), int(r["prediction"])) for r in selected)
        n_left = cells[(0, 0)] + cells[(0, 1)]
        n_right = cells[(1, 0)] + cells[(1, 1)]
        ba = (
            ((cells[(0, 0)] / n_left + cells[(1, 1)] / n_right) / 2) if n_left and n_right else None
        )
        for y in (0, 1):
            for predicted in (0, 1):
                check(
                    int(row[f"confusion_{y}{predicted}"]) == cells[(y, predicted)],
                    "Confusion arithmetic",
                )
        check(int(row["n_left"]) == n_left and int(row["n_right"]) == n_right, "Class counts")
        equal_number(row["balanced_accuracy"], ba, "Seed-group BA")
        measured[(row["subject"], row["method"], row["subset"], row["session"], row["seed"])] = ba
    seed_averaged = {}
    for row in table("per_participant_session_metrics.csv"):
        key = (row["subject"], row["method"], row["subset"], row["session"])
        values = [v for k, v in measured.items() if k[:4] == key]
        check(
            len(values) == (3 if row["method"] == "always_frozen_eegnet" else 1),
            "Every seed retained",
        )
        average = sum(values) / len(values) if all(v is not None for v in values) else None
        equal_number(row["balanced_accuracy"], average, "Seed averaging")
        seed_averaged[key] = average
    endpoints = table("participant_endpoints.csv")
    for row in endpoints:
        values = [
            seed_averaged[(row["subject"], row["method"], row["subset"], f"ses-{s}")]
            for s in range(1, 6)
        ]
        average = sum(values) / 5 if all(v is not None for v in values) else None
        equal_number(row["target_five_session_mean_BA"], average, "Equal five-session endpoint")
        check(
            int(row["n_defined_target_sessions"]) == sum(v is not None for v in values),
            "Undefined session count",
        )
    for summary in table("cohort_method_sensitivity_summary.csv"):
        ids = summary["eligible_subjects"].split(";") if summary["eligible_subjects"] else []
        selected = sorted(
            [
                r
                for r in endpoints
                if r["subject"] in ids
                and r["method"] == summary["method"]
                and r["subset"] == summary["subset"]
            ],
            key=lambda r: r["subject"],
        )
        check(len(selected) == int(summary["n_eligible_participants"]), "Summary denominator")
        values = [float(r[summary["endpoint"]]) for r in selected]
        equal_number(
            summary["mean"], sum(values) / len(values) if values else None, "Participant average"
        )
        if len(values) > 1:
            rng = np.random.default_rng(42)
            samples = rng.choice(np.asarray(values), size=(10000, len(values)), replace=True)
            means = np.add.reduce(samples, axis=1) / len(values)
            interval = np.percentile(means, [2.5, 97.5])
            equal_number(summary["ci95_low"], interval[0], "Bootstrap low")
            equal_number(summary["ci95_high"], interval[1], "Bootstrap high")
    participant_contrasts = table("paired_participant_contrasts.csv")
    endpoint_map = {(r["subject"], r["method"], r["subset"]): r for r in endpoints}
    for row in participant_contrasts:
        negative = (
            "source_only"
            if row["contrast"] == "refit_minus_frozen"
            else "frozen_csp_lda_recalibration"
        )
        a = endpoint_map[(row["subject"], "refit_csp_lda", row["subset"])][
            "target_five_session_mean_BA"
        ]
        b = endpoint_map[(row["subject"], negative, row["subset"])]["target_five_session_mean_BA"]
        equal_number(
            row["mean_difference"], float(a) - float(b) if a and b else None, "Participant contrast"
        )
    for summary in table("cohort_paired_contrasts.csv"):
        ids = summary["eligible_subjects"].split(";")
        values = [
            float(r["mean_difference"])
            for r in sorted(participant_contrasts, key=lambda r: r["subject"])
            if r["subject"] in ids
            and r["subset"] == summary["subset"]
            and r["contrast"] == summary["contrast"]
        ]
        equal_number(summary["mean"], sum(values) / len(values), "Contrast mean")
        samples = np.random.default_rng(42).choice(
            np.asarray(values), size=(10000, len(values)), replace=True
        )
        interval = np.percentile(np.add.reduce(samples, axis=1) / len(values), [2.5, 97.5])
        equal_number(summary["ci95_low"], interval[0], "Contrast bootstrap low")
        equal_number(summary["ci95_high"], interval[1], "Contrast bootstrap high")
    output = {
        "status": "passed",
        "implementation": "independent Counter and direct sum arithmetic; no import of original entry",
        "checks": CHECKS,
        "maximum_absolute_difference": MAXIMUM_ERROR,
        "raw_EEG_or_weights_read": False,
        "new_fits": 0,
        "new_forwards": 0,
        "failures": [],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with (HERE / "independent_public_arithmetic_validation.json").open("x") as handle:
        json.dump(output, handle, indent=2)
        handle.write("\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
