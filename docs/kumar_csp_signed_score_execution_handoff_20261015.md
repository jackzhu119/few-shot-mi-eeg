# CSP signed-score evidence reconciliation and CPU execution proposal

This is a review delivery, not permission to execute a diagnostic. No actual
CSP/LDA fit, EEG/model-array load, query access or Pod action occurs in this
round. The 18 accepted EEGNet checkpoints and their ledger are independent of
this diagnostic and remain unchanged. Paper 1 is outside this delivery.

## What the evidence actually establishes

The fixed scientific protocol remains commit
`757107fdc369d82b71960ab567d2f8730201337c`. Its freeze receipt records
`2026-10-14T07:29:13.289278+00:00` and explicitly says the new measurement was
not yet computed. The prepared restricted tensors were completed at
`2026-10-14T07:31:51.352202+00:00`; the independent static preparation review at
`07:33:51.432293 UTC` explicitly did **not** accept the consumer implementation.

| Required evidence | Observed, with identity checked | Status |
|---|---|---|
| Frozen exact-phase/source-score protocol | Current config, plan and independent methods review match their archived SHA256 values | Frozen scientific scope |
| Physically restricted inputs | All 18 prepared metadata/tensor/receipt files are present and match the historical review's byte hashes; 240 TRAIN and 596 current-support rows, 42 EDF provenance identities | Prepared inputs, no numerical replay this round |
| Six original SOURCE40 states | All 24 `source_before.npz`, `source_after.npz`, `fit_access_audit.json`, `participant_receipt.json` files match the existing full-GET R2 receipt by bytes and SHA256 | Reusable inputs, arrays not deserialized here |
| 240 new TRAIN20 phase pipelines, exact 20 × 20 scores, 2400 participant/pair rows | No matching completed measurement receipt, subject result or saved phase-model output in the bounded inventories below | Pending |
| Original LDA intercept, separate signed class margins, score bias/recalls/collapse | Historical six subject files contain source-axis vector contrasts; they lack the later `half_score_diagnostics` signed-LDA fields | Pending; historical contrasts are not substitutes |
| Independent numerical review and full-GET backup of the latest measurement | Static preparation review and historical CSP backup exist; latest diagnostic completion/numerical-review/backup proof does not appear in the examined scope | Pending |

This conclusion follows an evidence census, not a repeated filename assertion:

- The local `/workspace` census inspected 29,255 file paths, including ignored
  results, original attachments, private receipt/staging roots, chat archives
  and R2 upload staging. It excluded Git internals, caches and installed-package
  trees. Only the known power/support `measurement_receipt.json` files exist;
  there is no `subject_measurement.json` in that census.
- Read-only headers from 72 relevant local tar/zip archives cover 10,413
  members, with zero scan failures and no latest CSP/signed-score execution
  result member. Raw public-data zip archives were excluded. No archived array
  payload was deserialized.
- Five existing full-GET backup catalogs were checked: 28 GPU-preparation,
  618 primary-baseline, 1236 scientific-evidence, 294 low-dimensional and 27
  checkpoint-preparation objects. Their latest CSP execution-result matches
  are empty. The 28-object catalog positively identifies 12 historical CSP
  objects, including the original failed summary, corrected summary and log.
- Fresh R2 LIST metadata at `2026-10-15 04:11:59–04:12:02 UTC` inspected 3301
  `research-evidence/` objects over four pages and 672
  `experiments/kumar2024/` objects over one page, all HTTP 200. The 15 relevant
  matching keys are the 12 historical CSP objects, two earlier power/support
  measurement receipts and the preceding readiness document. There are zero
  latest CSP execution-result key matches and zero object GETs in this census.
  LIST length/date is existence metadata, not a new full-GET/SHA proof.
- A separate local CPU-host process snapshot at `04:17:20.529229 UTC` inspected
  13 processes with zero unreadable entries and no exact CSP consumer script
  token. It logged only matching basenames/PIDs/command names, never full argv.
  This snapshot establishes neither historical nor remote process absence.

See `research_logs/kumar_next_source_operations_20261015/` for
`csp_evidence_reconciliation_run01.json`, `R2_csp_object_census_run01.json`,
`local_CSP_process_metadata_snapshot_run01.json` and the independent code review.
These bounded searches do not prove that no unreported external execution ever
happened or inspect arbitrary unseen remote archive members. They establish
exactly which available evidence can support this handoff.

