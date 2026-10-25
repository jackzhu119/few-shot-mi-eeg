# 论文2当前状态

更新日期：2026-10-25（Asia/Shanghai）。本页汇总现行入口；按日期保留的旧状态见[历史索引](docs/archive/README.md)。

## 当前入口

| 项目 | 状态与位置 |
| --- | --- |
| 论文 | **Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**；[阅读PDF](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Reading.pdf) · [投稿Word](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Submission.docx) |
| 最新整理包 | [2026-10-19完整提交包与600dpi图件](manuscript/plos_one_submission_support_20261019/README.md) |
| 系统摘要与伦理声明 | [266词摘要](manuscript/plos_one_submission_support_20261019/Abstract_for_Submission_System.txt) · [现行伦理声明](manuscript/plos_one_innovation_20261017/Ethics_Statement_20261019.md)；按第32条第（一）项法规豁免依据，不包含学校确认表述 |
| 原研究结果 | 原CPU基线、54个源模型及一次冻结query评估已完成；[完整结果](CROSS_SESSION_RESULTS.md) |
| 新HPC扩展 | 代码/固定输入已交付；[学校下载与启动入口](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md) |
| 实际训练进度 | [实时STATUS.json](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json)，查看其中观察时间、step、checkpoint和完成数 |

## 原论文结果范围

18名参与者，原开发6人/主要比较12人；54个EEGNet源模型为18人×3种子，参与者是统计单位。

- 原主要比较：完整CSP/LDA重校准较冻结提高7.42个百分点，95%区间[2.49,12.48]。
- 同目标标签预算次要比较：完整重校准较仅LDA更新提高5.47个百分点，[2.17,8.91]。
- 冻结EEGNet在原12人目标会话BA为51.58%，[49.08,54.51]；其源query表现也偏弱。
- 个体下降、类别塌缩、预算差异和既往测试暴露保留在原稿、表格及[结果说明](CROSS_SESSION_RESULTS.md)。

当前稿件、S1/S2、6张图、底层派生数据和重放说明见[稿件索引](manuscript/README.md)。本仓库保存作者提供过的稿件编号PONE-D-26-52050；本次文件整理未操作投稿系统，未推断编辑决定。

## 学校HPC扩展V2

| 设置 | 现行值 |
| --- | --- |
| 工作分支 | `research/paper2-hpc-v2-20261023` |
| 调度 | `hpc_gpu1`，单节点/单作业，2GPU并行，总24CPU/128G |
| 每个worker | 1GPU、计划12CPU/64G；沿用Torch4线程、BLAS1线程 |
| 首批任务 | 6名原开发参与者；6个经典任务＋18个新V2神经源模型任务 |
| 方法/预算 | 经典8臂、神经4臂；4/8/12/16/最多20个当前会话标签，5个目标会话 |
| 输入 | 固定125,283,270-byte输入包；完整SHA256、角色/whole-run身份在下载包中 |
| 下载与恢复 | GitHub官方API优先、续传和SHA；既有数据/准备缓存复用，两代checkpoint及评估分片恢复 |
| 自动同步 | 学校终端隐藏输入token、实际写入核验后，独立同步器约180秒上传进度和已完成指标 |

新V2架构与原54份权重分开保存。候选EA＋经验协方差更新规则仍待结果检验；BNCI/OpenBMI外部验证只在方案中，尚未纳入当前运行队列。详见[实验设计](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md)。

本次整理开始时读到的学校同步快照为2026-10-25T05:30:24Z（北京时间13:30:24），0/24完成且无任务进度记录。这只说明该时间的公开快照；当前状态请读取上方实时入口。代码交付、Slurm提交和模型实际更新分别记录。

## 版本与追溯

- `main`：论文包、原研究结果与通用导航。
- [HPC研究分支](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023)：新实验源码、固定下载包及实时状态。
- [科研协议索引](docs/README.md) · [审计索引](research_logs/README.md) · [历史页面](docs/archive/README.md)。

稿件、协议、结果和验收原件保持原路径；本次仅整理文档入口，不训练、不再次query或改动学校作业。
