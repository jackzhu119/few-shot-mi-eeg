# Paper 2 GPU handoff — preparation, no external launch

Repository: jackzhu119/few-shot-mi-eeg, branch research/learning-preserving-bci.
Recovered scientific ancestor: 67f89ee0501d0d9a63ef9fa2e63a52e9465206fc.
Use the exact delivery commit reported with this handoff; do not follow a moving branch during a run.

## Actual status

- Existing three Kumar CPU baselines preserved; none rerun.
- New development supervised CSP diagnostic completed on 42 verified EDFs,
  836 windows (240 source TRAIN + 596 target support), no query or final subject loaded.
- Source two-whole-run held-out BA 62.9167%, participant bootstrap 95% interval
  [52.9167%, 72.0833%], n=6 published identities. Participant BA:
  sub-1 70%, sub-4 50%, sub-7 72.5%, sub-10 42.5%, sub-13 67.5%, sub-16 75%.
- Mean participant support split-half CSP direction cosine 0.29818,
  95% interval [0.04908, 0.55087]. Eight of 30 session half-cosines are negative.
  Training-label permutation mean BA ~49.32%; descriptive controls, not exchangeability p-values.
- These are exploratory follow-ups after power/PCA diagnostics, not independent
  confirmation, adaptation benefit or human learning evidence. No threshold search,
  policy implementation or final query evaluation. Next gate study needs a separate
  nested development protocol with matched label budgets before final evaluation.
- Aggregation initially used string subject keys with an integer-key bootstrap
  helper. Original summary is preserved. `summary_corrected.json` recomputes only
  aggregation from existing subject records; zero models rerun. Exact executed
  source snapshot and hashes retained alongside the original before-fit receipt.
- MIND live R2 list shows 72 raw `.eeg` objects; list/size is not full-content or
  native-run closure verification. The historical 62/90 closed-run claim is not
  promoted to 72/90 closed. No ingestion process exists on this new host; no downloader restarted.

Evidence: `research_logs/gpu_preparation_20261014/`.
Scientific summary: `supervised_csp_run01/summary_corrected.json`.

## Server and cost

Parent-observed existing RunPod 52ivinpjwv947i: RTX A4500 20470 MiB, driver
580.159.04, 12 vCPU, 62 GB RAM; Python 3.12.3 with torch 2.8.0+cu128.
`/workspace` is nonpersistent root overlay, total 30 GB; Stop is not a backup.
Do not create resources, start competing jobs, or shut down from this task.
Parent coordinates paper 1 and paper 2. Supplied rates are compute $0.25/h and
storage $0.004/h, not independently billed here. GPU fitting time remains unknown.
Record actual fit seconds before projecting 54 participant×seed fits; maximum
5,400 epochs / 16,200 optimizer steps unchanged. Do not interpret synthetic timing
as a real training estimate. Record installation/idle time separately.

## Minimal environment preparation (no training)

The isolated CUDA lock resolves successfully here; actual CUDA installation and
execution must be validated on RunPod. CPU regression is tested here, not presented
as GPU validation. Keep Python 3.11.16 and the official Braindecode 1.2.0 model.
CUDA 12.8 torch/torchaudio 2.8.0 is listed in the official installation source:
https://pytorch.org/get-started/previous-versions/#v280

After obtaining the exact delivery checkout, run:

```bash
cd /workspace/few-shot-mi-eeg
bash scripts/setup_paper2_gpu.sh
export PYTHONPATH="$PWD/src:$PWD/scripts"
export XDG_CACHE_HOME=/workspace/.cache-paper2
export MPLCONFIGDIR=/workspace/.cache-paper2/matplotlib
export MNE_DONTWRITE_HOME=true
export CUBLAS_WORKSPACE_CONFIG=:4096:8
/workspace/.venvs/paper2-gpu/bin/python -m pytest -q tests/test_kumar_eegnet_training.py
/workspace/.venvs/paper2-gpu/bin/python scripts/train_kumar_eegnet.py \
  --config configs/kumar_eegnet_gpu_development_20261014.json \
  --software-check --output /workspace/paper2-results/cuda-synthetic-run01
```

`uv` must already be installed (check `uv --version`); the script does not install
shell bootstrap code. Environment is `/workspace/.venvs/paper2-gpu`, separate from
system Python and paper 1. Lock is `environments/gpu/uv.lock`, CPU lock unchanged.
Installer requires 18 GiB free and uses no wheel cache. Reserve at least 5 GiB after
restoration; plan ~12 GiB environment, <0.5 GiB checkout, <2 GiB data and <1 GiB
outputs, but measure actual `df`/`du` after installation. These are capacity
allowances, not measured installed sizes. Never delete paper 1 files to make space.
CUDA absent/unsupported/determinism failures stop the job; no silent CPU fallback.

## Exact data scope and safe transfer

Source: Kumar2024 NEMAR nm000177 v1.0.5, CC-BY-4.0; keep attribution.
Frozen R2 mapping: `research_logs/public_data_expansion_20261010/r2/kumar2024_raw_20261011_run01.json`.
Frozen split SHA256: ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28.

| Scope | EDF | Files/bytes |
|---|---:|---:|
| development-csp | 42 | 211,043,998 bytes including required metadata; restored and full SHA verified here |
| development-eegnet | 18 | 98,743,492 bytes including source train/validation and metadata |
| formal | 360 | 1,780,417,279 bytes required by adapter; plan only |
| original whole Kumar archive | 360 | 2,705 files / 1,781,052,841 bytes |

