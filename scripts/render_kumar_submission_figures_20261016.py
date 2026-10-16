#!/usr/bin/env python3
"""Export submission figures exclusively from immutable, saved Kumar text tables.

No EEG, checkpoint, model or inference module is imported or read. The only new
calculation is subtraction of saved session balanced accuracies for Figure 4.
"""

import csv
import hashlib
import io
import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/figures/plos_submission_20261016"
LOG = ROOT / "research_logs/kumar_submission_figures_20261016/run01"
COMPARISON = ROOT / "research_logs/kumar_frozen_query_comparison_20261015/run01"
CSP = ROOT / (
    "research_logs/kumar_csp_signed_score_execution_20261015/run02/"
    "independent_numerical_audit_run01.json"
)
METHODS = (
    "source_only",
    "frozen_csp_lda_recalibration",
    "refit_csp_lda",
    "always_frozen_eegnet",
)
LABELS = (
    "Frozen\nCSP/LDA",
    "Frozen CSP +\nLDA update",
    "Full\nCSP/LDA refit",
    "Frozen\nEEGNet",
)
COLORS = ("#0072B2", "#E69F00", "#009E73", "#CC79A7")
DEV = (1, 4, 7, 10, 13, 16)
REMAINING = (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18)
STEMS = (
    "Fig1_target_query_participants",
    "Fig2_cpu_primary_paired_changes",
    "Fig3_csp_signed_support_halves",
    "Fig4_longitudinal_paired_changes",
)
DPI = 600
FILES = []
GEOMETRY = []


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_record(path):
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def publish(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def csv_output(stem, rows):
    target = OUT / f"{stem}_source_data.csv"
    with target.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    FILES.append(target)


def clean_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3, color="#666666")
    ax.grid(axis="y", linewidth=0.5, color="#E4E4E4", zorder=0)
    ax.set_axisbelow(True)


