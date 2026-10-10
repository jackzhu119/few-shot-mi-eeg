"""Analyze existing NETBCI behavior and saved EEG features; no downloads or fitting."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from learning_preserving_bci.datasets.netbci import file_sha256
from learning_preserving_bci.datasets.netbci_behavior import (
    join_verified_sessions,
    read_behavior_sessions,
)
from learning_preserving_bci.utils.reproducibility import collect_provenance

ROOT = Path(__file__).resolve().parents[1]


def read_table(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def write_table(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def cohort_statistics(behavior, sessions, seed, repetitions, numerical_tolerance_pp=1e-10,
                      reporting_sensitivity_pp=0.01):
    subjects = sorted({r["original_subject"] for r in behavior})
    lookup = {(r["original_subject"], r["session"]): r for r in behavior}
    matrix = np.array([[lookup[s, t]["mean_run_hit_percent"] for t in sessions] for s in subjects])
    rng = np.random.default_rng(seed)
    # Resample complete subject trajectories, keeping all within-subject dependence.
    bootstrap = matrix[rng.integers(0, len(subjects), size=(repetitions, len(subjects)))].mean(axis=1)
    rows = []
    for i, session in enumerate(sessions):
        interval = np.quantile(bootstrap[:, i], [.025, .975])
        rows.append({"session": session, "n_behavior_subjects": len(subjects),
                     "mean_subject_session_hit_percent": float(matrix[:, i].mean()),
                     "median_subject_session_hit_percent": float(np.median(matrix[:, i])),
                     "between_subject_sd_pp": float(matrix[:, i].std(ddof=1)),
                     "subject_bootstrap_CI95_low": float(interval[0]),
                     "subject_bootstrap_CI95_high": float(interval[1])})
    delta = matrix[:, -1] - matrix[:, 0]
    successive = np.diff(matrix, axis=1)
    epsilon = numerical_tolerance_pp
    interval = np.quantile(bootstrap[:, -1] - bootstrap[:, 0], [.025, .975])
    change = {"contrast": f"session_{sessions[-1]}_minus_{sessions[0]}",
              "n_subjects": len(subjects), "mean_change_pp": float(delta.mean()),
              "median_change_pp": float(np.median(delta)),
              "min_change_pp": float(delta.min()), "max_change_pp": float(delta.max()),
              "n_increased": int((delta > epsilon).sum()), "n_decreased": int((delta < -epsilon).sum()),
              "n_unchanged": int((np.abs(delta) <= epsilon).sum()),
              "n_strictly_increasing_all_sessions": int((successive > epsilon).all(axis=1).sum()),
              "n_nondecreasing_all_sessions": int((successive >= -epsilon).all(axis=1).sum()),
              "n_with_any_decrease": int((successive < -epsilon).any(axis=1).sum()),
              "n_with_any_decrease_larger_than_reporting_sensitivity": int((successive < -reporting_sensitivity_pp).any(axis=1).sum()),
              "comparison_numerical_tolerance_pp": epsilon,
              "reported_change_sensitivity_pp": reporting_sensitivity_pp,
              "subject_bootstrap_CI95_pp": interval.tolist(),
              "CI_scope": "complete published subject trajectories; observational, not causal learning"}
    return rows, change, matrix, subjects


def band_summaries(trials, sessions, variants):
    rows, contrasts = [], []
    for variant, rule in variants.items():
        for session in sessions:
            for band in ("mu", "beta"):
                summaries = {}
                for label in ("rest", "right_hand"):
                    counts, log_means, power_means = [], [], []
                    for run in rule["runs"]:
                        selected = [r for r in trials if r["session"] == session and r["run"] == run
                                    and r["label"] == label
                                    and (not rule["exclude_qc_flagged"] or r["qc_flag"] == "False")]
                        if not selected:
                            raise ValueError("Missing class/run cell: cannot silently change run weighting")
                        values = np.array([float(r[f"{band}_ROI_V2"]) for r in selected])
                        if (values <= 0).any() or not np.isfinite(values).all():
                            raise ValueError("Band powers must be positive and finite")
                        counts.append(len(values))
                        log_means.append(float(np.log10(values).mean()))
                        power_means.append(float(values.mean()))
                    log_power = float(np.mean(log_means))
                    arithmetic = float(np.mean(power_means))
                    row = {"variant": variant, "subject": trials[0]["subject"], "session": session,
                           "band": band, "label": label, "runs": ",".join(rule["runs"]),
                           "n_trials": sum(counts), "n_runs": len(counts),
                           "n_trials_per_run": json.dumps(counts),
                           "equal_run_mean_log10_power_V2": log_power,
                           "equal_run_geometric_mean_power_uV2": float(10**log_power * 1e12),
                           "equal_run_arithmetic_mean_power_uV2": arithmetic * 1e12}
                    rows.append(row)
                    summaries[label] = row
                rest, mi = summaries["rest"], summaries["right_hand"]
                contrasts.append({"variant": variant, "subject": mi["subject"], "session": session,
                                  "band": band, "n_rest": rest["n_trials"], "n_MI": mi["n_trials"],
                                  "MI_minus_rest_log_power_dB": 10 * (
                                      mi["equal_run_mean_log10_power_V2"] - rest["equal_run_mean_log10_power_V2"]),
                                  "ratio_of_arithmetic_mean_power_dB": float(10*np.log10(
                                      mi["equal_run_arithmetic_mean_power_uV2"] /
                                      rest["equal_run_arithmetic_mean_power_uV2"])),
                                  "interpretation": "between_task_window_contrast_not_baseline_ERD"})
    return rows, contrasts


def matched_spectral_contrasts(trials, sessions, config):
    """Equal trials/run/class sensitivity; repetitions are not independent people."""
    rule = config["spectral_variants"]["common_four_runs_qc_unflagged"]
    n = config["matched_spectral_trials_per_class_run"]
    rows = []
    for repetition in range(config["matched_spectral_repetitions"]):
        rng = np.random.default_rng(config["seed"]+repetition)
        for session in sessions:
            chosen = {}
            for label in ("rest", "right_hand"):
                chosen[label] = []
                for run in rule["runs"]:
                    pool = [r for r in trials if r["session"] == session and r["run"] == run
                            and r["label"] == label and r["qc_flag"] == "False"]
                    if len(pool) < n:
                        raise ValueError("Insufficient unflagged class/run cell for matched sampling")
                    chosen[label].extend(pool[i] for i in rng.choice(len(pool), n, replace=False))
            for band in ("mu", "beta"):
                means = {label: float(np.mean([np.log10(float(r[f"{band}_ROI_V2"])) for r in selected]))
                         for label, selected in chosen.items()}
                rows.append({"repetition": repetition, "seed": config["seed"]+repetition,
                             "subject": trials[0]["subject"], "session": session, "band": band,
                             "runs": ",".join(rule["runs"]), "n_rest": len(chosen["rest"]),
                             "n_MI": len(chosen["right_hand"]),
                             "MI_minus_rest_log_power_dB": 10*(means["right_hand"]-means["rest"]),
                             "variation_scope": "matched_subsampling_not_participant_CI"})
    return rows


def geometry_summary(rows, session, field):
    values = np.array([float(r[field]) for r in rows if r["session"] == session])
    if len(values) != 20:
        raise ValueError("Expected the saved 20 matched-subsample repetitions per session")
    return {"mean": float(values.mean()), "min": float(values.min()), "max": float(values.max())}


def analyze(config_path, output):
    start = time.monotonic()
    config = json.loads(config_path.read_text())
    sessions = list(config["session_columns"])
    if config["behavior_cohort_primary_descriptive_change"] != [sessions[0], sessions[-1]]:
        raise ValueError("This analysis requires the explicitly declared last-minus-first contrast")
    inputs = {"config": config_path, **{k: ROOT/config[k] for k in (
        "behavior_source", "behavior_dictionary", "behavior_receipt", "stage1_closure", "identity_audit", "qc_geometry")}}
    stage = ROOT/config["stage1_results"]
    for name in ("event_inventory.tsv", "trial_features.tsv", "matched_geometry.tsv", "decoder_results.json"):
        inputs[name] = stage/name
    closure = json.loads(inputs["stage1_closure"].read_text())
    # Check every preserved historical input/source/artifact hash before using its results.
    closure_checked = 0
    for section in ("input_sha256", "current_source_sha256", "artifact_sha256"):
        for filename, expected in closure[section].items():
            if file_sha256(ROOT/filename) != expected:
                raise ValueError(f"Historical stage1 closure mismatch: {filename}")
            closure_checked += 1
    receipt = json.loads(inputs["behavior_receipt"].read_text())
    for key, checksum in (("behavior_source", receipt["official_checksum"]),
                          ("behavior_dictionary", receipt["behavior_dictionary"]["checksum"])):
        if checksum["type"].upper() != "MD5":
            raise ValueError("Unexpected source checksum algorithm")
        if hashlib.md5(inputs[key].read_bytes()).hexdigest() != checksum["value"]:
            raise ValueError("Official behavioral-source MD5 mismatch")
    dictionary = inputs["behavior_dictionary"].read_text()
    for column in config["session_columns"].values():
        if f'"{column}"' not in dictionary:
            raise ValueError("Missing source dictionary session field")
    try:
        json.loads(dictionary)
        dictionary_status = "valid_strict_JSON"
    except json.JSONDecodeError as exc:
        dictionary_status = f"invalid_strict_JSON_preserved: {exc.msg}; line {exc.lineno}"
    behavior, positions = read_behavior_sessions(inputs["behavior_source"], config["session_columns"],
                                                  config["expected_reported_run_scores_per_session"])
    if len({r["original_subject"] for r in behavior}) != config["expected_behavior_subjects"]:
        raise ValueError("Unexpected behavior cohort size")
    audit = json.loads(inputs["identity_audit"].read_text())
    if not audit["subject_session_run_identity_verified"]:
        raise ValueError("Cross-version subject/session identity unverified")
    mapping = {audit["subject"]: audit["original_subject"]}
    trials, events = read_table(inputs["trial_features.tsv"]), read_table(inputs["event_inventory.tsv"])
    expected_subject = config["expected_EEG_subject"]
    if {r["subject"] for r in trials} != {expected_subject} or len(trials) != config["expected_EEG_trials"]:
        raise ValueError("EEG scope changed from the verified pilot")
    if len({r["trial_id"] for r in trials}) != len(trials):
        raise ValueError("Duplicate EEG trial")
    if [r["trial_id"] for r in trials] != [r["trial_id"] for r in events]:
        raise ValueError("Saved feature/event trial identities disagree")
    for trial, event in zip(trials, events, strict=True):
        if any(trial[k] != event[k] for k in ("subject", "session", "run", "label", "source_file")):
            raise ValueError("Saved feature/event metadata disagree")
        if event["original_subject"] != mapping[trial["subject"]]:
            raise ValueError("Original participant identity mismatch")
        if trial["qc_flag"] not in ("True", "False"):
            raise ValueError("Invalid saved QC flag")
    if {r["session"] for r in trials} != set(sessions):
        raise ValueError("Unexpected EEG session coverage")
    cohort, change, matrix, subjects = cohort_statistics(
        behavior, sessions, config["seed"], config["subject_bootstrap_repetitions"],
        config["comparison_numerical_tolerance_pp"], config["reported_change_sensitivity_pp"])
    bands, contrasts = band_summaries(trials, sessions, config["spectral_variants"])
    spectral_matched = matched_spectral_contrasts(trials, sessions, config)
    matched, qc = read_table(inputs["matched_geometry.tsv"]), read_table(inputs["qc_geometry"])
    decoders = json.loads(inputs["decoder_results.json"].read_text())
    eeg = []
    for i, session in enumerate(sessions):
        selected = [r for r in trials if r["session"] == session]
        counts = Counter(r["label"] for r in selected)
        airm = geometry_summary(matched, session, "AIRM_to_session01")
        qc_airm = geometry_summary(qc, session, "AIRM_to_session01")
        pca = geometry_summary(matched, session, "PCA_subspace_distance")
        within = geometry_summary(matched, session, "within_session_run_AIRM_mean")
        row = {"subject": expected_subject, "session": session, "n_EEG_trials": len(selected),
               "n_EEG_runs": len({r["run"] for r in selected}),
               "n_right_hand": counts["right_hand"], "n_rest": counts["rest"],
               "n_qc_flagged": sum(r["qc_flag"] == "True" for r in selected),
               "behavior_cohort_rank_descending": 1 + int((matrix[:, i] > matrix[subjects.index(mapping[expected_subject]), i]).sum()),
               "AIRM_matched144_mean": airm["mean"],
               "AIRM_matched144_resampling_min": airm["min"], "AIRM_matched144_resampling_max": airm["max"],
               "AIRM_qc_common_runs_matched96_mean": qc_airm["mean"],
               "PCA_subspace_distance_matched144_mean": pca["mean"],
               "within_session_run_AIRM_matched144_mean": within["mean"]}
        for family in ("CSP_LDA", "EEGNet_CPU_3epochs"):
            candidates = [r for r in decoders if r["subject"] == expected_subject
                          and r["session"] == session and r["decoder"] == family]
            if len(candidates) != 1:
                raise ValueError("Nonunique decoder participant/session/family result")
            result = candidates[0]
            row.update({f"{family}_BA_percent": 100*result["balanced_accuracy"],
                        f"{family}_query_n": result["n_test"],
                        f"{family}_query_runs_n": result["n_runs"],
                        f"{family}_BA_conditional_run_CI95_percent": json.dumps(
                            [100*x for x in result["conditional_run_bootstrap_CI95"]]),
                        f"{family}_query_qc_unflagged_BA_percent": 100*result["qc_unflagged_BA"]})
        eeg.append(row)
    linked = join_verified_sessions(behavior, eeg, mapping)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/"source_snapshot"
    snapshot.mkdir()
    snapshot_sources = [config_path, Path(__file__),
                        ROOT/"src/learning_preserving_bci/datasets/netbci_behavior.py"]
    for source in snapshot_sources:
        (snapshot/source.name).write_bytes(source.read_bytes())
    artifacts = {"behavior_sessions.tsv": behavior, "behavior_source_positions.tsv": positions,
                 "cohort_session_summary.tsv": cohort, "linked_EEG_behavior_sessions.tsv": linked,
                 "bandpower_session_summaries.tsv": bands, "task_bandpower_contrasts.tsv": contrasts,
                 "matched_task_bandpower_contrasts.tsv": spectral_matched}
    for filename, rows in artifacts.items():
        write_table(output/filename, rows)
    summary = {"status": "real_data_exploratory_session_analysis",
               "behavior_subjects": len(subjects), "behavior_sessions": len(behavior),
               "behavior_score_values": len(positions), "missing_score_values": 0,
               "EEG_subjects": 1, "EEG_trials": len(trials), "linked_sessions": len(linked),
               "cohort_behavior_change": change, "cohort_sessions": cohort,
               "pilot_sessions": linked, "dictionary_syntax": dictionary_status,
               "linked_grain": "participant_session; never EEG-run or EEG-trial outcome",
               "behavior_metric": config["behavior_aggregation"],
               "task_contrast_metric": "mean_log_power_difference_dB; arithmetic-power-ratio sensitivity also saved; not ERD",
               "neural_behavior_correlation_test": "not_performed_one_subject_four_dependent_sessions",
               "online_hit_chance_level": "unresolved_not_assumed_50_percent",
               "neural_behavior_discordance": "descriptive_different_endpoints_not_a_subtractable_learning_gain",
               "learning_retention_or_algorithm_causal_effect": "cannot_identify_from_current_observational_data"}
    write_json(output/"analysis_summary.json", summary)
    provenance = collect_provenance(config["seed"], ROOT)
    provenance.update({"analysis_script_sha256": file_sha256(Path(__file__)),
                       "inputs_sha256": {str(p.relative_to(ROOT)): file_sha256(p) for p in inputs.values()},
                       "historical_closure_hashes_checked": closure_checked,
                       "new_signal_download_bytes": 0, "model_fits": 0,
                       "elapsed_seconds": time.monotonic()-start,
                       "source_versions": {"behavior": "Dataverse RBJRC7 v2.2", "EEG": "NEMAR nm000305 v1.0.0"},
                       "outputs_sha256": {str(p.relative_to(output)): file_sha256(p)
                                          for p in sorted(output.rglob("*")) if p.is_file()}})
    write_json(output/"analysis_receipt.json", provenance)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/"configs/netbci_behavior_sessions.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = analyze(args.config.resolve(), args.output.resolve())
    print(json.dumps({"behavior_subjects": summary["behavior_subjects"],
                      "EEG_subjects": summary["EEG_subjects"], "linked_sessions": summary["linked_sessions"],
                      "cohort_change": summary["cohort_behavior_change"]}, indent=2))


if __name__ == "__main__":
    main()
