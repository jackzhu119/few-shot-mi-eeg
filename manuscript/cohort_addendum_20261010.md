---
status: exploratory_computation_complete_source_repetition_verified_sensitivity_complete
evidence_date: 2026-10-10
documentation_completed: 2026-10-11
EEG_participant_selection: first_ten_published_NETBCI_IDs
EEG_source_independence: exact_cross_identity_repetition_detected
separate_source_audit_sensitivity_n: 8
synthetic_results_included: false
human_learning_preservation_demonstrated: false
---

# Ten-ID NETBCI expansion: manuscript addendum

This addendum documents the exploratory expansion of the single-participant feasibility study. The historical pilot retains its original analysis partitions and numerical results. The expanded study reruns every selected identity, including the pilot identity, under a common cohort protocol. The two result sets should not be combined as if they used the same query or quality-screening partitions. Saved-table arithmetic has been independently reviewed, and the completed 240-run numerical audit establishes exact EEG repetition across sessions and published identities. The original ten-ID EEG statistics are preserved computational descriptions; their bootstrap intervals do not support inference from ten independent participants. A separate, completed eight-ID sensitivity excludes both identities involved in the cross-identity repetition, without refitting models or modifying the original outputs.

## Methods to incorporate into the cohort manuscript

### Scope, selection and evidence timing

We selected the first ten published participant identifiers, `sub-1` through `sub-10`, from the NEMAR `nm000305` v1.0.0 EDF/BIDS derivative of NETBCI. Selection did not depend on behavioural improvement, EEG measures or decoder success. The single-participant pilot and the 19-participant released behaviour table had already been observed when the expansion protocol was saved. This was therefore an exploratory expansion following a pilot, rather than an independent preregistered confirmation. The original Dataverse v2.2 behaviour source and the NEMAR derivative were kept distinct. Source provenance and verified original-header hashes supported the metadata participant mapping, but did not establish independent signal contents. The analysis did not combine original BrainVision signals, MEG or MRI with the derivative EEG.

At continuation, historical data-audit receipts existed but the active execution environment lacked the original signal files. Required files were restored from the same official version and manifests, preserving historical artifacts and reauditing the current bytes. Storage-path changes were recorded separately from scientific parameters. The source and transformed-data receipts preserve participant, session, run, source path, event-table row, semantic label, onset, duration and sample boundaries.

### Post-observation eligibility for fixed-duration inputs

A strict audit failed when one selected participant contained a shorter event. A source-event duration census identified a real 2.968-s rest event. Before any new cohort model fitting, we adopted and recorded an explicit fixed-duration input rule: retain every event in the source inventory, but exclude an event from the fixed 5-s tensor if it does not provide the specified window. The shorter event was retained with its source identity and exclusion reason; the participant remained in the cohort. No samples were padded, appended from later recording time, or synthesized. The initial strict-audit failure and the preceding configuration snapshot were preserved.

This eligibility choice followed observation of event duration and was not part of the original expansion protocol. It must be disclosed as an exploratory adapter decision. Spectral, model, geometry, matching and inferential parameters were unchanged. Source-event counts and eligible tensor counts are reported separately, rather than calling all released events five-second epochs.

### Source-frozen analysis and metric availability

For each participant, session 01 runs 01–04 supplied the fitting set and runs 05–06 supplied a disjoint reference-session query. All six runs in sessions 02–04 supplied later queries. Session 02 was a validation descriptor without hyperparameter selection; sessions 03–04 were exploratory tests. Quality thresholds, scaling, reference PCA, CSP and LDA were fitted only to the participant's source partition. Session-specific PCA was used only for descriptive subspace comparisons, not for predictive alignment or model selection. The cohort protocol did not train new EEGNet models or implement adaptation policies.

Analyses used the audited common EEG channels and sampling frequency, common-average reference, task-window cropping to `[0.5,4.5)` s, and the specified C3/Cz/C4 mu (8–13 Hz) and beta (13–30 Hz) bands. Trial log10 ROI powers were averaged separately within each class/run and then equally across prescribed runs. Ten times the difference between imagery and rest means is a task-window dB contrast. Absolute arithmetic powers were saved separately. These contrasts lack a verified prestimulus baseline and are not baseline-normalized ERD or isolated imagery responses.

