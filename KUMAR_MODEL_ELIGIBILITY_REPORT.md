# Kumar2024 model eligibility report

Assessment date: 2026-10-13 UTC. **The fixed local derivative passes the strict
source and split gates for the defined offline decoding experiment, with the
source-quality qualifications below.** Preparation computed no decoder fit or
model performance. The root reviewer must bind approval to the final hashes;
eligibility is not a result about decoding, human learning or retention.

The [frozen protocol](KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md) and
[config](configs/kumar_cross_session_20261012.json) define the endpoints. Actual
evidence is in the
[source gate receipt](research_logs/kumar_cross_session_20261012/protocol/source_gate_receipt.json),
[split manifest](research_logs/kumar_cross_session_20261012/protocol/split_manifest.json),
[role counts](research_logs/kumar_cross_session_20261012/protocol/role_counts.csv)
and [verified source files](research_logs/kumar_cross_session_20261012/protocol/verified_pinned_files.json).

## Strict gates: actual execution

Serial preparation ran from 2026-10-13 15:08:38 to 15:11:09 UTC, 151.90 seconds,
using Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, MNE 1.10.2 and sklearn 1.7.2.
The supplied existing checkpoint is `9aa580e5800245a1107b060fcdcba9807666ddca`;
preparation performed no Git command, source download, R2 action or model call.

| Gate | Actual evidence | Decision |
| --- | --- | --- |
| Pinned source coverage and official checksums | 2,705/2,705 local files; 1,781,052,841 bytes | Pass |
| Continuous signal integrity | 360/360 EDFs; all continuous samples finite; historical whole-signal numerical hashes equal | Pass |
| Rate, channels, units and reference metadata | All 22 fixed channels, 512 Hz; native µV, MNE V; reported CPz | Pass |
| Events and annotations | 7,200 TSV source rows match EDF labels/timing/sample bounds | Pass |
| Cohort and session coverage | 18 published identities, 108 sessions, 360 runs | Pass |
| Fixed-window eligibility | 7,156 full 5-second epochs; 44 partial rows retained but excluded from tensors | Pass |
| Split and sample leakage | Unique IDs, nonoverlapping source windows, complete runs with one role, disjoint cohorts | Pass |
| Exact numerical trial copies | Zero duplicate groups among all 7,200 raw windows and all 7,156 processed windows | Pass |
| Whole-recording exact copies | Zero duplicate groups among 360 recomputed numerical hashes | Pass |
| Target support budget | 20 raw events/run, no more than 10/class; actual included support 19–20 | Pass |
| Two-class viability | Both included classes in every planned subject/session/role | Pass |
| Acquisition order | All 18 published IDs have strictly increasing reported scan timestamps | Pass |
| Learned-component access | Source train only for descriptive scaler/PCA/reference; adaptive CSP/LDA current support only | Pass |

Any failure of these strict gates would stop qualification and forbid fitting.
No participant was removed because of classifiability, drift or a prediction.
Whole-recording central fingerprints remain historical checks: their source
files were reverified and complete continuous numerical hashes matched, but the
central 4 KiB fingerprints were not separately recomputed in this preparation.
Their historical duplicate census also contained zero groups.

## Source-quality qualifications

The raw 250 µV peak-to-peak flag occurs in **1,550/7,200 source windows** and
**1,512/7,156 included windows (21.13%)**. The largest raw window channel
peak-to-peak value is 0.0390946 V. This is a material signal-quality concern;
finite values and official checksums do not establish artifact-free EEG or that
class information is neural. Flags are included in every source-row record and
are retained in the primary analysis, as specified before performance. Report
the flags alongside any model result; no expert artifact certification is claimed.

| Qualification | Consequence for this experiment |
| --- | --- |
| Published IDs are not independently verified biological identities | Use participants as published units; do not assert pooled independence across resources |
| All participant ages are `2020` | No age covariate or demographic-age claim |
| GR/PAR mapping is not verified | No historical-group inference from ID or score |
| Acquisition timestamps are derivative-source reported | Ordering is supported; exact acquisition-date provenance remains unverified |
| CPz is reported acquisition metadata | Preserve the metadata; offline CAR cannot reconstruct the actual native-reference signal |
| Substantial raw-amplitude flags, without expert adjudication | Offline endpoints remain qualified by possible non-neural signal contributions |
| Only left/right task labels are used | No inferred hit/miss, racing score, human learning or retention endpoint |
| Offline zero-phase filtering | No real-time feasibility claim |

These qualifications permit the specifically defined, flag-inclusive offline
decoding and descriptive geometry endpoints. They do not establish the stronger
biological or behavioral interpretations above. No prediction outcome can repair
the source limitations.

## Final freeze and correction evidence

The initial freeze preceded source preparation and model performance. During
preparation, an unused fit-access helper was hardened to keep scaler, PCA,
normalizer and Riemann reference source-train-only for all methods. Exact AST
comparison confirms that only `allowed_fit_trial_ids` changed; all data-loading,
preprocessing, hashing, role and split-validation code remained identical. The
original split/gate receipts and original adapter snapshot are preserved. The
[freeze revision](research_logs/kumar_cross_session_20261012/protocol/freeze_revision_fit_access_hardening.json)
records the correction at 15:12:58 UTC, before real performance evaluation.
The final canonical manifest contains the identical trial records and binds the
hardened adapter. Meaningful safeguard validation: **77 tests pass; Ruff passes**.

| Bound artifact | SHA256 |
| --- | --- |
| Config | `f1b2d0fa870493cc2aaab906fe6d8b1227e45b2a270e06700e3ca137fbfe9c89` |
| Frozen protocol | `ac290f0e2c5ca58b3745d7cccd83c3fd265e5be9978f461ea5ed0fe7f645831e` |
| Final split manifest | `ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28` |
| Final source gate receipt | `16187f8d5eb46eefb744396c0e14b2d9d1f6259c6d898f338777d193fa9e730f` |
| Hardened live adapter | `4d1d9439d3adad80532ce24e59d203bea04e353cf5235788e979ab1f79883d57` |
| Fit-access freeze revision | `39e5a817b9d5ff942b88493378ac837268f7c0a4d15fed3a99b9ef42b74564bd` |

The root reviewer owns the separate independent execution-approval receipt.
This report neither creates that approval nor implies that a baseline has run.
