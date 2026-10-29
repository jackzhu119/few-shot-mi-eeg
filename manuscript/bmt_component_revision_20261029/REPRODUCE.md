# Reproduce this component revision

No training is needed for this revision. Use the saved prediction tables and an
existing Python environment with NumPy, Pandas/Matplotlib for plotting, and the
established document stack (Pandoc, XeLaTeX, python-docx, PyMuPDF) for exports.

From the repository root, with a fresh output directory:

```bash
python scripts/review_kumar_component_saved_evidence_20261029.py --budget-root research_logs/paper2_structure_revision_20261029/component_replay/input/budget --phase-root research_logs/paper2_structure_revision_20261029/component_replay/input/phase --output /tmp/paper2-component-replay-20261029
```

This reconstructs every original budget/phase endpoint and the existing
confidence intervals. It reads gzip copies of unchanged CSV bytes and the public
trial-role manifest; no EEG, model loading, fit or forward is performed. Budget
participant order is numeric; the phase postprocessor uses lexical order. The
historical original-main intervals are retained separately.

```bash
python scripts/render_component_revision_figures_20261029.py
python scripts/build_bmt_component_revision_20261029.py
```

Figures 1–2 are rendered from saved participant/session results. Figure 3 is the
unchanged external figure with a new article number. Original V3 geometric,
neural and simulation figures are preserved in `supplementary_figures/`.

The data/code ZIP preserves the repository-relative paths needed for numerical
replay; extract it into a clean directory and run its saved-prediction entry.
Document rebuilding additionally needs this revision's manuscript source folder,
provided by the full review package or the repository. Existing source models,
scientific configurations, accepted ledgers and all original archives remain at
their historical paths.
