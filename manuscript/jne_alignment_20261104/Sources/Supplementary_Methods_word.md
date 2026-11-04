# Supplementary methods: the added value of alignment

**Supplement title:** Supplementary methods

**Description:** Complete decoder definitions, statistical families, participant and class counts, calibration budgets, neural and geometric controls, matched implementation sensitivities, phase-window comparisons and supplementary figures.

This supplement accompanies *Limited-label cross-session motor-imagery EEG recalibration: spatial refitting and the added value of Euclidean alignment*. Sections S1–S15 retain the historical decoder definitions, comparison families, all scheduled budgets, neural/geometric controls and source-data details from the component revision. Sections S16–S20 report the present saved-prediction reanalysis and actually completed CPU sensitivities. The accompanying tables distinguish original participant cohorts, historical intervals and new descriptive endpoints. Repeated use of the same people or predictions does not add an independent cohort.

**Abbreviations:** AR, autoregressive; BA, balanced accuracy; BCI, brain–computer interface; BN, batch normalization; CSP, common spatial patterns; EA, Euclidean alignment; EEG, electroencephalography; KL, Kullback–Leibler divergence; LDA, linear discriminant analysis; MI, motor imagery; SOS, second-order sections; SPD, symmetric positive-definite.

## S 1. Analysis layers and statistical units

| Layer | Participants | Scientific role | Model/seed information | Selection status |
| --- | --- | --- | --- | --- |
| Original comparison | 18, partitioned as six development and 12 primary | Full CSP/LDA minus frozen was the primary contrast; full minus LDA-only was secondary | Original EEGNet reference: three seeds and 54 source models | Original pipeline and endpoint hierarchy frozen before primary performance calculation; prior exploratory exposure retained in the record |
| V2 extension | The same six development participants | Candidate covariance mixture versus EA-CSP; support-budget and neural diagnostics | 18 separately versioned individual sources | Later design informed by earlier results |
| V3 extension | The same six development participants | Predefined candidate comparisons and component mechanisms | Read-only reuse of 18 V2 sources; three new pooled sources; all fixed seeds | Task matrix and comparison roles frozen before execution |
| Mechanism simulation | No human participants | Known-mechanism estimator stress tests | 384 scenarios × 50 paired draws × nine methods | Synthetic, with software_validation_only=true; separate from real EEG evidence |

Participant was the independent unit for real-EEG intervals. Seeds were averaged within session and sessions within participant. V2/V3 used the same already-exposed development participants; their intervals are pointwise exploratory summaries. Pooled teachers are shared across participant evaluations, so their bootstrap uncertainty is conditional on the fitted teachers. Model, seed and repeated-prediction counts describe the nested experiments. The external cohort and its fixed endpoints are described in Section S12.

## S 2. Exact data access and endpoint definition

The original source-training set comprised session 0/runs 0–1, validation run 2, and source query run 3. The first whole run of each later session supplied support, with subsequent whole runs reserved for query. The chronological support prefixes were capped at 4/8/12/16/20 complete trials in V2/V3; the last cap retained 19 if only 19 complete support windows were available. A prefix containing one class was preserved. Future labels were never used to balance it, choose a policy, select a model or replace a missing class.

The two conventional updates pooled the same 40 source-training trials with the same 19/20 current-support trials. The frozen comparator used source training alone. Neural fine-tuning in V3 optimized current support only, starting from the specified source checkpoint. The functional constraint additionally evaluated the participant's 40 source-training examples as fixed prediction anchors. Source validation selected source epochs; it did not select target adaptation epochs. The pooled source regime used the six participants' source training/validation sets, not their query data.

Methods evaluated on the same query set used identical ordered trial IDs and true labels. EA-CSP predictions imported from V2 were matched by these arrays and their checksums because query-hash conventions differed between versions.

BA required both true classes. Participant target endpoints required all five sessions and all scheduled neural seeds. Undefined groups retained an explicit missing status. Source-query metrics were reported separately. The original trial exclusions and five-second window definition were retained.

### Cue-window interpretation

Seven thousand one hundred fifty-six complete sample windows were retained from 7,200 exported events; 44 crossed recording boundaries. The event-code documentation and MOABB interval establish the released cue-anchored convention. Partial recovery of original task markers supports the common-query phase-window comparison in Section S15. Original phase mapping remains unavailable for 980 of the 7,200 events; full-cohort phase assignment requires that remaining marker coverage. A partial exported event denotes an incomplete sample window rather than an observed task-ending category.

## S 3. Original prediction-transition and sensitivity definitions

For binary labels c∈{0, 1}, define C_c as the proportion of true-class-c trials that change from incorrect under A to correct under B, and E_c for the reverse transition. Then

$$
\Delta BA=\tfrac12(C_0+C_1)-\tfrac12(E_0+E_1).
$$

The two contributions were averaged over five sessions within each participant before cohort inference. They exactly reconstruct the saved BA difference. The 73.7 % spatial-component share is the descriptive ratio of cohort-average full-minus-LDA-only to full-minus-frozen. It decomposes the observed pipeline contrasts.

Original primary-cohort mean full-minus-LDA-only was 5.47 pp, with corrected-error and introduced-error contributions 16.04 pp and 10.57 pp. Left/right recall changes were 6.16 pp and 4.78 pp, with both individual intervals including zero. The same component contrast was positive in 10/12 participant averages and all five session means; participant-deletion means ranged 4.39–6.28 pp. Session profiles and participant-deletion summaries locate the component gain within the longitudinal data.

The pre-existing amplitude flag was 250 µV maximum raw channel peak-to-peak. It flagged 1,512/7,156 complete windows. Saved-prediction/QC matching used trial identity, role, true label and inclusion status. The unflagged target endpoint required both classes in every session; only ten original primary participants met that criterion. Their unflagged full-minus-frozen gain was 5.96 pp [0.99, 11.24] and component gain 3.82 pp [1.11, 6.72]. Their corresponding full-query gains were 6.50 pp and 4.53 pp. Source and support data were retained during this amplitude-conditional query restriction; the flag identifies a signal-amplitude property rather than a complete artifact assessment.

The original post-hoc exact sign-flip tests enumerated all $2^n$ sign assignments of the participant differences, retaining their magnitudes. The statistic was the absolute mean paired difference, with an inclusive boundary tolerance of $10^{-12}$ in BA units. The four-test family comprised full-minus-frozen, full-minus-LDA-only and LDA-only-minus-frozen in the 12-person primary cohort, and full-minus-frozen in the ten-person eligible unflagged subset. Unadjusted p values were 0.01953125, 0.01025390625, 0.26123046875 and 0.076171875; Holm-adjusted values were 0.05859375, 0.041015625, 0.26123046875 and 0.15234375, respectively. These tests use a sign-symmetric null conditional on the observed magnitudes. The original percentile-bootstrap intervals are pointwise and unadjusted for this family.

## S 4. Geometric estimator

### Source-fixed feature space

Each trial covariance was trace-normalized and regularized using shrinkage 0.1. Let R_s be the source-training-only reference covariance and

$$
z=\operatorname{vech}_{\sqrt2}\{\log(R_s^{-1/2}CR_s^{-1/2})\}.
$$

The symmetric-vector operator multiplies off-diagonal elements by √2 to preserve the Frobenius inner product. With 22 channels, p=253. The reference remains fixed for every current-session budget and all queries. Trace normalization and identity shrinkage do not confer strict invariance to arbitrary affine sensor transformations.

For a domain d, define class means $\mu_{d0}$, $\mu_{d1}$ and

$$
m_d=(\mu_{d0}+\mu_{d1})/2,\qquad h_d=(\mu_{d1}-\mu_{d0})/2,\qquad \theta_d=[m_d;h_d].
$$

Class feature covariance estimates B_dc use fixed 0.1 shrinkage. With U_dc=B_dc/n_dc, the estimated mean-observation covariance is

$$
V_d=\frac14\begin{bmatrix}U_{d0}+U_{d1}&U_{d1}-U_{d0}\\U_{d1}-U_{d0}&U_{d0}+U_{d1}\end{bmatrix}.
$$

Separate shift-variation scales are

$$
\tau_j^2=\max\{(\|\theta_{tj}-\theta_{sj}\|^2-\operatorname{tr}(V_{s,jj}+V_{t,jj}))/p,0\},\quad j\in\{m,h\}.
$$

Let T=diag(τ_m²I,τ_h²I), M=V_s+T. With both classes observed,

$$
\widehat\theta=\theta_s+M(M+V_t)^{-1}(\theta_t-\theta_s),\qquad
P=M-M(M+V_t)^{-1}M.
$$

The implementation uses a masked linear-Gaussian update and the Joseph form for P. For a single observed class, the mask retains only that class's observations, unidentifiable shift variation is set to zero, and the unobserved class retains its source mean. A class represented by one support trial uses the fixed source class covariance as its variance proxy. The numerical floor is $10^{-8}$.

### Conditional result and prediction

Under the specified Gaussian observation/prior model with known fixed noise matrices, completing the square gives the posterior above. For any estimate a, posterior expected squared error is tr(P)+‖a−θ̂‖²; the posterior mean minimizes that conditional risk. Plug-in covariance estimation, uncertainty in R_s, and uncertainty in source within-class covariance are outside that statement. The implementation propagates conditional class-mean uncertainty, not all representation uncertainty.

