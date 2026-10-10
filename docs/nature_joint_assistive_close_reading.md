# Wang 与 Rajeswaran 原始方法精读：第二篇论文如何提出可检验问题

精读日期：2026-10-10（Asia/Shanghai）。本文件是原始文献的方法核验与研究设计说明，不是本项目的实验结果。`L1` 和 `L3` 延续 [literature_review.md](literature_review.md) 的文献身份；Busch 的流形论文由独立精读文件负责。本文没有运行作者实验代码、重算论文效应或下载作者 EEG/动物信号。

## 1. 本轮实际读到了什么

| 文献 | 核验来源及本轮阅读范围 | 不能据此声称的工作 |
| --- | --- | --- |
| L1，Wang et al.，*Sensory-guided human-machine joint learning accelerates the acquisition of motor imagery brain computer interface control*，Nature Communications 17, 6177 (2026)，[DOI 10.1038/s41467-026-75435-5](https://doi.org/10.1038/s41467-026-75435-5) | 开放主文 Results/Methods/图说明；Supplementary Information 的方法 1–3、Table 1 及相关图说明；Reporting Summary 第 2–3 页图像核读；作者 GitHub 的 README、LICENSE、`updateModel.py`、`resources/modules.py`，固定 commit `57710f76a5ddd6f9a3aad28566ca55776a424400` | 未取得 Figshare EEG；未读所有 source-data 工作表；未运行在线反馈系统；未把当前 GitHub 版本当作已证实的原始实验运行版本 |
| L3，Rajeswaran et al.，*Assistive algorithms influence neural representations in motor brain-computer interfaces*，Nature Communications 17, 9832 (2026)，[DOI 10.1038/s41467-026-76109-y](https://doi.org/10.1038/s41467-026-76109-y) | 开放主文 Results/Methods/图说明；Supplementary Information 的 tuning、velocity、PR、模型 mode transformation 方法与相关图说明；Reporting Summary 第 2 页图像核读；公开 peer-review file 的统计争议段落；作者 GitHub README 和两个 demo notebook，固定 commit `571dfc0479b74a21f4b95bfda5671cf27d2ba36c` | 未取得完整历史动物 cohort；未运行 RNN、pickle 数据或 demo；未把公开 demo 认定为完整原论文分析；未逐条审读全部 peer-review 往返 |

主文全文暂存于 Git 忽略的 `data/literature_stage1/`；不把全文、原文图片或完整第三方实现提交到仓库。本文使用自己的方法释义，短引文仅用于定位公开来源的矛盾。下载、字节数和 SHA256 见 [补充材料访问收据](../research_logs/nature_joint_assistive_supplement_access.json)，作者代码的固定 commit、Git blob 与读取范围见 [代码阅读收据](../research_logs/nature_joint_assistive_code_metadata.json)，关键判断和 unresolved 的原文定位见 [核验清单](../research_logs/nature_joint_assistive_source_checks.json)。公开代码中的数值和 Notebook 已有输出不是本项目运行结果。

## 2. L1：先把“人学会了”与“系统分数提高了”分开

### 2.1 问题、研究对象和实验时序

L1 的问题是：能否同时引导初学者的 MI 策略探索及 decoder 更新，提高非侵入式 BCI 的训练效率？它不是只比较网络分类器。

依据 [Participants](https://www.nature.com/articles/s41467-026-75435-5#Sec11) 与 [Experimental paradigm](https://www.nature.com/articles/s41467-026-75435-5#Sec14)，主试验最终纳入 31 名健全 BCI 初学者（18 女，年龄 23.8 ± 4.42 岁）；联合训练 15、BCI2000 对照 8、触觉对照 8。另招募独立 EEGNet 对照 8 人，不能称为“所有对照一共只有 31 人”。

四个 session 所有主试验被试完成；21 人完成第 5–6 session（联合 8、BCI2000 7、触觉 6）。任务顺序为 S1–S2 左/右 MI，S3 混合左右及上下，S4–S6 2D。上对应双手 MI，下对应休息，因此 2D 不是四种对称 MI。超过两个月的长期测试包含联合 6、BCI2000 5、触觉 5，另做 L/R 与 2D session。发表日期不是采集日期；各 session 的实际日期间隔未在本轮逐受试者核验。

实验以 64 通道 EEG、1000 Hz、参考位于 Cz 与 CPz 之间、60 Hz notch、BCI2000 40 ms 数据包运行；公开实时代码 README 说明选取 62 EEG 通道。分析/复用时应记录“采集通道数”与“decoder 使用通道数”，不能将其混为一个数。

每个 session 的关键时序为：无反馈 calibration run → 无触觉但有视觉反馈的前测 run → 三个训练 run → 5 分钟休息 → 无触觉后测 run。L/R calibration/training run 60 trials，test run 30；2D 分别 64/32。每 trial 为 2 秒 fixation、5 秒 MI/视觉控制、2 秒休息。这里的 5 秒是该论文自己的任务定义，不能用来替代 NETBCI 的事件审计。

### 2.2 干预的真正成分

| 条件 | 用户侧政策 | Decoder 侧政策 | 可以和不可以隔离的因素 |
| --- | --- | --- | --- |
| 联合训练 | 同方向成对 trial；第一 trial 无刺激；上一 trial 在线 accuracy >70% 时第二 trial `copy`，否则 `new` 并给同侧触觉；上为双侧、下无触觉 | EEGNet，训练 run 后更新，样本重加权 | 完整组合效果；无法单独分离 contingent cue、pairing、感觉刺激和重加权 |
| 触觉对照 | 配对同方向，但无 copy/new；训练 trial 均触觉，不依前 trial 成绩 | EEGNet，run 后更新，无联合组的重加权流程 | 与联合组比较同时改变用户政策和重加权 |
| BCI2000 对照 | 无触觉、无策略提示 | 前六 session 固定 AR；长期测试改 EEGNet | 主阶段还混有 decoder 架构/更新方式差异 |
| 独立 EEGNet 对照 | 无配对、无触觉、无 copy/new | EEGNet，同 run-wise 更新预算 | 改善架构混杂的解释，但另批招募不能视为同时随机化的完整因素设计 |

“adaptive”在这项实验不是随每个窗口持续更新：模型在 training run **结束后**更新，run 内固定，online test run 不 fine-tune。前六 session 的模型继承上一 session 权重。长期实验的 weighted/conventional EEGNet **每个 session 从零初始化训练，不继承旧模型**。[Methods](https://www.nature.com/articles/s41467-026-75435-5#Sec14) 的这一点决定了它的长期行为证据边界。

无触觉前测/后测和延迟无触觉测试可以检验外部感觉辅助撤回后是否还能控制；它们不自动隔离 decoder 适配贡献。前后 test run 不更新模型，不表示两次 probe 使用同一个映射。长期重新 calibration 之后的高分也不同于“训练末的同一 frozen mapping 在延迟后仍可独立使用”。本文的结论是阅读边界，不是否定作者观察。

### 2.3 样本重加权数学逻辑及复现障碍

原文 [Joint learning framework](https://www.nature.com/articles/s41467-026-75435-5#Sec13)、Supplementary Table 1 将 sample 定义为 **1000 ms 窗口，步长 40 ms**，不是相互独立的 trial。预处理为 4–40 Hz、100 Hz、baseline correction。窗口高度重叠；统计时不能把窗口数量当成人数。

作者流程是：CSP+LDA 给训练样本初始置信分 → 取前 20% → 初始化 EEGNet → 按 true-label cross-entropy 从小到大排序 → inclusion ratio 逐轮由 0.2 增至 1 → 低 loss 窗口较大权重 → 加权训练。用自己的符号表示：

\[
\ell_i=-\log p_\theta(y_i\mid x_i),\qquad
r_i=\operatorname{rank}(\ell_i)/N,\qquad
\rho_t=\rho_0+(t/T)(1-\rho_0).
\]

训练目标为 \(\sum_i v_i\ell_i/\sum_i v_i\)，主文设 \(\rho_0=0.2,T=9\)。这使用了训练任务标签，不能移植为“无标签人类学习指标”，低 loss 也不能被定义为已产生技能。

复现前必须处理三项已经看到的来源差异：

- 主文初始分数为 \(\max_c p(c\mid x_i)\)；当前 `updateModel.py::cal_init_weight` 对预测错误的样本改用较小 posterior，binary 情况实际上重视 true-label probability。两个规则不是完全相同。
- 主文权重公式在最终 \(\rho_T=1\) 时有 \(\log(1-\rho_T)\) 边界；当前代码在 `round_size>=1` 用 \(\epsilon=10^{-2}\) 分支，并处理非有限/负权重。不能原样硬编码论文公式再声称可重现。
- 当前公开函数 `fit_weighted_eegnet` 默认 `rounds=8`、每轮最大 30 epoch；Methods 描述 `T=9`、maximum 300 epoch，且调用参数可变。本文只检查当前公开代码，不确定哪套参数对应原始每场实验；需要发布归档和运行日志进一步确认。

这是一种 self-paced/curriculum 更新思路；将其复制到新项目不构成独立创新，也不能据 offline gain 命名为 learning-preserving。

### 2.4 性能、神经指标与“学习”的操作性定义

原文 [Performance metrics](https://www.nature.com/articles/s41467-026-75435-5#Sec15) 的 online accuracy 是一 trial 中所有在线窗口正确控制的比例。PVC = hits/(hits+misses)，**排除 abort**；fPTC 将 abort 按最近目标作 forced assignment，再除总 trial。它们与本项目 offline balanced accuracy 不是同一种端点；NETBCI 百分比未知分母也不能按 PVC 的公式自造命中标签。

神经指标包括 C3/C4 的 8–13 Hz 和 13–30 Hz ERD/ERSP、topography、Grad-CAM 和 neural-change/decoder-gradient alignment。ERD 为 \(100(P-P_0)/P_0\)，ERSP 为 \(10\log_{10}(P/P_0)\)。主文神经结果明确比较了两种 baseline：−1500 至 0 ms 包含 instruction/触觉，以及 trial 前休息 −3500 至 −2000 ms。**刺激期 baseline 会改变 ERSP 的参照和解释**；不能把任意零均值化叫作同一 ERD/ERSP。

Supplementary Methods 2 实际定义：

\[
\Delta x_t=\bar x_{t+1}-\bar x_t,\qquad
g_t=\nabla_x f(x;\theta_t),\qquad
A_t=\Delta x_t^\top g_t,\qquad
\cos_t=\frac{\Delta x_t^\top g_t}{\|\Delta x_t\|\|g_t\|}.
\]

这里 \(g_t\) 是**输入空间 class-score gradient**，不是参数空间 \(\nabla_\theta L\) 或 decoder 权重变化。作者称 projection 的量未除 \(\|g_t\|\)，严格是依赖尺度的点积。正 cosine 是局部关联，不能证明人类神经可塑性沿优化权重轨迹因果发生；还需指定 class、gradient averaging、预处理尺度与零向量处理。本轮公开代码片段未包含完整 alignment 分析，未补猜这些细节。Grad-CAM 解释模型依赖什么，不直接测到神经元/突触学习。

论文行为学习端点包括 baseline 到后期 session 的 gain、训练后无触觉表现和延迟无触觉表现。它们支持“练习后的联合系统表现与撤除感觉引导后的持续表现”；主文更强的 plasticity 机制阐释仍依赖这些代理，不能直接搬成我们的结论。

### 2.5 随机化、样本量和统计单位：必须保留的 unresolved

主文 Participants 明写主试验随机分三组；但本轮图像核读的公开 **Reporting Summary 第 2 页 Randomization 栏写：“Participants were not allocated into experimental groups.”** 这与主文冲突。不能自行把它改成“肯定是填表错误”。目前仅能写：**主文报告随机分配，但公开 reporting 不一致，分配执行 unresolved**。

同页还写 convenience sampling、未 formal prospective sample-size calculation、研究者知道条件和假设；8 名额外人员因日程退出未纳入最终分析。这与“final31没有额外排除”可同时成立；不能写成没有任何失访。已刊统计的 empirical-data power simulation 不是事前样本量规划。

主文组间采用 rank-sum、重复测量 ANOVA、post-hoc Bonferroni，effect size \(r=Z/\sqrt N\)。不同图的单位必须分别看：Fig.1 的 n=15/8/8 是人；Fig.3 n=90/48、270/144 为多条 repeated records；Fig.4 有 n=29/20 等 session/task 记录、n=2700/1440 trials，长期 n=6/5/5 才是参与者子集。重叠窗口、trial、session 都不能直接充作独立人类样本。补充 Fig.12 的 pseudo-online 比较采用含 Subject 与 SubjectSession random intercept 的 mixed model，比独立汇总测试更接近层级结构；本项目优先 participant-level 或明示嵌套模型。

“长期 2D 差异不显著”不能严格证明 retention/等价：需要预设非劣效界值及足够精度。比较 session-best training 与最终 test 还涉及从多个 noisy training run 选最大值的选择效应；新研究应预定末端或平均训练端点。

## 3. L3：辅助是否改变 task information 的分布

### 3.1 生物学数据与干预时点

L3 的问题是：当 decoder 也在变时，神经回路将任务相关信息分配给哪些 readouts、哪些 population modes？这是侵入式动物 motor BCI，不是 human scalp EEG。

[Methods](https://www.nature.com/articles/s41467-026-76109-y#Sec8) 描述两只雄性 rhesus macaques J/S，在 motor/premotor cortices 用 128 microwire arrays 采集 multi-unit spikes/threshold crossings，控制 2D center-out cursor，8 个方向。J/S 的完整原始研究分别有 13/6 mappings；本文分析选取跨多天的 7/3 learning series，共 10 series。**10 series 不是 10 只独立动物。** Results 与 Methods 对 series 时长写法略有差异（至少四天/超过四天），最终具体 series/day 清单应以 Supplementary Table 1 和原始数据核实，本轮未重建完整表。

选择 readout 主要依据测量稳定性，非 target tuning；nonreadout 为同期测到但未用于控制的单位，stable readout 是全 series 一直参与控制的单位。任务成功要求 3–10 秒内到 peripheral target 并保持 250–400 ms；分析则纳入已到达目标的 trial，即使最后 hold 失败。**神经分析样本和奖励成功 trial 的定义不一样**；到达筛选会随训练成功率变化。

J 用 SmoothBatch、S 用 ReFIT 的 position–velocity Kalman decoder。初次 CLDA 5–15 分钟建立可用控制；后续当 success rate 掉约 10–20% 或 readout 丢失时，CLDA 3–5 分钟（1–2 次参数更新）。可仅改权重或换 readout 并改权重。系列初始 CLDA 强度本来有意变化，因此初始能力、测量质量、系列时长和更新次数并不独立。

fixed 比较来自另一历史研究的另外两只动物 P/R、**Wiener decoder**、两段 available series。公开 Reporting Summary 第 2 页明确：fixed/adaptive separate studies，decoder adaptation 不是该研究内随机条件，研究者未盲。早期 fixed 表现不足，作者将 first/last 150 trials 作为 epochs，adaptive 则比较 early/late day；两种时间聚合方式也不同。它提供比较线索，不是同架构、同动物、随机政策的因果估计。

### 3.2 Target decoding 与 compaction：数学定义决定命题

[Data analysis](https://www.nature.com/articles/s41467-026-76109-y#Sec12) 将 spiking 活动按 100 ms bin，go-cue 至 1800 ms；短 reach 零填充。以 multiclass logistic regression 预测 target，8 类，每个 direction 随机取 25 trials，总 200 training trials/day，剩余作为 test。L2 regularization、C=1、max_iter=1000。这里不是让后期同一 frozen classifier 去预测 early/late，而是每个 day 重新拟合，量化当日 task information。

Neuron-adding curve（NAC）的程序是：单 unit LR accuracy → 按信息从强到弱排序 → 逐步加入 units → 得到 \(a(k)\) → 将 accuracy 按当天峰值做 linear normalization → 找最少达到 0.8 的 units 数 \(N_c\)。Compaction 为 \(\Delta N_c=N_{c,late}-N_{c,early}<0\)。它表示达到**相对当天可解码上限**的信息所需单位数减少，不表示总体方差更小，也不表示神经功能变差。

Combinatorial NAC 检查全部同大小组合、包括/不包括 leading units 的 accuracy 分布，区别“所有少量组合都更有效率”与“只有特定少数 units 重要”。原文这里用的判别指数是 \(d'=|m_1-m_2|/[(s_1+s_2)/2]\)，不是可随意替换的 pooled-variance Cohen's d。

PC adding curve 则先在 early/late day 分别 PCA、保留所有 modes，再按单 PC **target-predictive score**排序形成 curve。高/低方差对照按 explained variance 上下各一半划分。最强 predictive PC 可以不是最高方差 PC；unit-level 与 mode-level compactness 也不是同一数学属性。

Supplementary Methods 的参与率明确为：

\[
PR=\frac{[\operatorname{tr}(C)]^2}{\operatorname{tr}(C^2)}
=\frac{(\sum_j\lambda_j)^2}{\sum_j\lambda_j^2},\qquad
PR_{norm}=\frac{PR-1}{n_{units}-1}.
\]

不是 \(PR/n_{units}\)。若 day-wise z-scoring，则 PR 反映标准化后的 covariance/correlation；de-mean 原始信号所得 PR 是另一度量。作者区分 total covariance PR 与既往 factor-analysis shared dimensionality。补充材料 PR 抽样按 target 分布匹配、trial 有放回重采样。对 EEG 需同时记录 scale/reference、rank-deficiency、shrinkage 和通道数；平均参考造成的秩约束不能被读成学习。

### 3.3 受控 RNN 解决哪一层因果问题

[Model](https://www.nature.com/articles/s41467-026-76109-y#Sec20) 是 100-unit RNN，先学 arm reaches，再随机取 12 个活跃 readouts 拟合 velocity KF，切换 BCI。REINFORCE 更新 W/U/b，F/V 固定；10 seeds，匹配初始参数和随机数。Kalman CLDA 对 \(X\in\{C,Q,m\}\) 作：

\[
X\leftarrow\alpha\hat X+(1-\alpha)X.
\]

\(\alpha=0\) 是 fixed。模拟每 day 都 CLDA（每 target 见 100 次），实验则因性能下滑触发。较高强度会让 CLDA 朝目标转向的局部目标与最终到达且速度归零的任务目标冲突；停止更新或降低更新频率是模型可检验的 ablation。RNN 的策略干预可以回答**该模型中 decoder update 是否导致 compaction/不同权重学习**，不能替代动物体内突触机制，也不能证明 human EEG 长期控制能力受损或被保留。

这篇论文的重要反直觉点是：辅助适配可能同时提高表现、使 task information 集中、保留整体 dimensionality；不能预设 compaction 是坏事。新项目需要脆弱性、transfer、撤回辅助与 retention 端点，才可评价好坏。

### 3.4 统计与公开 demo 的边界

原文早晚 signed-rank 多以 10 series 为样本；series within animal 的依赖不能因为数量变大而消失。模型 CI/SEM 的独立单位是 10 seeds，动物结论的生物学独立单位仍是 2 只。重复 split CI 描述数据划分造成的波动，不能充作动物/人群 generalization CI。early/late label permutation（B=10,000）还须说明 exchangeability/时间依赖。

本轮发现 **正文 Methods 写 100 training–test splits，Fig.3/Fig.5 caption 写 \(10^4\)**。公开 demo `compactness.ipynb` 当前设 `n_bs=10 #100`，不解决正式版本的差异；保留 unresolved。公开 README 明确 demo sample 不能准确复现论文图，完整 code/data 需请求；不得把 demo 跑通冒充整篇复现。

对 current demo 的源码阅读还看到：units 按 CV test score 排名，再用同一个 split 评估 NAC。ranking 与 evaluation 共用 test information 可能使绝对 predictive curve 乐观；完整原论文是否有独立 nested ranking，本轮无法证明。EEG 迁移时应在 inner training/validation 排名、outer run 测试，并记录 selector 和 classifier 的 data access。原文每 day PCA、test set 单独 z-score 也与我们的 frozen transportability protocol 不同；可作为描述性当日信息分析，不能移植成完全冻结的跨天预测流程。

公开 peer-review file 中也讨论 fixed cohort 只有两段 series、统计功效和模型不足；这些讨论帮助定位风险，但**最终主文/SI 才是已刊方法的主要依据**。不把审稿人的问题当作作者承认的确定结论。

## 4. 仿照研究思路时，我们自己的研究链条应是什么

可以借鉴的不是原文措辞或结果排列，而是它们把一个系统效果拆成机制与可证伪端点的方式：

| 原文逻辑 | 适合本项目的转换 | NETBCI 现阶段的证据边界 |
| --- | --- | --- |
| L1：training score → 无感觉辅助 probe → 延迟 probe → neural signature | 同时记录在线行为、decoder version；用统一 frozen reference mapping 做训练前/后及 delayed no-assistance probe；另报当前 decoder 的 assisted performance | 当前公开单被试没有已核实 trial outcomes/decoder日志/冻结映射延迟 probe，不能复现 retention 命题 |
| L1：用户信号变化与 decoder 输入敏感方向的关系 | 在相同输入坐标冻结 reference decoder，预定义 class score/尺度，分析变化与 frozen sensitivity；加负对照 | 只能是 signal/model 关联；没有 feedback 随机干预不能证明机器促进人学习 |
| L3：总体 variance 与可预测 task information 可分离 | 同时分析 Mu/Beta PSD、协方差、PCA 与 independently evaluated class information；检查低方差 modes，匹配 trials/run、reference、伪迹 | 能研究 longitudinal signal organization，不把 EEG channels 解释为单神经元 readouts |
| L3：fixed/adaptive 历史观察 → 匹配模型干预 | 离线冻结 decoder 与同预算校准仅评价算法；未来人体随机并行条件保持架构/反馈相同，只改变 update policy | 离线 update 后 label accuracy 没有改变人脑，所以不能回答对技能的因果效应 |

**可以形成独立切入点的候选问题**是：跨 session 的 total EEG geometry、task-predictive directions 与 frozen-reference generalization 是否发生可重复的分离？哪些变化属于测量/伪迹，哪些与真实无辅助行为有关？在后续在线实验中，update policy 的约束究竟提高 retention，还是只是保留了稳定但不够可控的信号？这些问题有明确的零结果和反向结果，才具有研究价值。

现阶段不提出“稳定性惩罚必定保留学习”算法。先做 matched-data geometry 与冻结 baseline；将 representation stability、可解码信息、online hit/abort/time、辅助撤回、长期 probe 列为不同端点。经过多被试复制与行为对齐后，才选择一个数学约束并与 conventional adaptation 做预算匹配的比较。

## 5. 写作中可采用的准确措辞与下一步决策

- 文献背景可写：感觉引导的人机训练、几何相容性与算法引发的表征变化说明，应同时研究 decoder 和用户，而不以训练准确率作为唯一学习端点。不能写三篇已经证明本项目算法。
- 当前个人论文的实证部分应写 **longitudinal EEG representation and fixed-reference decoding**；“Learning-Preserving Co-Adaptive BCI”是总体研究方向，尚不是已验证机制或算法名。
- 目前单受试者 findings 为 exploratory within-person observations。717 是当前四 session 子集的 events；不等于 NETBCI 全体样本，不等于 717 名独立学习证据。
- 对 H3/H4 的在线因果验证，先做同架构、同初始能力和更新预算的随机并行组，避免 skills 学习 carryover 使 crossover 无法洗脱；训练中安排低频 frozen-reference no-assistance probes，末端及延迟 retention/transfer；记录预定 trial IDs、feedback/abort、scores 的精确分母、mapping snapshots、sensor/疲劳质量。
- 人体样本量按参与者层级、预设行为主端点与非劣效/优效界值规划；不能照搬三篇的 n，不能用 n=1 的点估计作群体效应保证。新 online study 的伦理、招募、付费设备/资源不属于本轮已执行工作。

本轮没有改写两篇 Nature 的文字作为个人论文，没有把它们的数值填入自己的 Results，也没有替 unresolved 行为补造标签。下一步依赖本仓库真实 NETBCI 分析与三篇文献共同确定的证据缺口，形成有引用、有限定的原创 working manuscript。
