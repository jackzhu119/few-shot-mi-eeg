#!/usr/bin/env python3
"""One deterministic bounded CPU sensitivity; existing scientific outputs untouched."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import mne  # noqa: E402
import numpy as np  # noqa: E402
from learning_preserving_bci.alignment_mechanism import (  # noqa: E402
    METHODS, fit_mechanism, numeric_digest, score,
)

FROZEN_PLAN_COMMIT = "13dd764"
PLAN = ROOT / "docs/paper2_alignment_integrated_20261104/analysis_plan.yaml"
KUMAR_CONFIG = ROOT / "configs/kumar_cross_session_20261012.json"
KUMAR_SPLIT = ROOT / "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json"
RAW = ROOT / "data/public_eeg/kumar2024/nm000177/v1.0.5"
BNCI = Path("/workspace/private_external_validation/bnci001-v1-20261027/prepared")
INPUT = ROOT / "research_logs/paper2_structure_revision_20261029/component_replay/input"
DEVELOPMENT = {"sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16"}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def model_write(path, arrays):
    temp = path.with_name(path.name + ".tmp")
    with temp.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    return sha(path)


def _ids_hash(ids):
    return hashlib.sha256(json.dumps(list(ids), separators=(",", ":")).encode()).hexdigest()


def context_record(dataset, subject, session, method, source_ids, support_ids, query_ids):
    for name, ids in [("source", source_ids), ("support", support_ids), ("query", query_ids)]:
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate " + name + " trial identity")
    if set(source_ids) & set(support_ids) or set(source_ids + support_ids) & set(query_ids):
        raise ValueError("Source/support/query trial leakage")
    return {"dataset": dataset, "subject": subject, "session": session, "method": method,
            "n_source": len(source_ids), "n_support": len(support_ids), "n_query": len(query_ids),
            "source_ids": source_ids, "support_ids": support_ids, "query_ids": query_ids,
            "source_ids_sha256": _ids_hash(source_ids), "support_ids_sha256": _ids_hash(support_ids),
            "query_ids_sha256": _ids_hash(query_ids), "synthetic": False,
            "query_fitting_or_selection": False}


def historical_kumar():
    with gzip.open(INPUT / "budget/query_predictions.csv.gz", "rt") as stream:
        rows = list(csv.DictReader(stream))
    result = {}
    for r in rows:
        if r["budget"] != "full" or r["method"] not in {"refit_csp_lda", "ea_csp_lda"}:
            continue
        key = (r["subject"], r["session"], r["method"])
        target = result.setdefault(key, {})
        if r["trial_id"] in target:
            raise ValueError("Repeated historical prediction identity")
        target[r["trial_id"]] = (int(r["label"]), int(r["prediction"]))
    return result


def check_query_identity(query_ids, y, saved):
    if set(query_ids) != set(saved) or any(int(label) != saved[tid][0] for tid, label in zip(query_ids, y)):
        raise ValueError("Historical/new query identity or label mismatch")


class Run:
    def __init__(self, output, private, maximum_seconds, resume=False):
        self.output, self.private = Path(output), Path(private)
        self.started = time.monotonic()
        self.maximum_seconds = maximum_seconds
        if self.output.exists() and not resume:
            raise FileExistsError("Output exists; inspect it and use --resume only for unattempted cells")
        self.output.mkdir(parents=True, exist_ok=True)
        self.private.mkdir(parents=True, exist_ok=True)
        (self.output / "cells").mkdir(exist_ok=True)
        (self.output / "claims").mkdir(exist_ok=True)
        (self.output / "inputs").mkdir(exist_ok=True)
        self.fits = 0
        self.phase_fits = 0
        self.progress()

    def progress(self, extra=None):
        rows = [json.loads(p.read_text()) for p in sorted((self.output / "cells").glob("*.json"))]
        event = {"utc": now(), "pid": os.getpid(), "stage": "running", "completed_cells": len(rows),
                 "successful_cells": sum(x["status"] == "complete" for x in rows),
                 "this_process_fit_attempts": self.fits, "this_process_phase_fit_attempts": self.phase_fits,
                 "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        event.update(extra or {})
        atomic(self.output / "progress.json", event)
        print(json.dumps(event), flush=True)

    def input_receipt(self, name, value):
        path = self.output / "inputs" / (name + ".json")
        if path.exists():
            prior = json.loads(path.read_text())
            # Unrelated text commits do not invalidate byte-identical scientific inputs.
            def compare(row):
                return {k: v for k, v in row.items() if k != "head_at_execution"}
            if compare(prior) != compare(value):
                raise ValueError("Input receipt changed on resume: " + name)
        else:
            atomic(path, value)

    def cell(self, key, context, fit, query_x, query_y, *, historical=None, phase=False):
        completed = self.output / "cells" / (key + ".json")
        claim = self.output / "claims" / (key + ".json")
        if historical is not None:
            check_query_identity(context["query_ids"], query_y, historical)
        if completed.exists():
            value = json.loads(completed.read_text())
            if value["context"] != context:
                raise ValueError("Completed cell identity differs")
            if value["status"] == "complete" and sha(self.private / value["private_model_file"]) != value["private_model_sha256"]:
                raise ValueError("Completed private model bytes changed")
            return value
        if claim.exists():
            raise RuntimeError("Unresolved prior attempt; no automatic retry: " + key)
        if time.monotonic() - self.started > self.maximum_seconds:
            raise TimeoutError("Fixed bounded CPU execution time reached")
        with claim.open("x") as stream:
            json.dump({"key": key, "utc": now(), "pid": os.getpid(), "context": context}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        self.fits += 1
        self.phase_fits += int(phase)
        if self.fits > 576 or self.phase_fits > 180:
            raise RuntimeError("Frozen fit-count bound exceeded")
        began = now()
        try:
            model = fit()
        except np.linalg.LinAlgError as exc:
            # This is the only anticipated estimator-scientific exception class.
            value = {"context": context, "status": "failed_expected_estimator", "exception": repr(exc),
                     "started_utc": began, "completed_utc": now()}
            atomic(completed, value)
            self.progress({"last_cell": key, "last_status": value["status"]})
            return value
        state_before = model.state_arrays()
        digest = numeric_digest(state_before)
        predicted = np.asarray(model.predict(query_x), dtype=np.int64)
        probability = np.asarray(model.predict_probability(query_x), dtype=np.float64)
        if numeric_digest(model.state_arrays()) != digest:
            raise ValueError("Prediction changed fitted model state")
        path = self.private / (key + ".npz")
        model_hash = model_write(path, state_before)
        value = {"context": context, "status": "complete", "started_utc": began, "completed_utc": now(),
                 "metadata": model.metadata, "model_numeric_sha256": digest,
                 "private_model_file": path.name, "private_model_sha256": model_hash,
                 "prediction_state_unchanged": True, "label": np.asarray(query_y).tolist(),
                 "prediction": predicted.tolist(), "p_right": probability.tolist(),
                 "metrics": score(query_y, predicted, probability)}
        if historical is not None:
            old = np.asarray([historical[tid][1] for tid in context["query_ids"]])
            value["historical_reference_metrics"] = score(query_y, old)
            value["prediction_disagreements_with_historical"] = int(np.sum(old != predicted))
        atomic(completed, value)
        self.progress({"last_cell": key, "last_status": "complete"})
        return value


class PhaseDecoder:
    """Historical 22-channel/re-embedded EA, used only for the phase extension."""
    def __init__(self, source_x, source_y, support_x, support_y, budget_module):
        from learning_preserving_bci.decoders.csp_lda import make_csp_lda
        self.source_ref = budget_module.ea_reference(source_x)
        self.target_ref = budget_module.ea_reference(support_x)
        self.budget = budget_module
        self.model = make_csp_lda(n_components=4)
        self.model.fit(np.concatenate([budget_module.ea_transform(source_x, self.source_ref),
                                       budget_module.ea_transform(support_x, self.target_ref)]),
                       np.concatenate([source_y, support_y]))
        self.metadata = {"scope": "new_EA_extension_of_original_phase_protocol", "effective_coordinates":
                         "H21 whitening reembedded22; original CSP rankNone/LW and LDAauto",
                         "query_used_for_fitting": False, "probability_classes": [0, 1],
                         "source_condition": self.source_ref["condition_number"],
                         "support_condition": self.target_ref["condition_number"]}

    def predict(self, query):
        return self.model.predict(self.budget.ea_transform(query, self.target_ref))

    def predict_probability(self, query):
        return self.model.predict_proba(self.budget.ea_transform(query, self.target_ref))[:, 1]

    def state_arrays(self):
        output = {"source_reference": self.source_ref["reference"], "target_reference": self.target_ref["reference"],
                  "source_inverse": self.source_ref["inverse_sqrt"], "target_inverse": self.target_ref["inverse_sqrt"]}
        for name, estimator in self.model.named_steps.items():
            for key, value in vars(estimator).items():
                if key.endswith("_") and isinstance(value, np.ndarray):
                    output[name + key] = value
        return output


def run_phase(run, subject, loaded, split, mapping, phase_module, budget_module, saved):
    trials = [row for row in split["trials"] if row["subject"] == subject]
    selected, coverage = phase_module.select_common_trials(trials, [row for row in mapping if row["subject"] == subject])
    selected = [row for row in selected if row["role"] in {"source_train", "target_support", "target_query"}]
    source = [row for row in selected if row["role"] == "source_train"]
    if len(source) != 40:
        raise ValueError("Original phase source TRAIN must remain40")
    cue = {r["trial_id"]: loaded.X[i] for i, r in enumerate(loaded.metadata)}
    readers = {}
    def read(row, start, stop):
        relative = row["source_file"]
        if relative not in readers:
            readers[relative] = mne.io.read_raw_edf(RAW / relative, preload=False, verbose="ERROR")
        return readers[relative].get_data(start=start, stop=stop)
    try:
        arrays = phase_module.materialize_window_arrays(selected, read, saved_cue_epochs=cue)
    finally:
        for reader in readers.values():
            reader.close()
    run.input_receipt(subject + "__phase", {"mapping_sha256": sha(ROOT / "research_logs/kumar_component_followup_20261016/event_mapping/timing_partial_run05/all_7200_trial_mapping_including_missing.csv"),
                      "selected_trial_ids": [r["trial_id"] for r in selected],
                      "coverage_counts": {"eligible": sum(r["eligible_common"] for r in coverage), "all": len(coverage)},
                      "window_array_numeric_sha256": {w: numeric_digest(a) for w, a in arrays.items()}})
    for session in [f"ses-{i}" for i in range(1, 6)]:
        support = [r for r in selected if r["session"] == session and r["role"] == "target_support"]
        query = [r for r in selected if r["session"] == session and r["role"] == "target_query"]
        source_ids, support_ids, query_ids = [[r["trial_id"] for r in group] for group in [source, support, query]]
        for window in ["cue5s", "task2s"]:
            key = subject + "__" + session + "__phase_" + window + "__ea"
            context = context_record("kumar_phase", subject, session, "ea", source_ids, support_ids, query_ids)
            context["window"] = window
            if not support or not query:
                path = run.output / "cells" / (key + ".json")
                if not path.exists():
                    atomic(path, {"context": context, "status": "undefined_empty_support_or_query", "completed_utc": now()})
                continue
            xsource, xsupport, xquery = [np.stack([arrays[window][tid] for tid in ids]) for ids in [source_ids, support_ids, query_ids]]
            ysource, ysupport, yquery = [np.asarray([r["label"] for r in group]) for group in [source, support, query]]
            historical = saved.get((subject, session, window), {})
            check_query_identity(query_ids, yquery, historical)
            run.cell(key, context,
                     lambda: PhaseDecoder(xsource, ysource, xsupport, ysupport, budget_module),
                     xquery, yquery, historical=historical, phase=True)


def run_kumar(run, phase=False):
    from learning_preserving_bci.datasets.kumar import load_subject
    config = json.loads(KUMAR_CONFIG.read_text())
    split = json.loads(KUMAR_SPLIT.read_text())
    historical = historical_kumar()
    mapping, phase_module, budget_module, phase_saved = None, None, None, {}
    if phase:
        phase_module = load_module("integrated_phase_helpers", "scripts/run_kumar_phase_window_cpu_20261016.py")
        budget_module = load_module("integrated_budget_helpers", "scripts/run_kumar_component_budget_cpu_20261016.py")
        with (ROOT / "research_logs/kumar_component_followup_20261016/event_mapping/timing_partial_run05/all_7200_trial_mapping_including_missing.csv").open() as stream:
            mapping = list(csv.DictReader(stream))
        with gzip.open(INPUT / "phase/query_predictions.csv.gz", "rt") as stream:
            for row in csv.DictReader(stream):
                if row["method"] != "refit_csp_lda":
                    continue
                phase_saved.setdefault((row["subject"], row["session"], row["window"]), {})[row["trial_id"]] = (int(row["label"]), int(row["prediction"]))
    for subject in sorted(config["subjects"], key=lambda s: int(s.split("-")[-1])):
        run.progress({"stage": "load_kumar", "subject": subject})
        loaded = load_subject(RAW, subject, config, split, allowed_roles={"source_train", "target_support", "target_query"})
        run.input_receipt(subject, {"provenance": loaded.provenance, "config_sha256": sha(KUMAR_CONFIG),
                                   "split_sha256": sha(KUMAR_SPLIT), "processed_array_sha256": numeric_digest({"X": loaded.X, "y": loaded.y}),
                                   "ordered_trial_ids": [r["trial_id"] for r in loaded.metadata]})
        source = [i for i, row in enumerate(loaded.metadata) if row["role"] == "source_train"]
        for session in [f"ses-{i}" for i in range(1, 6)]:
            support = [i for i, r in enumerate(loaded.metadata) if r["role"] == "target_support" and r["session"] == session]
            query = [i for i, r in enumerate(loaded.metadata) if r["role"] == "target_query" and r["session"] == session]
            source_ids, support_ids, query_ids = [[loaded.metadata[i]["trial_id"] for i in group] for group in [source, support, query]]
            for method in METHODS:
                context = context_record("kumar", subject, session, method, source_ids, support_ids, query_ids)
                context["cohort"] = "development6" if subject in DEVELOPMENT else "primary12"
                context["n_support_flagged_250uv"] = sum(bool(loaded.metadata[i]["qc_peak_to_peak_over_250uv"]) for i in support)
                context["support_class_counts"] = [int(np.sum(loaded.y[support] == c)) for c in [0, 1]]
                old_method = "ea_csp_lda" if method == "ea" else "refit_csp_lda"
                saved = historical[(subject, session, old_method)]
                run.cell(subject + "__" + session + "__" + method, context,
                         lambda method=method: fit_mechanism(loaded.X[source], loaded.y[source], loaded.X[support], loaded.y[support], method, "kumar"),
                         loaded.X[query], loaded.y[query], historical=saved)
        if phase:
            run_phase(run, subject, loaded, split, mapping, phase_module, budget_module, phase_saved)


def run_bnci(run):
    from experiments.hpc_recalibration_v2.hpc_recalibration.data import load_split
    for n in range(1, 10):
        subject = f"bnci001-sub-{n:02d}"
        task = json.loads((BNCI / subject / "task.json").read_text())
        verified = []
        for role in ["source_train", "support", "query"]:
            relative = subject + "/" + role + ".npz"
            actual = sha(BNCI / relative)
            if actual != task["input_sha256"][relative]:
                raise ValueError("Original prepared BNCI SHA256 mismatch: " + relative)
            verified.append({"path": str(BNCI / relative), "sha256": actual, "original_sha_verified": True})
        splits = {role: load_split(BNCI / subject / (role + ".npz")) for role in ["source_train", "support", "query"]}
        run.input_receipt(subject, {"files": verified, "task_manifest_sha256": sha(BNCI / subject / "task.json")})
        source, support, query = [splits[role] for role in ["source_train", "support", "query"]]
        if (len(source), len(support), len(query)) != (96, 20, 120):
            raise ValueError("Frozen BNCI96/20/120 counts changed")
        for method in METHODS:
            context = context_record("bnci", subject, "E", method, source.trial_id.tolist(), support.trial_id.tolist(), query.trial_id.tolist())
            context["support_class_counts"] = [int(np.sum(support.y == c)) for c in [0, 1]]
            old = "ea_csp" if method == "ea" else "full_csp"
            record = json.loads((ROOT / "research_logs/paper2_external_validation_20261027/saved_predictions" / subject / ("E__n20__" + old + ".json")).read_text())
            saved = {tid: (int(y), int(p)) for tid, y, p in zip(record["trial_ids"], record["y"], record["prediction"])}
            run.cell(subject + "__E__" + method, context,
                     lambda method=method: fit_mechanism(source.x, source.y, support.x, support.y, method, "bnci"),
                     query.x, query.y, historical=saved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-models", type=Path, default=Path("/workspace/private_alignment_mechanisms_20261104/models"))
    parser.add_argument("--phase", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=7200)
    args = parser.parse_args()
    if args.max_seconds <= 0:
        raise ValueError("Positive bounded runtime required")
    plan = json.loads(PLAN.read_text())
    if plan["P2"]["maximum_target_fit_count_main"] != 396:
        raise ValueError("Frozen plan fit bound changed")
    mne.set_log_level("ERROR")
    lockpath = Path("/workspace/.locks/few-shot-mi-eeg-cpu.lock")
    lockpath.parent.mkdir(exist_ok=True)
    cpu_lock = lockpath.open("a")
    fcntl.flock(cpu_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    run = Run(args.output, args.private_models, args.max_seconds, args.resume)
    sources = [Path(__file__), ROOT / "src/learning_preserving_bci/alignment_mechanism.py", PLAN,
               KUMAR_CONFIG, KUMAR_SPLIT, ROOT / "scripts/run_kumar_component_budget_cpu_20261016.py",
               ROOT / "scripts/run_kumar_phase_window_cpu_20261016.py",
               ROOT / "experiments/hpc_recalibration_v2/hpc_recalibration/classical.py"]
    run.input_receipt("execution", {"frozen_plan_commit": FROZEN_PLAN_COMMIT,
        "head_at_execution": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in sources],
        "python": sys.version, "numpy": np.__version__, "mne": mne.__version__,
        "thread_settings": {k: os.environ[k] for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]},
        "new_fits": True, "neural_refits": False, "automatic_retry": False})
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(143))
    try:
        run_bnci(run)
        run_kumar(run, args.phase)
        run.progress({"stage": "complete"})
        atomic(run.output / "execution_receipt.json", {"status": "completed", "exit_code": 0,
               "completed_utc": now(), "new_fit_attempts": run.fits, "new_phase_fit_attempts": run.phase_fits,
               "maximum_target_fits_this_entry": 576, "preserves_historical_outputs": True})
    except BaseException as exc:
        # Outer exit evidence never reclassifies a storage/program error as a science failure.
        error = {"status": "failed", "completed_utc": now(), "exception_type": type(exc).__name__,
                 "exception": str(exc), "traceback": traceback.format_exc(), "fit_attempts": run.fits,
                 "phase_fit_attempts": run.phase_fits, "automatic_retry": False,
                 "exit_code": exc.code if isinstance(exc, SystemExit) and isinstance(exc.code, int) else 1}
        try:
            atomic(run.output / "exception_receipt.json", error)
        except OSError:
            print(json.dumps(error), file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
