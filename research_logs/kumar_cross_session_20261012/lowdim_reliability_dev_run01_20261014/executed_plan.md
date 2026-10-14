# Low-dimensional task-measurement diagnosis

Scope frozen before this computation on 2026-10-14 (Asia/Shanghai), after the
44-dimensional development-only diagnosis was seen. This is exploratory and is
not an external preregistration. The fixed development IDs are 1,4,7,10,13,16.
The previous baseline final-cohort scores have been seen; this does not restore
researcher blindness. No final-cohort file, query performance or new decoder
adaptation is used here. The MIND acquisition proceeds independently.

## Fixed candidates and access

Three candidates are reported together: source-standardized44 Mu/Beta log-power,
source PCA4 of that power, and the six source-standardized C3/Cz/C4 Mu/Beta columns.
These are fixed measuring conventions, not claimed neural manifolds or skill.
Use existing audited log10_bandpower_44 values and metadata. The NPZ contains
query rows, but only source_train and current target_support rows enter calculations.
Match each trial ID, class, cohort, source run and order; preserve all QC flags.
Do not fit on source_validation, source_query, target_query or future support.

## Source run transfer and negative controls

Within the originally allowed source_train pool, train on run0/test run1 and
train on run1/test run0. Each has20 events (10/class). Fit StandardScaler and full
SVD PCA4 only on the TRAIN20. The already saved40-trial scaler/PCA is not a valid
fold transform. Form a unit right-minus-left class-mean direction; the centroid
midpoint sets the diagnostic classifier threshold. Report balanced accuracy in
the other run, both folds and their participant mean. This is an auxiliary source
transfer probe, not an additional formal primary CSP/LDA baseline.

Run exact20x20 circular shifts of the labels in the two runs, including identity.
Each pair is shared across both folds and all three candidates. Refit the
label-dependent mean direction and midpoint each time; the independent fold
scaler/PCA can be reused. Save all conditional null values and tail fractions.
These shifts retain class counts and cyclic label-order dependence, but stationarity
and label exchangeability are not established. Do not call these fractions valid
population/randomization p-values or evidence of neural specificity. All features
share task/QC/confounding limits. Do not select the best candidate from these BA.
Report unique rotated label assignments separately from attempted shift pairs;
call these phase-alignment controls. Repeated assignments are not new evidence.

## Current support reliability

Fit coordinates on the full40-trial allowed source_train only. For each of the five
later sessions, use its fixed whole run0 support (19/20; no partial replacement).
For each class take its first floor(n/2) chronological trials and the remainder
as two halves. Report source/support direction cosine and half-to-half vector
cosine in each fixed dimension. Also project both halves onto the unit source task
axis and report signed right-minus-left contrasts divided by SOURCE projection SD
(ddof1), together with their product. A 1D direction cosine is only a sign and
does not substitute for effect size. Null/degenerate directions and insufficient
classes remain explicit; no row silently drops.

For each current support run enumerate every cyclic label shift. Recompute the
classwise halves inside each shift so the whole estimator appears in its null.
Also report fixed-original-half index sensitivity; single-class shifts are
unavailable and counted. Source direction/scaler/PCA remain fixed. Shift-null
comparisons are conditional temporal sensitivities, not biological independence.
Every null fraction reports its attempted/valid/invalid denominator; zero axes
and single-class halves cannot silently disappear.

## Aggregation and decision

Participants remain the independent unit: mean two source folds first and mean
five support sessions first. Report all six participants and10000 participant
bootstrap draws, seed42; no trial/session-as-independent confidence intervals.
No automatic winner, gate threshold or superiority test is selected. Any interval
and candidate comparison is exploratory in six development IDs. If results look
promising, first write a separate nested-development strategy protocol and compute
matched-budget controls; good measurement by itself does not establish adaptation
benefit. If unstable, preserve this negative diagnosis rather than fit to query.

Record actual hashes/config/source ancestor/runtime, fit/test/support identities,
probe/null fit counts and wall time. Preserve earlier outputs. This work does not
claim human skill, online causality, a trained EEGNet or a new effective algorithm.
