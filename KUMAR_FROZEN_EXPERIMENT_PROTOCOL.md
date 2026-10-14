# Kumar2024 frozen offline experiment protocol

Frozen on 2026-10-13 UTC before any Kumar model-performance evaluation in this
checkout. This is an internal prospective analysis freeze, not an external
preregistration. Historical NETBCI and learning-preserving records remain intact.
The current paper is **Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery
EEG**. The executable specification is
`configs/kumar_cross_session_20261012.json`; the preparation receipt binds its
SHA256, this document, source manifest, adapter, preparation script and split.

## Question and limits

Compare offline within-participant target-session decoding after a small,
preassigned labeled support run with a source-only decoder. The data contain
left-hand and right-hand motor-imagery labels. These are task labels, not trial
success, cursor control, racing outcomes, human skill acquisition or retention.
Signal geometry and classifier performance have distinct descriptive endpoints.
No online intervention or causal human-learning claim follows from this analysis.

## Fixed source, identities and order

Use only the already-local NEMAR `nm000177/v1.0.5` Kumar2024 derivative, CC BY 4.0,
and the pinned 2,705-file selection manifest. Each source file must match its
official size/checksum and receive a local SHA256 receipt. The adapter rechecks
the 360 EDFs and relevant sidecars, all continuous samples for finite values,
22-channel order, 512 Hz rate, native physical µV/MNE numerical V, CPz reference
metadata, source-event timing/bounds, TSV/EDF annotation agreement and historical
whole-recording numerical hashes. Preserve all 7,200 event identities.

Published identities `sub-1` through `sub-18` are the statistical units; absent
exact copies does not verify biological identities. Development identities are
`sub-1,4,7,10,13,16`; the other twelve are the fixed final-test cohort. Assignment
uses every third published numeric ID starting at one, independently of results.
No pooled independent sample count with another dataset is established.

The nominal order `ses-0` through `ses-5` and within-session scan order must agree
with strictly increasing `scans.tsv` acquisition timestamps. Record the actual
source strings and computed intervals, without inventing dates. These timestamps
are derivative-source reported; their acquisition provenance and calendar
accuracy are not independently established. Session indices remain the planned
analysis axis. Session 0 and 1 have four runs; sessions 2–5 have three.

## Windows, preprocessing and QC

Include exactly 5.0-second events containing exactly 2,560 samples. Retain all
44 partial events in source and split records, exclude them from fixed tensors,
and do not pad, extend or replace them. No content/performance-based exclusion.
Process each epoch independently: subtract the mean of all 22 channels at each
sample; fourth-order SciPy Butterworth SOS 8–30 Hz with `sosfiltfilt` default odd
padding; `resample_poly(up=1,down=4)` default Kaiser-5 window and constant padding.
Store 22 × 640 samples at 128 Hz as float32 numerical volts. No preprocessing is
learned, pooled across epochs or fitted on held-out data. Zero-phase filtering is
offline and does not establish a real-time implementation.

Flag a raw event when any channel's within-window peak-to-peak amplitude exceeds
250 µV. This fixed threshold was selected before performance; every flagged full
event remains in the primary tensor. Report flags by role/session and source
identity. Finite values and plausible amplitude are not expert artifact
certification. The native acquisition reference is CPz according to source
metadata; offline common-average referencing cannot reconstruct that acquisition
signal or supply a verified native-reference sensitivity analysis.

## Frozen partition and label budget

In `ses-0`, `run-0` and `run-1` are source train, `run-2` source validation, and
`run-3` source query. Validation is reserved for a descriptive readout; no search,
hyperparameter selection or refit uses it. In each later session, only `run-0`
is support; all remaining whole runs are query. The support budget is at most 20
source events, at most 10 of either class, before partial-window exclusion. Use
the complete first run in verified acquisition order. Partial loss reduces the
actual support count; do not balance by looking ahead, fill or replace events.
Adaptation sees source train plus only the current session's included support.
Previous and future target sessions are never accumulated.

The split audit must prove unique trial IDs, source-sample windows that do not
overlap, one role per complete run, disjoint development/final cohorts, and no
exact numerical duplicates across all raw trial windows or included processed
windows. Whole-recording numerical and mid-recording fingerprints are additional
source checks, not substitutes for the trial-window audit. Any strict failure
stops preparation and forbids fitting; qualified source-quality limitations are
reported separately without using prediction performance to exclude identities.

