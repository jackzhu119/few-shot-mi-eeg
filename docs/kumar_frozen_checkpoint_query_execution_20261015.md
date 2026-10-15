# Accepted54 checkpoint-only query baseline: exact handoff

The implemented scientific scope is frozen in
`docs/kumar_frozen_checkpoint_query_protocol_20261015.md`, following
`EEGNET_TRAINING_PLAN.md` and `KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md`.
The current round implements and tests software only. No real checkpoint tensor
or query file is opened by preparation. This document supersedes the missing
query-adapter implementation boundary in `kumar_all54_next_baseline_step_20261015.md`;
it does not supersede any scientific split or historical evidence.

## Reviewable input and implementation

- All54 source acceptance: commit
  `3e415b348decde71da54e366e357cded233d54c8`. The original18 prefix, real parent
  ACKs, original R2 receipts and historical producer stage flags remain intact.
- Checkpoint deployment: `configs/kumar_frozen_query_checkpoints_20261015.json`,
  SHA256 `12e2565c4a1d6e83809e6e513907fce53af47a9b37b4214ba8e62922fb54a6d9`;
  exactly54 original model tars / 12,636,160 bytes. Flat filenames are the exact
  basenames of each original R2 result_key. The first model uses original
  `2a4d0dd291f1f93bc0560e39b99b2e76fbf6bcba0d3a363ceb522fb4afea0f62`,
  not its separately preserved source-replay archive.
- Query inputs: `configs/kumar_frozen_query_inputs_20261015.json`, SHA256
  `4636a83e6be52c8e06de089ec2cc866e2008f6f17412b8d820dc62234999f76f`;
  1,189 files / 1,043,686,331 bytes, 216 query EDFs, 4,290 included events.
  Historical checksums are metadata here; actual full-byte verification is
  gated behind the future real query authorization.
- Guarded entry: `scripts/run_kumar_frozen_query_evaluation.py`.
  Read-only model kernel: `scripts/evaluate_kumar_frozen_queries.py`.
  Pure result aggregation: `scripts/aggregate_kumar_frozen_queries.py`.
  The operation contract and its detached exact-byte hash are
  `configs/kumar_frozen_query_operation_20261015.json` and `.sha256`.
  Final file hashes and actual software checks are in
  `research_logs/kumar_frozen_query_preparation_20261015/`.

Do not call `train_kumar_eegnet.py --execute-formal-training`, `formal_train`,
the completed development/remaining-source runners, or the private query worker
directly. All54 source models already exist; this path creates zero fits.
The completed CPU update baselines remain the original saved experiments.

## Safe metadata check now

From the reviewed checkout on the existing Codex CPU environment:

```bash
cd /workspace/few-shot-mi-eeg
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  /workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/run_kumar_frozen_query_evaluation.py --check
```

This checks code, JSON metadata, package versions and numerical environment;
it never opens model archives or raw query files, constructs a model or grants
execution. Success reports `metadata_verified_execution_closed`,
`execution_authorized=false` and `problems=[]`. Real resource/headroom, duplicate
claim and host checks are repeated by the authorized execution path.

