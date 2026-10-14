# EEGNet CPU preparation and formal training plan

Paper: **Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG**.
Prepared 2026-10-13 UTC. This document separates software validation from the
future source-only EEGNet research baseline.

| Work | Current status | Evidence |
| --- | --- | --- |
| Official EEGNet CPU forward/backward and checkpoint replay | Passed on synthetic data; `synthetic=true`, `software_validation_only=true` | `research_logs/kumar_cross_session_20261012/eegnet_software/synthetic_run02/software_validation.json` |
| Leakage, source normalization, validation stopping, evaluation and checkpoint tests | 21 passed; final stricter source inspection test separately passed | `research_logs/kumar_cross_session_20261012/eegnet_software/software_validation_receipt.json` |
| Real development sub-1 adapter inspection | Passed: source train `[40,22,640]`, source validation `[20,22,640]`; zero training or predictions | `research_logs/kumar_cross_session_20261012/eegnet_software/real_source_adapter_inspection_run01.json` |
| Formal EEGNet source fits and real query evaluation | **Pending; not executed or authorized this round** | `configs/kumar_eegnet_20261012.json`: `freeze.ready_for_formal_training=false` |
| Paid GPU use | Not requested; no paid resources created | CPU-only runtime evidence in software validation receipt |

## Input and split contract

Reuse `src/learning_preserving_bci/decoders/eegnet.py`, through the source-aware
wrapper in `scripts/train_kumar_eegnet.py`, and the shared Kumar adapter in
`src/learning_preserving_bci/datasets/kumar.py`. No alternative network is
silently substituted. The source adapter verifies the frozen source identity and
numerical hashes before exposing arrays.

The model takes `[trials, 22, 640]` float32 arrays in volts, with left hand `0`
and right hand `1`. A complete five-second source epoch has 2,560 samples at
512 Hz. The frozen adapter applies the 22-channel epoch average reference,
fourth-order 8–30 Hz Butterworth zero-phase filtering, then `resample_poly(1,4)`
to 128 Hz. These operations are epoch-local and learn no statistics. Partial
epochs remain in the source identity manifest and are excluded without padding,
replacement or label-based selection. This is offline preprocessing.

The independent statistical unit remains the published participant identity.
The fixed development cohort is sub-1, sub-4, sub-7, sub-10, sub-13 and sub-16;
the other twelve identities form the final-test cohort. Cohort assignment uses
identity order rather than performance.

| Partition | Frozen sessions and whole runs | EEGNet access |
| --- | --- | --- |
| Source training | ses-0, run-0 and run-1 | Optimizer and channel mean/scale fitting |
| Source validation | ses-0, run-2 | Cross-entropy epoch selection in evaluation mode only |
| Source query | ses-0, run-3 | Future prediction after complete pipeline freeze |
| Target support | ses-1 through ses-5, run-0 | No fitting or recalibration in this source-only EEGNet baseline |
| Target query | Remaining runs of ses-1 through ses-5 | Future prediction after freeze; no optimizer, BN updates, normalization fitting or threshold tuning |

The real software exercise is restricted to development sub-1 source training
and validation tensors. The adapter currently audits the full participant to
verify frozen identities and preprocessing; the EEGNet inspection selects source
arrays immediately and computes no real model prediction or performance score.
The actual source inspection passed in 6.124 seconds after imports. Both tensors
were finite float32 volts with the verified channel order and 128 Hz sampling;
each partition contained both classes. It performed zero optimizer steps and
did not fit normalization. Its frozen manifest SHA256 was
`ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28`.

## Prespecified model and optimization

The configuration fixes Braindecode 1.2.0 `models.EEGNet`: F1=4, D=2, F2=8,
temporal kernel 64, depthwise kernel 16, mean pools 4 and 8, ELU, dropout 0.5,
spatial max norm 1.0, and automatic final convolution length. Batch normalization
uses momentum 0.01, affine parameters and epsilon 0.001. The configuration records
all constructor arguments. A changed official constructor fails rather than
discarding unsupported settings.

Fit channel mean and standard deviation on source training axes `(trial,time)`
only, with a `1e-8` volt scale floor. Apply those fixed statistics to validation
and all future queries. Training updates batch normalization only on source
training minibatches. Validation and prediction use evaluation mode and
`torch.no_grad()`; a digest covering every parameter, BN buffer, class and learned
channel statistic must remain unchanged through evaluation.

