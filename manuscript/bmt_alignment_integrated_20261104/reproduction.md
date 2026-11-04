# Reproduce the integrated revision from saved results

Run from the repository root. The analysis plan is `13dd7646c4ce37db40504154388e76b4c6ca6595`. Sources, results and old manuscripts are retained separately; new output folders prevent overwriting the evidence.

## Verified one-line table reproduction

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python scripts/reproduce_paper2_alignment_saved_results_20261104.py --output /tmp/paper2-integrated-reproduction-new
```

This command was actually run with a fresh run02 directory. It rebuilt all 12 P1 CSVs and five P2 CSVs byte for byte and ran the independent P1 checker. It reads saved predictions and per-cell receipts only, creates no model, runs no new query forward and requires no EEG or private checkpoint. Use a new output name when repeating it. Outside this workspace, use a Python environment with the recorded science dependencies instead of the absolute interpreter path.

## Verified figure and document commands

```bash
python scripts/render_paper2_alignment_integrated_20261104.py
python scripts/build_paper2_alignment_integrated_20261104.py --no-package
python scripts/build_paper2_alignment_integrated_20261104.py --package-only
```

The renderer consumes recorded participant summaries and historical contrast tables, not raw EEG or models. Five original-format figures have 170 mm width, at least8pt text, embedded PDF fonts, editable SVG text, RGB8bit LZW TIFF at600dpi and individual source CSVs. Figure2 A/B use new descriptive uncertainty; C/D retain historical intervals. Figure5 A/B show individuals and means without arm confidence intervals, C/D show paired participant intervals. PDF/SVG byte hashes may differ after rendering because export metadata/identifiers change; source CSV values and declared geometry are the numerical checks.

Pandoc, XeLaTeX, DejaVu fonts and the available xurl/seqsplit packages produced the documents. The PDF-only line-break treatment keeps long identifiers/URLs on the page without changing editable source values. Main Word tables and formulas remain editable; main figures are supplied separately.

## Current software

`research_logs/paper2_alignment_integrated_20261104/ENVIRONMENT_VERSIONS.json` separates the actual science CPU interpreter (Python3.11.16, NumPy2.2.6, SciPy1.15.3, scikit-learn1.7.2, MNE1.10.2) from the document/plot interpreter. No existing environment was upgraded. Independent P1/P2 checks and targeted synthetic tests have their actual logs in the audit tree.

## Actual new CPU sensitivities

The complete original/continued invocations are recorded in `mechanisms/dispatch_run01.json` and `dispatch_continuation.json`; cumulative truth is in `AGGREGATE_EXECUTION_RECEIPT.json`. Source EEG, prepared arrays and544 private classical checkpoints remain outside the public package. The script `scripts/run_paper2_alignment_mechanisms_20261104.py` is the bounded actual entry, with original signal/role paths stated at its top. It is not needed to rebuild paper tables or figures. Do not rerun completed models to reproduce this manuscript.

Actual396 matched fits and148 EA phase fits were completed;32 original undefined cells did not fit. An expected-undefined compatibility stop occurred before the next claim;362 completed cells were preserved and only182 unattempted cells continued. Both executed wrappers, the real exception and logs remain archived. A later persistent-deadline/count correction was tested synthetically only; it is not falsely described as enforced by the already completed execution. This history concerns execution continuity, not an additional experiment or extra participants.

## Public inputs and licenses

The public data/code ZIP includes the49 original P1 source files, relevant native phase metadata/code, actual new cell predictions/probabilities, full-precision tables, original protocols and exact SHA manifests. It contains no raw EEG, private NPZ weights or credentials. Original source-data terms remain applicable. Paper1 definitions were adapted to Paper2's own participant/session weighting; no Paper1 effect size was imported. Paper3's same-prediction C/I analysis was deduplicated; its unlicensed code/prose was not redistributed. Source bodies read for the audit are retained locally rather than republished; immutable commit/path/hash records are provided.

New probability scores use genuine saved outputs from this revision's matched fits, clipping1e-7 for balanced NLL and a class-balanced single-coordinate Brier score. The old hard-label archive is not converted to probabilities. New exploratory seed20261104 intervals never overwrite historical intervals or Holm families.
