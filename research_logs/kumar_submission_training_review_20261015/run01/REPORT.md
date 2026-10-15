# Saved EEGNet training and validation review for manuscript revision

This review uses the **54 already accepted source models**, their complete saved
epoch histories, and existing source/target query metric tables. It adds no fit,
model load, query-array access, forward pass, seed choice, or policy. All three
fixed seeds remain in every participant endpoint. The 54 models represent **18
published participant identities**, not 54 independent participants. Development6
and remaining12 remain separate; all18 is a secondary description.

## Independent source-query weakness precedes target-session evaluation

| Frozen EEGNet description | Development6 | Remaining12 | All18, secondary |
| --- | ---: | ---: | ---: |
| Participants / source models | 6 / 18 | 12 / 36 | 18 / 54 |
| Source independent-query BA | 52.7778% | **52.9167%** | 52.8704% |
| Five-target-session mean BA | 52.3087% | **51.5783%** | 51.8218% |
| Target minus source BA, descriptive | −0.4691 pp | **−1.3384 pp** | −1.0486 pp |

Source query is a held-out whole run in the same source session (20 trials per
participant). Target endpoints first average the three seeds within each
participant/session and then the five target sessions, as in the saved analysis.
The small source-to-target difference is descriptive: the source run is small,
the target endpoint aggregates five sessions, and no new interval or causal
attribution is introduced. **The target result cannot chiefly be attributed to
cross-session drift when independent source-session discrimination is already
near chance.** These observations diagnose this small-source-data, fixed-pipeline
benchmark; they do not establish that neural decoders generally fail or identify
the causal contribution of architecture, optimization, artifacts, or signal.

## Full saved histories, not inferred execution from empty console logs

All54 original `weights.json` files contain consecutive, finite histories for
**2,871 epochs / 8,613 optimizer steps**. All54 epoch selections and stopping
reasons match the frozen earliest minimum validation-CE rule, patience15 and
maximum100 epochs. Source training uses40 labeled trials; the separate20 labeled
source-validation trials select the epoch. The source-validation BA is therefore
not an independent performance estimate.

| Descriptive training property | Development6 models | Remaining12 models | All54 models |
| --- | ---: | ---: | ---: |
| Number of models | 18 | 36 | 54 |
| Median executed epochs | 62.5 | 29.5 | 48 |
| Median selected epoch | 47.5 | 14.5 | 33 |
| Selected epoch1 | 4 | 8 | 12 |
| Reached maximum100 epochs | 1 | 10 | 11 |
| Final training CE below first-epoch training CE | 18 | 35 | 53 |
| Final validation CE above first-epoch validation CE | 10 | 19 | 29 |
| Selected validation CE at or above ln(2) | 5 | 11 | 16 |
| Selected source-validation single-class prediction | 1 | 4 | 5 |

The remaining12 median training CE moves from0.704246 at epoch1 to0.596543 in
the final epoch; median validation CE is0.693048 at epoch1,0.691847 at the selected
epoch and0.692351 at the final epoch. These are medians over36 repeated-seed fits,
not independent-participant inferential summaries. The all54 corresponding
training medians are0.708715 and0.504305; validation medians are0.692989,
0.690641 and0.692943. Loss typically falls on the optimized source training
examples without consistently improving held-out validation. Twelve models
select their initial epoch, while11 reach the100-epoch cap; these distinct
patterns do not support a single claim that every model either converged or was
undertrained. No training schedule or hyperparameter is changed on this basis.

Training CE is the batch-weighted training-mode loss accumulated while parameters
change within the epoch; validation CE is evaluated after the epoch in eval
mode. Dropout and batch-normalization mode also differ. Their numerical gap must
not be treated as a calibrated estimate of overfitting. Validation trends and
weak independent source-query performance together are **consistent with limited
generalization in this exact40-training-trial regime**, without proving a unique
mechanism.

The saved `training.log` is empty for37/54 archives (the first fit and36 later
fits). This is explicitly retained; it is not evidence of zero Python execution.
The complete JSON histories, saved selection metadata, epochs/steps and accepted
original archive hashes provide the available training-curve evidence. No
missing curve was reconstructed or fabricated.

## All seeds and collapses remain visible

| Remaining12 seed | Source query BA | Five-session target BA |
| --- | ---: | ---: |
| 20261012 | 52.9167% | 52.4249% |
| 20261013 | 51.2500% | 49.9401% |
| 20261014 | 54.5833% | 52.3699% |

These are equal-participant descriptive means, not candidates for seed selection.
The average within-participant range of target mean BA across the three seeds is
8.06pp in remaining12, with a maximum24.62pp (sub-17). Sub-9 has a22.54pp range.
The same source-query seed range averages19.17pp and reaches55pp. A source query
run contains only20 examples, so these discrete ranges are reported without
turning them into a population uncertainty estimate. They demonstrate why the
prespecified three-seed average and participant unit must be retained.

Across all54 models there are16 collapsed seed-session query outputs:2 source
and14 target. Remaining12 contributes2 source and7 target; development6 contributes
0 source and7 target. Counts refer to **model-seed/session outputs**, not16
participants. These outputs remain in all performance tables. The full
per-seed/session identities are already in the saved query metric CSV; this
review preserves their flags and sums them without rerunning predictions.

## Integrity and reproduction

The portable input index binds54 relative archive filenames to the accepted
job IDs, subjects, seeds and complete SHA256 hashes. All54 original archives and
**753 payload members** were length/SHA verified against their original manifests.
Binary members were streamed to SHA256 only; weights were never deserialized.
`review_receipt.json` records the exact `training.log`, `weights.json`,
training-config, manifest and execution-source member SHA256 for every archive.
Historical manifest/fit backup flags are left unchanged; current acceptance comes
from the real accepted54 ledger.

See `README.md` for portable commands and the compact outputs. The earlier
text-only postprocessing output in `initial_postprocessing/` is retained with
its exact executed script after adding the requested portable archive index.
This was not a second scientific attempt: both operations read saved text and
perform zero fitting/inference. New public CSVs contain histories and metrics,
not normalization arrays, learned weights, EEG, or private credentials.

The seven targeted synthetic tests check safe member handling, binary members
not being parsed/returned, archive hashes, epoch-selection ties, patience,
truncated histories and output preservation. Scoped Ruff also passes. Main
scientific configurations, original metrics and acceptance ledgers are inputs
and are not modified by this review.
