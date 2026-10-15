#!/usr/bin/env bash
# Frozen numerical environment; no fit occurs without the reviewed explicit CLI gates.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src:$PWD/scripts"
export XDG_CACHE_HOME=/workspace/.cache-paper2
export MPLCONFIGDIR=/workspace/.cache-paper2/matplotlib
export MNE_DONTWRITE_HOME=true
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
exec /workspace/.venvs/paper2-gpu/bin/python scripts/run_kumar_development_batch.py "$@"
