# S1 Text. Supplementary scientific methods

**Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**

This supplement specifies the component comparisons, task-measurement probes, participant-level inference and sensitivity analyses. S1 Data supplies the saved predictions and numerical inputs; S2 Text describes provenance and reproduction.

## S1. Source identity, chronology and eligible windows

We analyzed the Kumar2024 derivative at NEMAR `nm000177/v1.0.5`, released under CC BY 4.0. The 2,705-file selection manifest covers 18 published participant identities, six ordered sessions, 360 EDF recordings and 7,200 event identities. Session and run order were checked against acquisition metadata. Channel order, sampling rate, units, event annotations and window identities were reconciled with the source records; complete raw and processed windows contained no exact numerical duplicates. Participant identity and absolute calendar dates rely on the source metadata.

Development participants were sub-1, sub-4, sub-7, sub-10, sub-13 and sub-16. The primary cohort comprised sub-2, sub-3, sub-5, sub-6, sub-8, sub-9, sub-11, sub-12, sub-14, sub-15, sub-17 and sub-18. This allocation used every third numeric ID for development, starting at one, before performance calculations.

A complete cue-anchored window required five seconds, or 2,560 samples at 512 Hz. Forty-four boundary-truncated events were excluded, leaving 7,156 complete windows. Their identities and exclusion reasons remain in the sample ledger. S7 describes the task phases represented by these windows.

| Role | Whole-run assignment | Included windows across 18 participants |
| --- | --- | ---: |
| Source training | ses-0, run-0 and run-1 | 720 |
| Source validation | ses-0, run-2 | 360 |
| Source query | ses-0, run-3 | 360 |
| Target support | ses-1 through ses-5, run-0 | 1,786 |
| Target query | All other target-session runs | 3,930 |

Each participant contributed 40 source-training and 20 source-validation windows. The first run of each target session supplied at most 20 support events, with at most ten per class before exclusion. Of 90 target sessions, 14 supplied 19 complete support events and 76 supplied 20. Updates combined source training with support from the current session only. The query ledger contains 4,320 identities: 4,290 complete queries and 30 excluded partial queries. All CPU methods and EEGNet seeds used identical included query IDs.

The original study reports University of Texas at Austin protocol 2020-03-0073 and written informed consent [@kumar2024]. According to the author's report, the research administration office at Chongqing Medical University confirmed on 16 October 2026 that this secondary analysis is exempt from additional ethical review under Article 32, item (1), of the 2023 Chinese ethics-review measures [@china2023ethics]; no reference number was issued. The [ethics-statement record](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/docs/kumar_ethics_statement_revision_20261016.md) documents the reported confirmation separately from the original collection.

## S2. Epoch-local preprocessing and descriptive coordinates

Channel order was F7, F3, Fz, F4, F8, FC5, FC1, FC2, FC6, C3, Cz, C4, CP5, CP1, CP2, CP6, P7, P3, Pz, P4, P8 and POz. Left hand was coded 0 and right hand 1. MNE input values were in volts; source physical metadata used microvolts. Each epoch underwent:

1. Common-average referencing across all 22 channels at each sample.
2. Fourth-order SciPy Butterworth SOS band-pass filtering at 8–30 Hz, using `sosfiltfilt` with default odd padding.
3. `resample_poly(up=1, down=4)` with default Kaiser-5 window and constant padding, producing 22 × 640 float32 values at 128 Hz.

Preprocessing operated independently within each epoch. Zero-phase filtering defines an offline analysis. The acquisition CPz reference is reported as source metadata. A maximum raw channel peak-to-peak amplitude above 250 µV flagged 1,512 of the 7,156 complete windows. The primary analysis included these windows; S8 evaluates the amplitude flag as a query sensitivity.

Power features used Welch estimates with a Hann window, 256-sample segments, 128-sample overlap, constant detrending, density scaling, one-sided output and mean averaging. Trapezoidal integration included band-edge bins for mu (8–13 Hz) and beta (13–30 Hz). The transform was `log10(max(power, float64_tiny))`, ordered channel-major with mu then beta, giving 44 coordinates. These coordinates represent absolute task-window power in V² before transformation.

