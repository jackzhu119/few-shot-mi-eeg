# Spatial-filter refitting improves limited-label EEG decoding beyond classifier recalibration

**Running head:** Spatial refitting with limited calibration labels

**Ziyuan Zhu**\*

College of Artificial Intelligence Medicine, Chongqing Medical University, Jinyun Campus, No. 61 Daxuecheng Middle Road, Shapingba District, Chongqing 401331, China

**\*Corresponding author:** Ziyuan Zhu; zzy2630816871@gmail.com

**ORCID:** https://orcid.org/0009-0005-1153-4926

## Abstract

**Objectives:** To quantify the added value of spatial-filter refitting beyond classifier recalibration with approximately 20 current-session labels.

**Methods:** We compared frozen common spatial patterns and linear discriminant analysis (CSP/LDA), classifier-only recalibration and full refitting in 18 participants across six Kumar2024 sessions. The predefined primary cohort contained 12 participants. The two updating methods received identical source and current-session labels. Later component experiments used the six development participants.

**Results:** Full refitting achieved 65.36% balanced accuracy, 7.42 percentage points above freezing (95% participant-bootstrap interval 2.49–12.48). The secondary, matched-label full-minus-classifier-only gain was 5.47 points (2.17–8.91), accounting for 73.7% of the mean total gain. It was positive in ten of 12 participant averages and all five target-session averages. At the 20-label cap, fixed-normalization neural adaptation was 1.50–1.91 points higher than adaptive normalization and produced fewer single-class predictions. Smaller-budget profiles differed. Strong-reference comparisons favored simpler geometric decoders; source-functional constraints changed accuracy little.

**Conclusions:** Matched-label component analysis identified spatial-filter refitting as the main contributor to the observed recalibration gain. It separates the value of updating the representation from the value of recalibrating its classifier.

**Keywords:** batch normalization; brain–computer interfaces; covariance alignment; motor imagery; transfer learning

## Introduction

A decoder trained in the first Kumar2024 session must serve five later sessions. At the start of each later session, a short calibration run supplies only 19 or 20 complete labeled trials. Should these labels recalibrate the classifier, relearn its spatial filters, or update both? This practical choice links longitudinal motor-imagery brain–computer interfaces (BCIs) to the limited-sample estimation problem: each updated component must be learned from the available new observations [@lotte2018].

Common spatial patterns (CSP) and linear discriminant analysis (LDA) make the component question directly testable [@ramoser2000; @blankertz2008]. CSP extracts class-discriminative spatial power features; LDA maps them to decisions. Re-estimating LDA changes classification in the source feature space. Refitting both stages also changes that space. Giving the two updates identical labels isolates the added spatial update within the evaluated pipeline. The distinction matters for the broader instruction to adapt a representation: supervised spatial-filter refitting and repeated neural normalization are different operations with different estimation demands.

Previous research has established classifier adaptation, adaptive CSP, data-space transformations and distribution alignment [@vidaurre2011lda; @arvaneh2013dsa; @song2015acsp; @he2020alignment; @zanini2018alignment]. The Kumar acquisition study combined covariance recentering with a Riemannian classifier, added supervised prototype updates, and examined a recentering-based CSP extension [@kumar2024; @kumar2024correction]. These precedents motivate a quantitative question: how much does relearning spatial filters add when classifier recalibration already receives the same new labels?

Kozyrskiy et al. benchmarked label-revealed online updates across four EEG datasets [@kozyrskiy2026updates]. Their prequential procedure predicts a trial, reveals its label, then refits CSP or Riemannian pipelines using expanding, rolling or cold-start histories. Here, each later session is recalibrated from the source-training set and a fixed current-session support run, and full CSP/LDA refitting is compared directly with LDA-only recalibration using identical trial identities. The online benchmark evaluates how revealed label histories support continuing updates; our fixed-budget comparison measures the additional spatial component.

Neural adaptation introduces further choices. Weight updates can accompany changes in normalization statistics, affine parameters and Dropout. Adaptive batch normalization (BN) is established [@adabn2016], and longitudinal EEG studies have combined fine-tuning with alignment and normalization updates [@wimpff2025continual]. Weight and functional constraints offer other ways to preserve source information [@l2sp2018; @lwf2016; @trpo2015]. Explicitly separating these actions helps explain the resulting predictions.

We use **matched-label component analysis** to connect three contributions:

