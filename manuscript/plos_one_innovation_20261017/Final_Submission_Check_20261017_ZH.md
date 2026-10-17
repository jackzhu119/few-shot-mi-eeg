# 论文2 PLOS ONE 最终投稿核查

核查日期：2026年10月17日。科学内容基线为 `1d78ceb080c96865e3ed2b0a6b75ff81bccc6318`，本轮补充投稿所需的声明位置、数据访问日期、官方参与者清单及上传文件整理。

## 当前结论

稿件结构、正文格式、图表技术参数、参考文献、数据公开性、代码与许可均通过本轮核查。两项可直接修复的文字问题已处理：利益冲突声明移至投稿系统字段，数据访问日期补入方法部分。Human Participants Checklist 已按现有事实预填。

**正式提交前仍需作者补充一项事实：在本研究期间，是否曾接触能够识别具体参与者的信息或身份链接密钥。** 这是 PLOS 官方 Human Participants Checklist 第3项的明确要求。现有作者记录说明使用编码数据、不联系参与者、不尝试重新识别；这些记录没有直接回答能否接触身份信息，因此清单保留“Author completion required”，主稿没有代填未经确认的否定声明。

## 核查结果

| 项目 | 实际文件或证据 | 结论 |
| --- | --- | --- |
| 题目与摘要 | 主标题95字符、短标题55字符、摘要251词；摘要无文献引用 | 通过 |
| 主稿格式 | 英文DOCX，单栏，12 pt Times New Roman，正文和参考文献双倍行距，连续行号和页码 | 通过 |
| 文件状态 | 正式稿无嵌入图件、无锁定或保护、无批注及修订痕迹；六张表为真实可编辑表格 | 通过 |
| 结构与引用 | 标题页、摘要、引言、方法、结果、讨论、结论、致谢、参考文献及补充信息说明；图表首次引用与编号顺序匹配 | 通过 |
| 图件 | 六张独立TIFF，600 dpi、RGB、LZW压缩，逐张小于10 MB；当前像素、字体和源数据已核对 | 通过 |
| 上传命名 | 另提供Fig1.tif至Fig6.tif短名副本，与原TIFF逐字节一致 | 已整理 |
| 补充材料 | S1 Text、S2 Text和S1 Data分别提供；S1 Data为2,078,150 bytes | 通过 |
| 数据公开性 | 版本DOI 10.82901/nemar.nm000177.v1.0.5可解析，NEMAR来源和CC BY 4.0许可可核对；公开GitHub中的S1 Data可无需登录下载 | 通过 |
| 数据包完整性 | S1 Data的101个成员逐项大小、SHA-256和CRC核对一致；原有18个新增科学结果的实际重放记录继续适用 | 通过 |
| 软件与许可 | 原始项目软件MIT，原创稿件、图件和派生结果CC BY 4.0，第三方材料保留对应条款；复现脚本与说明可取得 | 通过 |
| 伦理说明 | 原始研究批准和知情同意、本次二次分析的机构免予额外伦理审查确认分别报告；未编造额外批准编号或机构文件 | 已报告 |
| 数据访问日期 | 元数据访问记录为2026年10月10日；选定EEG及配套元数据取得记录为2026年10月11日 | 已补入方法 |
| Funding与利益冲突 | Funding和利益冲突声明在作者信息表保留，供投稿系统填写；利益冲突句已从两份主稿移除 | 已修正 |
| AI辅助披露 | 正文、图注及补充材料说明工具、使用范围与输出核验；作者承担最终责任 | 已报告 |
| Human Participants Checklist | 官方2026版表格已预填并检查，身份信息访问情况尚待作者提供事实答复 | 作者须补全第3项 |

代码DOI或Zenodo归档属于可以进一步增强版本持久性的做法；当前原始数据有版本DOI，派生结果随S1 Data提供，代码在公开GitHub中可取得。本轮未把新增代码DOI列为初投稿的硬性条件。

## 本轮主稿修正

从正式稿与阅读稿中删除独立的利益冲突句，并将该部分标题改为“Author contributions”。利益冲突声明仍在 `Author_Submission_Details.md` 中完整保留，用于填写系统字段。

方法部分依据实际收据补入：

> Dataset metadata were accessed on 10 October 2026, and the selected EEG recordings and accompanying metadata were retrieved on 11 October 2026. This secondary analysis used the released coded participant identifiers; no participants were contacted and no re-identification was attempted.

日期来自收据内的UTC时间字段，并经原始文件校验记录交叉核对。科学结果、端点、表格数值及原有统计口径保持一致。

## 投稿时使用的文件

`PLOS_ONE_Submission_Files_20261017.zip` 用于一次性取得需要上传的文件，解压后分别选择系统中的文件类别。该ZIP本身不作为整篇稿件上传。

| 文件 | 投稿系统用途 |
| --- | --- |
| PLOS_ONE_Manuscript_Submission.docx | 主稿 |
| Fig1.tif至Fig6.tif | 六张独立图件 |
| S1_Text.pdf、S2_Text.pdf | Supporting Information，对应S1 Text、S2 Text |
| S1_Data.zip | Supporting Information，对应S1 Data |
| Cover_Letter.pdf | Cover Letter |
| Human_Participants_Checklist_Author_Completion_Required.pdf | 完成第3项后作为期刊要求的参与者研究清单上传 |

阅读版PDF供作者通读和批注；正式稿、图件和补充材料按上表分别提交。

## 作者在投稿系统完成的内容

使用已记录的作者姓名、单位、通讯邮箱、ORCID及CRediT贡献。对应作者需要在个人资料中绑定ORCID，并在系统填写Financial Disclosure、Competing Interests和Data Availability。系统最终生成的合并PDF需由作者核对后确认提交。

作者信息表保留了此前针对2026年10月16日版本的审阅记录；本次新增分析及最终附件应由作者在正式提交时一并核准。关于事先联系期刊、编辑建议、回避审稿人及相关稿件，应按实际情况填写。

## 官方依据

以下官方页面于2026年10月17日核查：

- [PLOS ONE Submission Guidelines](https://journals.plos.org/plosone/s/submission-guidelines)
- [PLOS ONE Figures](https://journals.plos.org/plosone/s/figures)
- [PLOS Human Subjects Research](https://journals.plos.org/plosone/s/human-subjects-research)
- [PLOS官方2026版Human Participants Checklist](https://journals.plos.org/plosone/s/file?id=ba3b%2FPLOS_Human_Participants_Research_Checklist_2026.pdf)
- [PLOS Data Availability](https://journals.plos.org/plosone/s/data-availability)
- [PLOS Materials, Software and Code Sharing](https://journals.plos.org/plosone/s/materials-software-and-code-sharing)
- [PLOS Ethical Publishing Practice](https://journals.plos.org/plosone/s/ethical-publishing-practice)

具体文件哈希、页面核验、数据可取得性与日期证据收录于同目录对应的最终核查记录。此次工作包括文件准备、核查和GitHub版本同步；期刊系统内的正式提交尚未执行。
