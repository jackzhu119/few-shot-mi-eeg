# NETBCI：已有行为记录与纵向 EEG 的会话层分析

日期：2026-10-10。状态：真实数据的探索性分析；已看到 stage-1 结果后开展，非预注册、非因果实验。
本轮无需联系作者来取得已经公开的成绩。**subject/session 行为关联已可执行；run/trial 关联仍 unresolved。**

## 1. 本轮实际分析的资料

| 数据层 | 当前核验范围 | 本轮允许的分析 |
| --- | --- | --- |
| 原始 Dataverse v2.2 participants.tsv | 19 个唯一受试者 × 4 session × 6 个已发布 run 命中率；456 个有限百分比，76 个会话，无缺值；官方 MD5 b9aa1c07015820e80bc79be6a61f30fc 匹配 | 每受试者/会话的无权成绩摘要，19 人的行为轨迹与个体变化 |
| 原始 participants.json | 官方 MD5 41b33bc709e7b36a14faa91da128aaba 匹配；字段明确描述每 run 的光标 target-hit 百分比 | 指标语义与 session 字段定义；原文件有尾逗号，保留原始字节并记录严格 JSON 解析失败 |
| NEMAR nm000305 v1.0.0 EEG | 仅 sub-1，对应原始 sub-01，4 session/24 run/717 trial，74 通道、250 Hz | 单人的任务频谱、协方差/PCA 与已有冻结模型结果 |
| 跨版本身份 | 24 原始头文件 hash、事件/marker 顺序与 NEMAR provenance；既有审计通过 | **4 行 subject/session 一对一 join**，并非 24 run 或 717 trial 的行为标签 |

19 人行为侧表不等于已读取 19 人 EEG。没有新增信号下载，没有重新训练模型。先核验历史 stage-1 的全部 source/input/artifact hash，再使用其保存结果。

官方来源：原始数据 [10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7) v2.2，EEG derivative
[10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)，CC BY 4.0。
两个版本只在已验证身份层连接；未把其采样、duration 或 trial/outcome 格式当作完全相同。

## 2. 为什么现有数据足以做会话层行为分析

原始字段 `BCI-Performance-session1..4` 各含六个已发布百分比。会话分数定义为这六个值的无权平均：

`B(subject, session) = mean(the six published run percentages)`。

该均值与向量排序无关，所以未解决的 run 顺序不阻止会话分析。它不是把所有 trial 合并后的命中率；各 run 实际评分分母尚未知，不能按 29/30 个 EEG 事件加权、补 hit/miss 或做二项 trial 模型。输出同时保留原始字段、源行、原始字面值、向量位置、均值、中位数、run 间 SD、极值及会话变化。位置只表示原始存储位置，不宣称是 EEG run ID。

代码拒绝重复键、未验证 subject map、缺失 session，以及将会话成绩广播到 EEG run/trial。run 顺序、评分分母、逐 trial outcome 和光标轨迹继续明确标为 `unresolved`。这不再作为会话描述的前置阻塞。

## 3. 19 人真实行为轨迹

| Session | 平均会话成绩 % | 受试者中位数 % | 平均值的受试者 bootstrap 95% 区间 |
| --- | ---: | ---: | --- |
| 01 | 54.11 | 53.83 | 50.93–57.67 |
| 02 | 56.74 | 53.83 | 51.98–62.25 |
| 03 | 62.15 | 58.89 | 57.22–67.34 |
| 04 | 68.68 | 69.44 | 63.06–74.28 |

末次减首次的平均变化为 **+14.5684 个百分点**，中位数 +14.9983，个体范围 −6.8650 至 +27.7133。
18 人末次高于首次，1 人降低（sub-17）。配对受试者 bootstrap 95% 区间 **[10.7063, 18.2662] 个百分点**。
重采样单位为 19 个完整四会话轨迹，seed=42，10,000 次；没有把 456 个百分比或 EEG trials 当作独立受试者。
该区间刻画公开样本的观察性行为变化，不是训练、学习或新算法效果的因果区间，也不含未知成绩分母的不确定性。

只有 4 人每次都严格增加；5 人没有会话下降，14 人的发布均值至少有一次下降。
其中 sub-03 的下降仅约 0.00167 个百分点，属于源百分比舍入敏感范围；若要求下降超过 0.01 个百分点，则为 13 人。
计数采用 1e−10 个百分点的纯数值容差，避免把求和顺序产生的约 −7e−15 当作下降。不能把末次提升写成每个人单调学习。

**这些是真实在线行为成绩，但变化来源仍可能包括练习、策略、疲劳和会话解码器重校准。**
没有随机干预、固定评价映射、辅助撤回或可靠延迟保持记录，因此不能把这条曲线单独解释为神经技能形成或保持。
在线 target-hit 的机会水平也未知，不默认是 50%。

[19人行为轨迹与个体变化图](../research_logs/netbci_behavior_sessions_20261010/figures/behavior_cohort.png)。