1. **A controlled spatial-component comparison.** LDA-only recalibration and full CSP/LDA refitting use the same 40 source-training labels, 19 or 20 current-session labels and query trials. Their difference measures the additional spatial update after classifier recalibration. A separate frozen arm measures the total benefit of receiving support labels and refitting.
2. **Prediction-level and longitudinal attribution.** Corrected and newly introduced errors reconstruct the component gain, while class recalls, target-session profiles and participant-deletion summaries locate that gain across the longitudinal data. The original full-minus-frozen comparison remains primary and full-minus-LDA-only secondary.
3. **Matched mechanism controls.** Conventional alignment, geometric uncertainty and neural update modes test which additional operations affect decoding under explicit information budgets. Complete strong-reference and ablation results connect the spatial gain to practical update choices.

## Materials and methods

### Data source and ethics

We analyzed the public Kumar2024 EEG derivative, NEMAR nm000177/v1.0.5 [@nemar177], associated with the original study and its correction [@kumar2024; @kumar2024correction]. The original study reported University of Texas at Austin ethical approval under protocol 2020-03-0073 and written informed consent before data collection.

This secondary analysis was exempt from additional ethical review under Article 32, item (1), of China's *Measures for Ethical Review of Life Science and Medical Research Involving Human Participants* (2023) [@china2023ethics]. It used lawfully obtained publicly available data, caused no harm to participants, and did not involve sensitive personal information or commercial interests.

Dataset metadata were accessed on 10 October 2026, and the selected EEG recordings and accompanying metadata were retrieved on 11 October 2026. This secondary analysis used the released coded participant identifiers; no participants were contacted and no re-identification was attempted. The author had no access to information that could identify individual participants during or after data collection. Original collection approval and consent and the regulatory basis for this secondary analysis are documented separately in the retained provenance materials.

### Windows, preprocessing and chronological information access

The derivative contains 18 participant identifiers, six sessions and 360 EDF recordings. Of 7,200 exported left/right events, 7,156 provided complete five-second windows; 44 reached a recording boundary and were excluded without padding. All 44 occurred at the last event of an online recording.

The original codebook assigns 769/770 to left/right cues and 7691/7701 to task starts [@kumarcodebook]; the documented MOABB adapter maps cues to a [0, 5]-second interval [@jayaram2018]. The original procedure included a 1.5-second cue preceding feedback and variable online feedback duration. Our endpoint is therefore task-label decoding over released cue-anchored windows. Original trial-level task-end and feedback markers were unavailable for phase reconstruction.

Preprocessing used common-average referencing across 22 channels, fourth-order 8–30 Hz zero-phase Butterworth filtering, and resampling from 512 to 128 Hz, producing 22×640 float32 values in volts. Learned transforms used training partitions.

Participants sub-1, 4, 7, 10, 13 and 16 formed the development group; the remaining 12 formed the original primary cohort. Session 0/runs 0–1 supplied 40 source-training windows, run 2 supplied 20 source-validation windows, and run 3 supplied source query. In later sessions, run 0 supplied support and subsequent whole runs query; updates used current-session labels without accumulating previous targets. The original query set contained 4,290 complete events, including 360 source and 3,930 target events; 30 partial-query exclusions remained fixed.

The existing 250 µV raw peak-to-peak flag marked 1,512/7,156 complete windows. The main analysis retained them. Sensitivity analysis required both classes in every target session.

### Original component comparison

The conventional decoder used four-component CSP, Ledoit–Wolf regularization and automatic-shrinkage LDA [@ledoit2004]. Frozen decoding used 40 source-training trials. LDA-only retained source CSP and refitted LDA on source training plus current support; full refitting re-estimated both components on that same union. Their difference measures the added spatial update and classifier fit in the revised feature space.

The original EEGNet reference used three fixed seeds per participant, source normalization, 40 training labels and 20 source-validation labels for epoch selection [@lawhern2018; @schirrmeister2017]. All 54 models and seed outcomes were retained. The HPC extension used the separately specified compact architecture below.

Prediction-transition analysis counted errors corrected by method B relative to A and the reverse changes, balancing the two classes. The difference between these contributions equals BA(B)−BA(A) exactly. This post-hoc analysis, class recalls, session profiles and participant-deletion means explain the original component endpoint.

### Extension design and comparison roles

