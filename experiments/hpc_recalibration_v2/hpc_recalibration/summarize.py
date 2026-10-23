"""Participant-unit summaries of saved V2 metrics; never loads EEG or a model."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

from .preflight import atomic_json, load_config, load_tasks

CLASSICAL_METHODS = ("frozen", "lda_only", "full_csp", "ea_csp", "anchored_csp",
                     "empirical_anchored_csp", "ea_anchored_csp", "ea_empirical_anchored_csp")
NEURAL_METHODS = ("frozen", "head", "full", "l2sp")


def _methods(config, family):
    if family == "classical":
        return config.get("classical_methods", list(CLASSICAL_METHODS))
    return config.get("training", {}).get("methods", config.get("methods", list(NEURAL_METHODS)))


def _budgets(config, family):
    if family == "classical":
        return config.get("budgets", [4, 8, 12, 16, 20])
    return config.get("training", {}).get("budgets", config.get("budgets", [4, 8, 12, 16, 20]))


def _read_cell(root, task, session, method, budget, source=False):
    family = task.get("family", "eegnet")
    path = root / "tasks" / task["task_id"]
    if family == "classical":
        filename = path / "evaluation" / f"{session}__n{budget}__{method}.json"
    elif source:
        filename = path / "source_query.json"
    else:
        filename = path / "evaluation" / session / method / f"budget-{budget}" / "metrics.json"
    row = {"dataset": task["dataset"], "family": family, "participant": task["participant"],
           "seed": str(task.get("seed", "deterministic")), "task_id": task["task_id"],
           "session": session, "method": method, "budget": int(budget),
           "actual_budget": None, "balanced_accuracy": None, "n_query": None,
           "status": "missing_shard", "query_identity": None,
           "synthetic": bool(task.get("synthetic", False)),
           "task_complete": (path / "complete.json").is_file()}
    if not filename.exists():
        if not path.exists():
            row["status"] = "task_not_started"
        elif row["task_complete"]:
            row["status"] = "missing_shard_after_task_complete"
        return row
    raw = filename.read_bytes()
    value = json.loads(raw)
    for key in ("task_id", "dataset", "participant", "session", "method"):
        if value.get(key) != row[key]:
            raise ValueError(f"Saved metric identity mismatch ({key}): {filename}")
    if int(value.get("requested_budget", value.get("budget_requested", -1))) != budget:
        raise ValueError(f"Saved metric budget mismatch: {filename}")
    if "seed" in value and str(value["seed"]) != row["seed"]:
        raise ValueError(f"Saved metric seed mismatch: {filename}")
    if bool(value.get("synthetic", False)) != row["synthetic"]:
        raise ValueError(f"Synthetic/real identity mismatch: {filename}")
    metrics = value.get("metrics", value)
    score = metrics.get("balanced_accuracy")
    if score is not None and (not np.isfinite(score) or not 0 <= score <= 1):
        raise ValueError(f"Invalid saved balanced accuracy: {filename}")
    count = metrics["n_query"]
    if not isinstance(count, int) or count < 0:
        raise ValueError(f"Invalid saved query count: {filename}")
    counts = metrics.get("class_counts", {})
    counts = list(counts.values()) if isinstance(counts, dict) else counts
    if sum(counts) != count or any(not isinstance(n, int) or n < 0 for n in counts):
        raise ValueError(f"Class counts do not sum to n_query: {filename}")
    if score is not None and (len(counts) < 2 or any(n == 0 for n in counts)):
        raise ValueError(f"Defined BA despite missing classes: {filename}")
    row.update(actual_budget=value.get("actual_budget", value.get("n_support_actual", 0)),
               balanced_accuracy=score, n_query=count,
               status="ok" if score is not None else "undefined_missing_query_class",
               query_identity=value.get("query_identity"),
               metric_sha256=hashlib.sha256(raw).hexdigest())
    return row


def _mean_or_none(values):
    return float(np.mean(values)) if values and all(value is not None for value in values) else None


def _interval(values, repetitions, seed):
    if len(values) < 2:
        return [None, None]
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(values), size=(repetitions, len(values)))
    lower, upper = np.quantile(values[samples].mean(axis=1), [0.025, 0.975])
    return [float(lower), float(upper)]


def _write_csv(path, rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as output:
            output.write(stream.getvalue())
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def summarize(config: dict, destination=None, *, repetitions=10000, seed=20261023):
    if repetitions != 10000 or seed != 20261023:
        raise ValueError("This protocol fixes 10000 participant bootstrap draws and seed20261023")
    tasks = load_tasks(config)
    root = Path(config["output_root"])
    destination = Path(destination) if destination else root / "analysis"
    destination.mkdir(parents=True, exist_ok=True)
    cells, source_cells = [], []
    seen = set()
    declared_sessions = {}
    for task in tasks:
        family = task.get("family", "eegnet")
        if family not in ("eegnet", "classical"):
            raise ValueError("Unknown task family")
        scope = (task["dataset"], family, task["participant"])
        sessions = tuple(target["session"] for target in task["targets"])
        if not sessions or len(sessions) != len(set(sessions)):
            raise ValueError("Each task needs distinct declared target sessions")
        roles = (sessions, bool(task.get("source_query")))
        if scope in declared_sessions and declared_sessions[scope] != roles:
            raise ValueError("All seeds of a participant must declare the same sessions and source-query role")
        declared_sessions[scope] = roles
        for target in task["targets"]:
            for budget in _budgets(config, family):
                for method in _methods(config, family):
                    row = _read_cell(root, task, target["session"], method, int(budget))
                    key = tuple(row[key] for key in ("dataset", "family", "participant", "seed",
                                                    "session", "method", "budget"))
                    if key in seen:
                        raise ValueError("Duplicate participant/seed/session/method/budget in task manifest")
                    seen.add(key)
                    cells.append(row)
        if task.get("source_query"):
            source_cells.append(_read_cell(root, task, "source", "frozen", 0, source=True))
    if len({row["synthetic"] for row in cells}) > 1:
        raise ValueError("Do not combine synthetic software checks and real scientific results")
    session_groups = defaultdict(list)
    for row in cells:
        key = tuple(row[key] for key in ("dataset", "family", "participant", "session", "method", "budget"))
        session_groups[key].append(row)
    session_rows = []
    for key, values in sorted(session_groups.items()):
        row = dict(zip(("dataset", "family", "participant", "session", "method", "budget"), key))
        row.update(expected_seeds=len(values), available_seeds=sum(v["status"] == "ok" for v in values),
                   balanced_accuracy=_mean_or_none([v["balanced_accuracy"] for v in values]),
                   missing_cells=sum(v["status"] != "ok" for v in values))
        session_rows.append(row)
    participant_groups = defaultdict(list)
    for row in session_rows:
        key = tuple(row[key] for key in ("dataset", "family", "participant", "method", "budget"))
        participant_groups[key].append(row)
    participant_rows = []
    for key, values in sorted(participant_groups.items()):
        row = dict(zip(("dataset", "family", "participant", "method", "budget"), key))
        row.update(expected_sessions=len(values),
                   available_sessions=sum(v["balanced_accuracy"] is not None for v in values),
                   balanced_accuracy=_mean_or_none([v["balanced_accuracy"] for v in values]),
                   incomplete_sessions=";".join(v["session"] for v in values
                                                if v["balanced_accuracy"] is None))
        participant_rows.append(row)
    cohorts = defaultdict(list)
    for row in participant_rows:
        cohorts[tuple(row[k] for k in ("dataset", "family", "method", "budget"))].append(row)
    cohort_rows = []
    for key, values in sorted(cohorts.items()):
        scores = [row["balanced_accuracy"] for row in values if row["balanced_accuracy"] is not None]
        row = dict(zip(("dataset", "family", "method", "budget"), key))
        lower, upper = _interval(scores, repetitions, seed)
        row.update(expected_participants=len(values), complete_participants=len(scores),
                   mean_balanced_accuracy=float(np.mean(scores)) if scores else None,
                   ci_low=lower, ci_high=upper,
                   incomplete_participants=[v["participant"] for v in values if v["balanced_accuracy"] is None],
                   ci_status="available" if len(scores) >= 2 else "insufficient_participants")
        cohort_rows.append(row)
    # Pair only matched saved query sets within a model family and every seed.
    cell_index = {(r["dataset"], r["family"], r["participant"], r["seed"], r["session"],
                   r["method"], r["budget"]): r for r in cells}
    comparisons = []
    individual = []
    classical_comparisons = [
        ("ea_empirical_anchored_csp", "ea_csp", "primary_at_budget20"),
        ("ea_empirical_anchored_csp", "full_csp", "secondary"),
        ("ea_empirical_anchored_csp", "frozen", "secondary"),
        ("ea_empirical_anchored_csp", "ea_anchored_csp", "fixed_anchor_ablation"),
        ("ea_empirical_anchored_csp", "empirical_anchored_csp", "alignment_ablation"),
    ]
    neural_comparisons = [(m, "frozen", "neural_reference") for m in ("head", "full", "l2sp")]
    scopes = sorted({(r["dataset"], r["family"], r["budget"]) for r in participant_rows})
    for dataset, family, budget in scopes:
        for left, right, label in classical_comparisons if family == "classical" else neural_comparisons:
            if left not in _methods(config, family) or right not in _methods(config, family):
                continue
            left_rows = {r["participant"]: r for r in participant_rows if
                         (r["dataset"], r["family"], r["method"], r["budget"]) == (dataset, family, left, budget)}
            right_rows = {r["participant"]: r for r in participant_rows if
                          (r["dataset"], r["family"], r["method"], r["budget"]) == (dataset, family, right, budget)}
            if not left_rows and not right_rows:
                continue
            eligible, omitted, gains = [], [], []
            for participant in sorted(set(left_rows) | set(right_rows)):
                a, b = left_rows.get(participant), right_rows.get(participant)
                if not a or not b or a["balanced_accuracy"] is None or b["balanced_accuracy"] is None:
                    omitted.append(participant)
                    individual.append({"dataset": dataset, "family": family, "participant": participant,
                                       "method": left, "reference": right, "budget": budget,
                                       "difference_pp": None, "status": "incomplete_pair",
                                       "decline_at_least_5pp": None})
                    continue
                for key, value in cell_index.items():
                    if key[0] == dataset and key[1] == family and key[2] == participant and key[5] == left and key[6] == budget:
                        opposite = cell_index.get(key[:5] + (right, budget))
                        if opposite is None or not value["query_identity"] or value["query_identity"] != opposite["query_identity"]:
                            raise ValueError("Paired methods use missing or different query identities")
                gain = a["balanced_accuracy"] - b["balanced_accuracy"]
                eligible.append(participant)
                gains.append(gain)
                individual.append({"dataset": dataset, "family": family, "participant": participant,
                                   "method": left, "reference": right, "budget": budget,
                                   "difference_pp": gain * 100, "status": "complete_pair",
                                   "decline_at_least_5pp": gain <= -0.05})
            low, high = _interval(gains, repetitions, seed)
            comparisons.append({"dataset": dataset, "family": family, "method": left,
                "reference": right, "budget": budget,
                "contrast_role": "primary" if label == "primary_at_budget20" and budget == 20
                                 else "descriptive_budget_curve" if label == "primary_at_budget20" else label,
                "expected_participants": len(set(left_rows) | set(right_rows)),
                "paired_participants": len(gains), "included_participants": eligible,
                "incomplete_participants": omitted,
                "mean_difference_pp": float(np.mean(gains) * 100) if gains else None,
                "ci_low_pp": low * 100 if low is not None else None,
                "ci_high_pp": high * 100 if high is not None else None,
                "negative_participants": sum(gain < 0 for gain in gains),
                "decline_at_least_5pp_participants": sum(gain <= -0.05 for gain in gains),
                "ci_status": "available" if len(gains) >= 2 else "insufficient_participants"})
    source_groups = defaultdict(list)
    for row in source_cells:
        source_groups[tuple(row[k] for k in ("dataset", "family", "participant"))].append(row)
    source_rows = []
    for key, values in sorted(source_groups.items()):
        source_rows.append(dict(zip(("dataset", "family", "participant"), key)) |
                           {"expected_seeds": len(values),
                            "available_seeds": sum(v["status"] == "ok" for v in values),
                            "source_query_balanced_accuracy": _mean_or_none([v["balanced_accuracy"] for v in values]),
                            "selection_use": False})
    summary = {"experiment_id": config["experiment_id"], "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "saved_predictions_metrics_only_no_forward_no_fit", "independent_unit": "participant",
        "aggregation_order": "all prespecified seeds per participant/session, then all prespecified target sessions per participant",
        "bootstrap_repetitions": repetitions, "bootstrap_seed": seed,
        "interval": "pointwise percentile95 participant bootstrap; exploratory, no multiplicity correction",
        "missingness_policy": "Any missing seed/session/class makes that participant endpoint unavailable; every omission listed",
        "negative_threshold_note": "A decline of at least 5 percentage points is descriptive, not a clinical threshold",
        "synthetic": bool(cells and cells[0]["synthetic"]),
        "software_validation_only": bool(cells and cells[0]["synthetic"]),
        "tasks_expected": len(tasks), "tasks_complete": sum((root / "tasks" / t["task_id"] / "complete.json").is_file() for t in tasks),
        "cells_expected": len(cells), "cells_with_defined_ba": sum(r["status"] == "ok" for r in cells),
        "missing_cells": [{k: row[k] for k in ("task_id", "dataset", "family", "participant", "seed", "session", "method", "budget", "status")}
                          for row in cells if row["status"] != "ok"],
        "missing_source_query_cells": [row for row in source_cells if row["status"] != "ok"],
        "cohorts": cohort_rows, "comparisons": comparisons, "source_query_participants": source_rows}
    _write_csv(destination / "saved_cells.csv", cells + source_cells,
               ["dataset", "family", "participant", "seed", "task_id", "session", "method", "budget",
                "actual_budget", "balanced_accuracy", "n_query", "status", "query_identity", "metric_sha256",
                "synthetic", "task_complete"])
    _write_csv(destination / "session_metrics.csv", session_rows,
               ["dataset", "family", "participant", "session", "method", "budget", "expected_seeds", "available_seeds", "balanced_accuracy", "missing_cells"])
    _write_csv(destination / "participant_metrics.csv", participant_rows,
               ["dataset", "family", "participant", "method", "budget", "expected_sessions", "available_sessions", "balanced_accuracy", "incomplete_sessions"])
    _write_csv(destination / "participant_differences.csv", individual,
               ["dataset", "family", "participant", "method", "reference", "budget", "difference_pp", "status", "decline_at_least_5pp"])
    _write_csv(destination / "comparisons.csv", comparisons,
               ["dataset", "family", "method", "reference", "budget", "contrast_role", "expected_participants", "paired_participants", "mean_difference_pp", "ci_low_pp", "ci_high_pp", "negative_participants", "decline_at_least_5pp_participants", "ci_status"])
    _write_csv(destination / "source_query.csv", source_rows,
               ["dataset", "family", "participant", "expected_seeds", "available_seeds", "source_query_balanced_accuracy", "selection_use"])
    _write_csv(destination / "missing_cells.csv", summary["missing_cells"],
               ["task_id", "dataset", "family", "participant", "seed", "session", "method", "budget", "status"])
    atomic_json(destination / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = summarize(load_config(args.config), args.output)
    print(json.dumps({"tasks_expected": result["tasks_expected"], "tasks_complete": result["tasks_complete"],
                      "cells_expected": result["cells_expected"], "cells_with_defined_ba": result["cells_with_defined_ba"]}))


if __name__ == "__main__":
    main()
