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
