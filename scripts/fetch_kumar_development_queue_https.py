"""Restore exactly the 127 frozen source-only files; no training or credentials."""

import argparse
import fcntl
import hashlib
import json
import shutil
import time
from pathlib import Path

from fetch_kumar_first_fit_https import fetch_one, verify
from fetch_nemar_subset import sanitized_error, validate_entry

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/kumar_development_queue_https_20261014.json"


def load_plan():
    raw = CONFIG.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG.with_suffix(".sha256").read_text().strip():
        raise ValueError("Frozen input manifest changed")
    plan = json.loads(raw)
    if len(plan["files"]) != 127 or sum(e["size"] for e in plan["files"]) != 98743492:
        raise ValueError("Unexpected source data scope")
    source = ROOT / "research_logs/gpu_preparation_20261014/eegnet_data_plan.json"
    if hashlib.sha256(source.read_bytes()).hexdigest() != plan["source_plan_sha256"]:
        raise ValueError("Frozen R2 input identity changed")
    original = {e["relative_path"]: e for e in json.loads(source.read_text())["files"]}
    if {e["path"] for e in plan["files"]} != set(original):
        raise ValueError("Different input members")
    for e in plan["files"]:
        validate_entry(e, plan["official_prefix"])
        ref = original[e["path"]]
        if (e["expected_sha256"], e["size"]) != (ref["sha256"], ref["bytes"]):
            raise ValueError("Historical SHA256/length mismatch")
    return plan


def verify_all(root, receipt):
    plan = load_plan()
    report = json.loads(receipt.read_text())
    if report["status"] != "all_127_full_sha256_verified" or report["manifest_sha256"] != (
        hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    ):
        raise ValueError("Missing complete input receipt")
    if {r["path"] for r in report["records"]} != {e["path"] for e in plan["files"]}:
        raise ValueError("Incomplete input receipt members")
    for entry in plan["files"]:
        verify(root / entry["path"], entry)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    plan = load_plan()
    if not args.execute:
        print(json.dumps(dict(status="plan_only", files=127, bytes=98743492)))
        return
    args.data_root.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with (args.data_root / ".queue-download.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.receipt.exists():
            verify_all(args.data_root, args.receipt)
            print("Existing complete input receipt and all 127 files reverified; no download")
            return
        if shutil.disk_usage(args.data_root).free < 98743492 + 2 * 1024**3:
            raise RuntimeError("Insufficient disk reserve")
        report = dict(
            status="started",
            manifest_sha256=hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
            records=[],
            query_access=False,
            maximum_attempts_per_file=1,
        )
        with args.receipt.open("x") as stream:
            json.dump(report, stream)
        deadline = time.monotonic() + plan["timeout_seconds"]
        try:
            for signal in (False, True):
                for e in plan["files"]:
                    if e["path"].endswith(".edf") != signal:
                        continue
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Download deadline reached")
                    report["records"].append(fetch_one(args.data_root, e, deadline))
                    args.receipt.write_text(json.dumps(report, indent=2) + "\n")
                if not signal:
                    meta = json.loads((args.data_root / "dataset_description.json").read_text())
                    if meta.get("License") != "CC-BY-4.0" or meta.get("Version") != "1.0.5":
                        raise ValueError("License/version mismatch")
            report["status"] = "all_127_full_sha256_verified"
        except Exception as error:
            report.update(status="failed_preserved_inputs", error=sanitized_error(error))
            raise SystemExit(
                "Failed; retain receipt and partial files. No automatic retry."
            ) from None
        finally:
            args.receipt.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
