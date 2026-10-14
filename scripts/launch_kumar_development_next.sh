#!/usr/bin/env bash
# One explicit parent dispatch; no loop, auto-retry, query evaluation or stop.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" != "--parent-acknowledge-replay-backup" ]]; then
  echo 'Parent must review replay backup and schedule the shared GPU before this command.' >&2
  exit 2
fi
export PYTHONPATH="$PWD/src:$PWD/scripts"
export XDG_CACHE_HOME=/workspace/.cache-paper2
export MPLCONFIGDIR=/workspace/.cache-paper2/matplotlib
export MNE_DONTWRITE_HOME=true
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
mkdir -p /workspace/paper2-results
PAPER2_DISPATCH_LOG=$(mktemp /workspace/paper2-results/queue-dispatch-XXXXXXXX.log)
set +e
(
  date -u +%Y-%m-%dT%H:%M:%SZ
  git rev-parse HEAD
  timeout --signal=TERM --kill-after=30s 1800s /workspace/.venvs/paper2-gpu/bin/python     scripts/run_kumar_development_queue.py --execute-next --parent-acknowledge-replay-backup
  PAPER2_STATUS=$?
  echo "QUEUE_DISPATCH_EXIT_CODE=$PAPER2_STATUS"
  date -u +%Y-%m-%dT%H:%M:%SZ
  exit "$PAPER2_STATUS"
) > "$PAPER2_DISPATCH_LOG" 2>&1
PAPER2_EXIT=$?
set -e
cat "$PAPER2_DISPATCH_LOG"
echo "Dispatch evidence: $PAPER2_DISPATCH_LOG"
if [[ "$PAPER2_EXIT" == 75 ]]; then
  echo 'One local fit awaits private archive acceptance. Do not rerun training or stop Pod.'
else
  echo "Exit $PAPER2_EXIT; preserve output and log. No automatic retry or queue loop."
fi
exit "$PAPER2_EXIT"
