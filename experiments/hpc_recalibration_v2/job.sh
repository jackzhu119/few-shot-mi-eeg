#!/bin/bash
# Slurm opens the absolute output/error paths before invoking this script.
printf 'shell_start job=%s task=%s host=%s utc=%s\n' "${SLURM_JOB_ID:-none}" "${SLURM_ARRAY_TASK_ID:-none}" "$(hostname)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set -u
config=${1:?configuration path required}
python=${2:?Python executable required}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
child=''
usr1_seen=0
cancel_seen=0
forward_usr1() {
    usr1_seen=1
    if [ -n "$child" ]; then kill -USR1 "$child" 2>/dev/null || :; fi
}
forward_cancel() {
    cancel_seen=1
    if [ -n "$child" ]; then kill -TERM "$child" 2>/dev/null || :; fi
}
trap forward_usr1 USR1
trap forward_cancel TERM INT
"$python" -u "$here/bootstrap.py" worker --config "$config" --index "${SLURM_ARRAY_TASK_ID:?array index required}" &
child=$!
if [ "$cancel_seen" -ne 0 ]; then kill -TERM "$child" 2>/dev/null || :; fi
if [ "$usr1_seen" -ne 0 ] && [ "$cancel_seen" -eq 0 ]; then kill -USR1 "$child" 2>/dev/null || :; fi
printf 'python_child pid=%s utc=%s\n' "$child" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Bash wait is interrupted by a trapped signal; wait again while the child lives.
while :; do
    wait "$child"
    rc=$?
    if kill -0 "$child" 2>/dev/null; then continue; fi
    # A trap may interrupt wait just as the child exits; obtain its cached real
    # status instead of accidentally reporting 128+USR1 as the worker exit.
    wait "$child"
    rc=$?
    break
done
printf 'python_exit code=%s usr1=%s cancelled=%s utc=%s\n' "$rc" "$usr1_seen" "$cancel_seen" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ "$cancel_seen" -ne 0 ]; then exit 130; fi
if [ "$rc" -eq 75 ] && [ "$usr1_seen" -eq 1 ]; then
    target=${SLURM_JOB_ID:?Slurm job identity missing}
    if [ -n "${SLURM_ARRAY_JOB_ID:-}" ]; then
        target="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
    fi
    if scontrol requeue "$target"; then
        printf 'requeue_requested job=%s; persisted checkpoint will be resumed\n' "$target"
        exit 0
    fi
    printf 'requeue_denied job=%s; checkpoint retained; rerun the same launch command\n' "$target" >&2
fi
exit "$rc"
