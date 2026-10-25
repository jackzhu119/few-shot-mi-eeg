# Longitudinal Motor-Imagery EEG Decoding

公开多会话运动想象EEG的跨会话解码研究：比较冻结模型、分类器重校准与空间滤波器更新，并检验少量校准标签下的更新强度。

当前论文：**Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**。

## 从这里开始

| 目的 | 入口 |
| --- | --- |
| 阅读论文 | [带图PDF](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Reading.pdf) · [投稿Word](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Submission.docx) |
| 获取最新投稿材料 | [完整文件索引](manuscript/README.md) · [2026-10-19完整提交包](manuscript/plos_one_submission_support_20261019/PONE-D-26-52050_submission_20261019_run02.zip) · [600dpi图件](manuscript/plos_one_submission_support_20261019/Paper2_High_Resolution_Figures.zip) |
| 运行学校HPC扩展 | [下载、更新与断点续跑](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/releases/paper2-hpc-v2-20261023/README.md) · [实验设计](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md) |
| 查看进度 | [项目状态](CURRENT_PROJECT_STATUS.md) · [学校实时同步快照](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json) |
| 复现与查证 | [S1 Data及重放说明](manuscript/plos_one_innovation_20261017/S1_Data_README.md) · [原研究结果](CROSS_SESSION_RESULTS.md) · [协议索引](docs/README.md) · [审计记录](research_logs/README.md) |

## 已完成研究

Kumar2024 / NEMAR `nm000177` v1.0.5，18名参与者、每人6个会话；6人为原开发组，12人为原主要比较队列。原54个EEGNet源模型及一次冻结query评估已完成验收，54个模型对应18人×3个种子。统计单位为参与者。

| 原12人主要队列的比较 | 平均差或BA | 95%参与者bootstrap区间 |
| --- | ---: | ---: |
| 完整CSP/LDA重校准 − 冻结（原主要比较） | +7.42个百分点 | [2.49,12.48] |
| 完整重校准 − 仅LDA更新（同标签预算次要比较） | +5.47个百分点 | [2.17,8.91] |
| 冻结EEGNet目标会话BA | 51.58% | [49.08,54.51] |

[结果与预算说明](CROSS_SESSION_RESULTS.md)保留个体差异、负结果及既往测试暴露范围。论文研究离线解码；后续使用已暴露队列的分析按探索性报告。

## 当前学校HPC扩展

研究分支：[research/paper2-hpc-v2-20261023](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023)。

- 检验“当前校准样本波动驱动的源—目标协方差混合”，以EA完整更新为主要强对照。
- 首批仍是原6名开发参与者：6个经典方法任务＋18个新V2神经源模型任务；经典8臂、神经4臂，标签预算4/8/12/16/最多20，覆盖5个目标会话。
- `hpc_gpu1`：**单节点、一个作业、2GPU并行，总24CPU/128G**；每个worker计划12CPU/64G。
- 在学校终端隐藏输入GitHub token并核验写权限；下载支持续传和SHA256，训练/评估支持断点，约180秒同步进度及已完成指标。

新V2使用独立实验版本；原54模型和论文结果保留。训练是否推进以[实际进度记录](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json)、step及checkpoint为准。外部独立数据验证尚未纳入当前可执行队列。

## 文件导航

| 位置 | 内容 |
| --- | --- |
| [manuscript/](manuscript/README.md) | 当前论文、补充材料、图件、系统字段与历史稿件 |
| [docs/](docs/README.md) | 冻结协议、方法、数据审计、文献与历史页面 |
| [experiments/](experiments/README.md) | 当前学校HPC实验入口和旧实验范围 |
| [releases/](releases/README.md) | 固定下载包、输入manifest和更新入口 |
| [research_logs/](research_logs/README.md) | 原始执行、审计、验收、失败及复现记录 |
| [training_status/](training_status/README.md) | 学校进度同步说明和实时快照入口 |
| [src/](src/learning_preserving_bci/) · [scripts/](scripts/) · [tests/](tests/) | 原研究软件、分析/构建脚本及测试 |
| [configs/](configs/) · [environments/](environments/) | 原冻结配置及环境锁定文件 |
| [results/](results/README.md) | 本地输出位置与公开结果导航 |

`main`展示论文与通用导航；HPC扩展代码、下载包及实时进度在上述研究分支。学校HPC使用独立入口，不将根目录旧环境安装流程作为其启动条件。

## 数据、许可与历史

源数据：[NEMAR nm000177 v1.0.5](https://doi.org/10.82901/nemar.nm000177.v1.0.5)；原研究：[Kumar et al.,2024](https://doi.org/10.1093/pnasnexus/pgae076)。原始数据与第三方组件保留来源条款。原创代码和论文/派生成果采用限定MIT与CC BY4.0，具体范围见[LICENSING.md](LICENSING.md)和[LICENSE](LICENSE)。

[历史页面索引](docs/archive/README.md)保留旧主页、旧状态和当时的配置/声明；[本次整理说明](docs/repository_organization_20261025.md)记录整理范围。所有冻结实验、稿件包、结果和回执仍保留原路径。
