"""Focused protections for source-only descriptive saved-result aggregation."""

import importlib.util
import io
import tarfile
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "saved_results", Path(__file__).parents[1] / "scripts/aggregate_kumar_development_saved_results.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_balanced_accuracy_preserves_collapsed_predictions_and_both_class_recalls():
    result, _ = MODULE.describe_logits([[2, 0], [2, 0], [2, 0], [2, 0]], [0, 0, 0, 1])
    assert result["source_validation_accuracy"] == 0.75
    assert result["source_validation_balanced_accuracy"] == 0.5
    assert result["single_class_prediction"] is True
    assert result["right_recall"] == 0


def test_participant_aggregation_includes_all_seeds_and_rejects_missing_duplicate_seeds():
    rows = []
    for subject, scores in (("a", [0.4, 0.5, 0.9]), ("b", [0.5, 0.5, 0.5])):
        for seed, score in zip([1, 2, 3], scores):
            rows.append({"subject": subject, "seed": seed, "source_validation_CE_recorded": 0.7,
                         "source_validation_balanced_accuracy": score,
                         "source_validation_accuracy": score, "single_class_prediction": False,
                         "epochs": 2, "optimizer_steps": 6})
    participants = MODULE.aggregate_participants(rows, ["a", "b"], [1, 2, 3])
    assert participants[0]["mean_source_validation_balanced_accuracy"] == pytest.approx(0.6)
    assert np.mean([p["mean_source_validation_balanced_accuracy"] for p in participants]) \
        == pytest.approx(0.55)
    with pytest.raises(ValueError, match="Incomplete"):
        MODULE.aggregate_participants(rows[:-1], ["a", "b"], [1, 2, 3])
    rows[-1] = rows[-2]
    with pytest.raises(ValueError, match="Duplicate"):
        MODULE.aggregate_participants(rows, ["a", "b"], [1, 2, 3])


def test_nonfinite_or_one_class_saved_labels_fail_closed():
    with pytest.raises(ValueError, match="Nonfinite"):
        MODULE.describe_logits([[np.nan, 1], [0, 1]], [0, 1])
    with pytest.raises(ValueError, match="missing binary"):
        MODULE.describe_logits([[0, 1], [0, 1]], [0, 0])


def test_archive_hash_and_unsafe_member_fail_before_prediction_access(tmp_path):
    path = tmp_path / "original.tar"
    with tarfile.open(path, "w") as archive:
        member = tarfile.TarInfo("../source_validation_predictions.npz")
        member.size = 1
        archive.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="SHA256"):
        MODULE.read_verified_archive(path, "0" * 64)
    with pytest.raises(ValueError, match="Unsafe"):
        MODULE.read_verified_archive(path, MODULE.sha256(path.read_bytes()))
