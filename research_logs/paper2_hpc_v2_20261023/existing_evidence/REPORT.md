# Existing Paper 2 component evidence used to design HPC V2

This is a text-only, byte-identical snapshot of selected **already completed** component analyses from 2026-10-16. It adds their provenance and relevant results to the new HPC design record. No EEG, model/checkpoint, raw trial prediction file, credential or learned Ridge coefficient is included. No fit, query inference, bootstrap or new R2 GET was performed while making this snapshot. Existing source files were read and verified unchanged after copying.

The source is the portable component package under:

`/workspace/private_model_receipts/paper2-component-followup-20261016/data_package_portable_check/run02/extracted/component/repository/`

The reference main revision used at the start of this work was `04d21b06a7acc225391958556220e7cdb2bcffbd`. These completed component artifacts were available in the portable package but were not all integrated in that historical main checkout. The older untracked revision draft still described phase/gain as pending; that description is superseded by the preserved reports here. This snapshot does not overwrite the submitted manuscript, original results or acceptance ledger.

## Directly checked findings

| Saved result | Participant-level result | Interpretation for V2 |
|---|---|---|
| Budget: remaining12, full support, EA − full refit | **+5.30 pp [2.81, 8.26]**; EA 70.66%, full 65.36% | EA is a strong control; the new principal contrast is EA plus empirical anchoring versus EA. |
| Budget: full − LDA at 4/8/12 labels | **−0.08 [−2.95, 2.54] / +1.18 [−1.35, 3.91] / +2.90 [−1.12, 7.02] pp** | All three pointwise intervals include zero. This motivates examining update strength, not declaring full refitting uniformly best. |
| Phase: conditional remaining cohort n=9, full − frozen | Cue 5 s **+2.06 [−3.73, 8.17] pp**; task-start 2 s **+3.21 [0.08, 6.56] pp** | The gain change is **+1.15 [−5.55, 7.22] pp**. It does not establish that phase differences explain the original effect. |
| Gain selector: remaining12, Ridge − full | **−4.47 [−7.94, −1.32] pp** | The completed saved results do not support a superior task-aware selector. |

`SOURCE_HASH_MANIFEST.json` preserves the exact existing CSV decimal strings behind each displayed value, the row-check outcome, original source path, byte count and SHA256 of every copied file. Values above were obtained by locating unique existing table rows and formatting their stored values; no new statistical estimator was run.

## Historical statistical and execution distinctions

- These component results are **post-exposure exploratory**, with fixed development6/remaining12 membership. CSV labels such as `final_test` are preserved historical field values, not claims that these outcomes remain unseen.
- Full support means **19 labels in 14 of 90 sessions and 20 in 76**. Budget endpoints average all five target-session BAs equally within participant. The old full-support main effect **+7.42 [2.49, 12.48] pp** and secondary **+5.47 [2.17, 8.91] pp** keep their original intervals; later exploratory bootstrap tables have slightly different intervals and do not replace them.
- Phase eligibility differs from the original 12-person analysis. The copied report retains n=9 conditional and n=8 metadata-complete scopes, 96 undefined cells, the five-query-trial sub-15/ses-5 cell, incomplete mapping and joint anchor/window/filter-edge changes. An isolated positive window interval is not evidence of a between-window difference.
- The gain launcher **failed with exit 1** after `KeyError: VmRSS`; the worker exit was not independently recorded. Its complete saved result files passed the previously recorded integrity/arithmetic audit. This snapshot preserves both facts and does not convert the operation into a clean success, accepted run or new attempt.
- No new gate is authorized or validated by these saved results. Old 54 source weights and predictions remain historical; the incompatible new CompactEEGNet version uses explicitly new source fits.

## File map

- `budget_cohort_paired_gains.csv`: all saved cohort/budget contrasts and intervals.
- `budget_cohort_means.csv`: all saved method/cohort/budget means and intervals.
- `budget_participant_endpoints.csv`: all participant-level budget/method endpoints.
- `budget_original_RESULTS_REVIEW.md`: original evidence/identity review, counts and limitations.
- `phase_cohort_paired_contrasts.csv`: saved cohort/window contrasts, scope and participant lists.
- `phase_original_REPORT.md`: original phase coverage, missingness and interpretation.
- `gain_policy_summary.csv`: all saved policy-level means, paired gains and downside summaries.
- `gain_original_failed_launcher_REPORT.md`: unchanged original gain integrity/arithmetic audit and failure status.

The copied reports may contain historical reproduction commands and paths. They are provenance, not instructions to rerun old operations. The new HPC executable scope is described by the separate V2 delivery. Data tables and narrative here are original derived research outputs; the project's existing license scope applies, without relicensing third-party raw EEG.
