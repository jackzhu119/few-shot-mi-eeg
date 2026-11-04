# Journal of Neural Engineering — individual upload files

The manuscript and author declarations remain approved. The current delivery replaces the failed ZIP upload with actual PDF and CSV files. It changes file format and availability wording, adds no model fit or prediction, and retains every reported result and statistical role.

## Seven files for the current upload page

| Order | File | ScholarOne designation |
| --- | --- | --- |
| 1 | [JNE_Manuscript.pdf](UPLOAD_FILES/JNE_Manuscript.pdf) | Complete Document for Review (PDF Only) |
| 2 | [Supplementary_Methods.pdf](UPLOAD_FILES/Supplementary_Methods.pdf) | Supplementary Data Files (incl. Multimedia) |
| 3 | [Supplementary_Results.csv](UPLOAD_FILES/Supplementary_Results.csv) | Supplementary Data Files (incl. Multimedia) |
| 4 | [Supplementary_Budget_Predictions.csv](UPLOAD_FILES/Supplementary_Budget_Predictions.csv) | Supplementary Data Files (incl. Multimedia) |
| 5 | [Supplementary_Phase_Predictions.csv](UPLOAD_FILES/Supplementary_Phase_Predictions.csv) | Supplementary Data Files (incl. Multimedia) |
| 6 | [Supplementary_Saved_Records.csv](UPLOAD_FILES/Supplementary_Saved_Records.csv) | Supplementary Data Files (incl. Multimedia) |
| 7 | [Supplementary_Code_and_Reproduction.pdf](UPLOAD_FILES/Supplementary_Code_and_Reproduction.pdf) | Supplementary Data Files (incl. Multimedia) |

These are real PDFs and CSVs, not renamed archives. CSVs begin with two rectangular metadata records (`#title`, `#description`); the third record is their data header. Use `skiprows=2` and text dtypes when reading, as explained in the code/reproduction PDF. All original decimal strings and empty fields are retained. The prediction data sections exactly match their decompressed original CSVs. Saved JSON objects are canonicalized reversibly, not presented as original formatting bytes.

[Upload instructions in Chinese](DIRECT_UPLOAD_README.md) · [File sizes/hashes](DIRECT_UPLOAD_MANIFEST.json) · [Editable main Word](JNE_Manuscript.docx) · [Editable methods Word](Supplementary_Methods.docx).

## Additional individual files

- [Optional readable workbook](READABLE_COPY/Supplementary_Results.xlsx): 58 sheets, every source field stored as text. It mirrors the 56 table sources in the Results CSV and is not an additional required upload.
- [Cover letter](EDITOR_FILES/Cover_Letter.pdf), [declarations](EDITOR_FILES/Declarations.pdf) and [editorial statement](EDITOR_FILES/Related_Manuscript_Statement.pdf) use the appropriate editorial or declaration fields rather than public supplementary-data categories.
- [Figures](figures/) and [supplementary figures](supplementary_figures/) remain available in vector and high-resolution formats; the main/methods PDFs already embed them.

## Approved scope and preserved versions

On 4 November 2026, all three authors' substantive intellectual review, approval of scientific version `79c0c53803efe226088b35991326904254e05023`, consent to JNE submission and accountability were explicitly confirmed. The approval was recorded in fixed commit `407e6ce0a17339d5808a7acc14e9745b9dceffbd`. The current change only adapts those approved materials for direct file upload; it does not create another author-approval gate.

The earlier complete ZIP files remain intact in that immutable GitHub version and Git history. They are omitted from the active upload folder. The full original machine-readable code/input records and historical neural/synthetic packets remain at their documented fixed locations. The current CSV files represent the scopes specified in the guide, not all 1,471 historical source files or all neural/synthetic raw outputs.

[Reproduction](REPRODUCTION.md) · [Author confirmation](AUTHOR_DETAILS.md) · [Supplement titles/descriptions](SUPPLEMENT_METADATA.csv) · [JNE requirements](../../docs/paper2_jne_20261104/FORMAT_POLICY.md).

No submission-system operation, new experiment or merge to main has been performed.
