#!/usr/bin/env bash
# Parent starts this once after checking paper 1 does not need the shared GPU.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src:$PWD/scripts"
export XDG_CACHE_HOME=/workspace/.cache-paper2
export MPLCONFIGDIR=/workspace/.cache-paper2/matplotlib
export MNE_DONTWRITE_HOME=true
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
PAPER2_PYTHON=/workspace/.venvs/paper2-gpu/bin/python
PAPER2_LAUNCH_LOG=/workspace/paper2-results/kumar-first-fit-launch-run01.log
if [[ -e "$PAPER2_LAUNCH_LOG" ]]; then
  echo 'Prior launch log exists; inspect previous task, do not automatically relaunch.' >&2
  exit 1
fi
PAPER2_GPU_PIDS=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)
if [[ -n "$PAPER2_GPU_PIDS" ]]; then
  echo 'GPU compute process already present; parent must resolve scheduling.' >&2
  exit 1
fi
mkdir -p /workspace/paper2-results
set +e
(
  set -o noclobber
  timeout --signal=TERM --kill-after=30s 1800s "$PAPER2_PYTHON" \
    scripts/run_kumar_parent_first_fit.py \
    --data-root /workspace/paper2-data/kumar \
    --download-receipt /workspace/paper2-results/https-first-fit-download-run01.json \
    --execute-first-fit > "$PAPER2_LAUNCH_LOG" 2>&1
)
PAPER2_EXIT=$?
set -e
if [[ "$PAPER2_EXIT" == 75 ]]; then
  echo 'Local fit/package ready; R2 backup and parent acknowledgement PENDING. Do not stop Pod.'
  exit 75
fi
echo "First fit failed or timed out (exit $PAPER2_EXIT); preserve log and task state; no automatic retry." >&2
exit "$PAPER2_EXIT"
