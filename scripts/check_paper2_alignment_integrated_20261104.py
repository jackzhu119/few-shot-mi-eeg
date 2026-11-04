"""Independent exact-count check of the frozen Paper2 saved-decision reanalysis.

This checker does not import the production analysis or its functions. Fractions
are used for confusion counts and transition weights; NumPy is used only for
the separately implemented descriptive bootstrap and summary comparison.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess

import numpy as np


ALG = {
    "source_only": "frozen",
    "frozen_csp_lda_recalibration": "lda_only",
    "refit_csp_lda": "full_csp",
    "ea_csp_lda": "ea_csp",
}
METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
DIFFERENCES = {
    "lda_minus_frozen": ("lda_only", "frozen"),
    "full_minus_frozen": ("full_csp", "frozen"),
    "full_minus_lda": ("full_csp", "lda_only"),
    "ea_minus_full": ("ea_csp", "full_csp"),
    "ea_minus_frozen": ("ea_csp", "frozen"),
}
RATES = ("ba", "weak_recall", "recall_gap", "recall_left", "recall_right")
DEV = [1, 4, 7, 10, 13, 16]
COHORTS = {
    "Kumar2024": {
        "development6": [f"sub-{i}" for i in DEV],
        "remaining12": [f"sub-{i}" for i in range(1, 19) if i not in DEV],
        "all18_descriptive": [f"sub-{i}" for i in range(1, 19)],
    },
    "BNCI2014-001": {"external9": [f"sub-{i:02d}" for i in range(1, 10)]},
}
DIAGNOSTICS = defaultdict(lambda: {"checks": 0, "maximum_absolute_error": 0.0})
INPUTS = {}
HISTORICAL = {}
ROOT = Path(__file__).resolve().parents[1]


def acquire(relative):
    path = ROOT / relative
    data = path.read_bytes()
    INPUTS[relative] = {
        "path": relative, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return data


def table(relative):
    data = acquire(relative)
    if relative.endswith(".gz"):
        data = gzip.decompress(data)
    return list(csv.DictReader(io.StringIO(data.decode())))


def decision(value):
    number = int(value)
    assert str(value) in ("0", "1"), ("Nonbinary decision", value)
    return number


def check(category, actual, expected, context):
    stats = DIAGNOSTICS[category]
    stats["checks"] += 1
    if actual is None:
        assert expected in (None, ""), (category, context, actual, expected)
    elif isinstance(actual, str):
        assert actual == expected, (category, context, actual, expected)
    else:
        error = abs(float(actual) - float(expected))
        stats["maximum_absolute_error"] = max(stats["maximum_absolute_error"], error)
        assert error <= 1e-12, (category, context, actual, expected)


def exact_rates(rows):
    counts = [0, 0]
    hits = [0, 0]
    for _, label, predicted, _, _ in rows:
        counts[label] += 1
        hits[label] += int(label == predicted)
    recalls = [Fraction(hits[c], counts[c]) if counts[c] else None for c in (0, 1)]
    complete = min(counts) > 0
    ba = (recalls[0] + recalls[1]) / 2 if complete else None
    weak = min(recalls) if complete else None
    gap = abs(recalls[0] - recalls[1]) if complete else None
    if complete:
        assert weak == ba - gap / 2
    return {
        "n_query": len(rows), "n_left": counts[0], "n_right": counts[1],
        "correct_left": hits[0], "correct_right": hits[1],
        "recall_left": recalls[0], "recall_right": recalls[1],
        "ba": ba, "weak_recall": weak, "recall_gap": gap,
        "prediction_left": sum(row[2] == 0 for row in rows),
        "prediction_right": sum(row[2] == 1 for row in rows),
        "status": "ok" if complete else "undefined_missing_class",
    }


def exact_pair(a, b):
    assert [(r[0], r[1]) for r in a] == [(r[0], r[1]) for r in b]
    ra, rb = exact_rates(a), exact_rates(b)
    names = ["delta_" + metric for metric in RATES]
    names += ["corrected", "introduced", "disagreement"]
    if ra["status"] != "ok":
        return {**dict.fromkeys(names), "status": ra["status"]}
    corrected = [0, 0]
    introduced = [0, 0]
    different = [0, 0]
    for old, new in zip(a, b):
        label = old[1]
        corrected[label] += int(old[2] != label and new[2] == label)
        introduced[label] += int(old[2] == label and new[2] != label)
        # Count disagreement independently, never infer it from C + I.
        different[label] += int(old[2] != new[2])
    denominators = [ra["n_left"], ra["n_right"]]
    def balanced(n):
        return sum((Fraction(n[c], 2 * denominators[c]) for c in (0, 1)), Fraction())
    result = {"delta_" + metric: rb[metric] - ra[metric] for metric in RATES}
    result.update(corrected=balanced(corrected), introduced=balanced(introduced),
                  disagreement=balanced(different), status="ok")
    assert result["corrected"] - result["introduced"] == result["delta_ba"]
    assert result["corrected"] + result["introduced"] == result["disagreement"]
    return result


def sign(value):
    return "positive" if value > 1e-12 else "negative" if value < -1e-12 else "zero"


DRAW_CACHE = {}


def describe(values):
    x = np.asarray([float(v) for v in values], dtype=float)
    n = len(x)
    if not n:
        return {"n": 0, "mean": None, "ci_low": None, "ci_high": None,
                "median": None, "minimum": None, "maximum": None,
                "positive": 0, "zero": 0, "negative": 0,
                "leave_one_out_min": None, "leave_one_out_max": None,
                "status": "undefined_no_eligible_participant"}
    if n not in DRAW_CACHE:
        draws = np.random.Generator(np.random.PCG64(20261104)).integers(n, size=(10000, n))
        DRAW_CACHE[n] = np.vstack([np.bincount(d, minlength=n) for d in draws])
    resampled_means = DRAW_CACHE[n] @ x / n
    low, high = np.percentile(resampled_means, [2.5, 97.5], method="linear")
    loo = [np.mean(np.delete(x, i)) for i in range(n)] if n > 1 else []
    return {"n": n, "mean": np.mean(x), "ci_low": low, "ci_high": high,
            "median": np.median(x), "minimum": np.min(x), "maximum": np.max(x),
            **{s: sum(sign(v) == s for v in x) for s in ("positive", "zero", "negative")},
            "leave_one_out_min": min(loo) if loo else None,
            "leave_one_out_max": max(loo) if loo else None,
            "status": "ok" if n > 1 else "single_participant_degenerate_interval"}


def load_raw():
    base = "research_logs/paper2_structure_revision_20261029/component_replay/input/budget/"
    source = table(base + "query_predictions.csv.gz")
    for row in table(base + "session_metrics.csv.gz"):
        key = ("Kumar2024", row["subject"], row["session"], row["budget"], ALG[row["method"]])
        assert key not in HISTORICAL
        HISTORICAL[key] = row
    quality = {r["trial_id"]: r for r in table(
        "research_logs/kumar_submission_qc_20261015/run01/query_identity_qc_ledger.csv")}
    frozen = json.loads(acquire(
        "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json"))["trials"]
    annotations = {r["trial_id"]: r for r in frozen}
    assert len(annotations) == len(frozen)
    sets = defaultdict(list)
    seen = set()
    for row in source:
        assert row["synthetic"] == row["software_validation_only"] == "False"
        meta = annotations[row["trial_id"]]
        assert meta["role"] == "target_query" and meta["included"]
        assert meta["subject"] == row["subject"] and meta["session"] == row["session"]
        assert meta["run"] == row["run"]
        y = decision(row["label"])
        assert meta["label"] == ("left_hand" if y == 0 else "right_hand")
        q = quality[row["trial_id"]]
        assert q["role"] == "target_query" and q["included"] == "True"
        assert q["label"] == meta["label"]
        flagged = float(q["raw_peak_to_peak_max_volts"]) > 250e-6
        assert flagged == (q["qc_peak_to_peak_over_250uv"] == "True")
        assert flagged == meta["qc_peak_to_peak_over_250uv"]
        key = ("Kumar2024", row["subject"], row["session"], row["budget"], ALG[row["method"]])
        identity = key + (row["trial_id"],)
        assert identity not in seen
        seen.add(identity)
        sets[key].append((row["trial_id"], y, decision(row["prediction"]), row["run"], flagged))
    for person in range(1, 10):
        prefix = "research_logs/paper2_external_validation_20261027/"
        meta = json.loads(acquire(prefix + f"trial_identity/bnci001-sub-{person:02d}/manifest.json"))
        expected = [r for r in meta["trials"] if r["role"] == "query" and r["included"]]
        assert len(expected) == 120
        for method in METHODS:
            pred = json.loads(acquire(prefix + f"saved_predictions/bnci001-sub-{person:02d}/E__n20__{method}.json"))
            assert pred["query_used_for_fitting"] is False and pred["synthetic"] is False
            assert pred["trial_ids"] == [r["trial_id"] for r in expected]
            assert pred["y"] == [r["label"] for r in expected]
            assert len(pred["prediction"]) == 120
            key = ("BNCI2014-001", f"sub-{person:02d}", "E", "full", method)
            sets[key] = [(tid, decision(y), decision(p), "run-" + str(t["run"]), False)
                         for tid, y, p, t in zip(pred["trial_ids"], pred["y"], pred["prediction"], expected)]
    for d, p, s, b, m in sets:
        ref = sets[d, p, s, b, "frozen"]
        assert [(r[0], r[1], r[3]) for r in ref] == [(r[0], r[1], r[3]) for r in sets[d, p, s, b, m]]
        if d == "Kumar2024":
            assert [(r[0], r[1]) for r in ref] == [(r[0], r[1]) for r in sets[d, p, s, "full", "frozen"]]
    return sets, len(source)


def rebuild(sets):
    endpoints, changes = {}, {}
    for (d, p, s, b, m), rows in sets.items():
        endpoints[d, p, s, b, m, "all_query"] = exact_rates(rows)
        if d == "Kumar2024" and b == "full":
            endpoints[d, p, s, b, m, "unflagged_query"] = exact_rates([r for r in rows if not r[4]])
    for d, p, s, b in {k[:-1] for k in sets}:
        for name, (new, old) in DIFFERENCES.items():
            a, z = sets[d, p, s, b, old], sets[d, p, s, b, new]
            changes[d, p, s, b, name, "all_query"] = exact_pair(a, z)
            if d == "Kumar2024" and b == "full":
                changes[d, p, s, b, name, "unflagged_query"] = exact_pair(
                    [r for r in a if not r[4]], [r for r in z if not r[4]])
    people = []
    for cells, is_contrast in [(endpoints, False), (changes, True)]:
        grouped = defaultdict(list)
        for (d, p, session, budget, method, subset), values in cells.items():
            grouped[d, p, budget, method, subset].append((session, values))
        person_values = {}
        for key, rows in grouped.items():
            d = key[0]
            assert len(rows) == len({r[0] for r in rows}) == (5 if d == "Kumar2024" else 1)
            complete = all(r[1]["status"] == "ok" for r in rows)
            fields = (["delta_" + x for x in RATES] + ["corrected", "introduced", "disagreement"]
                      if is_contrast else list(RATES))
            result = {f: sum((r[1][f] for r in rows), Fraction()) / len(rows) if complete else None
                      for f in fields}
            result["status"] = "ok" if complete else "undefined_incomplete_participant"
            if is_contrast:
                result.update({"endpoint_" + state + "_fraction":
                               Fraction(sum(sign(r[1]["delta_ba"]) == state for r in rows), len(rows))
                               if complete else None for state in ("positive", "zero", "negative")})
            person_values[key] = result
        people.append(person_values)
    return endpoints, changes, *people


def compare_results(analysis, sets, endpoints, changes, people, paired):
    for key, old in HISTORICAL.items():
        rebuilt = endpoints[key + ("all_query",)]
        check("historical_session_BA", rebuilt["ba"], old["balanced_accuracy"], key)
        check("historical_session_query_count", rebuilt["n_query"], old["n_query"], key)
    for filename, values, ident in [
        ("endpoint_metrics.csv", endpoints, "method"),
        ("endpoint_transitions.csv", changes, "contrast"),
    ]:
        output = table(str(analysis / filename))
        assert len(output) == len(values)
        for row in output:
            key = tuple(row[x] for x in ("dataset", "participant", "session", "budget", ident, "subset"))
            for field, value in values[key].items():
                check(filename, value, row[field], (key, field))
    for filename, values, ident in [
        ("participant_metrics.csv", people, "method"),
        ("participant_contrasts.csv", paired, "contrast"),
    ]:
        output = table(str(analysis / filename))
        assert len(output) == len(values)
        for row in output:
            key = tuple(row[x] for x in ("dataset", "participant", "budget", ident, "subset"))
            for field, value in values[key].items():
                check(filename, value, row[field], (key, field))
    summaries = []
    for filename, values, ident in [
        ("cohort_method_metrics.csv", people, "method"),
        ("cohort_contrasts.csv", paired, "contrast"),
    ]:
        for row in table(str(analysis / filename)):
            d, cohort, b, name, subset = (row[x] for x in ("dataset", "cohort", "budget", ident, "subset"))
            members = [p for p in COHORTS[d][cohort] if values[d, p, b, name, subset]["status"] == "ok"]
            assert json.loads(row["participants"]) == members
            nums = [values[d, p, b, name, subset][row["metric"]] for p in members]
            stats = describe(nums)
            for field, value in stats.items():
                check(filename, value, row[field], (d, cohort, b, name, subset, row["metric"], field))
            summaries.append({"dataset": d, "cohort": cohort, "budget": b, "name": name,
                              "subset": subset, "metric": row["metric"],
                              **{k: float(v) if isinstance(v, (Fraction, np.floating)) else v
                                 for k, v in stats.items()}})
    for row in table(str(analysis / "joint_benefit_distribution.csv")):
        d, cohort, b, name, subset = (row[x] for x in ("dataset", "cohort", "budget", "contrast", "subset"))
        all_ids = [p for p in COHORTS[d][cohort] if paired[d, p, b, name, subset]["status"] == "ok"]
        members = [p for p in all_ids if sign(paired[d, p, b, name, subset]["delta_ba"]) == row["ba_sign"]
                   and sign(paired[d, p, b, name, subset]["delta_weak_recall"]) == row["weak_recall_sign"]]
        assert json.loads(row["members"]) == members
        for field, value in {"count": len(members), "n_defined": len(all_ids),
                             "fraction": Fraction(len(members), len(all_ids)) if all_ids else None}.items():
            check("joint_benefit_distribution.csv", value, row[field], (d, cohort, b, name, subset, field))
    for row in table(str(analysis / "qc_same_eligible_comparisons.csv")):
        ident = "contrast" if row.get("contrast") else "method"
        values = paired if ident == "contrast" else people
        d, cohort, name, field = row["dataset"], row["cohort"], row[ident], row["metric"]
        members = [p for p in COHORTS[d][cohort] if values[d, p, "full", name, "unflagged_query"]["status"] == "ok"]
        assert json.loads(row["eligible_participants"]) == members
        unrestricted = [values[d, p, "full", name, "all_query"][field] for p in members]
        restricted = [values[d, p, "full", name, "unflagged_query"][field] for p in members]
        choices = {"all_query_same_eligible": unrestricted, "unflagged_query": restricted,
                   "paired_unflagged_minus_all": [y - x for x, y in zip(unrestricted, restricted)]}
        for f, value in describe(choices[row["scope"]]).items():
            check("qc_same_eligible_comparisons.csv", value, row[f], (cohort, name, field, row["scope"], f))
    run_groups = defaultdict(list)
    for (d, p, s, b, m), rows in sets.items():
        if b == "full":
            for r in rows:
                run_groups[d, p, s, r[3], m].append(r)
    for row in table(str(analysis / "query_run_metrics.csv")):
        key = tuple(row[x] for x in ("dataset", "participant", "session", "run", "method"))
        for f, value in exact_rates(run_groups[key]).items():
            check("query_run_metrics.csv", value, row[f], (key, f))
    return summaries


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--analysis", type=Path, default=Path("research_logs/paper2_alignment_integrated_20261104/analysis"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ROOT = args.root.resolve()
    analysis = (ROOT / args.analysis).resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    sets, kumar_rows = load_raw()
    rebuilt = rebuild(sets)
    summaries = compare_results(analysis, sets, *rebuilt)
    for row in json.loads((analysis / "INPUT_MANIFEST.json").read_text()):
        assert INPUTS[row["path"]] == row, ("Source digest mismatch", row["path"])
    with (args.output / "independently_rebuilt_summaries.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    plan = "13dd7646c4ce37db40504154388e76b4c6ca6595"
    try:
        resolution = subprocess.run(["git", "rev-parse", plan], cwd=ROOT, text=True,
                                    capture_output=True, check=False)
    except FileNotFoundError:
        resolution = None
    plan_git_verified = resolution is not None and resolution.returncode == 0
    if plan_git_verified:
        assert resolution.stdout.strip() == plan
    report = {
        "status": "PASS", "plan_commit": plan,
        "plan_ref_verified_in_checkout": plan_git_verified,
        "plan_ref_source": "checkout ancestor" if plan_git_verified else "recorded frozen-plan identity; archive has no Git history",
        "implementation": "Independent stdlib Fraction confusion/transition counts and bootstrap multiplicity-matrix implementation; no import of production analysis functions",
        "kumar_prediction_rows": kumar_rows,
        "bnci_prediction_rows": sum(len(v) for k, v in sets.items() if k[0] == "BNCI2014-001"),
        "original_endpoint_groups": len(sets), "endpoint_rates_including_QC": len(rebuilt[0]),
        "endpoint_contrasts_including_QC": len(rebuilt[1]),
        "participant_rate_cells": len(rebuilt[2]), "participant_contrast_cells": len(rebuilt[3]),
        "summary_rows": len(summaries), "comparisons": dict(DIAGNOSTICS),
        "full_support_all_four_cohorts_checked": True, "all_five_kumar_budgets_checked": True,
        "QC_same_cohort_all_rates_contrasts_and_intervals_checked": True,
        "nonlinear_metrics_computed_before_session_averaging": True,
        "direct_disagreement_counts": True,
        "bootstrap": {"seed": 20261104, "resamples": 10000, "participant_order": "numeric suffix", "percentile": "linear"},
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": list(INPUTS.values()), "new_fits": 0, "new_query_forwards": 0,
    }
    (args.output / "INDEPENDENT_CHECK.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"inputs", "comparisons"}}, indent=2))


if __name__ == "__main__":
    main()