V2 and V3 used the same six previously exposed development participants, chronological whole-run partitions, scheduled seeds and query identities. Current support was capped at 4, 8, 12, 16 or 20 complete trials, retaining the observed class order. Within each frozen execution, query was excluded from fitting and selection; the design of later rounds was informed by earlier results.

V2 tested source–target covariance mixing against EA-CSP. V3 fixed two cap-20 primary candidate contrasts before execution: uncertainty-aware prediction minus ordinary tangent refitting, and source-functional-constrained minus ordinary full neural adaptation within each source regime. BN, Dropout and dose comparisons were exploratory mechanisms. The full matrix included 10,350 target and 42 source prediction files, all nested within the same six participants; details are in the supplement.

### Neural update-mode experiment

The compact HPC EEGNet used eight temporal filters, depth multiplier two, temporal kernel 64 and source Dropout 0.25. Individual sources reused 18 V2 checkpoints, each with 40 training and 20 validation labels. Three pooled sources, one per seed, used 240 training and 120 validation examples from the same six participants, changing source-data amount and cross-participant composition.

Source training used 100 epochs with validation cross entropy selecting the model. Optimizer adaptations used current support, 20 epochs, batch 16, AdamW, learning rate $10^{-4}$, weight decay $10^{-4}$, a cosine schedule and no automatic mixed precision. A separate sampler matched support order. Query inference used evaluation mode.

Eight policies covered freezing, head-only, full fixed-BN, full adaptive-BN, adaptive-BN plus Dropout, BN-affine-only, BN-statistics-only and functional-constrained full updates. Dropout was off except in its explicit arm. Fixed BN used source running statistics during adaptation and inference; adaptive BN used batch statistics during adaptation and updated the inference state. This contrast changes normalization during optimization and the resulting buffers, with potentially different weight trajectories.

The functional policy bounded mean teacher-to-candidate KL on 40 source-training anchors at 0.01, with additional doses 0.001 and 0.1. Bounded backtracking restored parameters and optimizer state after a rejected proposal [@lwf2016; @trpo2015].

### Geometric estimator and matched controls

Trace-normalized trial covariances used fixed 0.1 shrinkage and a source-training-only log-SPD reference, giving 253 features for 22 channels. Class means were represented by common location m=(μ₀+μ₁)/2 and half contrast h=(μ₁−μ₀)/2. The candidate estimated separate noise-corrected shift scales, matrix mean-noise covariances and a linear-Gaussian posterior. Prediction added class-mean posterior covariance to fixed source within-class covariance.

Controls covered frozen source prediction, ordinary pooled means, tangent refitting, candidate point prediction, isotropic noise, coupled shift scales, and removal of source noise or shift variance. Missing support classes followed the fixed masked-observation rule. Equations and assumptions are in the supplement.

Saved synthetic experiments tested all nine methods across 384 known-mechanism conditions and 50 paired repetitions, varying dimension, sample sizes, shift, anisotropy and serial correlation. These results were analyzed separately from EEG.

### Participant-level analysis and saved-result verification

BA averaged the two true-class recalls. Seeds were averaged within session, five target sessions within participant, then participants within cohort. Paired contrasts used matched endpoints and 10,000 participant-bootstrap resamples: seed 42 for the original comparison and 20261023 for the extensions. Extension intervals use the six participants as resampling units and are pointwise summaries. A post-hoc check enumerated every sign assignment of the observed participant differences, preserving their magnitudes, using the absolute mean as the statistic. Holm adjustment covered four saved contrasts: full-minus-frozen, full-minus-LDA-only and LDA-only-minus-frozen in the primary cohort, plus full-minus-frozen in the eligible unflagged subset. These family-adjusted tests accompany the original pointwise bootstrap intervals.

All scheduled seeds, sessions, caps and doses were retained; any missing required cell left the endpoint incomplete. Pooled-source intervals are conditional on the fitted shared teachers. Synthetic summaries equally weighted the fixed scenarios and paired draws. Exploratory EEG cross entropy clipped probabilities at $10^{-15}$; simulation scoring used the same numerical floor.

Saved trial identities, labels and metrics were checked before aggregation. The revision reused predictions and histories; no model fitting or new inference was required. The supplement identifies the full result packet, code and provenance checks.

## Results

### Spatial refitting supplied the main matched-label gain

