# Actual budget results: saved-prediction review

UTC execution: 2026-10-16T03:42:29.163634+00:00 to 2026-10-16T03:42:39.485673+00:00. Source commit: `f59b14d45419ade50657f554585369eae4cd4d4b`.

The authorized saved-result postprocessor ran once, after 33 synthetic tests and Ruff passed. No EEG/model state, fit or new inference was accessed. Every planned budget is reported. All intervals below are new post-exposure exploratory pointwise 95% percentile intervals (10,000 participant resamples, seed42). They are not multiplicity-adjusted, cannot establish equivalence and must not replace the historical main-analysis intervals or four-test Holm family.

The endpoint is the equal mean of all five target-session BAs before any cohort average. All 18 participants have complete endpoints at every budget/method. Development6 and remaining12 retain their fixed memberships; all18 is descriptive. Full support is 19 labels in14/90 sessions and20 labels in76/90 sessions.

Validation retained1800 session/action cells and78600 saved prediction rows. All budgets/actions use identical ordered query identities, runs, true labels and counts within a subject/session. The11790 unique historical target predictions (three old actions) matched the original saved file exactly; full-support prediction differences and their BA differences are zero. Frozen predictions at every smaller budget also matched exactly. Cross-participant/session/role identity ownership, fit/query exclusion and EA source/current-prefix reference scopes passed. The180 provided half-support validation audit rows were checked; the selector consumer separately owns feature/holdout completeness checks.

## development6

BA in percent [pointwise95% CI].

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA |
|---|---:|---:|---:|---:|
| 4 | 59.97 [57.34, 63.59] | 62.69 [59.02, 66.76] | 62.35 [57.53, 67.02] | 64.14 [60.57, 67.54] |
| 8 | 59.97 [57.34, 63.59] | 63.81 [60.21, 67.59] | 64.93 [59.55, 70.64] | 67.26 [63.20, 71.90] |
| 12 | 59.97 [57.34, 63.59] | 64.00 [60.38, 68.12] | 65.00 [59.63, 70.78] | 67.98 [63.58, 71.60] |
| 16 | 59.97 [57.34, 63.59] | 65.38 [61.01, 70.48] | 67.10 [61.19, 74.11] | 68.46 [63.28, 74.33] |
| full | 59.97 [57.34, 63.59] | 64.37 [56.99, 71.82] | 63.22 [58.39, 67.40] | 70.51 [66.15, 75.22] |

Paired gains in percentage points [pointwise95% CI]; final count is participants whose measured gain was negative.

| Budget | LDA − frozen | Full − frozen | EA − frozen |
|---|---:|---:|---:|
| 4 | +2.72 [+1.27, +4.59]; 0/6 decreased | +2.38 [-0.58, +5.41]; 2/6 decreased | +4.17 [-0.18, +8.69]; 2/6 decreased |
| 8 | +3.84 [+1.81, +6.49]; 0/6 decreased | +4.96 [+1.12, +9.77]; 1/6 decreased | +7.29 [+2.78, +12.03]; 1/6 decreased |
| 12 | +4.03 [+1.41, +7.31]; 1/6 decreased | +5.03 [+0.68, +10.46]; 2/6 decreased | +8.01 [+3.24, +12.56]; 1/6 decreased |
| 16 | +5.41 [+2.63, +9.43]; 0/6 decreased | +7.13 [+1.98, +13.58]; 1/6 decreased | +8.49 [+3.69, +14.28]; 0/6 decreased |
| full | +4.40 [-1.75, +11.53]; 2/6 decreased | +3.25 [-0.90, +7.14]; 2/6 decreased | +10.53 [+5.21, +15.73]; 0/6 decreased |

| Budget | Full − LDA | EA − full |
|---|---:|---:|
| 4 | -0.33 [-2.94, +2.13]; 3/6 decreased | +1.79 [-2.87, +6.64]; 3/6 decreased |
| 8 | +1.12 [-1.20, +3.51]; 3/6 decreased | +2.33 [-1.89, +6.88]; 2/6 decreased |
| 12 | +1.00 [-2.29, +4.09]; 2/6 decreased | +2.98 [-0.35, +6.54]; 2/6 decreased |
| 16 | +1.72 [-1.85, +4.77]; 2/6 decreased | +1.36 [-0.08, +2.89]; 3/6 decreased |
| full | -1.15 [-5.02, +2.46]; 4/6 decreased | +7.29 [+2.90, +11.27]; 1/6 decreased |

