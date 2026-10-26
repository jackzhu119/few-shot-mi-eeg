"""Small V3 dispatcher and resumable geometric fits/evaluation shards."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
from pathlib import Path
import signal
import time
import traceback

import numpy as np

from hpc_recalibration.classical import score_predictions
from hpc_recalibration.data import atomic_json, atomic_npz, load_split, resolve_input
from .runtime import utc_now


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def split_identity(split):
    return identity(
        {
            "trial_ids": split.trial_id.tolist(),
            "run_ids": split.run_id.tolist(),
            "labels": split.y.tolist(),
            "shape": list(split.x.shape),
        }
    )


class Signals:
    def __init__(self):
        self.code = None

    def __enter__(self):
        self.previous = {
            n: signal.getsignal(n) for n in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT)
        }
        for number in self.previous:
            signal.signal(number, self.request)
        return self

    def request(self, number, frame):
        if number in (signal.SIGTERM, signal.SIGINT):
            self.code = 130
        elif self.code is None:
            self.code = 75

    def __exit__(self, *unused):
        for number, handler in self.previous.items():
            signal.signal(number, handler)


def run_task(task, config):
    effective = copy.deepcopy(config)
    effective["science"].update(task.get("science_overrides", {}))
    if task["family"] == "geometry":
        return run_geometry(task, effective)
    if task["family"] == "simulation":
        from .simulation import run_task as run_simulation

        return run_simulation(task, effective)
    from . import neural

    if task["family"] == "pooled_pretrain":
        return neural.run_pretrain(task, effective)
    if task["family"] == "neural":
        return neural.run_task(task, effective)
    raise ValueError("Unknown discovery task family")


def run_geometry(task, config):
    from .geometry import Decoder, fit

    output = Path(config["output_root"]) / "tasks" / task["task_id"]
    output.mkdir(parents=True, exist_ok=True)
    task_id = identity(
        {"task": task, "science": config["science"], "version": config["scientific_version"]}
    )
    with (output / "task.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 73
        complete = output / "complete.json"
        if complete.is_file():
            if json.loads(complete.read_text())["identity"] != task_id:
                raise ValueError("Completed geometric scientific identity changed")
            return 0
        with Signals() as signals:
            try:
                return _geometry(task, config, output, task_id, signals, Decoder, fit)
            except BaseException:
                text = traceback.format_exc()
                print(text, flush=True)
                try:
                    atomic_json(
                        output / "failures" / f"{time.time_ns()}.json",
                        {"task_id": task["task_id"], "traceback": text, "utc": utc_now()},
                    )
                except OSError:
                    traceback.print_exc()
                raise


def _geometry(task, config, output, task_id, signals, Decoder, fit):
    science = config["science"]
    steps = 0
    last_emit = 0.0

    def progress(phase, **fields):
        nonlocal last_emit
        row = {
            "task_id": task["task_id"],
            "family": "geometry",
            "phase": phase,
            "step": steps,
            "updated_at": utc_now(),
            "synthetic": bool(task.get("synthetic", False)),
            **fields,
        }
        atomic_json(output / "progress.json", row)
        now = time.monotonic()
        if now - last_emit >= float(config.get("heartbeat_seconds", 30)) or phase in (
            "completed",
            "paused",
            "failed",
        ):
            print(json.dumps(row, allow_nan=False), flush=True)
            last_emit = now

    source = load_split(resolve_input(config["data_root"], task["source_train"]))
    source_id = split_identity(source)
    settings = science["geometry"]
    methods = science["geometry_methods"]
    if len(set(methods)) != len(methods):
        raise ValueError("Duplicate geometric method declaration")
    source_path = output / "source_model.npz"
    source_fit_id = identity(
        {"task": task_id, "source": source_id, "method": "source_tangent_frozen"}
    )

    def model_at(path, subset, method, fit_id):
        nonlocal steps
        if path.is_file():
            model = Decoder.load(path)
            if model.metadata.get("fit_identity") != fit_id:
                raise ValueError("Saved model science/actual support changed")
        else:
            model = fit(source, subset, method, settings)
            model.metadata.update(
                fit_identity=fit_id,
                task_identity=task_id,
                synthetic=bool(task.get("synthetic", False)),
                software_validation_only=bool(task.get("synthetic", False)),
            )
            model.save(path)
            steps += 1
        atomic_json(output / "model_diagnostics" / (path.stem + ".json"), model.metadata)
        return model

    progress("source_fit")
    model_at(source_path, None, "source_tangent_frozen", source_fit_id)
    records = []
    supports = {}
    for target in task["targets"]:
        support = load_split(resolve_input(config["data_root"], target["support"]))
        if set(source.trial_id.tolist()) & set(support.trial_id.tolist()):
            raise ValueError("Source/support trial leakage")
        if source.x.shape[1:] != support.x.shape[1:]:
            raise ValueError("Source/support representation differs")
        supports[target["session"]] = support
        for budget in science["budgets"]:
            subset = support.prefix(min(int(budget), len(support)))
            for method in methods:
                if signals.code:
                    progress("paused", exit_code=signals.code)
                    return signals.code
                stem = f"{target['session']}__n{budget}__{method}"
                path = (
                    source_path
                    if method == "source_tangent_frozen"
                    else output / "models" / (stem + ".npz")
                )
                fit_id = (
                    source_fit_id
                    if method == "source_tangent_frozen"
                    else identity(
                        {
                            "task": task_id,
                            "source": source_id,
                            "support": split_identity(subset),
                            "method": method,
                        }
                    )
                )
                if method != "source_tangent_frozen":
                    progress("fit", session=target["session"], method=method, budget=budget)
                    model_at(path, subset, method, fit_id)
                records.append((target, budget, method, path, stem, len(subset)))
    # All model fitting precedes the first query tensor load.
    if task.get("source_query"):
        records.insert(
            0,
            (
                {"session": "source", "query": task["source_query"]},
                0,
                "source_tangent_frozen",
                source_path,
                "source__n0__source_tangent_frozen",
                0,
            ),
        )
    summaries = []
    query_cache = {}
    for target, budget, method, path, stem, actual in records:
        if signals.code:
            progress("paused", exit_code=signals.code)
            return signals.code
        model = Decoder.load(path)
        destination = output / "evaluation" / stem
        metric = destination / "metrics.json"
        if metric.is_file() and (destination / "predictions.npz").is_file():
            result = json.loads(metric.read_text())
            if result["fit_identity"] != model.metadata["fit_identity"]:
                raise ValueError("Completed prediction belongs to another fitted model")
            summaries.append(result)
            continue
        session = target["session"]
        if session not in query_cache:
            query = load_split(resolve_input(config["data_root"], target["query"]))
            fit_ids = set(source.trial_id.tolist())
            fit_ids.update(x for s in supports.values() for x in s.trial_id.tolist())
            if fit_ids & set(query.trial_id.tolist()):
                raise ValueError("Query/fitting trial leakage")
            query_cache[session] = query
        query = query_cache[session]
        qid = split_identity(query)
        partial = destination / "evaluation.partial.npz"
        probability = np.zeros((len(query), 2), dtype=np.float64)
        position = 0
        if partial.is_file():
            with np.load(partial, allow_pickle=False) as saved:
                if (
                    str(saved["fit_identity"].item()) != model.metadata["fit_identity"]
                    or str(saved["query_identity"].item()) != qid
                ):
                    raise ValueError("Partial evaluation input/model differs")
                position = int(saved["position"].item())
                probability[:] = saved["probabilities"]
        progress("evaluation", session=session, method=method, budget=budget)
        for start in range(position, len(query), 16):
            if signals.code:
                progress("paused", exit_code=signals.code)
                return signals.code
            end = min(start + 16, len(query))
            probability[start:end] = model.predict_probabilities(query.x[start:end])
            atomic_npz(
                partial,
                probabilities=probability,
                position=np.asarray(end),
                fit_identity=np.asarray(model.metadata["fit_identity"]),
                query_identity=np.asarray(qid),
            )
        prediction = probability.argmax(axis=1) if len(query) else np.empty(0, dtype=np.int64)
        scored = score_predictions(query.y, prediction, np.array([0, 1]))
        result = {
            "task_id": task["task_id"],
            "dataset": task["dataset"],
            "participant": task["participant"],
            "family": "geometry",
            "session": session,
            "method": method,
            "requested_budget": budget,
            "actual_budget": 0 if method == "source_tangent_frozen" else actual,
            "balanced_accuracy": scored["balanced_accuracy"],
            "n_query": len(query),
            "class_counts": [scored["class_counts"]["0"], scored["class_counts"]["1"]],
            "recalls": [scored["class_recall"]["0"], scored["class_recall"]["1"]],
            "accuracy": float(np.mean(query.y == prediction)) if len(query) else None,
            "collapse": bool(len(np.unique(prediction)) == 1) if len(query) else False,
            "fit_identity": model.metadata["fit_identity"],
            "query_identity": qid,
            "query_used_for_fitting": False,
            "selection_use": False,
            "completed_at": utc_now(),
            "synthetic": bool(task.get("synthetic", False)),
            "software_validation_only": bool(task.get("synthetic", False)),
        }
        atomic_npz(
            destination / "predictions.npz",
            probabilities=probability,
            labels=query.y,
            classes=np.array([0, 1]),
            trial_id=query.trial_id,
            run_id=query.run_id,
        )
        atomic_json(metric, result)
        summaries.append(result)
        atomic_json(output / "summary.json", {"task_id": task["task_id"], "results": summaries})
    atomic_json(
        output / "complete.json",
        {
            "task_id": task["task_id"],
            "identity": task_id,
            "status": "completed",
            "family": "geometry",
            "participant": task["participant"],
            "dataset": task["dataset"],
            "synthetic": bool(task.get("synthetic", False)),
            "software_validation_only": bool(task.get("synthetic", False)),
            "completed_at": utc_now(),
            "result_count": len(summaries),
        },
    )
    progress("completed", result_count=len(summaries))
    return 0
