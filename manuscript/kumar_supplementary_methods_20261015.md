# Supplementary methods

**Longitudinal Motor-Imagery EEG Decoding: Frozen Baselines, Supervised Recalibration, and Task-Measurement Reliability**

This supplement describes the completed analyses reported in the
[English working draft](kumar_longitudinal_decoding_working_draft_20261015.md),
using their frozen protocols, executed source and saved audit records. It adds
no experiment, statistical result, adaptation rule or permission to execute.
The historical NETBCI material is a separate dataset and analysis record.

## S1. Source identity, chronology and eligible windows

The source was the Kumar2024 derivative at NEMAR `nm000177/v1.0.5`, CC BY 4.0,
bound by the existing 2,705-file selection manifest. The analysis covered 18
published participant identities, six ordered sessions, 360 EDF recordings and
7,200 event identities. Source size/checksum, local SHA256, annotation/event
agreement, channel order, sampling rate, units and frozen numerical window
hashes were checked. Complete raw and processed windows had no exact numerical
duplicates in the frozen split audit. These checks do not independently
establish biological identity or the accuracy of derivative-reported calendar
timestamps. Session order and within-session run order were checked against
the source acquisition metadata.

Development IDs were sub-1, sub-4, sub-7, sub-10, sub-13 and sub-16. The fixed
remaining IDs were sub-2, sub-3, sub-5, sub-6, sub-8, sub-9, sub-11, sub-12,
sub-14, sub-15, sub-17 and sub-18. Assignment preceded performance calculations
and used every third numeric published ID, starting at one. Later analysis of
previously inspected test identities remains exploratory.

Exactly five seconds and 2,560 samples at 512 Hz were required for a complete
window. The 44 partial events remained in source/split records and were
excluded from tensors without padding, replacement or selecting another run.
The included role counts were:

| Role | Fixed whole-run assignment | Included windows across 18 IDs |
| --- | --- | ---: |
| Source training | ses-0, run-0 and run-1 | 720 |
| Source validation | ses-0, run-2 | 360 |
| Source query | ses-0, run-3 | 360 |
| Target support | ses-1 through ses-5, run-0 | 1,786 |
| Target query | All other target-session runs | 3,930 |

Each person had 40 training and 20 validation windows. The fixed first support
run allowed at most 20 events, at most 10 per class, before partial exclusion.
Among 90 target sessions, 14 had 19 included support events and 76 had 20.
There was no replacement or accumulation of support from other target sessions.
The query inventory retained all 4,320 event identities, including 30 partial
exclusions, yielding 4,290 included queries. The saved-result comparison
verified the same trial IDs, labels, sessions, runs, roles and included-window
hashes for every CPU method and every EEGNet seed.

## S2. Epoch-local preprocessing and descriptive coordinates

The channel order was F7, F3, Fz, F4, F8, FC5, FC1, FC2, FC6, C3, Cz, C4,
CP5, CP1, CP2, CP6, P7, P3, Pz, P4, P8 and POz. Labels were left hand = 0
and right hand = 1. MNE numerical input was in volts; the native physical
metadata used microvolts. Each epoch independently underwent:

1. Common-average reference over all 22 channels at each sample.
2. Fourth-order SciPy Butterworth SOS band-pass filtering at 8–30 Hz with
   `sosfiltfilt` and its default odd padding.
3. `resample_poly(up=1, down=4)` with its default Kaiser-5 window and constant
   padding, yielding 22 × 640 float32 values at 128 Hz in volts.

These operations fitted no state across epochs. Zero-phase filtering is an
offline convention. A raw within-window peak-to-peak value above 250 µV in any
channel generated a fixed quality flag. All 1,512 flagged complete windows
remained among the 7,156 primary windows. No expert artifact certification or
verified reconstruction of the acquisition CPz reference was claimed.

