"""Pure CPU engine for the frozen post-exposure cue5s/activity2s comparison.

There is intentionally no standalone real-data execution switch. The existing
guarded CPU operation must supply verified arrays, source state and callbacks.
This module adds no claim, authorization or resource-monitoring framework.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import time

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_variable] = "1"

import numpy as np  # noqa: E402
from scipy.signal import butter, resample_poly, sosfiltfilt  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402

from learning_preserving_bci.decoders.csp_lda import make_csp_lda  # noqa: E402

WINDOWS = ("cue5s", "task2s")
METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda")
SESSIONS = tuple(f"ses-{index}" for index in range(1, 6))
LABELS = {"left_hand": 0, "right_hand": 1}
END_CODES = {"left_hand": {7692, 7693}, "right_hand": {7702, 7703}}
PROTOCOL_SHA256 = "1c3e87ad634148bde031579cd8efb976e75643635d452a2ea69d911ccc9b09fc"
ROOT = Path(__file__).resolve().parents[1]
PHASE_SETTINGS = {
    "window_seconds": 2.0,
    "start": "task_start",
    "end_condition": "task_end_at_or_after_window_end",
    "preserve_original_44_partial_exclusions": True,
    "compare_methods": list(METHODS),
    "require_all_five_sessions_for_endpoint": True,
    "query_scope": "common_eligible_identical_ids",
}


def truth(value):
    return value is True or value == "True"


def ids_hash(ids):
    return hashlib.sha256(json.dumps(list(ids), separators=(",", ":")).encode()).hexdigest()


def arrays_hash(arrays):
    digest = hashlib.sha256()
    for name, value in sorted(arrays.items()):
        value = np.ascontiguousarray(value)
        if value.dtype.hasobject:
            raise ValueError("Object arrays are forbidden")
        digest.update(json.dumps([name, value.dtype.str, list(value.shape)], separators=(",", ":")).encode())
        digest.update(b"\0")
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def preprocess_window(raw_epoch, window):
    expected = {"cue5s": 2560, "task2s": 1024}
    if window not in expected:
        raise ValueError("Unfrozen window")
    raw_epoch = np.asarray(raw_epoch, dtype=np.float64)
    if raw_epoch.shape != (22, expected[window]) or not np.isfinite(raw_epoch).all():
        raise ValueError("Invalid exact window shape or values")
    referenced = raw_epoch - raw_epoch.mean(axis=0, keepdims=True)
    sos = butter(4, [8, 30], btype="bandpass", fs=512, output="sos")
    result = resample_poly(sosfiltfilt(sos, referenced, axis=-1), 1, 4, axis=-1).astype(np.float32)
    if result.shape != (22, expected[window] // 4) or not np.isfinite(result).all():
        raise ValueError("Invalid processed activity window")
    return result


def materialize_window_arrays(selected, read_raw_epoch, *, saved_cue_epochs=None):
    """Caller verifies EDF/cache hashes; request only exact allowed intervals.

    The reader receives ``(trial_record, start, stop)`` and must return volts in
    the frozen 22-channel order. No validation or source-query role is read.
    """
    arrays = {window: {} for window in WINDOWS}
    permitted_roles = {"source_train", "target_support", "target_query"}
    for row in selected:
        if row["role"] not in permitted_roles:
            continue
        trial_id = row["trial_id"]
        if not row["eligible_common"]:
            raise ValueError("Ineligible trial reached window materialization")
        start = row["task_start_sample"]
        if start + 1024 > row["task_end_sample"]:
            raise ValueError("Activity extraction would cross verified task end")
        arrays["task2s"][trial_id] = preprocess_window(read_raw_epoch(row, start, start + 1024), "task2s")
        if saved_cue_epochs is None:
            cue = row["original_cue_start_sample"]
            arrays["cue5s"][trial_id] = preprocess_window(read_raw_epoch(row, cue, cue + 2560), "cue5s")
        else:
            cached = np.asarray(saved_cue_epochs[trial_id])
            if cached.shape != (22, 640) or cached.dtype != np.float32 or not np.isfinite(cached).all():
                raise ValueError("Frozen cue cache has invalid shape/dtype/values")
            arrays["cue5s"][trial_id] = cached
    return arrays


def select_common_trials(trials, phase_rows):
    """Return identical eligible identities for both windows, never refill roles."""
    if len({row["trial_id"] for row in trials}) != len(trials):
        raise ValueError("Duplicate frozen trial identity")
    mapping = {row["trial_id"]: row for row in phase_rows}
    if len(mapping) != len(phase_rows) or set(mapping) != {row["trial_id"] for row in trials}:
        raise ValueError("Phase inventory must include every frozen identity, including missing rows")
    selected, coverage = [], []
    for trial in trials:
        phase = mapping[trial["trial_id"]]
        if (phase["subject"], phase["session"], phase["run"], phase["class"]) != (
                trial["subject"], trial["session"], trial["run"], trial["label"]):
            raise ValueError("Frozen phase subject/session/run/class mismatch")
        reason = ""
        mapped = truth(phase.get("cue_mapping_exact")) and truth(phase.get("phase_mapping_success"))
        if not trial["included"] or trial["sample_count"] != 2560:
            reason = "original_partial_remains_excluded"
        elif not mapped:
            reason = "unknown_or_ambiguous_original_phase"
        else:
            if float(phase["sample_rate"]) != 512.0:
                raise ValueError("Original event clock differs from frozen 512Hz")
            cue = int(phase["cue_sample_0based"])
            start = int(phase["task_start_sample_0based"])
            end = int(phase["task_end_sample_0based"])
            if cue != trial["start_sample"] or int(phase["task_start_code"]) != 7691 + LABELS[trial["label"]] * 10:
                raise ValueError("Cue/task-start identity mismatch")
            if int(phase["task_end_code"]) not in END_CODES[trial["label"]] or not cue < start < end:
                raise ValueError("Task endpoint class or order mismatch")
            if end - start < 1024:
                reason = "active_phase_shorter_than_2s"
            elif start + 1024 > int(phase["recording_n_samples"]):
                reason = "task2s_exceeds_recording"
        record = {
            "trial_id": trial["trial_id"], "subject": trial["subject"],
            "session": trial["session"], "run": trial["run"], "role": trial["role"],
            "label": LABELS[trial["label"]], "cohort": trial["cohort"],
            "original_included": bool(trial["included"]), "phase_mapped": mapped,
            "eligible_common": not reason, "exclusion_reason": reason,
            "original_cue_start_sample": trial["start_sample"],
            "task_start_sample": int(phase["task_start_sample_0based"]) if mapped else None,
            "task_end_sample": int(phase["task_end_sample_0based"]) if mapped else None,
            "source_file": trial["source_file"],
        }
        coverage.append(record)
        if not reason:
            selected.append(record)
    return selected, coverage


def source_model_arrays(csp, lda):
    result = {"n_components": np.asarray(4, dtype=np.int64)}
    for prefix, estimator, fields in (
        ("csp", csp, ("filters_", "patterns_", "mean_", "std_")),
        ("lda", lda, ("classes_", "coef_", "intercept_", "means_", "priors_", "covariance_")),
    ):
        for field in fields:
            result[f"{prefix}_{field.removesuffix('_')}"] = np.asarray(getattr(estimator, field)).copy()
    return result


def features_from_arrays(arrays, X):
    filters = arrays["csp_filters"][:int(arrays["n_components"])]
    projected = np.asarray([np.dot(filters, epoch) for epoch in np.asarray(X, dtype=np.float64)])
    features = np.log(np.square(projected).mean(axis=-1))
    if not np.isfinite(features).all():
        raise ValueError("Nonfinite fixed-CSP features")
    return features


def predict_arrays(arrays, X):
    score = features_from_arrays(arrays, X) @ arrays["lda_coef"].T + arrays["lda_intercept"]
    if score.shape[1] != 1 or arrays["lda_classes"].tolist() != [0, 1]:
        raise ValueError("Expected frozen binary CSP4/LDA state")
    if not np.isfinite(score).all():
        raise ValueError("Nonfinite LDA prediction score")
    return arrays["lda_classes"][(score[:, 0] > 0).astype(int)]


def fit_arrays(X, y, source_arrays=None):
    """One fit only; caller catches LinAlgError, never filesystem/integrity errors."""
    if set(np.asarray(y).tolist()) != {0, 1} or len(y) < 4:
        raise ValueError("Preflight requires sufficient combined source/support classes")
    if source_arrays is None:
        pipeline = make_csp_lda(n_components=4)
        pipeline.fit(np.asarray(X, dtype=np.float64), y)
        return source_model_arrays(pipeline.named_steps["csp"], pipeline.named_steps["lda"])
    lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    lda.fit(features_from_arrays(source_arrays, X), y)
    arrays = {key: np.asarray(value).copy() for key, value in source_arrays.items()}
    for field in ("classes_", "coef_", "intercept_", "means_", "priors_", "covariance_"):
        arrays[f"lda_{field.removesuffix('_')}"] = np.asarray(getattr(lda, field)).copy()
    return arrays


def counts(rows):
    return {"left": sum(row["label"] == 0 for row in rows),
            "right": sum(row["label"] == 1 for row in rows)}


def _stack(window_arrays, rows, window):
    expected = 640 if window == "cue5s" else 256
    if not rows:
        return np.empty((0, 22, expected), dtype=np.float32)
    X = np.stack([window_arrays[row["trial_id"]] for row in rows])
    if X.shape != (len(rows), 22, expected) or not np.isfinite(X).all():
        raise ValueError("Window tensor identity/shape/integrity failure")
    return X


def evaluate_participant(*, subject, cohort, selected, coverage, window_arrays,
                         cue_source_arrays, saved_cue_frozen_predictions,
                         emit=None, model_sink=None, synthetic=False):
    """Run this participant under the caller's existing authorization/monitor.

    ``emit`` runs outside estimator exception handling. Any disk/hash/permission
    failure therefore propagates immediately, before another fit can start.
    """
    if not synthetic and (emit is None or model_sink is None):
        raise ValueError("Real execution requires persistent partial-evidence and private model sinks")
    emit = emit or (lambda record: None)
    model_sink = model_sink or (lambda arrays, context: None)
    if set(window_arrays) != set(WINDOWS):
        raise ValueError("Exactly the two frozen windows are required")
    if any(row["subject"] != subject for row in coverage + selected):
        raise ValueError("Cross-participant phase input")
    source = [row for row in selected if row["role"] == "source_train"]
    if len(source) != 40 or counts(source) != {"left": 20, "right": 20}:
        raise ValueError("The unchanged 40 source TRAIN identities/classes are required")
    permitted_roles = {"source_train", "target_support", "target_query"}
    selected = [row for row in selected if row["role"] in permitted_roles]
    required_ids = {row["trial_id"] for row in selected}
    for window in WINDOWS:
        if set(window_arrays[window]) != required_ids:
            raise ValueError("Both windows must contain exactly the same eligible fit/query identities")
    query_ids = {row["trial_id"] for row in selected if row["role"] == "target_query"}
    if set(saved_cue_frozen_predictions) != query_ids:
        raise ValueError("Saved frozen cue predictions must cover exactly the common target queries")
    source_hash = arrays_hash(cue_source_arrays)
    source_ids = [row["trial_id"] for row in source]
    y_source = np.asarray([row["label"] for row in source], dtype=np.int64)
    models = {"cue5s": cue_source_arrays}
    fit_audit = []

    def perform_fit(window, method, training, source_state=None):
        training_ids = [row["trial_id"] for row in training]
        if len(set(training_ids)) != len(training_ids):
            raise ValueError("Duplicate fit identity")
        if any(row["role"] not in {"source_train", "target_support"} for row in training):
            raise ValueError("Validation/query trial reached fit")
        target_sessions = {row["session"] for row in training if row["role"] == "target_support"}
        if len(target_sessions) > 1:
            raise ValueError("Prior/future target support reached fit")
        event = {"kind": "fit_attempt", "subject": subject, "window": window, "method": method,
                 "session": next(iter(target_sessions)) if target_sessions else "ses-0",
                 "fit_trial_ids": training_ids, "fit_ids_sha256": ids_hash(training_ids),
                 "fit_classes": counts(training), "synthetic": synthetic}
        emit(event)
        arrays = fit_arrays(_stack(window_arrays[window], training, window),
                            np.asarray([row["label"] for row in training], dtype=np.int64), source_state)
        if any(not np.isfinite(value).all() for value in arrays.values()):
            raise ValueError("Nonfinite newly fitted model state")
        fit_audit.append(event)
        model_sink(arrays, {**event, "parameter_sha256": arrays_hash(arrays)})
        emit({**event, "kind": "fit_complete", "parameter_sha256": arrays_hash(arrays)})
        return arrays

    task_source_error = None
    try:
        models["task2s"] = perform_fit("task2s", "source_only", source)
    except np.linalg.LinAlgError as error:
        task_source_error = str(error)
        emit({"kind": "expected_source_estimator_failure", "window": "task2s",
              "exception": type(error).__name__, "message": str(error), "synthetic": synthetic})
    rows, predictions = [], []
    for session in SESSIONS:
        query = [row for row in selected if row["role"] == "target_query" and row["session"] == session]
        support = [row for row in selected if row["role"] == "target_support" and row["session"] == session]
        original_query = [row for row in coverage if row["role"] == "target_query" and row["session"] == session]
        original_support = [row for row in coverage if row["role"] == "target_support" and row["session"] == session]
        unknown_query = [row for row in original_query if row["original_included"] and not row["phase_mapped"]]
        unknown_support = [row for row in original_support if row["original_included"] and not row["phase_mapped"]]
        query_count, support_count = counts(query), counts(support)
        qids, sids = [row["trial_id"] for row in query], [row["trial_id"] for row in support]
        for window in WINDOWS:
            base = models.get(window)
            for method in METHODS:
                fit_rows = source if method == "source_only" else source + support
                state, status, failure, applied = base, "defined", None, method
                fitted = False
                if not query or min(query_count.values()) == 0:
                    status = "undefined_query_missing_class"
                elif base is None:
                    status, failure = "undefined_source_model", task_source_error
                elif method != "source_only" and unknown_support:
                    status = "undefined_support_phase_access_incomplete"
                elif method != "source_only" and not support:
                    status, applied = "fallback_no_eligible_support", "source_only"
                    fit_rows = source
                elif method != "source_only":
                    try:
                        state = perform_fit(window, method, fit_rows,
                                            base if method == "frozen_csp_lda_recalibration" else None)
                        fitted = True
                    except np.linalg.LinAlgError as error:
                        status, applied, failure = "fallback_estimator_linear_algebra_failure", "source_only", str(error)
                        fit_rows = source
                        emit({"kind": "expected_estimator_failure", "window": window,
                              "session": session, "method": method, "exception": type(error).__name__,
                              "message": str(error), "synthetic": synthetic})
                row = {
                    "subject": subject, "cohort": cohort, "session": session, "window": window,
                    "method": method, "applied_action": applied, "status": status,
                    "synthetic": synthetic, "post_exposure_exploratory": True,
                    "n_original_query": len(original_query), "n_original_query_included": sum(r["original_included"] for r in original_query),
                    "n_unknown_query_phase": len(unknown_query), "n_common_query": len(query),
                    "n_query_left": query_count["left"], "n_query_right": query_count["right"],
                    "n_original_support": len(original_support), "n_unknown_support_phase": len(unknown_support),
                    "n_common_support": len(support), "n_support_left": support_count["left"],
                    "n_support_right": support_count["right"], "support_single_class": bool(support) and min(support_count.values()) == 0,
                    "query_ids_sha256": ids_hash(qids), "query_trial_ids": qids,
                    "common_support_ids_sha256": ids_hash(sids), "common_support_trial_ids": sids,
                    "fit_ids_sha256": ids_hash([r["trial_id"] for r in fit_rows]),
                    "fit_trial_ids": [r["trial_id"] for r in fit_rows],
                    "n_source_train": 40, "new_fit_performed": fitted,
                    "target_update_fit_performed": fitted,
                    "source_model_origin": "read_only_original_cue5s_state" if window == "cue5s" else "new_exploratory_task2s_source_cpu_fit",
                    "balanced_accuracy": None, "class_collapse": None,
                    "model_parameter_sha256_before": None, "model_parameter_sha256_after": None,
                    "prediction_sha256": None, "failure_message": failure,
                    "mapping_scope": "common_known_subset_with_unknown_query_rows_retained" if unknown_query else "all_original_query_phase_metadata_known",
                }
                if not status.startswith("undefined"):
                    before = arrays_hash(state)
                    X_query = _stack(window_arrays[window], query, window)
                    prediction = predict_arrays(state, X_query)
                    if window == "cue5s" and applied == "source_only":
                        saved = np.asarray([saved_cue_frozen_predictions[trial_id] for trial_id in qids])
                        if not np.array_equal(prediction, saved):
                            raise ValueError("Read-only frozen cue replay disagrees with saved original predictions")
                        prediction = saved
                    after = arrays_hash(state)
                    if before != after:
                        raise ValueError("Query inference mutated model state")
                    y_query = np.asarray([r["label"] for r in query])
                    ba = float(np.mean([np.mean(prediction[y_query == label] == label) for label in (0, 1)]))
                    row.update(balanced_accuracy=ba, class_collapse=len(set(prediction.tolist())) < 2,
                               model_parameter_sha256_before=before, model_parameter_sha256_after=after,
                               prediction_sha256=arrays_hash({"prediction": prediction}))
                    predictions.extend({"subject": subject, "session": session, "window": window,
                                        "method": method, "trial_id": r["trial_id"], "label": r["label"],
                                        "prediction": int(value), "synthetic": synthetic}
                                       for r, value in zip(query, prediction))
                rows.append(row)
                emit({"kind": "metric", **row})
    if arrays_hash(cue_source_arrays) != source_hash:
        raise ValueError("Read-only original cue source model changed")
    if len(rows) != 30:
        raise ValueError("Expected every five-session/two-window/three-action row")
    return {"metrics": rows, "predictions": predictions, "fit_access_audit": fit_audit,
            "source_train_ids": source_ids, "source_labels_sha256": arrays_hash({"y": y_source}),
            "original_cue_state_sha256_before": source_hash,
            "original_cue_state_sha256_after": arrays_hash(cue_source_arrays)}


def aggregate_participants(rows, *, bootstrap_replicates=10_000, seed=42):
    """Equal-session participant endpoints and paired pointwise bootstrap CIs."""
    if bootstrap_replicates != 10_000 or seed != 42:
        raise ValueError("Frozen exploratory bootstrap is 10000/seed42")
    keys = [(window, method) for window in WINDOWS for method in METHODS]
    subjects = sorted({row["subject"] for row in rows})
    endpoints = []
    for subject in subjects:
        for window, method in keys:
            group = [row for row in rows if (row["subject"], row["window"], row["method"]) == (subject, window, method)]
            if len(group) != 5 or {row["session"] for row in group} != set(SESSIONS):
                raise ValueError("A full five-session row inventory is required, including undefined cells")
            valid = all(row["balanced_accuracy"] is not None for row in group)
            endpoints.append({"subject": subject, "cohort": group[0]["cohort"], "window": window,
                              "method": method, "n_defined_sessions": sum(row["balanced_accuracy"] is not None for row in group),
                              "balanced_accuracy": float(np.mean([row["balanced_accuracy"] for row in group])) if valid else None,
                              "query_mapping_complete_all_sessions": all(row["n_unknown_query_phase"] == 0 for row in group)})
    contrasts = []

    def paired_summary(cohort, window, name, paired, values):
        values = np.asarray(values)
        interval = None
        if len(values):
            rng = np.random.default_rng(seed)
            sampled = values[rng.integers(0, len(values), size=(bootstrap_replicates, len(values)))].mean(axis=1)
            interval = np.quantile(sampled, [0.025, 0.975]).tolist()
        return {"cohort": cohort, "window": window, "contrast": name,
                "n_participants": len(paired), "paired_participants": paired,
                "mean_difference_ba": float(values.mean()) if len(values) else None,
                "pointwise_95ci_ba": interval, "bootstrap_replicates": bootstrap_replicates,
                "seed": seed, "unit": "participant", "exploratory": True}

    for cohort in sorted({row["cohort"] for row in rows}):
        for window in WINDOWS:
            for left, right in ((METHODS[2], METHODS[0]), (METHODS[2], METHODS[1]), (METHODS[1], METHODS[0])):
                left_rows = {row["subject"]: row for row in endpoints if (row["cohort"], row["window"], row["method"]) == (cohort, window, left)}
                right_rows = {row["subject"]: row for row in endpoints if (row["cohort"], row["window"], row["method"]) == (cohort, window, right)}
                paired = [subject for subject in sorted(left_rows) if left_rows[subject]["balanced_accuracy"] is not None and right_rows[subject]["balanced_accuracy"] is not None]
                values = np.asarray([left_rows[s]["balanced_accuracy"] - right_rows[s]["balanced_accuracy"] for s in paired])
                contrasts.append(paired_summary(cohort, window, f"{left}-{right}", paired, values))
        lookup = {(row["subject"], row["window"], row["method"]): row["balanced_accuracy"]
                  for row in endpoints if row["cohort"] == cohort}
        members = sorted({row["subject"] for row in endpoints if row["cohort"] == cohort})
        for method in METHODS:
            paired = [subject for subject in members if all(lookup[(subject, window, method)] is not None for window in WINDOWS)]
            values = [lookup[(subject, "task2s", method)] - lookup[(subject, "cue5s", method)] for subject in paired]
            contrasts.append(paired_summary(cohort, "paired_task2s_minus_cue5s", method, paired, values))
        for right in (METHODS[0], METHODS[1]):
            paired = [subject for subject in members if all(lookup[(subject, window, method)] is not None
                      for window in WINDOWS for method in (METHODS[2], right))]
            values = [(lookup[(subject, "task2s", METHODS[2])] - lookup[(subject, "task2s", right)])
                      - (lookup[(subject, "cue5s", METHODS[2])] - lookup[(subject, "cue5s", right)])
                      for subject in paired]
            contrasts.append(paired_summary(cohort, "paired_gain_change_task2s_minus_cue5s",
                                            f"{METHODS[2]}-{right}", paired, values))
    complete_mapped = {}
    for cohort in sorted({row["cohort"] for row in rows}):
        cohort_subjects = sorted({row["subject"] for row in endpoints if row["cohort"] == cohort})
        complete_mapped[cohort] = [subject for subject in cohort_subjects if all(
            row["balanced_accuracy"] is not None and row["query_mapping_complete_all_sessions"]
            for row in endpoints if row["subject"] == subject
        )]
    return {"participant_endpoints": endpoints, "paired_contrasts": contrasts,
            "complete_mapped_participants_by_cohort": complete_mapped}


def _guarded_common_module():
    """Use the actual existing monitored worker, never import a second runner."""
    common = sys.modules.get("__main__")
    expected = ROOT / "scripts/run_kumar_component_budget_cpu_20261016.py"
    if common is None or Path(getattr(common, "__file__", "")).resolve() != expected:
        raise ValueError("Phase consumer requires the canonical existing guarded CPU worker")
    return common


def _csv_safe(rows):
    return [{key: json.dumps(value, separators=(",", ":")) if isinstance(value, (list, dict)) else value
             for key, value in row.items()} for row in rows]


def execute_bound_inputs(args, config):
    """Thin real-data consumer called only after the shared worker's guards.

    This function creates no launcher, lock, authorization or retry mechanism.
    It preserves partials and propagates unexpected/storage/integrity failures.
    """
    import csv

    import mne

    from learning_preserving_bci.datasets.kumar import CHANNEL_NAMES, numeric_hash

    common = _guarded_common_module()
    if config.get("analysis_mode") != "phase_window" or config.get("phase_settings") != PHASE_SETTINGS:
        raise ValueError("Unfrozen activity-window settings")
    if common.sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise ValueError("Phase scientific protocol hash differs from fixed proposal")
    mapping_path = ROOT / config["phase_mapping"]
    if (Path(config["phase_mapping"]).is_absolute() or ".." in Path(config["phase_mapping"]).parts
            or common.sha256_file(mapping_path) != config["phase_mapping_sha256"]
            or config["input_text_pins"].get(config["phase_mapping"]) != config["phase_mapping_sha256"]):
        raise ValueError("Phase mapping is not an exact pinned text input")
    old = common.read_json(ROOT / config["old_config"])
    frozen = common.read_json(args.split_manifest)["trials"]
    if len(frozen) != 7200 or len({row["trial_id"] for row in frozen}) != 7200:
        raise ValueError("Frozen 7200-trial inventory changed")
    with mapping_path.open(newline="", encoding="utf-8") as handle:
        phases = list(csv.DictReader(handle))
    selected_all, coverage_all = select_common_trials(frozen, phases)
    manifest = common.read_json(ROOT / old["source_manifest"])
    entries = {entry["path"]: entry for entry in manifest}
    if len(entries) != len(manifest):
        raise ValueError("Duplicate official source manifest paths")
    baseline = Path(args.baseline_root)
    original_receipt = common.read_json(baseline / "execution_receipt.json")
    if common.sha256_file(args.saved_predictions) != original_receipt["outputs"]["query_predictions.csv"]:
        raise ValueError("Original saved predictions SHA mismatch")
    with Path(args.saved_predictions).open(newline="", encoding="utf-8") as handle:
        saved_rows = list(csv.DictReader(handle))
    saved = {}
    for row in saved_rows:
        if row["method"] == "source_only":
            key = row["trial_id"]
            if key in saved or row["synthetic"].lower() != "false":
                raise ValueError("Duplicate/non-real original frozen prediction")
            saved[key] = row
    output = Path(args.output)
    output.mkdir(exist_ok=False)
    claim = common.read_json(args.claim)
    data_root = ROOT / config["data_root"]
    all_metrics, all_predictions, input_bindings, source_bindings = [], [], {}, {}
    current_subject = None
    try:
        for subject in config["subjects"]:
            current_subject = subject
            if time.time() >= claim["deadline_epoch"] - 30:
                raise TimeoutError("Phase consumer reached the fixed cleanup reserve")
            directory = output / subject
            directory.mkdir(exist_ok=False)
            source_arrays = common.load_verified_source_model(baseline, subject)
            trials = [row for row in frozen if row["subject"] == subject]
            selected = [row for row in selected_all if row["subject"] == subject]
            coverage = [row for row in coverage_all if row["subject"] == subject]
            frozen_by_id = {row["trial_id"]: row for row in trials}
            if len(trials) != 400:
                raise ValueError("Participant frozen trial count changed")
            historical_fit = common.verify_historical_fit_scope(baseline, subject, [row for row in trials if row["included"]])
            common.write_json(directory / "historical_fit_scope_verification.json", historical_fit)
            verified, opened, epoch_records = {}, {}, {}

            def verify(relative):
                if Path(relative).is_absolute() or ".." in Path(relative).parts or relative not in entries:
                    raise ValueError("Unpinned/unsafe source path")
                path, entry = data_root / relative, entries[relative]
                if relative in verified:
                    return path
                if not path.is_file() or path.stat().st_size != entry["size"]:
                    raise ValueError("Official source length mismatch")
                digest = common.sha256_file(path)
                if entry["checksum_algorithm"] == "sha256":
                    official = digest
                elif entry["checksum_algorithm"] == "git":
                    payload = path.read_bytes()
                    official = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
                else:
                    raise ValueError("Unsupported official checksum")
                if official != entry["checksum"]:
                    raise ValueError("Official source checksum mismatch")
                verified[relative] = {"sha256": digest, "bytes": path.stat().st_size,
                                      "official_algorithm": entry["checksum_algorithm"],
                                      "official_checksum": official}
                return path

            description = common.read_json(verify("dataset_description.json"))
            if (description["Version"], description["DatasetType"], description["License"]) != ("1.0.5", "derivative", "CC-BY-4.0"):
                raise ValueError("Frozen dataset version/license changed")
            allowed = {row["trial_id"] for row in selected if row["role"] in {"source_train", "target_support", "target_query"}}

            def reader(row, start, stop):
                if row["trial_id"] not in allowed or row["role"] not in {"source_train", "target_support", "target_query"}:
                    raise ValueError("Forbidden role or trial in phase signal reader")
                trial = frozen_by_id[row["trial_id"]]
                relative = trial["source_file"]
                if relative not in opened:
                    for raw in opened.values():
                        raw.close()
                    opened.clear()
                    path = verify(relative)
                    if verified[relative]["sha256"] != trial["raw_file_sha256"]:
                        raise ValueError("Frozen EDF SHA differs from official bytes")
                    prefix = relative.removesuffix("_eeg.edf")
                    for suffix in ("_eeg.json", "_events.json", "_events.tsv", "_channels.tsv"):
                        verify(prefix + suffix)
                    verify(f"{subject}/{trial['session']}/{subject}_{trial['session']}_scans.tsv")
                    raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
                    opened[relative] = raw
                    prior_path = ROOT / old["prior_signal_audit"] / "runs" / (relative.replace("/", "__") + ".json")
                    prior = common.read_json(prior_path)
                    if (raw.first_samp != 0 or raw.info["sfreq"] != 512
                            or tuple(raw.ch_names) != CHANNEL_NAMES or raw.get_channel_types() != ["eeg"] * 22
                            or raw.n_times != prior["n_times"] or prior["status"] != "passed"
                            or any(raw._orig_units[name] != "µV" for name in CHANNEL_NAMES)):
                        raise ValueError("Frozen EDF channels/clock/units/boundary differ")
                raw = opened[relative]
                if not 0 <= start < stop <= raw.n_times or stop - start not in (1024, 2560):
                    raise ValueError("Unfrozen activity/cue extraction boundary")
                epoch = raw.get_data(start=start, stop=stop)
                if epoch.shape != (22, stop - start) or not np.isfinite(epoch).all():
                    raise ValueError("Invalid extracted original EDF epoch")
                window = "task2s" if stop - start == 1024 else "cue5s"
                digest = numeric_hash(epoch)
                if window == "cue5s" and digest != trial["raw_window_numeric_sha256"]:
                    raise ValueError("Original cue raw-window numeric SHA changed")
                epoch_records[(row["trial_id"], window)] = {
                    "trial_id": row["trial_id"], "window": window, "role": row["role"],
                    "start_sample": start, "stop_sample_exclusive": stop,
                    "raw_numeric_sha256": digest, "source_file_sha256": verified[relative]["sha256"],
                }
                return epoch

            try:
                window_arrays = materialize_window_arrays(selected, reader)
            finally:
                for raw in opened.values():
                    raw.close()
            for window, tensors in window_arrays.items():
                for trial_id, tensor in tensors.items():
                    digest = numeric_hash(tensor, dtype="<f4")
                    if window == "cue5s" and digest != frozen_by_id[trial_id]["processed_window_numeric_sha256"]:
                        raise ValueError("Original cue preprocessing numeric SHA changed")
                    epoch_records[(trial_id, window)]["processed_numeric_sha256"] = digest
            common.write_csv(directory / "window_identity_hashes.csv", list(epoch_records.values()))
            common.write_csv(directory / "trial_coverage.csv", coverage)
            private_models = []
            with (directory / "partial_evidence.jsonl").open("x", encoding="utf-8") as partial:
                def emit(record):
                    partial.write(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n")
                    partial.flush()
                    os.fsync(partial.fileno())

                def sink(arrays, context):
                    record = common.save_model_state(directory / "private_models" / context["window"],
                                                     {**context, "budget": "common_eligible"}, arrays)
                    bound = {**context, **record}
                    private_models.append(bound)
                    emit({"kind": "private_model_saved", **bound})

                query = [row for row in selected if row["role"] == "target_query"]
                selected_saved = {}
                for row in query:
                    old_prediction = saved[row["trial_id"]]
                    if (old_prediction["subject"] != subject or old_prediction["session"] != row["session"]
                            or int(old_prediction["label"]) != row["label"]):
                        raise ValueError("Saved original query identity/label mismatch")
                    selected_saved[row["trial_id"]] = int(old_prediction["prediction"])
                result = evaluate_participant(subject=subject, cohort=trials[0]["cohort"],
                                              selected=selected, coverage=coverage, window_arrays=window_arrays,
                                              cue_source_arrays=source_arrays,
                                              saved_cue_frozen_predictions=selected_saved,
                                              emit=emit, model_sink=sink, synthetic=False)
            common.write_csv(directory / "metrics.csv", _csv_safe(result["metrics"]))
            if result["predictions"]:
                common.write_csv(directory / "query_predictions.csv", result["predictions"])
            else:
                common.write_json(directory / "query_predictions_empty.json", {"rows": 0, "all_cells_retained_in_metrics": True})
            common.write_json(directory / "fit_access_audit.json", result["fit_access_audit"])
            common.write_json(directory / "private_model_manifest.json", private_models)
            common.write_json(directory / "participant_receipt.json", {
                key: value for key, value in result.items() if key not in {"metrics", "predictions", "fit_access_audit"}
            })
            common.write_json(directory / "loader_provenance.json", {"verified_source_files": verified,
                              "allowed_roles": ["source_train", "target_support", "target_query"],
                              "source_validation_or_source_query_read": False,
                              "task_filter_only_within_verified_2s": True})
            postcheck = common.verify_subject_inputs_after(baseline, subject, data_root, {"verified_source_files": verified})
            common.write_json(directory / "input_after_verification.json", postcheck)
            input_bindings.update({str(data_root / relative): record["sha256"] for relative, record in verified.items()})
            source_bindings.update({str(baseline / subject / name): original_receipt["outputs"][f"{subject}/{name}"]
                                    for name in ("source_before.npz", "source_after.npz", "participant_receipt.json", "fit_access_audit.json")})
            all_metrics.extend(result["metrics"])
            all_predictions.extend(result["predictions"])
            del window_arrays, source_arrays, result
        if len(all_metrics) != 18 * 5 * 2 * 3:
            raise ValueError("Expected all 540 phase comparison cells")
        common.write_csv(output / "metrics.csv", _csv_safe(all_metrics))
        if all_predictions:
            common.write_csv(output / "query_predictions.csv", all_predictions)
        else:
            common.write_json(output / "query_predictions_empty.json", {"rows": 0, "all_540_cells_retained_in_metrics": True})
        aggregate = aggregate_participants(all_metrics)
        common.write_csv(output / "participant_endpoints.csv", aggregate["participant_endpoints"])
        common.write_json(output / "paired_contrasts.json", aggregate["paired_contrasts"])
        common.write_json(output / "metadata_complete_participant_scope.json", aggregate["complete_mapped_participants_by_cohort"])
        common.verify_pins(config["source_code_pins"])
        common.verify_input_text_pins(config, old)
        for path, expected in {**input_bindings, **source_bindings}.items():
            if common.sha256_file(path) != expected:
                raise ValueError("Phase source input changed after all consumers")
        if (common.sha256_file(args.saved_predictions) != original_receipt["outputs"]["query_predictions.csv"]
                or common.sha256_file(mapping_path) != config["phase_mapping_sha256"]):
            raise ValueError("Saved prediction or phase mapping changed during execution")
        common.write_json(output / "input_before_after_manifest.json", {
            "before_after_equal": True, "dataset_inputs": input_bindings,
            "historical_source_inputs": source_bindings, "phase_mapping_sha256": config["phase_mapping_sha256"],
        })
        common.write_json(output / "execution_receipt.json", {
            "status": "completed_post_exposure_common_trial_phase_comparison", "synthetic": False,
            "source_model_cue5s_refitted": False, "source_model_task2s_new_cpu_fits": True,
            "EEGNet_models_loaded_or_refitted": False, "new_optimizer_or_GPU": False,
            "query_or_validation_fitted": False, "rows": len(all_metrics),
            "phase_mapping_sha256": config["phase_mapping_sha256"], "protocol_sha256": PROTOCOL_SHA256,
            "config_sha256": common.sha256_file(args.config),
            "authorization_sha256": common.sha256_file(args.authorization),
            "source_git_commit": common.git_head(),
            "source_code_pins": config["source_code_pins"],
            "original_baseline_execution_receipt_sha256": config["baseline_execution_receipt_sha256"],
            "outputs": {str(path.relative_to(output)): common.sha256_file(path)
                        for path in sorted(output.rglob("*")) if path.is_file()},
        })
    except BaseException as error:
        common.write_json(output / "consumer_exception_receipt.json", {
            "subject": current_subject, "exception": type(error).__name__, "message": str(error),
            "failed_utc_epoch": time.time(), "partial_and_claim_preserved": True,
            "scientific_retry": False,
        })
        raise


if __name__ == "__main__":
    raise SystemExit("Pure engine only: use the separately frozen guarded CPU operation; no standalone scientific execution.")