For class 0/1, let A_c=[I,−I] or [I, I]. The full candidate scores a Gaussian with mean A_cθ̂ and covariance Q_c=W+A_cPA_cᵀ, using equal class priors and fixed source within-class covariance W. Point prediction uses the same θ̂ and W without P. B/n assumes independent observations; serial-correlation simulations explicitly test violation of that approximation. The risk identity concerns class-mean squared error under the stated Gaussian model; classification accuracy and target BA are evaluated empirically.

### Complete arm definitions

| Saved method ID | Defining difference |
| --- | --- |
| source_tangent_frozen | Source-fixed means and within-class covariance |
| tangent_pooled | Ordinary source/support pooled means; fixed source within-class covariance |
| tangent_refit | Ordinary source/support refitting of means and within-class covariance |
| eb_point | Candidate posterior means; prediction uses fixed W without P |
| eb_predictive | Full candidate posterior means and predictive covariance |
| eb_isotropic | Isotropic mean-noise replacement, retaining predictive covariance |
| eb_coupled | One common shift scale instead of separate m/h scales |
| eb_no_source_noise | Same estimated T, with source mean-noise covariance removed |
| eb_no_shift | T=0, retaining finite-sample mean updating |

The candidate-minus-tangent_refit cap 20 comparison retains its prespecified primary role. Candidate-minus-saved-V2-EA-CSP is the strong reference. Other budgets and ablations provide the full component profiles.

## S 5. Neural update modes and optimization

The compact HPC network follows an EEGNet-style temporal/spatial architecture [@lawhern2018; @schirrmeister2017] and uses temporal_filters 8, depth_multiplier 2, kernel_length 64, source Dropout 0.25, BN epsilon 0.001 and momentum 0.01. The individual regime reuses 18 V2 checkpoint identities; the pooled regime uses three new shared source checkpoints trained on 240 source-training/120 source-validation examples. These six participants are the same people in both conditions.

All optimizer adaptations use 20 epochs, batch 16, AdamW, learning rate $10^{-4}$, weight decay $10^{-4}$, cosine scheduling and no AMP. A separate saved sampler controls support order. The methods reset to their own declared teacher before adapting each current-session/budget; they do not accumulate future support. Source normalization is reused rather than refitted from query.

| Policy (readable name) | Optimized parameters | Adaptation BN mode | Dropout during adaptation |
| --- | --- | --- | --- |
| Frozen | None | Source statistics | Off |
| Head only, fixed BN | Classifier head | Source statistics | Off |
| Full, fixed BN | All | Source statistics | Off |
| Full, adaptive BN | All | Current minibatch statistics; running-state updates | Off |
| Full, adaptive BN + Dropout | All | Current minibatch statistics; running-state updates | On |
| BN affine, fixed statistics | BN affine scale/bias only | Source statistics | Off |
| BN statistics only | No optimizer; one support batch | Running-state update | Off |
| Full, KL constrained | All, subject to source KL constraint | Source statistics | Off |

Canonical policy IDs are retained in the complete machine-readable tables: frozen, head_fixed, full_fixed, full_adaptive_bn, full_adaptive_bn_dropout, bn_affine_fixed, bn_stats_only and trust_fixed, in the row order above.

Adaptive normalization is an established transfer operation [@adabn2016; @wimpff2025continual]. Fixed/adaptive BN changes normalization during gradient computation and the resulting running state; weight trajectories can consequently differ. Within each budget, initialization, support order, Dropout and optimizer exposure are held fixed. Across budgets, examples and minibatch structure change together: batch 16 gives one batch per epoch for caps≤16 and two for 19/20. With three BN modules, 20 epochs correspond to 60 or 120 total batch-counter increments. Thus the within-budget comparison identifies the BN-mode effect, while the between-budget profiles combine label quantity, class composition and update schedule.

The source functional constraint draws on prediction-preservation and bounded-policy ideas [@lwf2016; @trpo2015]. The functional policy evaluates teacher-to-candidate mean KL on 40 source-training anchors and enforces δ=0.01 in the core experiment, with separate full runs at 0.001 and 0.1. Up to 12 halvings are attempted for a proposed optimizer step. Rejected proposals restore parameters and Adam state and are counted separately from accepted optimizer updates. These steps form the constrained optimizer’s proposal procedure. Pinsker and Jensen give mean anchor total variation ≤√(δ/2). The bound concerns prediction probabilities on the source anchors; target BA is an empirical endpoint.

## S 6. Complete reporting, intervals and influence

Machine-readable tables retain every method, budget, participant, session and seed, together with the predefined contrast roles. Original intervals use 10,000 participant resamples with seed 42; extension intervals use the same number with seed 20261023. Complete method and budget profiles accompany the selected component interpretations.

The cap 20 BN-mode participant-deletion mean ranges were +1.07 to +1.90 pp for individual sources and +1.34 to +2.29 pp for pooled sources. These summaries assess participant influence on the same six-person result.

Collapse means a model/session predicts one class on its query set even when both true classes exist. Cap 20 fixed-BN/adaptive-BN collapse counts were 8/16 for individual sources and 0/18 for pooled sources, each out of 90 nested seed/session cells. All predictions contributed to BA; participant averages define the independent endpoint.

## S 7. Complete saved synthetic grid

The fixed factorial grid used p∈{16, 64}, source examples per class∈{10, 20,100}, support examples per class∈{1, 2, 5, 10}, shift type∈{none, common, contrast, both}, anisotropy∈{1, 20}, and stationary AR(1) correlation∈{0, 0.5}. Shift scale was 0.5, with 50 paired draws and 100 query examples per class. All nine methods received the same source/support/query draws within each replicate. The estimator used its fixed variance approximation across all generating correlations.

All 172,800 saved cells were retained with finite metrics and explicit synthetic/software-validation flags. Cross entropy uses the true-class probability with a numerical lower bound of $10^{-15}$ before taking the logarithm. Outcomes comprise BA, cross entropy, binary Brier score and two class-mean squared-error definitions. Full-grid averaging gives every frozen scenario equal weight. Paired Monte Carlo variation measures the finite draws under these fixed generating conditions, separately from the human-participant endpoint intervals.

The companion figure and saved scenario table display performance by shift, noise anisotropy, dimension, source size and serial correlation. Full-grid summaries accompany the factor-specific profiles. Probability-based EEG diagnostics use the saved probabilities; their numerical logarithmic-scoring floor is identified in the analysis record.

## S 8. Calibration measurements and interpretation

Original source/support probes evaluated low-dimensional power and source-fitted representations, followed by supervised CSP4/LDA controls. The support-half analysis split each class chronologically and retained frozen source transforms. Among 30 sessions, 19 had positive signed source-score orientation in both halves, two were negative in both, and nine changed sign. These observations distinguish calibration-subset agreement from the intended class orientation, providing measurements for future support-driven policy tests.

The Kumar and V2/V3 endpoints are offline task-label decoding in the same longitudinal cohort. Cue/feedback contributions, zero-phase filtering and amplitude artifacts in fitting/query data affect their interpretation. Pooled-source and source-validation labels are explicit information-budget differences. The separate fixed-budget BNCI replication in Section S12 evaluates spatial update operations in another acquisition; independent neural validation remains a further step.

## S 9. Saved-result provenance and computational scope

The V3 raw received archive is `paper2-results-83cbdfdcfa541b3ab3addfc3.tar.gz`, 40,194,093 bytes, SHA256 `e509c2591efa21fff4dd47236e613ed6b611ca10ad20bac3da37e66e34a9d170`. It comprises three verified GitHub parts at fixed commit `500831c086d9e1d1e8412cf8ebca5fb6a288db76`. Its 49,984 payload files plus manifest matched their lengths and checksums; 126 unique valid task-completion identities matched the frozen queue. The public packet contains no original EEG, optimizer tensors or model weights.

Runtime, scheduler and storage records are provided in the repository audit reports. Saved-prediction reconstruction supplies the numerical verification.

Kumar analyses reused saved predictions, metrics and histories with their original fitted models, seeds and support windows. The external comparison in Section S12 generated its own four-method predictions. Original submission packages and all experiment outcomes remain at their versioned paths. Reproduction scripts, table definitions, figure inputs and targeted verification are identified in the accompanying revision report.

## S 10. Complete V3 cohort means across all frozen budgets

Values are BA percentages. Every row uses all six participants, all five target sessions and all declared seeds where applicable. `core`, `kl0p001` and `kl0p1` identify the separately frozen variants. The saved EA reference is included under the geometric scope after ordered query-identity alignment.