Geometry used the fixed CAR-compatible Helmert coordinates, epoch-wise fourth-order zero-phase 8–30-Hz filtering, trace-normalized covariances with 0.05 shrinkage, and ten-component spectral-feature PCA. Primary matching sampled 12 events per class/run across six runs, giving 144 events per session and repetition; the preset quality sensitivity used unflagged events from common runs 03–06, giving 96. Ten fixed matching repetitions were summarized within each participant. If a required cell was too small, the variant was marked unavailable for that participant; the sample size, quality rule and seed set were not relaxed.

The fixed baseline was four-component CSP followed by shrinkage LDA. Model state, fitting identities and unchanged query-time hashes were checked. Constant predictions and other scientific failures were retained. Source-fitted coarse quality flags remained in primary analyses; unflagged samples were not certified artifact-free.

Complete published-ID trajectories were resampled 10,000 times with seed 42. Last-minus-first changes were computed within identity before resampling. Session summaries and paired changes report the number of available identities for each metric. Unavailable observations are not zero-filled. After the completed numerical audit, the original ten-ID EEG intervals must be read as arithmetic published-ID bootstrap summaries, not independent-participant population intervals. Five hundred run-bootstrap repetitions per identity supply conditional uncertainty for that particular frozen model and available runs. Matching repetitions, runs, trials and sessions do not increase the independent participant count. The separately saved eight-ID source-audit sensitivity uses the same estimators and seed; it remains post-observation and exploratory.

### Behavioural linkage

The original source provides 19 participants' four sessions, each containing six reported target-hit percentages. The EEG-linked analysis concerns only the ten selected participants. The session score is the unweighted mean of those six percentages and does not require a score-vector-to-EEG-run ordering assumption. It is not a pooled success probability with a verified denominator. Score-run order, scoring exclusions, trial outcomes and decoder-version logs remain unresolved. No percentages or classifications were converted into hit/miss labels, and session scores were not broadcast to EEG trials.

## Results

### Verified source and eligible-event flow

All ten published participant identities passed the source-integrity and structural real-signal audit, comprising 40 sessions and 240 runs. This did not yet establish recording independence. The source inventory contained 7,577 events (3,794 right-hand imagery and 3,783 rest); the eligible fixed-duration tensors contained 7,576 epochs (3,794 imagery and 3,782 rest). The sole excluded event was participant `sub-3`, session 01/run 03, event-table row 31: rest, onset 224.032 s, sample 56,008, duration 2.968 s, and 742 actual samples. It remained in the source inventory and exclusion evidence. This identity contributed 764 eligible epochs across all sessions and remained in every applicable cohort summary.

All derivative recordings shared the same 74-channel order, 250-Hz sampling and volt units. No participant-specific channel selection or reordering was performed. The 240 original headers were hash-verified; original header rates included approximately 249.9, 250 and 1,000 Hz, so the exported rate was not treated as the original rate in every recording. The audit establishes source identity and usable derivative structure, not artifact-free epochs or validation of all 19 published participants and all modalities.

Participant-level source counts and eligible counts were respectively 717/717, 767/767, 765/764, 768/768, 765/765, 768/768, 726/726, 766/766, 767/767 and 768/768 for identifiers 1–10. The complete participant/session flow is in the [cohort scientific report](../docs/netbci_cohort_results_20261010.md) and [final cohort audit](../research_logs/netbci_cohort_resume_20261010/audits_full_windows/cohort_audit.json).

### Numerical longitudinal findings

The ten published identities contributed complete four-session query records. Their source fitting counts were 120, 128, 126, 128, 127, 128, 119, 128, 128 and 128; reference-session query counts were 60, 64, 64, 64, 64, 64, 59, 63, 64 and 64. Later queries included every eligible event in their six runs. The source and query identities were disjoint at the event-ID level; the completed numerical audit nevertheless found source-training content repeated in later queries for identity 7. The complete per-identity query and QC counts are available in the [cohort scientific report](../docs/netbci_cohort_results_20261010.md).

