"""Participant-unit V3 summaries from saved metrics, never models or EEG.

The discovery matrix and every missing seed/session remain explicit. A cohort
endpoint is unavailable until all declared participants are complete; interim
complete-case means are separately named. Simulated mechanisms stay separate.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from hpc_recalibration.data import atomic_json
from .runtime import complete, load_tasks


BOOTSTRAP_REPETITIONS = 10000
BOOTSTRAP_SEED = 20261023
KEYS = (
    "dataset",
    "family",
    "source_regime",
    "variant",
    "participant",
    "seed",
    "session",
    "method",
    "budget",
)


def _csv(path, records, fields):
    """Keep empty/missing outputs inspectable, including their column names."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    # Reuse the project's same-directory fsync/replace publication policy.
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    with os.fdopen(descriptor, "wb") as output:
        output.write(stream.getvalue().encode())
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def _interval(values):
    if len(values) < 2:
        return None, None
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, len(values), size=(BOOTSTRAP_REPETITIONS, len(values)))
    lower, upper = np.quantile(values[indices].mean(axis=1), [0.025, 0.975])
    return float(lower), float(upper)


def _scope(task):
    return (
        task.get("dataset", "Kumar2024"),
        task["family"],
        task.get("source_regime", "within_subject"),
        task.get("variant", "core"),
    )


def _template(task, session, method, budget, *, imported=False):
    return {
        **dict(zip(KEYS[:4], _scope(task))),
        "participant": task["participant"],
        "seed": str(task.get("seed", "deterministic")),
        "session": session,
        "method": method,
        "budget": budget,
        "task_id": task["task_id"],
        "balanced_accuracy": None,
        "actual_budget": None,
        "n_query": None,
        "status": "missing_file",
        "query_identity": None,
        "metric_sha256": None,
        "synthetic": bool(task.get("synthetic", False)),
        "software_validation_only": bool(task.get("synthetic", False)),
        "imported_reference": imported,
        "reference_alignment_verified": False,
    }


def _read_metric(path, expected, task, *, raw_method=None, raw_task_id=None):
    row = dict(expected)
    row["metric_path"] = str(path)
    if not path.is_file():
        return row
    body = path.read_bytes()
    value = json.loads(body)
    identity = {
        "task_id": raw_task_id or task["task_id"],
        "dataset": row["dataset"],
        "participant": row["participant"],
        "session": row["session"],
        "method": raw_method or row["method"],
    }
    for key, wanted in identity.items():
        if value.get(key) != wanted:
            raise ValueError(f"Saved metric {key} mismatch: {path}")
    if int(value.get("requested_budget", value.get("budget_requested", -1))) != row["budget"]:
        raise ValueError("Saved metric requested budget mismatch: " + str(path))
    if "seed" in value and str(value["seed"]) != row["seed"]:
        raise ValueError("Saved metric seed mismatch: " + str(path))
    if bool(value.get("synthetic", False)) != row["synthetic"]:
        raise ValueError("Do not mix synthetic software checks and real EEG metrics")
    if value.get("query_used_for_fitting") is True or value.get("selection_use") is True:
        raise ValueError("Saved query record reports fitting/selection use: " + str(path))
    scored = value.get("metrics", value)
    count = scored.get("n_query")
    counts = scored.get("class_counts")
    if isinstance(counts, dict):
        if set(counts) != {"0", "1"}:
            raise ValueError("Saved binary query labels differ from0/1: " + str(path))
        counts = [counts["0"], counts["1"]]
    if (
        type(count) is not int
        or count < 0
        or not isinstance(counts, list)
        or len(counts) != 2
        or any(type(n) is not int or n < 0 for n in counts)
        or sum(counts) != count
    ):
        raise ValueError("Saved query class counts are invalid: " + str(path))
    score = scored.get("balanced_accuracy")
    if score is not None and (
        type(score) not in (float, int)
        or not np.isfinite(score)
        or not 0 <= score <= 1
        or any(n == 0 for n in counts)
    ):
        raise ValueError("Saved balanced accuracy is invalid: " + str(path))
    qid = value.get("query_identity")
    if not isinstance(qid, str) or not qid:
        raise ValueError("Saved query identity is missing: " + str(path))
    row.update(
        balanced_accuracy=float(score) if score is not None else None,
        actual_budget=value.get("actual_budget", value.get("n_support_actual", 0)),
        n_query=count,
        query_identity=qid,
        metric_sha256=hashlib.sha256(body).hexdigest(),
        status=(
            "ok"
            if score is not None
            else "undefined_query_class"
            if any(n == 0 for n in counts)
            else "undefined_saved_ba"
        ),
    )
    return row


