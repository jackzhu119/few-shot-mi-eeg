"""Record reproducibility context without collecting credentials."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import tempfile
from typing import Any

import numpy as np


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


def collect_provenance(seed: int, repository: str | Path | None = None) -> dict:
    """Record current source/config hashes as well as Git and environment identity.

    Pass the repository root. Recursive Python files under ``src`` and JSON
    files under ``configs`` are hashed as currently present, including local
    edits and untracked files. A commit alone does not identify a dirty run.
    Credentials, process environment values and dataset contents are excluded.
    """
    root = Path(repository) if repository is not None else Path.cwd()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    try:
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        dirty = None
    hashes = {}
    source_files = list((root / "src").rglob("*.py"))
    configuration_files = list((root / "configs").rglob("*.json"))
    for path in sorted(source_files + configuration_files):
        if path.is_file():
            with path.open("rb") as source:
                hashes[path.relative_to(root).as_posix()] = hashlib.file_digest(
                    source, "sha256"
                ).hexdigest()
    versions = {}
    for name in (
        "numpy",
        "scipy",
        "scikit-learn",
        "mne",
        "torch",
        "torchaudio",
        "braindecode",
        "moabb",
    ):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "seed": int(seed),
        "git_commit": commit,
        "git_dirty": dirty,
        "source_config_sha256": hashes,
        "source_config_hash_scope": ["src/**/*.py", "configs/**/*.json"],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": versions,
    }


def _json_default(value: Any):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def write_result_json(path: str | Path, result: dict, *, overwrite: bool = False) -> None:
    """Atomically write strict JSON and preserve existing evidence by default.

    Serialization completes before any filesystem changes, so unsupported or
    nonfinite values cannot leave a partial result. The default publication
    uses an exclusive hard link, which also protects against concurrent writers.
    An explicit ``overwrite=True`` allows an intentional atomic replacement.
    """
    if not isinstance(result.get("synthetic"), bool):
        raise ValueError("Result must include an explicit boolean synthetic flag")
    payload = json.dumps(result, indent=2, allow_nan=False, default=_json_default) + "\n"
    path = Path(path)
    if not overwrite and path.exists():
        raise FileExistsError(f"Result already exists; choose a new output path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        if overwrite:
            temporary.replace(path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
