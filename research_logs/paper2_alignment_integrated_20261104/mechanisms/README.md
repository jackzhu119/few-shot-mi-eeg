# Fixed covariance-information and EA phase sensitivities

Actual source operations completed on 4 November 2026 UTC (3 November in the client timezone), under the analysis plan frozen at `13dd764`. These are new classical fits on previously exposed cohorts; historical predictions and the 54 accepted EEGNet models were preserved.

## Executed scope

- 396 coordinate-matched target fits: 18 Kumar participants × five target sessions × four fixed arms, plus nine BNCI participants × four arms.
- 148 additional EA phase fits at the original shared cue5s/task2s eligibility, with 32 original undefined phase cells retained. Full predictions for this phase comparison were replayed from the original saved outputs.
- Total544 successful fits, 544 unique fit claims, 576 defined/undefined cell records. First invocation completed362 fits, then stopped before claiming the one-class-query phase cell; the explicit same-state continuation skipped all362 and added182 fits. The old exception and actual source versions remain.
- First dispatch06:51:11.567632UTC; final exit0 at06:58:35.166668UTC. Combined observed elapsed443.599036seconds includes the pause. No new neural source fit, GPU, Pod, or model search.

## Four fixed arms

Kumar uses the same fixed Helmert21 CAR coordinates, MNE CSP4/Ledoit–Wolf (`norm_trace=False`, `rank="full"`) and LDA `lsqr`/automatic shrinkage in every arm. BNCI preserves its original22-channel recorded-reference arrays, trace-normalized CSP covariances, fixed0.1 covariance/LDA shrinkage and four extreme CSP components. These are within-dataset matched operations, not a cross-dataset estimator unification.

1. `full`: shared core on the original source/support union.
2. `rms_full`: one common RMS scalar per complete trial, then the shared core.
3. `diagonal_ea`: source/current-support domain references with off-diagonal entries removed in the stated fixed coordinates, then the shared core.
4. `ea`: full domain covariance references, then the shared core.

Kumar diagonal coordinates are Helmert contrasts, not independent electrodes. RMS changes amplitude information. EA references are computed only from sourceTRAIN and current support; each query is transformed with the fixed target reference. Source40/support19or20 and BNCI source96/support20 are unchanged.

## New matched-core BA results

| Cohort | Full | Common RMS | Diagonal reference | Full covariance EA |
| --- | ---: | ---: | ---: | ---: |
| kumar_primary12 | 65.36% | 69.52% | 67.88% | 70.43% |
| kumar_development6 | 63.11% | 67.03% | 63.88% | 69.86% |
| bnci9 | 71.85% | 72.87% | 72.59% | 77.50% |

| Cohort | Contrast | Mean difference, pp [new pointwise95%CI] | Positive / zero / negative participants |
| --- | --- | ---: | --- |
| kumar_primary12 | ea_minus_full | +5.07 [2.88, 7.71] | 11 / 0 / 1 |
| kumar_primary12 | ea_minus_rms_full | +0.91 [-1.28, 3.18] | 5 / 0 / 7 |
| kumar_primary12 | ea_minus_diagonal_ea | +2.55 [0.59, 4.49] | 8 / 0 / 4 |
| kumar_development6 | ea_minus_full | +6.75 [2.75, 10.34] | 5 / 0 / 1 |
| kumar_development6 | ea_minus_rms_full | +2.83 [-3.26, 9.20] | 4 / 0 / 2 |
| kumar_development6 | ea_minus_diagonal_ea | +5.97 [2.89, 9.06] | 6 / 0 / 0 |
| bnci9 | ea_minus_full | +5.65 [3.15, 8.70] | 9 / 0 / 0 |
| bnci9 | ea_minus_rms_full | +4.63 [1.94, 7.96] | 9 / 0 / 0 |
| bnci9 | ea_minus_diagonal_ea | +4.91 [1.94, 8.24] | 7 / 1 / 1 |

