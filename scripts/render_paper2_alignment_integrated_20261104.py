"""Render the integrated Paper2 figures from recorded participant-level evidence.

No EEG, checkpoint, fit, inference or bootstrap is invoked here.  Historical
contrast intervals retain their historical identities; new descriptive intervals
are read from the frozen-analysis tables, never recalculated by the renderer.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.text import Text
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "research_logs/paper2_alignment_integrated_20261104/analysis"
METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
LABELS = ("Frozen", "LDA-only", "Full", "EA")
COLORS = {"frozen": "#666666", "lda_only": "#009E73", "full_csp": "#0072B2", "ea_csp": "#D55E00"}
MARKERS = {"frozen": "o", "lda_only": "s", "full_csp": "^", "ea_csp": "D"}
STYLES = {"frozen": ":", "lda_only": "--", "full_csp": "-.", "ea_csp": "-"}
PRIMARY = tuple(f"sub-{n}" for n in (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18))
DEVELOPMENT = tuple(f"sub-{n}" for n in (1, 4, 7, 10, 13, 16))
COHORTS = (
    ("Kumar2024", "remaining12", "Kumar2024: original 12", PRIMARY),
    (
        "BNCI2014-001",
        "external9",
        "BNCI2014-001: 9 participants",
        tuple(f"sub-{n:02d}" for n in range(1, 10)),
    ),
)
NEW_CI = "descriptive_10000_seed20261104_numeric_participant_order"
FIELDS = (
    "panel",
    "dataset",
    "cohort",
    "participant",
    "budget",
    "method",
    "contrast",
    "statistic",
    "value",
    "lower",
    "upper",
    "unit",
    "interval_identity",
)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def one(rows, **criteria):
    result = [r for r in rows if all(r.get(k) == v for k, v in criteria.items())]
    if len(result) != 1:
        raise ValueError(f"Expected one source row for {criteria}, received {len(result)}")
    return result[0]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def num(row, key):
    value = float(row[key])
    if not np.isfinite(value):
        raise ValueError(f"Nonfinite plot datum: {key}")
    return value


def record(rows, **values):
    rows.append({key: values.get(key, "") for key in FIELDS})


def panel(ax, letter, title):
    ax.text(-0.16, 1.09, letter, transform=ax.transAxes, fontsize=10, weight="bold", va="top")
    ax.set_title(title, fontsize=8.5, loc="left", pad=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3, width=0.6, pad=3, labelsize=8)


def point_interval(ax, x, y, low, high, *, color="black", marker="D", horizontal=False):
    if horizontal:
        ax.errorbar(
            x,
            y,
            xerr=[[x - low], [high - x]],
            fmt=marker,
            color=color,
            ms=5,
            lw=1,
            capsize=2,
            zorder=5,
        )
    else:
        ax.errorbar(
            x,
            y,
            yerr=[[y - low], [high - y]],
            fmt=marker,
            color=color,
            ms=5,
            lw=1,
            capsize=2,
            zorder=5,
        )


def export(fig, stem, rows, output):
    """Keep exact 170 mm canvas width, vector text, RGB 600 dpi TIFF."""
    fig.canvas.draw()
    sizes = [obj.get_fontsize() for obj in fig.findobj(Text) if obj.get_text().strip()]
    if sizes and min(sizes) < 8:
        raise ValueError(f"{stem}: font below 8 pt")
    if abs(fig.get_figwidth() * 25.4 - 170) > 1e-8:
        raise ValueError("Unexpected figure width")
    renderer = fig.canvas.get_renderer()
    outside_ticks = set()
    for ax in fig.axes:
        for axis, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
            low, high = sorted(limits)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    outside_ticks.update((tick.label1, tick.label2))
    clipped = []
    for text in fig.findobj(Text):
        if text in outside_ticks or not text.get_visible() or not text.get_text().strip():
            continue
        bounds = text.get_window_extent(renderer)
        if (
            bounds.x0 < -1
            or bounds.y0 < -1
            or bounds.x1 > fig.bbox.x1 + 1
            or bounds.y1 > fig.bbox.y1 + 1
        ):
            clipped.append(text.get_text())
    if clipped:
        raise ValueError(f"Text outside figure canvas in {stem}: {clipped}")
    for ext in ("pdf", "svg", "png"):
        options = {"dpi": 600, "facecolor": "white"}
        if ext == "pdf":
            options["metadata"] = {
                "Creator": "Python / Matplotlib",
                "CreationDate": None,
                "ModDate": None,
            }
        elif ext == "svg":
            options["metadata"] = {"Creator": "Python / Matplotlib", "Date": None}
        fig.savefig(output / f"{stem}.{ext}", **options)
    with Image.open(output / f"{stem}.png") as image:
        image.convert("RGB").save(output / f"{stem}.tiff", compression="tiff_lzw", dpi=(600, 600))
    with (output / f"{stem}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    plt.close(fig)
    import fitz

    with fitz.open(output / f"{stem}.pdf") as document:
        raster_count = sum(len(page.get_images()) for page in document)
    svg = ET.parse(output / f"{stem}.svg")
    svg_images = sum(node.tag.endswith("}image") for node in svg.iter())
    with Image.open(output / f"{stem}.tiff") as image:
        raster = {
            "pixels": list(image.size),
            "mode": image.mode,
            "dpi": [float(x) for x in image.info["dpi"]],
            "compression": image.info["compression"],
        }
    if raster_count or svg_images or raster["mode"] != "RGB":
        raise ValueError(f"Publication-format check failed: {stem}")
    return {
        "stem": stem,
        "width_mm": 170,
        "minimum_font_pt": min(sizes),
        "PDF_raster_image_count": raster_count,
        "SVG_image_element_count": svg_images,
        "visible_text_within_canvas": True,
        "tiff": raster,
        "plot_rows": len(rows),
        "outputs": [
            {
                "file": f"{stem}.{ext}",
                "bytes": (output / f"{stem}.{ext}").stat().st_size,
                "sha256": digest(output / f"{stem}.{ext}"),
            }
            for ext in ("pdf", "svg", "tiff", "png", "csv")
        ],
    }


def workflow(output):
    fig = plt.figure(figsize=(170 / 25.4, 115 / 25.4))
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.98])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rows, nodes, edges = [], [], []
    input_audit = json.loads(
        (
            ROOT
            / "research_logs/paper2_alignment_integrated_20261104/input_audit/INPUT_MANIFEST.json"
        ).read_text()
    )
    source_kumar = input_audit["trial_metadata"]["roles_included"]["source_train"] // len(
        input_audit["trial_metadata"]["subjects"]
    )
    source_bnci = input_audit["preprocessing"]["BNCI2014-001"]["counts"]["source_train"]
    if (source_kumar, source_bnci) != (40, 96):
        raise ValueError("Frozen source-label counts changed")
    for dataset, key, value in [
        ("Kumar2024", "source_train_labels", source_kumar),
        ("BNCI2014-001", "source_train_labels", source_bnci),
        ("Kumar2024", "minimum_full_support_labels", 19),
        ("Kumar2024", "maximum_full_support_labels", 20),
        ("BNCI2014-001", "support_labels", 20),
    ]:
        record(rows, panel="workflow", dataset=dataset, statistic=key, value=value, unit="labels")
    ax.text(
        0.5,
        0.965,
        "Kumar2024 / BNCI2014-001: matched calibration information",
        ha="center",
        fontsize=9,
    )
    ax.text(
        0.5,
        0.915,
        "Source TRAIN: 40 / 96 labels     Current support: 19–20 / 20 labels",
        ha="center",
        fontsize=8,
    )

    def box(identity, x, y, width, height, text):
        ax.add_patch(
            Rectangle((x, y), width, height, facecolor="white", edgecolor="#444444", lw=0.8)
        )
        ax.text(
            x + width / 2,
            y + height / 2,
            text,
            ha="center",
            va="center",
            fontsize=8,
            linespacing=1.25,
        )
        nodes.append(
            {"id": identity, "x": x, "y": y, "width": width, "height": height, "text": text}
        )
        record(
            rows,
            panel="workflow",
            method=identity,
            statistic="node_label",
            value=text,
            unit="label",
        )

    def arrow(start, end, identity):
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=8,
                linewidth=0.8,
                color="#444444",
                shrinkA=0,
                shrinkB=0,
            )
        )
        edges.append({"id": identity, "x0": start[0], "y0": start[1], "x1": end[0], "y1": end[1]})

    box("source", 0.015, 0.72, 0.25, 0.12, "Source TRAIN\nFixed earlier-session labels")
    box("support", 0.015, 0.43, 0.25, 0.12, "Current-session support\nChronological first run")
    ys = [0.78, 0.58, 0.38, 0.18]
    descriptions = [
        "Frozen\nSource CSP + LDA kept fixed",
        "LDA-only\nSource CSP fixed; refit LDA",
        "Full refit\nRefit CSP + LDA",
        "EA-CSP\nSeparate source/support whitening;\nrefit CSP + LDA",
    ]
    for method, y, text in zip(METHODS, ys, descriptions):
        box(method, 0.39, y - 0.065, 0.34, 0.13, text)
    arrow((0.265, 0.78), (0.39, 0.78), "source_to_frozen")
    ax.plot([0.305, 0.305], [0.78, 0.68], color="#444444", lw=0.8)
    arrow((0.305, 0.68), (0.305, 0.64), "source_to_updates")
    ax.plot([0.305, 0.305], [0.18, 0.64], color="#444444", lw=0.8)
    arrow((0.265, 0.49), (0.305, 0.49), "support_to_updates")
    for method, y in zip(METHODS[1:], ys[1:]):
        arrow((0.305, y), (0.39, y), "source_support_to_" + method)
    ax.text(
        0.13,
        0.20,
        "Same source + support\nfor updating pipelines",
        ha="center",
        va="center",
        fontsize=8,
    )
    box("query", 0.82, 0.39, 0.165, 0.2, "Later query\nShared trial IDs\nPrediction +\nscoring")
    ax.plot([0.78, 0.78], [0.18, 0.78], color="#444444", lw=0.8)
    for method, y in zip(METHODS, ys):
        arrow((0.73, y), (0.78, y), method + "_to_prediction")
    arrow((0.78, 0.49), (0.82, 0.49), "models_to_query")
    ax.text(
        0.5,
        0.015,
        "EA references use source TRAIN and current support; query enters after fitting.",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    for name, data in [("nodes", nodes), ("edges", edges)]:
        with (output / f"Fig1_workflow_{name}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    result = export(fig, "Fig1_workflow", rows, output)
    result["additional_data_files"] = [
        {
            "file": f"Fig1_workflow_{name}.csv",
            "sha256": digest(output / f"Fig1_workflow_{name}.csv"),
        }
        for name in ("nodes", "edges")
    ]
    return result


def performance(tables, output):
    points, means = tables["participant_metrics"], tables["cohort_method_metrics"]
    historical = read_csv(
        ROOT / "manuscript/bmt_component_revision_20261029/figures/Fig1_components.csv"
    )
    original = json.loads(
        (
            ROOT / "research_logs/kumar_cross_session_20261012/baselines/"
            "cpu_run01_20261013T151445Z/participant_bootstrap_summary.json"
        ).read_text()
    )
    bnci = json.loads(
        (ROOT / "research_logs/paper2_external_validation_20261027/aggregate.json").read_text()
    )
    rows = []
    fig, axs = plt.subplots(
        2, 2, figsize=(170 / 25.4, 153 / 25.4), gridspec_kw={"height_ratios": [1.4, 1]}
    )
    fig.subplots_adjust(left=0.18, right=0.98, bottom=0.11, top=0.92, wspace=0.63, hspace=0.58)
    for col, (dataset, cohort, title, members) in enumerate(COHORTS):
        ax = axs[0, col]
        panel(ax, "AB"[col], title)
        offsets = np.linspace(-0.12, 0.12, len(members))
        values = np.array(
            [
                [
                    num(
                        one(
                            points,
                            dataset=dataset,
                            participant=person,
                            method=method,
                            budget="full",
                            subset="all_query",
                        ),
                        "ba",
                    )
                    * 100
                    for method in METHODS
                ]
                for person in members
            ]
        )
        for i, person in enumerate(members):
            ax.plot(
                np.arange(4) + offsets[i], values[i], color="#bbbbbb", lw=0.45, alpha=0.55, zorder=1
            )
        for k, method in enumerate(METHODS):
            ax.scatter(
                k + offsets,
                values[:, k],
                s=17,
                marker=MARKERS[method],
                color=COLORS[method],
                alpha=0.65,
                edgecolor="none",
                zorder=2,
            )
            m = one(
                means,
                dataset=dataset,
                cohort=cohort,
                budget="full",
                subset="all_query",
                method=method,
                metric="ba",
            )
            point_interval(
                ax,
                k,
                100 * num(m, "mean"),
                100 * num(m, "ci_low"),
                100 * num(m, "ci_high"),
                color="black",
            )
            for i, person in enumerate(members):
                record(
                    rows,
                    panel="AB"[col],
                    dataset=dataset,
                    cohort=cohort,
                    participant=person,
                    budget="full",
                    method=method,
                    statistic="ba",
                    value=values[i, k],
                    unit="percent",
                )
            record(
                rows,
                panel="AB"[col],
                dataset=dataset,
                cohort=cohort,
                participant="mean",
                budget="full",
                method=method,
                statistic="ba",
                value=100 * num(m, "mean"),
                lower=100 * num(m, "ci_low"),
                upper=100 * num(m, "ci_high"),
                unit="percent",
                interval_identity=NEW_CI,
            )
        ax.axhline(50, ls=":", color="#999999", lw=0.7)
        ax.set(
            xticks=range(4),
            xticklabels=LABELS,
            xlim=(-0.45, 3.45),
            ylim=(35, 100),
            ylabel="Balanced accuracy (%)",
        )
        ax.yaxis.set_major_locator(plt.MultipleLocator(20))
        ax = axs[1, col]
        panel(ax, "CD"[col], "Historical paired contrasts")
        if col == 0:
            # Original Full–Frozen CI is read from its original frozen summary.
            items = original["cohorts"]["final_test"]["paired_comparisons"]
            full = items["refit_csp_lda_minus_source_only"]
            comp = [
                (
                    "Full − Frozen",
                    "Primary",
                    num(full, "mean_difference") * 100,
                    full["ci95"][0] * 100,
                    full["ci95"][1] * 100,
                    "original_historical_10000_seed42_lexicographic_participant_order",
                    "full_minus_frozen",
                )
            ]
            for contrast, label, role in [
                ("full_minus_lda_pp", "Full − LDA-only", "Secondary"),
                ("ea_minus_full", "EA − Full", "Exploratory"),
            ]:
                r = one(historical, panel="B", participant="mean", contrast=contrast)
                comp.append(
                    (
                        label,
                        role,
                        num(r, "value"),
                        num(r, "lower"),
                        num(r, "upper"),
                        r["interval_scope"],
                        contrast,
                    )
                )
        else:
            comp = []
            for key, label in [
                ("full_csp_minus_lda_only", "Full − LDA-only"),
                ("full_csp_minus_frozen", "Full − Frozen"),
                ("ea_csp_minus_full_csp", "EA − Full"),
            ]:
                r = bnci["contrasts"][key]
                comp.append(
                    (
                        label,
                        r["role"].capitalize(),
                        r["mean_difference_pp"],
                        *r["bootstrap_ci95_pp"],
                        "historical_10000_seed20261027_numeric_participant_order",
                        key,
                    )
                )
        for y, (label, role, mean, lo, hi, scope, contrast) in enumerate(comp):
            marker = {"Primary": "o", "Secondary": "s", "Exploratory": "D"}[role]
            point_interval(
                ax,
                mean,
                y,
                lo,
                hi,
                marker=marker,
                color=COLORS["ea_csp"] if label.startswith("EA") else COLORS["full_csp"],
                horizontal=True,
            )
            record(
                rows,
                panel="CD"[col],
                dataset=dataset,
                cohort=cohort,
                participant="mean",
                budget="full",
                contrast=contrast,
                statistic="delta_ba",
                value=mean,
                lower=lo,
                upper=hi,
                unit="percentage_points",
                interval_identity=scope,
            )
        ax.axvline(0, ls=":", color="#999999", lw=0.7)
        ax.set(
            yticks=range(len(comp)),
            yticklabels=[f"{r[0]}\n{r[1]}" for r in comp],
            ylim=(len(comp) - 0.55, -0.55),
            xlim=(-4, 15),
            xlabel="Paired difference (pp)",
        )
    fig.legend(
        [
            Line2D([], [], marker="o", linestyle="none", color="#888888", ms=4),
            Line2D([], [], marker="D", color="black", ms=4),
        ],
        ["Participant", "Mean and 95% participant interval"],
        loc="lower center",
        ncol=2,
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(0.5, 0.005),
    )
    return export(fig, "Fig2_performance", rows, output)


def error_coverage(tables, output):
    cohorts, people = tables["cohort_contrasts"], tables["participant_contrasts"]
    rows = []
    fig, axs = plt.subplots(2, 2, figsize=(170 / 25.4, 151 / 25.4))
    fig.subplots_adjust(left=0.22, right=0.98, bottom=0.09, top=0.93, wspace=0.70, hspace=0.63)
    ax = axs[0, 0]
    panel(ax, "A", "EA − Full: error redistribution")
    for i, (dataset, cohort, _, members) in enumerate(COHORTS):
        for j, metric in enumerate(("corrected", "introduced")):
            y = i * 2 + j
            m = one(
                cohorts,
                dataset=dataset,
                cohort=cohort,
                budget="full",
                subset="all_query",
                contrast="ea_minus_full",
                metric=metric,
            )
            vals = [
                num(
                    one(
                        people,
                        dataset=dataset,
                        participant=p,
                        budget="full",
                        subset="all_query",
                        contrast="ea_minus_full",
                    ),
                    metric,
                )
                * 100
                for p in members
            ]
            ax.scatter(
                vals, y + np.linspace(-0.10, 0.10, len(vals)), s=12, color="#aaaaaa", zorder=1
            )
            point_interval(
                ax,
                100 * num(m, "mean"),
                y,
                100 * num(m, "ci_low"),
                100 * num(m, "ci_high"),
                horizontal=True,
                marker="o" if i == 0 else "^",
            )
            record(
                rows,
                panel="A",
                dataset=dataset,
                cohort=cohort,
                participant="mean",
                budget="full",
                contrast="ea_minus_full",
                statistic=metric,
                value=100 * num(m, "mean"),
                lower=100 * num(m, "ci_low"),
                upper=100 * num(m, "ci_high"),
                unit="class_balanced_query_percent",
                interval_identity=NEW_CI,
            )
            for p, v in zip(members, vals):
                record(
                    rows,
                    panel="A",
                    dataset=dataset,
                    cohort=cohort,
                    participant=p,
                    budget="full",
                    contrast="ea_minus_full",
                    statistic=metric,
                    value=v,
                    unit="class_balanced_query_percent",
                )
    ax.set(
        yticks=range(4),
        yticklabels=[
            "Kumar: corrected",
            "Kumar: introduced",
            "BNCI: corrected",
            "BNCI: introduced",
        ],
        ylim=(3.5, -0.5),
        xlabel="Class-balanced query share (%)",
        xlim=(0, 31),
    )
    ax = axs[0, 1]
    panel(ax, "B", "EA − Full: accuracy and coverage")
    for i, (dataset, cohort, _, _) in enumerate(COHORTS):
        for j, metric in enumerate(("delta_ba", "delta_weak_recall")):
            y = i * 2 + j
            m = one(
                cohorts,
                dataset=dataset,
                cohort=cohort,
                budget="full",
                subset="all_query",
                contrast="ea_minus_full",
                metric=metric,
            )
            point_interval(
                ax,
                100 * num(m, "mean"),
                y,
                100 * num(m, "ci_low"),
                100 * num(m, "ci_high"),
                horizontal=True,
                color=COLORS["ea_csp"],
                marker="o" if i == 0 else "^",
            )
            record(
                rows,
                panel="B",
                dataset=dataset,
                cohort=cohort,
                participant="mean",
                budget="full",
                contrast="ea_minus_full",
                statistic=metric,
                value=100 * num(m, "mean"),
                lower=100 * num(m, "ci_low"),
                upper=100 * num(m, "ci_high"),
                unit="percentage_points",
                interval_identity=NEW_CI,
            )
    ax.axvline(0, color="#999999", lw=0.7, ls=":")
    ax.set(
        yticks=range(4),
        yticklabels=["Kumar: ΔBA", "Kumar: ΔW", "BNCI: ΔBA", "BNCI: ΔW"],
        ylim=(3.5, -0.5),
        xlabel="Paired difference (pp)",
        xlim=(-1, 18),
    )
    for col, (dataset, cohort, title, members) in enumerate(COHORTS):
        ax = axs[1, col]
        panel(ax, "CD"[col], title)
        selected = [
            one(
                people,
                dataset=dataset,
                participant=p,
                budget="full",
                subset="all_query",
                contrast="ea_minus_full",
            )
            for p in members
        ]
        for r in selected:
            x, y = 100 * num(r, "delta_ba"), 100 * num(r, "delta_weak_recall")
            positive = x > 1e-10 and y > 1e-10
            ax.scatter(
                x,
                y,
                s=28,
                marker="o" if col == 0 else "^",
                facecolor=COLORS["ea_csp"] if positive else "white",
                edgecolor="black",
                lw=0.6,
                zorder=3,
            )
            if x < 0:
                offset = (6, -3) if r["participant"] == "sub-8" else (6, 10)
                ax.annotate(
                    r["participant"],
                    (x, y),
                    xytext=offset,
                    textcoords="offset points",
                    fontsize=8,
                    ha="left",
                    arrowprops={"arrowstyle": "-", "lw": 0.4, "color": "#777777"},
                )
            record(
                rows,
                panel="CD"[col],
                dataset=dataset,
                cohort=cohort,
                participant=r["participant"],
                budget="full",
                contrast="ea_minus_full",
                statistic="delta_ba",
                value=x,
                unit="percentage_points",
            )
            record(
                rows,
                panel="CD"[col],
                dataset=dataset,
                cohort=cohort,
                participant=r["participant"],
                budget="full",
                contrast="ea_minus_full",
                statistic="delta_weak_recall",
                value=y,
                unit="percentage_points",
            )
        n = sum(
            num(r, "delta_ba") > 1e-12 and num(r, "delta_weak_recall") > 1e-12 for r in selected
        )
        ax.text(
            0.04,
            0.94,
            f"Joint increase: {n}/{len(selected)}",
            transform=ax.transAxes,
            fontsize=8,
            va="top",
        )
        ax.axhline(0, color="#999999", lw=0.7)
        ax.axvline(0, color="#999999", lw=0.7)
        ax.set(
            xlim=(-2.5, 18),
            ylim=(-8, 35),
            xlabel="Δ balanced accuracy (pp)",
            ylabel="Δ weak-class recall (pp)",
        )
    return export(fig, "Fig3_error_coverage", rows, output)


def budgets(tables, output):
    means, gains = tables["cohort_method_metrics"], tables["cohort_contrasts"]
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(170 / 25.4, 85 / 25.4))
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.25, top=0.85, wspace=0.38)
    bs = ("4", "8", "12", "16", "full")
    xs = np.arange(5)
    ax = axs[0]
    panel(ax, "A", "Kumar2024: original 12")
    for k, method in enumerate(METHODS):
        selected = [
            one(
                means,
                dataset="Kumar2024",
                cohort="remaining12",
                budget=b,
                subset="all_query",
                method=method,
                metric="ba",
            )
            for b in bs
        ]
        ys = [100 * num(r, "mean") for r in selected]
        lo = [100 * num(r, "ci_low") for r in selected]
        hi = [100 * num(r, "ci_high") for r in selected]
        shifted = xs + (k - 1.5) * 0.045
        ax.errorbar(
            shifted,
            ys,
            yerr=[np.subtract(ys, lo), np.subtract(hi, ys)],
            color=COLORS[method],
            fmt=MARKERS[method],
            linestyle=STYLES[method],
            ms=4,
            lw=1,
            capsize=1.5,
            label=LABELS[k],
        )
        for b, r in zip(bs, selected):
            record(
                rows,
                panel="A",
                dataset="Kumar2024",
                cohort="remaining12",
                participant="mean",
                budget=b,
                method=method,
                statistic="ba",
                value=100 * num(r, "mean"),
                lower=100 * num(r, "ci_low"),
                upper=100 * num(r, "ci_high"),
                unit="percent",
                interval_identity=NEW_CI,
            )
    ax.set(
        xticks=xs,
        xticklabels=["4", "8", "12", "16", "19–20"],
        xlabel="Current-session labels",
        ylabel="Balanced accuracy (%)",
        ylim=(43, 87),
        xlim=(-0.35, 4.35),
    )
    ax.axhline(50, color="#999999", lw=0.7, ls=":")
    ax = axs[1]
    panel(ax, "B", "Added EA benefit beyond full refitting")
    selected = [
        one(
            gains,
            dataset="Kumar2024",
            cohort="remaining12",
            budget=b,
            subset="all_query",
            contrast="ea_minus_full",
            metric="delta_ba",
        )
        for b in bs
    ]
    ys = [100 * num(r, "mean") for r in selected]
    lo = [100 * num(r, "ci_low") for r in selected]
    hi = [100 * num(r, "ci_high") for r in selected]
    ax.errorbar(
        xs,
        ys,
        yerr=[np.subtract(ys, lo), np.subtract(hi, ys)],
        fmt="D-",
        color=COLORS["ea_csp"],
        ms=4,
        lw=1,
        capsize=2,
    )
    ax.axhline(0, color="#888888", lw=0.7, ls=":")
    ax.set(
        xticks=xs,
        xticklabels=["4", "8", "12", "16", "19–20"],
        xlabel="Current-session labels",
        ylabel="EA − Full (pp)",
        xlim=(-0.35, 4.35),
    )
    ax.set_ylim(min(-1, min(lo) - 0.8), max(hi) + 0.8)
    for b, r in zip(bs, selected):
        record(
            rows,
            panel="B",
            dataset="Kumar2024",
            cohort="remaining12",
            participant="mean",
            budget=b,
            contrast="ea_minus_full",
            statistic="delta_ba",
            value=100 * num(r, "mean"),
            lower=100 * num(r, "ci_low"),
            upper=100 * num(r, "ci_high"),
            unit="percentage_points",
            interval_identity=NEW_CI,
        )
    fig.legend(
        *axs[0].get_legend_handles_labels(),
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(0.5, 0.01),
        columnspacing=1.3,
    )
    return export(fig, "Fig4_budget", rows, output)


def mechanisms(tables, output, mechanism_root):
    """Render only completed, independently identified P2 summary tables."""
    points = read_csv(mechanism_root / "participant_metrics.csv")
    effects = read_csv(mechanism_root / "cohort_comparisons.csv")
    phases = read_csv(mechanism_root / "phase_cohort_comparisons.csv")
    arm_names = ("full", "rms_full", "diagonal_ea", "ea")
    arm_labels = ("Full", "RMS\n+ Full", "Diagonal\n+ Full", "EA\n+ Full")
    colors = {
        "full": COLORS["full_csp"],
        "rms_full": "#333333",
        "diagonal_ea": "#999999",
        "ea": COLORS["ea_csp"],
    }
    markers = dict(zip(arm_names, ("^", "s", "o", "D")))
    specs = [
        ("kumar", "kumar_primary12", "Matched Kumar2024 (n=12)"),
        ("bnci", "bnci9", "Matched BNCI (n=9)"),
    ]
    rows = []
    fig, axs = plt.subplots(
        2, 2, figsize=(170 / 25.4, 164 / 25.4), gridspec_kw={"height_ratios": [1.35, 1]}
    )
    fig.subplots_adjust(left=0.18, right=0.98, bottom=0.12, top=0.93, wspace=0.70, hspace=0.65)
    for col, (dataset, cohort, title) in enumerate(specs):
        ax = axs[0, col]
        panel(ax, "AB"[col], title)
        members = sorted(
            {r["subject"] for r in points if r["cohort"] == cohort},
            key=lambda s: int(s.rsplit("-", 1)[-1]),
        )
        if len(members) != (12 if col == 0 else 9):
            raise ValueError("Incomplete matched-control plotting cohort")
        values = np.array(
            [
                [
                    num(
                        one(points, dataset=dataset, cohort=cohort, subject=p, method=m),
                        "balanced_accuracy",
                    )
                    * 100
                    for m in arm_names
                ]
                for p in members
            ]
        )
        offset = np.linspace(-0.12, 0.12, len(members))
        for i, p in enumerate(members):
            ax.plot(
                np.arange(4) + offset[i], values[i], color="#bbbbbb", lw=0.45, alpha=0.55, zorder=1
            )
        for k, method in enumerate(arm_names):
            ax.scatter(
                k + offset,
                values[:, k],
                s=17,
                marker=markers[method],
                color=colors[method],
                alpha=0.7,
                zorder=2,
            )
            mean = float(values[:, k].mean())
            ax.plot([k - 0.19, k + 0.19], [mean, mean], color="black", lw=1.7, zorder=5)
            for i, p in enumerate(members):
                record(
                    rows,
                    panel="AB"[col],
                    dataset=dataset,
                    cohort=cohort,
                    participant=p,
                    budget="full",
                    method=method,
                    statistic="balanced_accuracy",
                    value=values[i, k],
                    unit="percent",
                )
            record(
                rows,
                panel="AB"[col],
                dataset=dataset,
                cohort=cohort,
                participant="mean",
                budget="full",
                method=method,
                statistic="balanced_accuracy",
                value=mean,
                unit="percent",
            )
        ax.set(
            xticks=range(4),
            xticklabels=arm_labels,
            xlim=(-0.45, 3.45),
            ylim=(35, 100),
            ylabel="Balanced accuracy (%)",
        )
        ax.axhline(50, color="#999999", lw=0.7, ls=":")
        ax.yaxis.set_major_locator(plt.MultipleLocator(20))
    ax = axs[1, 0]
    panel(ax, "C", "EA increment over matched controls")
    groups = [
        ("kumar", "kumar_primary12", "Kumar (n=12)"),
        ("kumar", "kumar_development6", "Kumar dev (n=6)"),
        ("bnci", "bnci9", "BNCI (n=9)"),
    ]
    contrasts = ("ea_minus_full", "ea_minus_rms_full", "ea_minus_diagonal_ea")
    symbols = ("o", "s", "D")
    for i, (dataset, cohort, _) in enumerate(groups):
        for j, contrast in enumerate(contrasts):
            r = one(
                effects,
                dataset=dataset,
                cohort=cohort,
                contrast=contrast,
                metric="balanced_accuracy",
            )
            y = i + (j - 1) * 0.21
            point_interval(
                ax,
                num(r, "mean_difference_pp"),
                y,
                num(r, "ci_low_pp"),
                num(r, "ci_high_pp"),
                color=COLORS["ea_csp"],
                marker=symbols[j],
                horizontal=True,
            )
            record(
                rows,
                panel="C",
                dataset=dataset,
                cohort=cohort,
                participant="mean",
                budget="full",
                contrast=contrast,
                statistic="delta_ba",
                value=num(r, "mean_difference_pp"),
                lower=num(r, "ci_low_pp"),
                upper=num(r, "ci_high_pp"),
                unit="percentage_points",
                interval_identity=NEW_CI,
            )
    ax.axvline(0, color="#888888", lw=0.7, ls=":")
    ax.set(
        yticks=range(3),
        yticklabels=[x[2] for x in groups],
        ylim=(2.5, -0.5),
        xlabel="Paired difference (pp)",
        xlim=(-4.5, 12),
    )
    ax = axs[1, 1]
    panel(ax, "D", "Common-trial EA − Full sensitivity")
    windows = ("cue5s", "task2s", "task2s_minus_cue5s")
    for i, scope in enumerate(("conditional", "metadata_complete")):
        for y, window in enumerate(windows):
            r = one(
                phases,
                dataset="kumar",
                cohort="kumar_primary12",
                scope=scope,
                window=window,
                contrast="ea_minus_full",
            )
            value, lo, hi = (num(r, k) for k in ("mean_difference_pp", "ci_low_pp", "ci_high_pp"))
            position = y + (i - 0.5) * 0.22
            point_interval(
                ax,
                value,
                position,
                lo,
                hi,
                color=COLORS["ea_csp"] if i == 0 else "#444444",
                marker="o" if i == 0 else "^",
                horizontal=True,
            )
            record(
                rows,
                panel="D",
                dataset="kumar",
                cohort="kumar_primary12_" + scope,
                participant="mean",
                budget=window,
                contrast="ea_minus_full",
                statistic="window_delta_ba" if y == 2 else "delta_ba",
                value=value,
                lower=lo,
                upper=hi,
                unit="percentage_points",
                interval_identity=NEW_CI,
            )
    ax.axvline(0, color="#888888", lw=0.7, ls=":")
    ax.set(
        yticks=range(3),
        yticklabels=["Cue 5 s", "Task 2 s", "Task 2 s − Cue 5 s"],
        ylim=(2.6, -0.85),
        xlabel="Paired difference (pp)",
        xlim=(-15.5, 15.5),
    )
    ax.legend(
        [
            Line2D([], [], marker="o", color=COLORS["ea_csp"], linestyle="none", ms=4),
            Line2D([], [], marker="^", color="#444444", linestyle="none", ms=4),
        ],
        ["Conditional, n=9", "Metadata-complete, n=8"],
        loc="upper left",
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(-0.01, 1.01),
        handletextpad=0.4,
        borderaxespad=0,
    )
    fig.legend(
        [Line2D([], [], marker=m, color=COLORS["ea_csp"], ms=4) for m in symbols],
        ["EA − Full", "EA − RMS+Full", "EA − diagonal+Full"],
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(0.5, 0.005),
        columnspacing=1,
    )
    return export(fig, "Fig5_mechanisms", rows, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, default=ANALYSIS)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "manuscript/bmt_alignment_integrated_20261104/figures"
    )
    parser.add_argument(
        "--mechanisms",
        type=Path,
        default=ROOT / "research_logs/paper2_alignment_integrated_20261104/mechanisms",
    )
    parser.add_argument(
        "--figures", nargs="+", type=int, choices=range(1, 6), default=[1, 2, 3, 4, 5]
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 8.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )
    source_paths = [
        args.analysis / (name + ".csv")
        for name in [
            "participant_metrics",
            "cohort_method_metrics",
            "participant_contrasts",
            "cohort_contrasts",
        ]
    ]
    tables = {p.stem: read_csv(p) for p in source_paths}
    extra = [
        ROOT / "research_logs/paper2_alignment_integrated_20261104/input_audit/INPUT_MANIFEST.json",
        ROOT / "manuscript/bmt_component_revision_20261029/figures/Fig1_components.csv",
        ROOT / "research_logs/paper2_external_validation_20261027/aggregate.json",
        ROOT
        / "research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z/participant_bootstrap_summary.json",
    ]
    functions = {
        1: lambda: workflow(args.output),
        2: lambda: performance(tables, args.output),
        3: lambda: error_coverage(tables, args.output),
        4: lambda: budgets(tables, args.output),
        5: lambda: mechanisms(tables, args.output, args.mechanisms),
    }
    manifests = [functions[n]() for n in args.figures]
    source_paths += extra
    if 5 in args.figures:
        source_paths += [
            args.mechanisms / name
            for name in (
                "participant_metrics.csv",
                "cohort_comparisons.csv",
                "phase_cohort_comparisons.csv",
            )
        ]
    try:
        git_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
        )
    except FileNotFoundError:
        git_head = None
    git_available = git_head is not None and git_head.returncode == 0
    manifest = {
        "rendered_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": git_head.stdout.strip() if git_available else None,
        "git_metadata_available": git_available,
        "renderer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": digest(__file__)},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "actual_new_fit_or_forward": False,
        "EEG_or_weights_loaded": False,
        "bootstrap_run_by_renderer": False,
        "statistical_unit": "participant; Kumar five target sessions first averaged within participant",
        "intervals": {
            "new_descriptive": "10000 resamples, seed20261104, numeric participant order, linear percentiles",
            "historical_Fig2_contrasts": "original stored contrasts and original bootstrap identities retained",
        },
        "source_files": [
            {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": digest(p)}
            for p in source_paths
        ],
        "figures": manifests,
    }
    (args.output / "FIGURE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "figures": [x["stem"] for x in manifests],
                "output": str(args.output),
                "all_format_checks_passed": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
