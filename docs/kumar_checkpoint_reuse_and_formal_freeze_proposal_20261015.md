# Checkpoint reuse and separate formal-freeze proposal

This preparation follows `EEGNET_TRAINING_PLAN.md`, the original Kumar protocol,
the accepted 18 development fits and the latest task-measurement plans. It does
not authorize a real checkpoint forward pass, another fit, query access or Pod
operation. The proposal is
`configs/kumar_eegnet_formal_freeze_proposal_20261015.json`; its execution
permissions are all false. A proposal checksum fixes reviewable bytes, not a
scientific pass or a parent acknowledgement.

## Minimal implemented path

`scripts/evaluate_kumar_checkpoint_reuse.py` exposes a read-only CPU kernel.
It verifies an exact-hash ledger and plan, the selected job's actual parent
acknowledgement and original full-GET receipt, complete original archive bytes
and every manifest member. It binds the checkpoint, JSON sidecar, tensor-encoded
context, scientific configuration, source identities and frozen split before
constructing the official Braindecode EEGNet architecture.

`torch.load` uses `weights_only=True` and CPU mapping. The archived CUDA training
configuration is preserved; CPU is an explicit execution property of this
software kernel. It does not replace or rewrite checkpoint context. The handle
has no fitting or optimizer API. Parameters have gradients disabled, all modules
are in evaluation mode, and forward passes use `torch.inference_mode()`.
Channel statistics are restored from the checkpoint, never fitted again.

The evaluator accepts only the complete archived source-validation identity
sequence, frozen labels and per-trial processed numeric hashes. The hash rule is
the existing SHA256 of little-endian float32 C-order bytes, not a new transform.
Query, target-support and future-session metadata
are rejected before signal/label arrays are accessed. Real source replay is
closed by default and additionally requires a separately reviewed exact-hash
authorization binding the job, ledger, plan, split and zero-update scope. This
round creates no such authorization. The only forwards in its tests use
explicitly synthetic, untrained random-initialization fixtures. No optimizer,
fit or backward pass is needed even to construct those fixtures.

Real replay must reproduce the bound selected-epoch validation CE within the
unchanged absolute tolerance `1e-7`; CPU execution does not justify relaxing that
gate. Synthetic untrained fixtures explicitly mark this scientific comparison
as inapplicable. No accepted checkpoint is forward-evaluated here, so no real
CPU/GPU replay success is claimed. A future reviewed caller still has to verify
the original source files and epoch-local preprocessing before supplying arrays;
the kernel itself has no EEG reader.

Before and after evaluation, guards compare every parameter and buffer
(including BN), classes, normalization, bound metadata, gradient/evaluation
state, source archive and evidence-file bytes. Mutation causes failure without
restoring state or returning successful predictions. Input arrays are copied;
the loader/evaluator writes neither files nor accepted status. CPU constructor
initialization preserves caller RNG state and numerical thread settings.

Returned receipts identify the original accepted model/result key and say
`new_fit=false`, `optimizer_steps=0`, `query_rows_loaded=0` and
`formal_scientific_gate_passed=false`. Historical training history remains
historical. A future authorized replay would be a checkpoint verification,
not another trained model or another independent experiment.

The CLI is metadata-only; it has no real-data, fit or query execution mode.
This is not yet an end-to-end query evaluator. A query-specific adapter, input
scope and operational freeze require a separate reviewed delivery. In
particular, do not invoke `formal_train` in `scripts/train_kumar_eegnet.py`:
it would refit all 54 participant/seed combinations before evaluating queries.
That frozen historical file is unchanged.

## Exact identity and scope

| Item | Binding / permitted preparation |
|---|---|
| Accepted development models | 18, six participants × all three seeds; fixed ledger commit `92cd2434b0ac8c3b16a6fe8ce163ba6328432094` |
| Ledger SHA256 | `1ee1868b97e6ff7ea2e42327fe64337cafbb0f8ee6aff19cc24fba5265f9aaa9` |
| Unchanged checkpoint-training JSON | `configs/kumar_eegnet_gpu_development_20261014.json`, exact-byte SHA256 `14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d` |
| Canonical training identity | `91c361210f6fbefc06581541a6cac9a4ee551669d62f2137f90321c7e141bc4e`, sorted compact JSON with the existing self-digest field null |
| Split manifest | SHA256 `ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28` |
| Reuse inventory | `research_logs/kumar_checkpoint_reuse_preparation_20261015/accepted_checkpoint_inventory.json`; binds original archive/result key, checkpoint and state digests, sidecar, source identities and historical selection for all 18 |
| Future source-only proposal | sub-2/3/5/6/8/9/11/12/14/15/17/18, each seeds 20261012/13/14, in that order; exactly 36 proposed identities, currently zero authorized |
| Future source input proposal | 253 files / 196,740,994 bytes, including 36 EDF / 196,540,216 bytes; no query/support EEG or query-label files |

The new source-input proposal selects only ses-0 runs 0/1 for TRAIN and run 2
for validation. Its 217 metadata files include 72 acquisition-order scans.tsv,
60 from future sessions; these identity metadata do not authorize future EEG or
labels. The selector reproduces the existing six-development-participant
127-file scope exactly. No file in the new 253-file scope is downloaded or
signal-read here. The complete historical 360-EDF `formal_data_plan.json`
includes query EEG and must not be used as the source-only download scope.

Partial trials, epoch-local CAR/filter/resampling, channel order, units, class
mapping, normalization, architecture, stopping, seed order and argmax rule all
retain the existing scientific definitions. The proposal identifies the
immutable fit configuration instead of filling fields inside old checkpoint
context or relabelling accepted models as newly trained formal fits.

## Count budget and missing execution fields

Current authorized new compute is zero fits and zero real evaluation forwards.
The possible remaining source stage is bounded at 36 fits × 100 epochs,
at most three minibatches per epoch: 3,600 epochs and 10,800 optimizer steps.
The historical 54-fit count ceilings remain 5,400 epochs / 16,200 steps.
Already used 1,027 epochs / 3,081 steps belong to the accepted 18; unused
allowance is not permission to rerun them.

The previous per-fit 1,800-second limit, 30-second TERM grace, serial shared GPU
lock and zero automatic retries are constraints to retain in a future reviewed
operation. The old two-fit / 3,600-second chunks, 5-GiB disk floor, 16-MiB model
archive and 64-MiB export bounds are documented historical operation settings,
not an implemented new 36-fit contract. The old 19,800-second absolute deadline
belongs to a completed run and must never be reset or scaled into new permission.
The new total wall deadline and cost scope remain null; historical platform
rates are not current billing verification. No live runtime/disk is inspected.

The proposal lists the union of nine unresolved execution bindings:

1. Actual parent review receipt for the fixed delivery and exact scope.
2. Final separate operational configuration and detached exact-byte SHA256.
3. Its canonical self-digest, calculated with its own digest field null.
4. Reviewed source-only 36-fit entry and contract, excluding the accepted 18.
5. Full source-input bytes/identity/processed-data verification receipt.
6. Current runtime, software-lock, hardware and disk acceptance.
7. New absolute total wall deadline and explicit cost/resource scope.
8. Bounded off-Pod export, recovery, independent audit, R2 full-GET and real
   parent-acceptance contract, with no credential copying or unsupported API.
9. A separately reviewed query-specific checkpoint-reuse entry and input scope.

Their stage applicability is explicit in the proposal. The remaining 36 source
fits require items 1–8, without requiring a query adapter. Existing-18 source
replay requires items 1/2/3/6, its existing 127-file source provenance and the
kernel's exact-hash replay authorization; it does not require the remaining
253-file manifest or a new training entry. Query evaluation requires items
1/2/3/6/7/8/9, a separate query-input manifest and accepted models for its exact
cohort. The remaining 36 become an upstream condition only when that query
scope needs them. No stage is opened by this applicability table.

Before future execution, create new freeze artifacts binding the already known
protocol, split and unchanged training-identity digests. Keep the old scientific
and formal JSON false/null fields, old receipts and ledger untouched. Source
fitting and query evaluation require separate scope/approval bindings; parent
review of this preparation alone is not an execution receipt. Failure or
ambiguous claims stop the future queue and preserve evidence; no automatic retry
or deletion of an old claim is proposed.

## Scientific decision

The latest evidence review is
`docs/kumar_csp_source_score_readiness_20261015.md`. The older positive CSP
run-transfer result is not the latest complete signed-score phase-control
experiment. Matching execution evidence for the latter was not located in the
current checkout. No executed nested matched-budget policy comparison is
available. Therefore no new adaptive strategy, threshold or feature winner is
selected. The smallest policy decision is to reconcile immutable results for
the already frozen measurement stage or leave it pending, without fitting it
in this round. Source-only checkpoint reuse preparation can proceed separately.

Any later source-only EEGNet evaluation is a secondary baseline extension. It
does not overwrite the original CPU primary contrast. Keep all three seeds,
average within participant/session, then average the five target sessions per
participant; participants are the statistical units. The existing 10,000-draw,
seed-42 participant-bootstrap definition remains. Preserve every failure and
class collapse. Source validation selected the epoch and is descriptive only.
Later strategy work on the exposed cohort remains exploratory. Offline decoding
does not establish human learning, retention or clinical efficacy.

## Minimum next instructions for dot

On the reviewed fixed checkout, run only the metadata checker:

```bash
PYTHONPATH=src:scripts /workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/check_kumar_checkpoint_reuse_proposal.py
```

Its expected result is `proposal_valid_execution_closed`, accepted 18,
proposed 36, authorized 0, query false, and the nine missing bindings above.
It reads no checkpoint tensors or signal files. Dot should review the fixed
code, tests, proposal and reliability report, then record the next actual
scientific/operational decision with those exact hashes. Do not execute the old
development batch, generic formal trainer, uncommitted CSP diagnostic or any
new source fit/query command from this preparation. No such execution command
is supplied or authorized here.
