"""Synthetic integrity tests for text-only submission-stage postprocessing."""

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_kumar_saved_training_curves import (  # noqa: E402
    check_history,
    digest,
    run,
    verified_text_archive,
)


def synthetic_history(losses, maximum=100, patience=2):
    history = [{"epoch": number, "source_train_loss": 0.7,
                "source_validation_loss": loss} for number, loss in enumerate(losses, 1)]
    selected = min(range(len(losses)), key=losses.__getitem__) + 1
    weights = {"history": history, "selected_epoch": selected,
               "source_validation_loss": min(losses), "optimizer_steps": 3 * len(losses)}
    fit = {"selected_epoch": selected, "epochs_executed": len(losses),
           "optimizer_steps": 3 * len(losses)}
    config = {"optimization": {"max_epochs": maximum, "early_stopping": {
        "patience": patience, "min_delta": 0, "ties": "earliest_epoch"}}}
    return weights, fit, config


def test_earliest_tie_and_patience_are_verified():
    weights, fit, config = synthetic_history([0.6, 0.6, 0.6])
    history, reason = check_history(weights, fit, config)
    assert len(history) == 3 and weights["selected_epoch"] == 1 and reason == "patience_2"


def test_continued_training_after_patience_is_rejected():
    with pytest.raises(ValueError, match="continued"):
        check_history(*synthetic_history([0.6, 0.6, 0.6, 0.5]))


def test_incorrect_checkpoint_selection_is_rejected():
    weights, fit, config = synthetic_history([0.6, 0.6, 0.6])
    weights["selected_epoch"] = fit["selected_epoch"] = 2
    with pytest.raises(ValueError, match="selection"):
        check_history(weights, fit, config)


def test_truncated_history_is_not_called_a_complete_curve():
    with pytest.raises(ValueError, match="stopping reason"):
        check_history(*synthetic_history([0.7, 0.6]))


def make_archive(path, unsafe=False):
    payload = {"weights.json": b"{}", "fit_result.json": b"{}", "training_config.json": b"{}",
               "training.log": b"", "weights.pt": b"binary-only-never-loaded"}
    if unsafe:
        payload["../escape"] = b"unsafe"
    manifest = {"files": [{"path": name, "bytes": len(raw), "sha256": digest(raw)}
                           for name, raw in payload.items()]}
    payload["manifest.json"] = json.dumps(manifest).encode()
    with tarfile.open(path, "w") as archive:
        for name, raw in payload.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return digest(path.read_bytes())


def test_binary_members_are_verified_but_not_returned_or_loaded(tmp_path):
    path = tmp_path / "synthetic.tar"
    expected = make_archive(path)
    text, evidence = verified_text_archive(path, expected)
    assert "weights.pt" not in text and evidence["payload_members"] == 5
    assert evidence["text_member_sha256"]["weights.json"] == digest(b"{}")


def test_archive_hash_and_unsafe_paths_fail_closed(tmp_path):
    path = tmp_path / "synthetic.tar"
    expected = make_archive(path, unsafe=True)
    with pytest.raises(ValueError, match="archive differs"):
        verified_text_archive(path, "0" * 64)
    with pytest.raises(ValueError, match="Unsafe"):
        verified_text_archive(path, expected)


def test_existing_output_is_preserved_before_any_input_read(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(ValueError, match="Output exists"):
        run(output, tmp_path / "no-archives")
