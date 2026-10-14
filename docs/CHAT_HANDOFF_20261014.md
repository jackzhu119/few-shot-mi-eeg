# 当前恢复入口

在现有`/workspace/few-shot-mi-eeg`、`research/learning-preserving-bci`继续，不初始化。
完整科研状态和下一步命令以根目录[NEXT_STAGE_HANDOFF.md](../NEXT_STAGE_HANDOFF.md)为准。
2026-10-12交接和NETBCI历史结果保持原样；当前论文按用户正式指示转为
**Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG**。

Kumar18人真实三基线、性能前冻结和独立预测重放已完成，充分EEGNet训练及原创门控
尚Pending。六库没有重复下载或上传；Wang/Liu2026归档/源审计完整但建模资格未通过，
MIND仅既有V4授权范围继续源HTTP429后安全续传。不能把全部365计划编号计为已训练人数。

新增对象与真实HEAD/GET范围见[R2报告](../R2_RECOVERY_AND_COMPLETENESS_REPORT.md)，
未完成文件与范围见[下载审计](../DOWNLOAD_RECOVERY_AUDIT.md)；科学模型与结论见
[基线执行](../BASELINE_EXECUTION_REPORT.md)、[跨会话结果](../CROSS_SESSION_RESULTS.md)。
最新Git/R2源代码检查点及末次关闭回执见`research_logs/recovery_20261014`。


低维证据R2已关闭：294对象/18,483,470 bytes全部GET SHA256；累计目录lowdim_cumulative_catalog_run01共16,407去重keys/45,047,516,373 bytes，其中6,130对象有完整GET。目录native闭合61run、原始源文件667/695（采样阶段不同），稍后live闭合62/90；MIND未全量完成。目录不自递归计入后续closing账本。下载沿用PID5558/5563，若已消失先核实failure/checkpoint/lock再恢复，勿重复启动。独立数值审核最大差1.28e-13，小于1e-9容差；720预测及BA逐值相同。
