# 同一Pod容器重建后的固定恢复方案：只准备，不调度fit

本方案由dot在审核本轮返回的固定方案提交后单独执行。本任务没有连接、恢复、重启或配置Pod，没有执行下面的安装、下载或GPU验收命令。下面各阶段独立验收，失败即停；本方案没有训练入口，也不创建第7fit预约。

## 已知状态和冻结身份

用户转述dot实际观察：Pod `52ivinpjwv947i` 的容器于2026-10-14 14:59:11 UTC从`b5646c12356b`变为`a7d3f0e408a4`；15:01:58 UTC只读核查`/workspace`仅`.cache`，overlay从30GiB变为50GiB。原因未核实，dot报告未Stop/Restart；这些是父侧观察，不是Codex独立检查新容器。旧路径、Python、uv、venv、数据、缓存、SSH安装均不能假定存在。不要通过重启、修改镜像、删除文件或增加算力来执行此恢复。

科学源码与验收状态固定于`b2e3f2b6378faacd7296c9e769f9f91a4d276d4c`，tree=`18d9c7faa64295dadb6562cb3cedcd319945c4c9`。前6fit原包及证据已离机并完整R2 GET验收；恢复这一固定Git状态即可保留连续6项账本，无需恢复六个模型权重或重新训练。账本SHA256=`73ef4a1489c9ac1df8b148a55edc616e3e6988ecbff1bcb32154ac0c505e0971`。第7fit从未执行或创建预约；唯一下一项为`sub-7 / seed20261012`，job=`735d0b78575ffe08b0be4e51a26fcadaa0a2db1977c9120d1e837e3ed48d03d7`。

本次50GiB等新事件单独保存在恢复清单，**不改**旧科学config中的30GiB历史观察、预算、线程、种子、容差、query/formal关闭状态或失败证据。仅既有公开HTTPS和已认证browser/Jupyter通路；不安装SSH、不添加密钥、不创建或复制凭据，不延长旧授权截止`2026-10-16 09:54 UTC`。

## 版本化材料

本轮固定方案提交中的`research_logs/kumar_pod_rebuild_recovery_20261014/`包含：

- `recovery_plan.json`：事件来源、保留账本、下一job、路径和验收边界。
- `frozen_source_manifest.json`：149个必要源码/配置/验收依赖的完整字节身份，包括22个adapter数值身份元数据文件。
- `frozen_inputs_127.json`：全部127文件的路径、长度、历史SHA256、官方checksum、官方HTTPS URL及已有R2键。
- `runtime_inventory.json`：旧fit实际记录、原GPU lock、恢复工具pin和91个Linux/Python3.11目标依赖版本。
- `cache_recovery_checklist.json`：必要输入/元数据和可重建缓存的逐项处置。
- `plan_payload_sha256.json`：上述五份清单和本文的递送身份；其他本地核查回执是准备证据。

dot从**本轮返回的固定方案提交**经GitHub HTTPS/browser取回这些文件，清单五件放在新的`/workspace/paper2-recovery-plan-20261014`，核对完整字节SHA256与`plan_payload_sha256.json`。不要从移动分支取材料。该方案提交与下文科学源码固定提交分别记录，不能把提交相同当作环境已恢复。

## 1. 发现新容器实际状态

