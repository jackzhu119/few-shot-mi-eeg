"""Redraw Figure 3 from saved external-validation metrics, without model access.

The script only reads the frozen aggregate/run JSON and the earlier figure CSV.
It preserves every participant, contrast, saved interval, and heatmap cell.
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
from PIL import Image  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
LABELS = ("Frozen", "LDA-only", "Full refit", "EA-CSP")
PALETTE = ("#666666", "#009E73", "#0072B2", "#D55E00")
MARKERS = ("s", "^", "o", "D")
PARTICIPANTS = tuple(str(index) for index in range(1, 10))
COMPARISONS = (
    ("full_csp_minus_lda_only", "full_csp", "lda_only", "Full − LDA-only", "Primary"),
    ("ea_csp_minus_full_csp", "ea_csp", "full_csp", "EA − Full", "Secondary"),
)
FIELDS = ("panel", "participant", "method", "run", "contrast", "value", "unit", "lower", "upper")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_sources(aggregate_path: Path, runs_path: Path):
    """Reconstruct the existing figure's display data, without new inference."""
    aggregate = json.loads(aggregate_path.read_text())
    run_rows = json.loads(runs_path.read_text())
    if (aggregate["status"] != "complete" or aggregate["synthetic"]
            or tuple(aggregate["complete_participants"]) != PARTICIPANTS):
        raise ValueError("Expected the nine actual, complete participant endpoints")
    participant_index = {
        (row["participant"], row["method"]): row
        for row in aggregate["participant_results"]
    }
    run_index = {
        (row["participant"], row["method"], int(row["run_id"].rsplit("-", 1)[1])): row
        for row in run_rows
    }
    if len(participant_index) != 36 or len(aggregate["participant_results"]) != 36:
        raise ValueError("Duplicate or missing participant/method endpoint")
    if len(run_index) != 180 or len(run_rows) != 180:
        raise ValueError("Duplicate or missing participant/method/query-run endpoint")
    if any(row["class_counts"] != {"0": 60, "1": 60}
           for row in participant_index.values()):
        raise ValueError("Saved session endpoint class counts changed")
    if any(row["class_counts"] != {"0": 12, "1": 12} for row in run_index.values()):
        raise ValueError("Saved query-run endpoint class counts changed")

    values = np.array([
        [participant_index[(person, method)]["balanced_accuracy"] * 100 for method in METHODS]
        for person in PARTICIPANTS
    ])
    if np.any((values < 0) | (values > 100)):
        raise ValueError("Invalid balanced-accuracy endpoint")
    sources, effects, heatmaps = [], [], []
    for row_index, person in enumerate(PARTICIPANTS):
        for column, method in enumerate(METHODS):
            sources.append({"panel": "A", "participant": person, "method": method,
                            "value": values[row_index, column], "unit": "BA_percent"})
    for column, method in enumerate(METHODS):
        mean = values[:, column].mean()
        np.testing.assert_allclose(
            mean, aggregate["cohort_balanced_accuracy"][method]["mean_percent"],
            atol=1e-12, rtol=0,
        )
        sources.append({"panel": "A", "participant": "cohort_mean", "method": method,
                        "value": mean, "unit": "BA_percent"})
    for comparison_index, (name, newer, reference, _, _) in enumerate(COMPARISONS):
        contrast = aggregate["contrasts"][name]
        difference = np.array([
            (participant_index[(person, newer)]["balanced_accuracy"]
             - participant_index[(person, reference)]["balanced_accuracy"]) * 100
            for person in PARTICIPANTS
        ])
        np.testing.assert_allclose(difference.mean(), contrast["mean_difference_pp"],
                                   atol=1e-12, rtol=0)
        effects.append(difference)
        for person, value in zip(PARTICIPANTS, difference):
            sources.append({"panel": "B", "participant": person, "contrast": name,
                            "value": value, "unit": "BA_percentage_points"})
        sources.append({
            "panel": "B", "participant": "cohort_mean", "contrast": name,
            "value": contrast["mean_difference_pp"], "unit": "BA_percentage_points",
            "lower": contrast["bootstrap_ci95_pp"][0],
            "upper": contrast["bootstrap_ci95_pp"][1],
        })
        matrix = np.array([
            [(run_index[(person, newer, run)]["balanced_accuracy"]
              - run_index[(person, reference, run)]["balanced_accuracy"]) * 100
             for run in range(2, 7)]
            for person in PARTICIPANTS
        ])
        np.testing.assert_allclose(matrix.mean(axis=1), difference, atol=1e-12, rtol=0)
        heatmaps.append(matrix)
        for row_index, person in enumerate(PARTICIPANTS):
            for column, run in enumerate(range(2, 7)):
                sources.append({"panel": "C" if comparison_index == 0 else "D",
                                "participant": person, "run": run, "contrast": name,
                                "value": matrix[row_index, column],
                                "unit": "BA_percentage_points"})
    return aggregate, values, effects, heatmaps, sources


