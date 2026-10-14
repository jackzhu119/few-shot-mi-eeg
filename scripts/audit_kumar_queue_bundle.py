"""Audit received source-only queue evidence without loading EEG or fitting a model."""

import argparse
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import torch

from audit_kumar_first_fit_bundle import archive
from run_kumar_development_queue import FILES, ROOT, require


def audit(path, expected_sha, expected_bytes):
    require(expected_bytes <= 16 * 1024**2, "Archive exceeds frozen size bound")
    manifest, data = archive(path, expected_sha, expected_bytes, len(FILES))
    require(set(data) == set(FILES) | {"manifest.json"}, "Archive member scope differs")
    plan = json.loads((ROOT / "configs/kumar_development_queue_plan_20261014.json").read_text())
    jobs = {j["job_id"]: j for j in plan["jobs"][1:]}
    job = json.loads(data["job.json"])
    require(job["job_id"] in jobs and job == jobs[job["job_id"]], "Unexpected or reused job")
    for key in ("job_id", "subject", "seed", "result_key"):
        require(manifest[key] == job[key], "Manifest identity mismatch")
    record, weights = [json.loads(data[n]) for n in ("fit_result.json", "weights.json")]
    require(
        record["status"] == "fit_saved"
        and not record["synthetic"]
        and record["query_rows_loaded"] == 0
        and record["source_train_rows"] == 40
        and record["source_validation_rows"] == 20,
        "Unexpected fit scope/status",
    )
    require(
        record["job_id"] == job["job_id"]
        and record["seed"] == job["seed"] == weights["seed"]
        and record["subject"] == job["subject"],
        "Fit identity mismatch",
    )
    config = json.loads(data["training_config.json"])
    require(
        hashlib.sha256(data["training_config.json"]).hexdigest()
        == job["training_config_sha256"]
        == record["training_config_sha256"],
        "Frozen config mismatch",
    )
    require(config == weights["config"] and not weights["synthetic"], "Checkpoint config mismatch")
    require(config["freeze"]["ready_for_formal_training"] is False, "Formal gate opened")
    sha = hashlib.sha256(data["weights.pt"]).hexdigest()
    require(
        sha == weights["checkpoint_sha256"] == record["checkpoint_sha256"],
        "Checkpoint hash mismatch",
    )
    payload = torch.load(io.BytesIO(data["weights.pt"]), map_location="cpu", weights_only=True)
    require(
        set(payload)
        == {"model_state_dict", "channel_mean", "channel_scale", "classes", "context_utf8"},
        "Checkpoint payload mismatch",
    )
    context = json.loads(bytes(payload["context_utf8"].tolist()).decode())
    require(
        context == {k: v for k, v in weights.items() if k != "checkpoint_sha256"},
        "Unbound checkpoint metadata",
    )
    tensors = dict(payload["model_state_dict"])
    tensors.update({k: payload[k] for k in ("channel_mean", "channel_scale", "classes")})
    state = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        require(torch.isfinite(tensor).all().item(), "Nonfinite checkpoint")
        a = tensor.detach().cpu().contiguous().numpy()
        for value in (
            name.encode(),
            str(a.dtype).encode(),
            json.dumps(a.shape).encode(),
            a.tobytes(),
        ):
            state.update(value)
    require(state.hexdigest() == weights["frozen_state_sha256"], "State digest mismatch")
    require(
        tuple(payload["channel_mean"].shape) == tuple(payload["channel_scale"].shape) == (1, 22, 1)
        and (payload["channel_scale"] > 0).all().item()
        and payload["classes"].tolist() == [0, 1],
        "Invalid normalization/classes",
    )
    split_path = ROOT / config["split_manifest"]
    require(
        hashlib.sha256(split_path.read_bytes()).hexdigest()
        == job["split_sha256"]
        == record["split_sha256"],
        "Split identity mismatch",
    )
    split = json.loads(split_path.read_text())["trials"]
    roles = {}
    for role, key in (
        ("source_train", "source_train_ids"),
        ("source_validation", "source_validation_ids"),
    ):
        selected = [
            t
            for t in split
            if t["subject"] == job["subject"] and t["role"] == role and t["included"]
        ]
        require(
            set(weights[key]) == {t["trial_id"] for t in selected}
            and len(weights[key]) == len(selected),
            "Frozen source IDs differ",
        )
        roles[role] = {t["trial_id"]: t for t in selected}
    history = weights["history"]
    require(
        1 <= len(history) <= 100
        and [h["epoch"] for h in history] == list(range(1, len(history) + 1)),
        "Epoch sequence mismatch",
    )
    require(all(math.isfinite(h["source_validation_loss"]) for h in history), "Nonfinite history")
    selected = min(range(len(history)), key=lambda i: history[i]["source_validation_loss"])
    best = history[selected]["source_validation_loss"]
    require(
        record["epochs_executed"] == len(history)
        and weights["optimizer_steps"] == record["optimizer_steps"] == 3 * len(history),
        "Step budget mismatch",
    )
    require(
        weights["selected_epoch"] == record["selected_epoch"] == selected + 1
        and weights["source_validation_loss"] == record["selected_validation_loss"] == best,
        "Earliest minimum mismatch",
    )
    first_stop, running_best, stale = None, float("inf"), 0
    for h in history:
        if h["source_validation_loss"] < running_best:
            running_best, stale = h["source_validation_loss"], 0
        else:
            stale += 1
        if stale >= 15:
            first_stop = h["epoch"]
            break
    require(
        (first_stop == len(history)) if first_stop is not None else len(history) == 100,
        "Early stopping differs from frozen rule",
    )
    with np.load(io.BytesIO(data["source_validation_predictions.npz"]), allow_pickle=False) as n:
        ids = n["trial_ids"].tolist()
        logits = n["logits"].astype(np.float64)
        require(
            ids == weights["source_validation_ids"] and logits.shape == (20, 2),
            "Prediction IDs/shape mismatch",
        )
        labels = np.asarray(
            [config["input"]["class_mapping"][roles["source_validation"][x]["label"]] for x in ids]
        )
        require(np.array_equal(n["labels"], labels), "Prediction labels mismatch")
        loss = np.logaddexp(logits[:, 0], logits[:, 1]) - logits[np.arange(20), labels]
        require(
            np.isfinite(loss).all() and np.max(np.abs(loss - n["loss_float64"])) < 1e-14,
            "Independent CE differs",
        )
        require(
            abs(float(loss.mean()) - best) <= 1e-7
            and abs(record["replay_torch_loss"] - best) <= 1e-7
            and record["replay_absolute_tolerance"] == 1e-7,
            "Loss tolerance exceeded",
        )
    inputs = json.loads(data["input_audit.json"])
    require(
        inputs["subject"] == job["subject"]
        and len(inputs["runs"]) == 3
        and all(r["role"] in {"source_train", "source_validation"} for r in inputs["runs"]),
        "Input audit contains unexpected signals",
    )
    frozen = json.loads((ROOT / plan["data_manifest"]).read_text())["files"]
    mapping = {e["relative_path"]: e for e in frozen}
    for path_name, value in inputs["verified_source_files"].items():
        require(value["sha256"] == mapping[path_name]["sha256"], "Input SHA mismatch")
    download = json.loads(data["input_receipt.json"])
    require(
        download["status"] == "all_127_full_sha256_verified" and len(download["records"]) == 127,
        "Input download receipt incomplete",
    )
    require(
        download["manifest_sha256"]
        == hashlib.sha256(
            (ROOT / "configs/kumar_development_queue_https_20261014.json").read_bytes()
        ).hexdigest(),
        "Input manifest differs",
    )
    provenance = record["provenance"]
    require(provenance["git_dirty"] is False, "Uncommitted source execution")
    commit = provenance["git_commit"]
    for received, source in (
        ("run_source.py", "scripts/run_kumar_development_queue.py"),
        ("train_source.py", "scripts/train_kumar_eegnet.py"),
        ("adapter_source.py", "src/learning_preserving_bci/datasets/kumar.py"),
    ):
        require(
            data[received]
            == subprocess.check_output(["git", "show", f"{commit}:{source}"], cwd=ROOT),
            "Executed source mismatch",
        )
    for name, expected in provenance["source_config_sha256"].items():
        require(
            hashlib.sha256(
                subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
            ).hexdigest()
            == expected,
            "Provenance source/config mismatch",
        )
    return dict(
        status="queue_archive_independently_verified",
        job_id=job["job_id"],
        subject=job["subject"],
        seed=job["seed"],
        archive_sha256=expected_sha,
        archive_bytes=expected_bytes,
        result_key=job["result_key"],
        checkpoint_sha256=sha,
        epochs=len(history),
        selected_epoch=selected + 1,
        source_validation_loss=best,
        independent_saved_logit_loss=float(loss.mean()),
        query_rows_loaded=0,
        audit_refits=0,
        audit_EEG_loaded=False,
        R2_backup_verified=False,
        parent_acknowledged=False,
        stop_Pod=False,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--bytes", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.archive, args.sha256, args.bytes)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(result))
