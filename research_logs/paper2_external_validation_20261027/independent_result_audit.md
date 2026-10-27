# Independent audit of the external four-arm replication

Execution: `457e7bdaad96e84782b6fe968f88925a1200c4b3`. PID 3020 ran from 2026-10-27T06:34:54.957215+00:00 to 2026-10-27T06:36:59.303326+00:00 and returned exit code 0.

**11,844 explicit checks passed; 0 failed.** The audit covered 9 participants, 36 saved prediction files, 1,080 unique target-query trials, 4,320 method-specific prediction rows and 180 run-level endpoints. No EEG arrays or model tensors were reopened, and no forward pass or fitting was performed.

## Recomputed results

| Method | Mean BA |
| --- | ---: |
| frozen | 70.555556% |
| lda_only | 71.666667% |
| full_csp | 71.851852% |
| ea_csp | 77.500000% |

| Contrast | Mean pp | Pointwise paired-bootstrap 95% interval | Exact two-sided p | Secondary Holm p |
| --- | ---: | --- | ---: | ---: |
| full_csp_minus_lda_only (primary) | +0.185185 | [-1.851852, 2.129630] | 0.96875000 | — |
| full_csp_minus_frozen (secondary) | +1.296296 | [-1.759259, 3.981481] | 0.45312500 | 0.68750000 |
| lda_only_minus_frozen (secondary) | +1.111111 | [-0.462963, 2.962963] | 0.34375000 | 0.68750000 |
| ea_csp_minus_full_csp (secondary) | +5.648148 | [3.148148, 8.703704] | 0.00390625 | 0.01171875 |

The fixed primary full-minus-LDA-only comparison gave a mean difference of +0.19 points with an interval spanning zero. It does not reproduce a substantial spatial-refitting advantage in this cohort. The predeclared EA-minus-full secondary contrast was positive in all nine participants and retained a Holm-adjusted p value below 0.05 across the three secondary comparisons. These findings retain their distinct endpoint roles.

All 36 saved BA values reproduced with maximum absolute error 0. Each query contained 60 left and 60 right trials, with 12 per class in each of five whole query runs. Source fitting used 96 trials, current-session support used 20 chronological hand trials, and the unused support-run tail remained excluded. The 5,184 original event records retained all classes and original artifact flags.

## Checks and scope

A standalone implementation reconstructed the statistics from saved JSON, using count arithmetic and NumPy without importing the project summarizer. It verified the frozen commit and protocol/code hashes, launch and actual exit records, trial identities and labels, sample-index conventions, chronological run allocation, and complete participant/method coverage. Exact tests enumerated all 512 sign assignments with the observed magnitudes. Paired bootstrap used 10,000 samples, seed 20261027 and participant order 1–9. The separate three-secondary family used Holm adjustment.

This audit did not reopen EEG files or CSP/LDA tensors. The source-file length and SHA checks compare recorded provenance with the frozen manifest; they are not a second complete read of those EEG files. Model-filter equality and internal EA reference scopes were checked by the executed runner and its pre-execution tests; this JSON-only review independently checks the declared data roles and pinned source code.

For participant 5, classifier-only minus frozen differs by 5.55×10⁻¹⁷ BA in floating arithmetic although query accuracy is equal. Descriptive tie counts here use a 10⁻¹² BA tolerance: 5 positive, 2 negative and 2 tied. The original frozen statistics retain their raw positive count of 6 and remain unchanged.

The first-paper dataset exposure and the implementation/source-budget differences from Kumar remain recorded. This audit preserves original endpoint hierarchy and does not pool datasets into one primary participant cohort.
