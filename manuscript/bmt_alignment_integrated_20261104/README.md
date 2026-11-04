# EA增量与弱类别覆盖：隔离扩展稿

目标期刊：**Biomedical Engineering / Biomedizinische Technik**，Research Article。作者：Ziyuan Zhu*, Sihao Liu, Haoyang Yu。工作分支：`research/paper2-alignment-integrated-revision`。基准：`da2a3acee24746981bbcdd779ab88132da6e24c4`；本轮执行前固定方案：`13dd7646c4ce37db40504154388e76b4c6ca6595`。

本稿围绕同样校准信息下EA相对完整CSP/LDA重拟合的增量展开。原PLOS存档主要研究Full与LDA-only，10月29日BMT版已加入EA/BNCI；本轮新增弱类别/联合收益、EA专属QC、共享坐标和尺度/协方差对照，以及EA任务窗分析。[相关稿件精确关系](../../docs/paper2_alignment_integrated_20261104/related_manuscript_overlap.md)区分这些版本。本轮未改main或正在审理的投稿文件。

## 审阅文件

- [带图英文PDF](BMT_Manuscript_Reading.pdf)，19页，五图全矢量。
- [可编辑阅读Word](BMT_Manuscript_Reading.docx)。
- [主稿Word](BMT_Manuscript_Submission.docx)，2张可编辑表、4个可编辑公式；5张图和图注单独组织。
- [补充方法PDF](Supplementary_Methods.pdf)／[Word](Supplementary_Methods.docx)，33页，保留旧控制与新增完整结果。
- [独立伦理与法律声明](Ethical_and_Legal_Declarations.md)／[Word](Ethical_and_Legal_Declarations.docx)。国家法规二次分析豁免依据不变；AI协助集中披露于此。
- [五张主图与底表](figures/)：每图PDF/SVG、600dpi RGB TIFF/PNG、对应CSV和格式清单。
- `Supplementary_Data_and_Code.zip`：可独立核查的公开预测/表格、分析代码和协议；不含EEG或模型权重。
- `Integrated_Revision_Review_Package.zip`：完整审阅包，解压后阅读；本轮不执行期刊投稿。
- [一行保存结果复现与详细说明](reproduction.md)。

## 经核验的结果

原Kumar主要12人EA−Full为+5.30pp，BNCI9人为+5.65pp。新增动态弱类别召回分别提高10.45pp与8.52pp，BA/W同时改善10/12和9/9。新共享21维敏感性保留Kumar+5.07pp；其EA−RMS为+0.91pp、区间跨零。BNCI EA−RMS为+4.63pp。

新增EA时间窗结果是重要限定：同条件9人cue5s增益7.85pp，task2s为0.13pp，配对变化−7.73pp [−12.17,−3.76]；这同时改变信号锚点、时长和局部滤波。两窗共享合格身份，实际支持为4–19标签，与原全支持范围分开。正文、摘要、图5及补充材料均报告。

## 已实际完成

- 82,920份保存决策重放，1,836原终点BA重建差0；新增W/H/左右召回/联合受益/EA-QC。
- 544次新经典CPU拟合：396匹配对照+148EA phase；保留32原未定义单元。54个EEGNet源模型未重训。
- 31项针对性测试；P1独立105,672项核对，P2独立5,440项评分核对。新旧bootstrap与比较角色分别保留。
- 17张表在干净目录从保存预测/单元回执重建，逐字节一致；无需读取EEG/模型或重新拟合。
- 摘要164词，完整投稿Word4983词，5图+2表，17条主文参考文献；均在BMT本次核实上限内。

## 当前状态

这是新增结果后的作者审阅稿，10月29日批准不自动延伸。三作者、贡献、利益冲突和资助沿用已提供事实；无虚构新批准。用户最新确认原PLOS仍在审理，未访问投稿系统核实其当前文件。其余待实际作者审阅的事项集中于`AUTHOR_REVIEW_ITEMS.md`，不阻断本轮研究和文档交付。未执行的P3增强单列[后续方案](../../docs/paper2_alignment_integrated_20261104/future_validation_plan.md)。