Coordinate-matched Kumar EA differs from the historical re-embedded22-channel implementation. Its new score does not replace the historical70.66% endpoint or historical+5.30pp contrast. The new Full scores match the prior endpoints, while the new Kumar EA mean is70.43%. BNCI Full and EA predictions match their historical counterparts exactly.

## EA phase comparison

| Scope | Window/paired contrast | n | EA−Full, pp [new pointwise95%CI] |
| --- | --- | ---: | ---: |
| conditional | cue5s | 9 | +7.85 [3.04, 13.66] |
| conditional | task2s | 9 | +0.13 [-1.40, 1.92] |
| conditional | task2s_minus_cue5s | 9 | -7.73 [-12.17, -3.76] |
| metadata_complete | cue5s | 8 | +7.55 [2.32, 13.95] |
| metadata_complete | task2s | 8 | +0.53 [-1.01, 2.39] |
| metadata_complete | task2s_minus_cue5s | 8 | -7.03 [-11.84, -2.97] |

EA supplies an increment for the cue-anchored five-second definition in the nine-person common-eligibility scope; its task-start two-second increment is close to zero. The paired window difference retains the same participants and query identities. Anchor, duration and local filtering boundaries change jointly, so the contrast characterizes these two complete signal definitions rather than isolating a physiological cause. The eight-person metadata-complete scope preserves the same direction. Original missing phase markers and undefined cells are not filled.

## Probability and reference diagnostics

Every new successful cell stores genuine class1/right-hand probabilities, fixed class order[0,1], fitted-state digest before/after prediction, full trial identities, support class counts, and private checkpoint SHA256. Kumar support amplitude-flag counts are retained. Aligned arms store source/support reference eigenvalues and condition numbers.

Balanced NLL uses class-equal weights and clipping1e−7; the balanced Brier score is the single-coordinate binary definition. These probabilities belong only to the new sensitivity fits. Historical hard-label predictions are not converted into probabilities. `probability_quality_main_contrasts.json` records the main comparisons in nats and squared-probability units, respectively.

## Reproduction and status

Existing compatible CPU environment and original local source/prepared data are required. The first command below is the actual fitting entry, for a fresh output directory only; the second is the actual saved-cell summarizer used for this delivery. Do not rerun existing completed cells.

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -u scripts/run_paper2_alignment_mechanisms_20261104.py --output research_logs/paper2_alignment_integrated_20261104/mechanisms/run01 --private-models /workspace/private_alignment_mechanisms_20261104/models --phase
/workspace/.venvs/few-shot-mi-eeg/bin/python research_logs/paper2_alignment_integrated_20261104/mechanisms/summarize_mechanisms.py
```

Use `--resume` solely to continue the same output state; completed cell/model hashes are verified and skipped, unresolved prior attempt claims prevent retraining. `AGGREGATE_EXECUTION_RECEIPT.json` describes the real two-invocation history. The original executed wrappers are archived in `versions/`; a later wrapper-only persistent deadline/count repair passed17 targeted synthetic tests and was not executed for new scientific fits. No retroactive global-deadline enforcement is asserted for the completed run.

### Outputs

- `participant_metrics.csv`, `cohort_means.csv`, `cohort_comparisons.csv`: all four arms, all six descriptive paired contrasts and seven metrics, full precision.
- `phase_participant_metrics.csv`, `phase_cohort_comparisons.csv`: complete and undefined endpoints, conditional/metadata-complete scopes.
- `run01/cells/`, `run01/claims/`, `run01/inputs/`: actual outputs, unique attempts, input/version receipts.
- `run01_initial.log`, `run01_continuation.log`, original exception, operational repair manifest and post-run wrapper-fix record: actual execution boundaries.

New descriptive intervals use10000 paired participant resamples, seed20261104, numeric participant order and linear percentile quantiles. Kumar sessions receive equal weight before participant aggregation; BNCI retains its original120-query participant endpoint. All new intervals are distinct from historical bootstrap sequences and Holm comparison families. No new p-values or multiplicity-family redefinition is performed.
