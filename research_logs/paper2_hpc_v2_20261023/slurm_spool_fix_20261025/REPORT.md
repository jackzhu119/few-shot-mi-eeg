# Job771415: Slurm copied-script controller path repair

The user's actual school stderr establishes the cause:

```text
python: can't open file '/opt/gridview/slurm/spool/slurmd/job771415/controller.py': [Errno 2] No such file or directory
```

The shell started on gpu4 at2026-10-25T07:07:26Z and exited2 at07:07:28Z, with
USR1/cancellation flags0. The original job script derived its runtime directory
from `dirname "$0"`. Slurm copies a batch script into its spool directory, so
the derived path was not the shared versioned runtime. Failure occurred while
opening the controller file. The original school logs are not overwritten.
[User-provided evidence](user_reported_job_771415.json) records the terminal
excerpt and provenance; its excerpt hash is not claimed as the original file hash.

## Minimal runtime change

- The submit command explicitly supplies
  `--export=ALL,PAPER2_POOL_RUNTIME=<fixed absolute shared runtime directory>`.
- The batch script uses that directory, prints the resolved controller path,
  and never derives it from the Slurm spool path. Missing/relative binding fails
  clearly before dispatch. Ordinary direct local execution retains its fallback.
- Batch positional arguments remain unchanged, including the recorded config
  position. Science, controller scheduling, numerical threads, inputs, methods,
  checkpoint identities and completed-task skipping are unchanged.
- Matching resource counts alone cannot reuse an obsolete copied launcher.
  If an old launcher is still PENDING, only the recorded project job is held,
  manually authorized and cancelled before terminal accounting and one fixed
  replacement submission. Its original records and config remain. A live job
  follows the existing TERM-save path; no concurrent duplicate is launched.

Resources remain one node/job on hpc_gpu1,2GPUs,total24CPUs/128G. Existing
downloaded input/code archives and preparation cache are reused. This repair
does not delete claims, rerun accepted54 models, install dependencies or operate
the school scheduler from Codex. Normal manual GitHub input/write probe and the
independent progress/metric synchronizer remain in place.

Frozen runtime: `57571a93a020e4c4c75ccbdcbbd51350b8393239`.
Frozen loader: `e50ef7d9d75a6af731e955d027df90ab79530e2d`, SHA256
`6ff4d246cba9b2269860ce433d39efea773e07f0f8c3f115d897715b457a96b6`.

## Verification actually completed

85 focused tests passed: copied-spool startup4, pool/signal17, submission21,
migration14, automatic selection/replacement7, runtime profile10, runtime
installation3, local starter9. Ruff, Bash syntax and whitespace checks passed.
The prior signal tests now explicitly bind the runtime. New actual Bash/Python
tests execute a copied batch file, including a shared path containing spaces,
and verify missing bindings fail without launching a child.

An independent actual local reproduction showed original direct launch exit0
but copied launch exit2, with the same missing-controller failure. Its
explicit-argument prototype demonstrated the cause; the final released repair
uses the environment binding to preserve positional arguments. See
[failure_reproduction.json](failure_reproduction.json).

The actual public loader/runtime were downloaded and installed into the
versioned local cache. The delivered updater completed with `--no-launch`,
reused the original120-file installation and performed no input redownload/full
archive rescan. A real copied batch script then started the actual installed
controller and four synthetic stdlib workers; it dispatched two distinct GPU
tokens concurrently, retained fixed order and completion records, and exited0
with empty stderr. This was CPU software validation, not GPU or EEG training.
See [fixed_chain_validation.json](fixed_chain_validation.json).

The school operator runs the [fixed one-line updater](../../../releases/paper2-hpc-v2-20261023/UPDATE_SPOOL_FIX_20261025.txt)
and enters GitHub authorization at the hidden prompt. A new school's log should
show the absolute `pool_runtime` path followed by actual controller/worker and
step/checkpoint progress. The failed771415 evidence remains historical.
