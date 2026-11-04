# Local Paper2 input and implementation audit

Observed on 2026-11-04 UTC (2026-11-03 in the client timezone, America/Los_Angeles). The inspected baseline was `da2a3acee24746981bbcdd779ab88132da6e24c4`. This task only read existing files, inspected schemas, calculated file hashes and checked fixed trial identities. It did not compute new outcome metrics, fit models, perform a forward pass or operate HPC/Pod resources.

## Ready P1 inputs

- Kumar original budget trial predictions: `research_logs/paper2_structure_revision_20261029/component_replay/input/budget/query_predictions.csv.gz`; 78,600 saved rows, subject/session/run/budget/k/method/trial_id, binary label/prediction, reuse/fallback/synthetic flags. Four methods, budgets 4/8/12/16/full. These deterministic classical fits have no seed dimension.
- Budget session metadata: sibling `session_metrics.csv.gz`, 1,800 cells; actual support19/20 retained under full.
- Phase predictions and metrics: sibling `input/phase/`; 11,460 saved rows and540 cells. Only Frozen/LDA-only/Full exist here; no saved EA phase results. Actual source IDs/common-trial membership are in phase metrics.
- BNCI four-method predictions: `research_logs/paper2_external_validation_20261027/saved_predictions/bnci001-sub-XX/E__n20__{frozen,lda_only,full_csp,ea_csp}.json`; 36 files with trial_ids, y and prediction. Corresponding `trial_identity/*/manifest.json` supplies acquisition and role metadata.
- The above original predictions contain hard labels, not probability columns/logits. Balanced NLL/Brier cannot be inferred from them. A separately specified saved-state/signal replay could reconstruct original LDA scores but was not executed in this input audit.
- Kumar QC: `research_logs/kumar_submission_qc_20261015/run01/public_inputs/frozen_trial_metadata.json`; all7,200trial identities with raw-channel peak-to-peak flags. `query_identity_qc_ledger.csv` is also available. Exact frozen role metadata is in `research_logs/kumar_cross_session_20261012/protocol/split_manifest.json`.

The role manifest has7,156 complete windows:720 source TRAIN,360 source validation,360 source-query,1,786 target support and3,930 target-query. The classification map is left=0/right=1. Query/support IDs are deterministic whole-run identities, not label-selected samples. Source labels are40 per Kumar participant, BNCI96; support is full available first-run19/20 for Kumar or20 for BNCI.

## Actual local signals and P2 feasibility

All2,705paths in the frozen Kumar official selection manifest exist under `data/public_eeg/kumar2024/nm000177/v1.0.5`, and every file length matches. This audit does not claim a new full-byte hash check of the entire raw tree. Use the pinned loader's per-input checks when materializing arrays.

`src/learning_preserving_bci/datasets/kumar.py::load_subject` provides fixed22-channel CAR,8–30Hz epoch-local zero-phase filter and512→128Hz resampling to22×640float32. Load a subject once, then reuse that tensor for all fixed arms. No source/validation/query role may be redefined by the new analysis.

Actual ready six-development-subject NumPy shards are also at `/workspace/paper2_hpc_v2_delivery/inputs/kumar_cue5s_v1/sub-{1,4,7,10,13,16}/`. Each subject has source_train/validation/query, current-session support/query and a `preparation_receipt.json` binding the original config/split/adapter and each prepared output hash. This cache covers only the six development IDs; the remaining12 require the original loader. The cache was located, not used as a new validation pass.

All nine BNCI prepared directories exist at `/workspace/private_external_validation/bnci001-v1-20261027/prepared/bnci001-sub-XX/`. `source_train.npz`, `support.npz` and `query.npz` contain x/y/trial_id/run_id and have been fully hashed in INPUT_MANIFEST. No array values were loaded by this audit. They preserve recorded reference,250Hz,8–30Hz continuous-run zero-phase filtering, and cue0–4s epochs. They can be reused without re-downloading or filtering the MAT files.

The actual phase mapping exists at `research_logs/kumar_component_followup_20261016/event_mapping/timing_partial_run05/all_7200_trial_mapping_including_missing.csv`, pinned by `configs/kumar_phase_window_exploratory_20261016.json`. Existing `select_common_trials`, `preprocess_window` and `materialize_window_arrays` in `scripts/run_kumar_phase_window_cpu_20261016.py` define the partial2s task-start eligibility. Missing markers must remain missing. Both Full and EA should use the same retained source/support/query identities at each window; source/Full sensitivity fits should be new-version outputs rather than replacements of old models.

## Original EA/Full implementation comparison

Kumar original Full and EA share raw22channelCAR data, source/current-support fit IDs and the same downstream factory (`CSP4`, Ledoit–Wolf, no trace normalization, log-average-power; LDA lsqr/auto). EA explicitly forms an unregularized ddof1 pooled reference in a fixed21×22Helmert CAR basis, uses separate source/support inverse roots (condition≤1e12), then reembeds22dimensions for that factory. Full passes CAR22 directly to MNE with automatic rank handling. This is an explicit numerical/rank-coordinate difference worth checking with shared21coordinate sensitivity, not proof that the historical code is erroneous.

BNCI original Full/EA are fixed-shrinkage NumPy comparators in `experiments/hpc_recalibration_v2/hpc_recalibration/classical.py`. CSP averages per-trial trace-normalized covariances, then uses shrinkage.1; LDA shrinkage.1. EA reference is the mean non-trace-normalized ddof1 covariance plus.1shrinkage. Its query whitener is fixed from support. These are distinct estimators/preprocessing/source budgets from original Kumar; keep historical dataset-specific results separate.

The existing `fit_decoder(source,support,method,config,source_model)` API has no query argument. It provides a useful isolation pattern for new matched Full/RMS/diagonal/EA arms. The diagonal coordinate system must be fixed explicitly; CAR-effective coordinates do not mean independent electrode scaling.

## P0 access audit executed now

`FIT_SCOPE_CHECK.json` independently checks the1,800 original budget fit-access rows, including450EA cells and90full-supportEA cells. Every fit list equals fixed source TRAIN plus current chronological support prefix; every EA reference exactly equals its source/current prefix; all query IDs have the proper target-query role and are disjoint from fit IDs. Source validation is absent. Four core saved CSV/JSON SHA256 values match the original execution receipt. The extra180half-support rows are counted separately and not relabeled as budget cells.

## Outputs and scope

- `INPUT_MANIFEST.json`:105 actual source files, full measured hashes and schemas, plus raw-tree existence/length audit; no EEG or model bytes copied.
- `input_files.csv`:compact inventory for the parent's lineage/reuse ledger.
- `FIT_SCOPE_CHECK.json`:executed identity/fit/reference scope validation, not scientific performance recomputation.

Scientific Python metadata was measured in `/workspace/.venvs/few-shot-mi-eeg`:Python3.11.16, NumPy2.2.6, SciPy1.15.3, scikit-learn1.7.2, MNE1.10.2. The default system Python is separate and lacks MNE metadata; use the existing science venv for actual original-pipeline operations.