| Family / source / variant | Method | Cap 4 | Cap 8 | Cap 12 | Cap 16 | Cap 20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Geometry / own / core | EB coupled | 57.82 | 60.33 | 61.63 | 66.10 | 61.35 |
| Geometry / own / core | EB isotropic | 62.37 | 62.72 | 65.14 | 66.31 | 64.57 |
| Geometry / own / core | EB no shift | 59.06 | 57.23 | 60.62 | 62.53 | 60.22 |
| Geometry / own / core | EB no source noise | 57.83 | 59.95 | 63.01 | 65.27 | 61.71 |
| Geometry / own / core | EB point | 58.67 | 60.84 | 63.84 | 67.24 | 66.52 |
| Geometry / own / core | EB predictive | 59.11 | 61.48 | 63.92 | 66.63 | 64.68 |
| Geometry / own / core | Saved V2 EA-CSP | 66.79 | 67.48 | 67.71 | 70.86 | 70.37 |
| Geometry / own / core | Frozen tangent | 60.36 | 60.36 | 60.36 | 60.36 | 60.36 |
| Geometry / own / core | Pooled means | 59.46 | 59.73 | 61.61 | 64.46 | 64.08 |
| Geometry / own / core | Tangent refit | 63.50 | 62.90 | 66.19 | 66.97 | 67.01 |
| Neural / pooled / core | BN affine, fixed statistics | 55.23 | 55.02 | 55.39 | 55.49 | 55.46 |
| Neural / pooled / core | BN statistics only | 55.22 | 55.24 | 55.32 | 55.29 | 54.95 |
| Neural / pooled / core | Frozen | 55.26 | 55.26 | 55.26 | 55.26 | 55.26 |
| Neural / pooled / core | Full, adaptive BN | 55.27 | 55.61 | 55.41 | 55.34 | 54.31 |
| Neural / pooled / core | Full, adaptive BN + Dropout | 55.28 | 55.61 | 55.39 | 55.41 | 54.59 |
| Neural / pooled / core | Full, fixed BN | 56.02 | 55.61 | 55.90 | 56.66 | 56.22 |
| Neural / pooled / core | Head only, fixed BN | 55.48 | 55.41 | 55.57 | 55.74 | 55.54 |
| Neural / pooled / core | Full, KL constrained | 56.02 | 55.61 | 55.87 | 56.66 | 56.25 |
| Neural / pooled / KL 0.001 | Full, KL constrained | 55.77 | 55.25 | 55.64 | 56.45 | 56.03 |
| Neural / pooled / KL 0.1 | Full, KL constrained | 56.02 | 55.61 | 55.90 | 56.66 | 56.22 |
| Neural / individual / core | BN affine, fixed statistics | 56.73 | 56.73 | 56.76 | 57.11 | 57.04 |
| Neural / individual / core | BN statistics only | 56.73 | 56.73 | 56.71 | 56.73 | 55.59 |
| Neural / individual / core | Frozen | 56.74 | 56.74 | 56.74 | 56.74 | 56.74 |
| Neural / individual / core | Full, adaptive BN | 57.08 | 57.11 | 57.26 | 57.54 | 56.01 |
| Neural / individual / core | Full, adaptive BN + Dropout | 57.25 | 57.18 | 57.16 | 57.43 | 55.86 |
| Neural / individual / core | Full, fixed BN | 56.90 | 56.77 | 56.80 | 57.50 | 57.51 |
| Neural / individual / core | Head only, fixed BN | 56.39 | 56.45 | 56.84 | 56.88 | 56.81 |
| Neural / individual / core | Full, KL constrained | 56.91 | 56.83 | 56.87 | 57.50 | 57.50 |
| Neural / individual / KL 0.001 | Full, KL constrained | 56.64 | 56.68 | 56.83 | 57.32 | 57.29 |
| Neural / individual / KL 0.1 | Full, KL constrained | 56.90 | 56.77 | 56.80 | 57.50 | 57.51 |

All paired participant differences, pointwise intervals, negative-participant counts and reference-role labels are retained in the companion comparison table. The full primary geometric and neural outcomes appear in Section S13; this table supplies their complete budget context.

## S 11. Complete-grid synthetic method summary

These means give every frozen scenario and paired draw equal weight. Probability scoring uses the saved simulation definitions; these numerical scales apply to the synthetic generator.

| Method | BA (%) | Cross entropy | Binary Brier | Mean squared feature error |
| --- | ---: | ---: | ---: | ---: |
| source_tangent_frozen | 74.31 | 2.9701 | 0.2276 | 0.10815 |
| tangent_pooled | 75.72 | 2.5729 | 0.2134 | 0.08115 |
| tangent_refit | 76.19 | 2.2408 | 0.2064 | 0.08115 |
| eb_point | 70.40 | 3.9747 | 0.2688 | 0.26669 |
| eb_predictive | 70.36 | 3.6337 | 0.2669 | 0.26669 |
| eb_isotropic | 73.29 | 2.0276 | 0.2304 | 0.16210 |
| eb_coupled | 70.58 | 3.5845 | 0.2646 | 0.25179 |
| eb_no_source_noise | 70.28 | 3.7042 | 0.2681 | 0.25980 |
| eb_no_shift | 74.87 | 2.5946 | 0.2210 | 0.13010 |

The full candidate minus tangent refitting was −5.8255 BA points. Of 384 scenario means, eight favored the candidate and 376 favored refitting. Candidate feature-mean squared error was larger than refitting in every scenario mean. Posterior-predictive versus point candidate prediction changed mean cross entropy by −0.34094, Brier by −0.00191 and BA by −0.0398 percentage points. The contrasts separate probability scoring from classification and mean estimation.

## S 12. External component comparison with a fixed calibration budget

### Dataset, events and information access

BNCI2014-001/BCI Competition IV 2a contains nine participants, each recorded on two different days. The reviewed original publication and six-page protocol describe six MI runs/session, with 48 four-class trials per run. The released original MAT files have all class labels; only left/right labels 1/2 were mapped to 0/1. Their `classes` arrays were explicitly checked. The initial EOG calibration objects have no MI trial indices and were excluded from MI-run numbering.

The one-based MAT `trial` field marks trial start. Cue onset is 500 samples later at 250 Hz. Epochs contain samples `trial−1+500 : trial−1+1500`, or cue [0,4) seconds, following the source MI instruction. Processing retains the recorded reference and first 22 EEG channels, excludes EOG, converts microvolts to volts, and applies fourth-order Butterworth 8–30 Hz SOS zero-phase filtering within each continuous run. No query-dependent normalization is fitted.

T runs 1–4 provide 96 source examples (48/class); T run 5 is unused and T run 6 is retained as an unused 24-trial source-query partition. E run 1 supplies its first 20 hand trials as support; four remaining hand trials are excluded. E runs 2–6 supply 120 query examples (60/class), with 24 per run. Support retains chronological class imbalance rather than selecting balanced labels. All 576 original four-class records per person retain sample boundaries, original artifact flags, identities and exclusion reasons.

LDA-only, Full CSP/LDA and EA-CSP use identical 116 source/support trials; Frozen uses 96 source labels and zero target labels. EA has separate source/support covariance references and never estimates a reference from query signals. Four-component CSP and covariance/LDA shrinkage 0.1 use the existing V2 NumPy implementation. This differs from the original Kumar MNE/Ledoit–Wolf model and 40-example source setting; the between-dataset result cannot isolate acquisition from implementation and source-budget differences.

### Complete results

BA values are percentages. Differences are percentage points; participants, not four-method or run rows, are the independent units.

| Participant | Frozen | LDA-only | Full CSP/LDA | EA-CSP | Full − LDA | EA − Full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 87.50 | 85.00 | 84.17 | 90.00 | -0.83 | +5.83 |
| 2 | 49.17 | 49.17 | 54.17 | 56.67 | +5.00 | +2.50 |
| 3 | 88.33 | 90.00 | 90.00 | 95.00 | +0.00 | +5.00 |
| 4 | 73.33 | 71.67 | 65.00 | 72.50 | -6.67 | +7.50 |
| 5 | 49.17 | 49.17 | 53.33 | 59.17 | +4.17 | +5.83 |
| 6 | 58.33 | 59.17 | 59.17 | 65.83 | +0.00 | +6.67 |
| 7 | 50.83 | 57.50 | 58.33 | 74.17 | +0.83 | +15.83 |
| 8 | 93.33 | 94.17 | 94.17 | 95.00 | +0.00 | +0.83 |
| 9 | 85.00 | 89.17 | 88.33 | 89.17 | -0.83 | +0.83 |
| **Mean** | 70.56 | 71.67 | 71.85 | 77.50 | **+0.19** | **+5.65** |

| Contrast | Role | Mean difference, pp | Pointwise 95 % CI, pp | Exact p | Secondary Holm p |
| --- | --- | ---: | --- | ---: | ---: |
| Full − LDA-only | primary | +0.19 | [-1.85, 2.13] | 0.96875 | — |
| Full − Frozen | secondary | +1.30 | [-1.76, 3.98] | 0.45312 | 0.68750 |
| LDA-only − Frozen | secondary | +1.11 | [-0.46, 2.96] | 0.34375 | 0.68750 |
| EA − Full | secondary | +5.65 | [3.15, 8.70] | 0.00391 | 0.01172 |

The fixed primary comparison is Full−LDA-only, specified before this run's predictions. The three secondary comparisons form a separate Holm family. Exact two-sided sign-flip tests retain observed difference magnitudes over 512 assignments and use the absolute paired mean, with 1e−12 BA boundary tolerance. Pointwise percentile bootstrap intervals use 10,000 paired participant draws, seed 20261027 and numeric participant order 1–9.

Full−LDA-only is positive/negative/zero in 3/3/3 people; its leave-one-out mean spans −0.42 to +1.04 pp. EA−Full is positive in 9/9, with individual differences +0.83 to +15.83 pp and leave-one-out means +4.38 to +6.25 pp. Across query runs 2–6, EA−Full cohort means are +10.19, +2.78, +6.02, +6.94 and +2.31 pp. Floating-point tie handling is documented in the independent numerical audit.

