#!/bin/bash
# Bash 4.2 compatible; submit or resume the same unfinished experiment.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python=${HPC_V2_PYTHON:-/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python}
config=${1:-$here/configs/kumar_dev.json}
if [ "$#" -gt 0 ]; then shift; fi
exec "$python" -u "$here/bootstrap.py" submit --config "$config" "$@"
