# hpc_gpu1: one node, one job, two GPUs,24 total CPUs,128G

The latest author request supersedes the32CPU allocation. Both GPU workers run
on the same node inside one job: `--nodes=1 --ntasks=1 --partition=hpc_gpu1
--gres=gpu:2 --cpus-per-task=24 --mem=128G`. Each worker has a planned12CPU/64G
share; Slurm enforces the aggregate allocation. Existing numerical thread
settings, scientific task/input identities, models, seeds and task order are
unchanged. The original submitter, controller and signal shell are unchanged.

The resource profile is `configs/kumar_dev_hpc_gpu1_24cpu.json`, separate from
both previous companions. Installation does not overwrite an active32CPU
profile. The new `--switch-job auto` identifies the current project job through
the actual queue and submission ledger, including replacement job IDs created
by a prior migration; it reads the original config path from that batch command.
Pending jobs retain their ID and are held before manual authorization and both
NumCPUs/CPUsPerTask updates to24. Running jobs follow the existing TERM-save,
exit/accounting and checkpoint-continuation path. A recorded request already
matching the target allocation is reused without another TERM or submission.
Completed tasks skip; no duplicate or scientific retry loop is added.

Fresh hidden GitHub input and actual write verification precede release or new
submission. The existing independent monitor uploads progress and completed
metric summaries about every180seconds, retries reporting failures and cannot
cancel training. Model checkpoints remain on persistent school storage. The
manual-authorization implementation is unchanged from the prior
[pseudoterminal proof](../hpc_gpu1_switch_20261024/tty_authorization_validation.json).
No credential value is published.

Frozen runtime: `c7cb90a7c73dece6aca082c687dcafcc1028a32d`.
Frozen loader: `590241df53c8ef48b59dc4ed16707d52f2c4a1af`, SHA256
`8c1ba44de524a231110f128caf36545b50cc3255b07fe92e260a9f17e0202723`.

108 relevant tests passed: profile10, download29, runtime installation3,
migration/authorization14, submission21, bootstrap9, GitHub sync17, automatic
job selection5. Ruff and whitespace checks passed. These cover one-node
resource requests, automatic current-ID selection, unchanged science, manual
write authorization, exact pending CPU updates, idempotency, reporting failure
isolation and preventing duplicate jobs. Slurm/GitHub operations are mocked in
these tests; no school execution is inferred from them.

The actual public loader and changed runtime were downloaded through the
official GitHub API, then the delivered updater ran twice against the existing
local cached install with `--no-launch`, both exits0. The updated starter matches
the public source. Three prior config files retained their full SHA256. The
input was not downloaded again or rescanned by the installer; a separate
one-time local full archive SHA256 check confirmed125,283,270 bytes and
`b6f211bbf2ed512fbf30d178d59c67181396c98d0ec122812519ee95a9aa3e0a`.
The repeat needed no network. The installed submitter's metadata-only preview
produced the exact requested single-node allocation with no array.

The school monitor's public snapshot at2026-10-24T10:41:24Z showed0/24 completed
and no task progress records. That proves a reporting snapshot was published;
it does not prove model updates or explain the scheduler state. Actual school
queue/log/checkpoint progress must establish the start of training. Codex has
not accessed the private school scheduler or held/signaled/submitted any job.

See [validation.json](validation.json) and the
[one-line school updater](../../../releases/paper2-hpc-v2-20261023/UPDATE_TO_24CPU.txt).
