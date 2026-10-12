# NETBCI nineteen-ID independent methods review — 2026-10-11

The expanded analysis and the source-driven restriction to **14 published IDs**
passed independent saved-table arithmetic and provenance checks. The 19-ID output
is retained as a diagnostic record; it does not establish 19 independent EEG
participants. Exact derivative-signal copies affect `sub-1`, `sub-6`, `sub-7`,
`sub-15`, and `sub-17`. All five are excluded from the separate sensitivity by a
rule based on source content, without selecting exclusions by result direction.
Neither analysis establishes causal human learning or retained skill.

## Executed checks

The independent reviewers imported NumPy/SciPy and standard-library utilities;
they did **not** import the production analysis or statistical helpers. Each CLI
completed with exit code 0. Previous ten-ID review sources and results were kept.

- [Independent nineteen-ID source](../research_logs/netbci_cohort_all19_20261010/independent_review_source_v2.py)
  and [executed receipt](../research_logs/netbci_cohort_all19_20261010/independent_methods_review_run01.json):
  recomputed 76 original behavior/session joins; source/query identity, true labels,
  confusion matrices, balanced accuracy, 500 complete-run conditional bootstrap
  intervals, source-reference/CAR spectral contrasts, QC missing cells, matched
  selection identities, within-person matched means, and whole-ID session/change
  bootstrap intervals using seed 42 and 10,000 draws.
- [Independent sensitivity source](../research_logs/netbci_cohort_all19_20261010/independent_sensitivity_review_v2.py)
  and [executed receipt](../research_logs/netbci_cohort_all19_20261010/independent_sensitivity_review_run01.json):
  derived the excluded set directly from all cross-ID continuous-run **or**
  task-window exact-copy groups, checked the retained 56 session rows, all eight
  metric change/session summaries, and five association pairs with Pearson and
  tied-rank Spearman estimates and complete-pair bootstrap intervals.
- [Failure/provenance closeout source](../research_logs/netbci_cohort_all19_20261010/independent_methods_closeout_source.py)
  and [closed receipt](../research_logs/netbci_cohort_all19_20261010/independent_methods_closeout_run01.json):
  freshly checked all independent-review input hashes; separately counted model
  failures, unavailable matching, QC flags, and model parameter digests.
- [First-ten replay comparison](../research_logs/netbci_cohort_all19_20261010/independent_first10_replay_comparison_20261011.json):
  all 16 stable files for each original ID were freshly hashed against the
  preserved ten-ID run. **160/160 files are byte-identical**, including model,
  predictions, features, geometry, partitions, and failures. Scope configuration
  hashes differ and are retained in the receipt. This is reproducibility evidence.

All 19 saved model audits contain one fit call and identical model SHA256 before
and after query prediction. Training IDs exactly match session 01 runs 01–04;
source queries are runs 05–06, session 02 is validation without selection, and
sessions 03–04 are exploratory queries. Source-fitted QC, scaler and reference PCA
provenance passed. The production source was read to confirm these fit roles and
that session-specific descriptive PCA does not feed the decoder.

## Source census and copied derivative signals

The hashed pre-model raw identity audit covers 456 recordings. All 456 match both
official and participant SHA256 manifests, and their EDF annotations match the
official event TSVs. These raw-source checks were executed by the source audit;
this independent table review verifies their hashes and continuity into analysis.

There are 14,431 original task events and 14,429 eligible exact five-second epochs.
Both partial source events remain explicitly recorded, without padding or
invented events:

| Original event | Label | Original duration | Samples | Five-second analysis |
| --- | --- | ---: | ---: | --- |
| `sub-3/ses-01/run-03/tsv-row-31` | rest | 2.968 s | 742 | Ineligible, retained in source census |
| `sub-12/ses-02/run-02/tsv-row-32` | right hand | 4.976 s | 1,244 | Ineligible, retained in source census |

The source audit finds 30 continuous duplicate groups involving 78 recordings,
with 408 unique continuous numeric hashes. There are 909 exact task-window groups
with 2,352 members and no conflicting task labels. `sub-1` and `sub-17` share all
24 corresponding recordings, `sub-6` and `sub-15` share the six session-01
recordings, and `sub-7` sessions 01–03 share the six session-04 recordings present
under `sub-1` and `sub-17`. Within `sub-7`, later sessions contain 238 windows
identical to training windows and 118 identical to source-query windows. Distinct
trial IDs do not remove this content overlap.

