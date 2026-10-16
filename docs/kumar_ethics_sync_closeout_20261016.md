# 伦理版实际同步收尾（2026-10-16 UTC）

伦理修订内容已固定并实际推送 main、research/learning-preserving-bci：
[`d03b5a35eed3e303d224f41870bc62b0a926c88d`](https://github.com/jackzhu119/few-shot-mi-eeg/commit/d03b5a35eed3e303d224f41870bc62b0a926c88d)。
固定tag `paper2-plos-ethics-20261016` 真实指向该提交；旧科学tag及所有封存材料不变。

[完整新伦理审阅包](../manuscript/plos_one_submission_ethics_20261016/README.md)已导出12份PDF/Word。
1005项封存/元数据保留检查通过；独立查看96页PDF联系页及20个关键页、135结构及24科学内容/引用检查通过。
主稿摘要和5结果表原样；S1 Data及4图原字节复用。未渲染原生Word，实际字体替代限制保留，未投稿。

Git首次push/部分raw和Contents请求真实503；之后正常atomic push成功，并实际从官方API核对main/研究分支/tag。
5个关键公开文件（review PDF、Word、主Markdown、release manifest、作者陈述JSON）完整字节最终均已读回一致，
使用的具体通路和先前失败分开保留，未把binary空content或blob metadata当完整下载。

私有R2最终324个唯一对象共34,005,655 bytes均完整GET/SHA通过。首轮263通过/61失败；
显式只重传实际失败61对象的第二份回执全部通过，原失败不抹去。综合回执逐对象指向真正GET证明，
不是声称同一轮重新GET全部对象。完整综合回执SHA256为
`ea82543e5d3c836fa537ae1d8b9ab1322b270936b3e07b7183367759c0e1bc42`。

[真实收尾核验](../research_logs/kumar_ethics_statement_revision_20261016/sync_run01/final_sync_verification.json)、
[首轮R2原回执](../research_logs/kumar_ethics_statement_revision_20261016/sync_run01/r2_full_get_receipt.json)、
[第二轮61对象原回执](../research_logs/kumar_ethics_statement_revision_20261016/sync_run01/r2_failed_objects_retry01.json)、
[综合完整GET证明](../research_logs/kumar_ethics_statement_revision_20261016/sync_run01/r2_combined_full_get_verification.json)
列明范围。324对象包含新公开稿件/审计和私有法规取文/原始作者请求/版面检查证据，没有复制凭据或上传EEG/权重到Git。
后续同步元数据另立closing对象，不能追认这些新回执已包含在它们自己证明的324对象中。

伦理含义是作者报告的机构免审确认，学校按已确认作者单位重庆医科大学理解，科研处为描述性英译；
无编号，不编造新IRB批准、事前批准、新知情同意waiver或已认证机构原件。原采集批准与本次免审分别陈述。
本轮只作行政修订；新用户请求的CPU研究补强在独立方案/版本执行，不改本伦理封存字节。
