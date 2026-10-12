# 六源公开 EEG 资源闭合清单

资源审计日期：2026-10-11；最终收口沿用现有科研分支与云端环境。
六个固定来源的必要官方原始范围均已完成下载、官方 byte/checksum 验证及 R2 保存：
**10,253 文件、7,827,676,824 bytes、1,473 个 EEG 录制文件**。
这是来源资源清单，不是新增模型结果。Kumar、PhysioNet、Leeuwis、MILimbEEG、Liu 五个新增资源均未训练。

| 来源 | 固定版本 / 许可 | 发布资源 ID | ID-session 或单 visit | EEG 录制 | 必要文件 | 必要 bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| NETBCI2026 | nm000305 v1.0.0 / CC BY 4.0 | 19 | 76 | 456 EDF | 3,577 | 3,884,165,963 |
| Kumar2024 | nm000177 v1.0.5 / CC BY 4.0 | 18 | 108 | 360 EDF | 2,705 | 1,781,052,841 |
| PhysioNet EEGMMIDB | 官方 1.0.0 / ODC By 1.0 | 109 | 109 | 327 EDF + 327 `.event` | 654 | 834,146,640 |
| Leeuwis2021 | nm000327 v1.0.0 / CC BY 4.0 | 55 | 55 | 220 EDF | 2,095 | 568,544,461 |
| MILimbEEG | nm000328 v1.0.0 / CC BY 4.0 | 60 | 60 | 60 EDF | 666 | 62,287,177 |
| Liu2024 | nm000158 v1.0.3 / CC BY 4.0 | 50 | 50 | 50 BDF | 556 | 697,479,742 |
| 必要范围相加 | 六个来源 | **311** | **458** | **1,473 EEG 文件** | **10,253** | **7,827,676,824** |

**311 仅为 19+18+109+55+60+50 的发布 ID 算术和**，不是跨库全局唯一人数、
独立生物学统计单位、模型合格人数或已训练/评估样本量。458 也只是各来源 ID-session/visit
相加，不能当作共同纵向设计。总 EEG 信号 bytes 为 7,815,353,870；其余是必要官方 metadata、
events、provenance。四个 Leeuwis 原始非 EEG sidecar（10,508,553 bytes）另存，未计入上表。
审计、源码、模型、存储收据也未计入原始来源总量。

NETBCI 必要范围由 19 份官方选择下载 manifest 按 `path` 合并，五个共享 root 文件只计一次；
完整官方 manifest 的 3,582 项不是本表 3,577 项范围。其余 NEMAR 选择清单保留必要 derivative
及转换 provenance，未重复下载全仓库 `sourcedata` 信号。源库和其 NEMAR/MOABB 镜像是同一资源。
PhysioNet 仅选原始手部 imagery runs 04/08/12；其官方 archive transport 不另增加来源或身份。

## 来源验收实际状态

| 来源 | 完整来源审计与独立复核 | 科学限制 / 下一步 |
| --- | --- | --- |
| NETBCI | 456 EDF、76 sessions；14,431 源事件保留，14,429 达到现有五秒适配门槛；两个真实短事件仍存档；独立方法收口通过 | 跨 ID 精确信号复制涉及 sub-1/6/7/15/17。现有 main19 与排除这些 ID 的 sensitivity14 各保留；14 只代表未检测到指定精确复制，不证明独立生物身份。既有模型及行为解释见专属结果文档 |
| Kumar | 360/360 EDF 全通道连续样本有限，7,200 原始 MI 事件；7,156 恰五秒、44 较短（最短 4.146484 秒）；无本库整信号精确复制；独立复核通过 | 18 发布 ID、108 sessions 是资源设计；尚未冻结窗口、QC、训练分区或模型。较短源事件不填补、不套用 NETBCI 门槛 |
| PhysioNet | 109 发布 ID / 327 原始 EDF 全读并保留 WFDB sidecar；独立复核全部 654 文件及全信号通过；`complete_with_source_flags` | S088/S089/S092/S100 三个选定 run 均有源 annotation 异常；S088/S092/S100 为真实 128 Hz。315 文件 / 105 完整三-run ID 来源合格，含 4,722 可用四秒 MI 源事件；其余 12 文件保留。此描述不是模型窗口/已训练人数 |
| Leeuwis | 完整 220 EDF / 55 ID、8,800 MI + 8,580 EDGE；独立复核全文件、native headers、17,380 行，并完整复读首末 run 通过；未检出本 derivative 的整 run/task 精确复制 | 单 visit calibration+feedback；4.996 秒源任务半开 hash 长 1,249 samples。EDGE 隔开拼接段。原始 sidecar 55 ID 映射通过；在线错误表另有 5 个无 EEG ID，不新增 EEG 人数；曲线是 20 trial 平均，非逐 trial hit |
| MILimbEEG | 60 EDF / 单 visit混合人群；3,659 正时长 3.992 秒任务 + 3,659 零时长 EDGE；7,318 是源行数；独立复核通过 | 任务含 rest，不能称 7,318 MI trial；个体年龄/临床组不可用；`drf/plf` 生物任务映射尚不可用于跨库统一标签；无原 CSV 每行转换对应证明 |
| Liu | 全部 556 官方文件、50 BDF / 2,000 四秒任务完整普查；独立复核核全部字节、50 headers、源行与复制/重叠，并完整复读 8 个有关信号；来源检查闭合 | **`source_acceptance_complete=false`、`model_training_ready=false`**。全部 50 native µV 与 TSV V 冲突；sub-4/5 整 29 通道信号相同并有 40 source-task 复制组；sub-20/43 四条源任务重叠保留；sub-47/49 仅中央 4 KiB 共享指纹候选。未宣布任何 46/44 或 50 个模型合格人数 |

