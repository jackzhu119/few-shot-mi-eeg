# PLOS ONE final author-review package

**Longitudinal motor-imagery EEG decoding: Frozen baselines, supervised
recalibration, and task-measurement reliability**

This package is for the author's final review. It has not been submitted.
It preserves the frozen primary/secondary comparisons and adds only authorized
saved-result postprocessing, source verification, figures and editorial revision.
The remaining institutional determination, actual license selection and final
human approval are explicit; a local package is not a completed public release.

## Start here

- [Illustrated review PDF](manuscript_for_review.pdf) / [editable Word](manuscript_for_review.docx):27pages in PDF,4figures.
- [Image-free submission-format PDF](manuscript_for_submission.pdf) / [editable Word](manuscript_for_submission.docx):24pages in PDF. Single column, double spacing, continuous line/page numbering,4editabletables; figure graphics upload separately.
- [S1 Text: scientific methods](S1_Text.pdf) / [Word](S1_Text.docx):21pages, detailed phase/QC eligibility, decoders, statistical units and saved-history interpretation.
- [S2 Text: audit/reproduction](S2_Text.pdf) / [Word](S2_Text.docx):5pages; technical parent/R2/recovery history is separated from the main scientific story.
- [S1 Data](S1_Data.zip), [41-member length/SHA manifest](S1_Data_manifest.json), [dictionary](DATA_DICTIONARY.md) and [portable commands](REPRODUCE_SAVED_RESULTS.md).
- Separate600dpi flattenedLZW TIFF graphics: [Fig1](Fig1.tif), [Fig2](Fig2.tif), [Fig3](Fig3.tif), [Fig4](Fig4.tif); [alias/checksum manifest](figure_upload_manifest.json).
- [Author worksheet PDF](author_worksheet.pdf) / [Word](author_worksheet.docx):4pages; completed identity/declarations and remaining decisions.
- [Cover letter draft PDF](cover_letter_draft.pdf) / [Word](cover_letter_draft.docx):onepage in PDF, not sent.

Main PDF counts are actual export observations. Word text, editable table cells,
media, double spacing and line/page-number fields are checked structurally;
native Word layout is not rendered in this environment. PDF/figure fonts are
actually installed Liberation substitutions; exact Arial/Times production-font
compliance is not claimed. No font/environment was installed. Vector originals
remain in the separate figures directory for any later production conversion.

## Main corrections for scientific review

1. The original codebook distinguishes cue769/770 from task-start7691/7701;
   the documented exported[0,5]interval is cue-anchored, not verified continuous
   five-second imagery. All44partial events end at their recording boundary;
   they are not identified as44early task terminations.
2. Direct decoding QC sensitivity retains missing-class rows and shows10/12
   eligible remaining-cohort participants. Originalfull−frozen+7.42pp stays
   primary; unflagged+5.96pp is conditional exploratory sensitivity. Same-ten
   subset change−0.54pp is reported separately. Flaggedfitexamples still matter.
3. The secondarysame-label full−LDA-only+5.47pp remains secondary. Original
   first-run calibration/adaptiveCSP are acknowledged; no new gate is claimed.
4. EEGNet sourcequery52.92% precedes target51.58%; weak target accuracy is not
   chiefly attributed to drift. All54histories/seeds/collapses are retained.
5. NewFig4 shows all18participants×5targetsessions for both pairedcontrasts;
   individualdecreases−5.82/−0.67/−0.20pp are not all characterized as harm.

The [concise revision report](../../docs/kumar_submission_revision_report_20261015.md)
links each finding to its checks and limitations. No fitting, second query
forward, seed/parameter search, Pod change, new resources or paper1 work occurred.

## Versions and synchronization

`release_manifest.json` binds the actual package sources and outputs by bytes
andSHA256. The final local Git commit is reported in the handoff and final chat;
Git commit self-inclusion is not claimed. The reference remote is370bc94.
Current GitHub writes require an approval that this session's policy forbids;
the inherited shell proxy also refuses Git/R2 connections. Thus the revised
package is saved locally, with an offline delivery archive/bundle, and is not
misrepresented as already pushed or newly R2 full-GET verified. Earlier accepted
scientific backups and their real receipts remain unchanged.
