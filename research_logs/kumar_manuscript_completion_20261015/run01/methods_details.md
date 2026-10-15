# Independent methods-completeness notes

This review concerns reporting of completed analyses. It adds no experiment, scientific assumption, fit, model forward pass, query access, seed selection, threshold selection, or Pod operation. All settings below come from existing frozen files and saved text audits. Author declarations remain for the authors to supply.

## Review outcome

No unsupported adaptation-efficacy, architecture-causality, human-learning, retention, or clinical claim was found. The expanded main manuscript now correctly distinguishes 10,000-resample BA/reliability intervals from 2,000-resample drift-association intervals. The concrete definitions below belong in the supplement; they do not require rerunning completed analyses.

The initial main-draft wording could imply that all descriptive intervals used 10,000 resamples. The revised Methods explicitly limits that procedure to BA and participant-mean reliability and separately describes 2,000 participant-block resamples for session-level drift associations. This resolves the reporting ambiguity while preserving all results.

## 1. Data eligibility and information budgets

The analysis uses Kumar2024 NEMAR derivative `nm000177/v1.0.5`, not a pooled cohort. Preparation verified the pinned 2,705-file selection (1,781,052,841 bytes), 360 EDFs, 18 published identities, 108 sessions, 7,200 original event identities, 7,156 complete five-second windows and 44 preserved partial events. Exact numerical duplicate groups were absent among the raw trial windows, included processed windows and whole recordings. Absence of exact copies does not independently establish biological identity or independence across other datasets.

The complete whole-run partition is:

| Role | Session/run | Use |
|---|---|---|
| Source TRAIN | ses-0 / runs 0 and 1 | 40 windows per participant |
| Source validation | ses-0 / run 2 | 20 windows; EEGNet epoch selection only; CPU descriptive readout |
| Source query | ses-0 / run 3 | Fixed prediction |
| Current target support | ses-1 through ses-5 / run 0 | At most 20 original events, 10/class, without partial replacement |
| Target query | ses-1 / runs 1–3; ses-2 through ses-5 / runs 1–2 | Fixed prediction |

Across 90 target sessions, 14 support runs contain 19 included windows and 76 contain 20: 1,786 total. No previous or future target support is accumulated. The query inventory preserves 4,320 recorded identities and 30 original partial exclusions, leaving 4,290 included unique events: 360 source and 3,930 target. Each method evaluates those same identities and exclusions.

The label-use distinction is essential. EEGNet fits parameters and normalization on TRAIN40 and uses another 20 labeled validation windows to select epoch. CPU fixed settings do not use validation for selection. The two CPU updates additionally fit current support19/20, while both source-only pipelines use zero target labels. The two CPU update methods share exact source/current-support labels but differ in computation. Cross-family EEGNet-versus-CPU differences are descriptive pipeline comparisons, not effects under matched information or compute budgets. All seeds reuse the same trial labels; three seeds add no participants or unique trials.

Sources: `KUMAR_MODEL_ELIGIBILITY_REPORT.md`; `KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md:63`; `configs/kumar_cross_session_20261012.json`; the frozen split manifest; `research_logs/kumar_frozen_query_comparison_20261015/run01/comparison_receipt.json`.

## 2. Preprocessing, QC and model details

A complete event contains 2,560 samples at 512 Hz. Each epoch independently receives instantaneous common-average reference across 22 EEG channels, fourth-order Butterworth SOS 8–30 Hz filtering using `sosfiltfilt` default odd padding, and `resample_poly(1,4)` with default Kaiser-5 window and constant padding. The output is 22 × 640 float32 numerical volts at 128 Hz. These operations learn no held-out statistics. Zero-phase filtering is offline.

The fixed raw-window maximum channel peak-to-peak flag is 250 µV; all 1,512 flagged complete windows remain among 7,156 included windows. This is neither artifact removal nor expert certification. CAR cannot reconstruct native CPz acquisition or demonstrate neural specificity.

CPU CSP has four components, Ledoit–Wolf regularization, log mean-square features and `norm_trace=False`; LDA uses `lsqr` and automatic shrinkage. Seed is 42. Source-only fits both stages on TRAIN40. Recalibration retains source CSP and refits LDA on TRAIN40 plus current support. Full refitting updates both stages on the same union. Validation/query rows never enter CPU fitting or parameter selection.

The full EEGNet constructor/optimization must remain recoverable from the frozen configuration: Braindecode 1.2.0 EEGNet; F1=4, D=2, F2=8; temporal kernel64, depthwise kernel16; mean pools4/8; automatic final-convolution length; ELU; dropout0.5; spatial max-norm1.0; BN momentum0.01, affine parameters, epsilon0.001; `final_layer_with_constraint=false`, `norm_rate=0.25`. Adam uses learning rate0.001, betas(0.9,0.999), epsilon1e-8, zero weight decay and no AMSGrad. Batch size16, maximum100 epochs, no scheduler/class weights/label smoothing; seeded training shuffle, `drop_last=false`, `num_workers=0`.

