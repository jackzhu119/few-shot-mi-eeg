# 论文2当前进度与论文状态

## 2026年10月24日：当前HPC运行入口

[本地初始化与短命令续跑](releases/paper2-hpc-v2-20261023/README.md)
优先使用GitHub官方API、raw备用，入口先保存在学校本地；不再每次先依赖raw取代码。
当前资源为`hpc_gpu`、每任务1GPU/16CPU/128G、最多2项并行，
通过伴随运行配置提交，原科学输入和断点身份不变。token仅保存在学校私有0600文件，
公开仓库不含值；首次实际写权限仍由原授权步骤核验。46项相关测试及完整125MB
API下载/本地不启动安装已通过；学校实际网络、调度与GPU未由本环境访问。


## 2026年10月23日：学校HPC独立研究扩展V2

**直接下载更新：**按作者新要求，[学校一行GitHub下载入口](releases/paper2-hpc-v2-20261023/README.md)
提供四分片输入、源码及安装器；无需个人电脑中转或R2权限。分片还原原包，
原输入SHA/科学配置不变，数据原许可和署名一并保留。

[启动与恢复说明](experiments/hpc_recalibration_v2/README.md)、
[科研方案与文献核查](docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md)
和[实际交付报告](research_logs/paper2_hpc_v2_20261023/REPORT.md)已完成。
采用三项并行单A100任务，每项24CPU/128G；首批6开发参与者、24独立任务，
6项经典对照和18项新版本神经训练。固定源码为`71e79fb6f70346ac2fc307c0b93dc23af101e2c7`。
97项针对性合成测试通过，125MB真实输入包及离线安装已核验，学校GPU尚未运行。
新方案检验相同标签预算下的更新强度，主对照为更强的EA方法；旧54模型及
已投稿稿件保留。R2本次实际返回401，0对象上传成功；失败回执保留，学校
本地持久训练不依赖此权限恢复。新工作位于`research/paper2-hpc-v2-20261023`。

## 2026年10月19日：高清图件与投稿系统核查

[最新投稿辅助文件](manuscript/plos_one_submission_support_20261019/README.md)已整理最新完整提交包、600 dpi原始TIFF图包、六图高清审阅PDF及266词系统摘要。完整包的12份实际上传文件与现有main逐字节一致。作者提供的系统合并PDF图件实际为72 dpi，系统首页仍用旧摘要；原稿、图件内容、科学结果与已有归档包不变。补充附件在合并PDF中仅有链接，实际上传字节未获核验；没有代作者修改系统或提交。完整范围见[核查证据](research_logs/kumar_submission_support_20261019/run01/README.md)。

## 2026年10月19日：投稿稿局部修订

[本轮修改与核验](docs/kumar_limited_revision_20261019.md)基于已提交稿对应的`19a5909`，按作者最新要求将现行伦理声明统一为第32条第（一）项法规豁免，删除学校确认；同时处理九项文字/方法说明/图表格式意见。原实验、统计数值与历史审计记录保持可追溯。[现行投稿文件](manuscript/plos_one_innovation_20261017/README.md)及[英文系统伦理声明](manuscript/plos_one_innovation_20261017/Ethics_Statement_20261019.md)为当前入口；下方2026年10月17日及更早记录保留其历史范围。

## 2026年10月17日最终投稿核查

[最新PLOS ONE核查与上传文件说明](docs/kumar_main_submission_check_20261017.md)：主稿声明位置、数据访问日期、图件及公开数据已核查。作者于2026年10月17日确认无法访问可识别参与者身份的信息；该事实已补入方法部分，官方Human Participants Checklist第3项已完成。当前提供正式主稿、完成版清单与短名图件上传包。

## 当前入口：创新分析与PLOS ONE文件（2026-10-17）

[当前完整包](manuscript/plos_one_innovation_20261017/README.md)与[本轮中文说明](docs/kumar_innovation_revision_20261017.md)取代下方较早的写作入口。新增等标签组件增益的错误转移、两类平均召回、五会话曲线和参与者影响分析；引言列出四项贡献，主稿6图6表，S1/S2/附信同步更新。4,290条query、25,740行预测、90组拟合标签配对核验一致，实际新S1 Data中的18个科学文件重放逐字节一致。当前保存结果分析与原训练环境分别记载；完整旧软件检查的环境依赖状态见本轮验证记录。历史实验、原包和既有伦理确认均保留；未执行投稿。

## 最新写作版本（2026-10-17）

[论文2完整修订包](manuscript/plos_one_revision_20261017/README.md)与[中文修改说明](docs/kumar_editorial_revision_20261017.md)为当前阅读入口。本轮重写标题、摘要、结果、讨论、S1 方法、S2 复现说明及附信，集中呈现同标签预算的组件更新贡献，压缩重复自我否定。原科学结果、伦理记录和封存版本继续保留。后续任务阶段研究仍按其独立方案管理。

伦理版已实际同步：固定`d03b5a3`及tag，5关键公开文件完整读回；私有R2324对象/34,005,655 bytes最终完整GET通过，首轮61失败及后续修复回执均保留。[实际伦理同步收尾](docs/kumar_ethics_sync_closeout_20261016.md)。

