# hpc_gpu1: one job, two GPUs, manual GitHub authorization

The author's latest choice is one allocation on `hpc_gpu1`:2GPUs,32CPUs and128G
total, with two planned16CPU/64G worker shares. The screenshot reports zero idle
nodes; it does not establish immediate allocation availability. No new node,
resource purchase, model, scientific configuration or thread change is involved.

The school has actually accepted prior job771075. The new local migration entry
operates only on that project's recorded job; it does not assume its current
state from the previous submission response:

- PENDING: hold, recheck state, require hidden token input and actual GitHub
  write probe, update partition and both total CPU / CPUsPerTask to32, back up
  the old companion config and update it while held, then release the same job.
- RUNNING: request TERM through the batch shell's existing checkpoint-forwarding
  handler; wait at most45seconds for exit and terminal accounting, then require
  manual authorization before one continuation submission. No KILL/USR1 or
  automatic scientific retry loop is added. A still-running/settling job is not
  duplicated; the same migration command can be run again after it exits.
- A repeated successful pending migration is recognized and never interrupts
  the already migrated running job. Failure evidence, holds, old logs and model
  checkpoints are preserved. Completed tasks skip.

The new target profile is `configs/kumar_dev_hpc_gpu1.json`; creation/installation
does not alter the existing active `kumar_dev_hpc_gpu.json`. In-place migration
updates that old batch-referenced file only while held, retaining its old bytes.
The original sealed code tar and `kumar_dev.json` stay unchanged. The submitter,
controller and signal/requeue shell hashes are unchanged; only `switch.py` is
added to a versioned runtime.

The authorization helper always uses hidden terminal input for a new
submission/release, even with a valid cached receipt. It tests the supplied
identity and a real repository write before replacing the private0600 token.
Failure leaves the previous private token intact. No credential value or digest
is written to public code, receipts or logs. The existing independent monitor
reads the private token and uploads progress/completed metric summaries about
every180seconds; network failures do not stop model training.

Frozen runtime: `782074a4890779c0ffd6367d1b137b2161e0c36d`.
Frozen loader: `a3a722c1b71dca718cb35b87b42ea93c75c8ecdf`, SHA256
`fc7ebb3805c9f65860efcce3166a15dbd7f50521921e02357222e03988743772`.

85 relevant tests passed: profile10, downloads29, runtime installation3,
migration/authorization14, submission20, bootstrap9. Ruff and whitespace checks
passed. The tests mock Slurm and GitHub; they do not claim school execution.
An actual pseudoterminal test with a synthetic GitHub client confirmed hidden
input, no secret echo,0600 storage and no secret in the receipt. Actual official
GitHub downloads verified all four installed runtime files. The delivered local
updater ran twice with `--no-launch` against the existing local cached install:
both exits0, old config/backup retained, no input download or full rescan, and
the repeat needed no network. The installed submitter's metadata-only preview
produced one exact2GPU/32CPU/128G job on `hpc_gpu1`, with no array.

Slurm20.11.8 compatibility was checked against the actual upstream
[scontrol manual source](https://github.com/SchedMD/slurm/blob/slurm-20-11-8-1/doc/man/man1/scontrol.1),
which documents both `NumCPUs` and `CPUsPerTask` updates. Local policy permission
and actual job admission remain the school scheduler's decision. No actual
school job was held, signaled, changed, submitted or trained by Codex.

See [validation.json](validation.json), [install_validation.json](install_validation.json)
and [tty_authorization_validation.json](tty_authorization_validation.json).
The [delivered migration command](../../../releases/paper2-hpc-v2-20261023/UPDATE_TO_HPC_GPU1.txt)
is for the school interactive login terminal.
