# Independent phase-consumer software review

This review covers the thin `execute_bound_inputs` path in `scripts/run_kumar_phase_window_cpu_20261016.py` and its use of the existing guarded worker and persistence helpers. The reviewed file hashes, actual UTC and exact test command are in `consumer_synthetic_test_receipt.json`. This is synthetic software validation, not a completed scientific comparison or independent confirmation of real inputs.

## Finding and correction

The first static pass found that the participant path retained an empty-prediction JSON, but the final aggregate unconditionally called the shared CSV writer with an empty prediction list. The shared writer rejects empty tables. Therefore a valid inventory with all target cells undefined would fail before its 540-row/null aggregate could be preserved. The phase owner applied the minimal matching global `query_predictions_empty.json` branch. A targeted lifecycle test now exercises all 18 synthetic participants with unknown target-query phases and verifies all 540 null cells, zero complete pairs and a completed evidence inventory. This does not treat absent or one-class queries as chance accuracy.

## Verified behavior

- The consumer rejects an unrelated `__main__` caller, changed mode/window settings, a changed scientific protocol, unsafe mapping paths and mismatched mapping text pins before loading source state or any signal. The shared worker remains responsible for actual authorization, parent identity, CPU lock, monitoring and deadline gates; the consumer does not implement a second launcher.
- The synthetic 7,200-row inventory exercises the exact 18-participant/400-row checks. Duplicate trial identity, a changed mapping class and a changed saved-prediction digest stop before source/signal access.
- The real materialization/reader path is exercised against synthetic raw objects. The fixture deliberately includes many validation and source-query rows: none is read. Only source TRAIN, current support and target-query intervals reach the reader. Synthetic raw-file, raw-window and processed-window digest mismatches stop before the first estimator callback.
- The full successful synthetic lifecycle writes exactly 540 distinct participant/session/window/method metric cells and binds all 72 historical source-file hashes plus actually verified synthetic dataset files in the final before/after manifest.
- The synthetic estimator callback never constructs an estimator. It sends a finite synthetic state through the actual shared checkpoint helper. Injected checkpoint write and checkpoint hash failures each preserve first-participant partial evidence and an exception receipt, propagate the original exception and prevent any next fit callback or next participant. The hash-failure test also verifies that the already written synthetic checkpoint remains present.
- A changed historical input immediately after the first participant stops before participant two. A changed mapping during final verification prevents a completed receipt. A claim already inside the 30-second cleanup reserve preserves a failure receipt without loading state, reading signals or invoking a fit callback.
- The companion engine tests exercise window identity, training/query separation, missing support/classes, expected estimator failure boundaries, state immutability, participant-level aggregation and a small real estimator API call using synthetic arrays only.

## Actual checks and limits

`tests/test_kumar_phase_consumer_20261016.py` contributes 20 passing consumer cases. Together with the existing 22 phase-engine cases: **42 passed, 0 failed** in 9.34 seconds. Ruff passed on the new test file.

The fixture's files, raw arrays and source state are synthetic. Historical NPZ loading, raw EEG decoding and scientific estimator fitting are mocked in the thin-consumer lifecycle; the production serializer is exercised under pytest's temporary directory only. Its production `synthetic=false` branch is not evidence of a real operation. This review did not read original EEG, historical NPZ contents or actual query prediction rows and did not run a scientific fit or operate a Pod. It does not replace the shared runner's authorization/resource tests, pre-execution exact pins or the later independent review of any real result.
