# Research storage in Cloudflare R2

On 2026-10-10 the user authorized Cloudflare R2 storage for subsequent project
datasets and research artifacts. The existing cloud runtime supplies credentials;
do not place them in configuration, notebooks, receipts or Git. The uploader
never prints the endpoint, bucket name or credential values.

Use `scripts/sync_research_r2.py` after each verified download or completed
analysis stage. Local files remain the working copies; R2 holds the durable
copies with explicit source-relative paths. Do not treat successful upload as
verification of dataset licensing, scientific suitability or source authenticity.
Those checks precede transfer and remain in their separate source receipts.

## Transfer policy

- All object keys are below `few-shot-mi-eeg/`. Dataset keys include their source
  release, for example `datasets/netbci2026/nm000305/v1.0.0`.
- Single-object creation and multipart completion require `IfNoneMatch=*`.
  Existing objects are never overwritten. Reuse requires the expected byte
  length, SHA256 metadata and a full GET whose bytes independently match SHA256.
  A conflict fails that file and requires an explicitly chosen new version key.
- SHA256 is computed before transfer and over the actual bytes sent. Each PUT
  or multipart part includes Content-MD5 for transport integrity. Multipart
  ETags are never described as SHA256 checksums.
- Every newly created object receives HEAD length and SHA256 metadata checks.
  By default the largest file of each extension also receives a full GET and
  SHA256 comparison. The receipt clearly distinguishes these two evidence
  levels; metadata verification does not imply all remote bytes were read back.
  `--readback-mode all` reads every new object in full when that cost is warranted.
- File-level concurrency is bounded at four workers. Default multipart parts
  are 32 MiB, streamed serially within each file. SDK network attempts are bounded
  at three. Failed multipart uploads are aborted rather than published.
- Receipts are atomically updated by the controlling thread after each file.
  Start another run with a new receipt filename to preserve prior failures.
  Existing matching objects will be independently read back and reused.
- Secret filenames, private-key extensions and symlink inputs are refused.
  Upload only explicit reviewed directories. Do not point the source at a home
  directory, credential directory, raw chat export or an unreviewed repository
  root. The script does not claim to detect every possible secret inside a file.

## Existing cloud environment

The optional S3 SDK is isolated at `/tmp/codex-r2-connectivity-sdk`, outside the
scientific virtual environment. It is not a new core modeling dependency. If
that temporary directory is unavailable after a restart, restore the optional
SDK before using the uploader; the EEG analysis environment is unchanged.

```bash
PYTHONPATH=/tmp/codex-r2-connectivity-sdk \
  /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/sync_research_r2.py \
  --source data/netbci2026/nm000305/v1.0.0 \
  --key-prefix few-shot-mi-eeg/datasets/netbci2026/nm000305/v1.0.0 \
  --receipt research_logs/netbci_cohort_resume_20261010/r2/raw_new_run.json \
  --readback-mode sample --workers 4 --execute
```

Without `--execute` this writes a local hash manifest and performs no transfer.
Choose a new receipt filename each time. Add newly verified participants to the
same pinned raw dataset directory and run again; conditional writes preserve the
previous data. Derived epoch bundles use a distinct release/policy prefix, so
their provenance cannot be confused with the original recording files.

For an incremental expansion, repeat `--include 'sub-11/**'` (and other new
participant paths). Every include pattern must select at least one file. This
keeps the same immutable dataset prefix while transferring only the explicitly
selected addition; earlier upload receipts remain the evidence for earlier data.

Scientific artifacts that change after another analysis should use a distinct
run or content version prefix, never reuse a prior key with changed contents.
Upload finalized receipts in a separate artifact stage after the data run closes;
never upload a receipt while it is still being rewritten.

Software tests cover conflicting object refusal, concurrent create races,
changed source files, independent readback corruption, multipart abort,
protected paths and credential-free error records. Real network receipts are
separate from those synthetic software tests.

## Verified recovery on 2026-10-11

