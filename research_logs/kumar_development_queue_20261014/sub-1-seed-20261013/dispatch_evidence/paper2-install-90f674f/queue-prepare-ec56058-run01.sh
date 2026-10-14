#!/usr/bin/env bash
set -euo pipefail
test ! -e /workspace/paper2-install-90f674f/queue-prepare-ec56058-run01.log
exec > >(tee /workspace/paper2-install-90f674f/queue-prepare-ec56058-run01.log) 2>&1
trap 'r=$?; echo PREPARATION_EXIT_CODE=$r; date -u +END=%Y-%m-%dT%H:%M:%SZ' EXIT
date -u +START=%Y-%m-%dT%H:%M:%SZ
cd /workspace/paper2-90f674f
test -z "$(git status --porcelain)"
test ! -e /workspace/paper2-results/https-development-download-run01.json
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)"
flock -n /workspace/research-gpu.lock -c true
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1
git -c credential.helper= -c core.hooksPath=/dev/null fetch --depth=1 https://github.com/jackzhu119/few-shot-mi-eeg.git ec56058dc4d2716330db052aec6036cc845b39ba
git -c core.hooksPath=/dev/null checkout --detach ec56058dc4d2716330db052aec6036cc845b39ba
test "$(git rev-parse HEAD)" = ec56058dc4d2716330db052aec6036cc845b39ba
test -z "$(git status --porcelain)"
test "$(git hash-object research_logs/kumar_development_queue_20261014/delivery_hashes.json)" = fd05770256b9db004becb12389d278e12d59714d
git diff --exit-code 30e68e3dcdd2e2217e9c51bbdd84a6af4e568640 HEAD -- src scripts/train_kumar_eegnet.py scripts/replay_kumar_first_fit.py configs/kumar_eegnet_gpu_development_20261014.json configs/kumar_cross_session_20261012.json research_logs/kumar_cross_session_20261012/protocol/split_manifest.json
export PYTHONPATH="$PWD/src:$PWD/scripts"
/workspace/.venvs/paper2-gpu/bin/python -c 'exec("from pathlib import Path\nimport hashlib,json,shutil\np=Path(\"research_logs/kumar_development_queue_20261014/delivery_hashes.json\")\nm=json.loads(p.read_text())\nassert len(m)==7\nfor name,want in m.items():\n assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==want,name\nprint(\"DELIVERY_SHA256_ALL_7_PASS\")\nassert shutil.disk_usage(\"/workspace\").free>6*1024**3\nfrom run_kumar_development_queue import check_gate\nr,plan,j=check_gate()\nassert (j[\"subject\"],j[\"seed\"],j[\"job_id\"])==(\"sub-1\",20261013,\"5be2fc9499d4ec3916e5191c822c205e195c0e25655c39ec0f84e5aa2c091470\")\nassert not Path(j[\"output\"]).exists() and not Path(j[\"output\"]).with_suffix(\".tar\").exists()\nprint(json.dumps({\"NEXT_JOB\":j,\"query_access\":False,\"fit_started\":False}))\n")'
echo SOURCE_DOWNLOAD_START
timeout --signal=TERM --kill-after=30s 1800s /workspace/.venvs/paper2-gpu/bin/python scripts/fetch_kumar_development_queue_https.py --data-root /workspace/paper2-data/kumar --receipt /workspace/paper2-results/https-development-download-run01.json --execute
/workspace/.venvs/paper2-gpu/bin/python -c 'from pathlib import Path; from fetch_kumar_development_queue_https import verify_all; verify_all(Path("/workspace/paper2-data/kumar"),Path("/workspace/paper2-results/https-development-download-run01.json")); print("ALL_127_VERIFIED_NO_FIT_YET")'
df -B1 /workspace
