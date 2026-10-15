
**Longitudinal motor-imagery EEG decoding: Frozen baselines, supervised recalibration, and task-measurement reliability**

This supplement defines the completed frozen analyses and the separately labeled
post-observation sensitivities reported in the PLOS ONE submission draft. It
introduces no model, adaptation gate, new fit or repeated query inference. The
original scientific records and all incomplete-window exclusions remain intact;
operational authorizations, storage receipts and fault recovery are retained
separately in the repository audit records.

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
exported cue-anchored task-label window. Sample completeness does not certify
uninterrupted imagery or isolation of the active task phase; S7 details this
distinction. The 44 partial events remained in source/split records and were
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

For the fixed checkpoint query evaluation, original package/checkpoint bytes and
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
and three negative participant differences. The original full-refit minus
LDA-only secondary contrast was +5.47
percentage points [2.17, 8.91]. Its target-label budget was the same for the two
update methods; it was not promoted to a primary endpoint. LDA-only minus frozen
remained uncertain at +1.95 points [−0.98, +5.09]. All subsequent same-dataset
interpretation remained exploratory
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
a new decoder fit. For an exported cue-anchored window `X`, the four CSP features were the **natural
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

## S6. Retained outcomes and numerical-validation scope

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

The completed CSP measurement retained the original scientific definition. Its
saved-feature numerical check reconstructed 629,137 arithmetic fields with
maximum difference zero; it did not independently recompute EEG projections or
refit estimators. Earlier incomplete or differently specified diagnostics are
not pooled with these measurements. Their original files and failures remain in
the separate audit history rather than being rewritten as successful attempts.

## S7. Exported cue windows and unresolved within-trial task phases

The released intervals are **cue-anchored exported task-label windows**, rather
than five seconds certified to contain uninterrupted motor imagery. Three
questions are distinct: whether all samples of an interval are available,
whether its start corresponds to the intended marker, and whether its complete
span lies within active imagery or feedback. The first is established for the
7,156 included intervals. The documented cue convention supports the second at
the derivative/export level. The third remains unresolved at trial level.

The original authors' codebook distinguishes class cue markers 769/770 from
subsequent task-start markers 7691/7701 [@kumarcodebook]. The preserved official
MOABB Kumar adapter maps the former pair to left/right hand and declares an
interval of [0,5] seconds. NEMAR identifies MOABB conversion and preserves
corresponding onset/sample/class rows. Its metadata reports MOABB `1.5.0dev0`,
but the exact historical converter commit/options and original GDF marker
arrays have not been independently replayed. A current adapter is evidence of
the documented convention, not proof of every historical conversion operation.

The original Methods describe one-second fixation, a 1.5-second class cue,
then a five-second offline task period or online feedback lasting at most seven
seconds; a two-second result display and 1.5-second rest follow [@kumar2024].
Online evidence-threshold crossing or timeout can terminate the active period.
Consequently, a nominal five-second interval beginning at the class cue
contains cue presentation and at most the following 3.5 seconds of the task
phase, assuming the described phase schedule. Earlier online termination may
introduce post-termination signal, but its presence and duration cannot be
assigned to individual intervals from the retained labels. We do not claim that
every online interval includes result display or rest.

The source codebook describes 32766 as recording boundary triggers and 1000 as
trial/rest start. For 7692/7702 it describes offline trial end and online
timeout/incorrect-hit events. The online 7693/7703 description is literally
“Cue Left/Right Delivered”; we do not silently reinterpret it as a correct hit.
The authors' versioned task-bounded extraction function starts at 7691/7701
and terminates at the subsequent 7692/7702 or 7693/7703. This supports the
distinction between their task-period markers and the class-cue export, without
equating either annotation convention with evidence of sustained imagery physiology.

The 360 saved event tables contain `onset`, `duration`, `trial_type`, `value`
and `sample`, but not the complete within-trial marker sequence. Each of the 44
partial intervals is the twentieth and final retained class event of an online
recording and ends at its previously audited EDF sample boundary. Their
identities, lengths and exclusion reasons remain unchanged. This demonstrates
recording-boundary truncation of the stored interval, **not 44 verified early
task terminations**, and does not by itself establish an indexing error. No
retained interval overlaps the next retained class-event onset; absence of
this overlap still cannot demonstrate continuous imagery within a window.

