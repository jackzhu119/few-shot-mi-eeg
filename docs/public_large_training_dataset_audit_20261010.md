# Public motor-imagery training resource audit

Audit updated 2026-10-11, Asia/Shanghai. This extends the completed ten-person
NETBCI analysis and the separate [longitudinal audit](public_longitudinal_dataset_audit_20261010.md).
The fixed source ledger is
[`large_training_sources.json`](../research_logs/public_data_expansion_20261010/large_training_sources.json).
Primary metadata, participant tables, exact release manifests, licence text,
representative sidecars and HTTP evidence are saved beside that ledger. A
successful metadata or HEAD request is not a completed EEG download or a trained
model.

## What the search supports

The current MOABB summary contained 204 dataset rows; 25 rows described imagery
resources with at least 30 advertised participants. The audit checked these
against primary sources where available and also checked recent 2026 resources
outside that shortlist. Several software imagery entries actually describe motor
execution, mirrors, overlapping subsets, unavailable releases or task-confounded
labels. Those entries cannot increase a hand-imagery training sample.

Nine source cohorts below advertise 568 participants in total. This is a discovery
inventory, **not an independent pooled n, a downloaded n, or a training n**.
Participant overlap across studies is unknown. Runs, repeated days, modalities,
algorithm seeds and converted mirrors do not create additional participants.
Healthy and clinical participants, unilateral and bilateral imagery, hand and
lower-limb tasks, and calibration and feedback conditions must remain explicit.
Publication, acquisition and repository-conversion dates must remain distinct.

## Primary-source shortlist

Signal volume below counts only the selected converted signal files where a
pinned NEMAR manifest was inspected. Associated events, channels and root
metadata still need preserving. Original files and converted mirrors count once
per source identity. Decimal GB are used for planning, not estimates of disk
needed during model fitting.

