# Limited-label cross-session motor-imagery EEG recalibration: spatial refitting and the added value of Euclidean alignment

**Running head:** The added value of EEG alignment

**Ziyuan Zhu**\*, **Sihao Liu**, **Haoyang Yu**

College of Artificial Intelligence Medicine, Chongqing Medical University, Jinyun Campus, No. 61 Daxuecheng Middle Road, Shapingba District, Chongqing 401331, China

**\*Corresponding author:** Ziyuan Zhu; zzy2630816871@gmail.com

**Co-author emails:** Sihao Liu, liu3100853087@gmail.com; Haoyang Yu, jiaguca3329@163.com

**ORCID (Ziyuan Zhu):** https://orcid.org/0009-0005-1153-4926

## Abstract

**Objectives:** To measure what Euclidean alignment (EA) adds after spatial filters and a classifier receive the same short motor-imagery calibration run.

**Methods:** Three updating pipelines based on common spatial patterns and linear discriminant analysis received identical source/calibration information; a source-frozen reference shared their queries. Kumar2024 contained 18 participants over six sessions and BNCI2014-001 nine over two days. Participant summaries and fixed CPU sensitivities assessed errors, weak-class recall and signal definitions.

**Results:** Alignment added 5.30 balanced-accuracy points in the original twelve-person Kumar cohort (exploratory 95% interval 2.81–8.26) and 5.65 in BNCI (3.15–8.70; secondary Holm p=0.01172). Weak-class recall increased 10.45 and 8.52 points, with joint accuracy/weak-class benefit in 10/12 and 9/9 participants. In nine Kumar participants with common phase eligibility, EA-minus-full was 7.85 points for cue-anchored 5 s windows and 0.13 for task-start 2 s windows; the paired change was −7.73 (−12.17 to −3.76).

**Conclusions:** Alignment improved the cue-anchored decoder after supervised refitting, with added weak-class coverage. The Kumar increment depended on the evaluated signal window.

**Keywords:** brain–computer interfaces; calibration; covariance; domain adaptation; signal processing

**Abbreviations:** BA, balanced accuracy; BCI, brain–computer interface; CSP, common spatial patterns; EA, Euclidean alignment; EEG, electroencephalography; LDA, linear discriminant analysis.

## Introduction

A short calibration run can update a motor-imagery decoder in several ways: adjust its decision rule, relearn its spatial filters, or align the recordings before fitting both. The last operation matters only if it adds useful information processing after supervised refitting has already received the same examples. This study measures that added value and traces it to the later decisions and classes that change.

Repeated calibration is a central problem for EEG-based brain–computer interfaces (BCIs) [@lotte2018]. Changes between recording sessions alter the signals presented to a trained decoder. Common spatial patterns (CSP) and linear discriminant analysis (LDA) make the update operations explicit: CSP extracts class-discriminative spatial power features, and LDA estimates a decision rule in that feature space [@ramoser2000; @blankertz2008]. Refitting LDA preserves the source representation. Refitting CSP and LDA also uses the available labels to learn a new projection.

Classifier adaptation and spatial-filter adaptation are established approaches [@vidaurre2011lda; @song2015acsp; @arvaneh2013dsa]. Data alignment acts earlier, by changing the coordinates of the recordings [@zanini2018alignment]. He and Wu's Euclidean alignment (EA) estimates an arithmetic-mean covariance reference and applies its inverse square root to each domain [@he2020alignment]. Their work already evaluates EA-CSP/LDA with few target examples and simulated online reference estimation from the target signals then available. The present question concerns the magnitude and distribution of EA's additional contribution in repeated-session recalibration, after classifier-only and full spatial refitting have been separately accounted for.

The Kumar2024 acquisition study investigated adaptation, including covariance recentering, supervised prototype updates and a CSP extension [@kumar2024; @kumar2024correction]. More recent label-revealed benchmarks compare how update histories retain incoming labels [@kozyrskiy2026updates]. We hold a different information regime fixed: every later session restarts from the same source training set and a chronological prefix of that session's first run. This separates the use of current calibration information from accumulation of earlier target labels.

