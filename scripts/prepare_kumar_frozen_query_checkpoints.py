"""Describe the 54 accepted original archives from text evidence only.

No archive, checkpoint, EEG, query, network or tensor is opened by this command.
The first model retains its accepted original archive, not its later replay tar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "configs/kumar_frozen_query_checkpoints_20261015.json"
BASE = "research_logs/kumar_remaining36_acceptance_20261015/run01/"
LEDGER = BASE + "accepted_jobs_all54.json"
PLAN = BASE + "source_model_plan_all54.json"
OLD_INVENTORY = "research_logs/kumar_checkpoint_reuse_preparation_20261015/accepted_checkpoint_inventory.json"
AUDITS = "research_logs/kumar_remaining36_audit_20261015/run01/model_audits/"
PINS = {
    LEDGER: "013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670",
    PLAN: "28232bfa53515ae3e66acadefa39ee025320cfda0196a5d785631bf4d8f8abcd",
    OLD_INVENTORY: "c4bef5fd36c4759987737d73695de236d5e9924b94decc28bb977317303df788",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_entry(job, planned, receipt, receipt_sha256, acknowledgement, checkpoint):
    """Pure consistency join; checkpoint is audited metadata, never weight bytes."""
    for field in ("job_id", "subject", "seed", "result_key"):
        require(job[field] == planned[field], "Ledger and plan identity mismatch")
        if field in acknowledgement:
            require(job[field] == acknowledgement[field], "Parent acknowledgement identity mismatch")
    require(acknowledgement["status"] == "parent_acknowledged"
            and acknowledgement["receipt_sha256"] == receipt_sha256,
            "Actual parent acknowledgement does not bind this receipt")
    require(receipt["status"] == "completed", "R2 receipt incomplete")
    matches = [entry for entry in receipt["files"] if entry["key"] == job["result_key"]]
    require(len(matches) == 1, "Original archive result_key not unique in receipt")
    entry = matches[0]
    require(entry["sha256"] == job["archive_sha256"], "Accepted original archive hash mismatch")
    require(entry["verification"] == "full_get_sha256_verified"
            and entry["selected_for_full_readback"] is True
            and entry["readback_bytes"] == entry["bytes"] > 0,
            "Original archive lacks complete full GET bytes")
    require(checkpoint["job_id"] == job["job_id"]
            and checkpoint["subject"] == job["subject"] and checkpoint["seed"] == job["seed"]
            and checkpoint["archive_sha256"] == job["archive_sha256"],
            "Checkpoint metadata identity mismatch")
    require(re.fullmatch(r"[0-9a-f]{64}", checkpoint["checkpoint_sha256"]) is not None,
            "Missing frozen checkpoint hash")
    if "checkpoint_sha256" in acknowledgement:
        require(acknowledgement["checkpoint_sha256"] == checkpoint["checkpoint_sha256"]
                and acknowledgement["archive_bytes"] == entry["bytes"],
                "Parent checkpoint hash or original archive length mismatch")
    filename = PurePosixPath(job["result_key"]).name
    require(filename == f"{job['subject']}-seed-{job['seed']}-run01.tar",
            "Unexpected deployment archive filename")
    return {
        "job_id": job["job_id"], "subject": job["subject"], "seed": job["seed"],
        "result_key": job["result_key"], "filename": filename,
        "archive_sha256": job["archive_sha256"], "archive_bytes": entry["bytes"],
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "R2_receipt_path": job["receipt"], "R2_receipt_sha256": receipt_sha256,
        "parent_acknowledgement_path": job["parent_acknowledgement"],
    }


def build_manifest(root=ROOT):
    cache = {}

    def read(path, expected=None):
        require(not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts
                and path.endswith(".json"), "Only repository JSON evidence is allowed")
        if path not in cache:
            raw = (root / path).read_bytes()
            cache[path] = (json.loads(raw), len(raw), sha256(raw))
        value, _, actual = cache[path]
        require(expected is None or actual == expected, "Pinned evidence changed: " + path)
        return value

    ledger = read(LEDGER, PINS[LEDGER])
    plan = read(PLAN, PINS[PLAN])
    old = read(OLD_INVENTORY, PINS[OLD_INVENTORY])
    jobs = ledger["accepted_jobs"]
    require(len(jobs) == len(plan["jobs"]) == 54 and len({j["job_id"] for j in jobs}) == 54,
            "Expected exact accepted54 order")
    require({(j["subject"], j["seed"]) for j in jobs}
            == {(f"sub-{i}", seed) for i in range(1, 19) for seed in (20261012, 20261013, 20261014)},
            "Frozen participant/seed coverage changed")
    for binding in (ledger["historical_accepted18"], ledger["remaining36_ledger"]):
        read(binding["path"], binding["sha256"])
    for binding in plan["source_plans"]:
        read(binding["path"], binding["sha256"])
    read(plan["training_config"], plan["training_config_sha256"])
    read(plan["split_manifest"], plan["split_sha256"])
    old_models = {entry["job_id"]: entry for entry in old["models"]}
    require(len(old_models) == 18 and set(old_models) == {j["job_id"] for j in jobs[:18]},
            "Accepted18 checkpoint metadata coverage changed")
    models = []
    for index, (job, planned) in enumerate(zip(jobs, plan["jobs"]), 1):
        receipt = read(job["receipt"])
        ack = read(job["parent_acknowledgement"])
        if index <= 18:
            metadata_path = OLD_INVENTORY
            original = old_models[job["job_id"]]
            require(original["original_result_key"] == job["result_key"], "Old original result_key changed")
            checkpoint = {**original, "archive_sha256": original["original_model_archive_sha256"]}
        else:
            metadata_path = AUDITS + f"{index - 18:02d}_{job['job_id']}.json"
            checkpoint = read(metadata_path)
            require(checkpoint["status"] == "remaining_source_archive_independently_verified"
                    and checkpoint["query_rows_loaded"] == 0 and checkpoint["audit_refits"] == 0,
                    "Remaining source checkpoint audit not complete")
        model = checked_entry(job, planned, receipt, cache[job["receipt"]][2], ack, checkpoint)
        model.update(accepted_position=index, checkpoint_metadata_path=metadata_path,
                     checkpoint_metadata_sha256=cache[metadata_path][2],
                     parent_acknowledgement_sha256=cache[job["parent_acknowledgement"]][2])
        models.append(model)
    require(len({m["filename"] for m in models}) == 54, "Duplicate deployment filename")
    return {
        "schema_version": 1, "status": "accepted54_original_checkpoint_deployment_metadata_only",
        "execution_enabled": False, "archives_read": False, "checkpoints_loaded": False,
        "query_access": False, "new_fits_authorized": False, "downloads_performed": False,
        "identity_order": "accepted_jobs_all54 exact original18 prefix then frozen36 order",
        "accepted_ledger_path": LEDGER, "accepted_ledger_sha256": PINS[LEDGER],
        "source_model_plan_path": PLAN, "source_model_plan_sha256": PINS[PLAN],
        "model_count": 54, "total_original_archive_bytes": sum(m["archive_bytes"] for m in models),
        "first_model_original_not_replay": True,
        "first_model_replay_archive_excluded_sha256": old["models"][0]["metadata_read_from_archive_sha256"],
        "deployment_rule": "Use exact original result_key and filename; full archive bytes/SHA and checkpoint hash require verification after separate execution authorization",
        "dependencies": [{"path": path, "bytes": cache[path][1], "sha256": cache[path][2]}
                         for path in sorted(cache)],
        "models": models,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    manifest = build_manifest()
    raw = (json.dumps(manifest, indent=2) + "\n").encode()
    if args.write:
        with args.output.open("xb") as stream:
            stream.write(raw)
    else:
        require(args.output.read_bytes() == raw, "Deployment inventory changed")
    print(json.dumps({"status": "metadata_deployment_inventory_verified",
                      "manifest_sha256": sha256(raw), "models": 54,
                      "original_archive_bytes": manifest["total_original_archive_bytes"],
                      "archives_read": False, "execution_enabled": False}))


if __name__ == "__main__":
    main()
