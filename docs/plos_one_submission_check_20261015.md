# PLOS ONE author-review and submission compliance check

Scope: the current paper 2 Research Article, following reference commit
`370bc94b7af3c926adeb02c38e430a53e4a64135`. This review adds no fit, model
inference, query evaluation, policy search, Pod action or submission. The
54 accepted source fits, accepted query evaluation and historical evidence
remain independent of editorial readiness.

## Official policy access and editorial actions

The current official pages below were actually read using the supported web
tool on 2026-10-15 UTC. The four `official_web_access*.json` records in
[the compliance evidence](../research_logs/kumar_submission_compliance_20261015/run01/)
preserve source-access metadata, URLs, observation times and identities of
the tool-returned text. Full policy text is not republished. These are not hashes
of full original HTTP/HTML bodies. Source access does not
mean that a submission portal or journal account was opened.

| Official source | Applicable requirement and concrete action |
| --- | --- |
| [Submission guidelines](https://journals.plos.org/plosone/s/submission-guidelines) | Produce an unlocked DOCX; single column, double spacing, continuous line and page numbers; at most three heading levels. Use a sentence-case full title of at most 250 characters and short title of at most 100; abstract at most 300 words without citations. Title page precedes abstract; use citation-sequence Vancouver references. Place figure captions and editable tables after first citation. Upload figure graphics separately. Put supporting captions after references. Prepare a one-page cover letter. Financial disclosure belongs in the portal, outside the manuscript. |
| [Figures](https://journals.plos.org/plosone/s/figures) | Main figures: TIFF/EPS, 300–600 dpi, width 6.68–19.05 cm and height at most 22.23 cm; each under 10 MB. Use Arial, Times or Symbol at 8–12 points. Keep captions/titles outside images. TIFF must be single-page, flattened, without alpha, using LZW compression. Re-render from saved figure data rather than upscale a low-resolution plot. Match Fig1.tif etc. to citations. |
| [Tables](https://journals.plos.org/plosone/s/tables) | Retain editable, cell-based Word tables rather than screenshots, graphic objects or space-aligned text. Use explicit units and denominators, titles above and explanatory notes below. |
| [Supporting information](https://journals.plos.org/plosone/s/supporting-information) | Name each item with an S and integer and match filenames to end-of-manuscript captions. Supporting images need not follow main-figure production specifications. Target each supporting file below 10 MB; this also satisfies the submission-guideline limit of less than 20 MB. Supporting files are published as supplied. |
| [Data availability](https://journals.plos.org/plosone/s/data-availability) | Share the data and metadata necessary to reproduce every reported finding, including values behind summaries and graphs. Use machine-readable tables and fixed public identifiers. Cite the existing official source version instead of implying ownership of its raw recordings. A private R2 receipt is preservation evidence, not public data availability. |
| [Code sharing](https://journals.plos.org/plosone/s/materials-software-and-code-sharing) | Supply the author-generated analysis code, dependencies, control settings and clear usage documentation. An explicit open source license is recommended. GitHub is an example accepted software archive; a DOI-bearing archive is encouraged. No new DOI or release has been created by this compliance review. |
| [AI policy](https://journals.plos.org/plosone/s/ethical-publishing-practice) | Disclose tool names, affected research/content and how outputs were evaluated; put the disclosure in Methods, Acknowledgments or applicable legends. AI is not an author. Human responsibility includes methods, references and interpretations, not just wording. The final author's personal review remains required and cannot be replaced by technical or AI-assisted checks. |
| [Human data](https://journals.plos.org/plosone/s/human-subjects-research) | Describe actual approval/consent or an applicable exemption determination. The policy covers human data as applicable. Original-study approval cannot establish this institution's secondary-analysis status. Do not complete a human-participants checklist with an invented approval, exemption or waiver. |
| [Authorship](https://journals.plos.org/plosone/s/authorship) | Preserve the confirmed sole author and CRediT roles. The author must approve the final submitted version and accept accountability. Supplying factual identity and contribution answers is not final manuscript approval. |
| [Copyright](https://journals.plos.org/plosone/s/licenses-and-copyright) | PLOS article content is CC BY 4.0; third-party content needs compatible rights. Do not put CC BY-SA citation-style source or noncommercial software source inside an article-content supplement under a blanket CC BY declaration. Keep these separate as build dependencies with their existing notices. |

The established working title can be rendered in sentence case without changing
its meaning: **Longitudinal motor-imagery EEG decoding: Frozen baselines,
supervised recalibration, and task-measurement reliability**. Proposed short
title: **Longitudinal EEG decoding with limited recalibration labels**.

The former compact review PDFs and embedded PNG figures are preserved historical
review exports. They are not retrospectively certified as journal production
files. The new submission manuscript is
[the separate PLOS draft](../manuscript/kumar_plos_one_submission_draft_20261015.md);
the final package under `manuscript/plos_one_submission_20261015/` must
distinguish an image-free submission manuscript from an illustrated review copy.

## Concrete software and content license proposal

No root `LICENSE` has been established and `pyproject.toml` contains no project
license declaration. The author reported no institutional/collaborator release
restrictions; that does not itself select or grant a license.

**Proposed choice for the author's final selection: MIT for original project
software, CC BY 4.0 for original paper figures and non-sensitive derived tables.**
The complete inactive MIT wording is
[MIT_LICENSE_PROPOSAL.txt](../research_logs/kumar_submission_compliance_20261015/run01/MIT_LICENSE_PROPOSAL.txt).
It is intentionally outside the repository root and is explicitly not an
operative grant. Before adopting it, bind a final code-scope manifest containing
the original `src/learning_preserving_bci/` implementation, relevant analysis
scripts and their synthetic tests. A root MIT file must not silently relicense
the entire multi-dataset repository, articles, raw metadata, build dependencies
or third-party software.

| Component | Exact inspected evidence and proposed treatment |
| --- | --- |
| CPU statistical/scientific dependencies | Installed NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2 expose BSD-style primary licenses. NumPy/SciPy also include separately licensed bundled components. Retain their original notices; do not call entire wheels MIT. |
| EEGNet implementation | Installed Braindecode 1.2.0 `models/eegnet.py` explicitly identifies BSD 3-clause. Frozen `train_kumar_eegnet.py` selects this official EEGNet API. This project wraps it rather than claiming authorship of that architecture implementation. |
| Important Braindecode exception | Its actual `NOTICE.txt` identifies `models/eegminer.py` and `GeneralizedGaussianFilter` as CC BY-NC 4.0; the EEGMiner source also names a patent. The frozen architecture does not instantiate these components. A namespace import can import additional modules, so absence of execution is not a claim that these files were never imported. Do not redistribute or relicense the whole installed Braindecode package as BSD/MIT. The proposed release contains original wrappers, dependency pins and attribution, not bundled environments or these sources. |
| Torch/TorchAudio | Current CPU wheels are 2.8.0+cpu with BSD-style primary notices; preserve bundled notices if ever redistributed. Historical GPU fits used 2.8.0+cu128 and CUDA dependencies. CUDA redistribution rights are not established by a CPU-wheel metadata inspection. The proposed archive does not redistribute wheels, CUDA binaries or a container. |
| Plotting/build tools | Matplotlib 3.11.2 has its own permissive license and separate DejaVu/STIX font notices; Pillow 12.3.0 is MIT-CMU, not a project MIT grant. Pandoc/XeLaTeX and installed fonts are toolchain dependencies, not new scientific methods and not bundled into the public code release. |
| Other actual exceptions | `tqdm` carries MPL-2.0/MIT file-specific terms; `certifi` is MPL-2.0. EDFlib-Python metadata says UNKNOWN but its actual LICENSE is BSD-style; ptyprocess metadata says UNKNOWN but its actual LICENSE identifies ISC. Missing metadata alone is not proof of no license. |
| NEMAR source and metadata | Keep exact `nm000177/v1.0.5`, DOI `10.82901/nemar.nm000177.v1.0.5` and its CC BY 4.0 attribution. The source dataset's license does not license this project's code. Prefer official raw-data access rather than publishing a duplicate EEG archive. |
| Citation styles | Existing `plos.csl` identifies Sebastian Karcher, contributor Patrick O'Brien and CC BY-SA 3.0; retain unchanged rights and source attribution. Use as a separately licensed build tool, outside journal article-content supplementary files. A formatted bibliography is not a redistribution of the CSL source. |
| First-paper custom code | `docs/code_reuse_audit.md` records independent implementations and no copying of unlicensed first-paper custom source. A new static search of project source/scripts/tests found no copied/adapted notices or EEGMiner/filter usage; this is a bounded check, not proof of universal originality. Do not copy material now to fill a licensing gap. |
| Source papers and other datasets | Cite and summarize source findings rather than republish their figures or texts. This paper's release does not include unrelated NETBCI/MIND/etc. datasets; their individual licenses cannot be collapsed into Kumar CC BY 4.0. |

The [installed license inventory](../research_logs/kumar_submission_compliance_20261015/run01/installed_dependency_licenses_run02.json)
records **122 installed distributions and 157 actual license/notice file
identities** from this CPU venv, using metadata without scientific imports.
The [findings record](../research_logs/kumar_submission_compliance_20261015/run01/license_review_findings.json)
contains key source excerpts and hashes. The historical GPU lock has 105 entries
including unselected extras and **91 selected Linux/Python 3.11 distributions**.
This inventory does not claim those 91 GPU packages were reinstalled or
resampled here. CPU Torch and GPU Torch build variants remain distinct.

The required subsets also differ: historical CPU decoding used NumPy/SciPy,
MNE and scikit-learn; source EEGNet additionally used Torch/Braindecode and
their dependencies. MOABB was available for separate software validation and
is not evidence of a new MOABB cohort analysis here. Saved-prediction arithmetic
uses text readers and NumPy; rendering adds Matplotlib/Pillow. Pandoc/XeLaTeX,
fonts and Word/PDF inspection tools belong to the document toolchain. Listing
all installed distributions does not make each one a scientific dependency or
imply an all-packages runtime equivalence across CPU and GPU hosts.

## Exact scope of the public reproducibility package

The public artifact should be a paper-specific allowlist at the final Git commit,
with paths, byte lengths and SHA256 in a release manifest. A commit hash is
already a fixed software identity; do not invent an archive DOI or describe a
draft tag as a minted release. This review does not publish new private data.

1. **Manuscript documents:** the new PLOS submission source, image-free DOCX/PDF,
   separate illustrated review copy, supporting scientific methods, one-page
   cover letter draft and portal-fields worksheet. Proposed journal names are
   `S1_Text.pdf` for scientific supporting methods and
   `S2_Text.pdf` for a condensed audit appendix.
2. **Source data behind every result/figure:** original CPU
   `query_predictions.csv`; all 54 saved EEGNet prediction identities and per-job
   provenance, carried in an exact compact merged prediction CSV where
   convenient; exact trial-ID/role/label/QC lookup and excluded-trial ledger;
   seed/session/participant endpoints, bootstrap settings and original summaries.
   These allow arithmetic reproduction without EEG, weights or a second forward.
   The newly declared QC sensitivity must include full and unflagged rows,
   class denominators, missing/undefined groups and influence tables.
3. **Training interpretation:** all-54 selected epochs, actual epochs/steps,
   saved train/validation histories, label budgets and collapse information.
   These are already executed text results, not new experiments.
4. **New exploratory postprocessing:** `scripts/analyze_kumar_saved_query_qc_20261015.py`,
   its explicit input manifest and tests, and
   `scripts/render_kumar_submission_figures_20261015.py` with plotted-data CSVs
   and figure receipts. Export approved final figures separately as
   `Fig1.tif`, `Fig2.tif`, etc.
5. **Reproduction context:** frozen protocol/split/preprocessing/EEGNet
   configurations; `pyproject.toml`, CPU `uv.lock`,
   `environments/gpu/pyproject.toml`, GPU `uv.lock`; scientific runtime
   provenance, citation bibliography, source attributions, explicit license-scope
   proposal and data dictionary. Recorded dependency versions are evidence, not
   permission to automatically rerun training.
6. **Engineering audit separation:** publish a compact audit summary and
   necessary identity/hash checks with the journal; retain full historical
   parent ACK/R2/recovery/authorization records in the repository audit tree.
   Omit live host/session access details from journal files and never include
   credentials. Do not describe a parent review as a new independent human
   model replay if it only checked receipts and saved arithmetic.

Exclude raw EEG, epoch/feature arrays, checkpoint/model archives, individual
access credentials, complete software environments, first-paper manuscripts
and unrelated datasets. The historical R2 evidence remains preserved privately.
The newly prepared minimal-data ZIP must be machine-readable, below 10 MB if
practical, and separately byte-manifested; splitting is preferable to silently
dropping an unfavorable row.

## Saved-output reproduction and boundaries

The prior historical `compare_saved_predictions.py` hard-codes a private
`/workspace/private_model_receipts/.../results` path and exclusive output files.
Do not advertise that historical command as a portable public reproducer, and
do not rerun it in its already populated directory. The paper-specific minimal
data archive and explicit-path new postprocessor resolve this gap.

A reader can inspect the existing saved matched-cohort table without weights,
EEG, scientific package imports or inference:

```bash
cd /workspace/few-shot-mi-eeg
/workspace/.venvs/few-shot-mi-eeg/bin/python -B - <<'PY'
import csv
from pathlib import Path
p = Path("research_logs/kumar_frozen_query_comparison_20261015/run01/cohort_method_endpoint_summary.csv")
for row in csv.DictReader(p.open()):
    print(row)
PY
```

The actually tested portable QC command requires only the five compact public
input files (7,200 metadata identities and 25,740 saved prediction rows) and
Python 3.11/NumPy 2.2.6. It needs no credentials, raw EEG, weights or Git history:

```bash
mkdir /tmp/paper2-qc-reproduction
cp research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md /tmp/paper2-qc-reproduction/
/workspace/.venvs/few-shot-mi-eeg/bin/python -B scripts/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs research_logs/kumar_submission_qc_20261015/run01/public_inputs \
  --output /tmp/paper2-qc-reproduction
```

Use a previously nonexistent output path. An actual public-input replay already
reconstructed all 13 scientific CSV outputs byte-identically, as documented in
[the QC reproduction guide](../research_logs/kumar_submission_qc_20261015/run01/REPRODUCE.md).
Its public inputs are `frozen_trial_metadata.json`, `saved_predictions.csv`,
`frozen_analysis_configuration.json`, `original_participant_endpoints.csv` and
`public_input_provenance.json`. Do not silently change its post-observation
protocol SHA or original QC rule.

Four explicit figure source-data CSVs are supplied under
`manuscript/figures/plos_submission_20261015/`, one for each Fig1–Fig4.
The [figure-directory README](../manuscript/figures/plos_submission_20261015/README.md)
records the figure reproduction command and source manifest. A plotting command
is allowed to read only saved text tables. It must
preserve already rendered figures and use a fresh output path. Neither command
may invoke `generic formal_train`, source fit queues, checkpoint evaluation or
any query execution launcher.

Current font qualification: the actual figure renderer resolves Liberation Sans
from the installed fonts; Arial/Times requests resolve to substitutes. Thus
pixel dimensions, DPI, RGB/LZW/no-alpha TIFF checks do not establish strict
Arial/Times/Symbol family compliance. Preserve that qualification in the final
format checklist instead of reporting a complete PLOS production pass. No new
font, environment or resource was installed for this review.

A fresh dependency-license snapshot can be taken without scientific imports:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  research_logs/kumar_submission_compliance_20261015/run01/inspect_software_licenses.py \
  --output /tmp/paper2-installed-licenses-review.json
```

This final path must not already exist. The actual inventory recorded here used
`installed_dependency_licenses_run02.json`; the first metadata inspection is
also retained. These are inspection operations, not a new installed environment.

## Centralized author/institution decisions still needed

Only the following unresolved human/institution facts or choices remain; the
eight earlier factual answers are already recorded and need not be repeated.

- **Secondary-analysis institutional determination:** obtain the institution's
  actual applicable conclusion and source (including an identifier/date only
  if real). Until then, retain “no conclusion yet”; do not assert approval,
  exemption, waiver or “review not required.” The original study's reported
  approval and written consent only establish source-study attribution.
- **Specific licensing choice:** accept or change the concrete MIT-original-code
  plus CC BY 4.0-original-derived-content proposal and final allowlist; maintain
  all third-party carve-outs. No current restriction is an author statement,
  not an operative software license.
- **Final author review and accountability:** review the complete latest
  manuscript, negative results, limitations, AI disclosure and release manifest.
  Describe personal checks actually performed; do not sign an AI-output
  verification declaration merely because this task ran technical checks.
  Final approval/submission remains the author's action, and no submission
  has been performed.
- **Portal-only completion:** confirm any prior interactions with PLOS and any
  intended editor/reviewer suggestions or exclusions at actual submission;
  no editor identity, prior contact or acknowledgment consent is fabricated.

Already confirmed: sole author Ziyuan Zhu; supplied affiliation/contact; ORCID
name correction as author report; no specific funding; no competing interests;
no reported release restrictions; PLOS ONE Research Article; no prior preprint,
conference version or concurrent journal consideration. Changes to those facts
can be supplied at final review.

The scientific conclusions stay bounded: same-label-budget full refitting
versus classifier-only updating is secondary; the original primary contrast,
all negative results and exploratory labels remain intact. Reliable task-aware
policy benefit, continuous imagined movement within every exported five-second
window, human skill retention and clinical validity are not inferred from
engineering completeness.
