"""Saved synthetic metrics only; no model, EEG loading or inference."""

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"))

from hpc_recalibration.summarize import summarize


def fixture(tmp_path, family="eegnet", methods=None):
    tasks = [{"task_id": f"{family}-{participant}-{seed}", "family": family,
              "dataset": "synthetic", "participant": participant, "seed": seed,
              "synthetic": True, "source_query": "does-not-exist.npz",
              "targets": [{"session": "s2"}, {"session": "s3"}]}
             for participant in ("p1", "p2") for seed in (1, 2)]
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps(tasks))
    config = {"experiment_id": "software_validation_only", "output_root": str(tmp_path / "out"),
              "tasks_file": str(tasks_path), "budgets": [20],
              "methods": methods or ["frozen", "head"],
              "classical_methods": methods or ["ea_csp", "ea_empirical_anchored_csp"]}
    return config, tasks


def save(config, task, session, method, score, *, missing_class=False, query_identity=None):
    root = Path(config["output_root"]) / "tasks" / task["task_id"]
    budget = 0 if session == "source" else 20
    counts = {"0": 10, "1": 0 if missing_class else 10}
    metrics = {"balanced_accuracy": score, "n_query": sum(counts.values()), "class_counts": counts}
    value = {key: task[key] for key in ("task_id", "dataset", "participant", "seed", "synthetic")}
    value.update(session=session, method=method, query_identity=query_identity or f"{task['task_id']}-{session}")
    if task["family"] == "classical":
        path = root / "evaluation" / f"{session}__n{budget}__{method}.json"
        value.update(budget_requested=budget, n_support_actual=budget, metrics=metrics)
    else:
        path = root / "source_query.json" if session == "source" else root / "evaluation" / session / method / "budget-20" / "metrics.json"
        value.update(requested_budget=budget, actual_budget=budget, **metrics)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def populate(config, tasks):
    for task in tasks:
        for session in ("s2", "s3"):
            # Seed mean p1: frozen .50, head .60; p2 frozen .70, head .50.
            base = .4 if task["participant"] == "p1" else .6
            score = base + (.1 if task["seed"] == 2 else 0) + (.1 if session == "s3" else 0)
            gain = .1 if task["participant"] == "p1" else -.2
            methods = config["methods"] if task["family"] == "eegnet" else config["classical_methods"]
            save(config, task, session, methods[0], score)
            save(config, task, session, methods[1], score + gain)
        save(config, task, "source", "frozen", .8)


def csv_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def test_seed_session_participant_aggregation_and_source_separation(tmp_path):
    config, tasks = fixture(tmp_path)
    populate(config, tasks)
    report = summarize(config)
    assert report["tasks_expected"] == 4 and report["tasks_complete"] == 0
    assert report["cells_expected"] == report["cells_with_defined_ba"] == 16
    assert report["synthetic"] is report["software_validation_only"] is True
    assert report["independent_unit"] == "participant"
    contrast = report["comparisons"][0]
    assert len(report["comparisons"]) == 1
    assert contrast["paired_participants"] == 2  # not 4 seeds or 8 sessions
    assert contrast["mean_difference_pp"] == pytest.approx(-5)
    assert contrast["ci_low_pp"] == pytest.approx(-20)
    assert contrast["ci_high_pp"] == pytest.approx(10)
    assert contrast["decline_at_least_5pp_participants"] == 1
    rows = csv_rows(Path(config["output_root"]) / "analysis/participant_metrics.csv")
    scores = {(row["participant"], row["method"]): float(row["balanced_accuracy"]) for row in rows}
    assert scores == pytest.approx({("p1", "frozen"): .5, ("p1", "head"): .6,
                                    ("p2", "frozen"): .7, ("p2", "head"): .5})
    assert all(row["source_query_balanced_accuracy"] == .8 for row in report["source_query_participants"])
    assert all(row["selection_use"] is False for row in report["source_query_participants"])
    assert len(csv_rows(Path(config["output_root"]) / "analysis/saved_cells.csv")) == 20


def test_missing_seed_and_query_class_remain_explicit(tmp_path):
    config, tasks = fixture(tmp_path)
    populate(config, tasks)
    save(config, tasks[0], "s2", "head", None, missing_class=True)
    path = save(config, tasks[3], "s3", "head", .5)
    path.unlink()
    report = summarize(config)
    assert len(report["missing_cells"]) == 2
    contrast = report["comparisons"][0]
    assert contrast["paired_participants"] == 0
    assert contrast["incomplete_participants"] == ["p1", "p2"]
    assert contrast["mean_difference_pp"] is None
    assert contrast["ci_low_pp"] is None
    statuses = {row["status"] for row in report["missing_cells"]}
    assert statuses == {"undefined_missing_query_class", "missing_shard"}


def test_paired_query_identity_mismatch_is_not_compared(tmp_path):
    config, tasks = fixture(tmp_path)
    populate(config, tasks)
    save(config, tasks[0], "s2", "head", .6, query_identity="other-trials")
    with pytest.raises(ValueError, match="different query identities"):
        summarize(config)


def test_inconsistent_seed_session_declaration_is_not_averaged(tmp_path):
    config, tasks = fixture(tmp_path)
    tasks[0]["targets"].pop()
    Path(config["tasks_file"]).write_text(json.dumps(tasks))
    with pytest.raises(ValueError, match="same sessions"):
        summarize(config)


def test_classical_primary_and_prespecified_ablations(tmp_path):
    methods = ["ea_csp", "ea_empirical_anchored_csp", "full_csp", "frozen",
               "ea_anchored_csp", "empirical_anchored_csp"]
    config, tasks = fixture(tmp_path, "classical", methods)
    for task in tasks:
        for session in ("s2", "s3"):
            for method in methods:
                save(config, task, session, method, .6 if method == "ea_empirical_anchored_csp" else .5)
        save(config, task, "source", "frozen", .55)
    report = summarize(config)
    assert len(report["comparisons"]) == 5
    primary = [row for row in report["comparisons"] if row["contrast_role"] == "primary"]
    assert len(primary) == 1
    assert primary[0]["reference"] == "ea_csp"
    assert primary[0]["mean_difference_pp"] == pytest.approx(10)
    refs = {row["contrast_role"]: row["reference"] for row in report["comparisons"]}
    assert refs["fixed_anchor_ablation"] == "ea_anchored_csp"
    assert refs["alignment_ablation"] == "empirical_anchored_csp"


def test_source_missingness_and_invalid_class_count(tmp_path):
    config, tasks = fixture(tmp_path)
    populate(config, tasks)
    save(config, tasks[0], "source", "frozen", None, missing_class=True)
    report = summarize(config)
    assert len(report["missing_source_query_cells"]) == 1
    assert report["source_query_participants"][0]["source_query_balanced_accuracy"] is None
    save(config, tasks[0], "s2", "head", .5, missing_class=True)
    with pytest.raises(ValueError, match="missing classes"):
        summarize(config)


def test_real_and_synthetic_results_never_pool(tmp_path):
    config, tasks = fixture(tmp_path)
    tasks[-1]["synthetic"] = False
    Path(config["tasks_file"]).write_text(json.dumps(tasks))
    populate(config, tasks)
    with pytest.raises(ValueError, match="Do not combine"):
        summarize(config)


def test_bootstrap_settings_are_prespecified(tmp_path):
    config, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="10000"):
        summarize(config, repetitions=500)
