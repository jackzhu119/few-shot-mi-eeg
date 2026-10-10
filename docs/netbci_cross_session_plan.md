# NETBCI2026 单受试者跨会话分析方案

方案日期：2026-10-09（Asia/Shanghai）。状态：**适配与划分已执行验收；科学分析与真实 EEG 模型训练尚未执行**。
此方案在访问/格式审计之后、统计分析和模型训练之前冻结，不代表已经完成外部预注册。
现有样本只能作单受试者可行性与描述，不能证明人群泛化、人类学习或技能保持。

## 1. 来源、适配与已解决的问题

固定 EEG 来源为 NEMAR `nm000305 v1.0.0`，DOI `10.82901/nemar.nm000305.v1.0.0`，
CC BY 4.0；只用 `sub-1` 的 4 session × 6 run。原始 Dataverse v2.2（`10.57745/RBJRC7`）
只作独立事件/行为出处核对，不把两个版本的 EEG 拼接成更多 trial。

本地适配器 [netbci.py](../src/learning_preserving_bci/datasets/netbci.py) 成功读出 **717 × 74 × 1250**
的 250 Hz EEG，单位为 **V**，标签使用实际 `right_hand/rest` 名称；原始 EDF 数字
`right_hand=2/rest=1` 单独保存在 trial metadata。每个 trial 保留 subject、session、run、
TSV 行号、onset、半开样本区间、源文件与源校验和。行号是释放事件表的行号，
不能称作原始设计 trial 编号。适配不滤波、不换参考、不删 trial、不拟合模型。
NPZ 与强制配套 metadata.json 保存到 Git 忽略的 `data/netbci2026/derived_v1.0.0/sub-1/`，
已执行真实保存/读取校验。

对原始公开 ZIP 只做有严格字节上限的 HTTP Range 小文件读取：24 个 run 的
`.vhdr/.vmrk/events.tsv/channels.tsv/eeg.json`，不读任何 `.eeg`/MEG 信号。
24 个 `.vhdr` 的 SHA-256 全部与 NEMAR sourcedata provenance 相同；逐 run 的
717 个原始事件与 NEMAR 名称序列及重采样后时间位置一致。

- **717 个事件已经存在于原始事件表与 marker**，不是 NEMAR 导出再删 51 个 trial；
  相对于设计 4×6×32=768 的差异发生在原始公开版本之前。逐 trial 排除原因/日志仍缺失。
- `ses-01/run-04` 原始频率 **249.89999389648438 Hz**，导出为 250 Hz；事件按新采样网格取整，
  最大 onset 变化 **0.0019712411813159747 s**，小于半个 250 Hz 样本。
  其余 23 run 原始与导出都是 250 Hz、onset/sample 相同。
- 原始事件 `duration=0`（脉冲 marker），导出 `duration=5 s` 为任务 epoch 约定；
  不是实测反馈持续时间。原始 `.vmrk` 为 1 起始 sample，TSV/NEMAR 为 0 起始，
  已逐事件核验，不把两个约定混用。
- 原始和导出 Manufacturer/reference/参与者表字段有矛盾；不据此推断硬件变化。
  实际采集日期和日间间隔未从匿名化数据确认；以下 session 次序依据发表的四日实验协议，
  不把导出文件中的占位日期当成真实日期。

## 2. 冻结训练、验证、查询与校准分区

机器可读配置：[netbci_cross_session.json](../configs/netbci_cross_session.json)。
实际 717 个 trial 的固定身份清单：[analysis_partitions_verified](../research_logs/netbci2026_analysis_partitions_verified.json)。
所有分区以完整 run 隔离，任何同一 trial 的后续切窗都继承该 trial 分区。

| 用途 | Session/run | 实际 trial | 可以使用的数据 |
| --- | --- | ---: | --- |
| reference train | ses-01/run-01..03 | 90（45/45） | 开发阶段拟合 CSP、scaler、PCA 等 |
| reference validation | ses-01/run-04 | 30（15/15） | 仅选择源阶段预定候选参数；不接触 target query |
| reference query | ses-01/run-05..06 | 60（30/30） | 独立参考表现；不拟合任何变换 |
| target calibration pool | ses-02..04 各 run-01 | 90（各30） | 后续可选再校准的标签池；未选部分也不回流 query |
| target query | ses-02/run-02..06 | 149（75 MI/74 rest） | 固定模型与可选再校准使用相同测试集 |
| target query | ses-03/run-02..06 | 150（75/75） | 同上 |
| target query | ses-04/run-02..06 | 148（75/73） | 同上 |

