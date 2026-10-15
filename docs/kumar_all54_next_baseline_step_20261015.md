# Accepted 54 checkpoints: next frozen-baseline step

The completed source-training stage is 18 participants × three fixed seeds, all
54 accepted. Reuse those original checkpoints and their source normalization;
there is no remaining source fit to schedule. The first18 ledger remains an
unchanged prefix, including the legacy first job. New records retain their
original failures, pauses, source-selection history and private R2 object keys.
This note neither authorizes query access nor operates Pod.

The existing metadata entry is `scripts/evaluate_kumar_checkpoint_reuse.py`,
SHA256 `838f3ed7b8f67c65dcf27b3ef43aace29db9464c8cdaae730be5dfebc92ba4e2`.
Its `check_reuse_identity` accepts any complete same-order ledger/plan and has
no18-model count restriction. It verifies each actual parent acknowledgement,
the acknowledgement-bound complete R2 receipt, exact result key/archive hash,
HTTP200/full-GET verification and byte counts. The first legacy identity must
stay first because its historical acknowledgement predates the job_id field.
The older `check_kumar_checkpoint_reuse_proposal.py` deliberately validates its
historical18-only proposal and inventory; it is not the all54 readiness checker.

## Exact executable metadata check

From this delivery's fixed checkout, in the existing Codex CPU environment:

```bash
PYTHONPATH=src:scripts /workspace/.venvs/few-shot-mi-eeg/bin/python -B - <<'CHECK'
import hashlib
import json
from pathlib import Path
from evaluate_kumar_checkpoint_reuse import check_reuse_identity

base = Path('research_logs/kumar_remaining36_acceptance_20261015/run01')
ledger = base / 'accepted_jobs_all54.json'
plan = base / 'source_model_plan_all54.json'
ledger_sha = '013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670'
plan_sha = '28232bfa53515ae3e66acadefa39ee025320cfda0196a5d785631bf4d8f8abcd'
for path, expected in ((ledger, ledger_sha), (plan, plan_sha)):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Frozen all54 metadata SHA256 mismatch: ' + str(path))
jobs = json.loads(plan.read_text())['jobs']
if len(jobs) != 54 or len({j['job_id'] for j in jobs}) != 54:
    raise ValueError('Exactly54 unique accepted source models required')
verified = []
for job in jobs:
    entry, frozen_job, archive_bytes, snapshots = check_reuse_identity(
        job_id=job['job_id'], ledger_path=ledger, expected_ledger_sha256=ledger_sha,
        plan_path=plan, expected_plan_sha256=plan_sha)
    verified.append({'job_id': entry['job_id'], 'subject': entry['subject'],
                     'seed': entry['seed'], 'archive_bytes': archive_bytes})
print(json.dumps({'status': 'all54_accepted_identities_verified_metadata_only',
                  'models': verified, 'verified_count': len(verified),
                  'checkpoint_tensors_loaded': False, 'EEG_or_query_loaded': False,
                  'new_fits': 0, 'scientific_gate_passed': False}, indent=2))
CHECK
```

This is one CPU process, using the existing checker54times. Its module imports
NumPy/PyTorch but does not load checkpoint tensors, open EEG, build an optimizer,
run inference or write acceptance records. It stops on the first failed identity
or receipt check. It is neither a new experiment nor a query-evaluation command.
Saved source-validation predictions may also be aggregated descriptively without
new inference; their CE-selected epochs make them unsuitable as independent
query/generalization evidence. Preserve all three seeds and participant identity.

## The single unfinished execution gate

A separately frozen **query-only checkpoint-reuse evaluation path** is still
missing. The current Python evaluation API intentionally accepts only archived
source-validation identities; its CLI is metadata-only. The generic
`train_kumar_eegnet.py --execute-formal-training` would fit the models again and
must not be called. All54 acceptance alone does not implement or release query
inference.

The concrete next instruction is to prepare and review that minimal evaluation
path against the existing `EEGNET_TRAINING_PLAN.md` and frozen split: load the
accepted54 original checkpoints once each, restore their fixed channel mean/scale
and BN state, read only the exactly manifest-bound source_query
(ses-0/run-3) and target_query (ses-1–5, non-support runs), and evaluate with no
optimizer, refit, BN/normalization update or threshold/seed selection. Freeze its
exact code/config/input identities and prove parameter/buffer/context hashes
unchanged before and after evaluation, then bind a separate actual execution
scope. Preparation can proceed without opening query signals or labels; this
note supplies no query authorization or invented executable query command.

The intended output remains the prespecified source-only EEGNet baseline:
per-seed/session balanced accuracy and confusion counts, then mean seed score
within participant/session and mean over the five target sessions. Development6
and fixed final12 stay separate;18 participants, not54 seeds, are the independent
units. Do not replace the frozen primary CSP contrast with a post-hoc EEGNet
contrast. Retain original partial-window/QC rules and all failures. The completed
CSP signed-score control remains insufficient to establish a useful adaptation
gate, so no new strategy or model search is added. This is offline decoding, not
human skill retention or clinical benefit; prior cohort exposure remains disclosed.