The current environment reconnected successfully (HeadBucket HTTP 200). Earlier
uploads were retained rather than repeated:

| Stage | Objects | Bytes | Verification | Local receipt |
| --- | ---: | ---: | --- | --- |
| Original ten-person source subset | 1,885 | 2,049,560,417 | Original upload: HEAD on all, full GET SHA256 on five largest files by extension; current recovery: HEAD length and stored SHA256 metadata rechecked on all, zero missing/conflicting objects | `research_logs/netbci_cohort_resume_20261010/r2/raw_ten_20261010_run01.json`; `raw_ten_head_recheck_20261011_run01.json` |
| Ten-person full 5-second epoch bundles | 20 | 3,183,898,726 | Conditional upload and HEAD on all; largest NPZ and JSON full GET SHA256 verified (391,243,888 bytes read back) | `research_logs/netbci_cohort_resume_20261010/r2/full_window_bundles_ten_20261011_run01.json` |
| Private original-chat preservation archive and manifest | 2 | 12,238,340 | Both uploaded and fully read back with matching SHA256 | `research_logs/netbci_cohort_resume_20261010/r2/chat_backup_20261011_run01.json` |
| Full numeric signal-identity audit ledger and manifest | 2 | 11,050,966 | Both uploaded and fully read back with matching SHA256 | `research_logs/netbci_cohort_resume_20261010/r2/numeric_signal_identity_20261011_run01.json` |
| Immutable ten-person analysis outputs including sub-3 replay and software-check outputs | 188 | 13,296,015 | Every file uploaded and fully read back with matching SHA256, including model weights and reference arrays | `research_logs/netbci_cohort_resume_20261010/r2/analysis_results_ten_20261011_run01.json` |

These stages contain 2,097 distinct objects totaling 5,270,044,464 bytes. A
compact stage inventory is saved as
`research_logs/netbci_cohort_resume_20261010/r2/storage_catalog_ten_20261011.json`. The
HEAD recovery check is additional verification of existing objects and is not
counted as another upload. Full remote content was read back only for the
explicitly selected files; HEAD metadata agreement does not mean that every
remote byte was independently read back. No bucket policy, public URL or access
visibility was changed.

The derived bundle prefix is
`few-shot-mi-eeg/derived/netbci2026/nm000305/v1.0.0/full-window-5s/ten-participant-20261010-run01`.
The private preservation prefix is
`few-shot-mi-eeg/private-handoffs/20261010/original-chat-backup-run01`.
The archive retains the export's documented limitations; storage success does
not turn truncated historical outputs into complete transcripts.

For the nine-person raw extension, select only source-relative paths
`sub-11/**` through `sub-19/**` below the existing raw source directory, retain
the pinned original dataset prefix, and use a new upload receipt. Upload only
after the official source checksum receipts pass. The 19-person derived bundle
release and finalized analysis artifacts receive their own immutable version
prefixes after their scientific audits finish.

## Source checkpoint preserved on 2026-10-11

The already-pushed research commit `4290c4061f5d35381ed684bb07f1dd52836bbee0`
is preserved as a Git source archive, a verified Git history bundle and a
checkpoint manifest. All three objects (38,172,598 bytes) were conditionally
created and fully read back with matching SHA256. The prefix is
`few-shot-mi-eeg/code/checkpoint-4290c40/20261011-run01`; its receipt is
`research_logs/netbci_cohort_resume_20261010/r2/code_checkpoint_4290c40_20261011_run01.json`.
The source archive contains all tracked files at that commit, including completed
research documents and results. Untracked work, raw EEG data and runtime
credentials are outside the checkpoint archive.

The recorded-stage inventory after adding this checkpoint contains 2,100
distinct objects and 5,308,217,062 bytes. This counts the earlier ten-person
objects once; it is an inventory of explicit completed receipts, rather than a
listing of the entire bucket. The audit companion
`research_logs/public_data_expansion_20261010/r2/build_recorded_storage_catalog.py`
recounts each closed receipt from its file evidence, rejects conflicting
immutable keys and deduplicates repeated identical keys. The intermediate
inventory is `storage_catalog_before_raw_expansion_20261011.json` in that directory.

