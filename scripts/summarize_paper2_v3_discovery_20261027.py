#!/usr/bin/env python3
"""Reconstruct V3 participant endpoints and contrasts from saved result tables.

No EEG, checkpoint, fitting or forward pass is used. The original experiment's
participant order, 10,000 percentile bootstrap resamples and seed are retained.
New contrasts are labelled as exploratory rather than promoted to endpoints.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

PARTICIPANTS = tuple(sorted(("sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16")))
SESSIONS = {f"ses-{i}" for i in range(1, 6)}
SEEDS = {"20261023", "20261024", "20261025"}
BUDGETS = (4, 8, 12, 16, 20)
GROUP = ("family", "source_regime", "variant", "method", "budget")


def read_csv(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    if not rows:
        raise ValueError("An empty table cannot be presented as complete")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def interval(values):
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (len(PARTICIPANTS),) or not np.isfinite(values).all():
        raise ValueError("The complete six-participant endpoint is required")
    indices = np.random.default_rng(20261023).integers(0, len(values), (10000, len(values)))
    return tuple(float(x) for x in np.quantile(values[indices].mean(1), (0.025, 0.975)))


def aggregate(rows):
    """Average seeds within sessions, then five sessions within participants."""
    grouped = defaultdict(lambda: defaultdict(dict))
    unique = set()
    for row in rows:
        if row["status"] != "ok" or row["synthetic"] != "False":
            raise ValueError("Incomplete/synthetic EEG cell retained; endpoint unavailable")
        participant, session, seed = (row[k] for k in ("participant", "session", "seed"))
        if participant not in PARTICIPANTS or session not in SESSIONS:
            raise ValueError("Unexpected participant or target session")
        key = tuple(row[k] if k != "budget" else int(row[k]) for k in GROUP)
        uid = key + (participant, session, seed)
        if uid in unique:
            raise ValueError("Duplicate saved endpoint cell")
        unique.add(uid)
        value = float(row["balanced_accuracy"])
        if not np.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid balanced accuracy")
        grouped[key + (participant,)][session][seed] = value
    endpoints, session_rows = {}, []
    for key, sessions in grouped.items():
        if set(sessions) != SESSIONS:
            raise ValueError("A participant has an incomplete five-session endpoint")
        wanted = SEEDS if key[0] == "neural" else {"deterministic"}
        if any(set(scores) != wanted for scores in sessions.values()):
            raise ValueError("Missing/extra seed; do not use complete-case substitution")
        values = []
        for session, scores in sorted(sessions.items()):
            value = float(np.mean([scores[seed] for seed in sorted(scores)]))
            values.append(value)
            session_rows.append(dict(zip(GROUP + ("participant", "session", "balanced_accuracy"),
                                         key + (session, value))))
        endpoints[key] = float(np.mean(values))
    methods = {key[:-1] for key in endpoints}
    for method in methods:
        if {key[-1] for key in endpoints if key[:-1] == method} != set(PARTICIPANTS):
            raise ValueError("An incomplete participant cohort cannot be summarized")
    return endpoints, session_rows


def contrast(endpoints, method, reference, role):
    left = np.array([endpoints[method + (p,)] for p in PARTICIPANTS])
    right = np.array([endpoints[reference + (p,)] for p in PARTICIPANTS])
    values = (left - right) * 100
    low, high = interval(values)
    return {
        "family": method[0], "source_regime": method[1], "variant": method[2],
        "method": method[3], "budget": method[4], "reference_regime": reference[1],
        "reference_variant": reference[2], "reference": reference[3], "contrast_role": role,
        "n_participants": len(values), "mean_difference_pp": float(values.mean()),
        "ci_low_pp": low, "ci_high_pp": high,
        "positive_participants": int((values > 1e-12).sum()),
        "negative_participants": int((values < -1e-12).sum()),
        "ties": int((abs(values) <= 1e-12).sum()),
        "minimum_participant_difference_pp": float(values.min()),
        "maximum_participant_difference_pp": float(values.max()),
        "declines_at_least_5pp": int((values <= -5).sum()),
        "leave_one_out_min_pp": float(min(np.delete(values, i).mean() for i in range(len(values)))),
        "leave_one_out_max_pp": float(max(np.delete(values, i).mean() for i in range(len(values)))),
        "pointwise_exploratory_interval": True,
    }


def analyze(results_root, output_root):
    results_root, output_root = Path(results_root), Path(output_root)
    analysis = results_root / "analysis"
    rows = read_csv(analysis / "saved_cells.csv")
    endpoints, sessions = aggregate(rows)
    methods = sorted({key[:-1] for key in endpoints})
    participant_rows = [dict(zip(GROUP + ("participant", "balanced_accuracy"), key + (value,)))
                        for key, value in sorted(endpoints.items())]
    cohort_rows = []
    for method in methods:
        values = [endpoints[method + (p,)] for p in PARTICIPANTS]
        low, high = interval(values)
        cohort_rows.append({**dict(zip(GROUP, method)), "n_participants": 6,
                            "mean_balanced_accuracy": float(np.mean(values)),
                            "ci_low": low, "ci_high": high})
    # Check every original saved participant endpoint, not only favorable rows.
    previous = read_csv(analysis / "participant_metrics.csv")
    discrepancies = []
    for row in previous:
        key = tuple(row[k] if k != "budget" else int(row[k]) for k in GROUP) + (row["participant"],)
        discrepancies.append(abs(endpoints[key] - float(row["balanced_accuracy"])))
    if len(previous) != len(endpoints) or max(discrepancies, default=1) > 1e-12:
        raise ValueError("Saved participant summary was not independently reproduced")
    comparisons = []
    # Complete within-condition matrix: no selecting one winner after return.
    for scope in sorted({method[:3] + (method[4],) for method in methods}):
        family, regime, variant, budget = scope
        group = [method for method in methods if method[:3] == scope[:3] and method[4] == budget]
        for left, right in itertools.combinations(group, 2):
            comparisons.append(contrast(endpoints, left, right, "post_return_complete_pairwise_matrix"))
    priority = []
    geometry_methods = {m[3] for m in methods if m[0] == "geometry"}
    for budget in BUDGETS:
        candidate = ("geometry", "within_subject", "core", "eb_predictive", budget)
        for reference in sorted(geometry_methods - {"eb_predictive"}):
            role = ("frozen_geometry_primary" if budget == 20 and reference == "tangent_refit"
                    else "frozen_strong_reference" if budget == 20 and "v2" in reference
                    else "exploratory_geometry_control_or_budget")
            priority.append(contrast(endpoints, candidate,
                                      ("geometry", "within_subject", "core", reference, budget), role))
        for regime in ("reuse_v2", "pooled_source"):
            def key(method, variant="core"):
                return ("neural", regime, variant, method, budget)
            priority.append(contrast(endpoints, key("trust_fixed"), key("full_fixed"),
                                      "frozen_neural_primary" if budget == 20 else "frozen_neural_budget_curve"))
            priority.append(contrast(endpoints, key("full_fixed"), key("full_adaptive_bn"),
                                      "exploratory_controlled_BN_mode"))
            priority.append(contrast(endpoints, key("full_adaptive_bn_dropout"), key("full_adaptive_bn"),
                                      "exploratory_controlled_dropout"))
            for variant in ("kl0p001", "kl0p1"):
                priority.append(contrast(endpoints, key("trust_fixed", variant), key("full_fixed"),
                                          "frozen_exploratory_KL_dose"))
        for method in ("frozen", "head_fixed", "full_fixed", "full_adaptive_bn", "full_adaptive_bn_dropout",
                       "bn_affine_fixed", "bn_stats_only", "trust_fixed"):
            priority.append(contrast(endpoints, ("neural", "pooled_source", "core", method, budget),
                                      ("neural", "reuse_v2", "core", method, budget),
                                      "exploratory_source_condition_different_source_label_budget"))
    # Independently reconstruct all original published paired contrasts.
    original = read_csv(analysis / "comparisons.csv")
    differences = []
    for row in original:
        budget = int(row["budget"])
        left = (row["family"], row["source_regime"], row["variant"], row["method"], budget)
        right = (row["family"], row["source_regime"], row["reference_variant"], row["reference"], budget)
        fresh = contrast(endpoints, left, right, row["contrast_role"])
        differences.extend(abs(fresh[key] - float(row[key]))
                           for key in ("mean_difference_pp", "ci_low_pp", "ci_high_pp"))
    if max(differences, default=1) > 1e-10:
        raise ValueError("The frozen contrast table did not reproduce")
    output_root.mkdir(parents=True, exist_ok=True)
    for name, table in (("participant_endpoints.csv", participant_rows),
                        ("session_endpoints.csv", sessions), ("cohort_endpoints.csv", cohort_rows),
                        ("complete_pairwise_contrasts.csv", comparisons),
                        ("frozen_and_mechanism_contrasts.csv", priority)):
        write_csv(output_root / name, table)
    provenance = [{"file": path.name, "bytes": path.stat().st_size,
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in sorted(analysis.glob("*")) if path.is_file()]
    report = {
        "scope": "Saved-result postprocessing; no fit, inference, checkpoint or EEG load",
        "experiment_id": "paper2-kumar-discovery-v3-20261026",
        "source_result_commit": "500831c086d9e1d1e8412cf8ebca5fb6a288db76",
        "packet_id": "83cbdfdcfa541b3ab3addfc3",
        "archive_sha256": "e509c2591efa21fff4dd47236e613ed6b611ca10ad20bac3da37e66e34a9d170",
        "participants": list(PARTICIPANTS), "independent_unit": "participant",
        "bootstrap_repetitions": 10000, "bootstrap_seed": 20261023,
        "interval_scope": "pointwise exploratory, no multiplicity-adjusted confirmation",
        "seed_session_aggregation": "seed mean within session; equal mean of five sessions; equal participants",
        "saved_target_rows_including_imported_V2_reference": len(rows),
        "participant_endpoints": len(endpoints), "cohort_endpoints": len(cohort_rows),
        "original_participant_summary_max_difference": max(discrepancies),
        "original_comparisons_recomputed": len(original),
        "original_contrast_or_CI_max_difference_pp": max(differences),
        "all_pairwise_contrasts": len(comparisons), "priority_contrasts": len(priority),
        "input_tables": provenance,
    }
    (output_root / "RECONSTRUCTION.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.results_root, args.output_root), indent=2))