def _reference_alignment(candidate_path, legacy, row):
    """Compare ordered actual IDs/labels, not incompatible V2/V3 hash schemes."""
    predictions = candidate_path.with_name("predictions.npz")
    if not candidate_path.is_file() or not predictions.is_file():
        row["reference_alignment_status"] = "pending_candidate_predictions"
        return
    with np.load(predictions, allow_pickle=False) as data:
        ids = data["trial_id"].tolist()
        labels = data["labels"].tolist()
    if (
        len(ids) != row["n_query"]
        or len(labels) != row["n_query"]
        or len(ids) != len(set(ids))
        or ids != legacy.get("trial_ids")
        or labels != legacy.get("y")
    ):
        raise ValueError("V2 saved EA reference differs in ordered query IDs/labels")
    row["reference_alignment_verified"] = True
    row["reference_alignment_status"] = "ordered_trial_ids_and_labels_verified"


def _aggregate(cells):
    """Declared seeds -> sessions -> participants; every missing member matters."""
    grouped = {}
    for row in cells:
        key = tuple(row[k] for k in KEYS[:5]) + (row["method"], row["budget"])
        grouped.setdefault(key, []).append(row)
    participants = []
    for key, expected in sorted(grouped.items()):
        by_session = {}
        for row in expected:
            by_session.setdefault(row["session"], []).append(row)
        scores, missing = [], []
        for session, values in sorted(by_session.items()):
            if all(v["status"] == "ok" for v in values):
                scores.append(float(np.mean([v["balanced_accuracy"] for v in values])))
            else:
                missing.append(session)
        participants.append(
            {
                **dict(zip(KEYS[:5], key[:5])),
                "method": key[5],
                "budget": key[6],
                "expected_sessions": len(by_session),
                "available_sessions": len(scores),
                "expected_seed_session_cells": len(expected),
                "available_seed_session_cells": sum(v["status"] == "ok" for v in expected),
                "balanced_accuracy": float(np.mean(scores)) if not missing else None,
                "missing_sessions": ";".join(missing),
            }
        )
    return participants


def _cohorts(participants):
    grouped = {}
    for row in participants:
        key = tuple(row[k] for k in KEYS[:4]) + (row["method"], row["budget"])
        grouped.setdefault(key, []).append(row)
    cohorts = []
    for key, values in sorted(grouped.items()):
        valid = [v for v in values if v["balanced_accuracy"] is not None]
        complete = len(valid) == len(values)
        scores = [v["balanced_accuracy"] for v in valid]
        lower, upper = _interval(scores) if complete else (None, None)
        cohorts.append(
            {
                **dict(zip(KEYS[:4], key[:4])),
                "method": key[4],
                "budget": key[5],
                "expected_participants": len(values),
                "complete_participants": len(valid),
                "mean_balanced_accuracy": float(np.mean(scores)) if complete else None,
                "complete_case_mean_balanced_accuracy": float(np.mean(scores)) if scores else None,
                "ci_low": lower,
                "ci_high": upper,
                "endpoint_complete": complete,
                "incomplete_participants": ";".join(
                    v["participant"] for v in values if v["balanced_accuracy"] is None
                ),
            }
        )
    return cohorts