The historical corrected result is real but belongs to a different protocol:
12 observed TRAIN20 pipelines, 96 random-label-control pipelines and six new
SOURCE40 pipelines, total 114, bootstrap seed 20261014. Its config SHA256 is
`e0a9d2f7363d245299b9bff8e2d6fdbcf913021d7e6608ff08f893832ae3a315`.
The source BA 62.9167% and support cosine 0.298181 remain historical descriptive
results. They neither implement the exact phase design nor establish a signed
score decision rule or an adaptive benefit.

## Exact proposed diagnostic, with no scientific expansion

Development IDs remain `sub-1, sub-4, sub-7, sub-10, sub-13, sub-16`.
SOURCE TRAIN is exactly `ses-0/run-0` and `run-1`, 20 complete trials per run,
10 left and 10 right, 40 per participant and 240 total. Each of the five current
target sessions contributes only its prespecified `run-0` support, 19/20 trials;
there are 596 such support rows. These are current-support diagnoses, not source
TRAIN or query outcomes. No source-validation/run-2, source query, target query,
final-cohort, partial-window replacement or accumulated earlier support enters.

The 836 restricted tensors preserve 5 seconds, 22 channels, CAR, 8–30 Hz,
128 Hz, 640 float32 samples in volts, original labels/identities and retained
QC flags. Their 42 EDF provenance paths are six participants × seven files:
two SOURCE TRAIN runs plus five current-support runs. The existing prepared
NPZ files contain 43,786,391 compressed bytes in total. No whole EDF numerical
stream is needed by the consumer. These existing prepared inputs are untracked
local artifacts: check their exact pins on the execution host and stop if
missing; this delivery does not silently reconstruct them.

For each of the two run-held-out folds per participant, refit both CSP4 and LDA
once for each of 20 TRAIN-label rotations. Cache the unchanged holdout
predictions and cross-score all 20 holdout-label rotations. The exact maximum
is 240 pipeline attempts, including 12 identity pipelines, hence 240 CSP and
240 LDA estimator attempts. Save all 2400 participant/pair twofold rows and
4800 fold-phase score rows; failures retain explicit missing values and
denominators. No failed pipeline is retried. A singular pipeline remains a
failed attempted fit in the frozen design, not evidence to alter the design.

Load the six primary SOURCE40 CSP/LDA states from the already verified baseline,
with no new SOURCE40 decoder or support decoder fit. Six SOURCE40-only feature
scalers provide the prespecified measurement coordinates. Preserve original
LDA classes `[0, 1]`, right-positive score, intercept and zero threshold; use
SOURCE40 score SD with `ddof=1`. Save separate signed true-class margins,
balanced contrast, score location/bias, predicted proportions, recalls and
collapse. Enumerate every 19/20 support label rotation with recomputed
classwise halves and the fixed-half sensitivity. Participant bootstrap stays
10000 draws, seed 42; sessions, trials and phases do not become independent
subjects. Phase tail fractions are descriptive sensitivities, not formal
randomization p-values or evidence of neural specificity.

## Pinned reviewable execution files

| File | SHA256 |
|---|---|
| `configs/kumar_csp_reliability_20261014.json` | `4f71724c6be77696bbf8764e7de4795ceb1c9c4a315c1c2b266cc201a1c3da18` |
| `docs/kumar_csp_reliability_plan_20261014.md` | `b942fdb6265594d632dbfb70a536bd576b9e2d5b13871f8d4e8e4c9721a8b34f` |
| `docs/kumar_csp_reliability_methods_review_20261014.md` | `f53592721e4cff14b7d8466234c99d299f81870e0937346f92f1872b86532600` |
| `scripts/analyze_kumar_csp_signed_score_v1.py` | `f2a0eb4831d78c4cbef54656c56c5ee7c085c697eff287c64dd535a5bdb7a5ad` |
| `configs/kumar_csp_signed_score_input_binding_20261015.json` | `af65b5f0ce7850b010dc83965e799d3f26601b70fb6bc19607e59d1af3738712` |

The versioned consumer is a byte-exact copy of the preexisting untracked
candidate. The old candidate, old tests and all prepared untracked files are
unchanged. Its new test copy redirects only the import to the fixed new path.
The new input binding separately pins 18 prepared artifacts, 24 reusable
SOURCE40 artifacts and 12 protocol/dependency/receipt files; it does not turn
the old static preparation receipt into consumer or numerical acceptance.

