# MIND source and R2 receipt linkage review

Captured 2026-10-14T07:03:33.491999+00:00. Read-only review: no process restart, network request, upload, policy change or fresh raw-signal reread. Prior actual pipeline evidence was checked through fresh local native-audit pair hashes and manifest/source/R2 identity linkage.

**60/90 source/native/R2 runs are closed**; 20 released IDs have all three runs closed. Prior full GET SHA256 evidence covers **665/695 source files**, **21,444,190,502 bytes**. Remaining full-file deficit: **10,528,665,600 bytes**, with partial ranges recorded separately. Closed signals total 21,443,148,800 bytes. MIND remains incomplete. Integrity closure does not establish model qualification or unique biological participant count.

Every closed run passed official V4 size/MD5 identity, source/R2 SHA256 linkage, native finite 64-channel/1000 Hz audit, event count and identity, native audit + event-ledger pair SHA256, nine source path bindings and prior HEAD 200/full GET 200 assertions. Clock and quality flags remain preserved. The oldest audit lacks the later redundant binary SHA256 alias, and the first four closures lack an embedded pair; their separate audit-pair receipts bind exactly to the actual audit/event bytes and remote source identity.

Supervisor PID 5558 and controller PID 5563 were live. Current state: source_downloading, sub-21_task-mi2d_run-01. Pause at 55 was source HTTP 503 with zero range bytes and cache preserved. Restart 06:34 UTC recorded R2 HeadBucket 200 and one range worker. Earlier known 429 uses bounded cooldown; unknown integrity failures remain unqualified for retry. Do not duplicate the active controller.

In-memory preview including all prior extras and final-ledger/support stages: **16,111 keys / 44,323,932,103 bytes**, **5,834 full GET SHA256 objects**. This is a preview; the prior final-storage catalog stops at 43 runs. Create a formal immutable snapshot with:

```bash
cd /workspace/few-shot-mi-eeg
PYTHONPATH=/tmp/codex-r2-connectivity-sdk /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/audit_download_recovery.py \
  --output research_logs/recovery_20261014/mind_support_cumulative_catalog_run01 \
  --extra-receipt research_logs/recovery_20261014/kumar_results_R2_run01.json \
  --extra-receipt research_logs/latest_two_sources_20261012/mind_ingestion/full_eeg_v4/checkpoint_archives/closed_runs_0017_recovery_20261013/checkpoint_all_objects_receipt.json \
  --extra-receipt research_logs/recovery_20261014/scientific_evidence_R2_run01.json \
  --extra-receipt research_logs/recovery_20261014/code_checkpoint_R2_run01.json \
  --extra-receipt research_logs/recovery_20261014/closing_metadata_R2_run01.json \
  --extra-receipt research_logs/recovery_20261014/final_ledger_R2_run01.json \
  --extra-receipt research_logs/recovery_20261014/support_reliability_R2_run01.json \
  --extra-receipt research_logs/recovery_20261014/support_validation_R2_run01.json
```

Output must not exist; choose another suffix if needed. Historical 31 receipts and Wang/Liu 2 stages are included automatically. Current MIND single receipts are normalized automatically; do not add an older normalized snapshot. Optional `--head-all-recorded` establishes fresh HEAD length/SHA256 metadata separately from full GET evidence. The CLI rehashes 10,253 historical local files without source download/reupload. Concurrent later closures belong to later snapshots. This review and subsequent ledger archives intentionally remain outside the preview to avoid recursive counting.

All checks and local reference hashes are in `receipt.json`.
