"""Saved synthetic metric fixtures only: no model/EEG/forward/Slurm execution."""

from pathlib import Path
import csv
import json
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
sys.path.insert(0, str(ROOT / "experiments"))
from hpc_recalibration_v3.summarize import summarize  # noqa: E402


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n")


def raw(task, session, method, budget, ba):
    return {
        "task_id": task["task_id"],
        "dataset": task["dataset"],
        "participant": task["participant"],
        "session": session,
        "method": method,
        "requested_budget": budget,
        "actual_budget": budget,
        "balanced_accuracy": ba,
        "n_query": 20,
        "class_counts": [10, 10],
        "query_identity": "v3-" + task["participant"] + "-" + session,
        "seed": task.get("seed", "deterministic"),
        "query_used_for_fitting": False,
        "synthetic": True,
        "software_validation_only": True,
    }


@pytest.fixture
def experiment(tmp_path):
    tasks = []
    for person in ("p1", "p2"):
        targets = [
            {
                "session": "ses-" + str(s),
                "support": person + "-support" + str(s),
                "query": person + "-query" + str(s),
            }
            for s in (1, 2)
        ]
        tasks.append(
            {
                "task_id": person + "-geometry",
                "participant": person,
                "dataset": "synthetic",
                "family": "geometry",
                "variant": "core",
                "legacy_task_id": person + "-old",
                "targets": targets,
                "synthetic": True,
            }
        )
        for variant in ("core", "kl0p001"):
            for seed in (11, 12):
                task = {
                    "task_id": person + "-" + variant + "-s" + str(seed),
                    "participant": person,
                    "dataset": "synthetic",
                    "family": "neural",
                    "source_regime": "reuse_v2",
                    "variant": variant,
                    "seed": seed,
                    "targets": targets,
                    "synthetic": True,
                }
                if variant != "core":
                    task["science_overrides"] = {
                        "neural_methods": ["trust_fixed"],
                        "trust_kl_budget": 0.001,
                    }
                tasks.append(task)
    config = {
        "experiment_id": "synthetic-v3-summary",
        "output_root": str(tmp_path / "results"),
        "v2_output_root": str(tmp_path / "old"),
        "tasks": tasks,
        "science": {
            "budgets": [4, 20],
            "geometry_methods": ["tangent_refit", "eb_predictive"],
            "neural_methods": ["full_fixed", "trust_fixed", "full_adaptive_bn"],
            "analysis": {"bootstrap_repetitions": 10000, "bootstrap_seed": 20261023},
        },
    }
    root = Path(config["output_root"])
    for task in tasks:
        folder = root / "tasks" / task["task_id"]
        write(
            folder / "complete.json",
            {"task_id": task["task_id"], "status": "completed", "identity": "synthetic"},
        )
        methods = (
            config["science"]["geometry_methods"]
            if task["family"] == "geometry"
            else task.get("science_overrides", {}).get(
                "neural_methods", config["science"]["neural_methods"]
            )
        )
        for target in task["targets"]:
            session = target["session"]
            for budget in (4, 20):
                for method in methods:
                    if task["family"] == "geometry":
                        ba = {
                            "p1": {"tangent_refit": 0.60, "eb_predictive": 0.70},
                            "p2": {"tangent_refit": 0.65, "eb_predictive": 0.60},
                        }[task["participant"]][method]
                        path = (
                            folder
                            / "evaluation"
                            / f"{session}__n{budget}__{method}"
                            / "metrics.json"
                        )
                    else:
                        ba = (
                            0.60
                            + (0.02 if method == "trust_fixed" else 0)
                            + (0.04 if task["seed"] == 12 else 0)
                        )
                        path = (
                            folder
                            / "evaluation"
                            / session
                            / method
                            / f"budget-{budget}"
                            / "metrics.json"
                        )
                    write(path, raw(task, session, method, budget, ba))
                    if task["family"] == "geometry" and method == "eb_predictive":
                        np.savez_compressed(
                            path.with_name("predictions.npz"),
                            trial_id=np.array([f"trial-{i}" for i in range(20)]),
                            labels=np.repeat([0, 1], 10),
                        )
                if task["family"] == "geometry":
                    old = raw(task, session, "ea_csp", budget, 0.61)
                    old["task_id"] = task["legacy_task_id"]
                    old.pop("seed")
                    old["query_identity"] = "different-v2-hash-scheme"
                    old["trial_ids"] = [f"trial-{i}" for i in range(20)]
                    old["y"] = np.repeat([0, 1], 10).tolist()
                    write(
                        Path(config["v2_output_root"])
                        / "tasks"
                        / task["legacy_task_id"]
                        / "evaluation"
                        / f"{session}__n{budget}__ea_csp.json",
                        old,
                    )
    return config


