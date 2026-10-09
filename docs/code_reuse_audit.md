# 第一篇技术参考与复用审计

审计日期：2026-10-09。目标项目：**Learning-Preserving Co-Adaptive Brain–Computer Interfaces**。

本记录将“已读取的来源证据”“来源仓库的既有验证记录”和“本轮重新执行的检查”分开。第一篇只作为科研技术参考，其分类结果、模型权重、统计结论和神经生理描述均不是第二篇的新发现。

## 1. 访问范围与不可变来源

使用平台注入的 HTTPS Git 访问，执行 `git ls-remote` 和参考克隆。参考 checkout 位于 `/tmp/bci-reference/cross-subject-mi-eeg`；所有内容检查通过只读文件读取或 `git show <ref>:<path>` 完成。未向第一篇执行 commit、push、改写分支、标签或文件；未在其 checkout 运行会产生实验输出的脚本。该 checkout 是独立参考副本，第二篇不依赖它来安装或运行。

| 用途 | 检查到的精确 Git 身份 | 使用决定 |
| --- | --- | --- |
| 读取时的第一篇 `main` / `HEAD` | `fba2cf7d02e061357639f5689d34623f9edce964` | 仅了解最新公开入口，技术参考不跟随浮动 `main` |
| 冻结论文 `paper-v1.0.2` | tag object 为 `77d3b6cbc1b62d65624ed4d8771efcc8a36e4dca`，peeled commit 为 `b23480d996dd6c78e386686e1110e272decf166f` | 本审计主要可阅读快照；以下文件链接均固定到该 commit |
| 最新投稿材料 `plos-one-submission-v1.0` | `b99c119c080f30b6407bb9836e23e83e772d215e` | README 说明这是保留 Q1–Q16 的编辑发布，不是新科学训练 |
| Q15 科学代码 | `271af288a2f3863430ab80e3145c2dee9bd5571d` | 按冻结 README 和 reproducibility guide 追溯原训练/预测实现 |
| Q15 独立验证结果发布 | `bc48b257eb44f412ad069f50d0f1a72a33c3c520` | 原结果验证来源；未在本轮重跑 |
| Q16 原始功率计算前冻结 | `050e01b028aaab8e3d745934b13b2d17e9bb0a7a` | 原始生理估计协议和代码的冻结身份 |

原始入口：[冻结 README](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/README.md)、[冻结复现指南](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/research_runs/PAPER_FINAL_20261006/reproducibility_readme.md)、[PLOS 版本 README](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b99c119c080f30b6407bb9836e23e83e772d215e/README.md)。本轮读取 Git tags 与仓库内 publication receipts，没有独立下载 GitHub Release 的所有归档资产；标签存在不等于每个 release 资产均重新验证。

## 2. 已读取的技术实现与迁移决定

| 基础设施 | 已查看的固定来源 | 源实现与第二篇决定 |
| --- | --- | --- |
| EEGNet | [训练薄层](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/models/eegnet_training.py)、[Q15 source runner](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/scripts/q15_source.py) | 调用 Braindecode 的 EEGNet，随机种子在初始化/洗牌前设定，检查输出形状和有限 loss；预测使用 `eval()` / inference mode 避免目标数据改变 BatchNorm。第二篇独立编写标准库接口，并验证 CPU 前向/训练；不迁移旧 checkpoints、选定 epoch 或原结果。 |
| CSP + LDA | [早期 CSP baseline](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/scripts/run_csp_baselines.py)、[Q15 CAR 坐标](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/models/q15_csp.py) | 早期 baseline 使用 MNE CSP（4 components、log power、concat covariance）→训练折 StandardScaler→LDA。Q15 针对 21 通道 CAR 的 rank-20 空间使用固定 Helmert 基，不从目标数据估计。第二篇使用 MNE/sklearn 标准实现；组件数和参考策略属于新协议，不能盲拷贝 21×320 等 BNCI 专用限制。 |
| EEG 与元数据 | [BNCI epochs](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/data/bnci_epochs.py) | 校验频道顺序、事件映射、原生 250 Hz、run/session、专家伪迹标记；每 trial 保留 sample_id/subject/session/run/trial/label。第二篇采用通用多会话接口，新增 dataset 与明确 session chronology，数据集 adapter 必须按真实字段验证。 |
| 预处理 | [Q15 context](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/data/q15_context.py)、[外部数据协议](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/docs/external_dataset_protocol.md) | Q15 先选 21 通道、CAR，再在每个真实六秒 context 内做 native-rate 4th-order Butterworth 零相位滤波、polyphase 重采样至 160 Hz，裁取 cue [0.5,2.5) s。不会跨 Cho 人工拼接 trial 边界滤波。第二篇继承边界审计、反混叠和固定变换原则，另冻结适用参数；目标统计拟合须明确标注 adaptation，不能伪称 fixed decoder。 |
| Subject/session splitting | [split 实现](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/evaluation/splits.py)、[split 测试](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/tests/test_splits.py) | within-session 留整 run；cross-session 对同一人 `0train`→`1test`；LOSO 将目标人全部 session 留出。第二篇独立实现显式 subject/session-aware split，按提供的 chronological order 处理更多 session；不依赖字典序推断时间。 |
| 空间协方差与 PCA/geometry | [Q10 geometry](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/scripts/q10_geometry.py) | trial-wise covariance/log-Euclidean 特征，跨 trial 的 scaler/projection 在 source fold 内拟合。第二篇用 NumPy/SciPy/sklearn 实现 covariance/PCA/subspace 描述；传感器投影变化不能命名为已证实的 human neural learning，独立拟合 PCA 的坐标也不能直接相减。 |
| FFT / PSD / mu-beta | [Q16 protocol](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/research_runs/Q16-P001-BNCI-20261006/PROTOCOL.md)、[Q16 analysis](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/scripts/q16_bnci_analysis.py) | Q16 单独使用原生未额外滤波/参考信号；Welch periodic Hann、1 s segment、50% overlap、linear detrend、density scaling；积分 8–13 / 13–30 Hz。第二篇独立实现可配置 FFT/PSD/bandpower 并用已知频率合成信号验证；不能把 decoder 的滤波输入与生理估计混为同一表征。 |
| Experiment tracking | [provenance](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/provenance.py)、[reproducibility](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/src/mi_eeg/reproducibility.py) | 新 run 目录禁止覆盖旧证据，记录实际源码/配置 SHA-256、Python/package versions、命令与捕获时间。第二篇用标准库构建自己的 manifest，不把旧环境记录倒填到新运行，也不保存 credentials/env values。 |
| 统计 | [Q15 inference/statistics](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/scripts/q15_external.py)、[独立 Q15 validator](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/scripts/q15_validate_external.py) | 每 seed 每人 balanced accuracy 后先在人内合并，cohort 给参与者等权；participant bootstrap、paired sign-flip、预声明 Holm。第二篇新实现 participant-level 统计接口，必须显式配对 ID；不能把 trial、seed 或 session 当成独立参与者放大 n。旧 Lee protocol 的 session pooling 不适合直接研究纵向变化，第二篇保留 per-session 指标。 |

