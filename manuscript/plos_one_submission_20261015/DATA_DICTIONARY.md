# S1 Data: data dictionary and provenance

This author-review supporting-data bundle contains exact saved text predictions,
existing fixed QC metadata, original statistical summaries, saved training curves,
and the plotted observations. It contains no EEG samples, checkpoint weights,
authorizations, credentials, source-paper copies, dependency wheels or binary
model archives. It is not an independent dataset or a new scientific experiment.

## Provenance and rights status

The original public dataset is NEMAR **nm000177/v1.0.5**, version DOI
https://doi.org/10.82901/nemar.nm000177.v1.0.5, released under **CC BY 4.0**.
The original study is Kumar et al., *Transfer learning promotes acquisition of
individual BCI skills*, DOI https://doi.org/10.1093/pnasnexus/pgae076, with its
correction DOI https://doi.org/10.1093/pnasnexus/pgae137. Dataset/source-study
rights and attribution remain applicable. This bundle comprises derived metadata,
predictions and statistical tables; no new human participants were recruited.

The proposed license for newly authored code is **MIT, pending author approval**.
This statement is a proposal, not an active MIT grant or a replacement for third-
party licenses. Proposed publication of new derived tables under CC BY 4.0 is
likewise part of the author-review release plan; source-data CC BY 4.0 rights
remain as originally granted. No software LICENSE is silently applied here.

The reference source checkout is `370bc94b7af3c926adeb02c38e430a53e4a64135`.
The new postprocessor, outputs and package are as-yet uncommitted at bundle
creation; the manifest records their **actual byte hashes**, not a fictional
published commit. The enclosing final Git submission record will bind them.

## Units, independent units and missing values

- `subject` is a dataset release identity (`sub-1` ... `sub-18`), not proof of
  independently established biological identity. There are 18 identities, not
  54 participants. Fifty-four EEGNet fits are 18 identities × three fixed seeds.
- Source session is `ses-0`; target sessions are `ses-1` ... `ses-5`, chronological
  within identity. Runs retain their original whole-run assignment. `trial_id`
  is the exact stable `sub-N/ses-N/run-N/row-N` identity.
- `label`/`prediction` in saved prediction CSVs are **left=0, right=1**. Metadata
  JSON labels retain `left_hand`/`right_hand`. Metadata `source_row` is the
  original exported event row, not a new trial index.
- `BA`, `balanced_accuracy`, `mean_*BA`, recalls, differences and CI endpoints
  are **fractions on the 0–1 accuracy scale**. Multiply by 100 for percentage
  accuracy or percentage-point differences. A negative difference is retained.
  No clinical/individual-harm threshold is defined by its sign.
- `raw_peak_to_peak_max_volts` is in **volts**, from the original raw-window
  fixed QC ledger. `qc_peak_to_peak_over_250uv` is the original Boolean
  maximum-channel peak-to-peak **>0.00025 V** flag. This is not expert artifact
  certification; unflagged does not mean artifact-free.
- `n_*`, class counts, confusion cells, epochs and optimizer steps are counts.
  Rows after seed averaging retain **unique trial counts**, not threefold counts.
  `epoch` starts at 1. Cross-entropy losses are dimensionless negative-log-
  likelihood losses from the original saved curves; no smoothing was applied.
- `seed` is one of 20261012/20261013/20261014 for EEGNet, or `cpu_fixed` for
  the CPU methods. `job_id` is a deterministic task identity, not a participant.
- `_bytes` fields are bytes; `*_sha256` fields are complete-file SHA256 hex.
  `source_file` is the release-relative provenance path, not bundled EEG.
- Empty CSV numeric fields and JSON `null` represent **undefined/missing**,
  never chance, zero or a deleted row. BA needs both true classes. Low class
  counts (<5/class) are explicitly flagged and retained.

## Cohorts, endpoints and eligibility

Development6 = sub-1,4,7,10,13,16; remaining12 = sub-2,3,5,6,8,9,11,12,14,15,17,18.
`final_test` in original tables is the historical remaining-cohort name; prior
exposure makes subsequent analyses exploratory. `all18*` is secondary descriptive.
Participants, not trials/sessions/seeds, are the bootstrap independent unit.

