# 研究协议：Learning-Preserving Co-Adaptive BCI

核心问题：**How should BCIs adapt without compromising human neural skill acquisition?**

协议日期：2026-10-09（Asia/Shanghai）。状态：基础设施、单受试者真实审计及2026-10-10最小离线实验已执行；多目标算法与闭环人体实验仍为计划。本仓库的 synthetic smoke output 只验证软件路径，不作为 EEG、学习或疗效证据。文献核验见 [literature_review.md](literature_review.md)，数据可用性以 [dataset_feasibility.md](dataset_feasibility.md) 为准。

## 1. Scientific questions 与可检验假设

| 问题 | 假设与可证伪结果 | 可以支持它的证据 |
| --- | --- | --- |
| Q1. MI-EEG 跨 session 变化对固定 decoder 有多大影响？ | Operational-1：首次 session 校准后冻结的 reference decoder，在后续 session 的 held-out balanced accuracy 发生可重复变化。无变化、跨被试不一致或 CI 很宽均应保留 | 真实 EEG、严格分区、被试内 paired comparison；证明 decoder transportability 的变化，不证明人类学习或退化 |
| Q2. signal geometry 变化与 decoder performance 是否相关？ | Operational-2：预先规定的 covariance/subspace drift 与 reference decoder 分数变化关联；可出现零关联或相反关系 | 固定 feature convention、样本量匹配、多 session 被试内统计、噪声/伪迹控制；观察性关联 |
| Q3. 哪些几何变化携带 task information？ | Operational-3：总体方差、表征维度、class separation 与可解码信息可能不同步。若低方差模式没有可重复 task 信息，也报告该结果 | training-only feature construction、nested predictive validation、高/低 variance control；不能仅凭 PCA 图判断 |
| Q4. decoder 更新改善分数时，是否仍保留无辅助控制能力？ | Operational-4：与更新预算匹配的性能优化策略相比，未来候选策略保持训练性能并提升/保持 delayed no-assistance control；若撤回辅助后恶化则不支持 preservation | 新的人类 randomized closed-loop 实验、辅助撤回、frozen decoder probe、retention/transfer。历史离线 trial 不能检验此因果假设 |
| Q5. 哪些 adaptation 约束允许有益 neural plasticity？ | Operational-5：后续多目标方案可能优于仅惩罚 drift 或仅最大化 assisted score；其收益应在独立验证集与闭环 retention 上出现 | 与无约束、单约束、同计算预算对照及消融；目前没有已验证算法或命名方法 |

假设不预设所有被试表现提高，也不预设 drift 为坏、stable geometry 为好、compaction 为伤害或 high variance 为任务信息。人类练习、疲劳、electrode/噪声漂移与 decoder 更新可能产生相似离线现象。

## 2. Available evidence 与研究范围

