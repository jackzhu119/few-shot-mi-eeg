"""Render component-level discovery figures from saved result tables only.

This script never imports a decoder, loads EEG/checkpoints or performs inference.
EEG intervals resample participant endpoints. Simulation scenarios are shown as
the declared fixed factorial grid, separately from real-participant inference.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager
from matplotlib.text import Text
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BUDGETS = [4, 8, 12, 16, 20]
REGIMES = ["reuse_v2", "pooled_source"]
REGIME_LABELS = {"reuse_v2": "Individual source", "pooled_source": "Pooled source"}
COLORS = ["#2274a5", "#c05c25", "#4a8f69", "#80549a", "#a37725", "#777777"]


def read_rows(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def interval(values, seed=20261023):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), (10000, len(values)))
    return np.quantile(values[indices].mean(axis=1), [.025, .975])


def paired(rows, method, reference, budget, family="geometry", regime="within_subject"):
    chosen = [r for r in rows if r["family"] == family and r["source_regime"] == regime
              and r["variant"] == "core" and int(r["budget"]) == budget]
    a = {r["participant"]: float(r["balanced_accuracy"]) for r in chosen if r["method"] == method}
    b = {r["participant"]: float(r["balanced_accuracy"]) for r in chosen if r["method"] == reference}
    if a.keys() != b.keys() or len(a) != 6:
        raise ValueError("Figure contrast requires the full six-participant paired endpoint")
    people = sorted(a)
    values = np.array([(a[p] - b[p]) * 100 for p in people])
    return people, values, interval(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saved-results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--v2-analysis-root", type=Path,
                        default=ROOT / "research_logs/paper2_hpc_v2_analysis_20261026")
    args = parser.parse_args()
    saved = args.saved_results_root.resolve()
    if not (saved / "analysis").is_dir():
        saved = saved / "results"
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    participants = read_rows(saved / "analysis/participant_metrics.csv")
    cohorts = read_rows(saved / "analysis/cohorts.csv")
    simulations = read_rows(saved / "analysis/simulation_scenarios.csv")
    v2_curves = read_rows(args.v2_analysis_root / "classical/classical_budget_curves.csv")
    old = read_rows(ROOT / "manuscript/plos_one_innovation_20261017/Figures/Fig6_participant_source_data.csv")
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    font_family = next((name for name in ("Arial", "Helvetica") if name in available_fonts), "DejaVu Sans")
    intended_width_mm = 170
    plt.rcParams.update({"font.family": font_family, "font.size": 12,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "svg.fonttype": "none"})
    figures = []
    sources = []
    lettering_checks = []

    def save(fig, name, data):
        fig.savefig(out / (name + ".png"), dpi=600, bbox_inches="tight", facecolor="white")
        fig.savefig(out / (name + ".svg"), bbox_inches="tight", facecolor="white")
        fig.savefig(out / (name + ".pdf"), bbox_inches="tight", facecolor="white")
        fig.canvas.draw()
        bbox_width_in = fig.get_tightbbox(fig.canvas.get_renderer()).width + 2 * plt.rcParams["savefig.pad_inches"]
        minimum_native_pt = min(text.get_fontsize() for text in fig.findobj(Text)
                                if text.get_visible() and text.get_text().strip())
        minimum_final_pt = minimum_native_pt * (intended_width_mm / 25.4) / bbox_width_in
        if minimum_final_pt < 6:
            raise ValueError("Figure lettering would be below6pt at intended170mm width")
        lettering_checks.append({"figure": name, "font_family": font_family,
                                 "native_minimum_pt": minimum_native_pt,
                                 "exported_width_in": bbox_width_in,
                                 "intended_width_mm": intended_width_mm,
                                 "minimum_at_intended_width_pt": minimum_final_pt,
                                 "meets_six_pt_minimum": True})
        write_rows(out / (name + "_source_data.csv"), data)
        figures.append(fig)
        sources.append(name)

    def budget_axis(axis):
        axis.set_xticks(BUDGETS)
        axis.set_xlabel("Current-session support-label cap")
        axis.grid(axis="y", color="#e8e8e8", linewidth=.6)
        axis.set_axisbelow(True)

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 5.5), layout="constrained")
    data = []
    old_contrasts = [("full_minus_frozen_pp", "Full refit − frozen\n(original primary)"),
                     ("full_minus_lda_pp", "Full refit − LDA-only\n(same-label secondary)"),
                     ("lda_minus_frozen_pp", "LDA-only − frozen")]
    for y, (key, label) in enumerate(old_contrasts):
        subset = sorted((r for r in old if r["cohort"] == "final_test"), key=lambda r: r["subject"])
        values = np.array([float(r[key]) for r in subset])
        # Preserve the original frozen lexicographic subject order and seed42.
        lo, hi = interval(values, 42)
        mean = values.mean()
        axes[0].scatter(values, np.full(12, y) + np.linspace(-.09, .09, 12),
                        s=17, color=COLORS[y], alpha=.4, zorder=2)
        axes[0].errorbar(mean, y, xerr=[[mean-lo], [hi-mean]], fmt="D", color=COLORS[y],
                         capsize=4, markersize=6, zorder=3)
        axes[0].text(23.2, y, f"{mean:+.2f}\n[{lo:.2f}, {hi:.2f}]", va="center", fontsize=12)
        data.extend({"panel": "A", "cohort": "original_primary_12", "subject": r["subject"],
                     "contrast": key, "difference_pp": float(r[key]), "mean_pp": mean,
                     "ci_low_pp": lo, "ci_high_pp": hi} for r in subset)
    axes[0].axvline(0, color="#999999", linewidth=.8)
    axes[0].set_yticks(range(3), [c[1] for c in old_contrasts])
    axes[0].set(xlim=(-8, 31), ylim=(2.55, -.55), xlabel="Paired balanced-accuracy difference (pp)",
                title="A  Original primary cohort\n12 participants")
    for method, label, color in [("frozen", "Frozen", "#777777"), ("lda_only", "LDA-only", COLORS[2]),
                                  ("full_csp", "Full CSP/LDA", COLORS[0]), ("ea_csp", "EA-CSP", COLORS[1])]:
        subset = sorted((r for r in v2_curves if r["method"] == method), key=lambda r: int(r["budget"]))
        axes[1].plot(BUDGETS, [float(r["mean_ba_percent"]) for r in subset], "o-", label=label,
                     color=color, markersize=4)
        data.extend({"panel": "B", "cohort": "development_6_V2", **r} for r in subset)
    budget_axis(axes[1])
    axes[1].set(ylabel="Mean balanced accuracy (%)", ylim=(58, 74),
                title="B  V2 development extension\n6 participants")
    axes[1].legend(frameon=False, fontsize=12, loc="lower right")
    save(fig, "Fig1_update_components", data)

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 7.4), layout="constrained", gridspec_kw={"width_ratios": [1, 1.1]})
    methods = ["source_tangent_frozen", "tangent_pooled", "tangent_refit", "eb_point", "eb_predictive",
               "eb_isotropic", "eb_coupled", "eb_no_source_noise", "eb_no_shift"]
    labels = {"source_tangent_frozen": "Source frozen", "tangent_pooled": "Pooled means",
              "tangent_refit": "Tangent refit", "eb_point": "EB point", "eb_predictive": "EB predictive",
              "eb_isotropic": "Isotropic noise", "eb_coupled": "Coupled shift", "eb_no_source_noise": "No source noise",
              "eb_no_shift": "No shift"}
    data = []
    palette = ["#777777", "#6aa6a2", "#2274a5", "#4a8f69", "#c05c25", "#a484bd", "#be9877", "#859758", "#bd7ca0"]
    for method, color in zip(methods, palette):
        subset = sorted((r for r in cohorts if r["family"] == "geometry" and r["method"] == method),
                        key=lambda r: int(r["budget"]))
        emphasis = method in ("tangent_refit", "eb_point", "eb_predictive", "source_tangent_frozen")
        axes[0].plot(BUDGETS, [100*float(r["mean_balanced_accuracy"]) for r in subset],
                     "o-", label=labels[method], color=color, markersize=3,
                     linewidth=1.8 if emphasis else .9, alpha=1 if emphasis else .7)
        data.extend({"panel": "A", **r} for r in subset)
    budget_axis(axes[0])
    axes[0].set(ylabel="Mean balanced accuracy (%)", ylim=(53, 73), title="A  All geometric methods\nand budgets")
    axes[0].legend(frameon=False, fontsize=12, ncol=2, loc="upper center", bbox_to_anchor=(.5, -.15))
    refs = ["tangent_refit", "saved_V2_ea_csp", "tangent_pooled", "eb_point", "eb_isotropic",
            "eb_coupled", "eb_no_source_noise", "eb_no_shift", "source_tangent_frozen"]
    display = ["Tangent refit (primary)", "Saved EA-CSP (strong reference)", "Pooled means", "EB point",
               "Isotropic noise", "Coupled shift", "No source noise", "No shift", "Source frozen"]
    for y, (ref, name) in enumerate(zip(refs, display)):
        people, values, (lo, hi) = paired(participants, "eb_predictive", ref, 20)
        color = COLORS[1] if y == 0 else COLORS[0] if y == 1 else "#777777"
        axes[1].errorbar(values.mean(), y, xerr=[[values.mean()-lo], [hi-values.mean()]], fmt="o",
                         color=color, capsize=3, markersize=5)
        data.extend({"panel": "B", "participant": p, "method": "eb_predictive", "reference": ref,
                     "budget": 20, "difference_pp": v, "mean_pp": values.mean(), "ci_low_pp": lo,
                     "ci_high_pp": hi} for p, v in zip(people, values))
    axes[1].axvline(0, color="#999999", linewidth=.8)
    axes[1].set_yticks(range(len(refs)), display)
    axes[1].set(ylim=(len(refs)-.5, -.5), xlabel="EB predictive − comparator (pp)",
                title="B  Twenty-label cap:\npaired participant contrasts")
    save(fig, "Fig2_geometry", data)

    fig, axes = plt.subplots(1, 3, figsize=(12.0, 6.0), layout="constrained",
                             gridspec_kw={"width_ratios": [1.2, 1.05, 1]})
    data = []
    for index, regime in enumerate(REGIMES):
        means, lows, highs = [], [], []
        for budget in BUDGETS:
            people, values, (lo, hi) = paired(participants, "full_fixed", "full_adaptive_bn", budget,
                                              "neural", regime)
            means.append(values.mean())
            lows.append(lo)
            highs.append(hi)
            data.extend({"panel": "A/B", "source_regime": regime, "participant": p, "budget": budget,
                         "difference_pp": v, "mean_pp": values.mean(), "ci_low_pp": lo, "ci_high_pp": hi}
                        for p, v in zip(people, values))
            if budget == 20:
                axes[1].scatter(values, np.arange(6) + (index-.5)*.2, s=31, color=COLORS[index],
                                label=REGIME_LABELS[regime])
        means = np.array(means)
        axes[0].plot(BUDGETS, means, "o-", color=COLORS[index], label=REGIME_LABELS[regime], markersize=4)
        axes[0].fill_between(BUDGETS, lows, highs, color=COLORS[index], alpha=.12)
    axes[0].axhline(0, color="#999999", linewidth=.8)
    budget_axis(axes[0])
    axes[0].set(ylabel="Fixed − adaptive BN mode (pp)", title="A  Effect depends\non label budget")
    axes[0].legend(frameon=False, fontsize=12)
    axes[1].axvline(0, color="#999999", linewidth=.8)
    axes[1].set_yticks(range(6), people)
    axes[1].set(xlabel="Fixed − adaptive BN mode (pp)", ylim=(5.5, -.5), title="B  Twenty-label\nparticipant gains")
    collapse = {(r, m): [0, 0] for r in REGIMES for m in ["full_fixed", "full_adaptive_bn"]}
    for path in sorted((saved / "tasks").glob("*/summary.json")):
        if "-kl" in path.parent.name:
            continue
        for row in json.loads(path.read_text()).get("results", []):
            key = (row.get("source_regime"), row.get("method"))
            if key in collapse and row.get("requested_budget") == 20:
                collapse[key][0] += int(row["collapse"])
                collapse[key][1] += 1
    for x, regime in enumerate(REGIMES):
        for offset, method, label, color in [(-.17, "full_fixed", "Fixed BN", COLORS[2]),
                                              (.17, "full_adaptive_bn", "Adaptive BN", COLORS[3])]:
            numerator, denominator = collapse[(regime, method)]
            if denominator != 90:
                raise ValueError("Incomplete cap20 neural-collapse denominator")
            percentage = numerator / denominator * 100
            axes[2].bar(x + offset, percentage, width=.29, color=color, label=label if x == 0 else None)
            axes[2].text(x+offset, percentage+.7, f"{numerator}/{denominator}", ha="center", fontsize=12)
            data.append({"panel": "C", "source_regime": regime, "method": method, "budget": 20,
                         "collapsed_cells": numerator, "nested_cells": denominator, "collapse_percent": percentage})
    axes[2].set_xticks([0, 1], ["Individual\nsource", "Pooled\nsource"])
    axes[2].set(ylabel="Single-class prediction cells (%)", ylim=(0, 25),
                title="C  Twenty-label\nprediction collapse")
    axes[2].legend(frameon=False, fontsize=12, loc="upper left")
    save(fig, "Fig3_neural_normalization", data)

    by_scenario = {}
    for row in simulations:
        by_scenario.setdefault(int(row["scenario_index"]), {})[row["method"]] = row
    if len(by_scenario) != 384 or any(len(r) != 9 for r in by_scenario.values()):
        raise ValueError("Incomplete fixed simulation factorial")
    scenario = []
    for index, methods in sorted(by_scenario.items()):
        candidate, refit, point = [methods[m] for m in ["eb_predictive", "tangent_refit", "eb_point"]]
        row = {"scenario_index": index, **{k: candidate[k] for k in ["source_perclass", "serial_correlation", "shift", "p", "target_perclass", "anisotropy"]}}
        for metric in ["balanced_accuracy", "cross_entropy", "binary_brier", "mean_squared_feature_error"]:
            row[metric + "_vs_refit"] = float(candidate[metric]) - float(refit[metric])
            row[metric + "_vs_point"] = float(candidate[metric]) - float(point[metric])
        row["candidate_ba_percent"] = float(candidate["balanced_accuracy"])*100
        row["refit_ba_percent"] = float(refit["balanced_accuracy"])*100
        scenario.append(row)
    fig, axes = plt.subplots(2, 2, figsize=(10.3, 9.8), layout="constrained")
    data = []
    for i, rho in enumerate(["0", "0.5"]):
        values = []
        for source_n in [10, 20, 100]:
            subset = [r for r in scenario if float(r["serial_correlation"]) == float(rho)
                      and int(r["source_perclass"]) == source_n]
            mean = np.mean([r["balanced_accuracy_vs_refit"] for r in subset])*100
            values.append(mean)
            data.append({"panel": "A", "source_perclass": source_n, "serial_correlation": rho,
                         "scenario_count": len(subset), "mean_ba_difference_pp": mean})
        axes[0, 0].plot([10, 20, 100], values, "o-", color=COLORS[i], label=f"AR(1) ρ = {rho}")
    axes[0, 0].set_xscale("log")
    axes[0, 0].set_xticks([10, 20, 100], [10, 20, 100])
    axes[0, 0].set(xlabel="Source observations per class", ylabel="Candidate − refit BA (pp)",
                   title="A  Sample size\nand serial correlation")
    axes[0, 0].legend(frameon=False, fontsize=12)
    shifts = ["none", "common", "contrast", "both"]
    for x, shift in enumerate(shifts):
        subset = [r for r in scenario if r["shift"] == shift]
        values = np.array([r["balanced_accuracy_vs_refit"]*100 for r in subset])
        axes[0, 1].scatter(np.full(len(values), x) + np.linspace(-.15, .15, len(values)), values,
                           s=8, alpha=.25, color=COLORS[0], rasterized=False)
        axes[0, 1].plot(x, values.mean(), "D", color=COLORS[1], markersize=6)
        data.extend({"panel": "B", "scenario_index": r["scenario_index"], "shift": shift,
                     "difference_pp": r["balanced_accuracy_vs_refit"]*100} for r in subset)
    axes[0, 1].set_xticks(range(4), ["None", "Common", "Contrast", "Both"])
    axes[0, 1].set(ylabel="Candidate − refit BA (pp)", title="B  All four generating\nshift conditions")
    x = [r["refit_ba_percent"] for r in scenario]
    y = [r["candidate_ba_percent"] for r in scenario]
    axes[1, 0].scatter(x, y, s=13, alpha=.55, color=COLORS[0])
    axes[1, 0].plot([40, 100], [40, 100], color="#777777", linewidth=.8)
    axes[1, 0].set(xlabel="Refit balanced accuracy (%)", ylabel="Candidate balanced accuracy (%)",
                   title="C  All 384 fixed\nscenario means", xlim=(44, 101), ylim=(44, 101))
    x = np.array([r["cross_entropy_vs_point"] for r in scenario])
    y = np.array([r["balanced_accuracy_vs_point"]*100 for r in scenario])
    axes[1, 1].scatter(x, y, s=13, alpha=.45, color=COLORS[3])
    axes[1, 1].plot(x.mean(), y.mean(), "D", color=COLORS[1], markersize=7)
    axes[1, 1].set(xlabel="Posterior predictive − point CE (nats)",
                   ylabel="Posterior predictive − point BA (pp)",
                   title="D  Uncertainty changes confidence\nmore than labels")
    axes[1, 1].text(.03, .96, f"Grid mean: ΔCE {x.mean():+.3f}; ΔBA {y.mean():+.3f} pp",
                     transform=axes[1, 1].transAxes, va="top", fontsize=12)
    for axis in [axes[0, 0], axes[0, 1], axes[1, 1]]:
        axis.axhline(0, color="#999999", linewidth=.8)
    axes[1, 1].axvline(0, color="#999999", linewidth=.8)
    data.extend({"panel": "C/D", **r} for r in scenario)
    save(fig, "Fig4_mechanisms", data)

    with PdfPages(out / "Discovery_Revision_Figures.pdf") as pdf:
        for fig in figures:
            pdf.savefig(fig, bbox_inches="tight", facecolor="white")
    for fig in figures:
        plt.close(fig)
    captions = """# Figure captions