Liu 的原始重叠为 sub-20 TSV 行 15/16 的 1,998/90 samples，以及 sub-43 行 27/29 的
1,004/1,002 samples。40 个跨 ID 完整 source-task 复制组均只涉及 sub-4/5；中央指纹相同
不能推导整录制相同或生物身份相同。严格审计失败、单位冲突记录和早期 HTTP 503 收据原样保留，
有效 `source_integrity_census_run03` 完成普查不解除这些科学门槛。

## 固定来源、许可及证据

| 来源 | 原始发布 DOI | 版本身份与原始接入说明 |
| --- | --- | --- |
| NETBCI | [10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7)，原库 v2.2 | [NEMAR nm000305 v1.0.0](https://data.nemar.org/nm000305/v1.0.0/manifest.json)，EDF derivative；原 BrainVision 不能与 derivative 混作一份未经转换信号 |
| Kumar | [10.5281/zenodo.10694880](https://doi.org/10.5281/zenodo.10694880) | [nm000177 v1.0.5](https://data.nemar.org/nm000177/v1.0.5/manifest.json)，MOABB derivative |
| PhysioNet | [10.13026/C28G6P](https://doi.org/10.13026/C28G6P) | [官方 EEGMMIDB 1.0.0](https://physionet.org/content/eegmmidb/1.0.0/)，官方 RECORDS、SHA256 与实际 transport 均留存 |
| Leeuwis | [10.34894/Z7ZVOD](https://doi.org/10.34894/Z7ZVOD)，原库 v1.0 | [nm000327 v1.0.0](https://data.nemar.org/nm000327/v1.0.0/manifest.json)；2026 年镜像发布日期不是新增采集人数 |
| MILimbEEG | [10.17632/x8psbz3f6x.2](https://doi.org/10.17632/x8psbz3f6x.2) | [nm000328 v1.0.0](https://data.nemar.org/nm000328/v1.0.0/manifest.json)，许可核验证据为实际 NEMAR release |
| Liu | [10.6084/m9.figshare.21679035.v5](https://doi.org/10.6084/m9.figshare.21679035.v5) | [nm000158 v1.0.3](https://data.nemar.org/nm000158/v1.0.3/manifest.json)，29 EEG、500 Hz、预处理 derivative；许可核验证据为实际 NEMAR release |

机器可检查的[六源清单](../research_logs/public_data_expansion_20261010/resource_inventory_20261011.json)
逐源保存 official manifest/checksum inventory、selection/download manifest、实际成功下载收据、
有效 source audit 和 independent receipt 的**文件路径、文件 bytes、精确文件 SHA256**，
并独立记录原始 DOI、版本、许可、源事件/flags 和未选模型状态。PhysioNet receipt 内 canonical JSON
manifest hash 与 selection manifest 文件本体 hash 是不同约定，两者不互换。

有效独立收据链接：

- [NETBCI 方法收口](../research_logs/netbci_cohort_all19_20261010/independent_methods_closeout_run01.json)
- [Kumar 交叉核对](../research_logs/public_data_expansion_20261010/kumar_ingestion/independent_source_crosscheck.json)
- [PhysioNet 独立全信号核对](../research_logs/public_data_expansion_20261010/physionet_eegmmidb/independent_source_validation_20261011.json)
- [Leeuwis full run02 独立核对](../research_logs/public_data_expansion_20261010/leeuwis_ingestion/independent_review_full_run02/independent_source_crosscheck.json)
- [MILimb 独立核对](../research_logs/public_data_expansion_20261010/milimbeeg_ingestion/independent_source_crosscheck.json)
- [Liu census run01 独立核对](../research_logs/public_data_expansion_20261010/liu2024_ingestion/independent_review_census_run01/independent_source_crosscheck.json)

来源细节见 [Kumar](kumar2024_ingestion_audit_20261011.md)、
[Leeuwis](leeuwis2021_ingestion_audit_20261011.md)、
[MILimb/Liu](milimbeeg_liu2024_ingestion_audit_20261011.md)、
[PhysioNet 来源审计](public_large_training_dataset_audit_20261010.md)及
[NETBCI 全 19 结果](netbci_all19_results_20261011.md)。
九源 568 ID 的旧 discovery 表是候选发现范围，未改写成这次六源 acquired 清单，也不代表已接入或训练。

## 存储与研究边界

用户授权的私有 R2 必要原始范围全部保存完成；对象/bytes/hash 验证及实际 GET 范围
以 [R2 存储记录](r2_research_storage.md)和对应不可变收据为准。
来源验收、科学可用性与远端字节存储是不同门槛，Liu 的全部原始缺陷保存在官方字节档案中。
大型 Leeuwis 源事件/连续 run ledgers 留在本地与 R2，compact 摘要、源码、完整 ledger hash
及保存收据进入 Git；历史部分和失败结果不覆盖。

本次未重下载既有原始来源、修改 raw、选择建模窗口、训练新模型、创建付费资源或修改第一篇论文仓库。
后续建模需逐来源冻结任务映射、通道/参考/单位、段内窗口、QC、participant/session/train-query
分区及临床域规则；所有 learned transforms 仅在训练数据拟合。
离线 decoding 或几何稳定性不能证明 co-adaptive 人类学习保持；该结论仍需要在线对照与无辅助即时/延迟探测。
