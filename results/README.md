# 结果与本地输出

## 已保存的公开研究结果

- [原跨会话比较](../CROSS_SESSION_RESULTS.md)：CPU三基线与冻结EEGNet，含参与者单位、区间及预算说明。
- [论文及图表](../manuscript/README.md)：当前稿件、6张图和完整补充材料。
- [S1 Data与重放说明](../manuscript/plos_one_innovation_20261017/S1_Data_README.md)：保存预测、派生表格与代码；按包内说明重放。
- [审计记录索引](../research_logs/README.md)：执行、失败、接受和完整性证据。

## 学校HPC扩展输出

新实验输出在学校持久目录`/public/home/zhuziyuan/projects/paper2-recalibration-v2/outputs/kumar-dev-v2`，包含模型checkpoint、逐任务进度、评估分片和统计摘要。使用原路径恢复，不把运行层修复视为重新训练的理由。

[实时GitHub快照](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json)同步进度与已完成指标；完整checkpoint保存在学校目录。下载包中公开输入的范围与来源见[下载索引](../releases/README.md)，其来源条款保持不变。

本目录的普通运行输出默认由`.gitignore`排除；经过审计的派生材料按其既有路径保存。早期合成输出说明见[历史快照](../docs/archive/RESULTS_INDEX_20261025.md)。
