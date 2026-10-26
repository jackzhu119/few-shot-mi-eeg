"""Read only locally produced checkpoint/decoder files and export text metadata.

No model, optimizer or inference entry point is imported or constructed. PyTorch
checkpoint loading is limited to this workload's own trusted local files.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


CHECKPOINT_FIELDS = (
    "schema_version", "identity", "complete", "epoch", "step",
    "processed_samples", "position", "best_epoch", "checkpoint_at",
)
EXTRA_FIELDS = (
    "architecture_version", "architecture", "dims", "classes",
    "source_train_identity", "source_validation_identity",
    "source_training_science", "new_source_version", "actual_support_identity",
    "source_state_identity",
)
HISTORY_FIELDS = ("epoch", "train_loss", "learning_rate", "validation_loss")
CLASSICAL_FIELDS = (
    "implementation", "method", "settings", "fit_trial_ids", "source_trial_ids",
    "support_trial_ids", "classwise_update_weights", "query_used_for_fitting",
    "ea_reference_scope", "historical_MNE_model_reproduction", "fit_identity",
    "task_identity", "budget_requested", "n_support_actual", "n_support_available",
)
CLASSICAL_SETTINGS = (
    "n_components", "covariance_shrinkage", "lda_shrinkage", "anchor_tau",
)


def _json_value(value, location):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Nonfinite metadata at " + location)
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item, location + "[]") for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _json_value(item, location + "." + key) for key, item in value.items()}
    raise ValueError("Non-JSON metadata at " + location)


class ResultChangedError(RuntimeError):
    pass


def _stamp(path):
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_unchanged(path, loader):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected an ordinary local result file: " + str(path))
    before = _stamp(path)
    value = loader(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if _stamp(path) != before:
        raise ResultChangedError("Source result changed during metadata extraction: " + str(path))
    return value, {"path": str(path.resolve()), "bytes": before[2], "sha256": digest.hexdigest()}


def extract_checkpoint(path: Path) -> dict:
    import torch

    torch.set_num_threads(1)
    state, source = _read_unchanged(
        path, lambda item: torch.load(item, map_location="cpu", weights_only=False))
    if not isinstance(state, dict) or state.get("schema_version") != 1 or not state.get("identity"):
        raise ValueError("Unrecognized workload checkpoint schema")
    result = {key: _json_value(state[key], key) for key in CHECKPOINT_FIELDS if key in state}
    history = state.get("history", [])
    if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
        raise ValueError("Checkpoint history must be a list of epoch records")
    result["history"] = [{key: _json_value(row[key], "history." + key)
                          for key in HISTORY_FIELDS if key in row} for row in history]
    best_loss = state.get("best_loss")
    if isinstance(best_loss, float) and math.isinf(best_loss) and best_loss > 0:
        if any("validation_loss" in row for row in history):
            raise ValueError("Nonfinite best_loss despite validation history")
        pending_source_validation = isinstance(state.get("extra"), dict) and state["extra"].get("source_validation_identity")
        result.update(best_loss=None, best_loss_status="not_yet_observed_validation" if pending_source_validation
                      else "not_applicable_no_validation")
    else:
        result.update(best_loss=_json_value(best_loss, "best_loss"),
                      best_loss_status="recorded" if best_loss is not None else "not_recorded")
    extra = state.get("extra", {})
    if not isinstance(extra, dict):
        raise ValueError("Checkpoint extra metadata must be a dictionary")
    result["extra"] = {key: _json_value(extra[key], "extra." + key) for key in EXTRA_FIELDS if key in extra}
    result["source_file"] = source
    return result


def extract_classical_metadata(path: Path) -> dict:
    import numpy as np

    def load(item):
        with np.load(item, allow_pickle=False) as archive:
            return json.loads(str(archive["metadata_json"].item()))

    metadata, source = _read_unchanged(path, load)
    if not isinstance(metadata, dict):
        raise ValueError("Classical decoder metadata must be a dictionary")
    result = {key: metadata[key] for key in CLASSICAL_FIELDS if key in metadata}
    if "settings" in result:
        if not isinstance(result["settings"], dict):
            raise ValueError("Classical settings must be a dictionary")
        result["settings"] = {key: result["settings"][key] for key in CLASSICAL_SETTINGS
                              if key in result["settings"]}
    return {"metadata": _json_value(result, "metadata"), "source_file": source}
