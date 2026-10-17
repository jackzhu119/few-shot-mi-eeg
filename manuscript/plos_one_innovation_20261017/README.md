# 论文2：PLOS ONE 创新分析与投稿文件

**Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**

作者：Ziyuan Zhu。修订日期：2026-10-17。

## 阅读与使用

| 文件 | 用途 |
| --- | --- |
| [PLOS_ONE_Manuscript_Reading.pdf](PLOS_ONE_Manuscript_Reading.pdf) | 优先阅读：主稿与全部6张图合并，适合通读与批注 |
| [PLOS_ONE_Manuscript_Reading.docx](PLOS_ONE_Manuscript_Reading.docx) | 带图可编辑阅读版 |
| [PLOS_ONE_Manuscript_Submission.docx](PLOS_ONE_Manuscript_Submission.docx) | 投稿主文件：单栏、12 pt、双倍行距、连续行号、可编辑表格，图件单独上传 |
| [PLOS_ONE_Manuscript_Submission.pdf](PLOS_ONE_Manuscript_Submission.pdf) | 投稿版排版预览 |
| [S1_Supplementary_Methods.pdf](S1_Supplementary_Methods.pdf) / [Word](S1_Supplementary_Methods.docx) | S1 Text：原方法、统计细节及新增S12错误转移分析 |
| [S2_Reproducibility.pdf](S2_Reproducibility.pdf) / [Word](S2_Reproducibility.docx) | S2 Text：数据来源、软件版本、复现命令与核验 |
| [S1_Data.zip](S1_Data.zip) / [数据包说明](S1_Data_README.md) | 101成员的扩展数据与代码包；实际解压重放18个新增科学文件一致 |
| [Cover_Letter.docx](Cover_Letter.docx) / [PDF](Cover_Letter.pdf) | 一页附信 |
| [Author_Submission_Details.md](Author_Submission_Details.md) | 已有作者信息、Funding、伦理依据及投稿系统字段 |
| [Figure_Captions.md](Figure_Captions.md) | 六张图的完整图注，与主稿一致 |
| [Revision_Notes_ZH.md](Revision_Notes_ZH.md) | 中文修订、创新结果和实验完整性说明 |
| [Paper2_PLOS_ONE_Innovation_20261017.zip](Paper2_PLOS_ONE_Innovation_20261017.zip) | 上述文件、图件、源稿、许可与核验资料的完整下载包 |

`Figures/` 供应六张独立600 dpi RGB TIFF、便于浏览的PNG/PDF和数值CSV。`Sources/` 保存本轮Markdown与BibTeX的精确副本；完整仓库路径和构建脚本可从[研究分支](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/learning-preserving-bci)取得。软件复现以S1 Data内的说明和脚本为准。

## 本轮增加的贡献

引言前置四项贡献。主队列等标签条件下，空间重拟合额外贡献5.47个百分点，占7.42点平均总增益的73.7%；新Fig 5把该增益分解为16.04点纠错和10.57点新增错误，并展示两类平均recall。新Fig 6呈现所有参与者的联合增益、五个目标会话的队列曲线及删除任意一位参与者后的影响分析。Table 6提供两类完整区间。主稿现为6图6表，原比较层级和完整队列结果保留。

新增结果从同一批已保存预测计算。新S1 Data保留原69成员并增加32成员；压缩文件为2,078,150 bytes。所有18个新增科学输出已从实际ZIP解压后逐字节复现。具体数值、分母、等权规则和检查依据见S1/S2与中文说明。

## 文件与格式核验

主标题95字符、短标题55字符、摘要251词；参考文献按首次引用编号，使用核验的期刊缩写；预印本单独标识。投稿版正文和参考文献均为双倍行距，六张表保持可编辑，图注按首次引用顺序放置。所有DOCX均转换为PDF并逐页检查。格式、页面与文件SHA-256见 `formatting_audit_20261017.json`、`visual_QA_20261017.json` 和 `PACKAGE_MANIFEST.json`。

本轮分析与导出得到AI辅助，正文、图注和补充材料已说明实际范围。文字经过结构与表达修订，未宣称外部AI检测分数。投稿系统中Funding单独填写。文件准备不包含向期刊发送或提交的操作。

## 来源与许可

源EEG：Kumar2024，NEMAR nm000177/v1.0.5，https://doi.org/10.82901/nemar.nm000177.v1.0.5 。数据作者与来源许可见S1 Data。

原项目脚本适用MIT；本轮原始稿件、图件及衍生结果适用CC BY 4.0，第三方资料保留自身条款。`LICENSES/`和S1 Data内的扩展许可说明给出组件范围。字体文件和原始EEG不随本包分发。

本轮以研究分支内容提交 `30f23ed3c9afd271a3821fceaa99ab932bf25e5f` 为起点。此前稿件与归档保持其原日期和原科学记录，当前文件以本目录为准。
