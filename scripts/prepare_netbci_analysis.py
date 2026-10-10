"""Freeze trial/run partitions for a planned NETBCI analysis; never fit a model."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from learning_preserving_bci.datasets.netbci import file_sha256

REPO_ROOT = Path(__file__).resolve().parents[1]


def prepare(config: dict, trials: list[dict]) -> dict:
    reference = config["reference_session"]
    roles = {"reference_train": [], "reference_validation": [], "reference_query": [],
             "target_calibration_pool": [], "target_query": []}
    keys = [item["trial_id"] for item in trials]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate trial identities")
    if len(set(config["session_order"])) != len(config["session_order"]):
        raise ValueError("Duplicate session order entries")
    if reference not in config["session_order"]:
        raise ValueError("Reference session not in the explicit protocol order")
    if {item["session"] for item in trials} != set(config["session_order"]):
        raise ValueError("Configured and observed sessions differ")
    if reference != config["session_order"][0]:
        raise ValueError("Reference must be earliest in the explicit protocol order")
    for item in trials:
        if item["subject"] != config["subject"] or item["session"] not in config["session_order"]:
            raise ValueError("Unplanned subject or session")
        if item["session"] == reference:
            matching = [role for role in ["reference_train", "reference_validation", "reference_query"]
                        if item["run"] in config[role + "_runs"]]
        else:
            matching = []
            if item["run"] in config["target_calibration_runs"]:
                matching.append("target_calibration_pool")
            if item["run"] in config["target_query_runs"]:
                matching.append("target_query")
        if len(matching) != 1:
            raise ValueError("Run is absent from the plan or belongs to multiple partitions")
        roles[matching[0]].append(item)
    group_roles = {}
    for role, items in roles.items():
        if not items:
            raise ValueError(f"Empty partition: {role}")
        for item in items:
            group = (item["subject"], item["session"], item["run"])
            if group in group_roles and group_roles[group] != role:
                raise ValueError("One recording run crosses partitions")
            group_roles[group] = role
    rng = np.random.default_rng(config["seed"])
    reference_classes = {item["label"] for item in roles["reference_train"]}
    if len(reference_classes) < 2:
        raise ValueError("Reference training needs both task classes")
    calibration = {}
    for session in config["session_order"]:
        if session == reference:
            continue
        pool = [item for item in roles["target_calibration_pool"] if item["session"] == session]
        if {item["label"] for item in pool} != reference_classes:
            raise ValueError("Reserved calibration task classes differ from reference")
        selected = []
        for label in sorted({item["label"] for item in pool}):
            candidates = [item for item in pool if item["label"] == label]
            count = config["optional_calibration_trials_per_class"]
            if count > len(candidates) or count < 1:
                raise ValueError("Insufficient reserved calibration class coverage")
            positions = rng.choice(len(candidates), size=count, replace=False)
            selected.extend(candidates[int(index)]["trial_id"] for index in sorted(positions))
        calibration[session] = selected
    summaries = {}
    for role, items in roles.items():
        summaries[role] = {
            "trial_count": len(items), "class_counts": dict(Counter(item["label"] for item in items)),
            "groups": sorted({f'{item["subject"]}/ses-{item["session"]}/run-{item["run"]}' for item in items}),
            "trial_ids": [item["trial_id"] for item in items],
        }
    return {"status": "frozen_plan_only_not_an_executed_model_experiment", "configuration": config,
            "partitions": summaries, "optional_calibration_trial_ids": calibration,
            "all_stored_trials_assigned_once": sum(len(items) for items in roles.values()) == len(trials),
            "session_run_groups_disjoint": True, "trained_model": False,
            "final_reference_fit_count": len(roles["reference_train"]) + len(roles["reference_validation"]),
            "chronology_verified_to_calendar_dates": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs/netbci_cross_session.json")
    parser.add_argument("--bundle", type=Path, default=REPO_ROOT / "data/netbci2026/derived_v1.0.0/sub-1")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "research_logs/netbci2026_analysis_partitions.json")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new output path to preserve the frozen partition")
    config = json.loads(args.config.read_text())
    metadata = json.loads((args.bundle / "metadata.json").read_text())
    if (metadata["provenance"]["dataset_id"] != config["dataset_id"]
            or "v" + metadata["provenance"]["version"] != config["dataset_version"]):
        raise ValueError("Configuration and source dataset versions differ")
    if file_sha256(args.bundle / "epochs.npz") != metadata["epochs_sha256"]:
        raise ValueError("Epoch bundle checksum changed")
    result = prepare(config, metadata["trials"])
    result["config_sha256"] = file_sha256(args.config)
    result["trial_metadata_sha256"] = file_sha256(args.bundle / "metadata.json")
    result["source_provenance"] = metadata["provenance"]
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({role: {key: value for key, value in summary.items() if key != "trial_ids"}
                      for role, summary in result["partitions"].items()}, indent=2))


if __name__ == "__main__":
    main()