The predefined power description used Welch estimates with a Hann window,
256-sample segments, 128-sample overlap, constant detrending, density scaling,
one-sided output and mean averaging. Mu power integrated 8–13 Hz and Beta
power 13–30 Hz by trapezoidal integration including band-edge bins. Features
were `log10(max(power, float64_tiny))`, ordered channel-major with Mu then
Beta, giving 44 features. They are absolute task-window powers in V² before
the log transform, not baseline-normalized ERD.

Covariance descriptions used a fixed 21 × 22 Helmert basis to remove the CAR
null direction. Epochs were time-centered, covariance used the `n−1`
denominator, and trace-normalized covariance was shrunk as
`0.9*C + 0.1*I/21`. The source-training-only affine-invariant Riemann mean
used an arithmetic initializer, unit step, at most 100 iterations and tolerance
`1e-10`. Other roles supplied distances to that fixed reference, never a refit.
A source-training StandardScaler and full-SVD PCA retained four components
without whitening. Primary preprocessing and decoder fits did not change in
the fixed quality-flag, count-matched or C3/Cz/C4 descriptive sensitivities.

For the pre-frozen drift associations, the covariance measure was target-query
mean distance minus source-query mean distance. The task-axis measure was the
one-dimensional Wasserstein distance between target and source query projections
onto the fixed source-training right-minus-left power direction. Target labels
did not construct that drift variable; labels were used for BA and explicitly
supervised retrospective class descriptions. These remaining-cohort associations
were descriptive analyses, not development-only reliability probes or policy
selection.

## S3. Decoder definitions and label budgets

### S3.1. CPU baselines

CSP used four components, Ledoit–Wolf regularization, log mean-square features
and `norm_trace=False`; LDA used `solver="lsqr"` and automatic shrinkage.
The baseline seed was 42 and there was one prespecified configuration.
Source-only CSP/LDA fitted source training and then froze both stages.
Frozen-CSP/LDA recalibration reused source filters and refitted LDA on source
training plus current support. Full refitting fitted both CSP and LDA on that
same union. Every fit recorded exact trial IDs; validation and query were
forbidden from fitting or selecting the CPU pipeline. Source-query predictions
used the same source model for all three method labels.

### S3.2. Source-only EEGNet

The official `braindecode.models.EEGNet` implementation used F1=4, D=2, F2=8,
temporal kernel 64, depthwise kernel 16, mean-pool sizes 4 and 8, ELU, dropout
0.5, automatic final-convolution length and spatial max norm 1.0. Batch
normalization used momentum 0.01, affine parameters and epsilon 0.001.
`final_layer_with_constraint=false` and `norm_rate=0.25` were retained exactly
as recorded in the executed configuration.

For each participant, channel mean and standard deviation were fitted over
source-training trials and time only, with a `1e-8` V scale floor. The optimizer
was Adam: learning rate 0.001, betas (0.9, 0.999), epsilon `1e-8`, zero weight
decay, no AMSGrad or scheduler. Training used unweighted cross entropy, no
label smoothing, batch size 16, shuffled training rows, `drop_last=false`,
`num_workers=0` and at most 100 epochs. The source-validation mean cross entropy
selected the checkpoint, with patience 15, minimum improvement zero and the
earliest epoch on ties. The complete best state was restored. All seeds
20261012, 20261013 and 20261014 were retained; no favorable seed was selected.

The 54 completed source fits used 2,871 epochs and 8,613 optimizer steps.
Eleven reached the 100-epoch cap; reaching that cap was not relabeled as a
patience termination. Validation BA/CE was descriptive because validation
selected epochs. It received no new population interval or hypothesis test.

For the accepted query evaluation, original package/checkpoint bytes and
embedded source context were verified before loading with
`torch.load(map_location="cpu", weights_only=True)`. Evaluation mode,
disabled gradients and inference mode prohibited optimizer, parameter,
batch-normalization and normalization updates. The original state digest was
recorded before and after each model's predictions. Labels supported only the
fixed metrics; class prediction was untuned logit argmax. The original source
CE replay absolute tolerance remained `1e-7`. Independent saved-result audits
checked the recorded states and arithmetic without a second model forward.