def panel_label(ax, label):
    ax.text(0, 1.025, label, transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom")


def save_figure(fig, stem):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text_records = []
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        size = artist.get_fontsize()
        require(8 <= size <= 12, f"font size outside 8–12 pt: {size}")
        box = artist.get_window_extent(renderer)
        tolerance = 1.0
        require(
            box.x0 >= -tolerance
            and box.y0 >= -tolerance
            and box.x1 <= fig.bbox.width + tolerance
            and box.y1 <= fig.bbox.height + tolerance,
            f"text clipped by physical image boundary: {artist.get_text()!r}",
        )
        text_records.append({"text": artist.get_text(), "font_size_pt": size})
    for extension in ("png", "svg", "pdf"):
        target = OUT / f"{stem}.{extension}"
        metadata = {"Creator": "Kumar saved-text submission figure renderer"}
        if extension == "pdf":
            metadata.update(CreationDate=None, ModDate=None)
        elif extension == "svg":
            metadata["Date"] = None
        with target.open("xb") as handle:
            fig.savefig(handle, format=extension, dpi=DPI, metadata=metadata)
        FILES.append(target)
    tiff = OUT / f"{stem}.tif"
    with Image.open(OUT / f"{stem}.png") as image:
        require(image.size == tuple(round(x * DPI) for x in fig.get_size_inches()), "pixels")
        rgb = image.convert("RGB")
        with tiff.open("xb") as handle:
            rgb.save(handle, format="TIFF", compression="tiff_lzw", dpi=(DPI, DPI))
    FILES.append(tiff)
    with Image.open(tiff) as image:
        width, height = image.size
        dpi = tuple(float(x) for x in image.info["dpi"])
        width_cm, height_cm = width / dpi[0] * 2.54, height / dpi[1] * 2.54
        require(image.mode == "RGB" and len(image.getbands()) == 3, "flattened RGB TIFF")
        require(getattr(image, "n_frames", 1) == 1, "single TIFF image")
        require(image.info.get("compression") == "tiff_lzw", "LZW compression")
        require(all(300 <= value <= 600 for value in dpi), "TIFF dpi")
        require(6.68 <= width_cm <= 19.05001 and height_cm <= 22.23, "physical dimensions")
        require(tiff.stat().st_size < 10_000_000, "TIFF 10 MB limit")
        GEOMETRY.append(
            {
                "figure": stem,
                "pixel_width": width,
                "pixel_height": height,
                "width_cm": width_cm,
                "height_cm": height_cm,
                "dpi": dpi,
                "mode": image.mode,
                "compression": image.info["compression"],
                "single_frame": True,
                "alpha_channel": False,
                "physical_text_boundary_check_passed": True,
                "text_artists": text_records,
            }
        )
    plt.close(fig)


def figure1(participants, summaries):
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 4.5), sharey=True)
    fig.subplots_adjust(left=0.09, right=0.985, top=0.90, bottom=0.25, wspace=0.13)
    plotted = []
    for ax, (cohort, summary_cohort, subjects, label) in zip(
        axes,
        (
            ("development", "development6", DEV, "A"),
            ("final_test", "remaining12", REMAINING, "B"),
        ),
        strict=True,
    ):
        clean_axes(ax)
        panel_label(ax, label)
        ax.axhline(50, color="#888888", linewidth=0.8, linestyle="--", zorder=1)
        for subject, offset in zip(subjects, np.linspace(-0.18, 0.05, len(subjects)), strict=True):
            rows = [participants[(f"sub-{subject}", method)] for method in METHODS]
            require(all(row["cohort"] == cohort for row in rows), "cohort mismatch")
            values = [100 * float(row["target_five_session_mean_BA"]) for row in rows]
            xs = np.arange(4) + offset
            ax.plot(xs, values, color="#999999", alpha=0.32, linewidth=0.6, zorder=2)
            for x, value, color, row in zip(xs, values, COLORS, rows, strict=True):
                ax.scatter(x, value, s=19, c=color, edgecolors="white", linewidths=0.4, zorder=3)
                plotted.append(
                    {
                        "record_type": "participant",
                        "cohort": cohort,
                        "subject": row["subject"],
                        "method": row["method"],
                        "BA": value / 100,
                        "ci95_low": "",
                        "ci95_high": "",
                    }
                )
        for index, method in enumerate(METHODS):
            row = summaries[(summary_cohort, method, "target_five_session_mean_BA")]
            mean, low, high = [
                100 * float(row[key])
                for key in ("mean_BA", "descriptive_ci95_low", "descriptive_ci95_high")
            ]
            ax.errorbar(
                index + 0.22,
                mean,
                yerr=[[mean - low], [high - mean]],
                fmt="D",
                color="#222222",
                markersize=4,
                linewidth=1.1,
                capsize=2,
                zorder=4,
            )
            ax.text(index, 94, f"{mean:.1f}%", ha="center", va="center", fontsize=8.5)
            plotted.append(
                {
                    "record_type": "cohort_summary",
                    "cohort": summary_cohort,
                    "subject": "",
                    "method": method,
                    "BA": mean / 100,
                    "ci95_low": low / 100,
                    "ci95_high": high / 100,
                }
            )
        ax.set_xticks(range(4), LABELS, fontsize=8)
        ax.set_xlim(-0.45, 3.5)
        ax.set_ylim(0, 100)
        ax.set_yticks(range(0, 101, 20))
    axes[0].set_ylabel("Target-query balanced accuracy (%)")
    fig.legend(
        handles=[
            Line2D([], [], linestyle="none", marker="o", color="#777777", label="Participant (method color)"),
            Line2D([], [], linestyle="none", marker="D", color="#222222", label="Mean [95% CI]"),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.025),
        ncol=2,
        frameon=False,
        fontsize=8,
    )
    csv_output(STEMS[0], plotted)
    save_figure(fig, STEMS[0])
    return {"participant_points": 72, "cohort_summary_points": 8, "all_fixed_EEGNet_seeds": 3}


