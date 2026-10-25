# 实验入口

## 当前学校HPC扩展V2

实际执行代码位于[research/paper2-hpc-v2-20261023分支](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023/experiments/hpc_recalibration_v2)。

| 资料 | 入口 |
| --- | --- |
| 学校下载、更新、启动与恢复 | [固定下载入口](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md) |
| 精确输入、方法、checkpoint与输出 | [实验说明](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/experiments/hpc_recalibration_v2/README.md) |
| 方法依据与预定比较 | [科学设计](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md) |
| 最新软件验证与资源配置 | [单节点24CPU验证](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/research_logs/paper2_hpc_v2_20261023/hpc_gpu1_24cpu_20261024/REPORT.md) |

现行申请为`hpc_gpu1`、单节点/单作业、2GPU并行、总24CPU/128G。运行前在学校交互终端隐藏输入GitHub token；下载/授权核验后再提交或释放作业。已完成项跳过，中断阶段恢复；实际进度以step及checkpoint为准。

## 原论文与早期软件检查

[原冻结协议](../KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md)、[结果](../CROSS_SESSION_RESULTS.md)及[审计索引](../research_logs/README.md)对应已有研究。原54个模型及其结果保留。

`scripts/smoke_experiment.py`与`configs/smoke.json`是原项目合成软件检查，分数只用于验证软件流程。根目录旧环境与Phase0约定见[历史目录说明](../docs/archive/EXPERIMENT_INDEX_20261025.md)，不作为学校HPC启动前置步骤。
