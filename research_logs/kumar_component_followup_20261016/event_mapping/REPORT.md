# Original bar-task GDF phase audit — incomplete acquisition, actual mapping

The actual original event arrays resolve task phases for **311/360 runs and
6,220/7,200 trials**. Every recovered cue position and class matches exactly
one frozen derivative trial sequence. The remaining **49 runs / 980 trials
are unknown**, following recorded HTTPS-tunnel 503 responses. They are not
silently assigned timings or marked eligible. No EEG signals, checkpoints,
predictions, estimator or new decoding result was read or generated here.

Use `timing_partial_run05/all_7200_trial_mapping_including_missing.csv` for the
complete inventory, including unknown rows. `partial_run04/trial_event_mapping.csv`
contains only the 6,220 actually mapped trials. The `partial_run04` correspondence
and input manifests bind the 311 runs and exact frozen metadata. The newest
coverage table includes all participants, sessions, frozen roles and classes,
including groups whose original phases remain unknown.

## What was actually obtained and checked

The official versioned NEMAR full manifest lists the upstream bar-task GDFs and
their SHA256 identities. For each completed run, three HTTP **206** responses
provided only its 256-byte fixed header, variable header and event-table tail.
Each response passed exact Content-Range, total-length, body-length and SHA256
checks; the object ETag was identical across that run's slices. The complete
original GDF checksum in the source manifest was **not recomputed**. A hash of
a range must not be described as verification of the entire GDF.

The GDF 2.00 fixed/variable headers determine the exact signal-region extent and
event-table offset. No request crosses into that signal region. The completed
311 runs contain 82 events each, including 20 cues. The 20-pair sequence of
cue sample and class is unique across the 360 frozen derivative runs. Matching
requires all 20 pairs exactly, GDF's documented one-based to zero-based index
conversion, the same 512-Hz clock and complete recording sample count, the
same 22-channel order and acquisition time within 1 ms. No fitted or manually
chosen constant offset is used. Original `FZ/CZ/PZ/POZ` versus derivative
`Fz/Cz/Pz/POz` spelling is compared case-insensitively, with both original lists
retained and no channel permutation or electrode-name aliases.

Task starts and endpoints are then paired **within each real cue-to-next-cue
event bracket**. Every recovered trial has exactly one same-class start and
one same-class endpoint in temporal order. Independent MNE 1.10.2 GDF header/
event parsing agrees with the separately implemented parser for all event
positions, codes, counts and clocks in one offline and two online examples.
Those checks used metadata-only sparse files; their signal holes were never
populated with original EEG. This does not replay or certify every historical
exporter option or independently establish that every EEG amplitude was
unchanged during conversion.

## Actual timing findings, limited to the recovered subset

| Quantity | Actual recovered subset |
|---|---:|
| Mapped original trials | 6,220 |
| Complete original cue-anchored 5-s windows | 6,189 |
| Original shorter windows, all recording-boundary truncated | 31 |
| Cue-to-task-start median [range] | 1.503906 s [1.5, 1.5078125] |
| Offline active-phase duration mean | 5.001263 s |
| Shortest online active phase | 0.234375 s |
| Complete original windows extending beyond task-end marker | 2,853 / 6,189 (46.10%) |
| Mean original complete-window pre-task / active / post-task time | 1.504033 / 2.655223 / 0.840744 s |
| Fixed task-start 2-s windows eligible among original complete windows | 4,307 / 6,189 (69.59%) |

The complete original windows therefore are not five seconds of the marked
active phase. Some include post-endpoint data; this is now directly supported
for the mapped trials rather than inferred solely from variable task duration.
The endpoint does not separately label result display and rest, and task-phase
containment does not establish uninterrupted imagery or removal of feedback,
visual, eye or muscle contributions.

The recovered subset comprises all 400 trials for `sub-1` through `sub-14`,
380/400 for `sub-15`, and only 80 offline trials each for `sub-16` through
`sub-18`. It is not a random representative subset of all online recordings.
Session-specific durations and denominator counts are in
`timing_partial_run05/phase_timing_summary.json`; they must not be extrapolated
to the 980 missing trials.

The source codebook distinguishes 769/770 cues, 7691/7701 task starts and
7692/7702 endpoints. For online trials it combines timeout and incorrect hit
under the latter codes, so these outcomes cannot be separated. The literal
7693/7703 wording is **“Cue Left/Right Delivered”**; these are endpoints in the
authors' task-extraction function but are not relabeled as confirmed correct
hits. A duration below the nominal seven-second ceiling is only a timing
description, not a causal or outcome label. All original 44 partial windows
remain excluded by the frozen rule; only 31 have recovered original markers.
Neither those 31 nor the 13 unresolved partial windows are equated to 44 early
task terminations.

## Candidate window amendment before new decoding

A fixed task-start **[0, 2 s)** interval with a verified same-class endpoint at
or after 2 s is a compact, physically interpretable exploratory candidate.
It must intersect the original complete-window identities, preserving all 44
original exclusions. Coverage loss is substantial and nonuniform; it must be
reported before interpreting any decoding contrast. Even this candidate cannot
be called task-only physiology free of online feedback. A variable start-to-end
interval with a minimum one second is an alternative coverage description,
not an outcome-selected replacement or an interchangeable fixed-window score.

