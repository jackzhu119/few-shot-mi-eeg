# Independent statistical and scientific check of the BMT review report

Scope: read-only arithmetic from published participant tables; no EEG, weights, fit or new inference. Input hashes and exact paired vectors are retained in statistics_check.json.

## Verified numbers

| Original comparison | n | Mean difference, pp | Original percentile interval, pp | Exact sign-flip fraction | Unadjusted p | Holm p, four tests |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| Full refit − frozen, primary | 12 | 7.42135511 | [2.48755482, 12.47661575] | 80/4096 | 0.01953125 | 0.05859375 |
| Full refit − LDA-only, secondary | 12 | 5.47156685 | [2.16805745, 8.91379751] | 42/4096 | 0.01025390625 | 0.041015625 |
| LDA-only − frozen | 12 | 1.94978826 | [−0.98397295, 5.08557988] | 1070/4096 | 0.26123047 | 0.26123047 |
| Full refit − frozen, eligible unflagged subset | 10 | 5.95964914 | [0.98959258, 11.23833164] | 78/1024 | 0.07617188 | 0.15234375 |

All values reproduce the preserved earlier family exactly at the documented numerical tolerance. Bootstrap uses 10000 participant resamples, seed42, original lexicographic subject order. Differences are in BA units for sign flipping, with inclusive absolute boundary tolerance1e-12BA and zero relative tolerance.

The review correctly identified that the current BMT main manuscript omits these p values while S3 contains them. Add the two main comparison p values and the four-test scope to the main text. Retain the original bootstrap endpoint hierarchy; these sign-flip checks were post-hoc, not a newly preregistered primary test.

## Corrections to the reviewer's interpretation

1. **Sign flipping is not a signs-only sign test.** The statistic is the absolute mean of participant differences. Each sign permutation preserves its observed magnitude. The claim that sign flipping uses only directions whereas bootstrap uses magnitudes is false.
2. **The interval/p mismatch is not an arithmetic contradiction.** The reported bootstrap interval is pointwise, unadjusted and based on participant resampling. The exact test uses a sign-symmetric null conditional on magnitudes; Holm additionally controls the four-comparison family. These constructions are not inverses. The adjusted primary p is above0.05, while the matched-label component p is below0.05 in this explicitly post-hoc family. Report the values neutrally rather than calling p=.0586 “marginal significance.”
3. **Do not infer few-participant causation from the mismatch.** Positive endpoints and leave-one-participant-out means describe heterogeneity/influence but do not explain away the procedure difference. The tests use the same observed magnitudes.
4. **Frozen versus updated is not matched information.** Both adapted arms use the same40source plus19/20current-support labels. Frozen uses40source labels and no target support. The review's shorthand that all three arms have exactly the same labeled input is inaccurate; reserve “matched-label component contrast” for full versus LDA-only.
5. **Frozen/predefined is not external preregistration.** The repository establishes timestamped frozen endpoints/cohorts; this check found no basis to call the project publicly preregistered with an external registry.
6. **Proper-score gains do not prove calibration.** Simulated CE/Brier gains for posterior prediction are outcome-specific; no calibration-reliability decomposition was established. Real EEG Brier worsened. A heading claiming that uncertainty “improves calibration” would overstate the evidence.
7. **The BN control is valid within each fixed budget.** Fixed/adaptive arms at cap20 share data and optimizer exposure. Cross-budget comparisons mix label count, class composition, number of batches and BN exposure, so they do not identify a causal budget threshold. Lower collapse counts are descriptive nested counts, not stronger independent replication.
8. **EA's highest point estimate is not universal superiority.** V2 EA minus full CSP has an interval crossing zero. Reporting EA as a strong comparator is warranted; recommending it as universally best or treating “simple methods suffice” as an equivalence conclusion is not.
9. **A concrete introduction example must use observed facts.** Do not invent a participant whose session1 decline was caused by drift. An engineering question about allocation of20new labels provides a safe practical anchor.

## Suggested minimal main-text additions

Methods:
> A supplementary post-hoc check enumerated all sign assignments of the participant differences under a sign-symmetric null and applied Holm correction across four saved contrasts. These family-adjusted tests complement the original pointwise percentile-bootstrap intervals.

Results:
> The matched-label component contrast had an unadjusted exact sign-flip p value of0.01025 and a four-comparison Holm-adjusted value of0.04102. The primary full-minus-frozen contrast had corresponding values of0.01953 and0.05859. The percentile intervals and Holm-adjusted tests use different reference constructions and error control.

These additions report the full evidence without diluting the measured positive component gain or substituting a post-hoc hypothesis for the original hierarchy.
