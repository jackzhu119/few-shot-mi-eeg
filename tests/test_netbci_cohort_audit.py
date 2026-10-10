"""Cohort access checks reject guessed identities and unsupported source claims."""

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))
SPEC = importlib.util.spec_from_file_location("cohort_audit", SCRIPT_ROOT / "audit_netbci_cohort.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def provenance(original="sub-participantA", subject="27"):
    return {"files": [{
        "subject": subject,
        "file": f"{original}/ses-02/eeg/{original}_ses-02_task-MotorImageryRest_run-05_eeg.vhdr",
        "bytes": 100, "sha256": "a" * 64,
    }]}


def run(channels=("C3", "C4"), subject="sub-27"):
    return {"subject": subject, "session": "02", "run": "05",
            "sampling_frequency_hz": 250.0, "channel_names": list(channels),
            "channel_count": len(channels), "class_counts": {"rest": 2, "right_hand": 3},
            "trial_count": 5, "signal_samples": 10000, "trial_durations_s": [5.0]}


def test_subject_identity_is_from_explicit_provenance_not_zero_padding():
    original, rows = MODULE.upstream_subject_map(provenance(), "sub-27")
    assert original == "sub-participantA" and rows[0]["subject"] == "27"
    with pytest.raises(ValueError, match="No upstream"):
        MODULE.upstream_subject_map(provenance(), "sub-1")


def test_ambiguous_and_duplicate_original_identities_fail():
    source = provenance()
    source["files"] += provenance("sub-participantB")["files"]
    # Same session/run mapping is invalid before an identity could be selected.
    with pytest.raises(ValueError, match="Duplicate"):
        MODULE.upstream_subject_map(source, "sub-27")
    source["files"][1]["file"] = source["files"][1]["file"].replace("run-05", "run-06")
    with pytest.raises(ValueError, match="Ambiguous"):
        MODULE.upstream_subject_map(source, "sub-27")
    with pytest.raises(ValueError, match="Duplicate"):
        MODULE.upstream_subject_map({"files": provenance()["files"] * 2}, "sub-27")


@pytest.mark.parametrize("path", ["/absolute/file.vhdr", "../file.vhdr",
                                   "sub-A/ses-03/eeg/sub-A_ses-02_task-MotorImageryRest_run-05_eeg.vhdr"])
def test_unsafe_or_conflicting_upstream_paths_fail(path):
    source = provenance()
    source["files"][0]["file"] = path
    with pytest.raises(ValueError):
        MODULE.upstream_subject_map(source, "sub-27")


def test_missing_header_is_a_declaration_not_an_actual_hash_check(tmp_path):
    original, headers = MODULE.inspect_original_headers(provenance(), "sub-27", [run()], [tmp_path])
    assert original == "sub-participantA"
    assert headers[0]["original_header_hash_verified"] is False
    assert headers[0]["actual_original_header_sha256"] == "unresolved"
    assert headers[0]["original_sampling_frequency_hz"] == "unresolved"
    assert headers[0]["original_signal_equality_verified"] is False


def cached_header(tmp_path):
    source = provenance()
    path = tmp_path / source["files"][0]["file"]
    path.parent.mkdir(parents=True)
    path.write_text("Brain Vision Data Exchange Header File Version 1.0\n"
                    "[Common Infos]\nNumberOfChannels=2\nSamplingInterval=4001.6\n"
                    "[Channel Infos]\nCh1=C3,,0.1,µV\nCh2=C4,,0.1,µV\n")
    source["files"][0].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             bytes=path.stat().st_size)
    return source, path


def test_actual_header_rate_preserved_and_empty_reference_not_invented(tmp_path):
    source, _ = cached_header(tmp_path)
    _, rows = MODULE.inspect_original_headers(source, "sub-27", [run()], [tmp_path])
    row = rows[0]
    assert row["original_header_hash_verified"] is True
    assert row["original_sampling_frequency_hz"] == 1e6 / 4001.6
    assert row["original_sampling_frequency_hz"] != row["derivative_sampling_frequency_hz"]
    assert row["original_reference_fields_json"] == '{"": 2}'
    assert "do not establish" in row["original_reference_interpretation"]
    assert row["original_marker_sequence_verified"] is False


def test_header_byte_change_and_channel_mismatch_fail(tmp_path):
    source, path = cached_header(tmp_path)
    with pytest.raises(ValueError, match="channel order"):
        MODULE.inspect_original_headers(source, "sub-27", [run(("C4", "C3"))], [tmp_path])
    path.write_text(path.read_text() + "\nchanged")
    with pytest.raises(ValueError, match="SHA256"):
        MODULE.inspect_original_headers(source, "sub-27", [run()], [tmp_path])


def audit_row(subject="sub-27", original="sub-participantA", channels=("C3", "C4")):
    return {"summary": {"subject": subject, "all_checks_pass": True,
                        "class_counts": {"rest": 2, "right_hand": 3},
                        "sessions": [{"session": "02", "runs": 1, "trial_count": 5}]},
            "runs": [run(channels, subject)],
            "upstream_mapping": {"original_subject": original,
                                 "actual_headers_hash_verified": 1, "declared_original_headers": 1}}


def test_summary_retains_channel_mismatch_and_does_not_drop_missing_participants():
    first, other = audit_row(), audit_row("sub-29", "sub-participantB", ("C4", "C3", "Cz"))
    summary = MODULE.cohort_summary([first, other], ["sub-27", "sub-28", "sub-29"])
    assert summary["all_channel_orders_equal"] is False
    assert summary["common_channel_order"] == ["C3", "C4"]
    assert summary["channel_selection_or_reordering_performed"] is False
    assert summary["unvalidated_subjects"] == ["sub-28"]
    assert summary["subject_count"] == 2 and summary["total_trials"] == 10
    assert summary["whole_dataset_validated"] is False
    assert summary["training_performed"] is False


def test_summary_rejects_pseudoreplicated_or_failed_participants():
    first = audit_row()
    with pytest.raises(ValueError, match="Duplicate audited"):
        MODULE.cohort_summary([first, copy.deepcopy(first)], ["sub-27"])
    other = audit_row("sub-29")
    with pytest.raises(ValueError, match="Duplicate original"):
        MODULE.cohort_summary([first, other], ["sub-27", "sub-29"])
    first["summary"]["all_checks_pass"] = False
    with pytest.raises(ValueError, match="failed"):
        MODULE.cohort_summary([first], ["sub-27"])