迁移方式是**协议和测试需求复用 + 独立标准库薄层实现**。没有把旧 `src/mi_eeg`、scripts、tests、配置、论文内容、结果表、模型权重或数据复制进第二篇；这一决定同时避免把来源数据专用限制和未确认的代码许可引入新项目。标准数学操作和上游库 API 的使用不意味着获得旧仓库自定义实现的再分发许可。

## 3. 依赖版本：声明、实际运行与新环境分开

[冻结 pyproject](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/pyproject.toml) 声明 `Python >=3.11`，并使用范围约束：NumPy >=2,<3；SciPy >=1.13,<2；MNE >=1.10,<2；MOABB >=1.4,<2；sklearn >=1.6,<2；deep extra 固定 Braindecode 1.5.1，Torch >=2.6,<3。版本范围本身不是一次运行的冻结环境。

| 软件 | Q15 已保存运行记录 | Q16 已保存运行记录 |
| --- | --- | --- |
| Python | 3.12.3 | 3.12.14 |
| NumPy | 2.5.3 | 2.3.5 |
| SciPy | 1.18.1 | 1.17.0 |
| scikit-learn | 1.9.1 | 未列在该 manifest 中 |
| MNE | 1.13.2 | 未列在该 manifest 中 |
| MOABB | 1.7.2 | 未列在该 manifest 中 |
| Braindecode | 1.5.1 | 未列在该 manifest 中 |
| Torch / TorchAudio | 2.8.0+cu128 / 2.8.0+cu128 | 未列在该 manifest 中 |
| pandas | Q15 所读 runtime block 未列出；requirements 为 3.0.6 | 2.2.3 |
| GPU / CUDA | 旧运行记录：NVIDIA RTX 4000 Ada Generation / CUDA runtime 12.8 | 该分析不声明 GPU 验证 |

Q15 精确记录：[source run_config](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/results/Q15-E005/source/run_config.json)、[Q15 requirements](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/requirements-q15-runtime.txt)。Q16 精确记录：[run_manifest](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/research_runs/Q16-P001-BNCI-20261006/run_manifest.json)。

`requirements-cloud.txt`、`requirements-paper-cu128.txt` 与 Q15/Q16 实际 manifest 不是同一版本集合，不能拼成一个“已验证依赖锁”。旧环境有 CUDA 不代表当前容器有 GPU；这些来源版本也没有在本轮逐一安装或验证其 Python 3.11 wheel 兼容性。第二篇以本机安装、import、CPU smoke test 和测试生成的环境报告为准，并保存自己的约束/锁。

## 4. 已有验证的证据覆盖

### 来源仓库已保存的验证记录

