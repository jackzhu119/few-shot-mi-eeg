# Revised PLOS ONE author-review package — 2026-10-16

**Longitudinal motor-imagery EEG decoding: Frozen baselines, supervised
recalibration, and task-measurement reliability**

This is a revised Research Article package for the author's review. It has not
been submitted. The applicable ethics basis for this secondary analysis and the
author's personal review/approval remain outstanding. The scoped license choice
has been completed; it does not resolve those separate matters.

## Documents

- [Illustrated review PDF](manuscript_for_review.pdf) / [Word](manuscript_for_review.docx): 30 PDF pages, four figures and five editable Word tables.
- [Image-free submission-format PDF](manuscript_for_submission.pdf) / [Word](manuscript_for_submission.docx): 28 PDF pages; single column, double spacing, continuous line/page numbering. Graphics are supplied separately.
- [S1 Text: scientific methods](S1_Text.pdf) / [Word](S1_Text.docx): 24 PDF pages, including event-search scope and the post-review statistical definitions.
- [S2 Text: audit and reproduction](S2_Text.pdf) / [Word](S2_Text.docx): five PDF pages. Engineering provenance is separated from the main scientific narrative.
- [Author worksheet](author_worksheet.pdf) / [Word](author_worksheet.docx): three PDF pages. Recorded answers are retained; no new ethics decision or human approval is invented.
- [Unsent cover letter](cover_letter_draft.pdf) / [Word](cover_letter_draft.docx): one PDF page.
- [S1 Data](S1_Data.zip), [full member/hash manifest](S1_Data_manifest.json), [data overview](S1_Data_README.md), [dictionary](DATA_DICTIONARY.md) and [portable reproduction commands](REPRODUCE_SAVED_RESULTS.md).
- Separate 600-dpi flattened LZW TIFF graphics: [Fig 1](Fig1.tif), [Fig 2](Fig2.tif), [Fig 3](Fig3.tif), [Fig 4](Fig4.tif); [upload hashes](figure_upload_manifest.json).

The page counts above are observations of these PDF exports. DOCX text, tables,
media and numbering are checked structurally; native Word layout is not rendered
in this environment. The actual PDF/figure fonts are Liberation substitutions,
with the existing Noto CJK font used for the verbatim Chinese author reply.
Exact Arial/Times production-font compliance is not claimed. No font or new
execution environment was installed.

## What changed after review

The [point-by-point response](../../docs/kumar_review_response_20261016.md)
distinguishes supported suggestions from inaccurate or overstated claims. The
[Chinese revision report](../../docs/kumar_submission_revision_report_20261016.md)
summarizes the changes. Original Tables 1–4, predictions, bootstrap intervals,
participant split, all seeds, negative results and historical failures remain
unchanged. No model was fitted or forwarded, no query was evaluated again, and
no Pod or first-paper task was operated on.

Table 5 adds four explicitly exploratory, review-triggered sign-flip checks.
For the original primary contrast, raw p=0.01953125 becomes 0.05859375 after
Holm adjustment over these four checks. Neither result creates a new
confirmatory claim. A positive percentile interval is not interchangeable with
this test: the unflagged ten-participant contrast has raw p=0.076171875.

The original GR/PAR comparison is distinguished from the present LDA-only
contrast. The retained derivative lacks task-phase markers, while the public
release lists original GDFs whose embedded arrays have not been reconstructed
or mapped here. Weak source-session EEGNet performance is retained without a
causal attribution of the target score to drift. Fig 1's point key is clarified;
all four figure-data CSVs and Fig 2–4 exports remain byte-identical to the prior
version. Saved reliability/drift data and the new statistical inputs are included
in the revised data supplement; unavailable historical draw vectors are not
fabricated.

## Availability, licenses and version identity

The source/data version is identified by the Git tag
[`paper2-plos-source-20261016`](https://github.com/jackzhu119/few-shot-mi-eeg/tree/paper2-plos-source-20261016).
`release_manifest.json` binds the actual source and output bytes. The tag resolves
to the public content commit; the manifest does not attempt to include its own
Git commit or self-hash. Subsequent synchronization receipts may be committed
separately without changing the sealed scientific package.

[LICENSING.md](../../LICENSING.md) applies MIT to original project software and
CC BY 4.0 to original manuscript, figures and derived results. Source annotations,
third-party code, styles, fonts and reference materials retain their own terms.
The data ZIP contains text/code rather than EEG arrays, learned weights or
third-party full texts. No archive DOI or journal acceptance is asserted.

The original [2026-10-15 package](../plos_one_submission_20261015/README.md) remains
sealed and unchanged. Current GitHub and private R2 synchronization evidence is
linked from [CURRENT_PROJECT_STATUS.md](../../CURRENT_PROJECT_STATUS.md).
