# 研究记录与审计导航

[仓库主页](../README.md) · [当前状态](../CURRENT_PROJECT_STATUS.md) · [文档](../docs/README.md) · [稿件](../manuscript/README.md)

本目录保存真实执行、独立复核、备份与故障记录。按研究阶段查找；`run01/run02`、失败、partial和旧回执保留原路径。不同日期的“完成”应结合其研究范围与回执阅读。

## 原论文：源模型、冻结评估与结果

| 内容 | 入口 |
| --- | --- |
| 54项源模型连续验收账本 | [accepted_jobs_all54.json](kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json) |
| 最后36项接受及旧18项保留范围 | [验收报告](kumar_remaining36_acceptance_20261015/run01/REPORT.md) |
| 54项保存训练结果汇总 | [source-only汇总目录](kumar_all54_source_aggregation_20261015/run01/) |
| 一次冻结query评估的真实接受范围 | [query接受报告](kumar_frozen_query_acceptance_20261015/run01/REPORT.md) |
| 同query、标签预算与方法比较 | [比较报告](kumar_frozen_query_comparison_20261015/run01/REPORT.md) |
| 论文端点与区间 | [CROSS_SESSION_RESULTS](../CROSS_SESSION_RESULTS.md) · [冻结协议](../KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md) |

54个模型对应18名参与者的三个种子。原CPU主要比较与次要比较层级、负结果、类别塌缩和既往测试暴露标记随结果保留。

## 稿件修订与投稿文件核查

- [2026-10-19投稿支持核查](kumar_submission_support_20261019/run01/README.md)：系统PDF与原始高清图件、摘要及附件的实际核验范围。
- [定向修改核查目录](kumar_targeted_checks_20261019/) · [创新分析与导出记录](kumar_plos_innovation_20261017/)。
- [现行稿件与完整提交包](../manuscript/README.md)：对应正文、S1/S2、数据包、checklist与图表。
- [早期稿件审阅修订记录](kumar_review_revision_20261016/)：按当时版本保存。

## 来源、事件与早期队列审计

- [Kumar事件映射记录](kumar_component_followup_20261016/event_mapping/)：事件边界、阶段标注和原失败/恢复证据。
- [原开发队列](kumar_development_queue_20261014/) · [剩余36项审计](kumar_remaining36_audit_20261015/)。
- [NETBCI十九发布身份记录](netbci_cohort_all19_20261010/)：来源身份、重复录制与独立性问题见对应报告，不能与Kumar直接合并样本量。
- [公开数据扩容审计](public_data_expansion_20261010/) · [R2恢复总览](../R2_RECOVERY_AND_COMPLETENESS_REPORT.md)。

## 学校HPC V2：研究分支中的新增记录

- [V2交付与验证目录](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023/research_logs/paper2_hpc_v2_20261023)。
- [单节点2GPU/24CPU/128G入口核验](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/research_logs/paper2_hpc_v2_20261023/hpc_gpu1_24cpu_20261024/REPORT.md)。
- [实时进度及已完成指标](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json) · [下载与恢复说明](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md)。

V2当前首批为6名开发参与者、18个新源模型和6个经典任务；软件测试、调度状态和模型实际step分别记录。新方法收益及外部验证只能按实际结果报告。旧54模型与新V2训练有各自身份和结果目录。

## 历史材料

[历史主页与状态索引](../docs/archive/README.md)保留时间线。旧Pod授权、过期交接、早期伦理措辞、当时的R2状态和失败原因均按原日期阅读，不作为新的运行指令。目录整理只增加导航，不移动或改写封存数据和回执。