Covariance features used a fixed 21 × 22 Helmert basis to remove the common-average-reference null direction. Epochs were time-centered, and covariance used the n−1 denominator. After trace normalization, shrinkage was `0.9*C + 0.1*I/21`. The affine-invariant Riemann reference was fitted to source training, with arithmetic initialization, unit step, at most 100 iterations and tolerance `1e-10`. A source-training StandardScaler and full-SVD PCA supplied four unwhitened coordinates. These source references remained fixed for all subsequent transformations. Descriptive QC, count-matched and C3/Cz/C4 sensitivities used the same preprocessing and decoder fits.

The prespecified covariance-drift measure was target-query mean distance to the source-training reference minus source-query mean distance. Task-axis drift was the one-dimensional Wasserstein distance between target- and source-query projections onto the normalized source-training right-minus-left direction in standardized power coordinates. Target labels supplied decoding outcomes and retrospective class summaries; drift predictors used the fixed source axis and unlabeled query distributions. These descriptive primary-cohort associations combine within- and between-participant variation, with five session changes sharing each participant's source-query baseline.

## S3. Decoder definitions and label budgets

### S3.1. CPU baselines

CSP used four components, Ledoit–Wolf regularization, log mean-square features and `norm_trace=False`. LDA used `solver="lsqr"` with automatic shrinkage. The baseline seed was 42, with one prespecified configuration.

| Action | CSP fitting data | LDA fitting data |
| --- | --- | --- |
| Source-only | Source training | Source training |
| LDA-only recalibration | Source training | Source training + current support |
| Full refit | Source training + current support | Source training + current support |

Source-only parameters stayed fixed across sessions. Each fit recorded its trial IDs; CPU fitting and parameter selection were restricted to the data listed above. All three action labels shared the same source model on the source query. The two update actions used the exact same labeled union, so their comparison estimates the additional contribution of updating CSP within this pipeline.

### S3.2. Source-only EEGNet

The `braindecode.models.EEGNet` implementation used F1=4, D=2, F2=8, temporal kernel 64, depthwise kernel 16, mean-pool sizes 4 and 8, ELU, dropout 0.5, automatic final-convolution length and spatial max norm 1.0. Batch normalization used momentum 0.01, affine parameters and epsilon 0.001. The constructor used `final_layer_with_constraint=false` and `norm_rate=0.25`.

For each participant, channel means and standard deviations were fitted over source-training trials and time, with a `1e-8` V scale floor. Adam used learning rate 0.001, betas (0.9, 0.999), epsilon `1e-8`, zero weight decay and `amsgrad=false`, with no scheduler. Training used unweighted cross entropy, zero label smoothing, batch size 16, shuffled rows, `drop_last=false`, `num_workers=0` and at most 100 epochs. Source-validation mean cross entropy selected the earliest best epoch, with patience 15 and minimum improvement zero. The complete selected state was restored.

Each participant contributed seeds 20261012, 20261013 and 20261014. Query predictions used logit argmax in evaluation and inference mode, with fixed parameters, batch-normalization buffers and source-normalization statistics. The 54 source fits supplied all neural results; S9 summarizes their histories.

### S3.3. Information budgets

| Pipeline | Source training labels | Source-validation labels for epoch selection | Current support labels for fitting |
| --- | ---: | ---: | ---: |
| Source-only CSP/LDA | 40 | 0 | 0 |
| Frozen CSP + LDA recalibration | 40 | 0 | 19/20 |
| CSP/LDA refit | 40 | 0 | 19/20 |
| Always-frozen EEGNet, each seed | 40 | 20 | 0 |

Full refit versus frozen decoding measures the total change after adding current-session labels and updating both stages. Full refit versus LDA-only isolates the incremental pipeline change under matched fitting IDs. EEGNet provides a reference for the fixed 40-training-trial setting; its additional validation labels and absence of target adaptation give it a different information budget from the CPU updates.

## S4. Endpoints, resampling and evidence hierarchy

Balanced accuracy (BA) was the mean of left and right recall. Session summaries also report confusion counts, recalls, predicted class proportions and single-class prediction indicators. The target endpoint was the equal mean of five session BAs within each participant. EEGNet first averaged all three seeds within participant/session. Source-query BA was a separate endpoint. Participants received equal cohort weight and were the independent statistical units. The six development participants, 12 primary participants and secondary all-18 summary were reported separately.