def figure2(comparison, participants):
    original = [
        x
        for x in comparison["preserved_original_CPU_primary_contrast"]
        if x["original_primary_cohort"]
    ]
    require(len(original) == 1 and original[0]["cohort"] == "remaining12", "original primary")
    original = original[0]
    mapping = dict(zip(original["subjects"], original["participant_differences"], strict=True))
    differences = [100 * mapping[f"sub-{n}"] for n in REMAINING]
    rows = []
    fig, ax = plt.subplots(figsize=(7.5, 5.3))
    fig.subplots_adjust(left=0.19, right=0.96, top=0.965, bottom=0.16)
    clean_axes(ax)
    ax.grid(False)
    ax.grid(axis="x", linewidth=0.5, color="#E4E4E4")
    ax.axvline(0, color="#777777", linewidth=0.9)
    for y, (subject, value) in enumerate(zip(REMAINING, differences, strict=True)):
        full = float(
            participants[(f"sub-{subject}", "refit_csp_lda")]["target_five_session_mean_BA"]
        )
        frozen = float(
            participants[(f"sub-{subject}", "source_only")]["target_five_session_mean_BA"]
        )
        require(math.isclose(100 * (full - frozen), value, abs_tol=1e-12), "paired endpoint")
        color = "#0072B2" if value >= 0 else "#D55E00"
        ax.plot([0, value], [y, y], color=color, alpha=0.45, linewidth=1.3)
        ax.scatter(value, y, color=color, marker="o" if value >= 0 else "v", s=31, zorder=3)
        ax.annotate(
            f"{value:+.2f}",
            (value, y),
            xytext=(7 if value >= 0 else -7, 0),
            textcoords="offset points",
            ha="left" if value >= 0 else "right",
            va="center",
            fontsize=8.5,
        )
        rows.append(
            {
                "record_type": "participant",
                "subject": f"sub-{subject}",
                "difference_pp": value,
                "ci95_low_pp": "",
                "ci95_high_pp": "",
            }
        )
    mean = original["mean_difference"] * 100
    low, high = [x * 100 for x in original["ci95"]]
    summary_y = len(differences) + 0.8
    ax.errorbar(
        mean,
        summary_y,
        xerr=[[mean - low], [high - mean]],
        fmt="D",
        color="#222222",
        markersize=5,
        linewidth=1.5,
        capsize=3,
    )
    ax.text(
        23.8,
        summary_y,
        f"{mean:+.2f}\n[{low:+.2f}, {high:+.2f}]",
        ha="right",
        va="center",
        fontsize=8.5,
    )
    ax.axhline(len(differences) - 0.25, color="#DDDDDD", linewidth=0.7)
    ax.set_yticks(
        list(range(len(differences))) + [summary_y],
        [f"sub-{n}" for n in REMAINING] + ["Mean [95% CI]"],
    )
    ax.set_ylim(summary_y + 0.8, -0.7)
    ax.set_xlim(-10, 25)
    ax.set_xticks(range(-10, 26, 5))
    ax.set_xlabel("Full refit − frozen balanced accuracy (percentage points)")
    rows.append(
        {
            "record_type": "original_primary_mean",
            "subject": "remaining12",
            "difference_pp": mean,
            "ci95_low_pp": low,
            "ci95_high_pp": high,
        }
    )
    csv_output(STEMS[1], rows)
    save_figure(fig, STEMS[1])
    return {
        "positive_participants": sum(x > 0 for x in differences),
        "negative_participants": sum(x < 0 for x in differences),
        "original_primary_mean_pp": mean,
        "original_primary_ci95_pp": [low, high],
        "numeric_subject_order": list(REMAINING),
    }


