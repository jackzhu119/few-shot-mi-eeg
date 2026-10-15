"""Describe all frozen development fits from saved source-validation logits only.

This script never imports a decoder, loads EEG or checkpoint tensors, fits a
model, performs a model forward pass, or evaluates a query. Source validation
selected the checkpoint epoch, so these are development descriptions only.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PLAN = "configs/kumar_development_queue_plan_20261014.json"
LEDGER = "research_logs/kumar_development_queue_20261014/accepted_jobs.json"
REPLAY_RECEIPT = "research_logs/kumar_first_fit_replay_20261014/r2_full_get_receipt.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_verified_archive(path, expected_sha):
    """Hash every original byte/member; read tar members without extraction."""
    raw = Path(path).read_bytes()
    require(len(raw) <= 16 * 1024**2, "Archive exceeds frozen model/replay size bound")
    require(sha256(raw) == expected_sha, "Archive SHA256 differs")
    data = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and ".." not in name.parts,
                    "Unsafe archive member")
            require(member.name not in data, "Duplicate archive member")
            require(member.size <= 16 * 1024**2, "Oversize archive member")
            data[member.name] = archive.extractfile(member).read()
            require(len(data[member.name]) == member.size, "Incomplete archive member")
    manifest = json.loads(data["manifest.json"])
    require(len({item["path"] for item in manifest["files"]}) == len(manifest["files"]),
            "Duplicate manifest member")
    require(set(data) == {item["path"] for item in manifest["files"]} | {"manifest.json"},
            "Manifest/member scope differs")
    for item in manifest["files"]:
        value = data[item["path"]]
        require(len(value) == item["bytes"] and sha256(value) == item["sha256"],
                "Archive member length/SHA256 differs")
    return data, {"bytes": len(raw), "sha256": sha256(raw),
                  "payload_members_verified": len(manifest["files"])}


def describe_logits(logits, labels):
    """Argmax has the frozen no-tuning rule; both class recalls enter BA."""
    logits = np.asarray(logits, dtype=np.float64)
    labels = np.asarray(labels)
    require(logits.ndim == 2 and logits.shape[1] == 2 and labels.shape == (len(logits),),
            "Invalid saved prediction shape")
    require(np.isfinite(logits).all() and set(labels.tolist()) == {0, 1},
            "Nonfinite predictions or missing binary class")
    prediction = logits.argmax(axis=1)
    losses = np.logaddexp(logits[:, 0], logits[:, 1]) - logits[np.arange(len(labels)), labels]
    recalls = [float(np.mean(prediction[labels == label] == label)) for label in (0, 1)]
    return {
        "source_validation_CE_recomputed": float(np.mean(losses)),
        "source_validation_balanced_accuracy": float(np.mean(recalls)),
        "source_validation_accuracy": float(np.mean(prediction == labels)),
        "left_recall": recalls[0], "right_recall": recalls[1],
        "left_label_count": int(np.sum(labels == 0)),
        "right_label_count": int(np.sum(labels == 1)),
        "left_prediction_count": int(np.sum(prediction == 0)),
        "right_prediction_count": int(np.sum(prediction == 1)),
        "single_class_prediction": bool(np.unique(prediction).size == 1),
    }, losses


def aggregate_participants(rows, subjects, seeds):
    """All seeds have equal weight inside each independent participant."""
    require(len(rows) == len(subjects) * len(seeds), "Incomplete fit cohort")
    require(len({(row["subject"], row["seed"]) for row in rows}) == len(rows),
            "Duplicate subject/seed")
    participants = []
    for subject in subjects:
        selected = [row for row in rows if row["subject"] == subject]
        require({row["seed"] for row in selected} == set(seeds), "Missing or extra seed")
        ce = [row["source_validation_CE_recorded"] for row in selected]
        ba = [row["source_validation_balanced_accuracy"] for row in selected]
        participants.append({
            "subject": subject, "seeds_included": len(selected),
            "mean_source_validation_CE": float(np.mean(ce)),
            "minimum_seed_CE": min(ce), "maximum_seed_CE": max(ce),
            "mean_source_validation_balanced_accuracy": float(np.mean(ba)),
            "minimum_seed_balanced_accuracy": min(ba),
            "maximum_seed_balanced_accuracy": max(ba),
            "seed_balanced_accuracy_range": max(ba) - min(ba),
            "mean_source_validation_accuracy": float(np.mean(
                [row["source_validation_accuracy"] for row in selected])),
            "single_class_prediction_fits": sum(row["single_class_prediction"]
                                                for row in selected),
            "epochs_total": sum(row["epochs"] for row in selected),
            "optimizer_steps_total": sum(row["optimizer_steps"] for row in selected),
        })
    require({row["subject"] for row in rows} == set(subjects), "Unexpected participant")
    return participants


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(index_path, output):
    output = Path(output)
    require(not output.exists(), "Output already exists; preserve earlier analysis")
    plan_raw = (ROOT / PLAN).read_bytes()
    plan = json.loads(plan_raw)
    ledger_raw = (ROOT / LEDGER).read_bytes()
    ledger = json.loads(ledger_raw)
    jobs = plan["jobs"]
    require(len(jobs) == 18 and [item["job_id"] for item in ledger["accepted_jobs"]]
            == [job["job_id"] for job in jobs], "All18 ordered acceptance is required")
    index_raw = Path(index_path).read_bytes()
    index = json.loads(index_raw)
    entries = index["archives"]
    require([item["job_id"] for item in entries] == [job["job_id"] for job in jobs],
            "Saved-archive index differs from frozen order")
    config_path = plan["training_config"]
    config_raw = (ROOT / config_path).read_bytes()
    config = json.loads(config_raw)
    require(sha256(config_raw) == plan["training_config_sha256"], "Config hash differs")
    require(config["freeze"]["ready_for_formal_training"] is False, "Formal gate opened")
    split_path = config["split_manifest"]
    split_raw = (ROOT / split_path).read_bytes()
    split = json.loads(split_raw)["trials"]
    replay_receipt_raw = (ROOT / REPLAY_RECEIPT).read_bytes()
    replay_object = next(item for item in json.loads(replay_receipt_raw)["files"]
                         if item["relative_path"] == "sub-1-seed-20261012-replay-run01.tar")
    require(replay_object["verification"] == "full_get_sha256_verified",
            "First replay lacks verified archived identity")
    rows, provenance, identities = [], [], {}
    for number, (job, accepted, entry) in enumerate(zip(jobs, ledger["accepted_jobs"], entries)):
        require(job["training_config_sha256"] == sha256(config_raw)
                and job["split_sha256"] == sha256(split_raw), "Frozen input/config binding differs")
        expected_sha = replay_object["sha256"] if number == 0 else accepted["archive_sha256"]
        require(entry["sha256"] == expected_sha, "Archive index is not bound to accepted bytes")
        data, verified = read_verified_archive(entry["path"], expected_sha)
        weights = json.loads(data["weights.json"])
        require(weights["seed"] == job["seed"] and weights["config"] == config
                and weights["synthetic"] is False, "Saved checkpoint identity/config differs")
        if number == 0:
            record_path = ROOT / "research_logs/kumar_first_gpu_fit_20261014/fit_text_evidence/fit_result.json"
            record_raw = record_path.read_bytes()
            record = json.loads(record_raw)
            replay = json.loads(data["replay_result.json"])
            require(replay["fits"] == 0 and replay["query_rows_loaded"] == 0,
                    "First replay scope differs")
            verified["first_fit_text_record_path"] = str(record_path.relative_to(ROOT))
            verified["first_fit_text_record_sha256"] = sha256(record_raw)
        else:
            record = json.loads(data["fit_result.json"])
            require(json.loads(data["job.json"]) == job and record["job_id"] == job["job_id"],
                    "Job identity differs")
        require(record["subject"] == job["subject"] and record["seed"] == job["seed"]
                and record["query_rows_loaded"] == 0 and record["source_train_rows"] == 40
                and record["source_validation_rows"] == 20, "Unexpected fit partition/scope")
        require(record["checkpoint_sha256"] == weights["checkpoint_sha256"]
                == sha256(data["weights.pt"]), "Checkpoint hash binding differs")
        selected_trials = [item for item in split if item["subject"] == job["subject"]
                           and item["role"] == "source_validation" and item["included"]]
        label_map = {item["trial_id"]: config["input"]["class_mapping"][item["label"]]
                     for item in selected_trials}
        with np.load(io.BytesIO(data["source_validation_predictions.npz"]), allow_pickle=False) as saved:
            require(set(saved.files) == {"logits", "labels", "trial_ids", "loss_float64"},
                    "Unexpected NPZ payload")
            ids = saved["trial_ids"].tolist()
            labels = saved["labels"]
            require(len(ids) == len(set(ids)) == 20 and set(ids) == set(label_map)
                    and ids == weights["source_validation_ids"]
                    and np.array_equal(labels, [label_map[key] for key in ids]),
                    "Frozen source-validation IDs/labels differ")
            metrics, losses = describe_logits(saved["logits"], labels)
            require(np.max(np.abs(losses - saved["loss_float64"])) < 1e-14,
                    "Saved per-trial loss differs")
        identity = tuple(zip(ids, labels.tolist()))
        require(job["subject"] not in identities or identities[job["subject"]] == identity,
                "Seeds do not share identical source-validation identities")
        identities[job["subject"]] = identity
        history = weights["history"]
        require([item["epoch"] for item in history] == list(range(1, len(history) + 1))
                and all(math.isfinite(item["source_validation_loss"]) for item in history),
                "Invalid selection history")
        selected = min(range(len(history)), key=lambda i: history[i]["source_validation_loss"])
        ce = history[selected]["source_validation_loss"]
        require(weights["selected_epoch"] == record["selected_epoch"] == selected + 1
                and record["epochs_executed"] == len(history)
                and weights["optimizer_steps"] == record["optimizer_steps"] == 3 * len(history)
                and weights["source_validation_loss"] == ce, "Frozen selection history differs")
        require(abs(metrics["source_validation_CE_recomputed"] - ce) <= 1e-7,
                "Saved CE exceeds unchanged replay tolerance")
        rows.append({"job_id": job["job_id"], "subject": job["subject"], "seed": job["seed"],
                     "epochs": len(history), "selected_epoch": selected + 1,
                     "optimizer_steps": record["optimizer_steps"],
                     "source_validation_CE_recorded": ce, **metrics})
        provenance.append({"job_id": job["job_id"], "archive_path": entry["path"],
                           "archive_kind": "first_fit_replay" if number == 0 else "original_model",
                           "accepted_original_model_sha256": accepted["archive_sha256"],
                           "saved_logits_sha256": sha256(data["source_validation_predictions.npz"]),
                           "weights_metadata_sha256": sha256(data["weights.json"]), **verified})
    participants = aggregate_participants(rows, plan["development_subjects"], plan["seeds"])
    summary = {
        "status": "saved_source_validation_descriptive_aggregation_complete",
        "independent_participants": len(participants), "fits_included": len(rows),
        "seeds_per_participant": len(plan["seeds"]), "all_frozen_seeds_included": True,
        "unique_source_validation_trials": sum(len(ids) for ids in identities.values()),
        "saved_prediction_rows_with_repeated_seeds": 20 * len(rows),
        "mean_participant_source_validation_CE": float(np.mean(
            [row["mean_source_validation_CE"] for row in participants])),
        "uniform_binary_predictor_CE_reference": math.log(2.0),
        "mean_participant_source_validation_balanced_accuracy": float(np.mean(
            [row["mean_source_validation_balanced_accuracy"] for row in participants])),
        "mean_participant_source_validation_accuracy": float(np.mean(
            [row["mean_source_validation_accuracy"] for row in participants])),
        "single_class_prediction_fits": sum(row["single_class_prediction"] for row in rows),
        "fits_selected_at_epoch_one": sum(row["selected_epoch"] == 1 for row in rows),
        "fits_reaching_maximum_100_epochs": sum(row["epochs"] == 100 for row in rows),
        "total_epochs": sum(row["epochs"] for row in rows),
        "total_optimizer_steps": sum(row["optimizer_steps"] for row in rows),
        "maximum_recorded_vs_saved_CE_absolute_error": max(
            abs(row["source_validation_CE_recorded"] - row["source_validation_CE_recomputed"])
            for row in rows),
        "model_fits_performed": 0, "model_forward_passes_performed": 0,
        "EEG_loaded": False, "query_rows_loaded": 0, "seed_selection_performed": False,
        "participant_aggregation": "equal mean of all three frozen seeds, then equal participant mean",
        "inference": "descriptive only; no hypothesis test or CI on epoch-selected validation",
        "scientific_limits": [
            "Source validation selected checkpoint epoch; these scores are not an independent test.",
            "Six development identities; three seeds do not increase participant n to eighteen.",
            "No target-session query evaluated and no adaptive policy validated.",
            "No matched comparison with existing CPU query baselines is available here.",
            "Offline source decoding does not demonstrate human learning, retention or clinical effect.",
        ],
    }
    output.mkdir(parents=True)
    write_csv(output / "per_fit_source_validation.csv", rows)
    write_csv(output / "per_participant_source_validation.csv", participants)
    files = {PLAN: sha256(plan_raw), LEDGER: sha256(ledger_raw), config_path: sha256(config_raw),
             split_path: sha256(split_raw), REPLAY_RECEIPT: sha256(replay_receipt_raw)}
    receipt = {"analysis_script_sha256": sha256(Path(__file__).read_bytes()),
               "input_archive_index_sha256": sha256(index_raw),
               "source_git_commit": subprocess.check_output(
                   ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "python_version": platform.python_version(), "numpy_version": np.__version__,
               "source_text_sha256": files, "archives": provenance, "summary": summary,
               "outputs": {name: sha256((output / name).read_bytes()) for name in
                           ("per_fit_source_validation.csv", "per_participant_source_validation.csv")}}
    (output / "aggregation_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-index", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    aggregate(args.archive_index, args.output)


if __name__ == "__main__":
    main()