717 个 trial 均只分配到一个基本分区；session/run 不跨分区。最终 source 模型仅在源端
参数决定后，可用 reference train+validation **120 trial** 拟合一次，随后冻结。参考 query
60 与 target query 447 始终保持独立。当前通用 `evaluate_fixed_decoder` 默认整 session
训练，**不能直接不加选择地用于此方案**；执行器须按上述 trial ID 分区接入，验收后才运行。

可选再校准预先以 seed=42 从每个 target 的 run-01 标签池抽 **10 MI+10 rest**，已保存
三个 target 各20个 trial ID。此选择只是公开离线数据中的明确标签预算，不假装这些标签
可在真实无监督在线条件获得。固定模型也在同一 target query 上测试；不能给再校准模型
额外 query 标签、target-wide scaler 或测试集 batch normalization。

## 3. 待执行的解码与神经指标

首个解码基线为 **CSP（4 components）+ shrinkage LDA**。使用 8–30 Hz、每 epoch 平均参考，
滤波/参考是计划中的确定处理，不声称是原始释放数据未经处理的真实参考。
数据驱动 normalization、QC 阈值、空间变换及任何参数选择只来自允许的源分区。
模型和变换冻结后报告 reference query 与三个 target query 的 balanced accuracy、
macro-F1、逐类 recall、confusion matrix 与实际标签数量；不报告训练 accuracy 为参考基线。

可选离线再校准保持源 CSP 冻结，只在预留的 target support 上拟合 LDA；其结果称
**label-budget recalibration diagnostic**，不称人机协同学习、实际减负或用户技能提高。
EEGNet、大模型与任何真实模型训练均不在本轮执行范围。

神经描述按统一 74 通道坐标、单位、参考、频带与时间窗计算：

- Welch PSD（V²/Hz）、Mu 8–13 Hz/Beta 13–30 Hz bandpower（V²），先逐 trial、再按 class/run 汇总；
  保留 MI 与 rest 两类，不把 rest 当成左手。
- trial covariance 与固定约定的 shrinkage/log-Euclidean 距离；样本数、SNR、参考、坏道和
  session 干扰都可能制造变化，不能把 drift 直接叫 neural learning/plasticity。
- reference train+validation 拟合 PCA 后冻结，目标 query 只投影；不在目标 query 上选维数、
  对齐或筛选有利模式。样本数匹配与 rank 敏感性另行记录，探索结果标 exploratory。
- 当前 bundle 只含 `[0,5)` 任务窗口，包含提示与反馈相关活动；不是纯 MI 时间。
  没有已核实的 prestimulus baseline、反馈 onset 或完整光标事件，**本轮不做 ERD/ERS 或
  按假定反馈事件切段**。这些分析需回到 continuous run 单独验证基线与时间语义。

适配层仅验证 finite/格式；不等于伪迹清理。执行科学分析前，需要确定 source-fit QC，
报告逐 run/class 的剔除数量和原因，并保留“不剔除”敏感性。原始已排除 trial 的缺失
不能由此修复，也不能只选择后期成功 trial 得到看似改善的神经指标。

## 4. 真实行为关联：已验证与仍待验证

原始官方 participants.tsv 与字典已通过仓储 MD5。`sub-01` 的
`BCI-Performance-session1..4` 各有六个原始光标命中率，属于真正在线反馈成绩的
**run-level percentage**。`sub-1` 对 `sub-01`、四 session 和24 run 的 EEG 身份已用
header SHA 与事件/marker 序列验证。

目前行为向量只有位置，没有显式 run ID。候选表按位置1..6对应run-01..06，但这不是
作者明确的逐 run 顺序验收；表中每行保留 `run_score_order_status`，不标为无条件完成。
在该候选顺序下 **23/24** 个成绩不与相应29/30 EEG trial 的百分比分母相容。
在分母1..200的数值检查中，28、56、84、112、140、168、196均可解释四舍五入值，
因此 **不能选28作为真实分母，也不反推整数 hits 或逐 trial hit/miss**。

