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