The original primary endpoint remains full CSP/LDA refit minus frozen CSP/LDA
on the equal-five-target-session participant mean, remaining12. Full minus
LDA-only remains secondary. The query-QC sensitivity was added **after seeing
original results**; its rule is recorded in `POST_OBSERVATION_PROTOCOL.md`.

Original metadata include 7,200 events, of which 7,156 are complete windows and
44 retain their historical partial exclusions. Query metadata retain all 4,320
query-role identities: 4,290 complete included queries and 30 historical partial
query exclusions. The public prediction table has 25,740 rows = 4,290 × six
method/seed outputs (three CPU methods + three EEGNet seeds).

For each method/seed, BA is computed per session and subgroup, then all three
EEGNet seed BAs are averaged within participant/session. The target endpoint
requires **all five** target-session BAs; it never averages fewer sessions.
Under the unflagged sensitivity sub-8 lacks two target sessions and sub-12 lacks
all five true-class-complete target sessions. Their endpoint rows remain, but
only 10/12 remaining participants are eligible. Sub-8 source-query BA is also
undefined. Every summary provides its own expected/eligible denominator and IDs.
Pooled-query endpoints are additional descriptive endpoints with different
session weighting. Do not substitute them for the five-session estimand.

`refit_minus_frozen` and `refit_minus_lda_only` use positive full-minus-comparator
orientation. `unflagged_minus_all_difference` compares contrasts in **the same**
eligible participants; a 12-person mean versus a 10-person mean is not itself a
matched QC change. Participant percentile bootstraps use 10,000 draws, seed 42,
lexicographic ID ordering. No new hypothesis test/p value is provided.

## Bundle layout

- `inputs/`: compact 7,200-event metadata; all 25,740 saved predictions; exact
  original configuration and original 72 participant endpoints; source hashes
  in `public_input_provenance.json`. Portable reproduction needs no private files.
- `results/qc/`: all 13 computed CSV tables, preserving every class count,
  undefined group, participant eligibility, paired difference and influence row.
- `results/training/`: six saved-result CSVs; 2,871 epoch-curve rows and 54 fit
  summaries, all seeds and source/target endpoints retained. These are logs of
  already completed fits, not new training.
- `results/original_comparison/`: original method/cohort, participant/session,
  seed/session and descriptive cross-family differences. Architecture comparisons
  have unequal label/validation/compute budgets; they are not fair rankings.
- `results/original_cpu/participant_bootstrap_summary.json`: exact original CPU
  summary, including the original primary and secondary contrast intervals and
  all participant values. The original primary was not redefined by QC.
- `figures/`: four exact plotted-data CSVs for the four final figures. Fig 1
  includes participant points and saved cohort means/intervals; Fig 2 includes
  original paired differences and the saved interval; Fig 3 contains signed
  support-half contrasts; Fig 4 retains participant × target-session contrasts.
- `code/`, `tests/`: portable text-only postprocessor and 15 synthetic tests.
- `MANIFEST.json`: payload SHA256/length/source-path index; self excluded to avoid
  circular hashing. External `S1_Data_manifest.json` additionally hashes the ZIP
  and every actual member, and records real CRC and full-member SHA verification.

The compact data and summaries do not remove potential artifacts from historical
fitting data, establish continuous imagery over the fixed window, validate any
new gate or prove clinical benefit/human skill retention. Zero-count or absent-
class groups cannot be interpreted as successful classification.

## CSV tables and exact columns

### `inputs/original_participant_endpoints.csv` — 72 data rows

`subject`, `cohort`, `method`, `source_query_BA`, `target_five_session_mean_BA`, `source_query_trials`, `target_query_trials`, `target_class_collapsed_seed_sessions`, `source_class_collapsed_seed_sessions`, `seeds_included`.

### `inputs/saved_predictions.csv` — 25,740 data rows

`subject`, `cohort`, `session`, `run`, `role`, `trial_id`, `label`, `prediction`, `qc_peak_to_peak_over_250uv`, `method`, `seed`.

### `results/qc/all_role_qc_counts.csv` — 540 data rows

`subject`, `session`, `role`, `n_events`, `n_complete`, `n_incomplete`, `n_flagged_complete`, `n_unflagged_complete`.

### `results/qc/cohort_method_sensitivity_summary.csv` — 96 data rows

`cohort`, `method`, `subset`, `endpoint`, `n_expected_participants`, `n_eligible_participants`, `eligible_subjects`, `ineligible_subjects`, `mean`, `ci95_low`, `ci95_high`, `bootstrap_draws`, `bootstrap_seed`.

