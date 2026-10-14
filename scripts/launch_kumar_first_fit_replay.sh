#!/usr/bin/env bash
# Parent schedules on the existing shared Pod. No fitting, networking or stop.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src:$PWD/scripts"
export XDG_CACHE_HOME=/workspace/.cache-paper2
export MPLCONFIGDIR=/workspace/.cache-paper2/matplotlib
export MNE_DONTWRITE_HOME=true
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
PAPER2_REPLAY=/workspace/paper2-results/kumar-first-fit-replay-run01
if [[ -e "$PAPER2_REPLAY" || -e "$PAPER2_REPLAY.log" || -e "$PAPER2_REPLAY.tar" ]]; then
  echo 'Replay evidence already exists; preserve and inspect, no automatic retry.' >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Require clean fixed checkout before replay.' >&2
  exit 1
fi
set +e
(
  set -o noclobber
  timeout --signal=TERM --kill-after=30s 600s /workspace/.venvs/paper2-gpu/bin/python     scripts/replay_kumar_first_fit.py     --data-root /workspace/paper2-data/kumar     --download-receipt /workspace/paper2-results/https-first-fit-download-run01.json     --fit-archive /workspace/paper2-results/kumar-sub1-seed20261012-parent-relay-run01.tar     --output "$PAPER2_REPLAY" > "$PAPER2_REPLAY.log" 2>&1
)
PAPER2_REPLAY_EXIT=$?
set -e
# Package both success and diagnostic evidence without editing the first-fit bundle.
PAPER2_REPLAY_EXIT="$PAPER2_REPLAY_EXIT" /workspace/.venvs/paper2-gpu/bin/python - <<'PY'
import hashlib, io, json, os, tarfile
from pathlib import Path
p = Path("/workspace/paper2-results/kumar-first-fit-replay-run01")
files = sorted(p.glob("*")) if p.exists() else []
files += [p.with_suffix(".log")]
entries = []
with p.with_suffix(".tar").open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as tar:
    for f in files:
        if not f.is_file() or f.is_symlink():
            raise ValueError("Unexpected replay evidence")
        value = f.read_bytes()
        if len(value) > 16 * 1024**2:
            raise ValueError("Replay evidence exceeds size bound")
        name = f.name
        info = tarfile.TarInfo(name)
        info.size = len(value)
        info.mode = 0o600
        tar.addfile(info, io.BytesIO(value))
        entries.append(dict(path=name, bytes=len(value), sha256=hashlib.sha256(value).hexdigest()))
    manifest = dict(files=entries, exit_code=int(os.environ["PAPER2_REPLAY_EXIT"]),
                    status="replay_finished_review_and_R2_backup_pending", fits=0,
                    R2_backup_verified=False, stop_Pod=False)
    value = (json.dumps(manifest, indent=2) + "\n").encode()
    info = tarfile.TarInfo("manifest.json")
    info.size = len(value)
    tar.addfile(info, io.BytesIO(value))
raw = p.with_suffix(".tar").read_bytes()
print(json.dumps(dict(archive=str(p.with_suffix(".tar")), bytes=len(raw),
                      sha256=hashlib.sha256(raw).hexdigest(),
                      exit_code=int(os.environ["PAPER2_REPLAY_EXIT"]))))
PY
exit "$PAPER2_REPLAY_EXIT"
