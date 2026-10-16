# 2026-10-16 审稿修订交付与同步收尾

新版论文内容已实际推送至 `main` 和 `research/learning-preserving-bci`：
[`f2901decfc39b2adecae13253ee4b1159a4f9a4b`](https://github.com/jackzhu119/few-shot-mi-eeg/commit/f2901decfc39b2adecae13253ee4b1159a4f9a4b)。
固定标签为 [`paper2-plos-source-20261016`](https://github.com/jackzhu119/few-shot-mi-eeg/tree/paper2-plos-source-20261016)。
本收尾提交只补同步证据，不移动标签，不改封存稿、旧结果、账本或许可。

## 审阅入口

- [完整文件索引](../manuscript/plos_one_submission_20261016/README.md)。
- [带图 PDF](../manuscript/plos_one_submission_20261016/manuscript_for_review.pdf) /
  [Word](../manuscript/plos_one_submission_20261016/manuscript_for_review.docx)：PDF 30 页。
- [无图投稿格式 PDF](../manuscript/plos_one_submission_20261016/manuscript_for_submission.pdf) /
  [Word](../manuscript/plos_one_submission_20261016/manuscript_for_submission.docx)。
- [逐条审稿回应](kumar_review_response_20261016.md)、[修订报告](kumar_submission_revision_report_20261016.md)。
- [69成员 S1 Data](../manuscript/plos_one_submission_20261016/S1_Data.zip)及
  [成员清单](../manuscript/plos_one_submission_20261016/S1_Data_manifest.json)。

新版数据 ZIP 为 1,423,505 bytes，SHA256：
`dccb1d88f4decae03794bc2fa81ead788cff87d2dd13b172f8b55d7e1e373416`。
38 个旧成员原路径逐字节保留，3 份旧文档原字节另存历史目录；旧 41 成员包不变。
新加入的是已保存的可靠性/drift 资料和审稿后统计输入，不是新模型或新 query 结果。

## 实际公开读回和私有备份

[GitHub 读回记录](../research_logs/kumar_review_revision_20261016/sync_run01/github_public_readback.json)
核对 main、研究分支及标签解析到相同内容提交，并对 10 份关键公开文件实际无认证 GET，
共 4,925,827 bytes，与本地完整 bytes/SHA256 全部相同。没有声称另对全部 283 文件逐一 HTTP GET。

| 私有 R2 批次 | 唯一对象 | bytes | 完整 GET/SHA256 失败 |
| --- | ---: | ---: | ---: |
| 稿件、代码、数据及私有原始核查证据 | 679 | 70,070,553 | 0 |
| 主回执、读回证据、Git增量包和离线审阅包等收尾资料 | 13 | 19,388,709 | 0 |
| 两个不同前缀的合计 | 692 | 89,459,262 | 0 |

主回执 579,221 UTF-8 bytes，完整 SHA256：
`7eab03bf7c6d21dc9ca60a8b878f2a74051ac95af32054255d145933ae4b3770`。
收尾回执 11,132 UTF-8 bytes，完整 SHA256：
`0bfdb0c6c4e67f6c295468aa2018ae4b923459f0f765b6679ba4bc9ff1655b37`。
[完整回执与独立核对](../research_logs/kumar_review_revision_20261016/sync_run01/README.md)
保留全部对象清单、长度与 hash。独立核对仅审阅已有回执、本地实际字节及 Git blob，未冒称第二轮远端 GET 或父侧 ACK。

主上传在内容提交前建立计划，原回执仍保留当时基线 `a78372d`；全部 283 个公开文件已另逐字节核对到
`f2901de` Git blob。没有改写旧回执把基线伪装成新稿提交。最后的收尾回执和 Git 元数据保存在 Git，
不作循环“回执备份自身”声明。R2 是私有保全，公开数据入口是 GitHub 与 S1 Data。

离线作者审阅 ZIP 共44成员、7,553,238 bytes，SHA256：
`86c817d598e6c2f44ddd7a88ddcb34665d97adc73175b7914cb9d20d52aaf430`。
该包是审阅资料选择，不冒充完整 Git clone；完整项目历史由固定公开版本提供。

## 核验结论与尚需本人完成的事实

原 Tables 1–4、816 项保护文件及旧包66个封存来源/产物不变。当前12份PDF/Word的135项结构检查、
91页联系页与关键细页检查、新统计24项合成测试均完成；Ruff、smoke、MOABB合成检查通过。
整仓实际结果仍为1,257通过、13失败、1跳过，历史host/claim/磁盘前提及子进程导入问题
[逐项保留](../research_logs/kumar_review_revision_20261016/run01/verification/historical_test_failures.md)，
未通过改门或删证据制造绿色结果。

主差仍为 +7.42pp [2.49,12.48]；审稿后 raw p=0.01953125、四项 Holm p=0.05859375，
保持探索性，不追认确认性结论。许可已按真实选择激活；不能替代本次二次分析的实际伦理依据，
也不能替代作者亲自核验及批准最终稿。[机构信息请求草稿](kumar_secondary_analysis_ethics_information_request_20261016.md)
尚未发送。没有新训练、query重跑、Pod操作、论文1操作、投稿或新DOI。
