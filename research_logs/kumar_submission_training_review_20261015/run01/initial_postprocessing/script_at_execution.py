"""Review immutable saved EEGNet histories and metrics, without loading a model.

This is descriptive submission-stage postprocessing. Archive binary members are
streamed only to SHA256; only explicitly named JSON/text members are parsed.
No EEG, query arrays, tensors, optimizer, forward call, or seed selection is used.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = "research_logs/kumar_remaining36_acceptance_20261015/run01"
SOURCE = "research_logs/kumar_all54_source_aggregation_20261015/run01"
QUERY = "research_logs/kumar_frozen_query_comparison_20261015/run01"
TEXT_MEMBERS = {"weights.json", "fit_result.json", "training_config.json", "training.log"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verified_text_archive(path, expected_sha):
    """Verify all original members; return only allowlisted text, never tensors."""
    path = Path(path)
    require(file_digest(path) == expected_sha, f"Original archive differs: {path.name}")
    hashes, text, lengths = {}, {}, {}
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        names = [item.name for item in members]
        require(len(names) == len(set(names)), "Repeated archive member")
        for member in members:
            name = PurePosixPath(member.name)
            require(member.isfile() and len(name.parts) == 1
                    and not name.is_absolute() and name.name not in (".", ".."),
                    "Unsafe archive member")
            with archive.extractfile(member) as stream:
                if member.name in TEXT_MEMBERS or member.name == "manifest.json":
                    raw = stream.read()
                    hashes[member.name] = digest(raw)
                    text[member.name] = raw
                else:
                    hashes[member.name] = hashlib.file_digest(stream, "sha256").hexdigest()
            lengths[member.name] = member.size
    require("manifest.json" in text and TEXT_MEMBERS <= text.keys(), "Missing saved text")
    entries = json.loads(text.pop("manifest.json"))["files"]
    require(len(entries) == len({item["path"] for item in entries}), "Duplicate manifest identity")
    require({item["path"] for item in entries} == set(names) - {"manifest.json"},
            "Manifest coverage differs")
    for entry in entries:
        require(entry["sha256"] == hashes[entry["path"]]
                and entry["bytes"] == lengths[entry["path"]], "Manifest integrity differs")
    require(file_digest(path) == expected_sha, "Original archive changed during review")
    return text, {"archive_filename": path.name, "archive_sha256": expected_sha,
                  "archive_bytes": path.stat().st_size, "payload_members": len(entries),
                  "text_member_sha256": {name: hashes[name] for name in TEXT_MEMBERS},
                  "manifest_sha256": hashes["manifest.json"],
                  "binary_handling": "streamed to SHA256 only; never parsed or loaded"}


def check_history(weights, fit, config):
    history = weights["history"]
    maximum = config["optimization"]["max_epochs"]
    stopping = config["optimization"]["early_stopping"]
    require(stopping["min_delta"] == 0 and stopping["ties"] == "earliest_epoch",
            "Frozen selection convention differs")
    require(1 <= len(history) <= maximum, "Missing/oversized epoch history")
    best, selected, stale = math.inf, None, 0
    for number, row in enumerate(history, 1):
        require(row["epoch"] == number and all(math.isfinite(row[key]) and row[key] >= 0
                for key in ("source_train_loss", "source_validation_loss")),
                "Nonconsecutive or nonfinite saved history")
        if row["source_validation_loss"] < best:
            best, selected, stale = row["source_validation_loss"], number, 0
        else:
            stale += 1
        require(number == len(history) or stale < stopping["patience"],
                "A fit continued after frozen patience was exhausted")
    require(selected == weights["selected_epoch"] == fit["selected_epoch"]
            and best == weights["source_validation_loss"], "Saved epoch selection differs")
    require(fit["epochs_executed"] == len(history)
            and weights["optimizer_steps"] == fit["optimizer_steps"] == 3 * len(history),
            "Saved epoch/optimizer accounting differs")
    require(len(history) == maximum or stale == stopping["patience"],
            "A saved fit has no frozen stopping reason")
    return history, (f"maximum_{maximum}_epochs" if len(history) == maximum
                     else f"patience_{stopping['patience']}")


def write_csv(path, rows):
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mean(values):
    return statistics.mean(values)


def run(output, archives):
    require(not output.exists(), "Output exists; preserve earlier evidence")
    inputs = {}

    def read(path, json_input=False):
        raw = (ROOT / path).read_bytes()
        inputs[path] = {"bytes": len(raw), "sha256": digest(raw)}
        return json.loads(raw) if json_input else list(csv.DictReader(io.StringIO(raw.decode())))

    plan = read(ACCEPTANCE + "/source_model_plan_all54.json", True)
    ledger = read(ACCEPTANCE + "/accepted_jobs_all54.json", True)
    config = read(plan["training_config"], True)
    source_rows = read(SOURCE + "/per_fit_source_validation.csv")
    query_rows = read(QUERY + "/eegnet_per_seed_session.csv")
    endpoint_rows = read(QUERY + "/per_participant_endpoints.csv")
    trainer = ROOT / "scripts/train_kumar_eegnet.py"
    inputs[str(trainer.relative_to(ROOT))] = {
        "bytes": trainer.stat().st_size, "sha256": file_digest(trainer)}
    require(inputs[plan["training_config"]]["sha256"] == plan["training_config_sha256"],
            "Frozen scientific configuration differs")
    require(len(plan["jobs"]) == len(ledger["accepted_jobs"]) == len(source_rows) == 54,
            "All54 identity scope differs")
    by_source = {row["job_id"]: row for row in source_rows}
    require(len(by_source) == 54, "Repeated source fit")
    by_query = {(row["subject"], int(row["seed"]), row["session"]): row for row in query_rows}
    require(len(by_query) == len(query_rows) == 324, "Repeated/missing seed-session query metrics")
    require(plan["seeds"] == [20261012, 20261013, 20261014], "Fixed seeds differ")
    epochs, fits, archive_evidence, seed_endpoints = [], [], [], []
    for job, accepted in zip(plan["jobs"], ledger["accepted_jobs"], strict=True):
        require(all(job[key] == accepted[key] for key in ("subject", "seed", "job_id")),
                "Accepted job identity differs")
        filename = f"{job['subject']}-seed-{job['seed']}-run01.tar"
        text, evidence = verified_text_archive(archives / filename, accepted["archive_sha256"])
        weights, fit = json.loads(text["weights.json"]), json.loads(text["fit_result.json"])
        require(json.loads(text["training_config.json"]) == weights["config"] == config,
                "Original model scientific configuration differs")
        require(weights["synthetic"] is False and weights["seed"] == job["seed"]
                and fit["subject"] == job["subject"] and fit["seed"] == job["seed"]
                and fit["source_train_rows"] == 40 and fit["source_validation_rows"] == 20
                and fit["query_rows_loaded"] == 0, "Saved model scope differs")
        history, reason = check_history(weights, fit, config)
        source = by_source[job["job_id"]]
        require(int(source["selected_epoch"]) == weights["selected_epoch"]
                and int(source["epochs"]) == len(history)
                and float(source["source_validation_CE_recorded"]) == weights["source_validation_loss"],
                "Previously audited source table differs")
        identity = {"subject": job["subject"], "cohort": source["cohort"], "seed": job["seed"],
                    "job_id": job["job_id"]}
        epochs.extend({**identity, **row} for row in history)
        initial, final = history[0], history[-1]
        selected = history[weights["selected_epoch"] - 1]
        per_seed = [by_query[(job["subject"], job["seed"], f"ses-{session}")]
                    for session in range(6)]
        require(all(int(row["n_query_trials"]) > 0 for row in per_seed), "Empty saved query group")
        source_query = float(per_seed[0]["balanced_accuracy"])
        target_query = mean(float(row["balanced_accuracy"]) for row in per_seed[1:])
        endpoint = {**identity, "source_query_BA": source_query,
                    "target_five_session_mean_query_BA": target_query,
                    "target_minus_source_BA": target_query - source_query,
                    "source_collapsed_seed_sessions": int(per_seed[0]["class_collapse"] == "True"),
                    "target_collapsed_seed_sessions": sum(row["class_collapse"] == "True"
                                                          for row in per_seed[1:])}
        seed_endpoints.append(endpoint)
        fits.append({**identity, "epochs": len(history), "optimizer_steps": fit["optimizer_steps"],
                     "selected_epoch": weights["selected_epoch"], "stopping_reason": reason,
                     "train_CE_epoch1": initial["source_train_loss"],
                     "train_CE_selected_epoch": selected["source_train_loss"],
                     "train_CE_last_epoch": final["source_train_loss"],
                     "validation_CE_epoch1": initial["source_validation_loss"],
                     "validation_CE_selected_epoch": selected["source_validation_loss"],
                     "validation_CE_last_epoch": final["source_validation_loss"],
                     "train_CE_last_minus_first": final["source_train_loss"] - initial["source_train_loss"],
                     "validation_CE_last_minus_first": final["source_validation_loss"]
                     - initial["source_validation_loss"],
                     "validation_CE_first_minus_selected": initial["source_validation_loss"]
                     - selected["source_validation_loss"],
                     "validation_BA_selected_checkpoint": float(source["source_validation_balanced_accuracy"]),
                     "validation_class_collapse": source["single_class_prediction"] == "True",
                     "training_log_bytes": len(text["training.log"]), **{
                         key: value for key, value in endpoint.items() if key not in identity}})
        archive_evidence.append({**identity, **evidence})
    require(len(epochs) == 2871 and sum(row["optimizer_steps"] for row in fits) == 8613,
            "Previously fixed all54 training totals differ")
    participants = []
    for subject in plan["development_subjects"] + plan["remaining_subjects"]:
        selected = [row for row in seed_endpoints if row["subject"] == subject]
        require(len(selected) == 3 and {row["seed"] for row in selected} == set(plan["seeds"]),
                "A participant is missing a fixed seed")
        reference = [row for row in endpoint_rows if row["subject"] == subject
                     and row["method"] == "always_frozen_eegnet"]
        require(len(reference) == 1, "Saved participant endpoint is missing/duplicated")
        item = {"subject": subject, "cohort": selected[0]["cohort"], "seeds": 3,
                "source_query_BA": mean(row["source_query_BA"] for row in selected),
                "target_five_session_mean_query_BA": mean(
                    row["target_five_session_mean_query_BA"] for row in selected),
                "target_mean_BA_seed_range": max(row["target_five_session_mean_query_BA"]
                                                 for row in selected)
                - min(row["target_five_session_mean_query_BA"] for row in selected),
                "source_BA_seed_range": max(row["source_query_BA"] for row in selected)
                - min(row["source_query_BA"] for row in selected)}
        item["target_minus_source_BA"] = item["target_five_session_mean_query_BA"] - item["source_query_BA"]
        require(abs(item["source_query_BA"] - float(reference[0]["source_query_BA"])) < 1e-14
                and abs(item["target_five_session_mean_query_BA"]
                        - float(reference[0]["target_five_session_mean_BA"])) < 1e-14,
                "Participant endpoint does not reproduce saved all-seed aggregation")
        participants.append(item)
    summaries = []
    for cohort in ("development6", "remaining12", "all18_secondary"):
        current = [row for row in fits if cohort == "all18_secondary" or row["cohort"] == cohort]
        people = [row for row in participants if cohort == "all18_secondary" or row["cohort"] == cohort]
        summaries.append({"cohort": cohort, "participants": len(people), "source_models": len(current),
                          "epochs": sum(row["epochs"] for row in current),
                          "optimizer_steps": sum(row["optimizer_steps"] for row in current),
                          "selected_epoch1_fits": sum(row["selected_epoch"] == 1 for row in current),
                          "reached_epoch100_fits": sum(row["epochs"] == 100 for row in current),
                          "median_epochs": statistics.median(row["epochs"] for row in current),
                          "median_selected_epoch": statistics.median(row["selected_epoch"] for row in current),
                          "train_CE_last_lower_than_first_fits": sum(row["train_CE_last_minus_first"] < 0
                                                                    for row in current),
                          "validation_CE_last_higher_than_first_fits": sum(
                              row["validation_CE_last_minus_first"] > 0 for row in current),
                          "selected_validation_CE_at_or_above_log2_fits": sum(
                              row["validation_CE_selected_epoch"] >= math.log(2) for row in current),
                          "median_train_CE_first": statistics.median(row["train_CE_epoch1"] for row in current),
                          "median_train_CE_last": statistics.median(row["train_CE_last_epoch"] for row in current),
                          "median_validation_CE_first": statistics.median(
                              row["validation_CE_epoch1"] for row in current),
                          "median_validation_CE_selected": statistics.median(
                              row["validation_CE_selected_epoch"] for row in current),
                          "median_validation_CE_last": statistics.median(
                              row["validation_CE_last_epoch"] for row in current),
                          "selected_validation_class_collapse_fits": sum(
                              row["validation_class_collapse"] for row in current),
                          "source_query_collapsed_seed_sessions": sum(
                              row["source_collapsed_seed_sessions"] for row in current),
                          "target_query_collapsed_seed_sessions": sum(
                              row["target_collapsed_seed_sessions"] for row in current),
                          "mean_participant_source_query_BA": mean(row["source_query_BA"] for row in people),
                          "mean_participant_target_query_BA": mean(
                              row["target_five_session_mean_query_BA"] for row in people),
                          "mean_participant_target_minus_source_BA": mean(
                              row["target_minus_source_BA"] for row in people),
                          "mean_participant_target_seed_range": mean(
                              row["target_mean_BA_seed_range"] for row in people),
                          "maximum_participant_target_seed_range": max(
                              row["target_mean_BA_seed_range"] for row in people)})
    require(len(archive_evidence) == 54 and len(participants) == 18, "Final identity coverage differs")
    for path, info in inputs.items():
        require(file_digest(ROOT / path) == info["sha256"], "A saved text input changed")
    output.mkdir(parents=True)
    for filename, rows in (("all_saved_epoch_curves.csv", epochs), ("per_fit_training_review.csv", fits),
                           ("per_seed_source_target_query.csv", seed_endpoints),
                           ("per_participant_source_target_query.csv", participants),
                           ("cohort_training_review.csv", summaries)):
        write_csv(output / filename, rows)
    receipt = {
        "status": "saved_text_training_review_passed", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "descriptive postprocessing of saved histories/metrics; no model or EEG load",
        "git_HEAD_at_execution": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": file_digest(Path(__file__)), "inputs": inputs, "archives": archive_evidence,
        "source_models": 54, "participants": 18, "epoch_history_rows": len(epochs),
        "complete_epoch_histories": 54, "missing_epoch_histories": 0,
        "query_metrics_rows_reused": len(query_rows), "new_forward_calls": 0, "new_fits": 0,
        "model_binary_loads": 0, "new_query_array_reads": 0, "seed_exclusions": [],
        "notes": ["54 source models are 18 participants by three fixed seeds, not 54 independent participants.",
                  "Source validation selected the epoch; it is not an independent performance endpoint.",
                  "Train loss is the batch-weighted training-mode CE during optimization; validation uses eval mode.",
                  "Thus train/validation CE differences are descriptive trajectories, not a calibrated generalization gap.",
                  "No seed selection, newly fitted model, new forward, inferential CI or hypothesis test was added.",
                  "An empty training.log is not evidence of zero execution; all54 weights.json histories are complete.",
                  "Historical fit_result/manifest backup flags remain unchanged; acceptance is read from the real ledger."],
        "outputs": {path.name: {"bytes": path.stat().st_size, "sha256": file_digest(path)}
                    for path in sorted(output.iterdir())},
    }
    (output / "review_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archives", type=Path, default=Path(
        "/workspace/private_model_receipts/frozen-query-originals-54"))
    args = parser.parse_args()
    run(args.output, args.archives)


if __name__ == "__main__":
    main()
