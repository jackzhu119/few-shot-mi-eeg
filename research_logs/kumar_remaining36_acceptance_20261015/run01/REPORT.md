# Actual remaining36 acceptance and all54 source baseline summary

The actual dot parent confirmation signed at `2026-10-15T08:27:35Z` accepts
every one of the 36 job IDs in the request at fixed commit
`f1d4bf4240747b152e9dcd969ff368eb1ab48b59`. It follows the parent's independent
read of the complete 113810-byte UTF-8 R2 receipt and comparison of all 113
objects / 33666029 bytes, all archive identities and all checkpoint hashes.
The confirmed receipt SHA256 is
`bd52fb3f691d9309ce1cd30a1fa4e92921282399e014a1119b06f06041bdcb1c`.
The actual decision is recorded as user-relayed parent confirmation; it is not
a new cryptographic signature or a new execution authorization.

`parent_confirmation.json` records the actual decision and exact fixed request
SHA256. The 36 individual acknowledgement files bind each job, original model
archive, checkpoint and full-GET receipt. `accepted_jobs_remaining36.json`
records that frozen sequence; `accepted_jobs_all54.json` contains the original
18 entries verbatim, followed by these 36 entries at positions 19–54.
The old18 ledger itself remains byte-identical. No old raw state, claim, failed
attempt, pending request, off-Pod receipt or R2 receipt was rewritten.

| Fixed metadata | SHA256 |
|---|---|
| Historical accepted18 ledger, unchanged | `1ee1868b97e6ff7ea2e42327fe64337cafbb0f8ee6aff19cc24fba5265f9aaa9` |
| New remaining36 accepted ledger | `6de4f15031109629b6d70823e7d8cd3b3feee335adfd7e01d791031a284a8f8d` |
| Combined accepted54 ledger | `013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670` |
| Matching original-job plan for all54 | `28232bfa53515ae3e66acadefa39ee025320cfda0196a5d785631bf4d8f8abcd` |

The existing `check_reuse_identity` metadata gate passed all54 identities and
their actual ACK/R2 bindings. Independent acceptance review checked the old18
prefix, frozen36 order, receipt bytes, per-job archive/checkpoint identity and
unchanged historical flags. It did not load weights or signals. The separate
new stage record now reports all36 trained, off-Pod exported, independently
audited, R2 full-GET verified and accepted. Total accepted is54; remaining source
fits to execute is zero. The original completed controller must not be resumed.

## All54 saved-result description

`scripts/aggregate_kumar_all54_saved_results.py` reuses the original saved-result
archive, argmax/CE and participant aggregation helpers. It reads saved source
validation logits and metadata only; it loads no checkpoint tensors, constructs
no model or optimizer, and performs no fit, model forward or EEG/query read.
All original archives and input text hashes are verified before and after.
The first legacy model uses its already accepted replay archive for saved
logits, binding the same original checkpoint; this is not another fitted model.

Full per-fit and per-participant tables, archive index and analysis receipt are
in `research_logs/kumar_all54_source_aggregation_20261015/run01/`.
There are 54 models but only18 published participant identities. Each summary
first averages all three seeds within participant, then weights participants
equally. Development6 and remaining12 remain separate; all18 is a secondary
descriptive combination.

| Cohort | Participants / models | Source-validation BA | Source-validation CE |
|---|---:|---:|---:|
| Development | 6 / 18 | 53.0556% | 0.6741382380 |
| Remaining fixed cohort | 12 / 36 | 57.3611% | 0.6471200455 |
| All, secondary description | 18 / 54 | 55.9259% | 0.6561261097 |

Historical compute totals are2871 epochs /8613 optimizer steps. Five models
predict only one class;12 select epoch1 and11 reach the100-epoch cap. Mean
within-participant three-seed BA range is18.8889 percentage points, with a
maximum45 points. These source-validation variability and class-collapse findings are preserved, without
choosing a seed or changing an epoch/threshold rule.

Source validation selected the checkpoint epoch. Following the prior saved
validation analysis, no confidence interval or hypothesis test is computed for
these selection-set scores. They do not establish untouched-query performance,
adaptive-gate utility or a benefit over the existing CPU baselines. The overall
mean and substantial seed variation support reporting source-validation variability; they
do not justify model search or an adaptive rule. Prior cohort exposure remains
disclosed. Offline decoding cannot establish skill retention or clinical effect.

## Verification and next executable step

Related acceptance/identity/R2 gates and saved-metric tests passed19 cases;
the aggregation's targeted tests passed6 cases (including4 shared metric tests).
These overlapping runs are not presented as25 distinct tests. Owned Python
files passed Ruff. The full unrelated suite was not rerun.

The exact currently executable all54 metadata check and its full ledger/plan
pins are in `docs/kumar_all54_next_baseline_step_20261015.md`. This uses the
existing CPU checker in one process. It can be run by dot without training,
query access or Pod operation. The completed saved-logit summary is ready to
use directly; no rerun is required to obtain the reported results.

The next scientific baseline is already defined: source-only EEGNet with all
accepted checkpoints, unchanged preprocessing, source normalization and BN,
and the original source-query/target-query split and participant aggregation.
The one actual implementation gate still open is a separately frozen query-only
checkpoint-reuse evaluator with its exact input scope and state-unchanged
checks. The present source-validation kernel explicitly rejects query rows;
generic `formal_train` would retrain all models and is forbidden. This delivery
does not invent a query command or interpret the acceptance ACK as unblinding.
Prepare that minimal evaluator from the existing frozen rules before dot binds
any separate query execution. No new strategy, fit or Pod action is released.

The new text acceptance and aggregation evidence is also archived under a new
private R2 evidence prefix; its separate full-GET receipt and closing check are
stored here. That text backup is distinct from the already parent-confirmed
113-object original-model receipt and does not alter it.
