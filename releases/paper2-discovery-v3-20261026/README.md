# V3 mathematical discovery round — school launch

**Ready code; no real V3 EEG run or A100 validation has been claimed.** The fixed initial exploratory matrix has126tasks and3persistentGPUjobs. This release reuses the already completed school V2 project,78input NPZ files and18V2source teachers. It downloads no new EEG and never refits oldV2/old54sources.

Read [the mathematical design](../../docs/paper2_discovery_v3_20261026.md) and [the exact task/freeze record](../../research_logs/paper2_discovery_v3_preparation_20261026/SCIENCE_FREEZE.json). It explores nine geometric estimators, eight neural update positions/modes under two source regimes, three functional-KL doses, and384paired synthetic mechanism scenarios. The newly pooled source data are240TRAIN/120validation from the same6participants, not additional independent participants.

## One-line download, install and submit

Execute the single line in [START_ON_HPC.txt](START_ON_HPC.txt) from `login1`. It uses the existing `paper2_start.py` only for trusted-CA/pinned-download helpers, downloads the127,001-byte installer, verifies SHA256, installs into a separate project and submits. It does not invoke the V2 training launcher.

First launch offers **hidden** GitHub token input; Enter may reuse the private token already saved on the server. It performs one actual write-permission probe in the new V3 status prefix before submission. No token is embedded in code or committed. Normal resumes reuse that authorization; to renew while jobs are active append ` --reauthorize` to the startup or resume command.

The installer uses `/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python`, without upgrading packages, installing dependencies or replacing the V2 project. All computational jobs are submitted to `hpc_gpu1`, account `zhuziyuan`, with **oneGPU/16CPU/64G each, threejobs maximum**. No giant array, DDP, GPU UUID requirement or hard-coded physical device index is used. Each job sees its Slurm allocation as `cuda:0`.

Submission replies identify acceptedjobIDs and partial-QoSrefusals separately. Existingaccepted/runningjobs are never cancelled to make room. Repeating the same command fills only missing slots; resource availability/queuewaiting are decided bySlurm, not by a website's free-count display. Actual first training steps/checkpoints establish GPU execution, not the submission reply.

## Resume without reinstallation or repeated tests

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/projects/paper2-recalibration-v3/bootstrap.py submit
```

Completed tasks are skipped; interrupted optimizer/scheduler/scaler/sampling/RNG states resume. Fit states and evaluation shards are separate. USR1 checkpoints then requests requeue when permitted; manual cancellation does not requeue. The configured5days3hours is a previously used candidate allocation limit, not a verified queue maximum. There is no cumulative12hour timer.

No pytest, full-library scan, repeated GPU pilot or per-fit approval is a school startup dependency. Frozen inputs reuse V2's verified file stats; first stage additionally hashes the18teachers once. Only changed/unverified bytes are hashed thereafter, and a timestamp-only touch with unchangedbytes refreshes the cache. Numeric/data/storage failures remain real failures; independent reporting errors cannot stop GPU workers.

## Paths, progress and results

- Project: `/public/home/zhuziyuan/projects/paper2-recalibration-v3`.
- Saved outputs/checkpoints: `outputs/kumar-discovery-v3/` under that project.
- Logs: `outputs/kumar-discovery-v3/logs/%x-%j.out` and `.err`.
- Progress: [training_status/paper2-discovery-v3/STATUS.json](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-discovery-v3/STATUS.json) appears after the school monitor actually publishes; it is not a pre-existing result.
- Monitor log: `outputs/kumar-discovery-v3/github_sync/monitor.log`.
- Saved-result analysis: `outputs/kumar-discovery-v3/analysis/`.

The login-side monitor reports about180seconds independently, retries network failures, and automatically uploads all completed derivedoutputs at the end with fullGET/SHA256. Terminal partial runs also publish an explicitly partial packet rather than waiting for a failed ancillary task. It retains failures, original predictionbytes, text traininghistories, new uncertainty diagnostics and modelhashes. Raw EEG/checkpoint/optimizer binaries remain in persistent school storage. A successful upload is not automatically a scientific acceptance.

Status without training:

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/projects/paper2-recalibration-v3/bootstrap.py status
```

To summarize or publish a partial result explicitly, replace `status` with `summarize` or `publish`. These commands do not fit or forward a model.

## Fixed versions and software validation

- Source: `36a74e751282c74ada32240b73033eeb71fb685e`.
- Installer artifact commit: `01eaa2d3b92b5a4e51f69a595bb702e469ad3e4e`.
- Installer bytes:127001; SHA256 `618e8cc7f51d88531154a4617e85d6350de938430b0e2954a38eac07f11d4a51`.
- Scientific JSON SHA256: `6c41a2135916ab133c423c2b972ba8745bcdc3e16b96abf6f26e7e076c8d2407`.
- 130 focused synthetic CPU tests passed; Ruff and Bashsyntax passed. This includes actual zipapp installation/reinstallation/imports in a fresh synthetic project, same-environment exact checkpoint continuation, separate Dropout/sampler RNG, projected KL feasibility and rollback, spool-path signals, missing-class mathematical fallback, source/regime/dose aggregation, and full-GET publication failures. No real A100 run/fullsimulationgrid was performed in Codex.

The operating baseline remains olderEL7/Bash4.2 with the user's existingPython3.12.3/Torch2.5.1+cu121/NumPy2.2.6 environment. Local tests usedPython3.11.16/Torch2.8.0+cpu/NumPy2.2.6. CUDA build is not asserted to be the installeddriver version. Actual runtime observations are recorded without turning patch-version differences into restart gates.
