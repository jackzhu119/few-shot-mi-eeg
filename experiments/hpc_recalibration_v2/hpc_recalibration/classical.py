"""V2 NumPy binary CSP/LDA comparators, explicitly distinct from old MNE fits.

Fixed linear covariance shrinkage replaces the old MNE Ledoit-Wolf estimator;
these are new matched V2 comparators, not a claimed numerical reproduction of
accepted historical models. All class covariance/EA references use source and
current support only. Query labels are used exclusively by score_predictions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import signal
import time
import traceback

import numpy as np

from .data import Split, atomic_json, atomic_npz, load_split, resolve_input

METHODS = ("frozen", "lda_only", "full_csp", "ea_csp", "anchored_csp", "empirical_anchored_csp", "ea_empirical_anchored_csp", "ea_anchored_csp")
IMPLEMENTATION = "numpy_binary_csp_fixed_shrinkage_lda_v2"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _settings(config: dict) -> dict:
    c = config.get("classical", {})
    settings = {"n_components": int(c.get("n_components", 4)),
                "covariance_shrinkage": float(c.get("covariance_shrinkage", 0.1)),
                "lda_shrinkage": float(c.get("lda_shrinkage", 0.1)),
                "anchor_tau": float(c.get("anchor_tau", 20.0)),
                "implementation": IMPLEMENTATION}
    if (not 0 < settings["covariance_shrinkage"] < 1
            or not 0 < settings["lda_shrinkage"] < 1 or settings["anchor_tau"] <= 0
            or settings["n_components"] < 2):
        raise ValueError("invalid frozen classical settings")
    return settings


def trial_covariances(x: np.ndarray, trace_normalize: bool = True) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 3 or x.shape[2] < 2 or not np.isfinite(x).all():
        raise ValueError("invalid EEG array")
    centered = x - x.mean(axis=2, keepdims=True)
    covariance = centered @ centered.transpose(0, 2, 1) / (x.shape[2] - 1)
    traces = np.trace(covariance, axis1=1, axis2=2)
    if np.any(traces <= 0):
        raise ValueError("zero-energy trial cannot define a covariance reference")
    if trace_normalize:
        covariance /= traces[:, None, None]
    return covariance


def _shrink(matrix: np.ndarray, amount: float) -> np.ndarray:
    scale = float(np.trace(matrix) / len(matrix))
    if not np.isfinite(matrix).all() or not np.isfinite(scale) or scale <= 0:
        raise ValueError("nonfinite or zero-energy covariance")
    return (1 - amount) * matrix + amount * scale * np.eye(len(matrix))


def inverse_root(matrix: np.ndarray) -> np.ndarray:
    eigenvalues, vectors = np.linalg.eigh((matrix + matrix.T) * 0.5)
    if np.any(eigenvalues <= 0) or not np.isfinite(eigenvalues).all():
        raise ValueError("reference covariance must be positive definite")
    return (vectors * eigenvalues ** -0.5) @ vectors.T


def ea_reference(x: np.ndarray, shrinkage: float) -> np.ndarray:
    return inverse_root(_shrink(trial_covariances(x, trace_normalize=False).mean(axis=0), shrinkage))


def _csp_filters(class_covariances: list[np.ndarray], n_components: int) -> np.ndarray:
    a, b = class_covariances
    whitening = inverse_root(a + b)
    _, vectors = np.linalg.eigh(whitening @ a @ whitening.T)
    count = min(n_components, len(a))
    # Alternating extremes, no outcome-dependent component selection.
    order = []
    for low in range((count + 1) // 2):
        order.append(low)
        if len(order) < count:
            order.append(len(a) - 1 - low)
    filters = (whitening @ vectors[:, order]).T
    for row in filters:
        if row[np.argmax(np.abs(row))] < 0:
            row *= -1
    return filters


def log_variance(x: np.ndarray, filters: np.ndarray) -> np.ndarray:
    filtered = np.einsum("kc,nct->nkt", filters, np.asarray(x, dtype=np.float64))
    variance = np.var(filtered, axis=2, ddof=0)
    return np.log(np.maximum(variance, np.finfo(np.float64).tiny))


def _fit_lda(features: np.ndarray, labels: np.ndarray, classes: np.ndarray,
             shrinkage: float) -> tuple[np.ndarray, np.ndarray]:
    means = np.stack([features[labels == c].mean(axis=0) for c in classes])
    counts = np.asarray([np.sum(labels == c) for c in classes])
    residual = np.concatenate([features[labels == c] - means[i] for i, c in enumerate(classes)])
    denominator = len(features) - len(classes)
    if denominator <= 0:
        raise ValueError("insufficient samples for pooled LDA covariance")
    covariance = residual.T @ residual / denominator
    pooled = _shrink(covariance, shrinkage)
    weights = np.linalg.solve(pooled, means.T).T
    priors = counts / counts.sum()
    bias = -0.5 * np.sum(means * weights, axis=1) + np.log(priors)
    return weights, bias


@dataclass
class Decoder:
    filters: np.ndarray
    weights: np.ndarray
    bias: np.ndarray
    classes: np.ndarray
    query_whitener: np.ndarray
    metadata: dict

    def predict(self, x: np.ndarray) -> np.ndarray:
        aligned = np.einsum("cd,ndt->nct", self.query_whitener, x)
        features = log_variance(aligned, self.filters)
        return self.classes[np.argmax(features @ self.weights.T + self.bias, axis=1)]

    def save(self, path: str | Path) -> None:
        atomic_npz(path, filters=self.filters, weights=self.weights, bias=self.bias,
                   classes=self.classes, query_whitener=self.query_whitener,
                   metadata_json=np.asarray(json.dumps(self.metadata, sort_keys=True, allow_nan=False)))

    @classmethod
    def load(cls, path: str | Path) -> "Decoder":
        with np.load(path, allow_pickle=False) as archive:
            values = [archive[k].copy() for k in
                      ("filters", "weights", "bias", "classes", "query_whitener")]
            metadata = json.loads(str(archive["metadata_json"].item()))
        if not all(np.isfinite(v).all() for v in values):
            raise ValueError(f"nonfinite saved model: {path}")
        return cls(*values, metadata)


def fit_decoder(source: Split, support: Split | None, method: str, config: dict,
                source_model: Decoder | None = None) -> Decoder:
    """Fit a binary comparator. The signature deliberately has no query input."""
    if method not in METHODS:
        raise ValueError(f"unknown method {method}")
    settings = _settings(config)
    classes = np.unique(source.y)
    if len(classes) != 2 or not np.array_equal(classes, [0, 1]):
        raise ValueError("V2 CSP comparators require binary source labels mapped to 0/1")
    if min(np.sum(source.y == c) for c in classes) < 2:
        raise ValueError("each source class needs at least two trials")
    if support is not None and (support.x.shape[1:] != source.x.shape[1:]
                                or not set(support.y.tolist()) <= set(classes.tolist())):
        raise ValueError("support shape/classes differ from source")
    if method != "frozen" and (support is None or len(support) == 0):
        raise ValueError("updating comparator needs actual support trials")
    source_x = source.x.astype(np.float64)
    support_x = support.x.astype(np.float64) if support is not None else None
    query_whitener = np.eye(source.x.shape[1])
    if method in ("ea_csp", "ea_empirical_anchored_csp", "ea_anchored_csp"):
        source_whitener = ea_reference(source_x, settings["covariance_shrinkage"])
        query_whitener = ea_reference(support_x, settings["covariance_shrinkage"])
        source_x = np.einsum("cd,ndt->nct", source_whitener, source_x)
        support_x = np.einsum("cd,ndt->nct", query_whitener, support_x)
    source_covs = trial_covariances(source_x)
    source_means = [source_covs[source.y == c].mean(axis=0) for c in classes]
    alpha = {}
    if method in ("anchored_csp", "empirical_anchored_csp", "ea_empirical_anchored_csp", "ea_anchored_csp"):
        support_covs = trial_covariances(support_x)
        selected_covariances = []
        for i, c in enumerate(classes):
            class_covs = support_covs[support.y == c]
            n = len(class_covs)
            weight = 0.0
            if n:
                target = class_covs.mean(axis=0)
                if method in ("anchored_csp", "ea_anchored_csp"):
                    weight = len(support) / (len(support) + settings["anchor_tau"])
                elif n >= 2:
                    variance = np.sum((class_covs - target) ** 2) / (n * (n - 1))
                    difference = float(np.sum((target - source_means[i]) ** 2))
                    weight = max(0.0, 1.0 - variance / difference) if difference > 0 else 0.0
                selected_covariances.append((1 - weight) * source_means[i] + weight * target)
            else:
                selected_covariances.append(source_means[i])
            alpha[str(int(c))] = float(weight)
    elif method in ("full_csp", "ea_csp"):
        all_covs = np.concatenate([source_covs, trial_covariances(support_x)])
        all_y = np.concatenate([source.y, support.y])
        selected_covariances = [all_covs[all_y == c].mean(axis=0) for c in classes]
    else:
        selected_covariances = source_means
    if method in ("frozen", "lda_only") and source_model is not None:
        filters = source_model.filters.copy()
    else:
        filters = _csp_filters([_shrink(c, settings["covariance_shrinkage"])
                                for c in selected_covariances], settings["n_components"])
    if method == "frozen" and source_model is not None:
        weights, bias = source_model.weights.copy(), source_model.bias.copy()
        fit_ids = source.trial_id.tolist()
    else:
        fit_x = source_x if method == "frozen" else np.concatenate([source_x, support_x])
        fit_y = source.y if method == "frozen" else np.concatenate([source.y, support.y])
        weights, bias = _fit_lda(log_variance(fit_x, filters), fit_y, classes, settings["lda_shrinkage"])
        fit_ids = source.trial_id.tolist() + ([] if method == "frozen" else support.trial_id.tolist())
    metadata = {"implementation": IMPLEMENTATION, "method": method, "settings": settings,
                "fit_trial_ids": fit_ids, "source_trial_ids": source.trial_id.tolist(),
                "support_trial_ids": [] if method == "frozen" else support.trial_id.tolist(),
                "classwise_update_weights": alpha, "query_used_for_fitting": False,
                "ea_reference_scope": "source/current_support_only" if method in ("ea_csp", "ea_empirical_anchored_csp", "ea_anchored_csp") else None,
                "historical_MNE_model_reproduction": False}
    return Decoder(filters, weights, bias, classes, query_whitener, metadata)


def score_predictions(y: np.ndarray, predicted: np.ndarray, classes: np.ndarray) -> dict:
    counts = {str(int(c)): int(np.sum(y == c)) for c in classes}
    recall = {str(int(c)): (float(np.mean(predicted[y == c] == c)) if counts[str(int(c))] else None)
              for c in classes}
    missing = any(count == 0 for count in counts.values())
    return {"balanced_accuracy": None if missing else float(np.mean(list(recall.values()))),
            "class_counts": counts, "class_recall": recall, "n_query": len(y),
            "status": "undefined_missing_query_class" if missing else "ok"}


def _digest_split(split: Split) -> str:
    digest = hashlib.sha256()
    for value in (split.x, split.y, split.trial_id, split.run_id):
        digest.update(str(value.dtype).encode())
        digest.update(str(value.shape).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _identity(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_task(task: dict, config: dict) -> int:
    """Fit all current-support models first, then resume independent evaluation shards."""
    task_id = str(task["task_id"])
    if not task_id or task_id in (".", "..") or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in task_id):
        raise ValueError("unsafe task identifier")
    root = Path(config["output_root"]) / "tasks" / task_id
    root.mkdir(parents=True, exist_ok=True)
    with (root / "worker.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"task_id": task["task_id"], "phase": "already_running"}), flush=True)
            return 0
        return _run_locked(task, config, root)


def _run_locked(task: dict, config: dict, root: Path) -> int:
    methods = config.get("classical_methods", list(METHODS))
    if any(m not in METHODS for m in methods) or not methods:
        raise ValueError("invalid classical_methods")
    budgets = config.get("budgets", [4, 8, 12, 16, 20])
    if not budgets or any(type(n) is not int or n <= 0 for n in budgets):
        raise ValueError("budgets must be positive integers")
    task_identity = _identity({"task": task, "settings": _settings(config),
                               "methods": methods, "budgets": budgets,
                               "experiment_id": config.get("experiment_id")})
    complete_path = root / "complete.json"
    if complete_path.exists():
        completed = json.loads(complete_path.read_text())
        if completed["task_identity"] != task_identity:
            raise ValueError("completed task science changed; use a new experiment version")
        return 0
    stop = {"signal": None}
    handlers = {}
    for sig in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT):
        handlers[sig] = signal.signal(sig, lambda number, frame: stop.update(signal=number))
    started = time.monotonic()
    heartbeat = float(config.get("heartbeat_seconds", 30))
    last_heartbeat = 0.0
    fitted_count = int((root / "source_model.npz").exists())
    fitted_count += sum(1 for p in (root / "models").glob("*.npz") if not p.stem.endswith("__frozen"))
    processed = 0

    def progress(phase: str, **extra) -> None:
        nonlocal last_heartbeat
        value = {"task_id": task["task_id"], "family": "classical", "phase": phase,
                 "step": fitted_count, "processed_samples": processed, "utc": utcnow(),
                 "updated_at": utcnow(),
                 "elapsed_seconds": time.monotonic() - started, "task_identity": task_identity,
                 "synthetic": bool(task.get("synthetic", False)), **extra}
        atomic_json(root / "progress.json", value)
        if time.monotonic() - last_heartbeat >= heartbeat or phase in ("completed", "failed", "paused"):
            print(json.dumps(value, allow_nan=False), flush=True)
            last_heartbeat = time.monotonic()

    def paused() -> int | None:
        if stop["signal"] is None:
            return None
        code = 75 if stop["signal"] == signal.SIGUSR1 else 130
        progress("paused", signal=stop["signal"], exit_code=code)
        return code

    try:
        source = load_split(resolve_input(config["data_root"], task["source_train"]))
        source_hash = _digest_split(source)
        source_id = _identity({"task_identity": task_identity, "source": source_hash})
        source_path = root / "source_model.npz"
        if source_path.exists():
            source_model = Decoder.load(source_path)
            if source_model.metadata.get("fit_identity") != source_id:
                raise ValueError("source model/input identity changed; use a new experiment version")
        else:
            progress("source_fit")
            source_model = fit_decoder(source, None, "frozen", config)
            source_model.metadata["fit_identity"] = source_id
            source_model.save(source_path)
            fitted_count += 1
        if (code := paused()) is not None:
            return code
        model_records = []
        # Entire fit stage precedes the first query-array load.
        for target in task["targets"]:
            support = load_split(resolve_input(config["data_root"], target["support"]))
            if set(source.trial_id.tolist()) & set(support.trial_id.tolist()):
                raise ValueError("source/support identity overlap")
            session = str(target["session"])
            if not session or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in session):
                raise ValueError("unsafe target session identifier")
            for budget in budgets:
                subset = support.prefix(min(budget, len(support)))
                for method in methods:
                    if (code := paused()) is not None:
                        return code
                    stem = f"{session}__n{budget}__{method}"
                    path = root / "models" / (stem + ".npz")
                    fit_id = _identity({"task_identity": task_identity, "source": source_hash,
                                        "support": _digest_split(subset), "method": method})
                    if path.exists():
                        model = Decoder.load(path)
                        if model.metadata.get("fit_identity") != fit_id:
                            raise ValueError(f"saved model identity mismatch: {stem}")
                    else:
                        progress("fit", session=session, method=method, budget=budget)
                        model = fit_decoder(source, subset, method, config, source_model=source_model)
                        model.metadata.update({"fit_identity": fit_id, "task_identity": task_identity,
                                               "budget_requested": budget,
                                               "n_support_actual": 0 if method == "frozen" else len(subset),
                                               "n_support_available": len(subset)})
                        model.save(path)
                        fitted_count += int(method != "frozen")
                    model_records.append((target, budget, method, path, stem))
                    if (code := paused()) is not None:
                        return code
        source_query = task.get("source_query")
        if source_query:
            model_records.insert(0, ({"session": "source", "query": source_query}, 0, "frozen",
                                     source_path, "source__n0__frozen"))
        summaries = []
        for target, budget, method, path, stem in model_records:
            if (code := paused()) is not None:
                return code
            shard_path = root / "evaluation" / (stem + ".json")
            model = Decoder.load(path)
            if shard_path.exists():
                saved = json.loads(shard_path.read_text())
                if saved["fit_identity"] != model.metadata["fit_identity"]:
                    raise ValueError("evaluation/model identity mismatch")
                summaries.append(saved["metrics"] | {k: saved[k] for k in ("session", "method", "budget_requested")})
                continue
            query = load_split(resolve_input(config["data_root"], target["query"]))
            if set(query.trial_id.tolist()) & set(model.metadata["fit_trial_ids"]):
                raise ValueError("query/training identity overlap")
            progress("evaluation", session=target["session"], method=method, budget=budget)
            predicted = model.predict(query.x) if len(query) else np.empty(0, dtype=np.int64)
            metrics = score_predictions(query.y, predicted, model.classes)
            saved = {"task_id": task["task_id"], "dataset": task["dataset"],
                     "participant": task["participant"], "session": target["session"],
                     "method": method, "budget_requested": budget,
                     "n_support_actual": model.metadata.get("n_support_actual", 0),
                     "n_support_available": model.metadata.get("n_support_available", 0),
                     "fit_identity": model.metadata["fit_identity"], "query_identity": _digest_split(query),
                     "metrics": metrics, "trial_ids": query.trial_id.tolist(), "y": query.y.tolist(),
                     "prediction": predicted.tolist(), "query_used_for_fitting": False,
                     "synthetic": bool(task.get("synthetic", False)), "completed_utc": utcnow()}
            atomic_json(shard_path, saved)
            processed += len(query)
            summaries.append(metrics | {k: saved[k] for k in ("session", "method", "budget_requested")})
            atomic_json(root / "summary.json", {"results": summaries})
            if (code := paused()) is not None:
                return code
        atomic_json(root / "summary.json", {"results": summaries})
        atomic_json(complete_path, {"task_id": task["task_id"], "task_identity": task_identity,
                                   "status": "completed",
                                   "dataset": task["dataset"], "participant": task["participant"],
                                   "seed": task.get("seed"), "family": "classical",
                                   "synthetic": bool(task.get("synthetic", False)),
                                   "software_validation_only": bool(task.get("synthetic", False)),
                                   "completed_utc": utcnow(), "summary": summaries,
                                   "implementation": IMPLEMENTATION, "query_used_for_fitting": False})
        progress("completed", result_count=len(summaries))
        return 0
    except BaseException as exc:
        text = traceback.format_exc()
        failure_path = root / f"failure_{time.time_ns()}.json"
        atomic_json(failure_path, {"task_id": task["task_id"], "utc": utcnow(),
                                  "exception_type": type(exc).__name__, "traceback": text})
        progress("failed", error_type=type(exc).__name__)
        raise
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