The available evidence concerns the EDF derivative. Original BrainVision signal
files were not independently read, and the correct source assignment or cause of
the duplication remains unknown. No acquisition, conversion, participant or
author conduct is inferred. Retained IDs are `sub-2`, `sub-3`, `sub-4`, `sub-5`,
`sub-8`, `sub-9`, `sub-10`, `sub-11`, `sub-12`, `sub-13`, `sub-14`, `sub-16`,
`sub-18`, and `sub-19`. Absence of detected exact copies does not prove their
biological identities or exclude near similarity.

## Retained failures and availability

All 19 frozen models completed. Their scientific failures remain in the results:
21 constant-prediction session records across 10 IDs and five unavailable QC
matching variants, for 26 failure records. These are decoder/analysis failures,
not evidence of human skill loss. All 456 QC-flagged trials remain in the primary
analysis.

The primary matched summary contains all 152 ID/session/variant cells, including
unavailable cells. All-six-run matching is available for 19/19 IDs; QC four-run
matching is available for 14/19. Within the restricted 14-ID sensitivity those
counts are 14/14 and 9/14. QC matching remains unavailable for `sub-8`, `sub-11`,
`sub-13`, `sub-14`, and `sub-19`; exact deficient cells are preserved in the
closeout receipt. The required 12 trials per label/run was never relaxed.

## Independently recomputed estimates

Values below are session 04 minus session 01, with whole-ID paired bootstrap
95% percentile intervals (10,000 draws, seed 42). The 19-ID EEG intervals are
arithmetic diagnostics because copied signals violate independence. The 14-ID
restriction is a post-observation sensitivity on the same dataset.

| Quantity | All 19 IDs: mean change [interval] | Restricted 14 IDs: mean change [interval] |
| --- | ---: | ---: |
| Published session mean hit score, percentage points | 14.5684 [10.7063, 18.2662] | 15.4098 [11.5257, 19.3322] |
| Frozen CSP/LDA balanced accuracy, percentage points | −4.6765 [−11.8841, 2.3328] | −4.2020 [−11.4127, 2.7111] |
| Mu MI-minus-rest task power contrast, dB | −0.5255 [−1.0171, 0.0383] | −0.5294 [−1.0085, −0.0580] |

All five restricted-cohort association pairs and both estimators were recomputed.
Each uses 14 complete participant pairs and 10,000 valid paired bootstrap draws.
All ten intervals span zero; they are exploratory, with no causal or confirmatory
interpretation.

| Pair | Pearson r [95% interval] | Spearman rho [95% interval] |
| --- | ---: | ---: |
| BA change / behavior change | 0.2725 [−0.4781, 0.6682] | 0.0792 [−0.6028, 0.6389] |
| Mu contrast change / behavior change | −0.3439 [−0.7841, 0.1660] | −0.4725 [−0.7937, 0.0697] |
| Mu contrast change / BA change | −0.1975 [−0.6893, 0.3255] | −0.2266 [−0.7618, 0.3941] |
| Session-04 all-six-run AIRM / BA change | −0.1452 [−0.5981, 0.4238] | −0.2486 [−0.7092, 0.3691] |
| Session-04 all-six-run PCA subspace distance / BA change | 0.3392 [−0.3359, 0.7710] | 0.2552 [−0.4000, 0.7692] |

The behavior table contains real published aggregate scores. Their run order,
denominators and trial outcomes remain unresolved; no aggregate score was
broadcast into trial labels. A task power contrast is not a prestimulus-baseline
ERD measure. Conditional run intervals omit training uncertainty. A spectral
interval excluding zero does not identify a learning mechanism or retained skill.

## Public-resource review crosscheck

The independent PhysioNet validation has completed: it freshly reread all 327
EDF recordings, rechecked all 654 official files, and compared original sidecar
annotations without importing the ingestion helper. Its closed receipt matches
the current source audit SHA256. The resource contains 109 source IDs; 105 have
three source-qualified hand-imagery runs (315 recordings, 4,722 complete
four-second imagery windows). `S088`, `S089`, `S092` and `S100` remain flagged for
source-annotation/timing issues. No new resource models or retention conclusions
are claimed. The 109 source count must not be described as 109 training-qualified
subjects.

## Review boundaries

This review independently recalculates saved-table statistics and checks source,
configuration, model, bundle and artifact hashes. It does not independently
repeat EEG filtering, PSD extraction or raw-array geometric distances, and does
not independently refit classifiers. These numerical steps were source-reviewed;
the raw identity gate was a separate executed audit. Replication on different
datasets, stable participant identity, online learning measurements and skill
retention remain separate research requirements.
