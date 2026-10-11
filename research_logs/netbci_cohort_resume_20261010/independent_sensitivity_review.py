"""Independent post-observation identity-restriction table arithmetic.

Uses the immutable ten-ID joined tables and SciPy rather than importing any
production analysis helper. Does not load EEG or select exclusions by outcome.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, rankdata

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "research_logs/netbci_cohort_resume_20261010"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def table(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def close(actual, expected):
    assert np.allclose(np.asarray(actual, float), np.asarray(expected, float),
                       rtol=0, atol=1e-10), (actual, expected)


def interval(values):
    values = np.asarray(values, float)
    assert np.isfinite(values).all()
    draws = np.random.default_rng(42).integers(0, len(values), (10000, len(values)))
    return np.percentile(values[draws].mean(axis=1), [2.5, 97.5]).tolist()


def verify():
    sensitivity = LOG / "independence_sensitivity_run01"
    summary = LOG / "summary_run01"
    receipt = read(sensitivity / "sensitivity_receipt.json")
    for entry in receipt["input_sha256"].values():
        assert sha(entry["path"]) == entry["sha256"]
    for name, digest in receipt["output_sha256"].items():
        assert sha(sensitivity / name) == digest
    identity = read(LOG / "numeric_signal_identity.json")
    assert identity["status"] == "complete_exact_numeric_identity_audit"
    assert identity["synthetic"] is False
    excluded = {subject for group in identity["continuous_duplicate_groups"]
                if group["cross_subject"] for subject in group["subjects"]}
    subjects = [f"sub-{i}" for i in range(1, 11) if f"sub-{i}" not in excluded]
    assert excluded == {"sub-1", "sub-7"}
    assert subjects == ["sub-2", "sub-3", "sub-4", "sub-5", "sub-6", "sub-8", "sub-9", "sub-10"]
    result = read(sensitivity / "sensitivity_summary.json")
    assert result["retained_identities"] == subjects
    assert set(result["excluded_identities"]) == excluded
    original = table(summary / "participant_session_join.tsv")
    rows = [row for row in original if row["subject"] in subjects]
    retained = table(sensitivity / "retained_participant_session_join.tsv")
    assert retained == rows and len(rows) == 32
    index = {(row["subject"], row["session"]): row for row in rows}
    assert len(index) == len(rows)
    paired = table(sensitivity / "cohort_paired_changes.tsv")
    sessions = {(row["metric"], row["session"]): row for row in
                table(sensitivity / "cohort_session_statistics.tsv")}
    individuals = {(row["subject"], row["metric"]): row for row in
                   table(sensitivity / "participant_first_last_changes.tsv")}
    changes, session_checks = [], []
    for row in paired:
        field = row["metric"]
        values = np.array([float(index[subject, "04"][field]) -
                           float(index[subject, "01"][field]) for subject in subjects])
        ci = interval(values)
        close(row["mean_change"], values.mean())
        close(row["median_change"], np.median(values))
        close([row["min_change"], row["max_change"]], [values.min(), values.max()])
        close([row["subject_bootstrap_CI95_low"], row["subject_bootstrap_CI95_high"]], ci)
        assert int(row["n_paired_subjects"]) == int(row["n_requested_subjects"]) == 8
        assert int(row["n_increased"]) == int((values > 0).sum())
        assert int(row["n_decreased"]) == int((values < 0).sum())
        assert int(row["n_unchanged"]) == int((values == 0).sum())
        for subject, value in zip(subjects, values):
            close(individuals[subject, field]["last_minus_first"], value)
        changes.append({"metric": field, "mean_change": float(values.mean()),
                        "subject_bootstrap_CI95": ci, "n_paired": 8})
        for session in ("01", "02", "03", "04"):
            pool = np.array([float(index[subject, session][field]) for subject in subjects])
            saved = sessions[field, session]
            close(saved["mean"], pool.mean())
            close(saved["median"], np.median(pool))
            close([saved["subject_bootstrap_CI95_low"], saved["subject_bootstrap_CI95_high"]],
                  interval(pool))
            assert int(saved["n_available_subjects"]) == 8
            session_checks.append({"metric": field, "session": session, "mean": float(pool.mean())})
    geometry = {(row["subject"], row["session"]): row for row in
                table(summary / "participant_matched_geometry.tsv")
                if row["variant"] == "all_six_runs"}
    derived = {}
    for subject in subjects:
        first, last = index[subject, "01"], index[subject, "04"]
        derived[subject] = {
            "CSP_BA_change_pp": float(last["CSP_BA_percent"]) - float(first["CSP_BA_percent"]),
            "behavior_change_pp": float(last["mean_run_hit_percent"]) - float(first["mean_run_hit_percent"]),
            "mu_task_contrast_change_dB": float(last["mu_MI_minus_rest_dB"]) - float(first["mu_MI_minus_rest_dB"]),
            "all_six_AIRM_session04": float(geometry[subject, "04"]["AIRM_to_session01"]),
            "all_six_PCA_subspace_session04": float(geometry[subject, "04"]["PCA_subspace_distance"]),
        }
    associations = []
    estimates = table(sensitivity / "association_estimates.tsv")
    assert len(estimates) == 10 and len({row["association"] for row in estimates}) == 5
    for row in estimates:
        x = np.array([derived[subject][row["x_metric"]] for subject in subjects])
        y = np.array([derived[subject][row["y_metric"]] for subject in subjects])
        draws = np.random.default_rng(42).integers(0, 8, (10000, 8))
        bx, by = x[draws], y[draws]
        if row["estimator"] == "Spearman_rho":
            x, y = rankdata(x), rankdata(y)
            bx, by = rankdata(bx, axis=1), rankdata(by, axis=1)
        else:
            assert row["estimator"] == "Pearson_r"
        distinct = np.array([len(set(indices)) >= 2 for indices in draws])
        valid = distinct & (np.ptp(bx, axis=1) > 0) & (np.ptp(by, axis=1) > 0)
        point = float(pearsonr(x, y).statistic)
        boot = pearsonr(bx[valid], by[valid], axis=1).statistic
        ci = np.percentile(boot, [2.5, 97.5]).tolist()
        close(row["estimate"], point)
        close([row["participant_bootstrap_CI95_low"], row["participant_bootstrap_CI95_high"]], ci)
        assert int(row["n_complete_paired_participants"]) == 8
        assert int(row["bootstrap_valid_draws"]) == int(valid.sum())
        assert int(row["bootstrap_degenerate_draws"]) == int((~valid).sum())
        associations.append({"pair": row["association"], "estimator": row["estimator"],
                             "estimate": point, "participant_bootstrap_CI95": ci,
                             "valid_draws": int(valid.sum()), "participants": 8})
    return {
        "status": "passed_independent_eight_identity_sensitivity_arithmetic",
        "synthetic": False, "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_basis": "All source identities in exact cross-subject continuous-run duplicate groups; no outcome selection",
        "excluded_identities": sorted(excluded), "retained_identities": subjects,
        "session_rows": 32, "paired_changes": changes, "session_mean_checks": session_checks,
        "association_checks": associations, "independent_of_production_helpers": True,
        "EEG_arrays_loaded": False, "models_refitted": False,
        "limits": ["Post-observation restriction of the same cohort; not independent confirmation.",
                   "No detected exact copies among these eight IDs does not prove biological participant identity or near-similarity absence.",
                   "Correlations and paired changes are exploratory observational summaries, not causal learning or skill-retention evidence."],
        "input_sha256": {"primary_session_join": sha(summary / "participant_session_join.tsv"),
                         "primary_geometry": sha(summary / "participant_matched_geometry.tsv"),
                         "sensitivity_receipt": sha(sensitivity / "sensitivity_receipt.json"),
                         "identity_ledger": sha(LOG / "numeric_signal_identity.json")},
        "review_source_sha256": sha(__file__),
        "runtime": {"numpy": np.__version__},
    }


def compact_identity():
    path = LOG / "numeric_signal_identity.json"
    identity = read(path)
    confirmation_path = LOG / "numeric_signal_identity_official_manifest_confirmation.json"
    confirmation = read(confirmation_path)
    assert confirmation["numeric_audit_sha256"] == sha(path)
    assert confirmation["summary"]["actual_edf_rehashed"] == 240
    by_id = {f"{row['subject']}/ses-{row['session']}/run-{row['run']}": row
             for row in identity["continuous_runs"]}
    official = {row["identity"]: row for row in confirmation["all_run_verifications"]}
    assert len(official) == len(by_id) == 240
    groups = []
    for group in identity["continuous_duplicate_groups"]:
        members = []
        for item in group["members"]:
            run, declaration = by_id[item], official[item]
            assert declaration["actual_edf_sha256"] == run["source_edf_sha256"]
            assert declaration["official_manifest_match"] and declaration["per_subject_manifest_match"]
            members.append({"identity": item, "source_file": run["source_file"],
                            "source_edf_sha256": run["source_edf_sha256"],
                            "original_header_sha256": run["original_header"]["actual_original_header_sha256"],
                            "official_manifest_match": True})
        hashes = {member["source_edf_sha256"] for member in members if member["identity"].startswith("sub-7/")}
        assert len(hashes) == 1
        assert next(iter(hashes)) != next(member["source_edf_sha256"] for member in members
                                         if member["identity"].startswith("sub-1/"))
        groups.append({**{key: value for key, value in group.items() if key != "members"},
                       "members": members, "sub7_three_sessions_whole_edf_hash_equal": True,
                       "sub1_same_numeric_signal_distinct_whole_edf_hash": True})
    overlap = identity["production_partition_content_overlap"]
    counts = {key: value for key, value in overlap.items() if not isinstance(value, list)}
    counts["affected_subject_sessions"] = [row for row in overlap["by_subject_session"]
                                          if row["exact_source_training_overlap_count"] or
                                          row["exact_source_reference_query_overlap_count"]]
    assert counts["source_training_later_query_affected_trials"] == 238
    return {"status": "compact_verified_numeric_identity_summary", "synthetic": False,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "full_ledger_file": str(path.relative_to(ROOT)), "full_ledger_sha256": sha(path),
            "full_ledger_bytes": path.stat().st_size, "full_ledger_preserved": True,
            "summary": identity["summary"], "method": identity["method"],
            "all_six_continuous_duplicate_groups": groups,
            "partition_content_overlap": counts,
            "official_confirmation": {"file": str(confirmation_path.relative_to(ROOT)),
                                      "sha256": sha(confirmation_path),
                                      "summary": confirmation["summary"],
                                      "official_manifest_sha256": confirmation["official_manifest_sha256"],
                                      "interpretation": confirmation["interpretation"]},
            "cross_subject_affected_identities": ["sub-1", "sub-7"],
            "limitations": identity["limitations"], "summary_source_sha256": sha(__file__)}


if __name__ == "__main__":
    for name, result in (("independent_sensitivity_review.json", verify()),
                         ("numeric_signal_identity_summary.json", compact_identity())):
        output = LOG / name
        with output.open("x") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(json.dumps({"output": str(output), "status": result["status"]}))
