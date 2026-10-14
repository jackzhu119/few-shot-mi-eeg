#!/usr/bin/env bash
set -euo pipefail
cd /workspace/paper2-90f674f
test "$(git rev-parse HEAD)" = ec56058dc4d2716330db052aec6036cc845b39ba
test -z "$(git status --porcelain)"
test ! -e /workspace/paper2-results/development-queue/sub-1/seed-20261013
test ! -e /workspace/paper2-results/development-queue/sub-1/seed-20261013.tar
test ! -e /workspace/paper2-install-90f674f/queue-sub1-seed20261013-dispatch-run01.log
exec > >(tee /workspace/paper2-install-90f674f/queue-sub1-seed20261013-dispatch-run01.log) 2>&1
trap 'r=$?; echo OUTER_EXIT_CODE=$r; date -u +END=%Y-%m-%dT%H:%M:%SZ' EXIT
date -u +START=%Y-%m-%dT%H:%M:%SZ
echo DISPATCH_PID=$$
ps -eo pid,ppid,comm | grep -E 'python|bash|timeout|curl|git'
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)"
flock -n /workspace/research-gpu.lock -c true
export PYTHONDONTWRITEBYTECODE=1
/workspace/.venvs/paper2-gpu/bin/python -c 'import shutil,json; from pathlib import Path; from collections import Counter; assert shutil.disk_usage("/workspace").free>6*1024**3; r=json.loads(Path("/workspace/paper2-results/https-development-download-run01.json").read_text()); assert r["status"]=="all_127_full_sha256_verified"; print("DOWNLOAD_RECEIPT",len(r["records"]),dict(Counter(x["status"] for x in r["records"])))'
bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup
