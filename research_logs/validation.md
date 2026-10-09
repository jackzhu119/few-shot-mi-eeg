# Phase 0 验证记录

执行日期：2026-10-09（Asia/Shanghai）。本记录对应科研实现 commit
`2e1f785285de4b23560ffe3c203a4d25f61d9f85`，不是文档记录提交的自引用 SHA。
默认分支初始化 commit 为 `78ca1a2173c2ce43b9b6f80ee1b177c311b51739`；
完整代码位于 `research/learning-preserving-bci`。GitHub 最终分支 HEAD 以推送后重新读取结果为准。

## 实际验证结果

| 检查 | 本轮结果 |
| --- | --- |
| Python 3.11.16 独立环境、`uv sync --locked --all-extras` | 成功；独立于系统 Python 3.12.14 |
| 再执行 `bash scripts/setup_environment.sh` | 成功复用安装；源码和 uv.lock 未被安装改变 |
| `uv pip check` / 指定依赖 import | 成功；实际版本见 `environment.json` |
| `python -m pytest -q --junitxml=/tmp/bci-pytest.xml` | **99 passed, 0 failures, 0 errors, 0 skipped**；2 条上游弃用警告 |
| `ruff check src tests scripts` | 通过 |
| wheel build + frozen-hash base dependencies + 独立 wheel venv | 通过；从 `/tmp` 运行，未使用 editable checkout 导入 |
| 未安装 deep/data extras 的 wheel 合成完整流程 | 通过；基础包不隐式依赖 Torch/Braindecode/MOABB |
| MNE + MOABB `FakeDataset` → `MotorImagery.get_data` | 20 个合成 epochs、3 通道、2 sessions；没有下载公共 EEG |
| 合成 EEG preprocessing → spectra/covariance/PCA → fixed CSP+LDA | 3 模拟受试者 × 2 held-out sessions，完成6条评估记录 |
| clean source commit、试次索引、配置与源码哈希 | 已核对，训练/测试索引无交集、标签与预测一一对应 |

EEGNet 测试实际执行 Braindecode 官方模型的 CPU 前向、一个小训练 epoch、概率输出、
推理前后完整 state 不变，以及相同 seed 的训练输出一致。它不是大规模 EEGNet 训练，
也不说明真实 EEG 上的有效性。统计测试验证参与者配对、顺序不变性和 CI/置换结果；
受试者标识字符串碰撞会明确拒绝。随机 decoder 的评估实际固定随机状态。

2 条 warning 来自 Braindecode 1.2.0 的 `final_layer_with_constraint` 参数弃用；
没有跳过 EEGNet 测试，也没有关闭包签名、下载哈希或 TLS 验证。

## 实际命令与工作目录

安装与完整验证在 `/workspace/few-shot-mi-eeg`：

```bash
bash scripts/setup_environment.sh
export UV_PROJECT_ENVIRONMENT=/workspace/.venvs/few-shot-mi-eeg
export UV_CACHE_DIR=/workspace/.cache/uv
export XDG_CACHE_HOME=/workspace/.cache
export MPLCONFIGDIR=/workspace/.cache/matplotlib
export MNE_DONTWRITE_HOME=true
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
source /workspace/.venvs/few-shot-mi-eeg/bin/activate
python -m pytest -q --junitxml=/tmp/bci-pytest.xml
ruff check src tests scripts
python scripts/environment_report.py --output research_logs/environment.json
python scripts/check_data_stack.py
uv run --locked --all-extras python scripts/smoke_experiment.py --config configs/smoke.json --output results/validated-code/report.json
```

环境报告是本轮采集记录。后续运行应省略 `--output` 或指定新的结果路径，
不要覆写已提交的环境证据。同样，smoke 实验默认生成唯一结果目录；指定现有输出会拒绝覆盖。

wheel 验证在 `/tmp` 的独立 `/tmp/bci-wheel-env`；该环境先安装由 `uv export --locked
--no-emit-project --no-dev` 导出的 base requirements（`--require-hashes`），再以 `--no-deps`
安装本轮构建 wheel，运行同一 smoke script。完整轮和锁文件 SHA256 在 `validation.json`。
`synthetic_validation.json` 保存 clean-code smoke 的完整配置、逐模拟受试者/试次结果、
有效模型参数和源码哈希；其中分数全部是软件 fixture，不能用于论文真实结果。

## 初始化中已修复的问题

首次 GitHub 推送因 GH007 邮箱隐私保护被拒绝。通过官方账号 API 核实账号 ID 后，
仅修改本仓库 local email 为账号的 GitHub noreply 地址，保留原始历史备份，
重建尚未发布的三个提交；源码树逐字不变。新历史上重新执行99项测试与clean-source smoke
均通过。未关闭 GitHub 隐私保护，也未改全局 Git 身份。


- 默认 uv 缓存位于只读 home：改用 `/workspace/.cache/uv` 和独立工具目录。
- 最初 editable build 时 README 尚未创建：完成项目元数据后重建成功。
- MOABB synthetic provider 尝试写只读 `.mne`：使用 MNE 支持的
  `MNE_DONTWRITE_HOME=true`，其配置写入临时目录，不改写 `HOME`。
- 独立 review 发现配对 ID 排序歧义、seed 仅记录未实际设定、非 cloneable 模板
  可能继承已训练状态：全部修正并加回归断言。

这些是已修复的开发/环境问题。最终必需软件检查无失败。没有把仅语法检查或零测试运行
称为科研工作流验收。

## 未验证与仅规划范围

实际容器为 Debian 13，5 个可用 CPU，约33.3 GiB RAM；没有 NVIDIA device、
`nvidia-smi` 或可用 CUDA。Torch 是 `2.8.0+cpu`。没有创建付费资源。

本轮读取了官方小型元数据，但没有下载真实 EEG 信号、大 ZIP 或模型权重；
没有运行真实数据实验、完整 EEGNet 训练、GPU 计算、在线闭环、人类学习或 retention 实验。
SHU ZIP 密码与事件单位矛盾、NETBCI 大归档/实际事件、订阅论文主文、对外源码许可选择，
均保留明确未解决状态。原始数据 adapter、候选协同自适应优化、非线性 manifold 和
前瞻人体实验属于后续阶段。

本机运行验证、云环境配置草稿、GitHub 提交和产品中的环境发布是四个不同状态。
保存草稿不执行安装，也不证明新任务恢复已验证；环境发布由用户在产品中完成。
