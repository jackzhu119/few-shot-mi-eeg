# Verified manuscript synchronization — 2026-10-16 UTC

The immutable author-review content commit is
`f2901decfc39b2adecae13253ee4b1159a4f9a4b`, published to main and the research
branch, with tag `paper2-plos-source-20261016`. Later commits record sync evidence
without changing the sealed scientific package. This is not a submission.

- [Public GitHub readback](github_public_readback.json): main/research/peeled tag
  matched; ten complete unauthenticated public files, 4,925,827 bytes, matched
  local full bytes and SHA256. This is not a claim of 283 separate HTTP GETs.
- [Primary private R2 receipt](r2_full_get_receipt.json): 679 unique objects,
  70,070,553 bytes, all complete GET/SHA256; zero failures. Receipt: 579,221 UTF-8
  bytes, SHA256 `7eab03bf7c6d21dc9ca60a8b878f2a74051ac95af32054255d145933ae4b3770`.
- [Independent reconciliation](independent_R2_receipt_verification.md): all rows
  matched local payload bytes; all 283 public files matched the content commit's
  Git blobs. This review performed no second remote GET or parent ACK.
- [Closing private R2 receipt](closing_r2_full_get_receipt.json): 13 objects,
  19,388,709 bytes, all complete GET/SHA256; zero failures. Receipt: 11,132 UTF-8
  bytes, SHA256 `0bfdb0c6c4e67f6c295468aa2018ae4b923459f0f765b6679ba4bc9ff1655b37`.
- [Combined summary](combined_sync_summary.json): **692 unique keys, 89,459,262
  bytes, zero failures**. Distinct prefixes prevent counting one key twice.

The primary upload was planned before the content commit. Its unchanged
`source_git_commit`/snapshot-base fields truthfully retain `a78372d`; independent
full-byte comparison to `f2901de` establishes the new public-file identity.
Those historical receipt fields were not rewritten.

The closing batch preserves the primary receipt, reconciliation, public-readback
proof, a verified incremental Git bundle and the 44-member author-review ZIP.
The bundle requires the already preserved `a78372d` prerequisite. It is not a
new full-history clone. The closing receipt and final Git metadata are held in
Git rather than making an impossible circular self-GET claim. The private
original reviewer text/full reading evidence are not published to GitHub.

The selected review ZIP is 7,553,238 bytes, SHA256
`86c817d598e6c2f44ddd7a88ddcb34665d97adc73175b7914cb9d20d52aaf430`.
Its [external full-member verification](delivery_archive_full_member_verification.json)
records all 44 member hashes, CRC and 42 repository-source matches. It is an
author-review selection; the public repository tag supplies full project history.

Artifact QA and new statistics tests passed. The full software run remains
1257 passed / 13 failed / 1 skipped, with the original historical-environment
failures preserved; no CI/full-suite pass is claimed. The ethics basis and final
personal author review/approval remain unresolved, separate from the activated
scoped licenses. No new real fitting, query, Pod or paper-1 operation occurred.