### `results/qc/cohort_paired_contrasts.csv` — 12 data rows

`cohort`, `contrast`, `subset`, `n_expected_participants`, `n_eligible_participants`, `eligible_subjects`, `ineligible_subjects`, `mean`, `ci95_low`, `ci95_high`, `participants_positive`, `participants_zero`, `participants_negative`.

### `results/qc/joined_saved_predictions_qc.csv` — 25,740 data rows

`subject`, `cohort`, `session`, `run`, `role`, `trial_id`, `label`, `prediction`, `qc_peak_to_peak_over_250uv`, `method`, `seed`.

### `results/qc/leave_one_participant_out_influence.csv` — 136 data rows

`cohort`, `contrast`, `subset`, `omitted_subject`, `omitted_subject_difference`, `n_retained`, `full_eligible_mean`, `leave_one_out_mean`, `change_in_mean_when_omitted`.

### `results/qc/paired_cross_subset_summary.csv` — 6 data rows

`cohort`, `contrast`, `n_expected_participants`, `n_eligible_participants`, `eligible_subjects`, `ineligible_subjects`, `mean`, `ci95_low`, `ci95_high`.

### `results/qc/paired_participant_contrasts.csv` — 72 data rows

`subject`, `cohort`, `subset`, `contrast`, `paired_endpoint_defined`, `mean_difference`, `undefined_sessions`.

### `results/qc/paired_session_contrasts.csv` — 432 data rows

`subject`, `cohort`, `subset`, `contrast`, `session`, `n_left`, `n_right`, `paired_BA_defined`, `paired_difference`.

### `results/qc/participant_cross_subset_changes.csv` — 72 data rows

`cohort`, `contrast`, `subject`, `paired_across_subsets_defined`, `all_included_difference`, `unflagged_difference`, `unflagged_minus_all_difference`.

### `results/qc/participant_endpoints.csv` — 144 data rows

`subject`, `cohort`, `method`, `subset`, `target_five_session_mean_BA`, `target_endpoint_defined`, `target_undefined_sessions`, `n_defined_target_sessions`, `target_query_trials`, `target_left`, `target_right`, `low_count_target_sessions`, `source_query_BA`, `pooled_all_query_BA`, `pooled_target_query_BA`.

### `results/qc/per_participant_session_metrics.csv` — 1,152 data rows

`subject`, `cohort`, `method`, `subset`, `session`, `n_query`, `n_left`, `n_right`, `balanced_accuracy`, `BA_defined`, `undefined_reason`, `fewer_than_5_per_class`, `seeds_included`, `class_collapsed_seed_groups`.

### `results/qc/per_seed_session_and_pooled_metrics.csv` — 1,728 data rows

`subject`, `cohort`, `method`, `seed`, `subset`, `session`, `n_query`, `n_left`, `n_right`, `predicted_left`, `predicted_right`, `confusion_00`, `confusion_01`, `confusion_10`, `confusion_11`, `balanced_accuracy`, `BA_defined`, `undefined_reason`, `fewer_than_5_per_class`, `class_collapse`.

### `results/qc/query_identity_qc_ledger.csv` — 4,320 data rows

`trial_id`, `subject`, `cohort`, `session`, `run`, `role`, `label`, `included`, `exclusion_reason`, `raw_peak_to_peak_max_volts`, `qc_peak_to_peak_over_250uv`.

### `results/training/all_saved_epoch_curves.csv` — 2,871 data rows

`subject`, `cohort`, `seed`, `job_id`, `epoch`, `source_train_loss`, `source_validation_loss`.

### `results/training/cohort_per_seed_query.csv` — 9 data rows

`cohort`, `seed`, `participants`, `mean_source_query_BA`, `mean_target_query_BA`.

### `results/training/cohort_training_review.csv` — 3 data rows

`cohort`, `participants`, `source_models`, `epochs`, `optimizer_steps`, `selected_epoch1_fits`, `reached_epoch100_fits`, `median_epochs`, `median_selected_epoch`, `train_CE_last_lower_than_first_fits`, `validation_CE_last_higher_than_first_fits`, `selected_validation_CE_at_or_above_log2_fits`, `median_train_CE_first`, `median_train_CE_last`, `median_validation_CE_first`, `median_validation_CE_selected`, `median_validation_CE_last`, `selected_validation_class_collapse_fits`, `mean_selected_validation_BA_descriptive_only`, `source_query_collapsed_seed_sessions`, `target_query_collapsed_seed_sessions`, `mean_participant_source_query_BA`, `mean_participant_target_query_BA`, `mean_participant_target_minus_source_BA`, `mean_participant_target_seed_range`, `maximum_participant_target_seed_range`.