### Original artifact flags and ethics sources

No artifact-marked trials were rejected. Across nine people, the original flags occurred in 87 source-fit, 17 support and 94 query trials. These retained flags are different from Kumar's amplitude rule. This experiment uses all original labeled hand trials in its assigned roles; the competition used an artifact-free-only scoring convention.

The inspected BNCI2a source paper and original protocol did not report a dataset-2a-specific ethics committee, approval number or consent form. The paper's Harborview IRB/informed-consent paragraph belongs to Dataset 4 (ECoG) and is not attributed to these participants. The secondary analysis uses public coded records under the national-law basis stated in the main text, without recontact or re-identification. Original MAT recordings retain CC BY-ND 4.0 terms; public derived tables and code do not relicense the source recordings.

### Version, execution and reconstruction

The protocol, raw-file identities and implementation were fixed at commit `457e7bdaad96e84782b6fe968f88925a1200c4b3` before prediction generation. The external experiment used nine source fits and 27 updating fits; frozen models reused the corresponding source fit. All 18 original MAT files matched the versioned NEMAR byte lengths and SHA256 checksums, totaling 779,873,919 bytes. Execution used Python 3.11.16, NumPy 2.2.6 and SciPy 1.15.3, with one BLAS thread.

The external public result folder is `research_logs/paper2_external_validation_20261027/`: all 36 saved prediction JSONs, trial-role manifests, participant/run tables, exact tests and an independent JSON-only reconstruction are retained. This covers 1,080 distinct target trials, 4,320 method-specific prediction rows and 180 nested run endpoints. Participants define the independent sample. BNCI had historical use in the first-paper project; the present component comparison was fixed in the repository before prediction generation.

The public repository supplies all saved predictions, trial-role manifests and numerical reconstruction code. Original EEG retains its source-data license. Private storage records and original transfer receipts are documented in the repository audit report.

Run `scripts/replay_paper2_external_saved_predictions_20261027.py` to regenerate the aggregate from public prediction JSON files. The result-folder REPRODUCE.md supplies the exact command and dependencies. Raw-data execution and resumption use the fixed script and a separate private output directory.


## S 13. Complete extension comparisons

### Covariance mixing and EA-CSP under matched labels

In the six-participant V2 extension at the 20-label cap, frozen classical decoding achieved 62.15 % BA, LDA-only 67.30 %, full CSP/LDA 68.65 % and EA-CSP 70.37 %. The covariance-mixture candidate achieved 69.24 %. The candidate improved on frozen decoding by +7.09 points (4.12–11.55). Its prespecified comparison with EA-CSP was −1.14 points (−3.52–1.14).

### Geometric estimation in a fixed tangent feature space

At the cap of 20 labels, EA-CSP achieved 70.37 % BA and ordinary tangent refitting 67.01 %, compared with 64.68 % for the geometric candidate. Its prespecified primary contrast was −2.33 points (−4.41 to −0.24), and its strong-reference contrast was −5.69 points (−9.30 to −2.22; Table S1). Both reference methods had higher BA in five of six participants. Ordinary tangent refitting had higher cohort-mean BA at all five support caps (Figure S1).

**Table S1. V3 geometric comparison at the 20-label cap.**

| Method | Mean BA | Candidate − method, pp |
| --- | ---: | ---: |
| Frozen source tangent model | 60.36 % | +4.32 [0.07, 8.61] |
| Pooled means with fixed source within-class covariance | 64.08 % | +0.60 [−3.09, 3.01] |
| Ordinary tangent refitting | 67.01 % | −2.33 [−4.41, −0.24] |
| Candidate means with point prediction | 66.52 % | −1.84 [−3.26, −0.46] |
| Full uncertainty-aware candidate | 64.68 % | Reference |
| Saved EA-CSP, strong reference | 70.37 % | −5.69 [−9.30, −2.22] |

BA, balanced accuracy; pp, percentage points. Ordinary tangent refitting was the frozen primary comparator. The same-query EA-CSP reference was imported from saved V2 predictions after ordered trial/label verification. Candidate ablations and every budget are retained in the supplementary methods and machine-readable tables.

The matched ablations distinguish three operations. Separating common and discriminative variation and retaining source-mean noise improved the cap-20 candidate over their respective ablations. Adding posterior covariance to the same posterior means reduced BA by 1.84 points relative to point prediction. The estimated common-location variation was larger than discriminative-contrast variation in every cap-20 support set. These observations distinguish changes in the estimated means from changes in predictive covariance.

![Figure S1](supplementary_figures/FigS1_geometry.png){width=150mm}

**Figure S1. Geometric candidate, matched controls and ablations.** Curves show BA across support budgets; paired cap-20 contrasts compare the candidate with tangent refitting, EA-CSP and matched ablations. Ablations vary posterior mean estimation, predictive covariance, source-mean noise and common/contrast shift scales. Intervals are participant-bootstrap summaries.

### Fixed source normalization reduced single-class predictions at the 20-label cap

At the 20-label cap, fixed-BN full updates predicted a single class in eight of 90 participant-by-seed-by-session query sets, compared with 16 for adaptive BN. Pooled-source counts were zero and 18, respectively. Fixed-BN BA was 57.51 %, versus 56.01 % for adaptive BN with individual sources, a difference of 1.50 points (0.33–2.74). Pooled-source values were 56.22 % and 54.31 %, a difference of 1.91 points (0.76–3.24; Table S2). Five of six participant differences favored fixed BN in each regime; the remaining difference was negative for individual sources and approximately zero for pooled sources. All participant-deletion mean contrasts stayed positive at this cap.

**Table S2. V3 neural component contrasts at the 20-label cap.**

| Contrast | Individual source models | Pooled source models | Role |
| --- | ---: | ---: | --- |
| Fixed-BN full update − adaptive-BN full update | +1.50 [0.33, 2.74] pp | +1.91 [0.76, 3.24] pp | BN-mode comparison |
| Fixed-BN full update − frozen | +0.77 [−0.16, 1.73] pp | +0.96 [−0.41, 2.77] pp | Update baseline |
| BN-statistics-only − frozen | −1.15 [−2.15, −0.12] pp | −0.30 [−0.68, 0.05] pp | Statistics-only comparison |
| Functional constraint − fixed-BN full update | −0.01 [−0.11, 0.09] pp | +0.03 [0.00, 0.09] pp | Prespecified neural primary contrast |
| Adaptive BN plus Dropout − adaptive BN | −0.15 [−0.40, 0.08] pp | +0.28 [0.04, 0.55] pp | Dropout comparison |

BN, batch normalization; KL, Kullback–Leibler divergence; pp, percentage points. Intervals summarize six participants after averaging fixed seeds and target sessions. Single-class prediction counts include 90 nested outcomes per arm. The functional-constraint row retains its predefined primary role. BN mode changes optimization-time normalization and the resulting inference state.

The full budget curves show how this contrast changes (Figure S2). Individual-source fixed-minus-adaptive BN differences were −0.18, −0.34, −0.46, −0.04 and +1.50 points across caps 4–20. Pooled-source differences were +0.75, +0.01, +0.48, +1.31 and +1.91 points. At the final support cap, batch size 16 also changed the number and size of minibatches: up to 16 support trials supplied one batch per epoch, whereas 19/20 supplied two. Three BN modules recorded 60 versus 120 cumulative batch-counter increments over 20 epochs. Within a support cap, the BN comparison holds minibatches and optimization exposure fixed. Across caps, label quantity, class composition and the normalization-update schedule change together.

![Figure S2](supplementary_figures/FigS2_neural_normalization.png){width=150mm}

**Figure S2. Neural normalization mode across support budgets.** Fixed-minus-adaptive BN contrasts are shown for both source regimes across all five caps, together with the cap-20 participant contrasts and single-class prediction counts. Fixed and adaptive BN use the same current support, initialization, optimizer budget and Dropout-off setting within each comparison. They differ in normalization during optimization and the resulting inference state. Collapse counts are nested seed/session observations; participant-level summaries define the uncertainty intervals.

### Source discrimination and functional-constraint effects

Frozen individual-source models achieved 56.74 % target BA, compared with 55.26 % for pooled-source models, a pooled-minus-individual difference of −1.48 points (−2.90 to −0.20). Source-query BA was 56.11 % and 57.78 %, respectively.

The three pooled models selected epochs 14, 20 and 17 by validation loss. Their final training losses were approximately 0.20–0.22, while final validation losses were 0.91–0.96, above the selected validation losses near 0.68.

At the core KL bound 0.01, the functional constraint changed the cap-20 mean relative to ordinary fixed-BN adaptation by −0.01 points for individual sources and +0.03 points for pooled sources. At bound 0.1, BA matched the ordinary update in both regimes; bound 0.001 produced differences of −0.22 and −0.19 points, respectively, with intervals crossing zero. The complete dose profiles and accepted/rejected-step histories are retained.

### Posterior covariance reduced simulated log loss with little change in accuracy

