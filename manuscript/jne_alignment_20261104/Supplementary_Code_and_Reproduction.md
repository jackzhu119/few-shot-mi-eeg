# Code and reproduction

**Description:** File index, fixed code and data links, checksums, field definitions and saved-result-only reconstruction instructions.

## Data delivery and fixed scientific version

This supplement accompanies the author-approved JNE article. The present delivery converts saved data to standalone CSV files; it creates no model, query prediction or new statistical estimate. Scientific definitions, participant units, exclusions, numerical values and the author approval are retained.

The fixed scientific/code/input snapshot is [the approved repository version](https://github.com/jackzhu119/few-shot-mi-eeg/tree/407e6ce0a17339d5808a7acc14e9745b9dceffbd), commit `407e6ce0a17339d5808a7acc14e9745b9dceffbd`. Original machine-readable files and the complete earlier data/code archive remain available there. That historical archive has 1,471 members; these direct-upload files are a documented selection and lossless conversion, rather than a claim that every historical file is embedded.

The source recordings remain at NEMAR nm000177/v1.0.5 and the original BNCI2014-001 source, with its verified NEMAR nm000139/v1.0.3 mirror. No raw EEG, model weights or credentials are supplied in these CSV files.

## Read the standalone CSV files

Each CSV contains two initial metadata records: #title and #description. The third record is the actual data header. Skip the first two records when reading data. Their removal recovers the exact verified CSV data section, including original decimal strings and empty fields. The two prediction data sections are byte-identical to their decompressed frozen source files.

```python
import csv
import json

with open(
    'Supplementary_Results.csv',
    encoding='utf-8', newline=''
) as f:
    next(f)  # title metadata record
    next(f)  # description metadata record
    result_cells = list(csv.DictReader(f))

# pandas: pd.read_csv(path, skiprows=2,
#                     dtype=str, keep_default_na=False)
# Saved_Records.record_json is parsed with json.loads; no eval is used.
```

CSV field strings retain their source precision. Spreadsheet software can coerce long decimals when importing or saving CSV; the optional public XLSX copy stores all fields as text. Keep the supplied CSV files unchanged for numerical reproduction.

### Result tables

Supplementary_Results.csv uses the fields table_id, row, column, field and value. Row and column are one-based data coordinates. It contains 238,401 cells from 56 sources: two main tables, 27 supplementary tables, 17 full-precision statistical CSVs and ten figure-source CSVs. Manuscript tables keep their display precision and text markers; the separate statistical-source rows preserve the original full decimal strings. The INDEX below maps every table ID to its original file.

### Saved predictions and records

Supplementary_Budget_Predictions.csv contains 78,600 saved chronological-budget prediction rows. Supplementary_Phase_Predictions.csv contains 11,460 saved cue/task-window prediction rows. Original trial IDs, labels, methods, budgets and eligibility representations are retained.

Supplementary_Saved_Records.csv has 2,952 records. Its columns are source_id, source_path, record_type, source_row and record_json. The 612 JSON documents comprise 36 original BNCI prediction files and 576 sensitivity cells; the latter retain 544 completed and 32 undefined cells. The remaining 2,340 records are the 1,800 budget-session and 540 phase-metric rows. JSON objects are serialized canonically; original formatting bytes can differ, while parsed values and nested arrays are retained. Original source-file checksums are in the public input index.

These files collectively contain 118,240 repeated, method-specific CSP/LDA prediction values, including 4,320 original BNCI, 20,040 matched-control and 3,820 new phase values inside JSON vectors. These are not unique participants or independent trials. The complete historical neural, geometric and synthetic raw exports retain their original public packet locations; their saved summaries and figure data are included in the result tables, rather than relabeled as new trial predictions.

## Fixed code and saved-result reconstruction

Use the recorded science dependencies: Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2. Formatting uses a separate document/plot interpreter. No environment or model retraining is needed to inspect the supplied files.

From a checkout of the fixed scientific snapshot, the previously validated saved-result command is:

```bash
p=scripts/reproduce_paper2_alignment_saved_results_20261104.py
python "$p" --output /tmp/jne-reproduction-new
```

Use an unused output directory. That command rebuilds 17 result CSVs from saved predictions/cell records and checks them against the saved tables. It loads no EEG or checkpoint and performs no model fit or query forward. Its actual earlier reproduction receipts remain in the fixed scientific repository; the present format conversion does not claim to repeat all experiments.

Relevant fixed source files:

- [Saved-result reproduction entry](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/scripts/reproduce_paper2_alignment_saved_results_20261104.py)
- [Saved-prediction analysis](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/scripts/analyze_paper2_alignment_integrated_20261104.py)
- [Independent numerical check](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/scripts/check_paper2_alignment_integrated_20261104.py)
- [Source/data lineage](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/data_lineage.json)
- [Input manifests and saved result tables](https://github.com/jackzhu119/few-shot-mi-eeg/tree/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104)

Historical V2 raw results: [fixed public packet](https://github.com/jackzhu119/few-shot-mi-eeg/tree/407e6ce0a17339d5808a7acc14e9745b9dceffbd/training_status/paper2-recalibration-v2/result_exports/f1689db3941ae31757442698). Historical V3 raw results: [fixed public packet](https://github.com/jackzhu119/few-shot-mi-eeg/tree/500831c086d9e1d1e8412cf8ebca5fb6a288db76/training_status/paper2-discovery-v3/result_exports/83cbdfdcfa541b3ab3addfc3). Trial QC and all-event phase mapping retain their original paths in the fixed source snapshot.

## Direct CSV checksums

Checksums below refer to the complete upload CSV, including its two metadata records. Full output/source mappings, headers and source hashes are supplied as INPUT_INDEX.json in the public repository next to the direct-upload validation records.

**Supplementary_Results.csv**

Bytes: 7547342; data records begin after two metadata records. SHA256: `3fa9bb98a3d340a8e4e41b65e0a15c76c338ebb1853d8eabfa27f208c17d1c54`.

**Supplementary_Budget_Predictions.csv**

Bytes: 8381461; data records begin after two metadata records. SHA256: `661ba41be38490024a7a49989de0b16e1fecfdcf49017f4d4c83a144c594d637`.

**Supplementary_Phase_Predictions.csv**

Bytes: 840080; data records begin after two metadata records. SHA256: `655d3a8110034b01b3fbcf23e55f7468ec0a49eaa7ef79ab8b06838e295a622f`.

**Supplementary_Saved_Records.csv**

Bytes: 7731686; data records begin after two metadata records. SHA256: `6ad3d54f2b2d59711cd39688b8a50690e4edbefb543d79b1d75f88bda7c612e1`.

## Result-source index

M01–M02 identify the main tables; S01–S27 the supplementary tables; A01–A12 and C01–C05 the statistical CSVs; F01–F10 the figure-data tables. Source headers occur in the CSV field column, and full source paths, dimensions and byte hashes are in INPUT_INDEX.json.

**M01: Main_Table_1** — 4 data rows, 5 columns.

Original source: [MAIN.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/MAIN.md). SHA256: `cae2ada330e4e917a6db09cdae24889be5f030b000292d3378ec69aaba7c4fac`.

**M02: Main_Table_2** — 7 data rows, 5 columns.

Original source: [MAIN.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/MAIN.md). SHA256: `cae2ada330e4e917a6db09cdae24889be5f030b000292d3378ec69aaba7c4fac`.

**S01: Supplement_Table_1** — 4 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S02: Supplement_Table_2** — 9 data rows, 2 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S03: Supplement_Table_3** — 8 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S04: Supplement_Table_4** — 30 data rows, 7 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S05: Supplement_Table_5** — 9 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S06: Supplement_Table_6** — 10 data rows, 7 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S07: Supplement_Table_7** — 4 data rows, 6 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S08: Supplement_Table_8** — 6 data rows, 3 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S09: Supplement_Table_9** — 5 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S10: Supplement_Table_10** — 5 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S11: Supplement_Table_11** — 5 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S12: Supplement_Table_12** — 5 data rows, 3 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S13: Supplement_Table_13** — 5 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S14: Supplement_Table_14** — 5 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S15: Supplement_Table_15** — 5 data rows, 3 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S16: Supplement_Table_16** — 5 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S17: Supplement_Table_17** — 5 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S18: Supplement_Table_18** — 5 data rows, 3 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S19: Supplement_Table_19** — 5 data rows, 7 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S20: Supplement_Table_20** — 4 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S21: Supplement_Table_21** — 16 data rows, 7 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S22: Supplement_Table_22** — 4 data rows, 7 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S23: Supplement_Table_23** — 9 data rows, 6 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S24: Supplement_Table_24** — 5 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S25: Supplement_Table_25** — 16 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S26: Supplement_Table_26** — 12 data rows, 5 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**S27: Supplement_Table_27** — 6 data rows, 4 columns.

Original source: [SUPPLEMENT.md](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/SUPPLEMENT.md). SHA256: `966125f2d936bb6c960b7143d9466c522c8b63ee050798ab464490987ff53f61`.

**A01: cohort_contrasts** — 1045 data rows, 21 columns.

Original source: [cohort_contrasts.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/cohort_contrasts.csv). SHA256: `54e1152aaf20137bf6cf62a1712442f1a8d48453f43b7374ebffa9b54d814211`.

**A02: cohort_method_metrics** — 380 data rows, 21 columns.

Original source: [cohort_method_metrics.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/cohort_method_metrics.csv). SHA256: `fb9bf900e183b86b207b989be5b297129d932c24a69dd0d2a7d218f3fb1c28c7`.

**A03: cohort_run_effect_distribution** — 60 data rows, 20 columns.

Original source: [cohort_run_effect_distribution.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/cohort_run_effect_distribution.csv). SHA256: `f269ffd14b7abc4d8f1c5a6a7059ca527c679c33b8c387df9975e89cb68581c7`.

**A04: endpoint_metrics** — 2196 data rows, 22 columns.

Original source: [endpoint_metrics.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/endpoint_metrics.csv). SHA256: `aceb553054887e0aa2a36b210591c28f3ffb8345d5961e25d8ab411c504b04cb`.

**A05: endpoint_transitions** — 2745 data rows, 18 columns.

Original source: [endpoint_transitions.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/endpoint_transitions.csv). SHA256: `7647cda30a14c944962e0140d6a0ab88516b0a281a429ec6f2143bf6676d198e`.

**A06: joint_benefit_distribution** — 855 data rows, 13 columns.

Original source: [joint_benefit_distribution.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/joint_benefit_distribution.csv). SHA256: `d9e6223fe6cbb4bab57a1ed32589b777c674db73f125f8309ebfac0e970373e8`.

**A07: participant_contrasts** — 585 data rows, 20 columns.

Original source: [participant_contrasts.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/participant_contrasts.csv). SHA256: `fad8ff38c6d6e7fdce0c89c281a8f9b7f9a1050e66dda15e68ca846d491a09a5`.

**A08: participant_metrics** — 468 data rows, 14 columns.

Original source: [participant_metrics.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/participant_metrics.csv). SHA256: `b0d7367d620510da5c0c70617185872ed2f9fcee66f5287bf42c37e55a5b381b`.

**A09: participant_run_effect_distribution** — 135 data rows, 9 columns.

Original source: [participant_run_effect_distribution.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/participant_run_effect_distribution.csv). SHA256: `3ca03d8c76214c7ed316ebb674314a52e7d7de376b267a3426e683df352bb7c7`.

**A10: qc_same_eligible_comparisons** — 405 data rows, 23 columns.

Original source: [qc_same_eligible_comparisons.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/qc_same_eligible_comparisons.csv). SHA256: `d8ba827e2899e7d1fc691f24e831a51e93b4f8f9be8593dd8d3171447e580c65`.

**A11: query_run_contrasts** — 1215 data rows, 17 columns.

Original source: [query_run_contrasts.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/query_run_contrasts.csv). SHA256: `42f863ffa623e00a7359ebefa8c0a9e949d79f093b2e71b04ee3844ff53634ee`.

**A12: query_run_metrics** — 972 data rows, 18 columns.

Original source: [query_run_metrics.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/analysis/query_run_metrics.csv). SHA256: `00e9707de291d5803b440e95d4122b18b2e2d1a0ebd448a0ac0afeb57a0cb760`.

**C01: cohort_comparisons** — 168 data rows, 19 columns.

Original source: [cohort_comparisons.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/mechanisms/cohort_comparisons.csv). SHA256: `26b3f7ac34ecfe9a48a513d4f5f943c81aa572285232a3530c629e1c3481ab6e`.

**C02: cohort_means** — 112 data rows, 8 columns.

Original source: [cohort_means.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/mechanisms/cohort_means.csv). SHA256: `ad9ec16c969d676cce3c6f813db7b0cf5b20e2521db1dab0fa44de1aaaceeb9b`.

**C03: participant_metrics** — 180 data rows, 12 columns.

Original source: [participant_metrics.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/mechanisms/participant_metrics.csv). SHA256: `80578fa9b7462bbcb36b30104df9644782b4eb9006aa666ca513dc740b1c0606`.

**C04: phase_cohort_comparisons** — 12 data rows, 11 columns.

Original source: [phase_cohort_comparisons.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/mechanisms/phase_cohort_comparisons.csv). SHA256: `4088037ef8e3c68f925d9939c4e29a924a7f8dd50fe060373beb63bedb2752e2`.

**C05: phase_participant_metrics** — 36 data rows, 10 columns.

Original source: [phase_participant_metrics.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/research_logs/paper2_alignment_integrated_20261104/mechanisms/phase_participant_metrics.csv). SHA256: `e395dbed3756473fa8c8d54731c012e56e7675bc3ce3829ec2a82c7b0c62e12e`.

**F01: Fig1_workflow** — 12 data rows, 13 columns.

Original source: [Fig1_workflow.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig1_workflow.csv). SHA256: `07286bcfbdcb0c2e0e2e4aaed686af42f356d2f6dfde847fe10e214b402cd864`.

**F02: Fig1_workflow_edges** — 11 data rows, 5 columns.

Original source: [Fig1_workflow_edges.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig1_workflow_edges.csv). SHA256: `d526939d99ff032b52f6418f19f4a01cc72046934f20ba01cdb7e164f596ca06`.

**F03: Fig1_workflow_nodes** — 7 data rows, 6 columns.

Original source: [Fig1_workflow_nodes.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig1_workflow_nodes.csv). SHA256: `d115cce44412c348e57e376117fbab7fd910fab50fa03edc0046ee57d61a3af7`.

**F04: Fig2_performance** — 98 data rows, 13 columns.

Original source: [Fig2_performance.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig2_performance.csv). SHA256: `4e83341ed2837e3d458d8a29a9c15498fd4fd684389ea971a8fadedd82e01eaf`.

**F05: Fig3_error_coverage** — 92 data rows, 13 columns.

Original source: [Fig3_error_coverage.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig3_error_coverage.csv). SHA256: `e620a927c1a58dfe2aa22c45b65cd88bbb69e1fad0329e4a59ff5065cf78d893`.

**F06: Fig4_budget** — 25 data rows, 13 columns.

Original source: [Fig4_budget.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig4_budget.csv). SHA256: `a7fdf675bc97d8e948f612fcba000da1fd22f4719e666b917691305a7812d9d9`.

**F07: Fig5_mechanisms** — 107 data rows, 13 columns.

Original source: [Fig5_mechanisms.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/figures/Fig5_mechanisms.csv). SHA256: `a9917f9a653f0aaf5e486888d6ebdebcc2ac5a9de829685648b85f751e4c9ed6`.

**F08: FigS1_source_data** — 104 data rows, 21 columns.

Original source: [FigS1_source_data.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/supplementary_figures/FigS1_source_data.csv). SHA256: `bd0115b0106bd83dca490768c9f0a5ce529a5bbe4f78aa66e9cd0d43d125a414`.

**F09: FigS2_source_data** — 64 data rows, 12 columns.

Original source: [FigS2_source_data.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/supplementary_figures/FigS2_source_data.csv). SHA256: `9a021afba4e2b9eadea08c817eeac652a47ae68269ae6a68647ad351b3b3983e`.

**F10: FigS3_source_data** — 774 data rows, 21 columns.

Original source: [FigS3_source_data.csv](https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/407e6ce0a17339d5808a7acc14e9745b9dceffbd/manuscript/jne_alignment_20261104/supplementary_figures/FigS3_source_data.csv). SHA256: `648713a1f5d5d3d20c8086813625e7d4c8999c12977ddc746e45b7035c5bff13`.

## Licenses and scope

Original project code follows MIT. Original derived data and manuscript/figure content follow CC BY 4.0 within LICENSING.md. Original EEG and third-party components keep their own terms; the citation style retains its separate CC BY-SA attribution. These files do not relicense original recordings or third-party software. Participant-level statistical units, previously exposed analysis scopes, undefined endpoints and negative/null results remain as reported.
