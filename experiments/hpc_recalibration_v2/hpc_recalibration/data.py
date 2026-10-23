"""Portable preprocessed EEG inputs; no downloader and no paper-specific channel count.

Canonical NPZ keys are x (N,C,T float32), y (N integer), trial_id and run_id
(N unicode). Trial IDs are globally qualified; run IDs must identify the actual
acquisition run within the session. Input order is acquisition order. The Kumar
exporter joins legacy X/y/trial_ids NPZ caches to the existing frozen manifest;
it never reconstructs missing EEG or changes the original whole-run roles.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np


@dataclass(frozen=True)
class Split:
    x: np.ndarray
    y: np.ndarray
    trial_id: np.ndarray
    run_id: np.ndarray

    def prefix(self, budget: int) -> "Split":
        if budget < 0:
            raise ValueError("budget must be nonnegative")
        return Split(self.x[:budget], self.y[:budget], self.trial_id[:budget], self.run_id[:budget])

    def __len__(self) -> int:
        return len(self.y)


def atomic_json(path: str | Path, value: dict | list) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except BaseException:
        # Preserve the temporary bytes on storage failure for diagnosis.
        raise


def atomic_npz(path: str | Path, **arrays: np.ndarray) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    with os.fdopen(fd, "wb") as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_input(data_root: str | Path, name: str | Path) -> Path:
    path = Path(name).expanduser()
    return path.resolve() if path.is_absolute() else (Path(data_root).expanduser() / path).resolve()


def load_split(path: str | Path) -> Split:
    """Load one required shard, checking shape/finite values; never scan other files."""
    with np.load(path, allow_pickle=False) as archive:
        missing = {"x", "y", "trial_id", "run_id"} - set(archive.files)
        if missing:
            raise ValueError(f"{path}: missing NPZ keys {sorted(missing)}")
        split = Split(*(np.array(archive[k], copy=True) for k in ("x", "y", "trial_id", "run_id")))
    if split.x.ndim != 3 or split.x.shape[1] < 2 or split.x.shape[2] < 2:
        raise ValueError(f"{path}: x must be N,C,T with C,T >= 2")
    if split.x.dtype != np.float32 or not np.isfinite(split.x).all():
        raise ValueError(f"{path}: x must be finite float32")
    n = split.x.shape[0]
    if split.y.shape != (n,) or split.y.dtype.kind not in "iu":
        raise ValueError(f"{path}: y must be N integer labels")
    if (split.y < 0).any():
        raise ValueError(f"{path}: labels must be nonnegative")
    for name, value in (("trial_id", split.trial_id), ("run_id", split.run_id)):
        if value.shape != (n,) or value.dtype.kind != "U" or any(not s for s in value.tolist()):
            raise ValueError(f"{path}: {name} must be N nonempty unicode strings")
    if len(set(split.trial_id.tolist())) != n:
        raise ValueError(f"{path}: duplicate trial IDs")
    return split


def save_split(path: str | Path, split: Split) -> None:
    atomic_npz(path, x=split.x, y=split.y, trial_id=split.trial_id, run_id=split.run_id)


def task_inputs(task: dict) -> list[tuple[str, str, str]]:
    """(role, session, path) in chronological declared order."""
    entries = [("source_train", "source", task["source_train"]),
               ("source_validation", "source", task["source_validation"])]
    if task.get("source_query"):
        entries.append(("source_query", "source", task["source_query"]))
    sessions = set()
    for target in task["targets"]:
        session = str(target["session"])
        if session in sessions or session == "source":
            raise ValueError("target session identities must be unique and distinct from source")
        sessions.add(session)
        entries.extend([("support", session, target["support"]), ("query", session, target["query"])])
    return entries


def validate_task_inputs(task: dict, data_root: str | Path, full_sha: bool = True) -> dict:
    """One-time preparation check; callers cache files and use stat-only resume checks.

    This function inspects prepared inputs; it fits no model. The worker loads
    query arrays only after its training stages have finished.
    """
    files, splits, used_trials, used_runs = [], [], set(), {}
    dimensions = None
    source_classes = None
    expected_hashes = task.get("input_sha256")
    if expected_hashes is not None and not isinstance(expected_hashes, dict):
        raise ValueError("input_sha256 must map every task input path to its frozen SHA256")
    for role, session, name in task_inputs(task):
        path = resolve_input(data_root, name)
        split = load_split(path)
        if dimensions is None:
            dimensions = split.x.shape[1:]
            source_classes = set(split.y.tolist())
            if len(source_classes) < 2:
                raise ValueError("source_train must contain at least two classes")
            if source_classes != set(range(len(source_classes))):
                raise ValueError("source labels must be contiguous 0..K-1; map external labels explicitly")
        if split.x.shape[1:] != dimensions:
            raise ValueError(f"{path}: channel/time shape differs within participant")
        if not set(split.y.tolist()) <= source_classes:
            raise ValueError(f"{path}: contains a class absent from source training")
        ids = set(split.trial_id.tolist())
        if ids & used_trials:
            raise ValueError(f"trial leakage/duplicate identity in {role}/{session}")
        used_trials |= ids
        for run in set(split.run_id.tolist()):
            key = (session, run)
            if key in used_runs and used_runs[key] != role:
                raise ValueError(f"whole-run leakage: {key} spans {used_runs[key]} and {role}")
            used_runs[key] = role
        if role in {"source_train", "source_validation", "support"} and not len(split):
            raise ValueError(f"{path}: empty required fitting/validation role")
        stat = path.stat()
        record = {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        if full_sha:
            record["sha256"] = sha256_file(path)
            if expected_hashes is not None:
                expected = expected_hashes.get(name)
                if not isinstance(expected, str) or len(expected) != 64:
                    raise ValueError(f"Missing frozen SHA256 for task input: {name}")
                if record["sha256"] != expected:
                    raise ValueError(f"Frozen input SHA256 mismatch: {name}")
        files.append(record)
        counts = {str(c): int(np.sum(split.y == c)) for c in sorted(source_classes)}
        splits.append({"role": role, "session": session, "trials": len(split), "classes": counts,
                       "runs": sorted(set(split.run_id.tolist()))})
    return {"task_id": task["task_id"], "files": files, "splits": splits,
            "channels": dimensions[0], "samples": dimensions[1],
            "class_count": len(source_classes), "whole_run_disjoint": True,
            "query_used_for_fitting": False}


def export_legacy_cache(manifest_path: str | Path, caches: list[str | Path],
                        output_root: str | Path, *, subjects: list[str] | None = None,
                        seed: int = 42, verify_numeric_hashes: bool = True) -> list[dict]:
    """Explicit offline conversion of existing Kumar arrays, never an automatic download.

    Each cache accepts canonical x/y/trial_id or legacy X/y/trial_ids keys. The
    exact manifest join determines all roles and order. All requested included
    trials must exist in supplied caches before any output is published.
    """
    manifest = json.loads(Path(manifest_path).read_text())
    all_rows = manifest["trials"] if isinstance(manifest, dict) else manifest
    rows = [r for r in all_rows if r.get("included") is True
            and (subjects is None or r["subject"] in subjects)]
    if not rows:
        raise ValueError("No included manifest trials in requested subjects")
    if len({r["trial_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate manifest trial identity")
    wanted = {r["trial_id"]: r for r in rows}
    arrays = {}
    for cache_path in caches:
        with np.load(cache_path, allow_pickle=False) as cache:
            x_key = "x" if "x" in cache.files else "X"
            id_key = "trial_id" if "trial_id" in cache.files else "trial_ids"
            x, y, ids = cache[x_key], cache["y"], cache[id_key]
            if len(x) != len(y) or len(y) != len(ids):
                raise ValueError(f"Cache row lengths disagree: {cache_path}")
            for index, trial_id in enumerate(ids.tolist()):
                if trial_id not in wanted:
                    continue
                if trial_id in arrays:
                    raise ValueError(f"Duplicate cache identity: {trial_id}")
                row = wanted[trial_id]
                expected_label = {"left_hand": 0, "right_hand": 1}[row["label"]]
                epoch = np.asarray(x[index], dtype=np.float32)
                if int(y[index]) != expected_label:
                    raise ValueError(f"Label mismatch: {trial_id}")
                if epoch.ndim != 2 or not np.isfinite(epoch).all():
                    raise ValueError(f"Invalid cached epoch: {trial_id}")
                expected_hash = row.get("processed_window_numeric_sha256")
                if verify_numeric_hashes and expected_hash:
                    observed = hashlib.sha256(epoch.astype("<f4", copy=False).tobytes(order="C")).hexdigest()
                    if observed != expected_hash:
                        raise ValueError(f"Frozen numeric hash mismatch: {trial_id}")
                arrays[trial_id] = (epoch.copy(), expected_label)
    missing = set(wanted) - set(arrays)
    if missing:
        by_role = {}
        for trial_id in missing:
            role = wanted[trial_id]["role"]
            by_role[role] = by_role.get(role, 0) + 1
        raise ValueError(f"Caches lack {len(missing)} included trials by role {by_role}; "
                         "supply the missing prepared arrays; no EEG download or fabrication occurs")
    output_root = Path(output_root)
    tasks = []
    participants = sorted({r["subject"] for r in rows}, key=lambda s: int(s.rsplit("-", 1)[-1]))
    for participant in participants:
        participant_rows = [r for r in rows if r["subject"] == participant]
        groups = {}
        for row in participant_rows:
            groups.setdefault((row["session"], row["role"]), []).append(row)
        paths = {}
        for (session, role), group in groups.items():
            group.sort(key=lambda r: (r.get("acquisition_time_utc", ""),
                                     int(r["run"].rsplit("-", 1)[-1]),
                                     r.get("start_sample", 0), r.get("source_row", 0)))
            relative = Path(participant) / f"{session}_{role}.npz"
            split = Split(np.stack([arrays[r["trial_id"]][0] for r in group]),
                          np.asarray([arrays[r["trial_id"]][1] for r in group], dtype=np.int64),
                          np.asarray([r["trial_id"] for r in group], dtype=str),
                          np.asarray([f"{participant}/{session}/{r['run']}" for r in group], dtype=str))
            destination = output_root / relative
            if destination.exists():
                old = load_split(destination)
                if not all(np.array_equal(a, b) for a, b in zip(
                        (split.x, split.y, split.trial_id, split.run_id),
                        (old.x, old.y, old.trial_id, old.run_id))):
                    raise ValueError(f"Refusing changed prepared data at {destination}; use a new version")
            else:
                save_split(destination, split)
            paths[(session, role)] = str(relative)
        source_sessions = {s for s, role in paths if role == "source_train"}
        if len(source_sessions) != 1:
            raise ValueError("Exactly one source session required")
        source_session = next(iter(source_sessions))
        task = {"task_id": f"kumar-v2-{participant}-seed{seed}", "dataset": "Kumar2024",
                "participant": participant, "seed": seed, "family": "eegnet",
                "source_train": paths[(source_session, "source_train")],
                "source_validation": paths[(source_session, "source_validation")],
                "targets": [], "prior_test_exposure": "all_Kumar_query_results_previously_exposed"}
        if (source_session, "source_query") in paths:
            task["source_query"] = paths[(source_session, "source_query")]
        for session in sorted({s for s, role in paths if role == "target_support"},
                              key=lambda s: int(s.rsplit("-", 1)[-1])):
            task["targets"].append({"session": session, "support": paths[(session, "target_support")],
                                    "query": paths[(session, "target_query")]})
        validate_task_inputs(task, output_root, full_sha=True)
        tasks.append(task)
    atomic_json(output_root / "tasks.json", tasks)
    atomic_json(output_root / "preparation.json", {
        "adapter": "Kumar2024_frozen_trial_join_v2", "split_manifest_sha256": sha256_file(manifest_path),
        "cache_files": [{"name": Path(p).name, "sha256": sha256_file(p)} for p in caches],
        "participants": participants, "trials": len(rows), "task_count": len(tasks),
        "original_roles_and_numeric_arrays_preserved": True,
        "new_window_selection": False, "source_models_imported": False})
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--cache", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--subjects", nargs="+")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    tasks = export_legacy_cache(args.split_manifest, args.cache, args.output_root,
                                subjects=args.subjects, seed=args.seed)
    print(json.dumps({"prepared_tasks": len(tasks), "output_root": args.output_root}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
