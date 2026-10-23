# Paper 2: school-HPC research extension and literature assessment

Date: 2026-10-23. Status: **new scientific-version proposal and literature review; no new scientific training or query evaluation in this work**. The existing submitted manuscript, 54 accepted source models, original split, predictions and acceptance history remain historical results. Moving execution from RunPod to school HPC does not itself change an experiment's scientific identity. A changed algorithm, source-label budget or data selection does.

## 1. The strongest next question

**At a fixed target-label budget, does support-noise source anchoring add value after support-only Euclidean alignment, and reduce negative transfer relative to alignment with pooled full refitting?**

This is narrower and more defensible than claiming a new task-aware decoder from the current reliability probes. Existing work already studies adaptive CSP, source regularization, data alignment and longitudinal neural fine-tuning. The useful contribution would be an explicit, inspectable update rule, matched-information comparisons, participant-level downside analysis and an independent cohort. L2-SP is an established baseline, not a new algorithm here. Adding models or obtaining a higher score on already viewed Kumar outcomes does not establish independent validation or guarantee suitability for a particular journal.

The proposed empirical covariance shrinkage rule is a **candidate to test**, not an established novel or risk-guaranteed estimator. A positive result should state exactly which comparator, label budget and external population it improves. A negative result should remain a result rather than trigger unreported model search.

## 2. Existing evidence changes the starting point

The current manuscript preserves the original remaining-12 primary full-refit minus frozen effect of **+7.42 pp [2.49, 12.48]**, and secondary full-refit minus LDA-only effect of **+5.47 pp [2.17, 8.91]**. These historical intervals must not be replaced by slightly different later exploratory bootstrap intervals. The 54 EEGNet models are 18 participants × three seeds, not 54 independent participants. Remaining-12 source-query EEGNet BA was already approximately 52.92%, compared with target BA 51.58%; weak source learning is a plausible limitation before any explanation based on longitudinal drift.

Newer completed component results are present in a portable package even where the current Git main checkout lacks the corresponding files. The evidence root for this review is:

`/workspace/private_model_receipts/paper2-component-followup-20261016/data_package_portable_check/run02/extracted/component/repository/`

Use the following saved results, rather than rerunning those experiments or relying on the older integration draft that still called phase/gain results pending. Exact report/CSV byte counts and SHA256 values are in the companion JSON. A minimal public copy of the supporting tables and unchanged reports is now in [existing_evidence](../research_logs/paper2_hpc_v2_20261023/existing_evidence/REPORT.md), with byte-identical source hashes and ten checked quoted results.

| Evidence under the component repository | Verified report contents | Consequence for the new study |
|---|---|---|
| `research_logs/kumar_component_followup_20261016/budget_summary/run01/RESULTS_REVIEW.md` and `cohort_budget_paired_gains.csv` | 1,800 cells; 78,600 saved predictions; budgets 4/8/12/16/full; full is 19 or 20 labels. Remaining-12 full−LDA means at 4/8/12 labels are −0.08/+1.18/+2.90 pp, with all three pointwise intervals crossing zero. Full-support EA−full is **+5.30 pp [2.81, 8.26]**; means 70.66% versus 65.36%. | EA is a necessary strong control. Full spatial refitting is not uniformly optimal at very low label counts. Do not select 16 labels just because an observed curve falls at full support. |
| `research_logs/kumar_component_followup_20261016/phase_summary/run01/REPORT.md` | 540 cells, 11,460 saved predictions; 444 defined/96 undefined cells. Conditional remaining cohort n=9: full−frozen 5-s cue window +2.06 [−3.73,8.17] pp; 2-s task-start window +3.21 [0.08,6.56] pp. Their paired gain-change interval crosses zero. Separate metadata-complete n=8 is retained. | The phase sensitivity exists. It does not identify contamination as the cause of the original gain. Selection on an observed task duration, changed anchor, duration and filtering edges limit the comparison. |
| `research_logs/kumar_component_followup_20261016/gain_independent_audit/run01/REPORT.md` | Saved coefficients/predictions/arithmetic were independently checked; original launcher exit 1 after a VmRSS-monitor error remains, worker exit is unknown. Remaining-12 Ridge−full **−4.47 [−7.94,−1.32] pp**; Ridge−frequency-matched-random **+0.093 [−0.904,1.147] pp**. | These are complete saved exploratory results from a failed monitored operation, not a clean accepted run. They do not support a useful task-aware selector. Preserve failure evidence; do not rerun merely to erase it. |

