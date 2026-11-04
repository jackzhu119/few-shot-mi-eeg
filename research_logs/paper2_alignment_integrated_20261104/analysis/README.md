# Saved-prediction EA increment and class coverage

Execution: 4 November 2026 UTC (3 November in the configured America/Los_Angeles client timezone). Frozen plan: `13dd7646c4ce37db40504154388e76b4c6ca6595`.

This analysis reads 82,920 saved hard decisions and frozen trial/role/QC metadata. It reconstructs all 1,836 original method/endpoint cells with maximum historical BA error 0. No EEG array, model, optimizer, fitting routine or query forward is used. Same-prediction analyses are replays/derived endpoint calculations, not additional experiments or participants.

## Full-support EA minus Full

All rates below are percentage-point differences, after scoring each original endpoint and then averaging endpoints equally within participant. The intervals are the newly fixed descriptive participant bootstrap (10,000 draws; seed 20261104; numeric participant order; linear quantiles). Historical pointwise intervals, original primary/secondary roles and Holm families remain in their original files and manuscript tables.

| Cohort | ΔBA [new 95% interval], pp | ΔW [new 95% interval], pp | ΔH, pp | Corrected / introduced, BA points |
| --- | ---: | ---: | ---: | ---: |
| Kumar original primary12 | +5.298 [+2.851, +8.206] | +10.453 [+5.107, +16.037] | -10.310 | 14.615 / 9.317 |
| Kumar development6 | +7.286 [+2.899, +11.267] | +17.854 [+11.272, +24.507] | -21.135 | 15.831 / 8.545 |
| Kumar all18 descriptive | +5.961 [+3.678, +8.368] | +12.920 [+8.362, +17.610] | -13.918 | 15.020 / 9.059 |
| BNCI9 | +5.648 [+3.148, +8.704] | +8.519 [+5.000, +12.593] | -5.741 | 12.778 / 7.130 |

W is min(left recall, right recall) and H is their absolute difference, evaluated within the original session/endpoint before averaging. W=BA−H/2; these quantities are related endpoints, not independent successful tests. Both class recalls remain in every metric table. In BNCI, mean left-recall change is −1.667pp while right-recall change is +12.963pp; the W improvement is not described as both named classes improving.

## Effect distribution and amplitude sensitivity

- Kumar primary12: BA and W both improve in ten participants; both decline in sub-8 and sub-15. EA−Full participant BA changes range from −0.386 to +16.333pp. Every one-participant deletion leaves the mean between +4.295 and +5.815pp.
- BNCI9: all nine participant BA and W differences are positive. Six of the 45 query-run differences are negative; the participant-equal negative-run proportion is 13.333%. A positive participant mean does not imply every run improves.
- Kumar primary participant-equal negative-target-session proportion is 30%; negative-query-run proportion is 31.818%. Runs and sessions remain repeated observations.
- The query-amplitude restriction uses the existing >250µV raw peak-to-peak flags. Ten original-primary participants retain both query classes in all five target sessions. For those same ten participants, EA−Full is +5.778pp on all queries and +6.075pp on unflagged queries (new interval +2.383 to +10.441). The paired restricted-minus-all change is +0.297pp (−1.009 to +1.517). Training and support signals are unchanged. All missing-class cells and exact retained counts are preserved.

## Tables

- `endpoint_metrics.csv`: actual left/right counts, recalls, BA/W/H, method, budget, support count and original/refined query subset. Undefined groups are explicit.
- `endpoint_transitions.csv`: paired C/I/D and all five metric differences.
- `participant_metrics.csv`, `participant_contrasts.csv`: original endpoint aggregation; all participants retained with completeness status.
- `cohort_method_metrics.csv`, `cohort_contrasts.csv`: full-precision participant summaries and descriptive intervals for all five scheduled contrasts/budgets/cohorts.
- `joint_benefit_distribution.csv`: all nine positive/zero/negative ΔBA×ΔW combinations, including empty categories.
- `qc_same_eligible_comparisons.csv`: all/restricted and paired subset change on exactly the same named eligible participants.
- `query_run_metrics.csv`, `query_run_contrasts.csv`: complete query-run diagnostics.
- `participant_run_effect_distribution.csv`, `cohort_run_effect_distribution.csv`: fractions first within people, then equal-person summaries.
- `KEY_RESULTS.json`: selected full-budget rows copied directly from the CSV outputs, without manual rounding.

The selected classical exports contain hard labels and no probabilities or logits. No NLL/Brier table is manufactured from these labels. Genuine probability records elsewhere in the project belong to their own method/protocol and are not substituted here.

## Actual validation and reproduction

The standalone scalar/Fraction checker imports no production analysis code. It performed 44,352 comparisons across 2,196 original/amplitude-restricted method endpoints and their contrasts/participant aggregates; maximum difference 4.44e−16. Rational identities C−I=ΔBA and C+I=D passed. All 49 source lengths/SHA values were rechecked. This checker scope predates the appended run diagnostics; the separate cross-agent checker records its own additional scope.

Fourteen software-only targeted tests passed. They cover unequal class denominators, missing classes, duplicate/reordered/missing identities, label mismatch, nonlinear aggregation order, joint ties, and unequal run counts before person-level aggregation. Ruff passed. A clean-directory saved-result replay reproduced all twelve result CSV files byte for byte, including run diagnostics; see `REPRODUCTION_CHECK.json`.

Commands actually executed (use a new output directory for a fresh replay):

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python scripts/analyze_paper2_alignment_integrated_20261104.py --output /tmp/paper2_alignment_saved_reproduction_20261104 --plan-commit 13dd764
/workspace/.venvs/few-shot-mi-eeg/bin/python scripts/verify_saved_alignment_metrics_20261104.py --analysis research_logs/paper2_alignment_integrated_20261104/analysis
/workspace/.venvs/few-shot-mi-eeg/bin/python -m pytest -q tests/test_paper2_alignment_integrated.py
```

The original metadata-validation failure is retained in `input_validation_attempt01.log`: the loader initially asserted that the frozen BNCI method used 20 support labels. Its actual metadata correctly records zero used labels with 20 available; the loader was corrected to enforce that distinction. This stopped before any result table was written. `EXECUTION_HISTORY.json` and actual stdout retain the sequence; no training attempt or automatic training retry occurred.
