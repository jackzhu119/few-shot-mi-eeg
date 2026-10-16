# Author-confirmation record synchronization

The actual author statement, bound manuscript identities, dated addendum and
current navigation updates are backed up as **9 objects / 106,829 bytes**,
all with complete R2 GET/SHA256 checks and zero failures.

- [Full R2 receipt](r2_full_get_receipt.json): 8487 UTF-8 bytes,
  SHA256 `afc76edc03e57f6eaa01aac700f2da68f207397a95bf83526ecfcff589371607`.
- [Local reconciliation](verification.json) rehashes each payload and matches
  current repository files; it does not claim another remote GET or a parent ACK.
- [Explicit payload manifest](payload_manifest.json) records the selected files.

The backup was planned from checkout baseline `c1544fd`; these new author
records are bound by the later metadata Git commit. The approved scientific
manuscript remains `f2901de` / `paper2-plos-source-20261016`, unchanged.

The receipt and this final synchronization metadata are held in Git; no circular
self-GET or unchanged manuscript re-export is claimed. This is a metadata-only
update, with no real fit/query, Pod, paper-1 or journal-submission action.
Ethics is author-reported approval with committee/date/identifier/scope pending;
the author's review date is not an invented ethics date.