## Verified NETBCI and Kumar additions on 2026-10-11

Official source checks passed before these transfers. Their R2 receipts are in
`research_logs/public_data_expansion_20261010/r2/`.

| Addition | Objects | Bytes | Remote verification | Receipt |
| --- | ---: | ---: | --- | --- |
| NETBCI original source, IDs `sub-11`–`sub-19`, including all 216 original headers | 1,692 | 1,834,605,546 | HEAD on all; four format samples fully read back with matching SHA256 | `netbci_raw_nine_20261011_run01.json` |
| Kumar2024 original source, 18 published IDs, `nm000177` v1.0.5 | 2,705 | 1,781,052,841 | HEAD on all; four format samples fully read back with matching SHA256 | `kumar2024_raw_20261011_run01.json` |
| Kumar full continuous-signal source audit | 362 | 5,127,511 | Every object fully read back with matching SHA256 | `kumar2024_signal_audit_20261011_run01.json` |
| Kumar frozen source receipts, failed initial audit record, independent checks, source code and report | 19 | 8,201,327 | Every object fully read back with matching SHA256 | `kumar2024_source_evidence_20261011_run01.json` |

The NETBCI addition uses the original immutable dataset prefix and includes only
the exact officially verified new participant and corresponding `sourcedata`
paths. It adds 1,692 objects; the earlier ten IDs and five shared root metadata
files were not uploaded again. An independent source-to-transfer-plan comparison
is stored in `netbci_raw_nine_source_gate_20261011.json`.

Kumar data use `few-shot-mi-eeg/datasets/kumar2024/nm000177/v1.0.5`.
The successful source audit and the frozen source evidence have their own prefixes
under `audits/kumar2024/.../source-signal-20261011-run02` and
`research-evidence/kumar2024/.../source-ingestion-20261011-run01`.
Original source events, including incomplete windows, remain recorded in the
audit; storage completion does not imply that a modeling eligibility decision has
been made or that subjects across repositories can be pooled.

The intermediate completed-stage catalog
`storage_catalog_after_netbci_kumar_20261011.json` records 6,878 distinct objects,
8,937,204,287 bytes and 591 objects with independent full GET SHA256 evidence.
Other recorded objects have verified HEAD length and stored SHA256 metadata.
Later public-dataset and nineteen-ID derived releases are additional stages;
this snapshot does not count files still in transit.

## Continued nineteen-ID transfer after tunnel recovery

The managed HTTPS tunnel returned HTTP 503 during the first nineteen-ID and
MILimb transfer attempts. Those failed `run01` receipts retain zero verified
objects. The user confirmed that no environment configuration was changed.
After the existing environment again returned HeadBucket HTTP 200, transfers
resumed with new receipt names and the same conditional immutable object keys;
credentials, TLS settings and bucket visibility were unchanged.

| Nineteen-ID stage | Objects | Bytes | Remote verification | Receipt |
| --- | ---: | ---: | --- | --- |
| Full-window derived epoch bundles | 38 | 6,035,422,199 | HEAD on every object; largest NPZ and JSON fully read back, 391,243,934 bytes with matching SHA256 | `netbci_all19_bundles_20261011_run02.json` |
| Completed source/adapter audits | 134 | 12,769,840 | Full GET SHA256 on every object | `netbci_all19_source_audits_20261011_run02.json` |
| Full numeric identity ledger and frozen source/configuration/manifest | 6 | 21,712,078 | Full GET SHA256 on every object | `netbci_numeric_identity_v2_20261011_run01.json` |
| All nineteen completed model-analysis output directories | 323 | 23,037,986 | Full GET SHA256 on every object, including model weights and reference arrays | `netbci_all19_analysis_results_20261011_run01.json` |

