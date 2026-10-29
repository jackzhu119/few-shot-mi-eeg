# Figure code, source data and reproduction

This package contains the three main manuscript figures and a separate black-and-white decoder workflow. The workflow is an independent methods illustration, not an additional numbered manuscript figure. All numerical plots use the project's saved results. The rendering scripts load no raw EEG or model tensors and perform no fitting, prediction, bootstrap resampling or new hypothesis tests.

## Software and editable formats

The figures were drawn programmatically with Python, Matplotlib and NumPy; Pillow supplies and checks the TIFF exports. Origin and GraphPad Prism were not used. No generative image tool was used.

Each rendering exports PDF, SVG, PNG and TIFF at a physical width of 170 mm. PDF and SVG retain vector drawing primitives and text; SVG uses editable text, and PDF embeds TrueType fonts (`pdf.fonttype=42`). The heatmap cells and color bars remain vector objects. PNG and TIFF are exported at 600 dpi, with LZW compression for TIFF. CSV source tables accompany the quantitative figures. The exact software versions, source hashes and export hashes are recorded in each rendering manifest rather than inferred from file names.

The actual new renders were first written to `/tmp/component_plot_redesign_20261029/main/`, `/external/` and `/workflow/`. These temporary locations are build locations, not persistent data dependencies. The review package retains the exported figures under this manuscript's `figures/` and `workflow/` directories, together with the code and source tables at their repository-relative locations.

## Figure meaning and statistical units

| Artifact | Saved information displayed | Statistical unit and interval scope |
| --- | --- | --- |
| Figure 1, `Fig1_components` | Four decoder endpoints; paired classifier, spatial-refitting and alignment increments; corrected/new-error decomposition | Original Kumar primary cohort, 12 participants. Each participant endpoint is the equal-weight mean of five target sessions. Contrast intervals are the previously saved 95% participant-bootstrap intervals: the original classifier/spatial contrasts keep their original historical analysis, while EA-minus-full keeps its later post-exposure exploratory, pointwise interval. No multiplicity-adjusted interpretation is added. The prediction-transition panel displays the saved class-balanced mean decomposition, without a new interval. |
| Figure 2, `Fig2_budgets_sessions` | Complete 4/8/12/16/full-support budget curves and two participant-by-session paired-gain heatmaps | Original remaining 12 and development 6 participants are plotted separately. Full support is the existing 19 or 20 labels. Budget curves display the saved cohort means, without newly estimated bands. Each heatmap cell is a within-participant/session paired BA difference; the five sessions are not five independent participants. Both heatmaps share the same zero-centered symmetric scale. |
| Figure 3, `Fig3_external_validation` | Four BNCI endpoints, paired full-minus-LDA-only and EA-minus-full contrasts, and participant-by-query-run paired gains | Nine BNCI2014-001 participants, each with 120 later-query trials in five whole runs. The participant is the inferential unit; run cells are descriptive. The saved 95% participant-bootstrap intervals are read directly from the fixed external analysis. Full-minus-LDA-only retains its primary role and EA-minus-full its secondary role. |
| `Decoder_component_workflow` | Existing fitting inputs, spatial representation, decision rule and later-query inference for four decoder actions | Methods diagram, not an estimated result. Source-label budgets are 40 for Kumar and 96 for BNCI; current support is 19/20 and 20, respectively. Query does not enter fitting, reference estimation or selection. |

The renderer preserves negative and zero differences, all participants, all fixed comparison roles and the historical confidence intervals. Redrawing is a visual revision; the underlying analyses and scientific conclusions are unchanged.

## Exact quantitative inputs

All paths below are relative to the repository root. The figure code/data archive, `Publication_Figures_and_Source_20261029.zip`, preserves these relative locations, so the same commands work after extracting it into a new directory. Raw EEG, checkpoints, credentials and a school-HPC installation are unnecessary for figure reproduction.

### Figures 1–2

Renderer: `scripts/render_component_revision_figures_20261029.py`.

