"""Rebuild full-precision participant summaries from new per-cell receipts only."""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = OUT / "run01"
METHODS = ("full", "rms_full", "diagonal_ea", "ea")
DEV = {1, 4, 7, 10, 13, 16}
METRICS = ("balanced_accuracy", "weak_recall", "recall_gap", "recall_left", "recall_right",
           "balanced_nll", "balanced_brier_single_coordinate")


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def interval(values):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return None, None
    rng = np.random.default_rng(20261104)
    means = values[rng.integers(len(values), size=(10000, len(values)))].mean(axis=1)
    return np.quantile(means, [.025, .975], method="linear").tolist()


def cohorts(dataset, subject):
    if dataset == "bnci":
        return ["bnci9"]
    return ["kumar_development6" if int(subject.split("-")[-1]) in DEV else "kumar_primary12", "kumar_all18"]


def numerical(subject):
    return int(subject.split("-")[-1])


def main():
    if not (RUN / "execution_receipt.json").exists():
        raise RuntimeError("Actual execution must finish before the full cohort summary")
    records = [json.loads(p.read_text()) for p in sorted((RUN / "cells").glob("*.json"))]
    groups = defaultdict(list)
    phase = []
    for row in records:
        c = row["context"]
        if c["dataset"] == "kumar_phase":
            phase.append(row)
        elif row["status"] == "complete":
            groups[(c["dataset"], c["subject"], c["method"])].append(row)
    participant = []
    for (dataset, subject, method), cells in sorted(groups.items()):
        expected = 5 if dataset == "kumar" else 1
        if len(cells) != expected:
            raise ValueError("Incomplete mechanism participant endpoint")
        for cohort in cohorts(dataset, subject):
            participant.append({"dataset": dataset, "cohort": cohort, "subject": subject,
                "method": method, "n_sessions": len(cells),
                **{m: float(np.mean([c["metrics"][m] for c in cells])) for m in METRICS}})
    summaries, comparisons = [], []
    for dataset, cohort in sorted({(r["dataset"], r["cohort"]) for r in participant}):
        group = [r for r in participant if (r["dataset"], r["cohort"]) == (dataset, cohort)]
        members = sorted({r["subject"] for r in group}, key=numerical)
        lookup = {(r["subject"], r["method"]): r for r in group}
        for method in METHODS:
            for metric in METRICS:
                values = [lookup[(s, method)][metric] for s in members]
                low, high = interval(values)
                summaries.append({"dataset": dataset, "cohort": cohort, "method": method, "metric": metric,
                                  "n": len(members), "mean": float(np.mean(values)), "ci_low": low, "ci_high": high})
        for i, left in enumerate(METHODS):
            for right in METHODS[:i]:
                for metric in METRICS:
                    values = np.asarray([lookup[(s, left)][metric] - lookup[(s, right)][metric] for s in members])
                    low, high = interval(values)
                    rate = metric not in {"balanced_nll", "balanced_brier_single_coordinate"}
                    comparisons.append({"dataset": dataset, "cohort": cohort, "contrast": left + "_minus_" + right,
                        "metric": metric, "n": len(values), "mean_difference": float(values.mean()),
                        "ci_low": low, "ci_high": high,
                        "mean_difference_pp": float(values.mean() * 100) if rate else None,
                        "ci_low_pp": low * 100 if rate else None, "ci_high_pp": high * 100 if rate else None,
                        "unit": "proportion; display pp" if rate else ("nats" if metric == "balanced_nll" else "squared probability"),
                        "n_positive": int(np.sum(values > 1e-12)), "n_zero": int(np.sum(np.abs(values) <= 1e-12)),
                        "n_negative": int(np.sum(values < -1e-12)), "minimum": float(values.min()),
                        "maximum": float(values.max()), "bootstrap_seed": 20261104,
                        "interval_identity": "new_descriptive_pointwise_participant_bootstrap"})
    write_csv(OUT / "participant_metrics.csv", participant)
    write_csv(OUT / "cohort_means.csv", summaries)
    write_csv(OUT / "cohort_comparisons.csv", comparisons)
    with gzip.open(ROOT / "research_logs/paper2_structure_revision_20261029/component_replay/input/phase/metrics.csv.gz", "rt") as f:
        old = {(r["subject"], r["session"], r["window"]): r for r in csv.DictReader(f) if r["method"] == "refit_csp_lda"}
    phase_subjects, phase_cohorts = [], []
    for subject in sorted({r["context"]["subject"] for r in phase}, key=numerical):
        for window in ["cue5s", "task2s"]:
            cells = [r for r in phase if (r["context"]["subject"], r["context"]["window"]) == (subject, window)]
            if len(cells) != 5:
                raise ValueError("Missing defined/undefined phase inventory")
            valid = [r for r in cells if r["status"] == "complete"]
            complete = len(valid) == 5
            base = {"dataset": "kumar", "subject": subject, "window": window,
                    "cohort": cohorts("kumar", subject)[0], "n_defined_sessions": len(valid),
                    "status": "complete" if complete else "undefined_incomplete_five_session_endpoint",
                    "query_metadata_complete_all_sessions": all(int(old[(subject, r["context"]["session"], window)]["n_unknown_query_phase"]) == 0 for r in cells),
                    "full_balanced_accuracy": None, "ea_balanced_accuracy": None, "ea_minus_full": None}
            if complete:
                full = float(np.mean([r["historical_reference_metrics"]["balanced_accuracy"] for r in valid]))
                ea = float(np.mean([r["metrics"]["balanced_accuracy"] for r in valid]))
                base.update(full_balanced_accuracy=full, ea_balanced_accuracy=ea, ea_minus_full=ea - full)
            phase_subjects.append(base)
    for cohort in ["kumar_primary12", "kumar_development6"]:
        for scope in ["conditional", "metadata_complete"]:
            group = [r for r in phase_subjects if r["cohort"] == cohort and r["status"] == "complete"
                     and (scope == "conditional" or r["query_metadata_complete_all_sessions"])]
            members = sorted({r["subject"] for r in group}, key=numerical)
            lookup = {(r["subject"], r["window"]): r for r in group}
            for window in ["cue5s", "task2s", "task2s_minus_cue5s"]:
                values = [lookup[(s, window)]["ea_minus_full"] if window != "task2s_minus_cue5s" else
                          lookup[(s, "task2s")]["ea_minus_full"] - lookup[(s, "cue5s")]["ea_minus_full"] for s in members]
                low, high = interval(values)
                phase_cohorts.append({"dataset": "kumar", "cohort": cohort, "scope": scope, "window": window,
                    "contrast": "ea_minus_full", "n": len(members), "participants": ";".join(members),
                    "mean_difference_pp": float(np.mean(values) * 100) if values else None,
                    "ci_low_pp": low * 100 if low is not None else None, "ci_high_pp": high * 100 if high is not None else None,
                    "bootstrap_seed": 20261104})
    write_csv(OUT / "phase_participant_metrics.csv", phase_subjects)
    write_csv(OUT / "phase_cohort_comparisons.csv", phase_cohorts)
    report = {"completed_at_utc": datetime.now(timezone.utc).isoformat(), "participant_method_groups": len(groups),
              "cell_records": len(records), "successful_fits": sum(r["status"] == "complete" for r in records),
              "undefined_phase_cells": sum(r["status"].startswith("undefined") for r in records),
              "fit_claims": len(list((RUN / "claims").glob("*.json"))),
              "outputs": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in sorted(OUT.glob("*.csv"))],
              "mechanism_BA_comparisons": [r for r in comparisons if r["metric"] == "balanced_accuracy"],
              "phase_comparisons": phase_cohorts}
    (OUT / "SUMMARY.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
