# 论文2数据版本与可复用证据清单

核对日期：2026-10-29（Asia/Shanghai）。本次只读取已有报告、CSV/JSON、代码与文件hash；没有读取EEG/模型张量、fit、forward或新bootstrap。

## 先区分“数据集”“分析版本”和“文稿副本”

当前稿件涉及 **2套原始采集数据**：Kumar2024（NEMAR nm000177/v1.0.5，18人×6会话）和BNCI2014-001（9人×2天，官方MAT、NEMAR nm000139/v1.0.3固定hash）。18人已经包括6名开发参与者与12名原主要比较参与者；V2/V3反复使用这6人，不新增参与者。两套数据分别统计，不能用模型/seed/会话重复数扩大独立样本量。

按科学执行身份可分 **6个证据层**，而不是6套独立人群：

| 层 | 真实范围 | 现有结果 | 与前层关系 |
| --- | --- | --- | --- |
| 原Kumar CPU三基线 | 18人，其中原主要12人；source40，support19/20 | 原主要Full−Frozen +7.42pp [2.49,12.48]；原次要Full−LDA +5.47pp [2.17,8.91] | 原终点和区间保留 |
| 原54个EEGNet源模型及冻结query | 同18人×3seed；source40+validation20 | 剩余12人source-query约52.92%，target51.58% | 54是模型数，不是54人；冻结目标标签0 |
| 原实现component follow-up | 同18人；4/8/12/16/full预算；4种经典方法，另有phase/gain探针 | 1800cell、78600保存预测；剩余12人full-support EA−Full +5.30pp [2.81,8.26] | 已见数据探索层，原MNE实现、source40；并非V2六人结果 |
| HPC V2 | 原开发6人；6classic+18neural=24任务 | 8个经典臂、4个神经臂、5预算；18个新CompactEEGNet源模型和1350适配阶段 | 使用新架构/固定收缩实现，不是重启原54模型 |
| HPC V3 | 同开发6人；126任务 | 复用18个V2源、新训练3个池化源；10392预测文件；BN/KL/Dropout/几何/模拟控制 | 不新增人；384×50×9模拟为独立非人体层 |
| BNCI固定外部比较 | 9人、source96、support20、query120/人 | Full−LDA +0.19pp [−1.85,2.13]；EA−Full +5.65pp [3.15,8.70]、Holm p=.01172，9/9正 | 另一采集数据；固定V2 NumPy实现，统计与Kumar分开 |

## 对本轮重构最重要的现有遗漏

### 原Kumar也已有严格support-only EA与完整预算曲线

已直接读取原始文本证据目录：

`/workspace/private_model_receipts/paper2-component-followup-20261016/budget_cpu/run01/`

文件`query_predictions.csv`含78600行；`session_metrics.csv`含1800行；`fit_access_audit.json`含1980条（包括额外half-support审计）；`source_support_trial_provenance.json`保留源/支持身份。四份文件完整SHA均与原execution_receipt的outputs逐一匹配。

本次逐条验证 **90个full-support EA拟合cell**：

- source reference恰好40个原source TRAIN试次，仅ses0/run0与run1；run2 validation未进入拟合。
- target reference恰好当前ses/run0的19/20个support，逐一等于provenance；不含query或未来会话。
- EA、Full与LDA-only的source/support fit-ID列表逐项一致，且与query不相交。
- 四臂在90个subject×session的有序query trial ID与label完全一致。
- 原remaining12有60个目标cell：50个support20、10个support19，共2625个不同target query试次。
- 全预算1800cell无fallback。原执行结束码0的operation状态仍保留“pending independent audit”；本清单未编造新的父确认或改accepted字段。

实际代码仅使用source和support估计参考：固定21×22 Helmert CAR基、非trace的中心化ddof1协方差、均值的float64对称eigh逆平方根；source/support分别变换，query仅用已冻support参考。后续为CSP4/Ledoit-Wolf/log-average-power/norm_trace=False以及LDA lsqr/auto-shrinkage。该脚本及所有源代码pin均与原receipt一致。

公开复核副本在`research_logs/paper2_hpc_v2_20261023/existing_evidence/`。保存的剩余12人full-support行是：

- EA BA=70.65681084896148%，Full BA=65.35874168179069%。
- EA−Full=**5.298069167170802pp**，点态95%bootstrap区间**[2.8091695654365805,8.263953165960878]pp**。
- 10人提高、2人降低；这是事后暴露探索性点态区间，不是新增多重校正检验。

原执行commit `f59b14d45419ade50657f554585369eae4cd4d4b`；完整receipt SHA `1c90633fbea3b09966913363e28b40f5edf8050cf8eab3241736d8ba9a700012`；配置SHA `31720a71619281a0f1b2c4162b6bfa28582faae7d074be311e7b5cc9582df88c`。更多文件hash和原operation状态见同名JSON。

### 任务阶段敏感性也已真实完成

同公开快照含`phase_original_REPORT.md`和`phase_cohort_paired_contrasts.csv`。已有540个cell/11460保存预测，444 defined、96 undefined；原remaining组conditional n=9与metadata-complete n=8分别保留。条件n9的Full−Frozen在cue5s为+2.06pp [−3.73,8.17]、task-start2s为+3.21pp [0.08,6.56]；二者配对gain-change为+1.15pp [−5.55,7.22]。因此不能把单独task2s区间为正解释成窗间差异成立。

最终报告仍有980/7200事件未映射，且anchor、长度、过滤边缘与trial-eligibility同时变化。可把原稿“marker全都 unavailable”的绝对措辞更正为部分映射、覆盖有限；不改原5秒主终点，也不凭此判定原切窗错误。

## 用户截图中已过期的判断

1. **“完整标签预算曲线尚缺”已过期。** 原18人4/8/12/16/full已完成；V2/V3也有4/8/12/16/20曲线。精确2/5/10/15标签不在这些冻结结果内，无需为这次写稿另跑。
2. **“EEGNet只有冻结参考”已过期。** 原54模型确为冻结参考；V2/V3已完成head/full/L2-SP及BN/Dropout/KL等适配控制。
3. **“EA只有V2六人证据”不完整。** 原MNE/source40的18人component-followup已有，剩余12人+5.30pp可与BNCI+5.65pp分别展示。
4. **“原事件全未映射”不完整。** 已有部分GDF阶段映射及2秒task-start敏感性，但覆盖与解释边界仍需准确表达。

## 文稿版本不是新增数据

现存文件可按三代阅读：原PLOS提交支持版（2026-10-19）、BMT discovery/review/Skill修订（2026-10-27起）、BMT双作者投稿准备版（2026-10-28）。PDF、Word、阅读版、上传版和ZIP是同一科学证据的展示副本。此次新增第三作者及结构修订应形成新的2026-10-29审阅版本，不覆盖旧批准范围。

## 无需新训练的重构路径

把主线定为 **固定短校准标签下，分类决策层、空间滤波重学和support-only对齐各贡献多少**。先报告原主要Full−Frozen，再以同标签Full−LDA定位原Kumar空间增量；完整预算曲线说明其随支持量的变化；prediction-transition与逐人/逐会话表解释净收益；原Kumar EA−Full +5.30和外部BNCI +5.65分别展示空间对齐作用。V2/V3的神经与几何控制承担补充组件解释职责，不写成不断试模型的项目流水账。

这个证据组合支持独立的计算组件分析，而不是把既有CSP、EA或第一run校准包装成新发明。原主要/次要身份、原区间、负结果和实际失败留在对应结果/补充/审计层；不需要重训54、重读query或新OT实验。