## 4. 当前有 EEG 的受试者：会话对应已经完成

| Session | 已发布六 run 平均命中率 % | EEG trial 数 | QC 标记数 | 冻结 CSP BA % | 3-epoch EEGNet BA % | AIRM（匹配144） | PCA 子空间距离 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 73.80 | 180 | 0 | 60.00 | 50.00 | ≈0 | ≈0 |
| 02 | 90.48 | 179 | 0 | 50.00 | 55.67 | 6.682 | 0.675 |
| 03 | 85.08 | 180 | 2 | 50.00 | 54.00 | 6.503 | 0.664 |
| 04 | 89.28 | 178 | 53 | 50.00 | 45.00 | 8.719 | 0.671 |

sub-01 在 19 人中四会话的行为均值均排名第 1。这是当前样本的描述，不说明我们事先按成绩选人；它说明单人 EEG pilot 特别不能代表队列典型表现。

行为摘要覆盖六个已发布 run 百分比；解码器 query 仅首次 run05–06 的60 trial，以及后续 run02–06 的149/150/148 trial；几何分析使用全部六 run 的类内匹配抽样。
表中只是会话级并列，**不是相同 trial 集合上的指标比较**。冻结模型与历史在线模型也不同，不能将在线命中率减离线 BA 称为“学习增益”或“辅助贡献”。

冻结 CSP 在后三会话恒预测 rest。其 50% BA 是模型退化/可迁移性失败案例，不是人类失去控制技能的证明；后期的高在线成绩也不证明某个固定神经映射被保留。
EEGNet 只有三 epoch CPU 流程验证，不能作充分训练的架构结论。已有 conditional run-bootstrap CI 保留在会话表：不是参与者级泛化 CI，源拟合不确定性没有纳入。

全 run 匹配144时，协方差距离末次最大；共同 run03–06、QC 未标记、每类每run12 trial（96/session）时，后三会话平均 AIRM 为 **8.295/8.409/8.507**。
选择和质控改变了差异排序与大小，不能把漂移幅度直接当作学习幅度。PCA 后三会话距离均约0.66–0.68，更像“与首次不同”而非已经建立线性进步尺度。
20 次抽样只衡量计算/抽样敏感性，不增加独立参与者数量，也不是生物学重复。

原始在线 channel/frequency 配置字面值随会话变化，通道数字不能猜测映射；该字段不是逐次decoder更新日志。
sub-01 的 STAI 只有首次=31，后3次为NA，不能据此调整此人的焦虑或解释疲劳。
[分开端点的六面板图](../research_logs/netbci_behavior_sessions_20261010/figures/pilot_behavior_EEG_endpoints.png)。

## 5. 新的任务相关频谱观察

使用已保存真实 `trial_features.tsv`：C3/Cz/C4 ROI 的积分功率，CAR，Mu 8–13 Hz、Beta 13–30 Hz，任务起点后 [0.5,4.5) 秒，Welch 参数沿用已验证 stage-1。
先在每 trial 对 ROI 功率取 log10，再分别按 label/run 求 trial 均值，再对规定 run 等权平均。
任务差异为 `10 × (mean_log10_P_MI − mean_log10_P_rest)` dB，即两类几何平均功率比的 dB。
同时保存“等run的算术平均功率比”敏感性；二者不是同一个估计量。
功率表明确 V² 与显示 μV² 的1e12换算；dB 对比不依赖这个单位换算。

| Session | Mu 任务差异 dB：全六run | Mu：共同四run且QC未标记 | Beta：全六run |
| --- | ---: | ---: | ---: |
| 01 | −0.792 | −0.776 | −0.468 |
| 02 | −1.058 | −1.135 | −0.818 |
| 03 | −1.857 | −1.886 | −1.161 |
| 04 | −2.197 | −2.102 | −0.919 |

Mu 的 MI 相对 rest 功率差异逐会话更负，Beta 并非同样单调。
共同四run未标记版本保留120/119/120/114 trial，尚非等trial；额外执行每run每类12个未标记trial、96/session、20种seed的计数敏感性：

| Session | 匹配96的 Mu dB 均值 | 20次抽样的min–max（非CI） |
| --- | ---: | --- |
| 01 | −0.848 | −1.000至−0.529 |
| 02 | −1.083 | −1.385至−0.886 |
| 03 | −1.904 | −2.216至−1.648 |
| 04 | −2.084 | −2.285至−1.891 |

末次比首次更负的方向在这些已执行敏感性中保留，值得多受试者核查；会话03与04抽样范围重叠，不宣称每一步都可重复区分。
这不是 baseline-normalized ERD：没有已验证 prestimulus baseline，窗口还包括 target/feedback。
没有检验真实运动/EOG/EMG、视觉反馈、历史mapping和接触质量的充分控制，不能称神经学习效应。
粗QC未标记也不等于无伪迹。当前没有对时间点、通道或频段作显著性筛选。