def primary(summary, family="geometry"):
    return next(
        r for r in summary["comparisons"] if r["contrast_role"] == f"prespecified_{family}_primary"
    )


def test_complete_participant_seed_session_aggregation_and_fixed_intervals(experiment):
    summary = summarize(experiment)
    row = primary(summary)
    assert row["expected_participants"] == row["paired_participants"] == 2
    assert row["mean_difference_pp"] == pytest.approx(2.5)
    assert [row["ci_low_pp"], row["ci_high_pp"]] == pytest.approx([-5, 10])
    assert primary(summary, "neural")["mean_difference_pp"] == pytest.approx(2)
    assert not summary["partial"] and summary["missing_cells"] == []
    assert summary["bootstrap_repetitions"] == 10000 and summary["bootstrap_seed"] == 20261023
    assert (Path(experiment["output_root"]) / "analysis/comparisons.csv").is_file()


def test_missing_seed_invalidates_participant_and_full_cohort_endpoint(experiment):
    path = (
        Path(experiment["output_root"])
        / "tasks/p1-core-s11/evaluation/ses-1/trust_fixed/budget-20/metrics.json"
    )
    path.unlink()
    summary = summarize(experiment)
    row = primary(summary, "neural")
    assert summary["partial"] and len(summary["missing_cells"]) == 1
    assert row["mean_difference_pp"] is None and row["paired_participants"] == 1
    assert row["complete_case_mean_difference_pp"] == pytest.approx(2)
    assert row["incomplete_participants"] == "p1"
    with (Path(experiment["output_root"]) / "analysis/participant_metrics.csv").open() as stream:
        p = next(
            r
            for r in csv.DictReader(stream)
            if r["participant"] == "p1"
            and r["family"] == "neural"
            and r["variant"] == "core"
            and r["method"] == "trust_fixed"
            and r["budget"] == "20"
        )
    assert p["balanced_accuracy"] == "" and p["available_sessions"] == "1"


def test_legacy_reference_uses_ordered_ids_not_unequal_hash_schemes(experiment):
    summary = summarize(experiment)
    rows = [
        r for r in summary["comparisons"] if r["contrast_role"] == "prespecified_strong_reference"
    ]
    assert len(rows) == 1 and rows[0]["paired_participants"] == 2 and rows[0]["endpoint_complete"]
    assert summary["imported_reference_cells"] == 8
    assert summary["reference_import_does_not_create_new_fit"] is True


def test_legacy_reference_wrong_order_stops_false_comparison(experiment):
    p = Path(experiment["v2_output_root"]) / "tasks/p1-old/evaluation/ses-1__n4__ea_csp.json"
    value = json.loads(p.read_text())
    value["trial_ids"].reverse()
    write(p, value)
    with pytest.raises(ValueError, match="ordered query IDs"):
        summarize(experiment)


def test_dose_compares_to_matching_core_without_reselecting_threshold(experiment):
    summary = summarize(experiment)
    rows = [r for r in summary["comparisons"] if r["contrast_role"] == "descriptive_KL_dose"]
    assert len(rows) == 2
    assert all(r["variant"] == "kl0p001" and r["reference_variant"] == "core" for r in rows)
    same = next(r for r in rows if r["reference"] == "trust_fixed")
    assert same["mean_difference_pp"] == pytest.approx(0)


