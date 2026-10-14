# Kumar2024 actual frozen split audit

Audit date: 2026-10-13 UTC. Actual serial preparation passed for all 18 published
identities, 108 sessions and 360 runs. No model fit or performance was computed
by preparation. The [manifest](research_logs/kumar_cross_session_20261012/protocol/split_manifest.json)
retains every one of the 7,200 source events, including each excluded partial
event, its exact samples, source file, label, role, cohort, reported timestamp,
raw numerical hash and peak-to-peak QC flag. Full epochs additionally retain
processed numerical hashes.

## Partition and coverage

Session `ses-0` runs 0/1 are source train, run 2 validation, run 3 source query.
Later sessions use only their complete run 0 as support; all remaining runs are
query. Partial events never move roles, receive padding or gain replacements.
All methods therefore evaluate the same queries and use the same actual support.

| Role | Source events | Included full epochs | Excluded partial | QC-flagged included |
| --- | ---: | ---: | ---: | ---: |
| Source train | 720 | 720 | 0 | 76 |
| Source validation | 360 | 360 | 0 | 36 |
| Source query | 360 | 360 | 0 | 36 |
| Target support | 1,800 | 1,786 | 14 | 478 |
| Target query | 3,960 | 3,930 | 30 | 886 |
| Total | 7,200 | 7,156 | 44 | 1,512 |

Source classes are 3,600 left and 3,600 right; included classes are 3,579 left
and 3,577 right. Every subject/session/role contains both included classes.
Each raw support run contains 20 events, 10/class. Actual included support is
19–20 events; partial losses are visible and are not refilled. A method may
fit only on the current session's support in addition to source train.

Development is fixed to published IDs 1, 4, 7, 10, 13 and 16, with 2,400 raw
events and 2,381 included epochs. The other twelve fixed final-test IDs contain
4,800 raw events and 4,775 included epochs. Cohort assignment predates model
performance and has no performance-based search.

| Published ID | Cohort | Source rows | Included | Partial excluded |
| --- | --- | ---: | ---: | ---: |
| sub-1 | Development | 400 | 396 | 4 |
| sub-2 | Final test | 400 | 400 | 0 |
| sub-3 | Final test | 400 | 396 | 4 |
| sub-4 | Development | 400 | 391 | 9 |
| sub-5 | Final test | 400 | 399 | 1 |
| sub-6 | Final test | 400 | 397 | 3 |
| sub-7 | Development | 400 | 400 | 0 |
| sub-8 | Final test | 400 | 399 | 1 |
| sub-9 | Final test | 400 | 397 | 3 |
| sub-10 | Development | 400 | 399 | 1 |
| sub-11 | Final test | 400 | 398 | 2 |
| sub-12 | Final test | 400 | 399 | 1 |
| sub-13 | Development | 400 | 399 | 1 |
| sub-14 | Final test | 400 | 400 | 0 |
| sub-15 | Final test | 400 | 398 | 2 |
| sub-16 | Development | 400 | 396 | 4 |
| sub-17 | Final test | 400 | 397 | 3 |
| sub-18 | Final test | 400 | 395 | 5 |

## Identity, numerical-copy and temporal checks

All 7,200 trial IDs are unique. Within every EDF, sorted source intervals are
nonoverlapping, with exact stored start/stop/count identity. Every whole run has
one role, and source/target/cohort memberships match the frozen configuration.
Raw numerical SHA256 was checked for all 7,200 windows, including partials;
processed float32 numerical SHA256 was checked for all 7,156 full windows.
Both duplicate-group lists are empty across the entire cohort, across roles and
across published identities. All 360 complete signal numerical hashes also
match their historical receipts and contain no duplicates.

Numerical conventions are explicit: raw hashes use all channels in source order,
little-endian float64 numerical V, C-order bytes; processed hashes use the
22 × 640 little-endian float32 V tensor. Exact-copy absence does not establish
biological identity, eliminate near duplicates or verify cross-resource subject
independence.

For all 18 IDs, reported `scans.tsv` timestamps increase strictly through nominal
sessions/runs. The interval from the first `ses-0` run to the first `ses-5` run
ranges from 4.9463 to 6.9795 days. Source strings, complete run timestamps and
numerical run QC are preserved in
[run metadata](research_logs/kumar_cross_session_20261012/protocol/run_metadata.csv)
and per-subject receipts. These are actual derivative-reported fields; their
original acquisition-date provenance is unverified, so the analysis does not
invent an exact uniform day schedule or equate session index with calendar day.

## QC and fixed diagnostics

The source-predeclared raw 250 µV channel peak-to-peak threshold flags 1,550 raw
and 1,512 included events. All full flagged events remain primary observations.
Per-role and per-session counts are in
[role counts](research_logs/kumar_cross_session_20261012/protocol/role_counts.csv);
flags measure a source-quality concern, without expert artifact adjudication.

The independently preserved
[count-matched diagnostic IDs](research_logs/kumar_cross_session_20261012/protocol/count_matched_diagnostic.json)
contain 234 subject/session/role groups and 7,122 selected events. For each group,
both classes contribute the smaller available class count; the earliest
included events are chosen by reported acquisition time then start sample.
No partial rows, replacements, signal-based decisions or model results enter
that selection. The primary manifest and decoder fitting sets remain unchanged.
All22 versus fixed C3/Cz/C4 power, the fixed 0.1 covariance shrinkage and source
reference qualifications are prescribed in the protocol. Offline CAR cannot
restore a verified native CPz acquisition signal.

## Frozen evidence and validation

Final manifest SHA256:
`ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28`.
Final source gate SHA256:
`16187f8d5eb46eefb744396c0e14b2d9d1f6259c6d898f338777d193fa9e730f`.
The original preparation receipts are preserved beside the final versions. A
documented pre-performance fit-access helper correction changed no loading,
filtering, hashes, source-row metadata or trial records; exact AST comparison and
77 safeguard tests support reuse of the same signal/split evidence. See the
[eligibility report](KUMAR_MODEL_ELIGIBILITY_REPORT.md) for all final input hashes
and source limitations, and the
[freeze revision](research_logs/kumar_cross_session_20261012/protocol/freeze_revision_fit_access_hardening.json)
for the preserved before/after provenance. This is preparation evidence, not a
claim of achieved model performance.