Full CSP/LDA refitting achieved 65.36% target BA in the original 12-participant primary cohort, compared with 57.94% for frozen decoding and 59.89% for LDA-only recalibration. The predefined primary full-minus-frozen gain was 7.42 percentage points (95% interval 2.49–12.48). With identical fitting labels, the secondary full-minus-LDA-only gain was 5.47 points (2.17–8.91), while LDA-only minus frozen was 1.95 points (−0.98–5.09). The spatial-component contrast accounted for 73.7% of the mean total gain (Table 1; Figure 1). The exact sign-flip p value was 0.01025 for the matched-label component contrast (Holm-adjusted p=0.04102) and 0.01953 for the primary full-minus-frozen contrast (Holm-adjusted p=0.05859). The bootstrap intervals estimate paired effects without a family adjustment; the sign-flip tests use a sign-symmetric reference and four-comparison error control.

\Needspace{16\baselineskip}

**Table 1. Original target-query component comparison.**

| Cohort | Participants | Frozen CSP/LDA BA | LDA-only BA | Full CSP/LDA BA | Full − frozen | Full − LDA-only |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development | 6 | 59.97% | 64.37% | 63.22% | +3.25 pp | −1.15 pp |
| Predefined primary cohort | 12 | 57.94% | 59.89% | 65.36% | +7.42 [2.49, 12.48] pp | +5.47 [2.17, 8.91] pp |
| All participants, secondary | 18 | 58.62% | 61.38% | 64.65% | +6.03 pp | +3.26 pp |

BA, balanced accuracy; pp, percentage points. The two updating methods used the same source-training/current-support union. Values average five sessions within participants. Full refitting versus freezing in the 12-participant cohort was the predefined primary comparison; full versus LDA-only was secondary. The six-person development row remains separate from the primary cohort and includes its negative component mean.

The component gain reflected 16.04 BA points of corrected errors against 10.57 points of newly introduced errors on the same query trials. Mean left- and right-class recall increased by 6.16 and 4.78 points, respectively. These recall intervals individually included zero; their class-balanced mean gives the observed component endpoint. The added spatial update was positive in ten of 12 participant averages and every target-session cohort average: +3.52, +5.20, +4.13, +4.18 and +10.33 points. Every single-participant deletion mean remained positive, between +4.39 and +6.28 points.

Full refitting gave higher BA than frozen decoding for nine of 12 primary participants. The three decreases were −5.82, −0.67 and −0.20 points. In the ten participants retaining both query classes across all five unflagged sessions, full-minus-frozen was +5.96 points (0.99–11.24) and full-minus-LDA-only +3.82 (1.11–6.72). This query restriction left original training and support data unchanged. The retained cohort and amplitude-conditional endpoint differ from the complete primary analysis.

![Figure 1](figures/Fig1_update_components.png){width=100%}

**Figure 1. Spatial-component evidence and strong-reference context.** Original primary-cohort component and total contrasts are displayed separately from the six-participant V2 budget profiles. Participant values, cohort means and participant-bootstrap intervals retain their original denominators and endpoint hierarchy. The original full-minus-LDA-only result compares matched labels; the V2 profiles compare separately versioned methods within the discovery cohort.

### EA-CSP provided a strong conventional reference

In the six-participant V2 extension at the 20-label cap, frozen classical decoding achieved 62.15% BA, LDA-only 67.30%, full CSP/LDA 68.65% and EA-CSP 70.37%. The covariance-mixture candidate achieved 69.24%. Its gain over frozen decoding was +7.09 points (4.12–11.55), but its prespecified comparison with EA-CSP was −1.14 points (−3.52–1.14). EA-CSP therefore provided the stronger conventional reference for the next experiment.

These results motivated the source-fixed feature and component controls in V3.

### Tangent refitting and EA-CSP gave higher geometric-decoder accuracy

At the cap of 20 labels, the geometric candidate achieved 64.68% BA, versus 67.01% for ordinary tangent refitting and 70.37% for saved EA-CSP. Its prespecified primary contrast was −2.33 points (−4.41 to −0.24), and its strong-reference contrast was −5.69 points (−9.30 to −2.22; Table 2). Five of six participant differences were negative in both comparisons. All five support-cap mean contrasts versus tangent refitting were negative (Figure 2).

\Needspace{16\baselineskip}

**Table 2. V3 geometric comparison at the 20-label cap.**

