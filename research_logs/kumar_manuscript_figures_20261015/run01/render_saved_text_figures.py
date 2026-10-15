#!/usr/bin/env python3
"""Render frozen manuscript figures from saved CSV/JSON text, without inference."""

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
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent
OUT = ROOT / "manuscript/figures/kumar2024_20261015"
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
    "Source-only\nCSP/LDA",
    "Frozen CSP +\nLDA recalibration",
    "CSP/LDA\nrefit",
    "Always-frozen\nEEGNet",
)
COLORS = ("#0072B2", "#E69F00", "#009E73", "#CC79A7")
DEV = (1, 4, 7, 10, 13, 16)
REMAINING = (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18)
STEMS = (
    "figure1_target_query_participants",
    "figure2_cpu_primary_paired_changes",
    "figure3_csp_signed_support_halves",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_record(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def publish(path, text):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def clean_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3, color="#666666")
    ax.grid(axis="y", linewidth=0.5, color="#E4E4E4", zorder=0)
    ax.set_axisbelow(True)


def save_figure(fig, stem):
    for extension in ("png", "svg", "pdf"):
        target = OUT / f"{stem}.{extension}"
        metadata = {
            "Title": stem,
            "Creator": "Frozen saved-text manuscript figure renderer",
        }
        if extension == "pdf":
            metadata.update(CreationDate=None, ModDate=None)
        elif extension == "svg":
            metadata["Date"] = None
        with target.open("xb") as handle:
            fig.savefig(handle, format=extension, dpi=300, metadata=metadata)
    plt.close(fig)


def target_figure(participants, summaries):
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.6), sharey=True)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.23, wspace=0.13)
    cohorts = (
        ("development", "development6", DEV, "A   Development participants (n = 6)"),
        ("final_test", "remaining12", REMAINING, "B   Remaining participants (n = 12)"),
    )
    plotted = []
    for ax, (cohort, summary_cohort, subjects, title) in zip(axes, cohorts, strict=True):
        clean_axes(ax)
        ax.axhline(50, color="#888888", linewidth=1, linestyle="--", zorder=1)
        offsets = np.linspace(-0.18, 0.05, len(subjects))
        for subject, offset in zip(subjects, offsets, strict=True):
            subject_rows = [participants[(f"sub-{subject}", method)] for method in METHODS]
            require(all(row["cohort"] == cohort for row in subject_rows), "cohort mismatch")
            values = [100 * float(row["target_five_session_mean_BA"]) for row in subject_rows]
            xs = np.arange(4) + offset
            ax.plot(xs, values, color="#B0B0B0", alpha=0.32, linewidth=0.65, zorder=2)
            for x, value, color, row in zip(xs, values, COLORS, subject_rows, strict=True):
                ax.scatter(x, value, s=30, c=color, edgecolors="white", linewidths=0.5, zorder=3)
                plotted.append(
                    {"subject": row["subject"], "method": row["method"], "BA": value / 100}
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
                markersize=5,
                linewidth=1.5,
                capsize=3,
                zorder=4,
            )
            ax.text(
                index, 94, f"{mean:.1f}%", ha="center", va="center", fontsize=10, fontweight="bold"
            )
        ax.set_title(title, loc="left", fontsize=11, pad=12)
        ax.set_xticks(range(4), LABELS, fontsize=9)
        ax.set_xlim(-0.45, 3.5)
        ax.set_ylim(0, 100)
        ax.set_yticks(range(0, 101, 20))
    axes[0].set_ylabel("Target-query balanced accuracy (%)")
    fig.suptitle("Target-query decoding by participant", y=0.98, fontsize=16, fontweight="bold")
    fig.text(
        0.5,
        0.91,
        "Same query trials; different selection and support-label budgets",
        ha="center",
        fontsize=11,
    )
    handles = [
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            color="#777777",
            label="Participant: mean of five target sessions",
        ),
        Line2D(
            [],
            [],
            linestyle="none",
            marker="D",
            color="#222222",
            label="Mean and saved 95% descriptive CI",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.075),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    fig.text(
        0.5,
        0.035,
        "EEGNet: all three seeds averaged. All participants retained. Follow-up comparison is exploratory.",
        ha="center",
        fontsize=9,
        color="#444444",
    )
    save_figure(fig, STEMS[0])
    return {
        "participant_method_points": len(plotted),
        "development_participants": 6,
        "remaining_participants": 12,
        "all_EEGNet_seeds_per_participant": 3,
        "target_sessions_per_participant": 5,
        "cohort_mean_CI_markers": 8,
        "values": plotted,
    }


