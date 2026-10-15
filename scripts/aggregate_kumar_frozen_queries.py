"""Pure aggregation of complete frozen query results; no file, signal or model IO.

All three seeds first receive equal weight within participant/session, followed
by the five target sessions within participant. The existing participant
bootstrap is reused. Source-query scores remain a separate secondary endpoint.
"""
from __future__ import annotations

import math

import numpy as np

from learning_preserving_bci.evaluation.statistics import bootstrap_subject_mean

SEEDS = (20261012, 20261013, 20261014)
DEVELOPMENT = tuple(f"sub-{s}" for s in (1, 4, 7, 10, 13, 16))
REMAINING = tuple(f"sub-{s}" for s in (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18))
ALL_SUBJECTS = tuple(f"sub-{s}" for s in range(1, 19))
SESSIONS = tuple(f"ses-{i}" for i in range(6))
SCOPE = "accepted54_always_frozen_query_only"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def mean_complete(values):
    """Unavailable seeds/sessions propagate; they are never silently dropped."""
    return None if any(value is None for value in values) else float(np.mean(values))


def fixed_metrics(predictions):
    matrix = np.zeros((2, 2), dtype=np.int64)
    for row in predictions:
        y, pred = row["y_true"], row["y_pred"]
        require(type(y) is int and type(pred) is int and y in (0, 1) and pred in (0, 1),
                "Invalid binary saved query label/prediction")
        logits = [row["logit_0"], row["logit_1"]]
        require(all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
                    for v in logits) and pred == int(np.argmax(logits)),
                "Saved query prediction differs from finite fixed argmax")
        matrix[y, pred] += 1
    require(int(matrix.sum()) > 0, "Empty query session")
    totals = matrix.sum(axis=1)
    recalls = [float(matrix[k, k] / totals[k]) if totals[k] else None for k in (0, 1)]
    return {"n": len(predictions), "confusion_matrix": matrix.tolist(), "class_recalls": recalls,
            "balanced_accuracy": mean_complete(recalls),
            "balanced_accuracy_status": "not_estimable_missing_class" if None in recalls else "estimated",
            "predicted_class_counts": matrix.sum(axis=0).tolist(),
            "class_collapse": bool(np.any(matrix.sum(axis=0) == 0))}


def endpoint_summary(values):
    unavailable = [subject for subject, value in values.items() if value is None]
    if unavailable:
        return {"status": "unavailable_missing_participant_endpoint", "participant_values": values,
                "unavailable_participants": unavailable, "mean": None,
                "bootstrap": None, "participants_dropped": 0}
    bootstrap = bootstrap_subject_mean(values, confidence=0.95, n_resamples=10000, seed=42)
    return {"status": "complete", "participant_values": values, "unavailable_participants": [],
            "mean": bootstrap["mean"], "bootstrap": bootstrap, "participants_dropped": 0}


