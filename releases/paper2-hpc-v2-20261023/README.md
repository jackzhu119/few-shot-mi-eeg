# One Slurm job for the Paper2 fixed task queue

Current mode: **one Slurm allocation**, `hpc_gpu`,2 GPUs,32 CPUs and256G total.
Inside it, at most two independent one-GPU workers take the next unfinished
task in the fixed queue. Each worker has the planned16CPU/128G share; the
scheduler enforces the aggregate job allocation. This is not DDP and no job
array is submitted. Scientific parameters, task order, source IDs and outputs
remain unchanged.

## Existing installation: update and continue

If downloads already completed and sbatch reported `QOSMaxSubmitJobPerUserLimit`,
run this one line in the same school account. It backs up the local entry,
updates only its two version pins, then runs the updated entry. Existing data,
checkpoints and the private GitHub authorization file are reused.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import re,runpy; from pathlib import Path; p=Path("/public/home/zhuziyuan/paper2_start.py"); s=p.read_text(); d=runpy.run_path(str(p),run_name="paper2_update_helper"); n,a=re.subn("(?m)^COMMIT = .*$","COMMIT = \"141410c7345e1fac33e85b31b316205e593f9fb3\"",s); n,b=re.subn("(?m)^SHA256 = .*$","SHA256 = \"41592d3cd2475afe73757e095d7f8c8ac982883b0464ec17ab956110d85cd3ac\"",n); assert (a,b)==(1,1),"Local entry format differs; no file changed"; compile(n,str(p),"exec"); q=p.with_name("paper2_start.before_single_job.py"); q.exists() or d["atomic_file"](q,s.encode()); d["atomic_file"](p,n.encode()); exec(compile(n,str(p),"exec"))'
```

After updating, the ordinary start/resume command remains:

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/paper2_start.py
```

Only the new small runtime files are fetched. The sealed original code package
and125,283,270-byte input archive are not replaced. The added runtime lives in
`.hpc_runtime/<fixed-commit>/`, with its complete file hashes.

## What changed in scheduling

The old `%2` limited simultaneously running array items; it did not reduce24
submitted array elements to one accounting item. The new command requests:

