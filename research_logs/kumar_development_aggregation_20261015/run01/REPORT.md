# All 18 frozen development fits: saved source-validation description

The frozen EEGNet development queue is complete for six development participants
and all three prescribed seeds per participant. This analysis reads only the
already saved validation logits, labels, source identities, checkpoint metadata
and training histories. It performs zero fits, zero model forward passes and
zero query evaluation; it loads no EEG or checkpoint tensors.

Across participants, after equally averaging the three seeds within each person,
mean source-validation balanced accuracy is **53.06%** and mean cross entropy is
**0.674138**, compared with the descriptive uniform binary-predictor reference
`log(2) = 0.693147`. Each person contributes the same 20 source-validation trials
to all three seeds, with ten trials per class. There are **120 unique validation
trials**, 360 saved prediction rows and **six independent participants**.

| Participant | Mean balanced accuracy, all seeds | Seed range | Mean CE |
|---|---:|---:|---:|
| sub-1 | 58.33% | 55–60% | 0.683085 |
| sub-4 | 50.00% | 40–60% | 0.693582 |
| sub-7 | 50.00% | 45–55% | 0.678633 |
| sub-10 | 40.00% | 30–50% | 0.692729 |
| sub-13 | 56.67% | 50–70% | 0.675250 |
| sub-16 | 63.33% | 60–65% | 0.621550 |

The source readout is heterogeneous. Three participants have a mean BA above
50%, two equal 50% and one below 50%; these are descriptive counts, not
participant significance tests. The variation between seeds reaches 20
percentage points in sub-4, sub-10 and sub-13. All sub-16 seeds are between 60%
and 65%, while sub-10 remains at or below 50% for every seed. With only 20
validation trials per person, BA moves in five-percentage-point increments.
This does not justify choosing a favorable seed or increasing statistical n.

One result, sub-13 / seed20261013, predicts only the left-hand class: BA is 50%,
left recall 100% and right recall 0%. It remains included. Four fits select
epoch 1. Sub-1 / seed20261014 reaches the frozen maximum of 100 epochs and
selects epoch 93; it is retained as a maximum-epoch termination, not described
as 15-epoch patience termination. Total execution across the 18 saved histories
is 1,027 epochs and 3,081 optimizer steps.

These scores use the validation run that selected checkpoint epoch by the
frozen early-stopping rule. They are **development descriptions**, not an
independent estimate of generalization, a confirmatory departure from chance,
or evidence for a task-aware adaptation gate. No confidence interval or p value
is attached to this epoch-selected readout. No comparison with the existing CPU
target-query scores is made because the evaluated partitions differ. Offline
source decoding cannot establish skill retention, learning or clinical effect.

The saved histories and logits now support a concrete negative/qualified
finding: source-only EEGNet development results are near chance on average,
with marked participant and seed variation and one class-collapse result.
This supports retaining the complete seed distribution and explicit collapse
diagnostics; it provides no basis to promote the unvalidated task/power gate.
No new rule, threshold, seed or scientific protocol is selected here.

## Reproduction and integrity

The deterministic script is
`scripts/aggregate_kumar_development_saved_results.py`. Run from the repository
with the existing CPU environment and the private originals at the indexed paths:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/aggregate_kumar_development_saved_results.py \
  --archive-index research_logs/kumar_development_aggregation_20261015/saved_archive_index_run01.json \
  --output /workspace/private_model_receipts/all18_descriptive_replay_unique_output
```

The output path must not already exist. No archive is extracted or changed.
Every archive byte and every manifest-listed member length/SHA256 is checked.
The first fit uses its previously archived source-only replay package; the
other 17 use their original result packages. Frozen plan order, all 18 accepted
IDs, config and split hashes, source-validation trial identity and labels,
checkpoint metadata hash bindings and earliest-minimum epoch selection are
checked. All 18 saved CE values reproduce within the unchanged `1e-7` absolute
tolerance; the largest discrepancy is `3.24826470166073e-8`.

The first four missing local saved-prediction packages were retrieved from their
existing private R2 objects: four full GETs, 604,160 bytes, zero failures.
`source_archive_R2_readback_receipt.json` preserves that exact readback receipt;
this is an additional source-analysis retrieval, separate from the prior
38-object batch backup receipt. Credentials and binaries are absent from Git.

`per_fit_source_validation.csv` retains every fit, recall and prediction count.
`per_participant_source_validation.csv` contains the independent statistical
units. `aggregation_receipt.json` binds archive, logits, metadata, ledger,
configuration, split and script hashes plus the Python/NumPy versions.
`summary.json` contains the scoped machine-readable conclusions. The frozen
query/formal-training gates remain closed; acceptance of development execution
does not release a further experiment.