def aggregate_query_results(results, jobs, *, expected_query_ids, synthetic=False):
    """Reject incomplete jobs/trials/sessions; retain non-estimable BA as None.

The outer evaluator must already have bound the frozen plan, manifest and
accepted checkpoint identities. This helper independently checks complete job
and trial coverage, common identities/labels across seeds and all saved metric
arithmetic. It only consumes supplied result dictionaries and never loads EEG,
weights, labels from external files, or another experimental result.
"""
    require(type(synthetic) is bool, "Explicit synthetic boolean required")
    require(len(jobs) == len(results) == 54 and len({j["job_id"] for j in jobs}) == 54,
            "Exactly all54 unique frozen jobs/results required")
    require({(j["subject"], j["seed"]) for j in jobs}
            == {(subject, seed) for subject in ALL_SUBJECTS for seed in SEEDS},
            "Frozen participant/seed cohort differs")
    expected_query_ids = list(expected_query_ids)
    require(len(expected_query_ids) == len(set(expected_query_ids)) > 0, "Duplicate/empty query manifest IDs")
    manifest_subjects = {subject: {trial for trial in expected_query_ids if trial.split('/')[0] == subject}
                         for subject in ALL_SUBJECTS}
    require(all(manifest_subjects.values()) and set().union(*manifest_subjects.values()) == set(expected_query_ids),
            "Query manifest subject identities differ")
    by_session, saved_metrics, identities, unavailable = {}, [], {}, []
    for result, job in zip(results, jobs, strict=True):
        identity = result["identity"]
        require(all(identity[k] == job[k] for k in ("job_id", "subject", "seed", "result_key")),
                "Saved query job identity/order differs")
        require(identity["synthetic"] is synthetic and identity["software_validation_only"] is synthetic,
                "Synthetic/real query result scope differs")
        require(result["scope"] == SCOPE and result["optimizer_instances_created"] == 0
                and result["optimizer_steps"] == 0 and result["new_fit"] is False
                and result["parameter_BN_normalization_updates"] is False
                and result["input_files_unchanged"] is True
                and result["processed_input_hashes_verified"] is True
                and result["source_training_context_preserved"] is True
                and result["state_before_sha256"] == result["state_after_sha256"]
                and result["query_labels_used_for"] == "fixed_metrics_only",
                "Query result violates unchanged frozen inference state")
        predictions = result["predictions"]
        subject, seed = job["subject"], job["seed"]
        ids = [row["trial_id"] for row in predictions]
        require(len(ids) == len(set(ids)) and set(ids) == manifest_subjects[subject]
                and result["query_rows_evaluated"] == len(ids)
                and result["real_query_rows_loaded"] == (0 if synthetic else len(ids)),
                "Incomplete/duplicate saved query trial scope")
        for row in predictions:
            session = row["session"]
            role = "source_query" if session == "ses-0" else "target_query"
            valid_runs = {"run-3"} if session == "ses-0" else (
                {"run-1", "run-2", "run-3"} if session == "ses-1" else {"run-1", "run-2"})
            require(row["subject"] == subject and row["seed"] == seed and session in SESSIONS
                    and row["role"] == role and row["run"] in valid_runs,
                    "Forbidden saved query participant/role/session/run")
        trial_identity = [(r["trial_id"], r["session"], r["run"], r["role"], r["y_true"]) for r in predictions]
        require(subject not in identities or identities[subject] == trial_identity,
                "Query identities/order/labels changed across seeds")
        identities[subject] = trial_identity
        metrics = result["session_metrics"]
        require(len(metrics) == 6 and {row["session"] for row in metrics} == set(SESSIONS),
                "All six fixed query session metrics required")
        for metric in metrics:
            session = metric["session"]
            role = "source_query" if session == "ses-0" else "target_query"
            require(metric["subject"] == subject and metric["seed"] == seed and metric["role"] == role,
                    "Session metric identity differs")
            measured = fixed_metrics([r for r in predictions if r["session"] == session])
            require(all(metric[key] == value for key, value in measured.items()), "Saved query session metric arithmetic differs")
            key = subject, session
            by_session.setdefault(key, {})[seed] = measured["balanced_accuracy"]
            row = {"job_id": job["job_id"], "subject": subject, "seed": seed,
                   "session": session, "role": role, **measured}
            saved_metrics.append(row)
            if measured["balanced_accuracy"] is None:
                unavailable.append(row)
    participant_sessions, endpoints = [], []
    for subject in ALL_SUBJECTS:
        scores = {}
        for session in SESSIONS:
            values = by_session[(subject, session)]
            require(set(values) == set(SEEDS), "Missing fixed seed in participant/session")
            scores[session] = mean_complete([values[seed] for seed in SEEDS])
            participant_sessions.append({"subject": subject, "session": session,
                "role": "source_query" if session == "ses-0" else "target_query",
                "seeds": list(SEEDS), "seed_balanced_accuracies": [values[seed] for seed in SEEDS],
                "mean_three_seed_balanced_accuracy": scores[session]})
        endpoints.append({"subject": subject,
            "source_query_balanced_accuracy": scores["ses-0"],
            "target_five_session_balanced_accuracy": mean_complete([scores[f"ses-{i}"] for i in range(1, 6)]),
            "target_session_balanced_accuracies": [scores[f"ses-{i}"] for i in range(1, 6)]})
    groups = {"development6": DEVELOPMENT, "remaining12": REMAINING, "all18_secondary_exploratory": ALL_SUBJECTS}
    cohorts = {}
    for name, subjects in groups.items():
        selected = [r for r in endpoints if r["subject"] in subjects]
        cohorts[name] = {"subjects": list(subjects), "independent_participants": len(selected),
            "target_query": endpoint_summary({r["subject"]: r["target_five_session_balanced_accuracy"] for r in selected}),
            "source_query_secondary": endpoint_summary({r["subject"]: r["source_query_balanced_accuracy"] for r in selected})}
    return {"schema_version": 1, "status": "complete_with_explicit_unavailable_metrics" if unavailable else "complete",
        "scope": SCOPE, "synthetic": synthetic, "software_validation_only": synthetic,
        "job_count": 54, "jobs": [j["job_id"] for j in jobs], "unique_query_trial_count": len(expected_query_ids),
        "prediction_rows_with_repeated_seeds": sum(len(r["predictions"]) for r in results),
        "aggregation_rule": "equal mean of all three seeds within participant/session, then equal mean of five target sessions within participant",
        "source_query_separate_secondary": True, "cohorts": cohorts,
        "per_participant": endpoints, "per_participant_session": participant_sessions,
        "per_job_session_metrics": saved_metrics, "unavailable_session_metrics": unavailable,
        "class_collapse_job_sessions": sum(r["class_collapse"] for r in saved_metrics),
        "missing_jobs_or_sessions_dropped": 0, "seed_selection_performed": False,
        "model_fits": 0, "model_forwards": 0, "checkpoint_tensor_loads": 0,
        "comparison_with_CPU_baselines_computed": False, "scientific_acceptance_pending": True,
        "limits": ["Synthetic results are software validation only when flagged synthetic.",
            "Later strategy claims on the previously exposed cohort remain exploratory; no strategy or threshold is selected.",
            "This baseline extension does not replace the frozen CPU primary comparison.",
            "Offline query decoding cannot establish human learning, skill retention or clinical effect."]}
