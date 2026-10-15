# Independent remaining-36 source operation: prepared, not authorized

This contract covers sub-2/3/5/6/8/9/11/12/14/15/17/18 in that order, each with
seeds 20261012/13/14. It excludes every identity and result of the accepted 18.
It does not require or implement a query adapter. The scientific training JSON
remains byte-identical (`14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d`),
including preprocessing, architecture, Adam, stopping, normalization, numerical
threads and the 1e-7 replay tolerance. No hyperparameter or policy is selected.

The independent operation is `configs/kumar_remaining_source_batch_20261015.json`.
Its checksum fixes reviewable proposal bytes. The current contract records
cost/authorization/approved duration/actual absolute start and deadline as null.
Default CLI operation is metadata only. Future execution must present a distinct
actual parent authorization that binds the reviewed code commit, exact contract
SHA256, ordered 36 IDs, query=false, no refitting accepted18, current reviewed
container and the concrete cost/time decision below. No such authorization is
created in this delivery. The immutable contract's `execution_enabled=false`
describes the present proposal; the explicit separately checked authorization is
the sole future execution permission. CLI flags alone cannot grant it.

## Fixed scope and concrete resource/time proposal

| Item | Prepared contract |
|---|---|
| Input scope | Exact 253 files / 196,740,994 bytes; 36 EDFs, only ses-0 runs 0/1 TRAIN and run 2 validation |
| Cohort overlap | Zero accepted-development subjects or job IDs; all 18 original acceptances remain unchanged |
| Per model | 40 TRAIN / 20 source validation; at most 100 epochs, three optimizer steps per epoch |
| New count ceiling | 36 models, 3,600 epochs, 10,800 steps; no transfer of unused allowance to repeated fits |
| Resource proposal | One existing dot-scheduled GPU, serial; no new paid resource or Pod operation by Codex |
| Active batch | Two sequential fits; shared GPU lock covers input revalidation, both workers and packaging |
| Time ceilings | 1,800 seconds per fit, 3,600 seconds per active batch, TERM grace 30 seconds then KILL |
| Off-Pod boundaries | 18 batches × intent/results = 36 full-download verification boundaries, each waits at most 600 seconds |
| New total proposal | 86,400 seconds, including rechecks, packaging and all waiting; a maximum, not a promise to finish all 36 |
| Cost / approved time | Null until an actual current decision; historical prices and the old 19,800-second run do not authorize this operation |
| Disk stop | Before each batch/fit/export, require 5 GiB plus 96 MiB active-batch reserve; otherwise preserve state and stop |
| Bounded artifacts | At most 16 MiB per original model tar, 64 MiB per export; at most two trained models lacking verified off-Pod export |
| Retry policy | Zero automatic training retries; partial or ambiguous claims stop the queue |

The time proposal is explicit: 36×1,800 fit ceilings plus 36×600 boundary waits
equals 86,400 seconds. Revalidation/packaging overhead consumes this same budget;
there is no hidden extension. A full conservative input/model/export footprint
plus the 5-GiB floor is 8,585,348,994 bytes, excluding logs; this is not a disk
guarantee. No current GPU, disk, price or billing state was inspected here.

The remaining parent decisions are concrete: select an actual absolute
`not_before_unix`/`deadline_unix` and `approved_wall_seconds<=86400`, and provide
the current comprehensive hourly rate, maximum USD and latest actual cost
authorization reference. The authorizing record must satisfy
`rate * approved_seconds / 3600 <= maximum_usd`. Its actual reviewed host and
the fixed commit/contract digest must match. All of these are still absent;
cost fields stay null. No estimated dollar amount is substituted.

## Source restoration and per-fit revalidation

`fetch_kumar_remaining_source_https.py` prepares the exact public NEMAR v1.0.5
scope with original official checksums and archived SHA256. It restores metadata
first, verifies CC-BY-4.0/version, uses one request at a time and one attempt per
file, preserves partial files/failed receipts, and exclusively creates targets.
Every future fit calls `verify_all` to hash all 253 files again. The receipt binds
both the HTTPS manifest and the underlying 253-file source manifest. Existing
valid files can be reused only after their full verification.