The minimum evidence for a future phase-specific amendment is the original
bar-task `POS`/`TYP` marker arrays for all 360 runs, their sample rate and
sample-origin convention, and a pinned converter or maintainer-confirmed
mapping to the current trial IDs. Cue, task start, outcome/task end and
recording boundaries must be matched without consulting decoding outcomes.
Before any new evaluation, an amendment would need to specify one anchor and
duration, handling of early ends and altered support/query budgets. Existing
cue-window predictions and models would remain the original analysis; they
cannot be relabeled as task-only models. No re-epoching, new fit or inference
was performed here. The correction to the original paper changes reported CSP
numbers, not these marker definitions [@kumar2024correction].

Relevant original Methods were read as accessible indexed full-text passages
from the publisher and PMC; the complete original XML could not be downloaded.
The complete author codebook, task-bounded extraction source and previously
saved correction XML were read. The original Methods identify UT Austin
protocol 2020-03-0073 and written informed consent. These are the original
study's statements only. The author's institutional determination for the
present secondary analysis remains unresolved; no approval, exemption or
no-review conclusion is inferred from public availability.

## S8. Exploratory decoding sensitivity to the fixed amplitude-QC flag

### S8.1. Status, input rules and exact identity joins

The sensitivity was requested and its protocol recorded **after the original
results had been observed**, but before computing these new summaries. It is
not preregistration, an amendment to the primary endpoint, artifact correction
or an untouched test. The original main results and 44 incomplete-window
exclusions, including 30 incomplete query identities, were preserved.

Only saved predictions, the existing Boolean
`qc_peak_to_peak_over_250uv` flag and frozen text metadata were used. The flag
was checked against the saved maximum raw channel peak-to-peak amplitude and
the fixed strict threshold `>0.00025 V` in any channel. The threshold was not
changed or selected by performance. Partial-window QC entries can be null and
are never silently interpreted as unflagged complete examples. The original
1,512 flagged complete windows comprised 76/720 source TRAIN, 36/360 source
validation, 36/360 source query, 478/1,786 target support and 886/3,930 target
query windows. Thus 922/4,290 unique included queries were flagged and 3,368 were
unflagged. Flagging is not expert artifact certification; unflagged does not
mean artifact-free.

Each saved prediction was joined by exact `trial_id` with unique, consistent
participant/session/run/role, original label, inclusion and QC values. Every
complete query required all three CPU methods and all three fixed EEGNet
seeds. Unexpected, missing, repeated or inconsistent identities caused failure
rather than partial scoring. The join comprised 25,740 stored predictions for
4,290 complete queries in 108 participant/method/seed groups. A separate
4,320-row query ledger retained the 30 incomplete identities and their original
exclusion reasons. All 144 reconstructed original participant endpoint values
matched the corresponding saved values exactly.

### S8.2. Class eligibility and aggregation

Both `all_included` and `unflagged` subsets retain rows for each participant,
method, seed and each of six sessions, plus separately labeled target-pooled
and all-query-pooled scopes. Counts include true left/right, predicted
left/right, all confusion cells and single-class prediction flags. Empty and
single-true-class groups remain present with undefined BA and an explicit
reason; unavailable values are not set to zero or chance.

Mathematical BA requires at least one example of each true class. A group with
fewer than five examples in either class is flagged as low-count descriptive
data but is not deleted by a new minimum-count rule. A group containing both
true classes can have model class collapse; a zero-query group has no defined
collapse assessment. EEGNet BA is computed separately for every seed and then
averaged over **all three** within participant/session. Counts represent unique
query identities, not trials multiplied by seeds, and no voting ensemble is
constructed.

The target endpoint requires all five target-session BAs and gives each equal
weight. If any target session is undefined, that participant's equal-session
endpoint is undefined; fewer sessions are never silently averaged. Cohort means
use the explicitly listed eligible participants. Source, target-pooled and
all-query-pooled endpoints have their own eligibility counts and cannot replace
the primary equal-session endpoint. Development 6, remaining 12 and secondary
all 18 remain separate.