def figure3(csp):
    subjects = sorted(csp["subjects"], key=lambda item: item["subject"])
    require(tuple(x["subject"] for x in subjects) == DEV, "CSP development identities")
    fig, axes = plt.subplots(2, 3, figsize=(7.5, 5.5), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.94, bottom=0.22, hspace=0.40, wspace=0.18)
    rows = []
    counts = {"both_positive": 0, "both_negative": 0, "opposite_signs": 0}
    for ax, subject in zip(axes.flat, subjects, strict=True):
        clean_axes(ax)
        ax.text(
            0, 1.025, f"sub-{subject['subject']}", transform=ax.transAxes, fontsize=10, va="bottom"
        )
        ax.axhline(0, color="#777777", linewidth=0.8, linestyle="--")
        require(
            [s["session"] for s in subject["support_sessions"]]
            == [f"ses-{n}" for n in range(1, 6)],
            "support sessions",
        )
        for number, session in enumerate(subject["support_sessions"], 1):
            first, second = session["half_LDA_signed_contrasts_source_sd"]
            require(
                math.isfinite(first) and math.isfinite(second) and first != 0 and second != 0,
                "margin",
            )
            kind = (
                "both_positive"
                if first > 0 and second > 0
                else "both_negative"
                if first < 0 and second < 0
                else "opposite_signs"
            )
            counts[kind] += 1
            ax.plot([number - 0.09, number + 0.09], [first, second], color="#999999", linewidth=0.8)
            ax.scatter(
                number - 0.09,
                first,
                color="#0072B2",
                marker="o",
                s=24,
                edgecolors="white",
                linewidths=0.4,
                zorder=3,
            )
            ax.scatter(
                number + 0.09,
                second,
                color="#D55E00",
                marker="s",
                s=24,
                edgecolors="white",
                linewidths=0.4,
                zorder=3,
            )
            rows.append(
                {
                    "subject": f"sub-{subject['subject']}",
                    "session": session["session"],
                    "first_half_margin_source_sd": first,
                    "second_half_margin_source_sd": second,
                    "sign_pattern": kind,
                }
            )
        ax.set_xticks(range(1, 6))
        ax.set_xlim(0.5, 5.5)
        ax.set_ylim(-4, 3)
        ax.set_yticks(range(-4, 4))
    require(
        counts == {"both_positive": 19, "both_negative": 2, "opposite_signs": 9},
        "signed margin counts",
    )
    fig.supylabel("Class-balanced signed margin / source-score SD", x=0.02, fontsize=9)
    fig.supxlabel("Target support session", y=0.12, fontsize=9)
    fig.legend(
        handles=[
            Line2D([], [], linestyle="none", marker=marker, color=color, label=label)
            for marker, color, label in (
                ("o", "#0072B2", "First chronological half"),
                ("s", "#D55E00", "Second chronological half"),
            )
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.025),
        ncol=2,
        frameon=False,
        fontsize=8,
    )
    csv_output(STEMS[2], rows)
    save_figure(fig, STEMS[2])
    return {
        "development_participants": 6,
        "support_sessions": 30,
        "half_measurements": 60,
        **counts,
    }


