# Kumar cue-window and task-phase review

This review preserves the frozen analyses and changes their interpretation. The
analyzed intervals can be described as **cue-anchored exported task-label
windows**. They have not been established as five uninterrupted seconds of
active motor imagery. No signal was re-epoched, no prediction was regenerated,
and no source model was fitted during this review.

## What is now supported

| Question | Evidence and conclusion | Remaining boundary |
| --- | --- | --- |
| Are the exported analysis windows complete? | The saved 360-run header audit and all 360 event TSVs agree with 7,200 retained event identities: 7,156 complete five-second/2,560-sample intervals and 44 shorter intervals. | A complete stored interval is not a statement about its cognitive content. |
| What do the retained original codes mean? | The original authors' dataset-description PDF distinguishes class cue markers 769/770 from task-start markers 7691/7701. The saved official MOABB adapter relabels 769/770 as left/right hand and sets its interval to [0, 5] seconds. NEMAR identifies this MOABB conversion and supplies corresponding left/right onset/sample rows. This establishes the documented cue-anchor convention for the analyzed derivative. | The exact historical MOABB conversion commit/options and every original GDF marker array were not independently replayed in this review. |
| Does every complete interval contain five seconds of active MI? | No such certification is supported. Original Methods describe a nominal 1.5-second class cue before the task/feedback period. A five-second cue-anchored interval therefore includes nominal cue presentation and at most 3.5 subsequent seconds, if the phase transition follows the stated schedule. Online task termination can occur before the maximum duration. | Trial-specific task onset/end and the fraction of each interval spent in feedback, result display or rest are unavailable in the retained class-only derivative markers. Not every online interval is known to overlap result/rest. |
| Do the 44 shorter events represent 44 early task terminations? | **No.** All 44 occur in row 20, the final retained class event of their run, and end exactly at the prior-audited EDF recording boundary. All occur in online sessions. | This establishes recording-boundary truncation of the stored interval, not the causal reason for recording ending or the time of MI termination. |

The new metadata-only audit performed **80,293 checks over 1,451 input files**;
all input bytes/hashes remained unchanged. The source TSVs contain only `onset`,
`duration`, `trial_type`, `value` and `sample`. Their labels cannot reconstruct
the omitted task-start, outcome and task-end events. None of the stored event
intervals overlaps the next retained class-event onset; this also does not
prove sustained MI within the interval.

## Source evidence actually read

