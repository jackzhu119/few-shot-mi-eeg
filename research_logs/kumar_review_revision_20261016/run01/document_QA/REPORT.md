# Final document export QA

Status: **PASS**. The gate record is `final_document_QA.json`, with
`unresolved_findings: []` and the actual byte lengths and SHA256 hashes of all
12 current exports. The structural validator passed 135 checks with no failures;
Ruff passed for the QA script. Current bytes match the original build receipt
with the explicitly recorded CJK and supporting-caption corrections applied.

| PDF | Actual pages |
| --- | ---: |
| Manuscript for submission | 28 |
| Manuscript for review | 30 |
| S1 Text | 24 |
| S2 Text | 5 |
| Author worksheet | 3 |
| Draft cover letter | 1 |

Both main DOCX files contain five native editable tables, with every cell
matching the current Markdown source. Original Tables 1–4 remain verbatim.
Review DOCX contains four embedded figures and submission DOCX contains none.
Each main document has 16 bibliography entries. Table 5, S11, all four
unadjusted/adjusted statistical rows, caption uniqueness, effective double
spacing in the scientific Word files, continuous line-numbering metadata and
linked PAGE footer fields pass. Worksheet and cover letter retain their
intended 1.1 spacing and page fields. Actual PDF margin numbers increase across
pages rather than restarting.

The actual final PDFs were rendered with `pdftoppm` and displayed with
`view_image`: contact sheets cover all 91 current PDF pages. Detail inspection
covered final review pages 14, 16, 19 and 20 (four figures), page 23 (Table 5),
pages 29–30 (references and final captions); submission pages 20–21 (Table 5
continuation) and 28; S1 pages 22–23 (S11 equations/results); and worksheet
page 2 (the actual Chinese approval reply). Visual files are kept privately,
and their exact paths/hashes and witnessed scope are recorded in the gate JSON.

No current blank page, physical text overflow, visible clipping, repeated
caption or unresolved last-page widow was found. Table 5 in submission spans
two pages with a normal repeated table header and a single caption. The final
review page 30 has separate bold supporting-item labels and correct body
reading order; its former page-31 single line is gone. S11's formulas,
exponents, tail fractions, Holm values and standardized effect are legible.

The initial worksheet PDF omitted the Chinese approval reply because the main
font lacked those glyphs. The parent's CJK-only export correction now shows
the exact reply, embeds a CJK font and has no new missing-glyph warning. The
parent also resolved the single-line final review page by shortening only the
supporting-data caption. Historical failed proofs and the corresponding
correction receipts remain preserved.

Word was inspected structurally, not rendered in native Microsoft Word. Native
Word pagination and layout are therefore not claimed. Actual PDF fonts are
Liberation substitutions with the recorded math/monospace/CJK families as
needed; exact Arial/Times compliance is not claimed. This AI-assisted QA does
not assert the author's personal final approval. The QA changed no manuscript,
export, old file or S1 Data ZIP and ran no training, model inference or EEG load.