def verify_previous_csv(path: Path, sources: list[dict]) -> dict:
    """Check all points and both historical confidence intervals by identity."""
    with path.open(newline="") as stream:
        previous = list(csv.DictReader(stream))
    identity = ("panel", "participant", "method", "run", "contrast", "unit")

    def key(row):
        return tuple(str(row.get(field, "")) for field in identity)

    previous_index = {key(row): row for row in previous}
    current_index = {key(row): row for row in sources}
    if (len(previous_index) != len(previous) or len(current_index) != len(sources)
            or previous_index.keys() != current_index.keys()):
        raise ValueError("Figure source identities differ from the earlier Figure 3")
    checked_values = 0
    maximum_error = 0.0
    for row_key, row in current_index.items():
        for field in ("value", "lower", "upper"):
            old_value, new_value = previous_index[row_key].get(field, ""), row.get(field, "")
            if old_value == "" and new_value == "":
                continue
            if old_value == "" or new_value == "":
                raise ValueError(f"Missing value in previous/current figure: {row_key}/{field}")
            error = abs(float(old_value) - float(new_value))
            if error > 1e-12:
                raise ValueError(f"Numerical figure mismatch: {row_key}/{field}")
            checked_values += 1
            maximum_error = max(maximum_error, error)
    return {"rows": len(sources), "numerical_fields_compared": checked_values,
            "maximum_absolute_error": maximum_error,
            "all_identities_and_saved_confidence_intervals_equivalent": True}


def panel_title(axis, letter: str, title: str):
    axis.text(0.0, 1.045, letter, transform=axis.transAxes,
              fontsize=10, fontweight="bold", va="bottom", ha="left")
    axis.annotate(title, xy=(0.0, 1.045), xycoords="axes fraction",
                  xytext=(14, 0), textcoords="offset points",
                  fontsize=8, va="bottom", ha="left")


def signed(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}".replace("-", "−")