def primary_figure(receipt, participants):
    rows = [
        item
        for item in receipt["preserved_original_CPU_primary_contrast"]
        if item["original_primary_cohort"]
    ]
    require(len(rows) == 1 and rows[0]["cohort"] == "remaining12", "primary contrast identity")
    primary = rows[0]
    require(primary["matches_saved_frozen_CPU_summary"] is True, "original summary not verified")
    mapping = dict(zip(primary["subjects"], primary["participant_differences"], strict=True))
    require(set(mapping) == {f"sub-{n}" for n in REMAINING}, "primary subject set")
    differences = [100 * mapping[f"sub-{n}"] for n in REMAINING]
    for subject, difference in zip(REMAINING, differences, strict=True):
        actual = float(
            participants[(f"sub-{subject}", "refit_csp_lda")]["target_five_session_mean_BA"]
        ) - float(participants[(f"sub-{subject}", "source_only")]["target_five_session_mean_BA"])
        require(
            math.isclose(actual * 100, difference, rel_tol=0, abs_tol=1e-12),
            "saved paired change mismatch",
        )
    require(sum(value < 0 for value in differences) == 3, "negative participant count")
    fig, ax = plt.subplots(figsize=(8.4, 6.8))
    fig.subplots_adjust(left=0.19, right=0.96, top=0.83, bottom=0.16)
    clean_axes(ax)
    ax.grid(False)
    ax.grid(axis="x", linewidth=0.5, color="#E4E4E4")
    ax.axvline(0, color="#777777", linewidth=1.1)
    for y, value in enumerate(differences):
        color = "#0072B2" if value >= 0 else "#D55E00"
        marker = "o" if value >= 0 else "v"
        ax.plot([0, value], [y, y], color=color, alpha=0.45, linewidth=1.5, zorder=2)
        ax.scatter(value, y, color=color, marker=marker, s=48, zorder=3)
        ax.annotate(
            f"{value:+.2f}",
            (value, y),
            xytext=(8 if value >= 0 else -8, 0),
            textcoords="offset points",
            ha="left" if value >= 0 else "right",
            va="center",
            fontsize=9,
        )
    summary_y = len(differences) + 0.8
    mean = primary["mean_difference"] * 100
    low, high = [value * 100 for value in primary["ci95"]]
    ax.errorbar(
        mean,
        summary_y,
        xerr=[[mean - low], [high - mean]],
        fmt="D",
        color="#222222",
        markersize=6,
        linewidth=2,
        capsize=4,
        zorder=4,
    )
    ax.text(
        23.5,
        summary_y,
        f"{mean:+.2f}\n[{low:+.2f}, {high:+.2f}]",
        ha="right",
        va="center",
        fontsize=9,
        fontweight="bold",
    )
    ax.axhline(len(differences) - 0.25, color="#DDDDDD", linewidth=0.8)
    ax.set_yticks(
        list(range(len(differences))) + [summary_y],
        [f"sub-{n}" for n in REMAINING] + ["Mean [95% CI]"],
    )
    ax.set_ylim(summary_y + 0.8, -0.7)
    ax.set_xlim(-10, 25)
    ax.set_xticks(range(-10, 26, 5))
    ax.set_xlabel("Refit − source-only balanced accuracy (percentage points)", labelpad=10)
    fig.suptitle("Original CPU primary contrast", y=0.98, fontsize=16, fontweight="bold")
    fig.text(
        0.5,
        0.925,
        "Remaining 12 participants · 9 positive and 3 negative changes",
        ha="center",
        fontsize=11,
    )
    fig.text(
        0.5,
        0.885,
        "Refit uses current-session labeled support; source-only does not",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    fig.text(
        0.5,
        0.055,
        "Five target sessions averaged per participant; original participant-bootstrap interval retained.",
        ha="center",
        fontsize=9,
        color="#444444",
    )
    save_figure(fig, STEMS[1])
    return {
        "participants": 12,
        "positive_changes": 9,
        "negative_changes": 3,
        "zero_changes": 0,
        "subject_order": [f"sub-{n}" for n in REMAINING],
        "saved_differences_percentage_points": differences,
        "saved_mean_percentage_points": mean,
        "saved_ci95_percentage_points": [low, high],
        "new_bootstrap_or_significance_tests": 0,
    }


def csp_figure(csp):
    subjects = sorted(csp["subjects"], key=lambda item: item["subject"])
    require(tuple(item["subject"] for item in subjects) == DEV, "CSP development subject set")
    fig, axes = plt.subplots(2, 3, figsize=(11, 7), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.08, right=0.985, top=0.81, bottom=0.18, hspace=0.35, wspace=0.20)
    counts = {"both_positive": 0, "both_negative": 0, "opposite_signs": 0}
    plotted = []
    for ax, subject in zip(axes.flat, subjects, strict=True):
        clean_axes(ax)
        require(
            [s["session"] for s in subject["support_sessions"]]
            == [f"ses-{n}" for n in range(1, 6)],
            "CSP five support session identities",
        )
        ax.axhline(0, color="#777777", linewidth=1, linestyle="--")
        for number, session in enumerate(subject["support_sessions"], 1):
            first, second = session["half_LDA_signed_contrasts_source_sd"]
            require(
                math.isfinite(first) and math.isfinite(second) and first != 0 and second != 0,
                "nonfinite/zero signed margins",
            )
            key = (
                "both_positive"
                if first > 0 and second > 0
                else "both_negative"
                if first < 0 and second < 0
                else "opposite_signs"
            )
            counts[key] += 1
            ax.plot(
                [number - 0.09, number + 0.09],
                [first, second],
                color="#999999",
                linewidth=1,
                zorder=2,
            )
            ax.scatter(
                number - 0.09,
                first,
                color="#0072B2",
                marker="o",
                s=34,
                edgecolors="white",
                linewidths=0.5,
                zorder=3,
            )
            ax.scatter(
                number + 0.09,
                second,
                color="#D55E00",
                marker="s",
                s=34,
                edgecolors="white",
                linewidths=0.5,
                zorder=3,
            )
            plotted.append(
                {
                    "subject": subject["subject"],
                    "session": session["session"],
                    "half_1": first,
                    "half_2": second,
                }
            )
        ax.set_title(f"sub-{subject['subject']}", loc="left", fontsize=11)
        ax.set_xticks(range(1, 6))
        ax.set_xlim(0.5, 5.5)
        ax.set_ylim(-4, 3)
        ax.set_yticks(range(-4, 4))
    require(
        counts == {"both_positive": 19, "both_negative": 2, "opposite_signs": 9},
        "signed-margin count mismatch",
    )
    saved_counts = csp["counts"]
    require(
        saved_counts["support_sessions_both_LDA_contrasts_positive"] == counts["both_positive"]
        and saved_counts["support_sessions_both_LDA_contrasts_negative"] == counts["both_negative"]
        and saved_counts["support_sessions_opposite_LDA_contrast_signs"]
        == counts["opposite_signs"],
        "independent audit count mismatch",
    )
    fig.suptitle(
        "Signed-score consistency across support halves", y=0.98, fontsize=16, fontweight="bold"
    )
    fig.text(
        0.5,
        0.925,
        "30 support sessions: 19 both positive · 2 both negative · 9 opposite signs",
        ha="center",
        fontsize=11,
    )
    fig.text(
        0.5,
        0.88,
        "Frozen source CSP/LDA diagnostic; no gate selected or evaluated",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    fig.supylabel("Class-balanced signed margin / source-score SD", x=0.015, fontsize=11)
    fig.supxlabel("Target support session", y=0.115, fontsize=11)
    handles = [
        Line2D([], [], linestyle="none", marker=marker, color=color, label=label)
        for marker, color, label in (
            ("o", "#0072B2", "First chronological half within class"),
            ("s", "#D55E00", "Second chronological half within class"),
        )
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.045),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    fig.text(
        0.5,
        0.02,
        "Shared scales; zero is the natural score sign reference, not a learned decision threshold.",
        ha="center",
        fontsize=9,
        color="#444444",
    )
    save_figure(fig, STEMS[2])
    return {
        "development_participants": 6,
        "support_sessions": 30,
        "half_measurements": 60,
        **counts,
        "values": plotted,
        "new_thresholds_or_rules": 0,
    }


CAPTIONS = """# Manuscript figure captions

## Figure 1 — Target-query decoding by participant

All 18 participants are retained, separated into the six development and 12 remaining participants. Each colored point is one participant's balanced accuracy (BA), with equal weight for the five target sessions. Always-frozen EEGNet uses the mean of all three fixed seeds within each session before averaging sessions; CPU methods each use their single frozen execution. Faint lines connect the same participant across methods. Black diamonds and bars reproduce the saved cohort means and 95% descriptive participant-bootstrap intervals (10,000 replicates, seed 42); intervals were not recomputed for this figure. Labels above each method show the saved mean. The 50% reference is descriptive and is not a new significance test. All methods use identical target-query trial identities, but their information and computation budgets differ: all fit on 40 source TRAIN trials, EEGNet selects an epoch using 20 additional source validation labels and receives no target support, whereas the adaptive CPU methods additionally fit with 19 or 20 labels from the current target support session. Thus these are descriptive comparisons, not a matched-budget ranking of model architectures. Previously exposed cohorts make the follow-up comparison exploratory; class-collapsed predictions remain included.

## Figure 2 — Original CPU primary paired contrast

Participant-wise differences in five-target-session mean BA for CSP/LDA refitting minus source-only CSP/LDA, retaining the original primary cohort of 12 remaining participants. Participants are displayed by numeric identity, not ordered by effect size. Nine differences are positive and three are negative (sub-6, sub-14 and sub-15); none is removed. The black diamond and bar reproduce the original mean difference of +7.42 percentage points and 95% participant-bootstrap interval [+2.49, +12.48] (10,000 replicates, seed 42). This frozen primary contrast intentionally compares different target-label access: both methods begin with 40 source TRAIN trials, while refitting additionally uses the current session's 19 or 20 labeled support trials. The figure adds no hypothesis test and does not reinterpret this support-access contrast as a same-budget architecture comparison. These offline decoding changes do not establish human learning, skill preservation or clinical efficacy.

## Figure 3 — Signed-score consistency across target support halves

The six development participants each contribute five target support sessions. Blue circles and vermilion squares show the first and second chronological halves within each class, connected only within the same session. Values are the saved class-balanced signed margin, (mean right-class source-LDA score − mean left-class score) / (2 × source-score standard deviation), with the source model and score normalization fixed. Shared axes retain all 60 half measurements, including negative margins; the natural zero line is a sign reference and is not a selected gate threshold. Of the 30 sessions, 19 have two positive margins, two have two negative margins and nine have opposite signs. In particular, a positive product of two half margins can also represent two negative orientations. These already audited support-only diagnostics do not establish a reliable adaptive gate; no query results, new threshold, refit or strategy search are used by this plotting task.

## Saved-text sources

- Figure 1: `research_logs/kumar_frozen_query_comparison_20261015/run01/per_participant_endpoints.csv` and `cohort_method_endpoint_summary.csv`.
- Figure 2: the preserved original primary contrast in `research_logs/kumar_frozen_query_comparison_20261015/run01/comparison_receipt.json`, checked against the participant endpoint CSV.
- Figure 3: `research_logs/kumar_csp_signed_score_execution_20261015/run02/independent_numerical_audit_run01.json`.

All exported PNG, SVG and PDF files are bound by byte size and SHA256 in the figure-generation receipt. The renderer reads saved CSV/JSON only; it does not read raw EEG, query trials, model weights or tensors, execute a producer, fit a model, perform a forward pass, or select seeds. No saved scientific producer or result is modified.
"""


def main():
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()
    require(OUT.is_dir(), "figure output directory must already exist")
    targets = [OUT / f"{stem}.{extension}" for stem in STEMS for extension in ("png", "svg", "pdf")]
    targets += [OUT / "CAPTIONS.md", LOG / "figure_generation_receipt.json"]
    require(
        not any(path.exists() for path in targets),
        "preserve existing outputs; renderer is exclusive",
    )
    source_paths = [
        COMPARISON / "per_participant_endpoints.csv",
        COMPARISON / "cohort_method_endpoint_summary.csv",
        COMPARISON / "comparison_receipt.json",
        CSP,
    ]
    source_bytes = {path: path.read_bytes() for path in source_paths}
    source_records = [file_record(path) for path in source_paths]
    participant_rows = list(
        csv.DictReader(io.StringIO(source_bytes[source_paths[0]].decode("utf-8")))
    )
    summary_rows = list(csv.DictReader(io.StringIO(source_bytes[source_paths[1]].decode("utf-8"))))
    participants = {(row["subject"], row["method"]): row for row in participant_rows}
    summaries = {(row["cohort"], row["method"], row["endpoint"]): row for row in summary_rows}
    require(
        len(participant_rows) == len(participants) == 72,
        "72 unique participant-method endpoints required",
    )
    require(len(summary_rows) == len(summaries) == 24, "24 unique cohort-method endpoints required")
    require(
        set(participants) == {(f"sub-{n}", method) for n in range(1, 19) for method in METHODS},
        "complete participant-method identities",
    )
    for row in participant_rows:
        require(
            int(row["seeds_included"]) == (3 if row["method"] == "always_frozen_eegnet" else 1),
            "all fixed EEGNet seeds required",
        )
        require(0 <= float(row["target_five_session_mean_BA"]) <= 1, "invalid participant BA")
    for row in summary_rows:
        require(
            int(row["bootstrap_replicates"]) == 10000 and int(row["bootstrap_seed"]) == 42,
            "saved CI identity",
        )
        require(
            0
            <= float(row["descriptive_ci95_low"])
            <= float(row["mean_BA"])
            <= float(row["descriptive_ci95_high"])
            <= 1,
            "invalid saved interval",
        )
    comparison = json.loads(source_bytes[source_paths[2]])
    csp = json.loads(source_bytes[source_paths[3]])
    matplotlib.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "svg.hashsalt": "kumar2024-frozen-saved-text-20261015",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    evidence = {
        STEMS[0]: target_figure(participants, summaries),
        STEMS[1]: primary_figure(comparison, participants),
        STEMS[2]: csp_figure(csp),
    }
    publish(OUT / "CAPTIONS.md", CAPTIONS)
    require(
        all(path.read_bytes() == content for path, content in source_bytes.items()),
        "saved source changed while plotting",
    )
    receipt = {
        "schema_version": 1,
        "status": "completed_saved_text_only",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - t0,
        "script": file_record(Path(__file__).resolve()),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "backend": matplotlib.get_backend(),
        },
        "sources": source_records,
        "sources_byte_unchanged_after_render": True,
        "outputs": [
            file_record(path) for path in targets if path != LOG / "figure_generation_receipt.json"
        ],
        "figures": evidence,
        "scientific_computation": {
            "new_model_fits": 0,
            "new_model_forward_passes": 0,
            "raw_EEG_or_query_trials_read": 0,
            "model_weights_or_tensors_read": 0,
            "producer_executions": 0,
            "new_bootstraps_or_hypothesis_tests": 0,
            "seed_selection": False,
            "new_gates_or_thresholds": 0,
        },
        "scope": "Visualization of saved text only; existing saved uncertainty and original primary contrast preserved; no new scientific analysis.",
    }
    publish(
        LOG / "figure_generation_receipt.json",
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "outputs": len(receipt["outputs"]),
                "receipt": file_record(LOG / "figure_generation_receipt.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