### S3.3. Comparison boundary

| Pipeline | Source estimator/optimizer labels | Additional source-validation labels for selection | Current support labels for fitting |
| --- | ---: | ---: | ---: |
| Source-only CSP/LDA | 40 | 0 | 0 |
| Frozen CSP + LDA recalibration | 40 | 0 | 19/20 |
| CSP/LDA refit | 40 | 0 | 19/20 |
| Always-frozen EEGNet, each seed | 40 | 20 | 0 |

The CPU validation run was not used for model selection or fitting. EEGNet
therefore had different source-label use, and only the CPU updates used target
support. Equal query identities do not establish equal information or compute
budgets. The two CPU update methods shared exact labeled fitting IDs, although
updating both stages and updating LDA alone involved different computations.
The original full-refit versus frozen contrast deliberately added current
support; it was not an equal-target-label architecture comparison.

## S4. Endpoints, resampling and evidence hierarchy

BA was the mean of left and right recall. Confusion counts, recalls, predicted
class proportions and single-class prediction indicators accompanied each
session. CPU target endpoints first averaged five sessions per participant.
EEGNet first averaged all three seeds within participant/session, then averaged
five target sessions per participant. Source query remained separate. Cohort
means weighted participants equally, never pooled trials or treated seeds and
sessions as additional independent people. Development6 and remaining12 were
separate; all18 was a secondary exploratory combination.

The primary contrast remained full CSP/LDA refit minus source-only CSP/LDA in
remaining12, with paired participant resampling. Mean/BA descriptive intervals
used 10,000 draws with seed 42 and the 2.5th/97.5th percentiles. The saved-query
comparison and decoder endpoint summaries used lexicographic participant-ID
order. The six-person reliability bootstrap used numeric order 1,4,7,10,13,16,
averaged source folds or support sessions within person first, and used
`default_rng(42)` for 10,000 six-ID samples with replacement. Missing participant
values made the entire reliability interval unavailable rather than silently
changing its participant denominator.

The original descriptive Spearman drift intervals instead used **2,000
participant-block bootstrap draws**, seed 42. Each selected participant
contributed all its session rows together. They did not use 10,000 independent
session or trial samples. Both original drift measures retained 2,000 valid
block draws. The difference between these two resampling designs is preserved.

No new EEGNet-minus-CPU contrast interval, p value, multiple-testing claim or
formal test against 50% was added. The saved comparison reproduced the original
CPU primary contrast, +7.42 percentage points [2.49, 12.48], with nine positive
and three negative participant differences. The LDA-only contrast remained
uncertain. All subsequent same-dataset interpretation remained exploratory
after prior test exposure. No task-aware policy benefited from looking at
these query outcomes.

## S5. Development-only measurement reliability

### S5.1. Fixed low-dimensional power probes

The candidates were standardized 44-dimensional Mu/Beta power, its source PCA4
coordinates and six C3/Cz/C4 Mu/Beta coordinates. Only the six development IDs'
source training and preassigned current support entered the calculations.
Source-run probes trained on run-0's 20 rows and evaluated run-1's 20, then
reversed the roles. Each run contained ten events per class. StandardScaler and
PCA for a fold were fitted to its TRAIN20 alone. The diagnostic classifier
used the right-minus-left class-centroid axis and the midpoint threshold.
It did not reuse a transform fitted on the held-out source run.

The exact Cartesian set of 20 × 20 circular label phases was shared across
the two source folds and three candidates, including identity. Label-dependent
centroid directions and midpoints were recomputed for controls; label-independent
fold scales/PCA could be reused. The 14,400 phase-control fold/candidate
evaluations included the 36 identity/observed probes; these were auxiliary
measurements, not replacements for the primary decoder baseline. All candidates remained;
the highest point estimate did not select a winner.

### S5.2. Supervised SOURCE20 CSP transfer probes

