# CSP signed-score CPU memory operation proposal — 2026-10-15

This is a resource-operation proposal for the already frozen development-only
measurement. It is not execution authorization or evidence that a scientific
measurement has run. The previous **8 GiB effective available RAM** proposal
cannot pass in an **8 GiB total** memory cgroup while that cgroup has any usage.
It must remain a recorded failed proposal; the revised gate needs separate parent
review. No new environment, paid resource, package installation or data transfer
is proposed.

## Frozen workload and static method

The six participants remain sub-1/4/7/10/13/16, with 240 SOURCE TRAIN and 596
current-support epochs, 836 total, each 22 channels × 640 samples, float32. The
consumer loads one participant at a time: metadata counts are respectively
139/139/140/139/140/139 epochs in subject order. It retains result dictionaries
for completed participants, not their full EEG tensors.

Preparation has already performed average referencing, the frozen 8–30 Hz
filtering and resampling from 512 to 128 Hz. The signed-score consumer reads the
existing prepared restricted NPZs. It neither rereads raw EDF nor filters again.
Accordingly this budget includes **zero new filtering buffers**. Changing the
consumer to perform preparation would invalidate this budget and input binding.

The static review covers `analyze_kumar_csp_signed_score_v1.py`, the imported
low-dimensional and baseline helpers, `decoders/csp_lda.py`, and readable installed
MNE 1.10.2 CSP/covariance and scikit-learn covariance source. Only Python stdlib
integer arithmetic, JSON metadata and `/proc`/cgroup reads were used for this
review. No NumPy/MNE import, NPZ/EEG array load, estimator fit or scientific timing
measurement was performed. All MiB/GiB below use powers of 1024; the 47.08 MB
decimal core is **44.90 MiB**, not 47 MiB in binary units.

## Conservative resident-memory envelope

The column labelled reserve is an engineering allowance, **not measured RSS**.
For conservatism, the tensor/conversion estimates below allow the entire 836-row
cohort to coexist, although the implementation loads at most 140 rows at once.
This is a static feasibility proposal with a runtime stop boundary, not a proven
worst-case bound for the interpreter or native libraries.

| Item | Frozen-workload calculation and reasoning | Reserve MiB |
| --- | --- | ---: |
| Canonical float32 epochs | 836 × 22 × 640 × 4 = 47,083,520 bytes = 44.9023 MiB; actual one-subject maximum is 7.5195 MiB | 64 |
| Float64 input conversions and additional full-size copies | One all-cohort float64 copy is 89.8047 MiB; two simultaneous copies are 179.6094 MiB. This covers `np.asarray(..., dtype=float)` paths and a further conversion/native copy with rounding margin | 256 |
| NPZ extraction, previous/next participant overlap and fold indexing | Loading uses an extraction plus `.copy()`; assigning the next subject may briefly retain the previous `X`. Two SOURCE20 folds keep advanced-indexed train/holdout copies. One 20-trial float64 copy is 2.1484 MiB | 64 |
| CSP projection, squaring, features and predictions | All-cohort 836 × 4 × 640 float64 projection = 16.3281 MiB, with another 16.3281 MiB for its square. Four-feature rows, labels, scores and SOURCE20 held-out prediction vectors are small | 64 |
| CSP/LDA covariance, learned state and native linear algebra scratch | Each covariance/filter matrix is only 22 × 22 float64 (3,872 bytes); SOURCE20 fit input is 2.1484 MiB float64. MNE rank/covariance and Ledoit–Wolf copying/SVD/eigh/lstsq get an intentionally large extra allowance. There is one active pipeline, not 240 concurrent models | 128 |
| Participant bootstrap | One 10,000 × 6 int64 index matrix plus sampled float64 values plus 10,000 means is 1,040,000 bytes = 0.9918 MiB. There are two participant summaries; retained Python float lists and quantile scratch are included | 16 |
| Cached controls, metadata and accumulated Python result trees | Per participant 40 pipeline attempt records, 400 joint phase-pair records/two folds, and five 19/20-shift support-control records. All six result trees remain in memory; cached predictions/scores are small lists, not fitted-model or EEG caches | 112 |
| Serialization, NPZ compression/decompression and streamed hash buffers | Full final JSON tree encoding/decoding, ZIP/native compression and file-hash streams. `file_digest` reads 1 MiB blocks; tensor content hashes may temporarily materialize bytes. Includes output page/cache pressure allowance but not a guarantee about all shared cgroup file cache | 128 |
| CPython, imported MNE/SciPy/scikit-learn/NumPy and shared native libraries | Conservative allocation for startup/import/lazy-import footprint, object machinery and dynamic-loader pages; no actual imported-consumer RSS measurement is claimed | 768 |
| Native allocator retention and unmodelled transient allowance | Additional margin for libraries retaining arenas, temporary arrays and sum-of-process RSS double-counting shared pages | 256 |
| **Total proposed resident envelope** | **1,856 MiB = 1.8125 GiB; 192 MiB below the 2 GiB RSS stop boundary** | **1,856** |

