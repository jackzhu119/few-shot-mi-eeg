# 论文2当前进度与论文状态

更新日期：**2026-10-15（UTC）**。工作分支：`research/learning-preserving-bci`。
本次汇总基于已推送的 `21ca8d89e866ee496d2cddbb6e52c10f3f83136a`、
现存冻结结果和作者实际回复。本页是当前入口；旧交接按原日期作为历史保留。

## 当前结论

冻结 CPU 基线、**54/54 个源 EEGNet 模型**及一次只读 always-frozen query
评估均已完成。54 个源模型和 query 评估分别获得真实父确认。
剩余已冻结源训练为 **0**，不应恢复已结束队列。
英文论文、补充方法、三张图、核验参考文献、作者核对表和 PDF/Word 审阅版已完成。
当前是**探索性研究的作者审阅稿，尚未完成投稿前要求，本任务未代作者投稿**。

投稿工作标题：**Longitudinal Motor-Imagery EEG Decoding: Frozen Baselines,
Supervised Recalibration, and Task-Measurement Reliability**。
目标：**PLOS ONE / Research Article**，由作者确认。
历史项目方向 Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG
不代表已提出或验证有效的 task-aware 门控。

## 科学进度与证据

| 项目 | 实际完成情况 | 证据入口 |
| --- | --- | --- |
| 数据资格与划分 | NEMAR nm000177/v1.0.5；18 个发布身份、6 会话、360 EDF；7,156 完整窗口，44 partial 保留并按原规则排除 | [资格报告](KUMAR_MODEL_ELIGIBILITY_REPORT.md)、[冻结协议](KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md) |
| 三种 CPU 基线 | Frozen CSP/LDA、冻结 CSP 的 LDA 重校准、完整 CSP/LDA 重拟合，原结果保留 | [执行报告](BASELINE_EXECUTION_REPORT.md)、[结果表](CROSS_SESSION_RESULTS.md) |
| 54 个源 EEGNet fit | 18 人 × 3 固定种子；原 18 + 后续 36；累计 2,871 epochs / 8,613 optimizer steps；54 项已验收 | [接受报告](research_logs/kumar_remaining36_acceptance_20261015/run01/REPORT.md)、[accepted54](research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json) |
| CSP signed-score 可靠性 | 实际 run02 完成 240 个 SOURCE20 流水线、复用 6 个 SOURCE40 模型；仅开发 SOURCE TRAIN/support，query0；独立核验与 R2 备份完成 | [实际 run02](research_logs/kumar_csp_signed_score_execution_20261015/run02/REPORT.md) |
| 一次只读 query | 54 个已有 checkpoint；4,290 个 query 身份（源 360、目标 3,930）；不重训、不建 optimizer、不更新参数/BN/归一化；已单独验收 | [执行审计](research_logs/kumar_frozen_query_execution_audit_20261015/run01/REPORT.md)、[真实 ACK](research_logs/kumar_frozen_query_acceptance_20261015/run01/REPORT.md) |
| 汇总与论文图表 | 参与者为统计单位；保留全部种子、collapse、负结果及预算差异；用已保存结果整理，不重复推理 | [比较报告](research_logs/kumar_frozen_query_comparison_20261015/run01/REPORT.md)、[图及图注](manuscript/figures/kumar2024_20261015/CAPTIONS.md) |

源 accepted54 账本 SHA256：
`013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670`。
query 接受单独记录，不重复计入源训练账本。父侧 query ACK 核对完整回执、
清单/GET/closing 一致性、54 项身份及保存算术；父侧没有新发 R2 GET、第二 forward
或重新逐字节核全部 147 个原对象。原操作侧完整 GET 证据和父侧回执审阅分别保留。

## 论文可以支持的结论

固定剩余 12 人的目标会话 BA：

| 方法 | 平均 BA | 标签/信息预算 |
| --- | ---: | --- |
| Frozen CSP/LDA | 57.94% | 40 个源 TRAIN，无目标 support 更新 |
| Frozen CSP + LDA recalibration | 59.89% | 同一 40 个源 TRAIN + 当前会话 19/20 个 support |
| Full CSP/LDA refit | 65.36% | 与 LDA-only 相同的拟合身份；更新计算量不同 |
| Always-frozen EEGNet | 51.58% | 40 个源 TRAIN + 20 个有标签源 validation 选 epoch；无目标 support 更新 |

原 CPU 主要配对差为 **+7.42 个百分点**，95% 参与者 bootstrap 区间
**[+2.49, +12.48]**；9 人提高、3 人降低。LDA-only 较冻结为 +1.95 点，
区间 [-0.98, +5.09]，收益仍不确定。冻结 EEGNet 区间 49.08–54.51%，接近机会水平。
不同标签、验证与计算预算不能硬排架构优劣。

开发可靠性和预冻结描述性漂移关联不支持部署有效的新门控。
既往测试暴露使后续比较保持探索性；18 是发布身份数，不是本研究独立证明的生物学身份。
负结果、类别塌缩、QC 标记和元数据限制均保留。离线结果不证明人类技能保持、
学习因果效应或临床有效性。