### `results/training/per_fit_training_review.csv` — 54 data rows

`subject`, `cohort`, `seed`, `job_id`, `epochs`, `optimizer_steps`, `selected_epoch`, `stopping_reason`, `train_CE_epoch1`, `train_CE_selected_epoch`, `train_CE_last_epoch`, `validation_CE_epoch1`, `validation_CE_selected_epoch`, `validation_CE_last_epoch`, `train_CE_last_minus_first`, `validation_CE_last_minus_first`, `validation_CE_first_minus_selected`, `validation_BA_selected_checkpoint`, `validation_class_collapse`, `training_log_bytes`, `source_query_BA`, `target_five_session_mean_query_BA`, `target_minus_source_BA`, `source_collapsed_seed_sessions`, `target_collapsed_seed_sessions`.

### `results/training/per_participant_source_target_query.csv` — 18 data rows

`subject`, `cohort`, `seeds`, `source_query_BA`, `target_five_session_mean_query_BA`, `target_mean_BA_seed_range`, `source_BA_seed_range`, `target_minus_source_BA`.

### `results/training/per_seed_source_target_query.csv` — 54 data rows

`subject`, `cohort`, `seed`, `job_id`, `source_query_BA`, `target_five_session_mean_query_BA`, `target_minus_source_BA`, `source_collapsed_seed_sessions`, `target_collapsed_seed_sessions`.

### `figures/Fig1_target_query_participants_source_data.csv` — 80 data rows

`record_type`, `cohort`, `subject`, `method`, `BA`, `ci95_low`, `ci95_high`.

### `figures/Fig2_cpu_primary_paired_changes_source_data.csv` — 13 data rows

`record_type`, `subject`, `difference_pp`, `ci95_low_pp`, `ci95_high_pp`.

### `figures/Fig3_csp_signed_support_halves_source_data.csv` — 30 data rows

`subject`, `session`, `first_half_margin_source_sd`, `second_half_margin_source_sd`, `sign_pattern`.

### `figures/Fig4_longitudinal_paired_changes_source_data.csv` — 180 data rows

`contrast`, `subject`, `cohort`, `session`, `n_unique_query_trials`, `full_refit_BA`, `comparator_BA`, `difference_pp`.

### `results/original_comparison/cohort_method_endpoint_summary.csv` — 24 data rows

`cohort`, `n_participants`, `method`, `endpoint`, `mean_BA`, `median_BA`, `descriptive_ci95_low`, `descriptive_ci95_high`, `bootstrap_replicates`, `bootstrap_seed`, `inference`.

### `results/original_comparison/per_participant_endpoints.csv` — 72 data rows

`subject`, `cohort`, `method`, `source_query_BA`, `target_five_session_mean_BA`, `source_query_trials`, `target_query_trials`, `target_class_collapsed_seed_sessions`, `source_class_collapsed_seed_sessions`, `seeds_included`.

### `results/original_comparison/per_subject_session.csv` — 432 data rows

`subject`, `cohort`, `method`, `session`, `n_unique_query_trials`, `balanced_accuracy`, `seeds_included`, `class_collapsed_seed_sessions`, `source_train_labels`, `validation_labels_used_for_checkpoint_selection`, `target_support_labels`.

### `results/original_comparison/eegnet_per_seed_session.csv` — 324 data rows

`subject`, `cohort`, `seed`, `session`, `balanced_accuracy`, `n_query_trials`, `class_collapse`.

### `results/original_comparison/per_participant_descriptive_differences.csv` — 108 data rows

`subject`, `contrast`, `endpoint`, `paired_difference`.

### `results/original_comparison/descriptive_eegnet_minus_cpu.csv` — 18 data rows

`cohort`, `n_participants`, `contrast`, `endpoint`, `mean_paired_difference`, `median_paired_difference`, `participants_positive`, `participants_zero`, `participants_negative`, `CI_or_p_value`, `budget_comparability`.

