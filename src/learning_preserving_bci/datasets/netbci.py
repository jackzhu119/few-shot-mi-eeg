"""Local NETBCI EDF/BIDS adapter with explicit, auditable trial identities.

No download, filtering, re-referencing, baseline correction, artifact rejection,
or model fitting is performed. An optional explicit fixed-window eligibility
policy retains all source event identities and excludes duration mismatches
only from the rectangular tensor. Labels are names; stored numeric values remain
in trial metadata so upstream and derivative encodings cannot be confused.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import mne
import numpy as np

from . import EEGDataset, load_npz, save_npz


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class NETBCITrial:
    subject: str
    session: str
    run: str
    trial_id: str
    tsv_row: int
    label: str
    stored_event_value: int
    onset_s: float
    duration_s: float
    start_sample: int
    stop_sample_exclusive: int
    source_file: str


@dataclass(frozen=True)
class NETBCISubset:
    dataset: EEGDataset
    trials: tuple[NETBCITrial, ...]
    provenance: dict

    def __post_init__(self) -> None:
        _require(not self.dataset.is_synthetic, "NETBCI empirical data cannot be synthetic")
        _require(len(self.trials) == self.dataset.n_trials, "Trial metadata length mismatch")
        _require(len({item.trial_id for item in self.trials}) == len(self.trials),
                 "Duplicate trial identity")
        for index, item in enumerate(self.trials):
            _require((item.subject, item.session, item.label) == (
                self.dataset.subjects[index], self.dataset.sessions[index], self.dataset.y[index]),
                "Trial metadata and dataset identity mismatch")
            _require(item.stop_sample_exclusive - item.start_sample == self.dataset.X.shape[2],
                     "Trial metadata and epoch length mismatch")
            _require(item.start_sample >= 0 and item.tsv_row > 0 and bool(item.run),
                     "Invalid trial/run identity")
            _require(abs(item.onset_s * self.dataset.sfreq - item.start_sample) < 1e-6
                     and abs(item.duration_s * self.dataset.sfreq - self.dataset.X.shape[2]) < 1e-6,
                     "Trial metadata times and sample indices mismatch")
            _require(item.stored_event_value == self.provenance["event_value_mapping"][item.label],
                     "Trial event value and source mapping mismatch")

    def subset(self, indices: Sequence[int] | np.ndarray) -> NETBCISubset:
        index = np.asarray(indices)
        selected = self.dataset.subset(index)
        positions = np.arange(self.dataset.n_trials)[index]
        return NETBCISubset(selected, tuple(self.trials[int(i)] for i in positions),
                            dict(self.provenance, selection="explicit trial subset"))

    def run_table(self) -> list[dict]:
        rows = []
        keys = sorted({(item.subject, item.session, item.run) for item in self.trials})
        for subject, session, run in keys:
            selected = [item for item in self.trials if (item.subject, item.session, item.run)
                        == (subject, session, run)]
            rows.append({"subject": subject, "session": session, "run": run,
                         "trial_count": len(selected),
                         "class_counts": dict(Counter(item.label for item in selected))})
        return rows


def load_netbci_subset(
    data_root: str | Path,
    manifest_path: str | Path,
    *,
    subject: str,
    sessions: Sequence[str] | None = None,
    fixed_window_duration_seconds: float | None = None,
    mismatch_action: str | None = None,
) -> NETBCISubset:
    """Read one local subject, preserving all stored trials and run boundaries.

    Epochs are exact ``[sample, sample + duration * sfreq)`` slices in volts.
    An incompatible duration, label, channel order, checksum, or annotation
    raises an error rather than silently changing or dropping a trial.
    With an explicit fixed duration and the supported mismatch action, every
    source event is audited and retained in provenance; only exact-duration
    events enter ``X``. No source event is padded, extended, or shortened.
    """
    root, manifest_path = Path(data_root), Path(manifest_path)
    fixed_window_policy = None
    if fixed_window_duration_seconds is not None or mismatch_action is not None:
        _require(fixed_window_duration_seconds is not None
                 and not isinstance(fixed_window_duration_seconds, bool)
                 and np.isfinite(fixed_window_duration_seconds)
                 and fixed_window_duration_seconds > 0,
                 "Explicit fixed-window duration must be finite and positive")
        _require(mismatch_action == "retain_source_event_exclude_from_fixed_window_tensor",
                 "Explicit fixed-window eligibility requires the supported mismatch action")
        fixed_window_policy = {
            "fixed_window_duration_seconds": float(fixed_window_duration_seconds),
            "mismatch_action": mismatch_action,
            "source_events_retained": True,
            "padding_or_extension_performed": False,
        }
    _require(bool(re.fullmatch(r"sub-[A-Za-z0-9]+", subject)), "Invalid subject identifier")
    manifest = json.loads(manifest_path.read_text())
    entries = {entry["path"]: entry for entry in manifest}
    _require(len(entries) == len(manifest), "Duplicate paths in source manifest")
    verified = {}

    def verify(relative: str) -> Path:
        path = Path(relative)
        _require(not path.is_absolute() and ".." not in path.parts, "Unsafe source path")
        _require(relative in entries, f"Missing pinned source checksum: {relative}")
        local, expected = root / path, entries[relative]
        _require(local.is_file() and local.stat().st_size == expected["size"],
                 f"Missing or size-mismatched source: {relative}")
        algorithm = expected["checksum_algorithm"]
        if algorithm == "sha256":
            digest = file_sha256(local)
        elif algorithm == "git":
            data = local.read_bytes()
            digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        else:
            raise ValueError(f"Unsupported source checksum: {algorithm}")
        _require(digest == expected["checksum"], f"Source checksum mismatch: {relative}")
        verified[relative] = {"algorithm": algorithm, "checksum": digest}
        return local

    description = json.loads(verify("dataset_description.json").read_text())
    _require(description["Version"] == "1.0.0" and description["DatasetType"] == "derivative",
             "This adapter is validated for the NEMAR v1.0.0 derivative only")
    _require(description["License"] == "CC-BY-4.0", "Unreviewed data license")
    paths = sorted(name for name in entries if name.startswith(subject + "/")
                   and name.endswith("_eeg.edf"))
    _require(bool(paths), "No selected subject EDF in the pinned manifest")
    selected_sessions = set(sessions) if sessions is not None else None
    chunks, identities, source_event_inventory, channel_names = [], [], [], None
    sfreq, n_samples = None, None
    mapping: dict[str, int] = {}
    seen_sessions = set()
    for relative in paths:
        match = re.search(r"_ses-([^_]+)_task-imagery_run-([^_]+)_eeg\.edf$", relative)
        _require(match is not None, f"Unsupported NETBCI task/file identity: {relative}")
        session, run = match.groups()
        if selected_sessions is not None and session not in selected_sessions:
            continue
        seen_sessions.add(session)
        prefix = relative.removesuffix("_eeg.edf")
        eeg_info = json.loads(verify(prefix + "_eeg.json").read_text())
        events_info = json.loads(verify(prefix + "_events.json").read_text())
        channels = _tsv(verify(prefix + "_channels.tsv"))
        events = _tsv(verify(prefix + "_events.tsv"))
        _require(bool(events), "Empty event table")
        _require(events_info["onset"]["Units"] == events_info["duration"]["Units"] == "s",
                 "Event units are not explicitly seconds")
        _require("First sample is 0" in events_info["sample"]["Description"],
                 "Zero-based sample indexing not documented")
        raw = mne.io.read_raw_edf(verify(relative), preload=False, verbose="ERROR")
        try:
            frequency = float(raw.info["sfreq"])
            _require(raw.first_samp == 0, "Unexpected signal sample origin")
            _require(frequency == float(eeg_info["SamplingFrequency"]), "Sampling metadata mismatch")
            names = tuple(raw.ch_names)
            _require(names == tuple(item["name"] for item in channels), "Channel order mismatch")
            _require(len(names) == int(eeg_info["EEGChannelCount"]), "Channel count mismatch")
            _require(all(item["type"] == "EEG" and float(item["sampling_frequency"]) == frequency
                         and raw._orig_units[item["name"]] == item["units"] for item in channels),
                     "Channel type, rate or physical unit mismatch")
            if channel_names is None:
                channel_names, sfreq = names, frequency
            _require(names == channel_names and frequency == sfreq, "Incompatible runs")
            onsets = np.array([float(item["onset"]) for item in events])
            durations = np.array([float(item["duration"]) for item in events])
            starts = np.array([int(item["sample"]) for item in events])
            labels = [item["trial_type"] for item in events]
            _require(set(labels) <= {"right_hand", "rest"}, "Unreviewed NETBCI task labels")
            _require(np.isfinite(onsets).all() and np.isfinite(durations).all()
                     and np.all(durations > 0), "Invalid event times")
            _require(np.allclose(onsets * frequency, starts, rtol=0, atol=1e-6),
                     "Event seconds/sample alignment failed")
            lengths = durations * frequency
            _require(np.allclose(lengths, np.rint(lengths), rtol=0, atol=1e-6),
                     "Nonintegral epoch length")
            lengths = np.rint(lengths).astype(int)
            stops = starts + lengths
            _require(np.all(starts >= 0) and np.all(stops <= raw.n_times), "Trial outside run boundary")
            _require(np.all(np.diff(starts) > 0) and np.all(stops[:-1] <= starts[1:]),
                     "Duplicate, unordered or overlapping trials")
            _require(len(raw.annotations) == len(events)
                     and list(raw.annotations.description) == labels
                     and np.allclose(raw.annotations.onset, onsets, rtol=0, atol=1e-6)
                     and np.allclose(raw.annotations.duration, durations, rtol=0, atol=1e-6),
                     "EDF and TSV annotation mismatch")
            if fixed_window_policy is None:
                if n_samples is None:
                    n_samples = int(lengths[0])
                _require(np.all(lengths == n_samples),
                         "Variable epoch length requires an explicit policy")
            else:
                required_length = fixed_window_duration_seconds * frequency
                _require(abs(required_length - round(required_length)) < 1e-6,
                         "Fixed-window duration is not an integral number of samples")
                n_samples = round(required_length)
                _require(n_samples > 0, "Fixed-window duration must contain at least one sample")
            eligible = lengths == n_samples
            signal = raw.get_data()
            _require(np.isfinite(signal).all(), "Nonfinite EEG signal")
            if eligible.any():
                chunks.append(np.stack([signal[:, start:stop]
                                        for start, stop in zip(starts[eligible], stops[eligible])]))
            for row, (event, start, stop) in enumerate(zip(events, starts, stops), start=1):
                label, value = event["trial_type"], int(event["value"])
                _require(label not in mapping or mapping[label] == value, "Event mapping changed")
                mapping[label] = value
                identity = NETBCITrial(
                    subject, session, run, f"{subject}/ses-{session}/run-{run}/tsv-row-{row}",
                    row, label, value, float(event["onset"]), float(event["duration"]),
                    int(start), int(stop), relative)
                is_eligible = bool(eligible[row - 1])
                source_event_inventory.append({
                    **asdict(identity), "source_length_samples": int(stop - start),
                    "fixed_window_eligible": is_eligible,
                    "exclusion_reason": "" if is_eligible else
                    "source_event_duration_does_not_match_fixed_window",
                })
                if is_eligible:
                    identities.append(identity)
        finally:
            raw.close()
    _require(selected_sessions is None or seen_sessions == selected_sessions, "Requested session missing")
    _require(bool(chunks) and len(set(mapping.values())) == len(mapping), "No usable or ambiguous classes")
    dataset = EEGDataset(np.concatenate(chunks), np.array([item.label for item in identities]),
                         np.array([item.subject for item in identities]),
                         np.array([item.session for item in identities]), sfreq, channel_names, False)
    provenance = {"dataset_id": "nm000305", "version": description["Version"],
                  "version_doi": "10.82901/nemar.nm000305.v1.0.0",
                  "license": description["License"], "signal_unit": "V",
                  "epoch_convention": "[sample, sample + duration * sfreq)",
                  "trial_identity_convention": "stored TSV row; not invented original trial number",
                  "event_value_mapping": mapping, "source_checksums": verified,
                  "manifest_sha256": file_sha256(manifest_path),
                  "adapter_source_sha256": file_sha256(Path(__file__)),
                  "operations": ["EDF unit conversion by MNE", "exact epoch slicing"],
                  "behavior_values_broadcast_to_trials": False,
                  "models_trained": False}
    if fixed_window_policy is not None:
        provenance["operations"].append("explicit fixed-window eligibility with retained source events")
        provenance.update({
            "fixed_window_policy": fixed_window_policy,
            "source_event_inventory": source_event_inventory,
            "total_source_trials": len(source_event_inventory),
            "eligible_trial_count": len(identities),
            "excluded_trial_count": len(source_event_inventory) - len(identities),
        })
    return NETBCISubset(dataset, tuple(identities), provenance)


def save_netbci_bundle(directory: str | Path, subset: NETBCISubset) -> None:
    """Save NPZ plus mandatory identity metadata; refuse existing directories."""
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError("Choose a new output directory; prior bundles are preserved")
    directory.mkdir(parents=True)
    save_npz(directory / "epochs.npz", subset.dataset)
    metadata = {"schema_version": 1, "trials": [asdict(item) for item in subset.trials],
                "provenance": subset.provenance,
                "epochs_sha256": file_sha256(directory / "epochs.npz")}
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


def load_netbci_bundle(directory: str | Path) -> NETBCISubset:
    directory = Path(directory)
    metadata = json.loads((directory / "metadata.json").read_text())
    _require(metadata["schema_version"] == 1, "Unsupported NETBCI bundle schema")
    _require(file_sha256(directory / "epochs.npz") == metadata["epochs_sha256"],
             "Epoch bundle checksum mismatch")
    return NETBCISubset(load_npz(directory / "epochs.npz"),
                        tuple(NETBCITrial(**item) for item in metadata["trials"]),
                        metadata["provenance"])
