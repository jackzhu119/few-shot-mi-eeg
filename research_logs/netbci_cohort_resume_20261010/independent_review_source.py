"""Independent table arithmetic review; never imports the production pipeline.

Reads small saved tables and receipts only. Does not read EEG arrays, refit any
model, download data, or infer trial behavior from aggregate percentages.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, rankdata

LABELS = ("rest", "right_hand")
ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def record(value):
    return json.loads(Path(value).read_text())


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def same(actual, expected, message, tolerance=1e-10):
    if expected is None:
        require(actual in (None, "", "unavailable"), message)
    else:
        require(actual not in (None, "", "unavailable") and
                np.allclose(np.asarray(actual, dtype=float), expected, rtol=0,
                            atol=tolerance), message)


def confusions(rows):
    return np.array([[sum(row["true_label"] == truth and
                         row["prediction"] == predicted for row in rows)
                      for predicted in LABELS] for truth in LABELS], dtype=int)


def ba(rows):
    matrix = confusions(rows)
    if (matrix.sum(axis=1) == 0).any():
        return None
    return float(np.mean(np.diag(matrix) / matrix.sum(axis=1)))


def run_interval(rows, seed, repetitions):
    runs = sorted({row["run"] for row in rows})
    if len(runs) < 2:
        return None
    pools = {run: [row for row in rows if row["run"] == run] for run in runs}
    generator = np.random.default_rng(seed)
    scores = []
    for _ in range(repetitions):
        sampled = [row for run in generator.choice(runs, len(runs), replace=True)
                   for row in pools[run]]
        score = ba(sampled)
        if score is not None:
            scores.append(score)
    return np.percentile(scores, [2.5, 97.5]).tolist() if scores else None


def spectral(rows, session, band, runs, clean=False, reference="CAR"):
    suffix = "ROI_V2" if reference == "CAR" else "source_reference_ROI_V2"
    log_means, powers, totals, shortages = {}, {}, {}, []
    for label in LABELS:
        cells = [[float(row[f"{band}_{suffix}"]) for row in rows
                  if row["session"] == session and row["run"] == run and
                  row["label"] == label and (not clean or row["qc_flag"] == "False")]
                 for run in runs]
        shortages.extend(f"{session}/{run}/{label}" for run, cell in zip(runs, cells)
                         if not cell)
        totals[label] = sum(map(len, cells))
        log_means[label] = (float(np.mean([np.log10(cell).mean() for cell in cells]))
                            if all(cells) else None)
        powers[label] = (float(np.mean([np.mean(cell) for cell in cells])) * 1e12
                         if all(cells) else None)
    contrast = (10 * (log_means["right_hand"] - log_means["rest"])
                if not shortages else None)
    return {"contrast": contrast, "rest_power": powers["rest"],
            "MI_power": powers["right_hand"], "counts": totals, "missing": shortages}


def subject_interval(values, seed, repetitions):
    values = np.asarray(values, dtype=float)
    generator = np.random.default_rng(seed)
    draws = generator.integers(0, len(values), (repetitions, len(values)))
    sampled = values[draws]
    counts = np.isfinite(sampled).sum(axis=1)
    bootstrap = np.nansum(sampled, axis=1)[counts > 0] / counts[counts > 0]
    return np.percentile(bootstrap, [2.5, 97.5]).tolist() if len(bootstrap) else [None, None]


def verify_matching(subject, rows, directory, config):
    statuses = record(directory / "matched_variants_status.json")
    geometry = table(directory / "matched_geometry.tsv") if (directory / "matched_geometry.tsv").exists() else []
    spectra = table(directory / "matched_spectral_contrasts.tsv") if (directory / "matched_spectral_contrasts.tsv").exists() else []
    notes = []
    for status in statuses:
        variant = status["variant"]
        runs = config["expected_runs"] if variant == "all_six_runs" else config["qc_matched_runs"]
        require(status["runs"] == runs, f"{subject} {variant}: run identity")
        pools = {(session, run, label): [index for index, row in enumerate(rows)
                 if row["session"] == session and row["run"] == run and row["label"] == label
                 and (variant == "all_six_runs" or row["qc_flag"] == "False")]
                 for session in config["session_order"] for run in runs for label in LABELS}
        shortages = [{"session": session, "run": run, "label": label,
                      "n_available": len(pool), "n_required": config["matched_trials_per_class_per_run"]}
                     for (session, run, label), pool in pools.items()
                     if len(pool) < config["matched_trials_per_class_per_run"]]
        saved = [row for row in geometry if row["variant"] == variant]
        saved_spectra = [row for row in spectra if row["variant"] == variant]
        require((status["status"] == "unavailable") == bool(shortages),
                f"{subject} {variant}: unavailable condition")
        if shortages:
            require(not saved and not saved_spectra and status["preset_not_relaxed"] is True,
                    f"{subject} {variant}: partial metric retained")
            payload = status["error"].split("Insufficient preset matched cells: ", 1)
            require(len(payload) == 2 and json.loads(payload[1]) == shortages,
                    f"{subject} {variant}: exact shortage cells")
            notes.append({"variant": variant, "status": "unavailable_retained", "shortages": shortages})
            continue
        index = {(int(row["repetition"]), row["session"]): row for row in saved}
        spectrum_index = {(int(row["repetition"]), row["session"], row["band"]): row
                          for row in saved_spectra}
        require(len(index) == len(saved) == config["matched_repetitions"] * 4,
                f"{subject} {variant}: repeated geometry count")
        require(len(spectrum_index) == len(saved_spectra) == config["matched_repetitions"] * 8,
                f"{subject} {variant}: repeated spectrum count")
        for repetition in range(config["matched_repetitions"]):
            generator = np.random.default_rng(config["seed"] + repetition)
            for session in config["session_order"]:
                chosen = [int(index) for run in runs for label in LABELS
                          for index in generator.choice(pools[session, run, label],
                                                        config["matched_trials_per_class_per_run"],
                                                        replace=False)]
                metric = index[repetition, session]
                require(int(metric["n_matched"]) == len(chosen) == len(runs) * 24,
                        f"{subject} {variant}: matched count")
                if session == config["session_order"][0]:
                    same(metric["AIRM_to_session01"], 0., f"{subject} descriptive reference AIRM", 1e-9)
                    same(metric["PCA_subspace_distance"], 0., f"{subject} descriptive reference PCA", 1e-7)
                for band in ("mu", "beta"):
                    values = np.array([float(rows[i][f"{band}_ROI_V2"]) for i in chosen])
                    labels = np.array([rows[i]["label"] for i in chosen])
                    difference = 10 * (np.log10(values[labels == "right_hand"]).mean() -
                                       np.log10(values[labels == "rest"]).mean())
                    same(metric[f"{band}_ROI_V2"], values.mean(), f"{subject} matched power", 1e-20)
                    same(spectrum_index[repetition, session, band]["MI_minus_rest_log_power_dB"],
                         difference, f"{subject} independent matched spectrum", 1e-10)
        notes.append({"variant": variant, "status": "available_reconstructed_from_saved_trials",
                      "repetitions": config["matched_repetitions"], "trials_per_session": len(runs) * 24})
    return notes


def validate_associations(directory, joined, matching, subjects):
    """Use SciPy's Pearson implementation on raw and tied-rank variable pairs."""
    receipt = record(directory / "association_receipt.json")
    for name, digest in receipt["output_sha256"].items():
        require(sha(directory / name) == digest, f"Association artifact hash {name}")
    for name, entry in receipt["input_sha256"].items():
        require(sha(entry["path"]) == entry["sha256"], f"Association input hash {name}")
    session_index = {(row["subject"], row["session"]): row for row in joined}
    geometry = {(row["subject"], row["session"]): row for row in matching if row["variant"] == "all_six_runs"}
    values = table(directory / "participant_association_values.tsv")
    estimates = table(directory / "association_estimates.tsv")
    expected_fields = ("CSP_BA_change_pp", "behavior_change_pp", "mu_task_contrast_change_dB",
                       "all_six_AIRM_session04", "all_six_PCA_subspace_session04")
    independently_derived = {}
    for subject in subjects:
        first, last = session_index[subject, "01"], session_index[subject, "04"]
        independently_derived[subject] = {
            "CSP_BA_change_pp": float(last["CSP_BA_percent"]) - float(first["CSP_BA_percent"]),
            "behavior_change_pp": float(last["mean_run_hit_percent"]) - float(first["mean_run_hit_percent"]),
            "mu_task_contrast_change_dB": float(last["mu_MI_minus_rest_dB"]) - float(first["mu_MI_minus_rest_dB"]),
            "all_six_AIRM_session04": float(geometry[subject, "04"]["AIRM_to_session01"]),
            "all_six_PCA_subspace_session04": float(geometry[subject, "04"]["PCA_subspace_distance"]),
        }
    require(len(values) == 10 and {row["subject"] for row in values} == set(subjects), "Association ten participant rows")
    for row in values:
        for field in expected_fields:
            same(row[field], independently_derived[row["subject"]][field], "Association source-derived variable")
    require(len(estimates) == 10 and len({(row["association"], row["estimator"]) for row in estimates}) == 10,
            "Five association pairs/two estimators")
    verified = []
    for row in estimates:
        require(row["x_metric"] in expected_fields and row["y_metric"] in expected_fields,
                "Association selected variables")
        x = np.array([independently_derived[subject][row["x_metric"]] for subject in subjects])
        y = np.array([independently_derived[subject][row["y_metric"]] for subject in subjects])
        draws = np.random.default_rng(42).integers(0, 10, (10000, 10))
        bx, by = x[draws], y[draws]
        if row["estimator"] == "Spearman_rho":
            x, y = rankdata(x), rankdata(y)
            bx, by = rankdata(bx, axis=1), rankdata(by, axis=1)
        else:
            require(row["estimator"] == "Pearson_r", "Known association estimator")
        point = float(pearsonr(x, y).statistic)
        distinct = np.array([len(set(indices.tolist())) >= 2 for indices in draws])
        nonconstant = np.ptp(bx, axis=1) > 0
        nonconstant &= np.ptp(by, axis=1) > 0
        valid = distinct & nonconstant
        boot = pearsonr(bx[valid], by[valid], axis=1).statistic
        ci = np.percentile(boot, [2.5, 97.5]).tolist()
        same(row["estimate"], point, "Independent association point")
        same([row["participant_bootstrap_CI95_low"], row["participant_bootstrap_CI95_high"]], ci,
             "Independent paired-participant association CI")
        require(int(row["n_complete_paired_participants"]) == 10 and
                int(row["bootstrap_valid_draws"]) == int(valid.sum()) and
                int(row["bootstrap_degenerate_draws"]) == int((~valid).sum()), "Association independent/degenerate counts")
        verified.append({"pair": row["association"], "estimator": row["estimator"], "estimate": point,
                         "participant_bootstrap_CI95": ci, "participants": 10, "valid_draws": int(valid.sum())})
    return {"status": "passed_independent_SciPy_table_recomputation", "estimates": verified,
            "receipt_sha256": sha(directory / "association_receipt.json"),
            "limits": "Five exploratory pairs; no causal interpretation or hypothesis confirmation."}


