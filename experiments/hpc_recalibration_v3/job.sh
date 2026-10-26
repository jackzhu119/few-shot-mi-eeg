#!/bin/bash
printf 'shell_start job=%s host=%s utc=%s mode=v3_three_jobs\n' "${SLURM_JOB_ID:-none}" "$(hostname)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set -u
config=${1:?absolute configuration path required}
python=${2:?Python executable required}
bootstrap=${3:?absolute installed bootstrap path required}
slot=${4:?worker slot required}
case "$bootstrap" in /*) ;; *) printf 'bootstrap path must be absolute\n' >&2; exit 2 ;; esac
if [ ! -r "$bootstrap" ]; then printf 'bootstrap missing: %s\n' "$bootstrap" >&2; exit 2; fi
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
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
"$python" -u "$bootstrap" worker --config "$config" --slot "$slot" &
child=$!
if [ "$cancel_seen" -ne 0 ]; then kill -TERM "$child" 2>/dev/null || :; fi
if [ "$usr1_seen" -ne 0 ] && [ "$cancel_seen" -eq 0 ]; then kill -USR1 "$child" 2>/dev/null || :; fi
printf 'worker_start pid=%s slot=%s utc=%s\n' "$child" "$slot" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
while :; do
    wait "$child"
    rc=$?
    if kill -0 "$child" 2>/dev/null; then continue; fi
    wait "$child"
    rc=$?
    break
done
printf 'worker_exit code=%s usr1=%s cancelled=%s utc=%s\n' "$rc" "$usr1_seen" "$cancel_seen" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ "$cancel_seen" -ne 0 ]; then exit 130; fi
usr1_exit=$((128 + $(kill -l USR1)))
if [ "$usr1_seen" -eq 1 ] && { [ "$rc" -eq 75 ] || [ "$rc" -eq "$usr1_exit" ]; }; then
    if [ "$rc" -eq "$usr1_exit" ]; then printf 'worker_signal_boundary: execution before handler is unknown; saved artifacts determine recovery\n'; fi
    if scontrol requeue "${SLURM_JOB_ID:?job identity missing}"; then
        printf 'requeue_requested job=%s\n' "$SLURM_JOB_ID"
        exit 0
    fi
    printf 'requeue_denied: checkpoints retained; rerun the same submit command\n' >&2
    exit 75
fi
exit "$rc"