These receipts are under `research_logs/public_data_expansion_20261010/r2/`.
The source gate independently matches all bundles to closed adapter receipts;
the model-output gate independently rehashes each file recorded in all nineteen
analysis receipts. Documented scientific failures and source identity issues are
preserved in storage. Completion of a transfer does not establish nineteen
independent EEG subjects or qualify a failed scientific comparison.

The derived release prefix is
`few-shot-mi-eeg/derived/netbci2026/nm000305/v1.0.0/full-window-5s/nineteen-id-20261011-run01`.
The full numeric ledger is below
`few-shot-mi-eeg/audits/netbci2026/nm000305/v1.0.0/numeric-signal-identity-nineteen-id-20261011-run01`.
The finalized model outputs are below
`few-shot-mi-eeg/results/netbci2026/nm000305/v1.0.0/nineteen-id-frozen-decoder-20261011-run01`.

The closed-stage snapshot `storage_catalog_after_netbci_all19_20261011.json`
also includes the earlier four original Leeuwis sidecar objects. It counts
7,383 completed immutable keys, 15,040,654,943 bytes, and 1,060 objects with
independent full GET SHA256 evidence. It counts each key once and excludes
failed and planned transfer receipts.
Later public-resource and final research checkpoints have separate receipts.

## Closed PhysioNet and MILimbEEG source releases

The restored connection also completed the following six stages, with zero
failed objects. Source raw files were independently rehashed against the exact
official selection manifests before transfer. Every audit and frozen evidence
object was fully read back and SHA256 checked.

| Stage | Objects | Bytes | Full GET objects | Receipt |
| --- | ---: | ---: | ---: | --- |
| PhysioNet v1.0.0 selected hand-imagery raw recordings and annotation sidecars | 654 | 834,146,640 | 2 format samples | `physionet_raw_20261011_run01.json` |
| PhysioNet complete signal audit and its snapshot manifest | 4 | 3,492,631 | 4 | `physionet_signal_audit_20261011_run01.json` |
| PhysioNet frozen source and independent validation evidence | 22 | 1,170,080 | 22 | `physionet_source_evidence_20261011_run01.json` |
| MILimbEEG `nm000328` v1.0.0 selected raw source | 666 | 62,287,177 | 5 format samples | `milimbeeg_raw_20261011_run02.json` |
| MILimbEEG complete signal audit and its snapshot manifest | 63 | 4,279,907 | 63 | `milimbeeg_signal_audit_20261011_run01.json` |
| MILimbEEG frozen source and independent validation evidence | 23 | 5,208,782 | 23 | `milimbeeg_source_evidence_20261011_run01.json` |

PhysioNet transfer selects exactly 327 officially verified EDFs and 327 official
annotation sidecars for runs 04, 08 and 12; four abandoned `.part` files were
excluded. The immutable prefix is
`few-shot-mi-eeg/datasets/physionet-eegmmidb/1.0.0/left-right-hand-imagery-r04-r08-r12`.
Although the source contains 109 IDs, the closed audit flags source annotation
disagreements and qualifies 315 recordings from 105 complete three-run IDs.
All original bytes, including flagged recordings, remain preserved in R2.

MILimbEEG raw files use
`few-shot-mi-eeg/datasets/milimbeeg/nm000328/v1.0.0`. Its source label, timing,
unit and participant-group caveats remain in the frozen evidence. Durable
storage does not imply that the resource is eligible for a pooled healthy
subject training set or for longitudinal human-retention analysis.

`public_closed_sources_delivery_20261011_run01.json` independently recounts the
six receipts. The completed-stage catalog
`storage_catalog_after_physionet_milimb_20261011.json` records 8,815 distinct
objects, 15,951,240,160 bytes, and 1,179 objects with independent full GET SHA256
evidence. This snapshot excludes still-transferring Leeuwis and Liu releases.

## Scientific closeout on 2026-10-12

