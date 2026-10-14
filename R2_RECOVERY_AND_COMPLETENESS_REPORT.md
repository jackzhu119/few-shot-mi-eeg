# R2 recovery and completeness

历史闭合目录storage_catalog_final_20261012_run01.json保持原字节，包含12,909去重对象、17,401,550,465 bytes。本轮没有重新上传它们。当前快照目录research_logs/recovery_20261014/source_snapshot_run01/storage_catalog.json共有14,398对象、32,257,060,959bytes，其中4,121对象具有真实完整GET SHA256证据。相对于历史目录新增1,489对象、14,855,510,494bytes，包含此前两套2026来源和本轮实际科学结果，不能全当成本日新增下载。

2026-10-13实际HEAD重验13,565对象，长度和SHA元数据零失败；10月14日实际HeadBucket200及新增上传/完整GET成功，当前逐对象HEAD重验结果另在current_remote_run01。HEAD证明当前长度和所存SHA元数据，不能冒称重新读取全部32GB。只有回执明确full_get_sha256_verified才算完整内容读回。

新增Kumar科学结果固定前缀为few-shot-mi-eeg/experiments/kumar2024/nm000177/v1.0.5/cpu-baselines-20261013-run01：618对象、54,272,330bytes全部完整GET SHA256，零失败，涵盖无pickle模型、预测、固定特征、源拟合与状态审计。Wang/Liu10原始对象5,175,298,549bytes及23证据对象21,547,125bytes，全部完整GET闭合。MIND17-run源审计checkpoint205对象3,991,399bytes完整GET闭合；当前27/90raw和全部605小文件保存完成，每raw先官方MD5/数值审计、R2FULLGET，再释放任务缓存。

MIND还剩63规范原始文件未闭合。该缺口不影响已经完整的Kumar数据和基线，不能将MIND全库归档称完成。旧失败传输回执全部保留，当前所统计的完成阶段零失败；未开始、source429暂停和仍在执行的对象不混入完成目录。

root最终科学证据、报告和代码快照将以独立不可变版本前缀追加；它们与当前快照之后的新增raw由各自关闭回执统计。末次目录/收据不反复包含自身，最终closing metadata和Git回执单独记录。所有对象条件创建IfNoneMatch，已有同key须长度/SHA和完整GET匹配；冲突不覆盖。没有bucket、公开权限、代理或TLS变更，没有输出凭据。最终实际批次以research_logs/recovery_20261014的关闭回执及NEXT_STAGE_HANDOFF.md为准。

未购买或创建付费算力。R2存储和请求使用用户既有账号，实际账单未查询，不能宣称所有服务零费用。


2026-10-14关闭记录：当前实际HEAD重验14,399对象，零失败；完整科学证据payload 1,236对象/98,076,860bytes已全部完整GETSHA256，前缀few-shot-mi-eeg/research-evidence/task-aware-kumar/20261014/scientific-closeout-run01，回执scientific_evidence_R2_run01.json。659项全套测试加7项限流策略测试已通过；末次完整测试见pytest_final_run02.log。后续更新及本段不重复覆盖该已经关闭的证据payload，追加末次metadata与Git记录。


末次科学快照2026-10-14T02:56:31.965054+00:00：MIND 39/90原始run闭合，13发布编号三run完整；剩余51原始文件/18,150,553,600规范bytes。项目累计15,649去重对象/36,677,929,915bytes，5,372对象有完整GET。相对旧12909目录新增2,740对象，不等于全部本日新下载。源码检查点84f2a8871dd179c57039ddd7661fe013cd57e5d6已经远端核对，3个代码归档对象100,276,896bytes全GET，4446Gitblob/commit-header/bundle核对通过。完整666pytest通过，15弃用警告已记录；Ruff/smoke/MOABB通过。此快照之后的raw实时进度仍在状态文件，closing metadata批次不自递归归档。


2026-10-14末次目录：final_storage_catalog_run01/storage_catalog.json包含15,841去重对象/38,137,312,346 bytes，其中5,564对象有完整GET SHA256证据；目录截点MIND43/90。稍后运行实际已完成55/90，源站HTTP503导致暂停，06:34 UTC R2 HeadBucket200后按原缓存恢复（mind_restart_run02.json，日志mind_supervisor_run02.log）。不得将目录截点或后台状态视为90run全部闭合。科学代码检查点84f2a88已推送并R2全GET归档；后续Git提交仅保存账本与交接。
