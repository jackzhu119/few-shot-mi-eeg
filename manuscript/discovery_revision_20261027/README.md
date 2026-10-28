# Biomedical Engineering / Biomedizinische Technik — author-review revision

**Version: Skill-assisted language revision with author-corrected AI disclosure — anti-defensive-writing-en — 28 October 2026.** Git tag: `paper2-bmt-skill-ai-corrected-20261028`. [Version record](SKILL_VERSION.md) · [Download the Skill revision package](BMT_Skill_Revision_AI_Corrected_20261028.zip). This label identifies the language-revision workflow; the scientific results are unchanged and the AI-use statement follows the author's 28 October clarification.

Scientific revision: 27 October 2026. Latest language revision: 28 October 2026. Article type: Research Article. This is a new scientific and journal-specific review draft; the earlier PLOS ONE submission files remain unchanged.

The manuscript now compares spatial update operations under matched target labels in two datasets. The original Kumar12-person component gain is +5.47pp; a fixed nine-person BNCI2014-001 replication gave Full−LDA-only +0.19pp [−1.85,2.13] and EA−Full +5.65pp [3.15,8.70], with EA gains in all9participants. Original endpoint roles remain intact. [External experiment and revised main line](../../research_logs/paper2_external_validation_20261027/REPORT.md) · [Exact public replay](../../research_logs/paper2_external_validation_20261027/REPRODUCE.md).

The verified external-review response is recorded in [the point-by-point revision report](../../research_logs/bmt_review_response_20261027/RESPONSE.md). The latest [language review](EDITORIAL_REVISION_20261028.md) clarifies cohort attribution, removes repeated framework claims and execution-log prose, and synchronizes Word, PDF and the package. All scientific results are preserved. The AI-use statement follows the [author-confirmed correction](AI_DISCLOSURE_CORRECTION_20261028.md). The [27 October editorial record](EDITORIAL_REVISION_20261027.md) remains available.

## Read and review

- [Download the complete author-review package](BMT_Author_Review_Package_20261027.zip), with [archive checksums](PACKAGE_SHA256.json).
- [English main source](MAIN.md), [review PDF](BMT_Manuscript_Review.pdf), [review Word](BMT_Manuscript_Review.docx).
- [Editable manuscript for later submission](BMT_Manuscript_Submission.docx): separate figure files and final figure legends, with editable tables/equations. This file has not been approved or submitted.
- [Supplementary methods and all-budget tables](SUPPLEMENT.md), [PDF](Supplementary_Methods.pdf), [Word](Supplementary_Methods.docx).
- [Five 600dpi figure sets, vector exports and underlying data](figures/), with [complete figure legends](figures/captions.md).
- [Ethical and legal declarations — review draft](ETHICAL_AND_LEGAL_DECLARATIONS_DRAFT.md), [Word](Ethical_and_Legal_Declarations_DRAFT.docx).
- [Cover letter — review draft](COVER_LETTER_DRAFT.md), [Word](Cover_Letter_DRAFT.docx).
- [Scientific revision report](../../research_logs/paper2_v3_analysis_20261027/REPORT.md), [complete saved-result reproduction](../../research_logs/paper2_v3_analysis_20261027/REPRODUCE.md).
- [Supplementary derived data and postprocessing code ZIP](Supplementary_Data_and_Code.zip), prepared below the journal's10MB per-file limit.
- [Official journal requirements and policy sources](../../docs/bmt_journal_requirements_20261027.md), [automated format checks](JOURNAL_FORMAT_CHECKS.json).

## Format and transparency

The journal's linked Instructions for Authors specify a200-word structured abstract (Objectives; Methods; Results; Conclusions),6000-word Research Article,3–6alphabetical lowercase keywords, a75-character running head, at most8figures/tables combined and35references. References use the journal's Vancouver convention. Each figure is supplied independently; supplementary files are prepared below10MB per file. The journal uses single-blind review.

The author reports using OpenAI ChatGPT/Codex for grammatical editing, pushing updates to GitHub, assembling and cross-checking project files, and revising code. This scope is stated in the acknowledgment and separate declarations; the [28 October correction](AI_DISCLOSURE_CORRECTION_20261028.md) supersedes earlier descriptions of AI assistance. Plotting scripts render saved numerical results. The author's scientific review and approval apply to the actual version being submitted. The publisher's policy and its disclosure requirements are linked in the journal-requirements record.

## Author items before actual submission

1. Personally review, revise and approve this new manuscript, additional analyses and exact AI-use declaration. Prior approval applied to an earlier version.
2. Confirm the actual status of the previous PLOS ONE submission and that this article is eligible for submission elsewhere.
3. Supply at least five appropriate reviewer suggestions with names, institutions, countries and email addresses, following the journal's independence criteria. [Editable blank list](Suggested_Reviewers_TO_COMPLETE.csv); no names are fabricated.
4. Check the existing sole-author affiliation, postal address, correspondence email and ORCID. An institutional email is recommended by the journal; the existing verified email is retained until a replacement is supplied.

The external replication added nine source fits and27updating CSP/LDA fits after its protocol was frozen; all previous Kumar/EEGNet models and evaluations were reused. No model search, Pod or school Slurm operation was performed. The new R2 transfer returned HTTP401 on all208planned objects; no remote backup is claimed. Raw inputs and model tensors remain private and local; all derived predictions and statistics are public. Negative outcomes, all seeds, the exposed-cohort status and original ethics wording remain traceable. Original code/results licenses retain their scope; see [third-party citation-style attribution](Third_Party/README.md).