def _comparisons(participants, cells):
    pindex = {(tuple(r[k] for k in KEYS[:5]), r["method"], r["budget"]): r for r in participants}
    cellindex = {}
    for row in cells:
        key = tuple(row[k] for k in KEYS[:5]) + (row["method"], row["budget"])
        cellindex.setdefault(key, {})[row["seed"], row["session"]] = row
    scopes = sorted({tuple(r[k] for k in KEYS[:4]) for r in participants})
    plans = []
    for scope in scopes:
        dataset, family, regime, variant = scope
        methods = {r["method"] for r in participants if tuple(r[k] for k in KEYS[:4]) == scope}
        budgets = sorted(
            {r["budget"] for r in participants if tuple(r[k] for k in KEYS[:4]) == scope}
        )
        if family == "geometry":
            pairs = [
                ("eb_predictive", "tangent_refit", "prespecified_geometry_primary"),
                ("eb_predictive", "saved_V2_ea_csp", "prespecified_strong_reference"),
                *[
                    ("eb_predictive", m, "descriptive_geometry_ablation")
                    for m in (
                        "source_tangent_frozen",
                        "tangent_pooled",
                        "eb_point",
                        "eb_isotropic",
                        "eb_coupled",
                        "eb_no_source_noise",
                        "eb_no_shift",
                    )
                ],
            ]
            for left, right, role in pairs:
                if left in methods and right in methods:
                    plans.extend((scope, left, scope, right, b, role) for b in budgets)
        elif family == "neural" and variant == "core":
            pairs = [
                ("trust_fixed", "full_fixed", "prespecified_neural_primary"),
                ("full_fixed", "full_adaptive_bn", "descriptive_BN_buffer_contrast"),
                ("full_adaptive_bn_dropout", "full_adaptive_bn", "descriptive_dropout_contrast"),
                *[
                    (m, "frozen", "descriptive_neural_baseline")
                    for m in (
                        "head_fixed",
                        "full_fixed",
                        "trust_fixed",
                        "bn_affine_fixed",
                        "bn_stats_only",
                    )
                ],
            ]
            for left, right, role in pairs:
                if left in methods and right in methods:
                    plans.extend((scope, left, scope, right, b, role) for b in budgets)
        elif family == "neural" and variant != "core" and "trust_fixed" in methods:
            core = dataset, family, regime, "core"
            for right in ("full_fixed", "trust_fixed"):
                plans.extend(
                    (scope, "trust_fixed", core, right, b, "descriptive_KL_dose") for b in budgets
                )
    comparisons = []
    for leftscope, left, rightscope, right, budget, role in plans:
        people = sorted(
            {r["participant"] for r in participants if tuple(r[k] for k in KEYS[:4]) == leftscope}
        )
        gains, omitted, alignment_pending = [], [], []
        for person in people:
            lkey, rkey = (
                (leftscope + (person,), left, budget),
                (rightscope + (person,), right, budget),
            )
            a, b = pindex.get(lkey), pindex.get(rkey)
            if (
                a is None
                or b is None
                or a["balanced_accuracy"] is None
                or b["balanced_accuracy"] is None
            ):
                omitted.append(person)
                continue
            aa = cellindex[lkey[0] + (left, budget)]
            bb = cellindex[rkey[0] + (right, budget)]
            if set(aa) != set(bb):
                raise ValueError("Paired methods declare different seed/session cells")
            pending = False
            for coordinate in aa:
                x, y = aa[coordinate], bb[coordinate]
                if y["imported_reference"]:
                    pending |= not y["reference_alignment_verified"]
                elif x["query_identity"] != y["query_identity"]:
                    raise ValueError("Paired V3 methods differ in saved query identities")
            if pending:
                omitted.append(person)
                alignment_pending.append(person)
                continue
            gains.append(a["balanced_accuracy"] - b["balanced_accuracy"])
        complete = len(gains) == len(people)
        lower, upper = _interval(gains) if complete else (None, None)
        comparisons.append(
            {
                **dict(zip(KEYS[:4], leftscope)),
                "method": left,
                "reference_variant": rightscope[3],
                "reference": right,
                "budget": budget,
                "contrast_role": role if budget == 20 else "descriptive_budget_curve",
                "expected_participants": len(people),
                "paired_participants": len(gains),
                "mean_difference_pp": float(np.mean(gains) * 100) if complete else None,
                "complete_case_mean_difference_pp": float(np.mean(gains) * 100) if gains else None,
                "ci_low_pp": lower * 100 if lower is not None else None,
                "ci_high_pp": upper * 100 if upper is not None else None,
                "negative_participants": sum(v < 0 for v in gains),
                "decline_at_least_5pp": sum(v <= -0.05 for v in gains),
                "endpoint_complete": complete,
                "incomplete_participants": ";".join(omitted),
                "reference_alignment_pending_participants": ";".join(alignment_pending),
            }
        )
    return comparisons