The six selected raw releases are now closed in R2: NETBCI, Kumar2024,
PhysioNet EEGMMIDB, Leeuwis2021, MILimbEEG and Liu2024. Their original source
and NeMAR mirror identities count as one resource each. The raw selection
contains 10,253 files and 7,827,676,824 bytes; the four original Leeuwis
non-EEG sidecars add 10,508,553 bytes. Leeuwis raw data use
`few-shot-mi-eeg/datasets/leeuwis2021/nm000327/v1.0.0` (2,095 objects,
568,544,461 bytes), and Liu raw data use
`few-shot-mi-eeg/datasets/liu2024/nm000158/v1.0.3` (556 objects,
697,479,742 bytes). Each passed HEAD length/SHA256 metadata checks and five
format samples passed full GET SHA256 verification. Their closed receipts are
`leeuwis2021_raw_20261011_run01.json` and `liu2024_raw_20261011_run01.json`.
Earlier raw, derived-array and model-output objects were retained; this final
evidence closeout did not upload them again.

The restored runtime again supplied ready R2 variables and enforced networking.
The optional uploader SDK remains isolated from the scientific environment
(`boto3==1.43.111`). Explicit reviewed files were copied into immutable staging
directories, with each original and staged byte sequence checked for agreement.
Each stage has an exact source-path/SHA256/length manifest and a separate closed
transfer receipt. Every object in the following six stages passed independent
full GET SHA256 verification, with zero failed objects:

| Final evidence stage | Objects | Bytes | Closed receipt |
| --- | ---: | ---: | --- |
| Complete Leeuwis signal/source-event audit, including all large ledgers | 226 | 15,475,636 | `leeuwis2021_signal_audit_20261012_run01.json` |
| Complete Liu source-integrity census run03 | 56 | 1,842,847 | `liu2024_source_integrity_census_20261012_run01.json` |
| Leeuwis source evidence, independent reviews and failed/partial historical audits | 170 | 17,141,087 | `leeuwis2021_source_evidence_20261012_run01.json` |
| Liu independent review v4, strict failed run02 and earlier representative audits | 107 | 3,807,561 | `liu2024_source_evidence_20261012_run01.json` |
| Nineteen-ID final scientific tables, reviews, notebook, figures and software checks | 467 | 31,432,355 | `netbci_all19_scientific_evidence_20261012_run01.json` |
| Six-source inventory, official source metadata and preserved public-resource surveys | 296 | 25,601,025 | `public_resource_inventory_20261012_run01.json` |

These 1,322 final evidence objects total 95,300,511 bytes. The complete Leeuwis
audit preserves 220 recordings and the large source-event, continuous-run and
verified-source ledgers that are intentionally excluded from Git. Its earlier
partial audit and both independent review versions remain preserved. The Liu
census has completed source inspection while retaining
`source_acceptance_complete=false`; all 50 native BDF headers report microvolts
while source sidecars report volts. The source conflicts, duplicate annotations,
original annotation flags and earlier strict audit failures were archived
unchanged. Successful storage does not change the modeling eligibility gates.

The nineteen-ID evidence snapshot includes all 285 exact small analysis
snapshots (19,169,738 bytes), independently matched to their original completed
model outputs and recorded digests. It preserves the final summary, exploratory
14-ID source-copy exclusion sensitivity, independent reviews, executed notebook
and HTML, all seven native figures in PNG/SVG/PDF, and the closed final visual
QA receipt. The software checks retain their software-only interpretation.
The final resource inventory independently rechecks 78 referenced artifacts;
its raw-root census does not reread EEG signal arrays.

The explicit 29-stage catalog is
`research_logs/public_data_expansion_20261010/r2/storage_catalog_scientific_closeout_20261012_run01.json`.
It counts 12,788 distinct immutable keys, 17,312,564,874 bytes, and 2,511 objects
with independent full GET SHA256 evidence. Recorded readback totals
1,095,668,103 bytes. This is a recount of supplied closed receipts, not a full
bucket listing. Failed/planned transfer receipts and HEAD-only recovery checks
are retained but do not add objects to the completed catalog. The final pushed
source checkpoint and the frozen receipt/catalog metadata archive receive
separate immutable receipts after this scientific closeout.

