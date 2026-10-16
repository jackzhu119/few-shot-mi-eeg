# Scoped licensing

Copyright (c) 2026 Ziyuan Zhu for the original contributions identified below.
The author authorized this license choice on 2026-10-16 (UTC). This is an operative
grant; the earlier proposal in the 2026-10-15 compliance record remains an
unchanged historical proposal.

## Original project software: MIT

The MIT license in [LICENSES/MIT.txt](LICENSES/MIT.txt) applies to Ziyuan Zhu's
independently authored software in these repository-relative paths:

- `src/learning_preserving_bci/**/*.py`
- `scripts/*.py` and `scripts/*.sh`
- `tests/*.py`
- `configs/*.json`
- `pyproject.toml`

This covers original wrappers, analysis/reproduction/rendering scripts,
synthetic tests and original configuration definitions. It does not claim
ownership of library APIs, third-party code called by a wrapper, quoted source
material, provider metadata or the data processed by the software. A package
name, URL, SPDX identifier or license citation in a file does not relicense the
referenced material. The audit snapshot in
[LICENSES/scope-manifest-20261016.json](LICENSES/scope-manifest-20261016.json)
records current covered files with byte lengths and SHA256; it is not a claim
that the entire repository has one license.

## Original paper content and derived results: CC BY 4.0

The Creative Commons Attribution 4.0 International license in
[LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) applies, to the extent of the
author's rights, to original paper-2 manuscript text, scientific supporting
text, figures, derived numerical results and original documentation in:

- `manuscript/kumar_*.md`
- `manuscript/figures/plos_submission_20261015/` and
  `manuscript/figures/plos_submission_20261016/`: the original figures, captions,
  source tables and figure documentation, excluding third-party items below.
- `manuscript/plos_one_submission_20261015/` and
  `manuscript/plos_one_submission_20261016/`: original manuscript/supporting
  documents, original figure uploads, derived data and original data/reproduction
  documentation, with the code and source-data exceptions below.

For `S1_Data.zip` and its uncompressed successor packages, the grant is
component-specific: original `.py` files under `code/` and `tests/` are MIT;
original derived tables, saved predictions, training histories, authored
annotations, methods and documentation are CC BY 4.0. Existing source-derived
event identities, labels and source metadata retain the source's rights,
attribution and license. Their inclusion does not transfer authorship to
Ziyuan Zhu. The current ZIP member inventory and hashes are in the scope
manifest. This notice applies to the original components without changing any
sealed historical ZIP bytes or its original receipt.

Suggested attribution for original content: “Ziyuan Zhu (2026), Longitudinal
motor-imagery EEG decoding: Frozen baselines, supervised recalibration, and
task-measurement reliability,” with the actual repository/version URL. Link to
CC BY 4.0, retain existing source credits, and indicate changes when made.
Publication acceptance and a journal DOI are not asserted by this notice.

## Exclusions and precedence

These exceptions take precedence over every path rule above. This project grants
only rights it owns. A third-party license or copyright notice is preserved and
is not replaced by MIT or by the author's CC BY grant.

- **Original EEG and provider material:** raw EEG, epoch/feature arrays, source
  recordings, original provider metadata, source figures/full text and other
  third-party data are excluded from the author's grant. Kumar2024/NEMAR
  `nm000177` version 1.0.5 remains under its existing CC BY 4.0 terms with
  attribution to the source creators. Obtain source data from its official
  versioned source; this notice does not authorize new raw-data redistribution.
- **Third-party software:** copied/vendored source, installed packages, wheels,
  binaries, fonts, toolchains, containers and their notices keep their own
  licenses. Dependency declarations, lockfiles and wrapper code do not make
  dependencies MIT. MNE, scikit-learn, NumPy, SciPy, Torch, Braindecode,
  Matplotlib, Pillow, MOABB and their bundled components are not licensed by
  Ziyuan Zhu here. In particular, the inspected Braindecode 1.2.0 EEGNet source
  identifies BSD-3-Clause, while its EEGMiner/GeneralizedGaussianFilter
  components have CC BY-NC 4.0 notices. The whole Braindecode package must not be
  described as MIT or uniformly BSD. No CUDA/NVIDIA redistribution rights are
  granted.
- **Styles and references:** `.csl` files (including the PLOS styles under the
  historical review packages), copied style/templates, third-party reading
  materials, article PDFs/XML/HTML and downloaded policy/license pages are
  excluded. The CSL styles retain their existing CC BY-SA 3.0 notices. A
  bibliography entry or quotation is not a new license grant over the cited
  article. A CC BY article-content supplement must not silently bundle
  incompatible third-party material under its own license.
- **Historical/private material:** first-paper manuscripts, third-party code
  from reference checkouts, credentials, model checkpoints/learned weights,
  archives of installed environments and private transport objects are not
  included. `research_logs/`, dataset/cache directories, and other paths not
  positively listed above receive no blanket grant from these root files.
- **Mixed documents:** the author's original prose or original compilation may
  be covered while attributed third-party extracts retain their existing terms.
  If a component's ownership or permission is unclear, no new rights over that
  component are asserted by a path match.

The complete MIT text is transcribed from the Open Source Initiative's
https://opensource.org/license/mit with the year and copyright holder filled in.
The complete CC BY 4.0 legal code is saved unchanged from
https://creativecommons.org/licenses/by/4.0/legalcode.txt. Source-access and
response hashes were recorded in the private review evidence. This scoped
notice does not certify ethics clearance, consent, data sensitivity, third-party
redistribution rights or the author's final approval of a manuscript.
