# MILimbEEG 与 Liu2024：公开外部域资源接入

日期：2026-10-11（Asia/Shanghai）。两库沿用现有云端环境与科研分支，固定最新官方
NEMAR derivative；不改变已经完成的 NETBCI 结果。新增资源仍未选择训练分区、窗口、
QC 或拟合模型，不能把这些资源的发布身份直接加到健康纵向学习样本量。

| 资源 | 固定版本与许可 | 必要子集 | 实际状态 |
| --- | --- | --- | --- |
| [MILimbEEG](https://doi.org/10.1016/j.dib.2023.109540) | [nm000328 v1.0.0](https://data.nemar.org/nm000328/v1.0.0/), CC BY 4.0 | 666 文件、62,287,177 bytes；60 EDF 占 60,464,776 bytes | 官方字节校验、全信号/源事件审计及独立复核通过；必要原始范围 R2 完整保存 |
| [Liu2024](https://doi.org/10.1038/s41597-023-02787-8) | [nm000158 v1.0.3](https://data.nemar.org/nm000158/v1.0.3/), CC BY 4.0 | 556 文件、697,479,742 bytes；50 BDF 占 696,884,480 bytes | 官方字节校验、50 信号完整普查与独立复核闭合；单位、复制及重叠问题保留，科学验收和模型就绪均为 false；必要原始范围 R2 完整保存 |

2026-10-11 14:47 刷新官方 `metadata.json`，两库的 license 和 `latest_snapshot`
与固定计划一致。完整官方 manifest 已保存，选择清单仅包含根元数据、必要 subject 文件
及原始来源 provenance，排除全仓储重复原始信号。每库的计划、SHA256、时间戳下载收据
和代表检查保存于
[MILimb 接入记录](../research_logs/public_data_expansion_20261010/milimbeeg_ingestion/)
及 [Liu 接入记录](../research_logs/public_data_expansion_20261010/liu2024_ingestion/)。
传输前检查磁盘预算；四个 HTTP workers、有界三次尝试，继承原代理与 TLS。
没有改动通用下载器，也没有覆盖旧结果、收据或原始文件。

## MILimbEEG 实际源验收

这是 **60 个发布身份、单次访问、混合人群**，不是 60 名健康训练者或 60 名患者。
源论文描述包括健康参与者、截肢、脑积水及 post-COVID 个案，当前 derivative
`participants.tsv` 的所有行复制相同整库 group 描述及 age=36.0，不能建立逐人的
病种、健康/临床分组、年龄或严重度协变量。实际字节有正常 tab/newline；早期元数据
快照中的字面转义不是本次实际下载格式。

原始研究包含 motor execution 与 imagery，当前选择的是 imagery derivative。
实读为 **16 EEG、125 Hz、物理 µV、MNE 数值 V**，每位发布身份只有 `ses-0/run-0`。
EDF 是单独 4 秒段的拼接：有 `EDGE boundary`，不能按连续自然录制进行跨段滤波或
把 sidecar 的 `RecordingType=continuous` 当成原始采集连续性证明。没有新的运动执行
信号、在线反馈或学习/保持测试。

60/60 EDF 官方校验、通道顺序、采样率、单位、annotation 与 TSV 逐行时间/标签、
源 sample 边界及所有连续样本有限值审计通过。共 **7,318 条源行**，其中
**3,659 条零时长 EDGE boundary、3,659 条正时长 3.992 秒任务事件**；boundary
不是训练 trial。任务标签为 `clh=299`，`crh/dlf/drf/plf/prf` 各 300，`rest=1,860`。
59 文件有 122 条源行，`sub-22` 有 120 行（`clh=4`，boundary=60）；差异原样保留，
不补齐预期 trial。全库未发布 `beo` 事件，不能由首次 4 秒位置补造标签。

实际 source value 为 `EDGE boundary=1, clh=2, crh=3, dlf=4, drf=5, plf=6, prf=7, rest=8`；
`drf/plf` 的数字与 README 示例不同。审计使用原 TSV 的 label/value 与 native annotation
对应，保留任务缩写，不凭示例整数重标生物任务；`drf/plf` 的生物任务含义尚不能用于统一任务映射。原始 provenance 提供 CSV 文件名和
hash，但没有当前 EDF 每个 event 与原 CSV 的逐行转换对应，本阶段仍不宣布该对应已验证。

完整信号数值 SHA256 和中央 4 KiB 指纹在本库均无相同 run 组；这个结果只排除所检查的
相同信号，不能证明跨库生物学身份独立。数值扫描按所有通道、little-endian float64、
16,384-sample 逐块 C-order 和 V 单位记录，不一次装载全部参与者。

实际下载收据
[download_receipt_20261011T065058411343Z.json](../research_logs/public_data_expansion_20261010/milimbeeg_ingestion/downloads/download_receipt_20261011T065058411343Z.json)，
SHA256 `4c0033ac8e0207076feff6927fff90179dec175c4dab39639b453ad201969cbb`；
成功完整源审计
[aggregate.json](../research_logs/public_data_expansion_20261010/milimbeeg_ingestion/signal_audit_run01/aggregate.json)，
SHA256 `ba50876f0099ce21e3d97573bfb8340f2f0af5e8581c66a03524865eecf97067`。
独立复核再次计算全部 666 文件官方校验，逐行确认全部 7,318 TSV 源行、计数和重复组，
重新实读按文件名首末两个 EDF，完整数值和中央指纹 hash 精确相同；见
[独立交叉核对](../research_logs/public_data_expansion_20261010/milimbeeg_ingestion/independent_source_crosscheck.json)。

## Liu2024 已闭合来源普查与科学问题

这是 **50 个急性卒中发布身份、单次访问**，原研究 1–30 天 post-stroke，非健康
NETBCI 的纵向练习人群。全部 556 必要文件现已通过官方校验，所有 50 事件 TSV
共 **2,000 源事件、左右手各 1,000、duration=4 秒**；每文件左右手各 20，标签全部
按时间交替。视频/音频提示、时间顺序、卒中侧与运动状态可能混杂，不能把离线分类解释
成独立神经控制、治疗效果或学习保持。

全部 BDF 实读及 native header 为 **29 EEG、500 Hz、物理 µV、0 EOG**，MNE 数值为 V；
全部 50 个 channel TSV 声明 V，形成全库 native/sidecar 单位冲突。没有手动缩放或修复，
模型使用前必须独立核实转换单位。原研究描述的 29 EEG+2 EOG 另行记录，当前 derivative
实际没有 31 个通道。数据已做 baseline
mean removal 与 0.5–40 Hz FIR，不能标成未处理原始 EEG。实际 participants 表正常
tab/newline，但全部 age=71，不能用来代替原论文的个体年龄或个体临床测量。

早期代表 `sub-1` BDF 的官方固定重定向三次均返回 HTTP 503、零信号 bytes。
对 `sub-1/sub-10` 的官方版本路径及 manifest 明确声明的 S3 对象做有界 1 KiB
Range 诊断，均返回 `upstream connect error ... Invalid argument ...
envoy://cloudflare_https_tunnel/`，是当前访问连接故障；没有归因于许可或源数据损坏，
没有绕过代理/TLS、降版本、下载其它未经校验来源或继续请求全部 50 文件。
[失败下载收据](../research_logs/public_data_expansion_20261010/liu2024_ingestion/representative_signal_download.json)、
[失败审计](../research_logs/public_data_expansion_20261010/liu2024_ingestion/representative_signal_audit/aggregate.json)
及 [HTTP 诊断](../research_logs/public_data_expansion_20261010/liu2024_ingestion/representative_http_diagnostic.json)
保留；该失败审计是历史文件缺失状态，没有源信号科学验收结论。

2026-10-11 官方固定路径恢复后，新完整下载收据
[download_receipt_20261011T125743501340Z.json](../research_logs/public_data_expansion_20261010/liu2024_ingestion/downloads/download_receipt_20261011T125743501340Z.json)
复核已有文件并下载余下 49 BDF；全部 556 文件、697,479,742 bytes 匹配官方长度及 checksum，
收据 SHA256 `21af6a1161c21aaa6a33ee7eca9c502f5c46389324235b1ca52beb7c7f4b58a3`。
恢复后的严格审计曾因单位冲突与原始重叠未闭合，原失败输出仍保留。有效全库收据为
[source_integrity_census_run03/aggregate.json](../research_logs/public_data_expansion_20261010/liu2024_ingestion/source_integrity_census_run03/aggregate.json)，
SHA256 `f92f90e260208356ea9ed186c2715a8b09d90ace97c98186cd4e90527340d4b2`。
它记录 `source_inspection_complete=true`、`source_bytes_complete=true`，
**`source_acceptance_complete=false`、`model_training_ready=false`**。
其中 `passed_signal_files=50` 只表示完整实读和普查成功，不表示 50 个身份均可靠或模型可用。
全部 50 信号逐块读取所有 29 通道、连续样本有限；每文件 160,000 samples / 320 秒。

全部 2,000 原始四秒任务行、native annotation 与源标签均保留。四条正时长重叠为：

| 源身份 | TSV 行（从 1 起） | 与前一任务重叠 samples / seconds |
| --- | ---: | ---: |
| sub-20 | 15 | 1,998 / 3.996 |
| sub-20 | 16 | 90 / 0.180 |
| sub-43 | 27 | 1,004 / 2.008 |
| sub-43 | 29 | 1,002 / 2.004 |

`sub-4/sub-5` 的全部 29 通道连续数值完全相同；40 个跨身份 source-task 精确复制组
均来自这一对身份，包括左右手各 20 组。不同身份的发布标签不能自动作为独立样本。
`sub-47/sub-49` 共享中央两通道 256 samples 的 4 KiB 指纹，但整信号 hash 不同；
该指纹是共享区域候选证据，当前闭合 JSON 没有这两人的完整 source-task 复制组。
不得把中央指纹相同等同于整信号复制或独立生物身份判定，也不得据此宣布 46/44 个模型合格身份。

新增[独立复核收据](../research_logs/public_data_expansion_20261010/liu2024_ingestion/independent_review_census_run01/independent_source_crosscheck.json)
SHA256 `a56f8d290dc5ebd6ef9e8e1aa5d7cb4fc27bc911031cdc30ab51452e6c94cb8e`。
[独立执行源 v4](../research_logs/public_data_expansion_20261010/liu2024_ingestion/independent_source_review_v4.py)
不导入生产辅助函数：重算全部 556 文件官方 checksum、50 native headers 和全部 2,000 TSV 源行，
独立重组全部整信号/任务复制组与 overlap，并完整逐块复读 `sub-1/50/4/5/20/43/47/49`
八个信号，核对全数值、每通道、中央指纹及各源任务 hash。v3 源文件保留，v4 更正复读范围文字。
独立复核通过是普查一致性证据；单位、重叠、复制及模型门槛仍未解除。

## 重放与后续门槛

专属 [审计器](../scripts/audit_milimb_liu_subset.py) 只接受以上两个固定版本，不拟合模型。
16 项针对性 tests 验证 source identity、unknown label、零时长 boundary、source value、
原 duration/边界、正时长重叠、全连续非有限样本和 JSON 整型；ruff 通过。测试只验证
软件规则，真实验收范围以各库实际成功/失败收据为准。

```bash
python scripts/fetch_nemar_subset.py \
  --plan research_logs/public_data_expansion_20261010/milimbeeg_ingestion/ingestion_plan.json \
  --data-root data/public_eeg/milimbeeg/nm000328/v1.0.0 \
  --output research_logs/public_data_expansion_20261010/milimbeeg_ingestion/downloads \
  --download --workers 4
python scripts/audit_milimb_liu_subset.py \
  --plan research_logs/public_data_expansion_20261010/milimbeeg_ingestion/ingestion_plan.json \
  --data-root data/public_eeg/milimbeeg/nm000328/v1.0.0 \
  --output research_logs/public_data_expansion_20261010/milimbeeg_ingestion/signal_audit_replay_new
```

来源接入扩大可用资源，不自动扩大任何已有模型实际训练样本。未来先独立冻结 task
mapping、通道/参考/单位、段内窗口、QC、source train/query/held-out subject 及临床域
验证规则，再拟合；Liu 首先要解决单位来源及复制/重叠处理方案并独立冻结有效身份规则。R2 已获用户授权，
实际远端存储/读取核验以 [R2 记录](r2_research_storage.md)的完成收据为准。
