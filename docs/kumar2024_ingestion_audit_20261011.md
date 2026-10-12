# Kumar2024 独立纵向库：固定来源接入与信号审计

执行日期：2026-10-11（Asia/Shanghai）。这是原十人队列之后的外部数据资源扩展，
不追溯改变十人探索性方案。固定版本全部必要文件和 360 EDF 源信号审计已实际完成；
本阶段为资源接入，不是已完成的新模型训练或外部预测验证。

## 固定来源与预算

采用 [Kumar et al. 2024](https://doi.org/10.1093/pnasnexus/pgae076) 的
[NEMAR nm000177 v1.0.5](https://data.nemar.org/nm000177/v1.0.5/)，数据 CC BY 4.0。
原始来源为 [Zenodo 10694880](https://zenodo.org/records/10694880)。
该固定 derivative 包含名义 18 人、108 人会话、360 EDF，22 EEG、512 Hz、左右手 MI。
首次离线校准为 `ses-0`，后五次在线会话为 `ses-1`–`ses-5`；仅 bar task。
这些标签和历史训练条件不能替代 hit/miss、racing 成绩或本项目的无辅助保持实验。

选择 [2,705 个必要文件](../research_logs/public_data_expansion_20261010/kumar2024_nm000177_v1.0.5_selection_manifest.json)，
总量 1,781,052,841 bytes；360 EDF 占 1,778,578,770 bytes。
保留每个 subject sidecar、四个根文件和原始来源 provenance；不下载全仓储重复 sourcedata。
选择清单 SHA256 为 `377eb25e0938fde905b023a309b8b7adebd1a4779fd48c3d2a2d6ce22cb16750`，
固定官方 manifest SHA256 为 `1fe0fe2dbf002614dc38c54b5cd25fcb68b65c6c18b348343307d9d4668d420f`。
版本、许可与独立容量清点见[接入计划](../research_logs/public_data_expansion_20261010/kumar2024_ingestion_plan.json)。

## 执行顺序与验收

先冻结原十人结果的 Git checkpoint，再下载新 EEG 信号。小型元数据可以先行读取；
接入脚本对所有元数据完成官方校验且核验根文件的 license/version 后，才开始任何 EDF 传输。
沿用既有云环境和科研分支，不初始化第二个项目或改变科学依赖。

[下载器](../scripts/fetch_nemar_subset.py) 默认只打印本地计划，显式 `--download` 才传输。
最多四个并行 HTTP 请求、每文件最多三次尝试，继承代理、CA 与 TLS 验证。
只接受选择清单中的明确 HTTPS URL 和该清单已有的官方 object redirect；校验 size 与
SHA256/Git blob checksum，已有错误文件拒绝覆盖。中间 `.part` 不视为完成数据；
失败、重试和实际字节数保存在带时间戳的不可覆盖收据，签名 URL 的查询秘密不记录。

[审计器](../scripts/audit_kumar_subset.py) 串行读取 360 个 EDF，每个原始文件和 sidecar
重新验证官方校验，核验 22 通道固定顺序、512 Hz、原始 µV 与 MNE 输出 V、源 onset/sample、
duration/boundary、左右手 `value=1/2`、EDF annotation 与 TSV 逐事件一致。
所有连续样本在有界 16,384-sample blocks 中检查有限值，避免只检查 trial 窗口或
将全部参与者装入内存。保存完整信号的确定数值 SHA256 和中间 4 KiB 数值指纹；
相同指纹是重复信号检查线索，不代替生物学身份核查。

已有事件 metadata 清点为 7,200 条源事件、左右手各 3,600，其中 7,156 条 5 秒、
44 条 4.146484–4.992188 秒的 partial event。六位小数 duration 导出可能造成
不足 0.001 sample 的舍入，审计显式核验该精度后转换实际边界。
本阶段保留全部源身份，不填充、延长、删除或沿用 NETBCI 固定 5 秒分析排除规则。
未来训练前另行冻结 Kumar 的窗口、QC、source/train/query/test 与 task mapping。

实际下载到的 `participants.tsv` 是正常 tab/newline 表（未出现转义分隔符），但
全部 age=2020，不能作为人类年龄；generic healthy group 不能建立 GR/PAR 分组。
原研究组别需显式追溯原始 subject mapping，不能由本 derivative 编号或成绩推断。

## 重放入口

```bash
python scripts/fetch_nemar_subset.py \
  --plan research_logs/public_data_expansion_20261010/kumar2024_ingestion_plan.json \
  --data-root data/public_eeg/kumar2024/nm000177/v1.0.5 \
  --output research_logs/public_data_expansion_20261010/kumar_ingestion/downloads \
  --download --workers 4
python scripts/audit_kumar_subset.py \
  --plan research_logs/public_data_expansion_20261010/kumar2024_ingestion_plan.json \
  --data-root data/public_eeg/kumar2024/nm000177/v1.0.5 \
  --output research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_replay_new
```

脚本 safeguards 的 34 个有意义测试通过，包括越界、partial event 原样保留、全连续信号
的非有限值、checksum/path/redirect/secret/有界重试和不可覆盖收据；这只验证软件，
不自动通过真实 EEG 或论文的训练、泛化、学习和保持验收。
真实首轮审计发现 MNE 的 `n_times` 为 `numpy.int64`，在首个通过验证的 EDF 收据序列化时
失败；没有源信号或事件校验失败，也未写出部分 run 收据。保留
[失败记录](../research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run01_serialization_failure.json)，
仅将两个 sample-count 字段显式转 Python `int`；回归测试验证数值 hash 不变且可序列化。
实际成功审计使用新的 `signal_audit_run02`；重放必须使用新的输出目录，不能覆盖旧记录。

## 本轮实际结果

2026-10-11 14:38:25–14:40:46（Asia/Shanghai）完成新的全部必要文件下载：
**2,705 文件、1,781,052,841 bytes**，与固定选择清单及磁盘实测一致。
2,345 个元数据文件复用后重新通过官方校验，360 个 EDF 新下载并通过官方校验，
实际新传输 **1,778,578,770 bytes**；无失败、重试或 `.part` 文件。
实际逐文件证据为
[下载收据](../research_logs/public_data_expansion_20261010/kumar_ingestion/downloads/download_receipt_20261011T063825615923Z.json)，
SHA256 `0eb789b011438ee7b99d5654dd7f5eeab3d04c83cd67b4002c63023e85bb3f4f`。

2026-10-11 14:42 完成 360/360 EDF 串行原始连续信号审计：**18 个发布身份、108 会话、
7,200 个源事件**，左右手各 3,600。所有 22 通道、512 Hz、µV/V、annotation、源事件时间、
边界、官方文件校验及全连续有限值检查通过。7,156 条为完整 5 秒，44 条 partial 的身份和
实际 duration 原样保留，没有选择训练窗口、填充、延长或删除。
完整数值 SHA256 和中央 4 KiB 指纹在本库内均无相同的 run 组；这不能证明跨资源的生物学身份独立。
详见 [360-run 审计汇总](../research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run02/aggregate.json)，
SHA256 `be849c3c0cdc1c2f948f1aaef3094a53bcfa2f1855419717d1baf59df2f3ac60`，
及保留所有来源行的 [事件清单](../research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run02/source_events.json)。

独立复核未调用接入或审计器的任何 helper：重新计算全部 2,705 文件官方校验、全部
360 原始 TSV 的逐行覆盖、类别/会话/partial 数量及重复组；从头实读两个首末代表 EDF，
完整信号及中央指纹数值 hash 与审计收据精确相同。结果见
[独立交叉核对](../research_logs/public_data_expansion_20261010/kumar_ingestion/independent_source_crosscheck.json)
与同目录的可重放 Python 源码。源数据已通知 R2 增量同步；实际上传与远端读取校验完成
程度以主任务的 [R2 存储记录](r2_research_storage.md)及带时间戳收据为准。

模型拟合、Kumar 窗口/QC/train/query/test 方案和 GR/PAR 原始组别映射仍未完成。
实际 participants 表有 152 个 tab、19 个 newline，没有字面转义分隔符；18 人 age=2020
仍不能作为年龄。固定接入计划中的 escaped-table 风险记录为先前探查快照，不覆盖当前实测结果。

扩充独立研究来源可增强离线外部验证的证据。多 trial、多 session、同人的不同 derivative
均不增加独立参与者数；跨研究身份重叠未排除前，不把名义人数相加称为确认的 pooled n。
本轮没有新模型拟合，也不能证明本项目候选 decoder policy 保留人类神经控制技能。