The two standalone metadata inventory checks are:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/prepare_kumar_frozen_query_inputs.py
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/prepare_kumar_frozen_query_checkpoints.py
```

## Concrete later dispatch, not authorized by this delivery

Dot must review the returned fixed commit and contract, then separately issue
the real query-only decision. The external template is
`research_logs/kumar_frozen_query_preparation_20261015/external_authorization.template.json`.
It is deliberately unapproved and has no actual host or time window. Publishing
an actual authorization is not part of this round.

After that decision, the operator records its real source and timestamp, sets
the status to `parent_reviewed_frozen_checkpoint_query_evaluation_authorized`,
sets only `query_evaluation_authorized=true`, and binds the reviewed full commit,
contract, exact54 job order, actual current container identity and an immutable
absolute window of at most7,200 seconds. Observe hostname, boot_id and
pid1_start_ticks on the actual execution host; never copy an old host binding.
Keep all training/optimizer/support/new-strategy/new-resource permissions false.
The frozen contract itself remains without an embedded grant; do not edit its
`execution_enabled`, scientific fields or hashes. Its explicit external grant
mechanism is the only execution path.

Use only the existing CPU venv; no installation or new allocation is proposed.
The reviewed runtime is Python3.11.16 / Torch2.8.0+cpu / Torchaudio2.8.0+cpu /
Braindecode1.2.0 / NumPy2.2.6 / SciPy1.15.3 / sklearn1.7.2 / MNE1.10.2.
This CPU contract does not implicitly approve a different GPU venv.
Before dispatch, stage the exact54 original archives in the external flat
archive directory below using the already-supported private storage path.
Retain the query data's original relative tree; do not rewrite or regenerate
any file. No raw query download or archive staging was performed in preparation.

For the following exact command, set `QUERY_REVIEWED_COMMIT` to the full fixed
commit returned with this delivery, and publish the actual JSON exclusively at
the external path shown only after the separate decision:

```bash
cd /workspace/few-shot-mi-eeg
test "$(git rev-parse HEAD)" = "$QUERY_REVIEWED_COMMIT"
QUERY_AUTH=/workspace/private_model_receipts/frozen-query-evaluation-20261015/actual_external_authorization.json
QUERY_AUTH_SHA256=$(sha256sum "$QUERY_AUTH" | cut -d ' ' -f 1)
QUERY_CONTRACT_SHA256=$(cut -d ' ' -f 1 configs/kumar_frozen_query_operation_20261015.sha256)
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  /workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/run_kumar_frozen_query_evaluation.py --execute \
  --expected-commit "$QUERY_REVIEWED_COMMIT" \
  --reviewed-contract-sha256 "$QUERY_CONTRACT_SHA256" \
  --authorization "$QUERY_AUTH" --authorization-sha256 "$QUERY_AUTH_SHA256" \
  --data-root /workspace/few-shot-mi-eeg/data/public_eeg/kumar2024/nm000177/v1.0.5 \
  --archive-root /workspace/private_model_receipts/frozen-query-originals-54 \
  --output /workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results
```

The host/resources/claim checks are mandatory; this command is not a grant to
run now. Dot remains the sole Pod operator; this handoff does not operate it.
No money or balance condition is introduced.

## Completion, stopping and backup

The attempt identity is
`kumar-accepted54-always-frozen-query-evaluation-run01-20261015`.
Its preserved claim, `worker_start.json`, `worker.log` and launcher receipt are
under `research_logs/kumar_frozen_query_evaluation_20261015/run01/`.
The output is new and outside the checkout. An existing state or output blocks
the invocation. Record actual PID/UTC start after dispatch; dispatch is not
completion.

The shared CPU lock spans the entire attempt. Full process-tree monitoring,
0.25-second sampling, 2GiB RSS ceiling, 1GiB running memory reserve, 3GiB
effective-available preflight RAM and 2GiB disk reserve apply. The original
absolute deadline is never reset; 30 seconds are reserved for TERM/KILL cleanup.
Any input/checkpoint/state/storage/hash/resource/timeout failure stops the
attempt and retains partial files and actual exception evidence. There is no
automatic retry, claim deletion or resume mode.

Each model result contains untouched-checkpoint state digests and full fixed
query predictions/metrics; each participant gets a completeness record.
The final summary requires all54 jobs and all six query sessions per model.
All3 seeds are averaged within participant/session before averaging five
target sessions. Development6, remaining12 and all18 secondary exploratory
results stay separate. Source-query scores are separate. The primary CSP
contrast and prior exposure qualification do not change.

A local complete receipt explicitly leaves independently audited, R2 verified
and accepted false. After actual execution, independently check all result
identities/numeric aggregation/state hashes and preserve the original output,
authorization, claim, logs and exit evidence. Use the existing private R2
uploader with full GET/SHA verification of every object, then obtain the real
parent readback/ACK. Do not call a local result or off-host copy an R2 proof.
This delivery does not pretend that future result backup has already occurred.
