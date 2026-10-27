"""Render the fixed nine-participant external replication from saved metrics.

This renderer loads JSON only. It never imports a decoder, loads EEG, fits a
model, or performs inference. Every displayed point/cell is retained in CSV.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import colors, font_manager  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.text import Text  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
LABELS = ("Frozen", "LDA-only", "Full refit", "EA-CSP")
PALETTE = ("#737373", "#c56a22", "#24689b", "#58a0bc")
PARTICIPANTS = tuple(str(index) for index in range(1, 10))
COMPARISONS = (("full_csp_minus_lda_only", "full_csp", "lda_only", "Full − LDA-only"),
               ("ea_csp_minus_full_csp", "ea_csp", "full_csp", "EA − Full"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path,
                        default=ROOT / "research_logs/paper2_external_validation_20261027")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "manuscript/discovery_revision_20261027/figures")
    args = parser.parse_args()
    aggregate_path, runs_path = args.results / "aggregate.json", args.results / "run_metrics.json"
    aggregate = json.loads(aggregate_path.read_text())
    run_rows = json.loads(runs_path.read_text())
    if (aggregate["status"] != "complete" or aggregate["synthetic"]
            or tuple(aggregate["complete_participants"]) != PARTICIPANTS):
        raise ValueError("The figure requires all nine actual participant endpoints")
    index = {(row["participant"], row["method"]): row for row in aggregate["participant_results"]}
    run_index = {(row["participant"], row["method"], int(row["run_id"].rsplit("-", 1)[1])): row
                 for row in run_rows}
    if len(index) != 36 or len(run_index) != 180:
        raise ValueError("Incomplete/duplicate participant or query-run identities")
    if any(row["class_counts"] != {"0": 60, "1": 60} for row in index.values()):
        raise ValueError("Session endpoint class counts changed")
    if any(row["class_counts"] != {"0": 12, "1": 12} for row in run_index.values()):
        raise ValueError("Whole-run endpoint class counts changed")

    values = np.array([[index[(person, method)]["balanced_accuracy"] * 100
                        for method in METHODS] for person in PARTICIPANTS])
    for column, method in enumerate(METHODS):
        expected = aggregate["cohort_balanced_accuracy"][method]["mean_percent"]
        if not np.isclose(values[:, column].mean(), expected, atol=1e-12, rtol=0):
            raise ValueError("Plotted cohort mean differs from the saved participant mean")

    sources, heatmaps = [], []
    for pindex, person in enumerate(PARTICIPANTS):
        for column, method in enumerate(METHODS):
            sources.append({"panel": "A", "participant": person, "method": method,
                            "value": values[pindex, column], "unit": "BA_percent"})
    for column, method in enumerate(METHODS):
        sources.append({"panel": "A", "participant": "cohort_mean", "method": method,
                        "value": values[:, column].mean(), "unit": "BA_percent"})
    for name, newer, reference, _ in COMPARISONS:
        contrast = aggregate["contrasts"][name]
        difference = np.array([(index[(p, newer)]["balanced_accuracy"]
                                - index[(p, reference)]["balanced_accuracy"]) * 100
                               for p in PARTICIPANTS])
        if not np.isclose(difference.mean(), contrast["mean_difference_pp"], atol=1e-12, rtol=0):
            raise ValueError("Plotted paired contrast differs from frozen analysis")
        for person, value in zip(PARTICIPANTS, difference):
            sources.append({"panel": "B", "participant": person, "contrast": name,
                            "value": value, "unit": "BA_percentage_points"})
        sources.append({"panel": "B", "participant": "cohort_mean", "contrast": name,
                        "value": contrast["mean_difference_pp"], "unit": "BA_percentage_points",
                        "lower": contrast["bootstrap_ci95_pp"][0],
                        "upper": contrast["bootstrap_ci95_pp"][1]})
        matrix = np.array([[(run_index[(p, newer, run)]["balanced_accuracy"]
                            - run_index[(p, reference, run)]["balanced_accuracy"]) * 100
                           for run in range(2, 7)] for p in PARTICIPANTS])
        heatmaps.append(matrix)
        # Runs have equal class denominators, so their mean must reconstruct
        # the saved session BA difference for each participant exactly.
        np.testing.assert_allclose(matrix.mean(axis=1), difference, atol=1e-12, rtol=0)
        for i, person in enumerate(PARTICIPANTS):
            for j, run in enumerate(range(2, 7)):
                sources.append({"panel": "C" if len(heatmaps) == 1 else "D",
                                "participant": person, "run": run, "contrast": name,
                                "value": matrix[i, j], "unit": "BA_percentage_points"})

    fonts = {font.name for font in font_manager.fontManager.ttflist}
    family = next((name for name in ("Arial", "Helvetica") if name in fonts), "DejaVu Sans")
    plt.rcParams.update({"font.family": family, "font.size": 12,
                         "axes.titlesize": 13, "axes.labelsize": 12,
                         "xtick.labelsize": 11, "ytick.labelsize": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "svg.fonttype": "none"})
    figure, axes = plt.subplots(2, 2, figsize=(10, 8.3),
                                gridspec_kw={"height_ratios": [1, 1.32]},
                                layout="constrained")
    ax = axes[0, 0]
    jitter = np.linspace(-0.13, 0.13, 9)
    for participant_values in values:
        ax.plot(np.arange(4), participant_values, color="#d4d4d4", linewidth=0.8, zorder=1)
    for column, (method, color) in enumerate(zip(METHODS, PALETTE)):
        ax.scatter(column + jitter, values[:, column], color=color, s=28,
                   edgecolor="white", linewidth=0.45, zorder=3)
        mean = values[:, column].mean()
        ax.scatter(column, mean, marker="D", s=68, color=color,
                   edgecolor="#202020", linewidth=0.9, zorder=4)
        ax.text(column, 101, f"{mean:.2f}", ha="center", va="bottom", fontsize=11)
    ax.axhline(50, color="#555555", linestyle="--", linewidth=0.8)
    ax.set(xticks=range(4), xticklabels=LABELS, ylim=(40, 107),
           ylabel="Query balanced accuracy (%)")
    ax.set_title("A  Four fixed methods", loc="left", weight="bold")
    ax.text(0.98, 0.02, "Dots: participants; diamonds: means", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=11)

    ax = axes[0, 1]
    for y, (name, newer, reference, _) in enumerate(COMPARISONS):
        contrast = aggregate["contrasts"][name]
        color = "#c56a22" if y == 0 else "#24689b"
        diff = [(index[(p, newer)]["balanced_accuracy"]
                 - index[(p, reference)]["balanced_accuracy"]) * 100 for p in PARTICIPANTS]
        ax.scatter(diff, y + np.linspace(-0.13, 0.13, 9), s=28, color=color,
                   edgecolor="white", linewidth=0.45, zorder=3)
        lo, hi = contrast["bootstrap_ci95_pp"]
        ax.plot([lo, hi], [y, y], color="#202020", linewidth=2, zorder=4)
        ax.scatter(contrast["mean_difference_pp"], y, s=62, marker="D", color=color,
                   edgecolor="#202020", linewidth=0.9, zorder=5)
        ax.text(17.8, y + 0.27, f"{contrast['mean_difference_pp']:+.2f} [{lo:+.2f}, {hi:+.2f}]",
                ha="right", va="center", fontsize=11)
    ax.axvline(0, color="#555555", linestyle="--", linewidth=0.8)
    ax.set(yticks=[0, 1], yticklabels=["Full − LDA-only\nPrimary", "EA − Full\nSecondary"],
           ylim=(1.55, -0.5), xlim=(-9, 18),
           xlabel="Paired BA difference (percentage points)")
    ax.set_title("B  Participant effects and 95% intervals", loc="left", weight="bold")

    maximum = float(np.ceil(max(np.max(np.abs(matrix)) for matrix in heatmaps) / 5) * 5)
    cmap = colors.LinearSegmentedColormap.from_list("signed_blue_orange", ["#ca793d", "#fffefd", "#2c79a7"])
    for col, (matrix, label) in enumerate(zip(heatmaps, ("Full − LDA-only", "EA − Full"))):
        ax = axes[1, col]
        im = ax.imshow(matrix, cmap=cmap, vmin=-maximum, vmax=maximum, aspect="auto",
                       interpolation="none")
        for i in range(9):
            for j in range(5):
                value = matrix[i, j]
                ax.text(j, i, f"{value:+.1f}" if abs(value) > 1e-10 else "0.0",
                        ha="center", va="center", fontsize=11,
                        color="white" if abs(value) > maximum * 0.62 else "#222222")
        ax.set(xticks=range(5), xticklabels=range(2, 7),
               yticks=range(9), yticklabels=[f"{int(p):02d}" for p in PARTICIPANTS],
               xlabel="Target-session query run", ylabel="Participant")
        ax.set_title(f"{'C' if col == 0 else 'D'}  {label} by query run", loc="left", weight="bold")
    colorbar = figure.colorbar(im, ax=axes[1, :], orientation="horizontal", fraction=0.08,
                               pad=0.09, aspect=42, ticks=[-maximum, -maximum / 2, 0, maximum / 2, maximum])
    colorbar.set_label("Within-run BA difference (percentage points)", fontsize=12)

    args.output.mkdir(parents=True, exist_ok=True)
    stem = args.output / "Fig5_external_validation"
    figure.canvas.draw()
    native_minimum = min(text.get_fontsize() for text in figure.findobj(Text)
                         if text.get_visible() and text.get_text().strip())
    width = figure.get_tightbbox(figure.canvas.get_renderer()).width + 2 * plt.rcParams["savefig.pad_inches"]
    minimum_at_170mm = native_minimum * (170 / 25.4) / width
    if minimum_at_170mm < 6:
        raise ValueError("Figure text would fall below 6pt at final journal width")
    for suffix in ("png", "pdf", "svg"):
        figure.savefig(stem.with_suffix("." + suffix), dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    fields = ["panel", "participant", "method", "run", "contrast", "value", "unit", "lower", "upper"]
    with stem.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sources)
    check = {"source_files": [{"file": str(p.relative_to(ROOT)), "sha256": digest(p)}
                              for p in (aggregate_path, runs_path)],
             "complete_participants": 9, "participant_method_endpoints": 36,
             "participant_method_run_endpoints": 180, "figure_source_rows": len(sources),
             "cohort_means_reconstructed": True, "run_to_session_contrasts_reconstructed": True,
             "original_figures_1_to_4_modified": False, "font_family": family,
             "native_minimum_font_points": native_minimum,
             "final_width_mm": 170, "minimum_font_points_at_final_width": minimum_at_170mm,
             "png_dpi": 600, "heatmap_common_symmetric_range_pp": [-maximum, maximum],
             "outputs": [{"file": str(stem.with_suffix('.' + s).relative_to(ROOT)),
                          "bytes": stem.with_suffix('.' + s).stat().st_size,
                          "sha256": digest(stem.with_suffix('.' + s))}
                         for s in ("png", "pdf", "svg", "csv")]}
    (args.results / "figure_checks.json").write_text(json.dumps(check, indent=2) + "\n")
    print(json.dumps(check, indent=2))


if __name__ == "__main__":
    main()