还需避免把相对差异误写成绝对MI功率降低：全六run的Mu几何平均功率，rest为
**3.103/4.690/5.311/5.925 μV²**，MI为 **2.585/3.676/3.463/3.572 μV²**。
两类末次均高于首次，rest上升更多；所以更负的MI/rest对比可能受到rest状态、总体幅度和测量差异影响。
它不能单独称为更强的MI抑制、ERD或神经技能进步。
[绝对功率、PCA与QC诊断图](../research_logs/netbci_behavior_sessions_20261010/figures/pilot_representation_diagnostics.png)。

## 6. 科学解释及可检验方向

已有证据表明三个观测量需要分开研究：历史在线 target-hit 成绩、任务相关 EEG 结构、以及早期冻结模型的可迁移性。
在线成绩较高、Mu 任务对比更负、旧 CSP 退化可以同时发生；它们并不矛盾，因为评价映射、计分规则和样本集合不同。
本轮仅有一名 EEG 受试者的四个相关会话，不计算神经—行为相关的显著性或回归，不将四点当成四个人。

H1（表征变化与分类成绩不等同）获得具体探索线索；H2（漂移与独立读出性能关联）目前没有足够样本可靠检验。
H3/H4 的自适应策略因果问题仍不能由这份离线记录检验。尤其不能以“限制所有漂移”为preservation目标：旧映射不可读也可能伴随有益的新控制策略。

参考三篇精读中的设计，应优先关注 task-relevant information 与 global covariance/subspace 的区别，而非只追逐一个 drift 最小化指标。
可借鉴 Wang 的独立反馈条件/保持测量、Busch 的mapping compatibility问题、Rajeswaran 的任务信息与整体维度区分；它们各自的对照与模态限制仍适用，引用技术并不构成独立创新。

## 7. 下一阶段决策

1. **已可开展会话级 EEG—行为研究，无需先取得已有成绩。** 本轮已经实际建立四行连接。run/trial精细问题保留，不制造对应。
2. 当前最有价值的离线问题是：多参与者的任务频谱差异、global geometry及冻结读出可迁移性是否分离，以及其会话内/跨会话可靠性。先固定QC、参考、窗口、类平衡、时间划分及模型失败报告规则。
3. 在后续明确扩展数据范围时，以行为表的全部参与者为抽样框，小批次选择预先规定的不同轨迹，避免只选高成绩；完整cohort优于只做极端组。当前没有新增其他人 EEG。
4. 下一轮先完善source-only调参的CSP基线与任务信息测量、伪迹/reference敏感性和split-half可靠性，再决定是否充分训练EEGNet；不能用三epoch模型结果预设算法优势。
5. 仅在研究需要run内反馈或trial成败时，才进一步核查日志或准备具体作者问题；run次序/分母未验证不阻塞本轮会话分析。未发送邮件。
6. 要主张Learning-Preserving策略有效，仍需合适的前瞻在线人体对照：同架构/更新预算/反馈条件，记录所有mapping更新，冻结训练结束后已学会的mapping做无额外辅助即时/延迟保持，同时区分早期mapping的transfer probe。离线观察不能替代该因果证据。

## 8. 重放、修正与文件

当前权威输出：[run03_verified](../research_logs/netbci_behavior_sessions_20261010/run03_verified/analysis_summary.json)；
[会话join](../research_logs/netbci_behavior_sessions_20261010/run03_verified/linked_EEG_behavior_sessions.tsv)、
[19人行为会话](../research_logs/netbci_behavior_sessions_20261010/run03_verified/behavior_sessions.tsv)、
[任务频谱](../research_logs/netbci_behavior_sessions_20261010/run03_verified/task_bandpower_contrasts.tsv)、
[等trial敏感性](../research_logs/netbci_behavior_sessions_20261010/run03_verified/matched_task_bandpower_contrasts.tsv)。
第二次独立执行run04_replay的11个计算结果/源码快照逐字节一致；[重放收据](../research_logs/netbci_behavior_sessions_20261010/replay_verification.json)。

run01/run02是保留的中间执行，浮点零变化计数修正前错误列15人“至少一次下降”；正式结果为14（舍入敏感性13）。
它们未覆盖，旧代码/配置快照按原运行收据SHA归档。失败/修正原因明确记录，不能引用它们的错误计数。
最新每run自动保存脚本/配置/行为模块快照及输入、输出SHA、Git dirty状态和实际依赖版本。

[已执行notebook](../notebooks/netbci2026_behavior_sessions.ipynb)与[离线HTML](../notebooks/netbci2026_behavior_sessions.html)
仅加载真实保存结果，不重新训练。5个代码单元自上而下执行、0错误、3个嵌入图；原生图已目视检查，未声称完成全页浏览器截图。

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python scripts/analyze_netbci_behavior_sessions.py \
  --config configs/netbci_behavior_sessions.json --output /workspace/scratch/netbci_new_session_analysis
```

输出目录必须不存在，避免覆盖已验证结果。本轮没有新增模型拟合、EEG下载、付费资源、第一篇仓库修改或新人体实验。
