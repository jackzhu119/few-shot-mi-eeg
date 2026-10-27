#!/usr/bin/env python3
"""Recompute the frozen V3 geometry comparisons from saved predictions only.

No EEG, Torch checkpoint, estimator, optimizer or inference entry is imported.
The six exposed development participants remain the independent units. Proper
scores are additional descriptive checks; they do not replace the frozen BA
primary comparison. Output paths must be separate from the immutable input tree.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

import numpy as np


BUDGETS = (4, 8, 12, 16, 20)
SESSIONS = tuple(f"ses-{s}" for s in range(1, 6))
BOOTSTRAP_SEED = 20261023
BOOTSTRAP_REPETITIONS = 10000
CE_PROBABILITY_FLOOR = 1e-15


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    if not rows:
        raise ValueError("Refusing to write a table without declared fields")
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def interval(values):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or len(values) != 6 or not np.isfinite(values).all():
        raise ValueError("The frozen comparison requires all six participants")
    # Lexicographic participant ordering reproduces the frozen summarizer's
    # finite Monte Carlo sample, not merely the same bootstrap distribution.
    indices = np.random.default_rng(BOOTSTRAP_SEED).integers(
        0, len(values), (BOOTSTRAP_REPETITIONS, len(values))
    )
    return np.quantile(values[indices].mean(axis=1), [0.025, 0.975]).tolist()


def effect(left, right, subjects):
    differences = 100 * (np.asarray(left) - np.asarray(right))
    lower, upper = interval(differences)
    return {
        "mean_pp": float(differences.mean()),
        "ci95_pp": [lower, upper],
        "participant_differences_pp": dict(zip(subjects, differences.tolist())),
        "positive": int((differences > 0).sum()),
        "negative": int((differences < 0).sum()),
        "decline_ge5pp": int((differences <= -5).sum()),
        "leave_one_participant_out_mean_pp": {
            participant: float(np.delete(differences, i).mean())
            for i, participant in enumerate(subjects)
        },
    }


def prediction_metrics(root):
    rows, diagnostics, identities = [], [], {}
    maximum_ba_error = 0.0
    for task in sorted((root / "tasks").glob("v3-geometry-*")):
        for path in sorted((task / "evaluation").glob("*/metrics.json")):
            saved = json.loads(path.read_text())
            if saved["requested_budget"] == 0:
                continue  # The target primary does not pool source-query trials.
            if saved.get("query_used_for_fitting") or saved.get("selection_use"):
                raise ValueError(f"Saved record reports query fitting/selection: {path}")
            with np.load(path.with_name("predictions.npz"), allow_pickle=False) as data:
                labels = data["labels"]
                probabilities = data["probabilities"]
                classes = data["classes"].tolist()
                trial_ids = data["trial_id"].tolist()
                if (
                    classes != [0, 1]
                    or labels.ndim != 1
                    or probabilities.shape != (len(labels), 2)
                    or len(trial_ids) != len(set(trial_ids))
                    or len(labels) != saved["n_query"]
                    or set(labels.tolist()) != {0, 1}
                    or not np.isfinite(probabilities).all()
                    or np.any(probabilities < 0)
                    or not np.allclose(probabilities.sum(axis=1), 1)
                ):
                    raise ValueError(f"Invalid saved prediction arrays: {path}")
                predicted = np.asarray(classes)[probabilities.argmax(axis=1)]
                ba = float(
                    np.mean([np.mean(predicted[labels == c] == c) for c in classes])
                )
                maximum_ba_error = max(
                    maximum_ba_error, abs(ba - saved["balanced_accuracy"])
                )
                key = (saved["participant"], saved["session"])
                value = (trial_ids, labels.tolist())
                if identities.setdefault(key, value) != value:
                    raise ValueError(f"Ordered query IDs/labels differ: {path}")
                rows.append(
                    {
                        "participant": saved["participant"],
                        "session": saved["session"],
                        "method": saved["method"],
                        "budget": saved["requested_budget"],
                        "ba": ba,
                        "ce_clipped_1e15": float(
                            -np.log(
                                np.clip(
                                    probabilities[np.arange(len(labels)), labels],
                                    CE_PROBABILITY_FLOOR,
                                    1,
                                )
                            ).mean()
                        ),
                        "brier_positive_class": float(
                            np.mean((probabilities[:, 1] - labels) ** 2)
                        ),
                        "collapse": len(set(predicted.tolist())) == 1,
                        "exact_probability_zeros": int((probabilities == 0).sum()),
                        "exact_probability_ones": int((probabilities == 1).sum()),
                    }
                )
        for path in sorted((task / "model_diagnostics").glob("*__eb_predictive.json")):
            saved = json.loads(path.read_text())
            session, budget, _ = path.stem.split("__")
            if saved.get("query_used_for_fitting"):
                raise ValueError(f"Saved diagnostic reports query fitting: {path}")
            diagnostics.append(
                {
                    "participant": task.name.removeprefix("v3-geometry-"),
                    "session": session,
                    "budget": int(budget[1:]),
                    "support_class_counts": saved["support_class_counts"],
                    "tau_common_squared": saved["tau_common_squared"],
                    "tau_halfcontrast_squared": saved["tau_halfcontrast_squared"],
                    "posterior_trace": saved["posterior_trace"],
                    "source_noise_trace": saved["source_mean_noise"]["trace"],
                    "target_noise_trace": saved["target_observation_noise"]["trace"],
                    "fallback": saved.get("fallback", []),
                }
            )
    keys = {(r["participant"], r["session"], r["method"], r["budget"]) for r in rows}
    if len(rows) != 1350 or len(keys) != 1350 or maximum_ba_error > 1e-12:
        raise ValueError("The1,350 frozen target cells are incomplete, duplicate or disagree")
    if len(diagnostics) != 150:
        raise ValueError("The150 predictive-method diagnostics are incomplete")
    return rows, diagnostics, maximum_ba_error


def analyze(results_root, output_root):
    root, output = Path(results_root).resolve(), Path(output_root).resolve()
    if output == root or output.is_relative_to(root):
        raise ValueError("Keep analysis outputs outside the immutable result-input tree")
    participants = read_csv(root / "analysis/participant_metrics.csv")
    cells = read_csv(root / "analysis/saved_cells.csv")
    cohorts = read_csv(root / "analysis/cohorts.csv")
    geometry_cells = [r for r in cells if r["family"] == "geometry"]
    if len(geometry_cells) != 1500:
        raise ValueError("Expected1,350 geometry cells plus150 saved EA reference cells")
    subjects = sorted({r["participant"] for r in geometry_cells})
    methods = sorted({r["method"] for r in geometry_cells})
    if len(subjects) != 6 or len(methods) != 10:
        raise ValueError("Frozen geometry participants/methods differ")
    metrics, diagnostics, maximum_ba_error = prediction_metrics(root)

    def participant_scores(method, budget, metric="ba"):
        result = []
        for participant in subjects:
            selected = [
                r for r in metrics
                if r["participant"] == participant
                and r["method"] == method and r["budget"] == budget
            ]
            if {r["session"] for r in selected} != set(SESSIONS) or len(selected) != 5:
                raise ValueError("Incomplete participant/session endpoint")
            result.append(float(np.mean([r[metric] for r in selected])))
        return result

    def frozen_participant_scores(method, budget):
        result = []
        for participant in subjects:
            selected = [
                r for r in participants
                if r["family"] == "geometry" and r["participant"] == participant
                and r["method"] == method and int(r["budget"]) == budget
            ]
            if len(selected) != 1 or selected[0]["missing_sessions"]:
                raise ValueError("Frozen participant summary is duplicate/incomplete")
            result.append(float(selected[0]["balanced_accuracy"]))
        if method != "saved_V2_ea_csp" and not np.allclose(
            result, participant_scores(method, budget), rtol=0, atol=1e-12
        ):
            raise ValueError("Independent prediction BA differs from participant summary")
        return result

    summary = {}
    for method in methods:
        summary[method] = {}
        for budget in BUDGETS:
            selected = [
                r for r in cohorts if r["family"] == "geometry"
                and r["method"] == method and int(r["budget"]) == budget
            ]
            if len(selected) != 1 or selected[0]["endpoint_complete"] != "True":
                raise ValueError("Frozen cohort summary is duplicate/incomplete")
            mean = float(selected[0]["mean_balanced_accuracy"])
            if abs(mean - np.mean(frozen_participant_scores(method, budget))) > 1e-12:
                raise ValueError("Cohort BA differs from participant endpoint mean")
            summary[method][str(budget)] = mean * 100

    comparisons, comparison_rows = {}, []
    for budget in BUDGETS:
        for reference in methods:
            if reference == "eb_predictive":
                continue
            value = effect(
                frozen_participant_scores("eb_predictive", budget),
                frozen_participant_scores(reference, budget), subjects,
            )
            comparisons[f"eb_predictive-minus-{reference}-n{budget}"] = value
            role = (
                "prespecified_geometry_primary"
                if budget == 20 and reference == "tangent_refit"
                else "prespecified_strong_reference"
                if budget == 20 and reference == "saved_V2_ea_csp"
                else "descriptive_geometry_ablation"
                if budget == 20
                else "descriptive_budget_curve"
            )
            comparison_rows.append(
                {
                    "method": "eb_predictive", "reference": reference,
                    "budget": budget, "contrast_role": role,
                    "participants": len(subjects), "mean_difference_pp": value["mean_pp"],
                    "ci_low_pp": value["ci95_pp"][0], "ci_high_pp": value["ci95_pp"][1],
                    "positive_participants": value["positive"],
                    "negative_participants": value["negative"],
                    "decline_at_least_5pp": value["decline_ge5pp"],
                    "participant_differences_pp_json": json.dumps(value["participant_differences_pp"]),
                    "leave_one_participant_out_mean_pp_json": json.dumps(value["leave_one_participant_out_mean_pp"]),
                }
            )

    proper = {}
    for budget in BUDGETS:
        proper[str(budget)] = {}
        for metric in ("ce_clipped_1e15", "brier_positive_class"):
            left = participant_scores("eb_predictive", budget, metric)
            right = participant_scores("eb_point", budget, metric)
            differences = np.asarray(left) - np.asarray(right)
            proper[str(budget)][metric] = {
                "predictive": float(np.mean(left)), "point": float(np.mean(right)),
                "predictive_minus_point": float(differences.mean()),
                "ci95_difference": interval(differences),
                "participant_difference": dict(zip(subjects, differences.tolist())),
            }
    collapse = {
        method: {
            str(budget): sum(
                r["collapse"] for r in metrics
                if r["method"] == method and r["budget"] == budget
            ) for budget in BUDGETS
        } for method in methods if method != "saved_V2_ea_csp"
    }
    session_methods = (
        "eb_predictive", "tangent_refit", "eb_point", "eb_coupled",
        "eb_no_source_noise", "eb_no_shift",
    )
    by_session = {
        method: {
            session: float(np.mean([
                r["ba"] for r in metrics if r["method"] == method
                and r["session"] == session and r["budget"] == 20
            ])) * 100 for session in SESSIONS
        } for method in session_methods
    }
    session_comparisons = {}
    for reference in session_methods[1:]:
        session_comparisons[reference] = {}
        for session in SESSIONS:
            values = []
            for method in ("eb_predictive", reference):
                values.append([
                    next(
                        r["ba"] for r in metrics if r["participant"] == participant
                        and r["method"] == method and r["session"] == session
                        and r["budget"] == 20
                    ) for participant in subjects
                ])
            session_comparisons[reference][session] = effect(*values, subjects)

    diagnostic_summary = {}
    for budget in BUDGETS:
        selected = [r for r in diagnostics if r["budget"] == budget]
        diagnostic_summary[str(budget)] = {
            "cells": len(selected),
            "class_missing": sum(0 in r["support_class_counts"] for r in selected),
            "common_tau_zero": sum(r["tau_common_squared"] == 0 for r in selected),
            "contrast_tau_zero": sum(r["tau_halfcontrast_squared"] == 0 for r in selected),
            "common_greater_than_contrast": sum(
                r["tau_common_squared"] > r["tau_halfcontrast_squared"] for r in selected
            ),
            "tau_common_median": float(np.median([r["tau_common_squared"] for r in selected])),
            "tau_contrast_median": float(np.median([r["tau_halfcontrast_squared"] for r in selected])),
            "target_noise_trace_median": float(np.median([r["target_noise_trace"] for r in selected])),
            "posterior_trace_median": float(np.median([r["posterior_trace"] for r in selected])),
            "fallbacks": dict(collections.Counter(
                json.dumps(fallback, sort_keys=True)
                for r in selected for fallback in r["fallback"]
            )),
        }
    participant_diagnostics = {}
    for participant in subjects:
        selected = [r for r in diagnostics if r["budget"] == 20 and r["participant"] == participant]
        participant_diagnostics[participant] = {
            "common_median": float(np.median([r["tau_common_squared"] for r in selected])),
            "halfcontrast_median": float(np.median([r["tau_halfcontrast_squared"] for r in selected])),
            "common_greater_in_sessions": sum(
                r["tau_common_squared"] > r["tau_halfcontrast_squared"] for r in selected
            ),
            "support_counts": [r["support_class_counts"] for r in selected],
        }
    report = {
        "source": "Saved V3 predictions and metrics only; no fitting/forward",
        "participants": subjects, "prediction_files_recomputed": len(metrics),
        "max_ba_error": maximum_ba_error, "all_query_ids_and_labels_match": True,
        "cohort_ba_percent": summary, "all_candidate_comparisons": comparisons,
        "proper_score_exploratory": proper, "collapse_count_of_30": collapse,
        "session_ba_percent_n20": by_session, "session_comparisons_n20": session_comparisons,
        "diagnostics": diagnostic_summary,
        "participant_shift_diagnostics_n20": participant_diagnostics,
        "bootstrap": {"repetitions": BOOTSTRAP_REPETITIONS, "seed": BOOTSTRAP_SEED,
                      "participant_order": subjects, "interval": "pointwise percentile95%"},
        "scope": (
            "Six already-exposed development participants; pointwise discovery intervals, "
            "not confirmatory multiple-comparison correction. CE is clipped to1e-15 "
            "because saved probabilities may saturate; binary Brier uses positive-class probability."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "geometry_findings.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    write_csv(output / "geometry_cell_metrics.csv", metrics)
    write_csv(output / "geometry_all_budget_comparisons.csv", comparison_rows)
    write_csv(output / "geometry_cohort_ba.csv", [
        {"method": method, "budget": int(budget), "cohort_ba_percent": score}
        for method, values in summary.items() for budget, score in values.items()
    ])
    write_csv(output / "geometry_diagnostics.csv", [
        {**{k: v for k, v in row.items() if k not in ("support_class_counts", "fallback")},
         "support_class0": row["support_class_counts"][0],
         "support_class1": row["support_class_counts"][1],
         "actual_support_budget": sum(row["support_class_counts"]),
         "fallback_json": json.dumps(row["fallback"], sort_keys=True)}
        for row in diagnostics
    ])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", required=True, type=Path,
                        help="Extracted paper2_results/results directory")
    parser.add_argument("--output-root", required=True, type=Path,
                        help="New analysis directory outside the immutable input tree")
    args = parser.parse_args()
    report = analyze(args.results_root, args.output_root)
    print(json.dumps({"output_root": str(args.output_root.resolve()),
                      "prediction_files_recomputed": report["prediction_files_recomputed"],
                      "max_ba_error": report["max_ba_error"],
                      "prespecified_geometry_primary_n20": report["all_candidate_comparisons"][
                          "eb_predictive-minus-tangent_refit-n20"]}, indent=2))


if __name__ == "__main__":
    main()
