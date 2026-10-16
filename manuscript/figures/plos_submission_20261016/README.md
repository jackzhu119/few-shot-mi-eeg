# Submission figures: 2026-10-16 legend revision

Fig 1 clarifies the neutral circular legend key as **Participant (method color)**.
The key identifies the participant marker type; the plotted point colors follow
the four methods on the horizontal axis. This is a legend clarification, not a
correction to the numerical observations or uncertainty intervals.

The producer is `scripts/render_kumar_submission_figures_20261016.py`. Relative
to the preserved 2026-10-15 producer, only its two output paths and that legend
label changed. All four figures were rendered from the same five saved text
inputs. They read no EEG, checkpoint, model or query-trial files and execute no
fit or inference pass. The four `_source_data.csv` exports must remain
byte-for-byte identical to the 2026-10-15 exports.

Fig 4 already used the red–blue diverging `RdBu_r` map. That map, its shared
symmetric −60 to +60 percentage-point limits, all 180 signed cell values,
participant order and both cohort boundaries are unchanged. The primary cell
range is approximately −39.86842105263158 to +55.00000000000001 percentage points;
the secondary range is −37.49999999999999 to +42.5. No new clipping or rescaling
was introduced. Fig 2–4 retain the previous graphical content.

| Figure | Stem | Source CSV data rows | Export geometry at 600 dpi |
| --- | --- | ---: | --- |
| 1 | `Fig1_target_query_participants` | 80 | 4500 × 2700 px; 19.05 × 11.43 cm |
| 2 | `Fig2_cpu_primary_paired_changes` | 13 | 4500 × 3180 px; 19.05 × 13.462 cm |
| 3 | `Fig3_csp_signed_support_halves` | 30 | 4500 × 3300 px; 19.05 × 13.97 cm |
| 4 | `Fig4_longitudinal_paired_changes` | 180 | 4500 × 4500 px; 19.05 × 19.05 cm |

Each stem has PNG, PDF, SVG, TIFF and source CSV files. TIFFs are single-frame,
flattened RGB with LZW compression and no alpha channel; each is below 10 MB.
PNG/TIFF RGB pixels and physical dimensions are checked from the actual exports.
The actual font is **Liberation Sans**, 8–12 pt. The exports do not claim exact
Arial or Times New Roman compliance. No environment, package or font was
installed or purchased for this revision. Captions remain outside the images
in [CAPTIONS.md](CAPTIONS.md).

## Reproduce into new paths

The wrapper verifies the producer hash and all five input hashes before using
explicit, fresh repository paths. It refuses existing non-empty, overlapping or
out-of-repository destinations. From the repository root, in the existing
environment:

```bash
MPLCONFIGDIR=/workspace/.cache/matplotlib \
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  research_logs/kumar_submission_figures_20261016/run01/reproduce_figures.py \
  --output-dir manuscript/figures/plos_submission_reproduction_20261016 \
  --log-dir research_logs/kumar_submission_figures_reproduction_20261016/run01 \
  --check-only
```

Remove `--check-only` to render into those fresh paths. Do not use the canonical
2026-10-15 or 2026-10-16 output directories as reproduction destinations.

Independent validation passed **1,324 checks with no failures**. All four source
CSVs are byte-identical to the old exports, and Fig 2–4 are byte-identical in all
four image/vector formats. Fig 1's actual raster and PDF-render differences are
confined to the bottom legend. All 55 protected historical files retain their
original byte lengths and SHA256 hashes.

The revision evidence is in
`research_logs/kumar_submission_figures_20261016/run01/`: generation receipt,
independent byte/numerical/export validation, CLI checks, visual review and the
baseline inventory of the unchanged historical artifacts.

## Attribution and licensing

The underlying source is Kumar2024, NEMAR `nm000177/v1.0.5`,
DOI [10.82901/nemar.nm000177.v1.0.5](https://doi.org/10.82901/nemar.nm000177.v1.0.5),
under its stated CC BY 4.0 terms. Original project code is MIT and original
figures, derived tables and authored documentation are CC BY 4.0 under the
author's 2026-10-16 scoped grant. Source-derived identities, labels and metadata
retain source attribution and rights. Third-party software, fonts and other
excluded materials retain their own terms; see [LICENSING.md](../../../LICENSING.md).
