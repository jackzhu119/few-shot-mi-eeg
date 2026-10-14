"""Exactly one frozen development fit; local success remains backup-pending.

The parent relays the immutable bundle through private Library to Codex/R2.
No credentials, network calls, query EEG or instance shutdown occur here.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/kumar_parent_relay_20261014.json"
TRAINING = ROOT / "configs/kumar_eegnet_gpu_development_20261014.json"
JOB = "kumar-sub1-seed20261012-parent-relay-run01"
STATE = Path("/workspace/paper2-results/.kumar-first-fit-20261014.json")
LOCK = Path("/workspace/research-gpu.lock")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_gate():
    contract = json.loads(CONTRACT.read_text())
    if not (
        contract["ready_for_first_fit"]
        and contract["mandatory_R2_backup"]
        and contract["subject"] == "sub-1"
        and contract["seed"] == 20261012
        and contract["maximum_real_fits"] == 1
        and contract["query_access"] is False
    ):
        raise ValueError("First-fit transport/scope gate is closed")
    if digest(TRAINING) != contract["frozen_training_config_sha256"]:
        raise ValueError("Frozen scientific configuration changed")
    receipt_path = ROOT / contract["synthetic_checkpoint_acceptance_receipt"]
    if digest(receipt_path) != contract["synthetic_checkpoint_acceptance_sha256"]:
        raise ValueError("Checkpoint relay acceptance receipt changed")
    receipt = json.loads(receipt_path.read_text())
    totals = receipt["totals"]
    if (
        receipt["status"] != "completed"
        or totals["planned_files"] != 1
        or totals["failed_files"] != 0
        or totals["full_get_sha256_verified_files"] != 1
        or receipt["files"][0]["sha256"] != contract["synthetic_checkpoint_archive_sha256"]
        or receipt["files"][0]["verification"] != "full_get_sha256_verified"
    ):
        raise ValueError("Checkpoint-bearing R2 full-readback gate failed")
    return contract


def validate_inputs(data_root, receipt_path):
    from fetch_kumar_first_fit_https import load_plan, verify

    result = json.loads(receipt_path.read_text())
    plan = load_plan()
    if (
        result["status"] != "all_25_full_sha256_verified"
        or result["config_sha256"] != digest(ROOT / "configs/kumar_first_fit_https_20261014.json")
        or len(result["records"]) != 25
        or {e["path"] for e in result["records"]} != {e["path"] for e in plan["files"]}
    ):
        raise ValueError("First-fit input receipt incomplete or from another scope")
    for entry in plan["files"]:
        verify(data_root / entry["path"], entry)


def bundle(output):
    required = [
        "weights.pt",
        "weights.json",
        "fit_result.json",
        "training.log",
        "download_receipt.json",
        "training_config.json",
        "relay_contract.json",
        "input_audit.json",
        "run_source.py",
        "train_source.py",
        "adapter_source.py",
    ]
    if {p.name for p in output.iterdir()} != set(required):
        raise ValueError("Unexpected or missing evidence file; do not package secrets or extras")
    files = []
    for name in required:
        path = output / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Evidence must be regular files")
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    if sum(e["bytes"] for e in files) > 256 * 1024**2:
        raise ValueError("Bundle exceeds bounded evidence size")
    manifest = {
        "job": JOB,
        "status": "fit_finished_backup_pending",
        "synthetic": False,
        "expected_R2_key": check_gate()["expected_result_key"],
        "files": files,
        "R2_backup_verified": False,
        "parent_acknowledged": False,
    }
    archive = output.with_suffix(".tar")
    if archive.exists():
        with tarfile.open(archive) as tar:
            if json.load(tar.extractfile("manifest.json")) != manifest:
                raise ValueError("Existing archive differs; preserve both and investigate")
            if set(tar.getnames()) != set(required) | {"manifest.json"}:
                raise ValueError("Existing archive has unexpected members")
            for entry in files:
                value = tar.extractfile(entry["path"]).read()
                if (
                    len(value) != entry["bytes"]
                    or hashlib.sha256(value).hexdigest() != entry["sha256"]
                ):
                    raise ValueError("Existing archive content hash mismatch")
    else:
        with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as tar:
            for entry in files:
                value = (output / entry["path"]).read_bytes()
                info = tarfile.TarInfo(entry["path"])
                info.size = len(value)
                info.mode = 0o600
                info.mtime = 0
                tar.addfile(info, io.BytesIO(value))
            value = (json.dumps(manifest, indent=2) + "\n").encode()
            info = tarfile.TarInfo("manifest.json")
            info.size = len(value)
            info.mode = 0o600
            info.mtime = 0
            tar.addfile(info, io.BytesIO(value))
    return {
        "job": JOB,
        "status": "fit_finished_backup_pending",
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": digest(archive),
        "R2_backup_verified": False,
        "parent_acknowledged": False,
        "stop_Pod": False,
    }


def execute(data_root, receipt, output):
    import numpy as np
    import torch

    from learning_preserving_bci.datasets.kumar import load_subject
    from learning_preserving_bci.utils.reproducibility import collect_provenance
    from train_kumar_eegnet import SourceOnlyEEGNet, load_checkpoint, save_checkpoint, source_arrays

    contract = check_gate()
    validate_inputs(data_root, receipt)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no CPU fallback")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise ValueError("CUBLAS_WORKSPACE_CONFIG must be :4096:8 before Python starts")
    if STATE.exists():
        state = json.loads(STATE.read_text())
        if state.get("output") != str(output) or state.get("job") != JOB:
            raise ValueError("Existing fixed job belongs to another output; no second fit")
        if not (output / "fit_result.json").exists():
            raise RuntimeError(
                "Prior attempt incomplete; preserve and investigate, no automatic refit"
            )
        record = json.loads((output / "fit_result.json").read_text())
        if record["training_config_sha256"] != digest(TRAINING):
            raise ValueError("Prior fit configuration differs")
        load_checkpoint(output / "weights.pt", expected_sha256=record["checkpoint_sha256"])
        return bundle(output)
    if output.exists():
        raise FileExistsError("Existing unregistered output preserved")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with STATE.open("x") as stream:
        json.dump(
            {"job": JOB, "status": "reserved_no_automatic_refit", "output": str(output)}, stream
        )
    output.mkdir(parents=True, exist_ok=False)
    for source, name in [
        (TRAINING, "training_config.json"),
        (CONTRACT, "relay_contract.json"),
        (receipt, "download_receipt.json"),
        (Path(__file__), "run_source.py"),
        (ROOT / "scripts/train_kumar_eegnet.py", "train_source.py"),
        (ROOT / "src/learning_preserving_bci/datasets/kumar.py", "adapter_source.py"),
    ]:
        (output / name).write_bytes(source.read_bytes())
    config = json.loads(TRAINING.read_text())
    torch.set_num_threads(config["threads"])
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    with (
        (output / "training.log").open("x") as log,
        contextlib.redirect_stdout(log),
        contextlib.redirect_stderr(log),
    ):
        subject = load_subject(
            data_root,
            "sub-1",
            ROOT / config["protocol_config"],
            split_manifest=ROOT / config["split_manifest"],
            allowed_roles={"source_train", "source_validation"},
        )
        source = source_arrays(subject)
        if (len(source[0]), len(source[2])) != (40, 20):
            raise ValueError("Frozen first-fit source counts changed")
        (output / "input_audit.json").write_text(json.dumps(subject.provenance, indent=2) + "\n")
        model = SourceOnlyEEGNet(config, 20261012).fit_source(*source)
        saved = save_checkpoint(
            model, output / "weights.pt", synthetic=False, software_validation_only=False
        )
        restored = load_checkpoint(
            output / "weights.pt", expected_sha256=saved["checkpoint_sha256"]
        )
        if not np.array_equal(model.predict_proba(source[2]), restored.predict_proba(source[2])):
            raise RuntimeError("Source validation checkpoint replay failed")
        torch.cuda.synchronize()
        record = {
            "job": JOB,
            "status": "fit_finished_backup_pending",
            "synthetic": False,
            "subject": "sub-1",
            "seed": 20261012,
            "query_rows_loaded": 0,
            "source_train_rows": 40,
            "source_validation_rows": 20,
            "checkpoint_sha256": saved["checkpoint_sha256"],
            "training_config_sha256": digest(TRAINING),
            "relay_contract_sha256": digest(CONTRACT),
            "selected_epoch": model.selected_epoch_,
            "epochs_executed": len(model.history_),
            "optimizer_steps": model.optimizer_steps_,
            "runtime_seconds": time.monotonic() - started,
            "peak_cuda_memory_bytes": torch.cuda.max_memory_allocated(),
            "provenance": collect_provenance(20261012, ROOT),
            "mandatory_R2_backup": contract["mandatory_R2_backup"],
            "R2_backup_verified": False,
            "parent_acknowledged": False,
        }
        (output / "fit_result.json").write_text(
            json.dumps(record, indent=2, allow_nan=False) + "\n"
        )
    return bundle(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--download-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/workspace/paper2-results") / JOB)
    parser.add_argument("--execute-first-fit", action="store_true")
    args = parser.parse_args()
    check_gate()
    if not args.execute_first_fit:
        print(json.dumps({"status": "plan_only", "job": JOB, "fits": 1, "query_access": False}))
        return
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = execute(
            args.data_root.resolve(), args.download_receipt.resolve(), args.output.resolve()
        )
    print(json.dumps(result))
    # Distinguish locally finished from end-to-end completion in shell supervisors.
    raise SystemExit(75)


if __name__ == "__main__":
    main()
