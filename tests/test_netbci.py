"""NETBCI adapter regression checks using tiny synthetic EDF software fixtures."""

import csv
import hashlib
import json

import mne
import numpy as np
import pytest

from learning_preserving_bci.datasets.netbci import (
    load_netbci_bundle,
    load_netbci_subset,
    save_netbci_bundle,
)


@pytest.fixture
def source(tmp_path):
    pytest.importorskip("edfio")
    root = tmp_path / "source"
    folder = root / "sub-1/ses-01/eeg"
    folder.mkdir(parents=True)
    prefix = folder / "sub-1_ses-01_task-imagery_run-01"
    description = {"Version": "1.0.0", "DatasetType": "derivative", "License": "CC-BY-4.0"}
    (root / "dataset_description.json").write_text(json.dumps(description))
    info = mne.create_info(["C3", "C4"], 10, ch_types="eeg")
    raw = mne.io.RawArray(np.arange(100).reshape(2, 50) * 1e-6, info, verbose="ERROR")
    raw.set_annotations(mne.Annotations([1.0, 2.0], [0.5, 0.5], ["rest", "right_hand"]))
    mne.export.export_raw(str(prefix) + "_eeg.edf", raw, fmt="edf", verbose="ERROR")
    (folder / (prefix.name + "_eeg.json")).write_text(json.dumps(
        {"SamplingFrequency": 10, "EEGChannelCount": 2}))
    (folder / (prefix.name + "_events.json")).write_text(json.dumps(
        {"onset": {"Units": "s"}, "duration": {"Units": "s"},
         "sample": {"Description": "First sample is 0."}}))
    with (folder / (prefix.name + "_channels.tsv")).open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["name", "type", "units", "sampling_frequency"])
        writer.writerows([["C3", "EEG", "µV", 10], ["C4", "EEG", "µV", 10]])
    with (folder / (prefix.name + "_events.tsv")).open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["onset", "duration", "trial_type", "value", "sample"])
        writer.writerows([[1.0, 0.5, "rest", 1, 10], [2.0, 0.5, "right_hand", 2, 20]])
    manifest = tmp_path / "manifest.json"

    def refresh_manifest():
        manifest.write_text(json.dumps([
            {"path": str(path.relative_to(root)), "size": path.stat().st_size,
             "checksum_algorithm": "sha256", "checksum": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(root.rglob("*")) if path.is_file()]))

    refresh_manifest()
    return root, manifest, prefix, refresh_manifest


def test_exact_half_open_epochs_labels_and_identity(source, tmp_path):
    root, manifest, prefix, _ = source
    subset = load_netbci_subset(root, manifest, subject="sub-1")
    continuous = mne.io.read_raw_edf(str(prefix) + "_eeg.edf", verbose="ERROR").get_data()
    np.testing.assert_array_equal(subset.dataset.X[0], continuous[:, 10:15])
    np.testing.assert_array_equal(subset.dataset.X[1], continuous[:, 20:25])
    assert subset.dataset.X.shape == (2, 2, 5)
    assert list(subset.dataset.y) == ["rest", "right_hand"]
    assert subset.provenance["event_value_mapping"] == {"rest": 1, "right_hand": 2}
    assert subset.trials[1].tsv_row == 2
    assert subset.trials[1].stored_event_value == 2
    assert subset.trials[1].trial_id.endswith("run-01/tsv-row-2")
    selected = subset.subset([1, 0])
    assert selected.trials == (subset.trials[1], subset.trials[0])
    output = tmp_path / "bundle"
    save_netbci_bundle(output, subset)
    restored = load_netbci_bundle(output)
    np.testing.assert_array_equal(restored.dataset.X, subset.dataset.X)
    assert restored.trials == subset.trials
    with pytest.raises(FileExistsError):
        save_netbci_bundle(output, subset)


@pytest.mark.parametrize("replacement,error", [
    (("sample", "10", "11"), "seconds/sample"),
    (("duration", "0.5", "5.0"), "outside run"),
    (("trial_type", "rest", "left_hand"), "task labels"),
])
def test_rejects_misaligned_out_of_bounds_or_wrong_task(source, replacement, error):
    root, manifest, prefix, refresh = source
    path = prefix.with_name(prefix.name + "_events.tsv")
    with path.open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    field, old, new = replacement
    assert rows[0][field] == old
    rows[0][field] = new
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    refresh()
    with pytest.raises(ValueError, match=error):
        load_netbci_subset(root, manifest, subject="sub-1")


def test_rejects_seconds_guess_checksum_change_and_missing_session(source):
    root, manifest, prefix, refresh = source
    path = prefix.with_name(prefix.name + "_events.json")
    info = json.loads(path.read_text())
    info["onset"]["Units"] = "millisecond"
    path.write_text(json.dumps(info))
    with pytest.raises(ValueError, match="checksum|size"):
        load_netbci_subset(root, manifest, subject="sub-1")
    refresh()
    with pytest.raises(ValueError, match="seconds"):
        load_netbci_subset(root, manifest, subject="sub-1")
    info["onset"]["Units"] = "s"
    path.write_text(json.dumps(info))
    refresh()
    with pytest.raises(ValueError, match="session missing"):
        load_netbci_subset(root, manifest, subject="sub-1", sessions=["02"])


def test_bundle_rejects_identity_tampering(source, tmp_path):
    root, manifest, _, _ = source
    output = tmp_path / "bundle"
    save_netbci_bundle(output, load_netbci_subset(root, manifest, subject="sub-1"))
    metadata_path = output / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["trials"][0]["label"] = "right_hand"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="identity mismatch"):
        load_netbci_bundle(output)
