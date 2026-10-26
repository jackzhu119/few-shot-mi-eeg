"""Tiny synthetic mechanism paths only; no EEG, model training, GPU or Slurm."""

from pathlib import Path
import json
import signal
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
sys.path.insert(0, str(ROOT / "experiments"))
from hpc_recalibration_v3 import simulation  # noqa: E402


@pytest.fixture
def config(tmp_path):
    return {
        "experiment_id": "synthetic-v3-simulation",
        "scientific_version": "software-check1",
        "output_root": str(tmp_path / "outputs"),
        "heartbeat_seconds": 30,
        "science": {
            "simulation": {
                "p": [4],
                "target_perclass": [1],
                "shift": ["none", "both"],
                "anisotropy": [2],
                "repetitions": 2,
                "source_perclass": 8,
                "query_perclass": 10,
                "seed": 7,
            },
            "geometry": {"feature_shrinkage": 0.1},
        },
    }


def task():
    return {"task_id": "simulation-small", "family": "simulation", "scenario_indices": [0, 1]}


def test_default_grid_has64_scenarios_and50_repetitions():
    assert len(simulation.scenarios({})) == 64
    assert simulation.settings({})["repetitions"] == 50


def test_two_source_and_serial_axes_produce384_declared_scenarios():
    cfg = {
        "science": {
            "simulation": {
                "source_perclass_levels": [10, 20, 100],
                "serial_correlations": [0.0, 0.5],
            }
        }
    }
    grid = simulation.scenarios(cfg)
    assert len(grid) == 384
    assert {r["source_perclass"] for r in grid} == {10, 20, 100}
    assert {r["serial_correlation"] for r in grid} == {0.0, 0.5}
    assert all(
        r["iid_variance_over_n_assumption_stress"] == (r["serial_correlation"] > 0) for r in grid
    )


def test_source_sample_axis_changes_actual_draw_count_and_ar1_is_deterministic(config):
    config["science"]["simulation"].update(
        source_perclass_levels=[4, 12], serial_correlations=[0.0, 0.5]
    )
    grid = simulation.scenarios(config)
    fixed = simulation.settings(config)
    for scenario in grid:
        first = simulation.generate(scenario, 0, fixed)
        second = simulation.generate(scenario, 0, fixed)
        assert first[0].shape == (2 * scenario["source_perclass"], 4)
        assert first[1].shape == (2 * scenario["source_perclass"],)
        assert all(np.array_equal(a, b) for a, b in zip(first, second))


def test_zero_ar1_keeps_iid_draws_and_positive_ar1_has_expected_lag_correlation():
    factor = np.array([[1.0, 0.0], [0.2, 0.8]])
    expected = np.random.default_rng(17).standard_normal((2000, 2)) @ factor.T
    actual = simulation._ar1_noise(np.random.default_rng(17), 2000, 2, factor, 0.0)
    assert np.array_equal(actual, expected)
    serial = simulation._ar1_noise(np.random.default_rng(17), 2000, 2, factor, 0.5)
    assert np.array_equal(serial[0], expected[0])
    assert not np.array_equal(serial[1:], actual[1:])
    assert 0.43 < np.corrcoef(serial[:-1, 0], serial[1:, 0])[0, 1] < 0.57


def test_small_serial_stress_run_preserves_axes_and_misspecification_flag(config):
    config["science"]["simulation"].update(source_perclass_levels=[4], serial_correlations=[0.5])
    assert simulation.run_task(task(), config) == 0
    root = Path(config["output_root"]) / "tasks" / task()["task_id"]
    rows = json.loads((root / "summary.json").read_text())["rows"]
    assert len(rows) == 2 * len(simulation.METHODS)
    assert all(r["source_perclass"] == 4 and r["serial_correlation"] == 0.5 for r in rows)
    assert all(r["iid_variance_over_n_assumption_stress"] for r in rows)


