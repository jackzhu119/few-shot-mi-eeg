# Current PLOS ONE policy and license review

This editorial review uses official pages actually accessed on 2026-10-15 UTC,
the existing CPU environment's distribution metadata and installed license
files, the frozen 91-package selected GPU-runtime inventory, and actual project
source. It runs no EEG analysis, model loading, fit, forward or query evaluation.
No credentials, Pod or first-paper files were accessed or changed by this review.

The main deliverable is `docs/plos_one_submission_check_20261015.md`.
Four official access records retain URL/source metadata and identities of the
tool-rendered policy text; full policy pages are not republished and no original
HTTP/HTML full-body hash is claimed. The requirements were read, not inferred
solely from a citation-style file.

The reproducible metadata-only inventory inspected 122 currently installed CPU
distributions and 157 actual license/notice files. The actual script is
`inspect_software_licenses.py`; scoped Ruff passed. `validation.json` contains
164 targeted evidence checks, zero failures, including all 157 current notice
hashes. These are evidence checks, not software/scientific experimental tests.
The initial inspection remains preserved beside the script-produced snapshot.

Important findings:

- No active project root LICENSE or declared `pyproject.toml` license exists.
  `MIT_LICENSE_PROPOSAL.txt` is explicitly inactive and awaits the author's
  specific selection. No restrictions is not a license grant.
- Braindecode's actual EEGNet source is BSD-3-clause, but its NOTICE identifies
  unused EEGMiner/GeneralizedGaussianFilter components as CC BY-NC 4.0. The
  frozen wrapper selects EEGNet and does not instantiate those optional
  components. No blanket BSD/MIT claim or environment redistribution is made.
- CPU wheels and the historical CUDA/GPU runtime are separate observations.
  The GPU lock's 105 entries/91 selected distributions are not an inventory of
  packages newly installed or run here. Proprietary CUDA redistribution rights
  are not established by reading CPU package metadata.
- CSL is CC BY-SA 3.0 and remains a separate build dependency. It does not
  belong in journal article-content supplementary files under blanket CC BY.
- Public reproduction now has a compact, actually replayed text-only QC path;
  the historical comparison's hard-coded private path is not advertised as a
  portable command. No weights or EEG arrays are needed by that new path.
- Actual PLOS formatting differs from old illustrated review PDFs: double
  spacing/line numbers, editable tables, separate production figures and
  captions at first citation; financial disclosure belongs in the portal.
  The available Liberation Sans substitute is explicitly distinguished from
  a demonstrated strict Arial/Times/Symbol family match.

The draft data/code/AI/author declarations are in
`declarations_for_final_author_review.md`. They distinguish actual technical
checks from the human author's final personal review, and original-study
ethics/consent from the unresolved secondary-analysis institution decision.

The consolidated unresolved human items are: actual institution determination;
specific license/allowlist choice; final author review/accountability and
submission approval; any portal-only author facts not yet supplied. There is
no request for repeated scientific fits, gates, new resources or a new journal
submission in this review.