| 来源/层次 | 当前可用或待取得的证据 | 允许的结论 | 不能跨越的边界 |
| --- | --- | --- | --- |
| synthetic generator | CPU 可运行的已知结构与人为变化，只用于软件验证 | shape、splits、train-only fit、统计输出和可复现性正常 | 不支持任何真实神经机制、技能或临床结论 |
| Dataset A: SHU cross-session MI EEG，DOI [10.1038/s41597-022-01647-1](https://doi.org/10.1038/s41597-022-01647-1) | 第二优先级，原始接入 `pending author access`。25 人/五日、32 通道/250 Hz、left/right MI；NEMAR nm000288 publication pending，停止请求。历史 Figshare v1 单受试者探针已保存，当前原始 ZIP 仍需作者合法访问 | 原始访问和 event/session 语义核实后可做 decoder stability/drift；通用接口与计划保留 | 非未处理连续 raw；无已确认闭环行为；原始 event 时间单位/完整 cue/rest 待确认；不猜测或绕过 ZIP 密码，不称接入完成 |
| Dataset B: NETBCI2026，DOI [10.1038/s41597-026-08237-5](https://doi.org/10.1038/s41597-026-08237-5) | 第一优先级 NEMAR nm000305 v1.0.0（CC BY 4.0）：19 人/四日。已实读 sub-1 的4 session×6 run、24 EDF，74通道/250 Hz、717 trial，right_hand/rest。原始 Dataverse v2.2 成绩侧表与 sub-01 小型元数据已读取；24 run 事件对应及本地适配通过；未下载大归档信号 | 公开访问/格式门槛通过；行为向量 run 顺序、评分分母和原始缺失原因验收后可做观察性 longitudinal 描述 | NEMAR为EDF derivative，不能与原始BrainVision混用；真实TSV right_hand=2/rest=1；每session重选特征并重校准LDA；无逐trial行为、撤回/延迟probe，不称独立技能retention |
| L1 sensory joint learning | 人类 EEG，有无触觉测试及超过两个月子集测试 | 人机联合训练与持久表现值得设计对照验证 | 本仓库未复现；主干预同时包含多个因素 |
| L2 manifold geometry | rt-fMRI navigation mapping 扰动 | 人类学习可能受到已有 geometry 约束 | 非 EEG，不能直接套用 sensorimotor covariance |
| L3 assistive algorithms | 侵入式猕猴 spikes 与 RNN | decoder adaptation 可能塑造 task 信息分布 | 历史 fixed/adaptive 数据不随机、非人类 EEG，没有本项目 retention endpoint |

第一篇工作常用的 BCI Competition IV 2a/2b 或 PhysioNet 不自动成为本项目默认数据。本项目优先 A/B 的跨 session 与行为证据适配；任何扩展数据先更新 audit，说明新增问题与限制。

**取得真实 EEG 是科研阶段的必要前提。** 如果数据被密码、授权、网络或缺失事件阻塞，继续软件验证、文献和协议工作；阶段状态仍写 blocked/pending，不能用 synthetic 分数填补真实结果。

## 3. Operational definitions

| 名称 | 本协议的定义 |
| --- | --- |
| decoder adaptation | 参数、normalization、alignment、readout 或 calibration 的更新；记录何时发生、看到哪些标签、更新预算 |
| signal drift | 同一表征约定下 EEG 分布/协方差/子空间随时间变化；包含生理与测量原因，不能默认是 plasticity |
| representation stability | 对规定指标和参考空间而言的相似程度；不是技能保存的同义词 |
| reference decoder score | 首次 session 的 training/support 上拟合、以后冻结的模型对真实 held-out trial 的离线 performance |
| recalibrated decoder score | 获得明确数量的目标 session labeled support 后更新模型，在独立 target query 上的离线 performance |
| human skill acquisition | 在可比较闭环任务/mapping下，被试练习后无外部辅助的行为控制提高；需控制 decoder 改变 |
| retention | 训练结束后经过预先规定延迟，**无外部辅助且 decoder mapping 保持规定冻结状态**的闭环行为能力保留 |
| transfer | 在预定义的新 mapping/task/context 上的无辅助行为表现；与同 mapping retention 分开 |
| learning-preserving | 后续干预相对于合适对照，在训练性能约束下支持无辅助技能/延迟 retention 的预注册终点；不能只由低 drift、loss 或 offline accuracy 命名 |

标签 `left/right`、`hand/feet/tongue/rest` 等按源文件 metadata 映射，并记录 class vocabulary。不能把不同 cue、rest 与 active MI、motor execution 与 motor imagery 混成同一任务。

## 4. Endpoints

### 4.1 当前离线阶段

主终点为**被试级跨 session reference decoder balanced accuracy**：分别报告每 target session，以被试为单位计算其后续 session 平均分和相对于 reference session held-out score 的差值。reference session 自身也留独立 held-out query，不能用训练分数作为基线。置信区间在被试层面求取。

重要次终点：macro-F1、逐类 recall、confusion matrix、失败/不收敛人数；相同 target support/query 划分下 recalibrated versus frozen decoder 的 held-out 差值；CSP-LDA 与 EEGNet 的同预算比较；校准 trial 数量、wall time、参数/数据预算。若缺少 target labeled support，可明确只做冻结模型，不能补造 recalibration 实验。

几何指标为辅助终点：covariance drift、PCA subspace distance、participation ratio、task separation 和跨 session 线性 probe。主要分析 pair/session 顺序预先指定，其他探索结果标 exploratory。

可用真实反馈数据时另列 run-level performance trajectory。单位、task success 定义、decoder recalibration 的位置必须源文件核实；run percentage 无 trial outcomes 时，不伪造 trial learning curve、response time 或 retention score。

**离线术语限制：** loss 更稳定只能说明对应模型损失轨迹；reference decoder score 更高只能说明在固定读取规则下数据更易分类；两者均不是“被试无辅助控制改善”或“人类学习 preserved”。

### 4.2 后续在线人类阶段（Phase 6，尚未开展）

训练时：matched closed-loop task success、完成时间/路径效率、错误率与 assist amount。统计“完成训练”不直接等于无辅助成功。

设两种明确区分的无辅助 probe：

1. **同 mapping retention probe：**训练结束时冻结所学 decoder，关闭外部触觉/纠偏/轨迹辅助和继续更新，立刻测一次；24–48 小时、7 天等预注册时间再以**相同 mapping**测量。报告 delayed minus immediate performance、绝对 delayed performance 和其 CI。立即与延迟之间不可再校准，否则这是 recalibration 后表现。
2. **固定 reference/transfer probe：**随机分组前，以统一校准规则得到每被试 reference decoder 并冻结；在各组相同时间/预算下重复测量。它评估对同一读取规则的变化。若训练 mapping 与此 reference 不同，应标作向 reference 的 transfer，不能改称同 mapping retention。

两 probe 都记录模型 hash、前处理状态与全部辅助开关。撤掉触觉但继续使用适应 decoder 与关闭 decoder 更新是不同操作；将 decoder reset 到旧 mapping 又会引入迁移难度。不能把不同操作所得分数混成一个 retention。

未来共同主张要求：预定义训练性能的非劣效界值和 delayed no-assistance control 的 superiority/非劣效标准；界值来自先导数据、量表含义和实际可接受差异，不能看过最终结果再选择。研究当前不宣布达到任何阈值。

## 5. Data partitioning 与防泄漏

分区单位至少为 **subject / session / run / trial**；同 trial 的重叠窗口只能在同一分区。session 顺序按原始日期/设计确认，不能仅凭文件排序或跨被试共享 session 编号。

- **Within-subject cross-session：**每被试最早 session 分出 reference support 与 reference query；其后的 target session 分出 calibration support 与 evaluation query。所有方法共用这些索引。target query 绝不参与 decoder/PCA/CSP/normalization、early stopping 或超参数选择。
- **Cross-subject（如果实施）：**外层 leave-one-subject-out/held-out subjects；仅源被试训练，目标被试 support 是事先限定数量的 few-shot calibration。目标 query 不混入源 pretraining。
- **Within-session sanity baseline：**run/trial 分组的划分，仅用于区别跨 session shift；不能取代跨天评估。
- **超参数选择：**开发被试/validation sessions 上完成；固定 pipeline 与主要分析后才打开最终 test cohort。小 cohort 使用 nested validation；留一轮 test 后不反复调参。
- **时间因果性：**流式 simulation 若开展，只使用当时已见数据；future labels、post-session batch normalization 和双向滤波的未来信息必须标离线。完整录制后的 zero-phase filter 不支持实时延迟结论。
- **几何分析：**reference PCA/CSP 仅 fit source support；target-transform 保持冻结。若为描述性分析另 fit target subspace，记录其数据预算，该 subspace 不回流 decoder；需要预测用途时另留 geometry support，避免用 query 对方案选择。

为每个样本保存 subject/session/run/trial/class/phase/source-file 元数据、split seed 和 partition ID。预处理在读取时验证 sampling rate、channel order/units、events、缺失/坏道/epoch时长，记录排除原因和各组数目。

所有 normalization、bad-channel 规则、artifact threshold 和 alignment 均作为学习器的一部分：使用相同规则与可获得信息。若方法使用 target 无标签分布，单列 **transductive/unlabeled adaptation** 对照；不能暗中赋予冻结基线同样不可得信息或利用 test distribution 调参。

## 6. Baseline selection 与 control groups

### 6.1 离线 baseline

| Baseline | 目的 | 公平性要求 |
| --- | --- | --- |
| CSP + shrinkage LDA | 简单、可解释的 MI decoding reference | training-only CSP；CSP components、频带与 shrinkage 在 validation 固定 |
| EEGNet | 小型深度 EEG 模型的补充 reference | 相同 trials、epoch、partition；report 初始化、optimization、early stopping、CPU/GPU与seed |
| frozen versus session-recalibrated 同一模型 | 区分固定读取与 decoder 重新校准 | target label budget 相同；query 独立；同一 model family，不把架构差异解释成 update 因果效应 |
| within-session versus cross-session | 衡量 transportability 差异 | trial/run grouped；并列说明两种 split 的问题不同 |
| simple alignment/regularization（后续候选） | 排除收益仅源于常规 normalization/域适应 | 只使用允许的 source/target support；匹配 label 与 compute budget；实施前更新 config/protocol |

多数类/chance/label-shuffle 是 sanity controls，用于发现错误，而不是论文中的主要创新对照。当前不以公开基准榜单数值充当本项目 baseline。

### 6.2 Phase 4/5 候选方法与 Phase 6 在线实验对照

多目标策略尚未实现/验证。可研究 decoder error、更新幅度、task information 和 geometry 约束的 trade-off；必须允许有益表征变化，不能把“最小 drift”直接定义为 preservation。拟定任何 objective 前先在真实数据检查指标可靠性及对 task information 的敏感性。

算法对照至少含：performance-only adaptation、匹配预算的 slow/small update、geometry-only constraint、计划中的联合约束及单项 ablation。所有方案使用同 decoder 架构与同 support budget，报告 model change magnitude 与 information source。只计算 offline objective 不产生 human learning loss 的真值。

在线实验优先 randomized parallel groups，按 baseline skill 分层；训练不可逆学习可能污染 crossover，若采用 crossover，须解释 carryover、order 和 washout 限制。主要组为固定 decoder、performance-only adaptive decoder、未来候选策略；有外部辅助时再加入强度/时序匹配、yoked/non-contingent/sham 组，区分 contingency 与刺激量。任务、校准规则、练习时间、feedback latency 与 probe 数量匹配；分析者盲于条件，执行者不能盲则如实记录。

## 7. Neural geometry metrics

所有指标都要求相同 channels/features、units、reference、band、epoch、trial-count convention。geometry 与 EEG 通道混合/volume conduction 有关，不等价于单神经元 geometry。

| 指标 | 定义/用途 | 解释与验证限制 |
| --- | --- | --- |
| PCA explained variance | reference support 拟合；记录维度数、eigenspectrum、center/scale | 最大方差不等于 task information。PCA 是线性 proxy，不声称重现 L2 的 diffusion manifold |
| subspace distance | 比较两正交 basis 的 projectors，例如 `||P_A-P_B||_F / sqrt(rank(A)+rank(B))`，相同环境维度 | basis sign/rotation 不改变结果；不同 rank 也可能增加 distance，需报告 rank、sample-count sensitivity 与 bootstrap |
| covariance drift | trial 或规定 session summary 的 SPD covariance；Riemannian/log-Euclidean 距离与 Frobenius 对照；报告正则化 | sampling、amplitude、reference、坏道可制造变化；shared shrinkage 必须固定。跨 trial/session 汇总约定不可临时切换 |
| class separation | within/between class covariance、validated linear-probe accuracy 或距离 | label-aware metric 仅作预定 held-out 描述/validation；不能用 test labels选 feature 再报告其 decoding |
| participation ratio | `PR=(sum(lambda))^2/sum(lambda^2)`，记录是否按 feature count 归一化 | overall effective dimension 与 task compactness 分开；matched feature count、trial count 与 SNR |
| task information versus variance | training-only rank 高/低 variance modes，独立 query 做单模式/逐步模式 probe | 模式排序和数目选择 nested；低 variance 也可能是噪声；禁止将 probe improvement 称 causal neural credit assignment |
| cross-session linear probe | 冻结 feature/decoder，对另一 session query 测量 | 主要评估 transportability；模型特征在各 session 分别 retrain 时坐标不可直接比较 |
| ERD/ERS/ERSP（数据支持后） | alpha/beta 及 C3/C4 或预定义 sensorimotor channels；baseline window 与功率单位固定 | 排除 cue/刺激/EMG contamination；频带选择不能由 test 效应调优 |

当前代码的 PCA、subspace 和 covariance 函数只是这些分析的基础。PR、mode information、ERSP、diffusion geometry 等若未实现，应在结果中保持 planned。二维 embedding/trajectory 只能辅助展示，不能代替 held-out quantitative endpoint。

## 8. Statistical analysis

**统计独立单位为被试。** Trial、window、run、session 和 random seed 是被试内重复测量；不能把它们扩成独立 n。动物文献的 learning series 也不能转换成可用于本研究 power 的人类 n。

离线主比较采用每被试 paired score differences，报告均值/中位数、全部个体点、95% subject-bootstrap CI、paired effect 和精确 p 值。默认双侧；预注册方向性检验才用单侧。小 n 时可用 subject-level sign-flip/randomization 或 Wilcoxon signed-rank，并明确假设；零值、ties、missing subjects 与失败模型不能静默删除。

多 session 时计划使用含 subject random intercept 的 mixed model，例如 `score ~ session + method + session:method`；有真实行为日志再加入预定义反馈阶段/更新事件。bounded accuracy 可考虑 binomial trial模型，但必须有实际 trial outcomes，不能从 run 百分比反推出二项计数。数据太少无法稳定拟合时降级为被试级描述/paired分析并报告不确定性。

geometry-performance association 使用 within-subject centering 或 repeated-measures model，避免把被试间能力差异当成跨时间变化；控制预定义 confounders 的数量与样本量匹配。相关/mediation 图不作为因果结论。报告效应 CI，避免仅凭不显著 p 值宣布 retention 或等价。

一个主终点和主比较先固定；次终点/模型的 family 做 Holm 或预定 FDR correction。time-frequency/channel 多重比较若开展，事先规定 permutation/cluster 方法与 family。探索分析明示 exploratory，不在最终结果中改成预设。

power 与 online 样本量在真实先导数据和最小有意义行为差异明确后做模拟，考虑 repeated measures、dropout 和非劣效界值；当前不凭三篇文献的其他模态效应编造 EEG power。算法 seeds 用于估计训练变异，报告 seed distribution；不能以最好的 seed 为主结果。

## 9. Confounders 与敏感性分析

| 混杂或失真来源 | 控制/记录 |
| --- | --- |
| impedance、electrode movement、channel dropout、reference、sampling/version change | 可用原始记录、signal-quality summaries、统一channel intersection、坏道敏感性；无元数据则保留未识别混杂 |
| EMG/EOG、真实运动、触觉/视觉 evoked activity | 保留伪迹标签/辅助通道；有刺激 trial 与无刺激 probe 分析；不能把 artifact 学得更好解释成 MI plasticity |
| fatigue、attention、睡眠、practice/imagery strategy | session时间/顺序、rest、问卷或原始日志；无日志不补造 covariates |
| decoder architecture、更新/标签/计算预算 | 同模型 policy 对比、统一 budget、记录 version/hash；历史异架构数据保持 observational |
| success-conditioned trial selection | 同一排除规则，报告全trial及成功trial敏感性；不能只在后期选择成功trial |
| feedback量、延迟、assistance强度与 contingency | matched/yoked controls、逐事件日志；aggregate score 不足以分离这些因素 |
| class imbalance、rest versus active MI、不一致cue或task难度 | balanced accuracy、逐类指标、统一任务语义，不混合不同任务的学习曲线 |
| 被试筛选、后期 dropout、组间不均衡 | 完整flow/counts、dropout原因与available-case限制；未来在线预设分析集 |
| 重复曝光 probe 导致练习 | 各组相同 probe 预算、顺序平衡，记录反馈；解释 probe 本身的训练作用 |
| geometry sample-size/SNR/维度差别 | matched counts、bootstrap稳定性、rank sensitivity、noise control，不以distance大小直接判技能 |

## 10. 阶段进展标准

阶段名称与 [ROADMAP.md](../ROADMAP.md) 一致；软件基础已经具备的函数，不代表相应真实数据科学阶段已经完成。

| Phase | 工作 | 进入下一阶段的最低证据 | 当前边界 |
| --- | --- | --- | --- |
| 0. Infrastructure | 环境/锁文件、可安装包、CPU baseline与geometry基础、schema、文献/许可/data audit、main与research分支 | clean checkout 可安装；tests、EEGNet CPU前向/反向及CSP跨session软件验证实际通过；smoke标 `software_validation_only`；配置/逐被试记录可读；推送SHA与远端核读一致 | 不产生真实 EEG 结论；数据集专用文件适配待Phase 1 |
| 1. Longitudinal Neural Dynamics | A解除合法访问/密码要求或B最小subject/session subset；核验channels、events、sampling、units、session时间、feedback、版本；再研究跨天mu/beta PSD、covariance和trial质量 | 至少可读取并对齐一个真实被试的跨session数据；许可/文件/event约定与出处完整；审计可重放；逐被试/session数量、缺失、排除和硬件/疲劳/任务混杂报告完整 | 无可读真实EEG即 blocked；不自动下载全量；仅纵向离线关联 |
| 2. Neural Representation Geometry | 同一可比坐标中的PCA、subspace/principal-angle、covariance、task information与stability；reference projection冻结 | 预定义feature、维度、对齐和train-only fit；置换/负对照与reliability通过；sample-count、channels/reference、SNR敏感性报告 | 允许零结果；几何proxy不直接等同fMRI/spiking manifold或技能 |
| 3. Fixed-Decoder Generalization | 冻结早期session的CSP-LDA与EEGNet，在后续session评估；区分within-subject longitudinal与held-out subject；validation选参 | 相同真实split可复跑；model/BN/normalization冻结且无重叠；逐被试balanced accuracy和subject-level CI；时序、class/trial count与失败记录完整 | 小subset不支持人群泛化；固定参考解码性能不替代在线无辅助行为 |
| 4. Co-Adaptive Learning | 设计固定、常规adaptation与候选policy比较；离线回放检验decoder更新与稳定性proxy；限定标签可获得条件 | 匹配训练/数据/调参预算；明确每一步看到的label与更新时间；历史标签不伪装在线可获得标签；收益/零收益均可复现 | 无真实人的反馈交互时，不宣称已验证人机共同学习 |
| 5. Learning-Preserving Optimization | 实施前更新协议；规划即时性能、长期稳定性proxy与更新成本的多目标、Pareto trade-off、消融/敏感性 | 候选objective与无更新/常规更新/单约束对照有独立、同预算可复现比较；端点/权重在final test前固定 | 目前无已验证新算法；离线proxy保留proxy名称，不能称human learning preserved |
| 6. External and Prospective Validation | 先跨数据集验证；再评估在线伦理/同意、硬件/实时运行、power、randomized controls、无辅助frozen probes、delay/transfer | 外部验证锁定mapping/端点；前瞻试验预注册训练性能与无辅助retention联合终点/排除规则，辅助/decoder日志与必要confounders完整；结论符合实际设计 | 未开展在线retention则不采用“保留人类神经技能”作为已证实结论；临床外推另需患者试验 |

每阶段保留正/负/不确定结果；更改假设、endpoint、排除或数据范围时版本化并说明是否看到结果。稿件可以先定位成可复现的 cross-session representation/decoder analysis，但其论点必须与已完成阶段匹配。

## NETBCI 历史单人分析前冻结方案

见 [跨会话分析方案](netbci_cross_session_plan.md)及[配置](../configs/netbci_cross_session.json)。此历史方案准备时，单受试者 717 trial 的 run 分组已验证，只完成接入与划分；后续最小模型验证和十人分析另有配置与收据，不以单受试者推断人群学习。原始与 derivative 事件对应已核查，行为 run 顺序和分母仍为 pending。

## 本轮正式假设与执行状态（2026-10-10）

用户正式H1–H4编号及证据条件统一见[最新stage1报告第5节](netbci_stage1_evidence_and_decision.md)。上文历史表已改为Operational-1..5，防止编号与新假设冲突。源端run隔离不变；新配置固定3epochCPU EEGNet仅最小验证，source-only transforms及模型冻结已实际检查。描述性target PCA不进入预测；事件相对谱不称ERD。单参与者不能估计人群CI；conditional run-bootstrap需标注退化及小cluster限制。新的策略和在线实验尚未执行。

## 2026-10-10 会话层行为扩展（探索性、已见先导结果）

已有原始19人×4session×6百分比已经核验；各session六个已发布百分比的无权均值可以直接
关联subject/session，不需先确认run顺序或联系作者取得已有成绩。实际执行见
[会话分析](netbci_behavior_session_analysis.md)和[配置](../configs/netbci_behavior_sessions.json)。
19人的完整行为轨迹进行subject-bootstrap，仅1人四会话有EEG，二者样本量不得混称。
神经—行为对照只作描述，不计算四点显著相关；run/trial outcome继续unresolved，不广播。
新增task-window log-power对比和96-trial匹配敏感性均不称ERD/学习，未新增解码器拟合。

## 2026-10-10 十人队列接续与修订

[十人扩展协议](netbci_cohort_expansion_protocol.md)沿用公开前十个编号，不按行为或 EEG 结果筛选；
已见 sub-1 先导与 19 人行为，因此属于探索性扩展。统一执行配置为
`configs/netbci_cohort_full_windows_20261010.json`，SHA256
`2bead8bccd0396e0358bb8167324621e80d48087ba011a334224f73962d10904`。
原 `configs/netbci_cohort.json` 不覆盖。十人 source training 均为 ses-01/run-01–04，
独立 source query 为 run-05–06；ses-02 仅作为 validation 描述且不选参，ses-03/04 为探索性评估。
粗 QC、scaler、预测 reference PCA 和 CSP/LDA 只在 source training 拟合；每人模型冻结且逐次
query 验证状态和预测重放。描述性匹配 PCA 使用同会话均衡样本，明确不进入预测。

严格审计实际遇到 sub-3 的一条 2.968 秒 rest 事件，边界恰达 EDF 末尾；
原始事件合规，不得填充成 5 秒或把其推断为行为失败。新模型拟合前记录
[完整窗口修订](netbci_full_window_policy_20261010.md)，保存全部 7,577 个源身份、7,576 个
纳入身份及一条排除原因，保留严格失败与早期 config 快照。此项为观察数据后的明确修订，
不冒称外部预注册；全部科学参数与主要描述对比不变。

主要描述对比为 ses-04−ses-01 的固定 CSP/LDA BA 和等 run Mu 任务窗口 log-power 差异。
重采样单位是完整参与者，10,000 次、seed=42；10 个匹配 seeds 和每人的 500 次 run bootstrap
均不增加参与者数。QC 匹配固定 run-03–06，每 run 每类 12 个 trial；样本不足记录 unavailable，
不降低数量或删除参与者。功率对比无 prestimulus baseline，不称 ERD。
额外的神经—行为/读出变化关联为参与者首末变化的探索性 Pearson/Spearman 描述，估计器及
五对指标的选择另有时间记录，非确认性或因果检验；不对 40 会话行作独立样本相关。

最新结果、QC/参考敏感性与下一阶段决策见[十人报告](netbci_cohort_results_20261010.md)。
within-session run AIRM 是异质性描述，不能代替测量可靠性；跨人的描述方向和计算重放
也不能分别冒称生物学重复或独立确认。H3/H4、算法新颖性、无辅助保持与 delayed retention
均仍待相应设计，当前不实现新 policy 或追加 EEGNet 训练。
