"""Read-only source replay; no optimizer, fitting, query access or network."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import traceback
from pathlib import Path

import numpy as np
import torch

from audit_kumar_first_fit_bundle import FIT_SHA, archive
from run_kumar_parent_first_fit import validate_inputs
from train_kumar_eegnet import load_checkpoint, source_arrays, state_digest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/kumar_first_fit_replay_20261014.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def independent_eval(model, x, labels, batch_size):
    """Independent forward loop and NumPy log-sum-exp CE; never use training loss helper."""
    before = state_digest(model)
    model.model_.eval()
    outputs, summed = [], 0.0
    with torch.inference_mode():
        for start in range(0, len(x), batch_size):
            batch = torch.from_numpy(x[start : start + batch_size]).to(model.device)
            logits = model.model_(batch)
            while logits.ndim > 2 and logits.shape[-1] == 1:
                logits = logits.squeeze(-1)
            require(tuple(logits.shape) == (len(batch), 2), "Unexpected logit dimensions")
            target = torch.as_tensor(
                labels[start : start + batch_size], dtype=torch.long, device=model.device
            )
            summed += torch.nn.functional.cross_entropy(logits, target, reduction="sum").item()
            outputs.append(logits.cpu().numpy())
    logits = np.concatenate(outputs)
    require(np.isfinite(logits).all(), "Nonfinite logits")
    shifted = logits.astype(np.float64) - logits.max(axis=1, keepdims=True)
    losses = np.log(np.exp(shifted).sum(axis=1)) - shifted[np.arange(len(labels)), labels]
    require(state_digest(model) == before, "Model/BN/normalization state changed")
    return logits, losses, summed / len(labels)


def replay(args, output, report):
    from learning_preserving_bci.datasets.kumar import load_subject

    contract = json.loads(CONTRACT.read_text())
    require(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8", "Missing CUBLAS setting")
    require(torch.cuda.is_available(), "CUDA unavailable; no CPU fallback")
    require(
        not subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"], text=True
        ).strip(),
        "GPU busy; parent must coordinate papers",
    )
    _, files = archive(args.fit_archive, FIT_SHA, 143360, 11)
    metadata = json.loads(files["weights.json"])
    fit = json.loads(files["fit_result.json"])
    config = json.loads(files["training_config.json"])
    require(
        hashlib.sha256(files["training_config.json"]).hexdigest()
        == contract["training_config_sha256"],
        "Training configuration differs",
    )
    for name, expected in fit["provenance"]["source_config_sha256"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected,
            "Historical source/config mismatch: " + name,
        )
    require(
        (ROOT / "scripts/train_kumar_eegnet.py").read_bytes() == files["train_source.py"],
        "Training implementation changed",
    )
    validate_inputs(args.data_root, args.download_receipt)
    require(metadata["seed"] == 20261012 and not metadata["synthetic"], "Wrong fit")
    torch.set_num_threads(config["threads"])
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    subject = load_subject(
        args.data_root,
        "sub-1",
        ROOT / config["protocol_config"],
        split_manifest=ROOT / config["split_manifest"],
        allowed_roles={"source_train", "source_validation"},
    )
    require(
        subject.provenance == json.loads(files["input_audit.json"]), "Rebuilt input audit differs"
    )
    train, _, val, labels, train_meta, val_meta = source_arrays(subject)
    require((len(train), len(val)) == (40, 20), "Source counts differ")
    require(
        [m["trial_id"] for m in train_meta] == metadata["source_train_ids"]
        and [m["trial_id"] for m in val_meta] == metadata["source_validation_ids"],
        "Frozen trial order differs",
    )
    # Use verified archive bytes; original checkpoint/sidecar remain untouched.
    for name in ("weights.pt", "weights.json"):
        (output / name).write_bytes(files[name])
    model = load_checkpoint(output / "weights.pt", expected_sha256=contract["checkpoint_sha256"])
    train = np.asarray(train, dtype=np.float32)
    mean = train.mean(axis=(0, 2), keepdims=True)
    scale = train.std(axis=(0, 2), keepdims=True).clip(
        min=config["normalization"]["scale_floor_volts"]
    )
    require(np.array_equal(mean, model.channel_mean_), "TRAIN mean differs bitwise")
    require(np.array_equal(scale, model.channel_scale_), "TRAIN scale differs bitwise")
    x = np.asarray((np.asarray(val, dtype=np.float32) - mean) / scale, dtype=np.float32)
    labels = np.asarray(labels, dtype=np.int64)
    logits, losses, torch_loss = independent_eval(model, x, labels, 16)
    expected = metadata["source_validation_loss"]
    numpy_loss = float(losses.mean())
    report.update(
        expected_loss=expected,
        replay_torch_loss=torch_loss,
        independent_numpy_loss=numpy_loss,
        torch_absolute_error=abs(torch_loss - expected),
        numpy_absolute_error=abs(numpy_loss - expected),
        normalization_bitwise_equal=True,
        input_audit_equal=True,
        source_train_rows=40,
        source_validation_rows=20,
        frozen_state_sha256=state_digest(model),
        selected_epoch=metadata["selected_epoch"],
    )
    np.savez(
        output / "source_validation_predictions.npz",
        logits=logits,
        labels=labels,
        loss_float64=losses,
        trial_ids=np.asarray(metadata["source_validation_ids"]),
    )
    require(
        abs(torch_loss - expected) <= contract["loss_absolute_tolerance"],
        "PyTorch loss outside preregistered tolerance",
    )
    require(
        abs(numpy_loss - expected) <= contract["loss_absolute_tolerance"],
        "Independent NumPy loss outside preregistered tolerance",
    )
    report["status"] = "source_checkpoint_independent_replay_passed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--download-receipt", type=Path, required=True)
    parser.add_argument("--fit-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Exclusive output reservation: any previous attempt is preserved, not overwritten.
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(
        status="failed_closed",
        fits=0,
        optimizer_steps=0,
        query_rows_loaded=0,
        parent_queue_execution_authorized=False,
        replay_contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        replay_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        git_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        torch_version=torch.__version__,
        numpy_version=np.__version__,
    )
    try:
        with Path("/workspace/research-gpu.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            replay(args, args.output, report)
    except Exception:
        (args.output / "failure_traceback.txt").write_text(traceback.format_exc())
        raise
    finally:
        (args.output / "replay_result.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )


if __name__ == "__main__":
    main()
