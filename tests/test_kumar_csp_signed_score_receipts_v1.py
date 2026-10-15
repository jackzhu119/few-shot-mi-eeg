"""Mocked completion/early-rejection guards; no real diagnostic or model load."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "csp_signed_receipt_consumer",
    Path(__file__).parents[1] / "scripts/analyze_kumar_csp_signed_score_v1.py",
)
consumer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consumer)


@pytest.fixture
def mocked_main(tmp_path, monkeypatch):
    """Exercise real orchestration/receipt code with every scientific operation replaced."""
    config, baseline_receipt = tmp_path / "config.json", tmp_path / "baseline.json"
    config.write_text(json.dumps({"plan_sha256": "f" * 64}))
    baseline_receipt.write_text("{}")
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "consumer", "--epochs", str(tmp_path / "opaque-epochs"),
        "--baseline-root", str(tmp_path / "opaque-baseline"),
        "--baseline-r2-receipt", str(baseline_receipt),
        "--config", str(config), "--output", str(output),
    ])

    def forbidden(*args, **kwargs):
        raise AssertionError("Real arrays, estimator construction or fits are forbidden")

    monkeypatch.setattr(consumer.np, "load", forbidden)
    monkeypatch.setattr(consumer, "make_csp_lda", forbidden)
    monkeypatch.setattr(consumer, "StandardScaler", forbidden)
    monkeypatch.setattr(consumer, "validate_config", lambda config: [])
    metadata = [{"trial_id": f"synthetic-source-{value}"} for value in range(40)]
    monkeypatch.setattr(consumer, "load_restricted_subject", lambda folder, subject: (
        np.ones((40, 2)), np.tile([0, 1], 20), metadata, [],
    ))
    monkeypatch.setattr(consumer, "chronological_indices", lambda *args: np.arange(40))
    monkeypatch.setattr(consumer, "load_verified_source_model", lambda *args: ({}, {"inputs": []}))
    original_write_json = consumer.write_json

    def mark_synthetic(path, value):
        # The real consumer always expects real scientific inputs. Mark artifacts
        # produced by this entirely mocked orchestration as software fixtures.
        original_write_json(path, {**value, "synthetic": True, "software_validation_only": True})

    monkeypatch.setattr(consumer, "write_json", mark_synthetic)
    calls = []

    def run(*, failed_subject=None, interrupt_subject=None):
        def fake_measure(X, labels, metadata, subject, arrays, audit, folder):
            calls.append(subject)
            if subject == interrupt_subject:
                raise RuntimeError("Synthetic interrupted subject; preserve prior files")
            folder.mkdir()
            (folder / "synthetic_marker.json").write_text(
                json.dumps({"synthetic": True, "software_validation_only": True}))
            failures = int(subject == failed_subject)
            return {
                "synthetic": True,
                "source_twofold_balanced_accuracy": None if failures else .5,
                "source_phase_alignment_control": {
                    "pipeline_fit_attempts": 40,
                    "pipeline_fit_successes": 40 - failures,
                    "pipeline_fit_failures": failures,
                    "nominal_csp_and_lda_estimator_fit_attempts": 80,
                    "heldout_prediction_rows": (40 - failures) * 20,
                    "shared_shift_pairs_sha256": "e" * 64,
                },
                "support_rows": [{"observed": {"support_split_half_direction_cosine": 0.0}}
                                 for _ in range(5)],
            }
        monkeypatch.setattr(consumer, "analyze_subject", fake_measure)
        consumer.main()
        return json.loads((output / "measurement_receipt.json").read_text())

    return output, calls, run


@pytest.mark.parametrize("failed_subject", [None, 7])
def test_main_receipt_requires_six_subjects_and_distinguishes_failures(mocked_main, failed_subject):
    output, calls, run = mocked_main
    receipt = run(failed_subject=failed_subject)
    assert calls == [1, 4, 7, 10, 13, 16]
    assert len(receipt["subjects"]) == 6
    assert receipt["synthetic"] is receipt["software_validation_only"] is True
    assert len(list(output.glob("sub-*/synthetic_marker.json"))) == 6
    assert receipt["pipeline_fit_attempts"] == 240
    assert receipt["pipeline_fit_failures"] == int(failed_subject is not None)
    assert receipt["pipeline_fit_successes"] == 240 - int(failed_subject is not None)
    assert receipt["joint_shift_twofold_rows"] == 2400
    assert receipt["query_rows_used"] == receipt["final_subjects_opened"] == 0
    if failed_subject is None:
        assert receipt["status"] == "completed_exploratory_measurement"
        assert receipt["participant_summaries"]["source_twofold_balanced_accuracy"]["status"] == "completed"
    else:
        assert receipt["status"] == "completed_with_explicit_source_fit_failures"
        summary = receipt["participant_summaries"]["source_twofold_balanced_accuracy"]
        assert summary["status"] == "unavailable_missing_participant_value"
        assert summary["missing_participant_count"] == 1
        assert summary["mean"] is None
        assert len(summary["participant_values"]) == 6


def test_interrupted_sixth_subject_preserves_partial_evidence_without_final_receipt(mocked_main):
    output, calls, run = mocked_main
    with pytest.raises(RuntimeError, match="Synthetic interrupted"):
        run(interrupt_subject=16)
    assert calls == [1, 4, 7, 10, 13, 16]
    assert len(list(output.glob("sub-*/synthetic_marker.json"))) == 5
    assert not (output / "measurement_receipt.json").exists()


@pytest.mark.parametrize("change", [
    "final_subject", "pending_receipt", "head_only", "missing_identity",
    "duplicate_identity", "unverified", "get_503", "bytes", "sha256",
])
def test_source40_invalid_backup_rejected_before_array_deserialization(tmp_path, monkeypatch, change):
    rows = []
    for name in ("source_before.npz", "source_after.npz", "participant_receipt.json", "fit_access_audit.json"):
        path = tmp_path / name
        path.write_bytes(b"SYNTHETIC OPAQUE BYTES; NEVER DECODED")
        rows.append({"relative_path": f"sub-1/{name}", "bytes": path.stat().st_size,
                     "sha256": consumer.file_digest(path), "readback_bytes": path.stat().st_size,
                     "verification": "full_get_sha256_verified", "head_http_status": 200,
                     "get_http_status": 200})
    receipt = {"status": "completed", "readback_mode": "all", "files": rows}
    subject = 2 if change == "final_subject" else 1
    if change == "pending_receipt":
        receipt["status"] = "pending"
    elif change == "head_only":
        receipt["readback_mode"] = "head"
    elif change == "missing_identity":
        rows.pop(0)
    elif change == "duplicate_identity":
        rows.append(dict(rows[0]))
    elif change == "unverified":
        rows[0]["verification"] = "head_only"
    elif change == "get_503":
        rows[0]["get_http_status"] = 503
    elif change == "bytes":
        rows[0]["readback_bytes"] -= 1
    elif change == "sha256":
        rows[0]["sha256"] = "0" * 64
    loads = []

    def forbidden(*args, **kwargs):
        loads.append(args)
        raise AssertionError("Invalid provenance must fail before numerical deserialization")

    monkeypatch.setattr(consumer.np, "load", forbidden)
    with pytest.raises(ValueError):
        consumer.load_verified_source_model(tmp_path, subject, None, None, [], receipt)
    assert loads == []
