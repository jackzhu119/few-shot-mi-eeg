# Exploratory decoding QC sensitivity from saved predictions

## What was done and what was preserved

The user requested this new sensitivity after the original results had already
been observed. `POST_OBSERVATION_PROTOCOL.md` was written before this new
computation. It uses the existing fixed 250 µV maximum raw channel peak-to-peak
flag, never a threshold chosen from performance. The original complete-window
analysis remains primary; its stored results and 44 historical incomplete-window
exclusions were not changed. This is not an artifact-corrected reanalysis.

The script read only saved text predictions and metadata, not EEG or model
weights. The actual original-input execution completed at 11:48:21 UTC on
2026-10-15. All 25,740 predictions (three CPU methods and all three EEGNet seeds)
joined exactly to 4,290 unique frozen queries in 108 participant/method/seed
joins. The 30 historically excluded incomplete query identities remain in the
4,320-row query ledger. All 144 reconstructed original participant endpoints
matched their saved values with absolute difference **0**. The 80 read inputs
were rehashed unchanged after execution. No new fitting or model forward occurred.

## Flag counts and eligibility

Of 7,156 complete windows, the existing rule flagged 1,512. These include:

| Frozen role | Complete windows | Flagged |
| --- | ---: | ---: |
| Source TRAIN | 720 | 76 |
| Source validation | 360 | 36 |
| Source query | 360 | 36 |
| Target support | 1,786 | 478 |
| Target query | 3,930 | 886 |

Thus 922/4,290 (21.49%) unique queries were flagged and 3,368 were unflagged.
Filtering queries does **not** remove the 76 flagged source TRAIN windows or
478 flagged target support windows from the historical fits. The validation
data used for EEGNet checkpoint selection also remain unchanged.

BA is undefined if either true class is absent. All such rows are retained,
including zero-window groups. The equal-five-target-session endpoint requires
all five BAs, rather than silently averaging fewer sessions. In the remaining
cohort, two identities lack this unflagged endpoint for all four methods:

- **sub-8:** target ses-3 and ses-4 have zero unflagged queries; only 28 remain
  across all target sessions (16 left, 12 right). Source query retains only one
  left-hand window, so its unflagged source BA is also undefined.
- **sub-12:** only four target queries remain, all left-hand (1/1/2/0/0 across
  target sessions). Every target session lacks the other class.

Other low-count sessions remain visible, including sub-8/ses-2 (2 left, 1 right),
sub-11/ses-2 (2 left, 1 right) and sub-5/ses-5 (3 left, 12 right). These are
descriptive, unstable estimates, not deleted groups. Five-session summaries
therefore have 10/12 eligible remaining-cohort participants and all 6/6
development participants. Source and pooled endpoints have separately reported
denominators; pooled queries are not a substitute for the equal-session endpoint.

## Main and sensitivity endpoints

All values below are percentages. EEGNet averages the BA of **all three seeds**
within each participant/session; it does not vote or count seeds as participants.
The original target endpoint has 12 participants; its unflagged complete-case
sensitivity has 10. Their means are not a matched change in the same cohort.

| Remaining cohort method | Original target mean BA (n=12) | Unflagged target mean BA (n=10) |
| --- | ---: | ---: |
| Frozen CSP/LDA | 57.94 | 60.14 |
| Frozen CSP + LDA-only recalibration | 59.89 | 62.28 |
| Full CSP/LDA refit | 65.36 | 66.10 |
| Always-frozen EEGNet | 51.58 | 51.80 |

| Remaining cohort contrast | Original, n=12: mean pp [95% interval] | Unflagged, n=10: mean pp [95% interval] |
| --- | ---: | ---: |
| Full refit minus frozen (original primary) | +7.42 [2.49, 12.48] | +5.96 [0.99, 11.24] |
| Full refit minus LDA-only (original secondary) | +5.47 [2.17, 8.91] | +3.82 [1.11, 6.72] |

Intervals are descriptive participant percentile bootstrap intervals with
10,000 draws, seed 42, using the existing lexicographic participant ordering.
No new p value or confirmatory hypothesis is introduced. The QC contrasts are
exploratory; the secondary contrast has not become the primary endpoint.

For the **same ten** participants eligible in both subsets, the original
full-minus-frozen mean is +6.50 pp and its unflagged mean is +5.96 pp. The
paired unflagged-minus-original change is **−0.54 pp [−1.30, +0.16]**.
For full-minus-LDA-only, the corresponding means are +4.53 and +3.82 pp,
with change **−0.71 pp [−2.11, +0.42]**. These descriptive checks do not show
that the original average benefit arose solely from the queried amplitude
flags, but the two lost identities, low class counts, conditioning on signal
amplitude, and unchanged fitting artifacts prevent a general robustness claim.

For completeness, averaging each participant's BA after pooling all its source
and target queries gives original/unflagged means of 58.41/57.58% frozen,
60.58/59.77% LDA-only, 65.43/65.95% full refit, and 51.81/51.99% EEGNet
(12 participants in both). This alternative pooled endpoint weights sessions
differently and is supplementary. Exact source, target-pooled, all-pooled,
per-session and per-participant values and denominators are in the CSVs.

## Individual magnitudes and influence

The three original full-minus-frozen participant declines are **sub-6 −5.82 pp,
sub-14 −0.67 pp and sub-15 −0.20 pp**. The latter two are small observed
differences, not evidence of substantial individual harm. The largest positive
differences are sub-11 +20.67 pp, sub-9 +19.62 pp and sub-2 +17.67 pp. Exact
values for every participant are retained without exclusions based on effect.

Leaving out any one of the twelve original participants produces full-minus-
frozen means from **+6.22 to +8.62 pp**; no single omission reverses its sign.
For the ten eligible unflagged participants the range is **+4.61 to +7.24 pp**.
This is an influence description, not a new test or justification for deleting
any participant. Full-minus-LDA-only influence rows are also retained.

## Verification and limitations

The entry passed Ruff and 15 focused synthetic tests covering strict joins,
missing classes, seed averaging, five-session completeness, bootstrap behavior
and the portable input path. A second execution of the **text-only
postprocessor**, using compact public inputs without private original paths,
reproduced all 13 scientific CSV tables byte-for-byte. This is arithmetic
verification, not repeat query inference. The historical full-GET hashes of
original prediction sources were checked; no new R2 action is claimed here.
An additional implementation using direct Counter/sum arithmetic, without
importing the analysis entry, passed **90,889 checks** of joins, confusion cells,
class counts, seed/session/participant aggregation and bootstrap summaries;
the maximum numeric difference was 2.220446049250313e-16.

The primary limitations are unchanged: unflagged windows are not certified
artifact-free; selecting evaluation windows alters sample/class composition;
flagged source/support/validation examples remain in historical fitting;
missing-class groups limit participant coverage; amplitude QC cannot determine
cue/feedback/task-phase timing; and the cohort had prior test exposure. This
analysis supports a bounded descriptive sensitivity, not proven artifact
robustness, independent replication or a new task-aware policy.

See `analysis_receipt.json`, `input_manifest.json`,
`original_endpoint_reconstruction.json`, `portable_replay_validation.json`,
`independent_public_arithmetic_validation.json`, `related_test_validation.json`
and `REPRODUCE.md` for exact identities, hashes,
commands and validation scope. The raw original scientific outputs are intact.