The full synthetic grid contained 172,800 numeric method-by-condition-by-repetition results. Equal-grid BA was 70.36 % for the candidate and 76.19 % for tangent refitting, a difference of −5.83 points; 376 of 384 scenario means favored refitting. Candidate feature-mean squared error was also larger. Adding posterior covariance to identical candidate means reduced mean cross entropy by 0.341 but changed BA by −0.04 points. Posterior covariance improved log loss for the same estimated means, with little change in classification accuracy (Figure S3).

![Figure S3](supplementary_figures/FigS3_mechanisms.png){width=150mm}

**Figure S3. Mechanism simulations and predictive uncertainty.** All 384 conditions retain 50 paired repeats. Panels show candidate-minus-refit BA by source size/correlation, all generating shifts, paired scenario BA, and posterior-versus-point changes in cross entropy and BA. Synthetic results are separate from human EEG endpoints.



## S 14. Original-pipeline calibration budgets and alignment

These completed component-follow-up results use the original eighteen Kumar participants. Source fitting used forty training trials and the current chronological support prefix, with source validation excluded. Support-only EA used a fixed 21-by-22 Helmert common-average basis, separate source/support arithmetic covariance means and their inverse square roots, followed by the same CSP/LDA estimator. Query signals passed through the fitted support transform. All following intervals are the original post-exposure pointwise participant-bootstrap summaries (10,000 draws, seed 42; numeric participant order). Historical main-analysis intervals and the four-comparison Holm family remain separately reported.

### Development cohort, six participants

BA in percent [pointwise 95% CI].

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA |
|---|---:|---:|---:|---:|
| 4 | 59.97 [57.34, 63.59] | 62.69 [59.02, 66.76] | 62.35 [57.53, 67.02] | 64.14 [60.57, 67.54] |
| 8 | 59.97 [57.34, 63.59] | 63.81 [60.21, 67.59] | 64.93 [59.55, 70.64] | 67.26 [63.20, 71.90] |
| 12 | 59.97 [57.34, 63.59] | 64.00 [60.38, 68.12] | 65.00 [59.63, 70.78] | 67.98 [63.58, 71.60] |
| 16 | 59.97 [57.34, 63.59] | 65.38 [61.01, 70.48] | 67.10 [61.19, 74.11] | 68.46 [63.28, 74.33] |
| full | 59.97 [57.34, 63.59] | 64.37 [56.99, 71.82] | 63.22 [58.39, 67.40] | 70.51 [66.15, 75.22] |

Paired gains in percentage points [pointwise 95% CI]; final count is participants whose measured gain was negative.

| Budget | LDA − frozen | Full − frozen | EA − frozen |
|---|---:|---:|---:|
| 4 | +2.72 [+1.27, +4.59]; 0/6 decreased | +2.38 [-0.58, +5.41]; 2/6 decreased | +4.17 [-0.18, +8.69]; 2/6 decreased |
| 8 | +3.84 [+1.81, +6.49]; 0/6 decreased | +4.96 [+1.12, +9.77]; 1/6 decreased | +7.29 [+2.78, +12.03]; 1/6 decreased |
| 12 | +4.03 [+1.41, +7.31]; 1/6 decreased | +5.03 [+0.68, +10.46]; 2/6 decreased | +8.01 [+3.24, +12.56]; 1/6 decreased |
| 16 | +5.41 [+2.63, +9.43]; 0/6 decreased | +7.13 [+1.98, +13.58]; 1/6 decreased | +8.49 [+3.69, +14.28]; 0/6 decreased |
| full | +4.40 [-1.75, +11.53]; 2/6 decreased | +3.25 [-0.90, +7.14]; 2/6 decreased | +10.53 [+5.21, +15.73]; 0/6 decreased |

| Budget | Full − LDA | EA − full |
|---|---:|---:|
| 4 | -0.33 [-2.94, +2.13]; 3/6 decreased | +1.79 [-2.87, +6.64]; 3/6 decreased |
| 8 | +1.12 [-1.20, +3.51]; 3/6 decreased | +2.33 [-1.89, +6.88]; 2/6 decreased |
| 12 | +1.00 [-2.29, +4.09]; 2/6 decreased | +2.98 [-0.35, +6.54]; 2/6 decreased |
| 16 | +1.72 [-1.85, +4.77]; 2/6 decreased | +1.36 [-0.08, +2.89]; 3/6 decreased |
| full | -1.15 [-5.02, +2.46]; 4/6 decreased | +7.29 [+2.90, +11.27]; 1/6 decreased |

### Original primary cohort, twelve participants

BA in percent [pointwise 95% CI].

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA |
|---|---:|---:|---:|---:|
| 4 | 57.94 [52.62, 63.62] | 58.83 [53.41, 64.59] | 58.74 [54.02, 63.95] | 60.22 [55.38, 65.55] |
| 8 | 57.94 [52.62, 63.62] | 60.07 [54.70, 66.06] | 61.25 [56.60, 66.37] | 66.10 [59.88, 72.32] |
| 12 | 57.94 [52.62, 63.62] | 61.41 [55.44, 67.98] | 64.31 [59.19, 69.78] | 67.59 [61.35, 73.82] |
| 16 | 57.94 [52.62, 63.62] | 62.14 [56.04, 68.50] | 66.93 [61.06, 72.78] | 70.08 [63.64, 76.19] |
| full | 57.94 [52.62, 63.62] | 59.89 [54.27, 65.44] | 65.36 [59.77, 70.83] | 70.66 [64.29, 76.76] |

Paired gains in percentage points [pointwise 95% CI]; final count is participants whose measured gain was negative.

| Budget | LDA − frozen | Full − frozen | EA − frozen |
|---|---:|---:|---:|
| 4 | +0.89 [-1.15, +2.66]; 4/12 decreased | +0.81 [-2.53, +4.17]; 7/12 decreased | +2.29 [-0.26, +4.84]; 4/12 decreased |
| 8 | +2.13 [+0.30, +3.87]; 4/12 decreased | +3.31 [-0.13, +6.94]; 4/12 decreased | +8.16 [+3.23, +13.08]; 3/12 decreased |
| 12 | +3.48 [+1.31, +5.48]; 3/12 decreased | +6.37 [+1.65, +11.18]; 4/12 decreased | +9.65 [+4.57, +14.83]; 1/12 decreased |
| 16 | +4.20 [+1.41, +6.76]; 2/12 decreased | +8.99 [+4.06, +14.23]; 2/12 decreased | +12.15 [+5.77, +18.82]; 2/12 decreased |
| full | +1.95 [-1.00, +5.03]; 5/12 decreased | +7.42 [+2.51, +12.43]; 3/12 decreased | +12.72 [+6.50, +19.10]; 2/12 decreased |

| Budget | Full − LDA | EA − full |
|---|---:|---:|
| 4 | -0.08 [-2.95, +2.54]; 6/12 decreased | +1.48 [-0.76, +3.58]; 4/12 decreased |
| 8 | +1.18 [-1.35, +3.91]; 6/12 decreased | +4.85 [+2.20, +7.76]; 2/12 decreased |
| 12 | +2.90 [-1.12, +7.02]; 4/12 decreased | +3.28 [+1.30, +5.31]; 3/12 decreased |
| 16 | +4.79 [+1.32, +8.41]; 3/12 decreased | +3.15 [+1.21, +4.98]; 2/12 decreased |
| full | +5.47 [+2.16, +8.88]; 2/12 decreased | +5.30 [+2.81, +8.26]; 2/12 decreased |

### All eighteen participants, descriptive

BA in percent [pointwise 95% CI].

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA |
|---|---:|---:|---:|---:|
| 4 | 58.62 [54.80, 62.52] | 60.11 [56.05, 64.25] | 59.95 [56.17, 63.86] | 61.53 [57.86, 65.27] |
| 8 | 58.62 [54.80, 62.52] | 61.32 [57.27, 65.55] | 62.47 [58.60, 66.45] | 66.48 [62.04, 70.90] |
| 12 | 58.62 [54.80, 62.52] | 62.28 [57.91, 66.85] | 64.54 [60.51, 68.73] | 67.72 [63.28, 72.09] |
| 16 | 58.62 [54.80, 62.52] | 63.22 [58.66, 67.78] | 66.99 [62.46, 71.56] | 69.54 [64.83, 74.10] |
| full | 58.62 [54.80, 62.52] | 61.38 [56.61, 66.09] | 64.65 [60.56, 68.73] | 70.61 [66.12, 74.99] |

Paired gains in percentage points [pointwise 95% CI]; final count is participants whose measured gain was negative.

| Budget | LDA − frozen | Full − frozen | EA − frozen |
|---|---:|---:|---:|
| 4 | +1.50 [-0.01, +2.86]; 4/18 decreased | +1.33 [-1.17, +3.84]; 9/18 decreased | +2.91 [+0.63, +5.29]; 6/18 decreased |
| 8 | +2.70 [+1.23, +4.21]; 4/18 decreased | +3.86 [+1.12, +6.78]; 5/18 decreased | +7.87 [+4.29, +11.62]; 4/18 decreased |
| 12 | +3.66 [+1.97, +5.37]; 4/18 decreased | +5.92 [+2.39, +9.64]; 6/18 decreased | +9.10 [+5.36, +13.07]; 2/18 decreased |
| 16 | +4.60 [+2.42, +6.83]; 2/18 decreased | +8.37 [+4.57, +12.53]; 3/18 decreased | +10.93 [+6.38, +15.93]; 2/18 decreased |
| full | +2.77 [-0.15, +6.01]; 7/18 decreased | +6.03 [+2.44, +9.88]; 5/18 decreased | +11.99 [+7.53, +16.76]; 2/18 decreased |

