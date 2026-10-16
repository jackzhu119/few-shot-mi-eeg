# Kumar2024公开数据二次分析：伦理适用依据的信息请求草稿

**状态：未发送。** 本文供作者审阅并向实际主管部门咨询时使用，收件部门
尚未指定。它不是伦理申请的替代品，不是委员会决定、豁免证明、追认批准、
投稿授权或最终稿批准。当前事实仍是：作者尚未取得本项目的机构结论。

## 中文草稿

**拟收件人：** 本单位实际负责研究伦理或科研合规的部门，由作者核实后填写。

**主题：** 咨询公开人类脑电数据二次分析的适用伦理要求及可引用依据

尊敬的主管部门老师：

我是Ziyuan Zhu，单位为重庆医科大学人工智能医学学院。我希望确认下述
公开数据二次分析适用的本单位及其他相关伦理要求，并取得可供论文准确
说明的实际依据。拟投稿论文题为“Longitudinal motor-imagery EEG decoding:
Frozen baselines, supervised recalibration, and task-measurement reliability”。

本项目使用Kumar2024公开研究数据，来源为NEMAR数据集`nm000177`，固定版本
`1.0.5`，来源许可为CC BY 4.0。数据按受试者编码组织；本研究不招募或接触
参与者，不开展新干预或新数据采集，也不尝试识别或关联到个人身份。
研究进行离线任务标签窗口解码，比较冻结模型、仅分类器重校准和完整
CSP/LDA重拟合，并报告测量及可解释性限制，不主张证明人体学习保持或临床疗效。

原研究论文报告了University of Texas at Austin伦理协议`2020-03-0073`和书面
知情同意。我们仅将这些信息归属于原始数据采集，不将其当作本项目在本单位的
伦理结论。公开可得及CC BY许可本身也不作为自动豁免的依据。脑电记录及编码后
的个体数据仍须依适用规则审慎处理；不声称编码消除了全部隐私风险。

本项目已开展离线分析，现于投稿材料定稿前核对伦理适用依据。我们不请求将
本次咨询表述为分析开展之前已经取得的批准。如本单位认为研究开始前需要
履行程序，请说明实际适用要求、当前状态的处理方式及后续应采取的步骤。

拟公开的本项目补充数据仅包括保存的预测、派生汇总、训练历史、与核查有关的
编码事件/角色/标签元数据，以及复现代码和说明，不重新发布原始EEG、信号
epoch/特征数组或模型权重。原始数据继续由官方来源提供并保留其许可与署名。
作者已为自己拥有的原创项目代码选择MIT，为原创派生数据、图表及文稿选择
CC BY 4.0；此选择不替代伦理审查或第三方权限。

烦请协助确认：

1. 在上述事实下，本项目属于本单位何种实际管理范围，适用哪些现行政策或规定？
   如适用审查、豁免、不需审查、非适用范围或其他分类，请使用贵部门实际采用的
   分类，不必限于本文列举的词语。
2. 对这类既有公开数据的使用及原始同意条件，有无额外要求？拟公开的编码元数据
   或其他派生结果是否需要删减、限制或进一步核查？
3. 哪项实际机构政策、公开规则或具体决定可以在论文伦理声明中引用？如已有具体
   决定，请仅提供真实存在的主管部门名称、决定日期、编号及可公开措辞；没有编号
   或个案书面决定时，请说明适用依据，不生成替代性证明。
4. 如不由贵部门负责，烦请告知实际应咨询的部门或正式程序。

我可按要求提供数据来源说明、研究方法、计划公开的字段清单和当前稿件。
任何论文表述将遵循实际答复与适用依据；在获得依据之前，不写入批准、豁免、
知情同意豁免或无需审查的既定结论。

Ziyuan Zhu

重庆医科大学人工智能医学学院

## English draft

**Status: unsent.** The author must identify the responsible office before use.
This draft is an information request, not an ethics determination, approval,
waiver, retrospective authorization or approval of the final manuscript.

**Intended recipient:** The institution's responsible research ethics or research
compliance office, to be identified by the author.

**Subject:** Applicable ethics requirements and reporting basis for secondary
analysis of publicly released human EEG data

