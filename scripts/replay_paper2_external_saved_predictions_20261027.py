"""Reproduce external replication endpoints from public JSON, without EEG/models."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.external_validation_20261027.statistics import METHODS, summarize  # noqa: E402


def replay(source):
    records, verified = [], []
    for participant in range(1, 10):
        task = f"bnci001-sub-{participant:02d}"
        manifest = json.loads((source / "trial_identity" / task / "manifest.json").read_text())
        expected = [r for r in manifest["trials"] if r["role"] == "query"]
        expected_ids = [r["trial_id"] for r in expected]
        expected_y = [r["label"] for r in expected]
        if len(expected_ids) != 120 or len(set(expected_ids)) != 120:
            raise ValueError("Fixed query identities must be 120 unique chronological trials")
        for method in METHODS:
            path = source / "saved_predictions" / task / f"E__n20__{method}.json"
            row = json.loads(path.read_text())
            if (row["participant"] != str(participant) or row["method"] != method
                    or row["session"] != "E" or row["query_used_for_fitting"]
                    or row["trial_ids"] != expected_ids or row["y"] != expected_y
                    or row["n_support_actual"] != (0 if method == "frozen" else 20)):
                raise ValueError("Saved prediction does not match frozen trial roles/method/budget")
            y, prediction = np.array(row["y"]), np.array(row["prediction"])
            if y.shape != prediction.shape or not np.isin(prediction, [0, 1]).all():
                raise ValueError("Invalid saved predicted classes")
            recall = {str(c): float(np.mean(prediction[y == c] == c)) for c in (0, 1)}
            counts = {str(c): int(np.sum(y == c)) for c in (0, 1)}
            score = float(np.mean(list(recall.values())))
            metrics = row["metrics"]
            if (counts != {"0": 60, "1": 60} or score != metrics["balanced_accuracy"]
                    or recall != metrics["class_recall"] or counts != metrics["class_counts"]):
                raise ValueError("Saved metrics do not match their label/prediction bytes")
            records.append({"participant": str(participant), "session": "E", "method": method,
                            "balanced_accuracy": score, "n_query": len(y), "class_counts": counts})
            verified.append(str(path.relative_to(source)))
    result = summarize(records)
    if result["status"] != "complete":
        raise ValueError("External fixed cohort is incomplete")
    return result, verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=ROOT / "research_logs/paper2_external_validation_20261027")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result, verified = replay(args.source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "replayed_aggregate.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"participants": len(result["complete_participants"]),
                      "verified_prediction_files": len(verified),
                      "fits": 0, "EEG_loaded": False, "checkpoints_loaded": False,
                      "new_forward_calls": 0, "output": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