| Budget | Full − LDA | EA − full |
|---|---:|---:|
| 4 | -0.17 [-2.25, +1.85]; 9/18 decreased | +1.58 [-0.61, +3.79]; 7/18 decreased |
| 8 | +1.16 [-0.75, +3.17]; 9/18 decreased | +4.01 [+1.67, +6.56]; 4/18 decreased |
| 12 | +2.26 [-0.56, +5.31]; 6/18 decreased | +3.18 [+1.47, +4.97]; 5/18 decreased |
| 16 | +3.77 [+1.15, +6.53]; 5/18 decreased | +2.56 [+1.16, +3.96]; 5/18 decreased |
| full | +3.26 [+0.37, +6.26]; 6/18 decreased | +5.96 [+3.74, +8.41]; 3/18 decreased |

### Completion and class counts

There were no scientific fallbacks, undefined query BAs or missing query classes. The budget actions had 1,170 newly attempted/completed fits and 630 historical prediction reuses. Half-support validation fits are separate and are not added to these budget counts. Six 4-label prefixes lacked one support class (development 1/30, remaining 5/60); all stayed included and completed their candidate fits using the fixed two-class source 40. Budgets 8/12/16/full had no missing support class.

Prediction class-collapse counts per 90 repeated participant/session cells; these are descriptive repeats, not independent sample sizes.

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA | Shared single-class support | Fallbacks, all methods |
|---|---:|---:|---:|---:|---:|---:|
| 4 | 3 | 4 | 10 | 1 | 6 | 0 |
| 8 | 3 | 3 | 10 | 3 | 0 | 0 |
| 12 | 3 | 3 | 6 | 0 | 0 | 0 |
| 16 | 3 | 1 | 3 | 0 | 0 | 0 |
| full | 3 | 0 | 0 | 0 | 0 | 0 |

### Budget profiles and participant variation

At 4/8/12 labels in remaining 12, full−LDA pointwise intervals include zero; their paired means are−0.08/+1.18/+2.90pp. At 4 labels full−frozen and EA−full intervals also include zero, with 7/12 and 4/12 participants respectively showing negative measured changes. Full support does not improve every method monotonically over the 16-label point: remaining 12 LDA means are 62.14% then 59.89%, and full-refit means 66.93% then 65.36%. These observations do not select 16 labels as an operating budget.

At full support the development 6 full−LDA mean is −1.15 pp [−5.02,+2.46], with 4/6 participants lower; remaining 12 has +5.47 pp [+2.16,+8.88], with 2/12 lower. The development and primary cohorts retain these distinct component-update profiles. Remaining12 EA−full means are positive at every budget, but measured participant decreases remain 4/2/3/2/2 across 4/8/12/16/full labels. The corresponding 4-label interval includes zero. EA supplies the stronger alignment reference alongside the original three-action component comparison. These endpoints describe offline task-label decoding under the declared calibration budgets.

CSV tables retain full precision, all individual curves, all exact class counts, every status/reason and actual complete participant lists. Three figures with source CSVs are in `manuscript/figures/component_followup_20261016/budget/`. The original execution receipt binds the fixed script/protocol/input hashes and all initial output hashes; the 16 October formatting-only review is bound separately by results_review_receipt.json.


## S 15. Marker-aware window sensitivity

This completed comparison used saved predictions on common eligible queries. Its nine-person conditional cohort and eight-person metadata-complete sensitivity are subsets of the same Kumar participants. The original twelve-person endpoint remains separate. Participant-bootstrap intervals used 10,000 draws and seed 42 with the phase-summary script's lexical participant order.

### Conditional phase-window results

All differences and confidence intervals below are percentage points (pp).

| Scope | Window | Full CSP/LDA − frozen | Full CSP/LDA − LDA only |
|---|---|---:|---:|
| Conditional primary, n=9 | Cue-anchored 5 s | 2.06 [−3.73, 8.17] | 0.17 [−4.63, 4.86] |
| Conditional primary, n=9 | Task-start 2 s | 3.21 [0.08, 6.56] | 2.38 [−1.29, 5.89] |
| Metadata-complete primary, n=8 | Cue-anchored 5 s | 3.98 [−0.90, 9.81] | 1.78 [−2.26, 5.92] |
| Metadata-complete primary, n=8 | Task-start 2 s | 3.46 [−0.02, 7.12] | 3.63 [0.54, 6.68] |

The paired change in the full-minus-frozen gain (task-start 2 s minus cue-anchored 5 s) was **1.15 pp [−5.55, 7.22]** in n=9 and **−0.51 pp [−7.30, 5.23]** in n=8. The corresponding full-minus-LDA-only gain changes were **2.21 pp [−2.31, 6.47]** and **1.85 pp [−3.25, 6.62]**. Every gain-change interval includes zero. A positive interval for an individual window/contrast does not establish that its benefit differs between windows.

Individual full-minus-frozen five-session differences in n=9 ranged from **−13.25 to +18.77 pp** for cue 5 s (4 positive, 5 negative) and **−2.75 to +10.96 pp** for task 2 s (6 positive, 3 negative). In n=8, the ranges were **−2.59 to +18.77 pp** (4 positive, 4 negative) and **−2.75 to +10.96 pp** (5 positive, 3 negative). These are observed participant differences, not proof of individual clinical harm or benefit. All individual values and all development contrasts remain in the CSV/JSON files.

### Marker coverage and eligibility

- `sub-11/ses-4` has only the left class among common eligible queries (20 left, 0 right), so BA is undefined; its six corresponding action/window cells are retained as null. It has no complete five-session endpoint.
- `sub-15/ses-5` has only **5 common eligible query trials (2 left, 3 right)**; 19 other originally included query trials have unknown original phase mapping. The conditional n=9 scope includes this noisy endpoint and marks it prominently. The n=8 sensitivity uses the same saved predictions and removes no other participant on effect size or sign.
- `sub-16`, `sub-17`, and `sub-18` lack online phase mapping, so all their target-session comparison cells are retained as null. In total, 980/7,200 original event rows still lack original phase mapping. No unknown row is assumed to be a noneligible task or a correct mapping.
- Eligibility required a class-matched task end at least 2 s after task start, EDF completeness, and inclusion in the original complete-window set. The 44 originally partial windows remain excluded. End duration may depend on online outcome and speed, so this subset is not an unbiased representation of all trials.
- The comparison jointly changes anchor (cue versus task start), window length (5 s versus 2 s), and window-local filtering edges. It is not a pure intervention on feedback contamination or a causal demonstration of sustained imagery. Queries and available support are matched within this exploratory comparison, but support can be smaller than the original 20-label budget. It cannot isolate which change explains an observed difference.
- The original three-action phase comparison did not include EA. The separate EA phase extension for this revision is reported in Section S20. The original comparison fitted no task-aware update-selection rule.

### Public saved-prediction reconstruction

The public data package contains gzip copies of the unchanged budget and phase prediction CSVs, original metrics, the fixed trial-role manifest and all existing interval tables. The supplied `scripts/review_kumar_component_saved_evidence_20261029.py` reconstructs all 1,800 budget cells and 540 phase cells, retaining undefined endpoints. The revision-folder REPRODUCE.md provides the exact command. No original private path or model tensors are needed for this numerical reconstruction.

## S 16. Present saved-prediction reanalysis: definitions and reconstruction

The present plan was committed at `13dd764` before the revision's new computations. It is a post-exposure analysis of existing evidence, not historical preregistration. The hard-label replay reads 78,600 Kumar budget prediction rows and 4,320 BNCI method-specific rows, with fixed trial-role manifests and the frozen Kumar query-QC ledger. Kumar data retain all 18 participants, five target sessions, five calibration budgets and four methods. BNCI retains nine participants, four methods and 120 target-query trials per person. Reconstructing these 82,920 rows involved no new model fit or query forward pass.

For Kumar, predictions match on participant/session/budget/trial identity; the join validates class labels and common query order. The class map is 0=left hand and 1=right hand. Support/query membership follows the original split manifest. For BNCI, saved JSONs are matched to their original trial-role manifests; the source 96, support 20 and target-query 120 roles remain distinct. Raw task/phase eligibility and synthetic examples are not mixed into this hard-label scope.

For endpoint unit u and true class c, recall is the correctly predicted count divided by that class's actual query count. Both classes must be present for BA, W and H. The two class recalls, BA, W=min(rL,rR) and H=|rL−rR| are first calculated within u. Kumar then averages five target sessions equally within each person. BNCI retains its original pooled 120-query endpoint for each person; its run-level metrics are descriptive. This order preserves the nonlinear weak-class and gap definitions. `W=BA−H/2` holds at each defined endpoint and after the common linear aggregation.

**Table S3. Full-support method means reconstructed from saved predictions.** Values are percentages. W is weak-class recall; H is the absolute recall gap. The all 18 Kumar scope is the union of the other two scopes, not an additional sample.

