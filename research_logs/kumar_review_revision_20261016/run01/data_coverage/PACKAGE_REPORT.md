# S1 Data 2026-10-16 package build

Final candidate ZIP: `1,423,505` bytes, `69` members, SHA256 `dccb1d88f4decae03794bc2fa81ead788cff87d2dd13b172f8b55d7e1e373416`.

Created only the authorized new data artifact files in the repository:

- `manuscript/plos_one_submission_20261016/S1_Data.zip`
- `manuscript/plos_one_submission_20261016/S1_Data_manifest.json`
- `manuscript/plos_one_submission_20261016/S1_Data_README.md`
- `manuscript/plos_one_submission_20261016/DATA_DICTIONARY.md`
- `manuscript/plos_one_submission_20261016/REPRODUCE_SAVED_RESULTS.md`

The ZIP has 68 payload members plus the self-excluded current `MANIFEST.json`.
All current payload hashes/sources/license classifications are in the internal
manifest. The external manifest additionally records every actual member's bytes,
SHA256 and CRC32, and the full archive identity. It records actual bytes rather
than an impossible self-containing Git commit. The parent will bind the final
source tag/release manifest.

Original41-member preservation: 38 members retain their original path and exact
bytes. Root DATA_DICTIONARY.md, REPRODUCE_SAVED_RESULTS.md and MANIFEST.json were
updated; their exact original bytes are retained under
`provenance/historical_20261015/`. All41 historical contents remain present. The
original2026-10-15 ZIP is still591,742bytes, SHA256
`797d0e4c2f913428b864688cebcf182f65e022f2fcd7e5225cd919701740867b`.

Added data:10 numeric-text members from the prior verified allowlist extraction;
7 existing postreview files (producer,test,2inputs,results CSV,execution receipt,
portable-validation receipt); operative component-specific licensing with full
MIT/CC BY legal texts; source attribution and pure-text field/SHA provenance.
The canonical root license texts and the7 postreview files are exact source-byte
copies. Four figure-source tables match the new2026-10-16 tables exactly.

No new BA,correlation,p-value,bootstrap or model calculation was performed while
packaging. The original2000-draw drift correlation vectors were never saved and
were not generated. The included reliability draw vectors are exact existing
saved arrays. EEG samples,feature matrices,fitted axes/scaler/PCA states/model
weights,credentials,operational authorizations and third-party paper/codebook full
texts are excluded. Existing source-derived metadata retain source attribution.

Reproduction instructions distinguish the originalQC producer's existing output
directory from the paired-check producer's required absent output directory.
They show the tests' required `scripts/` layout and require recorded versions
when comparing the version-bearing paired-check execution receipt byte-for-byte.
Old historical manifest paths are explicitly identified as the original archive's
paths,with reconstruction/remap guidance.

One independent documentation correction caused repackaging: an old blanket
“No new hypothesis test/p value” sentence is now limited to the originalQC tables.
Only dictionary,reproduction instructions and current internal manifest changed;
the other66 initial-package members remain identical. See `repackaging_history.json`.
The first ZIP was restored exactly against its recorded43a77d...SHA in
`initial_package_before_dictionary_scope/`. Its original external manifest had
already been replaced before the later retention instruction arrived; the saved
replacement explicitly says reconstructed and leaves its original creation time
unknown. It is not misrepresented as the original manifest bytes.

Builder `build_s1_data_20261016.py` and source-preservation receipt
`package_build_receipt.json` remain in this private directory. No repository
manuscript,producer script,test or old experiment file was changed by packaging.
The newZIP is ignored by `.gitignore` and needs explicit authorized staging
by the parent for publication.

Independent validation is recorded separately in `package_independent_validation.json`
and its accompanying Markdown when completed. Final parent handoff will report
that result,not infer success from this note.

Independent validation completed successfully against final dccb1d88...: all69 external member hashes/CRCs,all68 internal hashes,38same-path old members+3historical exact copies,10numeric and7postreview source-byte copies,34CSV schemas/counts,license texts and static reproduction instructions passed. No unresolved finding; no statistics or pytest executed by packaging/audit.