We compare frozen CSP/LDA, LDA-only recalibration, full CSP/LDA refitting and EA followed by full refitting. The three updating pipelines receive the same source and current-support labels and predict the same later trials. The study contributes an incremental EA comparison, a reconstruction of corrected and introduced errors together with weak-class recall, and a longitudinal account of participant, session and calibration-budget effects. Matched-coordinate and signal-definition sensitivities examine the specific implementation choices underlying these contrasts.

## Materials and methods

### Datasets, chronological partitions and ethics

Kumar2024, NEMAR nm000177/v1.0.5, contains 18 participants recorded over six sessions [@nemar177; @kumar2024]. BNCI2014-001, also known as BCI Competition IV 2a, contains nine participants recorded on two days [@tangermann2012competition]. Both analyses concern left- versus right-hand imagery; cohorts are analyzed separately.

The original Kumar study reported University of Texas at Austin ethical approval, protocol 2020-03-0073, and written informed consent [@kumar2024]. This secondary analysis was exempt from additional ethical review under Article 32, item (1), of China's *Measures for Ethical Review of Life Science and Medical Research Involving Human Participants* (2023) [@china2023ethics]. It used lawfully obtained public data, caused no harm to participants, and did not involve sensitive personal information or commercial interests. Coded records were analyzed without participant recruitment, contact or re-identification. Original acquisition ethics and consent information are reported separately in the declarations and supplementary methods.

Kumar preprocessing used common-average referencing across 22 channels, fourth-order 8–30 Hz zero-phase Butterworth filtering, and resampling from 512 to 128 Hz. Cue codes 769/770 anchored five-second windows, each containing 22×640 samples in volts. Of 7,200 exported events, 7,156 had complete windows; 44 reached the recording boundary and were excluded without padding. Original task-start codes 7691/7701 were separately documented [@kumarcodebook]. Complete cue-window extraction follows the released data convention [@jayaram2018].

The original development participants were sub-1, 4, 7, 10, 13 and 16; the remaining twelve formed the original primary cohort. Session 0/runs 0–1 supplied 40 source-training trials, run 2 supplied 20 source-validation trials, and run 3 supplied source query. Each of five later sessions used run 0 as support and later whole runs as query. The original target-query set contained 3,930 events across all 18 participants, with its 30 partial-query exclusions fixed. Conventional decoder fitting used source training and current support; source validation remained outside these fits.

BNCI preprocessing retained the first 22 EEG channels and the recorded reference. Four-second epochs began at the class cue, two seconds after each one-based MAT trial-start sample, following fourth-order 8–30 Hz zero-phase filtering within continuous runs. Source-day runs 1–4 supplied 96 hand trials. On the second day, the first 20 chronological hand trials of run 1 supplied support; its remaining four hand trials were withheld. Whole runs 2–6 supplied 120 query trials, 60 per class. Source-day runs 5–6 were also withheld.

Within each dataset, query identities, order and labels were common to paired methods. Calibration prefixes preserved acquisition order. Source and current-support signals alone estimated learned transforms and alignment references; query labels entered scoring. Figure 1 specifies the information available to each pipeline.

\Needspace{44\baselineskip}

![Figure 1](figures/Fig1_workflow.pdf){width=100%}

**Figure 1. Information and update operations.** The source training set and chronological current-session support define the fitting information. Frozen CSP/LDA uses source alone. LDA-only retains source CSP, full refitting relearns CSP and LDA, and EA estimates separate source/support references before full refitting. Later whole-run queries share identities across methods. Source/support sizes are 40/19–20 in Kumar and 96/20 in BNCI.

### Four decoder pipelines and the added alignment contrast