Two remaining-cohort identities lose their unflagged five-session endpoint for
all four methods. Sub-8 has no unflagged queries in ses-3 or ses-4 and only 28
across target sessions (16 left/12 right); its source query retains one left
and zero right events, so source BA is also undefined. Sub-12 retains four
target events, all left-hand, distributed 1/1/2/0/0 across the five sessions.
Every target session is missing the other class. Other low-count sessions
remain, including sub-8/ses-2 and sub-11/ses-2 (each 2 left/1 right), and
sub-5/ses-5 (3 left/12 right). Unflagged equal-session summaries therefore
include 6/6 development and 10/12 remaining participants. The eligible remaining
IDs are sub-2, 3, 5, 6, 9, 11, 14, 15, 17 and 18; sub-8 and 12 remain in all
eligibility and missing-class tables.

### S8.3. Paired sensitivities, same-participant comparisons and influence

The original remaining 12 full-refit minus frozen contrast stays the primary
comparison in the original analysis. Full-refit minus LDA-only stays secondary.
Their QC-restricted counterparts are **new exploratory sensitivities**. Both
use paired participant differences and 10,000 percentile bootstrap draws with
`default_rng(42)`, lexicographic participant-ID ordering and 2.5th/97.5th
percentiles. Fewer than two eligible participants yield no interval. No new
p value, formal chance test, multiplicity-adjusted claim or adaptation gate is
introduced.

In the unflagged remaining 10, full-refit minus frozen is +5.96 percentage points
[0.99, 11.24]; full-refit minus LDA-only is +3.82 [1.11, 6.72]. The corresponding
original 12-person values remain +7.42 [2.49, 12.48] and +5.47 [2.17, 8.91].
Contrasting these two cohort means directly would mix QC and changed membership.
For the **same 10** eligible identities, original full-minus-frozen is +6.50
and unflagged is +5.96; the paired change is −0.54 [−1.30, +0.16] points. For
full-minus-LDA-only, original is +4.53 and unflagged +3.82; the paired change is
−0.71 [−2.11, +0.42] points. These bounded checks do not support attributing
the original average improvement solely to flagged query amplitudes, but also
do not prove general artifact robustness.

Deterministic leave-one-participant-out means are retained for both CPU
contrasts without excluding anyone by observed gain. The original full-minus-
frozen mean ranges from +6.22 to +8.62 points over the 12 omissions; the unflagged
10-person range is +4.61 to +7.24. The three original negative individual
differences are −5.82, −0.67 and −0.20 points (sub-6, 14, 15). Small negative
differences are not automatically interpreted as substantial harm or tested
individual effects. These are influence descriptions, not additional
independent participants or an exclusion rule.

Conditioning query evaluation on amplitude changes its class/sample composition
and may select observations. The 76 flagged source TRAIN examples, 478 flagged
target support examples and 36 flagged validation examples were still used as
originally prescribed; no historical fit or checkpoint selection was cleaned
or repeated. The analysis therefore cannot remove training artifacts, resolve
task-phase uncertainty, demonstrate a reliable update rule or provide an
independent replication. All previously exposed-cohort follow-up remains
exploratory.

## S9. Saved learning histories and the weak source-only neural reference

All 54 original metadata histories supply 2,871 consecutive recorded epochs and
8,613 optimizer steps. We extracted text histories, selection metadata and
existing query metric tables; binary model members were only streamed for
integrity hashing, never deserialized. No query array or EEG was read and no
new forward pass, optimizer or fit was invoked. Complete curves are supplied
as 2,871 text rows with participant, cohort, seed, job, epoch, training CE and
validation CE; the accompanying 54-fit table retains every selected epoch and
stopping reason. Empty console logs in 37 archives were not treated as proof of
zero execution, and no missing curve was reconstructed.

Twelve models selected epoch 1 and 11 reached 100 epochs. In the remaining 36
fits, the corresponding counts are 8 and 10; median executed and selected
epochs are 29.5 and 14.5. Final training CE is below its first value in 53/54
models (35/36 remaining), whereas final validation CE is above its first value
in 29/54 (19/36 remaining). Remaining-cohort medians are training CE 0.704246
initially and 0.596543 finally; validation CE 0.693048 initially, 0.691847 at
the selected epoch and 0.692351 finally. These are repeated-model descriptions,
not participant-level intervals. Training CE is accumulated in training mode
while parameters change within each epoch; validation CE uses the post-epoch
model in evaluation mode. Dropout and batch-normalization mode also differ.
The loss difference is consequently not a calibrated generalization-gap
measurement or proof of one failure mechanism.