The 240 source-phase pipelines remain 20 train-label rotations × two folds × six
participants, executed sequentially. Only predictions/state hashes and result
records are cached; no 240-fold multiplier applies to the EEG working set. The
support controls use existing frozen SOURCE40 CSP/LDA state, and no new SOURCE40
decoder, normalization or bootstrap configuration is introduced. Participant
bootstrap stays 10,000 replicates/seed42; all scientific threads remain one.

## Proposed gates and stop conditions

Freeze these exact operation values for review, without altering the scientific
protocol, configuration, parallelism, numerical threads or tolerances:

| Boundary | Proposed value and semantics |
| --- | --- |
| Preflight effective available memory | **At least 3 GiB = 3,221,225,472 bytes**, as the minimum of host `MemAvailable` and the headroom of every observable finite governing memory cgroup. Unreadable or ambiguous proof fails closed |
| Consumer process-tree RSS | **Stop at or above 2 GiB = 2,147,483,648 bytes**, conservatively summing the consumer and any live descendant process RSS. Do not substitute virtual size or the supervisor's RSS |
| Governing cgroup remaining headroom | **Stop at or below 1 GiB = 1,073,741,824 bytes** in any observable finite governing cgroup, accounting for all processes and file cache in that cgroup |
| Host memory emergency boundary | Stop if host `MemAvailable` is at or below 1 GiB, even when the container limit has more headroom |
| Observation interval | Proposed **0.25 seconds** during the single consumer; inability to obtain required RSS/cgroup readings is a stopping error |
| Existing disk/time/failure rules | Keep 2 GiB free output disk, 7,200-second consumer timeout, TERM then 30-second KILL grace, no retry, unique output/state/claim and identity-bound actual authorization |

The 3 GiB availability gate accommodates a maximum 2 GiB observed consumer plus
1 GiB cgroup reserve. Preflight is a check of the currently available environment,
not an exclusive memory reservation. Other same-cgroup tasks must not be assumed
absent: their usage remains part of the observed cgroup headroom and can stop the
operation. No cgroup limits, swap policy, affinity, environment or thread settings
should be changed to force a pass.

RSS and cgroup limits are sampled observations. A native allocation can spike
between samples; page-cache growth or another process can exhaust the cgroup
before the supervisor acts. This proposal therefore does **not** promise
OOM-proof execution or guaranteed receipt delivery after cgroup-wide OOM/SIGKILL.
Do not add an unreviewed hard `RLIMIT_AS`: virtual address mappings are not RSS and
such a change could reject the existing numerical stack independently of actual
resident use.

On an observed boundary violation, stop the process group before starting any
further fit, preserve existing partial files and claims, and record the actual
resource sample, failure reason, signal/return code, partial-member integrity or
inventory failures and best-effort exit receipt. File writing/hash failure also
stops immediately; it is not a scientifically unavailable estimator fit. If the
failure prevents writing that receipt, preserve the partial receipt file and emit
the actual failure to the supervisor's existing log/stderr. No retry or deletion
may turn a failed single invocation into an apparently successful one.

## Actual read-only observation and pending decision

A stdlib-only snapshot at **2026-10-15 12:50:21.998393 +08:00** observed root
cgroup membership `0::/`, `memory.max = 8,589,934,592`,
`memory.current = 1,075,855,360`, `memory.high = max`, and host
`MemAvailable = 9,586,610,176` bytes. Root cgroup headroom at that one instant was
7,514,079,232 bytes. This confirms that the old 8 GiB-available gate cannot pass.
It is a momentary environment observation, **not** a consumer RSS profile, proof
about invisible ancestor cgroups, future readiness, or approval of the revised
gate. The launcher must reread all available governing boundaries immediately
before any separately authorized execution and throughout that execution.

The static budget supports proposing bounded execution in the existing Codex CPU
environment, subject to the revised gate, fixed-code review and actual parent
authorization. No new resource purchase or environment/data relocation is needed
by this proposal. If that environment fails the fresh preflight, stop and return
the observed blocker; any alternate original-Pod CPU operation needs its own
parent-reviewed runtime/resource/identity evidence and execution instruction.
This document neither selects nor operates that fallback. The independent
remaining36 GPU cost, balance/rate and absolute deadline stay unapproved/null;
this CPU memory proposal supplies none of those missing authorizations.