def test_query_identity_mismatch_not_paired(experiment):
    p = (
        Path(experiment["output_root"])
        / "tasks/p1-core-s11/evaluation/ses-1/trust_fixed/budget-20/metrics.json"
    )
    value = json.loads(p.read_text())
    value["query_identity"] = "different-query"
    write(p, value)
    with pytest.raises(ValueError, match="query identities"):
        summarize(experiment)


@pytest.mark.parametrize(
    "field,value",
    [
        ("participant", "wrong"),
        ("requested_budget", 999),
        ("balanced_accuracy", float("nan")),
        ("class_counts", [1, 1]),
    ],
)
def test_bad_saved_metric_rejected(experiment, field, value):
    p = (
        Path(experiment["output_root"])
        / "tasks/p1-geometry/evaluation/ses-1__n4__eb_predictive/metrics.json"
    )
    data = json.loads(p.read_text())
    data[field] = value
    write(p, data)
    with pytest.raises(ValueError):
        summarize(experiment)


def test_simulations_remain_separate_from_participant_cohorts(experiment):
    task = {
        "task_id": "simulation-only",
        "family": "simulation",
        "synthetic": True,
        "software_validation_only": True,
    }
    experiment["tasks"].append(task)
    folder = Path(experiment["output_root"]) / "tasks" / task["task_id"]
    write(
        folder / "complete.json",
        {"task_id": task["task_id"], "status": "completed", "identity": "synthetic"},
    )
    write(
        folder / "summary.json",
        {
            "synthetic": True,
            "software_validation_only": True,
            "rows": [
                {
                    "scenario_index": 0,
                    "method": "eb_predictive",
                    "balanced_accuracy": 0.8,
                    "repetitions_complete": 2,
                }
            ],
        },
    )
    summary = summarize(experiment)
    assert summary["simulation_scenario_method_rows"] == 1
    assert all(r["expected_participants"] == 2 for r in summary["cohorts"])


def test_missing_query_class_is_explicit_unavailable_endpoint(experiment):
    p = (
        Path(experiment["output_root"])
        / "tasks/p1-core-s11/evaluation/ses-1/trust_fixed/budget-20/metrics.json"
    )
    data = json.loads(p.read_text())
    data.update(class_counts=[20, 0], balanced_accuracy=None)
    write(p, data)
    summary = summarize(experiment)
    assert primary(summary, "neural")["mean_difference_pp"] is None
    assert summary["missing_cells"][0]["status"] == "undefined_query_class"


def test_variant_missing_entire_participant_not_silently_smaller_cohort(experiment):
    experiment["tasks"] = [
        t
        for t in experiment["tasks"]
        if not (t.get("variant") == "kl0p001" and t["participant"] == "p1")
    ]
    with pytest.raises(ValueError, match="different participant cohorts"):
        summarize(experiment)


def test_completion_file_requires_true_task_identity_and_completed_status(experiment):
    path = Path(experiment["output_root"]) / "tasks/p1-core-s11/complete.json"
    write(path, {"task_id": "p1-core-s11", "identity": "synthetic", "status": "failed"})
    with pytest.raises(ValueError, match="Malformed completion"):
        summarize(experiment)


def test_pending_reference_readback_is_partial_not_a_complete_strong_comparison(experiment):
    path = (
        Path(experiment["output_root"])
        / "tasks/p1-geometry/evaluation/ses-1__n20__eb_predictive/predictions.npz"
    )
    path.unlink()
    summary = summarize(experiment)
    assert summary["partial"] and summary["reference_alignment_pending_cells"] == 1
    row = next(
        r for r in summary["comparisons"] if r["contrast_role"] == "prespecified_strong_reference"
    )
    assert row["paired_participants"] == 1 and row["mean_difference_pp"] is None
