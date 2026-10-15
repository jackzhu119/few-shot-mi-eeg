
**Paper:** Longitudinal motor-imagery EEG decoding: Frozen baselines,
supervised recalibration, and task-measurement reliability

**Purpose:** final author review and later entry into the PLOS ONE submission
system. This worksheet is not part of the scientific manuscript, is not a
journal form already submitted, and does not grant new experimental permissions.
The eight earlier factual answers have already been recorded.

## Recorded submission fields

| Field | Current truthful entry |
| --- | --- |
| Journal / article type | PLOS ONE / Research Article; author confirmed |
| Full title | Longitudinal motor-imagery EEG decoding: Frozen baselines, supervised recalibration, and task-measurement reliability |
| Short title | Longitudinal EEG decoding with limited recalibration labels |
| Sole and corresponding author | Ziyuan Zhu |
| Affiliation | College of Artificial Intelligence Medicine, Chongqing Medical University, Chongqing, China |
| Correspondence email | zzy2630816871@gmail.com |
| Postal address | Jinyun Campus, Chongqing Medical University, No. 61, Daxuecheng Middle Road, Shapingba District, Chongqing 401331, China |
| ORCID | 0009-0005-1153-4926; author reports Given name Ziyuan / Family name Zhu correction. This task did not independently refresh the profile. The author should link the actual ORCID in the journal account. |
| Contributions | Ziyuan Zhu: Conceptualization; Methodology; Software; Formal analysis; Validation; Visualization; Writing – original draft; Writing – review & editing. These queried roles were author confirmed. |
| Financial disclosure | The author received no specific funding for this work. Enter in the financial-disclosure portal field; do not import the original study's funding or reinsert financial disclosure in the upload manuscript. |
| Competing interests | The author declares no competing interests. |
| Preprint / conference version | None reported by the author. |
| Concurrent journal consideration | None reported by the author. |
| Institutional/collaborator restrictions | None reported for original code or derived results; this does not select a license or eliminate third-party terms. |
| Prior contact with PLOS | Not yet supplied; do not assume none. Record any real editorial correspondence if relevant. |
| Academic Editor suggestions / opposed reviewers | Not yet selected. Do not invent names, affiliations, contacts, conflicts or opposition reasons. |

Identity/affiliation/contact were retrieved at the author's direction from
first-paper fixed commit `d9a11926076bd348696f6e690078955921dac3f8`.
Paper-2 declarations come from the author's actual eight-item reply recorded in
`research_logs/kumar_author_confirmation_20261015/run01/author_confirmation.json`;
first-paper funding, ethics and final-approval statements were not transferred.

## Decisions and facts still needed

### 1. Actual institutional determination for this secondary analysis

**Current status: the author reports no conclusion yet.**

Obtain the responsible institution's actual applicable conclusion and its
wording. Supply the responsible office/committee, decision or policy basis,
date and identifier only where real. Possible classifications depend on that
institution's rules; this worksheet does not choose approval, exemption, waiver,
non-human-subjects research or review-not-required status.

The original paper's Methods report University of Texas at Austin protocol
2020-03-0073 and written informed consent. Accessible indexed Methods passages
were checked; a direct complete-original-XML retrieval was unsuccessful.
These facts support attribution about the original collection, not a new
institutional decision for this project. Do not sign a human-participants
checklist with a fabricated approval or treat public availability as an
automatic exemption.

**Author/institution response:** pending.

### 2. Concrete license and public-material choice

**Proposed author choice: MIT for original project code; CC BY 4.0 for original
paper figures and non-sensitive derived tables. No operative grant is active.**

The inactive complete MIT text is
`research_logs/kumar_submission_compliance_20261015/run01/MIT_LICENSE_PROPOSAL.txt`.
The detailed rights inventory is
`docs/plos_one_submission_check_20261015.md`.
The final file-by-file release manifest, with lengths and SHA256, must bind the
selected scope before a root license is activated.

The proposed original-code allowlist covers the project's independently written
`src/learning_preserving_bci/` implementation and relevant Kumar scripts/tests,
including the new saved-prediction QC and figure scripts and their synthetic
tests. Frozen configurations accompany this code. Upstream MNE/sklearn/
Braindecode/Torch code remains separately licensed; neither upstream authorship
nor package ownership is assigned to this project's author.

