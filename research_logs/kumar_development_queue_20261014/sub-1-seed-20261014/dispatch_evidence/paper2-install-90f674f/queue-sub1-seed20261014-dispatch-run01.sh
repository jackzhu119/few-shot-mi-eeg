#!/usr/bin/env bash
set -euo pipefail
test ! -e /workspace/paper2-install-90f674f/queue-sub1-seed20261014-dispatch-run01.log
exec > >(tee /workspace/paper2-install-90f674f/queue-sub1-seed20261014-dispatch-run01.log) 2>&1
trap 'r=$?; echo OUTER_EXIT_CODE=$r; date -u +END=%Y-%m-%dT%H:%M:%SZ' EXIT
date -u +START=%Y-%m-%dT%H:%M:%SZ
echo DISPATCH_PID=$$
cd /workspace/paper2-90f674f
test -z "$(git status --porcelain)"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)"
flock -n /workspace/research-gpu.lock -c true
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1
git -c credential.helper= -c core.hooksPath=/dev/null fetch --depth=1 https://github.com/jackzhu119/few-shot-mi-eeg.git cc70f4274b7e14d9bd0e8d76d072aacf625bbf43
git -c core.hooksPath=/dev/null checkout --detach cc70f4274b7e14d9bd0e8d76d072aacf625bbf43
test "$(git rev-parse HEAD)" = cc70f4274b7e14d9bd0e8d76d072aacf625bbf43
test -z "$(git status --porcelain)"
git diff --exit-code ec56058dc4d2716330db052aec6036cc845b39ba HEAD -- src scripts configs research_logs/kumar_cross_session_20261012/protocol/split_manifest.json
test "$(git hash-object research_logs/kumar_development_queue_20261014/delivery_hashes.json)" = fd05770256b9db004becb12389d278e12d59714d
export PYTHONPATH="$PWD/src:$PWD/scripts"
/workspace/.venvs/paper2-gpu/bin/python -c 'exec("from pathlib import Path\nimport hashlib,json,shutil\nfrom run_kumar_development_queue import check_gate\nfrom fetch_kumar_development_queue_https import verify_all\nm=json.loads(Path(\"research_logs/kumar_development_queue_20261014/delivery_hashes.json\").read_text())\nassert len(m)==7\nfor p,h in m.items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p\nruntime,plan,j=check_gate()\nassert (j[\"subject\"],j[\"seed\"])==(\"sub-1\",20261014)\nassert not Path(j[\"output\"]).exists() and not Path(j[\"output\"]).with_suffix(\".tar\").exists()\nassert shutil.disk_usage(\"/workspace\").free>6*1024**3\nverify_all(Path(\"/workspace/paper2-data/kumar\"),Path(\"/workspace/paper2-results/https-development-download-run01.json\"))\nprint(\"ALL_7_DELIVERY_AND_127_CACHE_HASHES_PASS\")\nprint(json.dumps({\"next_job\":j,\"parent_confirmation_checked\":True,\"no_downloads\":True}))\n")'
bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup
