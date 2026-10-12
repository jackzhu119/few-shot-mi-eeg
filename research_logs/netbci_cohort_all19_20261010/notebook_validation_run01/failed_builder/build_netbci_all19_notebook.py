"""Build the all-19-ID companion from hash-verified saved results, without EEG fits.

Native Matplotlib cells remain editable. Duplicate exclusion is read from the
completed raw audit and never selected by result direction. Old notebooks and
results are never overwritten. Publication wording separates IDs from biological
participants and labels post-observation analyses as exploratory.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from textwrap import dedent

import nbformat

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = "research_logs/netbci_cohort_all19_20261010/summary_run01"
DEFAULT_NOTEBOOK = "notebooks/netbci2026_all19_20261011.ipynb"


def build_notebook(summary_relative: str):
    cells = []

    def markdown(source):
        cells.append(nbformat.v4.new_markdown_cell(dedent(source).strip()))

    def code(source):
        cells.append(nbformat.v4.new_code_cell(dedent(source).strip()))

    markdown("""
        # NETBCI 全部发布身份：纵向结果、数值副本与来源敏感性

        可重运行、原生可编辑 Matplotlib 图。仅读取保存结果及 SHA-256 收据；
        不加载 EEG 张量、不拟合模型、不改变参数。发布编号不等于已证实独立的生物学参与者。
        全编号的 EEG bootstrap 是算术记录；来源敏感性依据全部连续信号或任务窗口跨编号副本，
        同时排除每组所有编号，不按结果筛选。此扩展发生于已见十编号结果之后，属于探索性分析。
    """)
    code("""
        from pathlib import Path
        import hashlib
        import importlib.metadata
        import io
        import json
        import platform
        import sys

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        from IPython.display import Markdown, display

        ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents]
                     if (p / "configs/netbci_cohort_all19_20261010.json").is_file()), None)
        assert ROOT is not None, "Run from this repository."
        def sha256(path):
            with Path(path).open("rb") as stream:
                return hashlib.file_digest(stream, "sha256").hexdigest()
        def read_json(path):
            return json.loads(Path(path).read_text())
        def table(path):
            return pd.read_csv(path, sep="\\t", dtype={"subject": str, "session": str},
                               keep_default_na=True)
    """)
    code(f"""
        RESULTS = ROOT / {summary_relative!r}
        AUDIT = RESULTS.parent
        CONFIG = ROOT / "configs/netbci_cohort_all19_20261010.json"
        COMPACT = AUDIT / "numeric_signal_identity_summary_v2.json"
        SENSITIVITY = AUDIT / "independence_sensitivity_run01"
        receipt = read_json(RESULTS / "summary_receipt.json")
        summary = read_json(RESULTS / "cohort_summary.json")
        config = read_json(CONFIG)
        compact = read_json(COMPACT)
        sensitive_receipt = read_json(SENSITIVITY / "sensitivity_receipt.json")
        sensitivity = read_json(SENSITIVITY / "sensitivity_summary.json")
        LEDGER = Path(compact["full_ledger_file"])
        if not LEDGER.is_file():
            LEDGER = AUDIT / LEDGER.name
        assert receipt["status"] == "actual_data_summary_completed" and receipt["synthetic"] is False
        assert summary["status"] == "actual_audited_published_ID_cohort_exploratory"
        assert summary["synthetic"] is False and compact["synthetic"] is False
        assert compact["status"] == "compact_verified_pre_model_numeric_identity_summary"
        assert sha256(CONFIG) == receipt["config_sha256"] == compact["configuration_sha256"]
        assert sha256(LEDGER) == compact["full_ledger_sha256"]
        assert sha256(LEDGER) == sensitive_receipt["input_sha256"]["identity_audit"]["sha256"]
        assert sha256(RESULTS / "summary_receipt.json") == sensitive_receipt["input_sha256"]["summary_receipt"]["sha256"]
        assert sensitive_receipt["status"] == "completed_real_data_sensitivity"
        assert sensitive_receipt["synthetic"] is False
        assert sensitive_receipt["original_primary_outputs_modified"] is False
        assert sensitivity["no_model_refitting"] and sensitivity["not_independent_confirmation"]
        assert receipt["bootstrap_unit"] == "whole published identity trajectory"
        source_rows = []
        for directory, record in [(RESULTS, receipt), (SENSITIVITY, sensitive_receipt)]:
            for name, checksum in record["output_sha256"].items():
                assert sha256(directory / name) == checksum, name
                source_rows.append({{"artifact": str((directory / name).relative_to(ROOT)), "SHA256": checksum}})
        for name, item in receipt["input_sha256"].items():
            path = Path(item["path"])
            if not path.exists() and "/few-shot-mi-eeg/" in item["path"]:
                path = ROOT / item["path"].split("/few-shot-mi-eeg/", 1)[1]
            assert sha256(path) == item["sha256"], name
        for path in [CONFIG, COMPACT, LEDGER, RESULTS / "summary_receipt.json",
                     SENSITIVITY / "sensitivity_receipt.json"]:
            source_rows.append({{"artifact": str(path.relative_to(ROOT)), "SHA256": sha256(path)}})
        OFFICIAL_MANIFEST = Path(compact["official_manifest_file"])
        assert sha256(OFFICIAL_MANIFEST) == compact["official_manifest_sha256"]
        source_rows.append({{"artifact": str(OFFICIAL_MANIFEST.relative_to(ROOT)),
                            "SHA256": sha256(OFFICIAL_MANIFEST)}})
        SUBJECTS, SESSIONS = config["subjects"], config["session_order"]
        assert SUBJECTS == [f"sub-{{i}}" for i in range(1, 20)]
        RETAINED, EXCLUDED = sensitivity["retained_identities"], sensitivity["excluded_identities"]
        assert EXCLUDED == compact["cross_subject_affected_identities"]
        assert RETAINED == compact["identities_without_detected_cross_subject_exact_signal_copies"]
        assert not set(RETAINED) & set(EXCLUDED) and set(RETAINED + EXCLUDED) == set(SUBJECTS)
        assert summary["published_identities"] == len(SUBJECTS)
        assert compact["summary"]["continuous_runs"] == len(SUBJECTS) * len(SESSIONS) * 6
        assert compact["summary"]["official_manifest_matches"] == compact["summary"]["continuous_runs"]
        old_config = read_json(ROOT / "configs/netbci_cohort_full_windows_20261010.json")
        SCIENCE_KEYS = ["seed", "threads", "session_order", "expected_runs", "source_train_runs",
            "source_query_runs", "later_query_runs", "expected_sfreq_hz", "reference", "roi_channels",
            "decoder_band_hz", "filter", "edge_crop_seconds", "welch_segment_samples", "welch_overlap_samples",
            "mu_hz", "beta_hz", "covariance_trace_shrinkage", "pca_components", "csp_components",
            "artifact_log_peak_MAD_multiplier", "matched_trials_per_class_per_run", "matched_repetitions",
            "qc_matched_runs", "bootstrap_run_repetitions", "bootstrap_subject_repetitions",
            "fixed_window_duration_seconds", "mismatch_action"]
        assert all(config[key] == old_config[key] for key in SCIENCE_KEYS)
        joined = table(RESULTS / "participant_session_join.tsv")
        paired = table(RESULTS / "cohort_paired_changes.tsv")
        geometry = table(RESULTS / "participant_matched_geometry.tsv")
        spectral = table(RESULTS / "spectral_reference_QC_sensitivity.tsv")
        sensitive_paired = table(SENSITIVITY / "cohort_paired_changes.tsv")
        estimates = table(SENSITIVITY / "association_estimates.tsv")
        restricted = table(SENSITIVITY / "retained_participant_session_join.tsv")
        assert not joined.duplicated(["subject", "session"]).any()
        assert set(zip(joined.subject, joined.session)) == {{(s, t) for s in SUBJECTS for t in SESSIONS}}
        assert len(joined) == summary["sessions"] == len(SUBJECTS) * len(SESSIONS)
        assert int(joined.n_EEG_source_events.sum()) == summary["source_events"]
        assert int(joined.n_EEG_trials.sum()) == summary["trials"]
        assert int(joined.n_EEG_excluded_events.sum()) == summary["excluded_source_events_n"]
        assert (joined.n_EEG_source_events == joined.n_EEG_trials + joined.n_EEG_excluded_events).all()
        assert (paired.n_requested_subjects == len(SUBJECTS)).all()
        assert (sensitive_paired.n_requested_subjects == len(RETAINED)).all()
        assert set(restricted.subject) == set(RETAINED)
        print("Verified", len(SUBJECTS), "published identities;", len(RETAINED), "retained identities.")
    """)
    code("""
        def contrast_text(frame, metric):
            row = frame.loc[frame.metric == metric].iloc[0]
            if pd.isna(row.mean_change):
                return "unavailable"
            return (f"{row.mean_change:+.3f} [{row.subject_bootstrap_CI95_low:.3f}, "
                    f"{row.subject_bootstrap_CI95_high:.3f}], paired n={int(row.n_paired_subjects)}")
        counts = compact["summary"]
        text = [f"**Scope: {len(SUBJECTS)} published identities, {summary['sessions']} sessions, "
                f"{summary['runs']} runs; {summary['source_events']:,} original events, "
                f"{summary['trials']:,} eligible exact-5-second events and "
                f"{summary['excluded_source_events_n']} retained exclusion records.**",
                f"Raw numeric audit: {counts['continuous_duplicate_groups']} continuous duplicate groups; "
                f"{counts['task_window_duplicate_groups']} task-window duplicate groups. "
                f"Affected cross-ID union: {', '.join(EXCLUDED)}. "
                "Official byte checks establish deposit fidelity, not biological independence.",
                f"**Source-driven post-observation restriction: n={len(RETAINED)} published identities.** "
                "All cross-ID continuous or task-window group members are excluded, without selecting a correct copy. "
                "No refit, tuning or original-result overwrite occurs."]
        for metric, label, unit in [("mean_run_hit_percent", "Published online score", "pp"),
                                   ("CSP_BA_percent", "Frozen CSP+LDA BA", "pp"),
                                   ("mu_MI_minus_rest_dB", "Mu task-window MI−rest", "dB")]:
            text.append(f"- {label}: all-ID arithmetic {contrast_text(paired, metric)} {unit}; "
                        f"source restriction {contrast_text(sensitive_paired, metric)} {unit}.")
        text += [f"QC flags retained: {summary['qc_flags_retained_in_primary']}; "
                 f"constant-prediction identities: {len(summary['constant_prediction_participants'])}. "
                 "Missing fixed matching cells stay unavailable; counts are never reduced to obtain a result.",
                 "**Interpretation:** behavior, frozen-decoder generalization, and EEG representation are separate endpoints. "
                 "No causal human-learning, skill-retention, mapping-preservation or new-algorithm claim follows. "
                 "Session numbers are audited chronology; known exact within-person repeats and query content overlaps "
                 "remain visible below. Absence of exact cross-ID copies does not verify true biological identity."]
        display(Markdown("\\n\\n".join(text)))
    """)
    markdown("""
        ## Methods and source limits

        NEMAR nm000305 v1.0.0 (CC BY 4.0, DOI
        [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0));
        original published Dataverse v2.2 behavior (DOI
        [10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7)). Session score is the
        unweighted mean of six published percentages; denominators, run assignment
        and trial outcomes remain unresolved. No percent-to-trial reconstruction.

        Session01 runs01–04 fit QC/scaler/PCA/CSP+LDA; runs05–06 are ID-disjoint
        query. Session02 describes validation without parameter selection;
        sessions03/04 are exploratory evaluation. Frozen bytes and prediction
        replay are verified per identity. Numeric content audit additionally tests
        exact copies across IDs and planned train/query roles before expanded fits.
        Original BrainVision EEG has not been read to resolve erroneous assignment.

        Signals: 74 ordered common EEG channels, 250 Hz, V; average reference,
        73-dimensional Helmert coordinates, 5% trace shrinkage, PCA10, CSP4.
        Mu 8–13/Beta 13–30 Hz power uses C3/Cz/C4, 0.5–4.5 s task windows,
        Welch 250/125, equal run means of log power. No prestimulus baseline:
        this is a task-window MI−rest contrast, not baseline ERD.
        Fixed matching: 12/class/run; 144/session across six runs and 96/session
        across QC-common runs 03–06; ten within-ID draws are averaged first.
        Complete identity trajectories are resampled 10,000 times, seed42;
        500 within-ID run draws describe conditional decoder variation.
        These repeats do not increase independent n. No p-values or causal tests.
        The 19-ID extension follows observed ten-ID results and duplicate detection.
    """)
    code("""
        from collections import Counter
        from itertools import combinations
        relationships = Counter()
        for group in compact["continuous_duplicate_groups"]:
            for first, second in combinations(group["members"], 2):
                a, b = first["identity"], second["identity"]
                if a.split("/")[0] != b.split("/")[0]:
                    pair = tuple(sorted(["/".join(a.split("/")[:2]), "/".join(b.split("/")[:2])]))
                    relationships[pair] += 1
        display(pd.DataFrame([{ "first_identity_session": a, "second_identity_session": b,
                               "exact_paired_runs": n } for (a, b), n in sorted(relationships.items())]))
        display(pd.DataFrame(summary["excluded_source_events"]))
        display(pd.DataFrame(compact["same_subject_session_task_repeat_flags"]))
        overlap = compact["planned_partition_content_overlap"]
        display(pd.DataFrame(overlap["affected_subject_sessions"]))
        display(pd.DataFrame(summary["matching_availability"]))
        display(pd.DataFrame(summary["unavailable_decoder_sessions"]))
        display(pd.DataFrame(summary["scientific_failures"]))
        retained_overlap = [row for row in overlap["affected_subject_sessions"]
                            if row["subject"] in RETAINED]
        if retained_overlap:
            display(Markdown("**Retained IDs still include flagged train/query content overlap. "
                             "The source restriction alone does not remove this decoder contamination.**"))
    """)
    code("""
        plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
        COLORS = {s: plt.get_cmap("tab20")(i % 20) for i, s in enumerate(SUBJECTS)}
        X = np.arange(len(SESSIONS)) + 1
        METRICS = [("mean_run_hit_percent", "Published online score (%)"),
                   ("CSP_BA_percent", "Frozen CSP+LDA BA (%)"),
                   ("mu_MI_minus_rest_dB", "Mu MI−rest task contrast (dB)"),
                   ("beta_MI_minus_rest_dB", "Beta MI−rest task contrast (dB)")]
        def matrix(frame, field, subjects):
            return frame.pivot(index="subject", columns="session", values=field).reindex(
                index=subjects, columns=SESSIONS).to_numpy(dtype=float)
        def finite_mean(array):
            count = np.isfinite(array).sum(axis=0)
            return np.divide(np.nansum(array, axis=0), count,
                             out=np.full(array.shape[1], np.nan), where=count > 0), count
        def close_figure(fig):
            figure_number = len(figure_exports) + 1
            stem = FIGURE_ROOT / f"native_figure_{figure_number:02d}"
            assert not any(stem.with_suffix(suffix).exists() for suffix in [".png", ".svg", ".pdf"])
            exports = []
            for suffix in [".png", ".svg", ".pdf"]:
                path = stem.with_suffix(suffix)
                fig.savefig(path, dpi=180, bbox_inches="tight")
                exports.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                                "bytes": path.stat().st_size})
            figure_exports.append({"figure_number": figure_number, "artifacts": exports})
            display(fig)
            plt.close(fig)
        FIGURE_ROOT = AUDIT / "notebook_validation_run01" / "exports"
        FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
        figure_exports = []
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
        for ax, (metric, label) in zip(axes.flat, METRICS):
            values = matrix(restricted, metric, RETAINED)
            for subject, series in zip(RETAINED, values):
                ax.plot(X, series, "o-", color=COLORS[subject], alpha=.6,
                        linewidth=1, markersize=3, label=subject)
            mean, count = finite_mean(values)
            ax.plot(X, mean, "D-", color="black", lw=2.5, label="retained-ID mean")
            ax.set(title=label, xticks=X, xticklabels=SESSIONS, xlabel="Protocol session")
            ax.text(.02, .02, "available ID n=" + "/".join(map(str, count)), transform=ax.transAxes, fontsize=8)
        axes[0, 0].legend(ncol=4, fontsize=7)
        axes[0, 1].axhline(50, color="grey", ls="--", lw=1)
        for ax in axes[1]: ax.axhline(0, color="grey", ls="--", lw=1)
        fig.suptitle(f"Source-driven restriction: {len(RETAINED)} retained published identities")
        fig.text(.5, .01, "Observational, post-observation restriction; biological identity and causal human learning remain unverified.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .04, 1, .95]); close_figure(fig)
    """)
    markdown("""
        Individual retained-ID trajectories above preserve heterogeneous outcomes.
        Online behavior is an aggregate published score; BA reads the frozen
        offline model. A decline in BA does not identify loss of human skill.
    """)
    code("""
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
        change_metrics = [("mean_run_hit_percent", "Published online score change (pp)"),
                          ("CSP_BA_percent", "Frozen CSP+LDA BA change (pp)"),
                          ("mu_MI_minus_rest_dB", "Mu task-contrast change (dB)")]
        for ax, (metric, label) in zip(axes, change_metrics):
            for position, (frame, legend, color) in enumerate([
                (paired, f"All {len(SUBJECTS)} IDs (arithmetic)", "#888888"),
                (sensitive_paired, f"Retained {len(RETAINED)} IDs (exploratory)", "#146b8c")]):
                row = frame.loc[frame.metric == metric].iloc[0]
                ax.plot([row.subject_bootstrap_CI95_low, row.subject_bootstrap_CI95_high],
                        [position, position], color=color, lw=3)
                ax.scatter(row.mean_change, position, color=color, s=55, marker="D")
                ax.text(.02, .9 - position*.12, f"{legend}: paired n={int(row.n_paired_subjects)}",
                        transform=ax.transAxes, fontsize=8, color=color)
            ax.axvline(0, color="grey", ls="--", lw=1)
            ax.set(yticks=[0, 1], yticklabels=["All-ID arithmetic", "Source restriction"],
                   ylim=(-.5, 1.8), title=label, xlabel="Session04 − session01")
        fig.suptitle("Paired whole-ID trajectory bootstrap, 10,000 draws, seed 42")
        fig.text(.5, .01, "All-ID EEG intervals do not establish independent replication; source restriction is not independent confirmation.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .06, 1, .92]); close_figure(fig)
    """)
    code("""
        continuous = np.zeros((len(SUBJECTS), len(SESSIONS)))
        task = np.zeros_like(continuous)
        repeat = np.zeros_like(continuous)
        for group in compact["continuous_duplicate_groups"]:
            if group["cross_subject"]:
                for member in group["members"]:
                    subject, session, _ = member["identity"].split("/")
                    continuous[SUBJECTS.index(subject), SESSIONS.index(session.removeprefix("ses-"))] = 1
        for row in compact["cross_subject_task_window_affected_subject_sessions"]:
            task[SUBJECTS.index(row["subject"]), SESSIONS.index(row["session"])] = 1
        for row in compact["same_subject_session_task_repeat_flags"]:
            repeat[SUBJECTS.index(row["subject"]), SESSIONS.index(row["session"])] = 1
        fig, axes = plt.subplots(1, 3, figsize=(11, max(6, len(SUBJECTS)*.29)), sharey=True)
        for ax, data, title in zip(axes, [continuous, task, repeat],
                                  ["Cross-ID continuous copies", "Cross-ID task-window copies", "Within-ID/session task repeats"]):
            ax.imshow(data, aspect="auto", vmin=0, vmax=1, cmap="Blues")
            ax.set(xticks=np.arange(4), xticklabels=SESSIONS, yticks=np.arange(len(SUBJECTS)),
                   yticklabels=SUBJECTS, xlabel="Protocol session", title=title)
            for i, j in zip(*np.where(data)): ax.text(j, i, "flag", ha="center", va="center", color="white", fontsize=7)
        fig.suptitle(f"Full raw audit: {compact['summary']['continuous_runs']} runs; blue cells contain exact numeric repeats")
        fig.text(.5, .01, "Flags use raw numeric identity, never outcome direction. Same-session repeats alone do not imply another participant.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .04, 1, .94]); close_figure(fig)
    """)
    code("""
        selected_geometry = geometry.loc[geometry.subject.isin(RETAINED)]
        fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
        for i, variant in enumerate(["all_six_runs", "qc_common_four_runs"]):
            data = selected_geometry.loc[selected_geometry.variant == variant]
            for ax, field in zip(axes[i], ["AIRM_to_session01", "within_session_run_AIRM_mean", "PCA_subspace_distance"]):
                values = matrix(data, field, RETAINED)
                for subject, series in zip(RETAINED, values):
                    ax.plot(X, series, "o-", color=COLORS[subject], alpha=.5, lw=1, markersize=3)
                mean, count = finite_mean(values)
                ax.plot(X, mean, "D-", color="black", lw=2)
                ax.set(title=field, ylabel=variant, xticks=X, xticklabels=SESSIONS, xlabel="Protocol session")
                ax.text(.02, .02, "available ID n=" + "/".join(map(str, count)), transform=ax.transAxes, fontsize=8)
        fig.suptitle("Retained-ID descriptive geometry; ten matched draws averaged within each identity")
        fig.text(.5, .01, "Run AIRM describes heterogeneity, not measurement reliability; geometry is not human learning or skill retention.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .04, 1, .94]); close_figure(fig)
    """)
    code("""
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), sharey=True)
        for ax, reference in zip(axes, ["CAR", "source_reference"]):
            for variant, style in [("all_six_runs_all_trials", "o-"),
                                   ("common_four_runs_all_trials", "s--"),
                                   ("common_four_runs_qc_unflagged", "^:")]:
                data = spectral.loc[spectral.subject.isin(RETAINED) & (spectral.reference == reference)
                                    & (spectral.variant == variant) & (spectral.band == "mu")]
                values = matrix(data, "MI_minus_rest_log_power_dB", RETAINED)
                mean, count = finite_mean(values)
                ax.plot(X, mean, style, label=variant + " (n=" + "/".join(map(str, count)) + ")")
            ax.axhline(0, color="grey", ls="--", lw=1)
            ax.set(title=reference, xticks=X, xticklabels=SESSIONS, xlabel="Protocol session",
                   ylabel="Mu MI−rest task-window contrast (dB)")
            ax.legend(fontsize=7, loc="best")
        fig.suptitle("Retained-ID reference and coarse source-QC sensitivity; no baseline ERD")
        fig.text(.5, .01, "QC thresholds use source training only. Unflagged windows are not expert-confirmed artifact-free data.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .05, 1, .93]); close_figure(fig)
    """)
    code("""
        sys.path.insert(0, str(ROOT / "scripts"))
        from analyze_netbci_cohort_associations import PAIRS, participant_values
        values = pd.DataFrame(participant_values(restricted.astype(object).where(pd.notna(restricted), None).to_dict("records"),
                              selected_geometry.astype(object).where(pd.notna(selected_geometry), None).to_dict("records"),
                              subjects=RETAINED))
        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        for ax, (pair, xfield, yfield) in zip(axes.flat, PAIRS):
            for row in values.to_dict("records"):
                if pd.notna(row[xfield]) and pd.notna(row[yfield]):
                    ax.scatter(row[xfield], row[yfield], color=COLORS[row["subject"]], s=30)
                    ax.annotate(row["subject"], (row[xfield], row[yfield]), fontsize=7, xytext=(3, 3), textcoords="offset points")
            estimate_rows = estimates.loc[estimates.association == pair]
            labels = []
            for row in estimate_rows.itertuples():
                labels.append(f"{row.estimator}: r={row.estimate:.3f}, n={int(row.n_complete_paired_participants)}")
            ax.set(title="\\n".join(labels), xlabel=xfield, ylabel=yfield)
        axes.flat[-1].axis("off")
        fig.suptitle("Five retained-ID first-to-last change associations: descriptive, post-observation")
        fig.text(.5, .01, "No independent-session correlations, p-values, causal mediation, or human-learning inference. Full CIs and degenerate draws are tabulated below.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .04, 1, .94]); close_figure(fig)
        display(estimates)
    """)
    code("""
        availability = np.array([[int(str(row).lower() == "true") for row in
                                 joined.loc[joined.subject == s].set_index("session").reindex(SESSIONS).CSP_constant_prediction]
                                 for s in SUBJECTS])
        qc = matrix(joined, "n_qc_flagged", SUBJECTS)
        fig, axes = plt.subplots(1, 2, figsize=(10, max(6, len(SUBJECTS)*.29)), sharey=True)
        image = axes[0].imshow(availability, aspect="auto", cmap="Reds", vmin=0, vmax=1)
        axes[0].set_title("Frozen decoder constant prediction")
        image = axes[1].imshow(qc, aspect="auto", cmap="Oranges", vmin=0)
        axes[1].set_title("Coarse source-QC flagged windows")
        fig.colorbar(image, ax=axes[1], shrink=.75, label="Flagged window count")
        for ax in axes:
            ax.set(xticks=np.arange(4), xticklabels=SESSIONS, yticks=np.arange(len(SUBJECTS)),
                   yticklabels=SUBJECTS, xlabel="Protocol session")
        for i, j in zip(*np.where(availability)): axes[0].text(j, i, "flag", color="white", ha="center", va="center", fontsize=7)
        fig.suptitle("Failures and source-QC flags remain in all-ID arithmetic outputs")
        fig.text(.5, .01, "Constant predictions, missing matches and excluded short source events remain inspectable; failure records are not silent exclusions.", ha="center", fontsize=8)
        fig.tight_layout(rect=[0, .04, 1, .94]); close_figure(fig)
    """)
    markdown("""
        ## Reproducibility and remaining evidence gaps

        The tables below record source/output hashes and actual notebook runtime.
        The full raw numeric ledger is preserved locally; R2 synchronization
        and full GET confirmation require separate per-file receipts;
        the compact summary records its SHA-256. A storage ETag or HEAD metadata
        match is not proof of downloaded content identity; R2 receipts distinguish
        full GET checks from metadata checks.

        Exact copy exclusion cannot identify the correctly assigned original EEG,
        remove unknown acquisition confounds, or establish external replication.
        Biological measurement reliability, unassisted same-mapping probes,
        delayed retention, randomized intervention and new algorithms remain pending.
        Public training resources are a separate audit/ingestion scope, never silently
        appended to this longitudinal cohort or online behavior sample size.
    """)
    code("""
        display(pd.DataFrame(source_rows))
        versions = {package: importlib.metadata.version(package) for package in
                    ["numpy", "pandas", "scipy", "matplotlib", "mne", "scikit-learn", "nbformat", "nbclient"]}
        versions["python"] = platform.python_version()
        print(json.dumps(versions, indent=2))
        assert len(figure_exports) == 7
        figure_index = FIGURE_ROOT.parent / "native_figure_export_index.json"
        assert not figure_index.exists(), "Preserve previous figure export index."
        figure_index.write_text(json.dumps(figure_exports, indent=2) + "\\n")
    """)
    for position, cell in enumerate(cells):
        cell.id = f"netbci-all19-cell-{position:02d}"
    notebook = nbformat.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"name": "bci-netbci-local", "display_name": "BCI NETBCI local CPU", "language": "python"},
        "language_info": {"name": "python", "version": "3.11"},
        "analysis_scope": "All-19 published identity arithmetic and dynamic post-observation cross-ID source-copy restriction; no EEG or fitting",
        "summary_directory": summary_relative,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    nbformat.validate(notebook)
    return notebook


def write_reports(summary_relative: str):
    """Render numerical prose only from hash-verified completed saved artifacts."""
    import csv
    import json

    def sha(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    def read(path):
        return json.loads(path.read_text())

    def rows(path):
        with path.open(newline="") as stream:
            return list(csv.DictReader(stream, delimiter="\t"))

    summary_root = ROOT / summary_relative
    audit = summary_root.parent
    sensitive_root = audit / "independence_sensitivity_run01"
    compact_path = audit / "numeric_signal_identity_summary_v2.json"
    config_path = ROOT / "configs/netbci_cohort_all19_20261010.json"
    compact = read(compact_path)
    summary = read(summary_root / "cohort_summary.json")
    receipt = read(summary_root / "summary_receipt.json")
    sensitive = read(sensitive_root / "sensitivity_summary.json")
    sensitive_receipt = read(sensitive_root / "sensitivity_receipt.json")
    ledger = Path(compact["full_ledger_file"])
    assert receipt["synthetic"] is False and sensitive_receipt["synthetic"] is False
    assert sha(config_path) == receipt["config_sha256"] == compact["configuration_sha256"]
    assert sha(ledger) == compact["full_ledger_sha256"] == sensitive_receipt["input_sha256"]["identity_audit"]["sha256"]
    assert sha(Path(compact["official_manifest_file"])) == compact["official_manifest_sha256"]
    assert sha(summary_root / "summary_receipt.json") == sensitive_receipt["input_sha256"]["summary_receipt"]["sha256"]
    for directory, record in [(summary_root, receipt), (sensitive_root, sensitive_receipt)]:
        for name, checksum in record["output_sha256"].items():
            assert sha(directory / name) == checksum, name
    excluded, retained = sensitive["excluded_identities"], sensitive["retained_identities"]
    assert excluded == compact["cross_subject_affected_identities"]
    assert retained == compact["identities_without_detected_cross_subject_exact_signal_copies"]
    n, nr = summary["published_identities"], len(retained)
    from collections import Counter
    from itertools import combinations
    relations = Counter()
    for group in compact["continuous_duplicate_groups"]:
        for first, second in combinations(group["members"], 2):
            a, b = first["identity"], second["identity"]
            if a.split("/")[0] != b.split("/")[0]:
                pair = tuple(sorted(["/".join(a.split("/")[:2]), "/".join(b.split("/")[:2])]))
                relations[pair] += 1
    relation_lines = ["| Identity/session | Exact copied identity/session | Paired runs |",
                      "| --- | --- | --- |"]
    relation_lines.extend(f"| {a} | {b} | {count} |" for (a, b), count in sorted(relations.items()))
    relations_table = "\n".join(relation_lines)
    metrics = [("mean_run_hit_percent", "公开在线成绩 / Published online score", "pp"),
               ("CSP_BA_percent", "冻结 CSP+LDA BA / Frozen CSP+LDA BA", "pp"),
               ("mu_MI_minus_rest_dB", "Mu MI−rest 任务窗 / Mu MI−rest task-window contrast", "dB"),
               ("beta_MI_minus_rest_dB", "Beta MI−rest 任务窗 / Beta MI−rest task-window contrast", "dB")]

    def format_change(record, metric):
        row = next(row for row in record["paired_changes"] if row["metric"] == metric)
        if row["mean_change"] is None:
            return f"unavailable; paired n={row['n_paired_subjects']}"
        return (f"{row['mean_change']:+.3f} [{row['subject_bootstrap_CI95_low']:.3f}, "
                f"{row['subject_bootstrap_CI95_high']:.3f}]; n={row['n_paired_subjects']}")

    table_lines = ["| Metric | All-ID arithmetic change [95% interval] | Source restriction change [95% interval] | Unit |",
                   "| --- | --- | --- | --- |"]
    for metric, label, unit in metrics:
        table_lines.append(f"| {label} | {format_change(summary, metric)} | {format_change(sensitive, metric)} | {unit} |")
    numerical_table = "\n".join(table_lines)
    matching = summary["matching_availability"]
    matching_counts = {variant: sum(row["status"] == "available" and row["subject"] in retained
                                   for row in matching if row["variant"] == variant)
                       for variant in ["all_six_runs", "qc_common_four_runs"]}
    unavailability = [f"{row['subject']}/{row['variant']}: {row['error']}" for row in matching
                      if row["status"] != "available"]
    excluded_source = summary["excluded_source_events"]
    source_exclusion_lines = "\n".join(
        f"- `{row['trial_id']}`: duration={row['duration_s']} s; {row.get('exclusion_reason', 'recorded in source exclusion table')}."
        for row in excluded_source) or "- None."
    overlap = compact["planned_partition_content_overlap"]
    retained_overlap = [row for row in overlap["affected_subject_sessions"] if row["subject"] in retained]
    overlap_notice = ("保留编号仍有来源→query 数值内容重合，来源排除不能单独消除此解码污染。"
                      if retained_overlap else
                      "本次 planned-partition 数值审计未在保留编号发现来源→后续 query exact 内容重合；这不排除非 exact 泄漏或未知来源错误。")
    repeat_flags = compact["same_subject_session_task_repeat_flags"]
    retained_repeats = [row for row in repeat_flags if row["subject"] in retained]
    source_hashes = [
        ("all19 config", config_path, sha(config_path)),
        ("official pinned manifest", Path(compact["official_manifest_file"]), compact["official_manifest_sha256"]),
        ("compact numeric audit", compact_path, sha(compact_path)),
        ("full numeric audit (local; R2 receipt separate)", ledger, compact["full_ledger_sha256"]),
        ("all-ID summary receipt", summary_root / "summary_receipt.json", sha(summary_root / "summary_receipt.json")),
        ("restricted summary receipt", sensitive_root / "sensitivity_receipt.json", sha(sensitive_root / "sensitivity_receipt.json")),
    ]
    hashes = "\n".join(f"| {label} | `{path.relative_to(ROOT)}` | `{checksum}` |"
                       for label, path, checksum in source_hashes)
    association_table = ["| Association | Estimator | Estimate | 95% interval | Complete paired IDs | Degenerate draws |",
                         "| --- | --- | --- | --- | --- | --- |"]
    for row in rows(sensitive_root / "association_estimates.tsv"):
        number = lambda key: f"{float(row[key]):.3f}" if row[key] else "unavailable"  # noqa: E731
        association_table.append(f"| {row['association']} | {row['estimator']} | {number('estimate')} | "
            f"[{number('participant_bootstrap_CI95_low')}, {number('participant_bootstrap_CI95_high')}] | "
            f"{row['n_complete_paired_participants']} | {row['bootstrap_degenerate_draws']} |")
    stats = compact["summary"]
    report = f"""# NETBCI 全 19 个发布身份扩展（2026-10-11）

已完成真实源审计、拟合和汇总范围：{n} 个**发布身份**、{summary['sessions']} 个会话、
{summary['runs']} 个 EDF runs，来源 {summary['source_events']:,} 个事件，其中
{summary['trials']:,} 个完整 5 秒事件纳入张量，{summary['excluded_source_events_n']} 个短来源事件保留明确排除。
`participants` 历史字段是发布编号数量，不是已证实独立的生物学参与者数。

来源数值审计在模型拟合前完成：{stats['continuous_runs']} 个 EDF 全信号与全部来源任务窗口检查，
官方实际文件校验全部匹配。发现 {stats['continuous_duplicate_groups']} 个连续信号副本组、
{stats['task_window_duplicate_groups']} 个任务窗口副本组。跨编号 affected union 为 **{', '.join(excluded)}**。
原始 BrainVision EEG 未实读，正确分配与重复原因未知。逐会话 pairwise 内容关系如下，
同一多方副本组可以出现在多行，因此此表不能求和当成独立重复组：

{relations_table}

全 {n} 编号结果保留为算术诊断。另存来源驱动敏感性同时排除每个跨编号连续信号**或任务窗口**
副本组的全部成员，保留 {nr} 个编号：{', '.join(retained)}。没有选择一个“正确”副本，没有依据效果方向筛选，
没有覆盖十编号或全编号输出、重新拟合或改变参数。**未发现 exact 跨编号复制不等于验证生物学独立**。
本扩展已见十编号结果与既有 19 人行为，属于观察后探索分析，不是外部确认。

## 数值结果

下表均为 ses04−ses01；均值的 95% percentile interval 对完整发布身份轨迹重采样
10,000 次，seed42。全编号 EEG 区间不支持独立参与者推断；来源排除区间仍以来源和身份真实性未验证为限制。
在线成绩是六个已发布百分比的等权均值，不是 pooled hit rate。

{numerical_table}

在线成绩、离线固定读取与表征是不同端点。不能把 BA 下降推断为人的技能丢失，不能把
Mu/Beta 任务窗口变化直接推断为经典 baseline ERD、神经学习或保持。

## 模型、窗口、QC 与缺失

每人 ses01/run01–04 唯一拟合粗 QC、scaler、reference PCA 和 CSP+LDA；run05–06 为按 ID
分开的 query。ses02 是不选择参数的 validation 描述，ses03/04 为探索评估；另用数值内容审计
核对 ID 不相交以外的复制。各模型记录训练 trial IDs、状态前后 hash、单次 fit 和 exact 预测重放。
74 个有序公共 EEG 通道、250 Hz、V；全公共通道 CAR，73 维 Helmert 坐标；5% trace shrinkage、
PCA10、CSP4。任务窗裁剪 0.5–4.5 秒、ROI C3/Cz/C4、Mu 8–13/Beta 13–30 Hz、Welch 250/125；
先求每 run 的 trial log-power 均值，再对 run 等权。没有验证事件前基线。

固定匹配每类/run 12 个 trial：六-run144/session、QC 共同 run03–06 为96/session，每人先平均10次抽样。
保留编号的 matching 可用数为六-run {matching_counts['all_six_runs']}/{nr}、QC四-run
{matching_counts['qc_common_four_runs']}/{nr}。不足时保留 unavailable，不降低阈值、不删参与者。
全编号保留粗 QC 标记 {summary['qc_flags_retained_in_primary']} 个；至少一次恒预测的编号
{len(summary['constant_prediction_participants'])}/{n}；科学失败记录 {summary['scientific_failure_records_n']} 条。
500 次每人 run-bootstrap 是条件变异，10 个匹配 seeds 均不增加独立样本量。

Unavailable records: {'; '.join(unavailability) or 'none'}.

实际短事件（不补齐、延长或伪造行为标签）：

{source_exclusion_lines}

来源审计保留的同编号同会话任务窗口重复 flag 共 {len(repeat_flags)} 个会话，其中保留编号
{len(retained_repeats)} 个会话。它们与跨编号复制分开记录。
{overlap_notice}
完整位置和源→query 数量见 compact 的 `same_subject_session_task_repeat_flags` 与
`planned_partition_content_overlap`；不以官方 SHA 匹配代替来源独立。

## 来源限制后的探索关联

先计算每个保留编号 ses04−ses01 变化，只重采样完整变量对；不把 {nr*4} 会话行作为独立 n。
五对指标、Pearson/Spearman、10,000 次/seed42 沿用原估计器；不可用身份和退化重采样均保留。
不报告 p 值或机制、mediation、因果学习结论。

{chr(10).join(association_table)}

## 出处、复核与可重运行成果

固定 derivative DOI [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)，
CC BY4.0；原行为 Dataverse v2.2 [10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7)。
正式扩展时机与固定参数见 [扩展协议](netbci_all19_expansion_protocol_20261010.md)。
全部来源、排除、冻结模型及统计 receipt 可重查；完整数值 ledger 本地单独保留。
R2 实际同步、上传接收和 full GET 验证状态另见逐文件存储收据，HEAD/ETag 不当成内容 hash 证明。

| Source | Path | SHA-256 |
| --- | --- | --- |
{hashes}

可编辑 native figures 位于 `notebooks/netbci2026_all19_20261011.ipynb`，HTML 同名导出。
生产表和生成图在 `{summary_relative}`；来源敏感性在 `{sensitive_root.relative_to(ROOT)}`。
独立方法审计与 bootstrap 重算在该扩展日志目录单独保留；生产报告不代替独立复核。

H1/H2 的当前证据是固定读取、任务窗口和几何的观察性描述；within-session run AIRM 不等于
测量可靠性，跨编号结果不等于生物学重复。H3/H4 的干预归因、人的无辅助同 mapping 保持和
延迟 retention、新算法与外部独立确认均仍未完成。公共训练资源接入单列，不混入本纵向分析人数。
"""
    english_numerical_table = numerical_table
    for _, label, _ in metrics:
        english_numerical_table = english_numerical_table.replace(label, label.split(" / ")[1])
    manuscript = f"""# All-published-identity NETBCI exploratory addendum (11 October 2026)

We extended the saved longitudinal pipeline to all {n} published NETBCI identities, comprising
{summary['sessions']} sessions, {summary['runs']} runs and {summary['source_events']:,} source events.
The exact-5-second input policy retained {summary['trials']:,} events; {summary['excluded_source_events_n']}
short source events remain explicitly documented and were neither padded nor interpreted as behavioral failures.
The extension followed observed ten-identity results and a source-copy discovery; it is exploratory.

Before expanded model fitting, all {stats['continuous_runs']} EDF signals and source task windows were
numerically audited, alongside official file hashes and original-header provenance.
The audit identified {stats['continuous_duplicate_groups']} continuous-signal groups and
{stats['task_window_duplicate_groups']} task-window groups with exact copies. The cross-identity
continuous-or-task-window affected union was {', '.join(excluded)}. Deposit fidelity does not
establish biological independence. Original BrainVision EEG has not been read to determine the correct
assignment or the cause of duplication. The exact pairwise session relationships below can share a
multi-member duplicate group and must not be summed as independent duplicate groups:

{relations_table}

All-identity estimates are retained as arithmetic diagnostics.

A separately preserved, source-driven post-observation sensitivity excludes every identity in any
cross-identity continuous or task-window exact-copy group, retaining {nr} published identities.
Selection does not use effect direction, presume a correct copy, refit models or overwrite earlier outputs.
No detected exact cross-identity copies among retained identities does not verify biological identity,
measurement reliability, unknown provenance errors or external replication. Within-identity repetitions
and planned train/query content overlap remain separately visible in the audit.

## Methods

The source is NEMAR nm000305 v1.0.0 (DOI 10.82901/nemar.nm000305.v1.0.0; CC BY4.0), with
original published behavior from Dataverse v2.2 (DOI 10.57745/RBJRC7). For each identity, session01
runs01–04 alone fit coarse source QC, normalization, reference PCA and CSP+LDA; runs05–06 form
ID-disjoint reference query. Session02 describes validation without model selection; sessions03/04
are exploratory evaluations. Saved model bytes are frozen and predictions replayed exactly. A raw
numerical audit additionally tests content overlap, since different IDs do not establish independent signals.

The unchanged pipeline uses 74 ordered common EEG channels at 250 Hz in V, common-average reference,
73-dimensional Helmert coordinates, 5% trace shrinkage, PCA10 and CSP4. C3/Cz/C4 task-window power
uses a 0.5–4.5-second crop, Welch 250/125, Mu 8–13/Beta 13–30 Hz and equal weighting of run-level mean
log powers. This MI−rest contrast has no validated prestimulus baseline and is not baseline ERD.
Matched sampling fixes 12 trials/class/run: 144/session across six runs and 96/session across common
QC runs 03–06. Ten draws are averaged within identity. Insufficient cells remain unavailable without
reducing the preset. Whole identity trajectories receive 10,000 percentile-bootstrap draws, seed 42;
500 run draws per identity describe conditional decoder variation. Repetitions do not increase independent n.
Published session behavior averages six reported percentages; denominators, run order and trial outcomes
remain unresolved. No trial-level success labels are reconstructed.

## Results

First-to-last mean changes and 95% intervals are:

{english_numerical_table}

All-identity EEG intervals are arithmetic and cannot support independent-participant inference.
The source-restricted analysis remains conditional on unresolved biological identity and provenance.
Within retained identities, fixed six-run matching is available for {matching_counts['all_six_runs']}/{nr}
and common-QC matching for {matching_counts['qc_common_four_runs']}/{nr}. All-ID outputs retain
{summary['qc_flags_retained_in_primary']} source-QC flags and {len(summary['constant_prediction_participants'])}
identities with at least one constant-prediction session. Failures and unavailable metrics remain recorded.
The companion source-restricted associations use five predefined metric pairs with Pearson/Spearman
and paired-variable whole-identity bootstrap, without p-values or causal interpretation; their complete
intervals, available identities and degenerate draws are preserved in the report and tables.

## Interpretation and reproducibility

Online published behavior, offline frozen-decoder generalization and EEG representation are distinct
endpoints. Decoder degradation does not establish human skill loss; geometric or task-window changes
do not establish learning, retention, mapping preservation or a causal mechanism. No new algorithm,
randomized intervention, unassisted same-mapping delayed-retention probe or external confirmation is
claimed. Additional public training deposits are separately audited resources and do not increase this
longitudinal cohort's sample size.

Native editable figures and all source/output SHA-256 checks are in
`notebooks/netbci2026_all19_20261011.ipynb`. Full numeric identity ledger, source data, frozen-model
receipts and storage checks remain separately inspectable. Exact report input hashes:

| Source | Path | SHA-256 |
| --- | --- | --- |
{hashes}
"""
    targets = [ROOT / "docs/netbci_all19_results_20261011.md", ROOT / "manuscript/all19_addendum_20261011.md"]
    assert not any(path.exists() for path in targets), "Preserve existing reports; choose a reviewed revision"
    for path, content in zip(targets, [report, manuscript], strict=True):
        path.write_text(content, encoding="utf-8")
    return targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_NOTEBOOK))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise FileExistsError("Preserve previous notebooks; choose a new output")
    notebook = build_notebook(args.summary)
    if args.execute:
        from nbclient import NotebookClient
        NotebookClient(notebook, timeout=180, kernel_name="bci-netbci-local",
                       resources={"metadata": {"path": str(ROOT)}}, allow_errors=False).execute()
        nbformat.validate(notebook)
        assert all(cell.execution_count is not None for cell in notebook.cells if cell.cell_type == "code")
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output)
    if args.execute:
        from nbconvert import HTMLExporter
        html, _ = HTMLExporter(template_name="lab").from_notebook_node(notebook)
        output.with_suffix(".html").write_text(html, encoding="utf-8")
    if args.write_reports:
        for report_path in write_reports(args.summary):
            print(f"Rendered {report_path}")
    print(f"{'Executed' if args.execute else 'Scaffolded'} {output}")


if __name__ == "__main__":
    main()
