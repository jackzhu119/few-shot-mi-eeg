"""Independent dynamic exact-copy sensitivity arithmetic, without pipeline imports.

Reads saved small tables and provenance receipts. Does not load EEG arrays, refit
models, infer trial behavior, or choose exclusions by numerical effect direction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, rankdata


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def table(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def number(value):
    return np.nan if value in (None, "", "unavailable") else float(value)


def close(actual, expected, label):
    if expected is None or not np.isfinite(expected):
        assert actual in (None, "", "unavailable"), label
    else:
        assert np.isclose(float(actual), expected, rtol=0, atol=1e-10), label


def interval(values):
    """Bootstrap whole requested identity rows; unavailable rows stay explicit."""
    values = np.asarray(values, float)
    draws = np.random.default_rng(42).integers(0, len(values), (10000, len(values)))
    samples = values[draws]
    denominators = np.isfinite(samples).sum(axis=1)
    means = np.nansum(samples, axis=1)[denominators > 0] / denominators[denominators > 0]
    return np.percentile(means, [2.5, 97.5]).tolist() if len(means) else [None, None]


def verify(args):
    config, identity = read(args.config), read(args.identity_audit)
    assert identity["status"] == "complete_exact_numeric_identity_audit"
    assert identity["synthetic"] is False
    assert identity["subject_order"] == config["subjects"]
    assert identity["configuration_sha256"] == sha(args.config)
    configured, session_order = config["subjects"], config["session_order"]
    assert configured == [f"sub-{i}" for i in range(1, 20)]
    assert session_order == ["01", "02", "03", "04"]
    excluded = {subject for key in ("continuous_duplicate_groups", "task_window_duplicate_groups")
                for group in identity[key] if group["cross_subject"] for subject in group["subjects"]}
    subjects = [subject for subject in configured if subject not in excluded]
    assert subjects and excluded
    sensitivity, summary = args.sensitivity, args.summary
    receipt = read(sensitivity / "sensitivity_receipt.json")
    for entry in receipt["input_sha256"].values():
        assert sha(entry["path"]) == entry["sha256"]
    for name, digest in receipt["output_sha256"].items():
        assert sha(sensitivity / name) == digest
    result = read(sensitivity / "sensitivity_summary.json")
    assert result["synthetic"] is False
    assert result["retained_identities"] == subjects
    assert set(result["excluded_identities"]) == excluded
    assert result["no_model_refitting"] and result["not_independent_confirmation"]
    original = table(summary / "participant_session_join.tsv")
    assert len(original) == len(configured) * len(session_order)
    assert {(row["subject"], row["session"]) for row in original} == {
        (subject, session) for subject in configured for session in session_order}
    rows = [row for row in original if row["subject"] in subjects]
    assert table(sensitivity / "retained_participant_session_join.tsv") == rows
    index = {(row["subject"], row["session"]): row for row in rows}
    assert len(index) == len(rows) == len(subjects) * len(session_order)
    paired = table(sensitivity / "cohort_paired_changes.tsv")
    sessions = {(row["metric"], row["session"]): row for row in
                table(sensitivity / "cohort_session_statistics.tsv")}
    individuals = {(row["subject"], row["metric"]): row for row in
                   table(sensitivity / "participant_first_last_changes.tsv")}
    changes, session_checks = [], []
    for row in paired:
        field = row["metric"]
        values = np.array([number(index[subject, "04"][field]) -
                           number(index[subject, "01"][field]) for subject in subjects])
        available = np.isfinite(values)
        valid = values[available]
        ci = interval(values)
        close(row["mean_change"], valid.mean() if len(valid) else None, f"{field}: mean")
        close(row["median_change"], np.median(valid) if len(valid) else None, f"{field}: median")
        close(row["min_change"], valid.min() if len(valid) else None, f"{field}: min")
        close(row["max_change"], valid.max() if len(valid) else None, f"{field}: max")
        for suffix, expected in zip(("low", "high"), ci):
            close(row[f"subject_bootstrap_CI95_{suffix}"], expected, f"{field}: paired interval")
        assert int(row["n_requested_subjects"]) == len(subjects)
        assert int(row["n_paired_subjects"]) == len(valid)
        assert int(row["n_increased"]) == int((valid > 1e-10).sum())
        assert int(row["n_decreased"]) == int((valid < -1e-10).sum())
        assert int(row["n_unchanged"]) == int((np.abs(valid) <= 1e-10).sum())
        assert row["unavailable_subjects"] == ",".join(np.array(subjects)[~available])
        for subject, value in zip(subjects, values):
            close(individuals[subject, field]["last_minus_first"], value, f"{subject}/{field}: change")
        changes.append({"metric": field, "mean_change": float(valid.mean()) if len(valid) else None,
                        "subject_bootstrap_CI95": ci, "n_paired": len(valid), "n_requested": len(subjects)})
        for session in session_order:
            pool = np.array([number(index[subject, session][field]) for subject in subjects])
            finite = np.isfinite(pool)
            available_pool = pool[finite]
            saved = sessions[field, session]
            close(saved["mean"], available_pool.mean() if finite.any() else None, f"{field}/{session}: mean")
            close(saved["median"], np.median(available_pool) if finite.any() else None, f"{field}/{session}: median")
            for suffix, expected in zip(("low", "high"), interval(pool)):
                close(saved[f"subject_bootstrap_CI95_{suffix}"], expected, f"{field}/{session}: interval")
            assert int(saved["n_available_subjects"]) == int(finite.sum())
            assert int(saved["n_requested_subjects"]) == len(subjects)
            assert saved["unavailable_subjects"] == ",".join(np.array(subjects)[~finite])
            session_checks.append({"metric": field, "session": session,
                                   "mean": float(available_pool.mean()) if finite.any() else None,
                                   "n_available": int(finite.sum())})
    geometry = {(row["subject"], row["session"]): row for row in
                table(summary / "participant_matched_geometry.tsv")
                if row["variant"] == "all_six_runs"}
    derived = {}
    for subject in subjects:
        first, last = index[subject, "01"], index[subject, "04"]
        derived[subject] = {
            "CSP_BA_change_pp": number(last["CSP_BA_percent"]) - number(first["CSP_BA_percent"]),
            "behavior_change_pp": number(last["mean_run_hit_percent"]) - number(first["mean_run_hit_percent"]),
            "mu_task_contrast_change_dB": number(last["mu_MI_minus_rest_dB"]) - number(first["mu_MI_minus_rest_dB"]),
            "all_six_AIRM_session04": number(geometry[subject, "04"]["AIRM_to_session01"]),
            "all_six_PCA_subspace_session04": number(geometry[subject, "04"]["PCA_subspace_distance"]),
        }
    associations = []
    estimates = table(sensitivity / "association_estimates.tsv")
    assert len(estimates) == 10 and len({row["association"] for row in estimates}) == 5
    for row in estimates:
        x_all = np.array([derived[subject][row["x_metric"]] for subject in subjects])
        y_all = np.array([derived[subject][row["y_metric"]] for subject in subjects])
        complete = np.isfinite(x_all) & np.isfinite(y_all)
        x, y = x_all[complete], y_all[complete]
        n = len(x)
        if n:
            draws = np.random.default_rng(42).integers(0, n, (10000, n))
            bx, by = x[draws], y[draws]
            distinct = np.array([len(set(indices)) >= 2 for indices in draws])
            if row["estimator"] == "Spearman_rho":
                x, y = rankdata(x), rankdata(y)
                bx, by = rankdata(bx, axis=1), rankdata(by, axis=1)
            else:
                assert row["estimator"] == "Pearson_r"
            variance = (np.ptp(bx, axis=1) > 0) & (np.ptp(by, axis=1) > 0)
            valid = distinct & variance
            boot = pearsonr(bx[valid], by[valid], axis=1).statistic if valid.any() else np.array([])
            ci = np.percentile(boot, [2.5, 97.5]).tolist() if len(boot) else [None, None]
            n_valid, n_distinct, n_zero = int(valid.sum()), int((~distinct).sum()), int((distinct & ~variance).sum())
            point = float(pearsonr(x, y).statistic) if n >= 2 and np.ptp(x) > 0 and np.ptp(y) > 0 else None
        else:
            point, ci, n_valid, n_distinct, n_zero = None, [None, None], 0, 0, 0
        close(row["estimate"], point, "Association point")
        for suffix, expected in zip(("low", "high"), ci):
            close(row[f"participant_bootstrap_CI95_{suffix}"], expected, "Association interval")
        assert int(row["n_requested_participants"]) == len(subjects)
        assert int(row["n_complete_paired_participants"]) == n
        assert row["complete_subjects"] == ",".join(np.array(subjects)[complete])
        assert row["unavailable_subjects"] == ",".join(np.array(subjects)[~complete])
        assert int(row["bootstrap_valid_draws"]) == n_valid
        assert int(row["bootstrap_degenerate_draws"]) == n_distinct + n_zero
        assert int(row["bootstrap_fewer_than_two_distinct_subject_draws"]) == n_distinct
        assert int(row["bootstrap_zero_variance_other_draws"]) == n_zero
        associations.append({"pair": row["association"], "estimator": row["estimator"], "estimate": point,
                             "participant_bootstrap_CI95": ci, "valid_draws": n_valid,
                             "n_requested": len(subjects), "n_complete_paired": n})
    return {
        "status": "passed_independent_dynamic_cross_person_exact_copy_sensitivity_arithmetic",
        "synthetic": False, "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_basis": "Union of all source identities in exact cross-subject continuous-run or task-window duplicate groups; no outcome selection",
        "excluded_identities": [subject for subject in configured if subject in excluded],
        "retained_identities": subjects, "session_rows": len(rows), "paired_changes": changes,
        "session_mean_checks": session_checks, "association_checks": associations,
        "independent_of_production_helpers": True, "EEG_arrays_loaded": False, "models_refitted": False,
        "limits": ["Post-observation restriction of the same dataset; not independent confirmation.",
                   "Absence of detected exact copies does not prove biological participant identity or exclude near similarity.",
                   "Participant intervals remain exploratory; no causal learning or skill-retention inference."],
        "input_sha256": {"configuration": sha(args.config), "primary_session_join": sha(summary / "participant_session_join.tsv"),
                         "primary_geometry": sha(summary / "participant_matched_geometry.tsv"),
                         "sensitivity_receipt": sha(sensitivity / "sensitivity_receipt.json"),
                         "identity_ledger": sha(args.identity_audit)},
        "review_source_sha256": sha(__file__), "runtime": {"numpy": np.__version__},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--identity-audit", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--sensitivity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Preserve prior review output"
    result = verify(args)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "status": result["status"],
                      "retained_n": len(result["retained_identities"]), "excluded": result["excluded_identities"]}))


if __name__ == "__main__":
    main()
