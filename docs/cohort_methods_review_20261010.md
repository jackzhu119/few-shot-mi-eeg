# Independent methods review of the resumed NETBCI cohort

This review validates saved arithmetic and provenance while identifying a material
data-independence failure. Ten published subject IDs do not establish ten
independent longitudinal EEG records: six continuous-run groups repeat exactly
across `sub-7` sessions 01, 02 and 03 and `sub-1` session 04. The complete original
analysis remains preserved. The restriction to eight unaffected IDs is a
post-observation sensitivity analysis, not an independent replication or proof
of biological identity.

## Review scope and source preservation

The historical table-only review is preserved in
`research_logs/netbci_cohort_resume_20261010/independent_review_tables_v1.json`
with its exact source snapshot `independent_review_source_v1.py`. The subsequent
ten-ID review adds the five exploratory associations in `independent_review.json`
and `independent_review_source.py`. Neither imports production analysis helpers,
loads EEG tensors nor refits models. Both are arithmetic/methods checks, not
independent experimental confirmation.

Checks passed for all ten IDs, 40 session joins, 7,577 source events and 7,576
eligible five-second trials. The one valid shortened source event in
`sub-3/ses-01/run-03/tsv-row-31` remains in the source inventory with its explicit
exclusion from the fixed-window tensor. No padding, fabricated event or participant
deletion was used. The policy was documented after observing the strict-duration
failure and before new cohort model fitting; it is not a preregistration.

The saved predictions reproduce confusion matrices, balanced accuracy, all seven
constant-prediction session records and conditional whole-run bootstrap intervals.
The behavior joins reproduce the means of the original six reported percentages
per session. Source-only learned-transform partitions, event identities, audited
hashes, output receipts and missing matching cells were checked. Matching samples
and repeated spectral contrasts were reconstructed from saved trial tables.
Participant session means, paired first-to-last changes and ten association
estimates were independently recalculated, including complete-pair and degenerate
bootstrap counts.

## Exact numerical identity finding

`audit_numeric_signal_identity.py` reads one available EDF derivative at a time
using MNE 1.10.2 and NumPy 2.2.6. It hashes unfiltered returned signal arrays in
volts as canonical little-endian float64, preserving shape and channel order, and
separately hashes every actual labeled source interval. No rereferencing, spectral
filtering, rounding, resampling or fitted transformation is applied.

All 240 continuous runs and 7,577 actual source intervals were inspected. There
are 222 unique continuous numerical hashes and 7,043 unique interval hashes. The
six duplicate continuous-run groups contain 24 members: for each run 01–06,
`sub-7/ses-01`, `sub-7/ses-02`, `sub-7/ses-03` and `sub-1/ses-04` return exactly
identical numerical arrays. The 178 duplicate labeled-window groups contain 712
members, with no cross-label conflict. All six groups and exact member hashes are
included in `numeric_signal_identity_summary.json`; the full 11 MB ledger remains
preserved separately for R2 storage.

All 240 actual EDF file bytes also match the pinned official dataset manifest and
the subject manifests. Within each group, the three `sub-7` EDF whole-file hashes
are equal and explicitly repeated by the official manifest. The corresponding
`sub-1` EDF whole-file hash differs while its returned numerical array is equal.
EDF byte identity and numerical signal identity are therefore distinct checks.
This finding is not explained by a local recovery file failing the official
checksum. It does not establish the cause of derivative repetition or the true
participant assignment. The original BrainVision continuous EEG and marker
sequence have not been independently compared; distinct original header hashes
and filenames alone cannot resolve this.

For `sub-7` sessions 02 and 03, 119 query windows per session are exact copies of
the source training windows, totaling 238 later queries. Another 59 per session
copy the source held-out query windows, totaling 118. Their later-session scores
cannot support independent cross-session generalization. Near-zero geometry or
unchanged spectral summaries from these repeated derivatives cannot establish
biological stability. Absence of exact hashes among other IDs does not rule out
near similarity or establish physiological reliability.

## Eight-ID sensitivity review

The sensitivity removes **all** IDs present in any cross-person continuous-run
duplicate group, namely `sub-1` and `sub-7`. Correct source assignment is unknown,
so neither identity was preferentially retained. No outcome direction, model
accuracy or spectral value determines this restriction, and no model is refitted.
The remaining IDs are `sub-2`, `sub-3`, `sub-4`, `sub-5`, `sub-6`, `sub-8`,
`sub-9` and `sub-10`.

`independent_sensitivity_review.py` rebuilds the 32 retained session rows from the
immutable original ten-ID tables. It verifies exact receipt hashes, all eight
metrics' four session means, all paired differences and 95% percentile bootstrap
intervals (10,000 whole-participant draws, seed 42), individual changes and all
five Pearson/Spearman pairs using independent SciPy arithmetic. Every check passed.

| Session 04 minus 01 metric | Eight-ID mean change | Participant bootstrap 95% interval |
| --- | ---: | ---: |
| Reported online behavior | +14.3713 percentage points | +9.1885 to +19.3252 |
| Frozen CSP balanced accuracy | −9.5020 percentage points | −20.2441 to +2.7347 |
| CAR Mu MI-minus-rest task contrast | −0.6786 dB | −1.3168 to −0.0470 |
| CAR Beta MI-minus-rest task contrast | −0.1665 dB | −0.6541 to +0.3807 |

These are exploratory summaries of eight source IDs without detected exact
copies; the restriction does not repair original participant labels or provide
external confirmation. The eight-ID CSP interval includes zero. Mu task contrast
remains distinct from prestimulus ERD and from human learning, particularly because
absolute task-class power can change. The full association estimates and intervals
are stored in the sensitivity tables and independent review receipt; ten
exploratory association estimates do not establish causal mechanisms.

## Limits and next-stage gate

Signal extraction, filtering, PSD computation, reference handling and model fitting
were inspected in source; the independent table review does not refit models or
recalculate geometric distances from tensors. The separate numerical identity
audit loads the untransformed raw EDF derivative and verifies exact signal content.
Conditional run intervals omit source-model estimation uncertainty. Reported
percentages retain unresolved EEG run order, score denominator and trial hit/miss
mapping. Within-session run AIRM is descriptive dispersion and is not a measured
split-half reliability statistic.

Before fitting an expanded nineteen-ID cohort, inspect all 456 raw continuous
derivatives and all actual event windows for exact content repetition, deriving
source train/query roles directly from the fixed configuration. Record any new
duplicate memberships before calculating the expanded outcome contrasts. Keep
observational EEG description, frozen-decoder robustness, reported behavior and
causal skill-retention questions separate. Independent no-assistance retention
or randomized online adaptation data remain necessary for causal retention claims.