The completed signed-score run02 fitted CSP and LDA anew on each TRAIN20 fold.
Because CSP is label-dependent, every training-label phase refitted both stages.
For each participant/fold, 20 training-label phases produced 20 cached models
and their held-out predictions. Crossing those predictions with the 20 held-out
label phases yielded all 400 joint `(run0_shift, run1_shift)` pairs. Held-out
labels never entered fitting, so caching across held-out phases preserved the
exact full-pipeline controls.

Across six IDs, this produced 240 fitted pipelines—240 CSP plus 240 LDA fits,
including the 12 identity-fold pipelines—4,800 cached held-out trial predictions,
4,800 fold/phase BA evaluations and 2,400 participant/phase-pair twofold means.
All twelve source runs had 20 unique circular label assignments. The observed
value was the identity phase pair `(0,0)`. All 240 attempted pipelines completed;
the implemented expected singular-fit failures would have remained explicit
unavailable values, not exclusions of participants or controls.

### S5.3. Frozen SOURCE40 coordinates and signed scores

Current support used the six existing SOURCE40 baseline CSP/LDA models without
a new decoder fit. For an epoch `X`, the four CSP features were the **natural
logarithms** of mean squared projected amplitude:

`f_j(X) = ln(mean_t((W_j X_t)^2)), j=1,...,4`.

The executed consumer rejected nonpositive/nonfinite power rather than inventing
features. The vector diagnostic fitted a four-coordinate StandardScaler on
SOURCE40 features only, using population variance (`ddof=0`), and applied that
fixed transform to support. Its fixed source direction was
`d_source = mean(z|right) − mean(z|left)` and its unit direction was
`u_source = d_source / ||d_source||` when estimable.

Within each support class, trials were chronologically ordered by acquisition
time, start sample and source row. The first `floor(n_class/2)` entered the
first half and the remainder entered the second; corresponding class halves
were combined. For a half direction `d_h`, the diagnostics retained source/full
support cosine, half-to-half cosine and the signed axis contrast

`A_h = (d_h · u_source) / SD_SOURCE40(z · u_source)`.

This contrast has **no factor of one half**. Its source projection SD used
`ddof=1`. Zero directions, missing classes and non-estimable scales remained
explicitly unavailable.

The separate LDA diagnostic used original unstandardized CSP log features,
saved coefficient/intercept and classes `[0,1]`:

`s = f @ w + b; prediction = right if s > 0, otherwise left`.

The intercept and zero threshold remained unchanged; support was neither
centered nor used to fit a score scale. With `SD_s = SD_SOURCE40(s)` using
`ddof=1`, each half retained the balanced true-class signed margin

`M_h = (mean(s|right,h) − mean(s|left,h)) / (2*SD_s)`.

The factor of one half is part of this score-margin definition. Separate right
margin `mean(s|right,h)/SD_s`, left margin `−mean(s|left,h)/SD_s`, score
location, recalls, predicted proportions, BA and collapse were also saved.
The vector-axis contrast and LDA margin are distinct measurements. Neither is
a calibrated probability or a validated neural-information measure. A positive
half-product can arise from two negative margins, and a positive class contrast
can coexist with both classes on one side of the frozen threshold.

### S5.4. Support controls and denominators

Each current support run supplied all 19 or 20 circular label phases, including
identity, with source features, axes, scales and LDA fixed. The primary control
recomputed classwise chronological halves after every phase. A separate
sensitivity retained the original half indices while rotating labels.
For an estimable observation, the descriptive upper-tail fraction was
`count(available control >= observed) / count(available control)`, retaining
ties and identity without a plus-one adjustment. Attempted, available,
unavailable and unique-assignment denominators were recorded explicitly.
Unverified stationarity, cyclic boundaries and cue-order dependence prevent
treating these fractions as formal permutation p values.

