# Main-manuscript targeted prose revision

Reviewed source: `origin/main` at `19a5909fd76d96be9316559602010932ccec81a8`, `manuscript/kumar_plos_one_submission_draft_innovation_20261017.md`.

The parent subsequently authorized edits to that file and its matching `Sources/` copy. Both have now been edited. No other repository files were changed by this agent. Exact original/replacement blocks are in `main_prose_changes.json`; the human-readable unified diff is `main_prose_changes.diff`.

## Applied changes

1. Abstract: added the saved secondary all-18 contrasts, full minus LDA-only +3.26 percentage points and full minus frozen +6.03. Abstract is 266 whitespace-delimited words. Primary n=12 findings and their uncertainty remain unchanged.
2. Participant partition: stated the every-third-ID development allocation, reliability/pipeline purpose, and shared fixed CSP/LDA configuration. Did not introduce the reviewer's unsupported claim of an untouched confirmatory primary test.
3. Frozen EEGNet: clarified the source-only reference role and the extra target fine-tuning choices outside the chosen spatial-filter/classifier comparison. The source-validation budget remains explicit.
4. Statistical terminology: changed post-review to post-hoc exploratory/supplementary exact sign-flip wording. Preserved the full four-test family, every p value and both n=12 and n=10 denominators. Explained participant resampling versus a sign-symmetric null and family adjustment without claiming that overlap itself proves an overly conservative correction.
5. Reliability methods/results: expanded definitions of all three low-dimensional probes plus the supervised CSP/LDA probe, the 6 × 2 × 20 = 240 fitted pipelines, and the four-dimensional support-cosine and signed-score measurements. Rounded only the two requested prose summaries, not table values or underlying output.
6. Heterogeneity discussion: added all-18 results and the real sub-7/session-2 component loss of 37.50 points; added the unweighted 40-to-19/20 source/support union and alternative covariance weighting/alignment directions. Spatial disruption versus shifted task patterns are hypotheses, not experimentally identified mechanisms.
7. Scope: expanded the requested cue/phase, offline filtering, sample-weighting, and cohort/reference dimensions. Described the amplitude sensitivity without attributing large amplitudes to visual or ocular sources. Preserved exploratory exposure history, participant inference, and neural budget differences.
8. Removed exactly six repeated AI-assistance sentences from figure captions. Preserved the single central AI-assistance and verification disclosure unchanged.
9. Changed exactly seven comparison-label separators in Tables 5 and 6 from U+2212 to U+2013, leaving numeric negative signs and every table number unchanged.

## Review-text corrections grounded in existing sources

- Mu power is **8–13 Hz**, not the suggested 8–12 Hz. S1 Text, S2 defines the integration bands.
- Covariance drift is target-query **mean per-epoch Riemannian distance to the SOURCE40 reference minus the corresponding source-query mean**. It is not the distance between two query-set covariance matrices.
- The reported 0.295325 support-half cosine uses **SOURCE40-standardized four-dimensional CSP log-power features**, not 44-dimensional power. S1 Text, S5.3 gives the transformations.
- The three low-dimensional probes are standardized power44, PCA4 and C3/Cz/C4 motor-band6. Supervised CSP/LDA is a fourth probe. They use the same two source-run folds but distinct representations.
- The 240 count enumerates model fits for the training-label rotations. Held-out label rotations add scoring combinations, not further model fits.
- The two double-negative sessions have cosines approximately 0.191 and 0.850, so both cannot be described as having high internal agreement.
- The 21.1% amplitude-flag prevalence does not identify visual or ocular artifact sources.
- The reviewer-suggested confirmatory/no-primary-access history was not added. The current protocols retain previous test exposure.
- Holm controls familywise error under arbitrary dependence; the overlap alone does not establish that the observed correction is overly conservative. No unmeasured skewness of participant gains was asserted.

## Verification

- All Markdown table rows match the originals after normalizing only the seven requested comparison-label separators.
- All citation keys remain in the original order; no reference was added or deleted by this agent.
- Ethics, data/code availability, author material and the complete Conclusions section were left unchanged for the parent to handle ethics consistently.
- The central AI disclosure remains byte-for-byte unchanged.
- Sources copy equals the edited canonical main source byte-for-byte before the parent's ethics changes.
- Every change can be reconstructed by applying the 23 mapped replacements to the original source.
- Main scientific source SHA256 at handoff: `a21b868b825defa4fee3e7bc0dfa892bbadc160b44f209f9253f5cea02ee5792`.

This work read saved tables and text only. It did not run a model, read new query EEG, train, alter results, or create a scientific experiment. Document exports, ethics consistency, bibliography formatting, Figure 4, package synchronization and Git publication remain with the parent and other assigned agents.
