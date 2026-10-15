"""Independently audit the proposed 36 source-only fit packages; no model forward.

Without --archive this is JSON/hash preflight only: no tensor/data loader is
imported. Actual private-package audit is explicit and never changes acceptance.
The immutable old auditor's numerical checkpoint/history/label/CE block is
preserved verbatim; only job/input/runtime/source evidence bindings differ.
"""

import argparse
import hashlib
import io
import json
import math
import re
import subprocess
import tarfile
from pathlib import Path

from run_kumar_development_queue import FILES, ROOT, require

CONTRACT_RELATIVE = "configs/kumar_remaining_source_batch_20261015.json"
DEFAULT_CONTRACT = ROOT / CONTRACT_RELATIVE
MAX_ARCHIVE_BYTES = 16 * 1024**2


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(contract, key):
    path = (ROOT / contract[key]).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(), "Unsafe metadata path")
    require(digest(path.read_bytes()) == contract[key + "_sha256"],
            "Pinned metadata mismatch: " + key)
    return path


def preflight(contract_path=DEFAULT_CONTRACT):
    """Read only frozen JSON metadata; no EEG, tensors, forward, fitting or writes."""
    contract_path = Path(contract_path)
    contract = json.loads(contract_path.read_text())
    require(contract["policy_revision"] == "remaining-source-bounded-export-v1" and
            contract["execution_enabled"] is False, "Unexpected operation contract")
    from check_kumar_checkpoint_reuse_proposal import check
    proposal = json.loads(pinned(contract, "scientific_proposal").read_text())
    check(proposal, root=ROOT)
    proposed = proposal["remaining_source_training_proposal"]["jobs"]
    jobs = contract["remaining_jobs"]
    require(len(jobs) == len({j["job_id"] for j in jobs}) == 36 and
            [{key: job[key] for key in original} for job, original in zip(jobs, proposed)]
            == proposed, "Unexpected remaining job identity or order")
    accepted = json.loads(pinned(contract, "accepted_ledger").read_text())["accepted_jobs"]
    require(len(accepted) == 18 and not ({j["job_id"] for j in accepted} &
                                      {j["job_id"] for j in jobs}) and
            not ({j["subject"] for j in accepted} & {j["subject"] for j in jobs}),
            "Previously accepted models cannot be a new remaining-source experiment")
    for key in ("scientific_config", "split_manifest", "input_manifest", "https_manifest"):
        pinned(contract, key)
    inputs = json.loads(pinned(contract, "input_manifest").read_text())
    files = inputs["files"]
    require(len(files) == len({e["relative_path"] for e in files}) == 253 and
            sum(e["bytes"] for e in files) == 196740994 and inputs["query_access"] is False,
            "Incorrect source-only input scope")
    https = json.loads(pinned(contract, "https_manifest").read_text())
    require(https["source_plan_sha256"] == contract["input_manifest_sha256"] and
            https["query_access"] is False and len(https["files"]) == 253 and
            {e["path"]: (e["expected_sha256"], e["size"]) for e in https["files"]} ==
            {e["relative_path"]: (e["sha256"], e["bytes"]) for e in files},
            "HTTPS/raw source manifest mismatch")
    for job in jobs:
        require(job["training_config_sha256"] == contract["scientific_config_sha256"] and
                job["split_sha256"] == contract["split_manifest_sha256"],
                "Frozen science or split identity mismatch")
    for name, expected in contract["frozen_files"].items():
        source = (ROOT / name).resolve()
        require(source.is_relative_to(ROOT.resolve()) and digest(source.read_bytes()) == expected,
                "Frozen code changed: " + name)
    return contract, {"status": "remaining_source_audit_metadata_valid_execution_closed",
        "remaining_source_jobs": 36, "accepted_models_preserved": 18,
        "source_input_files": 253, "source_input_bytes": 196740994,
        "checkpoint_tensors_loaded": False, "EEG_or_query_loaded": False,
        "model_forward_passes": 0, "audit_refits": 0, "accepted_ledger_modified": False,
        "parent_acknowledgement_written": False, "Pod_operated": False}