For CSP run02 there were 596 support phases per half method; all 596 were
available for each of four saved control metrics—source/full-support cosine,
half-to-half cosine, vector half-contrast product and LDA half-margin product—
with zero unavailable.
For the three power candidates there were 1,788 phases per method, all available
for each of three metrics; the two methods contributed 3,576 method/phase
evaluations. Phase counts do not add participants. No sign flip, candidate,
confidence cutoff or adaptation threshold was selected from the results.

## S6. Retained outcomes and historical failures

The neural query analysis retained 16 collapsed seed/session outcomes across
seven source-model jobs and seven participants: 14 target and two source
outcomes. The frozen CPU model retained three target-session collapses; its
two updates retained zero. These denominators differ and their raw counts are
not a matched statistical comparison. All participant decreases and all three
neural seeds stayed in the aggregates. The five collapsed source-validation
fits and eleven 100-epoch terminations also remained in the source records.

CSP run02's observed source twofold mean BA was 62.9167% [52.5, 71.6667]; the
participant mean of five support half-cosines was 0.295325 [0.032041, 0.573003].
Among 30 support sessions, signed score half-margins were both positive in 19,
both negative in two and opposite in nine; five sessions had frozen-score
class collapse. These are calibration-pool measurements, not independent
target-query performance of an adaptation rule.

The earlier signed-score run01 actually launched and failed when the resource
observer could not read the host's procfs `children` interface. It retained its
claim, empty consumer log, termination/exit evidence and private failure backup;
there were no saved scientific outputs. An empty log does not prove that no
scientific statement or fit began. Explicitly authorized run02 changed process
monitoring, preserved the original absolute window and scientific consumer,
and completed the 240-pipeline measurement. Its numerical audit reconstructed
629,137 saved-feature arithmetic fields with maximum difference zero; it did
not independently recompute EEG projections or refit estimators.

The older, differently specified CSP diagnostic with random-label controls and
a mean cosine of 0.298181 is a historical record. It does not replace run02's
exact rotations, signed margins, original SOURCE40 reuse and mean 0.295325.
The source-fit batch's initial intent-export pause and subsequent same-run
resume, and the earlier container replacement, also remain in their original
records. Container rebuilding is not described as proof that every unrecorded
historical runtime detail was identical. Corrected audit/schema-reader failures
remain distinguishable from new scientific attempts. No old receipt or producer
stage flag was rewritten to erase these boundaries.

## S7. Recorded software, immutable identities and audit coverage

The CPU baseline used Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3,
scikit-learn 1.7.2 and MNE 1.10.2. Its recorded OMP, OpenBLAS and MKL thread
limits were one. Source GPU provenance recorded PyTorch/Torchaudio 2.8.0+cu128
and Braindecode 1.2.0; the source runtime inventory and per-fit records retain
the observed hardware and container qualifications. The query CPU contract
specified the same Python/NumPy/SciPy/sklearn/MNE versions, PyTorch/Torchaudio
2.8.0+cpu and Braindecode 1.2.0, one PyTorch thread, OMP/OpenBLAS limits of one
and `CUBLAS_WORKSPACE_CONFIG=:4096:8`. GPU fitting and CPU inference are separate
stages; no performance or compute-budget equivalence is inferred.

