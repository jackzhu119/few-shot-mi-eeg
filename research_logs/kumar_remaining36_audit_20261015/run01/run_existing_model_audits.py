"""Run the frozen read-only auditor on the 36 received original model archives.

No training, EEG loading, model forward, acceptance, or network operations.
Outputs are exclusive and a failed attempt remains recorded without retry.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import audit_kumar_remaining_source_bundle as auditor


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    manifest = json.loads((args.handoff / "MANIFEST.json").read_bytes())["payloads"]
    contract, preflight = auditor.preflight()
    write_new(args.output / "metadata_preflight.json", preflight)
    results = []
    started = datetime.now(timezone.utc).isoformat()
    try:
        for index, job in enumerate(contract["remaining_jobs"], 1):
            relative = "original-results/" + job["job_id"] + ".tar"
            expected = manifest[relative]
            result = auditor.audit(args.handoff / relative, expected["sha256"], expected["bytes"])
            assert result["job_id"] == job["job_id"]
            write_new(args.output / (f"{index:02d}_" + job["job_id"] + ".json"), result)
            results.append(result)
            print(json.dumps({"completed": index, "subject": result["subject"],
                              "seed": result["seed"], "epochs": result["epochs"]}), flush=True)
    except Exception as error:
        write_new(args.output / "failed_attempt.json", {
            "status": "stopped_no_retry", "completed_jobs": len(results),
            "error_type": type(error).__name__, "error": str(error),
            "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        raise
    summary = {
        "status": "all_36_frozen_model_audits_passed",
        "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "auditor_sha256": hashlib.sha256(Path(auditor.__file__).read_bytes()).hexdigest(),
        "contract_sha256": hashlib.sha256(auditor.DEFAULT_CONTRACT.read_bytes()).hexdigest(),
        "models": results, "model_count": len(results),
        "epochs": sum(r["epochs"] for r in results),
        "optimizer_steps": sum(3 * r["epochs"] for r in results),
        "maximum_saved_logits_numpy_CE_difference": max(
            abs(r["independent_saved_logit_loss"] - r["source_validation_loss"]) for r in results),
        "frozen_absolute_tolerance": 1e-7, "query_rows_loaded": 0,
        "audit_refits": 0, "audit_model_forward_passes": 0,
        "accepted_ledger_modified": False, "parent_acknowledgement_written": False,
        "scope": "Checkpoint tensor/state/metadata validation; selection history, source labels, saved-logit float64 CE and recorded original Torch replay. No independent checkpoint-to-EEG forward.",
    }
    write_new(args.output / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "models"}), flush=True)


if __name__ == "__main__":
    main()