def validate(args):
    config = record(args.config)
    subjects, sessions = config["subjects"], config["session_order"]
    require(subjects == [f"sub-{i}" for i in range(1, 11)] and sessions == ["01", "02", "03", "04"],
            "Preset first-ten-ID/four-session sample")
    inputs = {"config": args.config}
    summary_receipt = record(args.summary / "summary_receipt.json")
    for name, digest in summary_receipt["output_sha256"].items():
        path = args.summary / name
        require(sha(path) == digest, f"Summary artifact hash {name}")
        inputs[f"summary/{name}"] = path
    for name, information in summary_receipt["input_sha256"].items():
        require(sha(information["path"]) == information["sha256"], f"Summary input hash {name}")
    inputs["summary/summary_receipt.json"] = args.summary / "summary_receipt.json"
    behavior_path = ROOT / "research_logs/netbci2026_sources/original_dataverse/participants.tsv"
    inputs["official_behavior_table"] = behavior_path
    behavior = {row["participant_id"]: row for row in table(behavior_path)}
    require(len(behavior) == 19, "Original nineteen behavior participants")
    joined = table(args.summary / "participant_session_join.tsv")
    join_index = {(row["subject"], row["session"]): row for row in joined}
    require(len(joined) == len(join_index) == 40, "Unique forty session joins")
    sensitivity = table(args.summary / "spectral_reference_QC_sensitivity.tsv")
    metrics = ("mean_run_hit_percent", "CSP_BA_percent", "mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB",
               "mu_rest_power_uV2", "mu_MI_power_uV2", "beta_rest_power_uV2", "beta_MI_power_uV2")
    matrices = {metric: [] for metric in metrics}
    subject_results, constants, counts, exclusions, common = [], [], [], [], None
    for subject in subjects:
        directory = args.analysis_root / subject / "run01"
        if not directory.exists():
            directory = args.analysis_root / subject
        audit_directory = args.audit_root / subject
        audit = record(audit_directory / "audit.json")
        adapter = record(audit_directory / "adapter_receipt.json")
        analysis = record(directory / "analysis_receipt.json")
        require(audit["summary"]["all_checks_pass"] and analysis["synthetic"] is False,
                f"{subject}: actual audited participant")
        require(sha(args.config) == analysis["config_sha256"], f"{subject}: fixed config")
        require(analysis["bundle_sha256"] == adapter["epochs_sha256"] and
                analysis["metadata_sha256"] == adapter["metadata_sha256"], f"{subject}: exact audited bundle")
        for name, digest in analysis["outputs"].items():
            path = directory / name
            require(sha(path) == digest, f"{subject}: analysis artifact hash {name}")
            inputs[f"{subject}/{name}"] = path
        for name in ("audit.json", "adapter_receipt.json", "source_events.tsv", "excluded_events.tsv",
                     "events.tsv", "run_inventory.tsv", "original_header_inventory.tsv"):
            inputs[f"{subject}/audit/{name}"] = audit_directory / name
        inputs[f"{subject}/analysis_receipt.json"] = directory / "analysis_receipt.json"
        names = analysis["channel_names"]
        if common is None:
            common = names
        require(names == common and len(common) == 74 and analysis["sampling_frequency_hz"] == 250,
                f"{subject}: shared ordered coordinate system")
        trials, events, predictions = (table(directory / name) for name in
                                       ("trial_features.tsv", "event_inventory.tsv", "predictions.tsv"))
        require(len(trials) == len(events) == analysis["trials"] and
                [r["trial_id"] for r in events] == [r["trial_id"] for r in trials], f"{subject}: trial identity")
        event_index = {r["trial_id"]: r for r in events}
        source_events = table(audit_directory / "source_events.tsv")
        excluded_events = table(audit_directory / "excluded_events.tsv")
        eligible_events = [row for row in source_events if row["fixed_window_eligible"] == "True"]
        require(len(source_events) == audit["summary"]["total_source_trials"] == adapter["total_source_trials"] and
                len(eligible_events) == audit["summary"]["total_trials"] == len(events) and
                len(excluded_events) == audit["summary"]["excluded_trial_count"] == adapter["excluded_trial_count"] and
                excluded_events == [row for row in source_events if row["fixed_window_eligible"] == "False"] and
                [row["trial_id"] for row in eligible_events] == [row["trial_id"] for row in events],
                f"{subject}: source/eligible/excluded identity and counts")
        original_tables = {}
        for row in source_events:
            relative = row["source_file"].replace("_eeg.edf", "_events.tsv")
            if relative not in original_tables:
                source_path = ROOT / config["source_root"] / relative
                original_tables[relative] = table(source_path)
                inputs[f"{subject}/official_events/{relative}"] = source_path
            original_row = original_tables[relative][int(row["tsv_row"]) - 1]
            require(row["label"] == original_row["trial_type"] and
                    int(row["stored_event_value"]) == int(original_row["value"]) and
                    int(row["start_sample"]) == int(original_row["sample"]), f"{subject}: original event identity")
            same(row["onset_s"], float(original_row["onset"]), f"{subject}: original event onset")
            same(row["duration_s"], float(original_row["duration"]), f"{subject}: original event duration")
            length = round(float(original_row["duration"]) * 250)
            eligible = length == round(config["fixed_window_duration_seconds"] * 250)
            require(int(row["source_length_samples"]) == length and
                    int(row["stop_sample_exclusive"]) == int(row["start_sample"]) + length and
                    (row["fixed_window_eligible"] == "True") == eligible and
                    row["exclusion_reason"] == ("" if eligible else "source_event_duration_does_not_match_fixed_window"),
                    f"{subject}: exact-window eligibility rule")
        require(sum(map(len, original_tables.values())) == len(source_events), f"{subject}: complete source event census")
        exclusions.extend(excluded_events)
        train = [r["trial_id"] for r in events if r["session"] == "01" and r["run"] in ("01", "02", "03", "04")]
        query = {r["trial_id"] for r in events if r["trial_id"] not in set(train)}
        require({r["trial_id"] for r in predictions} == query and len(predictions) == len(query),
                f"{subject}: exhaustive disjoint queries")
        for prediction in predictions:
            event = event_index[prediction["trial_id"]]
            require(all(prediction[key] == event[key] for key in ("subject", "session", "run")) and
                    prediction["true_label"] == event["label"] and prediction["prediction"] in LABELS,
                    f"{subject}: prediction source identity")
        transform = record(directory / "transform_audit.json")
        model = record(directory / "CSP_LDA_model_audit.json")
        require(transform["source_train_trial_ids"] == model["source_train_trial_ids"] == train and
                transform["scaler_fit_source_only"] and transform["reference_PCA_fit_source_only"] and
                not transform["target_prediction_transforms_fitted"] and model["fit_calls"] == 1 and
                model["parameter_sha256_before"] == model["parameter_sha256_after"] == sha(directory / "csp_lda.pkl"),
                f"{subject}: source training and model freezing")
        decoder = {row["session"]: row for row in record(directory / "decoder_results.json")}
        original = audit["upstream_mapping"]["original_subject"]
        require(original in behavior and audit["upstream_mapping"]["actual_headers_hash_verified"] == 24,
                f"{subject}: explicit original-source mapping")
        participant = {metric: [] for metric in metrics}
        session_results = []
        for session in sessions:
            result = decoder[session]
            selected = [row for row in predictions if row["session"] == session]
            expected_runs = {"05", "06"} if session == "01" else set(config["expected_runs"])
            require({row["run"] for row in selected} == expected_runs and result["train_n"] == len(train),
                    f"{subject}/{session}: preset run roles")
            matrix, score = confusions(selected), ba(selected)
            require(matrix.tolist() == result["confusion_matrix_rest_right_hand"], f"{subject}/{session}: confusion")
            same(result["balanced_accuracy"], score, f"{subject}/{session}: BA")
            ci = run_interval(selected, config["seed"], config["bootstrap_run_repetitions"])
            same(result["conditional_run_bootstrap_CI95"], ci, f"{subject}/{session}: complete-run bootstrap")
            flagged = {row["trial_id"] for row in trials if row["qc_flag"] == "True"}
            clean = [row for row in selected if row["trial_id"] not in flagged]
            same(result["qc_unflagged_BA"], ba(clean), f"{subject}/{session}: clean BA")
            constant = len({row["prediction"] for row in selected}) == 1
            require(constant == result["constant_prediction"], f"{subject}/{session}: constant flag")
            if constant:
                constants.append({"subject": subject, "session": session, "label": selected[0]["prediction"]})
            published = ast.literal_eval(behavior[original][f"BCI-Performance-session{int(session)}"])
            require(len(published) == 6 and all(0 <= float(x) <= 100 for x in published), f"{original}: source scores")
            participant["mean_run_hit_percent"].append(float(np.mean(published)))
            participant["CSP_BA_percent"].append(100 * score if score is not None else np.nan)
            for band in ("mu", "beta"):
                values = spectral(trials, session, band, config["expected_runs"])
                participant[f"{band}_MI_minus_rest_dB"].append(values["contrast"])
                participant[f"{band}_rest_power_uV2"].append(values["rest_power"])
                participant[f"{band}_MI_power_uV2"].append(values["MI_power"])
            joined_row = join_index[subject, session]
            source_selected = [row for row in source_events if row["session"] == session]
            excluded_selected = [row for row in excluded_events if row["session"] == session]
            require(int(joined_row["n_EEG_source_events"]) == len(source_selected) and
                    int(joined_row["n_EEG_excluded_events"]) == len(excluded_selected),
                    f"{subject}/{session}: join source/exclusion counts")
            for metric in metrics:
                same(joined_row[metric], participant[metric][-1], f"{subject}/{session}: {metric} source recomputation")
            session_results.append({"session": session, "n_query": len(selected), "n_runs": len(expected_runs),
                                    "BA": score, "confusion_rest_right_hand": matrix.tolist(),
                                    "conditional_run_CI95": ci, "constant_prediction": constant})
        for row in (row for row in sensitivity if row["subject"] == subject):
            recomputed = spectral(trials, row["session"], row["band"], row["runs"].split(","),
                                  row["exclude_qc_flagged"] == "True", row["reference"])
            same(row["MI_minus_rest_log_power_dB"], recomputed["contrast"], f"{subject}: reference/QC contrast")
            same(row["rest_equal_run_arithmetic_power_uV2"], recomputed["rest_power"], f"{subject}: rest arithmetic")
            same(row["MI_equal_run_arithmetic_power_uV2"], recomputed["MI_power"], f"{subject}: MI arithmetic")
            require(row["missing_cells"] == ",".join(recomputed["missing"]), f"{subject}: spectral absent cells")
        matching = verify_matching(subject, trials, directory, config)
        for metric in metrics:
            matrices[metric].append(participant[metric])
        counts.append({"subject": subject, "source_events": len(source_events),
                       "excluded_events": len(excluded_events),
                       "analysis_trials": len(trials), "train_trials": len(train),
                       "query_trials": len(predictions), "qc_flagged": len(flagged)})
        subject_results.append({"subject": subject, "original_subject": original,
                                "sessions": session_results, "matched_sampling": matching})
    session_statistics = {(row["metric"], row["session"]): row for row in table(args.summary / "cohort_session_statistics.tsv")}
    change_statistics = {row["metric"]: row for row in table(args.summary / "cohort_paired_changes.tsv")}
    individual_statistics = {(row["subject"], row["metric"]): row for row in table(args.summary / "participant_first_last_changes.tsv")}
    result_changes = []
    for metric in metrics:
        matrix = np.asarray(matrices[metric], dtype=float)
        for position, session in enumerate(sessions):
            saved = session_statistics[metric, session]
            values = matrix[:, position]
            interval = subject_interval(values, config["seed"], config["bootstrap_subject_repetitions"])
            same(saved["mean"], np.nanmean(values), f"{metric}/{session}: participant mean")
            same([saved["subject_bootstrap_CI95_low"], saved["subject_bootstrap_CI95_high"]], interval,
                 f"{metric}/{session}: participant interval")
        difference = matrix[:, -1] - matrix[:, 0]
        interval = subject_interval(difference, config["seed"], config["bootstrap_subject_repetitions"])
        saved = change_statistics[metric]
        same(saved["mean_change"], np.nanmean(difference), f"{metric}: paired mean")
        same([saved["subject_bootstrap_CI95_low"], saved["subject_bootstrap_CI95_high"]], interval,
             f"{metric}: paired interval")
        require(int(saved["n_paired_subjects"]) == int(np.isfinite(difference).sum()), f"{metric}: paired n")
        for i, subject in enumerate(subjects):
            same(individual_statistics[subject, metric]["last_minus_first"], difference[i], f"{metric}: retained individual")
        result_changes.append({"metric": metric, "mean_change": float(np.nanmean(difference)),
                               "subject_bootstrap_CI95": interval, "paired_n": int(np.isfinite(difference).sum()),
                               "individual_changes": dict(zip(subjects, difference.tolist()))})
    matching_rows = table(args.summary / "participant_matched_geometry.tsv")
    matching_statistics = {(row["variant"], row["metric"], row["session"]): row
                           for row in table(args.summary / "cohort_matched_statistics.tsv")}
    matching_fields = ("AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance",
                       "mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB")
    require(len(matching_rows) == 80, "Two matching variants/four sessions/ten participants")
    matching_index = {(row["subject"], row["variant"], row["session"]): row for row in matching_rows}
    require(len(matching_index) == len(matching_rows), "Unique matching summary cells")
    for subject in subjects:
        directory = args.analysis_root / subject / "run01"
        geometry = table(directory / "matched_geometry.tsv")
        spectral_rows = table(directory / "matched_spectral_contrasts.tsv")
        for variant in ("all_six_runs", "qc_common_four_runs"):
            for session in sessions:
                saved = matching_index[subject, variant, session]
                rows = [row for row in geometry if row["variant"] == variant and row["session"] == session]
                band_rows = [row for row in spectral_rows if row["variant"] == variant and row["session"] == session]
                for field in matching_fields:
                    if field in ("mu_MI_minus_rest_dB", "beta_MI_minus_rest_dB"):
                        band = field.split("_", 1)[0]
                        values = [float(row["MI_minus_rest_log_power_dB"]) for row in band_rows if row["band"] == band]
                    else:
                        values = [float(row[field]) for row in rows]
                    same(saved[field], float(np.mean(values)) if values else None,
                         f"{subject}/{variant}/{session}: within-person repetition mean")
    for variant in ("all_six_runs", "qc_common_four_runs"):
        for field in matching_fields:
            for session in sessions:
                values = np.array([float(matching_index[subject, variant, session][field])
                                   if matching_index[subject, variant, session][field] else np.nan
                                   for subject in subjects])
                saved = matching_statistics[variant, field, session]
                valid = np.isfinite(values)
                interval = subject_interval(values, config["seed"], config["bootstrap_subject_repetitions"])
                same(saved["mean"], float(values[valid].mean()) if valid.any() else None,
                     f"{variant}/{field}/{session}: participant matching mean")
                same([saved["subject_bootstrap_CI95_low"], saved["subject_bootstrap_CI95_high"]], interval,
                     f"{variant}/{field}/{session}: participant matching interval")
                require(int(saved["n_available_subjects"]) == int(valid.sum()) and
                        saved["unavailable_subjects"] == ",".join(np.array(subjects)[~valid]),
                        f"{variant}/{field}/{session}: unavailable subject retained")
    final_summary = record(args.summary / "cohort_summary.json")
    require(final_summary["source_events"] == sum(row["source_events"] for row in counts) and
            final_summary["trials"] == sum(row["analysis_trials"] for row in counts) and
            final_summary["excluded_source_events_n"] == len(exclusions), "Cohort source/eligible/excluded totals")
    require(final_summary["constant_prediction_sessions_by_session"] ==
            {session: sum(row["session"] == session for row in constants)
             for session in sessions if any(row["session"] == session for row in constants)},
            "Cohort constant prediction totals")
    associations = (validate_associations(args.associations, joined, matching_rows, subjects)
                    if args.associations else {"status": "not_requested"})
    return {"status": "passed_independent_saved_table_arithmetic_and_methods_review", "synthetic": False,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "participants": len(subjects),
            "session_joins": len(joined), "counts": counts,
            "source_events": sum(row["source_events"] for row in counts),
            "eligible_analysis_trials": sum(row["analysis_trials"] for row in counts),
            "excluded_source_events": exclusions,
            "associations": associations,
            "constant_prediction_sessions": constants, "paired_changes": result_changes,
            "subject_validation": subject_results,
            "independent_of_production_helpers": True, "EEG_arrays_loaded": False, "models_refitted": False,
            "verified": ["source/query event identity and complete run roles", "raw original six-score session means",
                         "saved confusion matrices and BA including constant predictions", "conditional whole-run BA intervals",
                         "equal-run CAR and source-reference task contrast arithmetic", "QC spectral sensitivity missing cells",
                         "matched sampling identities/cell shortages and matched spectral arithmetic",
                         "whole-participant session and paired-change bootstrap intervals", "audit/bundle/model/config/artifact hashes",
                         "full source event census and explicit full-window exclusion identities",
                         "matched repetition means and participant intervals with metric-specific unavailable people retained"],
            "limits": ["Signal extraction and numerical filtering/PSD values were reviewed in source code, not independently rerun on raw EEG.",
                       "Saved geometric distance arithmetic was not recomputed from EEG; descriptive reference zeros and matched counts were checked.",
                       "Model fitting correctness is source-reviewed and receipt/hash-checked; classifiers were not independently refitted.",
                       "Percentages remain subject/session observations with unresolved run order, denominator and trial outcome.",
                       "Conditional run CIs omit training uncertainty; first-ten-ID subject CIs are exploratory, not population representativeness.",
                       "No independent biological replication, causal human-learning or retention evidence is established."],
            "input_sha256": {name: {"path": str(path.resolve()), "sha256": sha(path)} for name, path in inputs.items()},
            "review_source_sha256": sha(__file__),
            "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "runtime": {"python": platform.python_version(), "numpy": np.__version__}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--associations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Preserve previous review output")
    result = validate(args)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "participants": result["participants"],
                      "session_joins": result["session_joins"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