Online reported-score means across the selected identities were 54.535%, 57.448%, 64.731% and 68.803%. Every identity had a positive last-minus-first score difference. The paired mean difference was +14.268 percentage points (unadjusted participant-bootstrap 95% interval 10.085 to 18.291). This describes the released online training-period scores; it does not isolate human practice from the historical decoder and feedback changes.

Saved frozen CSP+LDA balanced-accuracy means were 68.676%, 63.642%, 60.432% and 56.103%. The paired change was −12.573 percentage points (published-ID arithmetic bootstrap interval −22.954 to −1.596); two identities increased and eight decreased. Seven queries from five identities yielded constant-class predictions: identity 1 in sessions 02–04, identity 2 in session 03, and identities 4, 5 and 7 in session 04. Six predicted rest and one predicted imagery. Each had 50% balanced accuracy, but a 50% score alone did not imply constant prediction; identity 10/session 04 predicted both classes. All 40 query computations completed. These are readout results conditional on the dataset as released; the verified cross-identity repetition precludes interpreting the original ten-ID EEG intervals as independent-participant inference.

Mean mu task-window contrasts were −0.470, −0.571, −0.785 and −0.880 dB. The paired change was −0.410 dB (−1.168 to 0.492), with five increases and five decreases. Mean beta contrasts were −0.316, −0.376, −0.443 and −0.414 dB; the change was −0.098 dB (−0.546 to 0.385). This expansion does not show a uniform task-power contrast direction. Absolute arithmetic mu power means in rest were 5.600, 5.836, 9.449 and 5.917 µV²; imagery means were 4.792, 4.172, 8.355 and 4.812 µV². Mean and median differed substantially in session 03. Neither a more negative contrast nor increased absolute power was predefined as neural skill acquisition.

The primary analysis retained 75 quality-flagged epochs, leaving 7,501 unflagged eligible epochs. The flags were concentrated in identity 1/session 04 (43/178) and identity 8/session 01 (18/191). Six-run matching was computable for all ten identities; the preset QC four-run variant was computable for nine. Identity 8/session 01 had only 11 unflagged rest trials in run 05 and eight in run 06, below the requirement of 12. Its entire QC matched variant was marked unavailable without lowering the count or removing the identity from other analyses.

The six-run matched mean AIRM distance to session 01 was approximately zero, 5.569, 7.222 and 7.471; within-session run AIRM means were 4.635, 4.100, 2.938 and 2.691. Matched PCA subspace means were approximately zero, 0.605, 0.623 and 0.642. Session-04 AIRM was 7.471 (6.218 to 8.625) and PCA distance 0.642 (0.601 to 0.685). The QC four-run estimates, with nine available identities, were 7.121 (5.877 to 8.263) and 0.663 (0.624 to 0.698), respectively. Differences between these summaries mix run selection and availability; they are not estimated causal QC effects.

### Exploratory associations and computational reproducibility

Five paired-identity associations were estimated after a separate estimator plan was saved. All had ten complete pairs and 10,000 valid paired-bootstrap draws, seed 42. The following intervals are unadjusted for multiplicity and are arithmetic bootstrap summaries of the published identity set. Exact EEG repetition violates the independent-participant interpretation of these original intervals.

| Association | Pearson r [95% interval] | Spearman ρ [95% interval] |
| --- | --- | --- |
| BA change versus online-score change | 0.424 [−0.050, 0.777] | 0.394 [−0.333, 0.852] |
| Mu-contrast change versus online-score change | −0.412 [−0.876, −0.014] | −0.479 [−0.764, 0.176] |
| Mu-contrast change versus BA change | −0.727 [−0.933, −0.355] | −0.721 [−0.962, −0.152] |
| Session-04 AIRM to session 01 versus BA change | −0.624 [−0.931, 0.331] | −0.503 [−0.925, 0.291] |
| Session-04 PCA distance versus BA change | 0.020 [−0.651, 0.666] | 0.164 [−0.686, 0.796] |

