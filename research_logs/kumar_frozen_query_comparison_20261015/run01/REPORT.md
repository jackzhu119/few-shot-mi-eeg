# Saved-result comparison after actual query acceptance

This is a recomputation from existing prediction/metadata text only. No raw EEG
array, checkpoint tensor, model forward, fit, new threshold or scientific test
was executed. All54 frozen query results received the actual09:49:05UTC parent
ACK; source accepted54 remains unchanged.

## Exact common sample and aggregation

The joined data preserve4320 recorded query identities,4290 included queries
(source360, target3930), and the same30 partial exclusions. Each CPU method and
each EEGNet seed uses these exact trial IDs/labels/session/run/role identities.
CPU and EEGNet each contribute12870 saved prediction rows; none are dropped.
Checks also bind original input numerical hashes and source/support fitting IDs.
The saved-result comparison completed30324 checks. Four synthetic join checks
cover one valid join and duplicate, missing and mismatched-label rejection.

All three EEGNet seed scores are averaged within participant/session; all five
target sessions are then averaged within participant. Participants remain the
independent units. Intervals below use the frozen10000 participant resamples,
seed42 convention. Development and remaining cohorts are separate; all18 is a
secondary exploratory summary. No new p-value or EEGNet paired-contrast CI is
computed. The original CPU primary contrast is reproduced unchanged.

## Target-query BA (percent)

All brackets are descriptive95% participant-bootstrap intervals. These rows
share query samples, but are not an equal-information-budget architecture ranking.

| Cohort | Frozen CSP/LDA | Frozen CSP + LDA recalibration | CSP/LDA refit | Frozen EEGNet |
| --- | ---: | ---: | ---: | ---: |
| development6 | 59.97 [57.34, 63.70] | 64.37 [56.97, 71.75] | 63.22 [58.36, 67.40] | 52.31 [48.43, 57.36] |
| remaining12 | 57.94 [52.65, 63.84] | 59.89 [54.30, 65.68] | 65.36 [59.81, 70.90] | 51.58 [49.08, 54.51] |
| all18_secondary_exploratory | 58.62 [54.88, 62.68] | 61.38 [56.79, 66.17] | 64.65 [60.53, 68.71] | 51.82 [49.59, 54.36] |

The frozen remaining12 CPU primary contrast, CSP/LDA refit minus source-only,
is +7.421355percentage points [2.487555,12.476616];9 participants improve and3
worsen. The existing matched-label CPU secondary contrast, full refit minus
LDA-only recalibration, is +5.47points [2.17,8.91]. Its update scope and compute
are different despite identical labeled fitting IDs.

EEGNet is close to chance at51.58% [49.08,54.51] on the remaining12. Its
descriptive paired differences from frozenCSP, LDA recalibration and full refit
are respectively−6.36,−8.31 and−13.78points; these cannot isolate architecture
or adaptation effects. No seeds or unfavorable participants were discarded.
EEGNet retains16 collapsed seed/session outcomes (14target,2source); the CPU
frozen model retains3 target-session collapses, the updates0. Their denominators
differ, so raw collapse counts are not a matched statistical contrast.

## Budget interpretation

Every pipeline uses the same40 source TRAIN identities. EEGNet additionally
uses20 source-validation labels for checkpoint epoch selection, whereas CPU
validation does not select or fit its models. Both frozen methods consume0
target support. The two CPU update methods consume the same current19/20
support labels (14 sessions with19 and76 with20), never past/future support.
Thus only the two update methods have exactly matched labeled fitting IDs;
the original refit-vs-frozen contrast deliberately adds current support.
See comparison_budget_status.csv for each comparison's explicit boundary.

## Artifacts, corrections and interpretation

The exact executed command was:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B research_logs/kumar_frozen_query_comparison_20261015/run01/compare_saved_predictions.py
```

Its outputs use exclusive creation and must not be overwritten. The script's
full SHA and210 source-file byte bindings are in comparison_receipt.json.
Per-participant, per-session and all-seed tables preserve exact precision.
The original CPU frozen summary and source acceptance records are unchanged.
An independent reader validates the new tables separately; see
independent_comparison_validation.json.

The first saved-text reader encountered a missing processed hash on excluded
partial windows. reader_correction_run01.json preserves that failure and the
explicit included-hash/excluded-no-hash schema correction; no exclusion, input
or scientific run changed. Two E702 formatting findings in the immutable
executed artifact are retained and recorded in validation.json; scoped Ruff
with those style findings excluded passed. This is not an assertion that the
unmodified executed script passed strict all-rule lint.

These results are exploratory after prior test exposure. Near-chance neural
performance, variable CPU recalibration benefit and mixed signed-score
reliability do not validate a task-aware gate or human skill retention. No
remaining frozen source fit or EEGNet update operator is waiting to execute.
The factual English draft is
../../../manuscript/kumar_longitudinal_decoding_working_draft_20261015.md.