仅由dot通过已有browser/Jupyter终端运行。先记录下面只读输出，缺少工具或硬件状态有冲突则停止，不启动任何安装或任务：

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
hostname
uname -a
cat /etc/os-release
df -B1 /workspace
ls -la /workspace
command -v git
command -v python3
python3 --version
command -v uv || true
command -v nvidia-smi || true
```

只核查列出的工具和路径，不打印环境变量全集、token、Jupyter URL或授权内容。`.cache`保留原样；不能用其存在推断旧源码、运行时或输入已恢复。旧驱动/GPU为父侧历史报告RTX A4500/580.159.04，新容器须另测。若浏览器通路、git或基础python3不可用，保留该事实并由dot处理，不引入SSH或新凭据。

## 2. 恢复固定源码与账本

以下变量只定义目标，**不表示路径已经存在**。已有同名路径先停下核对，不reset、覆盖、删除或重新初始化它。源码目录沿用原名称以便识别，但重新从固定Git身份获取；数据和venv路径必须与未改写入口默认值一致。

```bash
set -euo pipefail
set -C
PAPER2_SOURCE_COMMIT=b2e3f2b6378faacd7296c9e769f9f91a4d276d4c
PAPER2_CHECKOUT=/workspace/paper2-90f674f
PAPER2_PLAN_DIR=/workspace/paper2-recovery-plan-20261014
PAPER2_RECOVERY_RECEIPTS=/workspace/paper2-recovery-receipts-20261014-run01
PAPER2_TOOL_DIR=/workspace/paper2-recovery-tools-20261014
PAPER2_PYTHON=/workspace/.venvs/paper2-gpu/bin/python
PAPER2_DATA_ROOT=/workspace/paper2-data/kumar
PAPER2_INPUT_RECEIPT=/workspace/paper2-results/https-development-download-run01.json
: "${PAPER2_PAYLOAD_SHA256:?先将本轮固定交付回执中的完整payload SHA256设置为此变量}"
python3 -B - "$PAPER2_PLAN_DIR" "$PAPER2_PAYLOAD_SHA256" <<'PY'
import hashlib, json, sys
from pathlib import Path
directory = Path(sys.argv[1])
raw = (directory / 'plan_payload_sha256.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == sys.argv[2]
payload = json.loads(raw)
assert len(payload['files']) == 5
assert len({item['filename'] for item in payload['files']}) == 5
for item in payload['files']:
    assert Path(item['filename']).name == item['filename']
    path = directory / item['filename']
    assert path.stat().st_size == item['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
print(json.dumps({'status': 'five_plan_files_full_bytes_verified', 'payload_sha256': sys.argv[2]}))
PY
test ! -e "$PAPER2_CHECKOUT"
test ! -e "$PAPER2_RECOVERY_RECEIPTS"
test -d "$PAPER2_PLAN_DIR"
export GIT_TERMINAL_PROMPT=0
git -c credential.helper= clone --no-checkout -- \
  https://github.com/jackzhu119/few-shot-mi-eeg.git "$PAPER2_CHECKOUT"
git -C "$PAPER2_CHECKOUT" -c credential.helper= fetch origin "$PAPER2_SOURCE_COMMIT"
git -C "$PAPER2_CHECKOUT" checkout --detach "$PAPER2_SOURCE_COMMIT"
mkdir "$PAPER2_RECOVERY_RECEIPTS"
cd "$PAPER2_CHECKOUT"
python3 -B - "$PAPER2_PLAN_DIR/frozen_source_manifest.json" <<'PY' \
  > "$PAPER2_RECOVERY_RECEIPTS/source_acceptance.json"
import hashlib, json, subprocess, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_bytes())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == manifest['source_commit']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}']).decode().strip() == manifest['source_tree']
assert not subprocess.check_output(['git', 'status', '--porcelain'])
for item in manifest['required_files']:
    path = Path(item['path'])
    assert path.is_file() and path.stat().st_size == item['bytes'], item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], item['path']
ledger = json.loads(Path('research_logs/kumar_development_queue_20261014/accepted_jobs.json').read_bytes())
assert len(ledger['accepted_jobs']) == 6
next_output = Path(manifest['next_job']['output'])
assert not next_output.exists() and not next_output.with_suffix('.tar').exists()
print(json.dumps({'status': 'fixed_source_and_six_entry_ledger_verified',
                  'commit': manifest['source_commit'], 'source_files': len(manifest['required_files']),
                  'accepted_jobs': 6, 'next_reservation_absent': True, 'fit_executed': False}))
PY
```

22个adapter元数据共14,862,631bytes：冻结protocol、官方selection manifest、`source_events.json`、split manifest及18个源run数值身份JSON。它们是Git内既有审计证据；完整固定checkout恢复它们，不能用旧临时NPZ替代。

## 3. 精确安装配方与非拟合runtime验收

旧fit6实际记录Python3.11.16、NumPy2.2.6、SciPy1.15.3、scikit-learn1.7.2、MNE1.10.2、Torch/TorchAudio2.8.0+cu128、Braindecode1.2.0；MOABB未安装。旧平台为Linux6.8.0-134-generic/x86_64/glibc2.39。原GPU lock105项包含未选extras；`deep+dev`在Linux/Python3.11选中91项，不添加`data` extra，不复用系统Torch。

原GPU lock SHA256=`11682d951fe204e32859da12d9cc0ac73c6e63c1bce061d9834f8f68ebfe72e0`；原GPU pyproject SHA256=`90a3d349023ef448f731990abcad5f3015be3f84ad338be4473d2ef790550089`；原安装脚本SHA256=`868c5a3fe63e29fab8920fccd67c1b8d1303ecd63bcd58b831a17fc26746bcf0`。安装前必须至少18GiB空闲，恢复后至少5GiB；50GiB为父侧报告的总容量，不能代替实际剩余空间。

旧Pod uv版本、image digest、Python build hash及完整实际安装包清单未记录；不得补造。恢复工具固定uv0.12.19，来源为既有Codex resolver，**不是声称旧Pod曾用该版本**。本轮实际查询官方PyPI元数据取得Linux x86_64 wheel URL/长度/hash，仅作为递送身份。若现有uv正好为该版本，dot记录其路径、版本和文件hash后可复用；否则只在新工具目录提取这个固定wheel，不升级系统或安装shell bootstrap代码：

```bash
test ! -e "$PAPER2_TOOL_DIR"
python3 -B - "$PAPER2_PLAN_DIR/runtime_inventory.json" "$PAPER2_TOOL_DIR" <<'PY' \
  > "$PAPER2_RECOVERY_RECEIPTS/uv_bootstrap_run01.json"
