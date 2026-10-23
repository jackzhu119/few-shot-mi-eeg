# Paper 2 school-HPC V2 delivery

Date: 2026-10-23. Base main was fetched and verified at
`04d21b06a7acc225391958556220e7cdb2bcffbd`. New work is isolated on
`research/paper2-hpc-v2-20261023`; the submitted manuscript, original 54 models,
predictions, acceptance records and unrelated pre-existing untracked work were
preserved. No reset, Pod operation, school SSH access or scientific fit occurred.

## Delivered scientific change

The candidate estimates class-wise source/target covariance mixing from current
support variability. It is compared principally with the stronger EA comparator,
with the same target-label budget; matched-EA fixed-strength and no-EA variants
separate the two components. Fixed, LDA-only and full CSP/LDA updates remain
controls. Four neural update positions provide a separate representation-level
comparison. All methods and seeds are declared, with participant-level summaries
and missingness reporting. The proposal is exploratory on the already exposed
Kumar cohort; an independent cohort is still needed for a stronger generalization
claim. No new method benefit is asserted before execution.

The existing-evidence snapshot establishes why simply comparing a new method
with frozen CSP would be inadequate: saved remaining-12 EA exceeded full refit
by 5.30 pp [2.81, 8.26]. It also preserves the phase-analysis scope and the failed
gain-selector launcher. These are existing results, not experiments rerun here.
The literature review distinguishes full-text reading, abstract reading and
metadata-only checks, including the limits of a 2026 citation.

## Executable scope and resources

- 6 original development participants; 6 classical tasks and 18 new V2 neural
  tasks (three seeds each), 24 total, array concurrency 3.
- Per task: one A100, 24 CPUs, 128G RAM; Torch threads4/BLAS1/workers0.
- Exactly 78 NPZ input shards, 2,381 complete windows out of 2,400 source events.
  The 19 partial events in this subset preserve the original rules; they do not
  imply 19 early task endings. Full-cohort historical 44 partial records remain.
- Source, validation, independent source query, support and target query use
  original whole-run identities. No new window rule or label balancing.
- A new pure-PyTorch architecture is explicit; old Braindecode54 checkpoints
  are neither relabeled as compatible nor silently retrained. New source fits
  and support updates reuse their own complete checkpoints across all stages.
- One startup command and one identical resume command. First-use GitHub token
  authorization is hidden on the school terminal; monitoring is separate and
  retries failures without affecting computation. No credentials are packaged.
- USR1 save/requeue; TERM/INT save without automatic resurrection; two
  checkpoint generations; evaluation shards survive evaluation failures.

## Observed validation

- 97 focused synthetic tests passed in 5.22s. Full old-project test suites and
  scientific pilots were not rerun. Ruff, Bash syntax and diff whitespace passed.
- Actual prepared input validation passed for all 24 task definitions and 78
  distinct files in 1.19s locally, with expected SHA and role isolation checks.
  This read input arrays for metadata/integrity, not model fitting or inference.
- Input tar: 125,283,270 bytes,
  SHA256 `b6f211bbf2ed512fbf30d178d59c67181396c98d0ec122812519ee95a9aa3e0a`.
  Independent full read verified all93 members, zero failures.
- Offline installation of the integration snapshot and actual input tar passed;
  repeated installation used cached file stats, 0.060s, no full SHA rescan.
  Final package identity and installation verification are recorded separately
  after the source commit is fixed.
- The actual CLI summary on an empty task output reported 0/24 completed and
  0/3000 defined target cells; it did not invent zero-valued accuracies.
- Local validation host is CPU-only Python3.11.16/Torch2.8.0+cpu/NumPy2.2.6.
  School Python3.12.3/Torch2.5.1+cu121/A100 has not been accessed here. The first
  allocated GPU worker performs and records its real minimal CUDA check once.

## R2 status and outstanding execution

The configured cloud environment reports credential bindings ready, but an
actual HeadBucket and the existing immutable uploader returned HTTP401. The
attempted new input object has **0 uploaded bytes, 0 verified objects and 0 GET
bytes**. `r2_inputs_run01.json` retains that failure. Existing historical R2
receipts are preserved and are not claimed as proof of this new upload.

The input tar is available locally for user upload to the school's persistent
shared storage. R2 authentication restoration is independent of school training;
no new credential or permission scope has been created. After access is restored,
reuse the exact tar/hash and immutable key with a new transfer receipt filename.
School R2 automatic backup has not been configured or claimed; `/public/home`
holds its persistent checkpoints, while GitHub receives progress/metrics only.

The user runs the one-line installer in the internal login1 terminal and enters
a GitHub token there. Slurm partition time limits and actual A100 behavior will
be observed then. The candidate 5-day3-hour single-job limit is not claimed as a
verified queue maximum and imposes no cumulative 12-hour cutoff. No school task
is currently running as a consequence of this delivery.
