# 文档导航

[仓库主页](../README.md) · [当前状态](../CURRENT_PROJECT_STATUS.md) · [稿件](../manuscript/README.md) · [研究记录](../research_logs/README.md)

本页按用途索引现有材料。日期较早的交接、伦理描述和运行命令保留其历史范围；当前稿件与学校运行入口见下表。

## 当前稿件与投稿资料

| 内容 | 入口 |
| --- | --- |
| 最新完整提交包、高清图件与系统摘要 | [2026-10-19投稿辅助文件](../manuscript/plos_one_submission_support_20261019/README.md) |
| 主稿、补充材料及图表 | [当前稿件索引](../manuscript/plos_one_innovation_20261017/README.md) |
| 现行伦理声明 | [2026-10-19声明](../manuscript/plos_one_innovation_20261017/Ethics_Statement_20261019.md) |
| 最近局部修订与数值核查 | [10月19日修订](kumar_limited_revision_20261019.md) · [定向核查](kumar_targeted_checks_20261019_run02.md) |
| 许可及第三方材料边界 | [限定许可范围](../LICENSING.md) |

## 原论文：设计、结果与复现

- [冻结实验协议](../KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md)：原数据划分、预算与比较。
- [跨会话结果](../CROSS_SESSION_RESULTS.md)：CPU基线、54个源模型及一次冻结query评估。
- [数据划分审计](../KUMAR_DATA_SPLIT_AUDIT.md) · [模型资格](../KUMAR_MODEL_ELIGIBILITY_REPORT.md) · [CPU执行报告](../BASELINE_EXECUTION_REPORT.md)。
- [冻结checkpoint评估协议](kumar_frozen_checkpoint_query_protocol_20261015.md) · [组件分析协议](kumar_component_exploratory_protocol_20261016.md)。
- [S2复现说明](../manuscript/plos_one_innovation_20261017/S2_Reproducibility.pdf)与[S1 Data](../manuscript/plos_one_innovation_20261017/S1_Data.zip)提供稿件对应的复现材料。

## 学校HPC扩展：当前研究分支

这些链接明确指向 `research/paper2-hpc-v2-20261023`；原论文结果与新V2实验分别保存。

- [下载、手动GitHub授权、单作业启动与恢复](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md)。
- [V2方法、数据范围与文献依据](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md)。
- [代码与实验说明](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023/experiments/hpc_recalibration_v2) · [进度与已完成指标](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json)。

当前申请为 `hpc_gpu1` 单节点、单作业、2GPU、总24CPU/128G。代码验收、排队状态与实际模型进度分别记录；资源调整不生成新的科学结果。

## 数据来源与历史审计

- [Kumar2024源数据审计](kumar2024_ingestion_audit_20261011.md) · [公开纵向数据审计](public_longitudinal_dataset_audit_20261010.md)。
- [NETBCI十九个发布身份结果](netbci_all19_results_20261011.md) · [方法复核](netbci_all19_methods_review_20261011.md)：保留发布身份重复与独立性问题。
- [下载恢复审计](../DOWNLOAD_RECOVERY_AUDIT.md) · [R2恢复与完整性记录](../R2_RECOVERY_AND_COMPLETENESS_REPORT.md)。

## 历史交接与版本

[历史主页与状态索引](archive/README.md)收录原时间线。根目录的[NEXT_STAGE_HANDOFF](../NEXT_STAGE_HANDOFF.md)、[GPU服务器交接](../GPU_SERVER_HANDOFF_20261014.md)及本目录 `CHAT_HANDOFF_*.md` 是带日期的交接记录。旧Pod命令、旧资源配置、旧伦理措辞和当时的待办状态不作为当前执行指令。