- [Q15 source_validation](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/results/Q15-E005/source_validation.json) 记录 `passed=true`，14 neural source fits + 1 shallow fit，`target_fits=0`；这是 source partition/artifact 验证，不单独授权或证明外部推断。
- [Q15 external validation_report](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/results/Q15-EXTERNAL/validation_report.json) 记录 raw audit、raw→epoch、checkpoint prediction replay 与独立统计重建通过，model state 不变；probability tolerance `atol=1e-7, rtol=1e-6`，argmax 必须一致。其状态明确为 `completed_with_calibration_limitations`，原电压标定、Cho 硬件参考和硬件 cue latency 未独立验证。
- [Q16 independent_validation](https://github.com/jackzhu119/cross-subject-mi-eeg/blob/b23480d996dd6c78e386686e1110e272decf166f/research_runs/Q16-P001-BNCI-20261006/independent_validation.json) 记录 18 原文件 SHA-256、5,184 trial event identity、228,096 saved rows、聚合和六个描述性相关的检查。独立手工 FFT 原始重放覆盖 C3/Cz/C4 的 31,104 trial-channel-band pairs，不能扩写成“22 通道全部原始功率独立重算”。
- 已查看 split、Q15 context、CSP 和 validator 测试文件/索引以判断断言范围。本轮没有运行第一篇全部 pytest、任何原始 EEG 计算、checkpoint inference 或训练。

### 本轮实际执行的只读检查

1. HTTPS Git `ls-remote` 成功；核实 main、annotated paper tags 的 peeled commits 和 PLOS tag。
2. 读取冻结 README、复现指南、上述实现/协议/运行与验证 JSON，不把文档草稿当作执行结果。
3. 使用 Git blob 字节重新计算 `scripts/q16_common.py`、`scripts/q16_metadata_audit.py`、`scripts/q16_bnci_analysis.py` 的 SHA-256，三者均与 Q16 `run_manifest.freeze.frozen_code` 一致。
4. 检查 `paper-v1.0.2` 与读取时 HEAD 的 tracked file 树，未找到 `LICENSE`、`LICENCE`、`COPYING`、`COPYRIGHT` 或 license 命名文件；pyproject 未声明项目 license。

以上只能证明已读取快照及指定文件一致；未证明新数据上的泛化、来源实验全流程可在本机重现或本项目的人类学习假设成立。

## 5. 代码许可与数据使用限制

**未找到明确代码 license，故本轮不进行旧自定义代码的复制/再分发迁移。** 复现指南写有“under the repository's actual LICENSE”，但该文字不能替代实际缺失的许可文件。用户明确授权技术参考；本轮实施仍采用独立实现。后续如需拷贝具体自定义代码，应先明确权利人许可、适用文件范围、许可证和署名要求，写入新的迁移记录。

第一篇 README 表明 raw EEG 不包含于论文归档；原始数据必须直接从各 provider 获取并遵守其独立条款：

| 第一篇数据来源 | 官方入口 | 本轮处理 |
| --- | --- | --- |
| BCI Competition IV 2a / BNCI2014_001 | [BNCI](https://bnci-horizon-2020.eu/database/data-sets)、[原任务说明](https://www.bbci.de/competition/iv/desc_2a.pdf) | 读取来源记录；不转发私有 R2 transport 副本或假定有通用可再分发许可 |
| PhysioNet EEGMMIDB v1.0.0 | [原始 provider](https://physionet.org/content/eegmmidb/1.0.0/) | 原始 provider 独立许可/引用规则须再核实；不是本轮新数据的许可证 |
| Cho2017 | [10.5524/100295](https://doi.org/10.5524/100295) | 数据条款与旧代码许可分开；未下载原始 EEG |
| Lee2019 / OpenBMI | [10.5524/100542](https://doi.org/10.5524/100542) | 不假定所有 training/test/feedback run 等价；来源 Q15 仅使用已声明 offline-training runs |

本轮没有重新逐一阅读以上四个 provider 的全部最新许可法律文本，故不声明许可已获全面独立确认。Dataset A / NETBCI 是本项目新的可行性检查对象，应以 [`dataset_feasibility.md`](dataset_feasibility.md) 中其官方材料的核实结果为准。旧 provider 的许可、伦理陈述、行为记录和反馈设计不能替代新数据集审计。

## 6. 第二篇实施验收与科学边界

新基础代码应验证 train/test trial identity 不重叠、subject/session 协议正确、CSP/scaler/PCA 仅用训练数据拟合、固定 decoder 在目标 session 不更新参数/BN 状态、预测能追回原 sample ID、配置/随机种子/实际依赖写入新 run 记录。FFT/PSD 与 bandpower 用已知频率合成信号验证，统计按 participant 配对而非按 trial。

后续真实数据 adapter 的字段、事件 anchor、sampling rate、单位、session/day chronology、trial/run 边界、feedback 与行为指标均需另审计。只完成这些基础设施不能声称 Decoder adaptation、Neural representation drift、Human neural learning 或 Behavioural performance 是同一过程；只有前两者的离线估计也不能证明后两者。

第一篇两会话、source-only 解码和 post-outcome 描述性生理分析提供的是工程经验与证据标准。本项目的 co-adaptation、independent control 和 retention 需要适用的纵向/反馈/行为设计；没有对应证据时保留为研究问题，不迁移第一篇结论。
