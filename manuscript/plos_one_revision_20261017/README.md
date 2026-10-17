# Paper 2 — writing revision, 17 October 2026

## Current manuscript

**Updating spatial filters improves limited-label recalibration in a longitudinal motor-imagery EEG dataset**

Short title: **Spatial-filter updating with limited calibration labels**

This revision brings the scientific contribution to the front of the manuscript:
the added value of updating spatial filters with the same new labels, the
longitudinal variation in that value, and the reliability requirements for
using short calibration runs to select an update. The main text, scientific
supplement, reproducibility supplement and cover letter have been rewritten
around this argument.

## Read and edit

| File | Purpose |
| --- | --- |
| [PLOS_ONE_Manuscript_Revised.pdf](PLOS_ONE_Manuscript_Revised.pdf) | Illustrated reading copy |
| [PLOS_ONE_Manuscript_Revised.docx](PLOS_ONE_Manuscript_Revised.docx) | Editable illustrated manuscript |
| [PLOS_ONE_Manuscript_Submission.docx](PLOS_ONE_Manuscript_Submission.docx) | Main text with 12-point body, double spacing and continuous line numbers; figures supplied separately |
| [PLOS_ONE_Manuscript_Submission.pdf](PLOS_ONE_Manuscript_Submission.pdf) | Rendered preview of the submission-format Word file |
| [S1_Supplementary_Methods_Revised.docx](S1_Supplementary_Methods_Revised.docx) / [PDF](S1_Supplementary_Methods_Revised.pdf) | S1 Text: detailed scientific methods and sensitivity analyses |
| [S2_Reproducibility_Revised.docx](S2_Reproducibility_Revised.docx) / [PDF](S2_Reproducibility_Revised.pdf) | S2 Text: data provenance and reproducibility |
| [Cover_Letter_Revised.docx](Cover_Letter_Revised.docx) / [PDF](Cover_Letter_Revised.pdf) | Cover-letter draft |
| [Author_Submission_Details.md](Author_Submission_Details.md) | Author metadata and submission-field information |
| [Chinese revision notes](../../docs/kumar_editorial_revision_20261017.md) | What changed and why |

## Figures and underlying data

[Fig1.tif](Fig1.tif), [Fig2.tif](Fig2.tif), [Fig3.tif](Fig3.tif), and
[Fig4.tif](Fig4.tif) are the original figure uploads. The revised
[CAPTIONS.md](CAPTIONS.md) matches the current main text.

[S1_Data.zip](S1_Data.zip) preserves the existing saved-result package.
Use [S1_Data_README.md](S1_Data_README.md),
[DATA_DICTIONARY.md](DATA_DICTIONARY.md) and
[REPRODUCE_SAVED_RESULTS.md](REPRODUCE_SAVED_RESULTS.md) for its contents and
reconstruction commands. The original
[data manifest](S1_Data_manifest.json) and
[figure manifest](figure_upload_manifest.json) accompany these assets.

## Version and analysis continuity

The writing revision starts from the research branch at
`19007a24c0bce0df285643297f35d0f2fe83c713`. Its source manuscripts are the
16 October institutional-exemption revision. The original scientific results
are identified by `paper2-plos-source-20261016`; the ethical statement is
identified by `paper2-plos-ethics-20261016`.

The original participant split, endpoint hierarchy, saved numerical results,
figure values and data archive are retained. The primary contrast remains full
CSP/LDA refitting versus freezing. The comparison with LDA-only recalibration
remains the predefined secondary component contrast. The later sign-flip and
sensitivity checks retain their exploratory status.

The separate task-window protocol and partial event mapping available at the
branch head are reflected in the window description. This writing revision
reports the existing cue-window decoding results. It adds no task-window
performance results or trained update-selection policy.

The author metadata records the scope of the 16 October scientific approval
and the author-reported institutional exemption. This directory is the dated
17 October writing revision. The cover letter is supplied as a draft.

## Source and rebuild

- [Main source](../kumar_plos_one_submission_draft_20261017.md)
- [S1 source](../kumar_plos_one_supporting_methods_20261017.md)
- [S2 source](../kumar_plos_one_audit_reproducibility_20261017.md)
- [Cover-letter source](../kumar_plos_one_cover_letter_20261017.md)
- [Bibliography](../kumar_plos_one_references_20261017.bib)
- [Document builder](../../scripts/build_kumar_editorial_documents_20261017.py)

From the repository root, with Pandoc, python-docx and lxml available:

```bash
python scripts/build_kumar_editorial_documents_20261017.py
```

The builder uses the versioned PLOS CSL and original figure PNGs in the
repository. PDFs are rendered previews of the generated DOCX files.
`release_manifest.json` records the final exported files and source hashes.

The original software and original paper content continue under MIT and
CC BY 4.0 respectively, with the existing third-party exceptions. See
[the dated scope addendum](../../LICENSES/scope-addendum-paper2-revision-20261017.md)
and [LICENSING.md](../../LICENSING.md).
