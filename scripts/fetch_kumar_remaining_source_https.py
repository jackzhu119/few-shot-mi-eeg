"""Prepare or verify exactly 253 frozen source files; never train or access query.

The default command reads metadata only. Restoration additionally requires a
separately reviewed manifest with execution_enabled=true and explicit --execute.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from fetch_kumar_first_fit_https import fetch_one, verify
from fetch_nemar_subset import safe_destination, sanitized_error, validate_entry

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/kumar_remaining_source_https_20261015.json"
SOURCE_PLAN = (
    "research_logs/kumar_checkpoint_reuse_preparation_20261015/"
    "proposed_remaining_source_inputs.json"
)
OFFICIAL_SELECTION = (
    "research_logs/public_data_expansion_20261010/"
    "kumar2024_nm000177_v1.0.5_selection_manifest.json"
)
SOURCE_SUBJECTS = {f"sub-{n}" for n in (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18)}
COMPLETE = "all_253_full_sha256_verified"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan():
    raw = CONFIG.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG.with_suffix(".sha256").read_text().strip():
        raise ValueError("Frozen HTTPS manifest hash mismatch")
    plan = json.loads(raw)
    files = plan["files"]
    if (len(files) != 253 or len({e["path"] for e in files}) != 253
            or sum(e["size"] for e in files) != 196740994
            or plan.get("query_access") is not False
            or plan.get("maximum_attempts_per_file") != 1
            or plan.get("parallel_requests") != 1
            or type(plan.get("timeout_seconds")) is not int
            or not 0 < plan["timeout_seconds"] <= 3600
            or plan.get("official_prefix") != "https://data.nemar.org/nm000177/v1.0.5/"):
        raise ValueError("Unexpected source data scope or transfer limits")
    if (plan.get("source_plan_path") != SOURCE_PLAN
            or plan.get("official_selection_path") != OFFICIAL_SELECTION):
        raise ValueError("Unexpected provenance manifest path")
    source = ROOT / SOURCE_PLAN
    official = ROOT / OFFICIAL_SELECTION
    if (sha256(source) != plan["source_plan_sha256"]
            or sha256(official) != plan["official_selection_sha256"]):
        raise ValueError("Source/official provenance manifest changed")
    original = {e["relative_path"]: e for e in json.loads(source.read_text())["files"]}
    published = {e["path"]: e for e in json.loads(official.read_text())}
    if {e["path"] for e in files} != set(original):
        raise ValueError("Different input members")
    signals = [e["path"] for e in files if e["path"].endswith(".edf")]
    expected_signals = {
        f"{subject}/ses-0/eeg/{subject}_ses-0_task-imagery_run-{run}_eeg.edf"
        for subject in SOURCE_SUBJECTS for run in range(3)
    }
    if set(signals) != expected_signals or len(signals) != 36:
        raise ValueError("Signals include an unreviewed subject, session or run")
    for entry in files:
        validate_entry(entry, plan["official_prefix"])
        reference = original[entry["path"]]
        if (entry["expected_sha256"], entry["size"]) != (
                reference["sha256"], reference["bytes"]):
            raise ValueError("Historical SHA256/length mismatch")
        if {k: v for k, v in entry.items() if k != "expected_sha256"} != published[entry["path"]]:
            raise ValueError("Official source identity changed")
    return plan


def _check_metadata(root):
    description = json.loads(safe_destination(root, "dataset_description.json").read_text())
    if description.get("License") != "CC-BY-4.0" or description.get("Version") != "1.0.5":
        raise ValueError("Official license/version metadata gate failed")


def verify_all(root, receipt):
    """Validate the full receipt, then rehash every source file on each call."""
    root, receipt = Path(root), Path(receipt)
    plan = load_plan()
    report = json.loads(receipt.read_text())
    records = report.get("records", [])
    expected = {e["path"]: e for e in plan["files"]}
    if (report.get("status") != COMPLETE
            or report.get("manifest_sha256") != sha256(CONFIG)
            or report.get("input_manifest_sha256") != plan["source_plan_sha256"]
            or report.get("source_plan_sha256") != plan["source_plan_sha256"]
            or report.get("query_access") is not False
            or report.get("real_training_executed") is not False
            or report.get("maximum_attempts_per_file") != 1
            or len(records) != len(expected)
            or {r["path"] for r in records} != set(expected)):
        raise ValueError("Missing complete exact source input receipt")
    for record in records:
        if (record.get("status") not in {"reused_sha256_verified", "downloaded_sha256_verified"}
                or record.get("sha256") != expected[record["path"]]["expected_sha256"]):
            raise ValueError("Receipt record SHA256/status mismatch")
    for entry in plan["files"]:
        verify(safe_destination(root, entry["path"]), entry)
    _check_metadata(root)


def _write_receipt(receipt, report):
    temporary = receipt.with_name(receipt.name + ".pending")
    with temporary.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, receipt)


def restore(root, receipt):
    """A single bounded attempt; failures and partial files remain for review."""
    root, receipt = Path(root), Path(receipt)
    plan = load_plan()
    if plan.get("execution_enabled") is not True:
        raise PermissionError("Prepared manifest only; separately reviewed restoration freeze required")
    root.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with safe_destination(root, ".queue-download.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if receipt.exists():
            verify_all(root, receipt)
            return {"status": "existing_complete_receipt_and_all_files_reverified"}
        if receipt.with_name(receipt.name + ".pending").exists():
            raise FileExistsError("Preserved pending receipt exists; review before a new attempt")
        if shutil.disk_usage(root).free < sum(e["size"] for e in plan["files"]) + 2 * 1024**3:
            raise RuntimeError("Insufficient disk: require input bytes plus 2 GiB reserve")
        report = dict(
            status="started", manifest_sha256=sha256(CONFIG),
            input_manifest_sha256=plan["source_plan_sha256"],
            source_plan_sha256=plan["source_plan_sha256"], records=[], query_access=False,
            real_training_executed=False, maximum_attempts_per_file=1,
        )
        with receipt.open("x") as stream:
            json.dump(report, stream)
        deadline = time.monotonic() + plan["timeout_seconds"]
        try:
            for signal in (False, True):
                for entry in plan["files"]:
                    if entry["path"].endswith(".edf") != signal:
                        continue
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Source restoration deadline reached")
                    report["current_path"] = entry["path"]
                    report["records"].append(fetch_one(root, entry, deadline))
                    _write_receipt(receipt, report)
                if not signal:
                    _check_metadata(root)
            report["status"] = COMPLETE
        except Exception as error:
            report.update(status="failed_preserved_inputs", error=sanitized_error(error))
            raise SystemExit("Failed; preserve receipt and partial inputs. No automatic retry.") from None
        finally:
            _write_receipt(receipt, report)
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    plan = load_plan()
    if not args.execute:
        print(json.dumps(dict(status="plan_only", files=len(plan["files"]),
                              bytes=sum(e["size"] for e in plan["files"]),
                              query_access=False, real_training_executed=False,
                              execution_enabled=plan.get("execution_enabled") is True)))
        return
    print(json.dumps(restore(args.data_root, args.receipt)))


if __name__ == "__main__":
    main()
