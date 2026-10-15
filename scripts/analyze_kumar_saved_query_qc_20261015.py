#!/usr/bin/env python3
"""Exploratory QC sensitivity using saved predictions and frozen text metadata only.

No model or EEG library is imported. The pre-computation protocol is required.
Existing scientific results are read-only; every new output is exclusive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
import subprocess
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CPU_REL = Path("research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z")
SPLIT_REL = Path("research_logs/kumar_cross_session_20261012/protocol/split_manifest.json")
CONFIG_REL = Path("configs/kumar_cross_session_20261012.json")
COMPARISON_REL = Path("research_logs/kumar_frozen_query_comparison_20261015/run01")
CPU_METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda")
METHODS = (*CPU_METHODS, "always_frozen_eegnet")
SEEDS = (20261012, 20261013, 20261014)
SUBJECTS = tuple(f"sub-{i}" for i in range(1, 19))
DEV = ("sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16")
REMAINING = tuple(s for s in SUBJECTS if s not in DEV)
COHORTS = {"development6": DEV, "remaining12": REMAINING, "all18_secondary": SUBJECTS}
SESSIONS = tuple(f"ses-{i}" for i in range(6))
SUBSETS = ("all_included", "unflagged")
CONTRASTS = {
    "refit_minus_frozen": ("refit_csp_lda", "source_only"),
    "refit_minus_lda_only": ("refit_csp_lda", "frozen_csp_lda_recalibration"),
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def write_csv(path, rows):
    require(bool(rows), f"Empty output table: {path.name}")
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def exact_join(rows, expected, label_key, prediction_key):
    """Require one prediction per exact identity and matching frozen labels."""
    require(len(rows) == len(expected), "Prediction count differs from exact query set")
    ids = [row["trial_id"] for row in rows]
    require(len(ids) == len(set(ids)), "Duplicate prediction trial_id")
    require(set(ids) == set(expected), "Missing or unexpected prediction trial_id")
    joined = []
    for row in rows:
        meta = expected[row["trial_id"]]
        for field in ("subject", "session", "run"):
            require(row[field] == meta[field], f"Prediction metadata mismatch: {field}")
        if "role" in row:
            require(row["role"] == meta["role"], "Prediction role mismatch")
        require(int(row[label_key]) == int(meta["label"] == "right_hand"), "Frozen label mismatch")
        require(int(row[prediction_key]) in (0, 1), "Nonbinary saved prediction")
        joined.append(
            {
                "subject": meta["subject"],
                "cohort": meta["cohort"],
                "session": meta["session"],
                "run": meta["run"],
                "role": meta["role"],
                "trial_id": meta["trial_id"],
                "label": int(row[label_key]),
                "prediction": int(row[prediction_key]),
                "qc_peak_to_peak_over_250uv": meta["qc_peak_to_peak_over_250uv"],
            }
        )
    return joined


def score(rows):
    """BA is undefined with an absent true class; no silent class deletion."""
    cells = [[0, 0], [0, 0]]
    for row in rows:
        cells[row["label"]][row["prediction"]] += 1
    counts = [sum(row) for row in cells]
    predicted = [sum(cells[y][p] for y in (0, 1)) for p in (0, 1)]
    valid = min(counts) > 0
    return {
        "n_query": sum(counts),
        "n_left": counts[0],
        "n_right": counts[1],
        "predicted_left": predicted[0],
        "predicted_right": predicted[1],
        "confusion_00": cells[0][0],
        "confusion_01": cells[0][1],
        "confusion_10": cells[1][0],
        "confusion_11": cells[1][1],
        "balanced_accuracy": float(np.mean([cells[y][y] / counts[y] for y in (0, 1)]))
        if valid
        else None,
        "BA_defined": valid,
        "undefined_reason": "" if valid else "absent_true_class",
        "fewer_than_5_per_class": min(counts) < 5,
        "class_collapse": min(predicted) == 0 if sum(counts) else None,
    }


def aggregate_seeds(values, expected_seeds):
    require(len(values) == len(expected_seeds), "Missing seed; cannot average available seeds")
    require({v["seed"] for v in values} == set(expected_seeds), "Seed coverage differs")
    count_fields = ("n_query", "n_left", "n_right")
    require(
        all(len({v[field] for v in values}) == 1 for field in count_fields),
        "Seed query composition differs",
    )
    valid = all(v["BA_defined"] for v in values)
    return {
        **{field: values[0][field] for field in count_fields},
        "balanced_accuracy": float(np.mean([v["balanced_accuracy"] for v in values]))
        if valid
        else None,
        "BA_defined": valid,
        "undefined_reason": "" if valid else "absent_true_class",
        "fewer_than_5_per_class": values[0]["fewer_than_5_per_class"],
        "seeds_included": len(expected_seeds),
        "class_collapsed_seed_groups": sum(v["class_collapse"] is True for v in values),
    }


def participant_endpoint(session_rows):
    """Preserve the five-session estimand; never average fewer sessions."""
    require(len(session_rows) == 5, "Missing target session row")
    require({r["session"] for r in session_rows} == set(SESSIONS[1:]), "Wrong target sessions")
    missing = [r["session"] for r in session_rows if not r["BA_defined"]]
    return {
        "target_five_session_mean_BA": None
        if missing
        else float(np.mean([r["balanced_accuracy"] for r in session_rows])),
        "target_endpoint_defined": not missing,
        "target_undefined_sessions": ";".join(missing),
        "n_defined_target_sessions": len(session_rows) - len(missing),
        "target_query_trials": sum(r["n_query"] for r in session_rows),
        "target_left": sum(r["n_left"] for r in session_rows),
        "target_right": sum(r["n_right"] for r in session_rows),
        "low_count_target_sessions": sum(r["fewer_than_5_per_class"] for r in session_rows),
    }


def bootstrap(values):
    """Participant resampling; caller supplies lexicographic participant order."""
    array = np.asarray(values, dtype=np.float64)
    if len(array) == 0:
        return {"mean": None, "ci95_low": None, "ci95_high": None}
    if len(array) < 2:
        return {"mean": float(array.mean()), "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(42)
    means = array[rng.integers(0, len(array), (10000, len(array)))].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return {"mean": float(array.mean()), "ci95_low": float(low), "ci95_high": float(high)}


class Reader:
    def __init__(self):
        self.inputs = {}

    def raw(self, path):
        data = path.read_bytes()
        self.inputs[str(path.resolve())] = {"bytes": len(data), "sha256": digest(data)}
        return data

    def json(self, path):
        return json.loads(self.raw(path))

    def csv(self, path):
        return list(csv.DictReader(io.StringIO(self.raw(path).decode("utf-8-sig"))))

    def historical_entries(self, path):
        receipt = self.json(path)
        require(
            receipt["status"] == "completed" and receipt["readback_mode"] == "all",
            "Historical backup not closed",
        )
        entries = {r["relative_path"]: r for r in receipt["files"]}
        require(len(entries) == len(receipt["files"]), "Duplicate historical R2 paths")
        return entries

    def verify_historical(self, path, relative_path, entries):
        require(relative_path in entries, f"Historical receipt missing {relative_path}")
        data = self.raw(path)
        record = entries[relative_path]
        require(
            record["sha256"] == digest(data) and record["bytes"] == len(data),
            "Saved prediction historical hash mismatch",
        )
        require(
            record["verification"] == "full_get_sha256_verified"
            and record["readback_bytes"] == len(data),
            "Historical full GET mismatch",
        )

    def assert_unchanged(self):
        for filename, original in self.inputs.items():
            data = Path(filename).read_bytes()
            require(
                original == {"bytes": len(data), "sha256": digest(data)},
                f"Read-only input changed: {filename}",
            )


def load_original_predictions(reader, root, eeg, query):
    cpu_entries = reader.historical_entries(
        root / "research_logs/recovery_20261014/kumar_results_R2_run01.json"
    )
    eeg_entries = reader.historical_entries(
        root
        / "research_logs/kumar_frozen_query_execution_audit_20261015/run01/r2_full_get_receipt.json"
    )
    worker = reader.json(eeg / "worker_complete.json")
    require(
        worker["job_count"] == 54 and len(worker["jobs"]) == 54,
        "Incomplete saved EEG model identity set",
    )
    predictions, join_checks = [], []
    for subject in SUBJECTS:
        expected = {r["trial_id"]: r for r in query if r["subject"] == subject}
        cpu_path = root / CPU_REL / subject / "query_predictions.csv"
        reader.verify_historical(cpu_path, f"{subject}/query_predictions.csv", cpu_entries)
        cpu = reader.csv(cpu_path)
        require({r["method"] for r in cpu} == set(CPU_METHODS), "CPU method coverage differs")
        for method in CPU_METHODS:
            selected = [r for r in cpu if r["method"] == method]
            require(
                all(r["synthetic"] == "False" for r in selected),
                "Synthetic row in real CPU results",
            )
            joined = exact_join(selected, expected, "label", "prediction")
            predictions.extend({**r, "method": method, "seed": "cpu_fixed"} for r in joined)
            join_checks.append(
                {
                    "subject": subject,
                    "method": method,
                    "seed": "cpu_fixed",
                    "exact_query_identity_count": len(joined),
                }
            )
        jobs = [r for r in worker["jobs"] if r["subject"] == subject]
        require([r["seed"] for r in jobs] == list(SEEDS), "EEG seed coverage/order differs")
        for job in jobs:
            path = eeg / job["path"]
            reader.verify_historical(path, "results/" + job["path"], eeg_entries)
            result = reader.json(path)
            require(
                reader.inputs[str(path.resolve())]["sha256"] == job["sha256"],
                "Saved EEG worker result hash mismatch",
            )
            require(
                result["identity"]["job_id"] == job["job_id"], "Saved EEG job identity mismatch"
            )
            require(
                result["new_fit"] is False
                and result["optimizer_steps"] == 0
                and result["state_before_sha256"] == result["state_after_sha256"],
                "Historical query read-only state mismatch",
            )
            require(
                all(r["seed"] == job["seed"] for r in result["predictions"]),
                "Prediction seed mismatch",
            )
            joined = exact_join(result["predictions"], expected, "y_true", "y_pred")
            predictions.extend(
                {**r, "method": "always_frozen_eegnet", "seed": str(job["seed"])} for r in joined
            )
            join_checks.append(
                {
                    "subject": subject,
                    "method": "always_frozen_eegnet",
                    "seed": str(job["seed"]),
                    "job_id": job["job_id"],
                    "exact_query_identity_count": len(joined),
                }
            )
    return predictions, join_checks


def current_commit(root):
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "not_a_git_checkout"


def load_portable_predictions(reader, portable, query):
    rows = reader.csv(portable / "saved_predictions.csv")
    expected_keys = {
        (s, m, str(seed))
        for s in SUBJECTS
        for m in METHODS
        for seed in (SEEDS if m == "always_frozen_eegnet" else ("cpu_fixed",))
    }
    groups = defaultdict(list)
    for row in rows:
        groups[(row["subject"], row["method"], row["seed"])].append(row)
    require(set(groups) == expected_keys, "Public method/seed/participant coverage differs")
    predictions, checks = [], []
    for (subject, method, seed), selected in groups.items():
        expected = {r["trial_id"]: r for r in query if r["subject"] == subject}
        for row in selected:
            require(
                row["qc_peak_to_peak_over_250uv"] in ("True", "False"), "Nonboolean public QC flag"
            )
            require(
                (row["qc_peak_to_peak_over_250uv"] == "True")
                == expected[row["trial_id"]]["qc_peak_to_peak_over_250uv"],
                "Public QC flag differs",
            )
        joined = exact_join(selected, expected, "label", "prediction")
        predictions.extend({**r, "method": method, "seed": seed} for r in joined)
        checks.append(
            {
                "subject": subject,
                "method": method,
                "seed": seed,
                "exact_query_identity_count": len(joined),
            }
        )
    return predictions, checks


def export_public_inputs(
    reader, root, eeg, output, trials, predictions, config_path, old_endpoints_path
):
    public = output / "public_inputs"
    public.mkdir()
    fields = (
        "trial_id",
        "subject",
        "cohort",
        "session",
        "run",
        "role",
        "label",
        "included",
        "exclusion_reason",
        "raw_peak_to_peak_max_volts",
        "qc_peak_to_peak_over_250uv",
        "source_file",
        "source_row",
        "raw_file_sha256",
    )
    write_json(
        public / "frozen_trial_metadata.json",
        {"trials": [{k: r.get(k) for k in fields} for r in trials]},
    )
    write_csv(public / "saved_predictions.csv", predictions)
    for destination, source in [
        ("frozen_analysis_configuration.json", config_path),
        ("original_participant_endpoints.csv", old_endpoints_path),
    ]:
        with (public / destination).open("xb") as handle:
            handle.write(reader.raw(source))
    files = {
        p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
        for p in sorted(public.iterdir())
    }
    sources = []
    for filename, record in reader.inputs.items():
        path = Path(filename)
        if path.is_relative_to(root):
            relative, kind = str(path.relative_to(root)), "repository_text_input"
        elif path.is_relative_to(eeg):
            relative, kind = str(path.relative_to(eeg)), "accepted_saved_query_text_result"
        else:
            continue
        sources.append({"kind": kind, "relative_path": relative, **record})
    write_json(
        public / "public_input_provenance.json",
        {
            "status": "derived_exact_text_only_public_inputs",
            "created_utc": utc_now(),
            "dataset": "NEMAR nm000177 version 1.0.5",
            "source_data_license": "CC-BY-4.0",
            "no_EEG_no_weights_no_credentials": True,
            "prediction_rows": 25740,
            "unique_query_trials": 4290,
            "full_trial_metadata_rows": 7200,
            "compact_metadata_fields": list(fields),
            "files": files,
            "original_sources": sources,
            "derivation": "Exact stored labels, predictions and existing QC flags; no new model inference or QC rule.",
        },
    )


def compute(root, eeg, output, portable=None):
    started = utc_now()
    reader = Reader()
    reader.raw(output / "POST_OBSERVATION_PROTOCOL.md")
    reader.raw(Path(__file__))
    if portable is not None:
        provenance = reader.json(portable / "public_input_provenance.json")
        for filename, original in provenance["files"].items():
            require(Path(filename).name == filename, "Unsafe public input manifest filename")
            data = reader.raw(portable / filename)
            require(
                {"bytes": len(data), "sha256": digest(data)} == original,
                "Public input hash mismatch",
            )
    config_path = (
        root / CONFIG_REL if portable is None else portable / "frozen_analysis_configuration.json"
    )
    config = reader.json(config_path)
    require(
        config["quality_control"]["peak_to_peak_threshold_volts"] == 0.00025, "QC threshold changed"
    )
    require(
        config["statistics"]["bootstrap_replicates"] == 10000
        and config["statistics"]["seed"] == 42,
        "Statistical convention differs",
    )
    split_path = root / SPLIT_REL if portable is None else portable / "frozen_trial_metadata.json"
    split = reader.json(split_path)
    trials = split["trials"]
    require(
        len(trials) == 7200 and len({r["trial_id"] for r in trials}) == 7200,
        "Frozen event scope differs",
    )
    included = [r for r in trials if r["included"]]
    require(len(included) == 7156, "Frozen complete-window count differs")
    for row in included:
        require(type(row["qc_peak_to_peak_over_250uv"]) is bool, "QC flag missing/nonboolean")
        require(
            row["qc_peak_to_peak_over_250uv"] == (row["raw_peak_to_peak_max_volts"] > 0.00025),
            "Saved QC flag/amplitude mismatch",
        )
    require(
        sum(r["qc_peak_to_peak_over_250uv"] for r in included) == 1512, "Frozen QC total differs"
    )
    query_all = [r for r in trials if r["role"] in ("source_query", "target_query")]
    query = [r for r in query_all if r["included"]]
    require(len(query_all) == 4320 and len(query) == 4290, "Frozen query exclusion count differs")
    ledger = [
        {
            key: r.get(key)
            for key in (
                "trial_id",
                "subject",
                "cohort",
                "session",
                "run",
                "role",
                "label",
                "included",
                "exclusion_reason",
                "raw_peak_to_peak_max_volts",
                "qc_peak_to_peak_over_250uv",
            )
        }
        for r in query_all
    ]
    write_csv(output / "query_identity_qc_ledger.csv", ledger)
    counts = []
    for subject in SUBJECTS:
        for session in SESSIONS:
            for role in (
                "source_train",
                "source_validation",
                "source_query",
                "target_support",
                "target_query",
            ):
                group = [
                    r
                    for r in trials
                    if r["subject"] == subject and r["session"] == session and r["role"] == role
                ]
                complete = [r for r in group if r["included"]]
                counts.append(
                    {
                        "subject": subject,
                        "session": session,
                        "role": role,
                        "n_events": len(group),
                        "n_complete": len(complete),
                        "n_incomplete": len(group) - len(complete),
                        "n_flagged_complete": sum(
                            r["qc_peak_to_peak_over_250uv"] for r in complete
                        ),
                        "n_unflagged_complete": sum(
                            not r["qc_peak_to_peak_over_250uv"] for r in complete
                        ),
                    }
                )
    write_csv(output / "all_role_qc_counts.csv", counts)
    if portable is None:
        predictions, join_checks = load_original_predictions(reader, root, eeg, query)
    else:
        predictions, join_checks = load_portable_predictions(reader, portable, query)
    require(len(predictions) == 25740, "Complete prediction row count differs")
    write_csv(output / "joined_saved_predictions_qc.csv", predictions)
    write_json(
        output / "exact_join_validation.json",
        {
            "unique_included_queries": 4290,
            "excluded_queries_retained_in_ledger": 30,
            "prediction_rows": len(predictions),
            "method_seed_joins": join_checks,
            "failures": [],
        },
    )
    grouped = defaultdict(list)
    for row in predictions:
        grouped[(row["subject"], row["method"], row["seed"])].append(row)
    scored = []
    for (subject, method, seed), rows in grouped.items():
        for subset in SUBSETS:
            selected = (
                rows
                if subset == "all_included"
                else [r for r in rows if not r["qc_peak_to_peak_over_250uv"]]
            )
            for scope in (*SESSIONS, "pooled_target_queries", "pooled_all_queries"):
                eligible = (
                    selected
                    if scope == "pooled_all_queries"
                    else [r for r in selected if r["session"] != "ses-0"]
                    if scope == "pooled_target_queries"
                    else [r for r in selected if r["session"] == scope]
                )
                scored.append(
                    {
                        "subject": subject,
                        "cohort": "development6" if subject in DEV else "remaining12",
                        "method": method,
                        "seed": seed,
                        "subset": subset,
                        "session": scope,
                        **score(eligible),
                    }
                )
    write_csv(output / "per_seed_session_and_pooled_metrics.csv", scored)
    aggregate_groups = defaultdict(list)
    for row in scored:
        aggregate_groups[(row["subject"], row["method"], row["subset"], row["session"])].append(row)
    aggregate = []
    for (subject, method, subset, session), rows in aggregate_groups.items():
        seeds = [str(s) for s in SEEDS] if method == "always_frozen_eegnet" else ["cpu_fixed"]
        aggregate.append(
            {
                "subject": subject,
                "cohort": "development6" if subject in DEV else "remaining12",
                "method": method,
                "subset": subset,
                "session": session,
                **aggregate_seeds(rows, seeds),
            }
        )
    write_csv(output / "per_participant_session_metrics.csv", aggregate)
    aggregate_map = {(r["subject"], r["method"], r["subset"], r["session"]): r for r in aggregate}
    endpoints = []
    for subject in SUBJECTS:
        for method in METHODS:
            for subset in SUBSETS:
                target = [aggregate_map[(subject, method, subset, s)] for s in SESSIONS[1:]]
                source = aggregate_map[(subject, method, subset, "ses-0")]
                pooled = aggregate_map[(subject, method, subset, "pooled_all_queries")]
                target_pooled = aggregate_map[(subject, method, subset, "pooled_target_queries")]
                endpoints.append(
                    {
                        "subject": subject,
                        "cohort": "development6" if subject in DEV else "remaining12",
                        "method": method,
                        "subset": subset,
                        **participant_endpoint(target),
                        "source_query_BA": source["balanced_accuracy"],
                        "pooled_all_query_BA": pooled["balanced_accuracy"],
                        "pooled_target_query_BA": target_pooled["balanced_accuracy"],
                    }
                )
    write_csv(output / "participant_endpoints.csv", endpoints)
    endpoint_map = {(r["subject"], r["method"], r["subset"]): r for r in endpoints}
    comparisons = []
    old_endpoints_path = (
        root / COMPARISON_REL / "per_participant_endpoints.csv"
        if portable is None
        else portable / "original_participant_endpoints.csv"
    )
    for saved in reader.csv(old_endpoints_path):
        actual = endpoint_map[(saved["subject"], saved["method"], "all_included")]
        for field in ("source_query_BA", "target_five_session_mean_BA"):
            error = abs(actual[field] - float(saved[field]))
            require(
                error < 1e-14, f"Original all-query endpoint mismatch: {saved['subject']} {field}"
            )
            comparisons.append(
                {
                    "subject": saved["subject"],
                    "method": saved["method"],
                    "endpoint": field,
                    "absolute_difference": error,
                }
            )
    summaries = []
    for cohort, subjects in COHORTS.items():
        for method in METHODS:
            for subset in SUBSETS:
                for endpoint in (
                    "source_query_BA",
                    "target_five_session_mean_BA",
                    "pooled_all_query_BA",
                    "pooled_target_query_BA",
                ):
                    rows = [endpoint_map[(s, method, subset)] for s in sorted(subjects)]
                    eligible = [r for r in rows if r[endpoint] is not None]
                    summaries.append(
                        {
                            "cohort": cohort,
                            "method": method,
                            "subset": subset,
                            "endpoint": endpoint,
                            "n_expected_participants": len(subjects),
                            "n_eligible_participants": len(eligible),
                            "eligible_subjects": ";".join(r["subject"] for r in eligible),
                            "ineligible_subjects": ";".join(
                                r["subject"] for r in rows if r[endpoint] is None
                            ),
                            **bootstrap([r[endpoint] for r in eligible]),
                            "bootstrap_draws": 10000,
                            "bootstrap_seed": 42,
                        }
                    )
    write_csv(output / "cohort_method_sensitivity_summary.csv", summaries)
    paired_session, paired_participant = [], []
    for subject in SUBJECTS:
        for subset in SUBSETS:
            for contrast, (positive, negative) in CONTRASTS.items():
                a, b = (
                    endpoint_map[(subject, positive, subset)],
                    endpoint_map[(subject, negative, subset)],
                )
                valid = a["target_endpoint_defined"] and b["target_endpoint_defined"]
                paired_participant.append(
                    {
                        "subject": subject,
                        "cohort": "development6" if subject in DEV else "remaining12",
                        "subset": subset,
                        "contrast": contrast,
                        "paired_endpoint_defined": valid,
                        "mean_difference": a["target_five_session_mean_BA"]
                        - b["target_five_session_mean_BA"]
                        if valid
                        else None,
                        "undefined_sessions": a["target_undefined_sessions"]
                        or b["target_undefined_sessions"],
                    }
                )
                for session in SESSIONS:
                    x, y = (
                        aggregate_map[(subject, positive, subset, session)],
                        aggregate_map[(subject, negative, subset, session)],
                    )
                    valid_session = x["BA_defined"] and y["BA_defined"]
                    paired_session.append(
                        {
                            "subject": subject,
                            "cohort": "development6" if subject in DEV else "remaining12",
                            "subset": subset,
                            "contrast": contrast,
                            "session": session,
                            "n_left": x["n_left"],
                            "n_right": x["n_right"],
                            "paired_BA_defined": valid_session,
                            "paired_difference": x["balanced_accuracy"] - y["balanced_accuracy"]
                            if valid_session
                            else None,
                        }
                    )
    write_csv(output / "paired_session_contrasts.csv", paired_session)
    write_csv(output / "paired_participant_contrasts.csv", paired_participant)
    contrast_summaries, influence, subset_changes = [], [], []
    for cohort, subjects in COHORTS.items():
        for contrast in CONTRASTS:
            for subset in SUBSETS:
                all_rows = [
                    r
                    for r in paired_participant
                    if r["subject"] in subjects
                    and r["subset"] == subset
                    and r["contrast"] == contrast
                ]
                eligible = sorted(
                    [r for r in all_rows if r["paired_endpoint_defined"]],
                    key=lambda r: r["subject"],
                )
                values = [r["mean_difference"] for r in eligible]
                result = bootstrap(values)
                contrast_summaries.append(
                    {
                        "cohort": cohort,
                        "contrast": contrast,
                        "subset": subset,
                        "n_expected_participants": len(subjects),
                        "n_eligible_participants": len(eligible),
                        "eligible_subjects": ";".join(r["subject"] for r in eligible),
                        "ineligible_subjects": ";".join(
                            r["subject"] for r in all_rows if not r["paired_endpoint_defined"]
                        ),
                        **result,
                        "participants_positive": sum(v > 0 for v in values),
                        "participants_zero": sum(v == 0 for v in values),
                        "participants_negative": sum(v < 0 for v in values),
                    }
                )
                for omitted in eligible:
                    retained = [
                        r["mean_difference"] for r in eligible if r["subject"] != omitted["subject"]
                    ]
                    influence.append(
                        {
                            "cohort": cohort,
                            "contrast": contrast,
                            "subset": subset,
                            "omitted_subject": omitted["subject"],
                            "omitted_subject_difference": omitted["mean_difference"],
                            "n_retained": len(retained),
                            "full_eligible_mean": result["mean"],
                            "leave_one_out_mean": float(np.mean(retained)) if retained else None,
                            "change_in_mean_when_omitted": float(np.mean(retained)) - result["mean"]
                            if retained
                            else None,
                        }
                    )
            for subject in sorted(subjects):
                both = [
                    next(
                        r
                        for r in paired_participant
                        if r["subject"] == subject
                        and r["contrast"] == contrast
                        and r["subset"] == subset
                    )
                    for subset in SUBSETS
                ]
                valid = all(r["paired_endpoint_defined"] for r in both)
                subset_changes.append(
                    {
                        "cohort": cohort,
                        "contrast": contrast,
                        "subject": subject,
                        "paired_across_subsets_defined": valid,
                        "all_included_difference": both[0]["mean_difference"],
                        "unflagged_difference": both[1]["mean_difference"],
                        "unflagged_minus_all_difference": both[1]["mean_difference"]
                        - both[0]["mean_difference"]
                        if valid
                        else None,
                    }
                )
    write_csv(output / "cohort_paired_contrasts.csv", contrast_summaries)
    write_csv(output / "leave_one_participant_out_influence.csv", influence)
    write_csv(output / "participant_cross_subset_changes.csv", subset_changes)
    cross_subset_summary = []
    for cohort, subjects in COHORTS.items():
        for contrast in CONTRASTS:
            rows = [
                r for r in subset_changes if r["cohort"] == cohort and r["contrast"] == contrast
            ]
            eligible = [r for r in rows if r["paired_across_subsets_defined"]]
            cross_subset_summary.append(
                {
                    "cohort": cohort,
                    "contrast": contrast,
                    "n_expected_participants": len(subjects),
                    "n_eligible_participants": len(eligible),
                    "eligible_subjects": ";".join(r["subject"] for r in eligible),
                    "ineligible_subjects": ";".join(
                        r["subject"] for r in rows if not r["paired_across_subsets_defined"]
                    ),
                    **bootstrap([r["unflagged_minus_all_difference"] for r in eligible]),
                }
            )
    write_csv(output / "paired_cross_subset_summary.csv", cross_subset_summary)
    if portable is None:
        export_public_inputs(
            reader, root, eeg, output, trials, predictions, config_path, old_endpoints_path
        )
    reader.assert_unchanged()
    write_json(
        output / "input_manifest.json",
        {"files": reader.inputs, "all_read_inputs_unchanged_after_analysis": True},
    )
    receipt = {
        "status": "completed",
        "analysis": "post_observation_exploratory_saved_prediction_QC_sensitivity",
        "started_utc": started,
        "completed_utc": utc_now(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "reference_git_commit": current_commit(root),
        "input_mode": "original_saved_results_with_historical_R2_hash_checks"
        if portable is None
        else "hash_verified_compact_public_inputs",
        "protocol_sha256": digest((output / "POST_OBSERVATION_PROTOCOL.md").read_bytes()),
        "script_sha256": digest(Path(__file__).read_bytes()),
        "inputs_count": len(reader.inputs),
        "unique_complete_windows": 7156,
        "flagged_complete_windows": 1512,
        "query_included": 4290,
        "query_historical_exclusions": 30,
        "flagged_query_included": sum(r["qc_peak_to_peak_over_250uv"] for r in query),
        "unflagged_query_included": sum(not r["qc_peak_to_peak_over_250uv"] for r in query),
        "flagged_query_by_role": dict(
            Counter(r["role"] for r in query if r["qc_peak_to_peak_over_250uv"])
        ),
        "prediction_rows_exactly_joined": len(predictions),
        "method_seed_joins": len(join_checks),
        "session_or_pool_seed_metric_rows": len(scored),
        "undefined_seed_metric_rows": sum(not r["BA_defined"] for r in scored),
        "undefined_participant_target_endpoints": sum(
            not r["target_endpoint_defined"] for r in endpoints
        ),
        "all_query_endpoint_reconstruction_checks": len(comparisons),
        "maximum_all_query_endpoint_reconstruction_difference": max(
            r["absolute_difference"] for r in comparisons
        ),
        "all_read_inputs_unchanged": True,
        "raw_EEG_or_weights_read": False,
        "new_model_fits": 0,
        "new_model_forwards": 0,
        "failures": [],
        "limitations": [
            "Query exclusion does not remove artifacts from original training/validation/support fitting data.",
            "Unflagged is not certified artifact-free; QC does not establish task-phase alignment.",
            "Post-observation exploratory sensitivity; exposed test cohort; no rule selection or primary redefinition.",
            "Low class counts and undefined groups retained; cohort summaries use explicitly listed complete cases.",
        ],
    }
    write_json(output / "analysis_receipt.json", receipt)
    write_json(
        output / "original_endpoint_reconstruction.json", {"rows": comparisons, "failures": []}
    )
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--eeg-results",
        type=Path,
        default=Path(
            "/workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--portable-inputs",
        type=Path,
        help="Compact public inputs directory; no private original paths are needed",
    )
    args = parser.parse_args()
    require(args.output.is_dir(), "Output/protocol directory must already exist")
    require(
        (args.output / "POST_OBSERVATION_PROTOCOL.md").is_file(),
        "Record exploratory protocol before execution",
    )
    try:
        result = compute(
            args.root.resolve(),
            args.eeg_results.resolve(),
            args.output.resolve(),
            args.portable_inputs.resolve() if args.portable_inputs else None,
        )
    except Exception as error:
        # Only the outer receipt boundary catches unexpected errors; it re-raises.
        # No scientific operation, fit retry or continuation exists in this script.
        write_json(
            args.output / "exception_receipt.json",
            {
                "status": "failed",
                "utc": utc_now(),
                "exception_type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
                "partial_outputs_preserved": True,
                "automatic_retry": False,
            },
        )
        raise
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