Do not restore the cumulative 45 GB R2 catalog or MIND onto this container.
The signed receiver verifies every file SHA256 against the committed receipt and
never downloads unselected query EDFs. Existing corrupt content fails instead of
being overwritten. Interrupted `.partial` files can be redownloaded and verified.

R2 authorization here is existing injected AWS/S3-compatible runtime environment
variables with Cloudflare endpoint/bucket, verified HeadBucket 200 and real GETs.
No chat token, new key, persistent credential file, or paper 1 access assumption.
Do not copy those environment variables to RunPod. Instead prepare short-lived,
exact-object signed URLs on this authorized host, transfer the private capability
file securely outside Git and logs, and use it within one hour. Example on Codex:

```bash
PYTHONPATH=/tmp/paper2-r2-sdk:scripts /workspace/.venvs/few-shot-mi-eeg/bin/python \
 scripts/paper2_signed_transfer.py prepare-data --scope development-eegnet \
 --capability /tmp/paper2-dev-data-capability.json
PYTHONPATH=/tmp/paper2-r2-sdk:scripts /workspace/.venvs/few-shot-mi-eeg/bin/python \
 scripts/paper2_signed_transfer.py prepare-backup \
 --key few-shot-mi-eeg/experiments/kumar2024/gpu-source-20261014/sub-1-seed-20261012-run01.tar \
 --capability /tmp/paper2-sub1-backup-capability.json
```

Neither capability file has been created for a real server job in this preparation.
They are temporary bearer capabilities, not public dataset URLs. Do not paste them
in chat or publish them. GET permits only selected source objects; PUT permits only
one immutable result key (`If-None-Match: *`) plus GET for hash readback. If secure
capability transfer is unavailable, data/train delivery is pending; do not copy keys.
No persistent server authorization is required by this route. If a persistent
route is later desired, parent must confirm bucket/prefix-scoped read for frozen
source and create/read for new result prefix, no delete or account administration.

On RunPod after secure transfer to `/tmp`, with the environment above:

```bash
/workspace/.venvs/paper2-gpu/bin/python scripts/paper2_signed_transfer.py receive \
 --capability /tmp/paper2-dev-data-capability.json --directory /workspace/paper2-data/kumar
```

## First real fit — parent schedules only after CUDA and transfer checks

This is one source-only development fit, not a query experiment. Hold a common GPU
lock used by both papers; parent must also verify no unrelated GPU job is running.

```bash
flock -n /workspace/research-gpu.lock /workspace/.venvs/paper2-gpu/bin/python \
 scripts/run_kumar_gpu_source.py --subject sub-1 --seed 20261012 \
 --data-root /workspace/paper2-data/kumar \
 --output /workspace/paper2-results/sub-1-seed-20261012-run01 \
 --backup-capability /tmp/paper2-sub1-backup-capability.json
```

The first fit supplies actual timing. It uses source TRAIN 40 and validation 20
windows, official frozen optimizer/architecture, maximum 100 epochs, patience 15;
all target and source query signals are excluded before EDF read. No best-seed
selection. Up to 18 development fits may follow only under parent scheduling and
per-fit verified backup; retain all three seeds. Full 54-fit/query execution remains
separately frozen/pending; do not toggle the historical formal config by hand.

## Outputs, backup and failure recovery

Per fit: `weights.pt`, bound strict `weights.json`, `completed.json` including seed,
configuration/split/script/input hashes, actual runtime versions, selected epoch,
loss history, time and CUDA peak memory. Checkpoint replay is verified before backup.
The signed backup packs only that fit directory (maximum 256 MiB), conditional PUT,
then full GET SHA256. Archive and `.backup.json` receipt are beside the fit directory.
Never place the capability JSON inside an uploaded directory. Preserve stdout/stderr
and environment/software-check receipts separately; parent must archive those too.

A completed fit is hash-verified and reused on restart, not refit. Backup retry first
handles an already-existing object by comparing complete GET bytes; a different
object is a hard conflict. An expired capability needs a fresh short-lived capability
for the SAME target key, not new long-lived keys. Partial fit directories are preserved
and fail closed; inspect progress before choosing an explicit new attempt path. No
optimizer/RNG mid-epoch checkpoint exists: an interrupted incomplete small fit may
need restart, while completed seeds are never rerun. No automatic GPU shutdown.

Before Stop: parent verifies every expected fit receipt, transfers results/logs and
manifest to durable R2, full GET hashes, then brings small evidence back to Codex/Git.
Raw EEG and weights never enter the public repository. Confirm backups from a second
host/session when possible, record cost/runtime, then parent alone shuts down.

## Delivery verification

Executable/scientific delivery commit: `219cfd58fc55c83cf4cb1aa79375309dbb36d438`,
pushed and independently matched with `git ls-remote`. The subsequent receipt-only
commit does not change this executable version. Local resolver version: uv 0.12.19.
Full evidence backup receipt: `research_logs/gpu_preparation_R2_20261014_run01.json`;
all planned objects were uploaded/reused and fully GET SHA256 verified, zero failures.
The backup includes the synthetic checkpoint excluded from Git. The receipt is
outside its own payload to avoid recursive self-archiving. This is a Codex evidence
backup; it does not imply the future RunPod job or its backup has run.