These are exploratory associations rather than confirmatory H2 tests, and endpoint selection, small sample size and source repetition prevent a mechanistic interpretation. There were no p values or multiplicity corrections. A complete refit and feature recomputation for identity 3 reproduced all 16 stable output artifacts byte for byte, including model, predictions, spectra, geometry and partitions. Timing receipts were excluded from that equality check. This validates computational determinism for one identity, not a second fit of all ten identities or independent biological replication.

### Completed numerical source-independence audit

The exact numerical audit covered all 240 continuous EDF runs and all 7,577 actual source task windows, including the one short event. It found six four-member continuous-run duplicate groups: for each corresponding run 01–06, identity 7/sessions 01, 02 and 03 and identity 1/session 04 returned identical numerical arrays over the validated channel order. These groups contain 24 run records. At the task-window level, 178 four-member groups contain 712 event records, with no conflicting labels. The audit found 222 unique continuous numerical fingerprints and 7,043 unique source-window fingerprints. It assessed exact equality; different fingerprints do not rule out near similarity or verify true participant identity.

For identity 7, each of sessions 02 and 03 contained 119 later-query windows repeating source-training content and 59 repeating reference-session query content. This gives 238 source-training-to-later-query repetitions and 118 reference-query-to-later-query repetitions despite distinct event IDs. Those later-session scores therefore do not establish independent cross-session generalization. Identical spectra and near-zero geometry in these records do not establish neural stability.

All 240 EDF files were rehashed and matched the cached official root and per-subject manifests. In each duplicate run group, identity 7/sessions 01–03 share the same whole-file checksum, as explicitly declared by the official manifests; identity 1/session 04 has a different file checksum but the same returned numerical signal. The repetition is therefore not explained by a local recovery file failing the pinned official checksum. Original BrainVision EEG signals were not read for this comparison. Distinct verified original-header metadata does not identify the correct signal assignment or the cause of the derivative repetition. We retain the source files and original ten-ID outputs unchanged and make no acquisition, conversion or biological explanation for the copies.

This EEG finding does not change the separately verified 19-participant released behavioural table or its arithmetic. Behavioural scores alone cannot repair the EEG provenance or determine which repeated recording belongs to which identity.

### Separate eight-ID source-audit sensitivity

A completed, separately saved sensitivity excludes both identities 1 and 7 because both occur in the exact cross-identity continuous-signal duplicate groups and the correct assignment is unknown. It retains identities 2, 3, 4, 5, 6, 8, 9 and 10 (eight complete trajectories). Selection followed the source audit after outcomes had been computed; it was based on copies, not favourable or unfavourable outcomes. The analysis reused the saved per-identity outputs without refitting, changing endpoints, or overwriting the original ten-ID analysis. The same paired-trajectory bootstrap used 10,000 draws and seed 42.

| Session-04 minus session-01 endpoint | Eight-ID mean change [exploratory 95% bootstrap interval] |
| --- | --- |
| Frozen CSP+LDA balanced accuracy | −9.502 percentage points [−20.244, 2.735] |
| Mu task-window MI-minus-rest contrast | −0.679 dB [−1.317, −0.047] |
| Beta task-window MI-minus-rest contrast | −0.167 dB [−0.654, 0.381] |
| Released online score | +14.371 percentage points [9.189, 19.325] |

The BA interval now includes zero, whereas the mu-contrast interval no longer does; the beta interval includes zero. These shifts show the summaries' dependence on the source records, not confirmation of a mechanism or human learning. In the same eight-ID sensitivity, the Pearson association of BA change with score change was 0.438 [−0.299, 0.888], and that of mu-contrast change with score change was −0.538 [−0.935, 0.213]. The mu-change/BA-change Pearson estimate was −0.619 [−0.941, −0.203], while its Spearman estimate was −0.619 [−0.973, 0.140]. Both estimators' geometry/BA-change intervals included zero. These unadjusted associations remain small-sample, post-observation descriptions. No exact copies were detected among the eight retained identities, but true participant independence, measurement reliability and causal learning remain unverified; this sensitivity is not independent confirmation.

## Discussion and limitations to carry forward

