#!/usr/bin/env python3
"""Export actual participant results and descriptive support-only PCA distances."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import subspace_angles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads((args.results / "participant_bootstrap_summary.json").read_text())["cohorts"]["final_test"]
    methods = ["source_only", "frozen_csp_lda_recalibration", "refit_csp_lda"]
    labels = ["Frozen", "LDA recalibration", "CSP/LDA refit"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    values = np.asarray([summary["methods"][m]["participant_values"] for m in methods]) * 100
    for i in range(values.shape[1]):
        axes[0].plot(range(3), values[:, i], color="0.65", alpha=.6, linewidth=.8)
    means = values.mean(axis=1)
    ci = np.asarray([summary["methods"][m]["ci95"] for m in methods]) * 100
    axes[0].errorbar(range(3), means, yerr=np.stack([means-ci[:, 0], ci[:, 1]-means]), fmt="o", color="navy", capsize=5)
    axes[0].set(xticks=range(3), xticklabels=labels, ylabel="Participant mean target BA (%)", ylim=(30, 90), title="Fixed final test: 12 published IDs")
    delta = (values[2] - values[0])
    order = np.argsort(delta)
    axes[1].barh(np.arange(12), delta[order], color=["#b35445" if x < 0 else "#287c8e" for x in delta[order]])
    axes[1].set(yticks=np.arange(12), yticklabels=np.asarray(summary["subjects"])[order], xlabel="Refit minus frozen (percentage points)", title="Five target sessions equally weighted")
    axes[1].axvline(0, color="black", linewidth=.8)
    fig.suptitle("Kumar2024 v1.0.5 | offline decoding; ordinary baselines")
    fig.tight_layout()
    paths = []
    for suffix in ["png", "svg", "pdf"]:
        p = args.output / f"participant_baseline_comparison.{suffix}"
        fig.savefig(p, dpi=170, bbox_inches="tight"); paths.append(p)
    plt.close(fig)
    records, inputs = [], {}
    for folder in sorted(args.results.glob("sub-*")):
        meta = json.loads((folder / "included_trial_metadata.json").read_text())
        with np.load(folder / "fixed_features.npz", allow_pickle=False) as f:
            z = f["source_standardized_44"]
        with np.load(folder / "feature_source_fit.npz", allow_pickle=False) as f:
            source = f["pca_components"].T
        for session in [f"ses-{i}" for i in range(1, 6)]:
            idx = [i for i, row in enumerate(meta) if row["session"] == session and row["role"] == "target_support"]
            _, _, vectors = np.linalg.svd(z[idx] - z[idx].mean(axis=0), full_matrices=False)
            angles = subspace_angles(source, vectors[:4].T)
            records.append({"subject": folder.name, "cohort": meta[0]["cohort"], "session": session,
                            "support_trials": len(idx), "source_dimensions": 4, "target_dimensions": 4,
                            "normalized_chordal_distance": float(np.linalg.norm(np.sin(angles)) / 2),
                            "fit_access": "target_support_SVD_for_description_only; source_transform_frozen; no_query_or_decoder_update"})
        for p in [folder / "fixed_features.npz", folder / "feature_source_fit.npz"]:
            inputs[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    p = args.output / "support_only_PCA_subspace_distance.csv"
    with p.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    paths.append(p)
    with (args.output / "figure_and_PCA_diagnostic_receipt.json").open("x") as stream:
        json.dump({"status": "completed", "synthetic": False, "source_input_sha256": inputs,
                   "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "PCA_scope": "supplementary post-freeze support-only descriptive SVD; not a chosen predictor or primary test",
                   "decoder_fits": 0, "outputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}, stream, indent=2)


if __name__ == "__main__":
    main()