| Cohort | Method | BA | W | H | Left recall | Right recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Kumar primary 12 | Frozen | 57.94 | 36.06 | 43.75 | 62.52 | 53.36 |
| Kumar primary 12 | LDA-only | 59.89 | 43.75 | 32.27 | 61.29 | 58.49 |
| Kumar primary 12 | Full | 65.36 | 46.52 | 37.69 | 67.45 | 63.27 |
| Kumar primary 12 | EA | 70.66 | 56.97 | 27.38 | 70.79 | 70.53 |
| Kumar development 6 | Frozen | 59.97 | 37.23 | 45.49 | 64.53 | 55.42 |
| Kumar development 6 | LDA-only | 64.37 | 44.38 | 39.98 | 64.13 | 64.61 |
| Kumar development 6 | Full | 63.22 | 40.52 | 45.41 | 62.13 | 64.31 |
| Kumar development 6 | EA | 70.51 | 58.37 | 24.27 | 65.27 | 75.74 |
| Kumar all 18 | Frozen | 58.62 | 36.45 | 44.33 | 63.19 | 54.05 |
| Kumar all 18 | LDA-only | 61.38 | 43.96 | 34.84 | 62.23 | 60.53 |
| Kumar all 18 | Full | 64.65 | 44.52 | 40.26 | 65.67 | 63.62 |
| Kumar all 18 | EA | 70.61 | 57.44 | 26.34 | 68.95 | 72.27 |
| BNCI 9 | Frozen | 70.56 | 53.52 | 34.07 | 67.22 | 73.89 |
| BNCI 9 | LDA-only | 71.67 | 58.15 | 27.04 | 69.44 | 73.89 |
| BNCI 9 | Full | 71.85 | 58.15 | 27.41 | 73.33 | 70.37 |
| BNCI 9 | EA | 77.50 | 66.67 | 21.67 | 71.67 | 83.33 |

These cohort W/H means average endpoint-level values; they cannot be reproduced by taking the minimum or absolute difference of the cohort's two mean recalls. All individual endpoint class counts, missingness, predictions and status fields remain in `analysis/endpoint_metrics.csv`; participant averages are in `analysis/participant_metrics.csv`.

## S 17. EA transitions, joint effects and influence

For paired binary hard predictions, class-balanced query weights 1/(2n_c) give corrected error mass C, introduced mass I and prediction disagreement D. Verification checks `C−I=ΔBA` and `C+I=D` without rounding. The current computation independently reconstructs the EA transition quantities already reported from these same Paper2 predictions in the related integrated report; it does not count that earlier analysis as another experiment. Weak-class and joint-effect summaries are recomputed in the Paper2 scopes under the present plan.

**Table S4. EA-minus-full estimates at full support.** Differences and error masses are percentage points. All intervals below are new descriptive paired participant-percentile intervals, 10,000 resamples, seed 20261104, numeric participant order and linear quantiles. Historical BA intervals in the main Table 2 retain their original draws and roles.

| Cohort | ΔBA | ΔW | ΔH | Corrected C | Introduced I | Disagreement D |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Kumar primary 12 | +5.30 [+2.85, +8.21] | +10.45 [+5.11, +16.04] | -10.31 [-16.89, -3.70] | +14.61 [+11.52, +17.75] | +9.32 [+7.11, +11.64] | +23.93 [+19.17, +28.67] |
| Kumar development 6 | +7.29 [+2.90, +11.27] | +17.85 [+11.27, +24.51] | -21.13 [-28.46, -15.70] | +15.83 [+11.02, +21.34] | +8.54 [+4.55, +12.70] | +24.38 [+16.33, +33.15] |
| Kumar all 18 | +5.96 [+3.68, +8.37] | +12.92 [+8.36, +17.61] | -13.92 [-19.43, -8.30] | +15.02 [+12.32, +17.81] | +9.06 [+7.00, +11.09] | +24.08 [+19.88, +28.38] |
| BNCI 9 | +5.65 [+3.15, +8.70] | +8.52 [+5.00, +12.59] | -5.74 [-10.74, -0.93] | +12.78 [+8.15, +17.78] | +7.13 [+3.06, +12.31] | +19.91 [+11.76, +29.54] |

C and I use the whole class-balanced query denominator. For example, the primary Kumar values are 14.6147660819 and 9.3166969147 points, giving 5.2980691672 points before display rounding. A correction rate conditioned on reference errors would have a different denominator and would not reconstruct the BA difference.

**Table S5. Participant joint BA/weak-class outcomes for EA versus full.** Values are counts. The sign tolerance is 10\(^{-12}\) in fraction units; zeros are not assigned to benefit or decline.

| BA sign | W sign | Kumar primary 12 | Kumar development 6 | Kumar all 18 | BNCI 9 |
| --- | --- | ---: | ---: | ---: | ---: |
| positive | positive | 10 | 5 | 15 | 9 |
| positive | zero | 0 | 0 | 0 | 0 |
| positive | negative | 0 | 0 | 0 | 0 |
| zero | positive | 0 | 0 | 0 | 0 |
| zero | zero | 0 | 0 | 0 | 0 |
| zero | negative | 0 | 0 | 0 | 0 |
| negative | positive | 0 | 1 | 1 | 0 |
| negative | zero | 0 | 0 | 0 | 0 |
| negative | negative | 2 | 0 | 2 | 0 |

For the twelve-person Kumar scope, EA-minus-full BA is negative in 18 of 60 session outcomes, despite a positive mean in ten participants. The two participant-average BA changes are −0.17 and −0.39 points, while their W changes are −4.00 and −3.19 points. The single-participant-deletion BA mean remains positive, 4.29–5.81 points. Actual participant effects, medians, ranges and within-person negative-session proportions are retained in `analysis/participant_contrasts.csv` and `cohort_contrasts.csv`.

The anatomical class summaries preserve a further distinction. Kumar left/right mean recall changes are +3.34 [−4.81,11.37] and +7.26 [1.60,13.11] points. BNCI left/right changes are −1.67 [−12.41,8.15] and +12.96 [4.44,22.96]. Dynamic weak-class improvement thus does not mean both fixed hand-class cohort means increased. The recall gap can also decrease through changes in either class; both recalls accompany W/H throughout.

## S 18. Same-cohort amplitude sensitivity and probability availability

The original raw 250 µV peak-to-peak flags are joined by immutable Kumar trial IDs. They restrict query scoring only. An eligible complete participant endpoint requires both unflagged true classes in each of five target sessions. Ten of the original primary twelve meet that criterion: sub-2, 3, 5, 6, 9, 11, 14, 15, 17 and 18. The same ten participants define the all-query reference, avoiding a comparison between an original 12-person mean and a restricted 10-person mean. All participant/session class counts and undefined cases remain explicit in the endpoint table.

**Table S6. EA-minus-full on the same ten eligible participants.** Differences and intervals are percentage points. The last column is the participant-paired change in the contrast after query restriction, not a subtraction of two marginal confidence limits.

| Metric | All queries, same ten | Unflagged queries | Paired restricted-minus-all change |
| --- | ---: | ---: | ---: |
| ΔBA | +5.78 [+2.96, +9.12] | +6.07 [+2.38, +10.44] | +0.30 [-1.01, +1.52] |
| ΔW | +11.76 [+5.85, +17.81] | +11.31 [+3.85, +18.95] | -0.45 [-4.09, +2.02] |
| ΔH | -11.97 [-19.24, -4.78] | -10.47 [-19.21, -1.58] | +1.50 [-1.45, +6.46] |
| Δleft recall | +4.11 [-4.52, +12.85] | +3.95 [-4.86, +12.97] | -0.17 [-2.03, +1.41] |
| Δright recall | +7.44 [+0.77, +13.96] | +8.20 [+1.89, +14.36] | +0.76 [-1.21, +2.53] |

The amplitude restriction evaluates the existing predictions on a declared query subset. Unflagged does not mean artifact-free, and source/support exposure is unchanged. Original BNCI artifact flags remain a separate annotation system: no BNCI artifact exclusion is introduced by this Kumar sensitivity.

Both selected conventional exports contain hard class labels, not probability vectors or logits. Balanced NLL and Brier are therefore unavailable for this replay. They are not inferred from class labels. The historical neural/synthetic probability endpoints in Sections S7, S10–S11 and S13 retain their original definitions and distinct information regimes.

## S 19. Matched-coordinate scale and covariance sensitivities

The four fixed sensitivity arms were completed under the analysis plan committed at 13dd764. All use the original source training and full current-support identities, with no query reference fitting or parameter selection. The scope contains 18 Kumar participants×five target sessions×four arms and nine BNCI participants×four arms, totaling 396 new target fits. All 544 new fits in this revision include these 396 plus 148 additional EA phase fits; historical neural source models were not retrained. The complete execution history, including the operational stop and same-state continuation without repeating completed fits, remains in the repository receipts.

For Kumar, every arm first projects common-average signals into the same fixed 21×22 Helmert coordinates. Full refitting applies the unchanged CSP/LDA core to the source/support union. Common RMS divides each complete trial by one scalar equal to the square root of mean squared signal across coordinate/time; it changes amplitude information. Diagonal alignment estimates separate source/support mean covariance references and retains only their diagonals in the fixed Helmert coordinates. Full EA retains the full references. The Kumar reference estimate has no extra shrinkage; every arm then shares four-component MNE CSP, Ledoit–Wolf covariance regularization, `norm_trace=False`, full rank and LDA `lsqr`/automatic shrinkage.

