# JNE submission fields — author-approved files

## Journal and article

- Journal: Journal of Neural Engineering
- Article type: Paper
- Current submission-form review mode: double-anonymous. The form permits author-identifying information at the authors’ risk; the current approved main PDF retains it.
- Title: Limited-label cross-session motor-imagery EEG recalibration: spatial refitting and the added value of Euclidean alignment
- Keywords: brain–computer interfaces; calibration; covariance; domain adaptation; signal processing
- Corresponding/submitting author: Ziyuan Zhu, zzy2630816871@gmail.com
- Submitting-author ORCID: https://orcid.org/0009-0005-1153-4926
- Author order: Ziyuan Zhu; Sihao Liu; Haoyang Yu. Enter given and family names separately as listed in AUTHOR_DETAILS.md.

## Structured abstract

**Objective:** To measure what Euclidean alignment (EA) adds after spatial filters and a classifier receive the same short motor-imagery calibration run.

**Approach:** Three updating pipelines based on common spatial patterns and linear discriminant analysis received identical source/calibration information; a source-frozen reference shared their queries. Kumar2024 contained 18 participants over six sessions and BNCI2014-001 nine over two days. Participant summaries and fixed CPU sensitivities assessed errors, weak-class recall and signal definitions.

**Main results:** Alignment added 5.30 balanced-accuracy points in the original twelve-person Kumar cohort (exploratory 95% interval 2.81–8.26) and 5.65 in BNCI (3.15–8.70; secondary Holm p=0.01172). Weak-class recall increased 10.45 and 8.52 points, with joint accuracy/weak-class benefit in 10/12 and 9/9 participants. In nine Kumar participants with common phase eligibility, EA-minus-full was 7.85 points for cue-anchored 5 s windows and 0.13 for task-start 2 s windows; the paired change was −7.73 (−12.17 to −3.76).

**Significance:** Alignment improved the cue-anchored decoder after supervised refitting, with added weak-class coverage. The Kumar increment depended on the evaluated signal window.

## Ethics statement

The present secondary analysis was exempt from additional ethical review under Article 32, item (1), of China’s Measures for Ethical Review of Life Science and Medical Research Involving Human Participants (2023). It used lawfully obtained publicly available data, caused no harm to participants, and did not involve sensitive personal information or commercial interests. The original Kumar data collection reported University of Texas at Austin approval under protocol 2020-03-0073 and written informed consent. These statements refer to the original data collection. The reviewed BNCI2014-001 source publication and dataset description did not supply a dataset-2a-specific committee, approval number or consent statement; their acquisition ethics details are not inferred from another dataset. The present analysis used coded records without participant recruitment, contact or re-identification.

## Funding

This research received no external funding.

## Conflict of interest

The authors declare no conflict of interest.

## Data availability

Kumar2024 source EEG is available through NEMAR nm000177/v1.0.5, https://doi.org/10.82901/nemar.nm000177.v1.0.5, under CC BY 4.0. BNCI2014-001 original recordings are available from https://bnci-horizon-2020.eu/database/data-sets/001-2014/ under CC BY-ND 4.0; a versioned mirror with original-file hashes is available at NEMAR nm000139/v1.0.3, https://nemar.org/dataset/nm000139?v=v1.0.3. The accompanying Supplementary_Results.csv contains lossless cell-level transcriptions of the two main tables, 27 supplementary tables, 17 saved-result tables and ten figure-data tables. Supplementary_Budget_Predictions.csv and Supplementary_Phase_Predictions.csv retain the saved chronological-budget and phase-window prediction rows. Supplementary_Saved_Records.csv provides original classical prediction/cell records, including undefined cells, and source metric rows in a reversible format. Supplementary_Code_and_Reproduction.pdf describes their schemas, provenance and reconstruction commands. Full original CSV/JSON/GZ files, scripts, input manifests and the earlier complete data/code archive remain publicly accessible at https://github.com/jackzhu119/few-shot-mi-eeg/tree/407e6ce0a17339d5808a7acc14e9745b9dceffbd. Historical neural and synthetic raw exports retain their separately pinned public packet locations in that guide; they are not relabeled as new predictions in these CSV files. Original code is MIT; original derived data, figures and manuscript content are CC BY 4.0. Source EEG and third-party terms are unchanged.

## AI assistance

OpenAI Codex assisted with code revision, data analysis and result checks, manuscript preparation, GitHub updates and file organization; OpenAI ChatGPT assisted with grammatical correction. The authors are responsible for verifying sources, scientific claims and the final manuscript. Validation methods are described in the manuscript. Tool-version identifiers were not recorded.

## Related submission

PONE-D-26-52050 remains under review at PLOS ONE. Supply RELATED_MANUSCRIPT_STATEMENT.md and the actual current related manuscript with the final cover-letter disclosure. Shared data, baseline predictions and historical contrasts must remain visible. This draft does not certify an editorial determination of distinctness.

## Files and author declarations

Use the complete JNE manuscript PDF with embedded figures and tables as the initial main file, plus the six named PDF/CSV supplementary files in DIRECT_UPLOAD_README.md. Review the cover letter and related-manuscript statement as editor-facing documents. Suggested reviewers are optional under the public IOP guidance; any names supplied must be free of conflicts.

All three authors’ substantive intellectual review, approval of version `79c0c53803efe226088b35991326904254e05023`, consent to JNE submission and accountability were explicitly confirmed on 4 November 2026. Author order, contributions, affiliations, emails and AI disclosure were confirmed accurate. The current files record that approval without changing the scientific content. No submission-system action has been performed.

**Author approval statement:** All authors critically reviewed the manuscript, approved the final version, consented to its submission to Journal of Neural Engineering, and agree to be accountable for all aspects of the work.
