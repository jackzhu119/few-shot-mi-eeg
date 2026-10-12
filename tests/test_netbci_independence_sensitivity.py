"""Software source-copy fixtures; no real EEG or model fitting."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_netbci_independence_sensitivity import cross_subject_affected_identities


def identity_fixture():
    return {
        "subject_order": ["sub-1", "sub-2", "sub-7", "sub-11", "sub-19"],
        "continuous_duplicate_groups": [
            {"subjects": ["sub-7", "sub-1"], "cross_subject": True},
            {"subjects": ["sub-2"], "cross_subject": False}],
        "task_window_duplicate_groups": [
            {"subjects": ["sub-11", "sub-19"], "cross_subject": True},
            {"subjects": ["sub-2"], "cross_subject": False}],
    }


def test_window_only_cross_identity_copies_exclude_all_members_in_source_scope_order():
    identity = identity_fixture()
    assert cross_subject_affected_identities(identity) == ["sub-1", "sub-7", "sub-11", "sub-19"]
    # Whole-run-only filtering would wrongly retain the last two identities.
    assert identity["continuous_duplicate_groups"][0]["subjects"] == ["sub-7", "sub-1"]


def test_within_identity_repeats_are_reportable_but_do_not_fabricate_another_identity():
    identity = identity_fixture()
    identity["continuous_duplicate_groups"] = [identity["continuous_duplicate_groups"][1]]
    identity["task_window_duplicate_groups"] = [identity["task_window_duplicate_groups"][1]]
    assert cross_subject_affected_identities(identity) == []


@pytest.mark.parametrize("field", ["continuous_duplicate_groups", "task_window_duplicate_groups"])
@pytest.mark.parametrize("error", ["scope", "cross_flag"])
def test_wrong_duplicate_identity_scope_or_cross_flag_is_rejected(field, error):
    identity = identity_fixture()
    if error == "scope":
        identity[field][0]["subjects"].append("unverified_ID")
    else:
        identity[field][0]["cross_subject"] = False
    with pytest.raises(ValueError, match="scope/cross-subject"):
        cross_subject_affected_identities(identity)
