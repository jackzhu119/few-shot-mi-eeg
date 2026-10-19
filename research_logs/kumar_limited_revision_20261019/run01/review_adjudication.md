# 审稿建议逐项证据核对（只读）

核查基线：GitHub/main 19a5909fd76d96be9316559602010932ccec81a8；当前投稿题名 Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG。2026-10-19。完整意见以用户随后粘贴的26931-byte UTF-8文本为准；最初修改意见.pdf只有2097152bytes、缺少trailer，前四页虽可恢复，但并非完整附件。未据不完整PDF推断其余意见。

本核查只读保存的科学结果、脚本和冻结记录，没有重训、前向或新query计算。用户明确要求修改伦理及投稿文字、以审稿建议为依据；附件的具体替换句不是新的科学事实，逐项判定如下。

## 1. 六人划分及18人摘要：采纳数字与透明说明，拒绝错误历史

成立：六人ID1/4/7/10/13/16每隔三编号；源/支持可靠性诊断限定开发组；所有CSP比较使用同一固定CSP4/Ledoit-Wolf/LDA lsqr auto配置。应在Methods补足这些事实，并在摘要加all18 secondary结果。

逐行复核 `manuscript/figures/plos_innovation_20261017/Fig4_longitudinal_paired_changes_source_data.csv`，每人五会话等权：

- 全18 full−LDA = 3.2642277788980754pp，正文修约+3.26。
- 全18 full−frozen = 6.029850328247182pp，正文修约+6.03。
- 开发6 full−LDA = −1.150450359615514pp；主12 = 5.471566848154869pp。
- 开发6 full−frozen = 3.246840760906097pp；主12 = 7.421355111917724pp。

不能采纳“confirmatory hypothesis testing”“without accessing the primary evaluation data”或将后续分析描述为未见过结果的独立验证。冻结 `docs/kumar_component_exploratory_protocol_20261016.md:5` 明确全部18人既有query已经暴露，不属于preregistration/independent confirmation；原预定分组/终点可保留，之后诊断或分解仍标exploratory。以“predefined primary cohort / fixed configuration”准确交代即可。

## 2. 任务测量与240管线：扩充成立，但建议定义有四处实质错误

1. 实际mu范围 **8–13Hz**、beta13–30Hz；建议8–12Hz错误。依据 `scripts/run_kumar_baselines.py:210`，`scripts/verify_analyze_kumar_results.py:92`，S1 S2。
2. 实际低维诊断是三类表示：44维全22channel mu/beta log-power；source-PCA4；C3/Cz/C4六维mu/beta。不是“canonical channel log-power differences”一类取代44维。每个TRAIN20中训练Scaler/PCA/类中心方向与阈值；随后新增的监督CSP4/LDA是**第四类**。Methods需要把motor-band类保留，和Results的三个近chance数字对应。依据S1 S5.1/S5.2。
3. **covariance drift不是两query covariance矩阵之间的直接Riemann距离**。先在TRAIN40拟合21维CAR子空间的Riemann参考；对每个epoch求其trace-normalized/shrunk covariance到固定参考的距离；最后target-query平均距离减source-query平均距离。`scripts/verify_analyze_kumar_results.py:167–193` 和S1 S2可核。
4. 0.295325的support split-half cosine来自**source40标准化四维CSP log-power**；不能按建议改写成44维mu/beta cosine。CSP LDA分数margin也在四维CSP，而task-axis drift使用44维power，这两轴必须区分。`scripts/analyze_kumar_csp_signed_score_v1.py:390–409`；S1 S5.3。

成立：240 = 6participants ×2 TRAIN20 folds ×20 training-label rotations（包括12identity fits）；held-out label phases只评分，不再拟合；还可交叉20×20 phases，产生2400 participant-pair两折均值。240新fits全成功，sourcequery/targetquery零。见 `research_logs/kumar_csp_signed_score_execution_20261015/run02/{REPORT.md,scientific_summary_from_saved_results.json}`。

成立：漂移60个主组target sessions、participant-block bootstrap2000/seed42；性能及开发可靠性participant bootstrap10000/seed42；不能把两个replicate数混用。

成立：62.9167%→62.92% [52.50,71.67]，cosine0.295325→0.295 [0.032,0.573]（或0.30 [0.03,0.57]），只改变显示精度。

漂移轴通过source TRAIN标签定义，不是全流程无监督；可称“query-label-free”或“unlabeled target-distribution predictors”，保留source-trained轴。相关区间跨0说明当前数据未建立稳定关联，不证明预测能力不存在，更不能把描述性关联写成前瞻失效检测。

两double-negative sessions的cosine是sub1ses4=0.19105257、sub7ses2=0.85006940。不能笼统写“high internal agreement”对两者均成立。可准确写“positive subset agreement can coexist with reversed score orientation”。

## 3. Post-review及统计解释：术语采纳，保留完整统计事实

