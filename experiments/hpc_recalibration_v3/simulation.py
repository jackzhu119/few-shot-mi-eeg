"""Paired Gaussian-feature mechanism checks for the exact V3 estimator.

These are synthetic mechanism/software checks, never replacement EEG results.
Every declared scenario and method is retained. No parameter is selected from
these query outcomes and no failed scientific cell is automatically retried.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import platform
import signal
import time
import traceback

import numpy as np

from hpc_recalibration.data import atomic_json
from .geometry import IMPLEMENTATION as GEOMETRY_IMPLEMENTATION, METHODS, fit_features


IMPLEMENTATION = "v3_paired_gaussian_feature_mechanisms_2"
FLAGS = {"synthetic": True, "software_validation_only": True}


def _identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def settings(config):
    supplied = config.get("science", {}).get("simulation", {})
    value = {
        "p": supplied.get("p", supplied.get("dimensions", [16, 64])),
        "target_perclass": supplied.get("target_perclass", [1, 2, 5, 10]),
        "shift": supplied.get("shift", ["none", "common", "contrast", "both"]),
        "anisotropy": supplied.get("anisotropy", [1, 20]),
        "repetitions": supplied.get("repetitions", 50),
        "source_perclass": supplied.get("source_perclass", 20),
        "source_perclass_levels": supplied.get(
            "source_perclass_levels", [supplied.get("source_perclass", 20)]
        ),
        "serial_correlations": supplied.get("serial_correlations", [0.0]),
        "query_perclass": supplied.get("query_perclass", 100),
        "shift_scale": supplied.get("shift_scale", 0.5),
        "seed": supplied.get("seed", 20261026),
    }
    for key in (
        "p",
        "target_perclass",
        "shift",
        "anisotropy",
        "source_perclass_levels",
        "serial_correlations",
    ):
        if (
            not isinstance(value[key], list)
            or not value[key]
            or len(set(value[key])) != len(value[key])
        ):
            raise ValueError("Simulation factors must be nonempty unique lists: " + key)
    if any(type(x) is not int or x < 2 for x in value["p"]):
        raise ValueError("Feature dimensions must be integers >=2")
    if any(type(x) is not int or x < 1 for x in value["target_perclass"]):
        raise ValueError("Target class counts must be positive integers")
    if any(type(x) is not int or x < 2 for x in value["source_perclass_levels"]):
        raise ValueError("Source class counts must be integers >=2")
    if any(
        type(x) not in (int, float) or not np.isfinite(x) or not 0 <= x < 1
        for x in value["serial_correlations"]
    ):
        raise ValueError("Serial correlations must be finite and in[0,1)")
    if any(x not in ("none", "common", "contrast", "both") for x in value["shift"]):
        raise ValueError("Unknown Gaussian domain-shift factor")
    if any(
        not isinstance(x, (float, int)) or not np.isfinite(x) or x < 1 for x in value["anisotropy"]
    ):
        raise ValueError("Anisotropy condition numbers must be finite and >=1")
    for key, minimum in (
        ("repetitions", 1),
        ("source_perclass", 2),
        ("query_perclass", 1),
        ("seed", 0),
    ):
        if type(value[key]) is not int or value[key] < minimum:
            raise ValueError("Invalid fixed simulation setting: " + key)
    if (
        not isinstance(value["shift_scale"], (int, float))
        or not np.isfinite(value["shift_scale"])
        or value["shift_scale"] < 0
    ):
        raise ValueError("shift_scale must be finite and nonnegative")
    return value


def scenarios(config):
    """Fixed Cartesian factors; indices do not depend on observed outcomes."""
    value = settings(config)
    return [
        {
            "scenario_index": i,
            "p": p,
            "target_perclass": n,
            "shift": shift,
            "anisotropy": anisotropy,
            "source_perclass": source_n,
            "serial_correlation": correlation,
            "iid_variance_over_n_assumption_stress": correlation > 0,
            "serial_model": "independent domain/class starts; stationary within-class AR(1)",
        }
        for i, (p, n, shift, anisotropy, source_n, correlation) in enumerate(
            itertools.product(
                value["p"],
                value["target_perclass"],
                value["shift"],
                value["anisotropy"],
                value["source_perclass_levels"],
                value["serial_correlations"],
            )
        )
    ]


def _ar1_noise(rng, n, p, factor, correlation):
    """Stationary Gaussian noise; rho0 consumes precisely the former IID draws."""
    noise = rng.standard_normal((n, p)) @ factor.T
    if correlation:
        innovation_scale = np.sqrt(1 - correlation**2)
        # The first innovation is already N(0,W), the stationary initial law.
        for position in range(1, n):
            noise[position] = correlation * noise[position - 1] + innovation_scale * noise[position]
    return noise


def generate(scenario, repetition, fixed):
    """One paired draw shared by all methods; query truth never enters fitting."""
    rng = np.random.default_rng(
        np.random.SeedSequence([fixed["seed"], scenario["scenario_index"], repetition])
    )
    p = scenario["p"]
    rotation, _ = np.linalg.qr(rng.standard_normal((p, p)))
    eigenvalues = np.geomspace(1, scenario["anisotropy"], p)
    eigenvalues /= eigenvalues.mean()
    within = (rotation * eigenvalues) @ rotation.T
    within = (within + within.T) * 0.5
    factor = np.linalg.cholesky(within)
    source_h = rng.standard_normal(p)
    source_h /= np.linalg.norm(source_h)
    common = (
        rng.standard_normal(p) * fixed["shift_scale"] / np.sqrt(p)
        if scenario["shift"] in ("common", "both")
        else np.zeros(p)
    )
    contrast = (
        rng.standard_normal(p) * fixed["shift_scale"] / np.sqrt(p)
        if scenario["shift"] in ("contrast", "both")
        else np.zeros(p)
    )
    source_means = np.stack([-source_h, source_h])
    target_means = np.stack([common - source_h - contrast, common + source_h + contrast])

    def sample(means, n):
        features = np.concatenate(
            [
                means[c] + _ar1_noise(rng, n, p, factor, scenario.get("serial_correlation", 0.0))
                for c in (0, 1)
            ]
        )
        labels = np.repeat(np.array([0, 1], dtype=np.int64), n)
        return features, labels

    source, source_y = sample(
        source_means, scenario.get("source_perclass", fixed["source_perclass"])
    )
    support, support_y = sample(target_means, scenario["target_perclass"])
    query, query_y = sample(target_means, fixed["query_perclass"])
    return source, source_y, support, support_y, query, query_y, target_means


def metrics(model, query, labels, true_means):
    probabilities = model.predict_probabilities(query)
    if (
        probabilities.shape != (len(labels), 2)
        or not np.isfinite(probabilities).all()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
        or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-10, rtol=0)
    ):
        raise ValueError("Invalid Gaussian mechanism probabilities")
    predicted = probabilities.argmax(axis=1)
    recall = [float(np.mean(predicted[labels == c] == c)) for c in (0, 1)]
    mean_errors = np.asarray(model.class_means) - true_means
    values = {
        "balanced_accuracy": float(np.mean(recall)),
        "cross_entropy": float(
            -np.log(np.maximum(probabilities[np.arange(len(labels)), labels], 1e-15)).mean()
        ),
        "binary_brier": float(np.mean((probabilities[:, 1] - labels) ** 2)),
        "mean_squared_feature_error": float(np.mean(mean_errors**2)),
        "mean_squared_euclidean_error": float(np.sum(mean_errors**2, axis=1).mean()),
        "n_query": len(labels),
    }
    if not all(np.isfinite(x) for x in values.values()):
        raise ValueError("Nonfinite Gaussian mechanism metric")
    return values


class StopState:
    def __init__(self):
        self.code = None

    def request(self, number):
        if number in (signal.SIGTERM, signal.SIGINT):
            self.code = 130
        elif self.code is None:
            self.code = 75


def run_task(task, config, *, stop=None, fit_function=None, after_cell=None):
    """Persist each paired-method result; repeat calls reuse all completed cells."""
    fixed = settings(config)
    all_scenarios = scenarios(config)
    indices = task.get("scenario_indices", list(range(len(all_scenarios))))
    if (
        not isinstance(indices, list)
        or not indices
        or len(set(indices)) != len(indices)
        or any(type(i) is not int or i not in range(len(all_scenarios)) for i in indices)
    ):
        raise ValueError("Invalid fixed simulation scenario_indices")
    task_id = task["task_id"]
    if (
        not isinstance(task_id, str)
        or task_id in (".", "..")
        or not task_id
        or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
            for c in task_id
        )
    ):
        raise ValueError("Unsafe simulation task ID")
    root = Path(config["output_root"]) / "tasks" / task_id
    root.mkdir(parents=True, exist_ok=True)
    geometry_settings = config.get("science", {}).get("geometry", {})
    identity = _identity(
        {
            "implementation": IMPLEMENTATION,
            "geometry_implementation": GEOMETRY_IMPLEMENTATION,
            "methods": list(METHODS),
            "task": task,
            "fixed": fixed,
            "geometry": geometry_settings,
            "experiment_id": config["experiment_id"],
            "scientific_version": config.get("scientific_version"),
        }
    )
    complete = root / "complete.json"
    if complete.is_file():
        saved = json.loads(complete.read_text())
        if saved.get("identity") != identity or saved.get("status") != "completed":
            raise ValueError(
                "Completed simulation identity changed; retain original and use a new version"
            )
        return 0
    stop = stop or StopState()
    fit_function = fit_function or fit_features
    previous = {n: signal.getsignal(n) for n in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT)}
    for number in previous:
        signal.signal(number, lambda n, frame: stop.request(n))
    records, failures = [], []
    processed, reused, fresh = 0, 0, 0
    last_emit = 0.0
    total = len(indices) * fixed["repetitions"] * len(METHODS)

    def progress(phase, force=False, **extra):
        nonlocal last_emit
        value = {
            "task_id": task_id,
            "family": "simulation",
            "phase": phase,
            "identity": identity,
            "step": processed,
            "completed_simulation_cells": processed,
            "expected_simulation_cells": total,
            "new_fits": fresh,
            "reused_cells": reused,
            "failed_cells": len(failures),
            "updated_at_unix": time.time(),
            **FLAGS,
            **extra,
        }
        atomic_json(root / "progress.json", value)
        now = time.monotonic()
        if force or now - last_emit >= float(config.get("heartbeat_seconds", 30)):
            print(json.dumps(value, allow_nan=False), flush=True)
            last_emit = now

    def aggregate():
        grouped = {}
        for row in records:
            key = row["scenario_index"], row["method"]
            grouped.setdefault(key, []).append(row)
        rows = []
        for (index, method), values in sorted(grouped.items()):
            row = {
                **all_scenarios[index],
                "method": method,
                "repetitions_complete": len(values),
                "repetitions_expected": fixed["repetitions"],
                **FLAGS,
            }
            for key in (
                "balanced_accuracy",
                "cross_entropy",
                "binary_brier",
                "mean_squared_feature_error",
                "mean_squared_euclidean_error",
            ):
                row[key] = float(np.mean([v[key] for v in values]))
            rows.append(row)
        atomic_json(
            root / "summary.json",
            {
                "task_id": task_id,
                "identity": identity,
                "scope": "synthetic_paired_mechanisms_not_EEG_evidence",
                "rows": rows,
                "failures": failures,
                "scenario_selection_from_query": False,
                **FLAGS,
            },
        )

    try:
        atomic_json(
            root / "runtime.json",
            {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "accelerator": "NumPy CPU",
                "host": platform.node(),
                "query_used_for_fitting": False,
                **FLAGS,
            },
        )
        progress("simulation", force=True)
        for index in indices:
            scenario = all_scenarios[index]
            for repetition in range(fixed["repetitions"]):
                if stop.code is not None:
                    aggregate()
                    progress(
                        "paused" if stop.code == 75 else "cancelled",
                        force=True,
                        exit_code=stop.code,
                    )
                    return stop.code
                path = (
                    root
                    / "cells"
                    / ("scenario-" + str(index).zfill(3))
                    / ("repetition-" + str(repetition).zfill(3) + ".json")
                )
                pair_identity = _identity(
                    {"task": identity, "scenario": index, "repetition": repetition}
                )
                if path.is_file():
                    pair = json.loads(path.read_text())
                    if pair.get("identity") != pair_identity:
                        raise ValueError("Saved paired simulation identity changed")
                else:
                    pair = {
                        "identity": pair_identity,
                        "scenario": scenario,
                        "repetition": repetition,
                        "methods": {},
                        **FLAGS,
                    }
                data = None
                for method in METHODS:
                    if stop.code is not None:
                        aggregate()
                        progress(
                            "paused" if stop.code == 75 else "cancelled",
                            force=True,
                            exit_code=stop.code,
                        )
                        return stop.code
                    row = pair["methods"].get(method)
                    if row is not None:
                        if row.get("status") == "completed":
                            records.append(row)
                        elif row.get("status") == "failed":
                            failures.append(row)
                        else:
                            raise ValueError("Invalid saved simulation cell status")
                        reused += 1
                        processed += 1
                        continue
                    if data is None:
                        data = generate(scenario, repetition, fixed)
                    source, source_y, support, support_y, query, query_y, true_means = data
                    row = {
                        "scenario_index": index,
                        "repetition": repetition,
                        "method": method,
                        "paired_random_draw": True,
                        "query_used_for_fitting": False,
                        **FLAGS,
                    }
                    try:
                        model = fit_function(
                            source, source_y, support, support_y, method, geometry_settings
                        )
                        row.update(metrics(model, query, query_y, true_means), status="completed")
                        row["mechanism"] = {
                            key: model.metadata[key]
                            for key in (
                                "source_class_counts",
                                "support_class_counts",
                                "tau_common_squared",
                                "tau_halfcontrast_squared",
                                "posterior_trace",
                                "source_mean_noise",
                                "target_observation_noise",
                                "variance_fallbacks",
                            )
                            if key in model.metadata
                        }
                        records.append(row)
                    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as error:
                        row.update(
                            status="failed",
                            exception_type=type(error).__name__,
                            traceback=traceback.format_exc(),
                        )
                        failures.append(row)
                    pair["methods"][method] = row
                    atomic_json(path, pair)
                    fresh += 1
                    processed += 1
                    progress(
                        "simulation", scenario_index=index, repetition=repetition, method=method
                    )
                    if after_cell is not None:
                        after_cell(row, stop)
                aggregate()
        aggregate()
        if failures:
            progress("failed", force=True, exit_code=1)
            return 1
        atomic_json(
            complete,
            {
                "task_id": task_id,
                "identity": identity,
                "status": "completed",
                "family": "simulation",
                "scenario_indices": indices,
                "paired_repetitions": len(indices) * fixed["repetitions"],
                "result_cells": processed,
                "implementation": IMPLEMENTATION,
                "real_EEG_evidence": False,
                **FLAGS,
            },
        )
        progress("completed", force=True, exit_code=0)
        return 0
    except BaseException as error:
        try:
            atomic_json(
                root / ("failure-" + str(time.time_ns()) + ".json"),
                {
                    "task_id": task_id,
                    "identity": identity,
                    "exception_type": type(error).__name__,
                    "traceback": traceback.format_exc(),
                    **FLAGS,
                },
            )
        except OSError:
            traceback.print_exc()
        raise
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
