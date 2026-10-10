# 文献核验与研究缺口

研究方向：**Learning-Preserving Co-Adaptive Brain–Computer Interfaces**。核心问题是 *How should BCIs adapt without compromising human neural skill acquisition?*

本文记录截至 **2026-10-09（Asia/Shanghai）** 实际访问到的原始来源。它是研究立项的证据台账，不是完成复现实验后的结论。论文报告的结果与本仓库的待检验假设分开记录；此句为2026-10-09历史状态；2026-10-10最小真实分析见[stage1报告](netbci_stage1_evidence_and_decision.md)。

## 1. 访问记录与证据层级

| ID | 论文与来源 | 实际访问范围 | 尚未核实的内容 |
| --- | --- | --- | --- |
| L1 | Wang et al., **Sensory-guided human-machine joint learning accelerates the acquisition of motor imagery brain computer interface control**, *Nature Communications* 17, 6177 (2026), [出版社正文](https://www.nature.com/articles/s41467-026-75435-5), [DOI](https://doi.org/10.1038/s41467-026-75435-5)；2026-07-15 发布 | 出版社 HTML 为开放全文；读取 Abstract、Results、Discussion、Methods、Data/Code availability 与图说明 | 未逐项读取 supplement、原始 EEG、作者代码、预注册材料；未独立重算效应、检验分配执行或数据完整性 |
| L2 | Busch et al., **Human learning of noninvasive brain–computer interfaces via manifold geometry**, *Nature Neuroscience* 29, 2429–2437 (2026), [出版社页面](https://www.nature.com/articles/s41593-026-02311-2), [DOI](https://doi.org/10.1038/s41593-026-02311-2)；2026-06-09 发布 | 出版社主文为订阅预览；读取摘要、Data/Code availability。公开 [Supplementary Information PDF](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM1_ESM.pdf) 已取得并读取 Supplementary Methods、相关图说明；[Reporting Summary PDF](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM2_ESM.pdf) 的第 2、3 页进行了图像核读；亦读取 [作者分析仓库 README](https://github.com/ericabusch/avatarRT_analysis) | 未读取订阅主文全文；精确各主文比较的分析人数、所有主文效应量、完整扰动构造/超参数和排除流程未逐项核实。README 不能代替原始 Methods |
| L3 | Rajeswaran et al., **Assistive algorithms influence neural representations in motor brain-computer interfaces**, *Nature Communications* 17, 9832 (2026), [出版社正文](https://www.nature.com/articles/s41467-026-76109-y), [DOI](https://doi.org/10.1038/s41467-026-76109-y)；2026-09-15 发布 | 出版社 HTML 为开放全文；读取 Abstract、Results、Discussion、Methods、Data/Code availability 与图说明 | 未取得完整历史动物数据，未运行 RNN 或重算分析，未逐项读取全部 supplement |

访问成功是文献内容可读的证据，不代表作者数据已下载、许可已审计或结果已复现。检查使用平台 HTTPS 代理与 TLS 验证；PDF/HTML 暂存于云机器的 `/tmp`，未将出版社全文复制到仓库。

## 2. L1：感觉引导的人机联合学习

### 实验对象、模态和任务

这是**人类非侵入式 EEG MI-BCI**，不是侵入式神经接口或 fMRI。Methods 描述 64 通道 Neuroscan Quik-Cap，1000 Hz 采样，BCI2000 实时处理。31 名健全、BCI-naïve 被试随机分到 joint learning（15）、BCI2000 control（8）、tactile control（8）；另有**独立招募的 EEGNet control（8）**，不能把摘要的 31 人当成所有补充对照均包含在内。

所有主试验被试完成前四个 session；21 人继续后两个 session。长期测试另有主试验的子集：联合组 6、BCI2000 组 5、触觉组 5，间隔超过两个月。由左/右手 MI 逐步扩展到 2D；向上为双手 MI，向下为 rest，所以 2D 是含静息的非对称任务，而非四类对称 MI。

### 干预、对照和 decoder 更新

联合组采用相同方向的成对 trial：第一个 trial 无刺激；成功达到预设 70% 阈值后，第二个为 `copy`；未达到时为 `new` 并提供同侧振动触觉引导。EEGNet 的 sample reweighting 优先低 loss 样本、逐轮扩大纳入范围。decoder 在 training run **结束后**更新；run 内固定，online test run 不微调。

触觉组有匹配方向的 trial pair，但无 copy/new 指令、每 trial 触觉不依赖之前表现。原 BCI2000 对照前六 session 使用固定 AR decoder，无触觉/策略提示；长期测试改用 EEGNet。独立 EEGNet 对照保留 run-wise 更新但取消触觉、配对策略和重加权。另有同一数据上 Weighted-EEGNet 对比普通 EEGNet 的 pseudo-online 分析。

这比仅比较“深度网络 versus 传统 decoder”提供更丰富的证据，但并非完整、同时随机化的多因素设计。最初联合组与 BCI2000 组同时改变 decoder 架构、更新策略和训练流程；独立 EEGNet 组来自另一次招募。不能从整体差异唯一归因于某一种重加权、感觉或策略模块。

### 结果、神经分析和学习解释

论文区分滑窗 online accuracy、PVC、fPTC。摘要中的 86.0%（1D）和 77.5%（2D）为离散控制指标；77.5% 和 66.9% 为连续/滑窗控制指标。它们不是同一离线 trial 分类准确率，不能拿来与本项目的 balanced accuracy 横向比较。

神经分析包括 C3/C4 alpha（8–13 Hz）/beta（13–30 Hz）的 ERD/ERS、ERSP、topography、Grad-CAM、相邻 run 的信号变化与 decoder 梯度的 projection/cosine alignment。末端无触觉 test run 与训练前无触觉 test run，以及长期无触觉测试，比仅看 assisted training score 更接近持久技能的证据。

不过，**撤掉触觉不等于撤掉 decoder 适应带来的全部帮助**；无触觉表现由被试状态和当前 decoder 共同决定。ERSP/Grad-CAM 反映信号和模型关联，不是直接观察突触塑性。长期测试人数较小、主组不均衡、后期/长期子集选择、对照 decoder 改变、休息类与 MI 类的差异均需要敏感性分析。论文的神经塑性和持久学习机制解释应保留这些边界。

### 可迁移与不可迁移

可迁移的是：明确反馈条件；同步记录 decoder 更新；保留无刺激 probe；用架构和更新预算匹配的对照；将性能、信号变化与 decoder 学习分开报告。sample reweighting 可作为后续算法对照，但不能因离线收益就命名为 learning-preserving。

不能直接迁移的是：没有触觉/行为标签的公开离线 MI 数据无法重现 copy/new 干预；普通跨 session 准确率不能复现两个月的技能 retention；本项目不复制原文数值作为目标结果或验证标准。

### 数据与代码声明

论文链接 [Figshare EEG DOI 10.1184/R1/32293995](https://doi.org/10.1184/R1/32293995)、[作者 GitHub](https://github.com/bfinl/SensoryGuidedJointLearning/)、[Zenodo 10.5281/zenodo.20480141](https://doi.org/10.5281/zenodo.20480141)。本次仅核实出版社的声明与链接，未下载、验证这些数据/代码内容。

## 3. L2：流形几何约束人类 BCI 学习

### 模态、任务和实验对照

“noninvasive”在本研究指**实时 fMRI**，不是 EEG。被试用空间导航相关脑区活动控制视频游戏 avatar，先以 joystick 任务数据估计 intrinsic manifold，再做 neurofeedback。Reporting Summary 记载招募 20 名健康青年，随机分配 within-manifold perturbation（WMP）或 outside-manifold perturbation（OMP）先后（每种顺序 10 人）；属于被试内、跨 session 的扰动比较。被试不知道假设/条件，研究人员未盲。

公开 reporting 描述四或五次、每次四 run 的 MRI session，目标间隔 24 小时且七天内完成。两人从 neurofeedback 分析排除（扫描仪问题、睡着），另记录一名因 MRI 不适掉队；公开 supplement 的策略问卷为 N=18。不同部分的统计人数不能直接混成“所有分析 n=18”；各比较的最终 n 和缺失时间点需查主文/source data 后确认。

摘要的核心操作是改变 neural activity 到 avatar movement 的 mapping：沿 intrinsic manifold 的高变异方向的 mapping 学得较好，偏离该 manifold 的 mapping 在所测训练窗口未学会。因为 mapping 是主动干预且顺序 counterbalanced，证据强于仅观察自然漂移与分数相关；结论仍限于这个 rt-fMRI 导航任务、扰动构造和训练时长。不能推广成“人脑永远学不会低方差方向”。

### 几何分析（公开 supplement 可核实）

初次 joystick session 使用 T-PHATE 提取数据 diffusion manifold；MRAE 将 embedding 扩展到后续实时样本。神经 realignment 分析以 trained component 的 percent explained variance（PEV）变化为中心，区分整体 variance 改变、任意 component 改变、训练方向特异变化。

补充分析将“分布尺度变宽”的 realignment 与“偏选较大 projection”的 subselection 比较，使用模拟/null resampling；另重估跨 session manifold，用 Gromov–Wasserstein distance 比较同一被试跨 session 与不同被试之间的相似性。公开作者 README 另列 behavioral learning、run-wise decoding、counterbalancing order、跨 session decoding 和 realignment/consolidation 分析脚本。README 中分析名称不自动确立对应效应成立。

### 可迁移与不可迁移

可迁移的是：先规定参考表征空间；测试 decoder update 是否与可生成方向相容；扰动对照匹配；区别 overall variance、trained direction variance 与 task information；检验跨 session manifold 稳定性而不是假定稳定。

不能直接迁移的是：T-PHATE 的 fMRI voxel geometry、血氧延迟、导航网络和 avatar 行为并非 sensorimotor EEG covariance geometry；将所有 session 联合嵌入后得出的可视化不能当训练前已知 manifold；离线 PCA subspace distance 既不能证明人类学得更快，也不能证明神经技能保存。本仓库当前只有线性/协方差几何基础，未声称复现 T-PHATE/MRAE 或原文实时扰动实验。

### 数据与代码声明

出版社声明 [Dryad DOI 10.5061/dryad.9cnp5hr0w](https://doi.org/10.5061/dryad.9cnp5hr0w) 包含 fMRI、行为、model weights 和 masks；代码链接 [avatarRT_task](https://github.com/ericabusch/avatarRT_task)、[avatarRT_analysis](https://github.com/ericabusch/avatarRT_analysis)、[MRAE](https://github.com/ericabusch/MRAE)、[TPHATE](https://github.com/KrishnaswamyLab/TPHATE)。本次未下载原始 fMRI 或执行分析。

## 4. L3：辅助 decoder 如何改变神经表征

### 实验对象、数据来源和对照局限

这是**侵入式动物 motor BCI**：两只雄性 rhesus macaque（J、S），motor/premotor cortex 的 128 microwire electrode arrays，multi-unit spikes/threshold crossings，2D center-out cursor task。主要 adaptive-decoder 分析为 10 个跨天 learning series（J:7，S:3），不是 10 个独立动物。Series 单位统计不代表物种层面的样本量。

adaptive decoder 为 position-velocity Kalman filter，J 使用 SmoothBatch、S 使用 ReFIT 形式的 closed-loop decoder adaptation（CLDA），初次提升控制能力、跨天出现约 10–20% performance drop 或 unit 丢失时再调整。Stable readouts 与 nonreadouts 区分，前者被用于 cursor control。主要分析早期/晚期足够试次数日；使用到达外围目标的 trial，这种条件筛选可能受学习阶段的成功率影响。

fixed-decoder 对比来自**另一历史数据集、另外动物 P/R，且 Wiener filter 架构不同**。因此不构成同一队列随机分配的纯“固定 versus 自适应”因果实验。任务、动物、recording stability、训练历史、readout 选择和更新触发均可能混杂。读到的 Methods 明确将 fixed/adaptive 定义为 update policy，而实验数据里架构仍有差别。

### 表征分析和机制证据

论文分析每单位 target identity 可解码信息、ranked/combinatorial neuron adding curves（NAC）、达到阈值的单位数；再对 PCs 做 mode adding/单模式 task decoding，比较高/低方差 PCs、squared PC loadings、participation ratio（PR）。主要结果是适应 decoder 下 task information 更集中于少数 readout units/modes，而 overall population dimensionality 不必下降；task information 可能集中在低方差 modes。

这区分了**表征 compactness**与**总体 variance/dimensionality**。仅用前几个高方差 PCs 或单个 variance 图，可能遗漏 task-relevant 信息。EEG 通道是混合信号，不能把“少数 EEG 通道贡献高”写成“少数神经元承担任务”。

RNN 模型能在更受控条件下改变 adaptive/fixed decoder、CLDA intensity，检验 computational mechanism 及参数/权重变化。该模拟支持 adaptation 可以促成 compaction 的机制可行性；模型里的直接干预不是活体神经突触、信用分配或人类长期依赖的直接因果证据。动物数据没有本项目所需的“辅助撤回后人类 MI 技能 retention”端点。

### 可迁移与不可迁移

可迁移的是：同步记录 decoder 变更；用 task-predictive information 与方差共同分析 geometry；注意低方差信息；考察固定/适应模型、readout 变化、辅助强度；用受控模拟提出机制假设。

不能直接迁移的是：spike 单位 compactness 与 scalp EEG feature compactness 的生物学解释不同；这种 adaptive assistance 不等于外骨骼/触觉辅助；compaction 不自动意味着技能受损，可能提高效率或改变脆弱性。必须另做撤回辅助、固定 decoder probe、延迟 retention、干预对照才能判断 preservation。

### 数据与代码声明

完整 adaptive neural/behavioral 数据为按合理请求取得，fixed 历史数据由原作者分享；公开 [分析/模拟仓库](https://github.com/pavi-rajes/Assistive-sensory-motor-perturbations-influence-learned-neural-representations) 提供示例 experimental data 与分析。公开示例不能当完整跨 series cohort，数据请求尚未执行。

## 5. 综合证据与本项目的问题

| 层次 | 已有证据支持的研究问题 | 本项目可先做的离线工作 | 仍需要的真实闭环证据 |
| --- | --- | --- | --- |
| decoder robustness | signal 与 decoder 都会变，单个 accuracy 不能分解二者 | reference decoder 跨 session 分数、recalibrated decoder、更新前后离线差异 | 控制相同 neural state 下的 mapping/assistance 干预 |
| neural geometry | manifold 方向与 task 信息/variance 需要分别看；compactness 不等于降维 | PCA subspace、covariance drift、task separation，匹配试次数与固定 feature basis | EEG mapping 扰动、方向可生成性、信号/行为时间顺序 |
| human skill | 无刺激 probe 和延迟测试比训练分数更接近 persistence | 有真实反馈公开数据的观察性跨 run/session 分析；没有则仅做代理 | 随机分组、同架构 decoder、撤除辅助、固定 mapping、延迟 retention/transfer |
| learning-preserving adaptation | 辅助和适应可能塑造表征，但“更稳定=更好”并未成立 | 为将来的多目标方法定义证据需求和消融 | 预注册的性能与无辅助技能联合终点/非劣效界值 |

L2 的高变异 manifold 可学性与 L3 的低变异 task information 不是同一实验命题：它们的物种、模态、任务、辅助、时间尺度和分析空间不同。本项目应检验这些现象在 EEG 中是否发生，不能选其中一条当普遍规律。

当前项目以真实可访问的跨 session EEG 为第一道证据门槛。若只能取得标准离线 MI trial，论文论点应限定为 *decoder adaptation and representation stability*；若取得反馈/behavior日志，可做 co-adaptation 的观察性分析，但不能替代随机闭环学习实验。**只有未来的人类无辅助 retention/transfer 试验，才可能支持 learning-preserving skill acquisition 的核心主张。**

## 6. 下一轮核验清单

- 取得 L2 主文的合法可读版本；核实每比较人数、排除与 perturbation 构造，记录主文与 supplement 的一致性。
- 检查 L1 数据的 subject/session/run/trial、stimulation、decoder version、时间戳及长期测试标签；核实 independent EEGNet control 的招募与统计比较边界。
- 若使用 L3 示例做方法验证，记录它覆盖的动物、series 与 days；不得补写为完整原始数据复现。
- 使用任一来源前检查数据许可、文件校验与事件语义；本次文献 DOI 链接不代表 data ingestion 已完成。
- 所有新增结果都另列本仓库 run ID、config、数据版本、排除与统计单位，避免把文献结果当本项目结果。

## 2026-10-10 原始方法精读修订

详见[nature_joint_assistive_close_reading](nature_joint_assistive_close_reading.md)及[nature_geometry_close_reading](nature_geometry_close_reading.md)。L1正文随机分组与Reporting Summary矛盾、长期EEGNet重训、输入梯度公式；L2订阅阅读边界、n18与公开源表/源码口径差异；L3历史队列混杂和demo边界均有定位。旧摘要不是新精读或复现结论。原创[论文工作稿](../manuscript/longitudinal_eeg_working_draft.md)不复制原文或将方法借鉴称为已证创新。