“post-review”改“post-hoc exploratory”或“supplementary exact sign-flip”成立，表头同改。四个p及Holm不变：.01953/.05859；.01025/.04102；.26123/.26123；.07617/.15234。Methods继续保留原终点层级和后续探索范围。

建议的“because overlapping subsets, Holm correction is conservative”不是由数据自动推出的结论。Holm在任意依赖结构下控制family-wise error；不要用overlap贬低校正结果。简洁解释：bootstrap百分位区间基于经验重采样，exact sign-flip检验基于零效应下独立participant差值符号对称假设；再对四对比adjust，故区间和adjusted p不互相等价。不要把四检验改成一个、不要升级secondary为primary，不写所有primary tests均显著。

## 4. 队列差异、拼接、EEGNet：定量成立，机制需按假说写

sub7/ses2 fullBA=.45、LDAonly=.825，full−LDA=−37.50pp；full−frozen只有−15.00pp，勿混。该会话在开发30会话等权均值贡献−1.25pp，说明对−1.15pp开发总平均具有较大影响。仍保留所有参与者，不因这项结果删除或重分配开发组。

“噪声/伪迹导致CSP过拟合”“更换空间模式导致classifier无法恢复lost power”是合理机理假说，现有对比未将具体原因隔离，不能写已证明的因果机制。可直接给观察到的−37.5和开发/主组差异，再说明space重估的bias/variance trade-off供未来检验。

源40+目标19/20的观测行直接拼接、无target-domain额外重权，计数比约2:1成立；不能简单等同classwise Ledoit-Wolf covariance中的每域精确固定2:1权重。Weighted covariance、target-only、EA/Riemann recentering为未来设计选择，不能称当前稿已比较。

EEGNet source-only冻结且没有target fine-tune成立。解释固定范围避免新增layer-freezing/learning-rate选择自由度可采纳，但若写成历史决策动机需有冻结记录；最安全直接交代未微调、预算不同、适应比较限定CPU两组件。

## 5. 局限扩充：采纳明确操作事实，拒绝伪迹归因与未实施策略

可精确说明cue锚点5s、1.5s cue及后续活动、零相位滤波仅offline、unweighted source/support union、独立队列及prospective selector为未来步骤。已有44partial是boundary截断，不能改成提前任务结束。

**21.1%幅度flag不能证实ocular/visual contamination，也不应写“consistent with cue artifacts”暗示已经定位来源。**幅度阈值非伪迹诊断，未flag也非artifact-free。可引用现有QC敏感性，但不把它写成消除训练潜在伪迹影响。当前3.26/5.47阳性成分对比是现有科学结论，不因这段局限缩减其数值或添加无依据弱词。

后续support-driven action selection未完成prospective验证；不能称已有效的adaptive gate。保留这项科学边界不是防御性赘词。

## 6. Table5/6减号：显示修复可采纳

canonical Markdown已经有U+2212，但投稿PDF可能字体渲染未保留；按用户意见改为U+2013 en-dash“ – ”，验证最终DOCX及PDF的可见输出，不改行序/数值。此项属于格式修复。

## 7. 图注AI重复：可采纳

六处重复AI语句可删，主文Training-history review and AI assistance保留一次完整披露和作者核验责任。Fig5/6末句与Fig1–4 wording略有不同，不能只replace一种文字遗漏两处。移除重复不等于删除或弱化真实AI披露。

## 8. Fig4术语：可采纳

“Remaining (n=12)”改“Primary cohort (n=12)”以统一既有群组，不改IDs、排序、色阶、任何数值。绘图脚本和PNG/PDF/TIFF/SVG及副本同步，源CSV应保持字节不变。

## 9. Reference16：格式问题成立，不能臆造codebook作者或年份

当前Bib条目明确“no independent publication date assigned”；代码本仓库归属/与原论文关系不等于其单独PDF作者证明。可用已核验的TransLearning repository著者/维护者或机构写Vancouver Internet条目，保留固定commit548470...和实际访问日期。不要仅凭原论文作者名单给PDF添加Kumar S/Alawieh等五位作者、也不要把2024强行当独立codebook发布日期。需要由文件封面/仓库元数据证实后再加具体author/year；无法证实用n.d.或真实repo责任者。以真实访问日期，不把本次日期假装最初文献读取日期。

## 对用户“删限定词/否定词”的处理边界

删除重复过程词、AI图注、泛泛防御措辞；阳性主比较+7.42pp和匹配预算成分+5.47pp、73.7%分解、10/12/5sessions/all deletion结果可用直接主动语态。保留界定真实设计所需词：secondary all18、exploratory新增分析、pointwise intervals、source-only EEGNet、offline cue-window、样本与预算边界、Holm p=.05859、unflagged≠artifact-free、未验证门控。删除这些会改变科学含义，并不属于单纯润色。
