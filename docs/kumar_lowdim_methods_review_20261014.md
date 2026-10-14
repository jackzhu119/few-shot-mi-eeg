# Development-only low-dimensional measurement: methodological review

Date: 2026-10-14 (Asia/Shanghai). This review concerns the development-only
measurement protocol frozen by the parent task. It is a methodological review,
not verification of an executed experiment or evidence that an adaptation gate
works. No source-data experiment was run during this review.

## Scope and fitting boundaries

Use the six fixed development participants, source TRAIN runs 0/1 and the
current target-session run-0 support only. Keep the three candidates fixed:
standardized 44-dimensional Mu/Beta power, source PCA4, and anatomical
C3/Cz/C4 Mu/Beta power in six dimensions. Do not select a winning feature or
gate threshold from their results.

For source run-0-to-run-1 and run-1-to-run-0 measurement, start from raw
`log10_bandpower_44`. Fit the scaler, PCA when applicable, right-minus-left
task axis and class-midpoint threshold on the training run only. The existing
coordinates standardized on all 40 source trials would leak the held-out source
run into this fold. Fold-fitted scaler and PCA may be reused across label
surrogates because those transforms do not use labels; label-derived axes and
midpoints must be reconstructed for every assignment. Source held-out-run BA
is a measurement positive control, not target-query algorithm performance.

For support measurements, fitting the coordinate and task axis on all 40
permitted source TRAIN trials is valid. Those fitted quantities remain fixed
for all support halves and surrogates. Target query rows, final-cohort
participants and future support must not participate.

## Phase-alignment controls

Independent circular label shifts within each source run preserve run
boundaries, label counts and the cyclic label sequence. Reuse each pair of
assigned label sequences across both source folds and all three candidates.
Twenty by twenty shift-index pairs need not imply 400 distinct label
assignments: record both attempted index pairs and distinct assignments.

These shifts are descriptive phase-alignment controls. Circular wraparound,
within-run stationarity and the absence of cue-order confounding have not been
established. Empirical rank or tail fractions therefore are not formal
randomization p-values and do not demonstrate neural task specificity.

For support, recompute the class-wise chronological halves under each primary
circular label shift so that the estimator is included in its own control.
Also retain the fixed-original-half sensitivity. Record attempted, valid and
invalid shifts and the denominator of every tail fraction. Single-class
halves, zero task directions and other unestimable cases must remain visible;
do not silently omit them.

## Endpoints and statistical unit

Alongside task-direction cosine, report each support half's signed
right-minus-left mean contrast projected onto the fixed source axis and scaled
by the fixed source projection standard deviation. Report the product of the
two half contrasts. A one-dimensional direction cosine can only be +1 or -1
and is unsuitable as a graded reliability measure. Zero scale or zero axis is
unestimable, not a reason to choose another feature.

Average the two source folds or five support sessions within participant
before cohort summaries. The independent sample is six participants, not 12
folds or 30 sessions. Participant bootstrap intervals remain exploratory with
this sample size. Trial bootstrap intervals describe conditional uncertainty
of the small observed support and must not be called population intervals or
proof of independence.

## Decision limits

Positive source-run generalization and support reliability distinguishable
from these phase controls could justify investigating a minimal adaptation
gate. They would not establish that the measurement predicts adaptation
benefit or that a gate is effective. Preserve negative directions, failures
and unestimable cases; do not choose minimum pass fractions after observing
the results. This review does not specify an automatic gate-development pass
threshold.

The fixed final-cohort baseline results have already been seen. Restricting
this measurement to development participants prevents additional query-based
selection, but does not restore researcher blindness to those existing test
results. Any subsequent algorithm evaluation in the same cohort remains
exploratory; independent confirmation would require a separately frozen,
qualified evaluation scope. None of these measurements establishes human
learning, neural skill retention or a causal effect of adaptation.
