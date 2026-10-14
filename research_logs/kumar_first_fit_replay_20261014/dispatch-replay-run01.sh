#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a /workspace/paper2-install-90f674f/dispatch-replay-run01.log) 2>&1
trap 'r=$?; echo REPLAY_DISPATCH_EXIT_CODE=$r; date -u +%Y-%m-%dT%H:%M:%SZ; df -B1 /workspace' EXIT
date -u +%Y-%m-%dT%H:%M:%SZ
cd /workspace/paper2-90f674f
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = d4d2a64bb16e5f3841ecdefeb188fd8b9a121c71
test ! -e /workspace/paper2-results/kumar-first-fit-replay-run01
test ! -e /workspace/paper2-results/kumar-first-fit-replay-run01.log
test ! -e /workspace/paper2-results/kumar-first-fit-replay-run01.tar
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
timeout --signal=TERM --kill-after=10s 120s git -c credential.helper= -c core.hooksPath=/dev/null fetch --depth=1 https://github.com/jackzhu119/few-shot-mi-eeg.git 30e68e3dcdd2e2217e9c51bbdd84a6af4e568640
git diff --exit-code d4d2a64bb16e5f3841ecdefeb188fd8b9a121c71 FETCH_HEAD -- configs/kumar_eegnet_gpu_development_20261014.json configs/kumar_cross_session_20261012.json configs/kumar_first_fit_https_20261014.json scripts/train_kumar_eegnet.py scripts/run_kumar_parent_first_fit.py scripts/fetch_kumar_first_fit_https.py src/learning_preserving_bci research_logs/kumar_cross_session_20261012/protocol/split_manifest.json
git -c credential.helper= -c core.hooksPath=/dev/null checkout --detach FETCH_HEAD
test "$(git rev-parse HEAD)" = 30e68e3dcdd2e2217e9c51bbdd84a6af4e568640
test "$(git hash-object scripts/launch_kumar_first_fit_replay.sh)" = 5bf317593e90a1eba28f321157c7671937dbf655
test "$(git hash-object scripts/replay_kumar_first_fit.py)" = bd1ce27991f42f6829ef7cc6e8d1810aea41c30e
test "$(git hash-object scripts/audit_kumar_first_fit_bundle.py)" = 263be47dc2dd971dc1839b06370e2dc9c51ad2fb
test "$(git hash-object configs/kumar_first_fit_replay_20261014.json)" = 5c5ee8ae975b4f6be1606681f7739cc74219fff7
echo STARTING_SINGLE_SOURCE_VALIDATION_REPLAY_NO_FIT
date -u +%Y-%m-%dT%H:%M:%SZ
bash scripts/launch_kumar_first_fit_replay.sh
echo SINGLE_SOURCE_VALIDATION_REPLAY_ENDED_NO_FIT
