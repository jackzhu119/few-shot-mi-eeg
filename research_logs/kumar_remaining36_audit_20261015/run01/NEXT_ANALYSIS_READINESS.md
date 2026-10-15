# Saved-model analysis readiness after remaining36 reception

This is an evidence update, not a scientific protocol change or authorization
for query evaluation. The original `EEGNET_TRAINING_PLAN.md`, checkpoint-reuse
proposal and all historical configurations retain their original bytes and
status fields. Their historical statements that 36 source fits were pending
are superseded by the actual results received in this audit directory.

## Completed source fitting and current acceptance boundary

All 54 prespecified participant/seed models now have recorded source fits:
18 accepted development models plus these 36 remaining-cohort models. No old
model was fitted again. This batch contributes 1844 epochs and 5532 optimizer
steps; the combined historical totals are 2871 epochs and 8613 steps. These are
54 model instances across 18 published participant identities, not 54
independent participants. Every fit uses the same source40/source-validation20
split. Query rows remain zero in this batch and in this audit.

The accepted18 ledger is unchanged. The 36 new identities must remain outside
accepted status until dot actually reads the fixed audit and full R2 receipt
and confirms their exact bytes/hashes. Training, off-Pod export, independent
audit, full-GET verification and parent acceptance are separate records.
The supplementary final dispatch resolves the earlier handoff's pending-exit
field; the old handoff is preserved rather than rewritten.

## Analyses possible from already saved results

The companion `independent_saved_prediction_summary.json` retains all three
seeds and describes saved source-validation predictions. It averages seeds
within participant before group summaries. The validation set selected each
checkpoint epoch, so these numbers are descriptive selection-set performance,
not query performance or independent generalization. Trial rows and seeds do
not inflate the independent sample size. No best seed, threshold, sign flip,
adaptive rule or extra fit is selected from these observations.

The frozen audit verifies checkpoint hashes/tensors/state, source identities,
epoch selection and saved-logit CE. It checks the original recorded Torch
checkpoint replay and independently recomputes CE from saved logits. It does
not independently run EEG through the checkpoint. That distinction must remain
in any manuscript and later evaluation record.

## Minimal next protocol boundary

After actual parent acceptance, bind the original 54 archives, checkpoints,
normalization and BN states in a versioned reuse inventory. Keep the accepted18
ledger unchanged as historical evidence; any later combined inventory must
reference its actual acknowledgements and the separate remaining36 acceptance.
Do not call generic `formal_train`, which would refit existing models.

The existing `scripts/evaluate_kumar_checkpoint_reuse.py` provides a tested
read-only source-validation kernel with parameter/BN/normalization and file
state checks. Its current CLI is metadata-only and its identity gate expects a
matched accepted ledger and plan. It is not a delivered end-to-end query
adapter and must not be represented as one. A later query-only execution
delivery must separately freeze the exact accepted checkpoint inventory,
query-only input manifest, source-only preprocessing/normalization reuse,
state-unchanged evaluator, endpoint and serial bounded operation. This round
creates no such execution authorization or query input download.

Keep the original source-only EEGNet baseline: no target-support recalibration,
optimizer, BN update, new normalization fit or model search. For a later
authorized evaluation, preserve all seeds, average within participant/session,
then average the five target sessions within participant. The established
10000-draw seed42 participant bootstrap and all failures/class collapses remain
part of reporting. The primary CPU contrasts are not rerun or replaced.

The completed CSP signed-score run02 evidence is available at fixed
`9f7bc102dec264e10688765636596c336e69becc` and
`research_logs/kumar_csp_signed_score_execution_20261015/run02/`.
It found mixed signed directions and split-half reliability, including both
negative contrasts producing a positive product. It does not establish a
nested matched-budget policy benefit or justify inventing a gate from source
BA. No additional strategy is selected here. Analyses on the already exposed
cohort remain exploratory; offline decoding cannot demonstrate human learning,
skill retention or clinical effectiveness.

## Immediate instruction

Dot should read this fixed commit's `parent_acknowledgement_request.json`, all
36 model audits, dispatch audit, object inventory and the complete UTF-8 R2
receipt, compare them with the off-Pod original bytes, and issue an actual
confirmation for the exact 36 jobs if satisfied. No new fit or query command is
released by this handoff. The final completed controller must not be resumed.
