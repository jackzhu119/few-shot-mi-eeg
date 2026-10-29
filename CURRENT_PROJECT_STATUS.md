# 论文2当前状态

**2026-10-29：BMT三作者组件分析审阅稿已准备。** Ziyuan Zhu*, Sihao Liu, Haoyang Yu；三人共享重庆医科大学单位。新标题为 **Disentangling spatial-filter and classifier contributions to limited-label motor-imagery EEG recalibration**。[阅读PDF](manuscript/bmt_component_revision_20261029/BMT_Manuscript_Reading.pdf) · [Word与全部材料](manuscript/bmt_component_revision_20261029/README.md)。3图、2表，结构式摘要174词，完整正文约4,954词；新稿待全体作者最终审阅批准，尚未在ScholarOne提交。

2026-10-28双作者版及当时的两位作者批准保留于[历史目录](manuscript/bmt_submission_20261028/README.md)，不作为本次三作者导出稿的批准。作者已确认原PLOS稿件拒稿；下方按日期保留的旧记录仍表达当时的证据范围。

更新日期：2026-10-29（Asia/Shanghai）。本轮以保存预测、既有统计与文献核对重构论文，未新训练、重新运行query或操作学校作业。

## 当前入口

| 项目 | 状态与位置 |
| --- | --- |
| 当前目标期刊与新稿 | **Biomedical Engineering / Biomedizinische Technik**；[2026-10-29三作者审阅稿PDF](manuscript/bmt_component_revision_20261029/BMT_Manuscript_Reading.pdf) · [Word及完整材料](manuscript/bmt_component_revision_20261029/README.md) |
| 论文核心 | 同标签预算区分分类器、空间重学和support-only对齐：原Kumar Full−LDA +5.47pp；原Kumar探索性EA−Full +5.30pp [2.81,8.26]；BNCI次要EA−Full +5.65pp [3.15,8.70]，9/9正；BNCI唯一主要Full−LDA +0.19pp [−1.85,2.13] |
| 原始数据与分析层 | 两套原始采集：Kumar18人×6会话、BNCI9人×2天；六个分析层复用相应队列，不增加独立人数，见[数据版本清单](research_logs/paper2_structure_revision_20261029/DATA_VERSION_INVENTORY.md) |
| 保存预测复核 | [预算／phase复现与图表底表](research_logs/paper2_structure_revision_20261029/component_replay/README.md)：78,600+11,460行预测，仅重放保存结果，既有统计定义与区间保留 |
| V3实际结果 | 126/126完成；10,392份预测独立复算一致；[全分支科学分析](research_logs/paper2_v3_analysis_20261027/REPORT.md) |
| 原PLOS ONE稿件 | **Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**；[阅读PDF](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Reading.pdf) · [投稿Word](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Submission.docx) |
| 最新整理包 | [2026-10-19完整提交包与600dpi图件](manuscript/plos_one_submission_support_20261019/README.md) |
| 历史PLOS系统摘要与伦理声明 | [266词摘要](manuscript/plos_one_submission_support_20261019/Abstract_for_Submission_System.txt) · [现行伦理声明](manuscript/plos_one_innovation_20261017/Ethics_Statement_20261019.md)；按第32条第（一）项法规豁免依据，不包含学校确认表述 |
| 原研究结果 | 原CPU基线、54个源模型及一次冻结query评估已完成；[完整结果](CROSS_SESSION_RESULTS.md) |
| 新HPC扩展 | V2 24/24与V3 126/126均完成；不需为写稿重新启动训练 |
| 实际训练进度 | [实时STATUS.json](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/training_status/paper2-recalibration-v2/STATUS.json)，查看其中观察时间、step、checkpoint和完成数 |

## 原论文结果范围

18名参与者，原开发6人/主要比较12人；54个EEGNet源模型为18人×3种子，参与者是统计单位。

- 原主要比较：完整CSP/LDA重校准较冻结提高7.42个百分点，95%区间[2.49,12.48]。
- 同目标标签预算次要比较：完整重校准较仅LDA更新提高5.47个百分点，[2.17,8.91]。
- 冻结EEGNet在原12人目标会话BA为51.58%，[49.08,54.51]；其源query表现也偏弱。
- 个体下降、类别塌缩、预算差异和既往测试暴露保留在原稿、表格及[结果说明](CROSS_SESSION_RESULTS.md)。

当前三作者审阅稿、补充方法、3图/2表、底层派生数据和重放说明见[稿件索引](manuscript/README.md)；历史PLOS稿件的S1/S2及6张图仍保留原路径。本仓库保存作者提供过的稿件编号PONE-D-26-52050；本次文件整理未操作投稿系统，未推断编辑决定。

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

新V2架构与原54份权重分开保存。候选EA＋经验协方差更新规则仍待结果检验；V2历史队列未纳入BNCI/OpenBMI；2026-10-27已另行完成固定BNCI四臂复核，见本页新增状态。详见[实验设计](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/paper2-hpc-v2-20261023/docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md)。

V2完成结果见[2026-10-26独立分析](research_logs/paper2_hpc_v2_analysis_20261026/REPORT.md)。V3固定回传提交为`500831c086d9e1d1e8412cf8ebca5fb6a288db76`，包`83cbdfdcfa541b3ab3addfc3`，三分片合并40,194,093bytes。新几何候选相对tangent refit−2.33pp，KL核心对比近零；20标签BN模式对比为+1.50/+1.91pp，不外推为所有预算均有收益。全部结果保留于[新版分析](research_logs/paper2_v3_analysis_20261027/REPORT.md)。

2026-10-27原V3稿件修订仅使用保存结果；随后另行冻结并完成BNCI四臂外部实验，未重训旧模型或操作学校Slurm/Pod。10月27日稿依据[当时核查的官网要求](docs/bmt_journal_requirements_20261027.md)制作，结构式摘要≤200词，正文保守计数≤6000词，5图+3表。该段保留10月27日的原记录；10月28日作者已补充原PLOS拒稿信息，当前三作者版按页首入口审阅。

## 版本与追溯

- `main`：论文包、原研究结果与通用导航。
- [HPC研究分支](https://github.com/jackzhu119/few-shot-mi-eeg/tree/research/paper2-hpc-v2-20261023)：新实验源码、固定下载包及实时状态。
- [科研协议索引](docs/README.md) · [审计索引](research_logs/README.md) · [历史页面](docs/archive/README.md)。

稿件、协议、结果和验收原件保持原路径；本次仅整理文档入口，不训练、不再次query或改动学校作业。


## 2026-10-27新增外部固定验证（已完成）

- 9人BNCI2014-001、2天、每人20support/120whole-run query；执行前冻结457e7bd。
- Full−LDA-only +0.19pp [−1.85,2.13]，exact p=.96875；EA−Full +5.65pp [3.15,8.70]，9/9正、Holm p=.01172。
- 36份预测与180个run指标独立复算误差0；[报告](research_logs/paper2_external_validation_20261027/REPORT.md)及[公开JSON重放](research_logs/paper2_external_validation_20261027/REPRODUCE.md)。
- R2现有注入权限实际401，208计划对象均未上传/GET；失败回执保留，不影响GitHub派生结果和稿件交付。
