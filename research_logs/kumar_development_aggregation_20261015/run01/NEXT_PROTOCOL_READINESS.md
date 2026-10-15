# Readiness after accepting all 18 development fits

The accepted ledger is fixed at `92cd2434b0ac8c3b16a6fe8ce163ba6328432094`.
Development execution, independent audit, private R2 full-GET verification and
actual parent acknowledgement are complete. All six development participants
and all three seeds are included in the saved-result summary. No development
fit remains to run. This round schedules no additional experiment.

The result is scientifically limited: mean source-validation BA is 53.06%,
three participants have a 20-percentage-point seed range, and one fit collapses
to a single predicted class. Source-validation CE selected the checkpoint epoch,
so this is a descriptive development finding. The 18 fits are six independent
participants, and the 360 saved prediction rows repeat 120 unique trials.
These results establish neither independent generalization nor a useful
task-aware adaptation gate. No seed, threshold, sign flip or revised model is
selected from this summary.

| Next gate | Current evidence and remaining requirement |
|---|---|
| Formal configuration freeze | The existing scientific config retains `ready_for_formal_training=false` and null formal digest fields. Protocol, cohort, preprocessing, seeds and epoch rule need a separately reviewed exact freeze before any formal query path opens. No such config is created here. |
| Reuse accepted checkpoints | The generic `formal_train` in `scripts/train_kumar_eegnet.py:509` would fit all participant/seed combinations again before reading query. It must not be used. Future evaluation needs a reviewed path that reuses the 18 accepted checkpoints, source normalization and BN state, with no refitting or state updates. |
| Remaining cohort and evaluation | The historical overall plan spans 18 participants × 3 seeds. The other 12 participants' 36 source fits and future query evaluation are not performed or released by this acceptance. Any later execution must use its frozen scope and budget under dot's scheduling. |
| Original task-aware gate | The frozen task-aware plan requires separate nested development participant/run validation, current-support-only information and matched label/update budgets. Always-frozen, always-update, fixed-mixture and covariance-gate controls remain required. Existing power/PCA/task-axis diagnostics and CSP reliability do not supply an established decision rule or adaptation benefit. |
| Interpretation | Later strategy work on the already inspected cohort remains exploratory. External confirmation needs a separately locked mapping and endpoint. Offline decoding cannot establish human skill retention or clinical efficacy. |
| Execution readiness | This round does not inspect live Pod state or revalidate hardware/runtime. Historical receipts remain observations of their actual runs; dot alone schedules future execution. |

The exact gates and their source-file hashes are recorded in
`next_frozen_protocol_readiness.json`. They follow the existing
`EEGNET_TRAINING_PLAN.md`, frozen task-aware plan and CSP reliability methods
review. The old negative power/PCA/motor-channel findings and later qualified
CSP findings remain unchanged. Query/formal flags, scientific configuration,
numerical threads, tolerance, budget, old failure evidence and original receipts
are preserved. This is a readiness check, not a new scientific protocol or an
execution authorization.