EEGNet validation selection minimizes mean CE with patience15, min_delta0 and earliest epoch on ties; restore the complete selected state. Reaching the 100-epoch cap is distinct from patience termination. All seeds 20261012/13/14 are retained. Channel mean/SD uses source TRAIN axes(trial,time), floor1e-8 V. Only training minibatches update BN. Query is untuned logit argmax in eval/inference mode with no optimizer, parameter, BN, normalization or support update. Accepted checkpoint/context hashes and before/after state digests bind the recorded inference, but do not reconstruct transient memory or prove cross-hardware bitwise reproducibility. Source CE replay tolerance remains absolute1e-7, relative0.

Sources: `KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md:43`; `configs/kumar_eegnet_gpu_development_20261014.json`; `EEGNET_TRAINING_PLAN.md:54`; `docs/kumar_frozen_checkpoint_query_protocol_20261015.md:66`.

## 3. BA, aggregation and uncertainty

Per participant/session/method/seed, BA is half the sum of left and right recalls. An absent true class yields an unavailable BA rather than an invented score. Confusion counts, recalls, predicted proportions, collapsed cases and failures remain available.

EEGNet averages the three seed-specific BA values within participant/session, rather than averaging logits/probabilities or votes. It then averages five target sessions equally within participant; cohort summaries weight participants equally. Source query stays separate. Larger query sessions do not gain endpoint weight; trials, runs, sessions and seeds do not create additional participants. Missing required seeds/sessions propagate unavailability rather than silently disappearing.

Development6 and remaining12 stay separate; all18 is secondary. The original primary is full CSP/LDA refit minus source-only on remaining12 target endpoints. Paired intervals resample the same participant indices for both methods. CPU/EEGNet BA endpoint summaries use 10,000 resamples, seed42, percentile bounds[2.5,97.5], with recorded lexicographic subject order. New EEGNet-minus-CPU contrasts contain means/medians/sign counts, with no new CI, p value or selected winner. Selected source-validation scores remain descriptive.

Reliability means also use 10,000 participant resamples/seed42, but preserve numeric development order[1,4,7,10,13,16]. Session-level drift-association intervals instead use 2,000 participant-block resamples/seed42, preserving all five sessions of every sampled participant. These procedures must not be collapsed into a single generic 10,000-draw statement. No interval represents uncertainty over alternative training sets or hyperparameter searches.

Sources: `scripts/aggregate_kumar_frozen_queries.py:28`, `:138`; `scripts/run_kumar_baselines.py:552`; `scripts/analyze_kumar_lowdim_reliability.py:325`; `scripts/verify_analyze_kumar_results.py:67`; executed association JSON and comparison validation.

## 4. Drift predictors

The outcome is target-query frozen-CSP/LDA BA minus the same participant's source-query BA. Covariance change is the target-minus-source-query mean distance to a source-TRAIN Riemann mean. Use the fixed21×22 Helmert basis to remove the CAR null direction, within-epoch time centering, unbiased covariance, trace normalization, and `0.9C+0.1I/21` shrinkage. The affine-invariant Riemann mean uses an arithmetic initializer, unit step, maximum100 iterations and tolerance1e-10. This is a normalized covariance-shape proxy, not all distributional or amplitude change.

The task axis is normalized right-minus-left class mean in source-TRAIN standardized44-dimensional Mu/Beta log-power coordinates. One-dimensional Wasserstein distance compares source-query and target-query projections without target labels. The remaining-cohort Spearman analysis uses 60 participant×target-session rows, with participant-block uncertainty; separate participant-mean correlations are recorded. Retrospective labeled separation is not a label-free decision signal.

Sources: `KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md:102`; original frozen task-aware analysis plan:18; `scripts/verify_analyze_kumar_results.py:67`; `task_information_associations.json`.

## 5. Reliability coordinates and source folds

Reliability uses only development IDs1/4/7/10/13/16, source TRAIN runs0/1 and current target run0 support; no source validation/query, target query or remaining-cohort signals. These measurements are not replacements for held-out query endpoints.

Power features use Welch PSD at128 Hz, Hann window, nperseg256, noverlap128, constant detrending, density/one-sided scaling and mean averaging. Integrate Mu8–13 Hz and Beta13–30 Hz absolute power by trapezoid including edge bins; use `log10(max(power,float64 tiny))` in channel-major44-dimensional order. Candidates are standardized44, PCA4(full SVD, no whitening), and C3/Cz/C4 × two bands(motor6). Source-only StandardScaler uses ddof0. Each TRAIN20 fold fits its own scaler/PCA. The centroid probe uses the TRAIN right-minus-left direction and projected midpoint threshold, predicting right for projection>=threshold. Source40 transforms used for support diagnosis never fit the held-out source folds.

