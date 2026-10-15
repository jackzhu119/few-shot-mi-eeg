# Run02 identity preparation; no execution

Baseline and remote at inspection: `ad5be8e51e98eebd99ac994a249136e349d2f582`,
branch `research/learning-preserving-bci`. Original 16 untracked files are
preserved. No reset, initialization, Pod operation or scientific attempt occurred.

The launcher changes exactly three identity constants to run02; the contract
changes their matching values, command output and launcher self-pin. All launcher
functions are unchanged, including complete process-tree monitoring, timeout,
resource checks and cleanup. The scientific consumer remains SHA256
`ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3`.

New launcher SHA256:
`215ec7ec6cb199f2d70c485969583f9b09cfc8346ed7f316448bc92bfdadbf56`.
New contract SHA256:
`0ec85048e51e1f9d3e7cc0e553544db975ab4b792b3e534a3924c6faaef65157`.

The exact command in `docs/kumar_csp_run02_recovery_20261015.md` additionally
checks the frozen recovery binding, original failure receipt/claim/R2 receipt,
new external authorization link, same actual host, original absolute window and
absent run02 output/state. This gate lives in the reviewed command; the native
launcher remains unchanged apart from its three constants. The external
authorization template is explicitly not an actual execution authorization.
No run02 authorization, claim or result was created.

Actual read-only metadata preflight and host check at
2026-10-15T06:21:21.525319+00:00 passed on hostname `94346a2083c4`, boot_id
`02e1dd56-6faf-45ed-b710-a28705535fb6`, pid1_start_ticks `54`.
All 42 input artifacts and frozen runtime matched, no arrays were deserialized.
Effective available memory was 7600693248 bytes; free disk 5482606592 bytes.
These observations are not reservations; dispatch repeats the existing checks.
The original 07:27:00 UTC absolute deadline remains unchanged; startup and receipt
work consume remaining time and the launcher reserves up to 30 s for cleanup.

Validation: 17 new identity/linkage tests and 80 existing operation tests passed
(97 total, 0.71 s). Scoped Ruff and git diff checks passed. An independent agent
reviewed only this identity patch and ran the 17 new tests (0.11 s), finding no
blocking issue. Tests cover old receipt/claim/R2 tampering, wrong linkage, host,
deadline, old diagnostic, template authorization, contract and existing/symlinked
run02 paths. Exact source comparison and AST comparison establish that all
launcher functions remain identical to the reviewed baseline. No full suite or
scientific consumer was run.

All 62 protected files match the pre-edit SHA256 snapshot, including the original
16 untracked files, run01 external authorization/evidence and state, previous
procfs proof/receipts, scientific consumer and accepted18 ledger. The run01 R2
receipt remains SHA256
`b5524eeb9aa945535766dcfdba9dab224cb79b6910182694241adbe2d1f48a29`
(20 original objects / 40972 bytes / zero full-GET failures). No R2 object was
overwritten or reinterpreted, and no new R2 verification is claimed this turn.

No financial calculation or new financial gate was introduced. Historical
allocation evidence remains intact and financial blocking requirements are
recorded as superseded-by-user. No GPU/query, accepted18 refit, remaining36
release or new resource allocation is authorized by this preparation.

Next: dot checks the fixed identity delivery, creates a new external actual
authorization bound to that exact commit and the original window, then dispatches
the complete documented gated command once on this same CPU host. Failure stops;
preserve all evidence and do not retry or extend the window.
