"""Plot saved NETBCI results without EEG downloads, fitting, or causal inference."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "research_logs/netbci_behavior_sessions_20261010/run03_verified"
DEFAULT_CONFIG = ROOT / "configs/netbci_behavior_sessions.json"
SESSIONS = ("01", "02", "03", "04")
COLORS = {"pilot": "#087f8c", "cohort": "#2459a6", "CSP": "#d66a26", "EEGNet": "#7251a1"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_inputs(results: Path = DEFAULT_RESULTS, config: Path = DEFAULT_CONFIG) -> dict:
    """Validate figure grain and load only existing small scientific summaries."""
    files = {
        "summary": results / "analysis_summary.json",
        "behavior": results / "behavior_sessions.tsv",
        "cohort": results / "cohort_session_summary.tsv",
        "linked": results / "linked_EEG_behavior_sessions.tsv",
        "contrasts": results / "task_bandpower_contrasts.tsv",
        "power": results / "bandpower_session_summaries.tsv",
        "matched_contrasts": results / "matched_task_bandpower_contrasts.tsv",
        "config": config,
    }
    data = {
        name: json.loads(path.read_text()) if path.suffix == ".json" else read_tsv(path)
        for name, path in files.items()
    }
    behavior = data["behavior"]
    subjects = sorted({row["original_subject"] for row in behavior})
    if len(subjects) != 19 or len(behavior) != 76:
        raise ValueError("Expected the existing 19-person behavior-only table, not a new EEG cohort")
    keys = {(row["original_subject"], row["session"]) for row in behavior}
    if len(keys) != len(behavior) or keys != {(s, t) for s in subjects for t in SESSIONS}:
        raise ValueError("Behavior must contain one unique row per verified participant/session")
    for row in behavior:
        if row["n_reported_run_scores"] != "6":
            raise ValueError("Session means must summarize six reported run percentages")
        values = np.asarray(ast.literal_eval(row["source_literal"]), dtype=float)
        if values.shape != (6,) or not np.isfinite(values).all() or np.any((values < 0) | (values > 100)):
            raise ValueError("Invalid reported score vector")
        if not np.isclose(float(row["mean_run_hit_percent"]), values.mean()):
            raise ValueError("Saved session mean disagrees with the retained source literal")
    linked = sorted(data["linked"], key=lambda row: row["session"])
    if len(linked) != 4 or tuple(row["session"] for row in linked) != SESSIONS:
        raise ValueError("Exactly four linked EEG sessions are required")
    if any(row["original_subject"] != "sub-01" or row["subject"] != "sub-1" for row in linked):
        raise ValueError("Figures may link only the already verified single EEG participant")
    if any(row["join_grain"] != "verified_participant_session_only" for row in linked):
        raise ValueError("Behavior must not be broadcast to EEG run or trial outcomes")
    if sum(int(row["n_EEG_trials"]) for row in linked) != 717:
        raise ValueError("Existing EEG sample count changed")
    matched = data["matched_contrasts"]
    if len(matched) != 160 or any(row["n_rest"] != "48" or row["n_MI"] != "48" for row in matched):
        raise ValueError("Count sensitivity must preserve 20 repetitions of 96 balanced windows per session")
    matched_keys = {(row["repetition"], row["session"], row["band"]) for row in matched}
    expected = {(str(rep), session, band) for rep in range(20) for session in SESSIONS for band in ("mu", "beta")}
    if matched_keys != expected or len(matched_keys) != len(matched):
        raise ValueError("Matched contrasts require unique repetition/session/band identities")
    data["linked"] = linked
    data["subjects"] = subjects
    data["files"] = files
    return data


def configure_style() -> None:
    plt.rcParams.update({
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })


def session_axis(ax: plt.Axes) -> None:
    ax.set_xticks(range(1, 5), ["01", "02", "03", "04"])
    ax.set_xlim(0.65, 4.35)
    ax.set_xlabel("Protocol session (calendar gaps unresolved)")
    ax.grid(axis="y", alpha=0.18)


def vector(rows: list[dict], key: str) -> np.ndarray:
    return np.array([float(row[key]) for row in rows])


def make_behavior_cohort_figure(data: dict) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 7.8), gridspec_kw={"width_ratios": [1.15, 1]})
    fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.24, wspace=0.27)
    fig.suptitle("NETBCI: published behavioral performance trajectories", y=0.97, fontsize=18)
    fig.text(0.5, 0.91, "19 participants with behavioral scores; EEG analyzed for sub-01 only", ha="center", fontsize=13)
    behavior = data["behavior"]
    trajectories = {
        subject: [next(float(r["mean_run_hit_percent"]) for r in behavior
                       if r["original_subject"] == subject and r["session"] == session)
                  for session in SESSIONS]
        for subject in data["subjects"]
    }
    ax = axes[0]
    x = np.arange(1, 5)
    for subject, values in trajectories.items():
        if subject != "sub-01":
            ax.plot(x, values, color="0.65", alpha=0.5, linewidth=1)
    cohort = sorted(data["cohort"], key=lambda row: row["session"])
    ax.fill_between(x, vector(cohort, "subject_bootstrap_CI95_low"),
                    vector(cohort, "subject_bootstrap_CI95_high"),
                    color=COLORS["cohort"], alpha=0.15, label="Mean 95% participant-bootstrap CI")
    ax.plot(x, vector(cohort, "mean_subject_session_hit_percent"), "o-", color=COLORS["cohort"],
            linewidth=2.5, label="Cohort mean (n = 19)")
    ax.plot(x, trajectories["sub-01"], "o-", color=COLORS["pilot"], linewidth=2.8,
            label="sub-01 (only EEG participant)")
    ax.set_title("A   Session trajectories", loc="left")
    ax.set_ylabel("Mean of 6 reported run hit percentages (%)")
    ax.set_ylim(25, 101)
    session_axis(ax)
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    for xi, value in zip(x, vector(cohort, "mean_subject_session_hit_percent"), strict=True):
        ax.annotate(f"{value:.1f}", (xi, value), xytext=(0, -18), textcoords="offset points",
                    ha="center", color=COLORS["cohort"])
    changes = sorted(((subject, values[-1] - values[0]) for subject, values in trajectories.items()),
                     key=lambda item: item[1])
    ax = axes[1]
    y = np.arange(len(changes))
    ax.barh(y, [change for _, change in changes], color=[
        COLORS["pilot"] if subject == "sub-01" else "#b85b39" if change < 0 else "#829db7"
        for subject, change in changes], height=0.7)
    ax.set_yticks(y, [subject for subject, _ in changes])
    for label, (subject, _) in zip(ax.get_yticklabels(), changes, strict=True):
        if subject == "sub-01":
            label.set_color(COLORS["pilot"])
            label.set_fontweight("bold")
    ax.axvline(0, color="0.25", linewidth=0.8)
    ax.set_xlim(-10, 32)
    ax.set_title("B   Each participant: session 04 minus 01", loc="left")
    ax.set_xlabel("Change in reported session mean (percentage points)")
    ax.grid(axis="x", alpha=0.15)
    summary = data["summary"]["cohort_behavior_change"]
    low, high = summary["subject_bootstrap_CI95_pp"]
    fig.text(0.07, 0.15, f"Mean change: +{summary['mean_change_pp']:.2f} pp "
             f"(participant-bootstrap 95% CI {low:.2f} to {high:.2f}); "
             f"{summary['n_increased']}/19 increased, "
             f"{summary['n_strictly_increasing_all_sessions']}/19 strictly increased at every session.", fontsize=11)
    fig.text(0.07, 0.105, "Points summarize six published run percentages with equal weight; "
             "they are not pooled trial-level hit rates. Run IDs and scoring denominators remain unresolved.", fontsize=10)
    fig.text(0.07, 0.065, "Observational trajectories under session-wise decoder recalibration. "
             "They do not isolate human learning, retention, or an algorithm's causal effect. "
             "Online chance level is unresolved.", fontsize=10)
    return fig


def make_pilot_session_figure(data: dict) -> plt.Figure:
    fig, axes = plt.subplots(3, 2, figsize=(15.5, 15.8))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.16, hspace=0.62, wspace=0.26)
    fig.suptitle("sub-01: distinct behavioral, decoding, and EEG endpoints", y=0.97, fontsize=18)
    fig.text(0.5, 0.935, "One EEG participant, 4 sessions, 717 stored task windows; "
             "descriptive comparisons only", ha="center", fontsize=12)
    linked = data["linked"]
    x = np.arange(1, 5)
    ax = axes[0, 0]
    for xi, row in zip(x, linked, strict=True):
        scores = np.asarray(ast.literal_eval(row["source_literal"]), dtype=float)
        ax.scatter(xi + np.linspace(-0.1, 0.1, 6), scores, color=COLORS["pilot"], alpha=0.35, s=23)
    means = vector(linked, "mean_run_hit_percent")
    ax.plot(x, means, "o-", color=COLORS["pilot"], linewidth=2)
    for xi, value in zip(x, means, strict=True):
        ax.annotate(f"{value:.1f}", (xi, value), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.set_title("A   Reported online target-hit performance", loc="left")
    ax.set_ylabel("Mean of 6 reported run percentages (%)")
    ax.set_ylim(55, 107)
    ax.text(0.03, 0.06, "Faint points: six scores, run IDs unmapped\nNo assumed online chance threshold",
            transform=ax.transAxes, fontsize=10)
    session_axis(ax)

    ax = axes[0, 1]
    families = (("CSP_LDA", "CSP + LDA", COLORS["CSP"], -0.04),
                ("EEGNet_CPU_3epochs", "EEGNet: CPU, 3 epochs", COLORS["EEGNet"], 0.04))
    for key, label, color, offset in families:
        values = vector(linked, f"{key}_BA_percent")
        ci = np.array([ast.literal_eval(row[f"{key}_BA_conditional_run_CI95_percent"]) for row in linked])
        ax.errorbar(x + offset, values, yerr=[values - ci[:, 0], ci[:, 1] - values],
                    fmt="o-", linewidth=1.8, capsize=4, color=color, label=label)
    ax.axhline(50, color="0.45", linewidth=1, linestyle=":", label="BA constant-class reference")
    ax.set_ylim(25, 77)
    ax.set_title("B   Frozen reference decoder: offline query", loc="left")
    ax.set_ylabel("Balanced accuracy (%)")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.text(0.03, 0.05, "Query n = 60 / 149 / 150 / 148; run CI is conditional\n"
            "CSP predicts rest for every later query; EEGNet is a workflow pilot", transform=ax.transAxes, fontsize=9.5)
    session_axis(ax)

    ax = axes[1, 0]
    airm = vector(linked, "AIRM_matched144_mean")
    ax.fill_between(x, vector(linked, "AIRM_matched144_resampling_min"),
                    vector(linked, "AIRM_matched144_resampling_max"), color="#4c78a8", alpha=0.2)
    ax.plot(x, airm, "o-", color="#4c78a8", linewidth=2)
    ax.set_title("C   Covariance distance: all 6 runs", loc="left")
    ax.set_ylabel("AIRM distance to session 01 (dimensionless)")
    ax.set_ylim(-0.35, 9.8)
    ax.text(0.03, 0.07, "144 matched trials/session (12/class/run)\n"
            "Shading: min-max over 20 seeded resamplings, not a population CI",
            transform=ax.transAxes, fontsize=9.5)
    session_axis(ax)

    ax = axes[1, 1]
    qc_airm = vector(linked, "AIRM_qc_common_runs_matched96_mean")
    ax.plot(x, qc_airm, "s-", color="#a16a38", linewidth=2)
    ax.set_title("D   Covariance sensitivity: common runs + QC", loc="left")
    ax.set_ylabel("AIRM distance to its session 01 (dimensionless)")
    ax.set_ylim(-0.35, 9.8)
    ax.text(0.03, 0.07, "Runs 03-06; unflagged; 96 matched trials/session\n"
            "Different selection and reference; not an AIRM confidence interval",
            transform=ax.transAxes, fontsize=9.5)
    session_axis(ax)

    styles = (
        ("all_six_runs_all_trials", "All 6 runs, all trials", "#2459a6", "o", "-"),
        ("common_four_runs_all_trials", "Runs 03-06, all trials", "#bf7c2c", "s", "--"),
        ("common_four_runs_qc_unflagged", "Runs 03-06, QC unflagged", "#087f8c", "^", ":"),
    )
    for ax, band, panel in ((axes[2, 0], "mu", "E"), (axes[2, 1], "beta", "F")):
        for variant, label, color, marker, linestyle in styles:
            rows = sorted((row for row in data["contrasts"] if row["band"] == band and row["variant"] == variant),
                          key=lambda row: row["session"])
            if tuple(row["session"] for row in rows) != SESSIONS:
                raise ValueError("Task contrasts require four unique sessions per variant")
            ax.plot(x, vector(rows, "MI_minus_rest_log_power_dB"), color=color, marker=marker,
                    linestyle=linestyle, linewidth=1.8, label=label)
        repeated_values = np.array([
            [float(row["MI_minus_rest_log_power_dB"]) for row in data["matched_contrasts"]
             if row["session"] == session and row["band"] == band]
            for session in SESSIONS
        ])
        ax.fill_between(x, repeated_values.min(axis=1), repeated_values.max(axis=1),
                        color="#7251a1", alpha=0.12)
        ax.plot(x, repeated_values.mean(axis=1), color="#7251a1", marker="D", linewidth=1.7,
                label="Matched 96 unflagged; mean + resampling range")
        ax.axhline(0, color="0.4", linewidth=0.8)
        title = "Mu (8-13 Hz)" if band == "mu" else "Beta (13-30 Hz)"
        ax.set_title(f"{panel}   {title}: MI versus rest task windows", loc="left")
        ax.set_ylabel("Mean-log-power difference: MI - rest (dB)")
        ax.set_ylim(-2.65, 0.7)
        ax.legend(loc="upper right", frameon=False, fontsize=8.7)
        session_axis(ax)
    fig.text(0.08, 0.098, "Spectra: C3/Cz/C4, CAR across 74 channels, 0.5-4.5 s after the stored task marker, "
             "equal run weights; task windows may include feedback. Negative values mean lower MI power.", fontsize=10)
    fig.text(0.08, 0.068, "Task-window contrasts are not baseline-normalized ERD. QC flags are a coarse "
             "sensitivity screen. Geometry/spectral resampling ranges are not population confidence intervals.", fontsize=10)
    fig.text(0.08, 0.038, "Online target-hit %, offline BA, and geometry measure different quantities; "
             "their separation does not estimate a human learning gain or a causal decoder effect.", fontsize=10)
    return fig


def make_diagnostic_figure(data: dict) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 10.7))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.87, bottom=0.18, hspace=0.5, wspace=0.26)
    fig.suptitle("sub-01: representation and measurement sensitivity diagnostics", y=0.97, fontsize=17)
    fig.text(0.5, 0.92, "Additional single-participant descriptors; no biological replication claim", ha="center", fontsize=12)
    linked = data["linked"]
    x = np.arange(1, 5)
    ax = axes[0, 0]
    ax.plot(x, vector(linked, "PCA_subspace_distance_matched144_mean"), "o-", color="#7251a1", linewidth=2)
    ax.set_title("A   PCA subspace distance to session 01", loc="left")
    ax.set_ylabel("Projector distance (dimensionless)")
    ax.set_ylim(-0.03, 0.8)
    session_axis(ax)
    ax.text(0.04, 0.08, "148 log-bandpower features; rank 10\n"
            "Mean of 20 matched resamplings; descriptive target subspaces", transform=ax.transAxes, fontsize=9.5)

    ax = axes[0, 1]
    ax.plot(x, vector(linked, "within_session_run_AIRM_matched144_mean"), "o-", color="#4c78a8", linewidth=2)
    ax.set_title("B   Within-session covariance variation", loc="left")
    ax.set_ylabel("Mean between-run AIRM (dimensionless)")
    ax.set_ylim(0, 6.5)
    session_axis(ax)
    ax.text(0.04, 0.08, "All 6 runs; matched class/trial counts\n"
            "Lower variation does not establish neural skill stability", transform=ax.transAxes, fontsize=9.5)

    ax = axes[1, 0]
    for label, label_text, color in (("rest", "Rest", "#68778c"),
                                     ("right_hand", "Right-hand MI", COLORS["pilot"])):
        rows = sorted((row for row in data["power"] if row["band"] == "mu"
                       and row["variant"] == "all_six_runs_all_trials" and row["label"] == label),
                      key=lambda row: row["session"])
        ax.plot(x, vector(rows, "equal_run_geometric_mean_power_uV2"), "o-", color=color, label=label_text)
    ax.set_title("C   Absolute mu power: both tasks change", loc="left")
    ax.set_ylabel("Geometric mean ROI bandpower (µV²)")
    ax.legend(frameon=False, loc="upper left")
    session_axis(ax)
    ax.text(0.04, 0.08, "All 6 runs, all trials; equal run weights\n"
            "Amplitude shifts can influence geometry and task contrasts", transform=ax.transAxes, fontsize=9.5)

    ax = axes[1, 1]
    counts = vector(linked, "n_qc_flagged").astype(int)
    total = vector(linked, "n_EEG_trials").astype(int)
    ax.bar(x, counts, color="#be7952", width=0.55)
    for xi, n, denominator in zip(x, counts, total, strict=True):
        ax.annotate(f"{n}/{denominator}\n({100*n/denominator:.1f}%)", (xi, n),
                    textcoords="offset points", xytext=(0, 7), ha="center", fontsize=10)
    ax.set_title("D   Coarse artifact-screen burden", loc="left")
    ax.set_ylabel("Number of flagged stored task windows")
    ax.set_ylim(0, 67)
    session_axis(ax)
    ax.text(0.04, 0.67, "Source-fitted peak-amplitude/flat-channel screen\n"
            "Main analysis retains flagged windows; QC is a sensitivity test", transform=ax.transAxes, fontsize=9.5)
    fig.text(0.08, 0.09, "PCA and covariance use fixed conventions recorded in the stage-1 analysis. "
             "The single participant was the highest reported performer in all four sessions.", fontsize=10)
    fig.text(0.08, 0.05, "Measurement, reference, artifact, fatigue, and decoder recalibration effects "
             "remain possible. These plots cannot isolate biological learning or learning preservation.", fontsize=10)
    return fig


def make_figures(data: dict) -> dict[str, plt.Figure]:
    configure_style()
    return {
        "behavior_cohort": make_behavior_cohort_figure(data),
        "pilot_behavior_EEG_endpoints": make_pilot_session_figure(data),
        "pilot_representation_diagnostics": make_diagnostic_figure(data),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.results = args.results.resolve()
    args.config = args.config.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    if any(path.is_file() for path in args.output.iterdir()):
        raise FileExistsError("Preserve existing figure artifacts: choose a new output directory")
    data = load_inputs(args.results, args.config)
    outputs = {}
    for name, figure in make_figures(data).items():
        for extension in ("png", "svg", "pdf"):
            path = args.output / f"{name}.{extension}"
            figure.savefig(path, dpi=250, metadata={"Creator": "NETBCI saved-result visualization"}
                           if extension != "png" else None)
            outputs[str(path.relative_to(ROOT))] = sha256(path)
        plt.close(figure)
    receipt = {
        "status": "saved_real_data_result_figures_no_training_or_download",
        "created_UTC": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256(Path(__file__)),
        "input_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in data["files"].values()},
        "output_sha256": outputs,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "matplotlib": matplotlib.__version__},
        "behavior_independent_unit": "participant; n=19 behavior-only trajectories",
        "EEG_scope": "sub-01 only, 4 sessions, 717 stored windows",
        "neural_behavior_join": "participant/session only, no inferred run or trial outcomes",
        "inference": "descriptive, noncausal; no neural-behavior correlation test",
        "online_chance": "unresolved; not plotted",
        "geometry_shading": "seeded computational resampling min/max; not a population CI",
        "task_contrasts": "MI minus rest task-window mean log power; not baseline ERD",
    }
    (args.output / "plot_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"figures": len(outputs), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
