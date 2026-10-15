"""Validate the closed checkpoint-reuse proposal using JSON metadata only.

There is deliberately no execute flag, tensor/data loader or training import.
This checker cannot turn a proposal or a review hash into execution permission.
"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "configs/kumar_eegnet_formal_freeze_proposal_20261015.json"
MISSING = (
    "actual_parent_review_receipt",
    "final_operational_config_and_detached_sha256",
    "final_operational_freeze_canonical_sha256",
    "approved_36_source_fit_entry_and_contract",
    "remaining_source_input_full_verification_receipt",
    "current_runtime_disk_and_software_acceptance",
    "new_absolute_total_wall_deadline_and_cost_scope",
    "off_Pod_export_and_R2_acceptance_contract",
    "query_specific_checkpoint_reuse_entry_and_input_scope",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned(reference, root):
    path = (root / reference["path"]).resolve()
    require(path.is_relative_to(root.resolve()), "Pinned path outside repository")
    require(digest(path) == reference["sha256"], "Pinned input changed: " + reference["path"])
    return path


def check(proposal, root=ROOT):
    require(proposal["status"] == "proposal_only_separate_parent_review_required",
            "This checker accepts a closed proposal only")
    require(all(value is False for value in proposal["execution_permissions"].values()),
            "Execution permissions must remain closed")
    require(set(proposal["unresolved_execution_bindings"]) == set(MISSING)
            and all(value is None for value in
                    proposal["unresolved_execution_bindings"].values()),
            "Missing execution fields must remain explicit; freeze separately")
    stages = proposal["stage_binding_applicability"]
    require(stages["remaining36_source_fits"]["requires"] == list(MISSING[:-1])
            and stages["existing18_source_validation_replay"]["requires"]
            == [MISSING[i] for i in (0, 1, 2, 5)]
            and stages["query_evaluation"]["requires"]
            == [MISSING[i] for i in (0, 1, 2, 5, 6, 7, 8)],
            "Stage-specific freeze scope changed")
    pins = {key: pinned(value, root) for key, value in proposal["pinned_inputs"].items()}
    def read(name):
        return json.loads(pins[name].read_text())
    science, protocol = read("checkpoint_training_config"), read("protocol")
    plan, ledger = read("accepted_plan"), read("accepted_ledger")["accepted_jobs"]
    require(not science["freeze"]["ready_for_formal_training"]
            and all(science["freeze"][key] is None for key in
                    ("protocol_config_sha256", "split_manifest_sha256",
                     "frozen_training_config_sha256")), "Historical scientific freeze changed")
    require(len(ledger) == 18 and [row["job_id"] for row in ledger]
            == [row["job_id"] for row in plan["jobs"]], "Accepted eighteen must stay complete")
    require(proposal["reuse"]["job_ids"] == [row["job_id"] for row in ledger]
            and proposal["reuse"]["new_fits"] == 0
            and proposal["reuse"]["optimizer_instances"] == 0
            and proposal["reuse"]["query_adapter_implemented"] is False,
            "Reuse scope changed")
    inventory = read("accepted_checkpoint_inventory")["models"]
    require(len(inventory) == 18, "Incomplete checkpoint inventory")
    for entry, model in zip(ledger, inventory):
        require((entry["job_id"], entry["subject"], entry["seed"], entry["archive_sha256"],
                 entry["result_key"]) ==
                (model["job_id"], model["subject"], model["seed"],
                 model["original_model_archive_sha256"], model["original_result_key"]),
                "Checkpoint inventory identity changed")
        require(model["action"] == "reuse_existing_accepted_checkpoint_never_fit",
                "Accepted checkpoint must never refit")
    remaining = proposal["remaining_source_training_proposal"]
    require(remaining["subjects"] == protocol["final_test_subjects"]
            and remaining["seeds"] == science["seeds"] == plan["seeds"],
            "Remaining cohort or seeds changed")
    expected = [(subject, seed) for subject in protocol["final_test_subjects"]
                for seed in science["seeds"]]
    require([(job["subject"], job["seed"]) for job in remaining["jobs"]] == expected
            and len(expected) == 36, "Remaining frozen order changed")
    accepted_ids = {entry["job_id"] for entry in ledger}
    for job in remaining["jobs"]:
        identity = {key: job[key] for key in
                    ("subject", "seed", "training_config_sha256", "split_sha256")}
        actual = hashlib.sha256(json.dumps(identity, sort_keys=True,
                                          separators=(",", ":")).encode()).hexdigest()
        require(actual == job["job_id"] and actual not in accepted_ids
                and identity["training_config_sha256"] == digest(pins["checkpoint_training_config"])
                and identity["split_sha256"] == digest(pins["split"])
                and job["action"] == "proposal_only_not_authorized", "Future job identity changed")
    inputs = read("remaining_source_inputs")
    require(inputs["status"] == "proposal_only_unapproved"
            and inputs["execution_enabled"] is False
            and inputs["query_access"] is False
            and inputs["query_EEG_file_count"] == inputs["query_label_file_count"] == 0,
            "Source input proposal opened query")
    files = inputs["files"]
    paths = [entry["relative_path"] for entry in files]
    require(len(paths) == len(set(paths)) == 253
            and sum(entry["bytes"] for entry in files) == 196740994,
            "Source-only input count/bytes changed")
    edfs = {path for path in paths if path.endswith(".edf")}
    require(edfs == {
        f"{subject}/ses-0/eeg/{subject}_ses-0_task-imagery_run-{run}_eeg.edf"
        for subject in protocol["final_test_subjects"] for run in range(3)
    }, "Source input contains a query/target EDF or wrong participant")
    require(all(path == "dataset_description.json" or
                path.split("/")[0] in protocol["final_test_subjects"] for path in paths),
            "Input proposal overlaps accepted development cohort")
    limits = remaining["compute_count_limits"]
    require(limits == {"fits": 36, "epochs_per_fit": 100, "steps_per_epoch": 3,
                       "epochs_total": 3600, "optimizer_steps_total": 10800,
                       "historical_all54_epochs_limit": 5400,
                       "historical_all54_optimizer_steps_limit": 16200},
            "Frozen count budget changed")
    require(remaining["new_run_total_wall_seconds"] is None
            and remaining["new_run_total_cost_usd"] is None
            and remaining["old_19800_second_deadline_reused"] is False,
            "Old run deadline cannot authorize a new run")
    require(proposal["scientific_decision"]["adaptive_strategy_supported"] is False
            and proposal["scientific_decision"]["model_or_threshold_search"] is False,
            "No strategy is released by source development BA")
    stats = proposal["future_evaluation_statistics_proposal"]
    require(stats["independent_unit"] == "published_participant_identity"
            and stats["seed_aggregation"] == "equal_mean_all_three_within_participant_session"
            and stats["bootstrap_replicates"] == 10000 and stats["bootstrap_seed"] == 42
            and stats["existing_CPU_primary_comparison_unchanged"] is True,
            "Frozen aggregation/primary contrast changed")
    return {"status": "proposal_valid_execution_closed", "accepted_checkpoints": 18,
            "future_source_fits_proposed": 36, "future_source_input_files": 253,
            "future_source_input_bytes": 196740994, "new_fits_authorized": 0,
            "checkpoint_tensors_loaded": False, "signals_loaded": False,
            "query_access": False, "unresolved_execution_bindings": list(MISSING)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, default=DEFAULT)
    args = parser.parse_args()
    result = check(json.loads(args.proposal.read_text()))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