```text
--nodes=1 --ntasks=1 --partition=hpc_gpu --gres=gpu:2 --cpus-per-task=32 --mem=256G
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
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import base64,json,zlib; p=json.loads(zlib.decompress(base64.b64decode("eNqNWGtz27YS/SuoPlENTb2s2FaqueP4qo3nOnFGVjrTiTociAQt1BTAEqAtpdP/fg8elChLahNnYuK1u9g9e3aRv1pKVmXCWqPW3P7cyYTmISmZ0rTUdJEzopKllDlhQpebEdFlpTRLyc11SAouBD4TmbKQyCzjCadmY1pILrSKnMi5yEq5InGcVboqWRwTvipkqQkVQmqquRRqLubCzy6pWuZ8sR1L5QUUVJuF+vRnDLebykoUm+1IqXz3vVHbb81WRcZztpvgq92gKnOIj1hZyvL1ZMn+rOASY+bN/cePtzMyJvNW7xw/3eRicD5kvYwmgwG7HC4GPfx92+8O2fBqkF1li4HxwcOH6/7wrT123hte9dNBkvbPL4Y0YxeDi+EF614N04vsMrmkydVl//JysOievz1nSe+CLq6Gb3u9bno5TNIBTYy46eTuenb768QKZOuClbgKfN5ZFklcMgSRL0rr2/i530nli8glTWMMsSGCr4xJvz3MJh/jm2sICeatDtNJp3jiHZ2rTsJKCEvo2aISac6ipNTzVjgXpPmncQY7LTI6bK1LmgAhnYKtjKiznRDMnBSCmO2Umg8OOFHNlFPdNq6fi5RlhGq54klsAhkYTIQkpZq2R06umYkKWsIZ0eop5WXgBmo8KyvAlK250rF88sMVsDvuyotut+3OZ2locQKf1HCBHGW+g6JkGV+P5y0gm7xxqgRdQQz0jBuavSyTMLvbvnC9BJqjLJUFE4FRNG+9LHA3QhVRumR0Ndp3jpuMXkquWWBveXQ9yyu1DF6tGU1qI5Kg3oSbCBm0G9uwpWRFThMWmPuF9ka1H7iged60n2fmgL2ldaKyh9qjA7WVyLl4cqu7sHniiBMaNGOlDPhwiIlnXkoRPTINLD483MU3k+ks/vn2bgIPhW34e4tXd1qxnBmgQYAA6oKgIJksSUG48JJhcQGWSS1XBEU74srBpt0OyScpmL8r9tXCRnve8UZ9PTDodyitj7gTiRQaVph5lQOzDNiNcW9a5Tr2i8FOH5ivPhIZtMdKS3AjWBd+bUPheti9gq+gqmFSSbliZFoJQ1wTQ1Tw1SfZIGVi0pyl74hnLKKXWwbHqktEm05WHgMji9qQXawyZOQyKKXUIfkR1A68snJsPBYSlTNWjI0Bkf2sg+k24f7+A6HYJ88IQ7Pm/UWTpY2d0UI6SAVACzTWPwNBnS0wCdzSAonWMeS0ZTCbeZ5M39hTm+114FcndhdoG35fUiK1pDgW+D0IURovNqAY4CFasnXKH2EmzozHXkPD9UWJkgZDvjorfyfPoNyM4wq5KZmkNpCVI7i1Ulw8guuITU3LNY28q91u7XDTtOCWypdaF2rU6WAcPYIwqkWUyFUHaSpV5w+aPH1bVr3eVSdjL2dqKfXZip8x9tixITT8b/2zrQ7GQ/8Ba43ttCtdPvT0ZU8hxl5hpVjpxVnd/6C1IdWq2tfuiQRA4EDVOjR4MMnJRLViKE4sCHDN0JgSGgcgKXtNOllKpa2N+86ADgTaiiQ/jEmfsBxJMW+dvIGpdSfDiH0CaYxwEWu8VWrugjpjGEy7aYAxsCrb7qKDk8HdJ30X7j9xjVfJMHW/A0yHZMkMcNT4r3nrC2w/u36E6fPWCJqOJ8XrIvrdf+at6yRhhRdOiyI3VRZtQudZpLWT4ck3fygp5q2/XxUVV8Nsgge4SWg7KFnpcX9oqxj6xgLtHBsd2mfKl0l3v8OmX2Cy+EfS6/bPG4rY2lhIgmZDFn2Z3lnCC8nMqfSjGx8/KfyEoV+w9Q1I9Vebou5+dtXaaOUdhIjivhZss7sH0ug/fJ47IQ56weHlOPId3C1QSdl3mHEowCTJTgaKINBX1rKAbWufwZwtW/8ivu1SQm8Kb047imPTqMTxvuaT2QBfZBQEmo4c/J3+E4j31Osy8icyOBJ8Wyl8Au2vmjzlomJ7fcYrwradzx5D/3CEoU8WyP9uqbkuHCuuVhQl7p19u5AXoMIUZLZmSWUqeqthZLPddIztG85/5POjhryXJnvqd9IvXH+oFqh/UKm8u9/5amIfW0AEUfQZpYpMGV44tpa7dbDaylQ2LY3ycrPXIK8oF9sey5bXseuADtqsz9efJ9N+/P7+fvYwm15/jqf4MigDwxXVAtzQWcoV64D+v/FNRYHAun80cv+9wfab3SMTZjzmckFzFFxvwE7zw/2X6c2kWcr9Ie5iY3A/Oh6VbQfhUBzbp6vtC0IvxAs9gHvD2aMdz5+W1z6SAVo+MWEN2WtmgOuMP9r2pUnifsIR7Zk9W5cnO9jzUSGLPR/N7v83+bQlga2j3MHjfqqF2t8RbseL5kPBd6JuFziIik2QoHtShXkUtG3xTkzNtjva35Ntt+IZj8+UqMoUF/RHHue00ktZ8m+eSE9k2M6bIXEDW2/nc3ME6DX5uveGOYjpMXUujVy4842rYubl133b7R4t5LVXrSW7bvLU68Dn0S+3sw9f3rswNR8KwNRO2vZtuHsOveqId913nT4bFdHy8flrtxbn9tapaP7zI8K/sXn2BI310KxZ5kcDGMeGGFACaq7AJeuyYFre5o7RsQes4xU3rmt0M/ghuX84XWYPArXNN1eiEAV4Z2zuqjS4ujzVPFvQPWzMk3yy5jroYbH19/8Be4IHIg=="))); exec(compile(p["source"],"paper2_start.py","exec"),{"__name__":"__main__","BOOTSTRAP_SOURCE":p["source"].encode(),"BOOTSTRAP_TOKEN":p.get("token")})'
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
