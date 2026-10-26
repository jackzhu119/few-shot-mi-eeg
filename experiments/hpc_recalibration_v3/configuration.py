"""One-time staging of existing inputs and a finite, expandable discovery queue."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .runtime import atomic_json

VERSION = "kumar-discovery-v3.0.0"
SEEDS = (20261023, 20261024, 20261025)
PEOPLE = ("sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16")


def generate(base, original_tasks, checkpoints, project, science):
    project = Path(project).resolve()
    classical = {t["participant"]: t for t in original_tasks if t.get("family") == "classical"}
    neural = {
        (t["participant"], t["seed"]): t for t in original_tasks if t.get("family") == "eegnet"
    }
    if set(classical) != set(PEOPLE) or set(neural) != {(p, s) for p in PEOPLE for s in SEEDS}:
        raise ValueError("The existing six-participant V2 input identities differ")
    checkpoint_by_task = {r["task_id"]: r for r in checkpoints}
    source_inputs = [
        {
            "participant": p,
            "source_train": classical[p]["source_train"],
            "source_validation": classical[p]["source_validation"],
        }
        for p in PEOPLE
    ]
    tasks = []
    for seed in SEEDS:
        tasks.append(
            {
                "task_id": f"v3-pooled-source-s{seed}",
                "family": "pooled_pretrain",
                "participant": "pooled-six-source-only",
                "dataset": "Kumar2024",
                "seed": seed,
                "source_inputs": source_inputs,
                "query_used_for_fitting": False,
            }
        )
    for person in PEOPLE:
        t = copy.deepcopy(classical[person])
        t.update(
            task_id=f"v3-geometry-{person}",
            family="geometry",
            legacy_task_id=classical[person]["task_id"],
            variant="core",
        )
        tasks.append(t)
    # Starting at index9 and looping seeds innermost binds each pooled consumer
    # to the slot that already completed its matching source seed.
    for regime in ("reuse_v2", "pooled_source"):
        for person in PEOPLE:
            for seed in SEEDS:
                t = copy.deepcopy(neural[person, seed])
                original_id = t["task_id"]
                t.update(
                    task_id=f"v3-{regime}-{person}-s{seed}",
                    family="neural",
                    source_regime=regime,
                    variant="core",
                    legacy_task_id=original_id,
                )
                if regime == "reuse_v2":
                    expected = checkpoint_by_task[original_id]
                    t.update(
                        source_checkpoint_directory=str(
                            Path(base["output_root"]) / "tasks" / original_id / "source"
                        ),
                        source_checkpoint_identity=expected["identity"],
                        original_checkpoint_sha256=expected["sha256"],
                    )
                else:
                    t["pretrain_task_id"] = f"v3-pooled-source-s{seed}"
                tasks.append(t)
    core_neural = [copy.deepcopy(t) for t in tasks if t["family"] == "neural"]
    for delta in science["trust_dose_levels"]:
        dose = str(delta).replace(".", "p")
        for core in core_neural:
            t = copy.deepcopy(core)
            t["source_query_reference_task"] = core["task_id"]
            t.pop("source_query", None)  # Same teacher query is not measured anew for each dose.
            t.update(
                task_id=core["task_id"] + "-kl" + dose,
                variant="kl" + dose,
                science_overrides={"neural_methods": ["trust_fixed"], "trust_kl_budget": delta},
            )
            tasks.append(t)
    # Nine simulation blocks keep source/consumer slot indexing independent.
    simulation = science["simulation"]
    scenario_count = (
        len(simulation["p"])
        * len(simulation["target_perclass"])
        * len(simulation["shift"])
        * len(simulation["anisotropy"])
        * len(simulation.get("source_perclass_levels", [simulation["source_perclass"]]))
        * len(simulation.get("serial_correlations", [0.0]))
    )
    for block in range(9):
        tasks.append(
            {
                "task_id": f"v3-mechanism-block-{block}",
                "family": "simulation",
                "dataset": "synthetic_gaussian_features",
                "participant": "mechanism-only",
                "seed": 20261026,
                "scenario_indices": list(range(block, scenario_count, 9)),
                "synthetic": True,
                "software_validation_only": True,
            }
        )
    if len(tasks) != 126 or len({t["task_id"] for t in tasks}) != len(tasks):
        raise AssertionError("Unexpected discovery task matrix")
    config = {
        "experiment_id": "paper2-kumar-discovery-v3-20261026",
        "scientific_version": VERSION,
        "project_dir": str(project),
        "output_root": str(project / "outputs/kumar-discovery-v3"),
        "data_root": base["data_root"],
        "v2_project_dir": base["project_dir"],
        "v2_output_root": base["output_root"],
        "tasks_file": str(project / "configs/tasks.json"),
        "python": base.get(
            "python", "/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python"
        ),
        "device": "cuda:0",
        "science": copy.deepcopy(science),
        "slurm": {
            "account": "zhuziyuan",
            "user": "zhuziyuan",
            "partition": "hpc_gpu1",
            "gres": "gpu:NVIDIAA100-SXM4-80GB:1",
            "cpus_per_task": 16,
            "mem": "64G",
            "worker_jobs": 3,
            "time_limit": "5-03:00:00",
            "exclude": "gpu3",
        },
        "runtime": {
            "torch_threads": 4,
            "blas_threads": 1,
            "heartbeat_seconds": 30,
            "checkpoint_seconds": 120,
        },
        "git_sync": {
            "enabled": True,
            "repository": "jackzhu119/few-shot-mi-eeg",
            "branch": "research/paper2-hpc-v2-20261023",
            "status_prefix": "training_status/paper2-discovery-v3",
            "token_file": str(Path.home() / ".config/paper2-hpc/github-token"),
            "interval_seconds": 180,
        },
    }
    return config, tasks


def load_config(path):
    path = Path(path).expanduser().resolve()
    value = json.loads(path.read_text())
    value["_config_path"] = str(path)
    for key, item in value.get("runtime", {}).items():
        value.setdefault(key, item)
    return value


def _stamp(path):
    stat = path.stat()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prepare_inputs(config, tasks):
    """Reuse V2's verified file stats; hash only previously unverified/changed files.

    No EEG tensor, label or validation loss is loaded on login1. A touched but
    byte-identical input simply refreshes this cache rather than invalidating a fit.
    """
    expected = {}
    for task in tasks:
        for name, sha in task.get("input_sha256", {}).items():
            path = str((Path(config["data_root"]) / name).resolve())
            if path in expected and expected[path] != sha:
                raise ValueError("Conflicting input identity in the declared tasks")
            expected[path] = sha
        if task.get("source_checkpoint_directory") and task.get("original_checkpoint_sha256"):
            expected[
                str((Path(task["source_checkpoint_directory"]) / "checkpoint.pt").resolve())
            ] = task["original_checkpoint_sha256"]
    path = Path(config["output_root"]) / ".runtime/input_files.json"
    cache = json.loads(path.read_text()).get("files", {}) if path.is_file() else {}
    inherited = Path(config["v2_output_root"]) / ".runtime/prepared.json"
    if inherited.is_file():
        old = json.loads(inherited.read_text())
        stats = {
            r["path"]: {"bytes": r["bytes"], "mtime_ns": r["mtime_ns"]}
            for r in old.get("file_stats", [])
        }
        for task in old.get("input_validation", []):
            for row in task.get("result", {}).get("files", []):
                if row.get("sha256") and row["path"] in stats:
                    cache.setdefault(
                        row["path"], {"stat": stats[row["path"]], "sha256": row["sha256"]}
                    )
    hashes = reused = 0
    for filename, sha in sorted(expected.items()):
        source = Path(filename)
        current = _stamp(source)
        previous = cache.get(filename, {})
        if previous.get("stat") == current and previous.get("sha256") == sha:
            reused += 1
            continue
        observed = _sha(source)
        if observed != sha:
            raise ValueError("Actual frozen input bytes changed: " + filename)
        cache[filename] = {"stat": current, "sha256": observed}
        hashes += 1
    result = {
        "files": {k: cache[k] for k in sorted(expected)},
        "verified_files": len(expected),
        "reused_stat_records": reused,
        "new_full_hash_reads": hashes,
        "checks": "frozen bytes identity only; no repeated full venv, pilot or decoder fit",
    }
    atomic_json(path, result)
    return {k: v for k, v in result.items() if k != "files"}
