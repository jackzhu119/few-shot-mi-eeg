"""Validate source-time integrity without treating boundaries as training trials."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("milimb_liu_audit", SCRIPTS / "audit_milimb_liu_subset.py")
audit = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(audit)
finally:
    sys.path.pop(0)


def milimb_events():
    return [{"onset": "4.0", "duration": "0.0", "trial_type": "EDGE boundary", "value": "1", "sample": "500"},
            {"onset": "4.0", "duration": "3.992", "trial_type": "clh", "value": "2", "sample": "500"}]


def validate(rows, *, dataset="nm000328", n_times=1000):
    return audit.validate_events(rows, policy=audit.POLICIES[dataset], n_times=n_times,
                                 source_file="sub-1/ses-0/eeg/sub-1_ses-0_task-imagery_run-0_eeg.edf")


def test_zero_duration_boundary_and_tied_task_onset_keep_both_source_rows():
    result = validate(milimb_events())
    assert len(result) == 2
    assert result[0]["source_event_kind"] == "concatenation_boundary"
    assert result[0]["duration_samples_as_stored"] == 0
    assert result[1]["duration_seconds"] == 3.992
    assert result[1]["duration_samples_as_stored"] == 499
    assert result[1]["stop_sample_exclusive"] == 999
    assert all(e["analysis_eligibility"] == "unselected;no_model_window_policy" for e in result)


@pytest.mark.parametrize("field,value,message", [
    ("trial_type", "unknown", "Unknown source label"),
    ("trial_type", "rest", "Zero duration"),
    ("duration", "0.008", "Zero duration"),
    ("duration", "-1", "Invalid source times"),
    ("onset", "nan", "Invalid source times"),
    ("sample", "501", "onset/sample"),
    ("value", "0", "Invalid stored source"),
])
def test_boundary_does_not_allow_unknown_label_negative_time_or_implicit_trial(field, value, message):
    rows = milimb_events()
    rows[0][field] = value
    with pytest.raises(ValueError, match=message):
        validate(rows)


def test_5second_extension_exceeds_source_boundary_and_is_rejected():
    rows = milimb_events()
    rows[1]["duration"] = "5.0"
    with pytest.raises(ValueError, match="outside signal boundary"):
        validate(rows)


def test_positive_trial_overlap_rejected_despite_allowed_boundary_ties():
    rows = milimb_events()
    rows.append({**rows[1], "trial_type": "crh", "value": "3"})
    with pytest.raises(ValueError, match="Overlapping positive"):
        validate(rows)


def test_milimb_value_mapping_is_per_source_and_never_remapped_from_readme():
    rows = milimb_events()
    rows[1].update(trial_type="drf", value="5")
    assert validate(rows)[1]["stored_value"] == 5


def test_directory_and_file_participant_identity_must_match_before_reading(tmp_path):
    with pytest.raises(ValueError, match="Unexpected signal identity"):
        audit.audit_run(tmp_path, "sub-1/ses-0/eeg/sub-2_ses-0_task-imagery_run-0_eeg.edf",
                        {}, audit.POLICIES["nm000328"])


def test_liu_rejects_incorrect_class_code():
    rows = [{"onset": "2.0", "duration": "4.0", "trial_type": "left_hand", "value": "2", "sample": "1000"}]
    with pytest.raises(ValueError, match="Stored class/value mismatch"):
        validate(rows, dataset="nm000158", n_times=160000)


def test_liu_balanced_40_events_preserved_as_clinical_source():
    rows = [{"onset": str(2 + i * 8), "duration": "4.0", "trial_type": "left_hand" if i % 2 == 0 else "right_hand",
             "value": "1" if i % 2 == 0 else "2", "sample": str((2 + i * 8) * 500)} for i in range(40)]
    result = validate(rows, dataset="nm000158", n_times=160000)
    assert len(result) == 40
    assert result[-1]["stop_sample_exclusive"] == 159000
    assert "stroke" in audit.POLICIES["nm000158"]["population"]


class Raw:
    n_times = np.int64(20000)

    def __init__(self, bad=False):
        self.bad = bad
        self.ranges = []

    def get_data(self, *, start, stop, picks=None):
        self.ranges.append((start, stop))
        values = np.full((2 if picks else 16, stop - start), 1e-6)
        if self.bad and stop == self.n_times:
            values[0, -1] = np.inf
        return values


def test_full_numeric_scan_covers_outside_events_and_is_json_serializable():
    raw = Raw()
    result = audit.numeric_scan(raw)
    assert raw.ranges[:2] == [(0, 16384), (16384, 20000)]
    assert result["continuous_numeric_values"] == 16 * 20000
    assert result["global_rms_volts"] == pytest.approx(1e-6)
    assert json.loads(json.dumps(result)) == result


def test_nonfinite_last_continuous_sample_is_detected():
    with pytest.raises(ValueError, match="Nonfinite continuous"):
        audit.numeric_scan(Raw(bad=True))


def test_liu_native_microvolt_sidecar_volt_conflict_is_explicit_and_blocks_model_reconciliation():
    channels = [{"name": "C3", "type": "EEG", "units": "V", "sampling_frequency": "500"}]
    result = audit.validate_source_units(channels, {"C3": "µV"}, audit.POLICIES["nm000158"])
    assert result["native_header_unit"] == "µV"
    assert result["channel_sidecar_unit"] == "V"
    assert not result["native_and_sidecar_units_agree"]
    assert not result["units_reconciled_for_model_training"]
    assert "no additional rescaling" in result["numeric_loading_rule"]


@pytest.mark.parametrize("native,sidecar", [("V", "V"), ("mV", "V"), ("µV", "µV")])
def test_unit_changes_are_rejected_instead_of_guessed_or_rescaled(native, sidecar):
    channels = [{"name": "C3", "type": "EEG", "units": sidecar, "sampling_frequency": "500"}]
    with pytest.raises(ValueError, match="units"):
        audit.validate_source_units(channels, {"C3": native}, audit.POLICIES["nm000158"])


def test_whole_continuous_flat_channels_remain_recorded_not_excluded():
    result = audit.numeric_scan(Raw())
    assert result["flatline_channel_indices"] == list(range(16))


def test_explicit_source_census_keeps_overlapping_native_rows_without_retiming():
    rows = [{"onset": str(2 + i * 8), "duration": "4.0",
             "trial_type": "left_hand" if i % 2 == 0 else "right_hand",
             "value": "1" if i % 2 == 0 else "2", "sample": str((2 + i * 8) * 500)}
            for i in range(40)]
    rows[14].update(onset="106.008", sample="53004")
    with pytest.raises(ValueError, match="Overlapping positive"):
        validate(rows, dataset="nm000158", n_times=160000)
    result = audit.validate_events(rows, policy=audit.POLICIES["nm000158"], n_times=160000,
                                   source_file="sub-20/ses-0/eeg/sub-20_ses-0_task-imagery_run-0_eeg.bdf",
                                   record_source_overlap=True)
    assert len(result) == 40
    assert result[14]["start_sample"] == 53004
    assert result[14]["duration_samples_as_stored"] == 2000
    assert result[14]["source_overlap_with_previous_task_samples"] == 1996
    assert all(e["analysis_eligibility"] == "unselected;no_model_window_policy" for e in result)
