"""Development-only support measurement, without decoder fits or query scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def cosine(a, b):
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return None if denominator == 0 else float(np.dot(a, b) / denominator)


def direction(x, y):
    return x[y == 1].mean(axis=0) - x[y == 0].mean(axis=0)


def measure(source, source_labels, support, labels, seed=42):
    """All uncertainty is conditional on this tiny labeled support sample."""
    axis = direction(source, source_labels)
    groups = [np.flatnonzero(labels == value) for value in (0, 1)]
    if min(map(len, groups)) < 4:
        raise ValueError("Insufficient support per class for split-half measurement")
    halves = [np.concatenate([g[:len(g)//2] for g in groups]),
              np.concatenate([g[len(g)//2:] for g in groups])]
    estimate = cosine(axis, direction(support, labels))
    split = cosine(*(direction(support[h], labels[h]) for h in halves))
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(1000):
        ids = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups])
        value = cosine(axis, direction(support[ids], labels[ids]))
        if value is not None:
            boot.append(value)
    ci = np.quantile(boot, [.025, .975]).tolist() if boot else [None, None]
    return {"support_n": len(labels), "class_n": list(map(len, groups)),
            "source_support_direction_cosine": estimate,
            "support_split_half_direction_cosine": split,
            "conditional_bootstrap_cosine_interval": ci,
            "bootstrap_nonzero_directions": len(boot)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = Path("configs/kumar_support_reliability_20261014.json")
    config = json.loads(config_path.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    rows, inputs = [], []
    for subject in config["development_subjects"]:
        folder = args.results / f"sub-{subject}"
        metadata_path = folder / "included_trial_metadata.json"
        feature_path = folder / "fixed_features.npz"
        metadata = json.loads(metadata_path.read_text())
        selected = [i for i, t in enumerate(metadata)
                    if t["role"] in config["allowed_roles"]]
        meta = [metadata[i] for i in selected]
        if any(t["cohort"] != "development" for t in meta):
            raise ValueError("Forbidden final cohort")
        with np.load(feature_path, allow_pickle=False) as f:
            if list(f["trial_ids"]) != [t["trial_id"] for t in metadata]:
                raise ValueError("Feature/metadata identity mismatch")
            # The preexisting container contains query rows; only allowed rows are used.
            x = f["source_standardized_44"][selected]
        y = np.asarray([int(t["label"] == "right_hand") for t in meta])
        train = np.asarray([t["role"] == "source_train" for t in meta])
        if train.sum() != 40:
            raise ValueError("Source budget mismatch")
        for session in [f"ses-{i}" for i in range(1, 6)]:
            mask = np.asarray([t["role"] == "target_support" and
                               t["session"] == session for t in meta])
            selected_meta = [t for t, keep in zip(meta, mask, strict=True) if keep]
            if any(t["run"] != "run-0" for t in selected_meta):
                raise ValueError("Non-current support run")
            rows.append({"subject": subject, "session": session,
                         **measure(x[train], y[train], x[mask], y[mask], config["seed"]),
                         "source_trial_ids": [t["trial_id"] for t, keep in
                                              zip(meta, train, strict=True) if keep],
                         "support_trial_ids": [t["trial_id"] for t in selected_meta]})
        inputs.extend([{"path": str(p), "sha256": digest(p)}
                       for p in [metadata_path, feature_path]])
    result = {"status": "completed", "rows": rows, "inputs": inputs,
              "config_sha256": digest(config_path), "script_sha256": digest(Path(__file__)),
              "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "new_decoder_fits": 0, "query_rows_used": 0, "final_subjects_opened": 0,
              "threshold_selected": False, "numpy_version": np.__version__}
    (args.output / "measurement_receipt.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ["status", "new_decoder_fits",
                                           "query_rows_used", "final_subjects_opened"]}))


if __name__ == "__main__":
    main()
