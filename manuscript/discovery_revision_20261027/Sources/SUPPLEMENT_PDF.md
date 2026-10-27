# S 1 Text. Component-wise recalibration: detailed methods and complete comparison scope

This supplement accompanies *Spatial-filter refitting improves limited-label EEG decoding beyond classifier recalibration*. It defines the matched-label component analysis, original comparison and subsequent component experiments. Original scientific and provenance supplements remain available at their versioned paths.

## S 1. Study layers and statistical units

| Layer | Participants | Scientific role | Model/seed information | Selection status |
| --- | --- | --- | --- | --- |
| Original comparison | 18, partitioned as six development and 12 primary | Full CSP/LDA minus frozen was the primary contrast; full minus LDA-only was secondary | Original EEGNet reference: three seeds and 54 source models | Original pipeline and endpoint hierarchy frozen before primary performance calculation; prior exploratory exposure retained in the record |
| V2 extension | The same six development participants | Candidate covariance mixture versus EA-CSP; support-budget and neural diagnostics | 18 separately versioned individual sources | Later design informed by earlier results |
| V3 extension | The same six development participants | Predefined candidate comparisons and component mechanisms | Read-only reuse of 18 V2 sources; three new pooled sources; all fixed seeds | Task matrix and comparison roles frozen before execution |
| Mechanism simulation | No human participants | Known-mechanism estimator stress tests | 384 scenarios × 50 paired draws × nine methods | Synthetic, with software_validation_only=true; separate from real EEG evidence |

Participant was the independent unit for real-EEG intervals. Seeds were averaged within session and sessions within participant. V2/V3 used the same already-exposed development participants; their intervals are pointwise exploratory summaries. Pooled teachers are shared across participant evaluations, so their bootstrap uncertainty is conditional on the fitted teachers. Model, seed and repeated-prediction counts describe the nested experiments.

## S 2. Exact data access and endpoint definition

The original source-training set comprised session 0/runs 0–1, validation run 2, and source query run 3. The first whole run of each later session supplied support, with subsequent whole runs reserved for query. The chronological support prefixes were capped at 4/8/12/16/20 complete trials in V2/V3; the last cap retained 19 if only 19 complete support windows were available. A prefix containing one class was preserved. Future labels were never used to balance it, choose a policy, select a model or replace a missing class.

The two conventional updates pooled the same 40 source-training trials with the same 19/20 current-support trials. The frozen comparator used source training alone. Neural fine-tuning in V3 optimized current support only, starting from the specified source checkpoint. The functional constraint additionally evaluated the participant's 40 source-training examples as fixed prediction anchors. Source validation selected source epochs; it did not select target adaptation epochs. The pooled source regime used the six participants' source training/validation sets, not their query data.

All methods compared within a saved query identity used the same ordered trial IDs and true labels. Importing EA-CSP from V2 required actual ordered trial/label agreement, because versioned query-hash conventions differed. The identity comparison used actual ordered arrays alongside their checksums.

BA required both true classes. Participant target endpoints required all five sessions and all scheduled neural seeds. Undefined groups retained an explicit missing status. Source-query metrics were reported separately. The original trial exclusions and five-second window definition were retained.

### Cue-window interpretation

Seven thousand one hundred fifty-six complete sample windows were retained from 7,200 exported events; 44 crossed recording boundaries. The event-code documentation and MOABB interval establish the released cue-anchored convention. Reconstructing phase-pure motor imagery for each window would additionally require original marker arrays, task-end/feedback boundaries and the precise derivative-conversion lineage. Each partial event denotes an incomplete recorded window; interpreting its task phase requires those original boundaries.

## S 3. Original prediction-transition and sensitivity definitions

For binary labels c∈{0, 1}, define C_c as the proportion of true-class-c trials that change from incorrect under A to correct under B, and E_c for the reverse transition. Then

$$
\Delta BA=\tfrac12(C_0+C_1)-\tfrac12(E_0+E_1).
$$

The two contributions were averaged over five sessions within each participant before cohort inference. They exactly reconstruct the saved BA difference. The 73.7% spatial-component share is the descriptive ratio of cohort-average full-minus-LDA-only to full-minus-frozen. It decomposes the observed pipeline contrasts.

Original primary-cohort mean full-minus-LDA-only was 5.47 pp, with corrected-error and introduced-error contributions 16.04 pp and 10.57 pp. Left/right recall changes were 6.16 pp and 4.78 pp, with both individual intervals including zero. The same component contrast was positive in 10/12 participant averages and all five session means; participant-deletion means ranged 4.39–6.28 pp. These are related descriptions of the same fitted models and predictions.