The 2-s eligibility rule already produces missing classes in recovered data:
`sub-11/ses-4` query has only left-class trials; support is single-class for
`sub-2/ses-2`, `sub-5/ses-5`, `sub-11/ses-3` and `sub-11/ses-4`. Such rows and
their class counts must remain visible. A participant endpoint requires the
predefined session/class completeness rule; changing its denominator cannot be
interpreted as a model effect. No new decoder was run to choose this duration.

## Failures and recovery boundary

The first actual collection started at 03:00:44.920278 UTC and encountered
four in-flight HTTP 503 failures beginning at 03:03:19 UTC. The main thread
had collected 306 completions; after its existing workers finished, 307 complete
run folders remained. Both figures are preserved. The failed body was never
treated as GDF data. A bounded diagnostic against the official S3 object and
official NEMAR file URL returned the same 215-byte Envoy HTTPS-tunnel error.

After an explicit parent instruction, a separate `run02` rehashed and reparsed
all 307 completed runs and requested only the first missing run, with one worker
and strictly sequential dispatch. That first request returned 503 at
03:08:35.620637 UTC; execution stopped at 03:08:35.817724 UTC, with **no second
new request**. The initial acquisition used no automatic retry or full-file-download fallback.
Original failures, receipts, partials and logs remain retained. A separate
`run03`, following new actual network-recovery evidence and explicit parent
instruction, recovered **four more complete runs** (indices307–310), then stopped
on the first header request for index311 at03:15:16.831645UTC. It reused the
original307 runs without redownloading them. A premature progress message that
called this a first-request failure was corrected against the complete log;
that message is not the acquisition evidence.

The subsequently versioned **metadata-only network policy v2** permitted at
most three attempts per exact range forHTTP502/503/504 or transport exceptions,
fixed1/3-s backoff, one worker and a600-s total bound. Scientific fitting retries
remained zero. Under that explicit policy, `run04` acquired the next run's
256-byte and6,656-byte headers with206, but all three event-table attempts
returned503 (03:25:58.421793,03:25:59.628859 and03:26:02.813572UTC). It stopped
at03:26:02.972339UTC without another run request. These incomplete header slices
do not count as a mapped run. HTTP200/403, invalid206 range/length/ETag, parsing,
mapping, storage and integrity failures are nonretryable. Policy, source snapshot
and every actual attempt are preserved. The old generic exception receipt's
`automatic_retry:false` field did not encode these permitted metadata transport
retries; the append-only transport addendum documents the two retries rather
than rewriting the original receipt. No automatic scientific retry took place.

Current actual coverage is therefore311 complete GDF metadata records, not360.
See `failure_and_recovery_history.json`, the separately versioned network policy
and `metadata_resume_run03_run04_addendum.json` plus all four exception receipts.

Two local metadata-postprocessing failures are also preserved: literal channel
capitalization initially stopped the strict comparison, and a relative-path
formatting error stopped the first summary's final input-manifest publication.
The new versions document the case-only rule and absolute-path handling. These
were not estimator failures or scientific retries.

## Reproduction

Rehash/reparse saved original ranges without any HTTP or signal read, using new
output directories:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/audit_kumar_gdf_phase_mapping_20261016.py \
  --offline-ranges /workspace/private_model_receipts/paper2-component-followup-20261016/event_mapping/ranges_run01 \
  --private-output /workspace/private_model_receipts/paper2-component-followup-20261016/event_mapping/offline-new \
  --output research_logs/kumar_component_followup_20261016/event_mapping/mapping-new
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  scripts/summarize_kumar_gdf_phase_mapping_20261016.py \
  --input-dir research_logs/kumar_component_followup_20261016/event_mapping/mapping-new \
  --output-dir research_logs/kumar_component_followup_20261016/event_mapping/timing-new \
  --allow-partial
```

An eventual explicitly authorized metadata continuation can use `--reuse-ranges` with a new
private/output directory and `--workers 1`; it verifies existing bytes before
requesting missing runs and stops on failure. The optional versioned policy bounds metadata transport retries; it does not
authorize scientific retries or new decoding results. Existing successful
partial slices must also be reused if another continuation is separately prepared. The original
source URLs and exact byte receipts remain private reading evidence; the
public derived mapping, hashes, input inventories and failure statuses are
inspectable here.

The final mapping adds the observed preceding/following code1000 trial/rest
markers and both code32766 recording triggers as separate columns. These
triggers are kept distinct from the physical header-derived recording extent.
All pre-existing7200-row fields, including eligibility, are exactly unchanged;
see `marker_column_revision_preservation_check.json`. The stage-marker summary
also reports whether the stored cue window crosses the subsequent code1000
marker, without assigning unobserved psychological or outcome labels.

The minimal phase consumer and its74-test synthetic gate are described in
`PHASE_ENGINE_INTERFACE.md` and `final_related_test_gate.json`. No real phase
decoding was executed by this metadata task.
