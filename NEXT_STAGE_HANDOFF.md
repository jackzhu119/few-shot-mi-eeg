# Current scientific handoff

继续/workspace/few-shot-mi-eeg，research/learning-preserving-bci，不重新初始化、不删历史结果。当前方向Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG；在线实验不是本论文依赖，不宣称技能保持。

已完成Kumar18发布编号/6会话/360EDF的真实资格、性能前冻结、7156完整窗口与44partial保留、三种CPUbaseline和独立324行/12870预测重放。固定12测试编号冻结BA57.94%，全CSP/LDA重校准65.36%，配对+7.42pp CI[2.49,12.48]，9提高3降低。所有结果及618对象R2全GET通过；不要重跑已完成模型。主状态是baseline真实完成，原创门控尚未实现，EEGNet仅软件验收/训练准备完成。

协方差形状和源任务轴漂移关联区间跨零，不能据此命名有效的新策略。下一步在6开发编号内验证support任务分离可靠性、匹配标签预算及嵌套分组验证；固定阈值以后才能评一次最终query。真实as-stored/CAR、QC、通道/数量功率诊断、support-only PCA距离及科学图均已计算，额外诊断标明post-freeze，不更改主要模型。

MIND仍按已授权695文件/90raw固定V4清单续传，快照27raw已完整存R2，实时进度可能更晚。新控制器scripts/supervise_mind_recovery.py识别本子进程新鲜的HTTP429结构证据，限定次数/60秒冷却；未知ValueError/hash或R2冲突不重试。实际启动信息在research_logs/recovery_20261014/mind_restart_run01.json。若进程已消失，先查看state/supervisor_status/日志和文件锁，再用现有命令恢复，不能重复启动控制器。

恢复命令（仅确认无live controller后）：

```bash
cd /workspace/few-shot-mi-eeg
PYTHONPATH=/tmp/codex-r2-connectivity-sdk MIND_SOURCE_RANGE_WORKERS=1 /workspace/.venvs/few-shot-mi-eeg/bin/python -u scripts/supervise_mind_recovery.py
```

/tmp SDK可能随环境启动消失，使用uv --target恢复boto3==1.43.111，保留代理/CA与注入变量，不输出值。重新诊断实际HeadBucket，不凭旧503或ready推断连通性。旧六库10253文件均本地SHA通过，不下载/重传旧17GB对象。新Wang/Liu24资源268run归档完成，但跨ID/阶段副本等限制使模型资格未通过；MINDmetadata不能代替90run实读。

本轮未新建付费GPU或CPU，实际既有服务账单未查。第一篇仓库只读。禁止自动扩大下载、采购算力、论文Release或投稿。Git与最终R2状态以本目录回执、科研commit和关闭metadata递送记录为准。


2026-10-14关闭记录：当前实际HEAD重验14,399对象，零失败；完整科学证据payload 1,236对象/98,076,860bytes已全部完整GETSHA256，前缀few-shot-mi-eeg/research-evidence/task-aware-kumar/20261014/scientific-closeout-run01，回执scientific_evidence_R2_run01.json。659项全套测试加7项限流策略测试已通过；末次完整测试见pytest_final_run02.log。后续更新及本段不重复覆盖该已经关闭的证据payload，追加末次metadata与Git记录。


末次科学快照2026-10-14T02:56:31.965054+00:00：MIND 39/90原始run闭合，13发布编号三run完整；剩余51原始文件/18,150,553,600规范bytes。项目累计15,649去重对象/36,677,929,915bytes，5,372对象有完整GET。相对旧12909目录新增2,740对象，不等于全部本日新下载。源码检查点84f2a8871dd179c57039ddd7661fe013cd57e5d6已经远端核对，3个代码归档对象100,276,896bytes全GET，4446Gitblob/commit-header/bundle核对通过。完整666pytest通过，15弃用警告已记录；Ruff/smoke/MOABB通过。此快照之后的raw实时进度仍在状态文件，closing metadata批次不自递归归档。


2026-10-14末次目录：final_storage_catalog_run01/storage_catalog.json包含15,841去重对象/38,137,312,346 bytes，其中5,564对象有完整GET SHA256证据；目录截点MIND43/90。稍后运行实际已完成55/90，源站HTTP503导致暂停，06:34 UTC R2 HeadBucket200后按原缓存恢复（mind_restart_run02.json，日志mind_supervisor_run02.log）。不得将目录截点或后台状态视为90run全部闭合。科学代码检查点84f2a88已推送并R2全GET归档；后续Git提交仅保存账本与交接。
