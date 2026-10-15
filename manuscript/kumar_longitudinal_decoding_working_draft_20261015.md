# Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG

**English working draft; evidence available on 2026-10-15.** This draft reports
completed offline baselines and measurement diagnostics. The project title
states the research direction; an effective task-aware adaptation policy has
not been demonstrated. This is an exploratory research draft, not a
submission-ready manuscript. The historical NETBCI manuscript is a separate
record and contributes no additional participants to the present analysis.

## Abstract

Longitudinal motor-imagery decoding requires distinguishing changes in the EEG
distribution from changes in information useful for a fixed task. We studied
18 published participant identities across six ordered sessions in Kumar2024
(NEMAR nm000177, version 1.0.5). A frozen within-participant protocol compared
source-only CSP/LDA, LDA recalibration with frozen CSP, and full CSP/LDA refitting.
An additional source-only EEGNet baseline retained three fixed random seeds for
every participant. All methods were evaluated on the same query identities;
their source-validation and target-label budgets differed and are reported
explicitly. The primary CPU contrast in the fixed remaining 12 participants
favored full refitting over source-only decoding by 7.42 percentage points
(95% participant-bootstrap interval 2.49–12.48), although three participants
worsened. Always-frozen EEGNet achieved mean target balanced accuracy of 51.58%
(49.08–54.51%) in this cohort, retaining class-collapsed outcomes. Development-only
measurement diagnostics found heterogeneous task-direction reliability; they
did not validate an adaptation gate. These results support a conditional benefit
of conventional recalibration under the specified label budget and a weak
source-only neural baseline in this small-source setting. Previously inspected
test identities make subsequent analyses exploratory. Offline decoding does not
establish human learning, skill retention or clinical benefit.

## Introduction

A decoder trained in an early recording session may fail when signal
statistics change. Recalibration with labeled data from the current session
can improve decoding, but the benefit may vary between participants. A change
in signal covariance alone also need not identify a change in task-relevant
information. Before using such measurements to control adaptation, their
reliability and decision value need to be established using data allowed for
model development.

The present study separates three questions: whether conventional recalibration
improves longitudinal decoding under a fixed support budget; how a prespecified
source-only neural baseline transfers to later sessions; and whether available
task measurements justify a future adaptation rule. The first question has a
frozen primary CPU contrast. The latter analyses are exploratory diagnostics
and additional baselines. No task-aware policy is selected from the reported
query results.

## Methods

### Data, identity and chronological partition

