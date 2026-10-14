#!/usr/bin/env bash
# Environment preparation only. Never launches training or paid resources.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/workspace/.cache-paper2/uv
export UV_PYTHON_INSTALL_DIR=/workspace/.python-paper2
export UV_PROJECT_ENVIRONMENT=/workspace/.venvs/paper2-gpu
python3 - <<'PY'
import shutil
free = shutil.disk_usage('/workspace').free
print(f'Available container disk: {free / 1024**3:.2f} GiB')
if free < 18 * 1024**3:
    raise SystemExit('Need 18 GiB free before isolated CUDA installation; no automatic deletion')
PY
uv python install 3.11.16
uv sync --project environments/gpu --locked --python 3.11.16 --extra deep --extra dev --no-cache
export PYTHONPATH="$PWD/src:$PWD/scripts"
/workspace/.venvs/paper2-gpu/bin/python - <<'PY'
import sys
import torch
import braindecode
assert sys.version_info[:2] == (3, 11)
assert torch.__version__ == '2.8.0+cu128'
assert braindecode.__version__ == '1.2.0'
print({'python':sys.version.split()[0], 'torch':torch.__version__,
       'cuda_available':torch.cuda.is_available(), 'devices':torch.cuda.device_count()})
PY
