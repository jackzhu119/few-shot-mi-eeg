# 2026-10-16 figure legend revision

The new renderer and exports preserve the scientific values and visual encodings
of the 2026-10-15 figures. The only visible revision is Fig 1's legend label:
`Participant` becomes `Participant (method color)`.

## Review assessment

The old neutral grey circle is a marker-type key, while plotted point colors
follow methods/columns. Its generic label was numerically valid but could be
clearer. Describing it as a mathematical error would be inaccurate. `method
color` describes the actual encoding; `row color` would introduce a mismatch.

Fig 4 already uses `RdBu_r`, not a red–green map. The original producer,
generation receipt, source CSV and displayed image agree on shared limits of
−60 to +60 percentage points. The original primary cell range is
−39.86842105263158 to +55.00000000000001; the secondary range is
−37.49999999999999 to +42.5. This revision retains those ranges, all signed
annotations and the original dynamic limit calculation. An early commentary
estimate of ±40 was incorrect and was corrected after reading the actual
receipt and source values; it was never used to render an artifact.

## Implementation scope

`scripts/render_kumar_submission_figures_20261016.py` differs from the original
producer in exactly three string replacements: new output path, new log path
and the Fig 1 legend text. The original SVG hash salt is retained so unchanged
exports can be compared directly. All five scientific inputs remain the
original saved text tables/JSON. No source arrays, EEG, learned weights,
checkpoint deserialization, training or model-query runner is involved.

Each of the four figures has PNG/PDF/SVG/TIFF exports and a source CSV. The
producer retains its actual text-boundary, 8–12 pt font-size, DPI, pixel-size,
RGB/LZW/single-frame, TIFF size and numerical point/cell checks. The generation
receipt records the actual Liberation Sans file and its hash, without claiming
exact Arial/Times compliance. No font, package or environment was installed.

The new captions retain their original scientific wording. Main-manuscript and
author-worksheet prose revisions are owned by the parent task.

## Verification evidence

Completed: independent export/revision validation passed **1,324 checks, zero
failures**; all eight CLI checks and Ruff also passed. Four source CSVs are
byte-identical to their old versions. Fig 2–4 are byte-identical in all four
formats, while Fig 1's differences are confined to the intended bottom legend.
The PNG difference box is `[1429, 2494, 3104, 2576]` and the 72-dpi PDF-render
difference box is `[171, 299, 372, 310]`. All 55 protected historical files retain
their old lengths and SHA256 hashes.

- `figure_generation_receipt.json`: successful saved-text render, exact input,
  producer and output hashes, actual font, all image geometries and scientific
  point/cell counts. `render_stderr.log` is empty.
- `prior_artifact_baseline.json`: 55 historical files recorded before rendering
  across the old producer, old figure directory and old figure log directory.
- `reproduction_cli_validation.json`: eight passed CLI checks; fresh preflight
  succeeds, while missing arguments, existing old/new outputs, outside-repository,
  nested and identical destinations are rejected. These checks rendered no images
  and created no preflight destinations.
- `independent_revision_validation.json`: independent checks of actual export
  bytes, every saved heatmap cell, all four old/new CSV byte comparisons,
  unchanged Fig 2–4, TIFF/PNG pixels, embedded PDF fonts and historical preservation.
- `visual_review.json` and `visual_contact_sheet.png`: AI-assisted visual review
  of the actual new image exports. This is not an assertion of the author's
  personal final review or independent human replication.

Ruff is run on the new producer, reproduction wrapper and independent validator.
Only the new figure and log paths and new script are written by this subtask;
the main manuscript is not edited.