## remaining12

BA in percent [pointwise95% CI].

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA |
|---|---:|---:|---:|---:|
| 4 | 57.94 [52.62, 63.62] | 58.83 [53.41, 64.59] | 58.74 [54.02, 63.95] | 60.22 [55.38, 65.55] |
| 8 | 57.94 [52.62, 63.62] | 60.07 [54.70, 66.06] | 61.25 [56.60, 66.37] | 66.10 [59.88, 72.32] |
| 12 | 57.94 [52.62, 63.62] | 61.41 [55.44, 67.98] | 64.31 [59.19, 69.78] | 67.59 [61.35, 73.82] |
| 16 | 57.94 [52.62, 63.62] | 62.14 [56.04, 68.50] | 66.93 [61.06, 72.78] | 70.08 [63.64, 76.19] |
| full | 57.94 [52.62, 63.62] | 59.89 [54.27, 65.44] | 65.36 [59.77, 70.83] | 70.66 [64.29, 76.76] |

Paired gains in percentage points [pointwise95% CI]; final count is participants whose measured gain was negative.

| Budget | LDA − frozen | Full − frozen | EA − frozen |
|---|---:|---:|---:|
| 4 | +0.89 [-1.15, +2.66]; 4/12 decreased | +0.81 [-2.53, +4.17]; 7/12 decreased | +2.29 [-0.26, +4.84]; 4/12 decreased |
| 8 | +2.13 [+0.30, +3.87]; 4/12 decreased | +3.31 [-0.13, +6.94]; 4/12 decreased | +8.16 [+3.23, +13.08]; 3/12 decreased |
| 12 | +3.48 [+1.31, +5.48]; 3/12 decreased | +6.37 [+1.65, +11.18]; 4/12 decreased | +9.65 [+4.57, +14.83]; 1/12 decreased |
| 16 | +4.20 [+1.41, +6.76]; 2/12 decreased | +8.99 [+4.06, +14.23]; 2/12 decreased | +12.15 [+5.77, +18.82]; 2/12 decreased |
| full | +1.95 [-1.00, +5.03]; 5/12 decreased | +7.42 [+2.51, +12.43]; 3/12 decreased | +12.72 [+6.50, +19.10]; 2/12 decreased |

| Budget | Full − LDA | EA − full |
|---|---:|---:|
| 4 | -0.08 [-2.95, +2.54]; 6/12 decreased | +1.48 [-0.76, +3.58]; 4/12 decreased |
| 8 | +1.18 [-1.35, +3.91]; 6/12 decreased | +4.85 [+2.20, +7.76]; 2/12 decreased |
| 12 | +2.90 [-1.12, +7.02]; 4/12 decreased | +3.28 [+1.30, +5.31]; 3/12 decreased |
| 16 | +4.79 [+1.32, +8.41]; 3/12 decreased | +3.15 [+1.21, +4.98]; 2/12 decreased |
| full | +5.47 [+2.16, +8.88]; 2/12 decreased | +5.30 [+2.81, +8.26]; 2/12 decreased |

## all18_descriptive

BA in percent [pointwise95% CI].

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA |
|---|---:|---:|---:|---:|
| 4 | 58.62 [54.80, 62.52] | 60.11 [56.05, 64.25] | 59.95 [56.17, 63.86] | 61.53 [57.86, 65.27] |
| 8 | 58.62 [54.80, 62.52] | 61.32 [57.27, 65.55] | 62.47 [58.60, 66.45] | 66.48 [62.04, 70.90] |
| 12 | 58.62 [54.80, 62.52] | 62.28 [57.91, 66.85] | 64.54 [60.51, 68.73] | 67.72 [63.28, 72.09] |
| 16 | 58.62 [54.80, 62.52] | 63.22 [58.66, 67.78] | 66.99 [62.46, 71.56] | 69.54 [64.83, 74.10] |
| full | 58.62 [54.80, 62.52] | 61.38 [56.61, 66.09] | 64.65 [60.56, 68.73] | 70.61 [66.12, 74.99] |

Paired gains in percentage points [pointwise95% CI]; final count is participants whose measured gain was negative.

