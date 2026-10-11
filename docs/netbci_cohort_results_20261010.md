# NETBCI 十人队列：审计、纵向表征与冻结读出

分析日期：2026-10-10；来源独立性检查与报告定稿：2026-10-11（Asia/Shanghai）。十个发布身份的审计、统一纵向分析、汇总与探索性关联已经完成，保存表格的独立算术核读通过。**全部 240 runs 的完整数值检查确认跨身份、跨会话重复，以及 sub-7 训练信号在后续 query 中重现。原十身份 EEG 区间仅保留为算术结果，不能作为十个独立参与者的区间；另存基于源审计、同时排除 sub-1 与 sub-7 的八身份探索性敏感性。**

本轮接续现有 `research/learning-preserving-bci` 科研分支与云端环境。研究问题是：历史在线表现、任务相关 EEG、总体几何与早期冻结读出的跨会话可迁移性是否表现一致。它是单人先导研究之后固定方案的探索性扩展，尚未检验 Learning-Preserving 自适应策略的因果作用。

## 1. 来源、纳入与事件资格

EEG 来源为 [NEMAR nm000305 v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0) 的 EDF/BIDS derivative，许可 CC BY 4.0。任务为右手运动想象与休息。纳入公开编号 `sub-1` 至 `sub-10`，不按在线成绩、改善方向、EEG 指标或模型成功筛选。原始 [Dataverse v2.2](https://doi.org/10.57745/RBJRC7) 的行为表覆盖 19 人；其中前十人的 40 个会话才进入本轮 EEG—行为队列关联。19 人行为样本量与 10 人 EEG 样本量分别报告。

旧交接中的下载、两人审计和单人分析收据继续保留。恢复开始时，当前执行环境缺少历史原始信号，随后按相同版本、官方 manifest 和校验方案恢复必要文件，重新建立本轮审计，不把历史收据当作当前字节已经存在的证据。恢复只更改保存路径的记录见 [resume_plan.json](../research_logs/netbci_cohort_resume_20261010/resume_plan.json)。

原始 `participants.tsv` 的官方 MD5 为 `b9aa1c07015820e80bc79be6a61f30fc`，字典为 `41b33bc709e7b36a14faa91da128aaba`。字典有尾逗号，原始字节和严格 JSON 解析问题均保留。行为定义是每 session 六个已发布 target-hit 百分比的无权平均；它不是已知分母下的 pooled hit rate。source provenance 与逐 run 原始头文件校验提供显式 subject 身份映射。

审计检查通道与顺序、采样率、单位、完整信号有限性、事件语义、时间与样本锚点、重复、边界、annotation 以及 session/run 覆盖。derivative 标签由实际记录确定：`rest=1`、`right_hand=2`；不能采用 README 示例的相反数字映射。derivative 的秒、零起始 sample 与原始头文件采样率分别记录，原始空白 reference 字段不被解释为参考已核实。真实 calendar date 和日间隔仍未验证。

**5 秒输入资格是本轮实际观察后的明确适配决定。** 严格适配器在 `sub-3` 遇到不同长度 epoch 并失败；源事件普查发现一个真实 rest 事件仅 2.968 秒。该事件完整保留在源事件表与排除表中，只因不具备既定 5 秒、1,250 样点窗口而不进入固定长度张量。没有补零、拼接随后数据、补造 trial 或移除该参与者。决定在任何本轮队列模型拟合之前保存，但发生于读取新事件之后，因此不是原先预先固定或盲法决定。模型、频谱、几何、抽样和统计参数保持原方案。

具体决定、配置及保留的失败分别见 [输入资格决定](../research_logs/netbci_cohort_resume_20261010/full_window_policy_decision.json)、[本轮配置](../configs/netbci_cohort_full_windows_20261010.json) 和 [首次严格失败](../research_logs/netbci_cohort_resume_20261010/audits/sub-3/failure.json)。最终配置 SHA256 为 `2bead8bccd0396e0358bb8167324621e80d48087ba011a334224f73962d10904`；相对决定时快照只修正状态与时间说明，见 [配置定稿记录](../research_logs/netbci_cohort_resume_20261010/full_window_policy_finalization.json)。

## 2. 冻结方法与统计单位

每个人独立建立 source 模型。`ses-01/run-01..04` 用于拟合；同会话 `run-05/06` 是互斥 reference query；后续三个 session 均评估全部六 run。`ses-02` 是不作选参的 validation descriptor，`ses-03/04` 是探索性 test。QC 阈值、scaler、reference PCA、CSP 与 LDA 只用 source 拟合。目标 session 的单独 PCA 只作描述，不能进入预测。旧单人方案后续 query 只有五 run，本轮全部十人按统一六 run 方案重算，旧数字不拼入新队列。

共同 EEG 通道使用 CAR；固定 Helmert 坐标表征 CAR 降秩空间。频谱采用 C3/Cz/C4 ROI，任务内 `[0.5,4.5)` 秒，Welch 250 样点、125 重叠；Mu 为 8–13 Hz，Beta 为 13–30 Hz。先对每 trial ROI 功率取 log10，再分别对每 class/run 求均值，最后对规定 run 等权平均。`10 × (MI mean log10 power − rest mean log10 power)` 是 dB 任务对比。算术绝对功率另列；二者不能混为一个指标。这不是 prestimulus-baseline ERD，也不是纯想象阶段的生理效应。

几何采用每 epoch 四阶零相位 8–30 Hz Butterworth 滤波、每端裁剪 0.5 秒、trace normalization、0.05 shrinkage 与 10 维 PCA。全六 run 匹配为每 run 每类 12 trials，共 144/session，10 个固定抽样重复；QC 敏感性为共同 `run-03..06` 的未标记 trials，固定 96/session。任一规定单元不足，该变体对该人明确 unavailable；不降低计数、只留下成功 seed、改 QC 阈值或删人。10 次抽样先在每人内部求均值，不增加独立 n。

冻结解码器为预设 4-component CSP + LDA。模型 hash、训练 trial ID、fit 次数与 query 前后状态验证保存；恒预测与其他失败均保留。QC 为 source-only 粗筛查，主分析保留被标记 trials；未标记不等于无伪迹。没有新增 EEGNet 训练、复杂自适应策略或人体实验。

原汇总重采样单位是 10 个完整四会话发布身份轨迹，seed=42，10,000 次 percentile bootstrap。首末变化先在每个身份内部相减，再重采样身份；均值不能由两个互不关联的 session bootstrap 相减。完整数值检查随后证实这些身份不对应十个互相独立的 EEG 来源，因此原 EEG bootstrap 区间的参与者独立性假设不成立；保存区间只用于核对计算，不用于人口推断。每人的 500 次 run bootstrap 只是给定其数据和冻结拟合下的条件区间，源拟合不确定性、未知评分分母和人群抽样机制不在其中。人数按每个指标实际可用情况报告；unavailable 为缺失，不填零。另存八身份敏感性仍是观察数据后选定的探索性描述，不是算法效果或人口代表性保证。

## 3. 十人结果与逐人计数

全员最终审计通过：**10 人、40 sessions、240 runs，7,577 个真实源事件，7,576 个合格 5 秒 epochs，1 个短 rest 事件仅从固定张量排除。** 源事件为 MI 3,794/rest 3,783；合格张量为 MI 3,794/rest 3,782。全部 derivative 均为 74 EEG 通道、相同通道顺序、250 Hz、V 单位，不需要按人选通道或重排。240 个原始头文件 hash 已验证，原始头文件采样率包括 249.89999389648438、250 和 1,000 Hz；不能将 derivative 的 250 Hz 当所有原始记录采样率。

| 受试者 | 原始 ID | 源事件 | 合格 epochs | 排除 | 合格 ses-01 / 02 / 03 / 04 | 合格 MI / rest |
| --- | --- | ---: | ---: | ---: | --- | --- |
| sub-1 | sub-01 | 717 | 717 | 0 | 180 / 179 / 180 / 178 | 360 / 357 |
| sub-2 | sub-02 | 767 | 767 | 0 | 192 / 192 / 191 / 192 | 384 / 383 |
| sub-3 | sub-03 | 765 | 764 | 1 | 190 / 192 / 191 / 191 | 383 / 381 |
| sub-4 | sub-04 | 768 | 768 | 0 | 192 / 192 / 192 / 192 | 384 / 384 |
| sub-5 | sub-05 | 765 | 765 | 0 | 191 / 190 / 192 / 192 | 382 / 383 |
| sub-6 | sub-06 | 768 | 768 | 0 | 192 / 192 / 192 / 192 | 384 / 384 |
| sub-7 | sub-07 | 726 | 726 | 0 | 178 / 178 / 178 / 192 | 366 / 360 |
| sub-8 | sub-08 | 766 | 766 | 0 | 191 / 192 / 191 / 192 | 384 / 382 |
| sub-9 | sub-09 | 767 | 767 | 0 | 192 / 192 / 191 / 192 | 383 / 384 |
| sub-10 | sub-10 | 768 | 768 | 0 | 192 / 192 / 192 / 192 | 384 / 384 |
| **合计** | **10 人** | **7,577** | **7,576** | **1** | **40 sessions，240 runs** | **3,794 / 3,782** |

`sub-3/ses-01` 的源事件为 191，合格为 190；其余会话源数和合格数相同。唯一排除记录是 `sub-3/ses-01/run-03/tsv-row-31`，rest，onset 224.032 秒、sample 56,008、duration 2.968 秒、742 样点。完整记录见 [excluded_events.tsv](../research_logs/netbci_cohort_resume_20261010/audits_full_windows/sub-3/excluded_events.tsv)。[全队列最终审计](../research_logs/netbci_cohort_resume_20261010/audits_full_windows/cohort_audit.json)同时保存各人的 source/eligible/excluded、通道与采样信息。已审计十人不等于全部公开 19 人或完整原始多模态信号均已核验。

全部 40 个模型 query 成功执行；75 个 QC 标记合格 epochs 保留于主分析。逐人分区、QC 与解码轨迹如下。BA 的四值顺序为 ses-01/02/03/04，source 数为拟合数，query 四值为实际评估数；人数和 trial 数没有由群体均值替代。

| 身份 | source 拟合 n | query n：01 / 02 / 03 / 04 | QC 标记 n：01 / 02 / 03 / 04 | BA %：01 / 02 / 03 / 04 |
| --- | ---: | --- | --- | --- |
| sub-1 | 120 | 60 / 179 / 180 / 178 | 0 / 0 / 1 / 43 | 60.000 / 50.000 / 50.000 / 50.000 |
| sub-2 | 128 | 64 / 192 / 191 / 192 | 0 / 0 / 0 / 0 | 81.250 / 71.354 / 50.000 / 78.125 |
| sub-3 | 126 | 64 / 192 / 191 / 191 | 0 / 3 / 0 / 0 | 59.375 / 58.333 / 58.251 / 51.135 |
| sub-4 | 128 | 64 / 192 / 192 / 192 | 0 / 0 / 0 / 0 | 78.125 / 83.854 / 88.542 / 50.000 |
| sub-5 | 127 | 64 / 190 / 192 / 192 | 0 / 0 / 3 / 4 | 67.188 / 61.824 / 44.271 / 50.000 |
| sub-6 | 128 | 64 / 192 / 192 / 192 | 1 / 1 / 0 / 0 | 45.312 / 50.521 / 56.250 / 68.750 |
| sub-7 | 119 | 59 / 178 / 178 / 192 | 0 / 0 / 0 / 0 | 89.713 / 87.614 / 87.614 / 50.000 |
| sub-8 | 128 | 63 / 192 / 191 / 192 | 18 / 0 / 1 / 0 | 79.234 / 57.292 / 59.638 / 63.542 |
| sub-9 | 128 | 64 / 192 / 191 / 192 | 0 / 0 / 0 / 0 | 79.688 / 62.500 / 59.238 / 49.479 |
| sub-10 | 128 | 64 / 192 / 192 / 192 | 0 / 0 / 0 / 0 | 46.875 / 53.125 / 50.521 / 50.000 |

全部十人的 source 与 reference query trial ID 在身份和行号层面互斥；另项完整数值核查已确认 sub-7 source 与后续 query 的内容重复，不能将 ID 互斥等同于信号独立。完整 40 行在线成绩、频谱、query、QC 与百分比条件区间见 [participant_session_join.tsv](../research_logs/netbci_cohort_resume_20261010/summary_run01/participant_session_join.tsv)。

| 端点 | ses-01 均值 | ses-02 均值 | ses-03 均值 | ses-04 均值 | 04−01 配对均值 [95% CI] | 增 / 降 / 不变 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 在线六百分比均值，% | 54.535 | 57.448 | 64.731 | 68.803 | +14.268 pp [10.085, 18.291] | 10 / 0 / 0 |
| 冻结 CSP+LDA BA，% | 68.676 | 63.642 | 60.432 | 56.103 | −12.573 pp [−22.954, −1.596] | 2 / 8 / 0 |
| Mu MI−rest，dB | −0.470 | −0.571 | −0.785 | −0.880 | −0.410 [−1.168, 0.492] | 5 / 5 / 0 |
| Beta MI−rest，dB | −0.316 | −0.376 | −0.443 | −0.414 | −0.098 [−0.546, 0.385] | 4 / 6 / 0 |

以上 n=10 是发布身份的完整首末配对数；EEG 区间是有重复来源的身份重采样算术结果，不能称为十个独立参与者的区间。所有区间未经多重比较调整；在线改善描述已发布训练期表现，不识别人的学习或自适应策略效果。频谱首末变化没有统一方向，不能把单人先导的方向写成十人规律。EEG derivative 重复不改变原始 19 人已发布行为记录的样本量。

## 4. 模型失败、QC 与指标可用性

共保留 8 条科学失败记录：7 条恒预测 query、1 条预设 QC 匹配不可用；没有模型执行失败。恒预测涉及 5 个身份：sub-1 的 ses-02/03/04 均预测 rest；sub-2 的 ses-03、sub-4 的 ses-04、sub-7 的 ses-04 均预测 rest；sub-5 的 ses-04 均预测 right_hand。每次恒预测 BA 为 50%，对应一类 recall=0、另一类 recall=1。sub-10 的 ses-04 虽然 BA 也为 50%，但不是恒预测，不能只根据 BA 标记失败。

完整六-run 匹配在全部十个身份可计算；QC 共同四-run 匹配为 9/10。sub-8 的 ses-01/run-05 rest 仅有 11 个未标记 trials，run-06 rest 为 8 个，低于每类/run 固定要求 12，故该人的整个 QC 匹配变体 unavailable。没有降到 8、只取成功重复或移除该人。全员其余主分析继续保留。记录见 [cohort_summary.json](../research_logs/netbci_cohort_resume_20261010/summary_run01/cohort_summary.json) 的 `scientific_failures` 和 `matching_availability`。

QC 总负荷为 75/7,576（0.990%）；主分析未标记 7,501 个合格 epochs。QC 主要集中在 sub-1 ses-04（43/178）和 sub-8 ses-01（18/191）。QC 是每人 source-only 粗阈值，重复来源可能影响其适用性；各人的未标记集合不自动具有相同伪迹水平。

## 5. 几何、频谱与行为的解释

六-run 匹配在四会话的平均 AIRM 到 ses-01 为近零 / 5.569 / 7.222 / 7.471；会话内 run 间平均 AIRM 为 4.635 / 4.100 / 2.938 / 2.691；PCA 子空间距离为近零 / 0.605 / 0.623 / 0.642。ses-04 AIRM 的发布身份算术区间为 [6.218, 8.625]，PCA 为 [0.601, 0.685]。QC 共同四-run（n=9 发布身份）ses-04 AIRM 为 7.121 [5.877, 8.263]，PCA 为 0.663 [0.624, 0.698]。这些是不同 run 集、不同可用身份集合下的描述，不能直接用两组均值相减作为 QC 作用；重复来源使上述区间不具独立参与者解释。

**完整来源重复检查已完成，重复是确证的 derivative 数值事实。** 对全部 240 个连续 run 和 7,577 个真实源事件窗口按原始返回的 V 单位、74 通道顺序、float64 数值计算 SHA256；未滤波、重参考、舍入或设近似相似阈值。六组对应 run 均满足 `sub-7/ses-01 = sub-7/ses-02 = sub-7/ses-03 = sub-1/ses-04`，共 24 个重复 run 成员、222 个唯一连续信号。178 组任务窗口各有四个相同数值成员，共 712 条记录；无跨标签重复。sub-7 的前三会话对应 EDF 文件彼此逐字节相同；sub-1 的 EDF 文件 hash 不同，但实际解码 EEG 数值相同，说明只比文件 hash 不足以发现这类重复。

sub-7 ses-02 与 ses-03 各有 119 个 query 窗口重复 ses-01 source training、另有 59 个重复 source reference query，共 238 条训练重合和 118 条 reference query 重合。训练→后续 query 内容重合使对应后续解码分数不能作为独立跨会话泛化证据；不同 trial ID 无法消除实质内容重合。全部 240 个 EDF 的官方 manifest 校验正确，原始头文件也有不同身份，但不能凭这两点判定原始采集独立。原始 BrainVision 连续 EEG 和 marker 未在本项检查中实读，重复发生的环节与正确身份归属未明；不归因于人的生理、行为或任何已知转换错误。精确核查见 [numeric_signal_identity.json](../research_logs/netbci_cohort_resume_20261010/numeric_signal_identity.json) 和 [官方校验复核](../research_logs/netbci_cohort_resume_20261010/numeric_signal_identity_official_manifest_confirmation.json)。检查只证明精确相同；不同 hash 不排除近似重复。

### 来源审计后的八身份敏感性

由于不能确定重复信号属于哪个身份，另存敏感性同时排除跨身份重复组中的 sub-1 与 sub-7，保留 sub-2/3/4/5/6/8/9/10。排除根据完整源数值事实，不根据成绩、变化方向或模型成败；原始十身份表、模型和文件均不覆盖，没有重新拟合或改选方法。八身份没有发现本次检查范围内的精确数值副本，但这不验证真实生物学身份、测量可靠性或因果学习。此项在观察十身份结果及重复事实后制定，不是独立确认或预注册主分析。

| 八身份敏感性端点 | 04−01 配对均值 [未调整 95% bootstrap 区间] | 增 / 降 / 不变 |
| --- | --- | --- |
| 在线六百分比均值，% | +14.371 pp [9.189, 19.325] | 8 / 0 / 0 |
| 冻结 CSP+LDA BA，% | −9.502 pp [−20.244, 2.735] | 2 / 6 / 0 |
| Mu MI−rest，dB | −0.679 [−1.317, −0.047] | 4 / 4 / 0 |
| Beta MI−rest，dB | −0.167 [−0.654, 0.381] | 3 / 5 / 0 |

八身份 BA 均值从 67.131% 到 57.629%，首末区间跨零；Mu 平均变化的区间移至零以下，但方向仍有四增四降。两种区间位置变化都不构成策略效果或学习机制确认。八身份 Mu—BA 变化的 Pearson r=−0.619 [−0.941, −0.203]、Spearman ρ=−0.619 [−0.973, 0.140]；两个估计器的不确定性不同，不能只挑一种作机制解释。其他四组关联的两种区间均跨零。全量八身份端点和全部五组关联保存于 [敏感性汇总](../research_logs/netbci_cohort_resume_20261010/independence_sensitivity_run01/sensitivity_summary.json) 及 [敏感性收据](../research_logs/netbci_cohort_resume_20261010/independence_sensitivity_run01/sensitivity_receipt.json)。八身份关联集是完整配对身份，不把 32 会话、runs 或 trial 扩成独立 n。原始 19 人行为分析继续单独保留，不因 EEG 排除而缩减。

绝对算术 Mu 功率的四会话身份均值（µV²）为 rest 5.600 / 5.836 / 9.449 / 5.917，MI 4.792 / 4.172 / 8.355 / 4.812；首末配对变化 rest +0.318 [−2.511, 3.132]、MI +0.020 [−2.584, 3.439]。第三会话均值明显高于中位数，不能从均值上升直接推断统一神经机制。完整参考与 QC 敏感性保持 CAR/source_reference、六-run/共同四-run 全样本/共同四-run 未标记三种 run 集分别呈现，见 [spectral_reference_QC_sensitivity.tsv](../research_logs/netbci_cohort_resume_20261010/summary_run01/spectral_reference_QC_sensitivity.tsv)。会话内 run 距离是描述性比较，不自动构成 split-half 可靠性、测量误差模型或生物学重复性验证。

五组原始关联在保存的估计方案下使用完整首末配对身份，n=10；Pearson 和 Spearman 区间均重采样 10,000 次完整配对身份，seed=42。下表写明未调整的 95% 区间，保留全部五组而不只选择区间不跨零者。重复 EEG 已确认，下列区间只作为原计算的算术记录；不能作为独立参与者区间、H1/H2 确证或因果结果。

| 关联（首末变化，除另注） | Pearson r [95% CI] | Spearman ρ [95% CI] |
| --- | --- | --- |
| BA 与在线成绩变化 | 0.424 [−0.050, 0.777] | 0.394 [−0.333, 0.852] |
| Mu 对比与在线成绩变化 | −0.412 [−0.876, −0.014] | −0.479 [−0.764, 0.176] |
| Mu 对比与 BA 变化 | −0.727 [−0.933, −0.355] | −0.721 [−0.962, −0.152] |
| ses-04 AIRM 到 ses-01 与 BA 变化 | −0.624 [−0.931, 0.331] | −0.503 [−0.925, 0.291] |
| ses-04 PCA 距离与 BA 变化 | 0.020 [−0.651, 0.666] | 0.164 [−0.686, 0.796] |

不同估计器的区间可不同，不依据是否跨零宣称学习机制。没有 p 值或多重比较校正，估计方案不是原先独立预注册；探索多个端点、10 人小样本、源重复及未知在线解码器更新均限制解释。精确估计、有效重采样次数与输入散列见 [association_estimates.tsv](../research_logs/netbci_cohort_resume_20261010/associations_run01/association_estimates.tsv) 和 [association_receipt.json](../research_logs/netbci_cohort_resume_20261010/associations_run01/association_receipt.json)。

EEG—行为关联只允许明确的 subject/session。六值向量位置到 EEG run、评分分母与 abort/排除规则、trial outcome、光标轨迹和在线 decoder 更新版本仍 unresolved；不能广播成绩或由百分比倒推 hit/miss。在线 target-hit、冻结离线 BA 与任务窗口功率没有相同的映射、分母或 trial 集合，不能相减并称为学习增益。

## 6. Q1–Q7 与后续研究决策

| 问题 | 当前结果与解释边界 |
| --- | --- |
| Q1 可靠真实 EEG 有多少？ | 已实读审计 10 个发布身份、40 sessions、240 runs；7,577 源事件/7,576 固定 5 秒合格 epochs，1 个短 rest 明确排除。全部信号检查确认 sub-1/sub-7 跨身份重复；来源驱动敏感性保留 8 身份，未发现精确副本，仍不保证生物学可靠性。 |
| Q2 能否关联真实行为？ | 原始 19 人行为已存在，本轮 40 行 subject/session 标识关联核对通过，首末在线成绩 +14.268 pp [10.085, 18.291]。重复 derivative 限制对应神经证据；run/trial 关联继续 unresolved。 |
| Q3 能研究人类学习吗？ | 支持观察性训练期表现、纵向 EEG 与固定读出研究；历史在线重校准、反馈及测量变化不能分离，不能识别人的学习或技能保持因果效果。 |
| Q4 有可重复纵向神经变化吗？ | 原十身份 Mu −0.410 dB 区间仅算术记录；八身份敏感性 −0.679 dB [−1.317, −0.047]，四增四降。sub-3 计算重放 16 件稳定输出 byte 相同，但计算重现、精确副本和生物学重复是不同事实。 |
| Q5 固定解码器跨会话怎样？ | 原十身份 BA 68.676→56.103%，但 sub-7 有 238 条 source training→后续 query 重复。八身份敏感性 67.131→57.629%，−9.502 pp [−20.244, 2.735]；不能称人的控制技能下降。原 7 次恒预测继续保留。 |
| Q6 距真正创新还缺什么？ | 充分的 source-only baseline、任务信息与测量噪声分离、明确反事实及独立行为端点；增加人数或引用 Nature 技术本身不构成新算法。 |
| Q7 必须新在线人体实验吗？ | 范围清楚的离线方法学/观察性研究可以继续；主张算法保留或促进人的独立技能，需要前瞻在线对照，或等价的可靠公开随机干预证据。 |

H1（表征、固定读出与在线表现可能分离）和 H2（指定漂移与读出变化可能关联）允许零结果或相反结果。H3/H4 关于更新政策与技能保持的主张，本轮无 assigned policy、无辅助撤回和延迟 retention 数据，仍为理论假设。不要以整体 drift 最小化作为天然正确的学习目标。

后续在线设计应匹配 decoder 架构、更新/标注预算、训练时长和反馈，记录每次 mapping 变化与真实 trial outcome。保持训练结束时所学 mapping 的立即/延迟无辅助表现，是 retention；回到最初 reference mapping 的表现，是 transfer/readout。两者分别测量。当前十人公开样本不自动证明高水平投稿功效或临床适用性。

## 7. 证据入口与完成状态

原先范围与参数见 [十人扩展协议](netbci_cohort_expansion_protocol.md)，项目历史与暂停位置见 [完整交接](CHAT_HANDOFF_20261010.md)。历史单人稿和 19 人行为报告作为有日期的先导资料保留。本轮精确小表入口为 [汇总收据](../research_logs/netbci_cohort_resume_20261010/summary_run01/summary_receipt.json)、[配对变化](../research_logs/netbci_cohort_resume_20261010/summary_run01/cohort_paired_changes.tsv)、[匹配几何](../research_logs/netbci_cohort_resume_20261010/summary_run01/participant_matched_geometry.tsv) 和 [独立保存表算术核读](../research_logs/netbci_cohort_resume_20261010/independent_review.json)。该核读未加载 EEG 数组；完整数值身份检查另外实读了全部 240 runs。原始十身份结果不被八身份敏感性覆盖。

sub-3 从已审计 bundle 重新计算全部特征并重新拟合，其 16 件稳定输出（含模型字节、预测、谱、几何、分区）均 byte 相同，见 [计算重放收据](../research_logs/netbci_cohort_resume_20261010/computational_replay_sub3.json)。仅重放这一人，不声称全部十人模型已第二次训练；时间收据不作 byte 相等要求；计算确定性不等于生物学验证。

可编辑图与输入 hash 校验见 [已执行 notebook](../notebooks/netbci2026_cohort_20261010.ipynb) 和 [HTML 阅读版](../notebooks/netbci2026_cohort_20261010.html)。notebook 同时核验完整数值身份检查与八身份敏感性的输入/output hash，原生图逐张检查；[执行与图像验证收据](../research_logs/netbci_cohort_resume_20261010/notebook_validation_final/notebook_validation_receipt.json) 说明实际检查范围。报告与 notebook 修订来源重复解释及验证状态，原分析小表保持不覆盖。

下一步按另存协议审计其余公开 NETBCI 身份并扩大独立来源；当前十身份计算、完整重复检查与八身份敏感性作为本轮完成检查点。新增数据按任务、标签、原始来源、发布版本、许可、身份、纵向会话与 online 行为可验证性分别入库，外部横断面 MI 数据不能直接拼成学习或 retention 的样本量。用户已授权把后续数据保存到 R2；R2 储存与公开数据扩展由独立收据记录，不被本报告的十身份分析完成状态替代。原始信号、大型 NPZ 和模型文件由 Git 忽略；Git 保存代码、配置、小表和收据。没有付费资源或第一篇仓库修改。
