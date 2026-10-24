# Paper2: one job on hpc_gpu1, two independent GPU workers

Current allocation: **hpc_gpu1, one job,2 GPUs,32 CPUs,128G total**. Each
worker has a planned16CPU/64G share. The scheduler enforces the aggregate job
allocation. Tasks run in the existing fixed order, at most two concurrently;
there is no array or DDP. Scientific parameters, inputs, numerical threads,
completed tasks and checkpoint identities are unchanged.

## Existing job771075: update, enter token and migrate

Run this single line in the same school login terminal. It backs up the local
starter and changes its two pins. The downloaded inputs and original sealed
code package are reused. It handles only the recorded job771075 in this project.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import re,runpy; from pathlib import Path; p=Path("/public/home/zhuziyuan/paper2_start.py"); s=p.read_text(); d=runpy.run_path(str(p),run_name="paper2_update_helper"); n,a=re.subn("(?m)^COMMIT = .*$","COMMIT = \"a3a722c1b71dca718cb35b87b42ea93c75c8ecdf\"",s); n,b=re.subn("(?m)^SHA256 = .*$","SHA256 = \"fc7ebb3805c9f65860efcce3166a15dbd7f50521921e02357222e03988743772\"",n); assert (a,b)==(1,1),"Local entry format differs; no file changed"; compile(n,str(p),"exec"); q=p.with_name("paper2_start.before_hpc_gpu1.py"); q.exists() or d["atomic_file"](q,s.encode()); d["atomic_file"](p,n.encode()); exec(compile(n,str(p),"exec"))' --switch-job 771075
```

The script determines the actual job state before changing it:

- **PENDING:** hold the old job, force hidden GitHub token input and an actual
  repository write probe, update Partition=hpc_gpu1 and both NumCPUs/CPUsPerTask=32,
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
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/paper2_start.py
```

An already active job is not duplicated and its monitor is restarted if needed.
A new submission requires hidden token input. Completed work does not restart.
The target companion profile is `configs/kumar_dev_hpc_gpu1.json`; the original
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

[Current migration validation](../../research_logs/paper2_hpc_v2_20261023/hpc_gpu1_switch_20261024/)
records software-only Slurm/authorization tests and a real pseudoterminal hidden
input check. Historical [single-job](../../research_logs/paper2_hpc_v2_20261023/single_pool_20261024/)
and [36CPU/128G](../../research_logs/paper2_hpc_v2_20261023/resources_36cpu128g_20261024/)
receipts remain unchanged. No actual school Slurm action was executed by Codex.
