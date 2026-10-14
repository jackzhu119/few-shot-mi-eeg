# Independent static implementation review

Date: 2026-10-14 (Asia/Shanghai). Status: **passed for the restricted,
development-only pre-execution scope**. This report reviews code and provenance,
not executed real-data results. No source-data experiment, query-data access or
implementation edit was performed by this reviewer.

Reviewed implementation:
`scripts/analyze_kumar_lowdim_reliability.py`, SHA-256
`c3f19cac305cb72fdbfb539172b198bc67836ec6499730fad8829fe16f27a964`.
The accompanying receipt binds the configuration, plan, tests, projection receipt
and this report. Execution must use the physically restricted input directory
`lowdim_development_inputs_run01_20261014`; hashes of its declared files were
checked without loading numerical feature arrays. The original full containers
were not opened by this reviewer.

## Checks

- Source folds fit StandardScaler and full-SVD PCA4 on raw log-power from the
  TRAIN20 only. Held-out source-run features are transformed without fitting.
  The preexisting 40-trial standardized coordinates are not used in these folds.
- Source and current-support identities, labels, development membership, run
  roles, source budgets and support class counts have explicit validation. The
  executable loads only `source_train` and `target_support` rows for calculations.
  The actual container query-row count is derived from metadata rather than a
  hardcoded statement. Restricted input containers contain no query rows according
  to the separate projection receipt; this review checks that receipt's hashes,
  not the original-to-restricted numerical equality.
- Each circular source label-shift pair is reused across both source-fold
  directions and all three candidates. Label-derived centroid axes and midpoints
  are reconstructed; label-independent fold transformations are reused. Unique
  rotated label assignments are recorded separately from shift-index counts.
- Support uses source-only coordinates fitted on the permitted 40 source trials.
  The final implementation creates a fixed source-axis reference once per
  candidate per participant and reuses it across all five sessions and controls.
  Thus the declared 18 source-axis fit attempts are actual constructions, not
  repeated reconstructions hidden behind a unique-definition count.
- Primary support controls recompute class-wise chronological halves under every
  label shift. Fixed-original-half sensitivity retains single-class and zero-axis
  cases. Per-metric tail fractions record total, valid and unavailable counts.
  A zero half-vector can have zero scalar contrast while its direction cosine is
  unavailable; these are distinct endpoints and their denominators remain explicit.
- The source projection SD uses source-only data with ddof=1. Support does not
  fit a scale. Both signed half contrasts and their product are saved alongside
  vector cosines; the product alone does not establish agreement with the source
  orientation because two negative half contrasts also give a positive product.
- Cohort bootstrap uses six participant values, after averaging source folds or
  all five support sessions within each participant. A missing participant value
  makes the relevant summary unavailable instead of silently reducing the cohort.
  The 10,000 bootstrap draws are reproducible with seed 42.
- No adaptation gate, threshold search or automatic candidate selection is
  implemented. The source centroid probes are diagnostic fits, explicitly
  counted separately from primary baseline and adaptation fits.

## Limits and decisions

No blocking implementation issue remains in the reviewed revision. Two earlier
receipt issues were corrected before this review: the container query indicator
is dynamic, and the fixed source axes are actually constructed once and cached.

Circular shifts remain descriptive phase-alignment controls. Unknown stationarity,
circular wraparound and cue-order confounding prevent treating their tail
fractions as formal randomization p-values or evidence of neural specificity.
Six-participant bootstrap intervals are exploratory. Repeated shift assignments,
folds and sessions do not increase the independent participant count.

The previously seen final-cohort baseline results remain seen. Restricting this
diagnostic to development participants does not restore blind final testing for
a future same-cohort algorithm. Measurement reliability alone does not establish
adaptation benefit, human learning or skill retention. An independent review of
executed numerical results remains a separate step.
