#!/usr/bin/env python3
"""Reaggregate the saved V3 Gaussian mechanism grid; never fit or simulate.

Read the 19,200 existing paired-repetition JSON files and compare their means
with all 3,456 saved scenario/method summaries. Synthetic mechanisms remain
separate from EEG evidence. Monte Carlo intervals describe finite draws in the
fixed factorial grid, not uncertainty across human participants.

Requires only NumPy and the standard library. The input directory is the
``results`` directory within an extracted, integrity-verified V3 result packet.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np


METHODS = (
    "source_tangent_frozen",
    "tangent_pooled",
    "tangent_refit",
    "eb_point",
    "eb_predictive",
    "eb_isotropic",
    "eb_coupled",
    "eb_no_source_noise",
    "eb_no_shift",
)
METRICS = (
    "balanced_accuracy",
    "cross_entropy",
    "binary_brier",
    "mean_squared_feature_error",
    "mean_squared_euclidean_error",
)
FACTORS = (
    "p",
    "target_perclass",
    "shift",
    "anisotropy",
    "source_perclass",
    "serial_correlation",
)
REPETITIONS = 50
SCENARIOS = 384
TIE_TOLERANCE = 1e-14


def file_identity(path: Path, relative_to: Path) -> dict:
    data = path.read_bytes()
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def expected_scenarios() -> dict:
    """The already frozen factor ordering, without importing simulation code."""
    grid = itertools.product(
        (16, 64), (1, 2, 5, 10), ("none", "common", "contrast", "both"),
        (1, 20), (10, 20, 100), (0, 0.5),
    )
    return {index: dict(zip(FACTORS, values)) for index, values in enumerate(grid)}


def read_draws(root: Path):
    """Validate and load saved metrics, with exact paired identities and flags."""
    values = np.full((SCENARIOS, REPETITIONS, len(METHODS), len(METRICS)), np.nan)
    tau = np.full((SCENARIOS, REPETITIONS, 2), np.nan)
    scenarios = expected_scenarios()
    inputs = []
    for block in range(9):
        task = root / "tasks" / f"v3-mechanism-block-{block}"
        for path in sorted(task.glob("cells/scenario-*/repetition-*.json")):
            data = path.read_bytes()
            record = json.loads(data)
            scenario = record["scenario"]
            index = scenario["scenario_index"]
            repetition = record["repetition"]
            if (
                type(index) is not int or index not in scenarios
                or type(repetition) is not int or repetition not in range(REPETITIONS)
                or index % 9 != block
                or path.parent.name != f"scenario-{index:03d}"
                or path.name != f"repetition-{repetition:03d}.json"
            ):
                raise ValueError(f"Saved scenario/repetition path mismatch: {path}")
            if any(scenario.get(key) != val for key, val in scenarios[index].items()):
                raise ValueError(f"Saved scenario differs from the frozen grid: {path}")
            if np.isfinite(values[index, repetition]).any():
                raise ValueError(f"Duplicate paired draw: {path}")
            if set(record["methods"]) != set(METHODS):
                raise ValueError(f"Missing or extra method in paired draw: {path}")
            for method_index, method in enumerate(METHODS):
                row = record["methods"][method]
                if not (
                    row.get("scenario_index") == index
                    and row.get("repetition") == repetition
                    and row.get("method") == method
                    and row.get("paired_random_draw") is True
                    and row.get("synthetic") is True
                    and row.get("software_validation_only") is True
                    and row.get("query_used_for_fitting") is False
                    and row.get("status") == "completed"
                    and row.get("n_query") == 200
                ):
                    raise ValueError(f"Invalid saved method identity or scope flags: {path}")
                metrics = np.asarray([row[key] for key in METRICS], dtype=np.float64)
                if not np.isfinite(metrics).all() or (
                    not 0 <= metrics[0] <= 1 or (metrics[1:] < 0).any()
                ):
                    raise ValueError(f"Invalid saved numeric metric: {path}")
                values[index, repetition, method_index] = metrics
            mechanism = record["methods"]["eb_predictive"]["mechanism"]
            tau[index, repetition] = [
                mechanism["tau_common_squared"], mechanism["tau_halfcontrast_squared"]
            ]
            inputs.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            })
    if len(inputs) != SCENARIOS * REPETITIONS or not np.isfinite(values).all():
        raise ValueError("The saved fixed grid is incomplete; no partial endpoint is generated")
    if not np.isfinite(tau).all() or (tau < 0).any():
        raise ValueError("Invalid saved empirical drift scales")
    return values, scenarios, tau, inputs


def paired_comparison(values: np.ndarray, indices: list, reference: str) -> dict:
    candidate = METHODS.index("eb_predictive")
    baseline = METHODS.index(reference)
    differences = values[indices, :, candidate] - values[indices, :, baseline]
    scenario_differences = differences.mean(axis=1)
    result = {
        "n_scenarios": len(indices),
        "n_paired_draws": len(indices) * REPETITIONS,
    }
    for metric_index, metric in enumerate(METRICS):
        draws = differences[:, :, metric_index]
        means = scenario_differences[:, metric_index]
        # Independent repetitions within each predeclared stratum; no random
        # scenario resampling or treatment as independent EEG participants.
        se = float(np.sqrt(np.sum(np.var(draws, axis=1, ddof=1) / REPETITIONS)) / len(indices))
        average = float(draws.mean())
        result[metric] = {
            "mean_difference": average,
            "fixed_grid_monte_carlo_standard_error": se,
            "mc_normal_95_low": average - 1.96 * se,
            "mc_normal_95_high": average + 1.96 * se,
            "scenario_positive": int((means > TIE_TOLERANCE).sum()),
            "scenario_zero": int((np.abs(means) <= TIE_TOLERANCE).sum()),
            "scenario_negative": int((means < -TIE_TOLERANCE).sum()),
            "scenario_min": float(means.min()),
            "scenario_median": float(np.median(means)),
            "scenario_max": float(means.max()),
        }
    return result


def check_saved_summary(root: Path, means: np.ndarray) -> dict:
    path = root / "analysis" / "simulation_scenarios.csv"
    observed = set()
    maximum_error = 0.0
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            index = int(row["scenario_index"])
            method = row["method"]
            key = (index, method)
            if key in observed or index not in range(SCENARIOS) or method not in METHODS:
                raise ValueError("Duplicate or unexpected saved scenario summary")
            observed.add(key)
            if (
                int(row["repetitions_complete"]) != REPETITIONS
                or int(row["repetitions_expected"]) != REPETITIONS
                or row["synthetic"] != "True"
                or row["software_validation_only"] != "True"
            ):
                raise ValueError("Saved scenario summary flags/count mismatch")
            method_index = METHODS.index(method)
            for metric_index, metric in enumerate(METRICS):
                error = abs(float(row[metric]) - means[index, method_index, metric_index])
                maximum_error = max(maximum_error, float(error))
                if error > 1e-12:
                    raise ValueError(f"Saved scenario summary numeric mismatch: {key}, {metric}")
    if len(observed) != SCENARIOS * len(METHODS):
        raise ValueError("Saved scenario summary is incomplete")
    return {"rows_checked": len(observed), "maximum_absolute_metric_difference": maximum_error,
            "all_saved_summary_rows_match": True, "input": file_identity(path, root)}


def analyze(root: Path, destination: Path) -> dict:
    values, scenarios, tau, inputs = read_draws(root)
    means = values.mean(axis=1)
    summary_check = check_saved_summary(root, means)
    candidate = METHODS.index("eb_predictive")
    result = {
        "scope": (
            "SAVED synthetic mechanism diagnostics only; not EEG confirmation, no new fit or "
            "simulation. Equal weight all frozen 384 scenarios and all 50 paired repetitions. "
            "MC intervals concern finite simulated draws in a fixed grid, not population uncertainty."
        ),
        "synthetic": True, "software_validation_only": True,
        "no_training_or_inference": True,
        "expected_simulation_cells": SCENARIOS * REPETITIONS * len(METHODS),
        "observed_simulation_cells": int(np.prod(values.shape[:3])),
        "all_cells_numeric_and_flags_valid": True,
        "methods": METHODS, "metrics": METRICS,
        "method_means": {
            method: {metric: float(values[:, :, mi, ki].mean())
                     for ki, metric in enumerate(METRICS)}
            for mi, method in enumerate(METHODS)
        },
        "candidate_vs": {
            method: paired_comparison(values, list(range(SCENARIOS)), method)
            for method in METHODS if method != "eb_predictive"
        },
        "factors": {}, "source_summary_crosscheck": summary_check,
    }
    for factor in FACTORS:
        groups = {}
        for level in sorted({scenario[factor] for scenario in scenarios.values()}):
            indices = [index for index, scenario in scenarios.items() if scenario[factor] == level]
            groups[str(level)] = {
                "candidate_means": {
                    metric: float(values[indices, :, candidate, ki].mean())
                    for ki, metric in enumerate(METRICS)
                },
                "versus": {
                    method: paired_comparison(values, indices, method)
                    for method in (
                        "tangent_refit", "source_tangent_frozen", "eb_point",
                        "eb_isotropic", "eb_no_shift", "eb_coupled",
                    )
                },
            }
        result["factors"][factor] = groups
    result["tau"] = {
        "fraction_common_zero": float((tau[:, :, 0] == 0).mean()),
        "fraction_halfcontrast_zero": float((tau[:, :, 1] == 0).mean()),
        "fraction_both_zero": float((tau == 0).all(axis=2).mean()),
        "common_mean": float(tau[:, :, 0].mean()),
        "halfcontrast_mean": float(tau[:, :, 1].mean()),
        "by_shift": {},
    }
    for shift in sorted({scenario["shift"] for scenario in scenarios.values()}):
        indices = [index for index, scenario in scenarios.items() if scenario["shift"] == shift]
        result["tau"]["by_shift"][shift] = {
            "fraction_common_zero": float((tau[indices, :, 0] == 0).mean()),
            "fraction_halfcontrast_zero": float((tau[indices, :, 1] == 0).mean()),
        }
    destination.mkdir(parents=True, exist_ok=True)
    processor = Path(__file__).resolve()
    provenance = {
        "scope": "Saved paired repetition JSON; all lengths and SHA256 values retained",
        "count": len(inputs), "files": inputs,
        "saved_summary": summary_check["input"],
        "processor_sha256": hashlib.sha256(processor.read_bytes()).hexdigest(),
    }
    archive_manifest = root.parent / "MANIFEST.json"
    if archive_manifest.is_file():
        provenance["archive_manifest"] = file_identity(archive_manifest, root.parent)
    (destination / "simulation_inputs.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (destination / "simulation_findings.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ("scenario_index",) + FACTORS + ("method",) + METRICS
    with (destination / "simulation_all_scenarios.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index in range(SCENARIOS):
            for method_index, method in enumerate(METHODS):
                writer.writerow({
                    "scenario_index": index, **scenarios[index], "method": method,
                    **{metric: float(means[index, method_index, ki])
                       for ki, metric in enumerate(METRICS)},
                })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    arguments = parser.parse_args()
    result = analyze(arguments.results_root.resolve(), arguments.output_root.resolve())
    print(json.dumps({
        "scope": result["scope"],
        "simulation_cells": result["observed_simulation_cells"],
        "summary_crosscheck": result["source_summary_crosscheck"],
        "output_root": str(arguments.output_root.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