Frozen CSP/LDA learned spatial filters and LDA from source training alone. LDA-only retained those source filters and fitted LDA to the source/support union. Full refitting learned CSP and LDA from that same union. EA-CSP estimated separate covariance references for source training and current support, aligned both populations, and learned CSP/LDA from their aligned union. Query transformation used the already fixed support reference.

The historical Kumar implementations used four CSP components, Ledoit–Wolf covariance regularization, log-power features, and LDA with automatic shrinkage [@ledoit2004]. The EA branch represented common-average signals in 21 orthonormal coordinates and estimated arithmetic-mean trial sample covariance references. The historical full and EA branches differed in coordinate/rank handling; the matched-coordinate sensitivity below addresses this implementation difference. The separately fixed BNCI implementation used four components, fixed covariance and LDA shrinkage of 0.1, float64 internal operations and separate source/support references.

Let B denote a participant's BA. The sequential pipeline contrasts satisfy

$$
B_{\mathrm{EA}}-B_{\mathrm{frozen}}
=(B_{\mathrm{LDA}}-B_{\mathrm{frozen}})
+(B_{\mathrm{full}}-B_{\mathrm{LDA}})
+(B_{\mathrm{EA}}-B_{\mathrm{full}}).
$$

The terms quantify classifier recalibration, the additional spatial refit with its refitted classifier, and the additional EA branch. Their sum accounts for the total pipeline difference. The historical 73.7% spatial share is the ratio of the mean full-minus-LDA difference to the mean full-minus-frozen difference; it does not include EA's later increment.

### Prediction changes and class coverage

For each participant/session, we calculated left- and right-class recalls, rL and rR, BA=(rL+rR)/2, weak-class recall W=min(rL,rR), and recall gap H=|rL−rR|. The identity W=BA−H/2 was checked before aggregation. Nonlinear W and H were computed within each original endpoint unit, then averaged using its original session/participant weights. Both class recalls accompany W because the weaker class can change between methods.

For reference predictions a and updated predictions m, a query with true class c received weight 1/(2n_c). Corrected errors C sum the weights of trials changing from wrong to right, introduced errors I sum those changing from right to wrong, and disagreement D sums all changed hard predictions. Binary predictions satisfy

$$
\Delta\mathrm{BA}=C-I,\qquad D=C+I.
$$

C and I use the full class-balanced query denominator. They are not conditional rates within the reference method's errors or correct predictions. Common trial identities and class labels were verified before each comparison. BA/W joint effects retained all nine combinations of positive, zero and negative differences, using tolerance 10\(^{-12}\). Participant and session summaries include actual class counts, effect ranges, negative-session proportions and leave-one-participant-out means.

Previously reported EA error transitions from these same saved predictions were reconstructed, while recall-resolved and joint-benefit summaries were computed under the present analysis plan. These analyses describe the existing prediction evidence. Probability endpoints below derive from the newly fitted matched sensitivities; the historical hard-label replay retains its separate scoring scope.

### Calibration budgets and targeted sensitivities

The completed Kumar budget experiment evaluated chronological support prefixes of 4, 8, 12, 16 and the full 19/20 labels. Source training and later query identities stayed fixed. Full support contained 19 trials in 14 of 90 participant/session cells and 20 in 76. Single-class prefixes were retained because binary source training still supplied both classes.

The frozen 250 µV raw peak-to-peak rule flagged 1,512 of 7,156 complete Kumar windows. Main estimates retain them. Query-side sensitivity joins the same saved predictions to these flags by trial identity and compares all versus unflagged trials within the same eligible participants. Complete endpoints require both query classes in every target session; all undefined cells and retained class counts are reported.

The new fixed sensitivity compared full refitting, one common RMS normalization per trial, diagonal-reference alignment and full-covariance EA. Every Kumar arm used the same 21-dimensional Helmert common-average coordinates, four-component CSP with Ledoit–Wolf regularization (`norm_trace=False`, full rank), and automatic-shrinkage LDA. The BNCI arms retained the original 22-channel NumPy core and 0.1 covariance/LDA shrinkage. Diagonal references were defined in those fixed coordinates; Kumar contrasts are not individual electrode scales. These four arms required 396 new classical target fits. They saved genuine right-class probabilities and fitted-state digests before/after prediction. Balanced negative log likelihood used class-equal weights and a 10\(^{-7}\) clipping floor; binary Brier used the single-coordinate squared-probability definition.