def render(aggregate, values, effects, heatmaps):
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    family = next((name for name in ("Arial", "Helvetica") if name in available_fonts),
                  "DejaVu Sans")
    plt.rcParams.update({
        "font.family": family, "font.size": 8, "axes.labelsize": 8,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 3, "ytick.major.size": 3,
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.facecolor": "white", "figure.facecolor": "white",
    })
    figure = plt.figure(figsize=(170 / 25.4, 145 / 25.4))
    grid = figure.add_gridspec(
        2, 2, left=0.09, right=0.985, top=0.945, bottom=0.185,
        width_ratios=(1.02, 1), height_ratios=(1, 1.25), wspace=0.29, hspace=0.48,
    )
    ax = figure.add_subplot(grid[0, 0])
    panel_title(ax, "A", "Method performance (n = 9)")
    jitter = np.linspace(-0.085, 0.085, len(PARTICIPANTS))
    for person_index, participant_values in enumerate(values):
        ax.plot(np.arange(4) + jitter[person_index], participant_values,
                color="#CFCFCF", linewidth=0.55, zorder=1)
    for column, (color, marker) in enumerate(zip(PALETTE, MARKERS)):
        ax.scatter(column + jitter, values[:, column], s=13, marker=marker, color=color,
                   edgecolor="white", linewidth=0.25, zorder=3)
        ax.scatter(column, values[:, column].mean(), s=30, marker="D", color=color,
                   edgecolor="#202020", linewidth=0.65, zorder=4)
    ax.axhline(50, color="#707070", linestyle=(0, (3, 2)), linewidth=0.6, zorder=0)
    mean_labels = [f"{label}\n{mean:.2f}" for label, mean in zip(LABELS, values.mean(axis=0))]
    ax.set(xticks=range(4), xticklabels=mean_labels, xlim=(-0.36, 3.36), ylim=(40, 100),
           yticks=(40, 60, 80, 100), ylabel="Query balanced accuracy (%)")

    # The right-hand panel uses separate label/forest/value columns.  CI text
    # therefore cannot cover a participant point, or influence the x limits.
    subgrid = grid[0, 1].subgridspec(1, 3, width_ratios=(0.83, 1.12, 1.19), wspace=0.045)
    label_axis = figure.add_subplot(subgrid[0, 0])
    forest_axis = figure.add_subplot(subgrid[0, 1])
    text_axis = figure.add_subplot(subgrid[0, 2])
    panel_title(label_axis, "B", "Paired effects")
    for axis in (label_axis, forest_axis, text_axis):
        axis.set_ylim(1.65, -0.5)
    for axis in (label_axis, text_axis):
        axis.set_axis_off()
    for row, (name, _, _, label, role) in enumerate(COMPARISONS):
        color = PALETTE[2] if row == 0 else PALETTE[3]
        contrast = aggregate["contrasts"][name]
        label_axis.text(1.0, row, f"{label}\n{role}", ha="right", va="center", fontsize=8)
        forest_axis.scatter(effects[row], row + np.linspace(-0.13, 0.13, 9),
                            s=12, color=color, edgecolor="white", linewidth=0.25, zorder=3)
        mean = contrast["mean_difference_pp"]
        lower, upper = contrast["bootstrap_ci95_pp"]
        forest_axis.errorbar(
            [mean], [row], xerr=np.array([[mean - lower], [upper - mean]]),
            fmt="D", markersize=4.5, color=color, markeredgecolor="#202020",
            markeredgewidth=0.65, ecolor="#202020", elinewidth=1.05,
            capsize=2.6, capthick=0.8, zorder=4,
        )
        text_axis.text(0.04, row, f"{signed(mean)}\n[{signed(lower)}, {signed(upper)}]",
                       ha="left", va="center", fontsize=8, linespacing=1.35)
    forest_axis.axvline(0, color="#707070", linestyle=(0, (3, 2)), linewidth=0.6)
    forest_axis.set(xlim=(-9, 18), xticks=(-5, 5, 15), yticks=[], xlabel="BA difference (pp)")
    forest_axis.spines["left"].set_visible(False)

    cmap = colors.LinearSegmentedColormap.from_list(
        "signed_blue_orange", ["#CA793D", "#FFFEFD", "#2C79A7"]
    )
    heatmap_axes = []
    for column, (matrix, title) in enumerate(zip(heatmaps, ("Full − LDA-only", "EA − Full"))):
        axis = figure.add_subplot(grid[1, column])
        heatmap_axes.append(axis)
        panel_title(axis, "C" if column == 0 else "D", f"{title} by query run")
        image = axis.pcolormesh(
            np.arange(6) - 0.5, np.arange(10) - 0.5, matrix,
            cmap=cmap, vmin=-35, vmax=35, shading="flat", rasterized=False,
            edgecolors="none", antialiased=False,
        )
        for row in range(9):
            for col in range(5):
                value = matrix[row, col]
                axis.text(col, row, signed(value, 1) if abs(value) > 1e-10 else "0.0",
                          ha="center", va="center", fontsize=8,
                          color="white" if abs(value) > 35 * 0.62 else "#222222")
        axis.set(xlim=(-0.5, 4.5), ylim=(8.5, -0.5), xticks=range(5),
                 xticklabels=range(2, 7), yticks=range(9),
                 yticklabels=[f"{int(person):02d}" for person in PARTICIPANTS],
                 xlabel="Target-session query run", ylabel="Participant")
    colorbar_axis = figure.add_axes((0.10, 0.083, 0.85, 0.022))
    colorbar = figure.colorbar(image, cax=colorbar_axis, orientation="horizontal",
                              ticks=(-35, -17.5, 0, 17.5, 35))
    colorbar.solids.set_rasterized(False)
    colorbar.solids.set_edgecolor("face")
    colorbar.outline.set_linewidth(0.5)
    colorbar.set_label("Within-run balanced-accuracy difference (percentage points)",
                       fontsize=8, labelpad=3)
    figure.canvas.draw()
    visible = [text for text in figure.findobj(Text)
               if text.get_visible() and text.get_text().strip()]
    minimum_font = min(text.get_fontsize() for text in visible)
    if minimum_font < 8:
        raise ValueError("Text smaller than 8 pt at the exact 170 mm output width")
    return figure, family, minimum_font


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path,
                        default=ROOT / "research_logs/paper2_external_validation_20261027")
    parser.add_argument("--previous-csv", type=Path, default=ROOT / (
        "manuscript/bmt_component_revision_20261029/figures/"
        "Fig3_external_validation_source_data.csv"))
    parser.add_argument("--output", type=Path,
                        default=ROOT / "manuscript/bmt_component_revision_20261029/figures")
    args = parser.parse_args()
    aggregate_path = args.results / "aggregate.json"
    runs_path = args.results / "run_metrics.json"
    aggregate, values, effects, heatmaps, sources = read_sources(aggregate_path, runs_path)
    equivalence = verify_previous_csv(args.previous_csv, sources)
    figure, family, minimum_font = render(aggregate, values, effects, heatmaps)
    args.output.mkdir(parents=True, exist_ok=True)
    stem = args.output / "Fig3_external_validation"
    # No tight bounding-box rescaling: the physical width remains exactly 170 mm.
    for extension in ("png", "pdf", "svg"):
        figure.savefig(stem.with_suffix("." + extension), dpi=600)
    figure.savefig(stem.with_suffix(".tiff"), dpi=600,
                   pil_kwargs={"compression": "tiff_lzw"})
    with Image.open(stem.with_suffix(".tiff")) as raster:
        rgb = raster.convert("RGB")
    rgb.save(stem.with_suffix(".tiff"), compression="tiff_lzw", dpi=(600, 600))
    plt.close(figure)
    with stem.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sources)
    svg_text = stem.with_suffix(".svg").read_text()
    if "<image " in svg_text or "<text " not in svg_text:
        raise ValueError("SVG must retain editable text and vector heatmap rectangles")
    with Image.open(stem.with_suffix(".tiff")) as tiff:
        tiff_check = {"compression": tiff.info.get("compression"), "mode": tiff.mode,
                      "dpi": [float(value) for value in tiff.info.get("dpi", [])],
                      "pixels": list(tiff.size)}
        if tiff_check["compression"] != "tiff_lzw":
            raise ValueError("TIFF output was not LZW compressed")
    manifest = {
        "figure": "Fig3_external_validation", "rendering_only": True,
        "decoder_or_EEG_loaded": False, "new_fit_or_prediction": False,
        "source_files": [{"file": relative(path), "sha256": digest(path)}
                         for path in (aggregate_path, runs_path, args.previous_csv)],
        "renderer": {"file": relative(Path(__file__).resolve()),
                     "sha256": digest(Path(__file__).resolve())},
        "prior_figure_csv_equivalence": equivalence,
        "participants": list(PARTICIPANTS), "participant_method_endpoints": 36,
        "participant_method_query_run_endpoints": 180,
        "method_colors": dict(zip(METHODS, PALETTE)),
        "participant_marker_shapes": dict(zip(METHODS, MARKERS)),
        "participant_pairs_connect_actual_jittered_points": True,
        "paired_confidence_intervals": {
            name: {"mean_difference_pp": aggregate["contrasts"][name]["mean_difference_pp"],
                   "saved_bootstrap_ci95_pp": aggregate["contrasts"][name]["bootstrap_ci95_pp"]}
            for name, *_ in COMPARISONS
        },
        "cohort_mean_BA_percent": dict(zip(METHODS, values.mean(axis=0).tolist())),
        "font_family": family, "minimum_font_points_at_final_width": minimum_font,
        "panel_letter_font_points": 10, "final_width_mm": 170, "final_height_mm": 145,
        "raster_dpi": 600, "BA_axis_limits_percent": [40, 100],
        "heatmap_symmetric_range_pp": [-35, 35],
        "heatmaps_vector_rectangles": True, "SVG_text_editable": True,
        "PDF_font_type": 42, "TIFF": tiff_check,
        "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__,
        "outputs": [{"file": relative(stem.with_suffix("." + extension)),
                     "bytes": stem.with_suffix("." + extension).stat().st_size,
                     "sha256": digest(stem.with_suffix("." + extension))}
                    for extension in ("png", "pdf", "svg", "tiff", "csv")],
    }
    manifest_path = args.output / "Fig3_external_validation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output_directory": str(args.output), "equivalence": equivalence,
                      "font": family, "manifest": str(manifest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