| Method | Mean BA | Candidate − method, pp |
| --- | ---: | ---: |
| Frozen source tangent model | 60.36% | +4.32 [0.07, 8.61] |
| Pooled means with fixed source within-class covariance | 64.08% | +0.60 [−3.09, 3.01] |
| Ordinary tangent refitting | 67.01% | −2.33 [−4.41, −0.24] |
| Candidate means with point prediction | 66.52% | −1.84 [−3.26, −0.46] |
| Full uncertainty-aware candidate | 64.68% | Reference |
| Saved EA-CSP, strong reference | 70.37% | −5.69 [−9.30, −2.22] |

BA, balanced accuracy; pp, percentage points. Ordinary tangent refitting was the frozen primary comparator. The same-query EA-CSP reference was imported from saved V2 predictions after ordered trial/label verification. Candidate ablations and every budget are retained in the supplementary methods and machine-readable tables.

The matched ablations distinguish three operations. Separating common and discriminative variation and retaining source-mean noise improved the cap-20 candidate over their respective ablations. Adding posterior covariance to the same posterior means reduced BA by 1.84 points relative to point prediction. The estimated common-location variation was larger than discriminative-contrast variation in every cap-20 support set. These observations distinguish changes in the estimated means from changes in predictive covariance.

![Figure 2](figures/Fig2_geometry.png){width=100%}

**Figure 2. Geometric candidate, matched controls and ablations.** Full support-budget profiles and cap-20 paired contrasts retain ordinary tangent refitting and EA-CSP as strong references. Ablations separate posterior mean estimation, prediction covariance, source-mean noise and common/contrast variation scales. All candidate-versus-ablation and strong-reference contrasts are displayed together; intervals use participant-bootstrap resampling.

### Fixed source normalization reduced single-class predictions at the 20-label cap

At the 20-label cap, fixed-BN full updates produced eight single-class query predictions among 90 nested participant-by-seed-by-session outcomes, compared with 16 under adaptive BN. Pooled-source counts were zero and 18, respectively. Fixed-BN BA was 57.51%, versus 56.01% for adaptive BN with individual sources, a difference of 1.50 points (0.33–2.74). Pooled-source values were 56.22% and 54.31%, a difference of 1.91 points (0.76–3.24; Table 3). Five of six participant differences favored fixed BN in each regime; the remaining difference was negative for individual sources and approximately zero for pooled sources. All participant-deletion mean contrasts stayed positive at this cap.

\Needspace{16\baselineskip}

**Table 3. V3 neural component contrasts at the 20-label cap.**

| Contrast | Individual source models | Pooled source models | Role |
| --- | ---: | ---: | --- |
| Fixed-BN full update − adaptive-BN full update | +1.50 [0.33, 2.74] pp | +1.91 [0.76, 3.24] pp | BN-mode comparison |
| Fixed-BN full update − frozen | +0.77 [−0.16, 1.73] pp | +0.96 [−0.41, 2.77] pp | Update baseline |
| BN-statistics-only − frozen | −1.15 [−2.15, −0.12] pp | −0.30 [−0.68, 0.05] pp | Statistics-only comparison |
| Functional constraint − fixed-BN full update | −0.01 [−0.11, 0.09] pp | +0.03 [0.00, 0.09] pp | Prespecified neural primary contrast |
| Adaptive BN plus Dropout − adaptive BN | −0.15 [−0.40, 0.08] pp | +0.28 [0.04, 0.55] pp | Dropout comparison |

BN, batch normalization; KL, Kullback–Leibler divergence; pp, percentage points. Intervals summarize six participants after averaging fixed seeds and target sessions. Single-class prediction counts include 90 nested outcomes per arm. The functional-constraint row retains its predefined primary role. BN mode changes optimization-time normalization and the resulting inference state.

The full budget curves show how this contrast changes (Figure 3). Individual-source fixed-minus-adaptive BN differences were −0.18, −0.34, −0.46, −0.04 and +1.50 points across caps 4–20. Pooled-source differences were +0.75, +0.01, +0.48, +1.31 and +1.91 points. At the final support cap, batch size 16 also changed the number and size of minibatches: up to 16 support trials supplied one batch per epoch, whereas 19/20 supplied two. Three BN modules recorded 60 versus 120 cumulative batch-counter increments over 20 epochs. Within a support cap, the BN comparison holds minibatches and optimization exposure fixed. Across caps, label quantity, class composition and the normalization-update schedule change together.

