#!/usr/bin/env python3
"""Isolated exploratory CPU budget replay; historical results remain immutable.

The default command checks text metadata only. Real signal/model loading is
available solely in a monitored child of an authorized --execute invocation.
Synthetic callers may invoke run_budget_subject directly for software tests.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LOCK = Path("/workspace/.locks/few-shot-mi-eeg-cpu.lock")
OLD_METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda")
EA_METHOD = "ea_csp_lda"
PHASE_SCRIPT = "scripts/run_kumar_phase_window_cpu_20261016.py"
BUDGETS = [4, 8, 12, 16, "full"]
GIB = 1024 ** 3
POLL_SECONDS = .25
MAX_SECONDS = 3600
REQUIRED_PINS = (
    "scripts/run_kumar_component_budget_cpu_20261016.py",
    "scripts/run_kumar_csp_signed_score_operation.py",
    "scripts/run_kumar_baselines.py",
    "src/learning_preserving_bci/datasets/kumar.py",
    "src/learning_preserving_bci/decoders/csp_lda.py",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head():
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_csv(path, rows):
    require(bool(rows), "Empty evidence table")
    with Path(path).open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def ids_sha256(ids):
    return hashlib.sha256(json.dumps(list(ids), ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def chronological_indices(trials, role, session=None):
    selected = [i for i, row in enumerate(trials)
                if row["role"] == role and (session is None or row["session"] == session)]
    return sorted(selected, key=lambda i: (
        trials[i].get("acquisition_time_utc", ""),
        int(str(trials[i]["run"]).removeprefix("run-")), int(trials[i]["start_sample"]),
        int(trials[i]["source_row"]),
        trials[i]["trial_id"]))


def array_digest(arrays):
    import numpy as np
    digest = hashlib.sha256()
    for name, value in sorted(arrays.items()):
        value = np.ascontiguousarray(value)
        require(not value.dtype.hasobject, "Object model array")
        digest.update(json.dumps([name, value.dtype.str, list(value.shape)],
                                 separators=(",", ":")).encode())
        digest.update(b"\0")
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def validate_source_arrays(arrays):
    import numpy as np
    expected = {"n_components", "csp_filters", "csp_patterns", "csp_mean", "csp_std",
                "lda_classes", "lda_coef", "lda_intercept", "lda_means", "lda_priors",
                "lda_covariance"}
    require(set(arrays) == expected, "Unexpected frozen source array schema")
    require(all(not np.asarray(v).dtype.hasobject and np.isfinite(v).all()
                for v in arrays.values()), "Invalid frozen source numeric arrays")
    require(np.asarray(arrays["n_components"]).shape == ()
            and int(arrays["n_components"]) == 4, "Frozen CSP must have four components")
    filters = arrays["csp_filters"]
    require(filters.ndim == 2 and filters.shape[0] >= 4 and filters.shape[1] == 22
            and arrays["csp_patterns"].shape == filters.shape, "Frozen CSP shape mismatch")
    shapes = {"csp_mean": (4,), "csp_std": (4,), "lda_classes": (2,),
              "lda_coef": (1, 4), "lda_intercept": (1,), "lda_means": (2, 4),
              "lda_priors": (2,), "lda_covariance": (4, 4)}
    require(all(arrays[key].shape == shape for key, shape in shapes.items()),
            "Frozen LDA/feature shape mismatch")
    require(np.array_equal(arrays["lda_classes"], [0, 1]), "Frozen class ordering changed")


class ScientificFallback(RuntimeError):
    """A predefined unestimable scientific case, never a general error handler."""


def frozen_features(arrays, X):
    import numpy as np
    # Match the historical average-power replay's per-epoch np.dot convention.
    projected = np.asarray([np.dot(arrays["csp_filters"][:4], epoch) for epoch in X])
    powers = np.square(projected).mean(axis=2)
    if not np.isfinite(powers).all() or (powers <= 0).any():
        raise ScientificFallback("nonpositive_or_nonfinite_frozen_CSP_power")
    return np.log(powers)


def frozen_predict(arrays, X):
    features = frozen_features(arrays, X)
    scores = features @ arrays["lda_coef"].T + arrays["lda_intercept"]
    return arrays["lda_classes"][(scores[:, 0] > 0).astype(int)]


def balanced_accuracy(y, prediction):
    import numpy as np
    y, prediction = np.asarray(y), np.asarray(prediction)
    require(y.shape == prediction.shape and len(y) > 0, "Prediction alignment mismatch")
    require(np.isin(y, [0, 1]).all() and np.isin(prediction, [0, 1]).all(),
            "Nonbinary prediction/label")
    require(set(y.tolist()) == {0, 1}, "Balanced accuracy needs both true classes")
    return float(sum((prediction[y == label] == label).mean() for label in (0, 1)) / 2)


def helmert_matrix(channels=22):
    """Fixed orthonormal contrasts, independent of all participant data."""
    import numpy as np
    H = np.zeros((channels - 1, channels), dtype=np.float64)
    for row in range(channels - 1):
        denominator = np.sqrt((row + 1) * (row + 2))
        H[row, :row + 1] = 1 / denominator
        H[row, row + 1] = -(row + 1) / denominator
    return H


def centered_covariances(X):
    import numpy as np
    X = np.asarray(X, dtype=np.float64)
    require(X.ndim == 3 and X.shape[2] > 1, "Invalid covariance epoch shape")
    centered = X - X.mean(axis=2, keepdims=True)
    return np.einsum("nct,ndt->ncd", centered, centered) / (X.shape[2] - 1)


def ea_reference(X, H=None):
    """Mean ddof=1 raw covariance in fixed CAR contrast basis; no ridge."""
    import numpy as np
    H = helmert_matrix() if H is None else H
    reference = centered_covariances(np.einsum("kc,nct->nkt", H, X)).mean(axis=0)
    eigenvalues, eigenvectors = np.linalg.eigh(reference)
    if (not np.isfinite(eigenvalues).all() or eigenvalues[0] <= 0
            or eigenvalues[-1] / eigenvalues[0] > 1e12):
        raise ScientificFallback("EA_nonpositive_eigenvalue_or_condition_over_1e12")
    invroot = (eigenvectors * (eigenvalues ** -.5)) @ eigenvectors.T
    return {"reference": reference, "inverse_sqrt": invroot,
            "condition_number": float(eigenvalues[-1] / eigenvalues[0]), "helmert": H}


def ea_transform(X, reference):
    import numpy as np
    H = reference["helmert"]
    transform = H.T @ reference["inverse_sqrt"] @ H
    return np.einsum("kc,nct->nkt", transform, X)


def trace_normalized_covariance_drift(source, support):
    import numpy as np
    def mean_normalized(X):
        cov = centered_covariances(X)
        traces = np.trace(cov, axis1=1, axis2=2)
        if (traces <= 0).any() or not np.isfinite(traces).all():
            raise ScientificFallback("undefined_trace_normalized_covariance")
        return (cov / traces[:, None, None]).mean(axis=0)
    return float(np.linalg.norm(mean_normalized(source) - mean_normalized(support), ord="fro"))


def _fit_predict(method, X, y, fit_indices, eval_indices, source_arrays, factory,
                 seed, source_indices=None, support_indices=None, model_sink=None):
    """No catch for unexpected ValueError, I/O, or identity failures."""
    import numpy as np
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    fit_y = y[fit_indices].copy()
    if len(fit_y) < 4 or set(fit_y.tolist()) != {0, 1}:
        raise ScientificFallback("union_unestimable_sample_count_or_classes")
    if method == OLD_METHODS[1]:
        lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        lda.fit(frozen_features(source_arrays, X[fit_indices].copy()), fit_y)
        prediction = lda.predict(frozen_features(source_arrays, X[eval_indices].copy()))
        if model_sink is not None:
            arrays = {name: value.copy() for name, value in source_arrays.items()}
            for field in ("classes", "coef", "intercept", "means", "priors", "covariance"):
                arrays["lda_" + field] = np.asarray(getattr(lda, field + "_")).copy()
            model_sink(arrays)
        return prediction
    model = factory(n_components=4, random_state=seed)
    if method == EA_METHOD:
        require(source_indices is not None and support_indices is not None,
                "EA requires explicit source/support reference scopes")
        source_ref = ea_reference(X[source_indices].copy())
        target_ref = ea_reference(X[support_indices].copy())
        fit_X = np.concatenate([ea_transform(X[source_indices].copy(), source_ref),
                                ea_transform(X[support_indices].copy(), target_ref)])
        eval_X = ea_transform(X[eval_indices].copy(), target_ref)
    else:
        fit_X, eval_X = X[fit_indices].copy(), X[eval_indices].copy()
    csp, lda = model.named_steps["csp"], model.named_steps["lda"]
    features = csp.fit_transform(fit_X, fit_y)
    lda.fit(features, fit_y)
    prediction = lda.predict(csp.transform(eval_X))
    if model_sink is not None:
        name = "component_budget_baseline_helpers"
        helper = sys.modules.get(name) or load_module(name, "scripts/run_kumar_baselines.py")
        arrays = helper.model_arrays(csp, lda)
        if method == EA_METHOD:
            arrays.update({"ea_helmert": source_ref["helmert"].copy(),
                           "ea_source_reference": source_ref["reference"].copy(),
                           "ea_source_inverse_sqrt": source_ref["inverse_sqrt"].copy(),
                           "ea_target_reference": target_ref["reference"].copy(),
                           "ea_target_inverse_sqrt": target_ref["inverse_sqrt"].copy()})
        model_sink(arrays)
    return prediction


def save_model_state(folder, context, arrays):
    """Private pickle-free checkpoint; any persistence/integrity failure propagates."""
    import numpy as np
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    token = "_".join(str(context[key]) for key in ("session", "budget", "method"))
    require(all(part and set(part) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
                for part in token.split("/")), "Unsafe checkpoint identity")
    path = folder / (token + ".npz")
    require(not os.path.lexists(path), "Checkpoint exists; no overwrite/retry")
    digest = array_digest(arrays)
    require(all(not np.asarray(value).dtype.hasobject and np.isfinite(value).all()
                for value in arrays.values()), "Invalid checkpoint numeric arrays")
    with path.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    file_sha = sha256_file(path)
    with np.load(path, allow_pickle=False) as archive:
        restored = {key: archive[key] for key in archive.files}
    require(array_digest(restored) == digest and sha256_file(path) == file_sha,
            "Checkpoint fresh readback/hash mismatch")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": file_sha,
            "array_sha256": digest, "array_keys": sorted(arrays), "allow_pickle": False,
            "private_model_state": True}


def _saved_index(rows, subject):
    result = {}
    for row in rows:
        if row["subject"] != subject or row["method"] not in OLD_METHODS:
            continue
        key = row["method"], row["trial_id"]
        require(key not in result, "Duplicate saved prediction identity")
        require(str(row.get("synthetic", "false")).lower() in {"true", "false"},
                "Invalid saved synthetic flag")
        result[key] = row
    return result


def run_budget_subject(X, y, trials, source_arrays, saved_prediction_rows, config,
                       output=None, model_factory=None, model_sink=None):
    """Run one subject; injectable factory and arrays support synthetic tests.

    No source model is fitted. Frozen/full historical predictions are joined by
    identity. Returns pure evidence rows, and optionally writes a fresh directory.
    """
    import numpy as np
    if output is not None:
        require(not os.path.lexists(output), "Output must be fresh before any scientific work")
    if model_factory is None:
        from learning_preserving_bci.decoders.csp_lda import make_csp_lda
        model_factory = make_csp_lda
    require(config.get("budgets", BUDGETS) == BUDGETS, "Unfrozen budget list")
    X, y = np.asarray(X, dtype=np.float64), np.asarray(y, dtype=np.int64)
    require(X.ndim == 3 and X.shape[1] == 22 and len(X) == len(y) == len(trials)
            and np.isfinite(X).all(), "Input tensor/metadata mismatch")
    require(len({r["trial_id"] for r in trials}) == len(trials), "Duplicate trial identity")
    require(len({r["subject"] for r in trials}) == 1, "Subject mixing")
    require({r["role"] for r in trials} <= {"source_train", "target_support", "target_query"},
            "Budget engine received an unauthorized signal role")
    require(set(y.tolist()) <= {0, 1}, "Unexpected class vocabulary")
    synthetic = bool(config.get("synthetic", False))
    require(all(bool(r.get("synthetic", False)) == synthetic for r in trials),
            "Synthetic/data scope mismatch")
    validate_source_arrays(source_arrays)
    before = array_digest(source_arrays)
    subject = trials[0]["subject"]
    cohort = "development6" if trials[0]["cohort"] in {"development", "development6"} else "remaining12"
    source = chronological_indices(trials, "source_train")
    require(len(source) == 40 and set(y[source].tolist()) == {0, 1},
            "Source scope must be the original forty two-class TRAIN trials")
    saved = _saved_index(saved_prediction_rows, subject)
    def ids(indices):
        return [trials[i]["trial_id"] for i in indices]
    def reuse(method, indices):
        predictions = []
        for index in indices:
            row = saved[(method, trials[index]["trial_id"])]
            require(row["session"] == trials[index]["session"]
                    and row["run"] == trials[index]["run"]
                    and int(row["label"]) == int(y[index])
                    and str(row.get("synthetic", "false")).lower() == str(synthetic).lower(),
                    "Historical prediction identity/label/scope mismatch")
            predictions.append(int(row["prediction"]))
        return np.asarray(predictions, dtype=np.int64)
    source_query_rows = [r for (m, _), r in saved.items()
                         if m == OLD_METHODS[0] and r["session"] == "ses-0"]
    require(bool(source_query_rows), "Missing saved frozen source-query outcomes")
    source_query_ba = balanced_accuracy([int(r["label"]) for r in source_query_rows],
                                      [int(r["prediction"]) for r in source_query_rows])
    predictions, metrics, features, outcomes, audits, provenance = [], [], [], [], [], []
    sessions = sorted({r["session"] for r in trials if r["role"] == "target_support"},
                      key=lambda value: int(value.removeprefix("ses-")))
    for session in sessions:
        support = chronological_indices(trials, "target_support", session)
        query = chronological_indices(trials, "target_query", session)
        require(len(support) >= 16 and len(query) > 0, "Missing planned support/query")
        require(set(source).isdisjoint(support) and set(source + support).isdisjoint(query),
                "Source/support/query identity intersection")
        frozen_query = reuse(OLD_METHODS[0], query)
        query_hash = ids_sha256(ids(query))
        full_values = {}
        for budget in BUDGETS:
            prefix = support if budget == "full" else support[:budget]
            fit = source + prefix
            counts = np.bincount(y[prefix], minlength=2)
            for method in (*OLD_METHODS, EA_METHOD):
                reused = method == OLD_METHODS[0] or (budget == "full" and method in OLD_METHODS)
                fallback, reason = False, ""
                checkpoints = []
                context = {"subject": subject, "session": session, "budget": str(budget), "method": method}
                def persist(arrays, context=context, checkpoints=checkpoints):
                    checkpoints.append(model_sink(context, arrays))
                if reused:
                    prediction = reuse(method, query)
                else:
                    try:
                        prediction = _fit_predict(method, X, y, fit, query, source_arrays,
                                                  model_factory, config.get("seed", 42),
                                                  source, prefix,
                                                  model_sink=persist if model_sink is not None else None)
                    except (ScientificFallback, np.linalg.LinAlgError) as error:
                        prediction, fallback, reason = frozen_query.copy(), True, str(error)
                audits.append({"subject": subject, "session": session, "budget": str(budget),
                               "method": method,
                               "fit_trial_ids": ids(source if method == OLD_METHODS[0] else fit),
                               "fit_attempted_in_this_replay": not reused,
                               "fit_completed_in_this_replay": not reused and not fallback,
                               "fit_ids_scope": "original_historical_fit" if reused else "current_replay_fit",
                               "model_states": checkpoints,
                               "query_trial_ids": ids(query),
                               "reference_source_trial_ids": ids(source) if method == EA_METHOD else [],
                               "reference_target_trial_ids": ids(prefix) if method == EA_METHOD else [],
                               "query_never_fitted": True, "historical_predictions_reused": reused,
                               "fallback": fallback, "fallback_reason": reason})
                ba = balanced_accuracy(y[query], prediction)
                metrics.append({"subject": subject, "cohort": cohort, "session": session,
                                "budget": str(budget), "k": len(prefix), "method": method,
                                "n_query": len(query), "query_trial_ids_sha256": query_hash,
                                "balanced_accuracy": ba, "support_left": int(counts[0]),
                                "support_right": int(counts[1]),
                                "support_missing_class": bool((counts == 0).any()),
                                "prediction_left": int((prediction == 0).sum()),
                                "prediction_right": int((prediction == 1).sum()),
                                "prediction_class_collapse": bool(len(set(prediction.tolist())) == 1),
                                "historical_predictions_reused": reused, "fallback": fallback,
                                "fallback_reason": reason, "synthetic": synthetic,
                                "software_validation_only": synthetic})
                for index, predicted in zip(query, prediction):
                    predictions.append({"subject": subject, "cohort": cohort, "session": session,
                                        "run": trials[index]["run"], "budget": str(budget),
                                        "k": len(prefix), "method": method,
                                        "trial_id": trials[index]["trial_id"], "label": int(y[index]),
                                        "prediction": int(predicted),
                                        "historical_predictions_reused": reused,
                                        "fallback": fallback, "synthetic": synthetic,
                                        "software_validation_only": synthetic})
                if budget == "full":
                    full_values[method] = ba
        half = len(support) // 2
        train_half, holdout = support[:half], support[half:]
        holdout_counts = np.bincount(y[holdout], minlength=2)
        defined = bool((holdout_counts > 0).all())
        holdout_values = {method: None for method in OLD_METHODS}
        holdout_fallback, holdout_reason = not defined, "" if defined else "holdout_missing_true_class"
        candidate_fallback = {method: False for method in OLD_METHODS[1:]}
        candidate_reasons = {method: "" for method in OLD_METHODS[1:]}
        if defined:
            frozen_holdout = frozen_predict(source_arrays, X[holdout].copy())
            holdout_values[OLD_METHODS[0]] = balanced_accuracy(y[holdout], frozen_holdout)
            for method in OLD_METHODS[1:]:
                fallback, reason = False, ""
                checkpoints = []
                context = {"subject": subject, "session": session, "budget": "support_half_CV", "method": method}
                def persist(arrays, context=context, checkpoints=checkpoints):
                    checkpoints.append(model_sink(context, arrays))
                try:
                    predicted = _fit_predict(method, X, y, source + train_half, holdout,
                                             source_arrays, model_factory, config.get("seed", 42),
                                             model_sink=persist if model_sink is not None else None)
                except (ScientificFallback, np.linalg.LinAlgError) as error:
                    predicted, fallback, reason = frozen_holdout.copy(), True, str(error)
                    candidate_fallback[method], candidate_reasons[method] = True, reason
                holdout_values[method] = balanced_accuracy(y[holdout], predicted)
                audits.append({"subject": subject, "session": session, "budget": "support_half_CV",
                               "method": method, "fit_trial_ids": ids(source + train_half),
                               "support_holdout_trial_ids": ids(holdout),
                               "fit_attempted_in_this_replay": True,
                               "fit_completed_in_this_replay": not fallback,
                               "model_states": checkpoints,
                               "reference_source_trial_ids": [], "reference_target_trial_ids": [],
                               "query_never_fitted": True, "historical_predictions_reused": False,
                               "fallback": fallback, "fallback_reason": reason})
        full_counts = np.bincount(y[support], minlength=2)
        features.append({"subject": subject, "cohort": cohort, "session": session,
                         "source_trial_ids_sha256": ids_sha256(ids(source)),
                         "support_trial_ids_sha256": ids_sha256(ids(support)),
                         "n_support": len(support), "support_left": int(full_counts[0]),
                         "support_right": int(full_counts[1]),
                         "frozen_source_BA_all_support": balanced_accuracy(
                             y[support], frozen_predict(source_arrays, X[support].copy())),
                         "source40_to_support_trace_normalized_cov_frobenius":
                             trace_normalized_covariance_drift(X[source], X[support]),
                         "support_train_half_n": half, "support_holdout_n": len(holdout),
                         "support_holdout_left": int(holdout_counts[0]),
                         "support_holdout_right": int(holdout_counts[1]),
                         "holdout_BA_frozen": holdout_values[OLD_METHODS[0]],
                         "holdout_BA_lda_only": holdout_values[OLD_METHODS[1]],
                         "holdout_BA_full_refit": holdout_values[OLD_METHODS[2]],
                         "support_cv_lda_gain": (holdout_values[OLD_METHODS[1]]
                                                 - holdout_values[OLD_METHODS[0]]) if defined else 0.,
                         "support_cv_full_gain": (holdout_values[OLD_METHODS[2]]
                                                  - holdout_values[OLD_METHODS[0]]) if defined else 0.,
                         "holdout_defined": defined, "holdout_fallback_frozen": holdout_fallback,
                         "holdout_lda_fallback_frozen": candidate_fallback[OLD_METHODS[1]],
                         "holdout_full_refit_fallback_frozen": candidate_fallback[OLD_METHODS[2]],
                         "holdout_lda_fallback_reason": candidate_reasons[OLD_METHODS[1]],
                         "holdout_full_refit_fallback_reason": candidate_reasons[OLD_METHODS[2]],
                         "holdout_missing_reason": holdout_reason, "synthetic": synthetic,
                         "software_validation_only": synthetic})
        outcomes.append({"subject": subject, "cohort": cohort, "session": session,
                         "n_support": len(support), "n_query": len(query),
                         "query_trial_ids_sha256": query_hash,
                         "BA_frozen": full_values[OLD_METHODS[0]],
                         "BA_lda_only": full_values[OLD_METHODS[1]],
                         "BA_full_refit": full_values[OLD_METHODS[2]],
                         "frozen_source_query_BA": source_query_ba,
                         "synthetic": synthetic, "software_validation_only": synthetic})
        provenance.append({"subject": subject, "session": session,
                           "source_trial_ids": ids(source), "support_trial_ids": ids(support),
                           "support_train_half_trial_ids": ids(train_half),
                           "support_holdout_trial_ids": ids(holdout),
                           "lda_fit_trial_ids": ids(source + train_half),
                           "full_refit_fit_trial_ids": ids(source + train_half),
                           "source_support_disjoint": True, "fit_holdout_disjoint": True,
                           "prefix_chronological": True})
    require(array_digest(source_arrays) == before, "Frozen source arrays mutated")
    result = {"predictions": predictions, "metrics": metrics, "features": features,
              "outcomes": outcomes, "fit_audits": audits,
              "provenance": {"schema_version": 1, "synthetic": synthetic,
                             "software_validation_only": synthetic, "support_order": "chronological",
                             "rows": provenance},
              "source_parameter_sha256_before": before, "source_parameter_sha256_after": before,
              "synthetic": synthetic, "software_validation_only": synthetic}
    if output is not None:
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=False)
        _write_result(folder, result)
    return result


def _write_result(folder, result):
    for name, key in (("query_predictions.csv", "predictions"), ("session_metrics.csv", "metrics"),
                      ("full_support_features.csv", "features"),
                      ("full_support_outcomes.csv", "outcomes")):
        write_csv(folder / name, result[key])
    write_json(folder / "source_support_trial_provenance.json", result["provenance"])
    write_json(folder / "fit_access_audit.json", result["fit_audits"])
    write_json(folder / "subject_receipt.json", {key: result[key] for key in (
        "source_parameter_sha256_before", "source_parameter_sha256_after", "synthetic",
        "software_validation_only")})


def validate_config(config):
    require(config.get("schema_version") == 1 and config.get("synthetic") is False,
            "Real replay needs an explicit versioned nonsynthetic config")
    require(config.get("budgets") == BUDGETS and config.get("seed", 42) == 42,
            "Budget/seed defaults changed")
    require(config.get("max_seconds", MAX_SECONDS) == MAX_SECONDS,
            "Exploratory window must remain 3600 seconds")
    require(config.get("threads", 1) == 1, "CPU threads must remain one")
    require(config.get("analysis_mode", "budget") in {"budget", "phase_window"},
            "Unknown fixed scientific consumer")
    if config.get("analysis_mode") == "phase_window":
        require(PHASE_SCRIPT in config["source_code_pins"], "Phase consumer source pin missing")
    require(config.get("ea", {"basis": "helmert_21_reembed_22", "ddof": 1,
                               "condition_limit": 1e12, "ridge": 0}) == {
        "basis": "helmert_21_reembed_22", "ddof": 1, "condition_limit": 1e12, "ridge": 0},
        "EA defaults changed")
    require(bool(config.get("subjects")) and len(set(config["subjects"])) == len(config["subjects"]),
            "Duplicate/missing subjects")


def verify_pins(pins):
    require(set(REQUIRED_PINS) <= set(pins), "Required source pins missing")
    for relative, expected in pins.items():
        path = ROOT / relative
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts
                and path.is_file() and not path.is_symlink() and sha256_file(path) == expected,
                "Source pin changed: " + relative)


def verify_input_text_pins(config, old):
    pins = config["input_text_pins"]
    required = {old["source_manifest"], str(Path(old["prior_signal_audit"]) / "source_events.json")}
    source_events = read_json(ROOT / old["prior_signal_audit"] / "source_events.json")
    for row in source_events:
        if (row["subject"] in config["subjects"] and
                not (row["session"] == "ses-0" and row["run"] in {"run-2", "run-3"})):
            required.add(str(Path(old["prior_signal_audit"]) / "runs" /
                             (row["source_file"].replace("/", "__") + ".json")))
    require(required <= set(pins), "Historical loader text input pins incomplete")
    for relative, expected in pins.items():
        path = ROOT / relative
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts
                and path.suffix in {".json", ".csv", ".tsv", ".md", ".txt"}
                and not path.is_symlink() and path.is_file() and sha256_file(path) == expected,
                "Historical loader text pin changed: " + relative)
    return pins


def preflight(args, authorization=False):
    """Text-only integrity checks; deliberately does not read NPZ or EEG bytes."""
    config = read_json(args.config)
    validate_config(config)
    verify_pins(config["source_code_pins"])
    old = read_json(ROOT / config["old_config"])
    require(set(config["subjects"]) == set(old["subjects"]), "Protocol requires all eighteen subjects")
    require(config["data_root"] == old["data_root"], "Historical data root changed")
    input_text_pins = verify_input_text_pins(config, old)
    require(sha256_file(ROOT / config["old_config"]) == config["old_config_sha256"],
            "Historical loader config changed")
    require(sha256_file(args.split_manifest) == config["split_manifest_sha256"], "Split changed")
    require(sha256_file(args.protocol) == config["protocol_sha256"], "Protocol changed")
    require(sha256_file(Path(args.baseline_root) / "execution_receipt.json")
            == config["baseline_execution_receipt_sha256"], "Baseline receipt changed")
    receipt = read_json(Path(args.baseline_root) / "execution_receipt.json")
    require(receipt["status"] == "completed_frozen_offline_protocol" and not receipt["synthetic"],
            "Historical CPU execution incomplete")
    expected = receipt["outputs"].get("query_predictions.csv")
    require(expected and sha256_file(args.saved_predictions) == expected,
            "Saved historical query predictions changed")
    require(Path(args.output).is_absolute() and not os.path.lexists(args.output), "Output must be fresh")
    monitor = load_module("component_budget_monitor", REQUIRED_PINS[1])
    observed = monitor.resources(Path(args.output))
    require(observed["memory"]["effective_available_bytes"] >= 3 * GIB,
            "Startup effective memory below 3 GiB")
    require(observed["free_output_disk_bytes"] >= 2 * GIB, "Disk reserve below 2 GiB")
    report = {"status": "metadata_only_preflight", "scientific_inputs_loaded": False,
              "config_sha256": sha256_file(args.config), "protocol_sha256": sha256_file(args.protocol),
              "host_identity": monitor.container_identity(), "resources": observed,
              "runtime": monitor.runtime_metadata(), "source_git_commit": git_head(),
              "subjects": config["subjects"],
              "input_text_pins": input_text_pins,
              "synthetic": False, "new_scientific_evaluation": False}
    if authorization:
        auth = read_json(args.authorization)
        require(auth.get("schema_version") == 1 and auth.get("status") == "direct_user_authorized",
                "Missing direct-user authorization binding")
        require(auth.get("config_sha256") == report["config_sha256"]
                and auth.get("protocol_sha256") == report["protocol_sha256"]
                and auth.get("source_code_pins") == config["source_code_pins"]
                and auth.get("host_identity") == report["host_identity"]
                and auth.get("output") == str(Path(args.output).resolve()),
                "Authorization config/protocol/code/host/output binding mismatch")
        prompt = Path(auth["prompt_path"])
        require(prompt.is_file() and sha256_file(prompt) == auth["prompt_sha256"],
                "Authorization prompt binding mismatch")
        report["authorization_sha256"] = sha256_file(args.authorization)
    return config, report


def load_verified_source_model(baseline_root, subject):
    import numpy as np
    baseline_root = Path(baseline_root)
    original = read_json(baseline_root / "execution_receipt.json")
    participant = baseline_root / subject / "participant_receipt.json"
    require(sha256_file(participant) == original["outputs"][f"{subject}/participant_receipt.json"],
            "Original participant receipt hash mismatch")
    record = read_json(participant)
    require(record["source_frozen"] and record["source_parameter_sha256_before"]
            == record["source_parameter_sha256_after"], "Historical source not frozen")
    arrays = None
    for name in ("source_before.npz", "source_after.npz"):
        path = baseline_root / subject / name
        expected = original["outputs"][f"{subject}/{name}"]
        require(sha256_file(path) == expected, "Frozen source NPZ SHA mismatch")
        with np.load(path, allow_pickle=False) as archive:
            loaded = {key: archive[key].copy() for key in archive.files}
        validate_source_arrays(loaded)
        require(array_digest(loaded) == record["source_parameter_sha256_before"],
                "Frozen source array digest mismatch")
        require(sha256_file(path) == expected, "Frozen source NPZ changed during read")
        if arrays is None:
            arrays = loaded
    return arrays


def verify_historical_fit_scope(baseline_root, subject, trials):
    root = Path(baseline_root)
    original = read_json(root / "execution_receipt.json")
    relative = f"{subject}/fit_access_audit.json"
    path = root / relative
    require(sha256_file(path) == original["outputs"][relative], "Original fit audit SHA changed")
    historical = read_json(path)
    source = {r["trial_id"] for r in trials if r["role"] == "source_train"}
    expected = {(OLD_METHODS[0], "ses-0"): source}
    sessions = {r["session"] for r in trials if r["role"] == "target_support"}
    for session in sessions:
        support = {r["trial_id"] for r in trials
                   if r["role"] == "target_support" and r["session"] == session}
        for method in OLD_METHODS[1:]:
            expected[(method, session)] = source | support
    observed = {(row["method"], row["session"]): row for row in historical}
    require(len(observed) == len(historical) and set(observed) == set(expected),
            "Original fit audit method/session mismatch")
    for key, wanted in expected.items():
        row = observed[key]
        require(set(row["trial_ids"]) == wanted and len(row["trial_ids"]) == len(wanted)
                and row["query_and_validation_disjoint"], "Historical full-budget fit scope changed")
    return {"fit_access_audit_sha256": sha256_file(path), "exact_original_fit_ids_verified": True}


def verify_subject_inputs_after(baseline_root, subject, source_root, provenance):
    original = read_json(Path(baseline_root) / "execution_receipt.json")
    for name in ("source_before.npz", "source_after.npz", "participant_receipt.json", "fit_access_audit.json"):
        relative = f"{subject}/{name}"
        require(sha256_file(Path(baseline_root) / relative) == original["outputs"][relative],
                "Historical source input changed after subject execution")
    verified = provenance["verified_source_files"]
    for relative, record in verified.items():
        require(sha256_file(Path(source_root) / relative) == record["sha256"],
                "Source file changed after subject execution: " + relative)
    return {"historical_source_files_rechecked": 4, "dataset_files_rechecked": len(verified),
            "all_hashes_unchanged": True}


def is_launcher_command(command, cwd):
    """Recognize this script after ordinary Python interpreter switches."""
    index = 1
    no_argument = {"-u", "-B", "-E", "-I", "-s", "-S", "-q", "-O", "-OO", "-v"}
    while index < len(command):
        token = command[index]
        if token == "--":
            index += 1
            break
        if token in {"-W", "-X"}:
            index += 2
        elif token in no_argument or token.startswith(("-W", "-X")):
            index += 1
        else:
            break
    if index >= len(command):
        return False
    return ((Path(cwd) / command[index]).resolve() == Path(__file__).resolve()
            and "--execute" in command[index + 1:]
            and "--worker-internal" not in command[index + 1:])


def verify_common_inputs_after(args, config, report):
    verify_pins(config["source_code_pins"])
    verify_input_text_pins(config, read_json(ROOT / config["old_config"]))
    require(sha256_file(args.config) == report["config_sha256"]
            and sha256_file(args.protocol) == report["protocol_sha256"]
            and sha256_file(args.authorization) == report["authorization_sha256"]
            and sha256_file(args.split_manifest) == config["split_manifest_sha256"]
            and sha256_file(ROOT / config["old_config"]) == config["old_config_sha256"]
            and sha256_file(Path(args.baseline_root) / "execution_receipt.json")
                == config["baseline_execution_receipt_sha256"], "Bound inputs changed during execution")
    old_receipt = read_json(Path(args.baseline_root) / "execution_receipt.json")
    require(sha256_file(args.saved_predictions) == old_receipt["outputs"]["query_predictions.csv"],
            "Saved predictions changed during execution")
    authorization = read_json(args.authorization)
    require(sha256_file(authorization["prompt_path"]) == authorization["prompt_sha256"],
            "Authorizing prompt changed during execution")


def _worker(args):
    verify_pins(read_json(args.config)["source_code_pins"])
    monitor = load_module("component_budget_worker_monitor", REQUIRED_PINS[1])
    claim = read_json(args.claim)
    canonical_claim = Path(args.output).with_name(Path(args.output).name + ".operation") / "claim.json"
    require(Path(args.claim).resolve() == canonical_claim.resolve()
            and not Path(args.claim).is_symlink()
            and claim["output"] == str(Path(args.output).resolve()), "Noncanonical worker claim")
    parent = os.getppid()
    parent_cmd = (Path("/proc") / str(parent) / "cmdline").read_bytes().split(b"\0")
    parent_cmd = [value.decode("utf-8") for value in parent_cmd if value]
    parent_cwd = (Path("/proc") / str(parent) / "cwd").resolve()
    require(is_launcher_command(parent_cmd, parent_cwd),
            "Worker parent is not this monitored --execute entrypoint")
    require(claim["launcher_pid"] == os.getppid()
            and monitor.process_record(os.getppid(), Path("/proc"))["start_ticks"] == claim["launcher_start_ticks"]
            and claim["host_identity"] == monitor.container_identity(), "Worker launcher identity mismatch")
    require(time.monotonic() < claim["deadline_monotonic"] - 30
            and claim["deadline_monotonic"] <= time.monotonic() + MAX_SECONDS
            and abs((claim["deadline_epoch"] - time.time())
                    - (claim["deadline_monotonic"] - time.monotonic())) < 2,
            "Worker execution deadline invalid")
    fd = int(args.lock_fd)
    inherited, actual = os.fstat(fd), LOCK.stat()
    require((inherited.st_dev, inherited.st_ino) == (actual.st_dev, actual.st_ino),
            "Worker shared CPU lock identity mismatch")
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(not claim.get("synthetic", True), "Worker cannot claim synthetic scope")
    # Preflight requires fresh output, so verify against the launcher's still-fresh
    # scientific child directory, not its already-created monitoring directory.
    config, report = preflight(args, authorization=True)
    require(report["config_sha256"] == claim["config_sha256"]
            and report["authorization_sha256"] == claim["authorization_sha256"], "Worker claim changed")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        require(os.environ.get(name) == "1", "Worker numerical threads not pinned")
    if config.get("analysis_mode", "budget") == "phase_window":
        phase = load_module("bound_phase_window_consumer", PHASE_SCRIPT)
        phase.execute_bound_inputs(args, config)
        verify_common_inputs_after(args, config, report)
        return
    from learning_preserving_bci.datasets.kumar import load_subject
    output = Path(args.output)
    output.mkdir(exist_ok=False)
    with Path(args.saved_predictions).open(newline="", encoding="utf-8") as stream:
        saved = list(csv.DictReader(stream))
    all_results, dataset_bindings, source_bindings = [], {}, {}
    for subject in config["subjects"]:
        require(time.time() < claim["deadline_epoch"] - 30, "Execution cleanup reserve reached")
        arrays = load_verified_source_model(args.baseline_root, subject)
        loaded = load_subject(ROOT / config["data_root"], subject, ROOT / config["old_config"],
                              args.split_manifest, allowed_roles={"source_train", "target_support", "target_query"})
        historical_fit = verify_historical_fit_scope(args.baseline_root, subject, loaded.metadata)
        result = run_budget_subject(loaded.X, loaded.y, loaded.metadata, arrays, saved, config,
                                    output / subject, model_sink=lambda context, state: save_model_state(
                                        output / "model_states" / subject, context, state))
        write_json(output / subject / "loader_provenance.json", loaded.provenance)
        write_json(output / subject / "historical_fit_scope_verification.json", historical_fit)
        postcheck = verify_subject_inputs_after(args.baseline_root, subject,
                                               ROOT / config["data_root"], loaded.provenance)
        write_json(output / subject / "input_after_verification.json", postcheck)
        dataset_bindings.update({str(ROOT / config["data_root"] / relative): record["sha256"]
                                 for relative, record in loaded.provenance["verified_source_files"].items()})
        original = read_json(Path(args.baseline_root) / "execution_receipt.json")
        source_bindings.update({str(Path(args.baseline_root) / subject / name):
                               original["outputs"][f"{subject}/{name}"] for name in (
                                   "source_before.npz", "source_after.npz", "participant_receipt.json", "fit_access_audit.json")})
        all_results.append(result)
        del loaded, arrays
    combined = {key: [row for result in all_results for row in result[key]]
                for key in ("predictions", "metrics", "features", "outcomes", "fit_audits")}
    combined.update({"provenance": {"schema_version": 1, "synthetic": False,
                    "software_validation_only": False, "support_order": "chronological",
                    "rows": [row for result in all_results for row in result["provenance"]["rows"]]},
                     "source_parameter_sha256_before": "per_subject_receipts",
                     "source_parameter_sha256_after": "per_subject_receipts",
                     "synthetic": False, "software_validation_only": False})
    _write_result(output, combined)
    verify_common_inputs_after(args, config, report)
    for path, expected in {**dataset_bindings, **source_bindings}.items():
        require(sha256_file(path) == expected, "Bound scientific input changed after execution: " + path)
    write_json(output / "input_before_after_manifest.json", {
        "schema_version": 1, "before_after_equal": True,
        "source_model_and_fit_inputs": source_bindings, "dataset_inputs": dataset_bindings,
        "loader_text_inputs": config["input_text_pins"],
        "verification": "Fresh hashes before use and after all scientific consumers; no source-model refit"})
    write_json(output / "execution_receipt.json", {
        "status": "completed_exploratory_cpu_budget_replay", "synthetic": False,
        "source_models_refitted": False, "historical_full_budget_predictions_reused": True,
        "query_never_fitted": True, "config_sha256": report["config_sha256"],
        "source_git_commit": report["source_git_commit"],
        "protocol_sha256": report["protocol_sha256"], "runtime": monitor.runtime_metadata(),
        "source_code_pins": config["source_code_pins"],
        "outputs": {str(path.relative_to(output)): sha256_file(path)
                    for path in sorted(output.rglob("*")) if path.is_file()}})


def execute(args):
    config, report = preflight(args, authorization=True)
    monitor = load_module("component_budget_launcher_monitor", REQUIRED_PINS[1])
    state = Path(args.output).with_name(Path(args.output).name + ".operation")
    require(not os.path.lexists(state), "Operation claim exists; automatic retry forbidden")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    process, history, state_owned = None, {}, False
    started, absolute_deadline = time.monotonic(), time.monotonic() + MAX_SECONDS
    peak, samples, status, failure = 0, 0, "failed_preserved", None
    cleanup_failure, signals, old_handlers = None, [], {}
    pending_error = None

    def interrupted(signum, frame):
        for number in old_handlers:
            signal.signal(number, signal.SIG_IGN)
        raise InterruptedError("Launcher received " + signal.Signals(signum).name)

    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state.mkdir(exist_ok=False)
        state_owned = True
        for number in (signal.SIGTERM, signal.SIGHUP):
            old_handlers[number] = signal.signal(number, interrupted)
        claim = {"schema_version": 1, "launcher_pid": os.getpid(),
                 "launcher_start_ticks": monitor.process_record(os.getpid(), Path("/proc"))["start_ticks"],
                 "host_identity": report["host_identity"], "config_sha256": report["config_sha256"],
                 "authorization_sha256": report["authorization_sha256"], "synthetic": False,
                 "deadline_epoch": time.time() + max(0, absolute_deadline - time.monotonic()),
                 "deadline_monotonic": absolute_deadline, "automatic_retries": 0,
                 "output": str(Path(args.output).resolve())}
        claim_path = state / "claim.json"
        with monitor.deadline_guard(absolute_deadline - 30):
            write_json(claim_path, claim)
            write_json(state / "preflight.json", report)
        command = [sys.executable, str(Path(__file__).resolve()), "--worker-internal",
                   "--config", str(Path(args.config).resolve()), "--protocol", str(Path(args.protocol).resolve()),
                   "--split-manifest", str(Path(args.split_manifest).resolve()),
                   "--baseline-root", str(Path(args.baseline_root).resolve()),
                   "--saved-predictions", str(Path(args.saved_predictions).resolve()),
                   "--output", str(Path(args.output).resolve()),
                   "--authorization", str(Path(args.authorization).resolve()),
                   "--claim", str(claim_path), "--lock-fd", str(lock_fd)]
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT / "scripts"))
        with (state / "worker.log").open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, pass_fds=(lock_fd,))
            with monitor.deadline_guard(absolute_deadline - 30):
                with (state / "resource_samples.jsonl").open("x", encoding="utf-8") as resource_log:
                    while process.poll() is None:
                        require(time.monotonic() < absolute_deadline - 30,
                                "3600-second execution window reached")
                        try:
                            sample = monitor.running_memory(process.pid, observed_descendants=history)
                        except (OSError, KeyError, ValueError):
                            if process.poll() is not None:
                                break
                            raise
                        sample["elapsed_seconds"] = time.monotonic() - started
                        sample["free_output_disk_bytes"] = shutil.disk_usage(state).free
                        resource_log.write(json.dumps(sample, separators=(",", ":")) + "\n")
                        resource_log.flush()
                        samples += 1
                        peak = max(peak, sample["consumer_rss_bytes"])
                        require(sample["consumer_rss_bytes"] <= 2 * GIB, "Consumer RSS over 2 GiB")
                        require(sample["host_available_bytes"] >= GIB
                                and (sample["cgroup_headroom_bytes"] is None
                                     or sample["cgroup_headroom_bytes"] >= GIB), "Free memory below 1 GiB")
                        require(sample["free_output_disk_bytes"] >= 2 * GIB, "Disk reserve below 2 GiB")
                        try:
                            process.wait(timeout=min(POLL_SECONDS, max(
                                0, absolute_deadline - 30 - time.monotonic())))
                        except subprocess.TimeoutExpired:
                            pass
            require(process.wait() == 0, "Scientific worker failed; inspect worker.log")
            status = "consumer_exited_zero_pending_cleanup_and_independent_audit"
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error)}
        pending_error = error
    finally:
        try:
            if process is not None:
                try:
                    _, signals = monitor.stop_tracked_process(
                        process, min(30, max(0, absolute_deadline - time.monotonic())), history)
                    if signals and pending_error is None:
                        status = "descendant_cleanup_required_preserved"
                        pending_error = RuntimeError("Descendants required cleanup after scientific root exit")
                    elif pending_error is None:
                        status = "consumer_exited_zero_pending_independent_audit"
                except BaseException as error:
                    cleanup_failure = {"type": type(error).__name__, "message": str(error)}
                    signals = getattr(error, "signal_events", [])
                    status = "cleanup_failed_preserved"
                    if pending_error is None:
                        pending_error = error
            if state_owned:
                write_json(state / "operation_receipt.json", {
                    "status": status, "failure": failure, "cleanup_failure": cleanup_failure,
                    "signals": signals, "samples": samples, "peak_sampled_consumer_rss_bytes": peak,
                    "automatic_retries": 0, "max_seconds": MAX_SECONDS, "poll_seconds": POLL_SECONDS,
                    "elapsed_seconds": time.monotonic() - started,
                    "synthetic": False, "new_scientific_evaluation": process is not None,
                    "scientific_completion_accepted": False, "independently_audited": False})
        finally:
            for number, previous in old_handlers.items():
                signal.signal(number, previous)
            os.close(lock_fd)
    if pending_error is not None:
        raise pending_error
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "protocol", "split-manifest", "baseline-root", "saved-predictions", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--authorization")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--worker-internal", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--claim", help=argparse.SUPPRESS)
    parser.add_argument("--lock-fd", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_internal:
        require(args.claim is not None and args.lock_fd is not None and not args.execute,
                "Worker requires inherited launcher claim and lock")
        _worker(args)
    elif args.execute:
        require(args.authorization is not None, "Execution needs bound direct-user authorization")
        execute(args)
    else:
        require(args.claim is None and args.lock_fd is None, "Private worker arguments forbidden")
        _, report = preflight(args)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