**Figure 1. Spatial-update evidence and the classical extension.** (A) Original 12-participant primary-cohort differences. Small points are participant endpoints, diamonds are cohort means, and intervals are 10,000 participant-bootstrap percentile intervals using the original seed42. Primary and secondary roles are preserved. (B) V2 six-participant development budget curves. These panels represent different cohorts and scientific versions and are not pooled as an enlarged replication.

**Figure 2. All geometric candidates and the strong controls.** (A) Six-participant means for all nine geometric methods at every declared support-label cap. (B) Candidate-minus-comparator differences at the frozen 20-label endpoint, with paired participant-bootstrap intervals. The primary tangent-refit comparison and saved EA-CSP strong reference are distinguished from ablations. Positive comparisons with weaker ablations do not establish superiority over the strong controls.

**Figure 3. Neural normalization-mode effects.** Both full-update arms train all parameters with dropout disabled; they differ in BN evaluation versus training mode, including current-batch normalization and running-statistic updates. (A) Paired participant differences and pointwise bootstrap intervals at all five budgets, separately for individual-source and pooled-source teachers. (B) All six participant differences at cap20. (C) Single-class prediction counts among90 nested participant×seed×session cells per arm. These are not90 independent participants. The cap20 fitting schedule has two minibatches per epoch, whereas caps≤16 have one; cross-budget changes do not isolate batch size, number of BN updates or label quantity. Source regimes share the same six participants and have different source-label budgets.

