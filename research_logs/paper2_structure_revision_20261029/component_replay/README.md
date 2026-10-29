# Saved component evidence: independent numerical replay

All outputs are derived from the existing budget and phase prediction CSVs. No
EEG or model tensor is read, and no fit, forward pass, search or new test family
is performed. The `REPLAY_REPORT.json` records actual input byte hashes.

## Plot-ready files

- `remaining12_budget_curves.csv`:20 rows, four methods ×4/8/12/16/full; mean BA and existing pointwise intervals.
- `budget_participant_endpoints.csv`:360 rows,18people ×5budgets ×4methods; five-session equal means.
- `full_support_participant_effects.csv`:18rows with four method means and paired Full−LDA / EA−Full gains.
- `remaining12_full_support_session_effects.csv`:60rows,12people ×5sessions; four BA values and both paired gains, suitable for heatmaps.
- `budget_session_metrics_replayed.csv`:all1800 planned action cells, true/predicted class counts, exact rational BA and saved-float error.
- `phase_session_metrics_replayed.csv`:all540 phase cells, including96undefined; none replaced with chance or silently removed.

Budget BA was recomputed from all78,600 saved prediction rows with exact
confusion-count fractions. Its maximum difference from saved float BA is
1.11e−16. All60 existing cohort mean/interval rows and75 paired contrast/interval
rows reproduced exactly. The original postprocessor uses **numeric participant
order**, not lexicographic order, before seed42 resampling. This is distinct from
the old original-main intervals and from phase aggregation.

Phase BA was recomputed from all11,460 saved prediction rows; all444defined
cells matched exactly and96undefined cells remain. The33 existing phase contrasts
and intervals matched exactly with **lexicographic participant order** and seed42.
The conditional remaining cohort has9people, metadata-complete cohort8; their
identities remain in the report. No new p-values are calculated.

## Reproduction

The root script supports plain CSV or `.csv.gz`. The public compressed input
files are assembled in `input/` by the parent delivery task. Run from the
repository root, with a fresh output folder:

```bash
python scripts/review_kumar_component_saved_evidence_20261029.py --budget-root research_logs/paper2_structure_revision_20261029/component_replay/input/budget --phase-root research_logs/paper2_structure_revision_20261029/component_replay/input/phase --output /tmp/paper2-component-replay-check
```

The fixed7200-row trial-role manifest and the three original result CSVs are also
required; their default paths are already public in this repository. Explicit
`--trial-manifest` and `--saved-tables` can redirect them. Source originals and
historical bootstrap/acceptance records are never rewritten.
