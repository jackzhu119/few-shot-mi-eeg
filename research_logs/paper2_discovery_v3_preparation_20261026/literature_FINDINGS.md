# Focused literature check for V3 — 26 October 2026

The closest literature does not support claiming that source anchoring, covariance alignment, latent centering, BN adaptation, or longitudinal fine-tuning is new by itself. A defensible V3 contribution must be a precise new estimator/information regime, tested against those strong controls, with independent validation. This is a focused methods review, not an exhaustive novelty search.

## Most relevant established methods

- **He & Wu, EA:** https://arxiv.org/html/1808.05464 — relevant full Methods read. Covariance whitening/centering and online supervised evaluation already exist. Restricting target-statistic estimates to the current chronological support is a real information-access distinction from offline alignment using all query covariances; it must be explicit rather than an implied novelty claim.
- **Rodrigues, Jutten & Congedo, RPA (2019):** https://doi.org/10.1109/TBME.2018.2889705 — EuropePMC abstract/Crossref metadata read, HAL PDF blocked403. SPD distribution translation/scaling/rotation is established. The abstract supports this broad distinction, not an exact claim about every RPA implementation detail.
- **Bakas et al., latent alignment (2025):** https://doi.org/10.1088/1741-2552/adb336 — abstract/metadata read. Feature-space alignment is established, and the abstract explicitly identifies a tradeoff between later-stage alignment and sensitivity to class imbalance. This is directly relevant when a chronological4-label prefix may have only one class. A class-balanced common-mode/contrast estimator should include a matched imbalance/centering control and preserve missing-class fallbacks.
- **Wimpff et al. (2025 v1 preprint):** https://arxiv.org/html/2502.06828v1 — relevant full Methods read. It uses61participants/7–11sessions, source pretraining from other subjects' first sessions, causal independent/sequential fine-tuning, and onlineEA+AdaBN. V3 cannot claim first longitudinal neural adaptation or first EA+BN combination. Its prior-session, cross-subject-source regime differs from current-session20-label calibration.

## Supporting baseline references

- Lotte & Guan (2011), DOI10.1109/TBME.2010.2082539, abstract read: RCSP unifies source-informed covariance regularization; simple source/target mixing is established.
- Li et al., AdaBN (2016), https://arxiv.org/html/1603.04779, relevant full Algorithm1 read: explicitly replaces/modulates domain BN means and variances. Support-only BN statistics, full/frozen BN and fixed dropout should be separated experimentally; BN adaptation alone is not a new algorithm.
- Li, Grandvalet & Davoine (ICML2018), https://proceedings.mlr.press/v80/li18a.html, official PDF regularization Methods read: L2-SP anchors weights to the initial pretrained model. It does not by itself define a BN-buffer policy; scaling of its penalty must be reported, not tuned on query outcomes.
- Junqueira et al. (JNE2024), DOI10.1088/1741-2552/ad4f18, abstract read: EA+deep EEG shared/individual transfer is already evaluated. This DOI is distinct from the separate Eder benchmark DOIad6793 cited in the earlier review.

## Defensible incremental claim and controls

A candidate contribution could be **a source/current-support-only, finite-sample noise-aware estimator that shrinks shared session shift and class-discriminative contrast separately**, rather than a scalar covariance mix after noisy target whitening. The proposed estimator must state its exact risk proxy, class-prior convention, source- and target-variance estimates, and missing-class behavior. A covariance-mean risk result is not a classification-BA or negative-transfer guarantee.

Strong matched controls are EA-CSP, a tangent/log-covariance classifier with ordinary pooled fitting, fixed-weight versions in the same representation, common-mode-only and contrast-only ablations. Use equal source/support information, identical query identities, all fixed seeds, and participant-level aggregation. For neural diagnostics, separate BN-buffer policy and trainable parameters while holding dropout and source initialization fixed. Pooling more source subjects is a separate data-budget axis, not proof that the adaptation rule alone improved.

These6already-exposed participants support exploration. To obtain algorithm optimization evidence that is stronger than another selected development score, freeze one final candidate/primary contrast before an independent external query. Retain every prespecified result/failedcell; unlimited repeated tests followed by best-score selection cannot substitute for this evidence.

`LITERATURE_EVIDENCE.json` records exact retrieved source bytecounts/SHA256 and reading scopes. Copyrighted fulltexts stay in this local working folder and need not be committed; only this summary and metadata may be copied to the project.

## Functional trust-control references

- **Schulman et al., TRPO (ICML2015)**: https://proceedings.mlr.press/v37/schulman15.html . OfficialPDF sections3–5 read. The theoreticalmaximum-over-stateTV/KL constraint differs from the practicalaverageKL approximation, which thepaperexplicitlycallsheuristic. For a classificationanchor set, a bound onmeanKL only implies a finite-anchor meanTV bound viaPinsker/Jensen; it doesnotprovideunseenqueryBA, clinicalsafety ornegative-transferguarantees.
- **Li & Hoiem, Learning without Forgetting (ECCV2016; readarxivv3)**: https://arxiv.org/html/1606.09282 . RelevantMethodsread. It combinesfine-tuning withsoftteacherpredictiondistillation, applyingoldtaskoutputguidancetonewtaskinputswithoutoldtrainingdata. UsingexistingSOURCE TRAINexamplesasfunctionalanchorsisadifferentinformationregime, andfunctionalknowledgepreservationisalreadyestablished. Aweakteacher canremainweakunderKLpreservation.

For classifierprobabilities `p_i,q_i` onNfixedanchors, `mean_i TV(p_i,q_i) <= sqrt(mean_i KL(p_i||q_i)/2)`. This followsfromPinskerandJensenanddescribesonlytheobservedanchorset. It doesnotbounddiscreteargmaxlabelchangeswithoutadditionalmargins, anddoesnotbyitselfcontrolnewtargetrisk.