The proposed manuscript/data allowlist covers:

- The new English manuscript, scientific supporting methods and compact
  audit/reproduction appendix, with the final PDF/DOCX review versions.
- The four original figures, their exact machine-readable source tables and
  production TIFFs; no source-paper figure or full text is republished.
- **S1 Data:** saved CPU/EEGNet predictions, fixed event/role/label/QC metadata,
  original and sensitivity participant/session counts and endpoints, complete
  saved training histories and the values behind all plots. The compact public
  QC inputs contain 7,200 event identities and 25,740 stored prediction rows.
- The saved-result postprocessing and synthetic tests, explicit input/output
  manifests, protocol/configuration pins and reproduction instructions.

Excluded: original EEG, epoch/feature arrays, learned weights/model archives,
credentials, first-paper manuscripts and unrelated datasets. Public
reproduction uses saved text and does not require a second model forward or
private R2 access.

Important carve-outs: the NEMAR source remains CC BY 4.0 with source attribution;
the CSL build style remains CC BY-SA 3.0 outside article-content supplements;
Braindecode 1.2.0 has unused EEGMiner/GeneralizedGaussianFilter components under
CC BY-NC 4.0, so the whole environment cannot be called MIT/BSD. CUDA wheel/
container redistribution is not proposed or licensed by this review.

**Author choice:** accept the stated scoped proposal, or specify an alternative.
No response has yet been recorded.

### 3. Final personal review, AI disclosure and accountability

The actual AI assistance included software/validation, saved-result arithmetic,
figures, source/reference checking, drafting/editing and exports; it was more
than language polishing. OpenAI ChatGPT/Codex is disclosed in Methods and is
not an author. Technical evidence includes exact identity/hash joins,
original-endpoint reconstruction, synthetic tests, saved-arithmetic validation,
portable public-input replay and rendered-document/figure inspection.
Those checks were themselves AI-assisted and are not a substitute for the
author's personal review or independent human replication.

Before final approval, the author should review the following materials and
record the checks **actually performed**, without retroactively asserting checks
that were not done:

- Primary 12-participant contrast and secondary equal-label-budget contrast;
  all seeds, negative outcomes and class collapse; 54 models versus 18
  participant identities; historical test exposure.
- Cue-anchored five-second window interpretation, missing trial-level phase
  evidence and recording-boundary partial exclusions.
- Exploratory QC rules, missing-class groups and two unavailable five-session
  sensitivity endpoints; retained artifacts in historical training/validation.
- Source-query EEGNet weakness, complete saved histories and the limits of
  interpreting training/evaluation-mode loss differences.
- Citation accuracy/read-scope records, ethics attribution, data dictionary,
  scoped license choice and full manuscript/appendices/figure captions.

**Personal checks actually completed by the author:** pending author account.

**Approval of this exact final manuscript and accountability for its contents:**
pending. Earlier authorship/funding answers are not that approval. No journal
submission is authorized or performed by this worksheet.

### 4. Portal-only author entries at actual submission

Record any real prior interaction with PLOS, editor/reviewer suggestions or
exclusions, any acknowledgment requiring another person's consent, and the
institutional answer above. No additional acknowledgment, endorsement,
manuscript ID, submission date, ethics certificate or archived-release DOI has
been generated or inferred.

## Package separation and format qualification

The actual upload manuscript should be image-free with editable tables,
continuous line/page numbers and double spacing. Figures are separate uploads;
the illustrated PDF/Word copy is for the author's review. The supporting item
names are S1 Text, S2 Text and S1 Data and must match their actual filenames
and final captions.

Current production TIFFs preserve actual DPI/geometry/RGB/LZW checks. The
installed renderer uses Liberation Sans as an Arial-compatible substitute;
strict Arial/Times/Symbol family compliance has not been established. Preserve
this qualification rather than marking every PLOS production requirement
complete. An actual portal check is still needed before submission.

The current scientific draft, final package manifest and cover letter are
prepared for review, not evidence of acceptance, completed licensing,
institutional clearance or formal journal submission.
