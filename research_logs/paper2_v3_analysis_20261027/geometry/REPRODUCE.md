# Geometry saved-result postprocessing

Run from the repository root with the existing NumPy environment:

```bash
python scripts/analyze_paper2_v3_geometry_20261027.py --results-root /path/to/extracted/paper2_results/results --output-root research_logs/paper2_v3_analysis_20261027/geometry
```

The input is the unchanged extracted packet83cbdfdcfa541b3ab3addfc3 at fixed500831c086d9e1d1e8412cf8ebca5fb6a288db76. `--results-root` is the `results` subdirectory, not its parent archive directory. No source EEG, checkpoint, Torch import, fit or model forward is needed. Outputs are forbidden inside the input tree.

The script recomputes all1,350 target BA values from saved prediction arrays and checks identical ordered query IDs/labels across methods and budgets. It reproduces source-table endpoints, seeds10000 participant-bootstrap draws with20261023 and preserves lexicographic participant order. Six participants are the independent units. The150 saved EA-reference cells are read from the previously aligned summary, rather than claimed as new fits.

- `geometry_findings.json`: complete budget/participant/session effects and diagnostics.
- `geometry_all_budget_comparisons.csv`: all45 candidate-versus-reference contrasts, with the frozen primary/reference hierarchy.
- `geometry_cohort_ba.csv`:50 cohort method×budget entries.
- `geometry_cell_metrics.csv`:1350 saved-prediction BA, binary Brier, explicitly1e−15-clipped cross-entropy, collapse and saturated-probability counts.
- `geometry_diagnostics.csv`:150 support-only shift/noise diagnostic rows, actual class counts and fallback records.
- `SOFTWARE_CHECKS.json`: actual execution versions, script/input hashes and arithmetic validation.

Proper-score summaries are post-return exploratory analyses and keep all budgets. Cross-entropy is explicitly clipped because saved probabilities can be exactly zero/one. Binary Brier is the squared positive-class probability error, not the sum of two classwise errors. Pointwise intervals do not replace the original confirmatory hierarchy or account for discovery-wide selection. The source result packet is preserved.