The HTTP manifest currently also has `execution_enabled=false`, and even
`--execute` refuses before writing or network access. If parent review approves
restoration later, freeze the corresponding enabled HTTP manifest with the same
253 entries, update its exact digest in the separate final operation contract,
and review that final digest before issuing the actual cost/deadline
authorization. No restoration or new input receipt is performed/forged here.

## Full off-Pod receipt mechanism

The mechanism reuses the proven original eleven-fit export inspector and receipt
verification functions without altering their old globals or old contract. That
run has twelve actually downloaded boundaries/receipts, independently checked in
`all11_reception_run01/boundary_independent_review_run01.json` and
`dispatch_independent_review_run01.json`. The new contract is independently
scoped; the old 7/11/127-file runtime must not be invoked for it.

For each new batch, immutable claims and an intent export are created first.
Dot fully downloads that original tar to its off-Pod cloud filesystem using the
existing authenticated Jupyter/browser route. On that filesystem, the fixed
verifier checks all archive bytes, identity, member hashes and nested result
packages, and only then produces a new receipt:

```bash
PYTHONPATH=src:scripts python -B scripts/run_kumar_remaining_source_batch.py \
  --verify-export "$FULL_OFF_POD_ORIGINAL_TAR" \
  --receipt-output "$NEW_OFF_POD_RECEIPT_JSON" --attest-off-pod-possession
```

Return the receipt through the supported authenticated Jupyter upload or the
already tested terminal route; compare the complete UTF-8 SHA256, write a new
file exclusively and publish without replacing an existing receipt. There is
no invented browser/internal API or automatic R2 uploader. Physical off-Pod
possession is dot's attestation; verified bytes and member identities are the
verifier's evidence. The new runner waits for this actual receipt before fitting
and requires the corresponding results receipt before another batch.

## Truthful stages and recovery

`trained` means one fit and its complete original package were saved.
`off_Pod_exported` means its full-download receipt passed. The runner always
leaves `independently_audited`, `R2_full_GET_verified` and `accepted` false.
The new `audit_kumar_remaining_source_bundle.py` preserves the old independent
scientific checks, but binds the new 36-job/253-input contract and new source
entry. The old 18-job/127-input auditor correctly rejects these new packages
and must not be used. Actual future independent audit, complete R2 GET/SHA,
then real parent acknowledgement are separate external events. No accepted
ledger writer or parent acknowledgement generator exists in this runner.

State binds one run ID, exact authorization, fixed commit/contract, container
identity, immutable claims and absolute deadline. Exit 76 is a safe export wait
pause, not training failure or permission to start a new run. Resume keeps the
same budget/deadline and only proceeds after the awaited receipt is verified.
An active/failed/partial job, missing state, changed container or mismatched
claim cannot be silently retried. Preserve all files; parent must reconcile
the off-Pod intent/results packages before any separately reviewed recovery.
Do not delete claims or create a fresh run to repeat a trained item.

Future full result audit requires explicit original bytes and a new output:

```bash
PYTHONPATH=src:scripts python -B scripts/audit_kumar_remaining_source_bundle.py \
  --archive "$ORIGINAL_MODEL_TAR" --sha256 "$ORIGINAL_FULL_SHA256" \
  --bytes "$ORIGINAL_BYTE_COUNT" --output "$NEW_INDEPENDENT_AUDIT_JSON"
```

This is an audit command, not a fit or acceptance command. It is not run here
against any actual model. Raw models/EEG stay outside Git, and no R2 credential
is copied to the Pod.

## Exact safe next command

In the fixed checkout, using this Codex CPU venv only:

```bash
PYTHONPATH=src:scripts /workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/run_kumar_remaining_source_batch.py --plan-only
```

Expected: 18 preserved, 36 proposed, 253/196740994 input scope, cost null,
authorized fits 0, query false. This does not touch input signals or GPU/runtime.
After fixed-code review and the specific cost/deadline/restoration decisions,
dot alone may consider the explicit `--execute --new-run` entry with
`--expected-commit`, `--reviewed-contract-sha256`, `--authorization` and
`--authorization-sha256`; keep original thread/CUBLAS settings. No concrete
execution authorization or runnable new-fit command is supplied now.
