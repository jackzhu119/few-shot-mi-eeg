"""Describe all54 accepted source models from saved logits, without any model load.

Development6, remaining12 and secondary all18 summaries remain separate. Every
fixed seed is retained. Selected-checkpoint source-validation descriptions
preserve the old no-CI/no-hypothesis policy and imply no query efficacy.
"""

import argparse
import io
import json
import math
import platform
import subprocess
from pathlib import Path

import numpy as np

from aggregate_kumar_development_saved_results import (
    LEDGER as OLD_LEDGER,
    PLAN as OLD_PLAN,
    REPLAY_RECEIPT,
    ROOT,
    aggregate_participants,
    describe_logits,
    read_verified_archive,
    require,
    sha256,
    write_csv,
)

ACCEPTANCE = "research_logs/kumar_remaining36_acceptance_20261015/run01"
PLAN = ACCEPTANCE + "/source_model_plan_all54.json"
LEDGER = ACCEPTANCE + "/accepted_jobs_all54.json"
DEVELOPMENT_INDEX = "research_logs/kumar_development_aggregation_20261015/saved_archive_index_run01.json"
REMAINING_AUDIT = "research_logs/kumar_remaining36_audit_20261015/run01/independent_saved_prediction_summary.json"
REMAINING_ORIGINALS = Path("/workspace/private_model_receipts/remaining36-audit-20261015-run01/handoff/original-results")
REMAINING_CONTRACT = "configs/kumar_remaining_source_batch_20261015.json"
DEVELOPMENT = [f"sub-{s}" for s in (1, 4, 7, 10, 13, 16)]
REMAINING = [f"sub-{s}" for s in (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18)]
SEEDS = [20261012, 20261013, 20261014]


def validate_complete_identity(plan, ledger, old_plan, old_ledger, remaining_jobs):
    """Require the exact original18 prefix and ordered remaining36, without edits."""
    expected = old_plan["jobs"] + remaining_jobs
    require(len(expected) == 54 and plan["jobs"] == expected, "All54 plan order/identity differs")
    accepted = ledger["accepted_jobs"]
    require(len(accepted) == 54 and accepted[:18] == old_ledger["accepted_jobs"],
            "Original accepted18 prefix changed or incomplete all54 ledger")
    require([r["job_id"] for r in accepted] == [j["job_id"] for j in expected]
            and len({r["job_id"] for r in accepted}) == 54, "All54 acceptance order differs")
    require(plan["development_subjects"] == DEVELOPMENT and plan["remaining_subjects"] == REMAINING
            and plan["seeds"] == SEEDS, "Frozen cohort or seed definition differs")
    require({(j["subject"], j["seed"]) for j in expected}
            == {(s, seed) for s in DEVELOPMENT + REMAINING for seed in SEEDS},
            "Missing/extra subject or seed")
    for job, entry in zip(expected, accepted, strict=True):
        require(all(entry[k] == job[k] for k in ("job_id", "subject", "seed", "result_key")),
                "Accepted source identity differs")
    return expected


def summarize_cohort(rows, subjects):
    participants = aggregate_participants(rows, subjects, SEEDS)
    return participants, {
        "subjects": subjects, "participants": len(participants), "fits": len(rows),
        "mean_participant_source_validation_balanced_accuracy": float(np.mean(
            [p["mean_source_validation_balanced_accuracy"] for p in participants])),
        "participant_mean_source_validation_BA_range": [
            min(p["mean_source_validation_balanced_accuracy"] for p in participants),
            max(p["mean_source_validation_balanced_accuracy"] for p in participants)],
        "mean_participant_source_validation_CE": float(np.mean([p["mean_source_validation_CE"] for p in participants])),
        "inference": "descriptive only; no hypothesis test or CI on epoch-selected validation",
        "epochs": sum(r["epochs"] for r in rows),
        "optimizer_steps": sum(r["optimizer_steps"] for r in rows),
        "single_class_prediction_fits": sum(r["single_class_prediction"] for r in rows),
        "fits_selected_at_epoch_one": sum(r["selected_epoch"] == 1 for r in rows),
        "fits_reaching_maximum_100_epochs": sum(r["epochs"] == 100 for r in rows),
        "seed_balanced_accuracy_range_per_participant": {
            p["subject"]: p["seed_balanced_accuracy_range"] for p in participants},
        "mean_within_participant_seed_BA_range": float(np.mean([p["seed_balanced_accuracy_range"] for p in participants])),
        "maximum_within_participant_seed_BA_range": max(p["seed_balanced_accuracy_range"] for p in participants),
        "unique_source_validation_trials": 20 * len(participants),
        "saved_prediction_rows_with_repeated_seeds": 20 * len(rows),
    }


