"""Summarize verified NETBCI participant trajectories without downloads or fitting.

Each participant is an independent unit. Session scores are unweighted means of
published run percentages, never trial outcomes. Task-window power contrasts are
not baseline ERD; frozen-decoder failure is not human skill loss. Figures retain
individual participants and explicitly report metric availability.
"""
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
from learning_preserving_bci.datasets.netbci_behavior import join_verified_sessions, read_behavior_sessions
from learning_preserving_bci.utils.reproducibility import collect_provenance

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = ("01", "02", "03", "04")
LABELS = ("rest", "right_hand")
BEHAVIOR_ROOT = ROOT / "research_logs/netbci2026_sources/original_dataverse"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_table(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_table(path, rows):
    if not rows:
        return
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def finite_or_none(value):
    if value is None or value == "unavailable":
        return None
    number = float(value)
    require(np.isfinite(number), "Nonfinite metric must be explicitly unavailable")
    return number


def participant_statistics(rows, subjects, sessions, metrics, seed, repetitions):
    """Resample complete subject trajectories; never trials or repeated subsamples."""
    require(len(subjects) == len(set(subjects)) and bool(subjects), "Duplicate/empty participant list")
    index = {(row["subject"], row["session"]): row for row in rows}
    require(len(index) == len(rows), "Duplicate participant/session key")
    require(set(index) == {(subject, session) for subject in subjects for session in sessions},
            "Incomplete or unexpected participant/session coverage")
    require(repetitions >= 1, "Positive participant bootstrap count required")
    summary, changes, individual, matrices = [], [], [], {}
    for metric in metrics:
        matrix = np.array([[np.nan if finite_or_none(index[s, t].get(metric)) is None
                            else float(index[s, t][metric]) for t in sessions] for s in subjects])
        matrices[metric] = matrix
        # A single draw matrix keeps within-person and cross-session dependence.
        rng = np.random.default_rng(seed)
        draws = rng.integers(0, len(subjects), (repetitions, len(subjects)))
        for position, session in enumerate(sessions):
            values = matrix[:, position]
            available = np.isfinite(values)
            valid = values[available]
            # All requested subjects are retained in the draws, with missing metric
            # cells omitted only from that metric's descriptive mean. Report n.
            samples = values[draws]
            denominators = np.isfinite(samples).sum(axis=1)
            boot = np.nansum(samples, axis=1)[denominators > 0] / denominators[denominators > 0]
            interval = np.quantile(boot, [.025, .975]).tolist() if len(boot) else [None, None]
            summary.append({"metric": metric, "session": session, "n_requested_subjects": len(subjects),
                            "n_available_subjects": len(valid), "mean": float(valid.mean()) if len(valid) else None,
                            "median": float(np.median(valid)) if len(valid) else None,
                            "subject_bootstrap_CI95_low": interval[0], "subject_bootstrap_CI95_high": interval[1],
                            "unavailable_subjects": ",".join(np.array(subjects)[~available]),
                            "CI_scope": "participant-resampling conditional on first-ten-ID sample; not causal"})
        delta = matrix[:, -1] - matrix[:, 0]
        valid = np.isfinite(delta)
        values = delta[valid]
        # Paired changes are computed before resampling; no subtraction of two
        # independently bootstrapped session means and no trial pseudoreplication.
        samples = delta[draws]
        denominators = np.isfinite(samples).sum(axis=1)
        boot = np.nansum(samples, axis=1)[denominators > 0] / denominators[denominators > 0]
        interval = np.quantile(boot, [.025, .975]).tolist() if len(boot) else [None, None]
        change = {"metric": metric, "contrast": f"session{sessions[-1]}_minus_session{sessions[0]}",
                  "n_requested_subjects": len(subjects), "n_paired_subjects": len(values),
                  "mean_change": float(values.mean()) if len(values) else None,
                  "median_change": float(np.median(values)) if len(values) else None,
                  "min_change": float(values.min()) if len(values) else None,
                  "max_change": float(values.max()) if len(values) else None,
                  "n_increased": int((values > 1e-10).sum()), "n_decreased": int((values < -1e-10).sum()),
                  "n_unchanged": int((np.abs(values) <= 1e-10).sum()),
                  "subject_bootstrap_CI95_low": interval[0], "subject_bootstrap_CI95_high": interval[1],
                  "unavailable_subjects": ",".join(np.array(subjects)[~valid]),
                  "bootstrap_repetitions": repetitions,
                  "CI_scope": "paired participants; exploratory observational contrast"}
        changes.append(change)
        individual.extend({"subject": subject, "metric": metric,
                           "first_session_value": finite_or_none(matrix[i, 0]) if np.isfinite(matrix[i, 0]) else None,
                           "last_session_value": finite_or_none(matrix[i, -1]) if np.isfinite(matrix[i, -1]) else None,
                           "last_minus_first": float(delta[i]) if valid[i] else None,
                           "status": "available" if valid[i] else "unavailable_retained"}
                          for i, subject in enumerate(subjects))
    return summary, changes, individual, matrices


def equal_run_spectral(trials, sessions, runs, exclude_flagged=False, reference="CAR"):
    """Equal run weighting within each task; preserve absent cells as unavailable."""
    rows = []
    suffix = "ROI_V2" if reference == "CAR" else "source_reference_ROI_V2"
    for session in sessions:
        for band in ("mu", "beta"):
            means, powers, counts, missing = {}, {}, {}, []
            for label in LABELS:
                log_means, arithmetic, ns = [], [], []
                for run in runs:
                    selected = [row for row in trials if row["session"] == session and row["run"] == run
                                and row["label"] == label and (not exclude_flagged or row["qc_flag"] == "False")]
                    if not selected:
                        missing.append(f"{session}/{run}/{label}")
                        continue
                    values = np.array([float(row[f"{band}_{suffix}"]) for row in selected])
                    require(np.isfinite(values).all() and (values > 0).all(), "Invalid positive spectral power")
                    log_means.append(float(np.log10(values).mean()))
                    arithmetic.append(float(values.mean()) * 1e12)
                    ns.append(len(values))
                means[label] = float(np.mean(log_means)) if len(log_means) == len(runs) else None
                powers[label] = float(np.mean(arithmetic)) if len(arithmetic) == len(runs) else None
                counts[label] = sum(ns)
            rows.append({"session": session, "band": band, "reference": reference,
                         "runs": ",".join(runs), "exclude_qc_flagged": exclude_flagged,
                         "status": "unavailable_missing_cell" if missing else "available",
                         "missing_cells": ",".join(missing), "n_rest": counts["rest"], "n_MI": counts["right_hand"],
                         "MI_minus_rest_log_power_dB": None if missing else 10*(means["right_hand"]-means["rest"]),
                         "rest_equal_run_arithmetic_power_uV2": powers["rest"],
                         "MI_equal_run_arithmetic_power_uV2": powers["right_hand"],
                         "interpretation": "task_window_contrast_not_baseline_ERD_or_neural_learning"})
    return rows


def verify_predictions(predictions, decoder, events, config):
    """Reject accidentally reused pilot partitions and retain constant predictions."""
    event_index = {row["trial_id"]: row for row in events}
    require(len(event_index) == len(events), "Duplicate event ID")
    require(len({row["trial_id"] for row in predictions}) == len(predictions), "Duplicate prediction ID")
    scores = {row["session"]: row for row in decoder}
    require(len(scores) == len(decoder), "Duplicate decoder session")
    require(set(scores) == set(config["session_order"]), "Incomplete decoder session coverage")
    for session in config["session_order"]:
        runs = config["source_query_runs"] if session == config["session_order"][0] else config["later_query_runs"]
        expected = {row["trial_id"] for row in events if row["session"] == session and row["run"] in runs}
        selected = [row for row in predictions if row["session"] == session]
        require({row["trial_id"] for row in selected} == expected,
                "Frozen query coverage differs from preset cohort partition; do not reuse pilot targets")
        for row in selected:
            event = event_index[row["trial_id"]]
            require(all(row[key] == event[key] for key in ("subject", "session", "run")), "Prediction identity mismatch")
            require(row["true_label"] == event["label"] and row["prediction"] in LABELS, "Prediction label mismatch")
        matrix = np.array([[sum(row["true_label"] == truth and row["prediction"] == pred for row in selected)
                            for pred in LABELS] for truth in LABELS])
        score = scores[session]
        require(matrix.tolist() == score["confusion_matrix_rest_right_hand"], "Saved confusion matrix mismatch")
        require(len(selected) == score["n_test"], "Saved decoder sample count mismatch")
        constant = len({row["prediction"] for row in selected}) == 1
        require(constant == score["constant_prediction"], "Constant prediction flag mismatch")
        if (matrix.sum(axis=1) > 0).all():
            ba = float(np.mean(np.diag(matrix) / matrix.sum(axis=1)))
            require(np.isclose(ba, score["balanced_accuracy"], rtol=0, atol=1e-12), "Saved BA mismatch")
        else:
            require(score["balanced_accuracy"] is None, "Missing query class cannot support BA")


def verify_hashes(directory, receipt, required):
    for name in required:
        require(name in receipt["outputs"], f"Missing output hash: {name}")
        require(file_sha256(directory / name) == receipt["outputs"][name], f"Analysis output hash mismatch: {name}")


def load_participant(subject, config_path, config, analysis_root, audit_root):
    inputs = {}
    analysis_dir = analysis_root / subject
    if not (analysis_dir / "analysis_receipt.json").is_file():
        analysis_dir = analysis_dir / "run01"
    audit_dir = audit_root / subject
    inputs["analysis_receipt"] = analysis_dir / "analysis_receipt.json"
    inputs["audit"] = audit_dir / "audit.json"
    audit = json.loads(inputs["audit"].read_text())
    require(audit["summary"]["subject"] == subject and audit["summary"]["all_checks_pass"] is True,
            "Failed or wrong-subject data audit")
    require(audit["synthetic"] is False, "Synthetic audit cannot enter actual cohort summary")
    mapping = audit["upstream_mapping"]
    require(mapping["derivative_subject"] == subject and
            mapping["actual_headers_hash_verified"] == mapping["declared_original_headers"] == 24,
            "Original header identity not fully verified")
    original = mapping["original_subject"]
    analysis = json.loads(inputs["analysis_receipt"].read_text())
    require(analysis["synthetic"] is False and analysis["subject"] == subject, "Analysis subject/synthetic mismatch")
    require(analysis["status"] in ("completed_exploratory", "completed_with_scientific_failures"),
            "EEG analysis incomplete; report failure before cohort interpretation")
    require(analysis["config_sha256"] == file_sha256(config_path), "Analysis config SHA mismatch")
    for name in ("adapter_receipt.json", "events.tsv", "run_inventory.tsv"):
        inputs[f"audit/{name}"] = audit_dir / name
        require(file_sha256(inputs[f"audit/{name}"]) == audit["output_artifact_sha256"][name],
                f"Audit artifact hash mismatch: {name}")
    adapter = json.loads(inputs["audit/adapter_receipt.json"].read_text())
    require(analysis["bundle_sha256"] == adapter["epochs_sha256"] and
            analysis["metadata_sha256"] == adapter["metadata_sha256"], "Analysis bundle differs from audited adapter")
    require(analysis["trials"] == audit["summary"]["total_trials"] == adapter["trial_count"], "EEG trial counts disagree")
    require(analysis["channel_names"] == adapter["channel_names"], "EEG channel mapping differs")
    required = ["event_inventory.tsv", "trial_features.tsv", "matched_variants_status.json",
                "failures.json", "decoder_results.json", "transform_audit.json", "partitions.json"]
    for name in ("matched_geometry.tsv", "matched_spectral_contrasts.tsv", "predictions.tsv", "CSP_LDA_model_audit.json"):
        if (analysis_dir / name).exists():
            required.append(name)
    verify_hashes(analysis_dir, analysis, required)
    for name in required:
        inputs[name] = analysis_dir / name
    events = read_table(inputs["audit/events.tsv"])
    trials = read_table(inputs["trial_features.tsv"])
    analyzed_events = read_table(inputs["event_inventory.tsv"])
    require(len(events) == len(trials) == len(analyzed_events) == analysis["trials"], "Feature/event count mismatch")
    event_ids = [row["trial_id"] for row in events]
    require(len(set(event_ids)) == len(event_ids), "Duplicate audited event ID")
    require(event_ids == [row["trial_id"] for row in trials] == [row["trial_id"] for row in analyzed_events],
            "Feature/event identity order mismatch")
    for event, trial, analyzed in zip(events, trials, analyzed_events, strict=True):
        require(event["original_subject"] == original and event["subject"] == subject, "Original subject identity mismatch")
        require(all(event[key] == trial[key] == analyzed[key] for key in
                    ("subject", "session", "run", "label", "source_file", "trial_id")), "Feature/event metadata mismatch")
        require(trial["qc_flag"] in ("True", "False"), "Invalid saved QC flag")
    require({row["session"] for row in events} == set(config["session_order"]), "Session coverage mismatch")
    decoder = json.loads(inputs["decoder_results.json"].read_text())
    if decoder:
        require("predictions.tsv" in inputs and "CSP_LDA_model_audit.json" in inputs, "Decoder lacks immutable model evidence")
        verify_predictions(read_table(inputs["predictions.tsv"]), decoder, events, config)
        model = json.loads(inputs["CSP_LDA_model_audit.json"].read_text())
        require(model["query_state_unchanged"] is True and model["prediction_replay_exact"] is True and
                model["parameter_sha256_before"] == model["parameter_sha256_after"] and model["fit_calls"] == 1,
                "Frozen model state verification failed")
    else:
        require(any(row["scope"] == "CSP_LDA_fit_or_query" for row in json.loads(inputs["failures.json"].read_text())),
                "Unavailable decoder lacks recorded failure evidence")
    scores = {row["session"]: row for row in decoder}
    spectral = equal_run_spectral(trials, config["session_order"], config["expected_runs"])
    sensitivity = []
    for reference in ("CAR", "source_reference"):
        for name, runs, clean in (("all_six_runs_all_trials", config["expected_runs"], False),
                                  ("common_four_runs_all_trials", config["qc_matched_runs"], False),
                                  ("common_four_runs_qc_unflagged", config["qc_matched_runs"], True)):
            sensitivity.extend(dict(row, subject=subject, variant=name) for row in equal_run_spectral(
                trials, config["session_order"], runs, clean, reference))
    by_spectral = {(row["session"], row["band"]): row for row in spectral}
    sessions = []
    for session in config["session_order"]:
        selected = [row for row in trials if row["session"] == session]
        score = scores.get(session)
        sessions.append({"subject": subject, "session": session, "original_subject_from_audit": original,
                         "n_EEG_trials": len(selected), "n_EEG_runs": len({row["run"] for row in selected}),
                         "n_rest": sum(row["label"] == "rest" for row in selected),
                         "n_MI": sum(row["label"] == "right_hand" for row in selected),
                         "n_qc_flagged": sum(row["qc_flag"] == "True" for row in selected),
                         "CSP_BA_percent": 100*score["balanced_accuracy"] if score and score["balanced_accuracy"] is not None else None,
                         "CSP_constant_prediction": score["constant_prediction"] if score else "unavailable",
                         "CSP_query_n": score["n_test"] if score else 0,
                         "CSP_query_n_runs": score["n_runs"] if score else 0,
                         "CSP_conditional_run_CI95": json.dumps(score["conditional_run_bootstrap_CI95"] if score else None),
                         "CSP_status": "available" if score else "unavailable_retained",
                         **{f"{band}_MI_minus_rest_dB": by_spectral[session, band]["MI_minus_rest_log_power_dB"] for band in ("mu", "beta")},
                         **{f"{band}_{label}_power_uV2": by_spectral[session, band][f"{label}_equal_run_arithmetic_power_uV2"]
                            for band in ("mu", "beta") for label in ("rest", "MI")}})
    geometry = read_table(inputs["matched_geometry.tsv"]) if "matched_geometry.tsv" in inputs else []
    matched_spectral = read_table(inputs["matched_spectral_contrasts.tsv"]) if "matched_spectral_contrasts.tsv" in inputs else []
    statuses = json.loads(inputs["matched_variants_status.json"].read_text())
    matching_rows = []
    for status in statuses:
        variant = status["variant"]
        for session in config["session_order"]:
            chosen = [row for row in geometry if row["variant"] == variant and row["session"] == session]
            if status["status"] == "available":
                require(len(chosen) == config["matched_repetitions"] and
                        len({row["repetition"] for row in chosen}) == len(chosen), "Matched repetitions mismatch")
            else:
                require(not chosen, "Unavailable matching variant contains partial results")
            fields = ("AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance")
            matching_rows.append({"subject": subject, "session": session, "variant": variant,
                                  "status": status["status"], "error": status.get("error", ""),
                                  "n_subsample_repetitions": len(chosen),
                                  "n_matched_trials_per_repetition": int(chosen[0]["n_matched"]) if chosen else 0,
                                  **{field: float(np.mean([float(row[field]) for row in chosen])) if chosen else None for field in fields},
                                  **{f"{band}_MI_minus_rest_dB": float(np.mean([float(row["MI_minus_rest_log_power_dB"])
                                      for row in matched_spectral if row["variant"] == variant and row["session"] == session and row["band"] == band]))
                                      if chosen else None for band in ("mu", "beta")}})
    return original, sessions, sensitivity, matching_rows, inputs, analysis


def plot_results(output, subjects, sessions, trajectories, changes, individuals, matching):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    figure_dir = output / "figures"
    figure_dir.mkdir()
    x = np.arange(len(sessions)) + 1
    colors = plt.get_cmap("tab10")(np.arange(len(subjects)) % 10)
    layouts = [("mean_run_hit_percent", "Published online hit score (%)"),
               ("CSP_BA_percent", "Frozen CSP balanced accuracy (%)"),
               ("mu_MI_minus_rest_dB", "Mu MI − rest log-power (dB)"),
               ("beta_MI_minus_rest_dB", "Beta MI − rest log-power (dB)")]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for ax, (metric, title) in zip(axes.flat, layouts, strict=True):
        matrix = trajectories[metric]
        for i, subject in enumerate(subjects):
            ax.plot(x, matrix[i], "o-", color=colors[i], alpha=.65, linewidth=1, markersize=3, label=subject)
        means = np.nanmean(matrix, axis=0)
        ax.plot(x, means, "D-", color="black", linewidth=2.5, markersize=5, label="participant mean")
        ax.set(title=title, xticks=x, xticklabels=sessions, xlabel="Protocol session")
        ax.text(.02, .02, "available n=" + "/".join(map(str, np.isfinite(matrix).sum(axis=0))),
                transform=ax.transAxes, fontsize=8)
    axes[0, 1].axhline(50, linestyle="--", color="grey", linewidth=1)
    axes[1, 0].axhline(0, linestyle="--", color="grey", linewidth=1)
    axes[1, 1].axhline(0, linestyle="--", color="grey", linewidth=1)
    axes[0, 0].legend(fontsize=7, ncol=3)
    fig.suptitle(f"NETBCI: {len(subjects)} audited participants; exploratory longitudinal trajectories")
    fig.text(.5, .01, "Behavior: mean of six published run percentages, not pooled hit rate. CSP: session 01 query runs 05–06; later sessions all six.\n"
             "Power: equal run-weighted task-window contrast; no baseline ERD or human skill-retention inference.",
             ha="center", fontsize=8)
    fig.tight_layout(rect=[0, .055, 1, .95])
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"cohort_trajectories.{extension}", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, (metric, title) in zip(axes, layouts[:3], strict=True):
        selected = [row for row in individuals if row["metric"] == metric]
        values = np.array([np.nan if row["last_minus_first"] is None else row["last_minus_first"] for row in selected])
        for i in range(len(subjects)):
            ax.scatter(values[i], i, color=colors[i], s=35)
        change = next(row for row in changes if row["metric"] == metric)
        ax.axvline(0, color="grey", linestyle="--", linewidth=1)
        if change["mean_change"] is not None:
            ax.errorbar(change["mean_change"], len(subjects), xerr=np.array([
                [change["mean_change"]-change["subject_bootstrap_CI95_low"]],
                [change["subject_bootstrap_CI95_high"]-change["mean_change"]]]), fmt="D", color="black", capsize=3)
        ax.set(yticks=range(len(subjects)+1), yticklabels=subjects+["mean ± CI"],
               xlabel="Session 04 − session 01", title=title)
        ax.text(.02, .02, f"paired n={change['n_paired_subjects']}/{len(subjects)}", transform=ax.transAxes, fontsize=8)
    fig.suptitle("All individual changes retained; 95% percentile CI resamples paired participants")
    fig.tight_layout()
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"cohort_paired_changes.{extension}", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
    for row_number, variant in enumerate(("all_six_runs", "qc_common_four_runs")):
        for ax, field in zip(axes[row_number], ("AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance"), strict=True):
            index = {(row["subject"], row["session"]): row for row in matching if row["variant"] == variant}
            matrix = np.array([[np.nan if index[s, t][field] is None else index[s, t][field]
                                for t in sessions] for s in subjects])
            for i in range(len(subjects)):
                ax.plot(x, matrix[i], "o-", color=colors[i], alpha=.65, linewidth=1, markersize=3)
            if np.isfinite(matrix).any():
                with np.errstate(invalid="ignore"):
                    mean = np.nansum(matrix, axis=0)/np.maximum(np.isfinite(matrix).sum(axis=0), 1)
                ax.plot(x, mean, "D-", color="black", linewidth=2, markersize=4)
            ax.set(title=field, ylabel=variant, xticks=x, xticklabels=sessions, xlabel="Protocol session")
            ax.text(.02, .02, "available n=" + "/".join(map(str, np.isfinite(matrix).sum(axis=0))), transform=ax.transAxes, fontsize=8)
    fig.suptitle("Descriptive geometry; matched repetitions averaged within each participant")
    fig.text(.5, .01, "QC-common-four run matching uses preset cells/counts; unavailable participants remain recorded. Geometry change does not identify learning.", ha="center", fontsize=8)
    fig.tight_layout(rect=[0, .035, 1, .95])
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"cohort_geometry.{extension}", dpi=180)
    plt.close(fig)