## 论文文件和作者确认

| 材料 | 当前入口 |
| --- | --- |
| 完整审阅包 | [目录](manuscript/review_package_author_confirmed_20261015/README.md) |
| 英文主文 | [Markdown](manuscript/kumar_longitudinal_decoding_working_draft_20261015.md)、[PDF，12 页](manuscript/review_package_author_confirmed_20261015/manuscript.pdf)、[Word](manuscript/review_package_author_confirmed_20261015/manuscript.docx) |
| 补充方法 | [Markdown](manuscript/kumar_supplementary_methods_20261015.md)、[PDF，7 页](manuscript/review_package_author_confirmed_20261015/supplement.pdf)、[Word](manuscript/review_package_author_confirmed_20261015/supplement.docx) |
| 作者核对表 | [Markdown](manuscript/kumar_author_review_checklist_20261015.md)、[PDF，2 页](manuscript/review_package_author_confirmed_20261015/author_checklist.pdf) |
| 文献 | [10 项 BibTeX](manuscript/kumar_references_20261015.bib)、[核验范围及来源更正](manuscript/reference_map.md) |
| 作者逐项原始回复 | [8 项确认及解释边界](research_logs/kumar_author_confirmation_20261015/run01/author_confirmation.json) |

作者 **Ziyuan Zhu（朱子元）**，重庆医科大学人工智能医学学院；
通讯邮箱 `zzy2630816871@gmail.com`。作者确认独立作者及所询贡献角色、无专项资助、
无利益冲突、无机构/合作方公开限制、PLOS ONE 目标，无预印本/会议版本或同时在审。
ORCID `0009-0005-1153-4926` 姓名字段更正是作者报告，本任务未独立刷新其主页。
稿件如实列出 AI 辅助范围供作者审阅，不将 AI 列为作者或声称仅做语言润色。

**仍需完成的投稿前事项：**

1. 学校/机构对本次公开数据二次分析的实际结论。作者现答“尚无结论”，不能写成已批准、
   豁免或不需审查；源研究 UT Austin 2020-03-0073 不是本项目批准。
2. 原始知情同意表述的来源核对。保留文献/元数据实际访问范围，不冒称读过无法访问的完整原文。
3. 具体软件许可证、依赖权利核对和明确公开材料清单；“无限制”不自动生成 LICENSE。
4. PLOS ONE 当前格式、报告、数据/代码及 AI 声明检查，和作者对完整最终稿的批准。

这些事项不是新模型、重训、再次 query 或追选显著结果的理由。

## GitHub、私有 R2 与本次补归档

GitHub 保存代码、冻结协议/配置、接受账本、文本审计、论文/图及审阅版。
原始 EEG、epoch 数组、checkpoint 权重和原实验包保存在私有 R2；GitHub 保存对象清单、
长度、SHA256 与完整 GET 回执。私有备份不是公共下载端点或期刊数据发布。

| 最近论文备份 | 完整 GET/SHA256 | 回执 SHA256 |
| --- | --- | --- |
| 初版完整审阅包 | 131 对象 / 9,622,032 bytes，0 失败 | `240804c950587cfdabd408a2235b0971f88c8a6aa0c1e3df94928ddd9ce2ce37` |
| 作者确认新版 | 111 对象 / 9,233,753 bytes，0 失败 | `d4ecca0afafdfbc9405c14302fdea1e85500f73006564f99777bee9fa4f97d18` |

见[初版回执](research_logs/kumar_manuscript_completion_20261015/run01/r2_full_get_receipt.json)
和[新版回执](research_logs/kumar_author_confirmation_20261015/run01/r2_full_get_receipt.json)。
新版 1,559 项相关检查通过，759 份既有文件不变；主 Results、原表与科学配置未改。
PDF 已实际查看；Word 检查文本/XML/嵌入图，未声称在原生 Word 中渲染。

此前未跟踪的 CSP 准备材料：14 份 JSON 和 2 份旧脚本/测试本次原样归档进 Git，
6 份 epoch 数组只进入私有备份。见[本次同步清单、校验及回执](research_logs/kumar_project_status_sync_20261015/run01/README.md)。
它们是历史准备证据，不是新增已完成科学实验。
旧 `scripts/analyze_kumar_csp_reliability.py` 有已知 broad-except 存储失败边界缺陷，
不是可派发入口。实际已执行版本 `scripts/analyze_kumar_csp_signed_score_v1.py` 的 SHA256
为 `ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3`。
旧脚本合成测试通过不修复该缺陷或改变科学验收状态。

下一步只处理投稿前工作和保存结果的事实性写作。不恢复已完成 fit/query，
不改变冻结规则，不把历史命令当新授权。dot 仍是唯一 Pod 操作者；本次不操作 Pod。
论文1由原任务推进。NETBCI 与其他公开源保留独立历史账本，不拼入本论文扩大 n。
