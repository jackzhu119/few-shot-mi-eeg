# Existing behavior/session analysis — 2026-10-10

Authoritative result: `run03_verified/`. Exact independent computational replay:
`run04_replay/`; all 11 computational tables/summary/source snapshots match byte
for byte. See `replay_verification.json`. This is not biological replication.

- `behavior_sessions.tsv`: 19 original participants, 76 participant/session summaries.
- `behavior_source_positions.tsv`: 456 real source percentages; EEG run/trial and
  denominator remain unresolved. Source-vector position is not an EEG run ID.
- `linked_EEG_behavior_sessions.tsv`: four verified session joins for sub-1/sub-01;
  no broadcasting of scores to the 717 EEG trials.
- `cohort_session_summary.tsv`: behavior-only subject-bootstrap summaries.
- `task_bandpower_contrasts.tsv` and `bandpower_session_summaries.tsv`: log-power
  and arithmetic-power definitions kept distinct; no baseline ERD.
- `matched_task_bandpower_contrasts.tsv`: 20 resamplings, 96 unflagged balanced
  trials/session from common EEG runs 03–06; sampling ranges are not population CIs.
- `analysis_receipt.json` and `source_snapshot/`: pinned inputs/output checksums,
  actual code/config/runtime and Git state; zero new EEG downloads/model fits.

`run01/` and `run02_with_count_sensitivity/` are preserved intermediate executions.
They incorrectly counted an approximately −7e−15 floating-point zero change as a
decrease: 15 instead of 14 participants with any decrease. `run03_verified` uses
1e−10 percentage-point numerical tolerance, and separately reports the 0.01-point
reporting-precision sensitivity (13 participants). Scientific endpoint values,
cohort means and bootstrap intervals were unaffected. Do not cite the older
count. Historical source snapshots match their original runtime hashes; see
`historical_source_snapshot_check.json`.

`figures/` contains native PNG/SVG/PDF plots and plotting receipt. An initial
relative-path plotting failure is preserved under `figures/failed_initial/` and
recorded in `notebook_validation.json`. The executed companion notebook has
5 code cells, zero error outputs and 3 embedded plots. Native plots were visually
checked; full HTML browser screenshot was not performed.

Scientific interpretation, methods and next-stage decisions:
[`docs/netbci_behavior_session_analysis.md`](../../docs/netbci_behavior_session_analysis.md).