def aggregate(output, plan_path=ROOT / PLAN, ledger_path=ROOT / LEDGER):
    output = Path(output)
    require(not output.exists(), "Output exists; preserve prior evidence")
    text_inputs = {}

    def read_json(path):
        path = Path(path)
        raw = path.read_bytes()
        text_inputs[str(path.relative_to(ROOT))] = sha256(raw)
        return json.loads(raw)

    plan = read_json(plan_path)
    ledger = read_json(ledger_path)
    old_plan = read_json(ROOT / OLD_PLAN)
    old_ledger = read_json(ROOT / OLD_LEDGER)
    remaining = read_json(ROOT / REMAINING_CONTRACT)["remaining_jobs"]
    jobs = validate_complete_identity(plan, ledger, old_plan, old_ledger, remaining)
    old_entries = read_json(ROOT / DEVELOPMENT_INDEX)["archives"]
    new_audit = read_json(ROOT / REMAINING_AUDIT)
    require(new_audit["status"] == "passed_saved_prediction_and_checkpoint_integrity_audit",
            "Remaining saved prediction audit did not pass")
    new_by_job = {r["job_id"]: r for r in new_audit["jobs"]}
    require(len(new_by_job) == 36 and set(new_by_job) == {j["job_id"] for j in remaining},
            "Remaining archive audit scope differs")
    entries = old_entries + [{"job_id": j["job_id"],
                              "path": str(REMAINING_ORIGINALS / new_by_job[j["job_id"]]["archive_filename"]),
                              "sha256": new_by_job[j["job_id"]]["archive_sha256"]} for j in remaining]
    require([e["job_id"] for e in entries] == [j["job_id"] for j in jobs], "Archive order differs")
    config_path = plan["training_config"]
    config = read_json(ROOT / config_path)
    config_sha = text_inputs[config_path]
    require(config_sha == plan["training_config_sha256"] == old_plan["training_config_sha256"]
            and config["freeze"]["ready_for_formal_training"] is False, "Frozen training config differs")
    split = read_json(ROOT / config["split_manifest"])["trials"]
    split_sha = text_inputs[config["split_manifest"]]
    replay = read_json(ROOT / REPLAY_RECEIPT)
    replay_objects = [r for r in replay["files"] if r["relative_path"] == "sub-1-seed-20261012-replay-run01.tar"]
    require(len(replay_objects) == 1 and replay_objects[0]["verification"] == "full_get_sha256_verified",
            "First saved-logit replay R2 binding differs")
    rows, archive_evidence, identities = [], [], {}
    for number, (job, accepted, entry) in enumerate(zip(jobs, ledger["accepted_jobs"], entries, strict=True)):
        require(job["training_config_sha256"] == config_sha and job["split_sha256"] == split_sha,
                "Job scientific config/split binding differs")
        expected_sha = replay_objects[0]["sha256"] if number == 0 else accepted["archive_sha256"]
        require(entry["sha256"] == expected_sha, "Archive not bound to accepted bytes")
        data, verified = read_verified_archive(entry["path"], expected_sha)
        weights = json.loads(data["weights.json"])
        require(weights["seed"] == job["seed"] and weights["config"] == config
                and weights["synthetic"] is False, "Saved weights metadata identity differs")
        if number == 0:
            record = read_json(ROOT / "research_logs/kumar_first_gpu_fit_20261014/fit_text_evidence/fit_result.json")
            replay_record = json.loads(data["replay_result.json"])
            require(replay_record["fits"] == 0 and replay_record["query_rows_loaded"] == 0, "First replay scope differs")
        else:
            record = json.loads(data["fit_result.json"])
            require(json.loads(data["job.json"]) == job and record["job_id"] == job["job_id"], "Archive job differs")
        require(record["subject"] == job["subject"] and record["seed"] == job["seed"]
                and record["query_rows_loaded"] == 0 and record["source_train_rows"] == 40
                and record["source_validation_rows"] == 20, "Source scope differs")
        require(record["checkpoint_sha256"] == weights["checkpoint_sha256"] == sha256(data["weights.pt"]),
                "Checkpoint bytes differ")
        label_map = {r["trial_id"]: config["input"]["class_mapping"][r["label"]] for r in split
                     if r["subject"] == job["subject"] and r["role"] == "source_validation" and r["included"]}
        with np.load(io.BytesIO(data["source_validation_predictions.npz"]), allow_pickle=False) as saved:
            require(set(saved.files) == {"logits", "labels", "trial_ids", "loss_float64"}, "Saved prediction schema differs")
            ids, labels = saved["trial_ids"].tolist(), saved["labels"]
            require(len(ids) == len(set(ids)) == 20 and set(ids) == set(label_map)
                    and ids == weights["source_validation_ids"]
                    and np.array_equal(labels, [label_map[t] for t in ids]), "Source validation identity/labels differ")
            metrics, losses = describe_logits(saved["logits"], labels)
            require(np.max(np.abs(losses - saved["loss_float64"])) < 1e-14, "Per-trial CE differs")
        identity = tuple(zip(ids, labels.tolist(), strict=True))
        require(job["subject"] not in identities or identities[job["subject"]] == identity,
                "Source trial identities differ across seeds")
        identities[job["subject"]] = identity
        history = weights["history"]
        require(1 <= len(history) <= 100 and [r["epoch"] for r in history] == list(range(1, len(history) + 1))
                and all(math.isfinite(r["source_validation_loss"]) for r in history), "Selection history differs")
        selected = min(range(len(history)), key=lambda i: history[i]["source_validation_loss"])
        ce = history[selected]["source_validation_loss"]
        require(weights["selected_epoch"] == record["selected_epoch"] == selected + 1
                and record["epochs_executed"] == len(history)
                and weights["optimizer_steps"] == record["optimizer_steps"] == 3 * len(history)
                and weights["source_validation_loss"] == ce, "Checkpoint selection/step accounting differs")
        require(abs(metrics["source_validation_CE_recomputed"] - ce) <= 1e-7, "Frozen CE tolerance exceeded")
        rows.append({"job_id": job["job_id"], "subject": job["subject"], "seed": job["seed"],
                     "cohort": "development6" if job["subject"] in DEVELOPMENT else "remaining12",
                     "epochs": len(history), "selected_epoch": selected + 1, "optimizer_steps": record["optimizer_steps"],
                     "source_validation_CE_recorded": ce, **metrics})
        archive_evidence.append({"job_id": job["job_id"], "archive_path": entry["path"],
                                 "archive_kind": "first_fit_replay" if number == 0 else "original_model",
                                 "accepted_original_model_sha256": accepted["archive_sha256"],
                                 "saved_logits_sha256": sha256(data["source_validation_predictions.npz"]), **verified})
    partitions = {"development6": DEVELOPMENT, "remaining12": REMAINING,
                  "all18_secondary": [f"sub-{s}" for s in range(1, 19)]}
    participant_tables, summaries = {}, {}
    for name, subjects in partitions.items():
        selected_rows = [r for r in rows if r["subject"] in subjects]
        participant_tables[name], summaries[name] = summarize_cohort(selected_rows, subjects)
    require((summaries["all18_secondary"]["epochs"], summaries["all18_secondary"]["optimizer_steps"])
            == (2871, 8613), "All54 epoch/step totals differ")
    require(all(sha256((ROOT / p).read_bytes()) == value for p, value in text_inputs.items()), "Input text changed during analysis")
    require(all(sha256(Path(e["path"]).read_bytes()) == e["sha256"] for e in entries), "Original archive changed during analysis")
    summary = {"status": "all54_saved_source_validation_descriptive_aggregation_complete",
               "cohorts": summaries,
               "participant_aggregation": "equal mean of all three frozen seeds, then equal participant mean",
               "inference": "descriptive only; no hypothesis test or CI on epoch-selected validation",
               "maximum_recorded_vs_saved_CE_absolute_error": max(abs(r["source_validation_CE_recorded"] - r["source_validation_CE_recomputed"]) for r in rows),
               "model_fits_performed": 0, "model_forward_passes_performed": 0, "checkpoint_tensor_loads": 0,
               "EEG_loaded": False, "query_rows_loaded": 0, "seed_selection_performed": False,
               "accepted_ledger_modified": False, "original_archives_unchanged": True,
               "scientific_limits": [
                   "Source validation selected checkpoint epochs. Its BA/CE describe selected scores, not untouched-query generalization; no CI or hypothesis test is computed.",
                   "Development6 and remaining12 are reported separately; all18 is a secondary source-only descriptive combination, not a new test cohort.",
                   "Three seeds share participant trials and do not triple independent sample size. No seed, checkpoint rule or adaptive strategy was selected here.",
                   "No query or target efficacy comparison, skill-retention claim, clinical claim or experimental release follows from this aggregation."]}
    output.mkdir(parents=True)
    write_csv(output / "per_fit_source_validation.csv", rows)
    for name, participants in participant_tables.items():
        write_csv(output / f"per_participant_{name}.csv", participants)
    outputs = {p.name: sha256(p.read_bytes()) for p in output.iterdir()}
    receipt = {"analysis_script_sha256": sha256(Path(__file__).read_bytes()),
               "reused_aggregation_helper_sha256": sha256((ROOT / "scripts/aggregate_kumar_development_saved_results.py").read_bytes()),
               "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "python_version": platform.python_version(), "numpy_version": np.__version__,
               "source_text_sha256": text_inputs, "archives": archive_evidence, "summary": summary, "outputs": outputs}
    for name, value in (("summary.json", summary), ("aggregation_receipt.json", receipt),
                        ("saved_archive_index.json", {"archives": entries})):
        with (output / name).open("x") as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=ROOT / PLAN)
    parser.add_argument("--ledger", type=Path, default=ROOT / LEDGER)
    args = parser.parse_args()
    aggregate(args.output, args.plan, args.ledger)


if __name__ == "__main__":
    main()
