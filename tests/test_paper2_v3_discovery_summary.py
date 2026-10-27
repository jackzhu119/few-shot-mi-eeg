"""Participant aggregation must not turn repeated seeds into sample size."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest


spec = importlib.util.spec_from_file_location(
    "v3_discovery_summary",
    Path(__file__).parents[1] / "scripts/summarize_paper2_v3_discovery_20261027.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def cells():
    return [
        dict(family="neural", source_regime="reuse_v2", variant="core", method="frozen",
             budget="20", participant=p, session=session, seed=seed,
             status="ok", synthetic="False", balanced_accuracy=str((index + 1) / 10))
        for index, p in enumerate(module.PARTICIPANTS)
        for session in sorted(module.SESSIONS)
        for seed in sorted(module.SEEDS)
    ]


def test_seed_and_session_repetitions_leave_six_independent_endpoints():
    endpoints, sessions = module.aggregate(cells())
    assert len(endpoints) == 6
    assert len(sessions) == 30
    assert sorted(endpoints.values()) == pytest.approx(np.arange(1, 7) / 10)


@pytest.mark.parametrize("remove", ["seed", "session", "participant"])
def test_incomplete_endpoints_cannot_silently_become_complete_case(remove):
    rows = cells()
    first = rows[0]
    fields = {"seed": ("participant", "session", "seed"),
              "session": ("participant", "session"),
              "participant": ("participant",)}[remove]
    rows = [r for r in rows if any(r[k] != first[k] for k in fields)]
    with pytest.raises(ValueError, match="incomplete|Missing/extra"):
        module.aggregate(rows)


def test_duplicate_cell_rejected_instead_of_changing_weight():
    rows = cells()
    with pytest.raises(ValueError, match="Duplicate"):
        module.aggregate(rows + [dict(rows[0])])


def test_contrast_uses_paired_participant_not_session_variance():
    endpoints, _ = module.aggregate(cells())
    left = ("neural", "reuse_v2", "core", "updated", 20)
    right = ("neural", "reuse_v2", "core", "frozen", 20)
    for p in module.PARTICIPANTS:
        endpoints[left + (p,)] = endpoints[right + (p,)] + 0.02
    row = module.contrast(endpoints, left, right, "synthetic_software_validation")
    assert row["n_participants"] == 6
    assert row["mean_difference_pp"] == pytest.approx(2)
    assert row["ci_low_pp"] == pytest.approx(2)
    assert row["ci_high_pp"] == pytest.approx(2)