The remaining 12 independent source-query mean BA is 52.9167%, compared with
51.5783% over later target sessions, a descriptive −1.3384-point difference.
Weak source discrimination precedes transfer, so later near-chance performance
cannot chiefly be assigned to cross-session drift. Source query has only 20
trials per participant; the target endpoint averages five sessions. These
different sampling precisions preclude treating the mean difference as an
isolated causal drift estimate. Selected-validation performance is not an
independent query endpoint.

Every fixed seed stays in the results. Remaining-cohort target means for
20261012/20261013/20261014 are 52.42/49.94/52.37%; the average within-participant
target mean BA range is 8.06 percentage points, maximum 24.62. These values do
not select an advantageous seed or imply population uncertainty from 54
independent people. The finding concerns this small-source implementation,
not the general suitability of deep learning for motor-imagery EEG.

## S10. Scientific software versions and text-only reproduction

The CPU baseline used Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3,
scikit-learn 1.7.2 and MNE 1.10.2, with recorded OMP/OpenBLAS/MKL thread
limits of one. The GPU source fits used PyTorch/Torchaudio 2.8.0+cu128 and
Braindecode 1.2.0. Fixed checkpoint inference used PyTorch/Torchaudio 2.8.0+cpu
and Braindecode 1.2.0 with the same Python/NumPy/SciPy/scikit-learn/MNE versions,
one PyTorch thread, OMP/OpenBLAS limits of one and
`CUBLAS_WORKSPACE_CONFIG=:4096:8`. GPU fitting and CPU inference are distinct
stages; these software statements do not establish equal compute budgets.

The public QC inputs comprise the frozen 7,200-event metadata (including 44
historical incomplete identities), 25,740 saved predictions, original analysis
configuration, 72 participant-by-method endpoint rows and their provenance
manifest. The dictionary records left=0/right=1, `cpu_fixed` for CPU seeds,
the three EEGNet seeds, roles, inclusion/exclusion reasons, original amplitude
flags and input lengths/hashes. Full per-session class counts, missing groups,
confusion cells, paired differences and influence rows accompany the results.
No EEG samples, checkpoint parameters, private credentials or new dataset
collection is included in these compact inputs. Source-derived data retain
their NEMAR CC BY 4.0 attribution; that attribution is distinct from software
dependency licenses.

From a repository checkout, the following command reproduces the public
saved-prediction arithmetic only, using Python 3.11 and the recorded NumPy 2.2.6.
Choose a new output directory; the existing frozen results are not overwritten:

```bash
mkdir qc_text_reproduction_new
cp research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md qc_text_reproduction_new/
python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs research_logs/kumar_submission_qc_20261015/run01/public_inputs \
  --output qc_text_reproduction_new
```

The portable input path needs no private original checkpoint or prediction
directory. The original-input computation and portable text-only replay
produced the same 13 scientific CSVs byte-for-byte. These are repeat arithmetic
checks, not repeat model inference. Public saved history tables can be inspected
without weights. To independently validate their original archive/member hashes
requires authorized possession of the 54 unmodified originals; use the portable
relative-filename index and a new destination:

```bash
python -B scripts/summarize_kumar_saved_training_curves.py \
  --archive-index research_logs/kumar_submission_training_review_20261015/run01/archive_input_index.json \
  --archives /absolute/path/to/54_original_archives \
  --output /absolute/path/to/new_text_only_review
```

This second command reads only allowlisted metadata/text and streams binary
members to SHA 256; it does not load tensor values or construct a model. Both
postprocessors require explicit output arguments. Invoking either without
arguments exits with usage instead of initiating fitting or evaluation. Neither
command invokes the scientific training/query runners; no such rerun is needed
to reproduce the new saved-prediction summaries. The fixed protocols, code,
CSV dictionaries and complete hashes provide the detailed implementation record
without reproducing operational authorization or storage logs in this supplement.