The standard-library-only `scripts/check_kumar_csp_signed_score_inputs.py`
checks those bytes, restricted metadata and historical R2 proof without
importing NumPy, Torch, MNE, a model or a process launcher. It cannot train,
predict or deserialize arrays. Its pass remains
`metadata_verified_execution_closed`, `execution_authorized=false`.

That metadata check was actually run successfully in this Codex CPU venv;
its saved result is `csp_input_metadata_preflight_run01.json`. The 18 related
input-checker software tests passed, using synthetic metadata and inert opaque
bytes. The consumer's 12 original software tests also passed with synthetic
arrays/mock estimators. These are software checks, not real CSP execution.
The 12 independent supplemental mocked-receipt tests also passed; together
with the 18 input-checker cases the independent run passed 30 tests. They cover
completed/explicit-fit-failure/mid-run-interrupted receipt boundaries and nine
invalid SOURCE40 backup cases rejected before any array load. Both independent
review receipts remain separate, and all 42 CSP software cases use synthetic
data or mocks.

On this Codex CPU host, the following is an allowed metadata-only check:

```bash
cd /workspace/few-shot-mi-eeg
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/check_kumar_csp_signed_score_inputs.py
```

## Single future execution command, pending separate parent review

The proposed reservation is one existing CPU worker, no GPU, with 8 GiB
available RAM and 2 GiB free output disk checked before execution. This is one
attempt with a 7200-second consumer limit, then TERM with KILL after 30 seconds;
the preceding metadata/hash preflight consumes additional CPU time. Existing numerical CPU thread
caps in the consumer remain one. This is a resource/time proposal, not a
measured runtime or a paid-compute authorization; incremental monetary cost
stays `null` unless a current applicable authorization is recorded.
The proposed existing CPU venv's actually observed distribution metadata is
Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2,
matching the historical CSP runtime. Obtaining these version strings did not
import the numerical packages. The input checker does not enforce package
versions: the separate parent-reviewed CPU operation must bind that runtime
before execution; do not silently replace dependencies or numerical threads.

After the parent reviews the fixed delivery and separately approves this CPU
operation, in that exact reviewed checkout, the one compound command is:

```bash
bash -o pipefail -o noclobber -c '
  cd /workspace/few-shot-mi-eeg &&
  /workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/check_kumar_csp_signed_score_inputs.py &&
  PYTHONPATH=src:scripts timeout --signal=TERM --kill-after=30s 7200s \
    /workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/analyze_kumar_csp_signed_score_v1.py \
    --epochs research_logs/kumar_cross_session_20261012/csp_development_epochs_run01_20261014 \
    --baseline-root results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z \
    --baseline-r2-receipt research_logs/recovery_20261014/kumar_results_R2_run01.json \
    --config configs/kumar_csp_reliability_20261014.json \
    --output results/kumar_csp_signed_score_20261015/run01 \
    > research_logs/kumar_next_source_operations_20261015/csp_signed_score_run01.log 2>&1
'
```

This command has **not** been executed. First verify the proposed free-resource
reservation on the chosen CPU host. `noclobber` protects the log and the consumer
creates a new output directory with `exist_ok=False`; neither permits silently
overwriting a previous attempt. If preflight, process execution, timeout or disk
fails, preserve all files and the real exit status, stop and return for a new
reviewed recovery decision. Do not auto-retry, resume partially completed
scientific fits, remove old output or rerun a completed diagnostic. An incomplete
run is incomplete evidence. A full run with explicit singular-fit failures
must retain those failures and their unavailable denominators.

Post-execution acceptance would require actual start/exit/logs; all six subject
measurements; actual 240 attempts and all control/failed denominators; saved
model/features/scores/member hashes; a separate independent numerical review;
and genuine off-host export plus R2 full-GET/SHA backup. None is supplied by a
metadata pass or synthetic tests. Array payloads and weights remain outside Git.

The minimum scientific decision now is whether to approve this already frozen
measurement operation. There is no supported new gate or threshold. A later
nested participant/run policy comparison with matched-label/update-budget
controls requires its own scientific freeze after real measurement evidence;
the historical source BA and EEGNet development BA cannot supply that decision.
Offline decoding cannot establish skill retention or clinical efficacy.