| Artifact | Full-byte SHA256 |
| --- | --- |
| [CPU frozen protocol](../KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md) | `ac290f0e2c5ca58b3745d7cccd83c3fd265e5be9978f461ea5ed0fe7f645831e` |
| [CPU scientific configuration](../configs/kumar_cross_session_20261012.json) | `f1b2d0fa870493cc2aaab906fe6d8b1227e45b2a270e06700e3ca137fbfe9c89` |
| [Frozen split](../research_logs/kumar_cross_session_20261012/protocol/split_manifest.json) | `ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28` |
| [Executed EEGNet configuration](../configs/kumar_eegnet_gpu_development_20261014.json) | `14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d` |
| [Frozen query protocol](../docs/kumar_frozen_checkpoint_query_protocol_20261015.md) | `061892404460a97dd1d999cec3067a0947b2eb7fec063293cb2e65ee5bf5729c` |
| [Query operation contract](../configs/kumar_frozen_query_operation_20261015.json) | `fb3a429776e77a4ee8de96c8c7f2a833a4d311cedd8f0a9bcec3d0c6e8df225a` |
| [Executed signed-score scientific consumer](../scripts/analyze_kumar_csp_signed_score_v1.py) | `ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3` |
| [Accepted source54 ledger](../research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json) | `013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670` |
| [Original query full-GET receipt](../research_logs/kumar_frozen_query_execution_audit_20261015/run01/r2_full_get_receipt.json) | `15682a07c13d69aa7bd7aca2cf65327aea7c58fb4e8cb1205b195d4b0fcbb9e2` |
| [Saved-query comparison receipt](../research_logs/kumar_frozen_query_comparison_20261015/run01/comparison_receipt.json) | `a45664d75a3b1e84373f4af809715a8adb356a7710ba14d0843894e968cd80ae` |

Historical `execution_enabled=false` and other preparation flags in a frozen
contract were not silently edited. Actual execution authorization, launcher
receipts, audit, private R2 verification and parent acceptance were recorded
separately. The query ran once at commit
`d34703ca5bccf7a5b88a91c2ffb2cba893f7cec8`; its audit delivery was fixed at
`ac5a1f6d014421f0adf6f924a58a7063558b89f7`. The original operator verified
147 private evidence/result objects, 17,608,200 bytes, by full GET/SHA256 with
zero failures. Actual parent acceptance at 2026-10-15T09:49:05Z checked the
complete receipt, identities and saved arithmetic; it did not claim a new
parent network GET, a second forward or rehashing all 147 original objects.

| Evidence layer | Existing record and practical boundary |
| --- | --- |
| Original CPU results and fit access | [Execution receipt](../research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z/execution_receipt.json); exact source/support IDs and unchanged primary contrast |
| Source54 saved validation | [Aggregation receipt](../research_logs/kumar_all54_source_aggregation_20261015/run01/aggregation_receipt.json); no new fit, forward or query from this aggregation |
| Low-dimensional reliability | [Executed report](../research_logs/kumar_cross_session_20261012/lowdim_reliability_dev_run01_20261014/REPORT.md), [frozen plan](../docs/kumar_lowdim_reliability_plan_20261014.md); development source/support only |
| Complete supervised CSP reliability | [Run02 report](../research_logs/kumar_csp_signed_score_execution_20261015/run02/REPORT.md), [scientific summary](../research_logs/kumar_csp_signed_score_execution_20261015/run02/scientific_summary_from_saved_results.json), [methods review](../docs/kumar_csp_reliability_methods_review_20261014.md); saved-feature replay rather than a second EEG projection |
| Query identity and arithmetic | [Query audit report](../research_logs/kumar_frozen_query_execution_audit_20261015/run01/REPORT.md); all54 original archives and 1,189 inputs bound; independent numerical reconstruction without forward |
| Query acceptance | [Actual parent ACK](../research_logs/kumar_frozen_query_acceptance_20261015/run01/parent_acknowledged.json); source54 ledger and historical producer flags unchanged |
| Matched saved-query aggregation | [Comparison report](../research_logs/kumar_frozen_query_comparison_20261015/run01/REPORT.md) and [exact cohort table](../research_logs/kumar_frozen_query_comparison_20261015/run01/cohort_method_endpoint_summary.csv); no newly fitted or inferred strategy |

The original source EEG, checkpoint tensors and binary measurement artifacts
remain outside GitHub. Public source access and data terms are distinct from
the repository's software license and institutional secondary-data requirements.
The [author review checklist](kumar_author_review_checklist_20261015.md) separates
the author's eight actual confirmations from the still-unresolved institutional
determination, final approval and license/release decisions. Completing that checklist
does not change these methods or establish a task-aware, human-learning,
retention or clinical effect.