## Fixed CPU baselines and access rules

Use one configuration: MNE CSP with four components, Ledoit–Wolf regularization,
log mean-square features, `norm_trace=False`; sklearn LDA with `solver=lsqr` and
automatic shrinkage. Seed 42. Three methods share the same source and query data:

1. Source-only: fit CSP and LDA on source train; freeze both thereafter.
2. Frozen CSP plus LDA recalibration: retain source-trained CSP; fit LDA on source
   train plus current support.
3. CSP/LDA refit: fit both on source train plus current support.

Every fitting call records its exact trial IDs. All validation/query identities
are forbidden to CSP, LDA and every learned scaler, PCA, normalizer or geometric
reference. Query access is prediction or an already-defined descriptive
transformation only; no feature selection or threshold selection. Save replayable
numeric model state without pickle, predictions, class recalls, confusion counts,
prediction ratios, class-collapse flags, actual support counts and CPU wall time.
Report failures rather than removing difficult subjects by their performance.

## Fixed descriptive feature and geometry conventions

Welch PSD uses fs=128 Hz, Hann window, nperseg=256, noverlap=128, constant
detrending, density scaling, one-sided output and mean averaging. Integrate
absolute power by trapezoid including exact band-edge bins for Mu 8–13 Hz and
Beta 13–30 Hz. Use `log10(max(power,float64 tiny))`. Channel-major feature order
is `(F7,Mu),(F7,Beta),...,(POz,Mu),(POz,Beta)`, giving 44 dimensions. These are
absolute powers, not ERD: no verified pre-cue baseline is reconstructed.

Use a fixed 21 × 22 Helmert basis from `scipy.linalg.helmert(22,full=False)` to
remove the CAR null direction. Center each epoch over time, calculate unbiased
sample covariance, normalize its trace, then shrink with
`0.9*C + 0.1*I/21`. The fixed 0.1 identity shrinkage is not tuned. Fit an
affine-invariant Riemann mean using source train only: arithmetic initializer,
unit step, maximum 100 iterations, tolerance 1e-10. Record convergence. Validation,
support and query covariances may only be measured against that frozen reference.
Fit default StandardScaler and full-SVD PCA with four components, no whitening,
on source-train power features only; all other data only transform. Fixed
left-versus-right class descriptions in these coordinates are descriptive and
never choose features or parameters.

Predeclared diagnostics compare all 22 channels with C3/Cz/C4 power. A separate
count-matched diagnostic keeps the first chronological `min(n_left,n_right)`
included events of each class within each subject/session/role; primary data and
decoder fits remain unchanged. Selection uses acquisition time then source
start sample, has no replacements and does not use signal values or results.
Report QC flags and fixed covariance regularization; do not claim an unavailable
native-CPz reconstruction. No diagnostic is promoted post hoc to the primary test.

## Statistics and execution gate

The primary endpoint is each participant's mean balanced accuracy over its five
target sessions. The primary contrast is refit CSP/LDA minus source-only on the
same target queries, evaluated in the twelve fixed final-test identities.
Use 10,000 participant-resampled paired bootstrap replicates, seed 42, with a
95% percentile interval. Sessions/trials are not independent statistical units.
Report individual and session results as well as the participant mean contrast.
Other contrasts and feature/drift associations are descriptive, without a
confirmatory multiplicity-adjusted claim. Development results are reported apart
from final-test results and do not change this frozen setting.

Preparation performs no decoder fit or performance calculation. Formal execution
requires an independent receipt bound to the exact config, this protocol, source
gate receipt and split manifest. The root reviewer owns that receipt. This
internal review gate does not require another user authorization for the already
authorized CPU baseline. Record source snapshot hashes, runtime versions and
actual CPU execution receipts; preserve all historical and failed outputs.

## Declared source-quality qualifications

The participant table contains invalid `age=2020`; no age covariate is used.
GR/PAR group mapping is unresolved and is not inferred from numbering or scores.
Biological identity independence across datasets is not verified. Original
online feedback conditions do not create a verified hit/miss or retention
endpoint here. Derivative timestamps and CPz metadata are retained with their
provenance limits. No expert artifact certification is claimed. These limitations
qualify the defined offline decoding and descriptive geometry endpoints; they
cannot be resolved by stronger model performance.
