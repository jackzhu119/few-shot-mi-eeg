"""Execute at most one next frozen source fit; blocked until each predecessor is backed up."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "configs/kumar_development_queue_runtime_20261014.json"
LOCK = Path("/workspace/research-gpu.lock")
FILES = (
    "weights.pt",
    "weights.json",
    "fit_result.json",
    "training.log",
    "input_audit.json",
    "training_config.json",
    "input_receipt.json",
    "queue_runtime.json",
    "job.json",
    "run_source.py",
    "train_source.py",
    "adapter_source.py",
    "events.jsonl",
    "source_validation_predictions.npz",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_file(path):
    return json.loads(Path(path).read_text())


def checked_path(relative):
    path = ROOT / relative
    require(path.resolve().is_relative_to(ROOT.resolve()), "Unsafe evidence path")
    return path


def verified_receipt(path, key, expected_sha):
    r = json_file(path)
    require(
        r["status"] == "completed" and r["totals"]["failed_files"] == 0, "Incomplete R2 receipt"
    )
    matching = [f for f in r["files"] if f["key"] == key]
    require(len(matching) == 1, "Missing or ambiguous R2 key")
    f = matching[0]
    require(
        f["sha256"] == expected_sha
        and f["verification"] == "full_get_sha256_verified"
        and f["readback_bytes"] == f["bytes"],
        "R2 full-GET identity mismatch",
    )


def check_gate():
    from check_kumar_development_queue_plan import check

    check()
    runtime = json_file(RUNTIME)
    require(
        runtime["ready_for_parent_dispatch"]
        and not runtime["query_access"]
        and not runtime["formal_gate"]
        and runtime["maximum_new_fits"] == 17
        and runtime["maximum_new_fits_per_invocation"] == 1,
        "Runtime scope gate closed",
    )
    for key in ("scientific_config", "queue_plan", "replay_audit", "replay_receipt"):
        require(
            digest(checked_path(runtime[key])) == runtime[key + "_sha256"],
            "Pinned evidence changed: " + key,
        )
    audit = json_file(checked_path(runtime["replay_audit"]))
    require(
        audit["status"] == "independent_replay_archive_audit_passed"
        and audit["absolute_error"] <= 1e-7
        and audit["audit_refits"] == 0,
        "Independent replay gate failed",
    )
    verified_receipt(
        checked_path(runtime["replay_receipt"]),
        "few-shot-mi-eeg/experiments/kumar2024/gpu-source-20261014/"
        "sub-1-seed-20261012-replay-run01.tar",
        audit["replay_archive_sha256"],
    )
    plan = json_file(checked_path(runtime["queue_plan"]))
    accepted = json_file(checked_path(runtime["accepted_jobs"]))["accepted_jobs"]
    jobs = {j["job_id"]: j for j in plan["jobs"]}
    require(len({a["job_id"] for a in accepted}) == len(accepted), "Duplicate acceptance")
    for a in accepted:
        require(a["job_id"] in jobs, "Unplanned acceptance")
        j = jobs[a["job_id"]]
        require(
            (a["subject"], a["seed"], a["result_key"])
            == (j["subject"], j["seed"], j["result_key"]),
            "Acceptance identity mismatch",
        )
        receipt = checked_path(a["receipt"])
        verified_receipt(receipt, j["result_key"], a["archive_sha256"])
        ack = json_file(checked_path(a["parent_acknowledgement"]))
        require(
            ack["status"] == "parent_acknowledged" and ack["receipt_sha256"] == digest(receipt),
            "Parent receipt acknowledgement missing",
        )
        if j["action"] != "reuse_completed_never_refit":
            require(ack["job_id"] == j["job_id"], "Acknowledgement belongs to another job")
    ids = {a["job_id"] for a in accepted}
    require(plan["jobs"][0]["job_id"] in ids, "First fit must be reused, never refit")
    # Acceptance must be a prefix; cannot skip a failed subject or seed.
    ordered = [j["job_id"] for j in plan["jobs"]]
    require(ids == set(ordered[: len(ids)]), "Out-of-order acceptance")
    pending = [j for j in plan["jobs"] if j["job_id"] not in ids]
    return runtime, plan, pending[0] if pending else None


def event(output, status):
    with (output / "events.jsonl").open("a") as stream:
        stream.write(
            json.dumps(dict(status=status, utc=datetime.now(timezone.utc).isoformat())) + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def package(output, job):
    require(
        {p.name for p in output.iterdir()} == set(FILES),
        "Unexpected or incomplete output; preserve and diagnose",
    )
    record = json_file(output / "fit_result.json")
    require(
        record["job_id"] == job["job_id"]
        and record["status"] == "fit_saved"
        and record["query_rows_loaded"] == 0,
        "Incomplete local fit",
    )
    require(digest(output / "weights.pt") == record["checkpoint_sha256"], "Checkpoint changed")
    entries = []
    for name in FILES:
        p = output / name
        require(p.is_file() and not p.is_symlink(), "Unsafe output member")
        entries.append(dict(path=name, bytes=p.stat().st_size, sha256=digest(p)))
    require(
        sum(e["bytes"] for e in entries) < 16 * 1024**2 - 1024 * 1024, "Archive would exceed bound"
    )
    manifest = dict(
        job_id=job["job_id"],
        subject=job["subject"],
        seed=job["seed"],
        result_key=job["result_key"],
        files=entries,
        status="fit_saved_private_backup_pending",
        R2_backup_verified=False,
        parent_acknowledged=False,
        query_rows_loaded=0,
        stop_Pod=False,
    )
    path = output.with_suffix(".tar")
    if path.exists():
        with tarfile.open(path) as tar:
            members = tar.getmembers()
            require(
                len(members) == len(FILES) + 1
                and all(m.isfile() for m in members)
                and set(tar.getnames()) == set(FILES) | {"manifest.json"},
                "Existing archive members changed",
            )
            require(
                json.load(tar.extractfile("manifest.json")) == manifest,
                "Existing archive manifest differs",
            )
            for e in entries:
                raw = tar.extractfile(e["path"]).read()
                require(
                    len(raw) == e["bytes"] and hashlib.sha256(raw).hexdigest() == e["sha256"],
                    "Existing archive content differs",
                )
    else:
        with path.open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as tar:
            for e in entries:
                raw = (output / e["path"]).read_bytes()
                info = tarfile.TarInfo(e["path"])
                info.size, info.mode = len(raw), 0o600
                tar.addfile(info, io.BytesIO(raw))
            raw = (json.dumps(manifest, indent=2) + "\n").encode()
            info = tarfile.TarInfo("manifest.json")
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
    require(path.stat().st_size <= 16 * 1024**2, "Oversized archive")
    return dict(
        status="fit_saved_private_backup_pending",
        job_id=job["job_id"],
        subject=job["subject"],
        seed=job["seed"],
        archive=str(path),
        bytes=path.stat().st_size,
        sha256=digest(path),
        result_key=job["result_key"],
        R2_backup_verified=False,
        stop_Pod=False,
    )


def execute(job, runtime, data_root, receipt):
    import numpy as np
    import torch

    from fetch_kumar_development_queue_https import verify_all
    from learning_preserving_bci.datasets.kumar import load_subject
    from learning_preserving_bci.utils.reproducibility import collect_provenance
    from replay_kumar_first_fit import independent_eval
    from train_kumar_eegnet import SourceOnlyEEGNet, load_checkpoint, save_checkpoint, source_arrays

    output = Path(job["output"])
    if output.exists():
        # No fit call on any existing reservation, including incomplete/time-out state.
        if not (output / "fit_result.json").exists():
            raise RuntimeError("Existing partial reservation; diagnose, never automatically refit")
        return package(output, job)
    require(not output.with_suffix(".tar").exists(), "Orphan archive exists; inspect before action")
    require(torch.cuda.is_available(), "CUDA required; no CPU fallback")
    require(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8", "Missing CUBLAS setting")
    require(
        not subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"], text=True
        ).strip(),
        "GPU busy; parent must coordinate papers",
    )
    require(shutil.disk_usage(data_root).free >= 2 * 1024**3, "Require 2 GiB free space")
    verify_all(data_root, receipt)
    config = json_file(checked_path(runtime["scientific_config"]))
    torch.set_num_threads(config["threads"])
    torch.cuda.reset_peak_memory_stats()
    output.mkdir(parents=True, exist_ok=False)  # Exclusive persistent reservation.
    event(output, "reserved")
    try:
        for src, name in [
            (checked_path(runtime["scientific_config"]), "training_config.json"),
            (receipt, "input_receipt.json"),
            (RUNTIME, "queue_runtime.json"),
            (Path(__file__), "run_source.py"),
            (ROOT / "scripts/train_kumar_eegnet.py", "train_source.py"),
            (ROOT / "src/learning_preserving_bci/datasets/kumar.py", "adapter_source.py"),
        ]:
            (output / name).write_bytes(src.read_bytes())
        (output / "job.json").write_text(json.dumps(job, indent=2) + "\n")
        started = time.monotonic()
        with (
            (output / "training.log").open("x") as log,
            contextlib.redirect_stdout(log),
            contextlib.redirect_stderr(log),
        ):
            subject = load_subject(
                data_root,
                job["subject"],
                ROOT / config["protocol_config"],
                split_manifest=ROOT / config["split_manifest"],
                allowed_roles={"source_train", "source_validation"},
            )
            source = source_arrays(subject)
            require((len(source[0]), len(source[2])) == (40, 20), "Frozen source counts differ")
            (output / "input_audit.json").write_text(
                json.dumps(subject.provenance, indent=2) + "\n"
            )
            event(output, "fitting")
            model = SourceOnlyEEGNet(config, job["seed"]).fit_source(*source)
            saved = save_checkpoint(
                model, output / "weights.pt", synthetic=False, software_validation_only=False
            )
            restored = load_checkpoint(
                output / "weights.pt", expected_sha256=saved["checkpoint_sha256"]
            )
            require(
                np.array_equal(model.predict_proba(source[2]), restored.predict_proba(source[2])),
                "Checkpoint probability replay differs",
            )
            x = np.asarray(
                (source[2].astype(np.float32) - restored.channel_mean_) / restored.channel_scale_,
                dtype=np.float32,
            )
            logits, losses, torch_loss = independent_eval(restored, x, source[3], 16)
            require(
                abs(torch_loss - model.selected_validation_loss_) <= 1e-7
                and abs(float(losses.mean()) - model.selected_validation_loss_) <= 1e-7,
                "Source replay outside frozen absolute tolerance; preserve checkpoint",
            )
            np.savez(
                output / "source_validation_predictions.npz",
                logits=logits,
                labels=source[3],
                loss_float64=losses,
                trial_ids=np.asarray(restored.source_validation_ids_),
            )
            torch.cuda.synchronize()
            record = dict(
                status="fit_saved",
                job_id=job["job_id"],
                subject=job["subject"],
                seed=job["seed"],
                query_rows_loaded=0,
                source_train_rows=40,
                source_validation_rows=20,
                checkpoint_sha256=saved["checkpoint_sha256"],
                training_config_sha256=job["training_config_sha256"],
                split_sha256=job["split_sha256"],
                selected_epoch=model.selected_epoch_,
                epochs_executed=len(model.history_),
                optimizer_steps=model.optimizer_steps_,
                selected_validation_loss=model.selected_validation_loss_,
                replay_torch_loss=torch_loss,
                replay_numpy_loss=float(losses.mean()),
                replay_absolute_tolerance=1e-7,
                runtime_seconds=time.monotonic() - started,
                peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
                provenance=collect_provenance(job["seed"], ROOT),
                parent_dispatch_acknowledged_replay_backup=True,
                R2_backup_verified=False,
                synthetic=False,
            )
            require(
                record["optimizer_steps"] <= 300 and record["epochs_executed"] <= 100,
                "Training budget exceeded",
            )
            with (output / "fit_result.json").open("x") as stream:
                json.dump(record, stream, indent=2, allow_nan=False)
            print(
                json.dumps(
                    dict(
                        status="fit_saved",
                        selected_epoch=model.selected_epoch_,
                        epochs=len(model.history_),
                        query_rows=0,
                    )
                )
            )
        event(output, "fit_saved")
        return package(output, job)
    except Exception:
        event(output, "failed_preserved_no_automatic_retry")
        (output / "failure_traceback.txt").write_text(traceback.format_exc())
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, default=Path("/workspace/paper2-data/kumar"))
    p.add_argument(
        "--download-receipt",
        type=Path,
        default=Path("/workspace/paper2-results/https-development-download-run01.json"),
    )
    p.add_argument("--execute-next", action="store_true")
    p.add_argument("--parent-acknowledge-replay-backup", action="store_true")
    a = p.parse_args()
    if not a.execute_next:
        _, _, job = check_gate()
        print(json.dumps(dict(status="plan_only", next_job=job, fit_executed=False)))
        return
    require(a.parent_acknowledge_replay_backup, "Parent must review replay backup before dispatch")
    require(
        not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
        "Require clean fixed checkout",
    )
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runtime, _, job = check_gate()
        if job is None:
            print(
                json.dumps(
                    dict(
                        status="all_18_development_fits_accepted",
                        new_fits=0,
                        formal_query_gate=False,
                    )
                )
            )
            return
        result = execute(job, runtime, a.data_root.resolve(), a.download_receipt.resolve())
    print(json.dumps(result))
    raise SystemExit(75)  # Mandatory private backup/parent acknowledgement remains pending.


if __name__ == "__main__":
    main()
