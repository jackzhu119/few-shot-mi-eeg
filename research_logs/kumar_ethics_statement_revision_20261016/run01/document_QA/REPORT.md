# Independent final ethics-version document QA

Passed. `final_document_QA.json` binds the current 12 PDF/DOCX files; unresolved findings are empty. PDF pages: review 31, submission 29, S1 25, S2 6, worksheet 4, cover 1.

Final structural validation passed 135 checks. Another 24 checks preserve all five main scientific tables, existing S1 tables and scientific S8–S11 text, resolve source citation keys against the 17-entry bibliography, and confirm all 12 sealed old exports remain unchanged. Current hashes match the initial build receipt plus the separately documented submission PDF correction. Source hashes still match the build receipt. Ruff passed. Build logs have no missing-glyph warnings.

Each main DOCX has five editable native tables whose cells match the source, and 17 references. Review embeds four figures; submission embeds none. Main/S1/S2 retain double spacing and continuous line-number metadata. All six DOCX contain PAGE fields. Native Microsoft Word layout was not rendered or claimed.

All 96 current PDF pages were actually displayed in contact sheets; 20 current critical pages were displayed at 150 dpi, covering ethics wording, four figures, Table 5, S11 formulas, references, Chinese quotation and final pages. No clipping, blank pages, missing text, duplicate captions, unresolved citation keys or single-line terminal page was found. Initial submission Table 5 caption separation was fixed by the parent in the derived PDF layout. The corrected 29-page PDF was viewed again in full contact scope; page 21 now contains caption, full table and explanatory paragraph together.

Actual PDF fonts are Liberation Serif/Sans, with DejaVu Sans Mono, Latin Modern Math and Noto Serif CJK as used. Strict Arial/Times/Symbol compliance is not established. Reported institutional exemption is not independently authenticated by document QA.

QA-only guard corrections: an initial source-citation regex matched the email handle `@gmail`; it was corrected to exclude emails. A first caption-location assertion matched a narrative mention of Table 5; the exact full-caption check passes. Neither required manuscript changes. No source/export edits or scientific execution were performed by this QA.
