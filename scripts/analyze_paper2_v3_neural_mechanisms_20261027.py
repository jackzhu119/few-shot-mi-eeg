#!/usr/bin/env python3
"""Reproduce V3 neural mechanisms from saved text metrics and predictions only.

No EEG, Torch, checkpoints, model forward, fitting or query-based selection is
performed. Seeds -> sessions -> participants; all six exposed participants and
all frozen budgets/doses are retained. Intervals are exploratory and pointwise.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path, PurePosixPath

import numpy as np


BOOTSTRAP_SEED = 20261023
BOOTSTRAP_REPETITIONS = 10000
REGIMES = ("reuse_v2", "pooled_source")
BUDGETS = (4, 8, 12, 16, 20)
DELTA = {"core": 0.01, "kl0p001": 0.001, "kl0p1": 0.1}


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def statistics(values):
    values = np.asarray(values, dtype=np.float64)
    if len(values) != 6 or not np.isfinite(values).all():
        raise ValueError("This frozen report requires six finite participant endpoints")
    indices = np.random.default_rng(BOOTSTRAP_SEED).integers(
        0, len(values), (BOOTSTRAP_REPETITIONS, len(values))
    )
    lower, upper = np.quantile(values[indices].mean(axis=1), [0.025, 0.975])
    leave_one_out = [np.delete(values, i).mean() for i in range(len(values))]
    return {
        "mean": float(values.mean()), "ci_low": float(lower), "ci_high": float(upper),
        "participants": len(values), "positive": int((values > 1e-12).sum()),
        "negative": int((values < -1e-12).sum()),
        "tie_within_1e_minus12": int((np.abs(values) <= 1e-12).sum()),
        "min": float(values.min()), "max": float(values.max()),
        "leave_one_out_min": float(min(leave_one_out)),
        "leave_one_out_max": float(max(leave_one_out)),
    }


def metric_path(root, row):
    task = row["task_id"]
    prefix = "/tasks/" + task + "/"
    if prefix not in row["metric_path"]:
        raise ValueError("Saved metric path does not match task identity")
    relative = PurePosixPath(row["metric_path"].split(prefix, 1)[1])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe saved metric relative path")
    path = root / "tasks" / task / relative
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != row["metric_sha256"]:
        raise ValueError("Saved CSV and metric bytes differ: " + str(path))
    return path, json.loads(body)


def analyze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    cells = [r for r in read_csv(root / "analysis/saved_cells.csv") if r["family"] == "neural"]
    if len(cells) != 9000 or any(r["status"] != "ok" for r in cells):
        raise ValueError("Expected all 9,000 frozen neural target cells")
    participants = sorted({r["participant"] for r in cells})
    if len(participants) != 6:
        raise ValueError("Participant set differs from frozen discovery cohort")

    # Independently aggregate saved seed cells rather than treating seeds as people.
    seed_groups = defaultdict(list)
    metrics = {}
    for row in cells:
        path, value = metric_path(root, row)
        if value.get("query_used_for_fitting") or value.get("selection_use"):
            raise ValueError("Saved metric reports query fitting/selection")
        if value.get("synthetic") or not value.get("inference_state_unchanged"):
            raise ValueError("Expected real EEG evaluation with unchanged inference state")
        key = (row["source_regime"], row["variant"], row["method"], int(row["budget"]),
               row["participant"], row["session"])
        seed_groups[key].append(float(row["balanced_accuracy"]))
        full_key = key[:5] + (row["seed"], key[-1])
        if full_key in metrics:
            raise ValueError("Duplicate neural metric identity")
        metrics[full_key] = (row, value, path)
    if any(len(v) != 3 for v in seed_groups.values()):
        raise ValueError("Every neural session endpoint must contain all three fixed seeds")
    session_values = {k: float(np.mean(v)) for k, v in seed_groups.items()}
    groups = defaultdict(list)
    for key, value in session_values.items():
        groups[key[:5]].append(value)
    if any(len(v) != 5 for v in groups.values()):
        raise ValueError("Every participant endpoint must contain all five target sessions")
    endpoints = {k: float(np.mean(v)) for k, v in groups.items()}
    published = [r for r in read_csv(root / "analysis/participant_metrics.csv")
                 if r["family"] == "neural"]
    for row in published:
        key = (row["source_regime"], row["variant"], row["method"],
               int(row["budget"]), row["participant"])
        if abs(endpoints[key] - float(row["balanced_accuracy"])) > 1e-12:
            raise ValueError("Independent participant aggregation differs from saved summary")

    participant_rows = [dict(source_regime=k[0], variant=k[1], method=k[2], budget=k[3],
                             participant=k[4], balanced_accuracy=v)
                        for k, v in sorted(endpoints.items())]
    cohort_rows = []
    for key in sorted({k[:4] for k in endpoints}):
        cohort_rows.append(dict(source_regime=key[0], variant=key[1], method=key[2], budget=key[3],
                                unit="percentage_points_BA", **statistics(
                                    [100 * endpoints[key + (p,)] for p in participants])))

    contrasts, paired_rows = [], []
    for row in read_csv(root / "analysis/comparisons.csv"):
        if row["family"] != "neural":
            continue
        reg, var, method, budget = (row["source_regime"], row["variant"], row["method"], int(row["budget"]))
        rv, reference = row["reference_variant"], row["reference"]
        values = [100 * (endpoints[reg, var, method, budget, p]
                         - endpoints[reg, rv, reference, budget, p]) for p in participants]
        stats = statistics(values)
        if abs(stats["mean"] - float(row["mean_difference_pp"])) > 1e-10:
            raise ValueError("Independent frozen contrast differs from saved summary")
        ident = dict(source_regime=reg, variant=var, method=method, reference_variant=rv,
                     reference=reference, budget=budget, contrast_role=row["contrast_role"])
        contrasts.append({**ident, **stats})
        paired_rows.extend({**ident, "participant": p, "difference_pp": v}
                           for p, v in zip(participants, values))

    source_condition = []
    for method in sorted({k[2] for k in endpoints if k[1] == "core"}):
        for budget in BUDGETS:
            values = [100 * (endpoints["pooled_source", "core", method, budget, p]
                             - endpoints["reuse_v2", "core", method, budget, p])
                      for p in participants]
            source_condition.append(dict(method=method, budget=budget,
                                         contrast="pooled_minus_reuse_different_source_label_budgets",
                                         **statistics(values)))

    source_query = []
    sources = [r for r in read_csv(root / "analysis/source_query.csv") if r["family"] == "neural"]
    for reg in REGIMES:
        values = []
        for participant in participants:
            rows = [r for r in sources if r["source_regime"] == reg and r["participant"] == participant]
            if len(rows) != 3:
                raise ValueError("Expected three source-query seeds")
            values.append(100 * np.mean([float(r["balanced_accuracy"]) for r in rows]))
        source_query.append(dict(source_regime=reg, **statistics(values)))

    diagnostic_groups = defaultdict(list)
    for key, (_, value, _) in metrics.items():
        diagnostic_groups[key[:4]].append(value)
    diagnostics = []
    for key, values in sorted(diagnostic_groups.items()):
        row = dict(source_regime=key[0], variant=key[1], method=key[2], budget=key[3],
                   cells=len(values), collapse=sum(v["collapse"] for v in values),
                   inference_unchanged=all(v["inference_state_unchanged"] for v in values))
        for name, nested in (("source_anchor_kl", False), ("optimizer_steps", False),
                             ("bn_batches_changed", True), ("bn_buffer_update_rms", True),
                             ("parameter_update_rms", True)):
            numbers = [v.get("diagnostics", {}).get(name) if nested else v.get(name) for v in values]
            numbers = [float(v) for v in numbers if v is not None]
            if numbers:
                row.update({name + "_min": min(numbers), name + "_max": max(numbers),
                            name + "_mean": float(np.mean(numbers))})
        diagnostics.append(row)

    histories, pooled_histories = [], []
    for task in sorted((root / "tasks").iterdir()):
        if task.name.startswith("v3-pooled-source-"):
            value = json.loads((task / "source/training_history.json").read_text())
            pooled_histories.append(dict(task_id=task.name, best_epoch=value["best_epoch"],
                                         best_validation_loss=value["best_validation_loss"],
                                         epochs=value["epoch"], optimizer_steps=value["step"],
                                         first_epoch=value["history"][0], last_epoch=value["history"][-1]))
            continue
        if not task.name.startswith(("v3-reuse_v2-", "v3-pooled_source-")):
            continue
        reg = "reuse_v2" if "reuse_v2" in task.name else "pooled_source"
        var = "kl0p001" if task.name.endswith("kl0p001") else "kl0p1" if task.name.endswith("kl0p1") else "core"
        for path in sorted(task.glob("adaptation/**/training_history.json")):
            value = json.loads(path.read_text())
            relative = path.relative_to(task / "adaptation").parts
            history = value.get("history") or [{}]
            last = history[-1]
            row = dict(task_id=task.name, source_regime=reg, variant=var, session=relative[0],
                       method=relative[1], budget=int(relative[2].removeprefix("budget-")),
                       epoch=value.get("epoch"), accepted_optimizer_steps=value.get("step", 0),
                       proposed_optimizer_steps=value.get("proposal_count", 0),
                       rejected_proposals=value.get("rejected_proposals", 0),
                       backtracking_trials=value.get("backtracking_trials", 0),
                       source_anchor_kl=value.get("source_anchor_kl"),
                       first_train_loss=history[0].get("train_loss"), last_train_loss=last.get("train_loss"),
                       **value.get("diagnostics", {}))
            histories.append(row)

    paired_modes, kl_diagnostics = [], []
    for reg in REGIMES:
        for var, delta in DELTA.items():
            keys = sorted(k for k in metrics if k[:3] == (reg, var, "trust_fixed"))
            states = hard_same = label_changes = total_rows = 0
            maximum_probability_difference = 0.0
            final_kl = []
            for key in keys:
                _, candidate, candidate_path = metrics[key]
                _, reference, reference_path = metrics[(reg, "core", "full_fixed", *key[3:])]
                states += candidate["model_state_sha256"] == reference["model_state_sha256"]
                final_kl.append(float(candidate["source_anchor_kl"]))
                with np.load(candidate_path.with_name("predictions.npz"), allow_pickle=False) as left, np.load(
                        reference_path.with_name("predictions.npz"), allow_pickle=False) as right:
                    if not np.array_equal(left["trial_id"], right["trial_id"]) or not np.array_equal(
                            left["labels"], right["labels"]):
                        raise ValueError("Trust/full-fixed prediction identities differ")
                    a, b = left["probabilities"], right["probabilities"]
                    changes = np.argmax(a, axis=1) != np.argmax(b, axis=1)
                    hard_same += not changes.any()
                    label_changes += int(changes.sum())
                    total_rows += len(changes)
                    maximum_probability_difference = max(maximum_probability_difference, float(np.max(np.abs(a - b))))
            paired_modes.append(dict(source_regime=reg, variant=var, paired_cells=len(keys),
                                     identical_model_states=int(states),
                                     identical_query_label_vectors=int(hard_same), changed_label_rows=label_changes,
                                     repeated_query_rows=total_rows,
                                     max_probability_difference=maximum_probability_difference))
            fits = [h for h in histories if h["source_regime"] == reg and h["variant"] == var
                    and h["method"] == "trust_fixed"]
            kl_diagnostics.append(dict(source_regime=reg, variant=var, delta=delta, fits=len(fits),
                                       final_kl_max=max(final_kl),
                                       final_kl_violations=sum(v > delta + 1e-7 for v in final_kl),
                                       **{name: sum(h[name] for h in fits) for name in
                                          ("accepted_optimizer_steps", "proposed_optimizer_steps",
                                           "rejected_proposals", "backtracking_trials")}))

    session_bn = []
    for reg in REGIMES:
        for session in ("ses-1", "ses-2", "ses-3", "ses-4", "ses-5"):
            values = [100 * (session_values[reg, "core", "full_fixed", 20, p, session]
                             - session_values[reg, "core", "full_adaptive_bn", 20, p, session])
                      for p in participants]
            session_bn.append(dict(source_regime=reg, session=session, budget=20, **statistics(values)))

    metadata = dict(scope="saved_metrics_and_predictions_only_no_models_EEG_fit_or_forward",
                    independent_unit="participant", participants=participants,
                    aggregation="three seeds then five sessions within participant",
                    bootstrap_seed=BOOTSTRAP_SEED, bootstrap_repetitions=BOOTSTRAP_REPETITIONS,
                    interval="exploratory pointwise95 participant bootstrap; no multiplicity correction",
                    shared_source_limitation="Pooled models shared across six participants; intervals conditional on fitted teachers",
                    source_information="reuse40TRAIN/20validation per teacher; pooled240TRAIN/120validation",
                    bn_interpretation="Training-time normalization and running-buffer updates change together; batch16 means two batches at cap20 and one at caps<=16",
                    actual_neural_target_cells=len(cells), adaptation_history_count=len(histories))
    save_json(output / "neural_findings.json", dict(**metadata, cohorts=cohort_rows, contrasts=contrasts,
              source_condition_contrasts=source_condition, source_query=source_query,
              metric_diagnostics=diagnostics, source_training_history=pooled_histories))
    save_json(output / "neural_mechanism.json", dict(**metadata, paired_modes=paired_modes,
              kl_diagnostics=kl_diagnostics, session_bn=session_bn))
    for name, rows in (("neural_participants", participant_rows), ("neural_cohorts", cohort_rows),
                       ("neural_contrasts", contrasts), ("neural_paired_differences", paired_rows),
                       ("source_condition_contrasts", source_condition), ("neural_metric_diagnostics", diagnostics),
                       ("adaptation_history_diagnostics", histories), ("neural_session_bn", session_bn)):
        write_csv(output / (name + ".csv"), rows)
    print(json.dumps(dict(output_root=str(output), participants=len(participants), target_cells=len(cells),
                          cohorts=len(cohort_rows), contrasts=len(contrasts), histories=len(histories),
                          query_inference_executed=False, training_executed=False), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.results_root.resolve(), args.output_root.resolve())


if __name__ == "__main__":
    main()
