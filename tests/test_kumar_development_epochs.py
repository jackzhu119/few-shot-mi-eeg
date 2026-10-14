"""Access and identity safeguards using synthetic EEG only; no scientific scores."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from learning_preserving_bci.datasets.kumar import CHANNEL_NAMES, numeric_hash, preprocess_epoch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def preparation():
    spec = importlib.util.spec_from_file_location(
        "prepare_kumar_development_epochs", ROOT / "scripts/prepare_kumar_development_epochs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_epoch(seed):
    scale = 100e-6 if seed == 0 else 10e-6
    return np.random.default_rng(seed).normal(scale=scale, size=(22, 2560))


@pytest.fixture(scope="module")
def restricted_fixture(preparation, tmp_path_factory):
    folder = tmp_path_factory.mktemp("restricted_development_synthetic")
    config = json.loads((ROOT / "configs/kumar_cross_session_20261012.json").read_text())
    config["prior_signal_audit"] = str(folder / "audits")
    audit_root = Path(config["prior_signal_audit"]) / "runs"
    audit_root.mkdir(parents=True)
    data_root = folder / "data"
    metadata, entries, windows = [], {}, {}
    groups = [("ses-0", "run-0"), ("ses-0", "run-1")]
    groups += [(f"ses-{i}", "run-0") for i in range(1, 6)]
    for group_index, (session, run) in enumerate(groups):
        relative = preparation.expected_source_file("sub-1", session, run)
        path = data_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"synthetic_EDF_bytes/{relative}".encode()
        path.write_bytes(content)
        file_hash = hashlib.sha256(content).hexdigest()
        entries[relative] = {"path": relative, "size": len(content),
                             "checksum_algorithm": "sha256", "checksum": file_hash}
        windows[str(path)] = {}
        for row in range(1, 21):
            seed = group_index * 20 + row - 1
            epoch = synthetic_epoch(seed)
            start = (row - 1) * 2560
            peak = float(np.ptp(epoch, axis=-1).max())
            windows[str(path)][(start, start + 2560)] = seed
            label = "left_hand" if row % 2 else "right_hand"
            metadata.append({
                "subject": "sub-1", "session": session, "run": run,
                "source_row": row, "trial_id": f"sub-1/{session}/{run}/row-{row}",
                "role": "source_train" if session == "ses-0" else "target_support",
                "cohort": "development", "source_file": relative,
                "raw_file_sha256": file_hash, "included": True, "sample_count": 2560,
                "duration_seconds": 5.0, "start_sample": start,
                "stop_sample_exclusive": start + 2560, "processed_sample_count": 640,
                "onset_seconds": start / 512, "raw_numeric_unit": "V",
                "processed_numeric_unit": "V", "label": label,
                "stored_value": 1 if label == "left_hand" else 2,
                "analysis_eligibility": "included_full_5s", "exclusion_reason": None,
                "raw_window_numeric_sha256": numeric_hash(epoch),
                "processed_window_numeric_sha256": numeric_hash(
                    preprocess_epoch(epoch, config), dtype="<f4"
                ),
                "raw_peak_to_peak_max_volts": peak, "qc_peak_to_peak_over_250uv": peak > 250e-6,
                "qc_primary_action": "retain_flagged_no_artifact_certification",
                "synthetic": True, "status": "software_validation_only",
            })
        audit = {"status": "passed", "source_file": relative,
                 "verified_source_files": {relative: {"sha256": file_hash, "bytes": len(content)}},
                 "sfreq": 512.0, "n_times": 20 * 2560, "n_channels": 22,
                 "channel_names": list(CHANNEL_NAMES), "stored_physical_unit": "µV",
                 "MNE_numeric_unit": "V"}
        (audit_root / (relative.replace("/", "__") + ".json")).write_text(json.dumps(audit))
    metadata_path = folder / "included_trial_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return SimpleNamespace(folder=folder, data_root=data_root, config=config, entries=entries,
                           metadata=metadata, metadata_path=metadata_path, windows=windows)


@pytest.mark.parametrize("field,value,error", [
    ("role", "target_query", "Forbidden selected role"),
    ("role", "source_validation", "Forbidden selected role"),
    ("cohort", "final_test", "Forbidden cohort"),
    ("subject", "sub-2", "Forbidden cohort"),
    ("included", False, "Partial or changed epoch"),
    ("sample_count", 2559, "Partial or changed epoch"),
    ("duration_seconds", 4.999, "Partial or changed epoch"),
    ("source_file", "sub-1/ses-0/eeg/unknown.edf", "Unexpected source file"),
    ("raw_numeric_unit", "µV", "Changed numeric unit"),
])
def test_forbidden_metadata_fails_before_any_source_access(
    preparation, restricted_fixture, field, value, error
):
    metadata = deepcopy(restricted_fixture.metadata)
    metadata[0][field] = value
    with pytest.raises(ValueError, match=error):
        preparation.validate_selected_metadata(metadata, "sub-1", restricted_fixture.config)


def test_final_subject_and_missing_support_budget_rejected(preparation, restricted_fixture):
    with pytest.raises(ValueError, match="Forbidden final-cohort subject"):
        preparation.validate_selected_metadata([], "sub-2", restricted_fixture.config)
    # This silently drops an eligible support window rather than a source EOF partial.
    metadata = deepcopy(restricted_fixture.metadata)
    metadata = [t for t in metadata if not (t["session"] == "ses-1" and t["source_row"] < 3)]
    with pytest.raises(ValueError, match="Target support budget mismatch"):
        preparation.validate_selected_metadata(metadata, "sub-1", restricted_fixture.config)


def test_official_git_checksum_supported_and_unpinned_files_rejected(preparation, tmp_path):
    content = b"synthetic public source bytes\n"
    relative = "allowed.edf"
    path = tmp_path / relative
    path.write_bytes(content)
    file_hash = hashlib.sha256(content).hexdigest()
    official = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    entry = {"size": len(content), "checksum_algorithm": "git", "checksum": official}
    trials = [{"source_file": relative, "raw_file_sha256": file_hash}]
    actual_path, proof = preparation.verify_source_file(tmp_path, relative, {relative: entry}, trials)
    assert actual_path == path and proof["official_checksum"] == official
    with pytest.raises(ValueError, match="Unpinned source file"):
        preparation.verify_source_file(tmp_path, relative, {}, trials)
    with pytest.raises(ValueError, match="Unsafe source path"):
        preparation.verify_source_file(tmp_path, "../allowed.edf", {}, trials)
    entry["checksum"] = "0" * 40
    with pytest.raises(ValueError, match="Official source checksum mismatch"):
        preparation.verify_source_file(tmp_path, relative, {relative: entry}, trials)


class WindowOnlyRaw:
    def __init__(self, windows):
        self.windows = windows
        self.first_samp = 0
        self.info = {"sfreq": 512.0}
        self.ch_names = list(CHANNEL_NAMES)
        self._orig_units = dict.fromkeys(CHANNEL_NAMES, "µV")
        self.n_times = 20 * 2560
        self.calls = []
        self.closed = False

    def get_channel_types(self):
        return ["eeg"] * 22

    def get_data(self, *, start, stop):
        # A block read, neighboring window or any new query identity fails here.
        assert (start, stop) in self.windows
        self.calls.append((start, stop))
        return synthetic_epoch(self.windows[(start, stop)])

    def close(self):
        self.closed = True


def test_reconstruction_reads_only_allowed_windows_preserves_order_and_qc(
    preparation, restricted_fixture, monkeypatch, tmp_path
):
    opened = []

    def open_raw(path, *, preload, verbose):
        assert preload is False and verbose == "ERROR"
        raw = WindowOnlyRaw(restricted_fixture.windows[str(path)])
        opened.append(raw)
        return raw

    monkeypatch.setattr(preparation.mne.io, "read_raw_edf", open_raw)
    receipt = preparation.prepare_subject(
        restricted_fixture.data_root, restricted_fixture.metadata_path, "sub-1",
        restricted_fixture.config, restricted_fixture.entries, tmp_path / "subject"
    )
    assert len(opened) == 7 and all(raw.closed for raw in opened)
    assert sum(len(raw.calls) for raw in opened) == 140
    assert all(len(set(raw.calls)) == 20 for raw in opened)
    assert receipt["query_windows_read"] == receipt["partial_windows_read"] == 0
    assert receipt["quality_flags_retained"] == 1 and receipt["synthetic"] is True
    assert (tmp_path / "subject/included_trial_metadata.json").read_bytes() == (
        restricted_fixture.metadata_path.read_bytes()
    )
    with np.load(tmp_path / "subject/restricted_epochs.npz", allow_pickle=False) as saved:
        assert saved["X"].shape == (140, 22, 640) and saved["X"].dtype == np.float32
        assert saved["trial_ids"].tolist() == [t["trial_id"] for t in restricted_fixture.metadata]
        assert saved["y"].tolist() == [0 if t["label"] == "left_hand" else 1
                                      for t in restricted_fixture.metadata]
    with pytest.raises(FileExistsError):
        preparation.prepare_subject(
            restricted_fixture.data_root, restricted_fixture.metadata_path, "sub-1",
            restricted_fixture.config, restricted_fixture.entries, tmp_path / "subject"
        )


def test_preprocessing_drift_and_raw_numeric_drift_are_detected(
    preparation, restricted_fixture, monkeypatch
):
    trial = restricted_fixture.metadata[0]
    raw = WindowOnlyRaw({(trial["start_sample"], trial["stop_sample_exclusive"]): 0})
    original = preparation.preprocess_epoch

    def changed_transform(epoch, config):
        result = original(epoch, config)
        result[0, 0] = np.nextafter(result[0, 0], np.float32(np.inf))
        return result

    monkeypatch.setattr(preparation, "preprocess_epoch", changed_transform)
    with pytest.raises(ValueError, match="Processed window hash mismatch"):
        preparation.reconstruct_epoch(raw, trial, restricted_fixture.config)
    altered_trial = dict(trial, raw_window_numeric_sha256="0" * 64)
    with pytest.raises(ValueError, match="Raw window hash mismatch"):
        preparation.reconstruct_epoch(raw, altered_trial, restricted_fixture.config)


@pytest.mark.parametrize("attribute,value,error", [
    ("n_times", 20 * 2560 - 1, "sample count changed"),
    ("ch_names", list(reversed(CHANNEL_NAMES)), "channels/rate changed"),
    ("info", {"sfreq": 500.0}, "channels/rate changed"),
    ("_orig_units", dict.fromkeys(CHANNEL_NAMES, "V"), "physical unit changed"),
])
def test_native_header_drift_rejected(preparation, restricted_fixture, attribute, value, error):
    relative = restricted_fixture.metadata[0]["source_file"]
    trial = restricted_fixture.metadata[0]
    _, proof = preparation.verify_source_file(
        restricted_fixture.data_root, relative, restricted_fixture.entries, [trial]
    )
    audit_path = Path(restricted_fixture.config["prior_signal_audit"]) / "runs" / (
        relative.replace("/", "__") + ".json"
    )
    raw = WindowOnlyRaw({})
    setattr(raw, attribute, value)
    with pytest.raises(ValueError, match=error):
        preparation.validate_raw_header(raw, json.loads(audit_path.read_text()), proof)
