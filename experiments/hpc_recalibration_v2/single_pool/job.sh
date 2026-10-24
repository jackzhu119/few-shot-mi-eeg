#!/bin/bash
printf 'shell_start job=%s host=%s utc=%s mode=single_pool\n' "${SLURM_JOB_ID:-none}" "$(hostname)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set -u
config=${1:?configuration path required}
python=${2:?Python executable required}
indices=${3:-}
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
if [ -n "$indices" ]; then
    "$python" -u "$here/controller.py" --config "$config" --indices "$indices" &
else
    "$python" -u "$here/controller.py" --config "$config" &
fi
child=$!
if [ "$cancel_seen" -ne 0 ]; then kill -TERM "$child" 2>/dev/null || :; fi
if [ "$usr1_seen" -ne 0 ] && [ "$cancel_seen" -eq 0 ]; then kill -USR1 "$child" 2>/dev/null || :; fi
printf 'pool_controller pid=%s utc=%s\n' "$child" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
while :; do
    wait "$child"
    rc=$?
    if kill -0 "$child" 2>/dev/null; then continue; fi
    wait "$child"
    rc=$?
    break
done
printf 'pool_exit code=%s usr1=%s cancelled=%s utc=%s\n' "$rc" "$usr1_seen" "$cancel_seen" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ "$cancel_seen" -ne 0 ]; then exit 130; fi
usr1_exit=$((128 + $(kill -l USR1)))
if [ "$usr1_seen" -eq 1 ] && { [ "$rc" -eq 75 ] || [ "$rc" -eq "$usr1_exit" ]; }; then
    if [ "$rc" -eq "$usr1_exit" ]; then
        printf 'controller_preempted_before_or_after_handler observed_code=%s; execution before signal is unknown\n' "$rc"
    fi
    if scontrol requeue "${SLURM_JOB_ID:?job identity missing}"; then
        printf 'requeue_requested job=%s; retained task artifacts determine continuation\n' "$SLURM_JOB_ID"
        exit 0
    fi
    printf 'requeue_denied; checkpoints retained; rerun the same local command\n' >&2
    exit 75
fi
exit "$rc"
