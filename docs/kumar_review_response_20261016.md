# 2026-10-16 逐条审稿回应与修订依据

本文回应投稿前内部审阅，意见均作意译，不转载私有审稿全文，也不表示已收到期刊决定或已投稿。核查对象为既有保存结果、公开政策与原始文献；本轮不增加 EEG 数据、模型训练或真实 query 推理。原主次比较、参与者、失败、负结果与既有区间均保留。

修订源文件：[主稿](../manuscript/kumar_plos_one_submission_draft_20261016.md)、[S1 Text](../manuscript/kumar_plos_one_supporting_methods_20261016.md)、[S2 Text](../manuscript/kumar_plos_one_audit_reproducibility_20261016.md)、[作者工作表](../manuscript/kumar_plos_one_author_worksheet_20261016.md)。以下按章节定位，避免将排版前行号当作固定页码。原 Tables 1–4 的数值不变；新增 Table 5 单列审稿后探索性检验。

## C1：当前二次分析的伦理依据

**判定：部分正确。伦理依据尚未解决的提醒成立；所有公开去标识二次分析一律必须取得新书面 IRB 认定，以及必然被退稿的断言，超出已读政策。**

PLOS 要求如实报告适用的伦理审查、同意与豁免情况；若未取得批准，应具体说明为何不需要。其[人类研究政策](https://journals.plos.org/plosone/s/human-subjects-research)允许符合适用伦理委员会法规的豁免；[投稿指南](https://journals.plos.org/plosone/s/submission-guidelines)并未规定每项公开数据二次分析都须取得新的机构书面决定。这也不使本项目自动豁免。

原研究 UT Austin 2020-03-0073 与书面知情同意已从原作 Methods 核实，但只描述原始采集。作者尚未提供本次使用适用的机构或法规依据；不补造批准、豁免、waiver、无需审查结论、编号或日期。

**修订位置：**主稿 **Data source, original study and ethical status** 与 **Author contributions and declarations**；S1 **S7**；作者工作表第 1 项。机构适用依据和最终伦理声明仍须作者据实完成。取得真实书面回复是消除不确定性的可行方式，不被写成期刊对所有同类研究的统一要求。

## C2：公开访问、持久标识与许可

**判定：部分正确。应确保最小数据覆盖、版本可追踪和许可清楚；“S1 Data 仅在本地/私有备份”“必须先铸造新 DOI”“必须合并 main 才可公开”不成立。**

本轮对固定提交 `a78372db00cd4161e713ab47aca2d93c643a52bb` 中的旧版 S1 Data 作无认证 HTTPS GET，返回 200、591,742 bytes，SHA256 为 `797d0e4c2f913428b864688cebcf182f65e022f2fcd7e5225cd919701740867b`，与本地旧包一致。因此旧版支持数据已有公开访问事实；私人备份不是其唯一位置。

[PLOS 数据政策](https://journals.plos.org/plosone/s/data-availability)允许支持信息承载最小数据；仓储标识可用 DOI、accession、code 或其他持久标识。[代码共享政策](https://journals.plos.org/plosone/s/materials-software-and-code-sharing)鼓励带 DOI 的仓储与开源许可，不能把“鼓励”改写成每篇研究论文初投前必须铸造代码 DOI。固定提交可以定位版本，但不能据此保证永久托管或概括已满足一切仓储条件。是否合并 main 是发布选择，不是公开访问的必要条件。

旧包覆盖检查还发现，已有预测、训练和 QC 表并未完整承载正文中每类可靠性及 drift 诊断。新修订补入这些**已保存的数值记录**及本轮检验的输入、定义、脚本和输出；不把缺口误写成旧包不存在，也不把新增打包误写成新实验。新版实际公开的提交、文件与哈希由最终发布清单及读回记录确认，不从旧版公开访问外推。

作者已经明确选择并激活限定许可：原创项目代码 MIT，原创稿件、图和派生结果 CC BY 4.0；源数据、第三方软件、字体、CSL 和参考材料保留各自权利。许可选择**不再待定**，也不构成对全部环境、原始 EEG 或第三方文章的整体再许可。见 [LICENSING.md](../LICENSING.md) 和 [LICENSES](../LICENSES/)。

**修订位置：**主稿 **Data and code availability**；S1 **S10–S11**；S2 **Reproducing saved numerical results**、**Public availability and licensing**；作者工作表第 2 项；新版 S1 Data 的 dictionary、复现说明和成员清单。不宣称已铸造新 archive DOI、已投稿或获得接收。

## M1：增加配对检验及其解释

**判定：部分正确。补充透明的参与者级检验有价值；区间排除零与任意配对检验等价、补检验可升级为确认性结论的说法不成立。**

使用保存的参与者端点，固定四项比较；对 12 人穷举 4,096 个符号组合，对 10 人穷举 1,024 个组合，统计量为配对差均值的绝对值。BA 单位的绝对边界容差为 `1e-12`，相对容差为零。该符号翻转参考分布要求独立参与者差值在零假设下具有符号对称性；这不是由随机分派支持的随机化试验，也不是无假设的总体均值检验。

| 固定比较 | n | 原均值差及 95% percentile 区间（百分点） | 双侧 sign-flip p | 四项 Holm p |
| --- | ---: | --- | ---: | ---: |
| Full refit − frozen，主队列 | 12 | +7.42 [2.49, 12.48] | 0.01953125 | 0.05859375 |
| Full refit − LDA-only，同一主队列 | 12 | +5.47 [2.17, 8.91] | 0.01025390625 | 0.041015625 |
| LDA-only − frozen，同一主队列 | 12 | +1.95 [−0.98, 5.09] | 0.26123046875 | 0.26123046875 |
| Full refit − frozen，unflagged 完整端点子集 | 10 | +5.96 [0.99, 11.24] | 0.076171875 | 0.15234375 |

四项均完整报告，不挑选最小 p 的检验或结果。第三项含四个数值边界组合：已记录的容差规则计为 1,070/4,096；对保存十进制字符串严格分数运算为 1,066/4,096。S1 明确披露此差异，未在看到结果后更改规则。主要比较的样本配对标准化效应 `d_z=0.807128`，但百分点差和区间仍为主要效应表达。

计算规则和 Holm 家族在本轮运算前记录，但原结果与审稿意见已暴露，所以全部属于**审稿触发的探索性后处理**。Holm 不消除既往暴露；主比较的调整值为 0.05859375，不能仅凭其 raw p 宣布确认性通过，次要比较也不升格为主终点。

原 QC 区间 [0.99, 11.24] 排除零，而相应 sign-flip p 为 0.076171875，直接说明 percentile 区间和该检验不能互换。既有 CPU 实现本已联合重抽样参与者；相关 QC 比较使用相同 seed、n 和词典序，对应相同重抽样索引。有限次抽样及参与者排序可造成小幅区间差异，无需覆盖旧区间。t、signed-rank 和 sign 的额外计算仅用于核查审稿数值，不用于选择有利方法；ties 下不同 signed-rank 实现不可混称同一“exact”结果。

**修订位置：**主稿 **Post-review paired statistical checks**、**Exploratory post-review paired tests** 与新增 Table 5；S1 **S11**；S2 **Reproducing saved numerical results**。机器可读结果见 [statistics_results.csv](../research_logs/kumar_review_revision_20261016/run01/statistics/output/statistics_results.csv)。原 Tables 1–4、bootstrap seed/区间、端点和成员均不变。

## M2：问题与主次终点的对应，以及原作比较

**判定：部分正确。应解释主次问题的对应；不接受把原作 GR/PAR 结果用作本稿 classifier-only 对照的支持。**

主比较回答完整监督重拟合相对完全冻结的**总差异**，同时改变标签可用性和两个拟合阶段；次要的同标签预算比较更直接衡量额外更新 CSP 的增量。保留原先主次顺序，未按结果重指定主终点。

核读 Kumar 官方全文相关段落后确认：GR 持续进行无监督 covariance recentering；PAR 在此基础上，用首 run 标签更新 Riemannian MDM 类别原型。首 run 后原型固定，recentring 继续。两个各九人的组表现未显著不同，不等于等价，更不估计 LDA-only 相对无目标适应的 fully frozen 的效果。其另行 pseudo-online GR-CSP 也不是本稿的同标签 CSP/LDA 全量重拟合。

**修订位置：**主稿引言的两个问题段、**Primary and same-label-budget secondary decoding contrasts**、讨论 **Increment beyond established supervised recalibration**。原作及 correction 作为方法背景，不写“方向一致”或额外独立确认。

## M3：cue-anchored 窗口及原始标记查找

**判定：建议增加实际查找范围正确；若据此宣称原始公开发布缺失 task markers，则不成立。**

实际检查了全部 360 张保留的衍生事件表、7,200 行，字段为 `onset/duration/trial_type/value/sample`，只含左右手标签与 1/2 值，没有独立 task-start/end/outcome 字段。EDF 注释的结论来自既有 hash-matched 完整注释核查，不伪称本轮重新读取了信号。

另查原作者 codebook、task-bounded 提取函数、公开仓库完整树及文本、NEMAR 原始文件清单/转换元数据与既有备份清单。原始发布**公开列出 360 个 bar-task GDF**，其中 72 offline、288 online；其嵌入 `POS/TYP` 数组和与本稿 trial/sample 的映射尚未解析验证。保留衍生物缺相位信息，不能推成原始公开数据没有标记、无法恢复或只发布了衍生物。

摘要首次直接解释五秒窗以视觉 cue 为锚，使用“文档支持的导出约定”，不声称逐 trial 相位已认证。原 44 个末端短窗仍保留排除记录；它们是录制边界关系，不解释成恰好 44 次任务提前终止。引言也明确可靠性证据不足以验证更新规则。

**修订位置：**主稿摘要、**Exported windows, task-phase meaning and chronological partition**、引言可靠性段与讨论窗口限定；S1 **S7.1**；S2 **Marker and literature search scope**。未重新选窗、re-epoch、训练或推理；未来 task-only 分析需先验证原始数组与时钟映射，并另行冻结处理规则。

## M4：12 人主队列、开发划分和个体不确定性

**判定：正确，采纳更醒目的披露；不把区间或删一人均值解释成可靠的个体决策。**

摘要增加三名参与者下降及范围；结果保留九正三负与具体差值；讨论明确主区间约覆盖 2.5–12.5 个百分点。两个很小的负差并不单独建立个体伤害。六人开发划分先于结果，阴性可靠性结果不构成重新并入主队列的理由；其 +3.25 [−0.90, 7.14] 单列。参与者始终是独立统计单位，sessions、seeds、trials 不扩充 n。

**修订位置：**主稿摘要、**Primary and same-label-budget secondary decoding contrasts**、**Neural baseline and statistical scope**；S1 **S4**。未更换参与者、重新分组或按结果筛人。

## M5：弱 EEGNet 参考及比较公平性

**判定：正确，采纳设计意图和预算边界；同时收紧对 drift 的因果解释。**

明确它是固定 40 个源 TRAIN trials 下的 always-frozen 神经参考，不代表全部神经架构或公平架构竞赛。EEGNet 另用 20 个源 validation 标签选 epoch，CPU 两种更新才使用当前目标 support；相同 query 不等于相同信息预算。保留全部三 seeds、54 fits、选中 epoch 1/触顶、训练/验证损失及单类输出。

源 query 52.92% 与目标 51.58% 支持“源判别已经弱”，不隔离 drift 的贡献，也不证明 drift 不可能是主要因素。主稿和 S1 改为 target score alone does not identify the contribution of cross-session drift。未补做调参、更大训练预算、对齐或新网络。

**修订位置：**主稿预算表、**Weak source-session EEGNet discrimination precedes target transfer**、**Neural baseline and statistical scope**；S1 **S3.3、S9**；Fig 1 图注。

## Minor 1–8

| 编号及意见摘要（意译） | 判定与处理 | 修订位置 |
| --- | --- | --- |
| m1：正文三 seeds 的长破折号 | 正确。改为括号，保留三个固定 seed 值。 | 主稿 **Decoders and information budgets**。 |
| m2：S2 数字与单词缺空格 | 正确。改写为可读的数字、单位和计数；历史 ledger 内部标识不被改成新的科学名称。 | S2 **Scientific identities and historical preservation**、QC、复现与图格式段。 |
| m3：S1 队列标签粘连 | 正确。统一为 six development participants、12 primary participants 等可读表达。 | S1 **S4** 及有关分母说明。 |
| m4：摘要 original 含义不清 | 正确。摘要写 primary；正文区分本重分析冻结主比较与 Kumar 原始采集研究。这里的预定义层级不包括后来新增的 p 值。 | 主稿摘要、引言、统计方法；S1 **S11**。 |
| m5：摘要 EEGNet 数值未注明队列 | 正确。52.92/51.58% 明确属于 primary cohort；摘要前文已定义其为 12 人，未改成全 18 人的值。 | 主稿摘要及 Table 3。 |
| m6：数据可用性含内部工具语言 | 正确。改为读者可理解的保存结果、脚本和复现用途；技术失败和工作流记录集中在 S2。 | 主稿 **Data and code availability**、MOABB adapter 表述；S2。 |
| m7：建议补 Vidaurre 与 Arvaneh | 方向正确，给出的 Vidaurre 题名/年份/期刊提示不准确。新增核实后的 Vidaurre 2011 LDA 专文与 Arvaneh 2013；不拼接模糊书目信息，也不声称两方法已实现。 | 主稿引言与适应讨论；[新增两条 BibTeX](../manuscript/kumar_review_additional_references_20261016.bib)及新版完整 bibliography。 |
| m8：Fig 1 点图例及 Fig 4 色标 | 部分正确。Fig 1 原灰点是点型说明，可更清楚，现改为 `Participant (method color)`。Fig 4 原本已用 `RdBu_r`，保留共同对称范围和逐格数值，不为建议而另换色图。 | [新版图与验证记录](../research_logs/kumar_submission_figures_20261016/run01/REPORT.md)。四张 source CSV 不变，Fig 2–4 各格式字节不变；原图保留。 |

新增文献的精确身份与阅读层级：

- Vidaurre C, Kawanabe M, von Bünau P, Blankertz B, Müller KR. **Toward Unsupervised Adaptation of LDA for Brain–Computer Interfaces.** *IEEE TBME*. 2011;58(3):587–597. [DOI](https://doi.org/10.1109/TBME.2010.2093133)。核读完整摘要与书目，未取得原文方法；支持无监督 LDA 适应的背景，不支持本稿监督重拟合的具体公式或结果。
- Arvaneh M, Guan C, Ang KK, Quek C. **EEG Data Space Adaptation to Reduce Intersession Nonstationarity in Brain-Computer Interface.** *Neural Computation*. 2013;25(8):2146–2171. [DOI](https://doi.org/10.1162/NECO_a_00474)。已读相关全文方法及实验设置；其监督/无监督线性通道变换后使用既有 CSP/LDA，不能写成重训 CSP 或更新 LDA 参数。

## 公开证据与仍待作者提供的事实

[来源与实际阅读层级](../research_logs/kumar_review_revision_20261016/run01/review_evidence_reading_scope.json)仅公开 URL、来源哈希与阅读范围，不打包第三方全文或私有审稿报告。Kumar 官方 XML 已完整取得，实际只声明相关方法、结果和讨论段阅读；下载完整文件不等于穷尽论文及 supplements。

伦理适用依据、作者本人对精确最终版本的检查与批准、实际投稿时的 portal 信息仍须据实完成。许可选择已经完成，不再次列为待决。公开版本与最终文件身份以发布/读回记录为准；本文不以本地打包、既有公开快照或备份成功代替新版公开验证。所有历史结果、失败与原稿保留，不制造新科学结论或期刊接收承诺。
