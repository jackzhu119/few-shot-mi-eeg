# CSP4 / source-score evidence and the next scientific decision

Reviewed against `65fe52ee2cefa43f091cf466dac3682b4c6e5745`. The current
evidence does **not** support a new minimal adaptive strategy or a gate threshold.
The 18 accepted EEGNet checkpoints can support preparation of the prespecified
source-only evaluation path; checkpoint acceptance and source validation scores
do not establish adaptive benefit. This review performs no fits, forward passes,
EEG reads, query reads, Pod operations or seed selection.

## Completed evidence

The completed earlier supervised CSP diagnostic is
`research_logs/gpu_preparation_20261014/supervised_csp_run01/summary_corrected.json`
(SHA256 `de2ff0c8cd054aac4749b32badca8ccae09897ba28a3797d034d90e1271dc5c2`).
It reports source whole-run transfer BA **62.9167%**, participant-bootstrap 95%
interval **[52.9167%, 72.0833%]**, and mean support split-half direction cosine
**0.298181**, interval **[0.049077, 0.550874]**. The six participant BA values are
70%, 50%, 72.5%, 42.5%, 67.5% and 75%, in frozen development order. These are six
statistical units, after averaging folds or five support sessions within person.

The original records contain 12 observed TRAIN20 source folds, 96 seeded
training-label-shuffle control pipelines and six additional SOURCE40 pipelines
for support coordinates: 114 recorded pipelines. They contain 240 source TRAIN
rows and 596 current-support rows, with zero query/final-participant inputs.
This review independently recomputes each observed fold BA from its saved labels
and predictions, checks source/holdout identities and participant means, and
matches all six original participant-file hashes to the corrected summary.
The original failed string/integer-key aggregation and its correction remain
preserved; no fit or bootstrap is repeated here.

Eight of 30 support sessions have negative half-to-half cosine. Eleven have
opposite signs in the two saved source-axis contrasts; two have both contrasts
negative. These counts describe the saved source-axis diagnostic, not the later
frozen LDA score margins. Cosine can remain positive under a common class
reversal, and the product of two negative contrasts is positive. A useful
measurement coordinate therefore does not supply a valid decision threshold.

The fixed power diagnostics remain negative or inconclusive. Participant mean
source BA is 51.67% for power44, 50.00% for PCA4 and 54.17% for motor6; every
participant-bootstrap interval includes 50%, and every mean support split-half
cosine interval includes zero. They justify neither choosing a feature winner
nor claiming that all EEG task information is absent.

The accepted EEGNet source-validation mean BA, 53.06%, uses the same run that
selected checkpoint epoch. Its one collapsed prediction result and all three
seeds remain included. It is a descriptive development readout, not an
independent policy-selection signal. Its partition differs from both CSP source
TRAIN run transfer and the historical CPU query comparison; these scores cannot
be used as a matched method ranking.

## The latest frozen CSP4 / source-score stage has no located execution result

`configs/kumar_csp_reliability_20261014.json` and
`docs/kumar_csp_reliability_plan_20261014.md` define a later, more complete
diagnostic. Their bytes match the archived freeze receipt:

| Binding | SHA256 |
|---|---|
| CSP4 configuration | `4f71724c6be77696bbf8764e7de4795ceb1c9c4a315c1c2b266cc201a1c3da18` |
| CSP4 plan | `b942fdb6265594d632dbfb70a536bd576b9e2d5b13871f8d4e8e4c9721a8b34f` |
| Independent methods review | `f53592721e4cff14b7d8466234c99d299f81870e0937346f92f1872b86532600` |

That plan requires 240 source pipelines, including 12 observed folds, with both
CSP and LDA refitted for each training-label phase, and exact 20 × 20 joint
phase scores. It reuses six existing primary SOURCE40 model states, preserves
their signed LDA scores, and measures separate class margins, score bias,
recalls and collapse alongside vector reliability. The old diagnostic instead
fitted its own six SOURCE40 models. Its eight random-label controls per source
fold do not substitute for this exact phase design. Its bootstrap seed is
20261014; the later frozen plan uses 42. Neither historical setting is changed.

The current checkout contains the later plan, restricted-input preparation and a
static preparation review. No matching `measurement_receipt.json`, saved
`subject_measurement.json` result, or signed-score execution/numerical-review
receipt was found in the tracked or ignored `research_logs/` and `results/`
inventories. This is a statement about available local evidence, not proof that
an external execution never happened. Missing results are left unavailable.
Preparation and static review must not be represented as real diagnostic results.

Four preexisting untracked areas are preserved without adoption, staging,
modification or execution. Their relevant exact local versions are:

| Preexisting local artifact | SHA256 |
|---|---|
| `scripts/analyze_kumar_csp_reliability.py` | `f2a0eb4831d78c4cbef54656c56c5ee7c085c697eff287c64dd535a5bdb7a5ad` |
| `tests/test_kumar_csp_reliability.py` | `d7f794e95b715f5c6e431ed0556339b56cb103a39374e46550bc9f4b64eae404` |
| `csp_development_epochs_run01_20261014/preparation_receipt.json` | `f4b3a3bda5533d64c16c9d55e0c15bd934ade5d86c07cf444f340ab7a75e7964` |
| `csp_implementation_review_run01_20261014/preparation_static_review_receipt.json` | `f8ca93c82713d1ab9c6e174f3a00438f2b3b4dfcb556e78215317b989fb9ead5` |

The last two paths are relative to
`research_logs/kumar_cross_session_20261012/`. Their hashes make the limitation
inspectable; they do not make these uncommitted artifacts part of a frozen
executable delivery. The diagnostic script would fit new CSP/LDA models and
must not be invoked in this no-fit round.

## Minimum decision and remaining gates

Retain the prespecified source-only EEGNet baseline and prepare strict reuse of
the accepted 18 checkpoints. Keep formal query access, the remaining 36 source
fits and any new adaptive strategy closed until separately frozen operational
and scientific proposals receive the required parent review. A source-only
baseline freeze can be considered separately from an adaptive-policy freeze;
it does not establish or authorize a task-aware gate.

The original frozen task-aware plan explicitly requires stable development
evidence before implementing a new strategy. No separately frozen and executed
nested participant/run strategy comparison is available. A nested evaluation
must compare the same label/update budget against always-frozen, always-update,
fixed-mixture and covariance-gate controls. Source run transfer and support
reliability do not measure the benefit or harm of choosing an update.

The smallest next policy decision is to reconcile or obtain immutable execution
and independent-review evidence for the already frozen CSP4/source-score stage,
or retain it as pending. This round does not execute that stage. Only if its
measurement evidence supports proceeding would a separate minimal nested-policy
protocol be justified. Such a protocol still lacks exact outer participant and
inner grouped-run assignments, one fixed scalar and orientation/degeneracy rule,
the update operator and update budget, the inner-only threshold objective, exact
control settings, participant-level benefit/harm/collapse endpoints, and bound
code/input/operational budgets. No values are selected from existing scores here.

Later strategy work on the already inspected cohort remains exploratory.
Circular controls do not certify exchangeability or MI physiology. Offline
decoding establishes neither human learning or retention nor clinical benefit.
The machine-readable review in
`research_logs/kumar_checkpoint_reuse_preparation_20261015/reliability_review_run01.json`
retains all source hashes, saved-row checks and the distinction between completed
older results, the later frozen plan, and the unavailable nested-policy evidence.
