# Related work and the added-value question

Checked on 3 November 2026 (America/Los_Angeles); retrieval timestamps use UTC on 4 November. This note supports the isolated Paper2 extension based on `da2a3acee24746981bbcdd779ab88132da6e24c4`. It records prior art and manuscript requirements; it does not report a new experiment.

## What Euclidean alignment already established

He and Wu introduced Euclidean alignment (EA) in *Transfer learning for brain–computer interfaces: a Euclidean space data alignment approach*, DOI [10.1109/TBME.2019.2913914](https://doi.org/10.1109/TBME.2019.2913914). The article appeared online in 2019 and in the February 2020 issue, 67(2):399–410. The existing `he2020alignment` bibliography entry is therefore correctly dated by its journal issue. The full 12-page [author-hosted journal PDF](https://lab.bciml.cn/wp-content/uploads/2020/08/Transfer-Learning-for-Brain%E2%80%93Computer-Interfaces-A-Euclidean-Space-Data-Alignment-Approach.pdf) was obtained and read. The versioned [arXiv record](https://arxiv.org/abs/1808.05464v2) identifies the April 2019 author version; its complete PDF was also obtained. Source lengths, hashes and reading scopes are recorded in [SOURCE_RECEIPTS.json](../../research_logs/paper2_alignment_integrated_20261104/literature/SOURCE_RECEIPTS.json).

The original method estimates an arithmetic-mean covariance reference and applies its inverse square root to every trial in the corresponding domain (equations 10–12, journal pp401–402). The article explicitly evaluates EA followed by CSP and LDA. Its offline evaluation uses all available target trials for target-reference estimation, whereas its simulated online evaluation uses the target trials available at the calibration step. Section VI-B (p408) then combines the available labeled target trials with labeled auxiliary subjects to fit CSP and LDA. Limited target labels, source/target supervised fitting, and withholding future target signals from reference estimation are therefore already present in the EA literature.

The original study also compares arithmetic/geometric and imagery/resting reference choices (Section V-D), reports individual negative transfer, and evaluates calibration trajectories. Its MI experiments concern transfer between people using calibration recordings; the two recording days of BCI Competition IV 2a are not used as the source/target chronology of the present Paper2 comparison. Its published calibration simulation samples a starting position and can wrap the acquisition sequence. Paper2 instead fixes source-session and subsequent whole-run identities, resets each later session to the same source set, and separates its original development and primary cohorts.

The [official MATLAB repository](https://github.com/hehe03/EA/tree/c508ed812a126241e08f227e831cc294c0fc7579) was inspected at commit `c508ed812a126241e08f227e831cc294c0fc7579`. All four files were read. `main_MI.m` implements the offline leave-one-subject-out setting and estimates each target reference from that subject's complete trial set. The simulated-online procedure is supported by the article, not by an unseen online routine in this repository. No license file or GitHub license declaration was present. The code was read to verify the method; no MATLAB source was copied into Paper2. Its reference equations can be implemented independently with the published method citation. [Code provenance](../../research_logs/paper2_alignment_integrated_20261104/literature/EA_OFFICIAL_CODE_RECEIPT.json) records every inspected blob.

## The Paper2 question

The useful question is the incremental value of alignment **after full supervised spatial refitting has already received the same calibration information**. The four existing Paper2 pipelines provide a sequence of operational comparisons: frozen source CSP/LDA; LDA refitted with source and current support while source CSP remains fixed; CSP and LDA refitted with that same union; and domain-specific EA followed by CSP/LDA fitted with the same union. Within each dataset, subsequent query identities are shared.

This design supports a focused empirical contribution: a longitudinal, participant-level account of the added EA branch under a short, fixed calibration run, with class-balanced corrected/introduced errors, left/right recall, weak-class coverage and the distribution of effects across sessions and budgets. It does not require a new name for EA or the claim that matched labels were absent from earlier EA comparisons.

| Topic | Established work | Contribution to develop with Paper2 evidence |
| --- | --- | --- |
| Arithmetic covariance whitening | EA equations and domain-specific references are established | State the exact source/support reference populations, coordinates and numerical treatment actually used |
| EA plus CSP/LDA | Explicitly evaluated by He and Wu | Quantify EA beyond a full-refit baseline using the same chronological support and query identities |
| Few labeled target trials | Included in the original simulated-online supervised setting | Explain the finite current-session label and signal budget rather than presenting few-shot EA as a new algorithm |
| Classifier versus spatial updates | Adaptive classifiers and spatial filters have a substantial literature | Compare LDA-only and full refitting before measuring the added EA branch, preserving the original endpoint hierarchy |
| Longitudinal use | Session variability and recalibration are already studied | Follow the same people across five target sessions with a fixed source-session reset and explicit whole-run partitions |
| Corrected and introduced errors | A paired binary-decision accounting identity | Locate the observed EA increment in actual common query decisions; do not present the identity itself as a methodological invention |
| Weak-class recall and recall gap | Established metrics with a direct algebraic relationship to BA | Recompute them at the correct session/seed level and show whether the same participants gain in both BA and weak-class recall |
| BNCI2014-001 | The dataset is already used in the original EA article and this project's other work | Evaluate a separately fixed two-day source/support/query protocol; do not count prior use of the same nine people as another independent sample |
| Budget and robustness | Calibration trajectories and reference sensitivity are established | Show all scheduled budgets and only the EA-specific QC/window/control analyses actually completed on matched observations |

The present literature check establishes these specific distinctions. It is not an exhaustive priority search proving that no earlier article combined any subset of them. Novelty statements should identify what this analysis measures, rather than assert an unsupported first-ever algorithm or benchmark.

## Observations, algebra and mechanism

An EA-minus-full BA difference is an observed pipeline contrast. The decomposition into corrected minus introduced class-balanced error mass reconstructs that contrast. For binary decisions, changed predictions equal corrected plus introduced mass. Weak-class recall satisfies `W = BA − H/2` when computed from the same two class recalls. These checks establish accounting consistency and resolve the distribution of benefit; they are not three independent confirmations of a physiological mechanism.

EA's reference covariance becomes identity by construction. That fact alone does not establish better class separation on later trials. Its empirical added value must come from later-query results using references fixed from source/support. A minimal RMS/diagonal/full-reference comparison can test a specific alternative explanation only when source/support/query, CSP/LDA implementation, coordinates and covariance rules remain matched. Covariance whitening, signal scaling and neural normalization should retain their distinct definitions.

The original Paper2 Kumar implementation and BNCI implementation differ in reference handling, window definition, source-label count and regularization. Dataset-to-dataset differences therefore describe the evaluated complete pipelines. A unified-core sensitivity can isolate an implementation change; it does not replace historical estimates. Paper2's zero-phase filtering also differs from the causal FIR used by He and Wu. A support-fixed reference is a valid information restriction within the offline experiment, not evidence of a fully causal deployed system.

## Contribution-led manuscript wording

Suggested research question:

> What does Euclidean alignment add when a longitudinal motor-imagery decoder has already refitted its spatial filters and classifier with the same short calibration run?

Suggested contribution statement, conditional on the accompanying audited outputs:

> We quantify the added value of Euclidean alignment under matched source, calibration and later-query identities, then trace the difference through class-balanced prediction transitions, weak-class recall and longitudinal participant effects.

Use completed numerical results from the structured Paper2 tables. Keep the original Kumar full-minus-frozen primary comparison, full-minus-LDA-only secondary comparison, exploratory EA extension, and the separately fixed BNCI primary/secondary roles intact. New recall/transition/probability summaries are additional descriptive analyses on existing predictions. They do not create new participants, a new holdout, or an independent replication of those same predictions.

A concise introduction can establish repeated calibration, distinguish classifier/spatial/alignment actions, describe the existing EA result, then state this incremental measurement question. The discussion can lead with the measured added EA branch and its class-level distribution, while one focused scope paragraph identifies prior exposure, implementation differences and the actual signal endpoint. This gives the positive evidence a clear role without removing relevant comparators or altering their statistical status.

## Current BMT format and disclosure check

The [BMT author guide](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Instructions%20for%20Authors.pdf) and both official Word templates were downloaded again. All three have the same SHA256 as the 29 October check. Guide pages 4 and 6–10 were inspected; both templates were read in full. The current [journal submission information](https://www.degruyterbrill.com/journal/key/bmte/html) still requires the separate Ethical and Legal Declarations Word and describes Tier 2 data sharing.

| Requirement | Current value or instruction |
| --- | --- |
| Research Article | At most 6000 words |
| Structured abstract | At most 200 words; Objectives, Methods, Results, Conclusions |
| Keywords | Three to six; alphabetical, lowercase, semicolon-separated |
| Figures and tables combined | At most eight |
| References | At most 35; Vancouver order of first citation |
| Running head | At most 75 characters including spaces |
| Tables and equations | Editable Word/LaTeX; not screenshots |
| Figures | Separate supported image files; at least 600 dpi for combined line/raster graphics; lettering at least 6 pt |
| Supplementary files | No more than 10 MB per file; publication-ready |
| Declarations | Separate Word file; must agree with the manuscript |
| Suggested reviewers | At least five, with name/institution/country/email; institutions different from every author's; international suggestions encouraged |
| Authorship | Actual substantive contribution, accountability and approval of the version submitted |

The research template includes a Conclusions section. Four or five focused figures plus two tables can fit the combined eight-item limit. Existing Matplotlib vector rendering and editable Word construction remain suitable; no generative artwork is needed.

The current [publisher AI policy](https://www.degruyterbrill.com/publishing/for-authors/author-policies/artificial-intelligence), displayed September 2026, requires disclosure when substantive tool output contributes to a manuscript or research methodology; it exempts simple proofreading/copy-editing. Code, manuscript preparation and analysis assistance should therefore remain factual in the designated disclosure. A consolidated disclosure can replace repeated tool mentions in the scientific narrative. The policy also rejects submissions described as AI-generated papers, assigns content responsibility to the human authors, and prohibits generative creation/manipulation of research data or experimental figures. Source-based numerical plotting is distinct from generating artificial experimental images.

This extension remains an author-review version until its new content is actually approved. The earlier approval belongs to the earlier manuscript. Existing national-law secondary-use ethics wording and original acquisition ethics references remain separate; this check creates no institutional ethics confirmation. No journal submission, reviewer contact, withdrawal or editorial-system change was performed.

## Evidence and reuse classification

- Published EA equations and pipeline definitions: **B, methodological reference**, implemented independently where needed; no third-party MATLAB copied.
- Existing Paper2 predictions and component estimates: **A, existing evidence**, to be replayed and expanded under the current analysis plan.
- Candidate mechanism experiments: **C only if actually fitted and evaluated** under a fixed plan; this literature audit executes none.
- He–Wu performance numbers, different-subject protocols and other-paper effects: **D/E, context only**, never inserted as new Paper2 observations.
- Complete source receipts and inspected local-file hashes: [literature evidence directory](../../research_logs/paper2_alignment_integrated_20261104/literature/).
