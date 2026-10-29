# Three-author BMT component-analysis revision

Date: 29 October 2026. Journal: **Biomedical Engineering / Biomedizinische Technik**. Article type: Research Article. Authors: **Ziyuan Zhu*, Sihao Liu, Haoyang Yu**.

The paper now follows one question: what do the same current-session labels contribute through classifier recalibration, spatial refitting and support-only alignment? It uses completed analyses from two original acquisitions and keeps their participant cohorts separate. The original Kumar component gain is +5.47pp; its completed alignment follow-up adds +5.30pp beyond full refitting, and the fixed external BNCI comparison adds +5.65pp. Every original endpoint role and the complete budget/phase/extension results are reported.

## Read and review

- `BMT_Manuscript_Reading.pdf` / `.docx`: illustrated English article.
- `BMT_Manuscript_Submission.docx`: editable tables/equations, separate main figures and end legends. Main publication figures are supplied as 600 dpi RGB TIFF, with editable PDF/SVG originals.
- `Supplementary_Methods.pdf` / `.docx`: full original, budget, phase, neural, geometric and simulation evidence, including all scheduled comparisons.
- `Ethical_and_Legal_Declarations.docx`: separate journal-order statements, national-law ethics and actual AI-use disclosure.
- `Cover_Letter.docx`: corresponding-author cover letter for final review.
- `ABSTRACT_FOR_SUBMISSION.txt`, `AUTHOR_DETAILS.md`, `Suggested_Reviewers.csv` and `SUBMISSION_STATUS.json`: system fields and author facts.
- `BMT_Three_Author_Review_Package_20261029.zip`: complete review container with individual files; the separate upload ZIP is not nested inside it.
- `BMT_Upload_Files_20261029.zip`: eight individual candidate upload files after extraction; this is not a single supplementary upload.
- `Publication_Figures_and_Source_20261029.zip`: three main figures and a separate black-and-white workflow, each in PDF/SVG/600 dpi TIFF/PNG, with plotting scripts and all exact input tables. See [figure reproduction](FIGURE_REPRODUCTION.md).
- `Supplementary_Data_and_Code.zip`: public prediction reconstruction, plot data, scripts and provenance; no EEG or model tensors.

## Sources and originality

The prose uses the installed `anti-defensive-writing-en` skill. Generic research-article organization was studied in the requested papers; no external paper's data, algorithm or performance claim is presented as this project's result. Necessary technical and dataset citations remain. Peterson's institutional author manuscript was read in full; Song's journal abstract and official previews were accessible, with its complete journal text unavailable. A separate same-author open conference paper was read and is identified as a different publication in the reading record.

[Dataset/version inventory](../../research_logs/paper2_structure_revision_20261029/DATA_VERSION_INVENTORY.md) distinguishes two raw datasets from six analysis layers. [Reading and official-policy checks](../../docs/paper2_structure_revision_20261029/) record exact access scope. [Component replay](../../research_logs/paper2_structure_revision_20261029/component_replay/README.md) explains the independently reconstructed predictions, historical bootstrap orders and unchanged source files.

## Author review before actual submission

The user confirmed Haoyang Yu's agreement to authorship, data checking/aggregation, file organization, GitHub assistance and absence of conflicts. His name, email and shared affiliation are synchronized. The final exported three-author article is supplied for all authors' review. The earlier two-author approval remains attached to that earlier version. Authors should check the five existing reviewer suggestions against the expanded author list. No ScholarOne submission or external contact has been performed.

## Completed checks

The independent scientific review passed 29 targeted checks. The complete editable submission Word has 4,954 words; the structured abstract has 174, with three figures, two tables and 17 main references. All document exports completed without warnings. Numerical replay from the public ZIP in a clean temporary tree reproduced all 11 CSV outputs byte for byte. See [delivery checks](../../research_logs/paper2_structure_revision_20261029/DELIVERY_CHECKS.json) and [revision report](../../research_logs/paper2_structure_revision_20261029/REVISION_REPORT_ZH.md). `PACKAGE_SHA256.json` records each final ZIP.

The publication figures were redrawn with Python/Matplotlib from unchanged saved data. The TIFF files are 600 dpi, 8-bit RGB with LZW compression. PDF/SVG contain vector elements and editable text, including the heatmaps. The reading PDF now embeds vector figure PDFs. The workflow is supplied separately and does not change the three main figure numbers. Figure 3’s legend identifies the cohort means printed below the method names. Numerical results, source data, scientific comparisons, ethics and AI-use wording remain unchanged. Current format/data checks are in `research_logs/paper2_structure_revision_20261029/figure_redesign/`.

[Four-page vector figure review](figures/Publication_Figures_Review.pdf) collects the three main figures and the separate workflow. The standalone plotting package has been extracted and all three renderers run successfully in a clean directory; its five numerical/workflow CSV outputs were byte-identical.