![Figure 3](figures/Fig3_neural_normalization.png){width=100%}

**Figure 3. Neural normalization mode across support budgets.** Fixed-minus-adaptive BN contrasts are shown for both source regimes across all five caps, together with the cap-20 participant contrasts and single-class prediction counts. Fixed and adaptive BN use the same current support, initialization, optimizer budget and Dropout-off setting within each comparison. They differ in normalization during optimization and the resulting inference state. Collapse counts are nested seed/session observations; participant-level summaries define the uncertainty intervals.

### Source discrimination and functional-constraint effects

Frozen individual-source models achieved 56.74% target BA, compared with 55.26% for pooled-source models, a pooled-minus-individual difference of −1.48 points (−2.90 to −0.20). Source-query BA was 56.11% and 57.78%, respectively. Weak source discrimination was already present before target-session transfer. The pooled-source target mean was lower in this architecture and training regime.

The three pooled models selected epochs 14, 20 and 17 by validation loss. Their final training losses were approximately 0.20–0.22, while final validation losses were 0.91–0.96, above the selected validation losses near 0.68. These histories show training-loss reduction alongside weak held-out generalization within the source domain.

At the core KL bound 0.01, the functional constraint changed the cap-20 mean relative to ordinary fixed-BN adaptation by −0.01 points for individual sources and +0.03 points for pooled sources. At bound 0.1, BA matched the ordinary update in both regimes; bound 0.001 produced differences of −0.22 and −0.19 points, respectively, with intervals crossing zero. The complete dose profiles and accepted/rejected-step histories are retained.

### Posterior covariance reduced simulated log loss with little change in accuracy

The full synthetic grid contained 172,800 numeric method-by-condition-by-repetition results. Equal-grid BA was 70.36% for the candidate and 76.19% for tangent refitting, a difference of −5.83 points; 376 of 384 scenario means favored refitting. Candidate feature-mean squared error was also larger. Adding posterior covariance to identical candidate means reduced mean cross entropy by 0.341 but changed BA by −0.04 points. Thus, the probability-score improvement and classification endpoint moved differently (Figure 4).

![Figure 4](figures/Fig4_mechanisms.png){width=100%}

**Figure 4. Mechanism simulations and predictive uncertainty.** All 384 conditions retain 50 paired repeats. Panels show candidate-minus-refit BA by source size/correlation, all generating shifts, paired scenario BA, and posterior-versus-point changes in cross entropy and BA. Synthetic results are separate from human EEG endpoints.

## Discussion

### Matched-label analysis identifies the spatial contribution

The matched-label comparison identifies a substantial spatial-component gain. Full CSP/LDA refitting added 5.47 BA points beyond classifier-only recalibration in the original primary cohort and supplied 73.7% of the mean total improvement over freezing. Holding the fitting examples constant gives this result a clearer interpretation than an updated-versus-frozen comparison alone: the available labels supported a useful change in the spatial representation as well as in the class decision rule.

The neural extension adds a complementary observation. At the final support cap, fixed-source BN during full weight adaptation outperformed adaptive BN in both initialization regimes, with fewer collapsed seed/session predictions. This contrasts with the successful CSP spatial update. The component analysis distinguishes a supervised spatial estimator from repeated normalization updates, making the observed gain attributable to a specific pipeline operation.

The principal conventional result also has a direct trial-level explanation. The added spatial update corrected more class-balanced errors than it introduced, and its mean benefit involved both labels. Positive session means and participant-deletion summaries show that its cohort average was not supplied by a single participant or only one point in the session sequence. The participant and development-cohort results document variation around this positive primary-cohort mean.

### Normalization effects varied across support budgets

The BN comparison holds source initialization, support, trainable parameters, Dropout and optimizer schedule fixed within each budget. The cap-20 difference therefore identifies the BN-mode choice within the evaluated 20-epoch, batch-16 adaptation schedule.

Adaptive BN changes batch normalization during optimization and accumulates the running state used for evaluation; both can affect the resulting model. The small final minibatch, number of BN updates and class composition differ across the chronological prefixes. The full curves show a different sign for the individual-source comparison at smaller caps.