The original primary contrast was full refit minus source-only CSP/LDA in the 12-person cohort: +7.42 percentage points [2.49, 12.48]. The secondary same-label-budget contrast, full refit minus LDA-only, was +5.47 points [2.17, 8.91]; LDA-only minus frozen was +1.95 [−0.98, 5.09].

Descriptive 95% intervals used the 2.5th and 97.5th percentiles of 10,000 participant bootstrap draws with seed 42. Paired contrasts resampled participant differences. Saved decoder and QC endpoints used lexicographic participant-ID order. Development reliability summaries first averaged source folds or support sessions within participant, then used `default_rng(42)` with numeric order 1, 4, 7, 10, 13, 16 and 10,000 six-ID resamples. A missing participant value made the reliability interval unavailable.

Spearman drift associations used 2,000 participant-block bootstrap draws with seed 42, retaining all five sessions for each sampled participant; both measures produced 2,000 valid draws. This accounts for clustering while retaining the mixed within-/between-participant association and shared-baseline error. Intervals describe variation for the observed data and fitted models.

The original comparison hierarchy was retained throughout. Analyses introduced after query-result exposure, including QC sensitivities and the S11 paired checks, are exploratory. S11 reports the four CPU hypothesis checks; the EEGNet, reliability and new S12 prediction-transition summaries are descriptive or exploratory as specified in their methods.

## S5. Development-only measurement reliability

### S5.1. Fixed low-dimensional power probes

Three representations were evaluated: standardized 44-dimensional mu/beta power, source PCA4 coordinates and six C3/Cz/C4 mu/beta coordinates. Inputs were restricted to the six development participants' source training and current support. Source-run transfer trained on the 20 trials of run-0 and evaluated the 20 trials of run-1, then reversed the roles; each run contained ten trials per class. StandardScaler and PCA were fitted within each TRAIN20 fold. The diagnostic classifier used the right-minus-left class-centroid axis and midpoint threshold.

Controls crossed all 20 × 20 circular label phases of the two source runs, including identity. Label-dependent centroid directions and midpoints were recomputed, while label-independent fold scales and PCA were shared. The 14,400 fold/candidate/control evaluations included 36 observed probes. All three candidates were reported.

### S5.2. Supervised SOURCE20 CSP transfer probes

CSP and LDA were fitted within each TRAIN20 fold and refitted for every training-label phase. For each participant/fold, 20 training-label phases yielded 20 models and held-out predictions. Crossing these with 20 held-out label phases supplied all 400 joint `(run0_shift, run1_shift)` pairs. Held-out labels entered scoring only.

Across six participants, this yielded 240 completed CSP/LDA pipelines, including 12 identity-fold pipelines, 4,800 cached held-out trial predictions, 4,800 fold/phase BA evaluations and 2,400 participant/phase-pair means. All twelve runs had 20 unique circular label assignments. The observed phase pair was `(0,0)`. The procedure records an expected singular-fit failure as an unavailable value; all 240 pipelines completed in this analysis.

### S5.3. Frozen SOURCE40 coordinates and signed scores

Support measurements used the six existing SOURCE40 CSP/LDA models. For each window $X$ with $T$ time samples, CSP features were natural logarithms of mean squared projected amplitude:

$$
f_j(X)=\ln\!\left[\frac{1}{T}\sum_{t=1}^{T}(W_jX_t)^2\right],
\qquad j=1,\ldots,4.
$$

Power was required to be positive and finite. The vector diagnostic applied a four-coordinate StandardScaler fitted to SOURCE40 features with population variance (`ddof=0`). Using the SOURCE40 class means in standardized coordinates $\mathbf z$, define

$$
\mathbf d_{\mathrm{source}}
=\overline{\mathbf z}_{\mathrm{right}}-\overline{\mathbf z}_{\mathrm{left}},
\qquad
\mathbf u_{\mathrm{source}}
=\frac{\mathbf d_{\mathrm{source}}}{\lVert\mathbf d_{\mathrm{source}}\rVert}.
$$