def figure4(session_rows, participants):
    sessions = {(row["subject"], row["method"], row["session"]): row for row in session_rows}
    require(len(sessions) == len(session_rows) == 432, "complete unique 18×4×6 saved BA table")
    order = DEV + REMAINING
    arrays = []
    plotted = []
    for contrast, reference in (
        ("full_refit_minus_frozen", "source_only"),
        ("full_refit_minus_LDA_only", "frozen_csp_lda_recalibration"),
    ):
        values = []
        for subject in order:
            per_subject = []
            for session in range(1, 6):
                full = sessions[(f"sub-{subject}", "refit_csp_lda", f"ses-{session}")]
                comparator = sessions[(f"sub-{subject}", reference, f"ses-{session}")]
                require(
                    full["n_unique_query_trials"] == comparator["n_unique_query_trials"],
                    "matched query trial count",
                )
                full_ba, reference_ba = (
                    float(full["balanced_accuracy"]),
                    float(comparator["balanced_accuracy"]),
                )
                difference = (full_ba - reference_ba) * 100
                per_subject.append(difference)
                plotted.append(
                    {
                        "contrast": contrast,
                        "subject": f"sub-{subject}",
                        "cohort": full["cohort"],
                        "session": f"ses-{session}",
                        "n_unique_query_trials": int(full["n_unique_query_trials"]),
                        "full_refit_BA": full_ba,
                        "comparator_BA": reference_ba,
                        "difference_pp": difference,
                    }
                )
            saved_endpoint_difference = 100 * (
                float(
                    participants[(f"sub-{subject}", "refit_csp_lda")]["target_five_session_mean_BA"]
                )
                - float(participants[(f"sub-{subject}", reference)]["target_five_session_mean_BA"])
            )
            require(
                math.isclose(sum(per_subject) / 5, saved_endpoint_difference, abs_tol=2e-12),
                "heatmap five-session mean matches saved endpoint",
            )
            values.append(per_subject)
        arrays.append(np.asarray(values))
    maximum = max(abs(array).max() for array in arrays)
    limit = math.ceil(maximum / 10) * 10
    require(limit > 0, "heatmap symmetric limit")
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 7.5), sharey=True)
    fig.subplots_adjust(left=0.20, right=0.975, top=0.93, bottom=0.20, wspace=0.16)
    for ax, values, label in zip(axes, arrays, ("A", "B"), strict=True):
        panel_label(ax, label)
        heatmap = ax.imshow(
            values, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto", interpolation="nearest"
        )
        for row in range(18):
            for column in range(5):
                value = values[row, column]
                ax.text(
                    column,
                    row,
                    f"{value:+.1f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if abs(value) > 0.59 * limit else "#111111",
                )
        ax.set_xticks(range(5), [str(x) for x in range(1, 6)])
        ax.set_xlabel("Target session")
        ax.set_yticks(range(18), [f"sub-{x}" for x in order])
        ax.axhline(5.5, color="#111111", linewidth=1.3)
        ax.set_xticks(np.arange(-0.5, 5, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 18, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.35)
        ax.tick_params(which="minor", bottom=False, left=False)
    axes[0].text(
        -0.40,
        2.5,
        "Development (n = 6)",
        transform=axes[0].get_yaxis_transform(),
        rotation=90,
        ha="center",
        va="center",
        fontsize=9,
    )
    axes[0].text(
        -0.40,
        11.5,
        "Remaining (n = 12)",
        transform=axes[0].get_yaxis_transform(),
        rotation=90,
        ha="center",
        va="center",
        fontsize=9,
    )
    colorbar_axes = fig.add_axes([0.32, 0.085, 0.55, 0.023])
    colorbar = fig.colorbar(heatmap, cax=colorbar_axes, orientation="horizontal")
    colorbar.set_label("Balanced accuracy difference (percentage points)", fontsize=9)
    csv_output(STEMS[3], plotted)
    save_figure(fig, STEMS[3])
    return {
        "participants": 18,
        "sessions_per_participant": 5,
        "panels": 2,
        "cells": 180,
        "participant_order_numeric_within_cohort": [f"sub-{x}" for x in order],
        "shared_symmetric_color_limits_pp": [-limit, limit],
        "observed_max_absolute_change_pp": float(maximum),
        "rounding_for_display_decimals": 1,
        "negative_cells": [int((a < 0).sum()) for a in arrays],
        "zero_cells": [int((a == 0).sum()) for a in arrays],
        "positive_cells": [int((a > 0).sum()) for a in arrays],
        "all_individual_session_differences_retained": True,
        "paired_mean_matches_saved_participant_endpoints": True,
        "new_bootstraps_or_tests": 0,
    }


CAPTIONS = """# Figure captions for the PLOS ONE author-review version

## Fig 1. Target-query decoding by participant.

(A) Six development participants. (B) Twelve remaining participants. Each colored
point is one participant's balanced accuracy (BA), with equal weight for five
target sessions. EEGNet averages all three fixed seeds within session before the
session mean; CPU methods use their single frozen execution. Faint lines connect
the same participant across methods. Diamonds and bars reproduce saved means and
95% descriptive participant-bootstrap intervals (10,000 resamples, seed 42), not
new intervals. All methods use the same query trial identities, but information
budgets differ: each learns from 40 source TRAIN labels; EEGNet also uses 20 source
validation labels for epoch selection, while the two updating CPU baselines use
19 or 20 labeled support trials from the current target session. This is not a
matched-budget architecture ranking. The follow-up comparison is exploratory;
all seeds, participants and class-collapsed predictions are retained.

## Fig 2. Original primary CPU contrast by participant.

Full CSP/LDA refitting minus frozen CSP/LDA for the original remaining-12 primary
cohort, after equal averaging of five target sessions. Numeric participant order
is retained. Nine differences are positive and three negative. The negative
changes are sub-6 −5.82, sub-14 −0.67 and sub-15 −0.20 percentage points; these
descriptive decreases differ in magnitude and are not individual significance
claims. The mean and original 95% participant-bootstrap interval are +7.42
[+2.49, +12.48] percentage points. Refit has access to current-session support
labels whereas frozen does not. This figure adds no hypothesis test and does
not establish learning, skill retention or clinical efficacy.

## Fig 3. Signed-score consistency across target support halves.

Each development participant contributes five target support sessions. Circles
and squares show the first and second chronological halves within class. Values
are the saved class-balanced contrast of frozen source-LDA scores divided by
twice their source-score standard deviation. All 60 values use shared axes.
Of 30 sessions, 19 have two positive margins, two have two negative margins and
nine have opposite signs. The zero line indicates score orientation, not a
selected gate. These support-only diagnostics do not validate an update policy.

## Fig 4. Longitudinal paired changes for every participant and target session.

Each cell is a difference in balanced accuracy for identical saved query trials:
(A) full CSP/LDA refit minus frozen CSP/LDA (the original primary contrast);
(B) full refit minus LDA-only recalibration (the secondary same-support-label
contrast). Both panels contain all 18 participants and five target sessions.
Development and remaining cohorts are separated by a horizontal line; participant
identities are numeric within each cohort, without effect-size sorting. The
symmetric color scale is shared, and every signed cell value is displayed in
percentage points to one decimal. Exact values and trial counts are in the
matching source-data CSV. These session values describe heterogeneity; sessions
are not treated as independent participants. The original primary endpoint and
all inferential comparisons remain unchanged. No new model, query inference,
gate, bootstrap or significance test is performed to produce this figure.

## Export and font status

Each figure has PNG/PDF/SVG review exports and a flattened, single-frame RGB TIFF
with LZW compression at 600 dpi; dimensions and complete byte hashes are in the
generation receipt. Captions and figure titles are outside the images. The
existing host does not contain Arial or Times New Roman; all labels actually use
Liberation Sans, a metric-compatible substitute, at 8–12 pt. Thus strict requested
font-family compliance is **not claimed**. No font or environment was installed.
The editable vector files support later conversion if the journal requires an
exact font family. Content, dimensions, resolution and flattened TIFF checks
were performed on the actual exported bytes, not inferred from source settings.
"""


def contact_sheet():
    thumbnails = []
    for stem in STEMS:
        with Image.open(OUT / f"{stem}.png") as image:
            thumbnail = image.convert("RGB")
            thumbnail.thumbnail((1050, 1050))
            thumbnails.append(ImageOps.pad(thumbnail, (1100, 1100), color="white"))
    contact = Image.new("RGB", (2200, 2200), "#EEEEEE")
    for index, thumbnail in enumerate(thumbnails):
        contact.paste(thumbnail, ((index % 2) * 1100, (index // 2) * 1100))
    target = LOG / "visual_contact_sheet.png"
    with target.open("xb") as handle:
        contact.save(handle, format="PNG")
    FILES.append(target)


def main():
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    require(not list(OUT.iterdir()), "preserve prior figure outputs; require empty new directory")
    require(not (LOG / "figure_generation_receipt.json").exists(), "preserve existing receipt")
    paths = [
        COMPARISON / name
        for name in (
            "per_participant_endpoints.csv",
            "cohort_method_endpoint_summary.csv",
            "comparison_receipt.json",
            "per_subject_session.csv",
        )
    ] + [CSP]
    source_bytes = {path: path.read_bytes() for path in paths}
    sources = [file_record(path) for path in paths]
    parsed = [
        list(csv.DictReader(io.StringIO(source_bytes[paths[index]].decode())))
        for index in (0, 1, 3)
    ]
    participants = {(row["subject"], row["method"]): row for row in parsed[0]}
    summaries = {(row["cohort"], row["method"], row["endpoint"]): row for row in parsed[1]}
    require(len(participants) == len(parsed[0]) == 72, "72 unique participant/method rows")
    require(len(summaries) == len(parsed[1]) == 24, "24 unique cohort/method endpoints")
    require(
        set(participants) == {(f"sub-{n}", method) for n in range(1, 19) for method in METHODS},
        "full cohort",
    )
    for row in parsed[0]:
        require(
            int(row["seeds_included"]) == (3 if row["method"] == "always_frozen_eegnet" else 1),
            "all fixed seeds",
        )
        require(0 <= float(row["target_five_session_mean_BA"]) <= 1, "BA range")
    for row in parsed[1]:
        require(
            int(row["bootstrap_replicates"]) == 10000 and int(row["bootstrap_seed"]) == 42,
            "saved bootstrap identity",
        )
    font_path = Path(font_manager.findfont("Liberation Sans", fallback_to_default=False))
    actual_family = font_manager.FontProperties(fname=font_path).get_name()
    require(actual_family == "Liberation Sans", "actual expected installed font")
    matplotlib.rcParams.update(
        {
            "font.family": actual_family,
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8,
            "svg.hashsalt": "kumar-plos-submission-20261015",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    evidence = {
        STEMS[0]: figure1(participants, summaries),
        STEMS[1]: figure2(json.loads(source_bytes[paths[2]]), participants),
        STEMS[2]: figure3(json.loads(source_bytes[CSP])),
        STEMS[3]: figure4(parsed[2], participants),
    }
    publish(OUT / "CAPTIONS.md", CAPTIONS)
    FILES.append(OUT / "CAPTIONS.md")
    contact_sheet()
    require(
        all(path.read_bytes() == value for path, value in source_bytes.items()),
        "saved scientific sources unchanged",
    )
    receipt = {
        "schema_version": 1,
        "status": "completed_saved_text_only_four_figures",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - clock,
        "script": file_record(Path(__file__).resolve()),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "pillow": Image.__version__,
            "backend": matplotlib.get_backend(),
        },
        "source_files": sources,
        "source_bytes_unchanged_after_render": True,
        "actual_font": {
            "family": actual_family,
            "file": str(font_path),
            "sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
            "minimum_pt": 8,
            "maximum_pt": 12,
            "strict_Arial_or_Times_family_compliance_claimed": False,
            "limitation": "Installed metric-compatible Liberation Sans substitute used; exact Arial and Times New Roman unavailable; no installation performed.",
        },
        "outputs": [file_record(path) for path in FILES],
        "figures": evidence,
        "actual_export_checks": GEOMETRY,
        "scope": {
            "EEG_or_model_files_read": 0,
            "new_model_fits": 0,
            "new_forward_passes": 0,
            "new_bootstraps": 0,
            "new_hypothesis_tests": 0,
            "new_gates": 0,
            "query_trial_files_read": 0,
            "saved_trial_identity_changes": 0,
            "new_scientific_calculation": "Fig4 subtracts already-saved matched session BA; endpoint means checked against saved participant table.",
        },
    }
    publish(
        LOG / "figure_generation_receipt.json",
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "output_count": len(FILES),
                "receipt": file_record(LOG / "figure_generation_receipt.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
