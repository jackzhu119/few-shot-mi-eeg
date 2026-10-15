#!/usr/bin/env python3
"""Run the unchanged, hashed figure producer into explicit fresh repo paths."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    receipt = json.loads((HERE / "figure_generation_receipt.json").read_text())
    original = receipt["script"]
    script = ROOT / original["path"]
    if hashlib.sha256(script.read_bytes()).hexdigest() != original["sha256"]:
        raise ValueError("executed original renderer SHA256 changed")
    for source in receipt["source_files"]:
        data = (ROOT / source["path"]).read_bytes()
        if len(data) != source["bytes"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"frozen saved-text source changed: {source['path']}")
    output, log = args.output_dir.resolve(), args.log_dir.resolve()
    for path in (output, log):
        if path == ROOT or not path.is_relative_to(ROOT):
            raise ValueError("fresh output and log paths must be inside this repository")
        if path.exists() and (not path.is_dir() or any(path.iterdir())):
            raise FileExistsError(f"preserve existing non-empty output: {path}")
    if output == log or output.is_relative_to(log) or log.is_relative_to(output):
        raise ValueError("output and log directories must be distinct and non-nested")
    if args.check_only:
        print(
            json.dumps(
                {
                    "status": "saved_text_sources_and_fresh_paths_verified",
                    "source_count": len(receipt["source_files"]),
                    "output_dir": str(output),
                    "log_dir": str(log),
                    "renders_executed": 0,
                },
                indent=2,
            )
        )
        return
    spec = importlib.util.spec_from_file_location("frozen_kumar_submission_figure_producer", script)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    producer.OUT = output
    producer.LOG = log
    producer.main()


if __name__ == "__main__":
    main()
