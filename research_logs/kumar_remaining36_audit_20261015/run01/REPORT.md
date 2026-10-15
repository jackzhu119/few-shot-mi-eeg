# Remaining36: independent audit and original-byte R2 backup

All 36 newly trained source-only EEGNet model archives passed the frozen model
auditor. All 113 original objects completed private R2 full GET/SHA256
verification: 33,666,029 bytes, zero object failures. The previous accepted18
ledger and model identities remain unchanged. These 36 are independently
audited and backed up, but are **not accepted** until actual dot parent
confirmation. No new fit, query access or Pod operation occurred in this audit.

Execution used fixed commit `58b154a3572d073548fa21f6f0b2bbb09fc76401`, contract
SHA256 `f1a5b94aa89f6f2d9f694f7c270e48ef2624afc06be3a08e328f500224491bd9`,
run `a13f6c01e04e43948fc01f6b69314cec`. All 36 job identities, participants,
three seeds, source scope, science, numerical settings and original tolerance
match the frozen contract. These are 12 participants and 36 model instances.

## Received originals and actual execution

| Original attachment | Bytes | SHA256 |
|---|---:|---|
| remaining36-all-models-audit-handoff-run01.tar.gz | 5,573,743 | `b6adc8478cf95446f1ed2d3e34eaa2337ef7980a8b538d0b682c23adac21c56b` |
| remaining36-final-dispatch-evidence.tar.gz | 117,536 | `7fa2a7cc7a294934624627398976e22fe434e9f8113e46ec47a8dad2469d8678` |
| remaining36-all36-independent-integrity-20261015.json | 40,640 | `a7c032a9aeabaa60db5160d6e4215d9b9f7c4536d93d7b87ec4affe65233d5b6` |

The handoff has 109 payloads plus its manifest; the final dispatch has 284
payloads plus its manifest. The inventory independently hashed all 393 outer
payloads, 504 boundary payloads and 504 nested model payloads. All 36 separately
received model archives match their nested boundary copies byte for byte. The
parent's 12,453-check count remains an attributed parent report; this inventory
performed its own 6,007 assertions rather than claiming the same check counter.

Evidence timestamps below retain their original UTC convention:

| Event | Recorded UTC |
|---|---|
| Immutable authorized window | 2026-10-15 06:52:10–09:52:10 |
| Initial controller start | 06:57:58.993411 |
| Original receipt-wait pause, exit76 | 07:50:46.591616 |
| Same-run resume | 07:56:48.348789 |
| Actual final exit75 | 08:00:29.224666 |

The final state is `complete_exported`, `pending=null`, 36 trained and 36
off-Pod exported. Original audit/R2/accepted flags in that producer state remain
false. Subsequent audit/backup status is a separate record. The initial handoff's
`final_dispatch_evidence_pending=true` and `final_terminal_exit_observed=false`
also remain intact; the supplementary final dispatch resolves that earlier
snapshot. The final GPU-empty observation is a point-in-time postflight record,
not continuous independent GPU monitoring.

## Independent numerical audit

The unchanged `scripts/audit_kumar_remaining_source_bundle.py` verified each
original tar, 14 payload members, source/configuration identity, safe checkpoint
tensor loading, complete state/context digests, labels, epoch history, earliest
minimum, patience15 stopping and saved-logit CE. Its SHA256 remains
`e554a05a566102e1ff06508b7e380d56805df5cf6feb50270a3713acd2b5a0fd`.
The independent companion checked all 864 checkpoint tensors and recomputed
NumPy and CPU Torch CE from the saved validation logits.

| Quantity | Verified result |
|---|---:|
| Models / epochs / optimizer steps | 36 / 1,844 / 5,532 |
| Source TRAIN / source validation / query per model | 40 / 20 / 0 |
| Maximum independent NumPy float64 CE difference | 4.6890414995282015e-8 |
| Maximum original recorded Torch replay difference | 0 |
| Maximum independent CPU Torch saved-logit CE difference | 8.344650270775134e-8 |
| Unchanged absolute tolerance | 1e-7 |
| New audit fits / model forwards / EEG-array loads | 0 / 0 / 0 |

