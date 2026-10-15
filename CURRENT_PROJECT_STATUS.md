# 论文2当前进度与论文状态

更新日期：2026-10-15（科学记录使用UTC）。本轮基于实际远端
`370bc94b7af3c926adeb02c38e430a53e4a64135` 继续，工作分支仍为
`research/learning-preserving-bci`。本页取代旧快照的当前状态；历史结果、配置、
验收记录和旧稿完整保留在既有路径与固定Git提交中。

## 当前交付

**PLOS ONE Research Article最终作者审阅包已形成，未代作者投稿。**

- [完整文件索引](manuscript/plos_one_submission_20261015/README.md)。
- [带图审阅PDF](manuscript/plos_one_submission_20261015/manuscript_for_review.pdf) /
  [Word](manuscript/plos_one_submission_20261015/manuscript_for_review.docx)。
- [无图投稿格式PDF](manuscript/plos_one_submission_20261015/manuscript_for_submission.pdf) /
  [Word](manuscript/plos_one_submission_20261015/manuscript_for_submission.docx)。
- [科学方法S1 Text](manuscript/plos_one_submission_20261015/S1_Text.pdf)、
  [审计复现S2 Text](manuscript/plos_one_submission_20261015/S2_Text.pdf)、
  [最小数据包S1 Data](manuscript/plos_one_submission_20261015/S1_Data.zip)。
- [作者待办与已确认信息](manuscript/plos_one_submission_20261015/author_worksheet.pdf)、
  [未发送附信](manuscript/plos_one_submission_20261015/cover_letter_draft.pdf)。
- [简明整改报告](docs/kumar_submission_revision_report_20261015.md)。

工作标题为 **Longitudinal motor-imagery EEG decoding: Frozen baselines,
supervised recalibration, and task-measurement reliability**。仅按期刊要求改句首大小写，
未改变原获确认标题含义。作者为Ziyuan Zhu；作者8项事实回复已落实，不重复索取。

## 研究完成状态与本轮新核查

54/54源EEGNet模型（18发布身份×3种子）及一次只读冻结query评估已分别验收，
剩余冻结训练为0。三种CPU基线和原结果不变。本轮没有模型拟合、新forward/query、
追加种子、调参、Pod操作、新资源或论文1操作。

1. **窗口含义已收紧。** 原作者代码本确认769/770是cue、7691/7701是task start；
   保存的MOABB[0,5]导出链支持cue锚定窗口，不能称完整持续5秒MI。
   全44个partial是run最后事件且终点等于EDF边界，不是44次已确认任务提前终止。
   [时序审计](docs/kumar_submission_window_timing_review_20261015.md)列明原始marker/clock/
   exporter版本的最小补证与只供审阅、不执行的修正方案。
2. **解码QC后处理已完成。** 新探索性规则先记录，25,740保存预测严格join至4,290query；
   原144参与者端点重建差0。922query有原幅度标记，3,368未标记。
   未标记五会话端点仅10/12人有效，缺失类别sub-8/sub-12仍保留。
   主差+7.42pp[2.49,12.48]不变；敏感性+5.96[0.99,11.24]，同10人变化
   −0.54[−1.30,+0.16]。未标记不等于无伪迹，原拟合/验证中的标记数据未移除。
3. **同预算次比较未升级。** full−LDA-only仍为次比较+5.47pp[2.17,8.91]；
   原研究已做adaptiveCSP和第一轮标签校准，不把这些当新颖算法。
4. **EEGNet解释已修正。** 剩余12人源query52.92%、目标51.58%；先有源内判别偏弱，
   不主要归因于跨会话漂移。54份完整曲线2871epochs/8613steps及全部种子/collapse保留。
5. **纵向和幅度展示已补齐。** 新Fig4全18人×5会话两项配对差；三人下降实际
   −5.82/−0.67/−0.20pp，后两者不称明显损害。原12人任意留一主均值仍+6.22至+8.62。
6. **文献/格式/复现已完善。** 原研究书面同意与UT Austin2020-03-0073从索引Methods核实，
   不冒称成功下载原XML。14个实际引用、原文/摘要/元数据阅读范围、PLOS当前官方要求、
   依赖许可及具体MIT原代码/CC BY原派生内容方案均有记录。S1 Data41纯文本/代码成员，
   13QC表实际公开输入重放逐字节一致；没有EEG、权重或上游软件包。

研究仍为探索性离线任务标签解码。没有有效task-aware门控、持续MI隔离、生物学身份独立证明、
人类技能保持或临床结论。主比较12人、可靠性6人，54模型不等于54参与者。

## 集中剩余事项

- 学校/机构对本次二次分析的真实认定，现为“尚无结论”；不编造豁免。
- 作者对具体许可/公开清单的选择；MIT尚未自动激活，第三方组件边界保留。
- 作者最终亲自审阅及真实AI输出核验说明/批准；投稿系统未知项不代填。
- 精确Arial/Times生产字体尚未安装；图/PDF实际为Liberation替代，未冒称严格字体符合。
  DOCX文本/表格/媒体/编号结构核验完成，未声称已渲染原生Word版面。

## 版本与同步的实际边界

本轮原始结果和验收账本保持不变；新稿、代码、结果、图、完整文件清单和离线交付
形成真实本地Git版本。GitHub读取已核实370bc94，但当前写入工具要求审批而策略为never；
终端Git/R2代理也不可达。因此本轮没有谎称远端已更新或新R2完整GET完成。
已有科学备份和原真实回执仍保留。可在具备既有权限/网络的通路使用离线bundle/传输清单
接续同步，不需要重做实验，也不新增凭据。具体日志在
[本轮执行核验](research_logs/kumar_submission_optimization_20261015/run01/)。
