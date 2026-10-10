# L2 精读：人类 BCI 学习与流形几何

核验日期：2026-10-10（Asia/Shanghai）。本文用于第二篇论文的方法和论证设计；文献结果不属于本项目实验结果。

**Busch, E. L., Fincke, E. C., Lajoie, G., Krishnaswamy, S., & Turk-Browne, N. B. (2026). Human learning of noninvasive brain–computer interfaces via manifold geometry. Nature Neuroscience, 29, 2429–2437.** DOI：[10.1038/s41593-026-02311-2](https://doi.org/10.1038/s41593-026-02311-2)，在线发表日期 2026-06-09。

## 1. 实际阅读范围和证据来源

本轮阅读了出版社摘要、完整公开 Supplementary Methods 和 Supplementary Figs. S1–S16、Reporting Summary 第 2–3 页、公开 Fig. 3/Fig. 4 和补充图 source-data XLSX，以及作者分析仓库的 README、配置和部分分析函数。对 source table 做了人数与均值的独立算术核查，**没有下载 fMRI 数据、运行作者 MRAE/T-PHATE 或复现整篇实验**。

出版社主文仍为订阅预览。合法检索发现 Europe PMC 的索引 `PMC13318486`，但其全文 XML 请求返回 HTTP 500，PMC 页面返回浏览器验证页，未取得可读主文；OpenAlex 检索返回 429。不能因此写“已精读主文全文”。缺少主文的精确任务阶梯规则、全部模型超参数和所有排除细节仍标为未核实。

| 原始来源 | 本轮可核实内容 |
| --- | --- |
| [出版社页面](https://www.nature.com/articles/s41593-026-02311-2) | 标题、作者、摘要、出版信息、Data/Code availability、公开附件链接 |
| [Supplementary Information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM1_ESM.pdf) | 完整补充方法、S1–S16；下文页码为文件内部印刷页码 |
| [Reporting Summary](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM2_ESM.pdf) | 招募、排除、随机化、盲法、MRI、session/run 和行为测量；第 2–3 页另做图像核读，避免 PDF 字体编码错误 |
| [补充图 source data](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM3_ESM.xlsx) | 表内 n、S14 均值符号、S15 固定 decoder MSE；保留工作表命名错误 |
| [Fig. 3 source data](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM5_ESM.xlsx) | 实测/模拟身份、行为统计 n、trial/session/run 字段 |
| [Fig. 4 source data](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41593-026-02311-2/MediaObjects/41593_2026_2311_MOESM6_ESM.xlsx) | PEV–行为回归人数、按条件的关系及 CI |
| [作者分析仓库](https://github.com/ericabusch/avatarRT_analysis) | 方法实现的独立核对；README Git blob `7a9bf967dc474389d128cf4c8e52eb00f061446c`，helpers `2fe5f856d62233632671cb26b921c71898359672`，stability `69e9306eb8872ca0adab3394dc9f3c645b6e5cee`，config `f23a4fdc47c9c64051ee86e728eb6d047cbfc2a4` |

小型附件和代码读取响应存于 Git 忽略的 `data/literature_stage1/`，没有把出版社全文或第三方实现并入本仓库源码。公开访问成功不代表可任意重新分发原文。URL、HTTP 失败与 SHA256 见 [访问收据](../research_logs/netbci_stage1_20261010/nature_geometry_access.json)；实际表内核查见 [source checks](../research_logs/netbci_stage1_20261010/nature_geometry_source_checks.json)。后者只检验已发布数值的汇总，不能升级为原始 fMRI 复现。

## 2. 核心问题：脑能否学会不同的控制映射？

论文主动改变从神经活动到 avatar 运动的映射，以研究既有活动几何是否限制学习。重点不是寻找跨天分类准确率最高的模型，而是在可控制的反馈任务中检验**映射方向与可生成神经活动结构的关系**。

“noninvasive”在本研究指 **实时 fMRI**，不是 EEG。导航网络包括海马、内侧颞叶、楔前叶、外侧枕叶和海马旁皮层（S1，p. 7）。被试通过调节活动控制视频游戏 avatar，不能把这解释成 C3/C4 运动想象节律的直接实验。

Reporting Summary 报告 20 名健康青年、其中 10 名女性，19–35 岁；neurofeedback 分析排除 scanner malfunction 和睡着的两人。另记录一名 MRI 不适掉队者。作者代码将 `sub_12` 掉队者从最终 20 人列表排除，`sub_09/sub_20` 从多数 neurofeedback 分析排除。公开 Fig. 3 的统计表、Fig. 4 简单回归和本轮核算的 S14/S15 逐人表明确 **n=18**。Fig. 3 raw source sheet 仍含被排除的 09/20，不能对所有 raw rows 不加区分直接平均。

每次 MRI 4 个约 10 分钟 run，总计 4–5 个不同日期 session；目标间隔 24 小时，报告均值 27.4 小时、范围 13–48 小时，全部在 7 天内完成（Reporting Summary p. 3）。它不是数月后 delayed-retention 实验。

### 从校准到干预的顺序

1. **Joystick calibration：**初次 session 中被试实际操纵 joystick 导航，同时记录 fMRI。脑活动与游戏轨迹有同步记录；Unity 游戏状态 60 Hz，平均池化到 fMRI 的 0.5 Hz，再偏移 2 TR，即 4 秒，以校正血流动力学延迟（Supplementary Methods p. 2）。这个 4 秒延迟是 fMRI 处理规则，不能直接应用于 EEG。
2. **建立固定参考流形：**用初次 joystick session 的数据学习 T-PHATE diffusion manifold。后续 neural feedback 的参考来自这次校准，不能事后用所有 session 联合拟合，再把它描述为训练前已知空间。
3. **实时外推：**MRAE 的 reconstruction loss 加 manifold regularization，让新 fMRI 样本可映射到已学 embedding。S3–S5 报告 10,000 个训练 epoch 和 simulated-fMRI null；这只是原论文模型训练，不是本项目需要照搬的计算规模，也不是我们已经运行的实验。
4. **控制方向与扰动：**S12 明确训练 T-PHATE 参考表征的第 1、第 2、第 20 个成分，分别为 IM、WMP、OMP。作者 `get_manifold_component` 在非线性 embedding 上做 PCA 取得这些方向；因此不是在原始 voxel 空间直接取前三个 PCs。第 20 个方向是该实验的低方差操作化，不能泛化为任意严格位于全部流形外的神经状态。
5. **学习比较：**IM 首先训练；WMP/OMP 的先后在被试间 counterbalance。Reporting Summary 记载随机分配两种顺序，初始每组 10 人。被试对假设/条件盲，研究人员未盲。当前公开配置中的顺序名单与初始平衡表不能自动视为同一招募版本；若复现分配必须取得正式 session tracker。

S13 显示 joystick held-out 的 20% testing data 投影到三种方向后都覆盖一系列 avatar 转向角（−90° 到 90°）。作者 loader 注释使用校准投影的第 1/99 百分位范围标定映射斜率。**可产生一定投影范围不等于可自主、精确地控制该方向。** OMP 在所测训练时段学得差，也不等于人类永远不能学会低方差方向。

## 3. 什么算“学习”，哪些证据支持因果解释？

行为测量来自真实导航任务和轨迹，Reporting Summary 描述额外行走距离相对最短路径，并据此调节任务难度。公开 source sheet 有 `subject_id`、`trial_number`、`run_number`、`session_number`、`success`、`brain_control_normalized`、`simulated?`；这正是本项目应争取取得的明确行为身份结构。文献的 **ΔBrainControl** 是其导航任务和难度规则下的行为变化，不能换名为 NETBCI 的 MI/rest balanced accuracy。

主动 manipulation 是 neural-to-avatar mapping，WMP/OMP 为被试内对照，随机化的是扰动先后。这支持“在该任务和训练时长中，映射所依赖的几何方向影响可学性”的干预论证。它没有直接随机化人的脑活动方差、突触塑性或神经损伤；PEV 与行为的关联仍不自动是 mediator 的因果证明。IM 总是先训练、任务难度调整、练习策略与跨条件 carryover 需要一并讨论。

S6 的顺序分析有 session type 主效应，`F(1,32)=9.18, P=0.005`，无可靠顺序主效应或交互。但样本被分半后功效有限，**未显著发现顺序影响不能证明没有 carryover**。该公开表标为 OLS regression；本项目若分析重复测量应明确 participant 内相关结构，不因期刊等级就不检查统计模型。

论文摘要支持 IM/WMP 的成功学习与神经 realignment，相比 OMP 在研究窗口中的学习困难。不能把这一结论扩展为“所有 EEG 高方差方向都更容易学”或“低漂移代表技能保存”。

## 4. 几何分析的精读：分解竞争解释

### 4.1 ΔPEV 是相对方差，不是 task information

作者 `run_EVR` 对固定参考成分的投影时间序列计算各方向方差，再除以全部成分方差和。可写作 `PEV_k = 100 × Var(projection_k) / Σ_j Var(projection_j)`；`ΔPEV` 比较训练末端与开始的 run。它反映方差如何分配，不是该方向的因果贡献、全部脑活动维数或可解码任务信息。分母变化、噪声和策略改变也会影响比例。

S7 将每个 session 的 IM/WMP/OMP 三方向同时比较：IM、WMP 在各自训练 session 沿训练方向出现正 ΔPEV，OMP 没有可靠变化。S8 进一步检查：

- 整体 voxel 和 T-PHATE variance 没有可靠 pre/post 改变（`P ≥ 0.17`）。这是未检出整体变化，不能写成已证明总体方差完全不变。
- 对全部 20 方向建立 participant/session-specific null，检查训练方向相对任意方向是否特殊。IM 和 WMP 的 z-score 分别为约 0.574 与 0.409（source stats n=18），OMP 未出现可靠正效应。
- 投影范围方差的增加仅为 IM/WMP 的边缘证据（S8C `P=0.06/0.079`）；不应把所有补充神经结果写成强阳性。

公开 Fig. 4 简单回归显示 ΔPEV–ΔBrainControl 关系在 WMP 为正（n=18，斜率 5.599，95% CI 0.147–11.050，P≈0.0448），IM/OMP 未见可靠关系。线性混合模型给出的 WMP 项与简单回归不是同一模型结果，不能挑较小的 P 值混写。该关联支持候选机制，仍需要对替代解释和干预 mediator 的证据。

### 4.2 Realignment 与 subselection 不是两个可凭图形判定的标签

Supplementary Methods pp. 2–3 与 S9 比较两种生成解释：

- **Subselection：**以较高概率删除较小幅值投影，再从留下的分布补抽样；相同投影库的访问频率改变。
- **Realignment：**拟合初始投影分布（normal/lognormal/beta/gamma/triangular 候选），保留 shape，按 `(1+P)` 增宽 scale。

`P ∈ {0.2,0.3,0.4,0.5}`，每种模型/参数 10,000 次模拟；以 observed variance change 在模拟 KDE 中的 normalized density 衡量 typicality，作 participant 层比较。WMP 在多个参数下更支持 realignment，IM 仅最低 P 的差异较可靠。**normalized density 不是模型后验概率，两个候选更优也不排除其他策略。** 潜在变动中的尾部异常值、疲劳、噪声、自相关和任务难度仍须作为实际研究控制。

### 4.3 Gromov–Wasserstein：先检验参考结构是否可跨 session 使用

公开方法先分别重估每个 session 的 manifold，再比较初次 joystick 与后续 session 的结构距离，避免默认不同 embedding 空间的坐标已对齐。GW 利用空间内部距离关系，可比较未共享坐标的分布；这和共同 EEG 通道坐标中的 covariance 距离不是同一统计量。

作者以每人跨 session 的自身距离对两类 null 作比较：其他人的后续 neurofeedback manifold，以及其他人的初次 joystick manifold；participant 内抽样 10,000 次后计算 z-score，再在 participant 层作检验。该结论是**被试内结构比被试间更相似**，并不证明无漂移、保留相同 task information 或同一 decoder 可无限期泛化。固定的人体解剖、预处理和测量特性也可能贡献个体结构特异性。

本轮发现必须保留的核验问题：

1. S14 caption 打印 `mean z=1.051/0.416`，但 CI、效应方向和图为负。本轮逐人 source table 重算得到 **−1.0513338/−0.4155301**（n=18），与负 CI 一致。本文保留原文问题，并根据 source table 记录方向，不默默改写来源。
2. Supplement Methods p. 4 的自身跨 session 汇总为三个距离的**平均**；所读取的作者 `intrinsic_manifold_stability.py` Git blob `69e9306…` 在 `compute_zscored_results` 中使用自身距离的**最小值**，且 null sampling 包含自身值。当前公开代码不自动等于生成发表图的冻结版本，未运行原始数据，不能据此声称已查明作者实际实验执行。复现前需取得发布版本、缓存生成规则与作者解释；本项目预设平均/中位/逐 session 距离及匹配预算，不复制这个未解决的实现。
3. XLSX 的 `figureS14_stats` 实际含 S15B 的 `delta_MSE` tests，而 `figureS15B_stats` 是空表。读取必须靠字段核验，不能只靠工作表标题。

### 4.4 对本项目最有启发的反例：旧 decoder 下降可能伴随新映射学习

S15A 中各 session 内 leave-one-run-out 的位置 decoder MSE 没有可靠差异。S15B 把 IM session decoder 冻结，用于 WMP/OMP 的首次与末次 run：

| 条件 | 固定 IM decoder 的末 run − 首 run MSE | 95% CI | n | 单侧 permutation P |
| --- | --- | --- | --- | --- |
| WMP | +0.0490701 | −0.0008184 至 +0.1062309 | 18 | 0.050095 |
| OMP | +0.0072284 | −0.0370075 至 +0.0477084 | 18 | 0.369063 |

本轮从公开表的 18 个 participant 数值独立重算均值，但未重跑 fMRI、decoder 或 CI。WMP 旧读出 MSE 增加只是**边缘观察，CI 跨零**，不能写成已确证旧能力损害。它与成功的 WMP 学习共同提醒我们：**新 mapping 的学习与旧 reference 的可读性可能分离**。所以任何只惩罚漂移或只提高旧 decoder 分数的 objective 都可能约束有益适应；必须用真实无辅助行为判断是否保留技能。

## 5. 哪些可用于我们的 EEG 研究？

| 思路 | 可在当前 NETBCI 离线阶段实现的严格版本 | 不能直接移植的解释 |
| --- | --- | --- |
| 初期参考空间冻结 | source training 仅拟合 PCA/CSP/normalization；后续 session 用相同通道、单位、参考和特征；描述性 target geometry 单列 | 所有日期共同 fit 后的漂亮 embedding 不能当 prospective decoder |
| 训练方向特异变化 | 固定 source feature directions，同时报告总体方差、各方向方差、class separation 和 held-out decoding；匹配 trial/run 与伪迹敏感性 | EEG PCA 高方差方向不自动是可自主控制的 intrinsic neural manifold |
| Within/between-session baseline | equal-count resampling、split-half/run reliability 与时间顺序描述；多被试后检验 within-person versus between-person null | 当前 1 名受试者无法复现跨人 GW null、总体学习关系或人口 CI |
| 竞争解释 | 分离分布 scale、投影频率、噪声、坏道、参考与 session 重校准；必要时 source-only 建模、held-out 校验 | 单一 covariance drift 或散点图不能判定 plasticity、realignment 或 subselection |
| 信息与方差分离 | PSD/Mu/Beta、协方差、PCA 高/低方差成分的预设 task probe；拟合和选择全部在 training/validation 内 | 不把 sensor contribution 写成 neuron-specific compaction；低方差信息也可能为伪迹 |
| 固定读出反例 | frozen CSP+LDA/EEGNet 的 held-out BA 与几何变化并列，允许分数提高、下降或无变化 | reference BA 不等于关闭辅助后的 avatar 任务或人类技能 retention |
| 原始行为身份 | 按真正的 subject/session/run/trial/timestamp 连接；未知对应、分母保留 unresolved | source table 的 6 个百分比不能由数组顺序变成 trial success |

EEG sensor covariance 可使用 Riemannian geometry 描述 SPD 结构；平均参考会产生降秩，应使用显式参考子空间或记录 shrinkage 及敏感性。这不是本论文的 voxel/T-PHATE/GW 直接复现。跨 run 观测不能假装独立 participant，时间相邻 trial 也不能无条件 bootstrap 成人口效应。

当前数据即使观察到 PSD、covariance 或 fixed-decoder BA 的变化，最多形成纵向 EEG/读出关联的探索证据。原始 NETBCI 每日重选特征/重校准、行为向量对应尚不完整且没有预注册的无辅助 delayed probes，因此不能用它回答“限制 adaptation 是否保护人的学习”的因果问题。

## 6. 独立切入点与待检验假设

我们的独立问题可以是：**在 EEG BCI 中，哪些更新保留可自主控制的任务表征，同时允许对新任务有益的表征变化？** 已有流形方法、冻结 decoder 或正则化本身不是创新；创新需要一个过去不能区分的现象、明确的反事实对照和可检验的预测。

候选假设（尚未成立）：

- **可生成性、任务信息与旧读出一致性三者可能分离。** 高 variance 不必有最强 task information；保持旧 reference 也不必促进新 mapping 学习。需要可靠特征、held-out predictive probes 和真实自主控制三层证据。
- **简单“最小化 drift”可能过度限制有益学习。** 当 drift 伴随可靠任务信息和无辅助控制改善时，应允许这种变化；当 drift 伴随伪迹或只改善 assisted training score 时，不应称有益 plasticity。当前 NETBCI 无法验证这种反馈因果差异。
- **保留策略应根据 mapping 可学性与独立行为端点评估，而非仅用 decoder loss。** 必须与同架构、同标签/更新预算、同反馈和任务难度的 performance-only adaptation 比较，不通过架构差异制造“保留”效果。

可计划的未来 EEG intervention 借鉴的是实验逻辑：先合法招募并通过伦理审核；取得初始 source-only 几何与行为校准；构造几何相容与不相容的 mapping 或不同 adaptation 约束；在先导阶段匹配信号范围、增益、可观测噪声、初始控制难度和反馈；随机/平衡分配，限制 carryover；实时记录 decoder version、触觉/纠偏强度、trial ID、真实 outcome 和轨迹。不能把 scalp EEG 的低方差噪声方向故意做成困难条件，再把差异解释为内在神经学习约束。

学习判定需要预先区分两类 probes：训练结束冻结**当前已学 mapping**、关闭外部辅助与更新，做立即/延迟 retention；另外用最初 reference mapping 做独立 transfer/readout probe。如果训练已改变 mapping，回到最初 reference 的下降可能是迁移困难，不自动表示所学技能丢失。原论文 S15 的边缘结果正说明这一端点区别为何必要。

在当前单被试阶段，合理产出是可重放数据审计、预处理敏感性、几何可靠性和固定读出可行性；稿件可借鉴“操作定义 → 竞争解释 → 匹配对照 → 行为/神经证据分离”的论证结构。不能仿造原论文的成功学习、扰动效应或 retention 结果，也不能把其 fMRI 方法换成 EEG 名称就作为新的 Learning-Preserving 算法论文。
