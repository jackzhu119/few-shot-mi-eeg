# Paper 2 final author-review sealing record

Start with the [actual package](../../../manuscript/plos_one_submission_20261015/README.md)
and [revision report](../../../docs/kumar_submission_revision_report_20261015.md).
No training, EEG loading, second query forward, Pod change or paper 1 work was
performed in this revision. This is an author-review version, not a submission.

## Current evidence and preserved history

- `final_package_validation.json`: 1,025 checks, zero failures; all 816 protected
  scientific/configuration/ledger/history files are byte-identical to the initial
  preservation inventory. Current artifact hashes are in the package's
  `release_manifest.json`; this base reference does not mislabel new code as
  belonging to the old commit.
- `final_document_structure_QA.json`: 32 actual PDF/DOCX checks, all passed.
- `final_document_visual_QA.json`: all current 82 PDF pages reviewed; corrected
  review export re-viewed and detailed pages inspected. No remaining layout
  defects found. Native Word layout was not rendered. Liberation font
  substitution remains explicit.
- `closing_independent_review/`: 287 saved-data/document/package consistency
  checks, no scientific failures. Its sole documentation-location advisory was
  corrected to the exact figure-directory README. `final_link_correction.json`
  binds that change without changing any scientific value or exported document.
- `initial_seal_before_link_correction/` retains both original seal receipts
  byte-for-byte. They are historical, not the current release manifest.
- `document_build_receipt.json` records the initial twelve successful exports.
  `review_caption_correction.json` separately binds the two final review exports
  after removing automatic duplicate captions. Initial export bytes remain in
  the private receipt directory named in that correction. Initial TeX and
  figure-layout proof failures also remain in their original evidence folders.
- `staged_whitespace_review.json` records the actual non-clean full Git
  whitespace check: generated SVG path spaces, terminal blank lines in already
  hashed files and real historical TeX stderr were retained. The strict authored
  text/code subset passed. This is not represented as a clean full check.

QC arithmetic and original-source lineage have separate independent receipts
under `research_logs/kumar_submission_qc_20261015/`; they did not execute a model.
Relevant synthetic tests passed: 15 QC, 7 saved-training review and 3 figure CLI
checks. The active new producer/test/build/seal code also passed Ruff. No full
unrelated test suite was run.

## Public synchronization is blocked, not assumed

`remote_closing_verification.json` records the supported read-only GitHub check:
the remote research branch still points to reference commit 370bc94. A supported
write actually returned `MCP tool call requires approval, but approval policy is
never`; see `github_write_blocker.json`. The existing shell proxy refused Git
and R2 connections; the one real R2 read probe is recorded as
`ProxyConnectionError` in `r2_connectivity_observation.json`. No new upload or
full-GET verification is claimed. No credentials were copied or created and no
alternative permission-bypass attempt was made.

The final local commit, verified incremental Git bundle, complete review ZIP and
local R2 transfer plan are recorded in the external closing handoff under
`/workspace/private_model_receipts/paper2-plos-final-review-20261015/`.
An R2 plan is only a plan; old accepted scientific backups remain unchanged.
