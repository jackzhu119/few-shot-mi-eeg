"""Two-generation checkpoints using portable same-directory replacement.

Only checkpoints created by this workload should be loaded: PyTorch checkpoints
contain Python objects and are not a safe interchange format for untrusted files.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import pickle
import random
import tempfile
from pathlib import Path

import numpy as np
import torch


class CheckpointIdentityError(ValueError):
    """The checkpoint belongs to another scientific experiment or stage."""


def atomic_bytes(path: Path | str, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def atomic_json(path: Path | str, payload: dict) -> None:
    atomic_bytes(path, (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())


def capture_rng() -> dict:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng(state: dict, device: str) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"].cpu())
    if device.startswith("cuda") and state["cuda"]:
        # Slurm exposes the allocated accelerator as cuda:0. Device UUID is not
        # a portable recovery identity; use the saved worker's single GPU RNG.
        torch.cuda.set_rng_state(state["cuda"][0].cpu(), device=device)


def clone_state(model: torch.nn.Module) -> dict:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


_SERIALIZATION_ERRORS = (EOFError, pickle.UnpicklingError, RuntimeError, ValueError)


def _read(path: Path, identity: str) -> dict:
    state = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Unrecognized checkpoint schema")
    if state.get("identity") != identity:
        raise CheckpointIdentityError(f"Checkpoint identity mismatch: {path.name}")
    return state


def load_checkpoint(directory: Path | str, identity: str) -> dict | None:
    directory = Path(directory)
    current, previous = directory / "checkpoint.pt", directory / "checkpoint.previous.pt"
    errors = []
    for path in (current, previous):
        if not path.exists():
            continue
        try:
            result = _read(path, identity)
        except CheckpointIdentityError:
            raise
        except _SERIALIZATION_ERRORS as exc:
            errors.append({"file": path.name, "type": type(exc).__name__, "message": str(exc)})
            continue
        if errors:
            atomic_json(directory / "checkpoint_recovery.json", {
                "recovered_from": path.name,
                "corrupt_generation_retained": errors,
                "identity": identity,
            })
        return result
    if errors:
        raise RuntimeError(f"No readable checkpoint generation: {errors}")
    return None


def save_checkpoint(directory: Path | str, state: dict) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if state.get("schema_version") != 1 or not state.get("identity"):
        raise ValueError("Checkpoint requires schema_version=1 and scientific identity")
    current, previous = directory / "checkpoint.pt", directory / "checkpoint.previous.pt"
    fd, temporary = tempfile.mkstemp(prefix=".checkpoint.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            torch.save(copy.deepcopy(state), handle)
            handle.flush()
            os.fsync(handle.fileno())
        if current.exists():
            try:
                _read(current, state["identity"])
            except CheckpointIdentityError:
                raise
            except _SERIALIZATION_ERRORS:
                # Do not overwrite a good previous generation with a known bad
                # current generation. Keep the corrupt original as evidence.
                n = 0
                while (directory / f"checkpoint.corrupt.{n}.pt").exists():
                    n += 1
                os.replace(current, directory / f"checkpoint.corrupt.{n}.pt")
            else:
                os.replace(current, previous)
        os.replace(temporary, current)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