| Source | Advertised people | Visits/task | Pinned signal inventory | Data licence and access evidence | Research use |
|---|---:|---|---|---|---|
| [PhysioNet EEGMMIDB](https://physionet.org/content/eegmmidb/1.0.0/) | 109 | One visit; left/right fist MI in runs 04/08/12 | Version 1.0.0; 327 EDF + 327 WFDB event files, exactly 834,146,640 B; all 654 HEAD requests returned 200 | ODC-By-1.0; official RECORDS and SHA256SUMS pinned | First actual large ingestion; within-visit participant generalization, not retention |
| [Dreyer 2023](https://doi.org/10.1038/s41597-023-02445-z) | 87 | One visit; left/right hand MI, calibration and feedback | nm000250 v1.0.5; 520 converted signals, 9.485 GB | CC-BY-4.0; participant rows, manifest and representative signal HEAD verified | Compatible hand MI; Dreyer A/B/C are subsets, not new people |
| [Lee 2019 / OpenBMI](https://doi.org/10.5524/100542) | 54 | Two different-day visits; left/right hand MI | nm000338 v1.0.5; 216 signals, 65.266 GB | Original data CC0-1.0; NEMAR description GPL-3.0, preserve scope distinction | Cross-day external cohort; MI/ERP/SSVEP share the 54 people |
| [Cho 2017](https://doi.org/10.5524/100295) | 52 | One visit; left/right kinesthetic finger MI | nm000245 v1.0.2; 52 signals, 7.243 GB | CC-BY-4.0; participant rows, manifest and representative signal HEAD verified | Compatible hand MI; preserve four EMG channels and stated quality exclusions |
| [Yang 2025 / WBCIC-SHU](https://doi.org/10.1038/s41597-025-04826-y) | 51 in pinned binary release | Three different-day visits; left/right hand MI | nm000348 v1.0.5; 153 signals, 68.046 GB | CC-BY-4.0; pinned participants/manifest/HEAD verified | Newer cross-day source; paper's 62 people include 11 additional three-class subjects; nm000246 is a mirror |
| [Leeuwis 2021](https://doi.org/10.34894/Z7ZVOD) | 55 | One visit; calibration + three feedback runs | nm000327 v1.0.0; 220 EDF, 566,607,360 B | CC-BY-4.0; participants, sidecars, exact manifest and representative HEAD verified | Efficient additional hand-MI cohort; stored cue −3 to +5 s trials were concatenated with EDGE boundaries |
| [MILimbEEG](https://doi.org/10.17632/x8psbz3f6x.2) | 60 | Unequal repetitions; mixed limb MI and populations | nm000328 v1.0.0; 60 EDF, 60,464,776 B | CC-BY-4.0; participants, sidecars, manifest and representative HEAD verified | Separate low-channel/population validation; 16 channels/125 Hz, segmented CSVs are not continuous raw recordings |
| [Liu 2024 stroke MI](https://doi.org/10.1038/s41597-023-02787-8) | 50 | One visit; 40 trials per design | nm000158 v1.0.3; 50 BDF, 696,884,480 B | CC-BY-4.0; participants, sidecars, manifest and representative HEAD verified | Separate clinical validation; 29 EEG + 2 EOG/500 Hz; alternating labels require time/cue controls |
| [Martinez-Peon 2025](https://doi.org/10.17632/msgzn862ns.1) | 50 | One visit; four imagined-force recordings per person | Original Mendeley v1; 202 files, including 200 CSVs | CC-BY-NC-SA-4.0; original metadata/file inventory and representative signal HEAD verified | Reserve for force MI; first 25 imagine left hand and next 25 right hand, confounding hand with person; no verified per-trial event clock |

The most efficient additions after PhysioNet are Leeuwis (55 people, 0.567 GB
signals), followed by a bounded Dreyer or Cho subset. OpenBMI and Yang provide
valuable different-day validation but their tens of GB require staged transfer,
auditing and private R2 verification. The resource order is not determined by
publication year alone. Retention-relevant longitudinal sources remain in the
separate audit rather than being counted again in the nine-cohort arithmetic.

## Recent sources requiring distinct treatment

| Source | Public evidence and decision |
|---|---|
| [Guttmann-Flury 2025](https://doi.org/10.1038/s41597-025-04861-9), 31 people | Promising MI with ocular/control modalities. Primary release inventory and licence scope still need verification. MI/ME aliases share the same 31 people. |
| [Hefmi-ICH 2025](https://doi.org/10.1038/s41597-025-06100-7), 37 people | Figshare metadata/files checked; per-person availability varies from 1 to 6 sessions. Separate clinical/multimodal analysis. Preserve CC-BY declaration alongside description's commercial-use restriction. |
| [MIND 2026](https://doi.org/10.57760/sciencedb.34326), 30 people | ScienceDB PUBLIC v4 and CC-BY-NC-4.0 verified, direct signal inventory pending. Three consecutive blocks are one visit; direction pairs are confounded with acquisition half. |
| [Han 2026](https://doi.org/10.18112/openneuro.ds007327.v1.1.0), 35 people | Pinned version DOI read; release inventory/licence pending. Dribbling and passing MI have different cues from hand MI. Duplicate markers reported for subjects 20/25/27 require source checks. |
| [Wang 2026](https://doi.org/10.1184/R1/32293995.v1), 39 people | High scientific relevance, already the paper read as L1; not an independent confirmation of that study. Retain 15/8/8/8 groups, tactile assistance and decoder differences. Variable-length trials must not be padded silently. |
| [Zuo 2025](https://doi.org/10.1038/s41597-025-05767-2), 30 people | Separate lower-limb clinical cohort. Expected 150 sessions includes 32 missing raw sessions in 12 people; README/event-label conflicts need resolving before epochs or models. |
| [IMUMIA 2026](https://doi.org/10.5281/zenodo.20421767), advertised 244 people | Pinned public nm000316 v1.0.0 contains **5** participants and 25 EDFs. The public five-person pilot does not supply 244 training participants. |
| [SEFMEID 2026](https://doi.org/10.57760/sciencedb.30795), advertised 50 people | Official ScienceDB access is RESTRICTED and licence field is empty. Discovery evidence only; unavailable signal is not included. |
| [RhythmicMI 2026](https://github.com/SJTUwyxuan/RhythmicMI-CrossSubject), advertised 100 people | Author README says the dataset is under construction and future release; public code is not public EEG. Not counted as acquired data. |

NeBULA 2025, Perez-Blanco 2026, BNCI2020_001 and Schirrmeister 2017 concern overt
motor execution; they are excluded from hand-MI training despite software
imagery categorization. Guttmann-Flury ME does not add people to its MI entry.
MIMED, Rozado and Triana-Guzman remain task-specific candidates needing original
file and licence checks. Iwama, Stieger, NETBCI and Kumar are handled in the
longitudinal audit, without duplicate counts.

## Current PhysioNet ingestion checkpoint

The manifest was constructed from exact official records/checksums rather than
guessing filenames. Only unilateral hand-imagery runs 04, 08 and 12 are selected;
execution, baseline and bilateral hand/foot runs are absent. T1/T2 mean different
tasks in other source runs, so their codes cannot be pooled without run identity.
The selected 654 files require exactly 834,146,640 bytes. Four bounded download
workers verify positive exact length and official SHA256 before publishing a
local file; verified files are reused, inconsistent or failed files and receipts
are retained. Dataset destination is
`data/public_eeg/physionet_eegmmidb/1.0.0`.

The first canonical-host attempt was stopped after a measured transfer of
262,144 bytes took 33.715 seconds. Its complete and partial files and interruption
snapshot were preserved. PhysioNet's own
`archive.physionet.org/physiobank/database/eegmmidb/` served a complete
2,596,896-byte probe in 8.494 seconds with **the identical pinned v1.0.0 SHA256**.
The four-worker transfer resumed through that official archive transport. The
archive is not a new source or a new participant cohort; the canonical URLs,
official v1.0.0 hashes and exact lengths remain the version identity. Every
download records its actual transport URL. An arbitrary mirror is refused.

The serial signal audit reads every sample in volts, records original units,
sampling clock, channel order, complete-signal numeric digests, annotation
boundaries and durations, and compares the official WFDB sidecars against EDF
annotations. The representative source contains an EDF T0 rest segment at time
zero missing from its WFDB file; that exact explicit difference is retained,
without inventing a sidecar event. All other label, time and duration differences
are source-integrity failures for task qualification, while the original signal
and both annotation streams remain in the archival resource. A second deliberate
representative check, S088/R04, found a real 128 Hz clock in both files, 38 EDF
annotations versus 23 WFDB annotations, and 14 nonzero EDF events missing from
the sidecar. The first strict comparison failed and was retained before the full
audit. The audit now reports `complete_with_source_flags` when full signal reading
completes with such disagreements. It does not repair events, resample to 160 Hz,
delete S088, or approve it silently for fixed-window training.

Each flagged file retains its source identity, exact unmatched annotation
identities, class-specific missing counts and sampling rate. Source-qualified
file counts and complete three-run subject identities are distinct from all
downloaded identities and from future model eligibility. Short source events and
source sampling irregularities stay visible.
A four-second MI-window inventory is descriptive source availability only, not
created epochs, model training or a selected analysis cohort.

The actual fixed-subset download completed: **654 files / 834,146,640 bytes**, all
official v1.0.0 SHA256 and lengths verified, zero failed files. The completed
download receipt is
[`download_receipt_20261011T064522417697Z.json`](../research_logs/public_data_expansion_20261010/physionet_eegmmidb/download_receipt_20261011T064522417697Z.json).
The valid full source audit is
[`audit_20261011_run02/signal_audit.json`](../research_logs/public_data_expansion_20261010/physionet_eegmmidb/audit_20261011_run02/signal_audit.json),
with both original annotation tables retained. All **327 EDF from 109 source
identities** were read in full; all samples were finite, all had 64 channels with
the same order, and there were **zero complete-file or complete-signal duplicate
groups**. This does not certify the absence of partial trial duplication or
physiological artifacts. The first full read encountered a NumPy integer JSON
serialization failure after reading 327 signals; its incomplete JSON and log
were retained, the sample-count field was converted to an integer, and the whole
audit was rerun in a fresh directory. Only run02 is a completed audit receipt.

There are **9,836 original EDF annotations**: 4,918 T0 rest, 2,480 T1 left-hand
MI and 2,438 T2 right-hand MI. The official WFDB stream has 9,335 annotations.
Four source identities have anomalies in all three selected runs:

| Identity and runs | Actual Hz | EDF / WFDB annotations in each run | Missing nonzero EDF events in each WFDB stream: T0 / T1 / T2 | Source task qualification |
|---|---:|---:|---:|---|
| S088, 04/08/12 | 128 | 38 / 23 | 0 / 7 / 7 | Unresolved annotation disagreement and overlap; actual rate differs from advertised 160 Hz |
| S089, 04/08/12 | 160 | 30 / 13 | 2 / 7 / 7 | Unresolved annotation disagreement and overlap |
| S092, 04/08/12 | 128 | 38 / 23 | 0 / 7 / 7 | Unresolved annotation disagreement and overlap; actual rate differs from advertised 160 Hz |
| S100, 04/08/12 | 128 | 24 / 9 | 5 / 5 / 5 | Unresolved annotation disagreement and overlap; actual rate differs from advertised 160 Hz |

The explicit source gates leave **315 files from 105 complete three-run source
identities**, containing **4,722 available four-second hand-MI source windows**
(2,381 T1 and 2,341 T2). The other 12 files remain fully archived rather than
deleted or repaired. Final handling in a model protocol is undecided; these 105
are source-qualified candidate identities, not 105 newly trained or evaluated
participants. The resource audit status is `complete_with_source_flags`.

An [independent validation companion](../research_logs/public_data_expansion_20261010/physionet_eegmmidb/independent_source_validation.py)
did not import ingestion helpers. It rechecked all 654 official hashes, reread all
327 whole signals, recomputed time-major voltage digests and RMS, compared both
source annotation streams, reconstructed flags, and verified source identities,
counts, unmatched events and eligibility. The
[completed independent receipt](../research_logs/public_data_expansion_20261010/physionet_eegmmidb/independent_source_validation_20261011.json)
passed. Focused software validation passed 35 meaningful ingestion-integrity
tests and Ruff; these software checks are separate from the actual source read.

The 654 official original files, including all flagged files, are now complete in
the user-authorized private R2 archive. Exact object/byte/hash verification and
readback scope are recorded in [the R2 storage receipts](r2_research_storage.md),
separately from local source download success. No new training epochs or models
were produced by this audit.

## Consequences for the paper

These sources can support participant-held-out decoding, external dataset
transfer, few-shot calibration robustness and properly stratified geometry
checks after source/QC validation. Source-held-out evaluation should separate
acquisition hardware, channel coverage, preprocessing provenance, clinical
status, run type and acquisition time. Every learned transform must be fitted
on source training participants; target sessions and test labels cannot select
preprocessing or hyperparameters.

Larger offline resources do not establish whether adaptive feedback preserves
human skill acquisition. That conclusion still requires an appropriate online
comparison and unaided immediate/delayed probes. A single-visit resource adds
people to decoding tests, not longitudinal retention evidence. The paper should
report exact downloaded, source-audited, independent-identity-eligible,
model-eligible and evaluated counts separately, linked to immutable source and
R2 receipts.
