"""Run the frozen all-19 analysis only after the complete source identity gate.

This execution companion preserves previous outputs and stops on a failed fit.
Published aliases remain in arithmetic diagnostics; later sensitivity excludes
all identities implicated in cross-person exact signal copies.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/netbci_cohort_all19_20261010.json"
LEDGER = STAGE / "numeric_signal_identity_v2.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config = json.loads(CONFIG.read_text())
    gate = json.loads((STAGE / "audits/aggregate.json").read_text())
    ledger = json.loads(LEDGER.read_text())
    assert gate["successfully_audited_subjects"] == config["subjects"]
    assert not gate["failures"] and gate["config_sha256"] == sha(CONFIG)
    assert ledger["status"] == "complete_exact_numeric_identity_audit"
    assert ledger["synthetic"] is False
    assert ledger["subject_order"] == config["subjects"]
    assert ledger["configuration_sha256"] == sha(CONFIG)
    assert ledger["summary"]["continuous_runs"] == 456
    assert ledger["summary"]["official_manifest_matches"] == 456
    receipt_path = STAGE / "serial_model_execution_20261011.json"
    assert not receipt_path.exists(), "Preserve previous execution receipt"
    receipt = {"status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(),
               "synthetic": False, "config_sha256": sha(CONFIG),
               "source_gate_sha256": sha(STAGE / "audits/aggregate.json"),
               "identity_gate_sha256": sha(LEDGER), "runner_sha256": sha(Path(__file__)),
               "sequential_full_array_jobs": True, "subjects": []}
    runtime = STAGE / "runtime"
    for subject in config["subjects"]:
        output = ROOT / "results/netbci_cohort_all19_20261010" / subject / "run01"
        assert not output.exists(), f"Preserve prior output: {output}"
        command = [sys.executable, str(ROOT / "scripts/analyze_netbci_cohort_subject.py"),
                   "--config", str(CONFIG), "--bundle", str(ROOT / config["bundle_root"] / subject),
                   "--output", str(output)]
        with (runtime / f"analysis_{subject}_run01.log").open("x") as stream:
            completed = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        analysis_path = output / "analysis_receipt.json"
        analysis = json.loads(analysis_path.read_text()) if analysis_path.exists() else {}
        item = {"subject": subject, "exit_code": completed.returncode,
                "status": analysis.get("status"), "receipt_sha256": sha(analysis_path)
                if analysis_path.exists() else None}
        receipt["subjects"].append(item)
        if completed.returncode or analysis.get("status") == "failed":
            receipt["status"] = "failed_preserved_partial_execution"
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            raise RuntimeError(f"Analysis stopped at {subject}; evidence retained")
        assert analysis["config_sha256"] == sha(CONFIG) and analysis["synthetic"] is False
        print(json.dumps(item), flush=True)
    receipt["status"] = "completed_all19_serial_frozen_models"
    receipt["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