def test_same_scenario_draw_is_paired_deterministic_and_query_independent(config):
    fixed = simulation.settings(config)
    scenario = simulation.scenarios(config)[1]
    first = simulation.generate(scenario, 0, fixed)
    second = simulation.generate(scenario, 0, fixed)
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    assert first[0].shape == (16, 4) and first[2].shape == (2, 4)
    assert not np.array_equal(first[0][:2], first[2])
    assert np.isfinite(first[-1]).all()


def test_tiny_complete_all_methods_and_resume_without_any_refit(config):
    assert simulation.run_task(task(), config) == 0
    root = Path(config["output_root"]) / "tasks" / task()["task_id"]
    done = json.loads((root / "complete.json").read_text())
    assert done["result_cells"] == 2 * 2 * len(simulation.METHODS)
    assert done["synthetic"] is True and done["software_validation_only"] is True
    rows = json.loads((root / "summary.json").read_text())["rows"]
    assert len(rows) == 2 * len(simulation.METHODS)
    assert all(r["repetitions_complete"] == 2 for r in rows)
    assert all(np.isfinite(r["cross_entropy"]) and 0 <= r["balanced_accuracy"] <= 1 for r in rows)
    assert (
        simulation.run_task(
            task(), config, fit_function=lambda *a: pytest.fail("Completed task retrained")
        )
        == 0
    )


def test_usr1_partial_resumes_completed_method_cells_exactly_once(config):
    calls = []

    def fit(*args):
        calls.append(args[4])
        return simulation.fit_features(*args)

    assert (
        simulation.run_task(
            task(),
            config,
            fit_function=fit,
            after_cell=lambda row, stop: stop.request(signal.SIGUSR1),
        )
        == 75
    )
    assert len(calls) == 1
    assert simulation.run_task(task(), config, fit_function=fit) == 0
    assert len(calls) == 2 * 2 * len(simulation.METHODS)
    p = Path(config["output_root"]) / "tasks" / task()["task_id"] / "progress.json"
    assert json.loads(p.read_text())["reused_cells"] == 1


def test_scientific_cell_failure_is_retained_without_automatic_retry(config):
    calls = []

    def broken(*args):
        calls.append(args[4])
        if args[4] == "eb_predictive":
            raise FloatingPointError("synthetic intentional numerical failure")
        return simulation.fit_features(*args)

    assert simulation.run_task(task(), config, fit_function=broken) == 1
    assert len(calls) == 2 * 2 * len(simulation.METHODS)
    assert (
        simulation.run_task(
            task(), config, fit_function=lambda *a: pytest.fail("Retained failed cell retried")
        )
        == 1
    )
    root = Path(config["output_root"]) / "tasks" / task()["task_id"]
    assert len(json.loads((root / "summary.json").read_text())["failures"]) == 4
    assert not (root / "complete.json").exists()


def test_storage_failure_stops_before_any_additional_fit(config, monkeypatch):
    original = simulation.atomic_json
    calls = []

    def write(path, value):
        if "/cells/" in str(path):
            raise OSError("synthetic disk failure")
        return original(path, value)

    def fit(*args):
        calls.append(args[4])
        return simulation.fit_features(*args)

    monkeypatch.setattr(simulation, "atomic_json", write)
    with pytest.raises(OSError, match="disk failure"):
        simulation.run_task(task(), config, fit_function=fit)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "key,value",
    [
        ("p", [1]),
        ("target_perclass", [0]),
        ("repetitions", 0),
        ("shift", ["unknown"]),
        ("anisotropy", [float("inf")]),
        ("source_perclass_levels", [1]),
        ("source_perclass_levels", []),
        ("serial_correlations", [-0.1]),
        ("serial_correlations", [1.0]),
        ("serial_correlations", [float("nan")]),
    ],
)
def test_bad_fixed_grid_rejected_before_work(config, key, value):
    config["science"]["simulation"][key] = value
    with pytest.raises(ValueError):
        simulation.run_task(task(), config)
