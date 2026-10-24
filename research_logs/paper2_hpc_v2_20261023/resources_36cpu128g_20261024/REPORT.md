# One school job: two GPUs, 36 CPUs, 128G total

The author's latest resource choice supersedes the prior two-GPU/32-CPU/256G
request. The actual school `sbatch` response rejected that request with
`Memory specification can not be satisfied` and
`Requested node configuration is not available`; no job ID was returned.
The earlier explicit refusal remains in the existing submission ledger.

Only the companion deployment profile changes: two workers, each with planned
18-CPU/64G share. The unchanged submitter requests one allocation with
`--gres=gpu:2 --cpus-per-task=36 --mem=128G`; no array is submitted. Slurm enforces
the aggregate allocation. These are requested resources, not a measured memory
peak or a guarantee of admission on the private school cluster.

The loader is fixed at `d9743047f5c41c1f6226b5bf4e3bd9cbe89b6067`, SHA256
`6d539199bf7e7b641abcc8575d29ca1227cd1e74e22b9383024604557424fd71`.
The existing runtime remains `45e6548a7d0ef02fd26176a4c3860af034dc9c96`.
Its submitter, controller and signal/requeue shell bytes are unchanged. No new
resource preflight, scheduler-discovery dependency or automatic submission retry
was introduced. Scientific task/input/checkpoint identities and numerical thread
settings are unchanged.

69 relevant tests passed: profile8, direct downloads29, runtime installation3,
single-job submission20, bootstrap9. Ruff and whitespace checks passed. Added
tests specifically cover the requested aggregate resources and preserving the
actual memory refusal before a later single manual submission.

The delivered local updater was executed twice against the existing local cached
installation, with `--no-launch`: both exits0, old starter backup retained, new
starter byte-identical to the public source, original config unchanged, no input
download/full rescan or network request. A separate metadata-only dry run of the
unchanged installed submitter generated the exact one-job request and 24 pending
indices, without invoking Slurm, authorization, training or inference.

See [validation.json](validation.json) for actual local receipt and preview.
The [school updater](../../../releases/paper2-hpc-v2-20261023/UPDATE_RESOURCES_36CPU_128G.txt)
updates the two local version pins and reuses existing data, preparation cache,
private authorization and checkpoints. School admission and GPU execution remain
to be observed from the user's terminal.