## 最新伦理澄清（2026-10-16，作者报告机构确认）

学校科研处于2026-10-16确认本次二次分析适用免予额外伦理审查，无编号；按已确认作者单位记为重庆医科大学。此为作者报告的机构免审确认，不是新IRB批准或已独立认证的机构文件。原采集伦理与本次免审分别表述。
[新伦理修订审阅包](manuscript/plos_one_submission_ethics_20261016/README.md)与[依据和范围](docs/kumar_ethics_statement_revision_20261016.md)取代下方历史“伦理待补”状态。既有科学批准保留；原科学结果、旧包和账本不变，未投稿。

## 作者已确认审阅及批准（2026-10-16，作者报告日期）

作者已明确表示阅读并亲自核对、暂无修改意见，批准当前科学稿件
`f2901decfc39b2adecae13253ee4b1159a4f9a4b`／`paper2-plos-source-20261016`。
[原话及确认记录](research_logs/kumar_author_final_confirmation_20261016/run01/README.md)
和[稿件状态补充](manuscript/kumar_author_review_addendum_20261016.md)保留准确范围与文件SHA。
个人核验/批准不再列为待办；未推断作者逐条检查了所有引文、独立重算或渲染了原生Word。

作者同时报告已取得伦理批准；审批机构/委员会、真实决定日期、编号或确认无编号及本次二次分析的
适用范围仍待补录。2026-10-16是作者审阅日期，不自动当作伦理批准日期。现有完整AI辅助披露保留。
封存PDF/Word及下方旧快照中的pending为本次回复前状态，现由本补充说明更新；尚未投稿。

## 最新已验证同步（2026-10-16 UTC）

稿件固定内容提交 [`f2901de`](https://github.com/jackzhu119/few-shot-mi-eeg/commit/f2901decfc39b2adecae13253ee4b1159a4f9a4b)
已推送 main/研究分支及固定标签，10份关键公开文件完整读回一致。
本轮私有R2共692对象／89,459,262 bytes，全部完整GET/SHA256，失败0。
[实际收尾记录与回执](docs/kumar_review_revision_sync_closeout_20261016.md)列明全部范围与限制。
以下内容提交保持封存，后续只追加同步元数据；尚未代作者投稿。

## 当前修订：审稿意见核验与作者审阅稿（2026-10-16 UTC）

最新稿件入口为 [2026-10-16 完整投稿审阅包](manuscript/plos_one_submission_20261016/README.md)：
[带图 PDF](manuscript/plos_one_submission_20261016/manuscript_for_review.pdf) /
[Word](manuscript/plos_one_submission_20261016/manuscript_for_review.docx)。
[逐条审稿回应](docs/kumar_review_response_20261016.md)明确区分采纳、部分采纳和不成立的意见。
[简短修订报告](docs/kumar_submission_revision_report_20261016.md)列明新发现与限制。

- 54 个源模型与一次冻结 query 的原结果、主次比较和区间不变；无剩余训练、无新 query/Pod 操作。
- 新增审稿后探索性配对检验：主差仍 +7.42pp，raw p=0.01953125，四项 Holm p=0.05859375；不追认确认性显著。
- 新 S1 Data 补齐保存的可靠性/drift 底表与新统计输入；原 2026-10-15 包和 816 项科学保护文件保持不变。
- 作者已明确激活限定 MIT/CC BY 4.0，见 [许可范围](LICENSING.md)。以下历史“许可待定”已被本次真实选择取代。
- 作者已报告伦理批准，实际机构、决定日期、编号与范围待补；原机构咨询草稿保留为未发送历史材料。
- 作者已于报告的2026-10-16完成阅读/亲自核对并批准上述固定稿；尚未投稿。

固定内容版本使用 `paper2-plos-source-20261016` 标签。最终同步与软件检查状态见
[本轮交付核验](research_logs/kumar_review_revision_20261016/run01/README.md)。
整仓测试实际 1,257 通过、13 失败、1 跳过；失败来自受保护历史测试的主机/claim/磁盘前提和子进程导入路径，
未绕过门或改写失败。新增统计 24 项合成测试、Ruff、smoke 和 MOABB 合成检查通过。

**以下为按当时状态保留的旧快照，不作为当前命令、许可或同步状态。**

## 最新同步状态

完整审阅稿已实际推送至研究分支固定提交
[`f735ffd1e49915e41f28b727f5d3279ad337c692`](https://github.com/jackzhu119/few-shot-mi-eeg/commit/f735ffd1e49915e41f28b727f5d3279ad337c692)，
GitHub已读回同SHA；私有R2的434对象／82,392,690 bytes全部完整GET及SHA256通过，
失败0。主回执完整SHA256为
`7968542cb16687bdeb5670a8372e2054e865ce90278dec8401ec7da4e3171874`。
具体[同步收尾与审阅入口](docs/kumar_submission_sync_closeout_20261016.md)给出实际证据。
原封存稿及下文“代理阻塞／未推送”按当时历史保留，已不代表当前同步状态。
机构认定、具体许可选择和本人最终审阅仍待真实完成，未代作者投稿。

## 原作者审阅包封存快照

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