import hashlib, json, os, sys, urllib.request, zipfile
from pathlib import Path
spec = json.loads(Path(sys.argv[1]).read_bytes())['recovery_tool_pin']['wheel']
target = Path(sys.argv[2])
target.mkdir(exist_ok=False)
wheel = target / spec['filename']
partial = wheel.with_name(wheel.name + '.partial')
count = 0
digest = hashlib.sha256()
with urllib.request.urlopen(spec['url'], timeout=60) as response, partial.open('xb') as out:
    assert response.status == 200
    while True:
        block = response.read(128 * 1024)
        if not block:
            break
        count += len(block)
        assert count <= spec['bytes']
        digest.update(block)
        out.write(block)
    out.flush()
    os.fsync(out.fileno())
assert count == spec['bytes'] and digest.hexdigest() == spec['sha256']
os.link(partial, wheel)
partial.unlink()
with zipfile.ZipFile(wheel) as archive:
    matches = [name for name in archive.namelist() if name.endswith('.data/scripts/uv')]
    assert len(matches) == 1
    binary = archive.read(matches[0])
with (target / 'uv').open('xb') as out:
    out.write(binary)
(target / 'uv').chmod(0o755)
print(json.dumps({'wheel_bytes': count, 'wheel_sha256': digest.hexdigest(),
                  'uv_binary_sha256': hashlib.sha256(binary).hexdigest()}))
PY
export PATH="$PAPER2_TOOL_DIR:$PATH"
uv --version
```

仅从上述固定官方wheel安装工具，一次请求；下载/长度/hash/布局失败保留`.partial`和目录并停止，不自动换版本、重试或删除。若复用已有同版uv，则不执行这段下载提取，使用已记录的工具路径。两种方式均先确认`uv --version`精确为0.12.19。

原安装脚本仅安装Python3.11.16与原GPU lock的`deep+dev`，末尾只查CUDA可用性，不构造模型或训练。首次新venv安装前确认它和管理Python目标未被其他任务占用；已存在的venv先停止核对，不用sync覆盖其他实验环境。沿用原launcher的三个数值设置，**没有新增MKL覆盖或Torch线程重设**：

```bash
python3 -B - <<'PY' > "$PAPER2_RECOVERY_RECEIPTS/uv_tool_acceptance.json"
import hashlib, json, shutil, subprocess
from pathlib import Path
tool = Path(shutil.which('uv')).resolve()
version = subprocess.check_output([str(tool), '--version'], text=True).strip()
assert version.split()[:2] == ['uv', '0.12.19'], version
print(json.dumps({'version_output': version, 'tool_path': str(tool),
                  'binary_sha256': hashlib.sha256(tool.read_bytes()).hexdigest()}))
PY
test ! -e /workspace/.venvs/paper2-gpu
test ! -e /workspace/.python-paper2
export PYTHONPATH="$PWD/src:$PWD/scripts"
export XDG_CACHE_HOME=/workspace/.cache-paper2
export MPLCONFIGDIR=/workspace/.cache-paper2/matplotlib
export MNE_DONTWRITE_HOME=true
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
bash scripts/setup_paper2_gpu.sh \
  > "$PAPER2_RECOVERY_RECEIPTS/install_run01.log" 2>&1