The expansion describes the pilot's patterns across the released identity set and the preset metric and quality sensitivities. The verified source repetitions constrain any claim that those patterns recur across independent people; the eight-ID source-audit sensitivity documents dependence on the affected records. Neither analysis isolates human practice from changing historical online mappings, sensory feedback, strategy, fatigue or acquisition differences. Increased online scores, altered task power, changed covariance and a failing old classifier refer to different mappings and samples and must be reported as separate endpoints. No assumed beneficial direction is assigned to representation stability or drift.

Constant-class predictions identify a frozen-readout failure. They do not establish absent task information or loss of human control skill. Likewise, a nonzero covariance or subspace distance does not identify neural learning. Within-session run distances are descriptive benchmarks; they are not a formal split-half reliability analysis, a measurement-error model, or biological replication. The first-ten-ID sample is not a random population sample and contains verified repeated EEG; the eight-ID sensitivity does not establish adequate power or independent source validation for a high-level causal or clinical claim.

H1, that representations and performance need not move together, remains a falsifiable question informed by the separate endpoints. The saved H2 associations require independent EEG source validation before scientific inference; they are not confirmation of representation drift as a learning mechanism. The cohort observations do not test H3/H4 about competing adaptation policies or preserved human skill because no policy was assigned and no controlled assistance-withdrawal or delayed-retention endpoint was recorded.

The next methodological priorities are sufficiently evaluated source-only baselines, independent task-information measurements, and artifact/reference/reliability controls. A causal learning-preservation claim would require matched online conditions, reliable update and behavioural logs, and independent human task probes. Retention under the mapping learned at the end of training must be distinguished from transfer back to the initial reference mapping. Increasing the EEG sample, using CSP/PCA/Riemannian distances, or borrowing ideas from the three audited Nature studies does not itself constitute a validated new algorithm.

## Evidence

- [Expansion protocol](../docs/netbci_cohort_expansion_protocol.md) and [final full-window configuration](../configs/netbci_cohort_full_windows_20261010.json).
- [Continuation receipt](../research_logs/netbci_cohort_resume_20261010/resume_plan.json), [eligibility decision](../research_logs/netbci_cohort_resume_20261010/full_window_policy_decision.json), and [configuration timing correction](../research_logs/netbci_cohort_resume_20261010/full_window_policy_finalization.json).
- [Cohort scientific report](../docs/netbci_cohort_results_20261010.md), [saved summary receipt](../research_logs/netbci_cohort_resume_20261010/summary_run01/summary_receipt.json), [association receipt](../research_logs/netbci_cohort_resume_20261010/associations_run01/association_receipt.json), and [independent saved-table review](../research_logs/netbci_cohort_resume_20261010/independent_review.json).
- [Completed 240-run numerical identity audit](../research_logs/netbci_cohort_resume_20261010/numeric_signal_identity.json) and [official-manifest confirmation](../research_logs/netbci_cohort_resume_20261010/numeric_signal_identity_official_manifest_confirmation.json).
- [Eight-ID sensitivity summary](../research_logs/netbci_cohort_resume_20261010/independence_sensitivity_run01/sensitivity_summary.json), [paired changes](../research_logs/netbci_cohort_resume_20261010/independence_sensitivity_run01/cohort_paired_changes.tsv), [associations](../research_logs/netbci_cohort_resume_20261010/independence_sensitivity_run01/association_estimates.tsv), and [provenance receipt](../research_logs/netbci_cohort_resume_20261010/independence_sensitivity_run01/sensitivity_receipt.json).
- [One-identity computational replay](../research_logs/netbci_cohort_resume_20261010/computational_replay_sub3.json), [editable executed notebook](../notebooks/netbci2026_cohort_20261010.ipynb), and [HTML reading copy](../notebooks/netbci2026_cohort_20261010.html). The saved-table review did not load raw EEG arrays and cannot replace the separate signal-independence audit.
- [Historical single-participant manuscript](longitudinal_eeg_working_draft.md) and [19-participant behavioural source analysis](../docs/netbci_behavior_session_analysis.md), retained at their original scope.