The formal plan uses Adam (learning rate 0.001, betas 0.9/0.999, epsilon `1e-8`,
no weight decay or AMSGrad), unweighted cross entropy, batch size 16 and up to
100 epochs. There is no scheduler, label smoothing or class weighting. Use the
source validation mean cross entropy with patience 15, minimum improvement 0,
and the earliest epoch on ties; restore the best complete state before saving.
Only source training reaches the shuffled loader, with `num_workers=0` and
`drop_last=false`.

Seeds are 20261012, 20261013 and 20261014; deterministic PyTorch algorithms and
the seeded loader are required. No hyperparameter search or performance-driven
selection has been performed. Future summaries must retain every seed and use
the mean seed score within a participant/session before participant-level
aggregation. Seeds do not increase the independent sample size, and no best-seed
selection is permitted.

## Actual software evidence

The final synthetic command was:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python scripts/train_kumar_eegnet.py \
  --software-check \
  --output research_logs/kumar_cross_session_20261012/eegnet_software/synthetic_run02
```

It used 16 training and eight validation rows, two epochs and two optimizer
steps per fit, plus a second same-seed fit for exact replay. The recorded software
exercise took 3.791 seconds after imports and includes replay, checkpoint writing
and hashing. Forward/backward losses were finite; evaluation state and
probabilities survived checkpoint loading exactly. No query predictions or
accuracy metrics were computed. This small exercise is not a formal training
benchmark or evidence of real EEG decoding performance. The earlier
`preliminary_run01/` synthetic receipt is preserved; `synthetic_run02/` identifies
the final checkpoint format and guarded implementation.

The 21 tests cover rejection of query roles, wrong validation runs, duplicate
IDs, cross-subject rows and fractional labels; query signal/label isolation;
source-only normalization; validation without state or gradient updates;
patience stopping and best-state restoration; deterministic seed replay;
checkpoint byte/configuration/seed/selection/identity tampering; and formal
freeze gating. The real-inspection test refuses any model fit or prediction.
Owned-file Ruff validation passed. The observed 13 warnings are Braindecode's
deprecation notice for the explicitly recorded `final_layer_with_constraint=false`
setting; the architecture remains unchanged in this preparation.

Checkpoints contain tensor state and a UTF-8 JSON context stored as a uint8
tensor. The verified checkpoint SHA256 binds configuration, seed, source IDs,
selected epoch and loss history as well as weights and channel statistics.
Loading verifies the file hash first, uses
`torch.load(map_location="cpu", weights_only=True)`, compares the bound context
to the strict JSON sidecar, verifies state digests and restores evaluation mode.
Loading constructs no optimizer. Existing evidence paths cannot be overwritten.

## Resources and future freeze gate

Actual runtime: Python 3.11.16, PyTorch 2.8.0+cpu, Torchaudio 2.8.0+cpu,
Braindecode 1.2.0, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2.
The recorded software run used one PyTorch thread. PyTorch reports CUDA build
`null`, CUDA availability `false` and zero CUDA devices; GPU access or a free GPU
has not been assumed.

The planned maximum is 18 participants × three seeds = 54 serial fits, at most
5,400 epochs. Source training has at most 40 eligible rows, so batch size 16 gives
at most three optimizer steps per epoch and 16,200 optimizer steps overall.
This is a compute-count bound, not a wall-time or monetary estimate. A
representative source-only benchmark and explicit execution authorization are
still needed before formal EEGNet fitting. If a benchmark estimates `T` seconds
per complete fit, serial CPU compute hours are `54*T/3600`; preprocessing,
checkpointing and reporting must also be budgeted. The synthetic timing above
does not supply `T`.

No paid hourly rate has been supplied. A future paid resource estimate would be
`compute_hours * verified_hourly_rate`, plus verified ancillary costs; its cost
is currently unknown. Paid GPU creation would require a concrete budget and the
user's explicit approval. This preparation neither creates compute resources
nor asks for paid GPU permission.

Before future formal execution, freeze and verify the protocol configuration,
canonical split manifest, training settings, preprocessing, cohort, seeds and
epoch-selection rule; record any source-only development decisions. The
embedded training-config digest hashes canonical sorted JSON with its own digest
field set to null. A detached `.sha256` receipt additionally binds the exact
final configuration bytes. Keep `ready_for_formal_training=false` in this round.
Formal query balanced accuracy and confusion matrices, failures and
participant-level uncertainty remain pending. Offline decoding results will not
establish human learning, skill retention or a causal adaptive benefit.