BNCI retains the original 22-channel recorded-reference arrays and original fixed 0.1 covariance/LDA-shrinkage NumPy core. Source/support domain references use its fixed 0.1 shrinkage. Its diagonal entries therefore refer to the original channel coordinates; Kumar diagonals refer to Helmert contrasts. Source/support counts remain 40/19–20 in Kumar and 96/20 in BNCI. No cross-dataset preprocessing unification or hyperparameter grid was introduced.

**Table S7. Matched-arm performance and genuine probability scores.** BA is percent; NLL is nats; Brier is the binary single-coordinate class-balanced score in squared-probability units. All means first respect the original participant endpoint weights.

| Cohort | Arm | BA | Balanced NLL | Balanced Brier |
| --- | --- | ---: | ---: | ---: |
| Kumar primary 12 | Full | 65.36 | 0.70856 | 0.21958 |
| Kumar primary 12 | Common RMS + Full | 69.52 | 0.69209 | 0.20739 |
| Kumar primary 12 | Diagonal reference + Full | 67.88 | 0.68674 | 0.21150 |
| Kumar primary 12 | Full covariance EA + Full | 70.43 | 0.72715 | 0.21036 |
| Kumar development 6 | Full | 63.11 | 0.74835 | 0.22993 |
| Kumar development 6 | Common RMS + Full | 67.03 | 0.69755 | 0.22322 |
| Kumar development 6 | Diagonal reference + Full | 63.88 | 0.73138 | 0.22719 |
| Kumar development 6 | Full covariance EA + Full | 69.86 | 0.72863 | 0.21376 |
| Kumar all 18 | Full | 64.61 | 0.72183 | 0.22303 |
| Kumar all 18 | Common RMS + Full | 68.69 | 0.69391 | 0.21267 |
| Kumar all 18 | Diagonal reference + Full | 66.55 | 0.70162 | 0.21673 |
| Kumar all 18 | Full covariance EA + Full | 70.24 | 0.72765 | 0.21149 |
| BNCI 9 | Full | 71.85 | 0.54569 | 0.18021 |
| BNCI 9 | Common RMS + Full | 72.87 | 0.53950 | 0.17774 |
| BNCI 9 | Diagonal reference + Full | 72.59 | 0.54584 | 0.18050 |
| BNCI 9 | Full covariance EA + Full | 77.50 | 0.47304 | 0.15392 |

The shared-coordinate Kumar EA score 70.43% differs from the historical whitening/re-embedding endpoint 70.66%; the new 5.07-point contrast does not overwrite the historical 5.30-point estimate. Historical BNCI Full/EA predictions were exactly reproduced. The full per-participant and per-cell results remain in `mechanisms/participant_metrics.csv` and `mechanisms/run01/cells/`.

**Table S8. Prespecified focal matched-arm contrasts.** Values are new descriptive paired participant 95% intervals. BA differences use percentage points; NLL and Brier retain their own units. The complete output CSV retains all six pairwise contrasts and all seven metrics for every emitted cohort; this table displays the focal EA comparisons.

| Cohort | Contrast | ΔBA, pp | ΔNLL, nats | ΔBrier |
| --- | --- | ---: | ---: | ---: |
| Kumar primary 12 | EA−Full | +5.07 [+2.88, +7.71] | +0.01859 [-0.04038, +0.07941] | -0.00923 [-0.02739, +0.00717] |
| Kumar primary 12 | EA−RMS | +0.91 [-1.28, +3.18] | +0.03506 [-0.05592, +0.11604] | +0.00297 [-0.01679, +0.01943] |
| Kumar primary 12 | EA−diagonal | +2.55 [+0.59, +4.49] | +0.04041 [-0.00120, +0.07674] | -0.00115 [-0.01376, +0.01114] |
| Kumar development 6 | EA−Full | +6.75 [+2.75, +10.34] | -0.01972 [-0.07233, +0.03509] | -0.01617 [-0.03174, -0.00157] |
| Kumar development 6 | EA−RMS | +2.83 [-3.26, +9.20] | +0.03108 [-0.02915, +0.09866] | -0.00946 [-0.03408, +0.01503] |
| Kumar development 6 | EA−diagonal | +5.97 [+2.89, +9.06] | -0.00275 [-0.06806, +0.07504] | -0.01343 [-0.03545, +0.00461] |
| Kumar all 18 | EA−Full | +5.63 [+3.60, +7.78] | +0.00582 [-0.03883, +0.05065] | -0.01154 [-0.02449, +0.00060] |
| Kumar all 18 | EA−RMS | +1.55 [-0.91, +4.25] | +0.03373 [-0.03047, +0.09355] | -0.00117 [-0.01696, +0.01312] |
| Kumar all 18 | EA−diagonal | +3.69 [+1.89, +5.54] | +0.02603 [-0.01142, +0.06226] | -0.00524 [-0.01664, +0.00529] |
| BNCI 9 | EA−Full | +5.65 [+3.15, +8.70] | -0.07265 [-0.16079, -0.00720] | -0.02629 [-0.05188, -0.00771] |
| BNCI 9 | EA−RMS | +4.63 [+1.94, +7.96] | -0.06647 [-0.14807, -0.00661] | -0.02382 [-0.04790, -0.00628] |
| BNCI 9 | EA−diagonal | +4.91 [+1.94, +8.24] | -0.07280 [-0.15552, -0.00982] | -0.02658 [-0.05007, -0.00819] |

Probabilities are actual saved class 1/right-hand outputs, with model class order [0,1]. NLL uses class-equal averaging and clipping to [10\(^{-7}\),1−10\(^{-7}\)]; the Brier score averages `(p_right−y)^2` within each true class and then gives classes equal weight. It does not sum two probability coordinates. The input hard-label archives were never converted into fabricated probabilities.

Matched aligned arms retain source/support reference spectra and condition numbers. Support class counts are recorded; Kumar main cells also retain the number of support trials flagged by the existing amplitude rule. Fitted-state hashes before and after prediction were identical. References and classifiers used source/support only; query signals were transformed with the precomputed target reference. The query-label perturbation and state-invariance tests assess this separation. All 32 undefined phase cells and the original operational exception remain explicit rather than being reclassified as successful evaluations. No estimator scientific fit failed among the 544 completed fits.


## S 20. EA task-window extension

This extension adds EA to the original paired phase protocol; it does not relabel the earlier three-action result as EA evidence. The original 40 source TRAIN identities, common eligible support/query identities and frozen full-refit outputs were checked before fitting EA. The corresponding cue5s/task2s signals were used for source training, current support and later query in each pipeline. EA retains the historical 21-dimensional reference whitening re-embedded into 22 channels and original CSP/LDA defaults, separately from the matched 21-dimensional experiment in Section S19.

There are 148 new successful EA phase fits across all defined participant/session/window cells. Thirty-two original undefined cells retain their missing-marker, missing-class or otherwise undefined status without fitting; no marker was imputed. Original full predictions were replayed from their saved archive rather than retrained. In the nine-person conditional primary scope, all cells have 40 source examples, 4–19 support trials and 5–57 query trials. Each cue/task pair shares trial identities and class counts. This reduced, variable support budget must not be described as the original complete 19/20-label endpoint.

The nine conditional participants are sub-2, 3, 5, 6, 8, 9, 12, 14 and 15. The metadata-complete subset contains the same list except sub-15. Its sub-15/ses-5 endpoint has five common queries (two left, three right) and 19 unknown original query-phase mappings; the conditional result retains it, while the metadata-complete result follows the original exclusion. Sub-11/ses-4 lacks the right query class in this scope. Participants 16–18 lack the required online phase mapping. All identities, counts and undefined endpoints are preserved in the cell and phase participant tables.

**Table S9. Paired EA-minus-full phase comparisons.** Effects and intervals are percentage points, with the present 10,000-draw seed 20261104 paired participant bootstrap. Task-minus-cue is computed within each person before its interval; it is not the difference between marginal interval limits.

| Scope | n | Window or paired change | EA−Full, pp [95% interval] |
| --- | ---: | --- | ---: |
| Conditional | 9 | Cue-anchored 5 s | +7.85 [+3.04, +13.66] |
| Conditional | 9 | Task-start 2 s | +0.13 [-1.40, +1.92] |
| Conditional | 9 | Task 2 s−cue 5 s | -7.73 [-12.17, -3.76] |
| Metadata-complete | 8 | Cue-anchored 5 s | +7.55 [+2.32, +13.95] |
| Metadata-complete | 8 | Task-start 2 s | +0.53 [-1.01, +2.39] |
| Metadata-complete | 8 | Task 2 s−cue 5 s | -7.03 [-11.84, -2.97] |

The conditional and metadata-complete results show a larger added EA increment for the cue-anchored 5 s pipeline than for the task-start 2 s pipeline. The comparison changes anchor, duration, source/support/query waveforms and local filtering boundaries together. It identifies a dependence on the complete signal definition, rather than a causal effect of imagery duration or feedback removal. It does not convert the restricted phase sample into an unbiased version of the original cohort. Probabilities saved by the new EA phase fits are not paired with probabilities for the historical hard-label Full outputs, so no phase EA-minus-full probability contrast is manufactured.



## Supplementary references

::: {#refs}
:::