The pre-existing amplitude flag was 250 µV maximum raw channel peak-to-peak. It flagged 1,512/7,156 complete windows. Saved-prediction/QC matching used trial identity, role, true label and inclusion status. The unflagged target endpoint required both classes in every session; only ten original primary participants met that criterion. Their unflagged full-minus-frozen gain was 5.96 pp[0.99, 11.24] and component gain 3.82 pp[1.11, 6.72]. Their corresponding full-query gains were 6.50 pp and 4.53 pp. Source and support data were retained during this amplitude-conditional query restriction; the flag identifies a signal-amplitude property rather than a complete artifact assessment.

The original post-hoc exact sign-flip tests enumerated all $2^n$ sign assignments of the participant differences, retaining their magnitudes. The statistic was the absolute mean paired difference, with an inclusive boundary tolerance of $10^{-12}$ in BA units. The four-test family comprised full-minus-frozen, full-minus-LDA-only and LDA-only-minus-frozen in the 12-person primary cohort, and full-minus-frozen in the ten-person eligible unflagged subset. Unadjusted p values were 0.01953125, 0.01025390625, 0.26123046875 and 0.076171875; Holm-adjusted values were 0.05859375, 0.041015625, 0.26123046875 and 0.15234375, respectively. These tests use a sign-symmetric null conditional on the observed magnitudes; they are distinct from a signs-only test. The original percentile-bootstrap intervals are pointwise and unadjusted for this family.

## S 4. Geometric estimator

### Source-fixed feature space

Each trial covariance was trace-normalized and regularized using shrinkage 0.1. Let R_s be the source-training-only reference covariance and

$$
z=\operatorname{vech}_{\sqrt2}\{\log(R_s^{-1/2}CR_s^{-1/2})\}.
$$

The symmetric-vector operator multiplies off-diagonal elements by√2 to preserve the Frobenius inner product. With 22 channels, p=253. The reference remains fixed for every current-session budget and all queries. Trace normalization and identity shrinkage do not confer strict invariance to arbitrary affine sensor transformations.

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

The implementation uses a masked linear-Gaussian update and the Joseph form for P. For a single observed class, the mask retains only that class's observations, unidentifiable shift variation is set tozero, and the unobserved class retains its source mean. A class represented by one support trial uses the fixed source class covariance as its variance proxy. The numerical floor is $10^{-8}$.

### Conditional result and prediction

Under the specified Gaussian observation/prior model with known fixed noise matrices, completing the square gives the posterior above. For any estimate a, posterior expected squared error is tr(P)+‖a−θ̂‖²; the posterior mean minimizes that conditional risk. Plug-in covariance estimation, uncertainty in R_s, and uncertainty in source within-class covariance are outside that statement. The implementation propagates conditional class-mean uncertainty, not all representation uncertainty.

For class 0/1, let A_c=[I,−I] or[I, I]. The full candidate scores a Gaussian with mean A_cθ̂ and covariance Q_c=W+A_cPA_cᵀ, using equal class priors and fixed source within-class covariance W. Point prediction uses the same θ̂ and W without P. B/n assumes independent observations; serial-correlation simulations explicitly test violation of that approximation. No BA optimality or target negative-transfer theorem follows from the conditional expected squared-error result.

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

The compact HPC network uses temporal_filters 8, depth_multiplier 2, kernel_length 64, source Dropout 0.25, BN epsilon 0.001 and momentum 0.01. The individual regime reuses 18 V2 checkpoint identities; the pooled regime uses three new shared source checkpoints trained on 240 source-training/120 source-validation examples. These six participants are the same people in both conditions.

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

Fixed/adaptive BN changes normalization during gradient computation and the resulting running state; weight trajectories can consequently differ. Within each budget, initialization, support order, Dropout and optimizer exposure are held fixed. Across budgets, examples and minibatch structure change together: batch 16 gives one batch per epoch for caps≤16 and two for 19/20. With three BN modules, 20 epochs correspond to 60 or 120 total batch-counter increments. Thus the within-budget comparison identifies the BN-mode effect, while the between-budget profiles combine label quantity, class composition and update schedule.

The functional policy evaluates teacher-to-candidate mean KL on 40 source-training anchors and enforces δ=0.01 in the core experiment, with separate full runs at 0.001 and 0.1. Up to 12 halvings are attempted for a proposed optimizer step. Rejected proposals restore parameters and Adam state and are counted separately from accepted optimizer updates. These steps form the constrained optimizer’s proposal procedure. Pinsker and Jensen give mean anchor total variation ≤√(δ/2); this finite-anchor probability statement does not bound discrete class changes or unseen-target BA.

