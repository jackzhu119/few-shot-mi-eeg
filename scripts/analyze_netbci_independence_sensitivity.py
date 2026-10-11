"""Post-observation sensitivity excluding both identities in cross-person copies.

Original ten-ID outputs are immutable. This restriction follows raw signal
identity, not effect direction, and cannot recover the true source assignment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_netbci_cohort_associations import association_statistics, participant_values
from summarize_netbci_cohort import participant_statistics, read_table, write_json, write_table

from learning_preserving_bci.datasets.netbci import file_sha256
from learning_preserving_bci.utils.reproducibility import collect_provenance

ROOT = Path(__file__).resolve().parents[1]


def analyze(summary_root, identity_path, output):
    if output.exists():
        raise FileExistsError("Preserve previous outputs; choose a new directory")
    identity = json.loads(identity_path.read_text())
    if identity["status"] != "complete_exact_numeric_identity_audit" or identity["synthetic"]:
        raise ValueError("A completed real numerical identity audit is required")
    excluded = sorted({subject for group in identity["continuous_duplicate_groups"]
                       if group["cross_subject"] for subject in group["subjects"]})
    receipt_path = summary_root / "summary_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    inputs = {"identity_audit": identity_path, "summary_receipt": receipt_path,
              "script": Path(__file__), "statistics_script": ROOT / "scripts/summarize_netbci_cohort.py",
              "association_script": ROOT / "scripts/analyze_netbci_cohort_associations.py"}
    for name in ("cohort_summary.json", "participant_session_join.tsv", "participant_matched_geometry.tsv"):
        path = summary_root / name
        if file_sha256(path) != receipt["output_sha256"][name]:
            raise ValueError(f"Summary source hash differs: {name}")
        inputs[name] = path
    summary = json.loads(inputs["cohort_summary.json"].read_text())
    subjects = [s for s in summary["subjects"] if s not in excluded]
    if set(identity["subject_order"]) != set(summary["subjects"]) or not excluded or not subjects:
        raise ValueError("Identity audit scope differs or no valid restriction is defined")
    joined = [row for row in read_table(inputs["participant_session_join.tsv"]) if row["subject"] in subjects]
    matching = [row for row in read_table(inputs["participant_matched_geometry.tsv"]) if row["subject"] in subjects]
    metrics = [row["metric"] for row in summary["paired_changes"]]
    stats, changes, individual, _ = participant_statistics(joined, subjects, ["01", "02", "03", "04"],
                                                          metrics, 42, 10000)
    values = participant_values(joined, matching, subjects=subjects)
    associations = association_statistics(values, subjects=subjects, seed=42, repetitions=10000)
    result = {"status": "post_observation_cross_person_duplicate_exclusion_sensitivity", "synthetic": False,
              "excluded_identities": excluded, "retained_identities": subjects,
              "selection_basis": "all identities in exact cross-subject continuous-signal duplicate groups",
              "unknown_correct_assignment": True, "no_model_refitting": True,
              "not_independent_confirmation": True, "paired_changes": changes,
              "association_estimates": associations,
              "limitations": "No exact signal copies detected among retained IDs; true participant identity, biological reliability and causal learning remain unverified."}
    output.mkdir(parents=True)
    write_table(output / "retained_participant_session_join.tsv", joined)
    write_table(output / "cohort_session_statistics.tsv", stats)
    write_table(output / "cohort_paired_changes.tsv", changes)
    write_table(output / "participant_first_last_changes.tsv", individual)
    write_table(output / "association_estimates.tsv", associations)
    write_json(output / "sensitivity_summary.json", result)
    outputs = {p.name: file_sha256(p) for p in output.iterdir() if p.is_file()}
    write_json(output / "sensitivity_receipt.json", {"status": "completed_real_data_sensitivity", "synthetic": False,
               "input_sha256": {key: {"path": str(path.resolve()), "sha256": file_sha256(path)} for key, path in inputs.items()},
               "output_sha256": outputs, "provenance": collect_provenance(42, ROOT),
               "original_primary_outputs_modified": False, "bootstrap_unit": "paired retained identity"})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--identity-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.summary, args.identity_audit, args.output)
    print(json.dumps({"retained": result["retained_identities"], "excluded": result["excluded_identities"]}))


if __name__ == "__main__":
    main()
