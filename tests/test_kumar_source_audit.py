"""Source-event and signal validity checks are separate from model eligibility."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("kumar_audit", SCRIPTS / "audit_kumar_subset.py")
audit = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(audit)
finally:
    sys.path.pop(0)


def events():
    rows = []
    for index in range(20):
        sample = 5120 + index * 6144
        label = "left_hand" if index % 2 == 0 else "right_hand"
        rows.append({"sample": str(sample), "onset": str(sample / 512), "duration": "5.0",
                     "trial_type": label, "value": str(audit.MAPPING[label])})
    return rows


def validate(rows, n_times=125000):
    return audit.validate_events(rows, sfreq=512.0, n_times=n_times, subject="sub-1",
                                 session="ses-0", run="run-0", source_file="source.edf")


def test_partial_export_precision_is_preserved_without_implicit_exclusion():
    rows = events()
    rows[-1]["duration"] = "4.414062"  # exactly2260samples, six-decimal source export
    result = validate(rows)
    assert len(result) == 20
    assert result[-1]["sample_count"] == 2260
    assert result[-1]["duration_seconds"] == 4.414062
    assert result[-1]["source_duration_exactly5s"] is False
    assert result[-1]["analysis_eligibility"] == "not_selected_no_model_window_policy_yet"
    assert len({row["trial_id"] for row in result}) == 20


def test_full5second_extension_would_exceed_boundary_is_rejected():
    rows = events()
    last = int(rows[-1]["sample"])
    with pytest.raises(ValueError, match="outside EDF boundary"):
        validate(rows, n_times=last + 2260)
    rows[-1]["duration"] = "4.414062"
    assert validate(rows, n_times=last + 2260)[-1]["stop_sample_exclusive"] == last + 2260


@pytest.mark.parametrize("field,value,error", [
    ("trial_type", "rest", "Unknown labels"), ("value", "3", "label/value"),
    ("onset", "1", "seconds/sample"), ("duration", "nan", "Invalid event times"),
    ("duration", "4.123456", "sample-aligned"),
])
def test_rejects_task_mapping_time_and_fractional_sample_errors(field, value, error):
    rows = events()
    rows[0][field] = value
    with pytest.raises(ValueError, match=error):
        validate(rows)


def test_events_are_not_allowed_to_overlap_or_repeat():
    rows = events()
    rows[1]["sample"] = rows[0]["sample"]
    rows[1]["onset"] = rows[0]["onset"]
    with pytest.raises(ValueError, match="duplicate, unordered or overlapping"):
        validate(rows)


class Raw:
    n_times = 20000

    def __init__(self, bad=False):
        self.bad = bad
        self.ranges = []

    def get_data(self, *, start, stop, picks=None):
        self.ranges.append((start, stop))
        result = np.ones((2 if picks else 22, stop - start), dtype=float) * 1e-6
        if self.bad and stop == self.n_times:
            result[0, -1] = np.nan
        return result


def test_numeric_scan_covers_whole_signal_in_bounded_blocks_and4kib_fingerprint():
    raw = Raw()
    result = audit.numeric_scan(raw)
    assert raw.ranges[:2] == [(0, 16384), (16384, 20000)]
    assert result["all_continuous_samples_finite"] is True
    assert result["continuous_numeric_values"] == 22 * 20000
    assert result["global_rms_volts"] == pytest.approx(1e-6)
    assert len(result["central_4KiB_numeric_sha256"]) == 64
    assert len(result["whole_signal_numeric_sha256"]) == 64


def test_nonfinite_continuous_sample_outside_trial_windows_still_fails():
    with pytest.raises(ValueError, match="Nonfinite continuous"):
        audit.numeric_scan(Raw(bad=True))


def test_mne_numpy_integer_sample_count_serializes_without_changing_signal_hash():
    raw = Raw()
    expected = audit.numeric_scan(raw)
    raw.n_times = np.int64(raw.n_times)
    result = audit.numeric_scan(raw)
    assert result == expected
    assert json.loads(json.dumps(result)) == result


def test_duplicate_groups_only_use_successfully_read_signal():
    runs = [{"status": "passed", "source_file": "a.edf", "hash": "same"},
            {"status": "passed", "source_file": "b.edf", "hash": "same"},
            {"status": "failed", "source_file": "unread.edf"}]
    assert audit.duplicate_groups(runs, "hash") == [["a.edf", "b.edf"]]
