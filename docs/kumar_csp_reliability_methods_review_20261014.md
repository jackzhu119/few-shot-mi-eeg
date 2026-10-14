# Independent methods review: development-only supervised CSP measurement

Date: 2026-10-14 (Asia/Shanghai). This review precedes the proposed CSP measurement
execution. It is a methodological review, not a numerical replication or a result
of the proposed experiment. No scientific model was fitted and no query or final
cohort signal was inspected for this review.

The earlier fixed power, PCA4 and motor-channel diagnostics did not establish
reliable task measurements. That finding does not establish absence of task
information in EEG. The next diagnostic may examine the already fixed CSP4/LDA
model family, with its label dependence and signed orientation made explicit.
It must remain exploratory: the earlier final-cohort baseline outcomes have
already been seen.

## Scope and source bindings

- Use only development IDs 1, 4, 7, 10, 13, 16; original source ses-0/run-0 and
  run-1 (20 complete trials per run, 10 per class), and each current target
  session's preassigned run-0 support (19/20 trials). Do not replace partial
  windows, accumulate previous target support, or choose trials by performance.
- Preserve the frozen 5-second, all-22-channel CAR, 8–30 Hz offline filter and
  128 Hz resampling, original classes, trial identities and retained QC flags.
  No source-validation, source-query, target-query or final-cohort input belongs
  in this diagnostic. Restricted input arrays should physically omit those rows.
- Source transfer probes use TRAIN20-fitted CSP4 (Ledoit–Wolf, log average power,
  no trace normalization) and LDA (lsqr, automatic shrinkage). They are auxiliary
  diagnostic fits; they do not rerun, replace or redefine the completed primary
  source40/adaptation baseline experiment.
- Target support uses the existing SOURCE40 CSP/LDA model state without a new
  decoder fit. Replay its numeric arrays, validate all source fit IDs and hashes,
  and verify that its classes are exactly `[0, 1]`, with right-hand positive.

## Source leave-one-run-out positive control and exact phase controls

Fit run-0/train → run-1/test and run-1/train → run-0/test. The held-out run may
provide evaluation labels only. Saved SOURCE40 filters are invalid for these
folds because their supervised fit used both source runs. Any additional learned
feature scale used in a fold must fit the TRAIN20 only.

For each participant, use the same exact Cartesian set of 400 label-phase pairs
`(shift_run0, shift_run1)` in `0..19 × 0..19`, including identity. Reuse this set
across both fold directions and all six participants. A training-label phase
change must refit **both CSP and LDA**. Merely rotating labels after a supervised
CSP fit would leave task-label information in the purported control.

Exact controls need only 240 fitted pipelines, not 4,800:

1. For each of six participants and each of two folds, fit one pipeline for
   each of the 20 training-run label shifts.
2. Predict its fixed held-out signal array once; record the model state, training
   labels/IDs, held-out IDs, features, decision scores and predictions.
3. Score those same predictions against all 20 held-out label shifts.
4. Join the two fold scores by their shared run-0/run-1 phase pair and average
   the folds within participant before participant-level aggregation.

This is algebraically identical to separately refitting every joint pair:
the held-out label shift is not an input to training. There are 240 CSP fits
and 240 LDA fits, including the 12 identity-fold pipelines. Their 4,800 fold
score evaluations and 2,400 participant/pair two-fold means do not increase the
statistical sample size.

Read-only inspection of the restricted metadata found 20 unique rotations in
each of the twelve source runs; none of those rotations is an exact full class
swap. Record the unique-assignment counts in execution evidence rather than
assume every shift is distinct for future data. Keep identity as an explicitly
identified phase, preserve every control value and report phase tail fractions
as conditional alignment sensitivities. Temporal stationarity, cyclic-boundary
exchangeability and neural specificity are unverified; these fractions are not
formal randomization p-values.

## Frozen target-support measurement conventions

Let `f(x)` be the saved SOURCE40 CSP4 log-power features. Compute a four-coordinate
standardization from the SOURCE40 trials only, using their mean and population
SD (`ddof=0`). Apply that fixed transform to current support. This is a measurement
coordinate convention, not a decoder update. Degenerate scales must have an
explicit fixed policy and must not cause rows to disappear.

Let the fixed source task direction be the standardized right-minus-left class
mean vector. Define support halves separately within each class: the first
`floor(n_class/2)` chronological trials and the remaining trials. Compute:

- Full-support/source direction cosine and half-to-half direction cosine in
  the four frozen standardized coordinates.
- Each half's signed right-minus-left contrast on the unit **source** task axis,
  divided by SOURCE40 projection SD (`ddof=1`). Preserve both half values and
  their signs; the product alone is ambiguous.
