"""Fixed-window eligibility on synthetic EDF fixtures; software validation only."""

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import mne
import numpy as np
import pytest

from learning_preserving_bci.datasets.netbci import (
    load_netbci_bundle,
    load_netbci_subset,
    save_netbci_bundle,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))
SPEC = importlib.util.spec_from_file_location(
    "cohort_window_audit", SCRIPT_ROOT / "audit_netbci_cohort.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
POLICY = {"fixed_window_duration_seconds": 5.0,
          "mismatch_action": "retain_source_event_exclude_from_fixed_window_tensor"}


@pytest.fixture
def variable_source(tmp_path):
    pytest.importorskip("edfio")
    root = tmp_path / "synthetic_source"
    folder = root / "sub-fixture/ses-01/eeg"
    folder.mkdir(parents=True)
    prefix = folder / "sub-fixture_ses-01_task-imagery_run-03"
    (root / "dataset_description.json").write_text(json.dumps(
        {"Version": "1.0.0", "DatasetType": "derivative", "License": "CC-BY-4.0"}))
    info = mne.create_info(["C3", "C4"], 10, ch_types="eeg")
    raw = mne.io.RawArray(np.arange(400).reshape(2, 200) * 1e-6, info, verbose="ERROR")
    # A shortened first row prevents eligibility from depending on the first duration.
    raw.set_annotations(mne.Annotations([1.0, 4.0, 10.0], [2.0, 5.0, 5.0],
                                        ["rest", "right_hand", "rest"]))
    mne.export.export_raw(str(prefix) + "_eeg.edf", raw, fmt="edf", verbose="ERROR")
    prefix.with_name(prefix.name + "_eeg.json").write_text(json.dumps(
        {"SamplingFrequency": 10, "EEGChannelCount": 2}))
    prefix.with_name(prefix.name + "_events.json").write_text(json.dumps(
        {"onset": {"Units": "s"}, "duration": {"Units": "s"},
         "sample": {"Description": "First sample is 0."}}))
    with prefix.with_name(prefix.name + "_channels.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["name", "type", "units", "sampling_frequency"])
        writer.writerows([["C3", "EEG", "µV", 10], ["C4", "EEG", "µV", 10]])
    events = prefix.with_name(prefix.name + "_events.tsv")
    with events.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["onset", "duration", "trial_type", "value", "sample"])
        writer.writerows([[1.0, 2.0, "rest", 1, 10], [4.0, 5.0, "right_hand", 2, 40],
                          [10.0, 5.0, "rest", 1, 100]])
    manifest = tmp_path / "manifest.json"

    def refresh():
        manifest.write_text(json.dumps([
            {"path": str(path.relative_to(root)), "size": path.stat().st_size,
             "checksum_algorithm": "sha256", "checksum": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(root.rglob("*")) if path.is_file()]))

    refresh()
    return root, manifest, prefix, refresh


def test_strict_default_still_rejects_variable_duration(variable_source):
    root, manifest, _, _ = variable_source
    with pytest.raises(ValueError, match="Variable epoch length"):
        load_netbci_subset(root, manifest, subject="sub-fixture")


def test_explicit_window_retains_all_sources_and_slices_eligible_only(variable_source, tmp_path):
    root, manifest, prefix, _ = variable_source
    subset = load_netbci_subset(root, manifest, subject="sub-fixture", **POLICY)
    raw = mne.io.read_raw_edf(str(prefix) + "_eeg.edf", verbose="ERROR")
    signal = raw.get_data()
    raw.close()
    assert subset.dataset.X.shape == (2, 2, 50)
    np.testing.assert_array_equal(subset.dataset.X[0], signal[:, 40:90])
    np.testing.assert_array_equal(subset.dataset.X[1], signal[:, 100:150])
    assert [trial.tsv_row for trial in subset.trials] == [2, 3]
    source = subset.provenance["source_event_inventory"]
    assert len(source) == 3
    assert source[0]["trial_id"] == "sub-fixture/ses-01/run-03/tsv-row-1"
    assert source[0]["source_file"].endswith("_run-03_eeg.edf")
    assert source[0]["duration_s"] == 2.0
    assert source[0]["start_sample"] == 10 and source[0]["stop_sample_exclusive"] == 30
    assert source[0]["source_length_samples"] == 20
    assert source[0]["fixed_window_eligible"] is False
    assert source[0]["exclusion_reason"] == "source_event_duration_does_not_match_fixed_window"
    assert subset.provenance["total_source_trials"] == 3
    assert subset.provenance["excluded_trial_count"] == 1
    assert subset.provenance["fixed_window_policy"]["padding_or_extension_performed"] is False
    output = tmp_path / "bundle"
    save_netbci_bundle(output, subset)
    restored = load_netbci_bundle(output)
    assert restored.trials == subset.trials
    assert restored.provenance["source_event_inventory"] == source
    np.testing.assert_array_equal(restored.dataset.X, subset.dataset.X)


@pytest.mark.parametrize("arguments,error", [
    ({"fixed_window_duration_seconds": 5.0}, "mismatch action"),
    ({"mismatch_action": POLICY["mismatch_action"]}, "finite and positive"),
    ({**POLICY, "fixed_window_duration_seconds": np.nan}, "finite and positive"),
    ({**POLICY, "fixed_window_duration_seconds": 0}, "finite and positive"),
    ({**POLICY, "mismatch_action": "pad"}, "mismatch action"),
    ({**POLICY, "fixed_window_duration_seconds": 5.05}, "integral number"),
])
def test_policy_must_be_complete_and_integral(variable_source, arguments, error):
    root, manifest, _, _ = variable_source
    with pytest.raises(ValueError, match=error):
        load_netbci_subset(root, manifest, subject="sub-fixture", **arguments)


@pytest.mark.parametrize("field,value,error", [
    ("sample", "11", "seconds/sample"),
    ("duration", "2.1", "annotation mismatch"),
    ("duration", "20.0", "outside run boundary"),
    ("value", "2", "mapping changed"),
    ("trial_type", "left_hand", "task labels"),
])
def test_excluded_source_events_still_require_complete_validation(variable_source, field, value, error):
    root, manifest, prefix, refresh = variable_source
    path = prefix.with_name(prefix.name + "_events.tsv")
    with path.open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    rows[0][field] = value
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    refresh()
    with pytest.raises(ValueError, match=error):
        load_netbci_subset(root, manifest, subject="sub-fixture", **POLICY)


def test_source_and_eligible_counts_and_actual_window_seconds(variable_source):
    root, manifest, _, _ = variable_source
    result = AUDIT.audit(root, manifest)
    subset = load_netbci_subset(root, manifest, subject="sub-fixture", **POLICY)
    AUDIT.add_window_eligibility_counts(result, subset.provenance["source_event_inventory"])
    summary = result["summary"]
    assert summary["total_source_trials"] == 3 and summary["total_trials"] == 2
    assert summary["source_class_counts"] == {"rest": 2, "right_hand": 1}
    assert summary["class_counts"] == {"rest": 1, "right_hand": 1}
    assert summary["excluded_class_counts"] == {"rest": 1}
    for unit in [result["runs"][0], summary["sessions"][0]]:
        assert unit["trial_count"] == 3 and unit["eligible_trial_count"] == 2
        assert unit["excluded_trial_count"] == 1
        assert unit["source_task_window_seconds"] == 12.0
        assert unit["eligible_task_window_seconds"] == 10.0
    result["upstream_mapping"] = {"original_subject": "sub-original-fixture",
                                  "actual_headers_hash_verified": 1, "declared_original_headers": 1}
    aggregate = AUDIT.cohort_summary([result], ["sub-fixture"])
    assert aggregate["subject_count"] == 1
    assert aggregate["total_source_trials"] == 3 and aggregate["total_trials"] == 2
    assert aggregate["total_excluded_trials"] == 1
    assert aggregate["total_source_task_window_seconds"] == 12.0
    assert aggregate["total_exact_task_window_seconds"] == 10.0


def test_zero_exclusions_still_save_an_explicit_empty_evidence_table(tmp_path):
    path = tmp_path / "excluded_events.tsv"
    AUDIT.write_tsv(path, [], fieldnames=["trial_id", "duration_s", "exclusion_reason"])
    with path.open() as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        assert reader.fieldnames == ["trial_id", "duration_s", "exclusion_reason"]
        assert list(reader) == []
