# S2 Text. Data provenance and reproducibility

**Updating spatial filters improves limited-label recalibration in a longitudinal motor-imagery EEG dataset**

This supplement explains how to reproduce the reported numerical summaries from S1 Data and locate the records that connect them to the original analyses. S1 Text provides the signal-processing, decoder and statistical definitions.

## 1. Data package and versioned sources

The source EEG is the Kumar2024 derivative at NEMAR nm000177/v1.0.5, DOI 10.82901/nemar.nm000177.v1.0.5 [@nemar177]. Code, configurations and saved results are available at https://github.com/jackzhu119/few-shot-mi-eeg. The scientific snapshot is tagged `paper2-plos-source-20261016`, at content commit `f2901decfc39b2adecae13253ee4b1159a4f9a4b`. The subsequent `paper2-plos-ethics-20261016` revision records the updated ethics statement. The 17 October editorial revision uses the same scientific results and data.

The unchanged [S1 Data package](https://github.com/jackzhu119/few-shot-mi-eeg/blob/paper2-plos-source-20261016/manuscript/plos_one_submission_20261016/S1_Data.zip) contains 69 members and remains in `manuscript/plos_one_submission_20261016/`. Its accompanying [data dictionary](https://github.com/jackzhu119/few-shot-mi-eeg/blob/paper2-plos-source-20261016/manuscript/plos_one_submission_20261016/DATA_DICTIONARY.md) defines fields and units, the [member manifest](https://github.com/jackzhu119/few-shot-mi-eeg/blob/paper2-plos-source-20261016/manuscript/plos_one_submission_20261016/S1_Data_manifest.json) records identities and hashes, and the [reproduction guide](https://github.com/jackzhu119/few-shot-mi-eeg/blob/paper2-plos-source-20261016/manuscript/plos_one_submission_20261016/REPRODUCE_SAVED_RESULTS.md) gives the layout and execution commands. The current manuscript exports are in `manuscript/plos_one_revision_20261017/`. Repository paths in the commands and provenance records below are relative to the checkout root.

| Material | Coverage |
| --- | --- |
| Event metadata | 7,200 identities, including 7,156 complete windows and 44 recording-boundary exclusions |
| Query ledger | 4,320 identities: 4,290 included and 30 partial exclusions |
| Saved predictions | 25,740 rows: three CPU methods and three EEGNet seeds per included query |
| Participant endpoints | 72 participant-by-method rows, each with source-query and five-session target endpoints |
| EEGNet histories | 54 fit summaries, 2,871 epoch-history rows and 8,613 optimizer steps |
| Support and drift measurements | Source-run probes, support-half measurements and session-level drift records |
| Figure and statistical inputs | Four figure source tables and inputs for the four paired checks |

Of the 4,290 included queries, 360 belong to the source session and 3,930 to the five target sessions. The dictionary encodes left hand as 0, right hand as 1 and CPU seeds as `cpu_fixed`. EEGNet seeds are 20261012, 20261013 and 20261014. Raw EEG is obtained from NEMAR; the compact S1 Data reproduction workflow uses numerical tables.

## 2. Reproducing the saved-prediction summaries

Start from a repository checkout of the scientific snapshot above and use Python 3.11 with NumPy 2.2.6. From the repository root, the following commands reproduce the QC summaries in a new directory:

```bash
qc_records=research_logs/kumar_submission_qc_20261015/run01
mkdir qc_text_reproduction_new
cp "$qc_records/POST_OBSERVATION_PROTOCOL.md" qc_text_reproduction_new/
python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs "$qc_records/public_inputs" \
  --output qc_text_reproduction_new
```

The script checks exact trial identity, participant, session, run, role, true label and inclusion status before aggregation. Each included query has all three CPU outputs and all three EEGNet seed outputs. Missing or inconsistent required records produce an explicit error.

The original-input computation and portable replay produced the same 13 scientific QC CSVs byte-for-byte, and all 144 endpoint values matched their saved originals. Separate arithmetic checks covered class eligibility, seed averaging, equal session weighting, participant intervals and influence.

Commands for the paired checks and figure tables are in `REPRODUCE_SAVED_RESULTS.md`. The supplied inputs and expected outputs support checking these summaries without model checkpoints.

The recorded scientific environment was Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2. Source EEGNet fitting used PyTorch/Torchaudio 2.8.0+cu128 and Braindecode 1.2.0; fixed-checkpoint evaluation used the corresponding 2.8.0+cpu packages. Detailed numerical and thread settings are in S1 Text, S10.

## 3. Numerical checkpoints and aggregation rules

Participants are the independent units: six development participants and 12 participants in the predefined primary cohort. The target endpoint gives equal weight to five sessions within each participant. EEGNet first averages its three seeds within each participant/session.

The following values provide compact checkpoints for the saved-result replay. Intervals are the original 95% participant-bootstrap percentile intervals.

| Contrast | Participants | Mean difference, percentage points | 95% interval |
| --- | ---: | ---: | ---: |
| Full refit minus frozen, primary cohort | 12 | +7.42 | [2.49, 12.48] |
| Full refit minus LDA-only, primary cohort | 12 | +5.47 | [2.17, 8.91] |
| LDA-only minus frozen, primary cohort | 12 | +1.95 | [−0.98, 5.09] |
| Full refit minus frozen, unflagged complete cases | 10 | +5.96 | [0.99, 11.24] |

The amplitude sensitivity uses the original maximum-channel peak-to-peak flag of greater than 250 µV. It identifies 922 flagged and 3,368 unflagged queries. Balanced accuracy is defined only when both true classes are present; the target endpoint requires all five session values. Sub-8 and sub-12 lack complete unflagged target endpoints, leaving ten eligible primary participants. The paired unflagged-versus-full sensitivity therefore uses these same ten participants. Pooled-query endpoints and missing-class groups have separate rows in the output tables. The underlying fitted models are shared by the full-query and unflagged-query evaluations.

The four post-review sign-flip checks reproduce Table 5. Their tail counts, in table order, are 80/4,096, 42/4,096, 1,070/4,096 and 78/1,024, using an absolute boundary tolerance of `1e-12` BA. S1 Text, S11 supplies the complete p values, four-test Holm adjustment, sign-symmetry assumption and rounding diagnostics. The original percentile intervals are separate saved estimates.

## 4. Analysis sequence and model provenance

The cohort allocation, original endpoints and CPU comparisons preceded their performance calculations. Development-only support measurements and the separately frozen drift associations retain their original scopes. The QC, training-history and post-review statistical analyses followed exposure to the original query outcomes. QC and paired-check rules were recorded before the additional computations; these follow-up analyses are exploratory.

The CPU baselines, source-only EEGNet fits and fixed-checkpoint evaluation have separate records. The EEGNet ledger combines 18 development and 36 primary-cohort fits, three seeds per participant. Its SHA256 is:

```
013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670
```

The frozen query evaluator ran at commit `d34703ca5bccf7a5b88a91c2ffb2cba893f7cec8`, with contract SHA256:

```
fb3a429776e77a4ee8de96c8c7f2a833a4d311cedd8f0a9bcec3d0c6e8df225a
```

The query audit binds 54 checkpoint archives, 1,189 input files and 4,290 included query identities. Model parameters, batch-normalization buffers and source-normalization statistics were fixed during evaluation. The paper uses all 54 complete JSON training histories; 37 accompanying console logs are empty.

The completed CSP support analysis contains all 240 prescribed source-run fold/rotation pipelines. Its first execution was interrupted by an unavailable procfs monitoring interface; the original attempt and completed recovery are documented in `research_logs/kumar_csp_signed_score_execution_20261015/run01/` and `research_logs/kumar_csp_signed_score_execution_20261015/run02/`. Query provenance is indexed in `research_logs/kumar_frozen_query_execution_audit_20261015/run01/`. QC and training-history records are in `research_logs/kumar_submission_qc_20261015/run01/` and `research_logs/kumar_submission_training_review_20261015/run01/`. Post-review checks, including the numerical-boundary diagnostics and initial rounding assertion, are retained under `research_logs/kumar_review_revision_20261016/run01/`.

## 5. Figure and source interpretation

The four figures use the saved numerical inputs in S1 Data. Fig 4 retains all 180 participant/session contrast cells, including negative and zero values. Participant order, the shared symmetric RdBu scale and the original bootstrap intervals are retained. The figure exports were checked for dimensions, 600 dpi resolution, RGB color and LZW TIFF encoding. The installed figure font was Liberation Sans.

The reported decoding results use the released cue-anchored five-second task windows. The original derivative-marker review and subsequent partial mapping of original event metadata are distinct records. The later reporting addendum documents mapping for 311 of 360 runs and 6,220 of 7,200 event identities; 49 runs and 980 events remained unknown at that stage. This metadata work precedes the planned new phase-specific decoding and does not change the current windows or results. Its scope and coverage are recorded in `docs/kumar_phase_scope_reporting_addendum_20261016.md`.

The source-reading record identifies the original-study Methods, GR/PAR descriptions, results and correction, the relevant full-text data-space adaptation methods, and the abstract-level LDA-adaptation check. It is available in `research_logs/kumar_review_revision_20261016/run01/review_evidence_reading_scope.json`. S1 Text gives the event semantics and literature context used for the scientific interpretation.

## 6. Licensing, ethics and author review records

Original project software is MIT licensed. Original manuscript content, figures and derived results are licensed under CC BY 4.0. `LICENSING.md` and the complete license texts define this scope; source metadata retain their attribution and terms, and third-party software, fonts and CSL styles retain their own licenses. The versioned NEMAR release is the public source-EEG endpoint.

The original acquisition study reported ethical approval from the University of Texas at Austin under protocol 2020-03-0073 and informed consent [@kumar2024]. For this secondary analysis, the author reports that the research administration office at Chongqing Medical University confirmed on 16 October 2026 an exemption from additional ethical review under Article 32, item (1), of the 2023 Chinese ethics-review measures [@china2023ethics]. No reference number was issued. The office name is a descriptive translation, and the confirmation is recorded through the author's report; no institutional document was supplied for this record. The main Methods distinguishes this additional-review exemption from the original collection approval and consent.

OpenAI ChatGPT/Codex assisted with software and validation, saved-result aggregation, figures, source and reference checks, manuscript drafting and editing, and document exports. The author reviewed the scientific content and remains responsible for the work.

The author's personal reading, checking and approval on 16 October 2026 concern scientific content commit `f2901decfc39b2adecae13253ee4b1159a4f9a4b`. The confirmation is preserved at commit `1a7e1ab8b6253db52544ba185abb33a6bcb4937b`, in `research_logs/kumar_author_final_confirmation_20261016/run01/README.md`. This dated approval identifies the earlier scientific snapshot; the 17 October text and exports are the subsequent editorial revision. Earlier manifests, accepted model ledgers and execution records remain available through the versioned sources and evidence paths above.

## References

::: {#refs}
:::

