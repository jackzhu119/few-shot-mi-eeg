# Independent QC arithmetic and saved-input lineage review

**Passed: no critical implementation or consequential arithmetic discrepancy
found.** The independent arithmetic verifier performed **358,833 checks**; the
separate original-input lineage/coverage verifier performed **332,948 checks**
(**691,781 total**). Maximum numerical difference from the producer's tables
was **3.3306690738754696e-16**, below the audit comparison threshold `1e-14`.
This threshold compares saved arithmetic; it does not change the frozen model
replay tolerance, scientific configuration, preprocessing or primary analysis.

The audit imported only standard-library modules and NumPy. It did not import
the producer or its helpers, read EEG arrays or weights, fit a model, perform
query inference, change a prediction, operate the Pod or request new R2 GETs.
Both audit scripts and JSON proofs are retained in this directory. All input
bytes read by each verifier were rehashed unchanged after its pass.

## Independent reconstruction

- All 7,200 public metadata rows match the original saved split manifest in
  every projected field. There remain 7,156 complete windows, 1,512 flagged
  complete windows and 44 historical exclusions.
- All 25,740 public prediction rows match actual original stored CPU CSVs and
  54 EEGNet result JSONs in identity, label and prediction. Length/SHA256 for
  all 80 source-text manifest records match. These are saved text artifacts,
  not new model execution or a new R2 object readback.
- Exactly 4,290 unique complete query identities join in all 108 required
  participant/method/seed groups. The 30 partial query identities remain in
  the 4,320-row ledger. The existing amplitude rule marks 922 complete queries;
  3,368 are unflagged.
- Every seed/session/scope confusion table, true and predicted class count,
  undefined BA, low-count flag and collapse indicator was independently
  reconstructed. The EEGNet summary uses three separately computed seed BAs;
  seeds are never treated as independent participants or selected by outcome.
- Participant target endpoints use five equally weighted target-session BAs
  after seed averaging, not a pooled-query replacement or an available-session
  mean. A missing true class invalidates that session and the five-session
  endpoint. All undefined rows remain present.
- All 13 scientific CSV tables have the independently expected complete row
  counts. Source, all-query pooled, target-query pooled and five-session
  summaries have separately checked eligibility and participant denominators.
- The 144 original source/target endpoint cells match the saved historical
  values. Independent endpoint construction uses `math.fsum` for means,
  producing only normal floating-point rounding differences.

## Consequential contrasts

All values below are percentage points. Intervals use the existing participant
percentile convention: 10,000 draws, NumPy `default_rng(42)`, lexicographic
participant order. These are descriptive intervals, not new confirmatory tests.

| Remaining cohort contrast | Original, n=12 | Unflagged five-session complete cases, n=10 |
|---|---:|---:|
| Full refit − frozen, original primary | +7.4213551 [2.4875548, 12.4766157] | +5.9596491 [0.9895926, 11.2383316] |
| Full refit − LDA-only, original secondary | +5.4715668 [2.1680574, 8.9137975] | +3.8238936 [1.1056381, 6.7201170] |

The unflagged five-session endpoint is undefined for **sub-8 and sub-12** for
every method, because some sessions lack a true class, including zero-window
sessions. The eligible remaining-cohort identities are exactly:
`sub-11; sub-14; sub-15; sub-17; sub-18; sub-2; sub-3; sub-5; sub-6; sub-9`.
All six development participants retain a defined target endpoint. Low-count
sessions with both classes remain descriptive and are not removed by an
additional threshold.

The cross-subset checks use these **same ten** people in both subsets. The
unflagged-minus-original change in full-minus-frozen is −0.5363279 pp
[−1.3048133, +0.1597509]; for full-minus-LDA-only it is −0.7060217 pp
[−2.1093427, +0.4154815]. Subtracting the n=12 original mean from the n=10
unflagged mean would change cohort composition and was not used as that paired
change.

Independently checked leave-one-participant-out primary means remain positive:
**+6.2172359 to +8.6247319 pp** in the original twelve and
**+4.6057868 to +7.2360960 pp** in the unflagged eligible ten. This rules out
a sign reversal from deleting any one eligible participant in these saved
results; it does not prove population robustness or justify excluding anyone.

## Interpretation review

The amplitude threshold was fixed before the original outcomes and was not
searched in this revision. Nevertheless, this sensitivity was specified after
test results had been seen. Its mask depends on the evaluated signal and can
alter class, session and participant composition. The n=10 complete-case
summary is a conditional estimand, not a new estimate for the original n=12
population or an independent replication. All missing-class and low-count
rows remain auditable; neither chance nor zero replaces undefined BA.

Unflagged windows are not certified free of artifacts. The historical models
still contain flagged source TRAIN, source-validation and/or target-support
examples. This query-only sensitivity cannot establish robustness to artifacts
in fitting data. It also cannot resolve cue/feedback/task-end alignment,
establish sustained motor imagery, validate a gate or remove the exploratory
status of exposed test data. The original primary and secondary endpoint
hierarchy remains unchanged. There are 18 participant identities, not 54
independent people; the original main contrast has twelve participants and
reliability probes have six development participants.

## Reproduction and validation

Run from a checkout containing the saved outputs; each audit writes its new
proof exclusively and therefore needs a fresh destination if independently
repeated. No scientific runner is called:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B research_logs/kumar_submission_qc_20261015/independent_run01/verify_saved_qc.py
/workspace/.venvs/few-shot-mi-eeg/bin/python -B research_logs/kumar_submission_qc_20261015/independent_run01/verify_lineage_and_coverage.py
```

Those exact output files now exist; preserve them. Public arithmetic
verification requires only the compact public CSV/JSON input bundle and the
producer's text output tables. The separate original-lineage verifier also
requires the existing private saved prediction JSONs, without any weights or
EEG. Ruff passes for both audit scripts. An initial pre-execution Ruff E731
lambda-style finding was changed to a named local function before the
arithmetic pass; no scientific operation or failed arithmetic execution arose
from that style check. No whole unrelated test suite was rerun.
