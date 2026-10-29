# BMT当前规则与第三作者信息核对

核对日期：2026-10-29（Asia/Shanghai）。目标仍为 **Biomedical Engineering / Biomedizinische Technik**，Research Article。

本次重新获取并阅读六份官方来源。网页工具直开返回405；同一公开官方地址的正常HTTPS GET均为200。11页作者指南、两份Word模板和网页正文均实际读取。响应长度与SHA保存在[policy_sources.json](policy_sources.json)，出版社原文件仅保存在工作区，不作为本项目稿件素材再发布。

## 当前格式

[作者指南](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Instructions%20for%20Authors.pdf)页眉仍为December 2024。其完整字节与10月28日核查相同；两份Word模板也相同。

| 项目 | 本次核实要求 | 官方位置 |
| --- | --- | --- |
| Research Article长度 | 6000词；表格未明确计数排除项，建议继续报告保守完整计数 | 指南p8 |
| 摘要 | ≤200词；Objectives、Methods、Results、Conclusions；缩写首次展开，避免引文/图表/公式 | p8 |
| 关键词 | 3–6；小写、字母序、分号分隔；避免缩写和重复标题词 | p8–9 |
| 图表 | 合计≤8；按首次引用顺序连续编号 | p8–9 |
| 参考文献 | ≤35；Vancouver；正文和文献表双向对应 | p8–9及Research Article模板 |
| Running head | ≤75字符，含空格 | p7 |
| 正文层次 | sentence case、无编号和句末句号；最多4级 | p9 |
| 主文件 | 可编辑Word或LaTeX；LaTeX另需完整PDF作为Main Document | p7 |
| 表格与公式 | 可编辑，不能用截图代替 | p9–10 |
| 图件 | 分别上传JPG/EPS/PNG/TIFF；像素图≥300dpi、混合线图≥600dpi；图中文字≥6pt；panel用大写字母 | p9 |
| 补充材料 | 每文件≤10MB，出版就绪 | p10 |

[期刊Submit信息](https://www.degruyterbrill.com/journal/key/bmte/html)继续要求独立的Ethical and Legal Declarations Word；采用Tier2数据政策。首次投稿需致主编Jens Haueisen的附信；指南p4要求至少5位候选审稿人的姓名、机构、国家、邮箱，与任一作者不同机构。正式[研究论文模板](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Template%20for%20Research%20Articles.docx)包含Conclusions。

## 第三作者的准确字段

用户提供姓名的标准拼音显示为 **Haoyang Yu**：given name `Haoyang`，family name `Yu`。全体顺序为 **Ziyuan Zhu\*, Sihao Liu, Haoyang Yu**；Ziyuan Zhu继续为通讯作者。

- 第三作者邮箱：`jiaguca3329@163.com`。
- 三人共同单位：College of Artificial Intelligence Medicine, Chongqing Medical University。
- 三人共同地址：Jinyun Campus, No. 61 Daxuecheng Middle Road, Shapingba District, Chongqing 401331, China。
- 未提供Haoyang Yu的ORCID，保留空值。指南将ORCID和机构邮箱列为推荐项目，未将163邮箱写为禁止项。

指南p6要求作者作出实质贡献、同意承担责任并批准终稿，禁止荣誉署名；p7规定接受后不允许改变作者名单。当前指令足以补充姓名、顺序和联系字段，用户随后确认第三作者协助GitHub推送、整理文件、参与数据核对和汇总，同意署名且无利益冲突。贡献据此如实填写。最终导出的三作者稿供全体作者核阅，候选审稿人与第三作者的关系仍由作者检查；既有双作者稿的批准记录保留原范围。

[独立声明模板](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Template%20for%20Ethical%20and%20Legal%20Declarations.docx)中的全体作者批准句应在本轮全体作者确实批准后使用。真实贡献可以按自然语言写，不需要为新增作者编造整套CRediT角色。

## AI、引用与伦理

[现行AI政策](https://www.degruyterbrill.com/publishing/for-authors/author-policies/artificial-intelligence)页面仍标September 2026。对稿件有显著贡献的AI辅助需披露；简单proofreading/copy-editing可豁免。政策明确把代码辅助纳入生成式工具范围，并要求作者核查准确性、对内容负责。语言自然化与如实披露是不同事项；不能因使用文风Skill而把实际研究/代码/写作协助改写为仅语法检查。

指南p3要求先前发表材料适当引用。学习通用文章组织方式不等于引入他人实验；若正文实质讨论或采用既有CSP/适应/迁移方法，应按真实来源归属，不把重组叙述写成已经验证的新算法或无依据的首创性。

[数据政策](https://www.degruyterbrill.com/publishing/for-authors/author-policies/data-sharing-policy)要求数据可用性信息真实可核验，第三方数据许可独立保留。本项目继续使用既有国家法规的二次分析豁免依据，并把原Kumar采集伦理与本次二次分析区分；本次没有新建学校确认、IRB批准或审批编号。

本次核对没有联系作者/审稿人、没有登录或提交ScholarOne，也没有执行新实验。最终稿生成后，仍以实际文件机械核对字数、图表数、引用对应、作者字段和声明一致性。
