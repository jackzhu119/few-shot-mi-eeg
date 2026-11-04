"""Render JNE supplementary figures from their immutable plotted source CSVs.

No model, EEG, prediction, bootstrap or new inferential calculation is used.
The original plotted CSV bytes and recorded interval endpoints are preserved.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "manuscript/bmt_alignment_integrated_20261104/supplementary_figures"
ADAPTER = ROOT / "scripts/render_paper2_jne_figures_20261104.py"
SPEC = importlib.util.spec_from_file_location("jne_export", ADAPTER)
JNE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(JNE)
BUDGETS = [4, 8, 12, 16, 20]
COLORS = ["#0072B2", "#D55E00"]
REGIMES = ["reuse_v2", "pooled_source"]
REGIME_LABELS = ["Individual source", "Pooled source"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(name):
    with (ORIGINAL / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def panel(ax, letter, title):
    JNE.panel(ax, letter, title)


def budget_axis(ax):
    ax.set_xticks(BUDGETS)
    ax.set_xlabel("Current-session support-label cap")
    ax.grid(axis="y", color="#e8e8e8", linewidth=.6)
    ax.set_axisbelow(True)


def save(fig, stem, source_name, output):
    result = JNE.export(fig, stem, [], output)
    (output / (stem + ".csv")).unlink()
    source_path = ORIGINAL / source_name
    destination = output / source_name
    destination.write_bytes(source_path.read_bytes())
    assert destination.read_bytes() == source_path.read_bytes()
    result["plot_rows"] = len(source(source_name))
    result["source_CSV_byte_identical"] = True
    result["original_source_CSV"] = str(source_path.relative_to(ROOT))
    result["outputs"] = [row for row in result["outputs"] if not row["file"].endswith(".csv")]
    result["outputs"].append({"file": source_name, "bytes": destination.stat().st_size,
                              "sha256": digest(destination)})
    return result


def geometry(output):
    rows = source("FigS1_source_data.csv")
    fig = plt.figure(figsize=(150 / 25.4, 195 / 25.4))
    a = fig.add_axes([.16, .66, .81, .27])
    b = fig.add_axes([.43, .085, .54, .30])
    names = {"source_tangent_frozen": "Source frozen", "tangent_pooled": "Pooled means",
             "tangent_refit": "Tangent refit", "eb_point": "EB point",
             "eb_predictive": "EB predictive", "eb_isotropic": "Isotropic noise",
             "eb_coupled": "Coupled shift", "eb_no_source_noise": "No source noise",
             "eb_no_shift": "No shift", "saved_V2_ea_csp": "Saved EA-CSP"}
    emphasis = {"saved_V2_ea_csp": ("#0072B2", "D", "-"),
                "tangent_refit": ("#009E73", "s", "--"),
                "eb_predictive": ("#D55E00", "o", "-.")}
    muted = [(None, ":"), ("v", (0, (1, 1))), ("^", (0, (4, 2))),
             ("+", (0, (3, 1, 1, 1))), ("x", (0, (5, 2))),
             ("1", (0, (2, 2))), ("P", (0, (1, 2)))]
    styles = iter(muted)
    methods = list(names)
    for method in methods:
        selected = sorted((r for r in rows if r["panel"] == "A" and r["method"] == method),
                          key=lambda r: int(r["budget"]))
        assert [int(r["budget"]) for r in selected] == BUDGETS
        if method in emphasis:
            color, marker, line = emphasis[method]
        else:
            marker, line = next(styles)
            color = "#858585"
        a.plot(BUDGETS, [100 * float(r["mean_balanced_accuracy"]) for r in selected],
               color=color, marker=marker, linestyle=line, markersize=3.2,
               linewidth=1.4 if method in emphasis else .7,
               alpha=1 if method in emphasis else .7, label=names[method])
    panel(a, "A", "All geometric methods and budgets")
    budget_axis(a)
    a.set(ylabel="Mean balanced accuracy (%)", ylim=(53, 73))
    handles, labels = a.get_legend_handles_labels()
    order = [names[m] for m in emphasis]
    order.extend(x for x in labels if x not in order)
    mapping = dict(zip(labels, handles))
    a.legend([mapping[x] for x in order], order, frameon=False, fontsize=8, ncol=2,
             loc="upper center", bbox_to_anchor=(.50, -.25), columnspacing=1.4)
    references = ["tangent_refit", "saved_V2_ea_csp", "tangent_pooled", "eb_point",
                  "eb_isotropic", "eb_coupled", "eb_no_source_noise", "eb_no_shift",
                  "source_tangent_frozen"]
    display = ["Tangent refit (primary)", "Saved EA-CSP (strong reference)", "Pooled means",
               "EB point", "Isotropic noise", "Coupled shift", "No source noise",
               "No shift", "Source frozen"]
    for y, reference in enumerate(references):
        selected = [r for r in rows if r["panel"] == "B" and r["reference"] == reference]
        assert len(selected) == 6
        r = selected[0]
        mean, lo, hi = [float(r[x]) for x in ("mean_pp", "ci_low_pp", "ci_high_pp")]
        color = COLORS[1] if y == 0 else COLORS[0] if y == 1 else "#777777"
        b.errorbar(mean, y, xerr=[[mean - lo], [hi - mean]], fmt="o", color=color,
                   capsize=2.5, markersize=4)
    b.axvline(0, color="#999999", lw=.7)
    b.set(yticks=range(9), yticklabels=display, ylim=(8.5, -.5),
          xlabel="EB predictive − comparator (pp)")
    panel(b, "B", "Twenty-label paired contrasts")
    return save(fig, "FigS1_geometry", "FigS1_source_data.csv", output)


def neural(output):
    rows = source("FigS2_source_data.csv")
    fig = plt.figure(figsize=(150 / 25.4, 160 / 25.4))
    a = fig.add_axes([.15, .64, .82, .29])
    b = fig.add_axes([.16, .105, .31, .34])
    c = fig.add_axes([.68, .105, .29, .34])
    for i, regime in enumerate(REGIMES):
        chosen = [r for r in rows if r["panel"] == "A/B" and r["source_regime"] == regime]
        summaries = [next(r for r in chosen if int(r["budget"]) == budget) for budget in BUDGETS]
        means, lows, highs = [[float(r[field]) for r in summaries]
                              for field in ("mean_pp", "ci_low_pp", "ci_high_pp")]
        a.plot(BUDGETS, means, "o-" if i == 0 else "s--", color=COLORS[i],
               markersize=3, label=REGIME_LABELS[i])
        a.fill_between(BUDGETS, lows, highs, color=COLORS[i], alpha=.12)
        cap = sorted((r for r in chosen if int(r["budget"]) == 20), key=lambda r: r["participant"])
        assert len(cap) == 6
        b.scatter([float(r["difference_pp"]) for r in cap], np.arange(6) + (i - .5) * .2,
                  s=20, color=COLORS[i], marker="o" if i == 0 else "s")
    a.axhline(0, color="#999999", lw=.7)
    budget_axis(a)
    a.set_ylabel("Fixed − adaptive BN mode (pp)")
    a.legend(frameon=False, fontsize=8, loc="upper left")
    panel(a, "A", "Normalization across label budgets")
    b.axvline(0, color="#999999", lw=.7)
    b.set(yticks=range(6), yticklabels=[r["participant"] for r in cap], ylim=(5.5, -.5),
          xlabel="Fixed − adaptive BN (pp)")
    panel(b, "B", "Twenty-label participant gains")
    for x, regime in enumerate(REGIMES):
        for offset, method, label, color, hatch in [(-.17, "full_fixed", "Fixed BN", "#0072B2", "///"),
                                                  (.17, "full_adaptive_bn", "Adaptive BN", "#E69F00", "xx")]:
            r = next(r for r in rows if r["panel"] == "C" and r["source_regime"] == regime
                     and r["method"] == method)
            percent = float(r["collapse_percent"])
            c.bar(x + offset, percent, width=.29, color=color, hatch=hatch,
                  edgecolor="#333333", lw=.6, label=label if x == 0 else None)
            c.text(x + offset, percent + .7, f"{r['collapsed_cells']}/{r['nested_cells']}",
                   ha="center", fontsize=8)
    c.set(xticks=[0, 1], xticklabels=["Individual\nsource", "Pooled\nsource"],
          ylabel="Single-class prediction cells (%)", ylim=(0, 25))
    c.legend(frameon=False, fontsize=8, loc="upper left")
    panel(c, "C", "Twenty-label prediction collapse")
    return save(fig, "FigS2_neural_normalization", "FigS2_source_data.csv", output)


def mechanisms(output):
    rows = source("FigS3_source_data.csv")
    fig, axes = plt.subplots(2, 2, figsize=(150 / 25.4, 165 / 25.4))
    fig.subplots_adjust(left=.15, right=.97, bottom=.10, top=.93, wspace=.60, hspace=.65)
    a, b, c, d = axes.flat
    for i, rho in enumerate(("0", "0.5")):
        selected = sorted((r for r in rows if r["panel"] == "A" and r["serial_correlation"] == rho),
                          key=lambda r: int(r["source_perclass"]))
        a.plot([int(r["source_perclass"]) for r in selected],
               [float(r["mean_ba_difference_pp"]) for r in selected], "o-", color=COLORS[i],
               markersize=3, label=f"AR(1) ρ = {rho}")
    a.set_xscale("log")
    a.set(xticks=[10, 20, 100], xticklabels=[10, 20, 100], xlabel="Source observations per class",
          ylabel="Candidate − refit BA (pp)")
    a.legend(frameon=False, fontsize=8)
    panel(a, "A", "Sample size and serial correlation")
    for x, shift in enumerate(("none", "common", "contrast", "both")):
        selected = [r for r in rows if r["panel"] == "B" and r["shift"] == shift]
        values = np.array([float(r["difference_pp"]) for r in selected])
        b.scatter(np.full(len(values), x) + np.linspace(-.15, .15, len(values)), values,
                  s=5, alpha=.25, color=COLORS[0], rasterized=False)
        b.plot(x, values.mean(), "D", color=COLORS[1], markersize=4)
    b.set(xticks=range(4), xticklabels=["None", "Common", "Contrast", "Both"],
          ylabel="Candidate − refit BA (pp)")
    b.tick_params(axis="x", labelrotation=30)
    panel(b, "B", "All generating shift conditions")
    points = [r for r in rows if r["panel"] == "C/D"]
    assert len(points) == 384
    c.scatter([float(r["refit_ba_percent"]) for r in points],
              [float(r["candidate_ba_percent"]) for r in points], s=7, alpha=.55, color=COLORS[0])
    c.plot([40, 100], [40, 100], color="#777777", lw=.7)
    c.set(xlabel="Refit balanced accuracy (%)", ylabel="Candidate balanced accuracy (%)",
          xlim=(44, 101), ylim=(44, 101))
    panel(c, "C", "All 384 fixed scenario means")
    x = np.array([float(r["cross_entropy_vs_point"]) for r in points])
    y = np.array([100 * float(r["balanced_accuracy_vs_point"]) for r in points])
    d.scatter(x, y, s=7, alpha=.45, color="#80549a", rasterized=False)
    d.plot(x.mean(), y.mean(), "D", color=COLORS[1], markersize=4)
    d.set(xlabel="Posterior predictive − point\nCE (nats)",
          ylabel="Posterior predictive − point BA (pp)")
    d.text(.03, .96, f"Grid mean: ΔCE {x.mean():+.3f};\nΔBA {y.mean():+.3f} pp",
           transform=d.transAxes, va="top", fontsize=8)
    panel(d, "D", "Uncertainty changes CE and BA")
    for axis in (a, b, d):
        axis.axhline(0, color="#999999", lw=.7)
    d.axvline(0, color="#999999", lw=.7)
    return save(fig, "FigS3_mechanisms", "FigS3_source_data.csv", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "manuscript/jne_alignment_20261104/supplementary_figures")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                         "axes.labelsize": 8, "axes.titlesize": 8.5,
                         "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
                         "axes.linewidth": .6, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False})
    results = [geometry(args.output), neural(args.output), mechanisms(args.output)]
    manifest = {"journal": "Journal of Neural Engineering", "renderer": {
                    "path": str(Path(__file__).relative_to(ROOT)), "sha256": digest(__file__)},
                "export_adapter": {"path": str(ADAPTER.relative_to(ROOT)), "sha256": digest(ADAPTER)},
                "original_renderer_reference": "scripts/render_paper2_v3_discovery_figures_20261027.py",
                "scope": "presentation_only_from_saved_plotted_CSVs_no_bootstrap_no_fit_no_inference",
                "all_source_CSVs_byte_identical": True, "figures": results}
    (args.output / "FIGURE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "all_format_checks_passed": True}))


if __name__ == "__main__":
    main()