Supervised CSP source probes train on run0's20 rows and evaluate run1's20, then reverse. BOTH CSP and LDA refit for every training-label rotation. Enumerate all20×20 joint circular label shifts, including identity; cache20 TRAIN-rotation models per fold, predict each unchanged holdout once, then score those predictions against all20 held-out label rotations. Across six IDs this yields240 pipeline attempts(240 CSP and240 LDA), including12 identity-fold pipelines,4,800 fold-score evaluations and2,400 participant/joint-pair twofold means. Run02 had240 successes and0 failures. Rotating labels after fitting supervised CSP would be invalid.

Controls are conditional phase-alignment sensitivities, not formal permutation p values. Cyclic-boundary exchangeability, temporal stationarity, cue confounding and neural specificity are unverified. All failed/unavailable fits and exact attempted/valid denominators remain explicit.

Sources: `configs/kumar_lowdim_reliability_20261014.json`; `scripts/analyze_kumar_lowdim_reliability.py:147`,`:189`; `docs/kumar_csp_reliability_plan_20261014.md:28`; `scripts/analyze_kumar_csp_signed_score_v1.py:155`.

## 6. Support halves, vector direction and signed score

Reuse each participant's already fitted SOURCE40 CSP/LDA; no new full40 decoder fit. Features are natural log of mean squared projected amplitude. A four-coordinate StandardScaler fits SOURCE40 only(ddof0); the fixed source direction is standardized right-minus-left mean. Within each support class's chronological indices, half1 takes the first floor(n_class/2), half2 the remainder; concatenate and sort class indices within each half. Preserve zero directions, degenerate SDs, single-class halves, unavailable cases and denominators.

Half-to-half cosine is `dot(d1,d2)/(norm(d1)*norm(d2))`. The source-axis half contrast is `dot(d_half,u_source)/SD_SOURCE40(projection)`, with ddof1. Frozen LDA score is `s=f·w+b`, verified class order[0=left,1=right], predicting right strictly when `s>0`; no target centering, scaling or intercept change. Each half's balanced signed contrast is `(mean(s|right)-mean(s|left))/(2*SD_SOURCE40(s))`, with ddof1. Retain right mean/SD, negative left mean/SD, score location, recalls, prediction ratios and collapse separately.

Vector cosine and signed LDA contrast measure different properties. Positive cosine or half-product can occur when both halves oppose source direction. Class contrast cancels the intercept and can hide threshold collapse. Never flip score/labels or substitute max(BA,1-BA).

For support controls enumerate every19/20 cyclic label shift with fixed source axes/scores, recomputing classwise halves and separately retaining fixed-original-half sensitivity. No decoder is fitted on support in this diagnostic. Average two source folds or five support sessions within ID before six-ID bootstrap. Six published IDs—not30 sessions,240 fits or400 shifts—determine the population interval. Conditional within-support uncertainty is distinct from participant-population uncertainty.

Sources: `docs/kumar_csp_reliability_methods_review_20261014.md:71`; `docs/kumar_csp_reliability_plan_20261014.md:48`; `scripts/analyze_kumar_lowdim_reliability.py:236`; `scripts/analyze_kumar_csp_signed_score_v1.py:310`,`:339`; run02 scientific summary.

## 7. Source license, ethics and demographics

The data are declared CC BY4.0. Use the collection DOI10.82901/nemar.nm000177 and the explicit official version1.0.5 release URL https://data.nemar.org/nm000177/v1.0.5/, together with original data DOI10.5281/zenodo.10694880 and paper DOI10.1093/pnasnexus/pgae076. At the initial review, the version-suffixed DOI was present only in the historical ingestion plan and was withheld from the confirmed citation list. The later source-verification update below resolves that uncertainty: DOI10.82901/nemar.nm000177.v1.0.5 is now independently confirmed by the saved live DataCite response. The release metadata reports original-study UT Austin protocol2020-03-0073. Attribute that statement to the release; it is not the authors' secondary-analysis institutional determination.

The inspected available sources do not verify written consent text. Stored original-paper HTML is an HTTP403 challenge, not reviewed full text. The historical audit listed correction DOI10.1093/pnasnexus/pgae137. Its full content was initially pending; the later source-verification update below records the subsequently retrieved and reviewed OA correction, while leaving the original-paper HTTP403 record unchanged. Data licensing does not establish article/code licensing or ethical approval.

