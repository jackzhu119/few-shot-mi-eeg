# Actual run02 CSP diagnostic execution and audit

Run02 executed once under dot's actual 2026-10-15T06:25:45Z decision, using the
complete reviewed recovery_gate command at commit
`d6afce75da092df1b106182af5c9234b1392604a`. Contract SHA256 is
`0ec85048e51e1f9d3e7cc0e553544db975ab4b792b3e534a3924c6faaef65157`;
launcher SHA256 is
`215ec7ec6cb199f2d70c485969583f9b09cfc8346ed7f316448bc92bfdadbf56`.
Scientific consumer remained
`ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3`.

The new external authorization differs from the frozen template only in status
and reviewed_commit. Its full-byte SHA256 is
`24ca035e5be573924c8eac874879880de3d434a7d0afc479f853943935ef8e06`.
It links run01's original failed receipt/claim/R2 proof and the frozen recovery
binding. The actual parent decision and command-source binding were separately
recorded outside the checkout. These private originals are included in the R2
payload; Git contains their paths, lengths and hashes, not copied credentials.

## Actual execution

The observed host matched run01: hostname `94346a2083c4`, boot_id
`02e1dd56-6faf-45ed-b710-a28705535fb6`, pid1_start_ticks `54`.
Both the read-only preparation preflight and the actual guarded launch checked
the frozen runtime, 42 input artifacts and available resources. Run02 output and
state were absent before the exclusive claim. The reviewed complete command
performed the recovery linkage checks before invoking the guarded launcher.

| Event | Actual UTC |
|---|---|
| Launcher PID 17730 dispatched | 2026-10-15T06:28:25.274033Z |
| Consumer PID 17755 started | 2026-10-15T06:28:25.533301Z |
| Scientific measurement began | 2026-10-15T06:28:27.917072Z |
| Scientific measurement finished | 2026-10-15T06:28:42.803571Z |
| Consumer finish recorded | 2026-10-15T06:28:43.786427Z |
| Launcher exit observed | 2026-10-15T06:28:44.056017Z |

Consumer and launcher returned 0. The raw launcher status remains
`consumer_exited_zero_pending_audit`; its historical audit/R2/acceptance flags
remain false. Subsequent audits and R2 proof are separate records, not edits to
that original receipt. No retry was made.

The original 05:27–07:27 UTC window was not reset. Remaining consumer time at
launch was 3484.467525959015 seconds after startup and the 30-second cleanup
reserve. No timeout, resource stop, signal or required descendant cleanup was
recorded. Post-exit observation found neither launcher nor consumer PID present.

There were 72 actual process-tree samples, using the reviewed PPID/session and
PID/starttime method with TGID RSS deduplication. The maximum sampled RSS was
217903104 bytes; minimum sampled cgroup headroom 7383158784 bytes and host
availability 9455140864 bytes. Configured polling remained 0.25 seconds; the
largest recorded interval was 0.2630300521850586 seconds. These are discrete
observations, not proof of a continuous RSS maximum or every transient process.

## Saved scientific result

All 240 frozen SOURCE20 CSP/LDA pipeline attempts completed; zero expected
estimator failures were recorded. They cover 6 development participants × 2
source folds × 20 train-label rotations, with the 12 identity-rotation fits
already included. There are 4800 cached heldout trial predictions and 2400
joint-shift twofold rows. Six existing SOURCE40 decoders were reused, with six
source-only coordinate scalers; no new full40 decoder, adaptation model, GPU
model or primary baseline was trained. Inputs contain 240 source TRAIN and 596
predeclared support windows. Query rows and final subjects opened are both zero.

The original output contains 253 files / 26108327 bytes: 240 CSP parameter NPZ,
6 selected feature/score NPZ, 6 subject JSON and one full measurement JSON.
Every original output length/SHA256 matches the launcher inventory. All raw
weights/features remain private; only text audit records are committed to Git.
Independent operational and numerical audits are recorded separately alongside
this report; the original saved results are not rewritten.
The independent numerical audit passed 629137 field checks, with maximum
observed arithmetic difference 0, including all saved scores, joint controls,
both support-half control modes and both 10000-draw participant bootstraps.
It replays from saved log-CSP features; it does not recompute the EEG-to-CSP
projection or independently refit an estimator. Input bytes and identities
are independently covered by the operational audit.

| Participant | Source twofold BA | Descriptive source phase-control upper tail |
|---|---:|---:|
| sub-1 | 70.0% | 0.015 |
| sub-4 | 50.0% | 0.5275 |
| sub-7 | 72.5% | 0.025 |
| sub-10 | 42.5% | 0.84 |
| sub-13 | 67.5% | 0.04 |
| sub-16 | 75.0% | 0.005 |

The participant mean source BA is 62.9167%, with the frozen participant
bootstrap 95% interval [52.5%, 71.6667%]. Mean within-participant five-session
support split-half vector cosine is 0.295325, interval [0.032041, 0.573003].
These intervals use six independent participants, not 30 independent sessions.
The cyclic-control upper-tail fractions are descriptive sensitivity measures,
not formal permutation p-values.

Signed-score directions are mixed: among 30 support sessions, 19 have both
half-contrasts positive, two have both negative, and nine have opposite signs.
Thus a positive product also occurs when both halves point opposite to the
frozen source decoder: sub-1/ses-4 and sub-7/ses-2. This count describes the saved
diagnostic, not a selected decision threshold or a tested adaptation rule.
Five support sessions also show frozen-score prediction class collapse.
The new complete control evidence is distinct from earlier incomplete CSP
results even where identity-rotation source BA agrees. It does not establish a
nested out-of-sample policy improvement, validated adaptive gate, human learning
preservation or clinical effectiveness. No strategy/seed/model search occurred.

## Evidence, backup and remaining boundary

`original_output_manifest.json` lists every raw output. The R2 payload includes
all raw output bytes, all run02 state/log/exit and external authorization/dispatch
evidence, frozen source/contract/binding and the independent text audits. The
complete object list, sizes, hashes, full GET results and any failures are in
`R2_full_get_receipt.json`; `R2_closing_validation.json` verifies that receipt
against the original files. Both closing records live outside their own uploaded
payload to avoid recursive self-hashing. Remote keys use the new run02 prefix;
no run01 object is overwritten.

All 62 protected pre-existing files match the prior preservation snapshot,
including run01's failed claim, external authorization, receipts/R2 proof,
procfs proof, original 16 untracked files, scientific consumer and accepted18
ledger. The empty run01 log still does not prove zero Python execution.
Run02's claim and results remain in place and prevent reusing this identity.

Dot can independently read this fixed audit/R2 delivery and confirm the actual
measurement. No parent acknowledgement is fabricated here. Existing accepted18
and all 36 unstarted GPU fits are unchanged; no query evaluation or next
scientific stage is released. No additional scientific attempt is authorized.