- The frozen binary discriminant score `s = f(x) @ w + b`. Verify orientation
  through the saved class ordering. Preserve its original zero threshold;
  do not center on target support or fit a target scale.
- Each half's class-balanced true-class signed margin
  `0.5 * (mean(s | right) - mean(s | left)) / SD_source(s)`, with SOURCE40 score
  SD (`ddof=1`). Also preserve separate right margin `mean(s | right)/SD_source(s)`
  and left margin `-mean(s | left)/SD_source(s)`, the score location, class recalls,
  predicted proportions and class-collapse indicator.

The signed task-axis contrast and the signed LDA margin are different fixed
measurement conventions. Report both; do not select the one with a favorable
outcome. A margin is a discriminant-score measurement, not a calibrated posterior
probability, and its numerical scale does not make it neural task information.

Enumerate every 19/20 cyclic phase of current-support labels while the SOURCE40
filters, LDA, scales and reference axes remain fixed. Recompute the classwise
chronological halves for each phase. An additional fixed-original-half sensitivity
can be reported separately, including unavailable single-class halves and its
exact valid denominator. Preserve identity, negative orientations, zero vectors
and unavailable rows. No phase or sign may be chosen using query outcomes.

## Interpretation and operational limits

**Cosine does not determine task orientation.** Exchanging left/right labels in
both halves negates both difference vectors and leaves their cosine unchanged.
Two halves can therefore agree while both are opposite to the source task axis.
Similarly, their signed-contrast product is positive when both contrasts are
negative. A stable negative frozen-score margin may indicate a reproducible
reversal in this measurement, not absence of task information.

**Overall score contrast can hide threshold failure.** A right-minus-left score
contrast cancels the intercept. Both classes may nevertheless lie on the same
side of zero and produce a collapsed frozen classifier. Separate class margins,
recalls, predicted proportions and score location are necessary to distinguish
orientation, separation and decision-threshold calibration. Do not silently flip
the score or substitute `max(BA, 1-BA)`.

**Source and target estimates have different optimism and budgets.** SOURCE40
axes, scales and LDA are fitted with source labels; their in-sample margins are
optimistic. TRAIN20 leave-one-run-out transfer is a held-out positive control,
but is not a matched calibration distribution for SOURCE40/current-support
reliability. Do not set a universal threshold by directly comparing these values.

**Task label sensitivity does not certify MI physiology.** Retained large
amplitude flags, cue/time structure, ocular or muscle activity, reference choice
and the offline task window may explain apparent separation. Phase controls do
not resolve these confounders. Preserve all original QC flags and the lack of
expert artifact certification; do not promote this diagnostic to a neural skill,
learning, retention or clinical claim.

Use six published IDs as the independent statistical units: average the two
source folds or five current-support sessions within ID first, then bootstrap
IDs with the fixed seed and replicate count. Session/trial/phase/fit counts do
not create extra participants. Within-support resampling, if included, must be
called conditional measurement uncertainty, not a population interval.

Good measurement alone does not establish adaptation benefit. This stage must
not choose a candidate, confidence gate, sign correction or adaptation threshold.
Any subsequent strategy needs a separately frozen nested-development protocol,
matched label/update budgets and conventional adaptation controls. Because final
baseline outcomes were already observed, a later same-cohort algorithm evaluation
remains exploratory; it cannot restore an untouched final test.

## Required independent checks before accepting the diagnostic

- Input IDs, classes, chronology, source/support roles and original processed
  signal hashes match the frozen protocol; no query/final row can enter a fit.
- Replayed SOURCE40 feature/score/prediction arrays match saved numeric model
  state, including strict `score > 0` prediction convention and class ordering.
- Every supervised source-control model is bound to its exact shifted TRAIN20
  labels, training data and trial IDs. Cached predictions are reused only across
  held-out label phases; train-label changes never reuse a fitted CSP/LDA state.
- Independently reconstruct joint phase-pair scores from the saved predictions,
  shifted held-out labels and confusion matrices. The identity pair must match
  the two ordinary source-fold positive controls.
- Synthetic unit checks demonstrate full class-swap cosine invariance, reversal
  of signed margins, negative-orientation retention and a positive class contrast
  with a collapsed classifier caused by an offset. Source feature/score scale
  must remain invariant when only target-support values change.
- Preserve all numerical failures and exact denominators, estimator/score counts,
  CPU runtime and version/config/code/input hashes. Keep this review and the
  frozen plan distinct from later execution and numerical-review receipts.

No paid compute is required or authorized by this review. The existing MIND
download/R2 continuation is independent of this diagnostic and must not be
restarted merely to run the analysis.
