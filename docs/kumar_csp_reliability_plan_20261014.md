# Supervised CSP task-measurement diagnosis

Frozen before this computation on 2026-10-14 (Asia/Shanghai), after seeing the
development-only44/PCA4/motor6 power measurements and historical baseline results.
This new measurement choice is exploratory, not a retrospective primary hypothesis.
The six fixed development IDs are1,4,7,10,13,16. No final-cohort/query data enter
the input or execution; no adaptation gate is trained or threshold selected.
This experiment asks whether supervision yields a more usable task coordinate,
not whether a new strategy improves final query performance.

## Restricted epochs and source model provenance

Use the metadata already physically restricted to source_train and target_support.
Read only those allowed5-second windows in their42 source EDFs (seven per ID).
Recheck official whole-file size/checksum, pinned raw-file SHA, raw-window SHA,
and frozen float32 processed-window SHA. Use the original Kumar epoch-local CAR,
8–30 Hz filtering/resampling to22×640 at128Hz in volts. Preserve all QC flags and
19/20 target support budgets; no artifact exclusion, padding or replacement.
No source validation/query or target query window is loaded. Preserve historical
adapters, source files and model outputs; write a new immutable epoch projection.

Original source40 CSP/LDA arrays come from the already closed, SHA-verified
baseline source_before.npz. Match source_after arrays, parameter digest and
source-fit IDs/X-y hash to the executed baseline. The same4-component Ledoit-Wolf
CSP(log average-power,norm_trace=False) and lsqr auto-shrinkage LDA are used in
new TRAIN20 run probes. These probes do not replace any original baseline.

## Source run transfer and exact phase controls

Fit CSP and LDA on run0's20 source_train trials, evaluate run1's20, then reverse.
No40-source model or all-run transform is used to fit either fold. CSP is
label-dependent: every training label rotation requires a new CSP and LDA fit.
Enumerate the exact20×20 joint circular label shifts shared across both folds and
all six IDs. Cache20 models per fold, one per TRAIN label rotation; predict the
unchanged holdout epochs once per model and score all20 holdout label rotations.
This is identical to refitting the same TRAIN model for every joint shift, with
6×2×20=240 pipeline fits (240 CSP and240 LDA), including12 observed fits.
Save each fit's actual labels, identities, model state, predictions and scores;
save all2400 participant/joint-shift twofold BA values and failure denominators.

Report both observed folds and their participant mean, class recalls/collapse,
all phase controls and unique label-assignment counts. Controls are descriptive
phase-alignment sensitivities; circular stationarity, wraparound and cue-order
confounding remain unverified. Tail fractions are not formal p-values and do not
prove neural specificity. Preserve failed/singular fits as explicit unavailable
values; no participant or poor score is silently removed.

## Current support task directions and signed decision margins

Transform source40/current support using its EXISTING frozen source40 filters.
Compute four features as log of average squared projected amplitude. Fit a
four-feature StandardScaler on source40 only for vector-direction diagnosis.
The source right-minus-left standardized mean direction remains fixed.
Chronologically split each support class into first floor(n/2) and remainder.
Report source/support and half-to-half4D cosine, plus each half's signed
projection contrast scaled by SOURCE40 task-axis projection SD(ddof1).

Also use the EXISTING source LDA score s=feature·w+b, with classes verified0=left,
1=right. Scale only by SOURCE40 score SD(ddof1); retain its original intercept
and do not center/scale on support. For each half report
0.5[mean(s|right)−mean(s|left)]/sourceSD, mean(s|right)/sourceSD,
−mean(s|left)/sourceSD, score mean/bias, prediction ratio, class recalls and BA.
The balanced contrast can cancel an intercept and hide class-collapse; both
individual class margins and recalls therefore remain necessary. A positive
split-half cosine or half-contrast product can coexist with reversed source
orientation and is not a pass criterion. Support scores are calibration-pool
diagnoses, not independent final-query adaptation performance.

Enumerate every19/20 current-support cyclic label shift with recomputed classwise
halves, and fixed-original-half sensitivity. Reuse the same source axes/scores;
never fit a new decoder on support in this diagnostic. Keep single-class and
zero-axis/zero-SD cases, attempted/valid/invalid denominators and unique rotations.
Do not infer biological independence or absence of task information from a null.

## Aggregation and decision

Average two source folds and five support sessions within each ID first. The
independent statistical unit is six published IDs; mean estimates/percentile95%
intervals use10000 participant bootstrap draws, seed42. Report all individuals,
not trial/session-as-independent intervals. Existing source audits do not prove
biological ID independence or expert artifact-free MI. The already seen final
baseline scores do not become blind because this diagnostic uses development IDs.

There is no automatic pass threshold or evidence-selected feature winner.
If a coordinate is promising, first freeze a separate nested-development,
matched-label-budget strategy comparison and evaluate benefit/harms/update costs.
Reliable measurement alone does not prove adaptation benefit. If unstable,
preserve the diagnosis and consider another justified measurement protocol.
No formal EEGNet training, GPU purchase, online-human dependency or paper release
is introduced. Continue the existing MIND V4 download independently.