def archive(path, expected_sha, expected_bytes):
    """Validate bounded raw tar bytes/members before loading any checkpoint tensor."""
    path = Path(path)
    require(type(expected_bytes) is int and 0 < expected_bytes <= MAX_ARCHIVE_BYTES,
            "Archive exceeds frozen size bound")
    require(path.is_file() and path.stat().st_size == expected_bytes,
            "Archive length mismatch")
    raw = path.read_bytes()
    require(len(raw) == expected_bytes and digest(raw) == expected_sha, "Archive hash mismatch")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as package:
        members = package.getmembers()
        names = [member.name for member in members]
        require(len(members) == len(set(names)) == len(FILES) + 1 and
                set(names) == set(FILES) | {"manifest.json"} and
                all(member.isfile() and not Path(member.name).is_absolute() and
                    ".." not in Path(member.name).parts for member in members) and
                sum(member.size for member in members) <= MAX_ARCHIVE_BYTES,
                "Unsafe/duplicate/incorrect archive members")
        data = {member.name: package.extractfile(member).read() for member in members}
    manifest = json.loads(data["manifest.json"])
    entries = manifest["files"]
    require(len(entries) == len(FILES) and len({e["path"] for e in entries}) == len(FILES) and
            {e["path"] for e in entries} == set(FILES), "Archive manifest scope mismatch")
    for entry in entries:
        value = data[entry["path"]]
        require(len(value) == entry["bytes"] and digest(value) == entry["sha256"],
                "Archive member hash/length mismatch")
    return manifest, data


def verify_source_evidence(inputs, download, job, contract):
    frozen = json.loads(pinned(contract, "input_manifest").read_text())["files"]
    mapping = {entry["relative_path"]: entry for entry in frozen}
    expected_paths = {name for name in mapping
                      if name == "dataset_description.json" or
                      name.startswith(job["subject"] + "/")}
    require(set(inputs["verified_source_files"]) == expected_paths,
            "Subject input evidence is incomplete or contains another participant")
    for name, value in inputs["verified_source_files"].items():
        require(value["sha256"] == mapping[name]["sha256"], "Input SHA mismatch")
    expected_runs = {f"{job['subject']}/ses-0/eeg/"
                     f"{job['subject']}_ses-0_task-imagery_run-{run}_eeg.edf":
                     "source_train" if run < 2 else "source_validation" for run in range(3)}
    require({run["source_file"]: run["role"] for run in inputs["runs"]} == expected_runs,
            "Input signals are not exactly the frozen source runs")
    require(all(run["raw_file_sha256"] == mapping[run["source_file"]]["sha256"]
                for run in inputs["runs"]), "Source run hash mismatch")
    records = download["records"]
    require(download["status"] == "all_253_full_sha256_verified" and len(records) == 253 and
            len({entry["path"] for entry in records}) == 253 and
            {entry["path"] for entry in records} == set(mapping) and
            download["query_access"] is False and
            download["real_training_executed"] is False and
            download["maximum_attempts_per_file"] == 1 and
            download["manifest_sha256"] == contract["https_manifest_sha256"] and
            download["input_manifest_sha256"] == download["source_plan_sha256"] ==
            contract["input_manifest_sha256"], "Incomplete or different source download receipt")
    require(all(entry["sha256"] == mapping[entry["path"]]["sha256"] and
                entry["status"] in {"reused_sha256_verified", "downloaded_sha256_verified"}
                for entry in records), "Download receipt member SHA/status mismatch")


def audit(path, expected_sha, expected_bytes, contract_path=DEFAULT_CONTRACT):
    contract, _ = preflight(contract_path)
    manifest, data = archive(path, expected_sha, expected_bytes)
    jobs = {job["job_id"]: job for job in contract["remaining_jobs"]}
    job = json.loads(data["job.json"])
    require(job["job_id"] in jobs and job == jobs[job["job_id"]],
            "Unexpected or already accepted job")
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
    import numpy as np
    import torch

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
    verify_source_evidence(inputs, json.loads(data["input_receipt.json"]), job, contract)
    provenance = record["provenance"]
    require(provenance["git_dirty"] is False, "Uncommitted source execution")
    commit = provenance["git_commit"]
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit),
            "Execution provenance requires an exact fixed commit")
    require(data["queue_runtime.json"] == Path(contract_path).read_bytes() ==
            subprocess.check_output(["git", "show", f"{commit}:{CONTRACT_RELATIVE}"], cwd=ROOT),
            "Executed operation contract mismatch")
    required_provenance = {contract["scientific_config"], contract["https_manifest"],
                           CONTRACT_RELATIVE}
    require(required_provenance <= set(provenance["source_config_sha256"]),
            "Execution provenance does not bind the operation/science/HTTPS config")
    for received, source in (
        ("run_source.py", "scripts/run_kumar_remaining_source_batch.py"),
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
        status="remaining_source_archive_independently_verified",
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--bytes", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.archive is None:
        require(args.sha256 is None and args.bytes is None and args.output is None,
                "Archive audit identity/output requires --archive")
        _, result = preflight(args.contract)
    else:
        require(args.sha256 is not None and args.bytes is not None and args.output is not None,
                "Actual audit requires explicit original SHA256, bytes and a new output")
        require(not args.output.exists(), "Audit output must be new; preserve old evidence")
        result = audit(args.archive, args.sha256, args.bytes, args.contract)
        with args.output.open("x") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