uv --version > "$PAPER2_RECOVERY_RECEIPTS/uv_version.txt"
"$PAPER2_PYTHON" -B - "$PAPER2_PLAN_DIR/runtime_inventory.json" <<'PY' \
  > "$PAPER2_RECOVERY_RECEIPTS/runtime_acceptance.json"
import hashlib, importlib, importlib.metadata as md, json, os, platform, shutil, sys
from pathlib import Path
spec = json.loads(Path(sys.argv[1]).read_bytes())
assert platform.python_version() == '3.11.16' and platform.machine() == 'x86_64'
versions = {name: md.version(name) for name in spec['target_environment']['linux_x86_64_python311_selected_versions']}
assert versions == spec['target_environment']['linux_x86_64_python311_selected_versions']
try:
    md.version('moabb')
except md.PackageNotFoundError:
    pass
else:
    raise RuntimeError('Unexpected data extra; preserve environment and stop')
for name in ['numpy', 'scipy', 'sklearn', 'mne', 'torch', 'torchaudio', 'braindecode']:
    importlib.import_module(name)
import torch
assert torch.__version__ == '2.8.0+cu128' and torch.version.cuda == '12.8'
assert {name: os.environ.get(name) for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'CUBLAS_WORKSPACE_CONFIG']} == {
    'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}
assert torch.get_num_threads() == 1
assert shutil.disk_usage('/workspace').free >= 5 * 1024**3
actual_platform = platform.platform()
print(json.dumps({'status': 'locked_runtime_packages_verified', 'python': platform.python_version(),
                  'python_executable_sha256': hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
                  'platform': actual_platform, 'historical_platform': spec['scientific_runtime_observed_in_old_fit6']['platform'],
                  'platform_matches_historical': actual_platform == spec['scientific_runtime_observed_in_old_fit6']['platform'],
                  'packages': versions, 'torch_threads': torch.get_num_threads(),
                  'fit_executed': False, 'GPU_forward_executed': False}))
PY
nvidia-smi --query-gpu=name,driver_version,memory.total \
  --format=csv,noheader,nounits > "$PAPER2_RECOVERY_RECEIPTS/GPU_driver.txt"
nvidia-smi --query-compute-apps=pid \
  --format=csv,noheader,nounits > "$PAPER2_RECOVERY_RECEIPTS/GPU_compute_PIDs.txt"
"$PAPER2_PYTHON" -B - <<'PY' > "$PAPER2_RECOVERY_RECEIPTS/CUDA_capability.json"
import json, torch
assert torch.cuda.is_available() and torch.cuda.device_count() == 1
print(json.dumps({'cuda_build': torch.version.cuda, 'cuda_available': True,
                  'device_count': torch.cuda.device_count(), 'GPU_forward_executed': False}))
PY
```

dot对照旧RTX A4500/580.159.04/20470MiB及平台实际报告；差异先停下审核，不能把包版本通过当作旧环境完全复现，也不能自动改驱动/镜像/config或数值设置。GPU忙则由dot协调两篇，恢复验收不启动CUDA计算或占用fit锁。`environment_report.py`要求GPU旧环境没有的MOABB，`--software-check`包含synthetic fit，因此本方案均不调用；不重复先前全套pytest或synthetic模型检查。

## 4. 恢复127输入和可重建缓存

冻结输入是18个源`ses-0/run-0..2` EDF（98,642,480bytes）+109元数据（101,012bytes），共98,743,492bytes；每人21项另加dataset_description。所有6会话的36份scans.tsv保留，adapter会核查scans，但在EDF读取前按源TRAIN/validation角色过滤。不得恢复CSP247文件/42EDF方案、support/query/final EEG、MIND或累计R2目录。

官方固定HTTPS manifest SHA256=`10aa69b50a935587fcdaa38e4eb7424f7d3d92ab650f07f851a5083f000aaa1f`；R2映射SHA256=`b8dd6c8872f03a661b34d50fb826ef05e88e5502e9987290fec1301a4cb85363`。既有R2键仅用于身份核对；本方案不向Pod复制R2凭据、不签发新capability或猜URL。使用原公开官方HTTPS下载器即可恢复。若官方通路失败则保存诊断，由dot另行安排已认证browser传递相同冻结字节，不切换范围或创建秘密。

先plan-only，确认范围；再由dot执行一次下载（仅输入、不是fit），超时/失败停止：

```bash
"$PAPER2_PYTHON" -B scripts/fetch_kumar_development_queue_https.py \
  --data-root "$PAPER2_DATA_ROOT" --receipt "$PAPER2_INPUT_RECEIPT"
timeout --signal=TERM --kill-after=30s 1800s \
  "$PAPER2_PYTHON" -B scripts/fetch_kumar_development_queue_https.py \
  --data-root "$PAPER2_DATA_ROOT" --receipt "$PAPER2_INPUT_RECEIPT" --execute \
  > "$PAPER2_RECOVERY_RECEIPTS/input_restore_run01.log" 2>&1
"$PAPER2_PYTHON" -B - "$PAPER2_DATA_ROOT" "$PAPER2_INPUT_RECEIPT" <<'PY' \
  > "$PAPER2_RECOVERY_RECEIPTS/input_acceptance.json"
import hashlib, json, sys
from pathlib import Path
from fetch_kumar_development_queue_https import load_plan, verify_all
root, receipt = Path(sys.argv[1]), Path(sys.argv[2])
verify_all(root, receipt)
plan = load_plan()
print(json.dumps({'status': 'restored_127_full_bytes_verified', 'files': len(plan['files']),
                  'bytes': sum(item['size'] for item in plan['files']),
                  'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
                  'query_rows_loaded': 0, 'EEG_adapter_or_fit_executed': False}))
PY
```

下载器单路、每文件一次、先元数据后EDF，CC-BY-4.0/v1.0.5核验；保留至少输入总量+2GiB空闲。现有文件仅在完整长度/官方checksum/历史SHA同时一致时复用；冲突、`.partial`或失败收据均保留并停止。已有完整127收据仍重新验全部文件。旧第6外层输入收据26878bytes/SHA=`ee7b880edb2f9c7a1decd4f164fd815e92801222b6787852774c61eb429756e4`是历史证据，不能直接冒充新容器验收。

`.cache-paper2`的XDG/MNE/matplotlib和Python bytecode为可重新生成缓存，不含决策/模型状态；旧`.cache`不删除，不据缓存猜版本。原setup采用`--no-cache`安装锁定包；原Python/venv路径按精确版本重建。旧六个权重、optimizer、processed epochs/NPZ不需要恢复或重算来接续账本。共享GPU锁由原调度入口在实际调度时获取，不把旧锁文件视为模型状态。

## 5. 最终只读队列门控与交回dot

完成上述独立验收后，仅运行纯`check_gate()`，不要运行launcher、`--execute-next`、重放模型、EDF adapter或任何`.fit_source()`：

```bash
"$PAPER2_PYTHON" -B - <<'PY' > "$PAPER2_RECOVERY_RECEIPTS/queue_gate_acceptance.log"
import hashlib, json
from pathlib import Path
from run_kumar_development_queue import check_gate
runtime, plan, job = check_gate()
ledger_path = Path(runtime['accepted_jobs'])
assert hashlib.sha256(ledger_path.read_bytes()).hexdigest() == '73ef4a1489c9ac1df8b148a55edc616e3e6988ecbff1bcb32154ac0c505e0971'
accepted = json.loads(ledger_path.read_bytes())['accepted_jobs']
assert len(accepted) == 6
assert [item['job_id'] for item in accepted] == [item['job_id'] for item in plan['jobs'][:6]]
assert (job['subject'], job['seed'], job['job_id']) == ('sub-7', 20261012, '735d0b78575ffe08b0be4e51a26fcadaa0a2db1977c9120d1e837e3ed48d03d7')
assert not runtime['query_access'] and not runtime['formal_gate']
output = Path(job['output'])
assert not output.exists() and not output.with_suffix('.tar').exists()
print(json.dumps({'status': 'recovery_gate_passed_no_fit_dispatched', 'accepted_jobs': 6,
                  'next_job': job, 'query_access': False, 'formal_gate': False,
                  'fit_executed': False, 'reservation_created': False}))
PY
git status --short
sha256sum scripts/launch_kumar_development_next.sh scripts/run_kumar_development_queue.py
df -B1 /workspace
```

预期入口SHA保持`897018b23dd9e2a09fff60683c5c985ac42e5f2467384a17d515b597414f2285`（launcher）、`666324c630d51ca0308c1cc9bd44551f832991d07a541210b520b351e6a2df80`（runner），Git状态应为空。新验收输出保存在checkout之外，完整hash后经已有browser通路交回；保留安装/下载失败原日志，不含凭据。不得追加第7验收或伪造父确认。本方案验收结束仍只是恢复完成，由dot另行调度第7项；Pod不Stop/Terminate。
