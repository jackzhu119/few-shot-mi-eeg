"""Metadata-only scope and authorization tests, without importing Torch."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "reuse_proposal", Path(__file__).parents[1] / "scripts/check_kumar_checkpoint_reuse_proposal.py"
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


@pytest.fixture
def proposal():
    return json.loads(checker.DEFAULT.read_text())


def test_actual_proposal_stays_metadata_only_and_closed(proposal):
    result = checker.check(proposal)
    assert result["accepted_checkpoints"] == 18
    assert result["future_source_fits_proposed"] == 36
    assert result["new_fits_authorized"] == 0
    assert not result["checkpoint_tensors_loaded"] and not result["signals_loaded"]
    stages = proposal["stage_binding_applicability"]
    assert checker.MISSING[-1] not in stages["remaining36_source_fits"]["requires"]
    assert checker.MISSING[4] not in stages["existing18_source_validation_replay"]["requires"]


@pytest.mark.parametrize("field", ["new_fits", "query", "real_source_validation_replay"])
def test_execution_permission_cannot_be_opened_in_this_proposal(proposal, field):
    proposal["execution_permissions"][field] = True
    with pytest.raises(ValueError, match="remain closed"):
        checker.check(proposal)


def test_changed_ledger_hash_fails_before_reading_checkpoint_inventory(proposal):
    proposal["pinned_inputs"]["accepted_ledger"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Pinned input changed"):
        checker.check(proposal)


@pytest.mark.parametrize("change", ["seed", "refit", "deadline", "strategy"])
def test_no_seed_selection_refit_deadline_reset_or_strategy_release(proposal, change):
    altered = copy.deepcopy(proposal)
    if change == "seed":
        altered["remaining_source_training_proposal"]["seeds"] = [20261014]
    elif change == "refit":
        altered["reuse"]["new_fits"] = 1
    elif change == "deadline":
        altered["remaining_source_training_proposal"]["new_run_total_wall_seconds"] = 19800
    else:
        altered["scientific_decision"]["adaptive_strategy_supported"] = True
    with pytest.raises(ValueError):
        checker.check(altered)
