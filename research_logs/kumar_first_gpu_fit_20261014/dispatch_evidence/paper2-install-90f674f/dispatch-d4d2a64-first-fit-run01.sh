#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a /workspace/paper2-install-90f674f/dispatch-d4d2a64-first-fit-run01.log) 2>&1
trap 'r=$?; echo FIRST_FIT_DISPATCH_EXIT_CODE=$r; date -u +%Y-%m-%dT%H:%M:%SZ; df -B1 /workspace' EXIT
date -u +%Y-%m-%dT%H:%M:%SZ
cd /workspace/paper2-90f674f
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = 740326a6a8a2ac5a5cff8079403f8ec0abef688d
test ! -e /workspace/paper2-results/.kumar-first-fit-20261014.json
test ! -e /workspace/paper2-results/kumar-first-fit-launch-run01.log
test ! -e /workspace/paper2-results/kumar-sub1-seed20261012-parent-relay-run01
test ! -e /workspace/paper2-results/kumar-sub1-seed20261012-parent-relay-run01.tar
timeout --signal=TERM --kill-after=10s 120s git -c credential.helper= -c core.hooksPath=/dev/null fetch --depth=1 https://github.com/jackzhu119/few-shot-mi-eeg.git d4d2a64bb16e5f3841ecdefeb188fd8b9a121c71
git diff --exit-code 740326a6a8a2ac5a5cff8079403f8ec0abef688d FETCH_HEAD -- configs/kumar_eegnet_gpu_development_20261014.json configs/kumar_cross_session_20261012.json configs/kumar_first_fit_https_20261014.json scripts/train_kumar_eegnet.py scripts/fetch_kumar_first_fit_https.py src/learning_preserving_bci research_logs/kumar_cross_session_20261012/protocol/split_manifest.json
git -c credential.helper= -c core.hooksPath=/dev/null checkout --detach FETCH_HEAD
test "$(git rev-parse HEAD)" = d4d2a64bb16e5f3841ecdefeb188fd8b9a121c71
test "$(git hash-object scripts/launch_kumar_parent_first_fit.sh)" = 9f79aca5000958e63377f9e3492366d0ef96540d
test "$(git hash-object scripts/run_kumar_parent_first_fit.py)" = 43f98d4174501d4c85487d1cb809ea62988821d4
test "$(git hash-object configs/kumar_parent_relay_20261014.json)" = e4b71db174ddc04ef780e0bb99ea1e94b6a1d83a
printf '14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d  configs/kumar_eegnet_gpu_development_20261014.json\nbbdff282d3af9fb1b1e3062fb1459369b1e0c160903988d68c810c333b9ad19e  research_logs/checkpoint_relay_acceptance_20261014/r2_full_get_receipt.json\n' | sha256sum -c -
python3 -c 'import shutil; assert shutil.disk_usage("/workspace").free>=5*1024**3'
echo STARTING_EXACTLY_ONE_FROZEN_DEVELOPMENT_FIT
date -u +%Y-%m-%dT%H:%M:%SZ
set +e
bash scripts/launch_kumar_parent_first_fit.sh &
child=$!
echo LAUNCHER_PID=$child
sleep 2
ps -eo pid,ppid,comm | head -60
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
wait "$child"
rc=$?
set -e
echo SINGLE_LAUNCH_RETURN_CODE=$rc
exit "$rc"