The EA phase extension used common eligible trial identities in cue-anchored 5 s and task-start 2 s pipelines. Source training remained 40 examples; in the nine-person conditional scope, each session retained 4–19 support and 5–57 query examples. Support/query counts and identities were the same between windows, but this was not the original 19/20-label complete-query endpoint. All source, support and query windows used the corresponding signal definition. EA used the original 21-dimensional whitening/re-embedding into 22 channels and CSP/LDA path; original full-refit predictions were replayed after identity checks. There were 148 new EA phase fits and 32 original undefined cells. Nine original primary participants had complete five-session endpoints; a metadata-complete sensitivity retained eight, excluding sub-15. Unknown markers and missing classes were retained as undefined.

### Statistical units and analysis roles

Kumar endpoints first average five target sessions within each participant, then average participants equally. Original primary 12, development 6 and all 18 descriptive scopes are separate. BNCI retains the original 120-query participant endpoint; its five query runs describe within-person variation.

The historical Kumar full-minus-frozen contrast remains original primary and full-minus-LDA-only original secondary. Their historical 10,000-draw participant-bootstrap intervals are retained. The post-hoc exact sign-flip analysis preserves a four-contrast Holm family: those two contrasts, LDA-only minus frozen, and full minus frozen in the original ten-person amplitude-restricted subset. Thus, the original primary pointwise interval and adjusted test use different inferential conventions, both reported.

Kumar EA and budget/window follow-ups are exploratory. Their historical pointwise intervals used 10,000 participant draws, seed 42. The separately fixed BNCI primary contrast is full minus LDA-only; full minus frozen, LDA-only minus frozen and EA minus full form its three-test secondary Holm family. BNCI exact tests enumerate 512 sign assignments; historical bootstrap uses 10,000 draws, seed 20261027, participant order 1–9.

The present descriptive endpoints and CPU sensitivities were specified before their execution in an isolated revision plan on 4 November 2026 UTC. They use paired participant bootstrap, 10,000 draws, seed 20261104, numeric participant order and linear 2.5th/97.5th percentiles. These intervals are labeled separately from historical intervals; no new p-value family is introduced. Previously exposed data remain exposed. Participants are independent units; trials, sessions, seeds and model counts are repeated observations. Existing neural/geometric outcomes remain in the supplement rather than contributing extra people.

## Results

### Alignment added accuracy after supervised spatial refitting

At the full current-session support budget, EA-CSP achieved 70.66% BA in the original twelve-person Kumar cohort, compared with 65.36% for full refitting, 59.89% for LDA-only and 57.94% for frozen decoding (Table 1; Figure 2). Its incremental EA-minus-full gain was 5.30 percentage points (historical exploratory pointwise 95% interval 2.81–8.26), positive in ten of twelve participant averages. Its total gain over freezing was 12.72 points (6.50–19.10).

In BNCI, EA-CSP achieved 77.50% BA versus 71.85% for full refitting. The secondary EA-minus-full gain was 5.65 points (3.15–8.70; exact p=0.00391, Holm p=0.01172). All nine participant differences were positive, ranging from +0.83 to +15.83 points; every single-participant deletion retained a positive mean, 4.38–6.25 points. Each of the five target-query run cohort means favored EA.

\Needspace{12\baselineskip}

**Table 1. Four pipelines at the full calibration budget.**

| Pipeline | Fitting/update operation | Kumar primary cohort, n=12, BA | BNCI, n=9, BA | Current labels |
| --- | --- | ---: | ---: | --- |
| Frozen CSP/LDA | Source spatial filters and classifier | 57.94% | 70.56% | 0 |
| LDA-only | Source CSP; source/support LDA refit | 59.89% | 71.67% | Same support |
| Full CSP/LDA | Source/support CSP and LDA refit | 65.36% | 71.85% | Same support |
| EA-CSP/LDA | Separate domain references; aligned CSP/LDA refit | 70.66% | 77.50% | Same support |

BA is balanced accuracy. Kumar endpoints average five target sessions per participant; BNCI endpoints use 120 second-day query trials per participant. Source/support labels are 40/19–20 in Kumar and 96/20 in BNCI. Updating methods share these examples within each dataset; frozen decoding uses no current labels. These historical estimates retain the original implementations.

The original Kumar full-minus-frozen gain was 7.42 points (2.49–12.48; exact p=0.01953, Holm p=0.05859). Its secondary full-minus-LDA-only increment was 5.47 points (2.17–8.91; Holm p=0.04102), or 73.7% of the mean full-refit gain. By contrast, the fixed BNCI primary full-minus-LDA-only difference was 0.19 points (−1.85 to 2.13; p=0.96875): three participants improved, three decreased and three were unchanged. Table 2 retains these distinct analysis roles while locating EA's additional increment.

\Needspace{12\baselineskip}

**Table 2. Historical component contrasts and inferential roles.**

| Cohort | Contrast and role | Mean difference[95% interval],pp | Exact p | Holm p |
| --- | --- | ---: | ---: | ---: |
| Kumar 12 | Full−frozen; original primary | +7.42[2.49,12.48] | 0.01953 | 0.05859 |
| Kumar 12 | Full−LDA-only; original secondary | +5.47[2.17,8.91] | 0.01025 | 0.04102 |
| Kumar 12 | EA−Full; exploratory | +5.30[2.81,8.26] | — | — |
| BNCI 9 | Full−LDA-only; fixed primary | +0.19[−1.85,2.13] | 0.96875 | — |
| BNCI 9 | Full−frozen; secondary | +1.30[−1.76,3.98] | 0.45312 | 0.68750 |
| BNCI 9 | LDA-only−frozen; secondary | +1.11[−0.46,2.96] | 0.34375 | 0.68750 |
| BNCI 9 | EA−Full; secondary | +5.65[3.15,8.70] | 0.00391 | 0.01172 |

pp, percentage points. Intervals are pointwise participant-bootstrap intervals from their original analyses. Kumar Holm values use the original four-contrast family; BNCI secondary values use its separate three-contrast family. The BNCI primary comparison lies outside that secondary adjustment. A dash denotes a test not reported for that analysis role.

\Needspace{44\baselineskip}

![Figure 2](figures/Fig2_performance.pdf){width=100%}

**Figure 2. Four-method performance and paired increments.** Participant outcomes and cohort summaries in Kumar and BNCI distinguish the full-refitting increment from EA's additional branch. Panels A–B show new descriptive participant intervals; panels C–D retain the historical contrast intervals and roles in Table 2. Repeated sessions contribute within-participant observations rather than additional participants.

### Corrected errors and class recalls resolve the added value

EA corrected 14.61 points of class-balanced errors and introduced 9.32 points in Kumar, reconstructing its 5.30-point net gain from the unrounded values. The BNCI values were 12.78 corrected and 7.13 introduced points, reconstructing 5.65 points. These are transitions on identical later queries, recovered from the same saved prediction evidence previously used for EA summaries.

Weak-class recall increased by 10.45 points in Kumar (new descriptive 95% interval 5.11–16.04) and 8.52 points in BNCI (5.00–12.59). The recall gap decreased by 10.31 points (3.70–16.89 in magnitude) and 5.74 points (0.93–10.74), respectively. BA and weak-class recall increased together in ten of twelve Kumar participants and all nine BNCI participants (Figure 3). The two remaining Kumar participants decreased in both measures. These joint summaries retain all positive/zero/negative combinations in the source tables.

The Kumar participant BA differences ranged from −0.39 to +16.33 points; the two decreases were −0.17 and −0.39 points. Every leave-one-out cohort mean remained positive, 4.29–5.81 points. Eighteen of 60 participant/session BA differences were negative, giving an equally participant-weighted negative-session proportion of 30%. Thus, the longitudinal cohort gain coexisted with local session losses. The six-person development cohort and all 18-person descriptive scope are reported separately in the supplement.



\Needspace{44\baselineskip}

![Figure 3](figures/Fig3_error_coverage.pdf){width=100%}

**Figure 3. EA prediction transitions and class coverage.** Corrected and introduced class-balanced error mass reconstructs EA-minus-full BA. Recall-resolved estimates and paired participant BA/weak-class differences describe the distribution of that increment. Weak-class recall is computed within each original endpoint unit before aggregation; zero changes remain distinct from positive and negative changes. New descriptive intervals use the present paired participant bootstrap.

### Alignment gains varied across chronological calibration prefixes

The original primary-cohort EA curve rose from 60.22% BA at four labels to 66.10%, 67.59%, 70.08% and 70.66% at 8, 12, 16 and full support (Figure 4). Full-refit values were 58.74%, 61.25%, 64.31%, 66.93% and 65.36%. EA-minus-full means were therefore 1.48, 4.85, 3.28, 3.15 and 5.30 points. Historical pointwise intervals included zero at four labels and were positive at the other scheduled budgets.

LDA-only values were 58.83%, 60.07%, 61.41%, 62.14% and 59.89%. Consequently, the full-minus-LDA-only spatial increment increased from −0.08 points at four labels to 5.47 points at full support. Complete curves retain the nonmonotonic last step and all single-class support cases. They characterize the scheduled calibration sequence, with its changing examples and label counts, rather than select a new deployment budget.

\Needspace{44\baselineskip}

![Figure 4](figures/Fig4_budget.pdf){width=100%}

**Figure 4. Calibration budgets and the paired alignment increment.** Four-method BA and EA-minus-full differences across the fixed 4/8/12/16/full prefixes. Full support contains 19 or 20 labels. Query identities remain fixed across budgets. New paired descriptive uncertainty is identified separately from the preserved historical intervals in the result tables.

### Matched implementations and signal sensitivities

Ten original primary-cohort participants had both query classes in every session after amplitude restriction. Within this same eligible set, EA-minus-full was 5.78 points on all query trials and 6.07 points on unflagged queries (new interval 2.38–10.44). The paired change caused by restricting queries was +0.30 points (−1.01 to 1.52). This comparison preserves source/support signals and the same participant denominator.

With coordinates and decoder core matched, Kumar full/RMS/diagonal/EA BA was 65.36%, 69.52%, 67.88% and 70.43%, respectively (Figure 5). EA minus full was +5.07 [+2.88, +7.71] points. EA added +2.55 [+0.59, +4.49] points beyond diagonal alignment; its difference from common RMS normalization was +0.91 [-1.28, +3.18] points. The latter interval included zero. In BNCI, EA minus RMS was +4.63 [+1.94, +7.96] and EA minus diagonal alignment +4.91 [+1.94, +8.24] points. These new shared-core estimates remain separate from historical results.

In the matched fits, BNCI EA-minus-full balanced NLL changed by −0.07265 nats (−0.16079 to −0.00720) and Brier by −0.02629 (−0.05188 to −0.00771). Kumar changes were +0.01859 nats (−0.04038 to 0.07941) and −0.00923 (−0.02739 to0.00717), respectively. Thus, the classification gain did not imply the same probability-score improvement in both datasets.

The phase comparison located a marked dependence on signal definition. In the same nine conditional participants, EA-minus-full was 7.85 points (3.04–13.66) for cue-anchored 5 s windows and 0.13 points (−1.40 to1.92) for task-start 2 s windows. Their participant-paired task-minus-cue difference was −7.73 points (−12.17 to −3.76). The eight-person metadata-complete analysis gave 7.55 and 0.53 points, with a paired change of −7.03 (−11.84 to −2.97). Source/support/query trial identities were matched between windows; the retained calibration range was 4–19 labels per session. This is a joint comparison of anchor, duration and local filtering boundaries in complete fitting/evaluation pipelines.

