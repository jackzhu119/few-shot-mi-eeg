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


2026-10-14开发support可靠性已计算：30会话中12个split-half任务方向cosine为负，21个源/support方向条件bootstrap区间跨零。无query参与、无最终编号打开、无decoder拟合/阈值搜索。完整结果research_logs/kumar_cross_session_20261012/support_reliability_dev_run01_20261014/REPORT.md；暂不实现原创门控，下一步先冻结源TRAIN内低维测量及run分组负对照。

开发可靠性及MIND58run原生审计追加R2已关闭：240对象/6,818,801 bytes，全部GET SHA256通过、零失败，回执support_reliability_R2_run01.json。668项测试通过，Ruff、smoke、MOABB合成验收通过。


2026-10-14低维任务信息诊断真实完成并独立重放通过：6固定开发编号，三个固定候选（44维功率、PCA4、C3/Cz/C4六维），36源run probe、90support行，零query输入。源BA均值51.67/50.00/54.17%，编号级区间均含50%；分半cosine均值区间均含0。不选候选、不搜索门控阈值、不改变已完成baseline；不能推断不存在EEG任务信息。下一步另冻结源TRAIN监督CSP4空间或源判别分数的run分组可靠性，而不回看query。679测试和Ruff/smoke/MOABB通过。结果、冻结代码及独立NumPy重放见research_logs/kumar_cross_session_20261012/lowdim_reliability_dev_run01_20261014及lowdim_independent_numeric_review_run01_20261014。


低维证据R2已关闭：294对象/18,483,470 bytes全部GET SHA256；累计目录lowdim_cumulative_catalog_run01共16,407去重keys/45,047,516,373 bytes，其中6,130对象有完整GET。目录native闭合61run、原始源文件667/695（采样阶段不同），稍后live闭合62/90；MIND未全量完成。目录不自递归计入后续closing账本。下载沿用PID5558/5563，若已消失先核实failure/checkpoint/lock再恢复，勿重复启动。独立数值审核最大差1.28e-13，小于1e-9容差；720预测及BA逐值相同。

2026-10-14新云端接续：已从67f89ee恢复，监督CSP开发可靠性实际完成：42 EDF完整GET SHA256，836允许窗口（240 source TRAIN/596 support），零query/最终编号加载。source整run留出BA62.92%，六发布编号bootstrap95%区间[52.92,72.08]%；support分半cosine均值0.298，区间[0.049,0.551]，30会话中8负值。不是门控收益证据，尚未实现或调阈值。首次汇总字符串/整数key不匹配已只重算聚合并保留原件，未重跑fit；以research_logs/gpu_preparation_20261014/supervised_csp_run01/summary_corrected.json为准。NumPy逐fold预测重放通过。MIND实时R2列举72个原始EEG对象，只是存在/长度，不宣称72闭合。GPU依赖独立锁、CUDA设备支持、source-only单fit入口、短期逐对象签名传输及完整GET备份准备完成；682测试通过、1实际CUDA测试本机跳过，Ruff/smoke/MOABB通过。没有启动外部GPU。父对话统一调度现有A4500，30GB容器盘非持久，完整命令/空间/安全传输/失败恢复见GPU_SERVER_HANDOFF_20261014.md。现有R2运行环境注入授权HEAD/GET成功，禁止复制密钥到RunPod；短期签名备份用合成对象实测成功。完整54fit和query正式冻结仍待GPU/数据交付验收，不手改历史freeze开关。

运行元数据修订（监督CSP结果不变）：GPU开发config仅budget段更新为初次sub-1/seed20261012单source-only fit，上限100epoch/300步；总体18编号×3seeds=54fit/16200步另存overall_frozen_plan，所有非budget字段逐值完全相同。RTX A4500及$0.25/h compute、$0.004/h容器存储标明父对话平台实测来源，不冒称本agent已在远端验收；服务器论文2安装/真实GPU训练未开始，实际账单和停机未知。新config SHA256为14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d。SSH/SFTP各一次Connection refused，失败证据保留在research_logs/gpu_runtime_metadata_20261014/ssh_failure.json；未重复连接，父对话核查端口/sshd。软件仅验证配置契约、科学字段不变及正式训练门仍关闭，未重复模型拟合；未删除金额硬限额（原本不存在）。下一次运行固定本修订提交及新配置哈希，不能混用旧检查点配置身份。
