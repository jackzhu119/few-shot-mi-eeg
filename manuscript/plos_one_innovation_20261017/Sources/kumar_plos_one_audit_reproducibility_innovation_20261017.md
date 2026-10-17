# S2 Text. Data provenance and reproducibility

**Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**

This supplement connects the manuscript's numerical results to their source data and reproducible computations. S1 Text defines the scientific methods; S1 Data supplies the saved predictions, metadata, original summaries and 17 October component analyses.

## 1. Source versions and analysis coverage

The source EEG is Kumar2024 at NEMAR nm000177/v1.0.5, DOI 10.82901/nemar.nm000177.v1.0.5, under CC BY 4.0 [@nemar177]. The repository is https://github.com/jackzhu119/few-shot-mi-eeg. The original scientific snapshot is tagged paper2-plos-source-20261016, content commit f2901decfc39b2adecae13253ee4b1159a4f9a4b. The institutional-exemption update is tagged paper2-plos-ethics-20261016. The present extension starts from research-branch commit 30f23ed3c9afd271a3821fceaa99ab932bf25e5f and is supplied in manuscript/plos_one_innovation_20261017/.

The original 69-member S1 Data archive is retained in its dated directory. The new S1 Data preserves those original member bytes and adds the prediction-transition analysis, underlying tables, code and updated reproduction guidance. Its accompanying manifest distinguishes original and added members and records their SHA-256 hashes. The manuscript, scientific supplement, reproduction supplement and figure captions identify the added analyses consistently.

| Material | Coverage |
| --- | --- |
| Event ledger | 7,200 identities; 7,156 complete windows and 44 boundary exclusions |
| Query ledger | 4,320 identities; 4,290 included and 30 partial exclusions |
| Saved predictions | 25,740 rows; three CPU methods and three neural seeds for each included query |
| Original endpoints | 72 participant/method rows, each with source and target endpoints |
| Neural histories | 54 fits, 2,871 epochs and 8,613 optimizer steps |
| Calibration measurements | Source-run probes, support-half measurements and session drift records |
| Added component analyses | Three CPU contrasts, both true classes, every participant and target session |
| Figure data | Four original figure datasets and two new component-analysis datasets |

Of the 4,290 included queries, 360 belong to the source session and 3,930 to target sessions. The dictionaries encode left as 0 and right as 1; CPU seed labels are cpu_fixed, and neural seeds are 20261012, 20261013 and 20261014. The source/support/query role assignments and all original predictions are shared between the original report and this extension.

## 2. Reconstructing the original saved-result summaries

In S1 Data, inputs/ contains predictions, the frozen metadata, the original endpoint values and configuration records. code/ contains the original QC and paired-statistics postprocessors. REPRODUCE_SAVED_RESULTS.md provides their exact command-line options and the original directory layout. The corresponding repository input directory is research_logs/kumar_submission_qc_20261015/run01/public_inputs/.

For the QC postprocessor, the documented repository command is:

```bash
mkdir qc_text_reproduction_new
cp research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md \
  qc_text_reproduction_new/
python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs research_logs/kumar_submission_qc_20261015/run01/public_inputs \
  --output qc_text_reproduction_new
```

The original portable replay reproduced all 13 scientific QC CSVs byte-for-byte and reconstructed all 144 source/target endpoint values. The identity checks cover participant, session, run, role, true label, inclusion and QC status. Every included query has all three CPU outputs and all three EEGNet seed outputs.

The original scientific environment was Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2. Source EEGNet fitting used PyTorch/Torchaudio 2.8.0+cu128 and Braindecode 1.2.0; fixed-checkpoint evaluation used the corresponding 2.8.0+cpu packages. S1 Text, S10 records the numerical and thread settings. The new saved-prediction analysis records its own actual runtime separately in its execution receipt.

## 3. Reproducing the new component analyses

After extracting the new S1 Data archive, run the following from its root:

```bash
python code/analyze_kumar_update_mechanisms_20261017.py \
  --inputs inputs \
  --output reproduced_extension
```

The analysis uses the portable saved-prediction and metadata tables. It reconstructs paired class counts and endpoint values, computes all three CPU prediction-transition contrasts, and produces class-recall, session-profile and participant-influence summaries. Each participant has equal weight; the target endpoint equally averages the five sessions. Pointwise bootstrap intervals resample participants with seed 42 and 10,000 replicates. Both positive and negative values remain in the complete output tables.

The extension's input hashes, analysis definition, runtime record and independent arithmetic check accompany its result tables. Figure data are supplied as ordinary CSV files. The figures are drawn from these results; the source values can be inspected without a plotting library or model checkpoint. The correction and introduced-error contributions are class-balanced fractions of all true-class queries, as defined in S1 Text, S12.

## 4. Numerical checkpoints

The first three rows below retain the original participant-bootstrap intervals. The new decomposition and class-recall values reconstruct those contrasts from individual saved decisions.

