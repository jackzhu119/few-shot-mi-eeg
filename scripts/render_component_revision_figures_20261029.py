"""Render the fixed component revision from saved numerical tables only.

No EEG, checkpoint, decoder, fit, inference or statistical test is loaded here.
Historical confidence intervals and the later EA interval retain their own
recorded analysis scopes; this renderer does not recalculate their bootstrap.
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
from matplotlib import colors, font_manager
from matplotlib.text import Text
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "manuscript/plos_one_innovation_20261017/Figures"
EVIDENCE = ROOT / "research_logs/paper2_hpc_v2_20261023/existing_evidence"
METHODS = ("source_only", "frozen_csp_lda_recalibration", "refit_csp_lda", "ea_csp_lda")
NAMES = ("Frozen", "LDA-only", "Full refit", "EA-CSP")
PALETTE = ("#666666", "#009E73", "#0072B2", "#D55E00")
BUDGETS = ("4", "8", "12", "16", "full")
DEVELOPMENT = ("sub-1", "sub-4", "sub-7", "sub-10", "sub-13", "sub-16")
PRIMARY = tuple(f"sub-{i}" for i in range(1, 19) if f"sub-{i}" not in DEVELOPMENT)


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_rows(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def one(rows, **criteria):
    chosen = [r for r in rows if all(r.get(key) == value for key, value in criteria.items())]
    if len(chosen) != 1:
        raise ValueError(f"Expected one saved row for {criteria}, got {len(chosen)}")
    return chosen[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "manuscript/bmt_component_revision_20261029/figures")
    parser.add_argument("--session-metrics", type=Path, default=ROOT /
                        "research_logs/paper2_structure_revision_20261029/component_replay/"
                        "budget_session_metrics_replayed.csv")
    args = parser.parse_args()
    paths = [OLD / "Fig6_participant_source_data.csv", OLD / "Fig5_source_data.csv",
             ROOT / "manuscript/discovery_revision_20261027/figures/Fig1_update_components_source_data.csv",
             EVIDENCE / "budget_participant_endpoints.csv", EVIDENCE / "budget_cohort_means.csv",
             EVIDENCE / "budget_cohort_paired_gains.csv", args.session_metrics]
    old, transitions, historical_intervals, endpoints, means, gains, sessions = map(read_rows, paths)
    original = {r["subject"]: r for r in old if r["cohort"] == "final_test"}
    endpoint_index = {(r["subject"], r["budget"], r["method"]): r for r in endpoints}
    session_index = {(r["subject"], r["session"], r["budget"], r["method"]): r for r in sessions}
    if set(original) != set(PRIMARY) or len(endpoint_index) != 360 or len(session_index) != 1800:
        raise ValueError("Incomplete or duplicate recorded component endpoints")
    if any(r["complete_five_session_endpoint"] != "True" for r in endpoints):
        raise ValueError("A required five-session endpoint is incomplete")
    values = np.asarray([[float(endpoint_index[(p, "full", method)]["five_session_mean_BA"]) * 100
                          for method in METHODS] for p in PRIMARY])
    for i, person in enumerate(PRIMARY):
        for j, key in enumerate(("frozen_BA_pct", "LDA_BA_pct", "full_BA_pct")):
            np.testing.assert_allclose(values[i, j], float(original[person][key]), atol=1e-12, rtol=0)
        for j, method in enumerate(METHODS):
            session_values = [float(session_index[(person, f"ses-{s}", "full", method)]["balanced_accuracy"])
                              for s in range(1, 6)]
            np.testing.assert_allclose(values[i, j], np.mean(session_values) * 100, atol=1e-12, rtol=0)
    for j, method in enumerate(METHODS):
        expected = float(one(means, cohort="remaining12", budget="full", method=method)["mean_BA"]) * 100
        np.testing.assert_allclose(values[:, j].mean(), expected, atol=1e-12, rtol=0)

    contrasts = []
    for key, label, newer, reference, color in (
        ("lda_minus_frozen_pp", "LDA − frozen\nClassifier update", 1, 0, PALETTE[1]),
        ("full_minus_lda_pp", "Full − LDA\nSpatial refit", 2, 1, PALETTE[2]),
        ("ea_minus_full", "EA − full\nAlignment (exploratory)", 3, 2, PALETTE[3]),
    ):
        differences = values[:, newer] - values[:, reference]
        if key == "ea_minus_full":
            row = one(gains, cohort="remaining12", budget="full", contrast=key)
            mean = float(row["mean_gain_pp"])
            low, high = float(row["CI95_low_pp"]), float(row["CI95_high_pp"])
            scope = row["interval_scope"]
        else:
            candidates = [r for r in historical_intervals
                          if r.get("contrast") == key and r.get("cohort") == "original_primary_12"]
            if len(candidates) != 12:
                raise ValueError("Missing historical confidence-interval rows")
            row = candidates[0]
            mean, low, high = (float(row[k]) for k in ("mean_pp", "ci_low_pp", "ci_high_pp"))
            scope = "original_historical_10000_seed42_lexicographic_participant_order"
        np.testing.assert_allclose(differences.mean(), mean, atol=1e-12, rtol=0)
        contrasts.append({"key": key, "label": label, "values": differences, "mean": mean,
                          "low": low, "high": high, "scope": scope, "color": color})
    transition_rows = [one(transitions, cohort="primary", contrast="full_minus_lda",
                           measure="balanced_accuracy", component=component)
                       for component in ("corrected_pp", "introduced_pp", "net_pp")]
    corrected, introduced, net = [float(r["mean_pp_or_pct"]) for r in transition_rows]
    np.testing.assert_allclose(corrected - introduced, net, atol=1e-12, rtol=0)
    np.testing.assert_allclose(net, contrasts[1]["mean"], atol=1e-12, rtol=0)

    available = {font.name for font in font_manager.fontManager.ttflist}
    family = next((name for name in ("Arial", "Helvetica") if name in available), "DejaVu Sans")
    plt.rcParams.update({"font.family": family, "font.size": 8, "axes.titlesize": 8.5,
                         "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.linewidth": .6, "xtick.major.width": .6, "ytick.major.width": .6,
                         "xtick.major.size": 3, "ytick.major.size": 3,
                         "figure.constrained_layout.h_pad": .045,
                         "figure.constrained_layout.w_pad": .045,
                         "pdf.fonttype": 42, "svg.fonttype": "none"})
    args.output.mkdir(parents=True, exist_ok=True)
    output_records = []

    def save(figure, stem, rows):
        figure.canvas.draw()
        minimum = min(t.get_fontsize() for t in figure.findobj(Text)
                      if t.get_visible() and t.get_text().strip())
        width = figure.get_figwidth()
        at_170mm = minimum * (170 / 25.4) / width
        if at_170mm < 6:
            raise ValueError("Publication lettering below 6pt at 170mm")
        for suffix in ("png", "pdf", "svg", "tiff"):
            extra = {"pil_kwargs": {"compression": "tiff_lzw"}} if suffix == "tiff" else {}
            figure.savefig(args.output / (stem + "." + suffix), dpi=600,
                           facecolor="white", **extra)
            if suffix == "tiff":
                with Image.open(args.output / (stem + ".tiff")) as raster:
                    rgb = raster.convert("RGB")
                rgb.save(args.output / (stem + ".tiff"), compression="tiff_lzw", dpi=(600, 600))
        write_rows(args.output / (stem + ".csv"), rows)
        plt.close(figure)
        output_records.append({"figure": stem, "source_rows": len(rows), "font_family": family,
                               "native_minimum_font_pt": minimum, "minimum_font_pt_at_170mm": at_170mm,
                               "publication_width_mm": 170, "png_dpi": 600,
                               "TIFF_dpi": 600, "TIFF_compression": "LZW", "TIFF_mode": "RGB",
                               "vector_text_editable": True, "formats": [
                                   {"file": stem + "." + suffix,
                                    "bytes": (args.output / (stem + "." + suffix)).stat().st_size,
                                    "sha256": digest(args.output / (stem + "." + suffix))}
                                   for suffix in ("png", "pdf", "svg", "tiff", "csv")]})

    # Figure 1: endpoint distributions, the sequential matched-label contrasts,
    # and the exact prediction-transition identity producing the spatial gain.
    figure = plt.figure(figsize=(170 / 25.4, 124 / 25.4), layout="constrained")
    grid = figure.add_gridspec(2, 2, height_ratios=[1.6, 1], hspace=.1, wspace=.1)
    ax = figure.add_subplot(grid[0, 0])
    jitter = np.linspace(-0.13, 0.13, len(PRIMARY))
    for i, row in enumerate(values):
        ax.plot(np.arange(4) + jitter[i], row, color="#cccccc", linewidth=0.45, zorder=1)
    source_rows = []
    for j, (method, color) in enumerate(zip(METHODS, PALETTE)):
        ax.scatter(j + jitter, values[:, j], color=color, marker=("s", "^", "o", "D")[j],
                   s=12, edgecolor="white", linewidth=0.25, zorder=3)
        ax.scatter(j, values[:, j].mean(), marker="D", color=color, s=26,
                   edgecolor="#222222", linewidth=0.6, zorder=4)
        for i, person in enumerate(PRIMARY):
            source_rows.append({"panel": "A", "cohort": "remaining12", "participant": person,
                                "method": method, "value": values[i, j], "unit": "BA_percent"})
        source_rows.append({"panel": "A", "cohort": "remaining12", "participant": "mean",
                            "method": method, "value": values[:, j].mean(), "unit": "BA_percent"})
    ax.axhline(50, color="#999999", linestyle="--", linewidth=0.6)
    ax.set(xticks=range(4), xticklabels=("Frozen", "LDA-only", "Full", "EA-CSP"),
           ylim=(35, 95), ylabel="Query balanced accuracy (%)")
    ax.set_title("A  Endpoint performance (n = 12)", loc="left", weight="medium")
    ax.text(.02, .97, "Points: participants; diamonds: means", transform=ax.transAxes,
            ha="left", va="top", fontsize=7)
    ax = figure.add_subplot(grid[0, 1])
    all_diff = np.concatenate([c["values"] for c in contrasts])
    left = min(-10, float(np.floor(all_diff.min() / 5) * 5 - 2))
    right = max(20, float(np.ceil(all_diff.max() / 5) * 5 + 2))
    for y, c in enumerate(contrasts):
        ax.scatter(c["values"], y + np.linspace(-.09, .09, 12), color=c["color"], s=11,
                   edgecolor="white", linewidth=.25, zorder=2)
        ax.errorbar(c["mean"], y, xerr=[[c["mean"] - c["low"]], [c["high"] - c["mean"]]],
                    fmt="D", markersize=4.3, color=c["color"], markeredgecolor="#222222",
                    markeredgewidth=.55, ecolor="#222222", elinewidth=1, capsize=2.5, zorder=4)
        ax.text(.99, y + .27, f"{c['mean']:+.2f} [{c['low']:+.2f}, {c['high']:+.2f}]",
                transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=7)
        for person, value in zip(PRIMARY, c["values"]):
            source_rows.append({"panel": "B", "cohort": "remaining12", "participant": person,
                                "contrast": c["key"], "value": value, "unit": "BA_percentage_points"})
        source_rows.append({"panel": "B", "cohort": "remaining12", "participant": "mean",
                            "contrast": c["key"], "value": c["mean"], "lower": c["low"],
                            "upper": c["high"], "interval_scope": c["scope"], "unit": "BA_percentage_points"})
    ax.axvline(0, color="#999999", linestyle="--", linewidth=.6)
    ax.set(yticks=range(3), yticklabels=["LDA − Frozen", "Full − LDA", "EA − Full\nExploratory"],
           ylim=(2.5, -.4), xlim=(left, right + .5), xlabel="Paired BA difference (pp)")
    ax.set_title("B  Update contrasts", loc="left", weight="medium")
    ax = figure.add_subplot(grid[1, :])
    for y, (name, value, color) in enumerate((
        ("Errors corrected", corrected, PALETTE[2]),
        ("Errors introduced", -introduced, PALETTE[3]),
        ("Net spatial gain", net, "#444444"),
    )):
        ax.plot([0, value], [y, y], color=color, linewidth=1.6, zorder=2)
        ax.scatter(value, y, s=22, color=color, edgecolor="#222222", linewidth=.4, zorder=3)
        ax.text(value + (.35 if value > 0 else -.35), y, f"{value:+.2f}",
                ha="left" if value > 0 else "right", va="center", fontsize=8)
        source_rows.append({"panel": "C", "cohort": "remaining12", "participant": "mean",
                            "contrast": "full_minus_lda", "measure": name, "value": value,
                            "unit": "class_balanced_percentage_points"})
    ax.axvline(0, color="#777777", linewidth=.6)
    ax.set(yticks=range(3), yticklabels=["Corrected errors", "New errors", "Net gain"],
           ylim=(2.6, -.6), xlim=(-15, 21), xlabel="Contribution to Full − LDA-only (percentage points)")
    ax.set_title("C  Prediction-transition decomposition", loc="left", weight="medium")
    save(figure, "Fig1_components", source_rows)

    # Figure 2: complete source-matched budget curves, with original development
    # and remaining cohorts kept separate, and all full-support session effects.
    figure, axes = plt.subplots(2, 2, figsize=(170 / 25.4, 145 / 25.4), layout="constrained",
                                gridspec_kw={"height_ratios": [1, 1.45], "hspace": .1, "wspace": .12})
    source_rows = []
    for ax, cohort, title in zip(axes[0], ("remaining12", "development6"),
                                 ("A  Primary cohort (n = 12)", "B  Development cohort (n = 6)")):
        for method, name, color, marker, style in zip(METHODS, NAMES, PALETTE,
                                                     ("s", "^", "o", "D"), ("--", "-.", "-", "-")):
            selected = [one(means, cohort=cohort, budget=budget, method=method) for budget in BUDGETS]
            curve = [float(r["mean_BA"]) * 100 for r in selected]
            ax.plot(range(5), curve, color=color, marker=marker, linestyle=style,
                    label=name, linewidth=1.1, markersize=3.2)
            for budget, value in zip(BUDGETS, curve):
                source_rows.append({"panel": "A" if cohort == "remaining12" else "B",
                                    "cohort": cohort, "budget": budget, "method": method,
                                    "value": value, "unit": "BA_percent"})
        ax.set(xticks=range(5), xticklabels=("4", "8", "12", "16", "19/20"),
               xlabel="Current-session support labels", ylabel="Mean balanced accuracy (%)", ylim=(50, 75))
        ax.grid(axis="y", color="#ededed", linewidth=.45)
        ax.set_axisbelow(True)
        ax.set_title(title, loc="left", weight="medium")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside upper center", ncol=4, frameon=False, fontsize=8)
    matrices = []
    for newer, reference, label in (("refit_csp_lda", "frozen_csp_lda_recalibration", "Full − LDA-only"),
                                     ("ea_csp_lda", "refit_csp_lda", "EA − Full")):
        matrix = np.array([[(float(session_index[(p, f"ses-{s}", "full", newer)]["balanced_accuracy"])
                            - float(session_index[(p, f"ses-{s}", "full", reference)]["balanced_accuracy"])) * 100
                           for s in range(1, 6)] for p in PRIMARY])
        newer_values = np.array([float(endpoint_index[(p, "full", newer)]["five_session_mean_BA"]) for p in PRIMARY])
        reference_values = np.array([float(endpoint_index[(p, "full", reference)]["five_session_mean_BA"]) for p in PRIMARY])
        np.testing.assert_allclose(matrix.mean(axis=1), (newer_values - reference_values) * 100, atol=1e-12, rtol=0)
        matrices.append(matrix)
        for i, person in enumerate(PRIMARY):
            for j, session in enumerate(range(1, 6)):
                source_rows.append({"panel": "C" if newer == "refit_csp_lda" else "D",
                                    "cohort": "remaining12", "participant": person, "session": session,
                                    "contrast": label, "budget": "full", "value": matrix[i, j],
                                    "unit": "BA_percentage_points"})
    maximum = float(np.ceil(max(np.max(np.abs(m)) for m in matrices) / 5) * 5)
    cmap = colors.LinearSegmentedColormap.from_list("blue_orange_signed", ["#D55E00", "#fafafa", "#0072B2"])
    for ax, matrix, title in zip(axes[1], matrices, ("C  Full − LDA-only", "D  EA − Full")):
        image = ax.pcolormesh(np.arange(6) - .5, np.arange(13) - .5, matrix,
                              cmap=cmap, vmin=-maximum, vmax=maximum, shading="flat",
                              edgecolors="white", linewidth=.35, rasterized=False)
        for i in range(12):
            for j in range(5):
                v = matrix[i, j]
                ax.text(j, i, f"{v:+.1f}" if abs(v) > 1e-10 else "0.0", ha="center", va="center",
                        fontsize=7.2, color="white" if abs(v) > .64 * maximum else "#222222")
        ax.set(xticks=range(5), xticklabels=range(1, 6), yticks=range(12),
               yticklabels=[p.replace("sub-", "").zfill(2) for p in PRIMARY],
               xlabel="Target session", ylabel="Participant", xlim=(-.5, 4.5), ylim=(11.5, -.5))
        ax.set_title(title, loc="left", weight="medium")
    colorbar = figure.colorbar(image, ax=axes[1, :], orientation="horizontal", fraction=.05,
                               aspect=50, pad=.06, ticks=[-maximum, -maximum / 2, 0, maximum / 2, maximum])
    colorbar.solids.set_rasterized(False)
    colorbar.solids.set_edgecolor("face")
    colorbar.set_label("Paired balanced-accuracy difference (pp)", fontsize=8)
    save(figure, "Fig2_budgets_sessions", source_rows)

    manifest = {"source_files": [{"path": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
                                   "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths],
                "scientific_inputs": "saved result CSV only; no EEG/model tensors/fit/forward/test",
                "figures": output_records, "historical_intervals_preserved": True,
                "EA_interval_scope": "post-exposure exploratory pointwise interval; not multiplicity adjusted",
                "participants_kept_separate": {"original_primary": list(PRIMARY), "development": list(DEVELOPMENT)},
                "four_method_means_reconstructed": True, "five_session_mean_reconstructed": True,
                "transition_identity_reconstructed": True,
                "negative_and_zero_effects_retained": True,
                "heatmap_shared_symmetric_range_pp": [-maximum, maximum],
                "publication_style": "170mm; thin axes; participant points and original CIs; no decorative fills",
                "heatmap_cells_vector": True, "image_generation_used": False,
                "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__}
    (args.output / "FIGURE_MANIFEST_20261029.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