This audit checks original recorded checkpoint replay and independently
recomputes saved-logit CE. It does not claim a new checkpoint-to-EEG forward.
Separately, all 253 frozen local source files / 196,740,994 bytes were fully
rehashed without decoding EEG. Their hashes match the exact source manifest
and the model-bound download/input records. No query data was read.

The source-validation descriptive mean BA is 57.3611%, averaging all three
seeds within each of 12 participants. Participant means range 48.3333%–75%.
Four models predict only one class; ten reach the frozen 100-epoch cap. These
results and all seeds are retained. Validation selected the epoch; these are
not independent generalization scores or evidence for an adaptive gate.

## Exceptions and preserved history

The first dispatch audit recorded two failed byte-equality assumptions:
`dispatch/authorization-copy.json` differs from `batch/authorization.json`,
and `dispatch/source-receipt-copy.json` differs from the original source
receipt. The saved supervisor writes these copies with `sort_keys=True`.
Their complete JSON content matches; the actual runner, state, boundaries and
models bind the unchanged original hashes. They are derived JSON copies, not
byte-identical originals. Both versions, the first failed audit script/receipt,
and the subsequent explicit reconciliation are retained. No original file,
tolerance or scientific rule was changed to resolve this distinction.

The exit76 pause, same-run recovery, old failure evidence and all claims/logs
remain preserved. No automatic training retry or prior accepted-model duplicate
appears in the provided execution chain. Historical lock ownership and live
process continuity cannot be independently re-observed here; the fixed source,
worker timing, sequential intervals and receipt-gated journal are audited as
recorded evidence. Scientific audit failures and object-transfer failures are
reported separately from the two resolved dispatch-copy assumptions.

## R2 objects and actual full readback

Prefix: `few-shot-mi-eeg/experiments/kumar2024/gpu-remaining-source-20261015`.
Each model uses its exact frozen `result_key`. Shared evidence is under
`bounded-batch-20261015/a13f6c01e04e43948fc01f6b69314cec/`.

| Object category | Count |
|---|---:|
| Original model tar | 36 |
| Original intent/results boundary tar | 36 |
| Original actual off-Pod receipt | 36 |
| Original handoff status and manifest | 2 |
| Original received attachments, including final dispatch and parent report | 3 |
| Total | 113 |

The 285 dispatch members remain inside the original dispatch archive; they are
not additionally counted as separate R2 objects. The handoff envelope also
preserves its complete original bytes, so the object-byte total intentionally
includes envelope redundancy. `original_payload_inventory.json` lists every
source, exact key, byte count and SHA256. All upload keys are immutable; no old
object was overwritten and no credential was created or copied.

`r2_full_get_receipt.json` is 113,810 complete UTF-8 bytes, SHA256:

`bd52fb3f691d9309ce1cd30a1fa4e92921282399e014a1119b06f06041bdcb1c`

It records 113/113 full GETs, 33,666,029 readback bytes and zero failures.
`R2_receipt_crosscheck_run01.json` independently checks the receipt against
original/staged bytes and all 36 exact model keys. No weights, binary outputs
or raw EEG are committed to Git; only audit code and text evidence are included.

## Handoff

Relevant frozen-auditor and queue-gate tests: 65 passed in 3.24 seconds. The
full unrelated suite was not rerun. No production runner/configuration changed.
The per-job later-stage state is in `received_job_stages.json`; the pending
actual confirmation request is `parent_acknowledgement_request.json`.

After dot independently reads this fixed delivery and verifies the full receipt
against its originals, it can provide actual confirmation for these exact 36
identities. No confirmation is manufactured here. `NEXT_ANALYSIS_READINESS.md`
prepares saved-result reporting and the separate future checkpoint-only
evaluation boundary, without releasing query, training, or a new policy.