- `manuscript/plos_one_innovation_20261017/Figures/Fig6_participant_source_data.csv`: original participant endpoints.
- `manuscript/plos_one_innovation_20261017/Figures/Fig5_source_data.csv`: saved prediction-transition decomposition.
- `manuscript/discovery_revision_20261027/figures/Fig1_update_components_source_data.csv`: original paired-contrast confidence intervals, retained without a new bootstrap.
- `research_logs/paper2_hpc_v2_20261023/existing_evidence/budget_participant_endpoints.csv`: complete participant/budget/method endpoints.
- `research_logs/paper2_hpc_v2_20261023/existing_evidence/budget_cohort_means.csv`: saved budget/cohort means.
- `research_logs/paper2_hpc_v2_20261023/existing_evidence/budget_cohort_paired_gains.csv`: saved component contrasts and exploratory alignment interval.
- `research_logs/paper2_structure_revision_20261029/component_replay/budget_session_metrics_replayed.csv`: independently verified participant/session/budget/method metrics for heatmap construction.

The independent saved-prediction check and its source hashes are documented in `research_logs/paper2_structure_revision_20261029/component_replay/README.md` and `REPLAY_REPORT.json`. This plot-only step uses the verified tables, rather than running that numerical audit again.

### Figure 3

Renderer: `scripts/render_component_external_figure_20261029.py`.

- `research_logs/paper2_external_validation_20261027/aggregate.json`: 36 participant/method endpoints, cohort means and saved paired bootstrap intervals.
- `research_logs/paper2_external_validation_20261027/run_metrics.json`: all 180 participant/method/query-run endpoints.
- `manuscript/bmt_component_revision_20261029/figures/Fig3_external_validation_source_data.csv`: the previous Figure 3 data, retained for an explicit identity/value/interval equivalence check.

The new Figure 3 CSV has 150 rows. Its renderer matched all 154 nonblank numeric fields to the previous CSV by panel/participant/method/run/contrast/unit identity; maximum absolute difference was zero. This includes both paired intervals. The new output is named `Fig3_external_validation.csv`; the previous `_source_data.csv` remains an input to that check.

### Separate workflow

Renderer: `scripts/render_component_workflow_20261029.py`.

The diagram's boxes, edges and labels encode the already documented methods in `manuscript/bmt_component_revision_20261029/MAIN.md`. Its exports include `Decoder_component_workflow_nodes.csv`, `Decoder_component_workflow_edges.csv` and `Decoder_component_workflow_caption.txt`, as well as the four image formats and a source/export manifest. It does not load prediction data or generate a scientific endpoint.

## One-line redraw commands

Run each command from the repository root, or from the extracted figure code/data package root, using a Python environment that already contains Matplotlib, NumPy and Pillow. The two quantitative scripts use distinct manifest names, so both can write into the manuscript figure directory. These commands regenerate the figure files, not the Word/PDF manuscript.

Figures 1–2:

```bash
python scripts/render_component_revision_figures_20261029.py --output manuscript/bmt_component_revision_20261029/figures
```

Figure 3:

```bash
python scripts/render_component_external_figure_20261029.py --output manuscript/bmt_component_revision_20261029/figures
```

Separate workflow:

```bash
python scripts/render_component_workflow_20261029.py --output manuscript/bmt_component_revision_20261029/workflow
```

The Figures 1–2 manifest is `figures/FIGURE_MANIFEST_20261029.json`; Figure 3 uses the separate `figures/Fig3_external_validation_manifest.json`. The workflow manifest is `workflow/Decoder_component_workflow_manifest.json`. Their source hashes, result identities, interval provenance and image-format checks describe the actual render. Export file hashes can change with plotting-library versions or PDF metadata even when the numeric CSV remains identical.

## Read-only equivalence and export checks

On 29 October 2026, the newly rendered Figures 1–2 CSVs in `/tmp/component_plot_redesign_20261029/main/` were compared directly with the existing manuscript CSVs under `manuscript/bmt_component_revision_20261029/figures/`, before replacement of the image files. Both pairs were byte-for-byte identical:

| CSV | Rows | Bytes | SHA256 of both copies |
| --- | ---: | ---: | --- |
| `Fig1_components.csv` | 94 | 7,663 | `a1a98399e484ed4965df5729bcca2d8c47dedf8444fd80cd32e073a3f9a3a7d0` |
| `Fig2_budgets_sessions.csv` | 160 | 12,636 | `a02740bc962264502f33a33ce50b129cf8a36aefb331c861c911404629beca0a` |

The four newly rendered SVGs were read directly: all contained text elements and none contained embedded `<image>` elements. All four TIFFs were opened with Pillow and reported 600×600 dpi with `tiff_lzw` compression. Their dimensions were 4015×2929 pixels for Figure 1, 4015×3425 for Figures 2–3, and 4015×2976 for the workflow. These checks concern rendering and file integrity; they introduce no new statistical analysis.
