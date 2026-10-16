# Policy, public access and scoped license review

Recorded on 2026-10-16 UTC. This report addresses the administrative claims in
reviewer comments C1 and C2. It is a policy/source check and license record,
not an institutional determination or journal submission. Raw third-party
webpages and article full texts are not distributed in this directory.

## C1: actual ethics basis remains unresolved; a new written decision is not a universal rule

PLOS's human-research policy covers human data as applicable and recognizes
exemptions under applicable IRB/ethics committee regulations. Its submission
guidelines require an ethics statement and say: “If approval was not obtained,
the authors must provide a detailed statement explaining why it was not needed”.
Those requirements support resolving and accurately reporting the applicable
ethics basis. They do not establish that every analysis of public coded data
must obtain a new project-specific written IRB decision from the author's
institution.

The author currently reports no institutional conclusion. Public access and
CC BY are not an automatic exemption. The original collection's approval and
consent must be attributed to that collection and cannot substitute for this
project's actual applicable position. No approval, waiver, exemption,
review-not-required finding, date or certificate is invented here. The claim
that the manuscript would necessarily be rejected at initial screening is an
editorial prediction, not an outcome established by the policies read.

A real institutional policy or applicable rule may provide the detailed basis;
a real project-specific institutional decision is another route. A written
response is useful evidence when obtained, but must not be presented as a
universal PLOS requirement. The author should establish the actual applicable
basis and use only wording supported by it. The new
[bilingual information-request draft](../../../../docs/kumar_secondary_analysis_ethics_information_request_20261016.md)
is **unsent**. It neither prescribes the institution's classification nor seeks
to portray a later consultation as approval obtained before the analysis.

## C2: the earlier S1 data are public; DOI and a merge to main are not universal conditions

An unauthenticated HTTPS GET verified the historical `S1_Data.zip` at the fixed
public commit
[`a78372db00cd4161e713ab47aca2d93c643a52bb`](https://github.com/jackzhu119/few-shot-mi-eeg/tree/a78372db00cd4161e713ab47aca2d93c643a52bb).
The response was HTTP 200, 591,742 bytes, SHA256
`797d0e4c2f913428b864688cebcf182f65e022f2fcd7e5225cd919701740867b`, exactly
matching the local historical ZIP. See
[anonymous_public_snapshot_check.json](anonymous_public_snapshot_check.json).
The reviewer's “local/private R2 only” statement is therefore factually wrong
for that version. A public commit's files can be accessed while its branch
remains unmerged; branch distance from main does not show private access.

PLOS requires the minimal data underlying reported findings and related
metadata, publicly available without restriction at publication, together with
a truthful Data Availability Statement at submission. Data can be provided in
Supporting Information. Repository use is strongly recommended; when used,
the statement must identify the repository and relevant DOI, accession/code
or other persistent identifier. An author-created DOI is therefore not a
universal prerequisite to initial submission. Applicable field-specific
deposition rules still matter.

For author-generated code underpinning findings, PLOS expects unrestricted,
documented, reusable access at publication and may make central-code access a
publication condition. Its code-sharing guidance **encourages** persistent
identifiers such as DOIs and clear open source licensing. The stronger
software-manuscript rules list GitHub as an example software archive; this
research analysis is not automatically a software manuscript. A DOI-bearing
archive is a useful recommended release choice, not a fact to invent or a
universal rule to impose. No DOI was created here.

The old snapshot's availability does not establish that a later local revision
is already public. The revised package needs its own accurate version/link and
release verification. A commit is a fixed version identity, not a guarantee
of permanent hosting or a certification of every repository-selection criterion.

## The author's scoped license authorization is implemented

The author confirmed: **“确认按上述限定范围激活”**. The operative choice is MIT
for original project software and CC BY 4.0 for original derived data, figures
and manuscript text, preserving original EEG/source and third-party rights.
The [author receipt](author_license_activation_receipt.json) distinguishes the
recording time from the unrecorded exact author-message time and does not
interpret licensing confirmation as ethics clearance or final manuscript
approval.

The new root `LICENSE`, `LICENSING.md`, `LICENSES/MIT.txt`,
`LICENSES/CC-BY-4.0.txt` and `LICENSES/scope-manifest-20261016.json` implement
the scoped grant. The initial scope snapshot inventories 195 software files,
52 authored-content files and 41 historical S1 ZIP members. It is an audit
snapshot, not the final new-revision release manifest. Explicit path rules and
third-party exceptions are in [LICENSING.md](../../../../LICENSING.md).

Original EEG and provider material, third-party source/packages, CSL styles,
CUDA components and third-party reading materials retain their existing terms.
The whole Braindecode package is not called MIT or uniformly BSD: the inspected
1.2.0 EEGNet source identifies BSD-3-Clause, while EEGMiner and
GeneralizedGaussianFilter carry separate CC BY-NC 4.0 notices. Dependency calls
and license citations do not transfer ownership of packages or referenced
documents.

The complete CC BY 4.0 legal code was copied unchanged from Creative Commons;
the complete MIT substantive text matched OSI after whitespace and typographic
quote normalization, with year and copyright holder filled in. See
[license_activation_checks.json](license_activation_checks.json). Old sealed
members, the historical inactive proposal and old receipts were not changed.

For a new reproduction package, include the complete `MIT.txt` and
`CC-BY-4.0.txt`, a package-specific notice distinguishing original code from
original content and preserved source rights, and a final member hash manifest.
The notice should cite the actual repository/version plus the official license
URLs below. It should not claim that third-party files are covered merely by
being packaged or referenced.

## Evidence and limits

- [official_source_fetch_manifest.json](official_source_fetch_manifest.json)
  records actual UTC response fetches and full response-body SHA256 for five
  PLOS pages plus OSI MIT and Creative Commons CC BY legal code. The raw PLOS/OSI
  HTML is retained privately; no article, policy HTML, PDF or XML is copied here.
- [source_reading_scope.json](source_reading_scope.json) separates full-page
  retrieval from the particular sections actually read. It does not claim an
  exhaustive legal review of every fetched page or dependency.
- The author/institution's actual ethics basis and the author's personal review
  and approval of the exact final manuscript remain separate unresolved facts.
  License authorization itself is no longer pending.
- No new research fit, inference, query evaluation, credential action, Pod,
  journal portal, payment, account creation, DOI registration or external message
  was used in this policy/license subtask.

Official source URLs:

- [Human Subjects Research](https://journals.plos.org/plosone/s/human-subjects-research)
- [Submission Guidelines](https://journals.plos.org/plosone/s/submission-guidelines)
- [Data Availability](https://journals.plos.org/plosone/s/data-availability)
- [Materials, Software and Code Sharing](https://journals.plos.org/plosone/s/materials-software-and-code-sharing)
- [Licenses and Copyright](https://journals.plos.org/plosone/s/licenses-and-copyright)
- [OSI MIT license](https://opensource.org/license/mit)
- [Creative Commons CC BY 4.0 complete legal code](https://creativecommons.org/licenses/by/4.0/legalcode.txt)
