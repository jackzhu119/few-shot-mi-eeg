# Biomedical Engineering / Biomedizinische Technik 投稿要求核对

核对日期：2026-10-27（Asia/Shanghai）。目标为 De Gruyter Brill 的 **Biomedical Engineering / Biomedizinische Technik**（BME–BMT，journal key `BMTE`），拟按 **Research Article** 准备。以下来自官网当日链接的作者指南、正式 Word 模板和出版社政策，未使用第三方期刊排行榜替代官方要求。

## 已阅读的官方来源

| 来源 | 实际阅读范围 | 核对记录 |
| --- | --- | --- |
| [期刊主页与 Submit 信息](https://www.degruyterbrill.com/journal/key/bmte/html) | 期刊身份、scope、S2O、Submit、数据政策等级、下载链接 | 当前页面明确 Tier 2；S2O按年度运行 |
| [Instructions for Authors](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Instructions%20for%20Authors.pdf) | 11页全文，重点第2–10页及第11页参考文献示例 | HTTP200；849,140 bytes；SHA256 `5a11215a9b3ae9af62b10667e35b15cba20cb286102347c628ec0b1a304d52dc` |
| [Research Article Word template](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Template%20for%20Research%20Articles.docx) | 全部段落、表格和样式 | HTTP200；48,642 bytes；SHA256 `3ce360209b6393ee82932e9fb770a49156d20403634bcc22ba63ab60effeab15` |
| [Ethical and Legal Declarations template](https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Template%20for%20Ethical%20and%20Legal%20Declarations.docx) | 全部必填/选填字段和填写说明 | HTTP200；27,927 bytes；SHA256 `8facc5b46d8dc245e1814a9f749e2ddc4d84e2189b20ea9f511886c38d9ef230` |
| [AI-Policy for Authors](https://www.degruyterbrill.com/publishing/for-authors/author-policies/artificial-intelligence) | Authorship、Disclosure、AI Generated Images、Rights/Accuracy、Peer Review | 页面标注 **As of September 2026**；HTTP200；90,628 bytes；SHA256 `48ef040546581f9772a97ca74ef06c1d7e63df7f14d033855c3df105f801ffc7` |
| [Data Sharing Policy](https://www.degruyterbrill.com/publishing/for-authors/author-policies/data-sharing-policy) | 四级政策、数据可用性声明、数据引用 | HTTP200；94,854 bytes；SHA256 `810b837f47079569d74fbedeb50a14f44ab83d2609e11457432368342938d758` |

作者指南页眉写“last update: December 2024”；当日官网提供的该PDF元数据创建/修改时间为2026年5月。此处记录实际版本，不自行推断之后尚未发布的规则。来源文件保存在工作区 `/workspace/bmt_policy_20261027/`；仓库保留本阅读记录与链接，不擅自再许可出版社文件。

## Research Article 格式

| 项目 | 官网明确要求 | 本稿落实方式 |
| --- | --- | --- |
| 字数 | 6,000 words | 精简正文；官网表格未明确参考文献/图注是否计入，分别报告各部分字数 |
| 摘要 | **最多200词**，**Objectives; Methods; Results; Conclusions** | 四段结构；第一次出现展开缩写，无引文/公式 |
| 关键词 | 3–6个，字母序、小写、分号分隔 | 避免缩写与重复标题词 |
| 图和表 | **合计最多8个** | 当前4图＋3表，共7个；详表放补充材料 |
| 参考文献 | 最多35篇 | Vancouver，按首次引用顺序；正文方括号编号；超过6作者列前6位＋et al. |
| 短标题 | 不超过75字符，含空格 | 单独核数字符 |
| 标题/小标题 | sentence case，冒号后小写；小标题不编号，无句末句号 | 层次最多4级，同层分节至少2个 |
| 结构 | Title page; structured Abstract; Keywords; optional abbreviations; Introduction; Materials and methods; Results; Discussion; Acknowledgments; References; Table/Figure legends | 单独伦理法律声明文件，主稿信息一致 |
| 投稿文件 | Word或LaTeX；LaTeX稿需上传完整PDF为Main Document | 提供可编辑Word及阅读PDF；不沿用PLOS格式声明 |
| 表格 | 可编辑Word/LaTeX，不用图片或Excel代替 | 有标题、列名、单位与必要脚注；缩写展开 |
| 图 | 单独上传JPG/EPS/PNG/TIFF；像素图≥300dpi，线条与像素混合图≥600dpi | 保存600dpi PNG，附矢量PDF/SVG；文字≥6pt；各panel用大写字母 |
| 图编号 | `Figure`＋连续阿拉伯数字，全部在正文引用 | 不沿用`Fig`；正文按首次引用顺序排列 |
| 公式 | 可编辑数学文本；引用的展示公式连续编号 | Word公式对象，不制作成图片 |
| 补充文件 | 每文件≤10MB，publication-ready，按交付原样发布 | 补充方法、完整结果表、图底层数据分别交付；不把大原始包直接当补充文件 |

正式Research Article模板的Normal样式为Times New Roman 12pt、单倍行距，A4页面；这是模板观察值。作者指南未另列强制字体/行距数字，不把自拟排版偏好描述成期刊硬性要求。

## 伦理、作者、数据及AI声明

期刊要求提交单独的 **Ethical and Legal Declarations Word**，按模板顺序包括：Acknowledgments；Research ethics；Informed consent；Author contributions；Use of Large Language Models, AI and Machine Learning Tools；Conflict of interest；Research funding；Data availability。与主稿有差异时，模板内容将用于排版，故必须逐项一致。

本项目伦理陈述沿用真实法规依据：公开Kumar2024/NEMAR二次分析，依据中国2023年《涉及人的生命科学和医学研究伦理审查办法》第32条第（一）项豁免额外审查。原UT Austin协议2020-03-0073及原书面知情同意仅对应原数据收集。不恢复“学校科研处确认”的已删除表述，不捏造本项目IRB编号或机构豁免证明。

原数据、派生结果及代码都有实际公开位置，应填写数据可用性声明。主页写Tier 2，代表鼓励分享，而非凭此虚构更高等级的数据强制要求；本研究已公开的预测/指标、固定提交和NEMAR DOI仍应清楚列出并在参考文献引用。源数据许可与原创代码MIT/原创派生成果CC BY 4.0范围分别保留。

**文风自然与AI披露是两个问题。** 出版社2026年9月政策要求披露对稿件有实质贡献的AI输出；只有简单proofreading/copy-editing可不披露。官方表述包括“**The use of AI tools must be disclosed when their output has significantly contributed to any part of your manuscript.**” 该政策覆盖代码辅助工具与实质文本生成。本项目使用包括代码、核查、后处理、绘图程序及稿件协助，不能改成“仅语法润色”或删除全部AI声明。

当前政策也写明不接受AI/机器学习工具生成的论文，作者须对研究与稿件负责；同页允许在披露前提下的AI辅助，并要求核实准确性。因此本次交付应作为**供作者独立核验、实质修订及最终批准的审阅稿**，不能把工具生成草稿的自然化当成规避政策或自动通过检测。声明应真实描述辅助范围。数据图由保存数值经确定性代码绘制，不使用生成式图像修改实验图或伪造数据。

模板中的“the author ... approved its submission”只能在作者实际批准当前版本后使用。历史2026-10-16批准不自动覆盖本轮新增V2/V3内容；当前可先保留责任说明及待最终批准状态，不代签新的批准。

## 投稿操作信息

- 官方投稿入口：[ScholarOne BMT](https://mc.manuscriptcentral.com/bmt)。本轮不登录、操作或提交。
- 首次投稿须附Cover letter，致Editor-in-Chief，并简述实质新意。重点应为**相同约20个当前会话标签下，空间滤波器重学的额外收益及其组件机制**；不能把普通CSP/EA或未优于强基线的新候选称为首创获胜算法。
- 至少提供5位建议审稿人的姓名、机构、国家和邮箱；应与作者不同机构，并尽量不同国籍。无真实依据不编造邮箱、关系或利益冲突。
- 官方强烈推荐机构邮箱及ORCID；私人邮箱并未被写成绝对禁止。现有真实邮箱/ORCID保持，机构邮箱若要补充由作者提供。
- 投稿即声明稿件未同时由其他期刊审理。仓库存在PONE-D-26-52050历史投稿信息，本次没有新的真实撤回/拒稿状态；因此不会代作者宣称已满足排他投稿状态。可以继续准备全部新稿，而不预填未经核实的独家投稿确认。
- 主页当前S2O卷允许作者免费开放发表，指南说明S2O逐年实施。它支持“当前S2O无作者出版费用”，不支持未来接收年份永久免费或已取得特殊费用豁免的承诺。不涉及购买、充值或费用门控。

## 文风和证据处理

正文让阳性结论先行：原12人完整CSP/LDA比仅LDA更新额外+5.47个百分点，原主要完整更新比冻结+7.42个百分点。方法中一次说明原主/次终点、参与者单位与标签预算；讨论集中说明适用范围，删除重复自我辩护。

同样保留决定结论含义的事实：后续6人已用于发现；V3 BN效应有预算范围；新几何候选和KL主比较未胜出；窗口为cue锚定标签窗口；独立外部验证尚未完成。这些事实不应从稿件消失，也无需在每段重复。清晰直接的结果叙事比堆叠“可能、谨慎、不能”等套话更符合期刊要求。
