"""Independent scalar/Fraction check of saved-prediction descriptive tables.

This checker intentionally does not import the analysis module. Its estimates
come from integer confusion counts and rational class-balanced transition sums.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    body = path.read_bytes()
    if path.suffix == ".gz":
        body = gzip.decompress(body)
    return list(csv.DictReader(io.StringIO(body.decode())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--analysis", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.analysis.resolve()
    method_map = {"source_only": "frozen", "frozen_csp_lda_recalibration": "lda_only",
                  "refit_csp_lda": "full_csp", "ea_csp_lda": "ea_csp"}
    groups = defaultdict(list)
    qcl = {r["trial_id"]: r["qc_peak_to_peak_over_250uv"] == "True" for r in read(
        root / "research_logs/kumar_submission_qc_20261015/run01/query_identity_qc_ledger.csv")}
    for row in read(root / "research_logs/paper2_structure_revision_20261029/component_replay/input/budget/query_predictions.csv.gz"):
        key = "Kumar2024", row["subject"], row["session"], row["budget"], method_map[row["method"]], "all_query"
        value = row["trial_id"], int(row["label"]), int(row["prediction"])
        groups[key].append(value)
        if row["budget"] == "full" and not qcl[value[0]]:
            groups[key[:-1] + ("unflagged_query",)].append(value)
    for participant in range(1, 10):
        for method in ("frozen", "lda_only", "full_csp", "ea_csp"):
            path = root / ("research_logs/paper2_external_validation_20261027/saved_predictions/"
                           f"bnci001-sub-{participant:02d}/E__n20__{method}.json")
            row = json.loads(path.read_text())
            key = "BNCI2014-001", f"sub-{participant:02d}", "E", "full", method, "all_query"
            groups[key] = list(zip(row["trial_ids"], row["y"], row["prediction"]))
    # Explicit empty restricted groups are retained as undefined rather than disappearing.
    for key in list(groups):
        if key[0] == "Kumar2024" and key[3] == "full" and key[-1] == "all_query":
            groups.setdefault(key[:-1] + ("unflagged_query",), [])
    comparisons = 0
    maximum = 0.0

    def compare(actual, expected, description):
        nonlocal comparisons, maximum
        comparisons += 1
        if expected is None:
            if actual not in (None, ""):
                raise ValueError("Expected undefined: " + description)
        else:
            difference = abs(float(actual) - float(expected))
            maximum = max(maximum, difference)
            if difference > 1e-12:
                raise ValueError("Independent mismatch: " + description)

    exact = {}
    for key, rows in groups.items():
        n = Counter(y for _, y, _ in rows)
        good = Counter(y for _, y, p in rows if y == p)
        left = Fraction(good[0], n[0]) if n[0] else None
        right = Fraction(good[1], n[1]) if n[1] else None
        defined = left is not None and right is not None
        exact[key] = {"n_left": n[0], "n_right": n[1], "recall_left": left, "recall_right": right,
                      "ba": (left + right) / 2 if defined else None,
                      "weak_recall": min(left, right) if defined else None,
                      "recall_gap": abs(left - right) if defined else None}
    endpoint_rows = read(out / "endpoint_metrics.csv")
    if len(endpoint_rows) != len(exact):
        raise ValueError("Independent endpoint grid differs")
    for row in endpoint_rows:
        key = tuple(row[k] for k in ("dataset", "participant", "session", "budget", "method", "subset"))
        for field, value in exact[key].items():
            compare(row[field], value, str(key) + field)
    references = {"lda_minus_frozen": ("frozen", "lda_only"),
                  "full_minus_frozen": ("frozen", "full_csp"),
                  "full_minus_lda": ("lda_only", "full_csp"),
                  "ea_minus_full": ("full_csp", "ea_csp"),
                  "ea_minus_frozen": ("frozen", "ea_csp")}
    exact_contrasts = {}
    for row in read(out / "endpoint_transitions.csv"):
        base = tuple(row[k] for k in ("dataset", "participant", "session", "budget"))
        a, b = references[row["contrast"]]
        ka, kb = base + (a, row["subset"]), base + (b, row["subset"])
        reference, new = groups[ka], groups[kb]
        if [(t, y) for t, y, _ in reference] != [(t, y) for t, y, _ in new]:
            raise ValueError("Independent pairing mismatch")
        n = Counter(y for _, y, _ in reference)
        defined = bool(n[0] and n[1])
        changed = {}
        for field in ("ba", "weak_recall", "recall_gap", "recall_left", "recall_right"):
            value = exact[kb][field] - exact[ka][field] if defined else None
            changed["delta_" + field] = value
        corrected = introduced = disagreement = Fraction(0)
        if defined:
            for (_, y, pa), (_, _, pb) in zip(reference, new):
                weight = Fraction(1, 2 * n[y])
                if pa != y and pb == y:
                    corrected += weight
                if pa == y and pb != y:
                    introduced += weight
                if pa != pb:
                    disagreement += weight
            if corrected - introduced != changed["delta_ba"] or corrected + introduced != disagreement:
                raise ValueError("Exact rational transition identity failed")
        changed.update(corrected=corrected if defined else None,
                       introduced=introduced if defined else None,
                       disagreement=disagreement if defined else None)
        for field, value in changed.items():
            compare(row[field], value, str(base) + row["contrast"] + field)
        exact_contrasts[base + (row["contrast"], row["subset"])] = changed
    # Reconstruct people with scalar rational sums, without applying min/abs after averaging.
    for filename, lookup, method_key in [("participant_metrics.csv", exact, "method"),
                                         ("participant_contrasts.csv", exact_contrasts, "contrast")]:
        for row in read(out / filename):
            sessions = [f"ses-{i}" for i in range(1, 6)] if row["dataset"] == "Kumar2024" else ["E"]
            cells = [lookup[(row["dataset"], row["participant"], s, row["budget"],
                             row[method_key], row["subset"])] for s in sessions]
            for field in cells[0]:
                if field.startswith("n_"):
                    continue
                values = [c[field] for c in cells]
                value = sum(values, Fraction(0)) / len(values) if all(v is not None for v in values) else None
                compare(row[field], value, filename + row["participant"] + field)
    inputs = json.loads((out / "INPUT_MANIFEST.json").read_text())
    for row in inputs:
        p = root / row["path"]
        if p.stat().st_size != row["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Source changed during independent check")
    report = {"status": "passed", "implementation": "standalone scalar integer/Fraction; analysis module not imported",
              "endpoint_cells": len(exact), "scalar_comparisons": comparisons,
              "maximum_absolute_difference": maximum, "exact_rational_identities": "passed",
              "source_hashes_rechecked": len(inputs), "new_model_fits": 0, "query_forwards": 0}
    (out / "INDEPENDENT_NUMERICAL_CHECK.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
