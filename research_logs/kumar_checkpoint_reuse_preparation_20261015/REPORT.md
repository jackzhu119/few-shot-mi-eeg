# Read-only checkpoint reuse preparation; execution remains closed

Prepared from fixed `65fe52ee2cefa43f091cf466dac3682b4c6e5745` on the existing
research branch. The accepted development ledger remains 18, with SHA256
`1ee1868b97e6ff7ea2e42327fe64337cafbb0f8ee6aff19cc24fba5265f9aaa9`.
No old checkpoint, identity, scientific configuration, receipt or claim is
rewritten. The preexisting uncommitted CSP implementation/preparation is preserved.

The new `evaluate_kumar_checkpoint_reuse.py` is an inference-only CPU kernel for
the accepted checkpoint's exact existing source-validation sequence. Loading
verifies original archive/member hashes, actual acceptance and R2 evidence,
weights-only tensor context, source identities and frozen state. Evaluation
requires frozen per-trial processed-signal hashes, original labels and a real
separate parent authorization for non-software inputs. It creates no optimizer
and exposes no training or query API. Parameters, BN, normalization, classes,
context, gradients, evaluation mode and evidence-file bytes must remain unchanged.
Real CE must meet the original 1e-7 tolerance. No real CPU/GPU CE comparison is
claimed as performed or passed in this preparation.

The source-validation kernel does not implement an EEG reader or a formal query
adapter. The future caller must verify original source bytes and preprocessing.
The archived training device remains CUDA; this software kernel's execution
device is explicitly CPU. Its tests use synthetic random initialization without
fitting/backward/optimizer construction. The existing generic formal trainer
would refit accepted models and is forbidden.

The final kernel has SHA256
`838f3ed7b8f67c65dcf27b3ef43aace29db9464c8cdaae730be5dfebc92ba4e2`.
53 kernel tests plus nine metadata-only proposal tests pass: 62 total, with 22
documented upstream warnings for the unchanged architecture setting. Scoped
Ruff passes. The independent final kernel review additionally intercepts all
17 available original archives before real tensor loading. The first original
model archive is not local; its original manifest/sidecar history and synthetic
legacy compatibility test are reviewed, and the different first replay archive
is not substituted. No accepted checkpoint is loaded or forward-evaluated.

The separate formal-freeze proposal has SHA256
`3897af0474ae14b75e51ff06ca200f73e3bb26cf11adebcc32e79fe5662a8aea`;
its `.proposal.sha256` fixes review bytes only. Execution permissions remain
false, and nine execution bindings remain null. Known scientific digests,
all 18 reusable model identities and all 36 possible remaining source identities
are pinned. The remaining-input proposal contains exactly 253 files /
196,740,994 bytes, including 36 source EDFs and no query EEG or query-label
files. It is metadata, not a download or a verification receipt.

The possible remaining compute-count ceiling is 36 fits, 3,600 epochs and
10,800 optimizer steps; currently authorized new fits and real forwards are zero.
The completed old 19,800-second run deadline is not reset or reused. A new
source operation, wall deadline, resource/cost scope, runtime/disk verification,
bounded export/recovery/R2 contract and actual parent review must be frozen
separately. No new paid resource, credential or Pod operation is performed.

The latest CSP/source-score review makes no strategy claim. The older observed
CSP source BA of 62.92% and qualified split-half reliability are not the latest
frozen 240-pipeline exact-control and signed-class-margin stage. Matching final
execution evidence for that stage was not located in this checkout. No executed
nested matched-budget policy comparison is available. Source EEGNet validation
BA 53.06% selected the epoch and cannot supply a gate. The minimum scientific
decision is to retain the source-only baseline preparation, reconcile or leave
the measurement evidence pending, and keep adaptive-policy execution closed.

Exact freeze fields, scope, budget and one safe metadata-check command are in
`docs/kumar_checkpoint_reuse_and_formal_freeze_proposal_20261015.md`.
`docs/kumar_csp_source_score_readiness_20261015.md` binds the completed,
planned and unavailable scientific evidence. The primary CPU contrast, seed
aggregation, participant unit, previous negative results and exploratory limits
are unchanged. This is code, tests and a proposal, not a passed scientific gate.

Use `final_preparation_validation_run02.json`,
`independent_kernel_review_run02.json`, `independent_proposal_review_run02.json`
and `proposal_check_run02.json` for the final version. Earlier draft reviews
and validation logs are retained with their original hashes. The final proposal
review passes 109 checks; its nine unresolved fields are a union with distinct
source-replay, source-fit and query applicability. No actual parent execution
authorization has been created.