These details distinguish our information regime from reports using abundant target-domain statistics or continuous online adaptation [@adabn2016; @wimpff2025continual]. They also give a focused next hypothesis: when adaptation repeatedly revisits a short support run, normalization mode and exposure count should be controlled independently of label count. A follow-up can vary the BN update schedule while preserving the trained sources, support identities and comparison hierarchy.

### Strong references guide estimator comparisons

EA-CSP had higher mean BA than the V2 covariance-mixture candidate and the V3 uncertainty-aware candidate. Ordinary tangent refitting also had higher BA in the candidate’s own feature family. EA-CSP and tangent refitting therefore provide practical references for evaluating additional adaptation machinery on these data.

The candidate separated shared class movement from discriminative change and propagated estimated mean uncertainty. Ablations showed contributions from its shift scales and noise estimates, while point prediction identified a cost of adding posterior covariance. Its conditional expected squared-error result concerns class-mean estimation under the Gaussian assumptions; classification remains an empirical endpoint.

The enforced source-anchor KL constraint changed cap-20 BA by −0.01 and +0.03 points in the two source regimes. Alignment, source regularization and functional preservation are established [@he2020alignment; @l2sp2018; @lwf2016; @trpo2015]. The present evidence identifies their value through explicit information budgets and matched component comparisons.

### Source discrimination and calibration measurements

Original primary-cohort EEGNet BA was 52.92% on source query and 51.58% on target sessions. The extension's sources likewise showed weak held-out discrimination despite falling training losses. Source generalization therefore contributes to interpreting target performance alongside session transfer.

The original source/support probes also distinguished calibration agreement from correct task orientation. Of 30 development support sessions, 19 had positive source-score contrasts in both chronological halves, two were negative in both, and nine changed sign. Agreement can coexist with reversed orientation. These findings motivate testing support-driven selection among fixed component choices in an independent evaluation.

### Scope and next validation

The study uses one public longitudinal cohort. The original primary hierarchy is retained; V2/V3, prediction transitions and sensitivity analyses used previously exposed data. The extension estimates are exploratory, conditional on the recorded source models and support schedules. Pooled teachers share participants and change source-label budgets; the independent sample remains the participant cohort.

Cue-anchored windows may contain cue, imagery, feedback or post-task activity. Phase-specific decoding requires original marker-level reconstruction. Amplitude-restricted queries retained positive spatial gains in eligible participants, while training/support artifacts and other query artifacts remain possible. Zero-phase filtering makes the present endpoint offline.

An independent longitudinal study can freeze the matched-label spatial comparison and separately control BN exposure count and minibatch size. These are specific hypotheses generated by the component results.

## Conclusions

Matched-label component analysis showed that relearning spatial filters added 5.47 balanced-accuracy points beyond classifier recalibration with the same source and approximately 20 current-session labels. This increment accounted for 73.7% of the 7.42-point total mean gain over freezing. Practitioners evaluating short-run recalibration should therefore compare classifier-only and full spatial updates under identical labels, with EA-CSP as a strong conventional reference. In the neural extension, fixed BN produced fewer single-class predictions under the 20-label, batch-16 schedule; the full budget profiles motivate independent control of normalization exposure. Posterior covariance improved simulated log loss while classification favored simpler geometric references. Independent longitudinal validation should retain the fixed label budget and component contrasts before selecting an update policy.

## Data and code availability

Source EEG is available as NEMAR nm000177/v1.0.5, DOI 10.82901/nemar.nm000177.v1.0.5, under CC BY 4.0 [@nemar177]. Code, configurations, original results and saved extension predictions are available at https://github.com/jackzhu119/few-shot-mi-eeg, research branch `research/paper2-hpc-v2-20261023`. The supplement identifies the fixed V3 packet and reproduction inputs. Original software uses MIT; manuscript, figures and derived results use CC BY 4.0 within the scope defined in LICENSING.md. Source-data and third-party terms are retained.

## Acknowledgments

The author thanks the researchers who released Kumar2024. OpenAI ChatGPT/Codex assisted with grammar and language revision, GitHub file organization and uploading, manuscript formatting, and verification of saved results. This work included assistance with analysis and plotting code, statistical reconstruction, and manuscript drafting and revision. The author is responsible for the content and interpretation.

## References

::: {#refs}
:::

## Supporting information captions

**Supplementary methods and data.** Complete component definitions, mathematical assumptions, all methods/budgets/seeds, participant and scenario tables, original sensitivity analyses, prediction identities, provenance and saved-output reproduction instructions.
