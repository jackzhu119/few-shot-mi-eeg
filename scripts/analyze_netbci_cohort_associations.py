"""Five exploratory NETBCI associations with participants as independent units.

Read only verified cohort summaries. No signal downloads, model fitting, p-values,
or causal inference. Bootstrap paired participant rows, retaining missing IDs and
reporting degenerate resamples rather than replacing unavailable correlations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from learning_preserving_bci.utils.reproducibility import collect_provenance

ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = tuple(f"sub-{i}" for i in range(1, 11))
SESSIONS = ("01", "02", "03", "04")
PAIRS = (
    ("BA_change_vs_behavior_change", "CSP_BA_change_pp", "behavior_change_pp"),
    ("Mu_change_vs_behavior_change", "mu_task_contrast_change_dB", "behavior_change_pp"),
    ("Mu_change_vs_BA_change", "mu_task_contrast_change_dB", "CSP_BA_change_pp"),
    ("all_six_runs_AIRM_session04_vs_BA_change", "all_six_AIRM_session04", "CSP_BA_change_pp"),
    ("all_six_runs_PCA_session04_vs_BA_change", "all_six_PCA_subspace_session04", "CSP_BA_change_pp"),
)
UNITS = {"CSP_BA_change_pp": "percentage points", "behavior_change_pp": "percentage points",
         "mu_task_contrast_change_dB": "dB", "all_six_AIRM_session04": "AIRM distance",
         "all_six_PCA_subspace_session04": "normalized projector distance"}
DEFAULT_PLAN = ROOT / "research_logs/netbci_cohort_resume_20261010/association_estimator_plan.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_table(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def metric(value):
    if value is None or value in ("", "unavailable"):
        return None
    require(not isinstance(value, bool), "Boolean is not a quantitative metric")
    result = float(value)
    require(np.isfinite(result), "Nonfinite metric must be explicitly unavailable")
    return result


def participant_values(joined, matching, subjects=SUBJECTS, sessions=SESSIONS):
    """Validate the complete summary grain and compute paired changes first."""
    require(bool(subjects) and len(subjects) == len(set(subjects)), "Duplicate/empty requested participants")
    require(tuple(sessions) == SESSIONS, "Unexpected chronological session convention")
    index = {(row["subject"], row["session"]): row for row in joined}
    expected = {(subject, session) for subject in subjects for session in sessions}
    require(len(index) == len(joined) and set(index) == expected, "Duplicate/missing/unexpected participant/session key")
    fields = ("mean_run_hit_percent", "CSP_BA_percent", "mu_MI_minus_rest_dB")
    for row in joined:
        require(row["join_grain"] == "verified_participant_session_only" and "trial_id" not in row and "run" not in row,
                "Behavior association requires verified participant/session grain")
        for field in fields:
            value = metric(row[field])
            if value is not None and field != "mu_MI_minus_rest_dB":
                require(0 <= value <= 100, "Score percentage is outside 0..100")
    geometry = {(row["subject"], row["session"], row["variant"]): row for row in matching}
    expected_geometry = {(subject, session, variant) for subject in subjects for session in sessions
                         for variant in ("all_six_runs", "qc_common_four_runs")}
    require(len(geometry) == len(matching) and set(geometry) == expected_geometry,
            "Duplicate/missing/unexpected matched participant/session/variant key")
    for row in matching:
        require(row["status"] in ("available", "unavailable"), "Unknown matched geometry availability")
        for field in ("AIRM_to_session01", "PCA_subspace_distance"):
            value = metric(row[field])
            if row["status"] == "available":
                require(value is not None and value >= -1e-10, "Available matched geometry must be finite/nonnegative")
                if field == "PCA_subspace_distance":
                    require(value <= 1 + 1e-10, "Normalized PCA projector distance is outside 0..1")
                if row["session"] == sessions[0]:
                    require(abs(value) <= 1e-6, "Source-session matched drift must be zero")
            else:
                require(value is None, "Unavailable matched geometry contains a metric")
    values = []
    for subject in subjects:
        first, last = index[subject, sessions[0]], index[subject, sessions[-1]]
        row = {"subject": subject}
        for source_field, name in (("mean_run_hit_percent", "behavior"), ("CSP_BA_percent", "CSP_BA"),
                                   ("mu_MI_minus_rest_dB", "mu_task_contrast")):
            start, end = metric(first[source_field]), metric(last[source_field])
            unit = "dB" if name == "mu_task_contrast" else "percent"
            row[f"{name}_session01_{unit}"] = start
            row[f"{name}_session04_{unit}"] = end
            change_name = f"{name}_change_dB" if name == "mu_task_contrast" else f"{name}_change_pp"
            row[change_name] = end - start if start is not None and end is not None else None
        final_geometry = geometry[subject, sessions[-1], "all_six_runs"]
        row["all_six_matching_status"] = final_geometry["status"]
        row["all_six_AIRM_session04"] = metric(final_geometry["AIRM_to_session01"])
        row["all_six_PCA_subspace_session04"] = metric(final_geometry["PCA_subspace_distance"])
        values.append(row)
    return values


def row_correlations(x, y):
    """Pearson correlations for rows; undefined zero-variance rows remain NaN."""
    x = x - x.mean(axis=1, keepdims=True)
    y = y - y.mean(axis=1, keepdims=True)
    denominator = np.sqrt(np.sum(x * x, axis=1) * np.sum(y * y, axis=1))
    result = np.divide(np.sum(x * y, axis=1), denominator,
                       out=np.full(len(x), np.nan), where=denominator > 0)
    return np.clip(result, -1, 1)


def association_statistics(rows, subjects=SUBJECTS, seed=42, repetitions=10000):
    """Resample complete variable pairs, conditional on observed available pairs."""
    require(bool(subjects) and len(subjects) == len(set(subjects)), "Duplicate/empty requested participants")
    require(isinstance(repetitions, int) and repetitions > 0, "Positive participant bootstrap count required")
    index = {row["subject"]: row for row in rows}
    require(len(index) == len(rows) and set(index) == set(subjects), "Duplicate/missing/unexpected participant association key")
    estimates = []
    for identifier, x_field, y_field in PAIRS:
        x = np.array([np.nan if metric(index[subject][x_field]) is None else metric(index[subject][x_field]) for subject in subjects])
        y = np.array([np.nan if metric(index[subject][y_field]) is None else metric(index[subject][y_field]) for subject in subjects])
        complete = np.isfinite(x) & np.isfinite(y)
        paired_subjects = np.asarray(subjects)[complete]
        unavailable_subjects = np.asarray(subjects)[~complete]
        x, y = x[complete], y[complete]
        n = len(x)
        if n:
            draws = np.random.default_rng(seed).integers(0, n, (repetitions, n))
            sampled_x, sampled_y = x[draws], y[draws]
            distinct = np.any(np.diff(np.sort(draws, axis=1), axis=1) != 0, axis=1)
        for method in ("Pearson_r", "Spearman_rho"):
            if n >= 2:
                point_x = x[None, :] if method == "Pearson_r" else rankdata(x, method="average")[None, :]
                point_y = y[None, :] if method == "Pearson_r" else rankdata(y, method="average")[None, :]
                point = row_correlations(point_x, point_y)[0]
            else:
                point = np.nan
            if n:
                boot_x = sampled_x if method == "Pearson_r" else rankdata(sampled_x, method="average", axis=1)
                boot_y = sampled_y if method == "Pearson_r" else rankdata(sampled_y, method="average", axis=1)
                boot = row_correlations(boot_x, boot_y)
                valid = distinct & np.isfinite(boot)
                interval = np.quantile(boot[valid], [.025, .975]).tolist() if valid.any() else [None, None]
                n_valid = int(valid.sum())
                too_few_distinct = int((~distinct).sum())
                zero_variance = int((distinct & ~np.isfinite(boot)).sum())
            else:
                interval, n_valid, too_few_distinct, zero_variance = [None, None], 0, 0, 0
            estimates.append({"association": identifier, "x_metric": x_field, "y_metric": y_field,
                "x_units": UNITS[x_field], "y_units": UNITS[y_field], "estimator": method,
                "n_requested_participants": len(subjects), "n_complete_paired_participants": n,
                "complete_subjects": ",".join(paired_subjects), "unavailable_subjects": ",".join(unavailable_subjects),
                "status": "available_exploratory" if np.isfinite(point) else "unavailable_insufficient_n_or_zero_variance",
                "estimate": float(point) if np.isfinite(point) else None,
                "participant_bootstrap_CI95_low": interval[0], "participant_bootstrap_CI95_high": interval[1],
                "bootstrap_seed": seed, "bootstrap_repetitions_requested": repetitions,
                "bootstrap_repetitions_attempted": repetitions if n else 0,
                "bootstrap_valid_draws": n_valid, "bootstrap_degenerate_draws": too_few_distinct + zero_variance,
                "bootstrap_fewer_than_two_distinct_subject_draws": too_few_distinct,
                "bootstrap_zero_variance_other_draws": zero_variance,
                "CI_scope": "whole paired participants; complete-variable pairs; exploratory observational association"})
    return estimates


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_table(path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def analyze(summary_root, output, plan_path=DEFAULT_PLAN):
    started = time.monotonic()
    require(not output.exists(), "Prior association output exists; choose a new directory")
    plan = json.loads(plan_path.read_text())
    require(plan["pairs"] == [pair[0] for pair in PAIRS] and plan["estimators"] == ["Pearson_r", "Spearman_rho"] and
            plan["n_requested"] == 10 and plan["bootstrap"]["seed"] == 42 and plan["bootstrap"]["repetitions"] == 10000 and
            plan["changes"] == "session04_minus_session01" and plan["p_values"] is False and
            plan["hypothesis_confirmation"] is False and plan["causal_claims"] is False,
            "Recorded exploratory association plan differs from this estimator")
    inputs = {"plan": plan_path, "script": Path(__file__), "summary_receipt": summary_root / "summary_receipt.json"}
    receipt = json.loads(inputs["summary_receipt"].read_text())
    require(receipt["status"] == "actual_data_summary_completed" and receipt["synthetic"] is False,
            "Association source is not a verified real-data summary")
    for name in ("participant_session_join.tsv", "participant_matched_geometry.tsv", "cohort_summary.json"):
        inputs[name] = summary_root / name
        require(name in receipt["output_sha256"] and sha256(inputs[name]) == receipt["output_sha256"][name],
                f"Summary input hash mismatch: {name}")
    summary = json.loads(inputs["cohort_summary.json"].read_text())
    require(summary["synthetic"] is False and summary["subjects"] == list(SUBJECTS) and summary["participants"] == 10,
            "Association source differs from the requested first-ten-ID cohort")
    values = participant_values(read_table(inputs["participant_session_join.tsv"]),
                                read_table(inputs["participant_matched_geometry.tsv"]))
    estimates = association_statistics(values)
    result = {"status": "actual_cohort_exploratory_participant_associations", "synthetic": False,
        "subjects": list(SUBJECTS), "requested_participants": 10, "independent_unit": "participant",
        "session_contrast": "session04_minus_session01", "estimator_plan": plan,
        "participants": values, "association_estimates": estimates,
        "limitations": ["Five exploratory associations; no p-values or confirmatory significance labels",
            "First-ten published IDs, small observational cohort; source-session pilot previously seen",
            "Intervals condition on available complete variable pairs; missing identities and degenerate draws retained",
            "Session-level published behavior is not a pooled hit rate or trial-level outcome",
            "Behavior, fixed-reference decoding and spectral/geometry change do not identify causal human learning or skill retention",
            "No complex confounder adjustment, new model fitting or algorithm comparison"]}
    output.mkdir(parents=True)
    write_table(output / "participant_association_values.tsv", values)
    write_table(output / "association_estimates.tsv", estimates)
    write_json(output / "association_results.json", result)
    outputs = {path.name: sha256(path) for path in output.iterdir() if path.is_file()}
    write_json(output / "association_receipt.json", {"status": "actual_participant_associations_completed", "synthetic": False,
        "input_sha256": {key: {"path": str(path.resolve()), "sha256": sha256(path)} for key, path in inputs.items()},
        "output_sha256": outputs, "provenance": collect_provenance(42, ROOT),
        "duration_seconds": time.monotonic() - started, "bootstrap_unit": "paired whole participant",
        "new_model_fits": False, "new_EEG_downloads": False, "p_values": False, "causal_claims": False})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()
    result = analyze(args.summary, args.output, args.plan)
    print(json.dumps({"output": str(args.output), "participants": result["requested_participants"],
                      "association_estimators": len(result["association_estimates"])}))


if __name__ == "__main__":
    main()