\Needspace{44\baselineskip}

![Figure 5](figures/Fig5_mechanisms.pdf){width=100%}

**Figure 5. Implementation and signal sensitivities.** A–B: participant BA and cohort means for the four matched arms in Kumar and BNCI; means are shown without arm-wise confidence bars. C: paired EA-minus-full, EA-minus-RMS and EA-minus-diagonal contrasts with new descriptive participant intervals. D: EA-minus-full in the conditional nine-person and metadata-complete eight-person cue 5 s/task 2 s scopes, and their paired task-minus-cue changes. Each phase pair shares source/support/query identities; conditional support contains 4–19 labels per session. Historical results remain separate from newly fitted sensitivity arms.

## Discussion

### EA adds value after the decoder has used the same labels

EA increased BA beyond full spatial refitting in both evaluated acquisitions. The 5.30-point Kumar and 5.65-point BNCI increments occur after full CSP/LDA has already used the same source and current-support examples. The component sequence therefore identifies a concrete computational use of the short calibration run: estimate a domain reference before learning discriminative filters. This is more informative than comparing an updated decoder with a frozen source model alone.

The ordinary spatial-refitting increment differed between cohorts: 5.47 points beyond LDA-only in Kumar and 0.19 in BNCI. The positive EA branch is the common empirical finding, while that earlier component depends on the evaluated recording and implementation. Covariance estimation, references, source-label counts and windows differ between acquisitions. The matched-implementation sensitivity makes the relevant coding choices explicit rather than assigning all cross-cohort variation to physiology.

He and Wu already established EA, its CSP/LDA combination and calibration using only then-available target signals [@he2020alignment]. The contribution here is the longitudinal, information-matched measurement: how much EA adds after full refitting, which errors it corrects and introduces, and how those changes reach the two classes and individual participants. The current results support a specific update comparison rather than a new name for an established transform.

### Prediction redistribution gives the cohort mean practical resolution

The added EA gain arises from more corrected than introduced errors, not from eliminating every error introduced by adaptation. Class-balanced transition weights express both quantities on the same scale as BA. Left/right recall and weak-class recall resolve whether the average increment reaches the less accurately decoded class. The joint BA/weak-class gains show that the improvement reached the less accurately decoded class in the same people. This dynamic class need not be the same hand under every method. In BNCI, mean left recall changed by −1.67 points (−12.41 to 8.15) while right recall increased by 12.96 points (4.44–22.96). Kumar left/right changes were +3.34 (−4.81 to 11.37) and +7.26 points (1.60–13.11). Weak-class gains therefore describe improved coverage of the currently weaker class, rather than a claim that both fixed hand-class means increased.

Participant effects, session profiles and leave-one-out summaries show the extent to which the mean represents shared benefit. In BNCI, every participant and each query-run cohort mean favored EA. Kumar's ten positive participant averages coexist with two nonpositive averages and within-person variation. Preserving those distributions describes the actual reach of recalibration without turning repeated observations into independent replications.

The algebraic checks provide a compact audit of this interpretation: corrected minus introduced error equals the BA difference, and weak-class recall equals BA minus half the recall gap. These are connected views of the same predictions. They explain the measured endpoint; they do not by themselves identify a physiological cause of drift.

### Calibration information and the signal endpoint define the comparison

The budget curves show that EA's increment is already visible before the full support run, while its smallest-prefix uncertainty is larger. Chronological prefixes couple additional labels with additional signal examples and a changed observed class composition. Separating label revelation from the number of recorded reference trials is a useful next step for deciding how calibration effort should be allocated.

