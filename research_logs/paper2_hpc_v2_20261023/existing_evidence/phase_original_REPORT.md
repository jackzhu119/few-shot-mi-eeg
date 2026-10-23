# Saved-prediction phase-window analysis

This is postprocessing of the completed, authorized phase comparison. It reads saved prediction/metric tables and text manifests, not EEG or model arrays, and performs no new fit or forward pass. The original 12-person, full-support primary analysis is unchanged.

## Scope and verification

The exploratory protocol was frozen in `docs/kumar_component_exploratory_protocol_20261016.md` (SHA256 `1c3e87ad634148bde031579cd8efb976e75643635d452a2ea69d911ccc9b09fc`). The pre-execution scope clarification is `docs/kumar_phase_scope_reporting_addendum_20261016.md` (SHA256 `c8726176d9a80ee27275884a9facefe1bb8b3d1c12c1590418d3422a0ad17c92`).

All **540 cells** (18 participants × 5 target sessions × 2 windows × 3 actions) are retained: 444 defined and 96 undefined. All **11,460 saved trial predictions** were checked against trial identity, frozen roles, labels, class counts, and reported balanced accuracy (BA). The 22 previously saved conditional contrasts and confidence intervals were independently reproduced. Source/support fit identities and common eligible query identities were checked across windows/actions. Before/after SHA256 checks show the source result tables and protocol manifest were unchanged.

BA is first computed per session, then averaged equally across all five sessions for a participant. A participant with an undefined session has no five-session endpoint; there is no imputation. Cohort means and 95% intervals resample participants 10,000 times with seed 42. Intervals are exploratory, pointwise percentile intervals, without multiplicity adjustment. Trial-level resampling is not used.

The conditional primary scope has **9 participants** (sub-2/3/5/6/8/9/12/14/15); the separately frozen metadata-complete sensitivity has **8**, excluding sub-15 for incomplete phase mapping rather than its observed gain. Both scopes are reported. Development results have 5 participants and remain separate. These are not replacements for the original 12-person main comparison.

## Results

All differences and confidence intervals below are percentage points (pp).

| Scope | Window | Full CSP/LDA − frozen | Full CSP/LDA − LDA only |
|---|---|---:|---:|
| Conditional primary, n=9 | Cue-anchored 5 s | 2.06 [−3.73, 8.17] | 0.17 [−4.63, 4.86] |
| Conditional primary, n=9 | Task-start 2 s | 3.21 [0.08, 6.56] | 2.38 [−1.29, 5.89] |
| Metadata-complete primary, n=8 | Cue-anchored 5 s | 3.98 [−0.90, 9.81] | 1.78 [−2.26, 5.92] |
| Metadata-complete primary, n=8 | Task-start 2 s | 3.46 [−0.02, 7.12] | 3.63 [0.54, 6.68] |

The paired change in the full-minus-frozen gain (task-start 2 s minus cue-anchored 5 s) was **1.15 pp [−5.55, 7.22]** in n=9 and **−0.51 pp [−7.30, 5.23]** in n=8. The corresponding full-minus-LDA-only gain changes were **2.21 pp [−2.31, 6.47]** and **1.85 pp [−3.25, 6.62]**. Every gain-change interval includes zero. A positive interval for an individual window/contrast does not establish that its benefit differs between windows.

Individual full-minus-frozen five-session differences in n=9 ranged from **−13.25 to +18.77 pp** for cue 5 s (4 positive, 5 negative) and **−2.75 to +10.96 pp** for task 2 s (6 positive, 3 negative). In n=8, the ranges were **−2.59 to +18.77 pp** (4 positive, 4 negative) and **−2.75 to +10.96 pp** (5 positive, 3 negative). These are observed participant differences, not proof of individual clinical harm or benefit. All individual values and all development contrasts remain in the CSV/JSON files.

## Coverage and limitations

- `sub-11/ses-4` has only the left class among common eligible queries (20 left, 0 right), so BA is undefined; its six corresponding action/window cells are retained as null. It has no complete five-session endpoint.
- `sub-15/ses-5` has only **5 common eligible query trials (2 left, 3 right)**; 19 other originally included query trials have unknown original phase mapping. The conditional n=9 scope includes this noisy endpoint and marks it prominently. The n=8 sensitivity uses the same saved predictions and removes no other participant on effect size or sign.
- `sub-16`, `sub-17`, and `sub-18` lack online phase mapping, so all their target-session comparison cells are retained as null. In total, 980/7,200 original event rows still lack original phase mapping. No unknown row is assumed to be a noneligible task or a correct mapping.
- Eligibility required a class-matched task end at least 2 s after task start, EDF completeness, and inclusion in the original complete-window set. The 44 originally partial windows remain excluded. End duration may depend on online outcome and speed, so this subset is not an unbiased representation of all trials.
- The comparison jointly changes anchor (cue versus task start), window length (5 s versus 2 s), and window-local filtering edges. It is not a pure intervention on feedback contamination or a causal demonstration of sustained imagery. Queries and available support are matched within this exploratory comparison, but support can be smaller than the original 20-label budget. It cannot isolate which change explains an observed difference.
- Euclidean alignment was not repeated in the phase comparison. No task-aware gate was fitted or validated. No result from this analysis changes an action rule or parameter choice.

## Files and reproduction

- `session_metrics_all540.csv` and `saved_query_predictions_unchanged.csv`: byte-identical copies of the completed consumer's metrics/predictions; nulls remain explicit.
- `participant_endpoints_all108.csv`: every subject/window/action endpoint, including undefined values.
- `analysis_scopes.json`: conditional and completeness scopes, with participant identities.
- `cohort_method_means.csv`, `participant_paired_gains.csv`, and `paired_contrasts_all_scopes.{csv,json}`: participant-level means, paired differences, intervals, and signed individual ranges.
- `execution_receipt.json`: original input hashes, unchanged-state checks, and output hashes. Its recorded executed producer is retained verbatim as `executed_numerical_summary_script.py`.
- Figures and underlying plot data are in `../../phase_figures/run01/`. The figure-generation step reads these summary tables only; it does not rerun bootstraps.

From the repository root, reproduce into a **fresh** output directory:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/summarize_kumar_phase_window_20261016.py \
  --source /workspace/private_model_receipts/paper2-component-followup-20261016/phase_cpu/run01 \
  --frozen-manifest research_logs/kumar_cross_session_20261012/protocol/split_manifest.json \
  --output /path/to/fresh_phase_summary
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/plot_kumar_phase_summary_20261016.py \
  --summary /path/to/fresh_phase_summary --output /path/to/fresh_phase_figures
```

The original numerical execution used the source snapshot retained in this folder. Afterward, the public producer gained a thin optional figure wrapper; its numerical logic and all existing outputs were preserved. These commands are reproduction instructions, not authorization to rerun a scientific consumer.
