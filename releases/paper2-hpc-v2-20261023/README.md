# One Slurm job for the Paper2 fixed task queue

Current mode: **one Slurm allocation**, `hpc_gpu`,2 GPUs,36 CPUs and128G total.
Inside it, at most two independent one-GPU workers take the next unfinished
task in the fixed queue. Each worker has the planned18CPU/64G share; the
scheduler enforces the aggregate job allocation. This is not DDP and no job
array is submitted. Scientific parameters, task order, source IDs and outputs
remain unchanged.

## Existing installation: update and continue

If downloads already completed and sbatch reported `QOSMaxSubmitJobPerUserLimit`
or `Memory specification can not be satisfied`,
run this one line in the same school account. It backs up the local entry,
updates only its two version pins, then runs the updated entry. Existing data,
checkpoints and the private GitHub authorization file are reused.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import re,runpy; from pathlib import Path; p=Path("/public/home/zhuziyuan/paper2_start.py"); s=p.read_text(); d=runpy.run_path(str(p),run_name="paper2_update_helper"); n,a=re.subn("(?m)^COMMIT = .*$","COMMIT = \"d9743047f5c41c1f6226b5bf4e3bd9cbe89b6067\"",s); n,b=re.subn("(?m)^SHA256 = .*$","SHA256 = \"6d539199bf7e7b641abcc8575d29ca1227cd1e74e22b9383024604557424fd71\"",n); assert (a,b)==(1,1),"Local entry format differs; no file changed"; compile(n,str(p),"exec"); q=p.with_name("paper2_start.before_36cpu128g.py"); q.exists() or d["atomic_file"](q,s.encode()); d["atomic_file"](p,n.encode()); exec(compile(n,str(p),"exec"))'
```

After updating, the ordinary start/resume command remains:

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/paper2_start.py
```

Only the new small runtime files are fetched. The sealed original code package
and125,283,270-byte input archive are not replaced. The added runtime lives in
`.hpc_runtime/<fixed-commit>/`, with its complete file hashes.

The current resource request follows the author’s latest choice: **2 GPUs,36
CPUs,128G total in one job**. The prior256G request was explicitly rejected
before acceptance; preserve its ledger entry. This change does not add resource
probing or repeat data preparation. Scheduler admission remains determined by
the school’s actual configuration.

## What changed in scheduling

The old `%2` limited simultaneously running array items; it did not reduce24
submitted array elements to one accounting item. The new command requests:

```text
--nodes=1 --ntasks=1 --partition=hpc_gpu --gres=gpu:2 --cpus-per-task=36 --mem=128G
```

There is no `--array`. Processes are launched inside the existing allocation;
they do not invoke sbatch. Each child sees only its assigned Slurm GPU token
and continues to use logical `cuda:0`. Completed tasks skip; interrupted stages
load their existing full checkpoint. Scientific failures are preserved and not
automatically retried, while other independent tasks can finish. Known failed
items stay blocked across automatic same-job requeues; an explicit new manual
submission after a repair may retry them.

USR1 stops new dispatches, forwards to active workers and requeues only the same
job ID after safe interruption. TERM/INT preserve checkpoints and do not revive
the job. A single job still needs one available submission slot; account limits
are not bypassed and other papers are not cancelled.

The earlier failed sbatch record is kept. A missing job ID is resolved only when
its actual nonzero return code and explicit scheduler rejection prove that it
was not accepted; the original ledger bytes, status and stderr are preserved.
Ambiguous communication failures are not assumed to be rejections.

## Fresh installation

For an account that has not initialized the project, this one-line public
initializer saves the local entry before contacting either GitHub endpoint.
It contains no credential and uses existing trusted CA files.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import base64,json,zlib; p=json.loads(zlib.decompress(base64.b64decode("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"))); exec(compile(p["source"],"paper2_start.py","exec"),{"__name__":"__main__","BOOTSTRAP_SOURCE":p["source"].encode(),"BOOTSTRAP_TOKEN":p.get("token")})'
```

Public downloads need no token. Before first submission, the existing GitHub
permission check uses the account's private0600 token file or the hidden-input
prompt. Author-specific authorization is never published in this repository.
GitHub progress synchronization remains independent, about every180seconds;
reporting failures do not terminate workers.

## Input and evidence

The four parts restore the original archive SHA256
`b6f211bbf2ed512fbf30d178d59c67181396c98d0ec122812519ee95a9aa3e0a`.
[Input manifest](input_download_manifest.json) and [original source attribution](DATA_ATTRIBUTION.txt)
retain the CC BY4.0 source terms. [Scientific design](../../docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md)
and the old54 accepted models remain separate from these runtime changes.

[Single-job validation](../../research_logs/paper2_hpc_v2_20261023/single_pool_20261024/)
records real local runtime downloading, single-job command preview, synthetic
process/signal tests and preservation checks. No school Slurm job or scientific
model was run from the Codex validation environment.
