"""Audit immutable replay archives and independently recompute CE from saved logits."""

import argparse
import io
import json
from pathlib import Path

import numpy as np

from audit_kumar_first_fit_bundle import archive, sha

ROOT = Path(__file__).resolve().parents[1]
REPLAY_SHA = "394b934c18c1d814fa46de7d6f0e6bb82311be62205c310b9fdef8675841ea71"
DISPATCH_SHA = "7396bfed6aefd58485175ee0e84dbd29fa6d62762c843846c0b6d073710a0f36"


def audit(replay_path, dispatch_path, output):
    manifest, data = archive(replay_path, REPLAY_SHA, 51200, 5)
    _, external = archive(dispatch_path, DISPATCH_SHA, 71680, 3)
    assert external["kumar-first-fit-replay-run01.tar"] == replay_path.read_bytes()
    report = json.loads(data["replay_result.json"])
    weights = json.loads(data["weights.json"])
    old = ROOT / "research_logs/kumar_first_gpu_fit_20261014"
    original = json.loads((old / "independent_audit.json").read_text())
    assert sha(data["weights.pt"]) == original["checkpoint_sha256"]
    assert data["weights.json"] == (old / "fit_text_evidence/weights.json").read_bytes()
    assert report["frozen_state_sha256"] == original["checkpoint_state_sha256"]
    contract = json.loads((ROOT / "configs/kumar_first_fit_replay_20261014.json").read_text())
    assert report["replay_contract_sha256"] == sha(
        (ROOT / "configs/kumar_first_fit_replay_20261014.json").read_bytes()
    )
    assert report["replay_script_sha256"] == sha(
        (ROOT / "scripts/replay_kumar_first_fit.py").read_bytes()
    )
    assert report["git_commit"] == "30e68e3dcdd2e2217e9c51bbdd84a6af4e568640"
    assert manifest["exit_code"] == 0
    assert report["status"] == "source_checkpoint_independent_replay_passed"
    assert all(report[k] == 0 for k in ("fits", "optimizer_steps", "query_rows_loaded"))
    assert report["normalization_bitwise_equal"] and report["input_audit_equal"]
    with np.load(io.BytesIO(data["source_validation_predictions.npz"]), allow_pickle=False) as n:
        assert set(n.files) == {"logits", "labels", "loss_float64", "trial_ids"}
        logits, labels = n["logits"].astype(np.float64), n["labels"]
        ids = n["trial_ids"].tolist()
        assert ids == weights["source_validation_ids"] and logits.shape == (20, 2)
        split = json.loads((ROOT / weights["config"]["split_manifest"]).read_text())
        selected = {x["trial_id"]: x for x in split["trials"] if x["trial_id"] in ids}
        assert len(selected) == 20
        expected_labels = [
            weights["config"]["input"]["class_mapping"][selected[x]["label"]] for x in ids
        ]
        assert labels.tolist() == expected_labels
        assert all(
            selected[x]["role"] == "source_validation" and selected[x]["subject"] == "sub-1"
            for x in ids
        )
        # NumPy logaddexp supplies an independent stable two-class formula.
        losses = np.logaddexp(logits[:, 0], logits[:, 1]) - logits[np.arange(20), labels]
        assert np.isfinite(losses).all()
        assert np.max(np.abs(losses - n["loss_float64"])) < 1e-14
    expected = original["selected_source_validation_cross_entropy"]
    assert report["expected_loss"] == weights["source_validation_loss"] == expected
    assert abs(float(losses.mean()) - expected) <= contract["loss_absolute_tolerance"]
    assert abs(float(losses.mean()) - report["independent_numpy_loss"]) < 1e-14
    assert report["torch_absolute_error"] == abs(report["replay_torch_loss"] - expected) == 0
    log = external["dispatch-replay-run01.log"].decode()
    for text in (
        "2026-10-14T11:07:17Z",
        "2026-10-14T11:07:22Z",
        "REPLAY_DISPATCH_EXIT_CODE=0",
        REPLAY_SHA,
    ):
        assert text in log
    output.mkdir(parents=True, exist_ok=False)
    for name in ("replay_result.json", "manifest.json", "kumar-first-fit-replay-run01.log"):
        (output / name).write_bytes(data[name])
    for name in ("dispatch-replay-run01.sh", "dispatch-replay-run01.log"):
        (output / name).write_bytes(external[name])
    result = dict(
        status="independent_replay_archive_audit_passed",
        replay_archive_sha256=REPLAY_SHA,
        dispatch_archive_sha256=DISPATCH_SHA,
        verified_replay_members=5,
        verified_dispatch_members=3,
        checkpoint_identical_to_first_fit=True,
        source_validation_rows=20,
        frozen_trial_ids_and_labels_match=True,
        expected_loss=expected,
        recomputed_numpy_loss=float(losses.mean()),
        absolute_error=abs(float(losses.mean()) - expected),
        preregistered_absolute_tolerance=contract["loss_absolute_tolerance"],
        replay_model_state_unchanged_reported=True,
        audit_refits=0,
        audit_EEG_loaded=False,
        scope="Independent archive/config/checkpoint identity and saved-logit CE verification; actual EEG forward replay executed on Pod, not repeated on Codex",
        parent_receipt_acknowledgement_pending=True,
        stop_Pod=False,
    )
    (output / "independent_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--dispatch", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    audit(a.replay, a.dispatch, a.output)
