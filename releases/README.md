# 固定下载与交付入口

当前HPC下载文件位于[research/paper2-hpc-v2-20261023分支](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023)。`main`中的本页提供导航。

| 用途 | 入口 |
| --- | --- |
| 学校终端直接下载、更新及断点继续 | [交付说明](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md) |
| 已安装环境更新到单节点2GPU/24CPU/128G | [固定一行更新命令](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/UPDATE_TO_24CPU.txt) |
| 输入分片、总长度与SHA256 | [输入manifest](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/input_download_manifest.json) |
| 原始数据作者与许可 | [数据署名](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/DATA_ATTRIBUTION.txt) |
| 论文提交文件与图件 | [稿件目录](../manuscript/README.md) |

入口会下载固定版本并校验SHA256，复用完整缓存或续传分片；无需经个人电脑中转。GitHub token在学校终端隐藏输入，不包含在公开命令、包或仓库中。

历史资源配置的命令保留原文件名和Git提交，当前操作采用上面的24CPU入口。GitHub Release页面是说明入口；下载器使用仓库中已验证的文件路径和版本。
