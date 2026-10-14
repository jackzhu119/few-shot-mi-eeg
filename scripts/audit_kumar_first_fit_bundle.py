"""Independently audit received first-fit archives; no model fitting or EEG loading."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import subprocess
import tarfile
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "d4d2a64bb16e5f3841ecdefeb188fd8b9a121c71"
FIT_SHA = "2a4d0dd291f1f93bc0560e39b99b2e76fbf6bcba0d3a363ceb522fb4afea0f62"
LOG_SHA = "ad73258ad41c7f7f64508ac27d5726a99d56123faf339386ab8c925048222905"
RESULT_KEY = (
    "few-shot-mi-eeg/experiments/kumar2024/gpu-source-20261014/sub-1-seed-20261012-run01.tar"
)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def git_bytes(name):
    return subprocess.check_output(["git", "show", f"{COMMIT}:{name}"], cwd=ROOT)


def archive(path, expected_sha, expected_size, count):
    raw = path.read_bytes()
    assert len(raw) == expected_size and sha(raw) == expected_sha, "Archive identity mismatch"
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        assert len(names) == len(set(names)) == count + 1
        assert all(
            m.isfile() and not m.name.startswith("/") and ".." not in Path(m.name).parts
            for m in members
        )
        data = {m.name: tar.extractfile(m).read() for m in members}
    manifest = json.loads(data["manifest.json"])
    entries = manifest["files"]
    assert len(entries) == count and {e["path"] for e in entries} == set(data) - {"manifest.json"}
    for entry in entries:
        value = data[entry["path"]]
        assert len(value) == entry["bytes"] and sha(value) == entry["sha256"]
    return manifest, data


def audit(fit_path, dispatch_path):
    manifest, data = archive(fit_path, FIT_SHA, 143360, 11)
    outer, logs = archive(dispatch_path, LOG_SHA, 20480, 4)
    assert manifest["expected_R2_key"] == RESULT_KEY
    assert outer["result_archive_sha256"] == FIT_SHA
    fit, weights, config, inputs, download = [
        json.loads(data[n])
        for n in [
            "fit_result.json",
            "weights.json",
            "training_config.json",
            "input_audit.json",
            "download_receipt.json",
        ]
    ]
    assert data["training_config.json"] == git_bytes(
        "configs/kumar_eegnet_gpu_development_20261014.json"
    )
    assert data["relay_contract.json"] == git_bytes("configs/kumar_parent_relay_20261014.json")
    assert sha(data["training_config.json"]) == fit["training_config_sha256"]
    assert sha(data["relay_contract.json"]) == fit["relay_contract_sha256"]
    for received, source in [
        ("run_source.py", "scripts/run_kumar_parent_first_fit.py"),
        ("train_source.py", "scripts/train_kumar_eegnet.py"),
        ("adapter_source.py", "src/learning_preserving_bci/datasets/kumar.py"),
    ]:
        assert data[received] == git_bytes(source)
    assert fit["provenance"]["git_commit"] == COMMIT and fit["provenance"]["git_dirty"] is False
    for name, expected in fit["provenance"]["source_config_sha256"].items():
        assert sha(git_bytes(name)) == expected
    assert fit["subject"] == "sub-1" and fit["seed"] == weights["seed"] == 20261012
    assert fit["synthetic"] is False and weights["synthetic"] is False
    assert weights["software_validation_only"] is False
    assert (
        fit["query_rows_loaded"] == 0
        and fit["source_train_rows"] == 40
        and fit["source_validation_rows"] == 20
    )
    assert weights["config"] == config
    assert (
        sha(json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
        == weights["config_canonical_sha256"]
    )
    split = json.loads(git_bytes(config["split_manifest"]))
    assert (
        sha(git_bytes(config["split_manifest"]))
        == "ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28"
    )
    expected = {}
    for role in ["source_train", "source_validation"]:
        rows = [
            t
            for t in split["trials"]
            if t["subject"] == "sub-1" and t["role"] == role and t["included"]
        ]
        expected[role] = {t["trial_id"] for t in rows}
        actual = weights[role + "_ids"]
        assert len(actual) == len(set(actual)) and set(actual) == expected[role]
        assert all(t["session"] == "ses-0" for t in rows)
    assert not expected["source_train"] & expected["source_validation"]
    assert len(expected["source_train"]) == 40 and len(expected["source_validation"]) == 20
    assert inputs["subject"] == "sub-1" and inputs["cohort"] == "development"
    assert (
        inputs["source_events"] == inputs["included_trials"] == 60
        and inputs["excluded_trials"] == 0
    )
    assert len(inputs["runs"]) == 3 and {r["role"] for r in inputs["runs"]} == {
        "source_train",
        "source_validation",
    }
    plan = json.loads(git_bytes("configs/kumar_first_fit_https_20261014.json"))
    pinned = {e["path"]: e for e in plan["files"]}
    assert download["status"] == "all_25_full_sha256_verified" and len(download["records"]) == 25
    assert download["config_sha256"] == sha(
        git_bytes("configs/kumar_first_fit_https_20261014.json")
    )
    assert {r["path"] for r in download["records"]} == set(pinned)
    for row in download["records"]:
        assert row["sha256"] == pinned[row["path"]]["expected_sha256"]
        assert row["status"] in {"downloaded_sha256_verified", "reused_sha256_verified"}
    for path, value in inputs["verified_source_files"].items():
        assert value["sha256"] == pinned[path]["expected_sha256"]
        assert value["official_checksum"] == pinned[path]["checksum"]
    history = weights["history"]
    assert [r["epoch"] for r in history] == list(range(1, len(history) + 1))
    assert all(
        math.isfinite(r[k])
        for r in history
        for k in ["source_train_loss", "source_validation_loss"]
    )
    best, selected, stale, stopped = float("inf"), None, 0, None
    settings = config["optimization"]["early_stopping"]
    for row in history:
        loss = row["source_validation_loss"]
        if loss < best - settings["min_delta"]:
            best, selected, stale = loss, row["epoch"], 0
        else:
            stale += 1
        if stale >= settings["patience"]:
            stopped = row["epoch"]
            break
    assert selected == weights["selected_epoch"] == fit["selected_epoch"] == 26
    assert best == weights["source_validation_loss"]
    assert stopped == len(history) == fit["epochs_executed"] == 41
    assert (
        fit["optimizer_steps"]
        == weights["optimizer_steps"]
        == 41 * math.ceil(40 / config["optimization"]["batch_size"])
        == 123
    )
    assert sha(data["weights.pt"]) == weights["checkpoint_sha256"] == fit["checkpoint_sha256"]
    payload = torch.load(io.BytesIO(data["weights.pt"]), map_location="cpu", weights_only=True)
    assert set(payload) == {
        "model_state_dict",
        "channel_mean",
        "channel_scale",
        "classes",
        "context_utf8",
    }
    context = json.loads(bytes(payload["context_utf8"].tolist()).decode())
    assert context == {k: v for k, v in weights.items() if k != "checkpoint_sha256"}
    tensors = dict(payload["model_state_dict"])
    tensors.update(
        channel_mean=payload["channel_mean"],
        channel_scale=payload["channel_scale"],
        classes=payload["classes"],
    )
    h = hashlib.sha256()
    for name, value in sorted(tensors.items()):
        assert torch.isfinite(value).all()
        array = value.detach().cpu().contiguous().numpy()
        h.update(name.encode())
        h.update(str(array.dtype).encode())
        h.update(json.dumps(array.shape).encode())
        h.update(array.tobytes())
    assert h.hexdigest() == weights["frozen_state_sha256"]
    assert (
        tuple(payload["channel_mean"].shape) == tuple(payload["channel_scale"].shape) == (1, 22, 1)
    )
    assert (payload["channel_scale"] > 0).all() and payload["classes"].tolist() == [0, 1]
    dispatch = logs["paper2-install-90f674f/dispatch-d4d2a64-first-fit-run01.log"].decode()
    assert "2026-10-14T10:45:18Z" in dispatch and "2026-10-14T10:45:29Z" in dispatch
    assert "FIRST_FIT_DISPATCH_EXIT_CODE=75" in dispatch
    launch = json.loads(logs["paper2-results/kumar-first-fit-launch-run01.log"])
    assert launch["archive_sha256"] == FIT_SHA and launch["archive_bytes"] == 143360
    assert launch["status"] == "fit_finished_backup_pending"
    assert data["training.log"] == b"", "Do not invent missing text logs"
    return {
        "status": "independent_archive_protocol_checkpoint_audit_passed",
        "source_commit": COMMIT,
        "fit_archive_sha256": FIT_SHA,
        "dispatch_archive_sha256": LOG_SHA,
        "fit_members_verified": 11,
        "dispatch_members_verified": 4,
        "expected_R2_key": RESULT_KEY,
        "subject": "sub-1",
        "seed": 20261012,
        "source_train_rows": 40,
        "source_validation_rows": 20,
        "query_rows_loaded_by_audit": 0,
        "query_rows_loaded_reported_by_fit": 0,
        "epochs_executed": 41,
        "selected_epoch": 26,
        "optimizer_steps": 123,
        "selected_source_validation_cross_entropy": best,
        "runtime_seconds_reported": fit["runtime_seconds"],
        "peak_cuda_memory_bytes_reported": fit["peak_cuda_memory_bytes"],
        "dispatch_start_utc": "2026-10-14T10:45:18Z",
        "dispatch_end_utc": "2026-10-14T10:45:29Z",
        "dispatch_exit_code": 75,
        "checkpoint_sha256": weights["checkpoint_sha256"],
        "checkpoint_state_sha256": h.hexdigest(),
        "training_log_bytes": 0,
        "epoch_evidence": "41-row history bound inside weights.pt and matching weights.json; empty training.log preserved unchanged",
        "audit_methods": [
            "full archive/member hashes",
            "Git snapshot comparison",
            "frozen trial-ID set comparison",
            "independent earliest-minimum/patience recomputation",
            "torch weights_only CPU load and independent state hash",
        ],
        "limitations": [
            "No model refit or prediction replay performed",
            "Recorded losses not recomputed from EEG",
            "Single development participant/seed; no query decoding performance or cohort inference",
            "Device memory/time are execution-reported values, not independent billing",
        ],
        "parent_acknowledgement": "pending",
        "platform_stop_status": "not_checked_no_stop_executed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--dispatch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve existing audit")
    result = audit(args.fit, args.dispatch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