| Budget | LDA − frozen | Full − frozen | EA − frozen |
|---|---:|---:|---:|
| 4 | +1.50 [-0.01, +2.86]; 4/18 decreased | +1.33 [-1.17, +3.84]; 9/18 decreased | +2.91 [+0.63, +5.29]; 6/18 decreased |
| 8 | +2.70 [+1.23, +4.21]; 4/18 decreased | +3.86 [+1.12, +6.78]; 5/18 decreased | +7.87 [+4.29, +11.62]; 4/18 decreased |
| 12 | +3.66 [+1.97, +5.37]; 4/18 decreased | +5.92 [+2.39, +9.64]; 6/18 decreased | +9.10 [+5.36, +13.07]; 2/18 decreased |
| 16 | +4.60 [+2.42, +6.83]; 2/18 decreased | +8.37 [+4.57, +12.53]; 3/18 decreased | +10.93 [+6.38, +15.93]; 2/18 decreased |
| full | +2.77 [-0.15, +6.01]; 7/18 decreased | +6.03 [+2.44, +9.88]; 5/18 decreased | +11.99 [+7.53, +16.76]; 2/18 decreased |

| Budget | Full − LDA | EA − full |
|---|---:|---:|
| 4 | -0.17 [-2.25, +1.85]; 9/18 decreased | +1.58 [-0.61, +3.79]; 7/18 decreased |
| 8 | +1.16 [-0.75, +3.17]; 9/18 decreased | +4.01 [+1.67, +6.56]; 4/18 decreased |
| 12 | +2.26 [-0.56, +5.31]; 6/18 decreased | +3.18 [+1.47, +4.97]; 5/18 decreased |
| 16 | +3.77 [+1.15, +6.53]; 5/18 decreased | +2.56 [+1.16, +3.96]; 5/18 decreased |
| full | +3.26 [+0.37, +6.26]; 6/18 decreased | +5.96 [+3.74, +8.41]; 3/18 decreased |

## Failures and class counts

There were no scientific fallbacks, undefined query BAs or missing query classes. The budget actions had1170 newly attempted/completed fits and630 historical prediction reuses. Half-support validation fits are separate and are not added to these budget counts. Six4-label prefixes lacked one support class (development1/30, remaining5/60); all stayed included and completed their candidate fits using the fixed two-class source40. Budgets8/12/16/full had no missing support class.

Prediction class-collapse counts per90 repeated participant/session cells; these are descriptive repeats, not independent sample sizes.

| Budget | Frozen | LDA update | Full refit | EA + CSP/LDA | Shared single-class support | Fallbacks, all methods |
|---|---:|---:|---:|---:|---:|---:|
| 4 | 3 | 4 | 10 | 1 | 6 | 0 |
| 8 | 3 | 3 | 10 | 3 | 0 | 0 |
| 12 | 3 | 3 | 6 | 0 | 0 | 0 |
| 16 | 3 | 1 | 3 | 0 | 0 | 0 |
| full | 3 | 0 | 0 | 0 | 0 | 0 |

## Limits and negative findings

At4/8/12 labels in remaining12, full−LDA pointwise intervals include zero; their paired means are−0.08/+1.18/+2.90pp. At4 labels full−frozen and EA−full intervals also include zero, with7/12 and4/12 participants respectively showing negative measured changes. Full support does not improve every method monotonically over the16-label point: remaining12 LDA means are62.14% then59.89%, and full-refit means66.93% then65.36%. These observations do not select16 labels as an operating budget.

At full support the development6 full−LDA mean is−1.15pp [−5.02,+2.46], with4/6 participants lower; remaining12 has+5.47pp [+2.16,+8.88], with2/12 lower. The six development participants therefore do not reproduce a uniform component-update advantage. Remaining12 EA−full means are positive at every budget, but measured participant decreases remain4/2/3/2/2 across4/8/12/16/full labels. The corresponding4-label interval includes zero. A stronger EA comparator limits claims that the original three-action comparison establishes an optimal adaptation method. These exploratory results do not establish policy performance, online benefit, human learning, clinical effect or independent confirmation.

CSV tables retain full precision, all individual curves, all exact class counts, every status/reason and actual complete participant lists. Three figures with source CSVs are in `manuscript/figures/component_followup_20261016/budget/`. The original execution receipt binds the fixed script/protocol/input hashes and all initial output hashes; this formatting-only review is bound separately by results_review_receipt.json.
