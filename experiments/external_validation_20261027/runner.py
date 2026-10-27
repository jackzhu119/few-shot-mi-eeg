"""One fixed external-data replication, reusing the completed V2 four-arm code.

No neural training, model search, or Kumar query is performed here. Download
and prepare run before fitting; every completed model/evaluation shard resumes.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import sys
import time
import traceback
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
sys.path.insert(0, str(REPOSITORY / "experiments/hpc_recalibration_v2"))

from hpc_recalibration import classical  # noqa: E402
from hpc_recalibration.data import atomic_json, sha256_file  # noqa: E402
from experiments.external_validation_20261027.statistics import summarize  # noqa: E402

PARTICIPANTS = tuple(str(i) for i in range(1, 10))
METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
EXPERIMENT = "paper2-bnci001-component-replication-v1-20261027"


def raw_download(row, manifest, destination):
    """Verified upstream bytes; reuse verified files, resume transport only."""
    path = Path(destination) / row["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.stat().st_size == row["bytes"] and sha256_file(path) == row["sha256"]:
            return path
        raise ValueError(f"Existing raw input differs: {path}; retain it for inspection")
    partial = path.with_suffix(path.suffix + ".part")
    url = manifest["official_base_url"] + row["file"]
    if shutil.disk_usage(path.parent).free < row["bytes"] + 100 * 1024 ** 2:
        raise OSError("Insufficient disk for this download plus 100 MiB reserve")
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset == row["bytes"]:
            break
        if offset > row["bytes"]:
            raise ValueError("Partial download exceeds frozen byte length")
        print(json.dumps({"phase": "download", "file": row["file"],
                          "offset": offset, "attempt": attempt + 1}), flush=True)
        request = urllib.request.Request(url, headers={"User-Agent": EXPERIMENT})
        if offset:
            request.add_header("Range", f"bytes={offset}-")
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                resumed = offset and response.status == 206
                if resumed and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise ValueError("Invalid HTTP resume offset")
                with partial.open("ab" if resumed else "wb") as stream:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        stream.write(block)
                    stream.flush()
                    os.fsync(stream.fileno())
            break
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    if partial.stat().st_size != row["bytes"] or sha256_file(partial) != row["sha256"]:
        raise ValueError("Raw download failed frozen length/SHA256 check")
    os.replace(partial, path)
    return path


def make_config(root):
    return {"experiment_id": EXPERIMENT, "output_root": str(root / "results"),
            "data_root": str(root / "prepared"), "budgets": [20],
            "classical_methods": list(METHODS), "heartbeat_seconds": 30,
            "classical": {"n_components": 4, "covariance_shrinkage": 0.1,
                          "lda_shrinkage": 0.1, "anchor_tau": 20.0},
            "git_sync": {"enabled": True, "repository": "jackzhu119/few-shot-mi-eeg",
                         "branch": "research/paper2-hpc-v2-20261023",
                         "status_prefix": "training_status/paper2-external-bnci001",
                         "interval_seconds": 180}}


def check_inputs(task, config, cache_path):
    """Rehash only changed local files; input SHA is also in the fit identity."""
    cache = json.loads(cache_path.read_text()) if cache_path.is_file() else {}
    current = {}
    for name, expected in task["input_sha256"].items():
        path = Path(config["data_root"]) / name
        stat = path.stat()
        observed = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                    "sha256": expected}
        if cache.get(name) != observed and sha256_file(path) != expected:
            raise ValueError(f"Prepared input changed: {name}")
        current[name] = observed
    atomic_json(cache_path, current)


def analyze(root):
    """Recompute all metrics from saved labels/predictions, without forwarding."""
    import numpy as np

    records, audits, run_records, synthetic_flags = [], [], [], []
    for participant in PARTICIPANTS:
        directory = root / "results/tasks" / f"bnci001-sub-{int(participant):02d}"
        if not (directory / "complete.json").is_file():
            continue
        matched_ids, matched_y, matched_fit_ids = None, None, None
        for method in METHODS:
            path = directory / "evaluation" / f"E__n20__{method}.json"
            row = json.loads(path.read_text())
            synthetic_flags.append(bool(row.get("synthetic", False)))
            ids = row["trial_ids"]
            if len(ids) != len(set(ids)) or (matched_ids is not None and ids != matched_ids):
                raise ValueError("Four methods do not share unique ordered query trial IDs")
            matched_ids = ids
            if matched_y is not None and row["y"] != matched_y:
                raise ValueError("Four methods do not share identically ordered query labels")
            matched_y = row["y"]
            metrics = classical.score_predictions(np.array(row["y"]),
                                                    np.array(row["prediction"]), np.array([0, 1]))
            if metrics != row["metrics"] or row["query_used_for_fitting"]:
                raise ValueError("Saved prediction metrics/leakage mismatch")
            model = classical.Decoder.load(directory / "models" / f"E__n20__{method}.npz")
            if set(ids) & set(model.metadata["fit_trial_ids"]):
                raise ValueError("Query IDs occur in fitted model")
            if row["n_support_actual"] != (0 if method == "frozen" else 20):
                raise ValueError("Wrong target-label budget")
            if method != "frozen":
                fit_ids = model.metadata["fit_trial_ids"]
                if matched_fit_ids is not None and fit_ids != matched_fit_ids:
                    raise ValueError("Updating arms do not share identical fitted trial IDs")
                matched_fit_ids = fit_ids
            run_ids = [trial.rsplit("/trial-", 1)[0] for trial in ids]
            for run_id in dict.fromkeys(run_ids):
                mask = np.array([value == run_id for value in run_ids])
                run_metrics = classical.score_predictions(np.array(row["y"])[mask],
                                np.array(row["prediction"])[mask], np.array([0, 1]))
                run_records.append({"participant": participant, "session": "E", "method": method,
                                    "run_id": run_id, **run_metrics})
            records.append({"participant": participant, "session": "E", "method": method,
                            **metrics})
            audits.append({"participant": participant, "method": method,
                           "prediction_sha256": sha256_file(path), "n_query": len(ids),
                           "metrics_recomputed_exactly": True,
                           "query_used_for_fitting": False})
        frozen = classical.Decoder.load(directory / "models/E__n20__frozen.npz")
        lda = classical.Decoder.load(directory / "models/E__n20__lda_only.npz")
        full = classical.Decoder.load(directory / "models/E__n20__full_csp.npz")
        if not np.array_equal(frozen.filters, lda.filters):
            raise ValueError("Classifier-only arm changed spatial filters")
        if lda.metadata["fit_trial_ids"] != full.metadata["fit_trial_ids"]:
            raise ValueError("Classifier-only/full arms use different fit trial IDs")
    result = summarize(records)
    result.update({"experiment_id": EXPERIMENT, "dataset": "BNCI2014-001",
                   "synthetic": any(synthetic_flags),
                   "software_validation_only": any(synthetic_flags),
                   "implementation": classical.IMPLEMENTATION,
                   "prior_dataset_use_in_paper1": True,
                   "historical_Kumar_MNE_numerical_reproduction": False})
    atomic_json(root / "results/aggregate.json", result)
    atomic_json(root / "results/prediction_audit.json", {"objects": audits,
                "verified_evaluations": len(audits), "failed_checks": 0})
    atomic_json(root / "results/run_metrics.json", run_records)
    return result


def execute(root, prepare_only=False):
    from experiments.external_validation_20261027.data import prepare_subject, save_prepared
    import numpy as np
    import scipy

    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "operation.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = json.loads((HERE / "raw_manifest.json").read_text())
        config = make_config(root)
        atomic_json(root / "config.json", config)
        code = [HERE / "runner.py", HERE / "data.py", HERE / "statistics.py",
                HERE / "raw_manifest.json", REPOSITORY / "docs/paper2_external_validation_protocol_20261027.md",
                REPOSITORY / "experiments/hpc_recalibration_v2/hpc_recalibration/classical.py",
                REPOSITORY / "experiments/hpc_recalibration_v2/hpc_recalibration/data.py"]
        identity = {str(p.relative_to(REPOSITORY)): sha256_file(p) for p in code}
        pin = root / "science_identity.json"
        if pin.is_file() and json.loads(pin.read_text()) != identity:
            raise ValueError("Scientific code/protocol changed; use a new versioned output root")
        if not pin.is_file():
            atomic_json(pin, identity)
        atomic_json(root / f"invocation_{time.time_ns()}.json",
                    {"pid": os.getpid(), "host": socket.gethostname(), "utc": classical.utcnow(),
                     "python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
                     "platform": platform.platform(), "prepare_only": prepare_only,
                     "allocation": "existing_CPU_no_new_paid_resource"})
        for participant in PARTICIPANTS:
            task_id = f"bnci001-sub-{int(participant):02d}"
            task_path = root / "prepared" / task_id / "task.json"
            if not task_path.is_file():
                paths = {}
                for session in ("T", "E"):
                    row = next(r for r in manifest["files"]
                               if r["file"] == f"A{int(participant):02d}{session}.mat")
                    paths[session] = raw_download(row, manifest, root / "raw")
                print(json.dumps({"phase": "prepare", "participant": participant}), flush=True)
                prepared = prepare_subject(paths["T"], paths["E"], participant)
                saved = save_prepared(prepared, root / "prepared" / task_id)
                names = saved["files"]
                task = {"task_id": task_id, "dataset": "BNCI2014-001",
                        "participant": participant, "family": "classical", "seed": 20261027,
                        "source_train": task_id + "/" + names["source_train"],
                        "targets": [{"session": "E", "support": task_id + "/" + names["support"],
                                     "query": task_id + "/" + names["query"]}],
                        "input_sha256": {task_id + "/" + name: sha
                                         for name, sha in saved["input_sha256"].items()}}
                atomic_json(task_path, task)
            task = json.loads(task_path.read_text())
            check_inputs(task, config, task_path.with_name("input_check_cache.json"))
            if prepare_only:
                continue
            print(json.dumps({"phase": "participant_start", "participant": participant,
                              "utc": classical.utcnow()}), flush=True)
            code = classical.run_task(task, config)
            if code:
                return code
            analyze(root)
        if not prepare_only:
            result = analyze(root)
            print(json.dumps({"phase": "complete", "participants": len(result["complete_participants"]),
                              "utc": classical.utcnow()}), flush=True)
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    try:
        if args.analyze_only:
            analyze(root)
            return 0
        return execute(root, args.prepare_only)
    except BaseException:
        root.mkdir(parents=True, exist_ok=True)
        atomic_json(root / f"exception_{time.time_ns()}.json",
                    {"utc": classical.utcnow(), "pid": os.getpid(), "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