可立即保留每 session 六个公开成绩及其未加权均值作描述（不依赖向量内部顺序）；
均值不是全 session pooled trial success rate。逐 run 的神经指标—成绩关联等待
向量顺序确认；二项模型、成功/失败分组分析等待实际分母与 trial-level 日志。
在线 `ChannelFreq-Features-session1..4` 保留为 session 元数据，分类器每 session 重校准，
成绩与 session 改变有 decoder/疲劳/家庭练习等混杂，不能归因为本仓库算法或学习机制。

如果后续确需更细的学习分析，向作者确认的内容是：**六 run 成绩的顺序、百分比分母与
warm-up/abort/rejection 计分规则、EEG 排除 trial 的身份/原因、是否可提供逐 trial outcomes/
cursor logs 和实际 session 间隔**。这与 ZIP 密码无关，本轮没有发送邮件。

## 5. 统计与推进门槛

当前独立人数 **n=1**。24 run/717 trial 不是24或717个独立受试者；不做被试层面的
群体 CI、p值、人群泛化或学习保持结论。仅报告单受试者的描述与离线可行性，
观察到升高、降低或无变化都如实保留。

以后扩展受试者须另行决定下载；算法与指标在开发集决定后，测试被试不反复调参。
届时以被试为独立单位计算 paired changes/subject bootstrap；神经—成绩关联考虑
within-subject centering 与 session/在线解码器重校准，不能用 trial bootstrap冒充被试 CI。

已通过：访问/格式、精确 epoch 适配与真实 roundtrip、717个事件跨版本核对、固定划分。
仍待：run成绩顺序/计分分母/原始trial排除原因、科学QC、严格按划分的执行器、真实模型分析。
SHU 保留 `pending author access`，不阻塞 NETBCI 这些可独立完成的工作。

## 6. 可重放入口与证据

在 README 的冻结环境下执行。已有结果不覆盖，复跑时为 CLI 传新的 output/table 路径。

```bash
python scripts/check_netbci_subset.py --output /workspace/scratch/netbci_access_recheck.json
python scripts/check_netbci_behavior_link.py --output /workspace/scratch/netbci_behavior_recheck.json --table /workspace/scratch/netbci_behavior_recheck.tsv
python scripts/prepare_netbci_analysis.py --output /workspace/scratch/netbci_partitions_recheck.json
```

`fetch_netbci_original_metadata.py` 是显式的元数据联网入口，严格检查206响应、8 MB上限与
成员类型；拒绝信号成员或任何加密成员。已获取的原始小文件应优先本地复用，不重复请求。

- [原始元数据读取收据](../research_logs/netbci2026_original_metadata_receipt.json)：成员CRC与
  headerSHA校验；没有下载全档，不能称完整ZIP的MD5已经本地验证。
- [跨版本与行为核查](../research_logs/netbci2026_behavior_link_verified.json)、
  [带状态的候选run表](../research_logs/netbci2026_behavior_run_verified_candidates.tsv)。
- [真实适配验收](../research_logs/netbci2026_adapter_audit.json)。
- 作者事件编码来源：[BIDSify.py 固定版本](https://github.com/mccorsi/NETBCI_data/blob/48fe2b437ac641d222ad5c214f26f3008204ebd0/scripts/bidsify/BIDSify.py)，
  `event_dict={"MI":1,"Rest":2}`；只作源码证据，不复制 GPL 源码实现进本项目。

## 后续执行记录

2026-10-10已执行探索性表征、CSP-LDA及3epoch CPU EEGNet最小验证，见[stage1证据](netbci_stage1_evidence_and_decision.md)。本文件“不训练”陈述是上一轮范围。原pilot的源训练/验证按同session不同run；用户本轮要求三阶段分日期，现另有[日期角色协议](../configs/netbci_date_separated.json)及审计。其验证session02、测试03/04互斥，沿用未变冻结模型，无新选参；因先前pilot成绩已经观察，属于回顾性探索评估，不能冒充新未查看的确认性test。
