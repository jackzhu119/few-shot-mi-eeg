# Submission figure exports and exact plotted data

These figures read saved numerical text only. They do not load EEG, checkpoints,
query samples or predictions, and do not fit models or execute an inference pass.
The original three figures retain their saved observations and uncertainty. New
Fig 4 subtracts saved matched-session balanced accuracies, retaining every
participant and target session; its five-session means match the original saved
participant endpoints. The new image does not change any main analysis.

| Figure | Stem | Exact plotted CSV rows | Content |
| --- | --- | ---: | --- |
| 1 | `Fig1_target_query_participants` | 80 | 72 participant × method endpoints and 8 saved cohort means/intervals |
| 2 | `Fig2_cpu_primary_paired_changes` | 13 | 12 original primary participant differences and the original mean/interval |
| 3 | `Fig3_csp_signed_support_halves` | 30 | Two signed margins for each of 30 development support sessions |
| 4 | `Fig4_longitudinal_paired_changes` | 180 | Two contrasts × 18 participants × five target sessions, with BA inputs and query counts |

Each stem has `.png`, `.pdf`, `.svg`, `.tif` and `_source_data.csv` files. Captions
are in [CAPTIONS.md](CAPTIONS.md). Submission TIFFs are actual 600-dpi,
single-frame, flattened RGB images with LZW compression and no alpha channel.
All are 19.05 cm wide; heights are 11.43, 13.462, 13.97 and 19.05 cm, respectively.
All TIFFs are smaller than 10 MB. Their RGB pixels exactly match the PNG review
exports. No image includes a figure title or caption.

All labels actually use the existing **Liberation Sans** font at 8–12 pt; this is
a metric-compatible substitute, not Arial. The environment has no actual Arial
or Times New Roman font. Strict requested font-family compliance is therefore
not claimed. The PDF embeds the actual Liberation Sans fonts and SVG remains
editable. No font, package or new environment was installed.

## Inspect and reproduce without overwriting any exports

The exact producer is `scripts/render_kumar_submission_figures_20261015.py`.
The producer preserves existing output files. For a fresh clone that already
contains these canonical exports, use the small wrapper below. It verifies the
executed producer hash and all five input hashes, changes only the two output
paths, and refuses existing non-empty, overlapping or out-of-repository paths.
Run from the repository root in the documented existing environment:

```bash
MPLCONFIGDIR=/workspace/.cache/matplotlib \
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  research_logs/kumar_submission_figures_20261015/run01/reproduce_figures.py \
  --output-dir manuscript/figures/plos_submission_reproduction_20261015 \
  --log-dir research_logs/kumar_submission_figures_reproduction_20261015/run01 \
  --check-only
```

Remove only `--check-only` to render into those fresh directories. This rerenders
images from saved text; it does not rerun an EEG analysis. Use different fresh
directories for another reproduction. The existing canonical images, frozen
scientific results and historical receipts are never overwritten.

Validation and provenance are in
`research_logs/kumar_submission_figures_20261015/run01/`:

- `figure_generation_receipt.json`: exact source/producer/export byte hashes,
  runtime versions, all image dimensions/DPI, actual font file/hash, source-byte
  preservation, plotted point/cell counts and annotation-boundary checks.
- `independent_export_validation.json`: 829 actual-byte, saved-cell, identity,
  geometry and PDF font checks; no failures.
- `reproduction_cli_validation.json`: fresh-path metadata preflight succeeds;
  canonical existing output and outside-repository destinations are refused.
- `visual_contact_sheet.png` and `visual_review.json`: visual review scope.
- `layout_preflight_failure.json` and `layout_preflight_failed/`: initial
  publication-layout proof and its actual fail-closed annotation-boundary error,
  retained before the minimal layout correction. These are image proof history,
  not scientific results or additional scientific attempts.

The image source CSVs can be freely inspected with an ordinary CSV reader. The
query count column in Fig 4 is the saved matched-method count; the underlying
trial-identity matching audit remains the original comparison evidence. This
renderer does not reconstruct trial identities or claim a new per-trial audit.
