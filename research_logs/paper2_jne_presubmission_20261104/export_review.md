# JNE export review

Baseline: `ff9f6c47eea2745174a233bd4310b43d59cb6f5c`. This read-only review covers the final PDF/Word files, eight figures and both ZIP archives at that commit. No scientific analysis or new figure rendering was performed.

## Required format correction

**R1 — Supplementary tables:** SUPPLEMENT.md contains 27 tables but only nine numbered captions; 18 tables lack numbered captions. Number all tables consecutively S1–S27 and add short captions, updating the nine current references. The complete inventory, baseline line locations and suggested captions are in [export_review.table_inventory.md](export_review.table_inventory.md). Existing old-to-new labels are S1→S8, S2→S9, S3→S21, S4→S22, S5→S23, S6→S24, S7→S25, S8→S26, S9→S27. Values and scientific roles need no change. Rebuild Word/PDF and both manifests after the correction.

## Verified exports

- Main PDF: 23 pages; supplementary methods: 44 pages. Every page was examined through text bounds and layout contact sheets. No cropped text, blank page, orphan-only page or unresolved citation marker was found. These review-PDF page counts are not the JNE typeset-page count.
- All five document PDFs embed their fonts and contain no raster images. All eight figure PDFs are vector, 150 mm wide and contain 8 pt or larger text; all lowercase panel labels and figure references agree. Figure manifest bytes and SHA values match.
- Word has two/27 editable tables and four/17 native mathematical objects in the main/supplement. Table text is 12 pt. There are no tracked insertions/deletions or actual comment entries. Word pagination was not independently rendered in Microsoft Word; the PDFs were inspected for layout.
- Author-review ZIP: all 86 manifest records plus the manifest match full bytes/SHA/length and local files; no unlisted entry or ZIP CRC failure. The data/code ZIP has 1,451 readable entries and no CRC failures. Both archive hashes/lengths match PACKAGE_SHA256.json.

## Cosmetic options

- Supplement PDF p1 ends with the S1 section heading; its first table starts p2. Keeping the heading with its caption and first table content would improve flow.
- Main PDF pp4, 9, 11, 13 and16 have white space caused by keeping figures/tables and captions together. This does not hide content.
- Both p1 titles contain normal automatic word hyphenation. Manual title line breaks could improve appearance.

The supplementary caption/numbering gap is the only required export correction found. The proposed captions and contact sheets are audit artifacts, not modified manuscripts. This report applies to the fixed baseline; any rebuilt package should be checked again.