def summarize(config_path, analysis_root, audit_root, output):
    started = time.monotonic()
    require(not output.exists(), "Prior summary exists; choose a new output directory")
    config = json.loads(config_path.read_text())
    subjects, sessions = config["subjects"], config["session_order"]
    require(tuple(sessions) == SESSIONS, "Protocol session order differs")
    inputs = {"config": config_path, "summary_script": Path(__file__),
              "behavior_source": BEHAVIOR_ROOT/"participants.tsv",
              "behavior_dictionary": BEHAVIOR_ROOT/"participants.json",
              "behavior_receipt": BEHAVIOR_ROOT/"behavior_receipt.json"}
    source_receipt = json.loads(inputs["behavior_receipt"].read_text())
    for key, checksum in (("behavior_source", source_receipt["official_checksum"]),
                          ("behavior_dictionary", source_receipt["behavior_dictionary"]["checksum"])):
        require(checksum["type"].upper() == "MD5" and
                hashlib.md5(inputs[key].read_bytes()).hexdigest() == checksum["value"], "Official behavior source MD5 mismatch")
    columns = {session: f"BCI-Performance-session{int(session)}" for session in sessions}
    dictionary = inputs["behavior_dictionary"].read_text()
    require(all(f'"{column}"' in dictionary for column in columns.values()), "Missing source session dictionary field")
    try:
        json.loads(dictionary)
        dictionary_status = "valid_strict_JSON"
    except json.JSONDecodeError as error:
        dictionary_status = f"invalid_strict_JSON_preserved: {error.msg}; line {error.lineno}"
    behavior, _ = read_behavior_sessions(inputs["behavior_source"], columns, 6)
    require(len({row["original_subject"] for row in behavior}) == 19, "Behavior source cohort count changed")
    mapping, eeg_sessions, spectral, matching, receipts = {}, [], [], [], []
    for subject in subjects:
        original, rows, bands, geometry, files, receipt = load_participant(
            subject, config_path, config, analysis_root, audit_root)
        require(original not in mapping.values(), "Duplicate original participant mapping")
        mapping[subject] = original
        eeg_sessions.extend(rows)
        spectral.extend(bands)
        matching.extend(geometry)
        inputs.update({f"{subject}/{key}": value for key, value in files.items()})
        receipts.append(receipt)
    require(len({row["script_sha256"] for row in receipts}) == 1, "Mixed analysis script versions")
    joined = join_verified_sessions(behavior, eeg_sessions, mapping)
    require(len(joined) == len(subjects)*len(sessions), "Subject/session join count changed")
    metrics = ["mean_run_hit_percent", "CSP_BA_percent", "mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB",
               "mu_rest_power_uV2", "mu_MI_power_uV2", "beta_rest_power_uV2", "beta_MI_power_uV2"]
    statistics, changes, individuals, matrices = participant_statistics(
        joined, subjects, sessions, metrics, config["seed"], config["bootstrap_subject_repetitions"])
    matching_stats = []
    for variant in ("all_six_runs", "qc_common_four_runs"):
        selected = [row for row in matching if row["variant"] == variant]
        stats, _, _, _ = participant_statistics(selected, subjects, sessions,
            ["AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance",
             "mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB"], config["seed"], config["bootstrap_subject_repetitions"])
        matching_stats.extend(dict(row, variant=variant) for row in stats)
    # Validate everything before making this new output directory. No partial prior
    # output is rewritten if data/source integrity fails.
    output.mkdir(parents=True)
    write_table(output / "participant_session_join.tsv", joined)
    write_table(output / "cohort_session_statistics.tsv", statistics)
    write_table(output / "participant_first_last_changes.tsv", individuals)
    write_table(output / "cohort_paired_changes.tsv", changes)
    write_table(output / "spectral_reference_QC_sensitivity.tsv", spectral)
    write_table(output / "participant_matched_geometry.tsv", matching)
    write_table(output / "cohort_matched_statistics.tsv", matching_stats)
    plot_results(output, subjects, sessions, matrices, changes, individuals, matching)
    summary = {"status": "actual_audited_first_ten_ID_cohort_exploratory", "synthetic": False,
               "subjects": subjects, "subject_map": mapping, "participants": len(subjects),
               "sessions": len(joined), "runs": sum(row["n_EEG_runs"] for row in joined),
               "trials": sum(row["n_EEG_trials"] for row in joined),
               "class_counts": {"rest": sum(row["n_rest"] for row in joined), "right_hand": sum(row["n_MI"] for row in joined)},
               "qc_flags_retained_in_primary": sum(row["n_qc_flagged"] for row in joined),
               "constant_prediction_sessions_by_session": dict(Counter(row["session"] for row in joined if row["CSP_constant_prediction"] is True)),
               "constant_prediction_participants": [s for s in subjects if any(row["subject"] == s and row["CSP_constant_prediction"] is True for row in joined)],
               "behavior_dictionary_syntax": dictionary_status, "behavior_source_subjects": 19,
               "behavior_analyzed_EEG_linked_subjects_only": len(subjects),
               "source_selection": config["selection"], "pilot_previously_seen": config["pilot_subject_previously_observed"],
               "behavior_grain": "verified_subject_session_unweighted_mean_of_six_reported_percentages",
               "score_run_order_denominator_trial_outcomes": "unresolved_no_broadcast",
               "session_statistics": statistics, "paired_changes": changes,
               "matching_availability": [{"subject": s, "variant": variant,
                    "status": next(row["status"] for row in matching if row["subject"] == s and row["variant"] == variant),
                    "error": next(row["error"] for row in matching if row["subject"] == s and row["variant"] == variant)}
                    for s in subjects for variant in ("all_six_runs", "qc_common_four_runs")],
               "interpretation": "observational spectral/geometry/decoder contrasts; no causal neural-learning or skill-retention conclusion"}
    write_json(output / "cohort_summary.json", summary)
    outputs = {path.relative_to(output).as_posix(): file_sha256(path) for path in sorted(output.rglob("*")) if path.is_file()}
    write_json(output / "summary_receipt.json", {"status": "actual_data_summary_completed", "synthetic": False,
               "config_sha256": file_sha256(config_path), "script_sha256": file_sha256(Path(__file__)),
               "input_sha256": {key: {"path": str(path.resolve()), "sha256": file_sha256(path)} for key, path in inputs.items()},
               "output_sha256": outputs, "provenance": collect_provenance(config["seed"], ROOT),
               "duration_seconds": time.monotonic()-started,
               "bootstrap_unit": "whole participant", "source_reference_and_QC_sensitivity_saved": True,
               "new_EEG_downloads": False, "new_model_fits": False, "figures_native_rendered": True,
               "figure_visual_inspection": "pending_view_image_review"})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.config, args.analysis_root, args.audit_root, args.output)
    print(json.dumps({"output": str(args.output), "participants": result["participants"], "trials": result["trials"]}))


if __name__ == "__main__":
    main()
