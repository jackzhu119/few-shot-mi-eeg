# Learning-Preserving Co-Adaptive Brain–Computer Interfaces

**面向神经控制学习能力保留的人机协同自适应脑机接口**

核心问题：**How should brain–computer interfaces adapt without compromising human neural skill acquisition?**

本项目在现有科研分支上开展可复现的纵向 EEG 审计与探索性分析。仓库名称
`few-shot-mi-eeg` 不限定科学问题为 few-shot 分类，也不代表已提出或验证新算法。

## 2026-10-10 接续：十人队列

已沿用现有云端环境与 `research/learning-preserving-bci` 分支，完整读取旧聊天交接及其
状态快照后恢复相同的固定版本子集。十人信号审计已通过：40 会话、240 个 EDF、
7,577 条原始事件，其中 7,576 条满足完整 5 秒窗口，74 个通道的顺序跨人一致。
一条 2.968 秒 rest 事件保留在原始清单，按明确的
[分析窗口修订](docs/netbci_full_window_policy_20261010.md)排除出固定长度张量。
原始配置和失败记录保留；科学参数未重选，修订不称外部预注册。

最新队列证据和下一阶段门槛以[十人报告](docs/netbci_cohort_results_20261010.md)、
[统一执行配置](configs/netbci_cohort_full_windows_20261010.json)及
[接续日志](research_logs/netbci_cohort_resume_20261010/)为准。
下文单人记录保留为历史先导阶段，不能与新队列拼接计算。

完整数值身份审计发现 sub-7 前三个会话与 sub-1 第四会话的六个对应 run 信号相同；
文件校验通过不保证采集独立。原十身份统计保留为算术结果，另有排除两个受影响身份的
八身份敏感性分析，不能把原区间直接用于论文的人群结论。
2026-10-11 接续将扩展公开数据并保存至已验证的 Cloudflare R2；
[存储记录](docs/r2_research_storage.md)区分对象核对与完整读取校验。

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
[验证记录](research_logs/validation.md)。已完成 NETBCI2026 前十人的真实 EEG 访问、
MNE 读取检查及本地数据适配器验收；完整 EEGNet 训练、候选协同自适应方法以及在线人体实验
仍须通过 [路线图](ROADMAP.md) 的相应阶段。

## 数据接入优先级与实际验收

1. **NETBCI2026 / NEMAR `nm000305` 为第一优先级。**
   [官方入口](https://www.nemar.org/dataset/nm000305)、
   [可达下载 API](https://data.nemar.org/nm000305/)，固定公开快照 **v1.0.0**，
   DOI [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)，
   数据许可 **CC BY 4.0**。公开目录支持按文件/受试者下载。历史首次访问仅下载 `sub-1` 的
   24 个 EDF（4 个 session × 6 个 run）及配套元数据，169 个文件共 **193,462,298 bytes**；
   校验和全部与官方 manifest 匹配。MNE 实读为 **74 EEG 通道、250 Hz**，
   事件为 **右手运动想象 vs 休息**，四个 session 分别 **180 / 179 / 180 / 178 trials**，
   合计 **717 trials**。随后扩展为公开编号前十人：**1,885 个去重文件、2,049,560,417 bytes**，
   官方校验全部通过。新协议重新分析十人，旧单人 3 epoch CPU EEGNet 只保留为最小软件验证。
2. **SHU / Ma2022 为第二优先级，原始接入状态 `pending author access`。**
   NEMAR `nm000288` publication pending；不继续请求该接口，不尝试破解 ZIP。
   保留左右手 MI、五日 session 的研究计划与通用数据接口。调整优先级前读取的
   Figshare v1 单受试者文件保留为历史探针，不作为 SHU 接入验收完成的依据。

NEMAR NETBCI 是经 MOABB 转换的 **EDF/BIDS derivative**，与原始 Dataverse
[10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7) v2.2 的 BrainVision/MEG/行为侧表
必须分开记录。实际事件表是 `rest=1, right_hand=2`，与 NEMAR README 中的示例数字
映射相反；按真实 `trial_type` 与 EDF annotation 验证，不能硬编码 README 的数字。
`onset/duration` 为秒、`sample` 从 0 起，已按实际采样率与信号边界核验。
NEMAR 参与者表没有行为成绩；原始官方侧表提供每 session 的六个 run 命中率，
原始 sub-01 的 24 run 事件对应及十人的 240 个原始头文件来源已验证；未实读其余九人的原始 BrainVision 信号或 marker。成绩向量的 run 顺序、评分分母、逐 trial 命中和光标轨迹仍需确认。在线反馈实验及 EEG 跨天变化
不能单独证明人类学习、保持或新算法的因果效果。

详细来源、差异和检查结果见 [数据可行性](docs/dataset_feasibility.md)、
[来源与校验收据](research_logs/netbci2026_sources/access_receipt.json)、
[真实读取审计](research_logs/netbci2026_subject1_audit.json) 和
[可执行核查 notebook](notebooks/netbci2026_access_check.ipynb)。
本地复核入口为 `python scripts/check_netbci_subset.py --help`；默认不下载整个数据集。

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

十人分析在同一新协议下重新运行，源端 ses-01/run-01–04 训练，run-05–06 为独立参考 query，
后续会话只评估冻结模型。已有行为按 subject/session 关联；具体 run/trial 研究仍待
评分分母、顺序和缺失原因验证。后续需专门验证测量可靠性、任务信息、伪迹/参考敏感性和
充分训练的 source-only baseline，再评估独立确认样本；SHU 保留 `pending author access`。
算法影响人类学习与 retention 的因果问题仍需前瞻性在线对照和独立保持探测。

## 历史单人先导证据（2026-10-10）

[完整审计、行为映射、Q1–Q7及下一步决策](docs/netbci_stage1_evidence_and_decision.md)；
[可执行分析](scripts/run_netbci_stage1.py)、[配置](configs/netbci_stage1.json)、
[已执行 notebook](notebooks/netbci2026_longitudinal_stage1.ipynb)。
仅1人717trial：会话几何差异可计算重放；CSP后续恒预测rest；短训练EEGNet只验流程。
行为subject/session可定位，run顺序/分母/trial outcome仍unresolved；不作人类学习因果结论。
论文工作稿与三篇原始方法精读见 manuscript/README.md（探索性工作稿，未达到投稿证据门槛）。

## 已有行为成绩的实际分析（2026-10-10）

[会话层行为—EEG报告](docs/netbci_behavior_session_analysis.md)已完成：原始19人×4会话×6成绩共456值，
均值54.11%→56.74%→62.15%→68.68%；末次−首次平均+14.57个百分点，配对受试者bootstrap
95%区间[10.71,18.27]，属于观察性行为变化。该历史阶段仅sub-1有已读EEG，四行会话级join已完成；十人队列另行汇总。
Mu任务差异与冻结解码结果已分别对照、计数/QC敏感性和精确重放已保存；不作学习因果或算法保留结论。
可运行入口为[分析脚本](scripts/analyze_netbci_behavior_sessions.py)、[配置](configs/netbci_behavior_sessions.json)
和[已执行notebook](notebooks/netbci2026_behavior_sessions.ipynb)。没有新增信号下载或模型拟合。
