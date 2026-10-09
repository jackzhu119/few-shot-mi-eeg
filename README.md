# Learning-Preserving Co-Adaptive Brain–Computer Interfaces

**面向神经控制学习能力保留的人机协同自适应脑机接口**

核心问题：**How should brain–computer interfaces adapt without compromising human neural skill acquisition?**

本项目从新建空仓库开始，当前阶段建立可复现的离线 EEG 科研基础。仓库名称
`few-shot-mi-eeg` 不限定科学问题为 few-shot 分类，也不代表已提出或验证新算法。

## 科学边界

区分解码器参数自适应、EEG 表征漂移、人类神经控制学习和行为表现。
离线分类准确率、PCA 子空间距离、协方差变化都不能单独证明人类学习或技能保持。
固定模型的跨会话 EEG 分类性能是 **fixed-reference decoding performance**，
不能直接称为在线无辅助独立控制能力。合成数据输出仅用于软件正确性验证。

## 当前基础

- 多受试者、多会话、显式采样率/通道的数据接口，以及不使用 pickle 的 NPZ 读写。
- 每 epoch 的平均参考与带通处理，FFT、Welch PSD、Mu/Beta bandpower、空间协方差。
- 训练分区拟合的 PCA、共同通道坐标中的子空间及协方差距离。
- MNE CSP + scikit-learn LDA；Braindecode 官方 EEGNet 的 CPU 基线封装。
- 受试者/会话隔离与固定参考会话解码评估；参与者级配对统计。
- 随机种子、配置、依赖版本、源码 commit 和逐受试者结果日志。

具体已运行检查及版本见 [环境报告](research_logs/environment.json) 和
[验证记录](research_logs/validation.md)。真实数据适配器、完整 EEGNet 训练、候选协同自适应
方法以及在线人体实验仍须通过 [路线图](ROADMAP.md) 的相应阶段。

## 安装与验证

当前冻结目标为 Python **3.11.16**，Linux x86_64，CPU PyTorch。
`pyproject.toml` 声明直接依赖，`uv.lock` 冻结解析结果和下载校验信息。
先安装可用的 [uv](https://docs.astral.sh/uv/)；本机已提供 uv。

```bash
cd /workspace/few-shot-mi-eeg
bash scripts/setup_environment.sh
export UV_PROJECT_ENVIRONMENT=/workspace/.venvs/few-shot-mi-eeg
export UV_CACHE_DIR=/workspace/.cache/uv
export XDG_CACHE_HOME=/workspace/.cache
export MPLCONFIGDIR=/workspace/.cache/matplotlib
export MNE_DONTWRITE_HOME=true
uv run --locked --all-extras pytest -q
uv run --locked --all-extras python scripts/environment_report.py
uv run --locked --all-extras python scripts/smoke_experiment.py --config configs/smoke.json
uv run --locked --all-extras python scripts/check_data_stack.py
```

一般本地 checkout 会使用 `.venv`；脚本自动选择路径，也可通过 `BCI_ENV_DIR` 指定。
直接使用 `uv sync --locked` 可安装核心依赖；`--extra deep` 增加 EEGNet，
`--extra data` 增加 MOABB，`--extra dev` 增加测试工具。完整验证使用 `--all-extras`。
所有训练变换仅在训练分区拟合。烟雾实验不访问外部 EEG 数据、不需要 GPU。

## 结构与资料

```text
configs/                     完整软件验证配置
src/learning_preserving_bci/  datasets, preprocessing, signal_processing,
                             neural_geometry, decoders, adaptation, evaluation, utils
scripts/                     环境安装、实际环境报告、端到端软件验证
tests/                       数据/频谱/几何/划分/基线/统计/日志的自动化测试
docs/                        研究协议、数据可行性、文献核验、代码复用审计
experiments/ notebooks/      实验门槛与探索工作约定
research_logs/               小型可审计环境与验证记录
results/                     本地结果（除说明外不入 Git）
paper/                       写作范围与证据门槛
```

- [研究协议](docs/research_protocol.md)：可检验假设、控制、端点、泄漏防范与统计单位。
- [数据可行性](docs/dataset_feasibility.md)：SHU 与 NETBCI 官方来源、许可、字段与访问限制。
- [文献核验](docs/literature_review.md)：EEG、fMRI 与侵入式动物记录的迁移边界。
- [复用审计](docs/code_reuse_audit.md)：第一篇冻结 commit、核实的依赖与许可限制。

第一篇仓库只用于只读技术参考；不会复制第一篇结果为第二篇发现。
未确认旧源码授权前不迁入旧源码。本仓库尚未选择对外源码许可证；
依赖与数据遵守各自许可证，公开可访问不等于无条件可再分发。
数据、权重、密钥和大型产物由 `.gitignore` 排除。

## 下一步

先核实一个获准访问的小型真实数据子集，审计标签、时间单位、试次边界、参考、
通道顺序和反馈状态，冻结受试者/会话划分。随后开展预注册的跨会话频谱、协方差、
表征和固定解码实验。算法影响人类学习与 retention 的因果问题留待合适的前瞻性设计。
