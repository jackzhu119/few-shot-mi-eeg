# Download recovery audit

固定快照：2026-10-14T01:57:48.369126+00:00。恢复现有科研分支；历史六库没有重复下载或上传。当前cloudspec94已观测ready/enforced，实际R2HeadBucket HTTP200。

| Source/version | Expected files | Local SHA verified | Missing/corrupt | Status |
| --- | ---: | ---: | ---: | --- |
| NETBCI2026 v1.0.0 | 3577 | 3577 | 0/0 | A: retain |
| Kumar2024 v1.0.5 | 2705 | 2705 | 0/0 | A: retain |
| PhysioNet EEGMMIDB 1.0.0 | 654 | 654 | 0/0 | A: retain |
| Leeuwis2021 v1.0.0 | 2095 | 2095 | 0/0 | A: retain |
| MILimbEEG v1.0.0 | 666 | 666 | 0/0 | A: retain |
| Liu2024 v1.0.3 | 556 | 556 | 0/0 | A: retain |
| Wang/Liu2026 Figshare v11 | 10 archive/root files, 536 EEG members | official ZIP MD5/member CRC and source audit passed | 0 | A: raw and audit R2 complete |
| MIND ScienceDB V4 EEG-only | 695, including90 signals | 605 small files +27 complete signals in R2 | 63 signals not closed | C:27 archived caches evicted; D:remaining fixed queue |

本日恢复后3个原始信号闭环，完整文件合计1,038,131,200 bytes；其中首个安全续传已有分片。后两个全新文件合计686,515,200 bytes（0.687GB），是可确定的净新增完整数据下限。未完整计量全部HTTP失败、探测和续传接收量，不把整个文件体积冒称净新增下载。

MIND剩余规范完整文件体积22,373,068,800 bytes（22.37GB）；这是整文件缺口，当前有效分片可减少待接收字节。分片真实接收量依据range_checkpoints.completed，不用稀疏文件stat大小。官方90-run清单保持不变，不补下载fNIRS、Han或未授权来源。

A=字节验证完成；B=本地完整等待R2；C=R2全GET闭环、工作缓存已按规则释放；D=固定清单未闭合或可安全续传；E=校验损坏；F=不明或范围外。当前六库A10253，B/C/E/F均0；MIND的27个C是明确缓存政策，不是数据遗失。未闭合D包含当前部分下载和未开始队列，不等于损坏。

10月13日暂停原因已记录为官方source HTTP429，range未写入不匹配body。10月14日保留并重验分片后，采用单source worker、限定次数及60秒429冷却恢复；未知ValueError、源hash冲突和R2冲突仍停止。控制器PID和启动代码SHA见mind_restart_run01.json，不修改代理、TLS、凭据或权限。

逐文件SHA、官方manifest/版本、R2key及源身份记录见DOWNLOAD_RECOVERY_RECEIPTS.json引用。原始六库已实核10253文件，Kumar2705文件和360信号通过新资格审查。PhysioNet旧失败.part、历史失败审计和原始代表文件保留；不属于当前固定缺口，不自动重试或删除。

来源原始入口仍按旧selection_manifest与MINDall_files_manifest.tsv冻结；不会重新搜索其他版本。Wang/Liu全部268run已审计，但存在21/22跨编号复制、sub02跨阶段复制及伪迹/point-marker限制，未取得模型资格。MIND未完成全90run审计，不计30完整训练主体。


末次科学快照2026-10-14T02:56:31.965054+00:00：MIND 39/90原始run闭合，13发布编号三run完整；剩余51原始文件/18,150,553,600规范bytes。项目累计15,649去重对象/36,677,929,915bytes，5,372对象有完整GET。相对旧12909目录新增2,740对象，不等于全部本日新下载。源码检查点84f2a8871dd179c57039ddd7661fe013cd57e5d6已经远端核对，3个代码归档对象100,276,896bytes全GET，4446Gitblob/commit-header/bundle核对通过。完整666pytest通过，15弃用警告已记录；Ruff/smoke/MOABB通过。此快照之后的raw实时进度仍在状态文件，closing metadata批次不自递归归档。


2026-10-14末次目录：final_storage_catalog_run01/storage_catalog.json包含15,841去重对象/38,137,312,346 bytes，其中5,564对象有完整GET SHA256证据；目录截点MIND43/90。稍后运行实际已完成55/90，源站HTTP503导致暂停，06:34 UTC R2 HeadBucket200后按原缓存恢复（mind_restart_run02.json，日志mind_supervisor_run02.log）。不得将目录截点或后台状态视为90run全部闭合。科学代码检查点84f2a88已推送并R2全GET归档；后续Git提交仅保存账本与交接。