**Figure 4. Mechanism simulations and the limits of predictive uncertainty.** Every point summarizes50 paired repeats in the prespecified384-scenario factorial. (A) Equal-scenario mean candidate-minus-refit BA by source count and serial correlation. (B) Every scenario within each generating shift type, with group means as diamonds. (C) Candidate and refit BA in all384 scenarios. (D) Adding posterior predictive covariance to identical posterior means changes cross entropy more consistently than BA. Negative CE differences favor posterior prediction. Simulations are synthetic mechanism analyses, separate from real EEG inference; no subset is selected as a confirmatory success.
"""
    (out / "captions.md").write_text(captions)
    input_paths = [saved / "analysis/participant_metrics.csv", saved / "analysis/cohorts.csv",
                   saved / "analysis/simulation_scenarios.csv",
                   args.v2_analysis_root / "classical/classical_budget_curves.csv",
                   ROOT / "manuscript/plos_one_innovation_20261017/Figures/Fig6_participant_source_data.csv"]
    input_paths.extend(sorted((saved / "tasks").glob("*/summary.json")))
    manifest = {"scope": "saved_tables_and_metrics_only_no_fit_no_inference", "figures": sources,
                "eeg_independent_unit": "participant", "simulation_scenarios": 384,
                "lettering_at_intended_size": lettering_checks,
                "font_selection": {"selected": font_family, "preferred": ["Arial", "Helvetica"],
                                   "fallback_reason": None if font_family in ("Arial", "Helvetica")
                                   else "Neither Arial nor Helvetica is installed; DejaVu Sans is embedded in PDF."},
                "input_files": [{"path": str(p), "bytes": p.stat().st_size,
                                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                for p in input_paths],
                "files": [{"file": p.name, "bytes": p.stat().st_size,
                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in sorted(out.iterdir()) if p.is_file() and p.name != "FIGURE_MANIFEST.json"]}
    (out / "FIGURE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output": str(out), "figures": sources, "no_fit_no_inference": True}))


if __name__ == "__main__":
    main()