Within each support class, trials were ordered by acquisition time, start sample and source row. The first $\lfloor n_{\mathrm{class}}/2\rfloor$ formed the first half and the remainder the second; corresponding class halves were then combined. For half direction $\mathbf d_h$, the measurements included source/full-support cosine, half-to-half cosine and signed axis contrast

$$
A_h=
\frac{\mathbf d_h\cdot\mathbf u_{\mathrm{source}}}
{\mathrm{SD}_{\mathrm{SOURCE40}}(\mathbf z\cdot\mathbf u_{\mathrm{source}})}.
$$

The source projection standard deviation used `ddof=1`. Zero directions, missing classes and non-estimable scales produced unavailable measurements.

The LDA score used unstandardized CSP log features, source coefficient and intercept, and classes `[0,1]`:

$$
s=\sum_{j=1}^{4}f_jw_j+b.
$$

$$
\widehat y=
\begin{cases}
1\; (\mathrm{right}), & s>0,\\
0\; (\mathrm{left}), & s\leq 0.
\end{cases}
$$

The source intercept, zero threshold and score scale remained fixed. With $\mathrm{SD}_s=\mathrm{SD}_{\mathrm{SOURCE40}}(s)$ and `ddof=1`, and $\overline s_{\mathrm{right},h}$ and $\overline s_{\mathrm{left},h}$ denoting the class means within support half $h$, the class-balanced signed margin was

$$
M_h=\frac{\overline s_{\mathrm{right},h}-\overline s_{\mathrm{left},h}}
{2\,\mathrm{SD}_s}.
$$

Thus $M_h$ includes a factor of one half, whereas $A_h$ uses the full class contrast. Additional summaries were right margin $\overline s_{\mathrm{right},h}/\mathrm{SD}_s$, left margin $-\overline s_{\mathrm{left},h}/\mathrm{SD}_s$, score location, recalls, predicted proportions, BA and class collapse. These are standardized separation measures. Two negative margins can give a positive half-product, and a positive class contrast can coexist with both classes on one side of the decision threshold.

### S5.4. Support controls and denominators

Each support run supplied all 19 or 20 circular label phases, including identity, while source features, axes, scales and LDA stayed fixed. The primary control recomputed classwise chronological halves at each phase. A sensitivity used the original half indices with rotated labels. The descriptive upper-tail fraction was