| Quantity in the primary cohort | Value in percentage points |
| --- | ---: |
| Full refit minus frozen | +7.42 [2.49, 12.48] |
| Full refit minus LDA-only | +5.47 [2.17, 8.91] |
| LDA-only minus frozen | +1.95 [−0.98, 5.09] |
| Full versus LDA-only correction contribution | 16.04 |
| Full versus LDA-only introduced-error contribution | 10.57 |
| Full versus LDA-only left recall change | +6.16 |
| Full versus LDA-only right recall change | +4.78 |
| Component mean after single-participant deletion | +4.39 to +6.28 |

The mean component contrast is 73.7% of the mean total contrast. This is the ratio of the two cohort means after the specified participant/session aggregation. The five target-session component means are +3.52, +5.20, +4.13, +4.18 and +10.33 points.

The amplitude sensitivity uses the original maximum-channel peak-to-peak flag greater than 250 µV. It identifies 922 flagged and 3,368 unflagged included queries. Sub-8 and sub-12 lack complete unflagged five-session endpoints because the required true-class coverage is absent. In the remaining ten primary participants, full-minus-frozen is +5.96 points [0.99, 11.24] and full-minus-LDA-only is +3.82 [1.11, 6.72]. The same-ten full-query values are +6.50 and +4.53 points.

The four original exploratory sign-flip checks retain tail counts 80/4,096, 42/4,096, 1,070/4,096 and 78/1,024, using absolute boundary tolerance 1e-12 BA. S1 Text, S11 records the exact p values, four-test Holm adjustment and numerical-boundary diagnostics. These values and the original percentile intervals retain their respective reference constructions.

## 5. Model and execution provenance

The EEGNet ledger comprises 18 development and 36 primary-cohort fits, three seeds per participant. Its SHA-256 is:

```
013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670
```

The fixed-query evaluator used commit d34703ca5bccf7a5b88a91c2ffb2cba893f7cec8, with contract SHA-256:

```
fb3a429776e77a4ee8de96c8c7f2a833a4d311cedd8f0a9bcec3d0c6e8df225a
```

The query audit links 54 checkpoint archives, 1,189 input files and 4,290 included query identities. Evaluation retained fixed parameters, batch-normalization buffers and source-normalization statistics. All 54 JSON training histories are available, including the complete selected-epoch and stopping records. The CSP support analysis completed all 240 specified source-run fold/rotation pipelines.

The original execution records remain under research_logs/kumar_frozen_query_execution_audit_20261015/, research_logs/kumar_submission_qc_20261015/, research_logs/kumar_submission_training_review_20261015/ and research_logs/kumar_review_revision_20261016/. The added analysis is recorded under research_logs/kumar_update_mechanisms_20261017/run01/. Earlier interrupted attempts and their recovery records remain versioned alongside the completed operations.

The separate task-phase metadata mapping currently covers 311/360 runs and 6,220/7,200 events. The recorded coverage table retains 49 unresolved runs and 980 events. The decoding results in this paper use the original cue windows. Label-budget, alignment and phase-specific follow-ups are described in their separate protocols; the reported completed-experiment evidence is the original decoding study and the saved-result analyses listed here.

## 6. Figures and document preparation

The new figure directory is manuscript/figures/plos_innovation_20261017/. Figs 1–4 reproduce the original values with the publication font; their four source CSVs are checked against the earlier versions. Figs 5–6 present the new component analysis. Figure manifests record dimensions, resolution, color mode, file size and source-data identities. The PLOS submission package supplies TIFF uploads separately from the main manuscript, with captions at the point of first citation and editable tables in the manuscript. The illustrated reading copy combines text and figures for review.

OpenAI ChatGPT/Codex assisted with analysis software, validation, source checks, figure preparation, manuscript drafting and editing, and document export. Verification records cover input identity checks, reconstruction of the original endpoints, an independent implementation of the added arithmetic, portable replay and visual review. These checks were AI-assisted. The author's responsibility for the final content is stated in the main manuscript.

## 7. Licensing, ethics and author records

Original project software is MIT licensed; original manuscript content, figures and derived results are CC BY 4.0. LICENSING.md and the dated extension define the scope. Source metadata retain their NEMAR attribution; third-party libraries, styles and font files retain their own terms. Fonts used for rendering are documented separately and are not redistributed in the scientific data archive.

The original acquisition reported University of Texas at Austin protocol 2020-03-0073 and written informed consent [@kumar2024]. For the present secondary analysis, the author reported that the research administration office at Chongqing Medical University confirmed exemption from additional ethical review on 16 October 2026 under Article 32, item (1), of the 2023 Chinese ethics-review measures [@china2023ethics]. The confirmation carried no reference number. The institutional record and original collection ethics are kept separate.

The author's recorded scientific approval on 16 October concerns commit f2901decfc39b2adecae13253ee4b1159a4f9a4b, with the confirmation preserved in research_logs/kumar_author_final_confirmation_20261016/run01/README.md. The current sources and export manifest identify the subsequent 17 October extension. The updated author worksheet contains the author information and separate submission-system fields.

## References

::: {#refs}
:::
