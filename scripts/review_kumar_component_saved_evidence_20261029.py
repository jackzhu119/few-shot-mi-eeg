"""Independently replay saved Kumar budget/phase evidence; no EEG/models/forward.

CSV or gzip-compressed CSV inputs are accepted. Existing participant-bootstrap
intervals are reconstructed using their own frozen order and seed; no new test
family or parameter selection is introduced.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path("/workspace/private_model_receipts/paper2-component-followup-20261016")
SUBJECTS = tuple(f"sub-{i}" for i in range(1, 19))
DEVELOPMENT = tuple(f"sub-{i}" for i in (1, 4, 7, 10, 13, 16))
PRIMARY = tuple(s for s in SUBJECTS if s not in DEVELOPMENT)
COHORTS = {"development6": DEVELOPMENT, "remaining12": PRIMARY, "all18_descriptive": SUBJECTS}
BUDGETS = ("4", "8", "12", "16", "full")
METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda", "ea_csp_lda")
CONTRASTS = (
    ("lda_minus_frozen", METHODS[1], METHODS[0]),
    ("full_minus_frozen", METHODS[2], METHODS[0]),
    ("ea_minus_frozen", METHODS[3], METHODS[0]),
    ("full_minus_lda", METHODS[2], METHODS[1]),
    ("ea_minus_full", METHODS[3], METHODS[2]),
)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def bytes_input(path):
    path = Path(path)
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()


def locate(directory, filename):
    for path in (directory / filename, directory / (filename + ".gz")):
        if path.is_file():
            return path
    raise FileNotFoundError(f"Missing saved input {directory}/{filename}[.gz]")


def read_csv(path):
    return list(csv.DictReader(io.StringIO(bytes_input(path).decode("utf-8"), newline="")))


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def write_csv(path, rows):
    check(bool(rows), f"Empty output: {path}")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ids_hash(ids):
    return digest(json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode())


def score(group):
    truth = [int(r["label"]) for r in group]
    prediction = [int(r["prediction"]) for r in group]
    check(set(truth) <= {0, 1} and set(prediction) <= {0, 1}, "Nonbinary saved outcome")
    counts = Counter(truth)
    correct = Counter(y for y, p in zip(truth, prediction) if y == p)
    value = (
        None
        if counts[0] == 0 or counts[1] == 0
        else (Fraction(correct[0], counts[0]) + Fraction(correct[1], counts[1])) / 2
    )
    return value, counts, Counter(prediction)


def ci(values):
    # The old budget postprocessor converts exact Fraction participant endpoints
    # to float64 here, then creates a fresh seed42 generator for EACH contrast.
    data = np.asarray([float(x) for x in values], dtype=np.float64)
    draws = np.random.default_rng(42).integers(0, len(data), size=(10000, len(data)))
    low, high = np.quantile(data[draws].mean(axis=1), [0.025, 0.975], method="linear")
    return float(data.mean()), float(low), float(high)


def budget_replay(metrics, predictions, frozen, saved_root):
    groups = defaultdict(list)
    seen = set()
    for row in predictions:
        key = tuple(row[k] for k in ("subject", "session", "budget", "method"))
        identity = key + (row["trial_id"],)
        check(
            identity not in seen and row["synthetic"] == "False", "Duplicate/synthetic prediction"
        )
        seen.add(identity)
        original = frozen[row["trial_id"]]
        check(
            original["subject"] == row["subject"]
            and original["session"] == row["session"]
            and original["role"] == "target_query"
            and original["included"]
            and original["run"] == row["run"],
            "Forbidden budget trial role",
        )
        check(
            int(row["label"]) == (0 if original["label"] == "left_hand" else 1),
            "Budget truth mismatch",
        )
        groups[key].append(row)
    expected = {
        (s, f"ses-{t}", b, m)
        for s in SUBJECTS
        for t in range(1, 6)
        for b in BUDGETS
        for m in METHODS
    }
    check(len(metrics) == len(expected) and set(groups) == expected, "Budget grid incomplete")
    exact, session_rows, identity = {}, [], {}
    max_error = 0.0
    for row in metrics:
        key = tuple(row[k] for k in ("subject", "session", "budget", "method"))
        check(key in expected and key not in exact, "Duplicate metric cell")
        group = groups[key]
        ids = [r["trial_id"] for r in group]
        truth = [(r["trial_id"], r["label"], r["run"]) for r in group]
        ss = key[:2]
        check(ss not in identity or identity[ss] == truth, "Budget/method query labels/IDs differ")
        identity[ss] = truth
        check(
            len(set(ids)) == len(ids) == int(row["n_query"])
            and ids_hash(ids) == row["query_trial_ids_sha256"],
            "Query identity/count mismatch",
        )
        value, counts, pred_counts = score(group)
        check(value is not None, "Budget query unexpectedly lacks a class")
        error = abs(float(value) - float(row["balanced_accuracy"]))
        max_error = max(max_error, error)
        check(error <= 5e-15, "Saved BA differs from exact confusion arithmetic")
        check(
            (pred_counts[0], pred_counts[1])
            == (int(row["prediction_left"]), int(row["prediction_right"])),
            "Prediction class counts changed",
        )
        check(
            (min(pred_counts[0], pred_counts[1]) == 0)
            == (row["prediction_class_collapse"] == "True"),
            "Collapse status mismatch",
        )
        check(
            int(row["support_left"]) + int(row["support_right"]) == int(row["k"]),
            "Support label count mismatch",
        )
        exact[key] = value
        session_rows.append(
            {k: row[k] for k in ("subject", "cohort", "session", "budget", "k", "method")}
            | {
                "n_query": len(group),
                "query_left": counts[0],
                "query_right": counts[1],
                "prediction_left": pred_counts[0],
                "prediction_right": pred_counts[1],
                "balanced_accuracy": float(value),
                "saved_balanced_accuracy": float(row["balanced_accuracy"]),
                "absolute_error": error,
                "BA_exact_fraction": str(value),
                "query_ID_SHA256": ids_hash(ids),
            }
        )
    endpoints, lookup = [], {}
    for subject in SUBJECTS:
        for budget in BUDGETS:
            for method in METHODS:
                value = sum(exact[subject, f"ses-{t}", budget, method] for t in range(1, 6)) / 5
                lookup[subject, budget, method] = value
                endpoints.append(
                    {
                        "subject": subject,
                        "cohort": "development6" if subject in DEVELOPMENT else "remaining12",
                        "budget": budget,
                        "method": method,
                        "five_session_mean_BA": float(value),
                        "BA_percent": 100 * float(value),
                        "n_defined_sessions": 5,
                    }
                )
    cohorts, comparisons = [], []
    for cohort, members in COHORTS.items():
        for budget in BUDGETS:
            for method in METHODS:
                mean, low, high = ci([lookup[s, budget, method] for s in members])
                cohorts.append(
                    {
                        "cohort": cohort,
                        "budget": budget,
                        "method": method,
                        "n_participants": len(members),
                        "mean_BA": mean,
                        "CI95_low_BA": low,
                        "CI95_high_BA": high,
                        "mean_percent": mean * 100,
                        "CI95_low_percent": low * 100,
                        "CI95_high_percent": high * 100,
                    }
                )
            for contrast, left, right in CONTRASTS:
                values = [lookup[s, budget, left] - lookup[s, budget, right] for s in members]
                mean, low, high = ci(values)
                comparisons.append(
                    {
                        "cohort": cohort,
                        "budget": budget,
                        "contrast": contrast,
                        "n_participants": len(members),
                        "mean_gain_pp": mean * 100,
                        "CI95_low_pp": low * 100,
                        "CI95_high_pp": high * 100,
                        "n_positive": sum(v > 0 for v in values),
                        "n_equal": sum(v == 0 for v in values),
                        "n_negative": sum(v < 0 for v in values),
                    }
                )
    saved_means = {
        (r["cohort"], r["budget"], r["method"]): r
        for r in read_csv(saved_root / "budget_cohort_means.csv")
    }
    saved_pairs = {
        (r["cohort"], r["budget"], r["contrast"]): r
        for r in read_csv(saved_root / "budget_cohort_paired_gains.csv")
    }
    maximum = 0.0
    for row in cohorts:
        old = saved_means[row["cohort"], row["budget"], row["method"]]
        for field in ("mean_BA", "CI95_low_BA", "CI95_high_BA"):
            error = abs(row[field] - float(old[field]))
            maximum = max(maximum, error)
            check(error <= 5e-15, "Existing budget mean/CI not reproduced")
    for row in comparisons:
        old = saved_pairs[row["cohort"], row["budget"], row["contrast"]]
        for field in ("mean_gain_pp", "CI95_low_pp", "CI95_high_pp"):
            error = abs(row[field] - float(old[field]))
            maximum = max(maximum, error)
            check(error <= 5e-12, "Existing budget paired CI not reproduced")
    participant_effects = []
    for subject in SUBJECTS:
        vals = {m: lookup[subject, "full", m] for m in METHODS}
        participant_effects.append(
            {
                "subject": subject,
                "cohort": "development6" if subject in DEVELOPMENT else "remaining12",
                **{m + "_BA": float(v) for m, v in vals.items()},
                "full_minus_lda_pp": float(vals[METHODS[2]] - vals[METHODS[1]]) * 100,
                "ea_minus_full_pp": float(vals[METHODS[3]] - vals[METHODS[2]]) * 100,
            }
        )
    session_effects = []
    for subject in SUBJECTS:
        for t in range(1, 6):
            session = f"ses-{t}"
            vals = {m: exact[subject, session, "full", m] for m in METHODS}
            session_effects.append(
                {
                    "subject": subject,
                    "cohort": "development6" if subject in DEVELOPMENT else "remaining12",
                    "session": session,
                    **{m + "_BA": float(v) for m, v in vals.items()},
                    "full_minus_lda_pp": float(vals[METHODS[2]] - vals[METHODS[1]]) * 100,
                    "ea_minus_full_pp": float(vals[METHODS[3]] - vals[METHODS[2]]) * 100,
                }
            )
    return {
        "budget_session_metrics_replayed.csv": session_rows,
        "budget_participant_endpoints.csv": endpoints,
        "budget_cohort_means.csv": cohorts,
        "budget_cohort_paired_gains.csv": comparisons,
        "remaining12_budget_curves.csv": [r for r in cohorts if r["cohort"] == "remaining12"],
        "full_support_participant_effects.csv": participant_effects,
        "full_support_session_effects.csv": session_effects,
        "remaining12_full_support_session_effects.csv": [
            r for r in session_effects if r["cohort"] == "remaining12"
        ],
    }, {
        "metric_cells": len(exact),
        "saved_prediction_rows": len(predictions),
        "unique_target_trials": len({r["trial_id"] for r in predictions}),
        "participant_endpoints": len(endpoints),
        "existing_cohort_mean_rows_reproduced": len(cohorts),
        "existing_paired_contrast_rows_reproduced": len(comparisons),
        "maximum_BA_error": max_error,
        "maximum_saved_summary_or_CI_error": maximum,
        "participant_order": {k: list(v) for k, v in COHORTS.items()},
        "bootstrap_seed": 42,
        "bootstrap_replicates": 10000,
        "scope": "existing_post_exposure_pointwise_results_reproduced_no_new_tests",
    }


def phase_replay(metrics, predictions, frozen, saved_root):
    methods = METHODS[:3]
    windows = ("cue5s", "task2s")
    groups = defaultdict(list)
    seen = set()
    for r in predictions:
        key = tuple(r[k] for k in ("subject", "session", "window", "method"))
        unique = key + (r["trial_id"],)
        check(
            unique not in seen and r["synthetic"] == "False", "Duplicate/synthetic phase prediction"
        )
        seen.add(unique)
        original = frozen[r["trial_id"]]
        check(
            original["role"] == "target_query"
            and original["included"]
            and original["subject"] == r["subject"]
            and original["session"] == r["session"]
            and int(r["label"]) == (0 if original["label"] == "left_hand" else 1),
            "Phase trial identity/label mismatch",
        )
        groups[key].append(r)
    expected = {
        (s, f"ses-{t}", w, m)
        for s in SUBJECTS
        for t in range(1, 6)
        for w in windows
        for m in methods
    }
    check(len(metrics) == 540, "Phase grid must retain all 540 cells")
    parsed, observed, shared = [], set(), {}
    maximum = 0.0
    for raw in metrics:
        key = tuple(raw[k] for k in ("subject", "session", "window", "method"))
        check(key in expected and key not in observed, "Duplicate/unfrozen phase cell")
        observed.add(key)
        ids = json.loads(raw["query_trial_ids"])
        fit = json.loads(raw["fit_trial_ids"])
        check(
            ids_hash(ids) == raw["query_ids_sha256"]
            and len(ids) == len(set(ids)) == int(raw["n_common_query"]),
            "Phase query IDs/hash mismatch",
        )
        check(
            ids_hash(fit) == raw["fit_ids_sha256"] and not set(ids).intersection(fit),
            "Phase fit/query overlap",
        )
        signature = (raw["query_ids_sha256"], raw["common_support_ids_sha256"])
        check(
            key[:2] not in shared or shared[key[:2]] == signature,
            "Phase actions/windows do not share query/support",
        )
        shared[key[:2]] = signature
        group = groups.get(key, [])
        value = None
        if raw["balanced_accuracy"] in ("", None):
            check(
                not group and raw["status"].startswith("undefined"),
                "Undefined phase cell silently scored",
            )
        else:
            check(
                [r["trial_id"] for r in group] == ids,
                "Phase prediction order differs from identities",
            )
            _, counts, _ = score(group)
            check(
                (counts[0], counts[1]) == (int(raw["n_query_left"]), int(raw["n_query_right"])),
                "Phase class counts differ",
            )
            y = np.array([int(r["label"]) for r in group])
            pred = np.array([int(r["prediction"]) for r in group])
            check(set(y.tolist()) == {0, 1}, "Defined phase cell lacks a true class")
            value = float(np.mean([np.mean(pred[y == c] == c) for c in (0, 1)]))
            err = abs(value - float(raw["balanced_accuracy"]))
            maximum = max(maximum, err)
            check(err <= 1e-12, "Phase BA differs")
            check(
                raw["model_parameter_sha256_before"] == raw["model_parameter_sha256_after"],
                "Phase model state changed during recorded evaluation",
            )
        parsed.append(
            {k: raw[k] for k in ("subject", "cohort", "session", "window", "method", "status")}
            | {
                "balanced_accuracy": value,
                "n_query": int(raw["n_common_query"]),
                "query_left": int(raw["n_query_left"]),
                "query_right": int(raw["n_query_right"]),
                "n_unknown_query_phase": int(raw["n_unknown_query_phase"]),
            }
        )
    check(observed == expected and not (set(groups) - expected), "Phase coverage mismatch")
    endpoints, lookup = [], {}
    for subject in sorted(SUBJECTS):
        for window in windows:
            for method in methods:
                cells = [
                    r
                    for r in parsed
                    if (r["subject"], r["window"], r["method"]) == (subject, window, method)
                ]
                complete = all(r["balanced_accuracy"] is not None for r in cells)
                value = (
                    float(np.mean([r["balanced_accuracy"] for r in cells])) if complete else None
                )
                lookup[subject, window, method] = value
                endpoints.append(
                    {
                        "subject": subject,
                        "cohort": cells[0]["cohort"],
                        "window": window,
                        "method": method,
                        "n_defined_sessions": sum(
                            r["balanced_accuracy"] is not None for r in cells
                        ),
                        "balanced_accuracy": value,
                        "query_mapping_complete_all_sessions": all(
                            r["n_unknown_query_phase"] == 0 for r in cells
                        ),
                    }
                )
    scopes = {}
    for name, cohort, metadata in [
        ("development_conditional", "development", False),
        ("primary_conditional", "final_test", False),
        ("primary_metadata_complete", "final_test", True),
    ]:
        members = []
        for subject in sorted({r["subject"] for r in endpoints if r["cohort"] == cohort}):
            selected = [r for r in endpoints if r["subject"] == subject]
            if all(r["balanced_accuracy"] is not None for r in selected) and (
                not metadata or all(r["query_mapping_complete_all_sessions"] for r in selected)
            ):
                members.append(subject)
        scopes[name] = members
    contrasts = []

    def contrast(scope, window, name, values):
        mean, low, high = ci(values)
        contrasts.append(
            {
                "scope": scope,
                "window": window,
                "contrast": name,
                "n_participants": len(values),
                "participants": json.dumps(scopes[scope], separators=(",", ":")),
                "mean_difference_ba": mean,
                "ci_low_ba": low,
                "ci_high_ba": high,
            }
        )

    for scope, members in scopes.items():
        for window in windows:
            for left, right in [
                (methods[2], methods[0]),
                (methods[2], methods[1]),
                (methods[1], methods[0]),
            ]:
                contrast(
                    scope,
                    window,
                    left + "-" + right,
                    [lookup[s, window, left] - lookup[s, window, right] for s in members],
                )
        for method in methods:
            contrast(
                scope,
                "paired_task2s_minus_cue5s",
                method,
                [lookup[s, "task2s", method] - lookup[s, "cue5s", method] for s in members],
            )
        for right in methods[:2]:
            contrast(
                scope,
                "paired_gain_change_task2s_minus_cue5s",
                methods[2] + "-" + right,
                [
                    (lookup[s, "task2s", methods[2]] - lookup[s, "task2s", right])
                    - (lookup[s, "cue5s", methods[2]] - lookup[s, "cue5s", right])
                    for s in members
                ],
            )
    saved = {
        (r["scope"], r["window"], r["contrast"]): r
        for r in read_csv(saved_root / "phase_cohort_paired_contrasts.csv")
    }
    ci_error = 0.0
    for r in contrasts:
        old = saved[r["scope"], r["window"], r["contrast"]]
        check(
            json.loads(r["participants"]) == json.loads(old["participants"]),
            "Phase cohort membership/order changed",
        )
        for field in ("mean_difference_ba", "ci_low_ba", "ci_high_ba"):
            err = abs(r[field] - float(old[field]))
            ci_error = max(ci_error, err)
            check(err <= 1e-12, "Existing phase contrast/CI not reproduced")
    return {
        "phase_session_metrics_replayed.csv": parsed,
        "phase_participant_endpoints.csv": endpoints,
        "phase_existing_contrasts_reproduced.csv": contrasts,
    }, {
        "planned_cells": len(parsed),
        "defined_cells": sum(r["balanced_accuracy"] is not None for r in parsed),
        "undefined_cells_retained": sum(r["balanced_accuracy"] is None for r in parsed),
        "saved_prediction_rows": len(predictions),
        "maximum_BA_error": maximum,
        "maximum_existing_contrast_CI_error": ci_error,
        "scopes": scopes,
        "existing_contrasts_reproduced": len(contrasts),
        "participant_order": "lexicographic per old phase postprocessor",
        "bootstrap_seed": 42,
        "bootstrap_replicates": 10000,
        "new_test_family": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-root", type=Path, default=PRIVATE / "budget_cpu/run01")
    parser.add_argument("--phase-root", type=Path, default=PRIVATE / "phase_cpu/run01")
    parser.add_argument(
        "--saved-tables",
        type=Path,
        default=ROOT / "research_logs/paper2_hpc_v2_20261023/existing_evidence",
    )
    parser.add_argument(
        "--trial-manifest",
        type=Path,
        default=ROOT / "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = [
        locate(args.budget_root, "session_metrics.csv"),
        locate(args.budget_root, "query_predictions.csv"),
        locate(args.phase_root, "metrics.csv"),
        locate(args.phase_root, "query_predictions.csv"),
        args.trial_manifest,
        args.saved_tables / "budget_cohort_means.csv",
        args.saved_tables / "budget_cohort_paired_gains.csv",
        args.saved_tables / "phase_cohort_paired_contrasts.csv",
    ]
    before = {
        str(p): {
            "stored_bytes": p.stat().st_size,
            "stored_sha256": digest(p.read_bytes()),
            "uncompressed_bytes": len(bytes_input(p)),
            "uncompressed_sha256": digest(bytes_input(p)),
        }
        for p in inputs
    }
    frozen = {r["trial_id"]: r for r in json.loads(bytes_input(args.trial_manifest))["trials"]}
    budget_tables, budget = budget_replay(
        read_csv(inputs[0]), read_csv(inputs[1]), frozen, args.saved_tables
    )
    phase_tables, phase = phase_replay(
        read_csv(inputs[2]), read_csv(inputs[3]), frozen, args.saved_tables
    )
    check(
        all(digest(p.read_bytes()) == before[str(p)]["stored_sha256"] for p in inputs),
        "A source file changed during replay",
    )
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in (budget_tables | phase_tables).items():
        write_csv(args.output / name, rows)
    report = {
        "scope": "independent saved-derived-results replay; no EEG/model imports, fit or forward",
        "budget": budget,
        "phase": phase,
        "source_inputs": before,
        "new_significance_test_or_family": False,
        "historical_primary_intervals_or_Holm_results_modified": False,
        "original_files_changed": False,
        "software": {"python": sys.version, "numpy": np.__version__},
    }
    write_json(args.output / "REPLAY_REPORT.json", report)
    print(
        json.dumps(
            {
                "budget_cells": budget["metric_cells"],
                "budget_predictions": budget["saved_prediction_rows"],
                "phase_cells": phase["planned_cells"],
                "phase_defined": phase["defined_cells"],
                "phase_undefined": phase["undefined_cells_retained"],
                "phase_predictions": phase["saved_prediction_rows"],
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