All 18 Kumar participants' outcomes have been exposed. Existing development6/remaining12 labels remain in historical reports; a new split or new nested CV cannot restore unseen-test status. Reuse existing budget, phase, artifact and heterogeneous-response findings as motivation and exploratory checks.

## 3. What the closest literature actually establishes

This was a focused primary-source search, not a systematic or exhaustive review. Full-text reading means the relevant methods were actually opened; it does not mean every supplement or implementation was reproduced. Machine-readable reading scopes are in the companion JSON.

| Source and reading scope | Relevant distinction |
|---|---|
| [Kumar et al., PNAS Nexus 2024](https://doi.org/10.1093/pnasnexus/pgae076), original full-text Methods/Results and [correction](https://doi.org/10.1093/pnasnexus/pgae137) read | Adaptive versus fixed CSP and supervised first-online-run calibration predate this reanalysis. The correction changes CSP comparison numbers. A first-run support design or benefit from recalibration is not an original contribution by itself. |
| [Lotte & Guan, regularized CSP, 2011](https://doi.org/10.1109/TBME.2010.2082539), abstract/metadata | Prior/source-informed CSP regularization is established. Simply mixing source and target covariance does not establish an original algorithm. |
| [He & Wu, EA, online 2019 / volume 2020](https://arxiv.org/html/1808.05464), alignment methods full text | EA uses covariance-based whitening. A support-only estimate and an estimate using all future query covariances have different information access and must not share an unqualified label in comparisons. |
| [Rodrigues et al., Riemannian Procrustes analysis, 2019](https://doi.org/10.1109/TBME.2018.2889705), metadata only | Geometric transfer is established context; no performance or exact-method conclusion is inferred from unread full text. |
| [Li et al., L2-SP, ICML 2018](https://proceedings.mlr.press/v80/li18a.html), regularization methods full text | Anchoring neural parameters to pretrained values is established. Its usefulness here depends partly on the quality of the small source model, which was weak in the old EEGNet experiment. |
| [Eder et al., J Neural Eng 2024](https://doi.org/10.1088/1741-2552/ad6793), abstract/metadata | Multi-dataset benchmarking includes classical geometric and neural methods across within/cross-session settings. The current small-source result cannot establish that deep learning generally fails for MI. |
| [Wimpff et al., 2025 preprint v1](https://arxiv.org/html/2502.06828v1), relevant Methods full text | Already studies independent/sequential causal fine-tuning and online EA using a 61-person longitudinal dataset. Its preceding-session/online-information regime differs from the present fixed target-support regime. A general claim to first longitudinal neural adaptation is untenable. |
| [Ahmed et al., 2026](https://doi.org/10.3389/fnsys.2026.1840121), abstract/metadata | This is attention decoding, not a matching MI benchmark. Its explicit separation of parameter-sweep oracle results from leakage-free results is useful methodological context, not evidence for our method. |
| [Wang et al., Deep Cholesky space adaptation, Knowledge-Based Systems, October 2026](https://doi.org/10.1016/j.knosys.2026.116794), Crossref metadata and publisher search excerpt only | A recent cross-session MI geometry-adaptation paper was identified. Publisher text returned 403; no claim that our candidate is distinct from all its details is justified. It is a specific related-work item to read before an algorithm-novelty claim, not a reason to block runtime development. |

The inspected literature therefore reaches 2026, but detailed full-text coverage of recent longitudinal methods here reaches the 2025 paper. More citations alone do not improve the experiment.

## 4. Minimal new comparison, with an explicit candidate estimator

Start with a CPU spatial-filter question and a small neural mechanism check. Do not create a large architecture tournament.

For each class c, let S_c be the source mean of normalized trial covariance matrices, and T_c the corresponding mean from the current labeled support prefix. Define

- v_c = sum_i ||C_ic − T_c||_F² / [n_c(n_c−1)], for n_c ≥ 2;
- d_c² = ||T_c − S_c||_F²;
- alpha_c = max(0, 1 − v_c / d_c²) when d_c² > 0, and 0 when d_c² = 0;
- adapted covariance = (1 − alpha_c) S_c + alpha_c T_c.

Here alpha is the target weight. The variance estimate is for the **mean** covariance, not the variance of one trial. For a missing class or n_c<2, retain the source estimate for that class and record the condition. Use the same deterministic SPD regularization, CSP component count, covariance convention, feature scaling and classifier estimation for all new covariance-family arms. Preserve the explicit zero-difference case and report it; no hidden query-dependent fallback. The implementation uses exact nonpositive-difference fallback rather than an undocumented epsilon change.

This is an empirical bias–variance rule motivated by shrinkage. Source covariance itself is estimated from finite data; serial dependence, nonstationarity and a noisy source invalidate a blanket optimality or negative-transfer guarantee. Do not describe alpha as learned physiological reliability. A source-only or noisy-support fallback is a stated algorithm behavior, not an automatic retry.

The final classical family has eight arms in `experiments/hpc_recalibration_v2/hpc_recalibration/classical.py`:

| Method ID | Role |
|---|---|
| `frozen` | Frozen source CSP/LDA reference. |
| `lda_only` | Source CSP retained; LDA recalibrated on source plus current support. |
| `full_csp` | Classwise trial covariances pooled from source plus support; CSP/LDA refitted in the same V2 implementation. |
| `ea_csp` | Source-only and current-support-only EA references, followed by pooled CSP/LDA refitting; the main strong comparator. |
| `anchored_csp` | Unaligned source anchoring with a fixed tau rule, target weight n_support/(n_support+tau); regularization-strength control. Tau is fixed, while weight varies with support count. |
| `empirical_anchored_csp` | The classwise support-noise rule without EA; alignment ablation. |
| `ea_anchored_csp` | The same EA references as the principal candidate, followed by fixed-tau anchoring; matched alignment, nonadaptive update-strength control. |
| `ea_empirical_anchored_csp` | Support-only EA followed by the same classwise support-noise rule; the principal candidate. |

For all three EA arms, S_c and T_c in the formula are computed after separate source and support whitening. The target reference uses the current support prefix only. Every updating arm fits LDA using the source-plus-support labels, so this comparison changes covariance estimation while retaining classifier fitting information. The candidate versus `ea_anchored_csp` contrast isolates the adaptive versus fixed-tau update-weight rule at matched EA and budget. Candidate versus `empirical_anchored_csp` isolates alignment. Candidate versus unaligned `anchored_csp` changes both factors and is not a single-factor ablation. Across budgets the fixed-tau weight changes deterministically with available support count; within a fixed budget it is nonadaptive to observed covariance noise.

The new pooled full comparator shares the new family's implementation. It is **not an exact reproduction of the historical MNE estimator**, and does not inherit the +7.42 pp result. Historical saved predictions remain a separately labeled reference. A primary candidate-versus-EA difference tests the complete anchoring addition, while covariance/feature diagnostics provide descriptive interpretation rather than proving a unique causal mechanism.

The neural check comprises frozen, head-only, full update and L2-SP, sharing one **new V2** source initialization per participant/seed. The pure-PyTorch CompactEEGNet architecture is incompatible with the old accepted model state dictionaries: this version does **not** load or reuse those 54 weights. They remain unchanged historical models and frozen results. Changes to architecture and implementation are explicit in the new experiment identity rather than presented as a restart of the old source fits.

The compact initial scope is the six historical development participants (sub-1/4/7/10/13/16), with **three new seeds 20261023/20261024/20261025**: 18 new V2 source fits and six participant-level classical tasks. Budgets are chronological prefixes 4/8/12/16/20, with the 20 cap using the actual 19 or 20 eligible labels. All smaller budgets use the same query set. Neural tasks also contain support-adaptation fits; “18 source fits” is not a count of all optimizer runs. Frozen, head-only, full and L2-SP results reuse each new source checkpoint, and completed support updates/evaluation shards can be resumed independently.

Fixed, documented BN behavior and support-only optimization/epoch rules must be identical where appropriate; the query must not select an epoch, seed or regularization strength. All seeds contribute to a participant endpoint. Record parameter displacement and prediction collapse; neither measure establishes human skill retention. These six participants' outcomes were previously seen, so every V2 development comparison is exploratory.

**Pooled-source pretraining:** scientifically useful because 40 within-person source examples produced weak old neural models, but it changes the source-label budget and participant-transfer problem. Treat it as a separate later budget axis, using participant-isolated pretraining and a shared saved source checkpoint. Do not add it to this first core comparison or compare it to the old 54 models as if only the update rule changed. An additional architecture is lower priority than the independent cohort and the strong EA control.

## 5. External cohorts: exact opportunities and limits

### BNCI2014_001: proposed first external whole-run replication

**Status: protocol proposal for a separate data-preparation stage; this delivery has no executable external-data adapter and no external query result.** The [official six-page description](https://bnci-horizon-2020.eu/database/data-sets/001-2014/description.pdf) confirms nine participants, two days, six runs per session, 48 four-class trials/run, 22 EEG channels plus three EOG, and 250 Hz. Restricting to left/right gives 24 trials/run before data exclusions. The original cue indicates a four-second MI interval with no online feedback. Runs are separated by missing-value sections; split by events before filtering so those separators are not treated as signal. EOG is excluded from decoding. The [official dataset page](https://bnci-horizon-2020.eu/database/data-sets) lists **CC BY-ND 4.0**: retain original licensing and do not redistribute transformed EEG under the project's CC BY license.

Proposed new external roles, using chronological one-based run numbers: source session runs 1–4 for source fitting, run 5 for source validation, run 6 for source-only evaluation; target session run 1 for support, runs 2–6 for query. Retain target support prefixes 4/8/12/16/20, all from the same first run, and the same complete query runs for every budget. Source-budget and validation counts differ from Kumar; disclose them. The original competition document describes hidden evaluation labels; the current chosen official release/adapter must supply and map released labels once during dataset preparation. Do not infer labels from event 783 or silently substitute another session.

This is a genuine independent cohort only if project personnel have not already used its outcomes for selection. Nine additional participants improve cross-dataset evidence but do not solve low statistical precision or establish a six-session longitudinal claim. Do not pool nine and eighteen participants as one homogeneous primary cohort.

### Lee2019/OpenBMI: proposed larger, separately specified external validation

**Status: later external-validation proposal, not a configured or executable task in the initial V2 queue.** The original paper is [GigaScience 2019, 8(5):giz002](https://doi.org/10.1093/gigascience/giz002), **not Scientific Data**. Its Methods/Data Records were read: 54 participants on two days, 62 EEG plus four EMG channels, 1000 Hz, with a four-second MI task. The [official dataset DOI metadata](https://api.datacite.org/dois/10.5524/100542) explicitly confirms **CC0 1.0**. OpenBMI toolbox GPL-3.0 is a code license and should not be confused with these data rights.

The [current MOABB Lee2019_MI documentation](https://moabb.neurotechx.com/docs/generated/moabb.datasets.Lee2019_MI.html) says the MI online test run lacks labels and is excluded by default. The usual accessible labeled offline block contains 100 trials per session, rather than several independent labeled runs. Therefore do not assume 200 labeled trials/session or describe an 80/20 split of that block as whole-run isolation.

A separate chronological-block proposal is source-session first 80 trials for source fit and last 20 for validation; target first 20 for support and last 80 for query. All smaller support budgets still query the same last 80, with no future balancing of the prefix. This has no additional held-out source query and a different temporal-dependence structure from Kumar/BNCI, both of which must be explicit. Freeze electrode identities, task-relative window, source split and exclusions from metadata before evaluating outcomes. Download only the MI files needed, not the entire multi-paradigm archive. Verify the actually downloaded version once; a search-result NEMAR version is not a frozen manifest.

The 54-person cohort is a stronger precision extension, while its two sessions cannot verify longitudinal learning. A later genuinely longitudinal cohort such as that used by Wimpff et al. addresses a different question and is outside this minimal first implementation.

## 6. One scientific freeze and participant-level analysis

Before the first new external query, create one scientific configuration snapshot containing dataset/release and participant identities, chronological roles, channels/units/filter/window, source and target budgets, classifier/covariance definitions, method settings, seeds, epochs/stopping, BN policy, primary contrast and analysis code. The runtime configuration and hashes should record this once. Restarting an unchanged job uses the saved snapshot and checkpoint; it should not repeat scientific approval, full downloads or full-library scanning. A scientifically changed configuration gets a new experiment version.

The V2 principal contrast is **`ea_empirical_anchored_csp` minus `ea_csp` at the 20-label cap**, using participant-level BA differences. In Kumar this cap means the actual 19/20 labels and the six-participant result is exploratory. Carry this same declared contrast into a separately frozen external cohort, rather than promoting the best development contrast afterward. EA plus fixed-tau anchoring, unaligned empirical anchoring, full versus frozen, other budgets, neural head/full/L2-SP and downside distributions are secondary or ablation results. The unaligned fixed-tau arm is a further reference, not the single-factor fixed-weight control for the aligned candidate. Keep historical Kumar primary/secondary labels unchanged.

For the delivered Kumar queue, compute BA from the pooled eligible query trials within each target session, average all declared seeds within participant/session, then weight the five target sessions equally for that participant. Query runs are kept whole for splitting; they are not separate statistical participants or separately equally weighted endpoints. Compare participants after this aggregation. Preserve undefined BA where a query lacks a class and report missing tasks, seeds, sessions and class counts. Do not resample trials as independent participants, fill a support prefix using future labels, or drop a weak source participant after seeing target performance. External-cohort aggregation must be declared with its distinct session structure before evaluation.

Report the paired mean and 95% participant-bootstrap interval (10,000 resamples with fixed analysis seed), all individual changes, fraction decreasing, decrease magnitude and collapse counts. For the nine-person replication, also show every participant and recognize interval instability; exact paired sign-permutation inference, if included, belongs in the single frozen analysis rather than being added when bootstrap results are disappointing. Budget curves use pointwise intervals and do not identify a best operating budget. A prespecified −5 pp descriptive decrease threshold can distinguish visible losses from tiny numerical signs, but is not a clinical harm threshold. Any claim of downside reduction needs its own paired participant-level uncertainty.

CSP subspace angle, alpha and covariance deviation, plus neural update norm, can describe mechanisms. Associations computed on previously seen outcomes remain exploratory. A query-trained predictor of when to update is not part of this extension. No new gate is justified by the saved near-chance probes or failed Ridge selector.

## 7. Immediate work and scientific exit criteria

1. Integrate/read the already saved budget, phase and failed-operation gain evidence without rerunning them. Maintain original and exploratory intervals separately.
2. Use the implemented eight-arm covariance family and four neural update positions in the separate HPC version after relevant software tests: the first real scientific queue is **18 new source fits plus six classical development tasks**, with independently saved adaptation/evaluation work. Old 54-model weights are not reused by this incompatible V2 architecture.
3. Stage external data separately and implement the external adapter before claiming BNCI/Lee commands are executable. Prepare and inspect the source/support/query metadata once and lock the external protocol before query exposure. A100 execution remains unverified until a real allocated-node forward/backward/save/resume smoke check is recorded.
4. Run the independent tasks with checkpoint reuse; numerical/data failures remain failed cells with their traceback, while network progress-sync failure does not halt scientific computation.
5. Publish all planned results, including a failure of the candidate to beat full update or EA. Decide whether the larger Lee replication is warranted by scientific scope and precision, not by searching for a dataset that reverses an unfavorable finding.

A credible improved paper would combine clear matched-label evidence, a transparent update-strength rule, a strong alignment control, independent cohort evaluation and realistic uncertainty. If the candidate fails externally, the work can still provide a useful limit on low-label adaptation; it should not be rewritten as a successful new task-aware algorithm. This document adds no results to the submitted manuscript and makes no submission or journal-acceptance claim.
