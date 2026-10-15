# Frozen checkpoint reuse: the existing always-frozen EEGNet baseline

This is the executable completion of the source-only EEGNet evaluation already
specified in `EEGNET_TRAINING_PLAN.md`. It introduces no adaptation rule or model
search. The user authorized implementation and synthetic tests on 2026-10-15;
real query execution remains a separate, concrete dot dispatch. The actual
acceptance of all 54 source models is not query authorization.

## Unchanged scientific references

The controlling references are `EEGNET_TRAINING_PLAN.md`,
`KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md`,
`configs/kumar_cross_session_20261012.json`, and the accepted models' exact
`configs/kumar_eegnet_gpu_development_20261014.json`. The last two files retain
SHA256 `f1b2d0fa870493cc2aaab906fe6d8b1227e45b2a270e06700e3ca137fbfe9c89`
and `14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d`.
The split remains
`research_logs/kumar_cross_session_20261012/protocol/split_manifest.json`,
SHA256 `ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28`.
Historical readiness flags and historical failure/pause records are preserved.

The fixed identities are the 18 published participants and seeds 20261012,
20261013 and 20261014. All 54 accepted checkpoints are required in the accepted
ledger order: original development18 followed by the frozen remaining36 order.
Within each participant, all three seeds are retained. This order changes no
within-participant session or run chronology. Checkpoint loading verifies the
original archive, every payload, the accepted source identity, embedded context,
weights and complete frozen state; no old fit is copied into a new experiment.

## Exact whole-run input scope

The source remains Kumar2024 NEMAR `nm000177/v1.0.5`, CC BY 4.0. The derived
query-only manifest is `configs/kumar_frozen_query_inputs_20261015.json`.
It contains 1,189 files / 1,043,686,331 bytes: dataset metadata, 108 acquisition
TSVs, and 216 query EDFs with four sidecars per run. The manifest is derived
from existing frozen metadata, not a new look at raw query signals or events.
It records historical SHA256 and official checksums. Historical R2 HEAD checks
are expressly distinguished from full GET; this preparation claims no new raw
query verification or download.

| Role | Whole runs | Included rows | Action |
| --- | --- | ---: | --- |
| Source query | ses-0 / run-3 | 360 | Fixed prediction only |
| Target query | ses-1 / runs 1,2,3; ses-2 through ses-5 / runs 1,2 | 3,930 | Fixed prediction only |
| Source train / validation | ses-0 / runs 0,1 / run-2 | 0 new reads | Restore saved state only |
| Target support | ses-1 through ses-5 / run-0 | 0 new reads | No EEGNet update |

All 4,320 query event identities remain recorded; the same 30 partial events
are excluded without padding, replacement or outcome-based selection, leaving
4,290 included events and 12,870 predictions across three seeds. Chronology,
labels, raw/processed hashes and original exclusions come from the unchanged
split and adapter. Full input length/SHA verification precedes actual query
decoding after authorization, and repeats before successful completion. The
adapter also verifies official checksums, acquisition order, annotations and
frozen numerical hashes. It is called only with
`allowed_roles={"source_query", "target_query"}`.

The pre-existing support budget stays at the first whole run, at most 20 events
and 10 per class before partial exclusions, without replacement. Always-frozen
EEGNet uses zero support events. The three completed CPU baselines remain their
original source-only, frozen-CSP/LDA-recalibration and CSP/LDA-refit methods;
this entry neither refits those models nor invents an EEGNet update baseline.
No source-score/task-aware gate, threshold, seed selection or future-session
fitting is added. The CSP reliability diagnosis does not release a new strategy.

## Read-only checkpoint evaluation

Preprocessing stays epoch-local CAR, fourth-order 8–30 Hz zero-phase filtering
and resampling from 512 to 128 Hz: 22 by 640 float32 volts. Restore the original
source-trained channel mean/scale and all model/BN buffers. Load with
`torch.load(map_location="cpu", weights_only=True)`, then use evaluation mode,
disabled parameter gradients and inference mode. No optimizer is constructed,
no fit/backward is called, and no normalization or batch-normalization update
is permitted. Constructor RNG state is restored. The existing numerical thread
settings and CPU runtime are bound by the operation contract.

The kernel checks all parameter/BN/normalization/class state, embedded source
context and evidence-file hashes before and after inference. A mismatch stops
execution; it is never repaired or treated as a successful prediction. Labels
are checked against the frozen split and used solely for the fixed metrics.
Predictions are untuned logit argmax. Record each seed/session's predictions,
balanced accuracy, recalls, confusion matrix, class collapse, and state hashes.
The original 1e-7 source-validation replay tolerance is unchanged; query scores
do not select or revise that tolerance.

## Frozen aggregation and interpretation

Average the three seed balanced accuracies within each participant/session,
then the five target sessions within each participant. Source-query results
remain separate. Retain all participants, collapsed predictions and failures;
an incomplete seed/session inventory cannot become a complete result by dropping
rows. Participants, not trials or seeds, are the independent units.

Report the six development participants separately from the twelve fixed
remaining participants; the combined 18 are secondary. Preserve the existing
test-exposure qualification: these follow-up evaluations are exploratory,
not a newly untouched confirmatory test. The original primary contrast remains
refit CSP/LDA minus source-only CSP/LDA. EEGNet is an additional frozen baseline,
not a replacement primary contrast. Any descriptive participant uncertainty
uses the existing 10,000 resamples / seed 42 convention and is labeled as such.
No new significance test, model search, task-aware rule or clinical/skill
retention claim follows from this implementation.

## Execution and evidence boundary

The default entry checks frozen code/metadata only and constructs no model.
Actual execution needs the separately reviewed full commit, contract SHA,
external authorization SHA, actual current host identity and one immutable
absolute window. Its candidate maximum is 7,200 seconds, with 30 seconds
reserved for cleanup; no actual start or deadline is assigned by this document.
The existing CPU environment is the sole proposed allocation. There are no
financial execution gates and no new resources, GPU fits or Pod operations.

The operation uses an exclusive attempt claim and shared CPU lock, executes
one participant and one checkpoint at a time, and monitors the complete process
tree every 0.25 seconds. Limits are 2 GiB process-tree RSS, 1 GiB running memory
headroom, 3 GiB effective available memory at preflight, and 2 GiB free disk.
Failure, timeout, storage/hash error or unverifiable process visibility stops
the attempt and retains its claim, partial files, actual log and exit receipt.
There is no automatic retry, state clearing, deadline reset or resume option.
Any recovery would require an explicit later decision preserving old evidence.

Atomic per-model and per-participant results provide partial evidence. A local
complete result is still pending independent audit, private original-byte R2
full GET/SHA verification and actual parent acceptance. These stages are not
inferred from one another. Query output is scientific result data; historical
source archives and EEG/weights remain private and never enter GitHub.