## S 6. Complete reporting, intervals and influence

Machine-readable tables retain every method, budget, participant, session and seed, together with the predefined contrast roles. Original intervals use 10,000 participant resamples with seed 42; extension intervals use the same number with seed 20261023. Complete method and budget profiles accompany the selected component interpretations.

The cap 20 BN-mode participant-deletion mean ranges were+1.07 to+1.90 pp for individual sources and+1.34 to+2.29 pp for pooled sources. These summaries assess participant influence on the same six-person result.

Collapse means a model/session predicts one class on its query set even when both true classes exist. Cap 20 fixed-BN/adaptive-BN collapse counts were 8/16 for individual sources and 0/18 for pooled sources, each out of 90 nested seed/session cells. All predictions contributed to BA; participant averages define the independent endpoint.

## S 7. Complete saved synthetic grid

The fixed factorial grid used p∈{16, 64}, source examples per class∈{10, 20,100}, support examples per class∈{1, 2, 5, 10}, shift type∈{none, common, contrast, both}, anisotropy∈{1, 20}, and stationary AR(1) correlation∈{0, 0.5}. Shift scale was.5, with 50 paired draws and 100 query examples per class. All nine methods received the same source/support/query draws within each replicate. The estimator used its fixed variance approximation across all generating correlations.

All 172,800 saved cells were retained with finite metrics and explicit synthetic/software-validation flags. Cross entropy uses the true-class probability with a numerical lower bound of $10^{-15}$ before taking the logarithm. Outcomes comprise BA, cross entropy, binary Brier score and two class-mean squared-error definitions. Full-grid averaging gives every frozen scenario equal weight. Paired Monte Carlo variation measures the finite draws under these fixed generating conditions, separately from the human-participant endpoint intervals.

The companion figure and saved scenario table display performance by shift, noise anisotropy, dimension, source size and serial correlation. Full-grid summaries accompany the factor-specific profiles. Probability-based EEG diagnostics use the saved probabilities; their numerical logarithmic-scoring floor is identified in the analysis record.

## S 8. Calibration reliability and retained original limitations

Original source/support probes evaluated low-dimensional power and source-fitted representations, followed by supervised CSP4/LDA controls. The support-half analysis split each class chronologically and retained frozen source transforms. Among 30 sessions, 19 had positive signed source-score orientation in both halves, two were negative in both, and nine changed sign. These observations distinguish calibration-subset agreement from the intended class orientation, providing measurements for future support-driven policy tests.

The endpoint is offline task-label decoding in one public longitudinal cohort. Cue/feedback contributions, zero-phase filtering and amplitude artifacts in fitting/query data affect its interpretation. Pooled-source and source-validation labels are explicit information-budget differences; independent participant validation remains the next step for the component hypotheses.

## S 9. Saved-result provenance and computational scope

The V3 raw received archive is `paper2-results-83cbdfdcfa541b3ab3addfc3.tar.gz`, 40,194,093 bytes, SHA256 `e509c2591efa21fff4dd47236e613ed6b611ca10ad20bac3da37e66e34a9d170`. It comprises three verified GitHub parts at fixed commit `500831c086d9e1d1e8412cf8ebca5fb6a288db76`. Its 49,984 payload files plus manifest matched their lengths and checksums; 126 unique valid task-completion identities matched the frozen queue. The public packet contains no original EEG, optimizer tensors or model weights.

The original three slot jobs were 775309, 775310 and 775311. Each completed 42 tasks with recorded exit 0, no restart; actual slot walltimes show sequential execution. The three-slot capacity setting produced sequential execution in the recorded allocation. Runtime and storage records document provenance; saved-prediction reconstruction supplies the numerical verification.

This revision reused saved predictions, metrics and histories with the original fitted models, seeds and support windows. Original submission packages and all experiment outcomes remain at their versioned paths. Reproduction scripts, table definitions, figure inputs and targeted verification are identified in the accompanying revision report.

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

All paired participant differences, pointwise intervals, negative-participant counts and reference-role labels are retained in the companion comparison table. The full primary geometric and neural outcomes appear in the main text; this table supplies the complete budget context.

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

The full candidate minus tangent refitting was−5.8255 BA points. Of 384 scenario means, eight favored the candidate and 376 favored refitting. Candidate feature-mean squared error was larger than refitting in every scenario mean. Posterior-predictive versus point candidate prediction changed mean cross entropy by−0.34094, Brier by−0.00191 and BA by−0.0398 percentage points. The contrasts separate probability scoring from classification and mean estimation.
