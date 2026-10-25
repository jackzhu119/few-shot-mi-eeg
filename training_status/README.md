# 学校训练进度同步

本页提供入口，实际状态文件在[HPC研究分支](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2)。

- [STATUS.json](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json)：观察时间、完成数、任务phase/step/checkpoint和已完成指标。
- [AUTHORIZATION.json](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/AUTHORIZATION.json)：实际写权限探测的非秘密记录，不含token。
- [运行和恢复说明](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md)。

同步约每180秒进行。检查`observed_at`和任务step/checkpoint变化；“已提交”、Slurm RUNNING、授权成功或状态文件更新本身均不能单独证明模型正在更新。网络失败在独立同步器重试，训练继续使用学校持久存储。

本次主页整理不编辑实时JSON，也不启动、停止或迁移学校作业。
