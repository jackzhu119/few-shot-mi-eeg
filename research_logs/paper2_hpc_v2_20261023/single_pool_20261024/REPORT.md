# Single-job queue repair after actual Slurm QoS rejection

The school log shows successful125,283,270-byte input restoration, installation
and GitHub authorization, followed by `QOSMaxSubmitJobPerUserLimit`. A24-item
array with `%2` still counts multiple submitted items; `%2` limits running items.
The rejection did not start a scientific worker through that submission.

## Final behavior

One `sbatch`, one node, two GPUs,32CPUs,256G in partition hpc_gpu; no array.
Inside that allocation, at most two independent workers take the next fixed
index, each with one Slurm GPU token. All24 original tasks remain in the queue.
Source package, inputs, scientific config, experiment ID, output_root and
checkpoint identities are unchanged. The added immutable runtime files live
under `.hpc_runtime/<commit>/`; the old120-file installation cache remains valid.

The new submitter preserves prior submission evidence byte-for-byte in a backup,
then appends a resolution only for a nonzero, no-job-ID, explicit negative Slurm
reply. A conflicting numeric job reply or communication uncertainty remains
blocked. It never cancels other papers or loops sbatch after a rejection.
Even one job needs one available submit slot; a fully occupied account can
still be refused, with an explicit retry-after-release message.

USR1 stops dispatch and forwards to active groups; saved interruptions can
requeue the same job ID. TERM/INT never revive it. Known scientific failures
are not retried within the invocation or on automatic same-job requeue; other
independent items can continue. A new explicit manual submission after repair
can retry unfinished/failed tasks from their preserved checkpoints.

## Observed validation and limits

-75 related tests passed in2.65s; no unrelated full scientific suite rerun.
-Actual immutable runtime files were downloaded through the official API with
 full SHA checks. Installed originals were retained and no EEG archive was
 downloaded again.
-A real local controller dispatched24 real synthetic Python subprocesses once,
 with a maximum of two active; a repeat launched none. This is software-only
 validation without Torch/GPU/EEG/model fitting.
-Real Bash/controller signal tests and startup-signal tests verify USR1/requeue
 and TERM/no-revival boundaries.
-The versioned submit entry actually ran `--dry-run` with the prepared local
 input metadata, producing exactly one sbatch request and no array. It did not
 contact Slurm or perform a fit.
-The final local updater was executed twice: the original source backup and
 private token inode/mtime/mode remained unchanged, final source matched the
 public entry, and the second pass made no network connection.

School-side GitHub AUTHORIZATION.json from commit3a2480c was fetched and merged
without overwriting it. This is actual school permission-probe evidence; it is
not proof of a running or accepted Slurm training job. The final submit action
will be performed by the author in login1, using the updated local entry.

Pins, actual commands, hashes and scope are in validation_final.json and
final_upgrade_receipt.json. Earlier335cd65 runtime proofs remain as original
records; the final runtime is45e6548 and adds the explicit same-job failure
retention rule. No prior failure log, checkpoint, ledger or receipt was reset.