Dear responsible office,

I am Ziyuan Zhu of the College of Artificial Intelligence Medicine, Chongqing
Medical University. I am seeking the actual institutional and other applicable
ethics requirements for the secondary analysis described below, together with
a basis that can be accurately reported in the manuscript. The proposed paper
is entitled “Longitudinal motor-imagery EEG decoding: Frozen baselines,
supervised recalibration, and task-measurement reliability”.

The project uses the publicly released Kumar2024 data, NEMAR dataset `nm000177`,
fixed version `1.0.5`, distributed by the source under CC BY 4.0. Records are
organized by participant codes. This project does not recruit or contact
participants, conduct new interventions or collect new participant data, and
does not attempt re-identification or linkage to personal identities. It
compares frozen decoding, classifier recalibration and full CSP/LDA refitting
on offline task-label windows. Its claims are limited to decoding and the
reported measurement limitations, rather than demonstrated human learning
retention or clinical efficacy.

The original collection paper reports University of Texas at Austin protocol
`2020-03-0073` and written informed consent. We attribute those statements to the
original collection; we do not treat them as a determination for this project
at this institution. Public access and a CC BY license are not themselves
assumed to establish an exemption. EEG recordings and coded individual-level
records require consideration under the applicable rules; coding is not claimed
to eliminate every privacy risk.

The offline analysis has already been carried out. We are checking the
applicable ethics basis before finalizing submission materials. We are not
requesting that this consultation be represented as approval obtained before
the analysis. If a procedure should have been completed before the research,
please advise the actual applicable requirements, how the current status should
be handled, and the appropriate next steps.

The planned project supplement contains saved predictions, derived summaries,
training histories, coded event/role/label metadata needed for auditing, and
reproduction code and documentation. It does not redistribute raw EEG,
signal epochs/features or model weights. The original data remain available
from their official source with their existing license and attribution. The
author has selected MIT for original project software and CC BY 4.0 for original
derived data, figures and manuscript text. Those choices do not establish ethics
clearance or rights over third-party material.

Could you please clarify the following:

1. Which institutional category and current policies or regulations apply to
   this project on these facts? Please use the institution's actual terminology,
   whether review, exemption, review not required, outside scope, or another
   applicable classification.
2. Are there additional requirements concerning use of the released data or the
   original consent conditions? Does release of coded metadata or derived results
   require removal of fields, restrictions, or further assessment?
3. What actual institutional policy, published rule, or specific decision may be
   cited in the manuscript's ethics statement? For any real project-specific
   decision, please provide the responsible office, date, identifier if one
   exists, and wording that may be reported. If no case-specific written decision
   or identifier exists, please identify the applicable basis rather than create
   substitute documentation.
4. If another office is responsible, please indicate the appropriate office or
   formal procedure.

I can provide the source description, study methods, proposed public field
inventory and current draft as required. Manuscript wording will reflect the
actual response and applicable basis. Until that basis is established, no
approval, exemption, consent waiver or review-not-required conclusion will be
asserted as an accomplished fact.

Ziyuan Zhu

College of Artificial Intelligence Medicine, Chongqing Medical University

## Source and policy context for author review

This context is separate from the unsent request. PLOS ONE requires accurate
ethics reporting for human research and human data as applicable. Its human-data
policy recognizes exemptions under applicable IRB/ethics committee regulations;
its submission guidelines require a detailed explanation when approval was not
needed. These pages do not establish a universal requirement for a new written
institutional decision for every analysis of public data. The institution's
actual applicable policy or decision remains to be established for this project.

- [PLOS ONE Human Subjects Research](https://journals.plos.org/plosone/s/human-subjects-research)
- [PLOS ONE Submission Guidelines](https://journals.plos.org/plosone/s/submission-guidelines#loc-human-subjects-research)
- [Source NEMAR dataset](https://nemar.org/dataexplorer/detail?dataset_id=nm000177)
- [Scoped project licenses](../LICENSING.md)
- [Policy and license review record](../research_logs/kumar_review_revision_20261016/run01/policy_license/REPORT.md)
