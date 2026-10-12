"""Meaningful rejection checks for source identities and concatenation boundaries."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("leeuwis_source_audit", SCRIPTS /
                                           "audit_leeuwis_subset.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def source_rows():
    return [
        {"onset": "2.996", "duration": "4.996", "trial_type": "left_hand",
         "value": "2", "sample": "749"},
        {"onset": "8", "duration": "0", "trial_type": "EDGE boundary",
         "value": "1", "sample": "2000"},
        {"onset": "10.996", "duration": "4.996", "trial_type": "right_hand",
         "value": "3", "sample": "2749"},
    ]


def test_preserves_source_duration_and_edge_without_selecting_windows():
    rows = audit.validate_events(source_rows(), sfreq=250, n_times=np.int64(4000))
    json.dumps(rows)
    assert len(rows) == 3
    assert rows[0]["source_duration_sample_count"] == 1249
    assert rows[0]["segment_sample_count"] == 2000
    assert rows[0]["samples_after_source_event"] == 2
    assert rows[1]["event_kind"] == "boundary"
    assert rows[1]["source_duration_sample_count"] == 0
    assert rows[2]["trial_number_in_run"] == 2
    assert all(e["analysis_eligibility"] == "not_selected_no_model_window_policy_yet"
               for e in rows)


@pytest.mark.parametrize("field,value,message", [
    ("value", "1", "mapping"),
    ("trial_type", "rest", "mapping"),
    ("onset", "3", "identity"),
    ("duration", "nan", "Nonfinite"),
    ("duration", "-1", "negative"),
    ("duration", "4.999", "aligned"),
    ("duration", "6", "EDGE boundary"),
    ("duration", "0", "positive duration"),
])
def test_rejects_source_corruption(field, value, message):
    rows = source_rows()
    rows[0][field] = value
    with pytest.raises(ValueError, match=message):
        audit.validate_events(rows, sfreq=250, n_times=4000)


def test_rejects_boundary_with_duration():
    rows = source_rows()
    rows[1]["duration"] = "0.004"
    with pytest.raises(ValueError, match="EDGE must"):
        audit.validate_events(rows, sfreq=250, n_times=4000)


def test_rejects_missing_edge_between_stored_trials():
    rows = source_rows()
    del rows[1]
    with pytest.raises(ValueError, match="one-to-one"):
        audit.validate_events(rows, sfreq=250, n_times=4000)


def test_rejects_final_source_event_past_edf():
    with pytest.raises(ValueError, match="EDF sample boundary"):
        audit.validate_events(source_rows(), sfreq=250, n_times=3997)


def test_rejects_reordered_rows():
    rows = source_rows()
    rows[0], rows[1] = rows[1], rows[0]
    with pytest.raises(ValueError, match="unordered"):
        audit.validate_events(rows, sfreq=250, n_times=4000)


class FakeRaw:
    def __init__(self, values):
        self.values = values
        self.n_times = values.shape[1]
        self.ch_names = [f"channel-{i}" for i in range(values.shape[0])]

    def get_data(self, start, stop, picks=None):
        data = self.values[:, start:stop]
        return data if picks is None else data[picks]


def test_numeric_scan_checks_late_block_and_detects_flatline():
    values = np.tile(np.arange(17000, dtype=float), (16, 1)) / 1e6
    values[3] = 0
    result = audit.scan_numeric(FakeRaw(values))
    assert result["continuous_numeric_values"] == 16 * 17000
    assert result["flatline_channel_names"] == ["channel-3"]
    assert result["all_continuous_samples_finite"] is True
    values[5, -1] = np.nan
    with pytest.raises(ValueError, match="Nonfinite"):
        audit.scan_numeric(FakeRaw(values))


def test_duplicate_groups_separate_within_subject_and_cross_subject():
    rows = [{"subject": "sub-1", "id": "a", "hash": "x", "label": "left_hand"},
            {"subject": "sub-1", "id": "b", "hash": "x", "label": "left_hand"},
            {"subject": "sub-2", "id": "c", "hash": "y", "label": "right_hand"},
            {"subject": "sub-3", "id": "d", "hash": "y", "label": "left_hand"},
            {"subject": "sub-4", "id": "e", "hash": "z", "label": "left_hand"}]
    groups = audit.duplicate_groups(rows, "hash", "id")
    assert len(groups) == 2
    assert groups[0]["cross_subject"] is False
    assert groups[1]["cross_subject"] is True
    assert groups[1]["labels"] == ["left_hand", "right_hand"]