def summarize(config, destination=None):
    tasks = load_tasks(config)
    root = Path(config["output_root"])
    destination = Path(destination) if destination is not None else root / "analysis"
    destination.mkdir(parents=True, exist_ok=True)
    science = config.get("science", {})
    analysis = science.get("analysis", {})
    if (
        analysis.get("bootstrap_repetitions", BOOTSTRAP_REPETITIONS) != BOOTSTRAP_REPETITIONS
        or analysis.get("bootstrap_seed", BOOTSTRAP_SEED) != BOOTSTRAP_SEED
        or analysis.get("primary_budget", 20) != 20
    ):
        raise ValueError("V3 freezes cap20,10000 participant bootstrap draws and seed20261023")
    cells, source_cells, simulated = [], [], []
    role_signatures, seed_declarations = {}, {}
    for task in tasks:
        folder = root / "tasks" / task["task_id"]
        family = task["family"]
        if family == "simulation":
            path = folder / "summary.json"
            if path.is_file():
                value = json.loads(path.read_text())
                if not value.get("synthetic") or not value.get("software_validation_only"):
                    raise ValueError("Mechanism simulations must retain synthetic software flags")
                simulated.extend({"task_id": task["task_id"], **r} for r in value.get("rows", []))
            continue
        if family == "pooled_pretrain":
            continue
        if family not in ("geometry", "neural"):
            raise ValueError("Unknown V3 task family")
        effective = dict(science)
        effective.update(task.get("science_overrides", {}))
        methods = (
            effective.get("geometry_methods", [])
            if family == "geometry"
            else effective.get("neural_methods", [])
        )
        budgets = effective.get("budgets", [4, 8, 12, 16, 20])
        if (
            not methods
            or len(methods) != len(set(methods))
            or not budgets
            or len(budgets) != len(set(budgets))
        ):
            raise ValueError("Declared method/budget lists must be unique and nonempty")
        scope = _scope(task)
        roles = tuple((t["session"], t["support"], t["query"]) for t in task["targets"])
        person_scope = scope + (task["participant"],)
        if person_scope in role_signatures and role_signatures[person_scope] != roles:
            raise ValueError("Seeds declare different support/query session roles")
        role_signatures[person_scope] = roles
        seed_declarations.setdefault(person_scope, []).append(
            str(task.get("seed", "deterministic"))
        )
        for target in task["targets"]:
            for budget in budgets:
                for method in methods:
                    template = _template(task, target["session"], method, budget)
                    if family == "geometry":
                        path = (
                            folder
                            / "evaluation"
                            / f"{target['session']}__n{budget}__{method}"
                            / "metrics.json"
                        )
                    else:
                        path = (
                            folder
                            / "evaluation"
                            / target["session"]
                            / method
                            / f"budget-{budget}"
                            / "metrics.json"
                        )
                    cells.append(_read_metric(path, template, task))
                if (
                    family == "geometry"
                    and task.get("legacy_task_id")
                    and config.get("v2_output_root")
                ):
                    template = _template(
                        task, target["session"], "saved_V2_ea_csp", budget, imported=True
                    )
                    path = (
                        Path(config["v2_output_root"])
                        / "tasks"
                        / task["legacy_task_id"]
                        / "evaluation"
                        / f"{target['session']}__n{budget}__ea_csp.json"
                    )
                    reference = _read_metric(
                        path,
                        template,
                        task,
                        raw_method="ea_csp",
                        raw_task_id=task["legacy_task_id"],
                    )
                    if reference["status"] == "ok":
                        legacy = json.loads(path.read_text())
                        candidate = (
                            folder
                            / "evaluation"
                            / f"{target['session']}__n{budget}__eb_predictive"
                            / "metrics.json"
                        )
                        _reference_alignment(candidate, legacy, reference)
                    cells.append(reference)
        if task.get("source_query"):
            method = "source_tangent_frozen" if family == "geometry" else "frozen"
            template = _template(task, "source", method, 0)
            path = (
                folder / "evaluation/source__n0__source_tangent_frozen/metrics.json"
                if family == "geometry"
                else folder / "source_query.json"
            )
            source_cells.append(_read_metric(path, template, task))
    # A missing declared seed is a missing file, not silently a smaller ensemble.
    by_scope = {}
    people_by_family_regime = {}
    people_by_scope = {}
    seeds_by_family_regime = {}
    for person_scope, seeds in seed_declarations.items():
        if len(seeds) != len(set(seeds)):
            raise ValueError("Duplicate participant/seed declaration")
        scope, seedset = person_scope[:4], tuple(sorted(seeds))
        if scope in by_scope and by_scope[scope] != seedset:
            raise ValueError("Participants declare different seed ensembles")
        by_scope[scope] = seedset
        people_by_scope.setdefault(scope, set()).add(person_scope[4])
        people_by_family_regime.setdefault(scope[:3], set()).add(person_scope[4])
        if scope[:3] in seeds_by_family_regime and seeds_by_family_regime[scope[:3]] != seedset:
            raise ValueError("Variants declare different fixed seed ensembles")
        seeds_by_family_regime[scope[:3]] = seedset
    for scope, people in people_by_scope.items():
        if people != people_by_family_regime[scope[:3]]:
            raise ValueError(
                "Variants declare different participant cohorts; no reduced cohort substituted"
            )
    grain = [tuple(row[k] for k in KEYS) for row in cells]
    if len(grain) != len(set(grain)):
        raise ValueError("Duplicate saved-cell grain")
    flags = {row["synthetic"] for row in cells}
    if len(flags) > 1:
        raise ValueError("Synthetic and real evaluation cohorts must remain separate")
    participants = _aggregate(cells)
    cohorts = _cohorts(participants)
    comparisons = _comparisons(participants, cells)
    missing = [row for row in cells + source_cells if row["status"] != "ok"]
    pending_references = sum(
        row["imported_reference"]
        and row["status"] == "ok"
        and not row["reference_alignment_verified"]
        for row in cells
    )
    completed_tasks = sum(complete(root, task) for task in tasks)
    summary = {
        "experiment_id": config["experiment_id"],
        "scope": "saved_metrics_only_no_model_EEG_fit_or_forward",
        "independent_unit": "participant",
        "aggregation_order": "all declared seeds per participant/session, then all declared target sessions",
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "interval": "pointwise95 participant bootstrap; exploratory, no multiplicity correction",
        "partial_mean_policy": "Official cohort/contrast unavailable until every declared participant completes; interim complete-case means named separately",
        "synthetic": next(iter(flags)) if flags else False,
        "software_validation_only": next(iter(flags)) if flags else False,
        "tasks_expected": len(tasks),
        "tasks_complete": completed_tasks,
        "target_cells_expected": sum(not r["imported_reference"] for r in cells),
        "target_cells_defined": sum(
            r["status"] == "ok" and not r["imported_reference"] for r in cells
        ),
        "imported_reference_cells": sum(r["imported_reference"] for r in cells),
        "reference_alignment_pending_cells": pending_references,
        "source_query_cells_expected": len(source_cells),
        "source_query_cells_defined": sum(r["status"] == "ok" for r in source_cells),
        "missing_cells": missing,
        "partial": bool(missing) or bool(pending_references) or completed_tasks != len(tasks),
        "cohorts": cohorts,
        "comparisons": comparisons,
        "simulation_scope": "separate scenario/method rows, never pooled with EEG participants",
        "simulation_scenario_method_rows": len(simulated),
        "reference_import_does_not_create_new_fit": True,
    }
    cell_fields = list(KEYS) + [
        "task_id",
        "status",
        "balanced_accuracy",
        "actual_budget",
        "n_query",
        "query_identity",
        "metric_path",
        "metric_sha256",
        "synthetic",
        "software_validation_only",
        "imported_reference",
        "reference_alignment_verified",
        "reference_alignment_status",
    ]
    _csv(destination / "saved_cells.csv", cells, cell_fields)
    _csv(destination / "missing_cells.csv", missing, cell_fields)
    _csv(destination / "source_query.csv", source_cells, cell_fields)
    _csv(
        destination / "participant_metrics.csv",
        participants,
        list(participants[0]) if participants else list(KEYS),
    )
    _csv(destination / "cohorts.csv", cohorts, list(cohorts[0]) if cohorts else list(KEYS[:4]))
    _csv(
        destination / "comparisons.csv",
        comparisons,
        list(comparisons[0]) if comparisons else list(KEYS[:4]),
    )
    _csv(
        destination / "simulation_scenarios.csv",
        simulated,
        sorted({k for r in simulated for k in r}) or ["task_id", "method"],
    )
    atomic_json(destination / "summary.json", summary)
    return summary