$$
q_{\mathrm{tail}}=
\frac{\#\{k\in\mathcal A:C_k\geq C_{\mathrm{obs}}\}}{\#\mathcal A},
$$

where $\mathcal A$ is the set of available controls, $C_k$ is a control value and $C_{\mathrm{obs}}$ is the observed value.

Ties and identity were included, with the available controls as denominator. Attempted, available, unavailable and unique-assignment counts were recorded. These fractions are descriptive sensitivities to label phase. They are reported as tail fractions, separately from the participant-level p values in S11.

For CSP, all 596 support phases per half method were available for each of four metrics: source/full-support cosine, half-to-half cosine, vector half-contrast product and LDA half-margin product. For power probes, all 1,788 phases per method were available for each of three metrics, giving 3,576 method/phase evaluations across the two half methods.

## S6. Prediction outcomes and measurement summaries

EEGNet produced 16 single-class seed/session query outcomes across seven models and seven participants: two source and 14 target outcomes. Frozen CSP/LDA produced three collapsed target sessions; neither CPU update produced collapse. All predictions contributed to the reported endpoints. Neural collapse counts include repeated seeds, so their denominators differ from those of the CPU methods. Source records also include five collapsed source-validation fits and eleven 100-epoch terminations.

The supervised CSP probe's source twofold mean BA was 62.9167% [52.5, 71.6667]. The participant mean of five support half-cosines was 0.295325 [0.032041, 0.573003]. Across 30 support sessions, signed score half-margins were positive in both halves for 19, negative in both for two, and opposite for nine; five sessions had frozen-score class collapse. These measurements characterize source-run transfer, support-subset agreement and task-score orientation within the calibration pool.

## S7. Cue-window semantics and task-phase coverage

The analyzed intervals are five-second cue-anchored task-label windows. Their sample completeness is established for 7,156 events; the original codebook and export convention identify their intended phase anchor.

| Marker | Source definition or use |
| --- | --- |
| 769/770 | Left/right class cue |
| 7691/7701 | Left/right task-period start |
| 7692/7702 | Offline trial end; online timeout/incorrect-hit events |
| 7693/7703 | Described online as "Cue Left/Right Delivered"; also used as an end marker by the task-bounded extraction function |
| 1000 | Trial/rest start |
| 32766 | Recording boundary |

The original authors' extraction function starts at 7691/7701 and ends at the subsequent 7692/7702 or 7693/7703 [@kumarcodebook]. The MOABB Kumar adapter instead maps 769/770 to left/right hand and declares [0,5] seconds. NEMAR metadata identifies the converter as MOABB `1.5.0dev0`; the reported decoding follows the released cue annotations. The source correction changes reported CSP scores while retaining these marker definitions [@kumar2024correction].

The task schedule comprises one-second fixation, a 1.5-second class cue, five-second offline task or online feedback lasting at most seven seconds, two-second result display and 1.5-second rest [@kumar2024]. Online threshold crossing or timeout ends the active period. Under this schedule, a five-second cue window contains the cue and at most the next 3.5 seconds of activity; early termination can introduce later phases. The corresponding decoding endpoint is classification of the task label over that cue-anchored interval.

The 360 derivative event tables contain `onset`, `duration`, `trial_type`, `value` and `sample`, with left/right values 1/2. Their annotation stream omits separate task-start/end and outcome markers. Each of the 44 truncated intervals is the final class event of an online recording and ends at the EDF boundary. This establishes recording-boundary truncation; the count of actual early task terminations requires the original marker sequence. Included intervals end before the next retained class-event onset.

### S7.1. Subsequent marker-mapping work

The reported cue-window results use the original derivative annotations. Subsequent metadata work on the publicly listed 72 offline and 288 online bar-task GDFs has mapped 311/360 runs and 6,220/7,200 events; 49 runs and 980 events remain unresolved. The [follow-up protocol](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/docs/kumar_component_exploratory_protocol_20261016.md) and [phase-reporting scope](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/docs/kumar_phase_scope_reporting_addendum_20261016.md) define the separate task-phase comparison. The performance results reported here follow the original cue-window specification; the phase-mapping records support the separately defined follow-up.

## S8. Exploratory decoding sensitivity to the amplitude-QC flag

### S8.1. Inputs and identity joins

The QC protocol was recorded after the original results were observed and before computing the sensitivity summaries. It applies the existing Boolean `qc_peak_to_peak_over_250uv` flag to saved predictions. The threshold is a strict maximum raw channel peak-to-peak amplitude `>0.00025 V`. Partial-window QC entries may be null; eligibility first requires a complete window.

| Role | Flagged / complete windows |
| --- | ---: |
| Source training | 76/720 |
| Source validation | 36/360 |
| Source query | 36/360 |
| Target support | 478/1,786 |
| Target query | 886/3,930 |

Of 4,290 unique included queries, 922 were flagged and 3,368 unflagged. Predictions were joined by exact `trial_id`, with consistent participant, session, run, role, label, inclusion and QC values. Each complete query required all three CPU actions and all three EEGNet seeds. The join contains 25,740 predictions in 108 participant/method/seed groups. It reproduced all 144 source-query and target-endpoint values for 72 participant/method rows.

### S8.2. Class eligibility and aggregation

Both `all_included` and `unflagged` tables contain each participant, method, seed and session, with true/predicted class counts, confusion cells and collapse indicators. Empty and single-true-class groups have undefined BA and an explicit reason. A group with fewer than five examples in either class is marked as low-count descriptive data and remains in the table. Collapse is assessed for groups with queries; an empty group has an undefined collapse indicator. EEGNet BAs are averaged across all three seeds within participant/session, while counts refer to unique query identities.

The target endpoint requires all five session BAs and gives each equal weight. An undefined session makes the participant endpoint undefined. Source-only, target-pooled and all-query-pooled endpoints have separate eligibility counts. Cohort summaries retain the development/primary distinction.

Two primary participants have undefined unflagged five-session endpoints. Sub-8 has zero unflagged queries in ses-3/4 and 28 across all target sessions (16 left/12 right); its source query has one left and zero right trials. Sub-12 has four target queries, all left, distributed 1/1/2/0/0 across sessions. Low-count groups include sub-8/ses-2 and sub-11/ses-2 (two left/one right each) and sub-5/ses-5 (three left/12 right). Unflagged endpoints are available for all six development participants and ten primary participants: sub-2, 3, 5, 6, 9, 11, 14, 15, 17 and 18.

### S8.3. Paired contrasts and influence

QC-restricted contrasts use 10,000 paired participant bootstrap draws with `default_rng(42)`, lexicographic ID order and 2.5th/97.5th percentiles; an interval requires at least two eligible participants. The original primary and secondary contrasts retain their S4 definitions.

| Contrast, same ten eligible participants | All queries | Unflagged queries | Paired unflagged-minus-all change |
| --- | ---: | ---: | ---: |
| Full refit − frozen | +6.50 | +5.96 [0.99, 11.24] | −0.54 [−1.30, +0.16] |
| Full refit − LDA-only | +4.53 | +3.82 [1.11, 6.72] | −0.71 [−2.11, +0.42] |

Values are percentage points with descriptive 95% intervals where shown. Comparisons within these same ten participants separate the query restriction from the change in cohort membership. The positive unflagged contrasts demonstrate that the average gains persist after the specified query-amplitude restriction in the eligible subset.

Leave-one-participant-out mean full-minus-frozen differences range from +6.22 to +8.62 points in the original 12 participants and +4.61 to +7.24 in the unflagged ten. Original participant decreases were −5.82, −0.67 and −0.20 points for sub-6, sub-14 and sub-15, respectively. These describe influence and observed variation, with the original cohort retained for inference.

Amplitude conditioning changes the class and sample composition of query evaluation and leaves two primary endpoints undefined. The source-training, support and validation sets retain their 76, 478 and 36 flagged examples, respectively. The table therefore describes sensitivity to query selection with the fitted models held fixed.

## S9. Saved learning histories and the source-only neural reference

The 54 source fits supplied 2,871 recorded epochs and 8,613 optimizer steps. S1 Data contains every epoch's training/validation cross entropy (CE), participant, cohort, seed, job and epoch, together with each selected epoch and stopping reason.

| History summary | All fits (54) | Primary-cohort fits (36) |
| --- | ---: | ---: |
| Selected epoch 1 | 12 | 8 |
| Reached the 100-epoch limit | 11 | 10 |
| Final training CE below initial CE | 53 | 35 |
| Final validation CE above initial CE | 29 | 19 |

For primary-cohort fits, median executed/selected epochs were 29.5/14.5. Median training CE changed from 0.704246 to 0.596543; median validation CE was 0.693048 initially, 0.691847 at the selected epoch and 0.692351 finally. Training CE was accumulated as parameters changed in training mode; validation CE used the post-epoch model in evaluation mode. Dropout and batch normalization followed training mode for the training statistic and evaluation mode for validation.

Primary-cohort BA was 52.9167% on the 20-trial source query and 51.5783% on the five-session target endpoint, a descriptive difference of −1.3384 points. The source-query result establishes the source-session discrimination of this reference, and the target result reports its subsequent transfer. Validation scores reflect checkpoint selection.

Primary-cohort target means for seeds 20261012, 20261013 and 20261014 were 52.42%, 49.94% and 52.37%. The mean within-participant range of target BA across seeds was 8.06 points, with maximum 24.62. These summaries characterize this implementation and training budget; participant inference averages the three seeds as specified in S4.

## S10. Scientific software and reproduction

CPU baselines used Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2, with OMP/OpenBLAS/MKL threads limited to one. GPU source fitting used PyTorch/Torchaudio 2.8.0+cu128 and Braindecode 1.2.0. Fixed-checkpoint inference used PyTorch/Torchaudio 2.8.0+cpu and Braindecode 1.2.0 with the same other scientific-library versions, one PyTorch thread, OMP/OpenBLAS limits of one and `CUBLAS_WORKSPACE_CONFIG=:4096:8`. The source CE replay used absolute tolerance `1e-7`.

Public reproduction inputs include the 7,200-event metadata, 25,740 saved predictions, analysis configuration, 72 participant/method endpoint rows and provenance manifest. The dictionary specifies left=0/right=1, `cpu_fixed` CPU seed labels, the three EEGNet seeds, sample roles, eligibility, amplitude flags, input lengths and hashes. Session class counts, missing groups, confusion cells, paired contrasts and influence rows accompany the results. Source-derived data retain NEMAR CC BY 4.0 attribution.

For a repository checkout with Python 3.11 and NumPy 2.2.6, the QC summaries can be reproduced from the portable saved inputs:

```bash
mkdir qc_text_reproduction_new
cp research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md \
  qc_text_reproduction_new/
python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs research_logs/kumar_submission_qc_20261015/run01/public_inputs \
  --output qc_text_reproduction_new
```

This postprocessor reproduced all 13 scientific QC CSVs byte-for-byte. S2 Text and the S1 Data file `REPRODUCE_SAVED_RESULTS.md` provide the complete reproduction commands and identity checks. Operational records, including archive integrity, recovery and earlier diagnostic attempts, are preserved with the [prior audit supplement](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/manuscript/kumar_plos_one_audit_reproducibility_ethics_20261016.md) and its linked repository evidence.

## S11. Exploratory paired sign-flip checks

The post-review tests use saved participant endpoints and were specified after the original results had been observed. They supplement the original effect estimates under the retained comparison hierarchy.

For paired BA differences $d_i$, the two-sided statistic is

$$
T_{\mathrm{obs}}=\left|\frac{1}{n}\sum_{i=1}^{n}d_i\right|.
$$

All $2^n$ sign vectors $s_i\in\{-1,1\}$ are enumerated. The p value is the fraction for which $\left|n^{-1}\sum_i s_i d_i\right|$ reaches the observed statistic, with absolute boundary tolerance $10^{-12}$ BA and zero relative tolerance. Full enumeration uses its exact denominator. Inference assumes independent participant differences with signs exchangeable about zero conditional on their magnitudes; this is a sign-symmetry assumption rather than randomized treatment assignment.

| Contrast and subset | Tail fraction | Two-sided p | Holm p, four comparisons |
| --- | ---: | ---: | ---: |
| Full refit − frozen, primary 12 | 80/4,096 | 0.01953125 | 0.05859375 |
| Full refit − LDA-only, primary 12 | 42/4,096 | 0.01025390625 | 0.041015625 |
| LDA-only − frozen, primary 12 | 1,070/4,096 | 0.26123046875 | 0.26123046875 |
| Full refit − frozen, unflagged ten | 78/1,024 | 0.076171875 | 0.15234375 |

Holm correction applies to this four-test exploratory family. For the primary contrast, the sample standardized paired effect is $d_z=0.807128$; percentage points remain the principal effect measure.

Four LDA-only-minus-frozen assignments lie at a numerical tail boundary. The specified tolerance includes them, yielding 1,070/4,096; strict comparison of the saved decimal strings as exact fractions yields 1,066/4,096. Both counts are available in the numerical diagnostics. Bootstrap reproduction uses the seed and ID order specified in S4/S8. The original percentile intervals and sign-flip tests have different reference constructions: the unflagged contrast has interval [0.99, 11.24] points and sign-flip p=0.076171875. Portable paired inputs, code and outputs are supplied in S1 Data; S2 Text links the additional arithmetic audit records.



## S12. Prediction-transition analysis and component consistency

### S12.1. Inputs and paired identities

The 17 October extension used the released saved predictions, trial metadata and original participant endpoints. All CPU methods were joined by exact trial identity, participant, session, run, true class and data role. The three methods had the same included query sets. Each class-specific denominator was the number of included queries with that true class in the participant/session, and all five target sessions contributed to each participant endpoint.

The analysis was specified after the original query results had been reported. It explains the original component contrasts through additional descriptive calculations. The script requires complete paired identities and reproduces the original endpoint values before producing new tables. Source models, training/support memberships and original query predictions are fixed inputs.

### S12.2. Correction contributions and class recall

For participant i, target session s and true class c, let $n_{isc}$ be the number of included query trials. For methods A and B, let $n_{isc}^{WC}$ count trials that A classified incorrectly and B correctly, and $n_{isc}^{CW}$ count the reverse transition. Define the class-balanced correction contribution C and introduced-error contribution E by

$$
C_{is}^{A\to B}=\frac{1}{2}\sum_{c=0}^{1}\frac{n_{isc}^{WC}}{n_{isc}},
\qquad
E_{is}^{A\to B}=\frac{1}{2}\sum_{c=0}^{1}\frac{n_{isc}^{CW}}{n_{isc}}.
$$

The identity

$$
\mathrm{BA}_{is}(B)-\mathrm{BA}_{is}(A)
=C_{is}^{A\to B}-E_{is}^{A\to B}
$$

holds for every paired session. The script verifies it before averaging. Each term is expressed in BA units and multiplied by 100 for percentage-point reporting. Class recall changes use the corresponding unhalved within-class fractions. The other two prediction transitions, both methods correct and both methods incorrect, complete the per-class table. The four transition counts sum to $n_{isc}$.

We calculated frozen to LDA-only, LDA-only to full refitting and frozen to full refitting. The correction and introduced-error terms describe transitions on the same trials; the net contrasts obey

$$
\Delta_{\mathrm{full,frozen}}
=\Delta_{\mathrm{LDA,frozen}}+\Delta_{\mathrm{full,LDA}}.
$$

In the primary cohort, the component gain was 5.47 points, obtained from 16.04 points of corrected errors minus 10.57 points of introduced errors. Left- and right-class recall changes were +6.16 and +4.78 points. The fraction 73.7% is 100 times the ratio of the mean full-minus-LDA gain to the mean full-minus-frozen gain. It describes the arithmetic allocation of the mean gain across the two sequential component contrasts. Full refitting includes an LDA fit in the newly estimated CSP space.

### S12.3. Aggregation and resampling

For every method contrast, we averaged each contribution across the five target sessions within participant. We then averaged participants with equal weight in the six-person development cohort, 12-person primary cohort and all-18 summary. The same weights were used for class recalls. Raw transition counts and denominators were preserved alongside these equally weighted effects.

Pointwise 95% percentile intervals used 10,000 participant bootstrap resamples, seed 42. The participant order and actual runtime versions are recorded with the execution outputs. Every sampled participant contributes the complete paired vector of session results, preserving method, class and session relationships. The new intervals accompany the descriptive decomposition and leave the original four-test Holm family unchanged.

### S12.4. Session profiles and participant influence

For each target session, we computed a cohort mean of full-minus-LDA differences and its participant-bootstrap interval. These five repeated-session profiles describe the time distribution of the component gain. The primary means were +3.52, +5.20, +4.13, +4.18 and +10.33 points in sessions 1–5. The underlying participant/session values and development profiles are also provided.

Single-participant deletion summaries recomputed the mean five-session component contrast over the other 11 primary participants. Their range was +4.39 to +6.28 points. This operation measures influence on a fixed cohort estimate. The full-minus-frozen summaries provide the corresponding total-gain reference. Joint-gain tables preserve the LDA-minus-frozen and full-minus-LDA components for each participant.

### S12.5. Reproduction and numerical checks

The script is scripts/analyze_kumar_update_mechanisms_20261017.py in the repository and code/analyze_kumar_update_mechanisms_20261017.py in S1 Data. It reads portable numerical inputs and writes a new output directory. The complete extension includes per-class transition counts, participant/session contributions, participant endpoints, cohort intervals, class recalls, session profiles, influence summaries and underlying figure tables. S2 Text provides the portable command and the file manifest.

Checks include full trial-identity reconciliation, source and target endpoint reconstruction, both true classes per target session, five target sessions per participant, the correction-minus-introduced-error identity, the two-stage gain identity and class-recall/BA agreement. The independent arithmetic check uses a separate implementation of the count and weighting calculations. Input SHA-256 hashes, analysis definition, seeds and runtime versions accompany the outputs.

## References

::: {#refs}
:::