The release README reports18 healthy BCI-naive participants, age23.22±3.59 years, without identifying the± quantity. Actual derivative participants.tsv has age2020 and sex/hand n/a throughout. Do not recompute age/sex/handedness statistics, infer GR/PAR groups, or call the± quantity an SD without verification. The analyzed derivative has22 EEG channels; the original acquisition README's22EEG+3EOG description does not establish EOG channels or EOG artifact correction in this derivative.

Sources: `data/public_eeg/kumar2024/nm000177/v1.0.5/dataset_description.json:6`,`:18`,`:35`,`:36`,`:54`; release`README.md:24`; `participants.tsv:1`; frozen ingestion plan:5; original Zenodo metadata; historical extra-access receipts:79; `docs/public_longitudinal_dataset_audit_20261010.md:75`.

## 8. Runtime, preserved failures and author completion

Report training GPU and query CPU environments separately. The query contract lists Python3.11.16, Torch2.8.0+cpu, NumPy2.2.6, SciPy1.15.3, scikit-learn1.7.2, MNE1.10.2, Braindecode1.2.0 and Torchaudio2.8.0+cpu. Training records retain Torch2.8.0+cu128/A4500 and container-rebuild provenance. Keep exact code/config/input/checkpoint/state hashes and fixed numerical threads. Do not describe all historical hardware/storage/billing details as independently verified.

The failed CSP attempt, permission/recovery changes, initial batch pause, same-run resume and original producer-stage false flags remain historical evidence. Later audits, private full GET/SHA backups and actual parent confirmations append stages; they do not rewrite original receipts. Existing analyses need no repetition for writing.

Authors must supply authorship, affiliations, contributions, funding, COI, correspondence, institutional secondary-data determination, consent documentation and journal preferences. Verified bibliography/correction content still needs final author review. No new fit, query or online human study is necessary to report the completed offline evidence accurately; stronger human-learning or clinical claims remain outside this paper's demonstrated scope.


## 9. Later source verification: exact dataset version and published correction

The reference agent retrieved the exact version DOI from public DataCite at 2026-10-15T10:29:11.338833+00:00, HTTP200. The saved response confirms DOI `10.82901/nemar.nm000177.v1.0.5`, version `1.0.5`, publicationYear `2026`, state `findable`, title “Multi-session longitudinal motor imagery EEG dataset (Kumar et al. 2024)”, and landing URL `https://nemar.org/dataset/nm000177?v=v1.0.5`. This resolves the initial metadata-only uncertainty; the exact version DOI can now be cited alongside its explicit release/version, collection DOI and original study citation. The 2026 DataCite publicationYear describes the derivative metadata and does not change the original study's 2024 publication year.

The same source review obtained the full open-access correction `10.1093/pnasnexus/pgae137`, PMC10989871, from Europe PMC at 2026-10-15T10:29:43.632200+00:00, HTTP200. Its actual XML length is 4,378 bytes. The correction concerns the original paper's “GR transfer learning with common spatial patterns” paragraph, which had duplicated values: it retains CSP-Expert-Subject 0.3727±0.2924 and changes the compared CSP-Subject-Specific-Fix value to0.2120±0.2815 and CSP-Subject-Specific-Adapt to0.2515±0.3082. These are the original paper's reported quantities, not this manuscript's BA endpoints. The current study computes its own fixed-split CSP/LDA predictions and imports no numerical result from that paragraph, so no scientific result or frozen parameter changes. Cite the correction and disclose its scope; do not reinterpret those original quantities as our BA results.

This later correction access does **not** establish that the original main paper's previously blocked full text or original consent wording was read. The historical HTTP403 challenge remains preserved, and author confirmation of consent documentation and secondary-analysis institutional requirements remains pending.

Verified local source identities:

| Raw source | Bytes | SHA256 |
|---|---:|---|
| `research_logs/kumar_manuscript_references_20261015/run01/nemar177_version_datacite.json` | 13865 | `c65e6a698c39aac8f7dfb0a0f1f9e2b9f30e5e72ef5bbaa399fe8852574d0011` |
| `research_logs/kumar_manuscript_references_20261015/run01/kumar2024_correction_fulltext.xml` | 4378 | `9a0449d0b6add41822fd2e6e4148c30f582fc847318a28a2518498d99a091f09` |
| `research_logs/kumar_manuscript_references_20261015/run01/kumar2024_correction_body.txt` | 824 | `a29e6362f2fae1346760c17776147742e4c88e7342bd805ef5dc80d8f74b1b7f` |

The full HTTP/date/hash receipts are `version_and_correction_access_receipts.json` and `correction_fulltext_access_receipt.json` in that same references directory. This reviewer read the saved source files; the network retrieval belongs to the separately recorded reference agent and is not attributed to this read-only methods review.
