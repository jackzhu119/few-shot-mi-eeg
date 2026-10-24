# Paper2: one job on hpc_gpu1, two independent GPU workers

Current allocation: **hpc_gpu1, one job,2 GPUs,24 CPUs,128G total**. Each
worker has a planned12CPU/64G share. The scheduler enforces the aggregate job
allocation. Tasks run in the existing fixed order, at most two concurrently;
there is no array or DDP. Scientific parameters, inputs, numerical threads,
completed tasks and checkpoint identities are unchanged.

## Existing installation: update, enter token and apply24 total CPUs

Run this single line in the same school login terminal. It backs up the local
starter and changes its two pins. The downloaded inputs and original sealed
code package are reused. It automatically identifies this project’s current active job from the queue and
submission ledger, including a new job ID created by a prior migration. It never
selects another paper’s job or starts a duplicate. The request includes
`--nodes=1`, so both GPUs are allocated on the same node.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import re,runpy; from pathlib import Path; p=Path("/public/home/zhuziyuan/paper2_start.py"); s=p.read_text(); d=runpy.run_path(str(p),run_name="paper2_update_helper"); n,a=re.subn("(?m)^COMMIT = .*$","COMMIT = \"590241df53c8ef48b59dc4ed16707d52f2c4a1af\"",s); n,b=re.subn("(?m)^SHA256 = .*$","SHA256 = \"8c1ba44de524a231110f128caf36545b50cc3255b07fe92e260a9f17e0202723\"",n); assert (a,b)==(1,1),"Local entry format differs; no file changed"; compile(n,str(p),"exec"); q=p.with_name("paper2_start.before_hpc_gpu1_24cpu.py"); q.exists() or d["atomic_file"](q,s.encode()); d["atomic_file"](p,n.encode()); exec(compile(n,str(p),"exec"))' --switch-job auto
```

The script determines the actual job state before changing it:

- **PENDING:** hold the old job, force hidden GitHub token input and an actual
  repository write probe, update Partition=hpc_gpu1 and both NumCPUs/CPUsPerTask=24,
  update the companion config, then release the same job. No new job is submitted.
- **RUNNING:** send TERM to the batch shell, which forwards it for checkpoint
  saving without automatic requeue. Wait up to45seconds for exit and terminal
  accounting; then force hidden authorization and submit one continuation job.
  Completed tasks skip and unfinished stages load their checkpoints. No KILL or
  USR1 is sent. If exit/accounting is still pending, rerun this same migration
  line after it settles; no duplicate is submitted.
- Repeating a successful pending migration returns `already_migrated` and does
  not interrupt the migrated running job. Failures retain their actual receipts;
  a held job stays held if authorization or resource update fails.

At the prompt `GitHub token (hidden; repository Contents read/write):`, paste
your token and press Enter. It must permit **Contents: Read and write** for
`jackzhu119/few-shot-mi-eeg`. The token is not echoed or put in GitHub/code/logs.
It is stored in the account's private0600 file only after the write probe passes.
An existing cached authorization does not bypass this manual step. A rejected
new token leaves the previous private token intact.

## Later start / checkpoint continuation

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/paper2_start.py --switch-job auto
```

An already active job is not duplicated and its monitor is restarted if needed.
A new submission requires hidden token input. Completed work does not restart.
An existing allocation whose recorded request already matches24CPUs is reused;
no TERM, resubmission or token prompt is added for that running job.
The target companion profile is `configs/kumar_dev_hpc_gpu1_24cpu.json`, separate
from both previous resource profiles. The original
`kumar_dev.json` remains unchanged. An existing pending batch's referenced old
companion config is updated only while held, with its original bytes backed up.

GitHub progress and completed metric summaries are synchronized about every180
seconds to `training_status/paper2-recalibration-v2/STATUS.json` on branch
`research/paper2-hpc-v2-20261023`. Network failures retry in the independent
monitor and do not stop training. Persistent model/checkpoint outputs stay under
`/public/home/zhuziyuan/projects/paper2-recalibration-v2/outputs/kumar-dev-v2`.

The screenshot reports zero idle nodes. Resource availability and queue waiting
remain determined by the school scheduler. No node hostname or GPU UUID is
pinned. This does not modify another paper's jobs or acquire any new resources.

## Fresh installation only

Use the line below only if no local starter/installation exists. Public downloads
need no token; hidden manual authorization follows before the first submission.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import base64,json,zlib; p=json.loads(zlib.decompress(base64.b64decode("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"))); exec(compile(p["source"],"paper2_start.py","exec"),{"__name__":"__main__","BOOTSTRAP_SOURCE":p["source"].encode(),"BOOTSTRAP_TOKEN":p.get("token")})'
```

## Input and validation

The four GitHub input parts reconstruct125,283,270 bytes with SHA256
`b6f211bbf2ed512fbf30d178d59c67181396c98d0ec122812519ee95a9aa3e0a`.
[Input manifest](input_download_manifest.json) and
[source attribution](DATA_ATTRIBUTION.txt) retain the original CC BY4.0 terms.
[Scientific design](../../docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md)
keeps the new development experiment separate from the old54 accepted models.

[Current24CPU validation](../../research_logs/paper2_hpc_v2_20261023/hpc_gpu1_24cpu_20261024/)
records software-only Slurm/authorization tests and a real pseudoterminal hidden
input check. Historical [single-job](../../research_logs/paper2_hpc_v2_20261023/single_pool_20261024/)
and [36CPU/128G](../../research_logs/paper2_hpc_v2_20261023/resources_36cpu128g_20261024/)
receipts remain unchanged. No actual school Slurm action was executed by Codex.
