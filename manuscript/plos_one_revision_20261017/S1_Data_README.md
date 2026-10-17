# S1 Data — revised saved numeric-text companion, 2026-10-16

**Longitudinal motor-imagery EEG decoding: Frozen baselines, supervised
recalibration, and task-measurement reliability** — Ziyuan Zhu.

This companion retains the original 2026-10-15 saved CPU/EEGNet predictions,
trial/QC lookup, original comparisons, six training-history tables, thirteen QC
tables, four exact figure tables and portable QC code/tests. It adds the saved
development reliability/drift numeric records and the separately identified
post-review paired-check code, two inputs, four-row results and receipts.

Start with `DATA_DICTIONARY.md`, `REPRODUCE_SAVED_RESULTS.md`,
`SOURCE_PROVENANCE.json` and `MANIFEST.json`. `LICENSING.md` and the complete
MIT/CC BY texts define the current component-specific grant. Source annotations
retain their original Kumar2024/NEMAR attribution and terms.

Thirty-eight old members are unchanged at their original paths. The old root
dictionary, reproduction instructions and manifest are updated, while their
exact original bytes remain under `provenance/historical_20261015/`. Thus all
41 historical member contents remain available; this is not a claim that all
41 retain their old root names/hashes. The original41-member ZIP is untouched.

The added reliability files are allowlisted numeric extracts from existing
saved result JSONs; they omit fitted axes/scaler/PCA states and weights. They
include all original saved10,000-draw probe bootstrap vectors. The drift record
contains the original2000-draw result/CI/count/seed, not unrecorded individual
draw correlations. Those missing vectors have not been recreated.

The post-review four-test analysis is explicitly exploratory, with repeated
participants across46 contrast-input rows, original CI strings retained,
declared floating-point boundary rules and a family-four Holm adjustment. These
results were already computed and validated before packaging. Packaging copies
them and their receipts without recalculating statistics. Optional text-only
replay commands use fresh outputs and do not fit or invoke a model.

Excluded: EEG samples/epochs, raw or processed feature matrices, fitted axes,
CSP/LDA/EEGNet parameters and checkpoints, authorization/credential records,
third-party article/codebook full texts, vendor source/software, fonts, CSL,
CUDA/environment archives and unrelated datasets. License legal texts are
included as expressly requested notices. No trial-phase sequences or imagery
durations are inferred from class labels. Numeric checks do not establish
continuous imagery, a useful update gate, skill retention or clinical efficacy.

The official source release and study DOIs are in `SOURCE_ATTRIBUTION.md`.
The actual final repository revision/tag is bound by the enclosing release
manifest; this package records source-base identity and full actual bytes,
without a fictitious self-containing commit or new DOI. This is an author-review
artifact, not a claim of completed journal submission or ethics determination.
