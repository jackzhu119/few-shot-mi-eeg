# Independent saved-prediction verification

This is a separate implementation and review, not an import of the production scorer. The original decisions are read from the frozen Kumar CSV and the36 BNCI JSON files, with exact labels/trial metadata/QC joins. Integer confusion counts and `fractions.Fraction` reconstruct BA, W, H, left/right recall, C, I and direct prediction disagreement D. A separate bootstrap implementation forms resample multiplicity matrices and applies participant paired differences; it does not call the production bootstrap function.

## Actual result

- **105,672 comparisons passed**, maximum absolute numeric difference **4.440892098500626e-16**.
- Checked all5 Kumar budgets and all4 cohorts: development6, remaining12, overlapping all18 descriptions, and BNCI9.
- Checked original session rates, transitions, participant averages, all1,425 cohort metric/contrast summaries and their new CIs, all9 joint sign combinations, same-eligible QC and run diagnostics.
- Actual targeted software tests:12 passed in0.24s. The independently authored checker passed Ruff.
- No models, EEG arrays, fitting, forward inference or hyperparameter selection were executed.

## Verified full-support EA minus Full results

| Cohort | ΔBA, pp | ΔW, pp | ΔH, pp | C, pp | I, pp | D, pp | Joint positive ΔBA/ΔW |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kumar remaining12 | 5.298069 | 10.453216 | -10.310294 | 14.614766 | 9.316697 | 23.931463 | 10/12 |
| BNCI9 | 5.648148 | 8.518519 | -5.740741 | 12.777778 | 7.129630 | 19.907407 | 9/9 |

These are saved-result reanalyses, not independent new experimental cohorts. Nonlinear W/H were computed before averaging Kumar sessions. ΔW and ΔH are algebraically connected to ΔBA; they are not independent confirmations. Left/right recalls remain available: BNCI mean left recall changed -1.666667pp and right recall +12.962963pp, so improved dynamic W does not imply both left and right improved.

For Kumar's same-eligible10participant QC comparison, EA−Full was5.777858pp on all query trials and6.074704pp on unflagged query trials. The paired restricted-minus-all difference was+0.296845pp with this revision's descriptive bootstrap interval[-1.009468,1.516738]pp. This does not replace the historical12participant endpoint or address potential source/support artifacts.

## Reproduce the independent check

From repository root, with the existing scientific Python environment:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/check_paper2_alignment_integrated_20261104.py --output /tmp/paper2-independent-check
```

The command above was actually executed with this directory as `--output`. It checks the production tables but reconstructs its numerical values from original saved predictions. `INDEPENDENT_CHECK.json` records raw and comparison-file identities, exact plan commit, dimensions and comparison maxima. `CODE_REVIEW.json` binds the reviewed production/test/checker versions and actual targeted test output. `independently_rebuilt_summaries.csv` contains unrounded independent cohort summaries. Historical intervals remain unchanged; these checked new intervals use seed20261104,10,000 draws and linear quantiles.
