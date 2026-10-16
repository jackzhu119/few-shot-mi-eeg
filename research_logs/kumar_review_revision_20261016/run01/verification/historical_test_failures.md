# Historical test failures retained

**The full test suite failed:** 13 failed, 1257 passed, 1 skipped, 63 warnings; exit code 1. This is not a CI or full-suite pass. The original log and protected tests remain unchanged.

The observed causes are ten historical host-identity rejections, one child-process import-path failure, one existing historical query-state rejection, and one disk-reserve rejection. These findings do not authorize another historical operation.

## Individual failures

| # | Failed node | Observed cause and limitation |
|---:|---|---|
| 1 | `test_kumar_csp_run02_identity.py::test_exact_documented_gate_passes_read_only_with_original_claim_present` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 2 | `test_kumar_csp_run02_identity.py::test_wrong_authorization_identity_refused[deadline-Original window]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 3 | `test_kumar_csp_run02_identity.py::test_wrong_authorization_identity_refused[run01-Run02 identity]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 4 | `test_kumar_csp_run02_identity.py::test_wrong_authorization_identity_refused[template-Exact CPU-only]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 5 | `test_kumar_csp_run02_identity.py::test_wrong_authorization_identity_refused[contract-Exact CPU-only]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 6 | `test_kumar_csp_run02_identity.py::test_existing_run02_identity_stops_without_cleanup[directory-results/kumar_csp_signed_score_20261015/run02]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 7 | `test_kumar_csp_run02_identity.py::test_existing_run02_identity_stops_without_cleanup[directory-research_logs/kumar_next_source_operations_20261015/csp_signed_score_operation_run02]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 8 | `test_kumar_csp_run02_identity.py::test_existing_run02_identity_stops_without_cleanup[dangling_symlink-results/kumar_csp_signed_score_20261015/run02]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 9 | `test_kumar_csp_run02_identity.py::test_existing_run02_identity_stops_without_cleanup[dangling_symlink-research_logs/kumar_next_source_operations_20261015/csp_signed_score_operation_run02]` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 10 | `test_kumar_csp_run02_identity.py::test_original_deadline_cleanup_margin_cannot_be_renewed` | `Recovery host changed`; current host differs from the old binding and rejects before the intended pass or later check. |
| 11 | `test_kumar_development_batch.py::test_real_timeout_wrapper_preserves_GPU_lock_fd_and_bounds_CPU_child` | Child cannot import the old batch script; its scripts-directory path is missing. The lock-success branch is not reached. |
| 12 | `test_kumar_frozen_query_operation.py::test_default_metadata_reads_no_archive_or_signal` | Metadata correctly reports existing state; the old test expected no problems. No query/archive/model was opened. |
| 13 | `test_kumar_gpu_preparation.py::test_hash_conflict_never_promotes_download` | Actual disk-reserve check fails before the synthetic hash-conflict branch; no download is promoted. |

## Why the gates remain closed

The recovery handoff requires exact agreement among current host identity, saved binding, prior failure receipt and authorization. All three current identity fields differ from the historical binding. Ten tests therefore encounter the genuine host rejection before their expected pass or later rejection. This does not demonstrate that the later deadline, identity or duplicate-output checks passed on this host.

The default query metadata check sees the real historical state directory and claim. Its no-retry/no-overwrite message is correct; the old expectation of an empty problem list is incompatible with that preserved state. Its no-query/archive/model-open assertions precede the failing assertion.

The restore test encounters the unchanged `needed + 5 GiB` reserve check before its fake client can supply corrupt bytes. The original traceback does not record exact free bytes. A later read-only observation found 4796116992 bytes free, below the 5368709120-byte reserve. This later measurement is not substituted for a historical test-time measurement.

The watchdog test launches a synthetic CPU child with `python -c`. The child lacks the scripts-directory import path available in pytest and fails while importing the old batch module. This is a test-environment limitation, not evidence that the production lock or timeout guard passed or changed.

## Preservation and attribution limits

All four historical test files are in the 816-entry `preservation_before.json` protection list. Their bytes, the four corresponding production scripts and three related configurations match the recorded SHA256 values. The recovery gate document and binding also match the original checkout recorded before new statistics calculations (`a78372db00cd4161e713ab47aca2d93c643a52bb`). The JSON companion records each comparison.

No failing traceback enters the new statistics or figure producers, and the protected historical sources do not import the new producer. The observed errors point to the environment/history conditions above rather than new statistical arithmetic or figure-code changes. A controlled full-suite rerun on the prior checkout was not performed, so universal freedom from regressions is not established.

The earlier targeted post-review statistics run actually passed **24 synthetic software tests**; see [`portable_validation_receipt.json`](../statistics/audit/portable_validation_receipt.json). It also records byte-identical fresh-path replay and exact comparison with the independently checked saved-endpoint audit. These tests were not rerun here, and their pass does not make the whole suite green. Original Ruff, smoke and data-stack passes retain their limited software-validation scope.

No protected test, production gate, configuration, binding, claim, saved result or original log was edited. No failing test was suppressed, no plugin was added, and no fitting, real query evaluation, bootstrap recalculation or experiment was performed.

## Evidence

- Original log: [`pytest.log`](pytest.log), SHA256 `98d16e34d621cdfc2ecd558391250d72c82ddc58ae94df4dbb58439a23fa8e27`.
- Original command receipts: [`checks_receipt.json`](checks_receipt.json).
- Per-failure attribution and byte checks: [`historical_test_failures.json`](historical_test_failures.json).
- Targeted statistics validation: [`portable_validation_receipt.json`](../statistics/audit/portable_validation_receipt.json).
