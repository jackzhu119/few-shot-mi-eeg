# Reproduce the saved-prediction QC sensitivity

This entry performs text-only postprocessing. It cannot load models, fit them,
read EEG arrays or perform a new forward pass. Requires Python 3.11 and NumPy
2.2.6 for the recorded bootstrap arithmetic; all other imports are standard
library. The existing project CPU environment already provides them.

From the repository root, choose a **new** output directory. Existing numerical
outputs are never overwritten. The actual original computation used:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --root /workspace/few-shot-mi-eeg \
  --eeg-results /workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results \
  --output research_logs/kumar_submission_qc_20261015/run01
```

That historical output already exists; do not repeat that exact destination.
For public reproduction, only the compact `public_inputs` directory is required:

```bash
mkdir qc_reproduction
cp research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md qc_reproduction/
python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs research_logs/kumar_submission_qc_20261015/run01/public_inputs \
  --output qc_reproduction
```

The same command works after relocating the script, protocol and public input
directory by adjusting these paths. A Git checkout is not required in portable
mode; `reference_git_commit` then truthfully records `not_a_git_checkout`.
The portable mode validates every compact file's SHA256/length, all exact
trial/label/QC joins and all method/seed/participant coverage before scoring.
The original-input mode additionally checks historical private-backup receipts
against original saved prediction bytes. Public reproduction does not assert a
new private-backup readback, nor require credentials or private weights.

## Compact public input dictionary

- `frozen_trial_metadata.json`: all 7,200 frozen event identities, including the
  44 historical exclusions, source partition roles, release identity/session/run,
  original left/right label, Boolean inclusion, original exclusion reason,
  original fixed raw peak-to-peak amplitude/flag, and source-file provenance.
  Partial-window QC entries may be null and are never scored.
- `saved_predictions.csv`: 25,740 exact stored predictions for 4,290 complete
  query identities × (three CPU methods + three EEGNet seeds). `label` and
  `prediction` use left=0/right=1. `seed=cpu_fixed` identifies the CPU fit;
  EEGNet uses 20261012/20261013/20261014. The QC flag is copied from frozen
  metadata and checked again on read. There are no EEG samples or weights.
- `frozen_analysis_configuration.json`: exact original configuration text;
  frozen threshold/statistic checks fail if the convention changes.
- `original_participant_endpoints.csv`: 72 saved participant × method endpoints
  for reconstruction agreement. These are historical originals, not replacements.
- `public_input_provenance.json`: lengths/SHA256 for the four compact files;
  original source file hashes and relative identities; derivation and rights
  attribution. The metadata/predictions derive from NEMAR nm000177 v1.0.5 under
  CC BY 4.0, not a newly collected human dataset.

## Output dictionary

- `query_identity_qc_ledger.csv`: 4,320 source/target query identity rows,
  including all 30 excluded queries and their original reasons.
- `all_role_qc_counts.csv`: complete/partial/flagged counts for every frozen
  participant/session/role combination, including zero-count combinations.
- `joined_saved_predictions_qc.csv`: the strictly joined 25,740 predictions.
- `per_seed_session_and_pooled_metrics.csv`: separate CPU/EEG seed metrics for
  each subset and each session or pooled query scope, with all confusion cells,
  true/predicted class counts and missing-class reasons.
- `per_participant_session_metrics.csv`: same scopes after averaging all three
  EEG seed BAs; class counts are **unique trials**, never multiplied by seeds.
- `participant_endpoints.csv`: equal-five-session target endpoint eligibility,
  exact missing sessions, source BA, pooled BA and retained low-count counts.
- `cohort_method_sensitivity_summary.csv`: development6, remaining12 and all18
  separately, with actual eligible participant identities and percentile CIs.
- `paired_session_contrasts.csv`, `paired_participant_contrasts.csv`: original
  primary full-minus-frozen and secondary full-minus-LDA contrasts in each
  subset, retaining undefined rows.
- `cohort_paired_contrasts.csv`: participant-unit contrast summaries and signs.
- `participant_cross_subset_changes.csv`, `paired_cross_subset_summary.csv`:
  matched complete-case QC changes, explicitly identifying the intersection.
- `leave_one_participant_out_influence.csv`: deterministic influence rows for
  every eligible participant and both CPU contrasts; not an exclusion rule.
- JSON receipts: exact input hashes, join/endpoint reconstruction checks,
  runtime versions, protocol/code hash, failure status and portable replay.

The synthetic tests are:

```bash
python -m pytest -q tests/test_kumar_saved_query_qc_20261015.py
ruff check scripts/analyze_kumar_saved_query_qc_20261015.py tests/test_kumar_saved_query_qc_20261015.py
```

The protocol was recorded after prior results were visible; these new results
remain exploratory. Missing BA values are blank in CSV and null in JSON, never
replaced with chance or zero. A seed/session with no queries has no defined
collapse assessment; aggregate collapse counts should not be interpreted as
evidence of successful class coverage when `BA_defined` is false.
