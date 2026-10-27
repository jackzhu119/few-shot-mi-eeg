# Reproduce saved-result analysis

Use the three archive parts at fixed commit `500831c086d9e1d1e8412cf8ebca5fb6a288db76`, under `training_status/paper2-discovery-v3/result_exports/83cbdfdcfa541b3ab3addfc3/`. Join in `packet_manifest.json` order, check the combined SHA256 `e509c2591efa21fff4dd47236e613ed6b611ca10ad20bac3da37e66e34a9d170`, then extract and verify `paper2_results/MANIFEST.json`. The combined archive has40,194,093bytes. Do not execute its worker/submit entry to analyze results.

All commands below read saved JSON/CSV/predictions, never EEG, checkpoint tensors or a model forward. They require Python, NumPy and, for figures, Matplotlib. Use existing software; no school training environment change is necessary. Replace `/path/to/paper2_results/results` with the extracted `results` folder.

```bash
python scripts/audit_paper2_v3_saved_predictions_20261027.py --results-root /path/to/paper2_results/results --output research_logs/paper2_v3_analysis_20261027/audit/prediction_audit.json
python scripts/summarize_paper2_v3_discovery_20261027.py --results-root /path/to/paper2_results/results --output-root research_logs/paper2_v3_analysis_20261027/tables
python scripts/analyze_paper2_v3_geometry_20261027.py --results-root /path/to/paper2_results/results --output-root research_logs/paper2_v3_analysis_20261027/geometry
python scripts/analyze_paper2_v3_neural_mechanisms_20261027.py --results-root /path/to/paper2_results/results --output-root research_logs/paper2_v3_analysis_20261027/neural
python scripts/analyze_paper2_v3_simulations_20261027.py --results-root /path/to/paper2_results/results --output-root research_logs/paper2_v3_analysis_20261027/simulation
python scripts/render_paper2_v3_discovery_figures_20261027.py --saved-results-root /path/to/paper2_results/results --output manuscript/discovery_revision_20261027/figures
python scripts/build_paper2_discovery_revision_20261027.py
```

`tables/` independently reconstructs all900participant and150cohort endpoints and165original comparisons, then reports a complete505pair same-condition matrix and135design/mechanism contrasts. Imported V2 EA reference rows are identified separately; they are not newly fitted models. Six exposed participants are the independent units. Model seeds and repeated frozen-budget predictions do not increase sample size. The original12-person manuscript endpoints are preserved from their earlier audited source, not recalculated or retuned using V3.

`audit/prediction_audit.inputs.csv` maps every prediction and paired metric to its exact bytes/SHA256. `simulation/simulation_inputs.json` maps all19,200saved paired-draw result files; the original archive manifest supplies full provenance. Every simulation is marked synthetic/software-validation-only. Allcomplete outputs and negative comparisons are retained; undefined/incomplete endpoints are errors, rather than silently excluded rows.

The manuscript is a new review revision, not an author-approved submission. Earlier author approval records do not automatically cover these additional analyses. No acceptance ledger, training configuration, weight file, source split or query policy is changed by these commands.