## Final pushed research source checkpoint

The scientific commit `2fc09a16bcce81938757bdc77e01a2f551ef6529` was committed
and pushed to `research/learning-preserving-bci` before archival. Its Git source
archive, complete local-ref history bundle and full source-file manifest are
stored below `few-shot-mi-eeg/code/checkpoint-2fc09a1/20261012-run01`.
All three objects (75,554,783 bytes) were conditionally created and fully read
back with matching SHA256. The closed receipt is
`research_logs/public_data_expansion_20261010/r2/code_checkpoint_2fc09a1_20261012_run01.json`.

Every one of the archive's 2,736 tracked source files (183,656,143 uncompressed
bytes) was verified against the exact committed Git blob; the Git archive
commit header and the bundle's research-branch reference match that commit.
`git bundle verify` passed. The manifest records each source-relative path,
Git blob identity, SHA256 and byte length, plus independent SHA256 digests for
the 41,334,048-byte source archive and 33,271,370-byte history bundle. Ignored
raw EEG arrays and large ledgers remain in their separate verified R2 stages.

The 30-stage closed catalog
`storage_catalog_after_checkpoint_2fc09a1_20261012_run01.json` records 12,791
distinct immutable objects, 17,388,119,657 bytes, and 2,514 full GET SHA256
objects. Recorded readback totals 1,171,222,886 bytes. Final archival receipts,
catalogs and delivery-state metadata are frozen once after this checkpoint.
A later metadata-only Git commit does not trigger another source-history
archive; the metadata snapshot excludes its own still-open receipt.

## Closed final receipt and catalog metadata archive

The last metadata snapshot froze 117 reviewed source files (13,386,510 bytes),
including every preceding closed receipt/catalog, the preserved failed/planned
records, the exact source manifest, current handoff/state documentation,
resource-inventory validation and the software receipt's latest Git metadata.
The source list and source-path/SHA256/length manifest are
`final_receipt_metadata_selection_20261012_run01.json` and
`final_receipt_metadata_snapshot_manifest_20261012_run01.json`.
The snapshot manifest adds one object, giving 118 objects and 13,430,808 bytes.
All 118 were conditionally created and fully read back with matching SHA256,
with zero failed objects. The prefix is
`few-shot-mi-eeg/research-evidence/final-receipts-and-catalogs/20261012-run01`;
the closed receipt is `final_receipt_metadata_20261012_run01.json`.

`storage_catalog_final_20261012_run01.json` recounts the final explicit 31
completed stages: 12,909 distinct immutable objects, 17,401,550,465 bytes,
and 2,632 objects with independent full GET SHA256 evidence. Recorded readback
totals 1,184,653,694 bytes. The last archive's own closed receipt, this final
recount and `final_storage_delivery_20261012_run01.json` are retained in the
metadata-only Git closeout. They are outside the frozen metadata snapshot;
no receipt captures itself and no source-history archive loop is required.
All prior source-authenticity and scientific-eligibility caveats continue to
apply independently of durable storage completion.


## 2026-10-14 task-aware Kumar baseline checkpoint

Current scope is Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG. Existing six-source and NETBCI objects remain immutable. The new CPU baseline has18 participants/324model rows/12,870predictions;618result objects54,272,330bytes passed full GET SHA256. New frozen scientific evidence1236objects98,076,860bytes also passed full GET. Current HEAD revalidation14,399objects passed; HEAD and full-content scopes remain distinct. MIND90-run V4 acquisition is still partial and continues under the authorized manifest. Exact recovery catalogs and closing receipts are in research_logs/recovery_20261014; current handoff is NEXT_STAGE_HANDOFF.md.
