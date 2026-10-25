# Paper2: one job on hpc_gpu1, two independent GPU workers

Current allocation: **hpc_gpu1, one job,2 GPUs,24 CPUs,128G total**. Each
worker has a planned12CPU/64G share. The scheduler enforces the aggregate job
allocation. Tasks run in the existing fixed order, at most two concurrently;
there is no array or DDP. Scientific parameters, inputs, numerical threads,
completed tasks and checkpoint identities are unchanged.

## Existing installation: repair the Slurm-spooled launcher and continue

Run this single line in the same school login terminal. It backs up the local
starter and changes its two pins. The downloaded inputs and original sealed
code package are reused. It automatically identifies this project’s current active job from the queue and
submission ledger, including a new job ID created by a prior migration. It never
selects another paper’s job or starts a duplicate. The request includes
`--nodes=1`, so both GPUs are allocated on the same node.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import re,runpy; from pathlib import Path; p=Path("/public/home/zhuziyuan/paper2_start.py"); s=p.read_text(); d=runpy.run_path(str(p),run_name="paper2_update_helper"); n,a=re.subn("(?m)^COMMIT = .*$","COMMIT = \"e50ef7d9d75a6af731e955d027df90ab79530e2d\"",s); n,b=re.subn("(?m)^SHA256 = .*$","SHA256 = \"6ff4d246cba9b2269860ce433d39efea773e07f0f8c3f115d897715b457a96b6\"",n); assert (a,b)==(1,1),"Local entry format differs; no file changed"; compile(n,str(p),"exec"); q=p.with_name("paper2_start.before_spool_fix.py"); q.exists() or d["atomic_file"](q,s.encode()); d["atomic_file"](p,n.encode()); exec(compile(n,str(p),"exec"))' --switch-job auto
```

Job771415 failed because the original script located `controller.py` relative
to Slurm’s copied batch script. The updated submitter explicitly exports the
fixed shared runtime path; the batch script prints that path before starting
the controller. Existing inputs and scientific checkpoints remain reusable.

The script determines the actual job state and launcher version before changing it:

- **PENDING with an obsolete launcher:** hold, authorize, cancel only this held
  pending project job, wait for terminal accounting, then submit one replacement
  with the fixed runtime. Slurm’s old copied script cannot be repaired in place.
- **PENDING with the current launcher:** hold, authorize, update the resource
  request and companion config, then release the same job.
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
An existing allocation whose recorded request matches24CPUs and the fixed runtime is reused;
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

[Current spool repair](../../research_logs/paper2_hpc_v2_20261023/slurm_spool_fix_20261025/REPORT.md)
and [24CPU validation](../../research_logs/paper2_hpc_v2_20261023/hpc_gpu1_24cpu_20261024/)
records software-only Slurm/authorization tests and a real pseudoterminal hidden
input check. Historical [single-job](../../research_logs/paper2_hpc_v2_20261023/single_pool_20261024/)
and [36CPU/128G](../../research_logs/paper2_hpc_v2_20261023/resources_36cpu128g_20261024/)
receipts remain unchanged. No actual school Slurm action was executed by Codex.