The original authors' [Dataset_Description.pdf at fixed commit
548470542e63f97ab777684c1f5e4f1cace4b8ed](https://github.com/neurosatya/TransLearning/blob/548470542e63f97ab777684c1f5e4f1cace4b8ed/Dataset_Description.pdf)
was retrieved through the supported GitHub connector as complete base64 bytes,
decoded, independently Git-blob checked and converted to text locally. It is
149,232 bytes; SHA256:
`4c4c2f773c90fb5ee903c40aed65b57c5f36aaa63ed0e7dab7860fa7db058889`;
Git blob `ef757734fb7511d9dddd89bc0ba830137301893c`.

Its bar-task table identifies 32766 as first/last recording triggers; 1000 as
trial/rest start; 769/770 as class cue; 7691/7701 as task-period start; and
7692/7702 as timeout/incorrect-hit events online and trial end offline. For
online 7693/7703 its literal description is **“Cue Left/Right Delivered”**.
This review does not silently rename that last category as a correct hit. The
authors' [task-bounded extraction function](https://github.com/neurosatya/TransLearning/blob/548470542e63f97ab777684c1f5e4f1cace4b8ed/functions/riemannEpochs.m)
also uses 7691/7701 as starts and the subsequent 7692/7702 or 7693/7703 as
ends; its fixed Git blob was independently verified. This differs from the
MOABB class-cue/[0,5] export convention and identifies the exact phase records
that are missing from our retained derivative events.

The previously saved official MOABB adapter has actual acquisition receipt
SHA256 `96af996bfdbb7999f0aa681a6a3aa2a9030cb1c2aff52fc0827e8db2390f446d`
and 19,771 bytes. It is source evidence, not a substitute for an exact historical
exporter commit. NEMAR's fixed metadata report version 1.0.5, derivative status,
and MOABB 1.5.0dev0; source provenance records the upstream bar/racing archive.
The archive's signal bytes were not downloaded or opened for this review.

Relevant original-paper Methods and Results passages were actually read in
supported web-search indexed full-text returns from [OUP](https://academic.oup.com/pnasnexus/article/3/2/pgae076/7609232)
and [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10903645/).
These are full-text passages, not abstract-only evidence. They describe 1-second
fixation, 1.5-second cue, subsequent offline task/feedback duration of 5 seconds
and online maximum of 7 seconds, then a 2-second result display and 1.5-second
rest. Online evidence-threshold crossing or timeout terminates the active trial.
They also verify that the original study already compared fixed/adaptive CSP
and already used first-run labels for session recalibration. Those ideas must
not be presented as novel contributions of the present reanalysis.

The requested Europe PMC original full-XML endpoint was attempted but was not
accessible through the supported web fetcher. A direct standard HTTPS read in
the current sandbox was blocked (`URLError`, operation not permitted), and
direct PMC/OUP page opening returned a challenge or blocked redirect. No bypass
was attempted. Accordingly, this report does **not** claim a complete raw XML
download or cover-to-cover reading. Actual indexed text responses and access
outcomes are archived beside the audit. The correction's previously saved
complete XML was read locally and remains unchanged; its CSP numerical
correction does not resolve event timing.

Original Methods explicitly identify UT Austin protocol **2020-03-0073** and
state **“All participants provided written informed consent before conducting
the experiment”**. These facts support attribution of the **original study**
only. They neither approve this secondary analysis nor establish its exemption
or lack of review requirements; the author's institutional determination
remains unresolved.

## Exact manuscript wording to use

**Methods:** “We analyzed the published NEMAR class-label intervals, retaining
only intervals with all 2,560 samples at 512 Hz. The source codebook distinguishes
class-cue markers (769/770) from subsequent task-start markers (7691/7701),
whereas the documented MOABB export uses the class-cue events with a [0,5]-s
interval. We therefore refer to these as cue-anchored task-label windows, rather
than five seconds certified to contain uninterrupted motor imagery. Forty-four
shorter annotations were preserved and excluded by the original complete-window
rule; each was the last retained class event and terminated at the recording
boundary.”

**Limitations:** “Cue anchoring and sample completeness do not establish that
the full interval lies within the active imagery/feedback phase. The original
task has a separate cue period and variable online termination. The retained
derivative event table lacks trial-specific task-start and task-end markers,
so the contribution of cue processing, feedback and any post-termination
activity cannot be quantified. Our findings concern decoding these published
cue-anchored windows and cannot be attributed exclusively to sustained MI.
This phase uncertainty remains even if query amplitude-QC sensitivity estimates
are similar to the original analysis.”

## Minimal prospective correction plan; not executed

1. Obtain only the original bar-task marker `POS`/`TYP` arrays for the 360 runs,
   including cue, task-start, task-end/outcome and recording-end records, plus
   their recording sample rate and sample-origin convention. Whole EEG archive
   acquisition is not needed to establish timing if these metadata can be
   exported by the source maintainer from the versioned originals.
2. Pin the exact historical derivative converter commit/options, or a
   maintainer-confirmed original-marker to derivative-sample map. Match every
   original cue and its ensuing task start/end to the existing frozen trial ID,
   independently of model predictions and labels used for policy selection.
3. Before evaluating any new window, freeze an amendment specifying the task
   anchor, one common duration, handling of trials ending before that duration,
   and all effects on support/query budgets. A task-start window is eligible
   only when its complete span lies before the verified task end and recording
   boundary. Do not search multiple windows or choose a duration by scores.
4. Preserve every existing prediction, table, source fit and accepted ledger as
   the cue-window analysis. Changing the window changes the scientific input;
   old checkpoints trained on cue windows cannot be relabeled as models trained
   on task-only windows. Any necessary new fits/query inference would require a
   separate concrete amendment and explicit execution authorization. None is
   performed or implied by this report.

Current work can finish the transparently labeled cue-window manuscript and its
saved-prediction sensitivity analyses while this phase-specific evidence is
listed as a limitation. It cannot assert that a task-only correction has been
validated.

## Reproduction and artifact entry

[Audit directory](../research_logs/kumar_submission_timing_audit_20261015/run01/)
contains the metadata-only script, complete input mapping/hashes, 44-row
boundary inventory, reading-scope record and summary. Complete original
source-codebook bytes/text, base64 retrieval content and web full-text response
captures are **private source-reading evidence**, not material selected for
GitHub republication. Their fixed public source URLs and content hashes are
provided above and in the evidence manifest. The metadata script checks these
local source-reading copies as well as the already available original event
sidecars; a fresh reproduction first needs the fixed public source copies
staged at the declared locations. Recompute to a **new** output directory
without overwriting the recorded audit:

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -B \
  research_logs/kumar_submission_timing_audit_20261015/run01/audit_saved_event_metadata.py \
  --output-dir /workspace/private_model_receipts/kumar-timing-metadata-review-new
```

This command reads saved metadata and existing signal-header receipts only; it
does not read EEG arrays, source checkpoints or query predictions and does not
invoke an estimator.