The matched-coordinate comparison retained a 5.07-point Kumar EA increment over full refitting. Its mean exceeded diagonal alignment by 2.55 points, while the 0.91-point difference from common RMS normalization had an interval crossing zero. BNCI EA exceeded both simple controls. These findings identify which preprocessing contrasts are supported in each setting: full covariance information added value beyond diagonal scaling, while the Kumar RMS comparison leaves the extra contribution beyond one trial-wise scale uncertain. Probability scores likewise require their own endpoint: BNCI NLL and Brier improved, while the Kumar intervals spanned zero.

The paired window result is particularly informative for the task interpretation. EA's added gain was 7.85 points in the conditional cue-anchored pipeline and 0.13 points in its task-start counterpart, with a negative paired change. The same pattern in the metadata-complete subset places the observed contribution in the evaluated five-second definition. Source, support and query windows change jointly in anchor, duration and local filtering context; the contrast measures that complete signal-definition change.

The cue-anchored Kumar endpoint labels complete five-second windows that can include imagery, feedback or subsequent activity. The paired phase comparison uses a reduced common-eligibility scope and fewer support examples than the original full-budget endpoint. Query-amplitude sensitivity instead evaluates unchanged fitted decoders on a restricted test subset. These comparisons distinguish an amplitude restriction at scoring from a change in the complete fitting/evaluation signal definition.

### Scope and reproducibility

The evidence concerns 18 Kumar participants and nine BNCI participants, analyzed within their own cohorts. The original primary/secondary hierarchy remains attached to the historical comparisons. EA and the new prediction-level and CPU-sensitivity extensions use previously exposed data and are exploratory. The BNCI four-method protocol was fixed before its saved predictions were generated, with EA in its secondary family; the same public participants also appeared in related project work. Source and overlap ledgers identify reused predictions, tools and earlier analyses.

Complete neural and geometric controls are retained in the supplement, including their candidate primary contrasts, seeds and budget profiles. They use the existing six-person development group and do not enlarge the independent sample. This revision's central evidence is the conventional four-pipeline comparison and its targeted sensitivities. Zero-phase preprocessing defines an offline endpoint; closed-loop benefit and clinical outcomes require a separately designed study.

## Conclusions

Euclidean alignment added 5.30 BA points beyond full supervised refitting in the original Kumar cue-anchored comparison and 5.65 points in BNCI, with improved weak-class coverage. The shared-coordinate sensitivity retained a 5.07-point Kumar increment, while the paired Kumar task-window analysis located the larger EA contribution in the five-second cue-anchored setting. Prediction transitions, class recalls and matched signal controls identify what the short calibration run adds and which signal definition supports that gain.

## Data and code availability

Kumar2024 source EEG is available as NEMAR nm000177/v1.0.5, DOI 10.82901/nemar.nm000177.v1.0.5, under CC BY 4.0 [@nemar177]. BNCI2014-001 original recordings are available through the official BNCI directory, with versioned hashes in NEMAR nm000139/v1.0.3, under their CC BY-ND 4.0 terms. Code, saved-prediction lineage, full-precision tables and reproduction instructions accompany this isolated extension at https://github.com/jackzhu119/few-shot-mi-eeg, branch \texttt{\seqsplit{research/paper2-alignment-integrated-revision}}. Source manifests distinguish historical evidence, new derived metrics and actually refitted sensitivities. Original code uses MIT; original manuscript, figures and derived results use CC BY 4.0 within LICENSING.md. Third-party terms remain applicable.

## Acknowledgments

The authors thank the researchers who released Kumar2024 and BCI Competition IV 2a. Tool assistance and author responsibilities are documented in the separate Ethical and Legal Declarations.

## References

::: {#refs}
:::

## Supporting information captions

**Supplementary methods and data.** Complete historical decoder definitions and comparisons; new recall, error-transition and probability definitions; participant/session/class counts; all calibration budgets; completed implementation, amplitude and window sensitivities; full neural/geometric controls; input lineage and reconstruction instructions.