The source was the already archived Kumar2024 derivative at NEMAR
`nm000177/v1.0.5`, licensed CC BY 4.0
([source release README](https://data.nemar.org/nm000177/v1.0.5/README.md)).
The frozen selection contained 360 EDF
recordings, 18 published participant identities, six sessions and 7,200 event
identities. Forty-four partial events were preserved in the audit but excluded
from tensors without padding or replacement, leaving 7,156 complete
five-second windows. Published identities are the statistical units; numerical
duplicate checks do not independently verify biological identity.

Development identities were sub-1, sub-4, sub-7, sub-10, sub-13 and sub-16; the
other 12 identities formed the fixed remaining cohort. This assignment used
numeric identity order rather than performance. Session and run chronology
was checked against the derivative's acquisition timestamps. Their calendar
accuracy was not independently established.

In session 0, runs 0 and 1 supplied 40 source-training windows, run 2 supplied
20 source-validation windows, and run 3 supplied source query. In each of the
five later sessions, the first whole run (`run-0`) was the preassigned support
run; all other runs supplied target query. Partial events were excluded without
replacing the run or filling its missing windows. The support allowance was at most 20
events and 10 per class before partial-window exclusions; actual support was
19 or 20 events: 14 of the 90 target sessions had 19 and 76 had 20, totaling
1,786 support events. Updates used source training plus current-session support,
without accumulating previous or future target sessions. The same 4,290
included query events were evaluated by the CPU methods and EEGNet: 360 source
queries and 3,930 target queries. Thirty partial query events remained excluded.

### Preprocessing and quality qualifications

Each event independently underwent common-average referencing over 22 channels,
fourth-order 8–30 Hz Butterworth zero-phase filtering and polyphase resampling
from 512 to 128 Hz. Inputs were 22 × 640 float32 values in volts. These
epoch-local operations learned no held-out statistics. Zero-phase filtering
defines an offline analysis and does not establish real-time operation.

A fixed 250 µV raw peak-to-peak threshold flagged 1,512 of the 7,156 complete
windows. All flagged full windows remained in the primary analysis. There was
no expert artifact certification; decoding could reflect non-neural signal
components. Native CPz reference was a source-metadata declaration, and offline
common-average referencing cannot reconstruct or independently verify the
original acquisition reference.

### Decoders and explicit data budgets

The CPU pipeline used four-component CSP with Ledoit–Wolf regularization,
log mean-square features and `norm_trace=False`, followed by shrinkage LDA
(`solver=lsqr`, automatic shrinkage). One prespecified configuration was used.
Source-only CSP and LDA stayed fixed. Recalibration retained source CSP and
refitted LDA with source training plus current support; full refitting updated
both stages using that same union. Validation and query identities were
excluded from all CPU fitting and parameter selection.

EEGNet used the frozen Braindecode architecture (F1=4, D=2, F2=8, dropout 0.5),
Adam at learning rate 0.001, batch size 16 and a maximum of 100 epochs. Channel
means and scales were fitted to source training only. Source-validation
cross entropy selected the earliest best epoch with patience 15; the complete
selected state was restored. All three seeds—20261012, 20261013 and 20261014—
were retained for each participant. The 54 completed source fits used 2,871
epochs and 8,613 optimizer steps. No source fit was repeated for query evaluation.
Query inference used evaluation mode with fixed parameters, batch-normalization
buffers and normalization statistics, with zero optimizer or support updates.

**Table 1. Labeled-data use per participant.**

| Method | Source optimizer/estimator training | Source-validation use | Current target support for fitting |
| --- | --- | --- | --- |
| Source-only CSP/LDA | 40 labeled windows | No model or checkpoint selection | 0 |
| Frozen CSP + LDA recalibration | 40 labeled windows; LDA then refitted with current support | No model or checkpoint selection | 19/20 labeled windows |
| CSP/LDA refit | 40 labeled windows; both stages then refitted with current support | No model or checkpoint selection | 19/20 labeled windows |
| Always-frozen EEGNet | 40 labeled windows per seed | 20 labeled windows select stopping epoch | 0 |

Thus the two CPU update methods share the same adaptation label budget. Their
comparison with the frozen CPU model measures performance after adding the
specified support labels. Identical query samples do not make EEGNet and CPU
methods equal-budget architecture comparisons: EEGNet additionally uses the
source-validation labels for epoch selection, and only the CPU update methods
use target labels. No causal architecture or compute-efficiency ranking is
inferred from these differences.

### Endpoints and statistical units

Balanced accuracy (BA) was the mean of the two class recalls. The primary
endpoint was each participant's mean BA over its five target sessions. The
primary contrast remained full CSP/LDA refitting minus source-only CSP/LDA in
the fixed remaining 12 identities. For EEGNet, all three seed scores were
averaged within participant/session before the five target sessions were
averaged within participant. Source query was reported separately. Neither
seeds, sessions nor trials increased the independent participant count.

Descriptive 95% percentile intervals used 10,000 participant resamples with
seed 42; paired CPU contrasts resampled paired participant differences.
Development and remaining cohorts were reported separately; all-18 summaries
were secondary. Cohort intervals containing 50% were not converted into a
new formal chance hypothesis test. Previously exposed test results preclude
describing subsequent same-dataset evaluations as untouched external confirmation.

The task-information diagnostics used only development source training and
predeclared support. Fixed power, PCA and supervised CSP-score measurements
were evaluated with source-run grouping, support split halves and cyclic-label
controls. The controls are phase-alignment sensitivities, not formal
permutation p values. No diagnostic selected an adaptation threshold or used
query outcomes to choose a policy.

## Results

### Conventional CPU recalibration and the frozen neural baseline

Table 2 reports equally weighted participant target-session endpoints, rounded
to two decimal places; exact values remain in the linked machine-readable
saved-result comparison. CPU values derive from the original executed baseline
results; the newly tabulated all-18 combination and descriptive intervals do
not replace the original primary contrast. All three EEGNet seeds contribute
to every participant endpoint. Every bracketed interval is a descriptive 95%
participant-bootstrap interval.

**Table 2. Target-query balanced accuracy (%, mean across five sessions within participant).**

| Cohort | Participants | Source-only CSP/LDA | Frozen CSP + LDA recalibration | CSP/LDA refit | Always-frozen EEGNet |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 6 | 59.97 [57.34, 63.70] | 64.37 [56.97, 71.75] | 63.22 [58.36, 67.40] | 52.31 [48.43, 57.36] |
| Fixed remaining cohort | 12 | 57.94 [52.65, 63.84] | 59.89 [54.30, 65.68] | 65.36 [59.81, 70.90] | 51.58 [49.08, 54.51] |
| All identities, secondary | 18 | 58.62 [54.88, 62.68] | 61.38 [56.79, 66.17] | 64.65 [60.53, 68.71] | 51.82 [49.59, 54.36] |

The original primary paired CPU contrast was +7.42 percentage points
[+2.49, +12.48] in the 12-participant cohort. Nine participants improved and
three worsened. The development contrast was +3.25 points [−0.90, +7.14].
In secondary remaining-cohort contrasts, LDA recalibration minus source-only
was +1.95 points [−0.98, +5.09], and full refitting minus LDA recalibration was
+5.47 points [+2.17, +8.91]. These secondary intervals do not provide a
multiplicity-adjusted confirmatory claim. The two update methods had the same
source and support label budget, so their difference is informative within the
frozen CPU comparison.

The all-18 row is a secondary combination rather than a new test cohort.
Table 3 keeps source query separate from the target endpoint. The three CPU
method labels use the same unchanged source-fit model at source query;
these are not three independent source estimates. All EEGNet target-cohort
intervals included 50%. Under the specified source-only protocol, the neural baseline
therefore showed weak average transfer rather than an established advantage.
This is not evidence that other architectures, training budgets or methods
cannot decode these data.

**Table 3. Source-query balanced accuracy (%, participant mean and descriptive 95% interval).**

| Cohort | Participants | CPU source model, shared by the three method labels | Always-frozen EEGNet |
| --- | ---: | ---: | ---: |
| Development | 6 | 60.83 [54.17, 68.33] | 52.78 [47.50, 59.44] |
| Fixed remaining cohort | 12 | 65.00 [56.67, 74.17] | 52.92 [48.89, 58.75] |
| All identities, secondary | 18 | 63.61 [57.50, 70.28] | 52.87 [49.44, 57.22] |

The query evaluation included all 54 checkpoints, producing 12,870 saved
prediction rows and 324 seed/session metric records. Every prescribed
participant, seed and session remained in the complete result inventory.

### Preserved heterogeneity and collapsed predictions

EEGNet produced 16 single-class model/session outcomes across seven models and
seven participants: two source-query outcomes and 14 target-query outcomes.
They remained in all means. These are model/session counts across seeds, not
16 independent participants. The original frozen CPU model also had three
single-class target-session outcomes across the full cohort, including two in
the remaining cohort; neither CPU update method had such an outcome. Collapse
and participant worsening were not reasons to exclude data or select seeds.

Epoch-selected source-validation scores were kept separate from query results.
The all-18 participant mean validation BA was 55.93%; the development mean was
53.06% and the remaining-cohort mean was 57.36%. Five of the 54 validation
fits predicted a single class. Within-participant seed BA ranges reached
45 percentage points. These selected validation scores describe training
behavior; they are not independent estimates of generalization and have no
new confidence interval or hypothesis test.

### Task measurement remains insufficient to release a policy

In the previously frozen remaining-cohort descriptive analysis, covariance
shape change and source-task-axis Wasserstein distance had session-level
Spearman associations of −0.007 and 0.197 with frozen BA change. Their
participant-block 95% intervals were [−0.505, 0.438] and [−0.240, 0.518],
respectively. These broad intervals provide no reliable ranking of the two
measurements as performance predictors.

Development-only low-dimensional power probes had mean source BA of 51.67%
for standardized 44-dimensional power, 50.00% for PCA4 and 54.17% for the
six sensorimotor-band features. Each feature set's participant-bootstrap
interval included 50%, and each support split-half cosine interval included
zero. The supervised CSP-score
diagnostic subsequently completed all 240 prescribed source-fold/label-rotation
pipeline attempts, retaining all controls. Its mean source twofold BA was
62.9167% [52.5, 71.6667]; mean participant-averaged support split-half vector
cosine was 0.295325 [0.032041, 0.573003].

The positive mean cosine did not establish reliable direction in every session.
Among 30 support sessions, signed frozen-score half-contrasts were both positive
in 19, both negative in two, and opposite in nine. In particular, a positive
product could arise when both halves pointed against the frozen source
direction. Five support sessions had frozen-score prediction collapse. These
diagnostics do not constitute a nested out-of-sample adaptation-policy test,
and no effective task-aware gate was declared.

## Discussion

The strongest completed comparison is conventional CSP/LDA recalibration under
a specified current-session label allowance. Full refitting improved the
remaining-cohort mean relative to source-only decoding, while preserving three
participants with worse outcomes. This combination motivates evaluating the
reliability of update decisions, but does not by itself establish that a
task-aware gate can improve them. The weaker and uncertain LDA-only contrast
also cautions against assuming a fixed source spatial representation is
sufficient for every later session.

The always-frozen EEGNet baseline remained close to chance on average across
later sessions, with collapsed cases retained. Its poor transfer is a finding
about this frozen architecture, source sample size, optimization rule and
dataset. Additional source-validation labels did not turn it into a successful
longitudinal baseline under the executed protocol. It does not demonstrate
that neural decoding is generally ineffective, nor explain whether the
limitation arose from sample size, signal quality or another mechanism.

The task diagnostics further distinguish task-discriminative source structure
from a dependable current-support decision signal. Supervised CSP source probes
showed stronger point estimates than the tested power probes, but the differing
measurements do not establish a new superior policy. Mixed signed directions,
class collapse, small support sets and uncertain drift associations remain
material constraints. Choosing a favorable feature, seed or threshold after
looking at these query scores would not resolve them.

## Limitations and remaining evidence

The sample comprises 18 published identities from one derivative dataset;
the development set has six independent units and the remaining cohort 12.
Biological identity, source timestamp provenance and demographic fields are
not independently established. An invalid `age=2020` field and unresolved
GR/PAR group mapping were not used for subgroup or covariate inference. Signal
quality was qualified rather than clinically certified, and retained amplitude
flags permit artifact-related decoding. The small, chronological runs may
confound task information with run-specific acquisition effects; cyclic-label
controls do not prove exchangeability or neural specificity.

The study has an internal analysis freeze, not external preregistration. Earlier
exposure of the same-dataset test results limits all later method development
to exploratory interpretation. The EEGNet/CPU comparison shares query events
but differs in validation use, target labels, optimization and hardware; it
does not identify an equal-budget architectural effect. No EEGNet adaptation
baseline, nested task-aware policy comparison, independent external confirmation
or prospective online evaluation was completed here.

A future policy would require a separately frozen development-only decision
rule and group-aware nested evaluation against always-freeze, conventional
update and equal-budget controls. Current query results cannot select that
rule, and this draft releases no experiment. Independent, qualified external
data would be needed for stronger confirmation. Human learning or retention
claims would additionally require relevant behavior, interventions and delayed
tests; the present task labels and offline decoder scores cannot supply them.

Author affiliations, contributions, funding, competing interests, institutional
secondary-data requirements and a complete verified scholarly bibliography
remain to be supplied and reviewed. No author, funding or ethics statement is
invented in this working draft.

## Evidence and reproducibility

The methods and numerical statements above are tied to the following preserved
repository records. Older reports contain historical stage flags; later audit
and actual acceptance records append evidence rather than rewrite those flags.
This manuscript update itself runs no experiment.

- [Frozen CPU experiment protocol](../KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md),
  [CPU configuration](../configs/kumar_cross_session_20261012.json), and
  [frozen split manifest](../research_logs/kumar_cross_session_20261012/protocol/split_manifest.json).
- [Original task-aware descriptive plan](../research_logs/kumar_cross_session_20261012/protocol/task_aware_analysis_plan_frozen_20261013.md)
  and [recorded research decisions](../TASK_AWARE_ADAPTATION_RESEARCH_PLAN.md).
- [Executed CPU baseline summary](../CROSS_SESSION_RESULTS.md),
  [original execution receipt](../research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z/execution_receipt.json),
  and [participant endpoints](../research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z/participant_endpoints.csv).
- [EEGNet training plan](../EEGNET_TRAINING_PLAN.md),
  [unchanged executed architecture/optimization configuration](../configs/kumar_eegnet_gpu_development_20261014.json),
  and [all-54 saved source-validation summary](../research_logs/kumar_all54_source_aggregation_20261015/run01/summary.json).
- [Frozen checkpoint query protocol](../docs/kumar_frozen_checkpoint_query_protocol_20261015.md),
  [actual query execution and independent audits](../research_logs/kumar_frozen_query_execution_audit_20261015/run01/REPORT.md),
  [query participant summary](../research_logs/kumar_frozen_query_execution_audit_20261015/run01/per_participant_frozen_query_summary.csv),
  and [subsequent actual query acceptance](../research_logs/kumar_frozen_query_acceptance_20261015/run01/parent_acknowledged.json).
- [Matched saved-query comparison table](../research_logs/kumar_frozen_query_comparison_20261015/run01/cohort_method_endpoint_summary.csv),
  [participant endpoints](../research_logs/kumar_frozen_query_comparison_20261015/run01/per_participant_endpoints.csv),
  and [comparison provenance and identity checks](../research_logs/kumar_frozen_query_comparison_20261015/run01/comparison_receipt.json).
- [Development low-dimensional reliability report](../research_logs/kumar_cross_session_20261012/lowdim_reliability_dev_run01_20261014/REPORT.md)
  and [complete supervised CSP signed-score diagnostic](../research_logs/kumar_csp_signed_score_execution_20261015/run02/REPORT.md).

The EEGNet query evaluation executed once at commit
`d34703ca5bccf7a5b88a91c2ffb2cba893f7cec8`; its audit delivery was fixed at
`ac5a1f6d014421f0adf6f924a58a7063558b89f7`. The original operator's private
result/evidence backup verified all 147 objects by full GET/SHA256. The actual
parent acceptance at 2026-10-15T09:49:05Z separately records reading and hashing
the complete receipt, metadata/result identity checks, and arithmetic
reconstruction of 18 participant means and six bootstrap summaries. It does
not claim a new parent R2 GET, second model forward or independent rehash of
all 147 original objects. Source
weights and original EEG remain private and are excluded from the manuscript
repository. Data redistribution remains subject to the source license.
