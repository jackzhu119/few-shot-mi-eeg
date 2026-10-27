"""BNCI2014-001 MATLAB adapter for the frozen external four-arm comparison.

Only the two hand-imagery classes enter decoding. All four-class trial records
and original artifact flags remain in the manifest. The official MATLAB trial
indices are one based and identify trial start; the class cue occurs 2 s later.
No fitted preprocessing, label balancing, artifact rejection or query-dependent
selection is performed here. Filtering is offline, zero phase, within each run.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, sosfiltfilt


ADAPTER_VERSION = "bnci2014-001-cue0to4s-four-arm-v1"
SFREQ = 250
EEG_CHANNELS = 22
CUE_OFFSET_SAMPLES = 500
EPOCH_SAMPLES = 1000
SUPPORT_BUDGET = 20
LABEL_NAMES = {1: "left_hand", 2: "right_hand", 3: "feet", 4: "tongue"}


def _digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _participant(value):
    text = str(value)
    match = re.fullmatch(r"(?:sub-|A)?0?([1-9])", text)
    if not match:
        raise ValueError("BNCI2014-001 participant must identify one of subjects 1..9")
    return "sub-" + match.group(1).zfill(2)


def _integers(value, name):
    array = np.asarray(value).reshape(-1)
    if (array.dtype.kind not in "iuf" or not np.isfinite(array).all()
            or np.any(array != np.floor(array))):
        raise ValueError(f"{name} must contain finite integer values")
    return array.astype(np.int64)


def _verify_class_order(run):
    values = np.asarray(getattr(run, "classes", []), dtype=object).reshape(-1)
    if len(values) != 4 or any(not isinstance(value, str) for value in values):
        raise ValueError("Official classes must explicitly identify the four ordered class names")
    observed = [re.sub(r"[\s_]+", " ", value.strip().casefold()) for value in values]
    if observed != ["left hand", "right hand", "feet", "tongue"]:
        raise ValueError("Official classes order differs from labels 1:left hand 2:right hand 3:feet 4:tongue")


def load_session(path, participant, session):
    """Return chronological hand-only run arrays plus every original trial row.

    ``session`` is the original T/E acquisition identity, not a shuffled split.
    Empty-trial EOG calibration objects are skipped and never consume an MI-run
    number. The six MI runs must each contain 12 trials of each of four classes.
    """
    path = Path(path)
    participant = _participant(participant)
    if session not in ("T", "E"):
        raise ValueError("session must be the official T or E acquisition")
    contents = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "data" not in contents:
        raise ValueError("MATLAB file has no official data run objects")
    run_objects = np.asarray(contents["data"], dtype=object).reshape(-1)
    runs, manifest, skipped = [], [], []
    for original_position, run in enumerate(run_objects, 1):
        raw_trials = np.asarray(getattr(run, "trial", [])).reshape(-1)
        if not len(raw_trials):
            skipped.append({"original_object_position": original_position,
                            "reason": "no_MI_trials_EOG_calibration_object"})
            continue
        _verify_class_order(run)
        ordinal = len(runs) + 1
        run_identity = f"bnci2014-001/{participant}/ses-{session}/run-{ordinal:02d}"
        trials = _integers(raw_trials, "trial start")
        labels = _integers(getattr(run, "y", []), "original label")
        artifacts = _integers(getattr(run, "artifacts", []), "artifact flag")
        frequency = np.asarray(getattr(run, "fs", [])).reshape(-1)
        if frequency.shape != (1,) or float(frequency[0]) != SFREQ:
            raise ValueError("BNCI2014-001 acquisition frequency must be 250 Hz")
        if (len(trials) != 48 or labels.shape != trials.shape
                or artifacts.shape != trials.shape
                or any(np.sum(labels == label) != 12 for label in LABEL_NAMES)
                or not np.isin(labels, list(LABEL_NAMES)).all()
                or not np.isin(artifacts, [0, 1]).all()):
            raise ValueError("Each MI run must have 48 four-class trials and aligned artifact flags")
        if np.any(trials <= 0) or np.any(np.diff(trials) <= 0):
            raise ValueError("Official one-based trial starts must be positive and increasing")
        raw = np.asarray(getattr(run, "X", []))
        if (raw.ndim != 2 or raw.shape[1] < EEG_CHANNELS
                or raw.dtype.kind not in "iuf" or not np.isfinite(raw[:, :EEG_CHANNELS]).all()):
            raise ValueError("X must contain finite continuous samples and at least 22 EEG channels")
        starts = trials - 1 + CUE_OFFSET_SAMPLES
        stops = starts + EPOCH_SAMPLES
        if np.any(stops > raw.shape[0]):
            raise ValueError("A cue-aligned 4-second epoch exceeds its continuous run")
        # X is supplied in microvolts by the official MATLAB derivative.
        # Keep recorded referencing; do not fit any normalization or use EOG.
        continuous = raw[:, :EEG_CHANNELS].astype(np.float64).T * 1e-6
        sos = butter(4, [8., 30.], btype="bandpass", fs=SFREQ, output="sos")
        filtered = sosfiltfilt(sos, continuous, axis=-1)
        hands = np.flatnonzero(np.isin(labels, [1, 2]))
        x = np.stack([filtered[:, starts[i]:stops[i]] for i in hands]).astype(np.float32)
        ids = np.asarray([f"{run_identity}/trial-{i + 1:04d}" for i in hands])
        rows = []
        for index, label in enumerate(labels):
            row = {"dataset": "BNCI2014-001", "participant": participant,
                   "session": session, "run": ordinal, "run_id": run_identity,
                   "original_object_position": original_position,
                   "trial_id": f"{run_identity}/trial-{index + 1:04d}",
                   "original_trial_number": index + 1,
                   "original_label": int(label), "class_name": LABEL_NAMES[int(label)],
                   "label": int(label - 1) if label in (1, 2) else None,
                   "artifact_flag": bool(artifacts[index]),
                   "original_trial_start_matlab_1based": int(trials[index]),
                   "cue_start_sample_0based": int(starts[index]),
                   "epoch_start_sample_0based": int(starts[index]),
                   "epoch_stop_sample_0based_exclusive": int(stops[index]),
                   "epoch_samples": EPOCH_SAMPLES}
            rows.append(row)
        manifest.extend(rows)
        runs.append({"x": x, "y": (labels[hands] - 1).astype(np.int64),
                     "trial_id": ids, "run_id": np.full(len(hands), run_identity),
                     "artifact": artifacts[hands].astype(bool),
                     "original_label": labels[hands].copy(), "manifest": rows})
    if len(runs) != 6:
        raise ValueError(f"Expected exactly six MI acquisition runs, observed {len(runs)}")
    return {"runs": runs, "manifest": manifest, "skipped_runs": skipped,
            "file": {"path": str(path), "bytes": path.stat().st_size, "sha256": _digest(path)}}


def _join(runs):
    return {key: np.concatenate([run[key] for run in runs], axis=0)
            for key in ("x", "y", "trial_id", "run_id")}


def prepare_subject(source_path, target_path, participant):
    """Prepare the fixed chronological T→E split, retaining all exclusions.

    T MI runs1–4:96hand source trials; T run5:unused; T run6:24hand
    source-query trials. E run1:first20hand support, remaining4unused;
    E runs2–6:120hand query trials. No source-model validation is selected.
    """
    source = load_session(source_path, participant, "T")
    target = load_session(target_path, participant, "E")
    first_target = _join(target["runs"][:1])
    support = {key: value[:SUPPORT_BUDGET].copy() for key, value in first_target.items()}
    splits = {"source_train": _join(source["runs"][:4]),
              "source_query": _join(source["runs"][5:]), "support": support,
              "query": _join(target["runs"][1:])}
    expected = {"source_train": 96, "source_query": 24, "support": 20, "query": 120}
    if {key: len(value["y"]) for key, value in splits.items()} != expected:
        raise ValueError("Prepared chronological split counts differ from the fixed protocol")
    role_by_id = {trial: role for role, split in splits.items() for trial in split["trial_id"]}
    if len(role_by_id) != sum(expected.values()):
        raise ValueError("Trial identities overlap between fixed split roles")
    role_by_run = {}
    for role, split in splits.items():
        for run in set(split["run_id"].tolist()):
            if run in role_by_run and role_by_run[run] != role:
                raise ValueError("Whole acquisition run spans source/support/query roles")
            role_by_run[run] = role
    manifest = []
    for original in source["manifest"] + target["manifest"]:
        row = dict(original)
        role = role_by_id.get(row["trial_id"])
        row["included"] = role is not None
        row["role"] = role or "excluded"
        row["reason"] = (None if role else "non_hand_class" if row["label"] is None
                         else "unused_source_run_5" if row["session"] == "T"
                         else "unused_support_run_tail")
        manifest.append(row)
    metadata = {"adapter_version": ADAPTER_VERSION, "dataset": "BNCI2014-001",
                "participant": _participant(participant), "session_order": ["T", "E"],
                "sample_rate_hz": SFREQ, "channels": EEG_CHANNELS,
                "channel_selection": "first_22_EEG_in_original_order_EOG_excluded",
                "raw_units": "microvolt", "prepared_units": "volt",
                "reference": "recorded_reference_no_additional_CAR",
                "filter": {"family": "Butterworth", "order": 4, "band_hz": [8, 30],
                           "implementation": "scipy.signal.sosfiltfilt",
                           "scope": "continuous_per_acquisition_run", "phase": "offline_zero_phase"},
                "epoch_relative_to_class_cue_seconds": [0, 4],
                "trial_start_to_cue_seconds": 2, "epoch_stop_exclusive": True,
                "artifact_policy": "retain_original_flags_no_artifact_based_exclusion",
                "support_selection": "first_20_chronological_hand_trials_of_first_target_MI_run",
                "support_class_counts": {str(c): int(np.sum(support["y"] == c)) for c in (0, 1)},
                "counts": expected, "all_original_trial_records": len(manifest),
                "query_used_for_fitting": False, "whole_run_role_disjoint": True,
                "source_file": source["file"], "target_file": target["file"],
                "skipped_EOG_objects": {"T": source["skipped_runs"], "E": target["skipped_runs"]}}
    return {"splits": splits, "manifest": manifest, "metadata": metadata}


def _atomic(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    with os.fdopen(descriptor, "wb") as stream:
        writer(stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def save_prepared(result, destination):
    """Write portable NPZ splits and a complete trial/provenance manifest."""
    destination = Path(destination)
    records, expected = {}, {}
    for role, split in result["splits"].items():
        filename = role + ".npz"
        path = destination / filename
        _atomic(path, lambda stream, values=split: np.savez_compressed(stream, **values))
        records[role] = filename
        expected[filename] = _digest(path)
    value = {"metadata": result["metadata"], "trials": result["manifest"],
             "files": records, "input_sha256": expected}
    body = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    _atomic(destination / "manifest.json", lambda stream: stream.write(body))
    return {"files": records, "input_sha256": expected,
            "manifest_sha256": _digest(destination / "manifest.json")}
