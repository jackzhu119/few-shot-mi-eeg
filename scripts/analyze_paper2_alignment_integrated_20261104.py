"""Reanalyze saved Paper2 predictions using the frozen descriptive analysis plan."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from learning_preserving_bci.paper2_alignment_integrated import execute  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-commit", required=True)
    args = parser.parse_args()
    report = execute(args.root.resolve(), args.output.resolve(), args.plan_commit)
    print(json.dumps({k: report[k] for k in ["plan_commit", "saved_prediction_rows",
                                            "original_endpoint_groups", "maximum_historical_BA_error",
                                            "new_fit_count", "query_forward_count"]}, indent=2))


if __name__ == "__main__":
    main()
