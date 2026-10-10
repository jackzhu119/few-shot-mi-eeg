# 数据集可行性审计：SHU 与 NETBCI

核查日期：2026-10-09（Asia/Shanghai）。本报告区分原论文陈述、官方发布元数据、实际小型文件与实际信号读取。**最新验收仅覆盖 NETBCI2026 的一个受试者：4 个 session、24 个 EDF；未下载全量数据、MEG/MRI 或大型 ZIP，访问验收时未训练模型；2026-10-10已另外执行单受试者冻结baseline最小实验，见[最新真实证据](netbci_stage1_evidence_and_decision.md)。** 第 1–3 节保留初始元数据审计及原始来源信息；当前接入状态以第 0 节为准。

结论：**第一优先级为 NETBCI2026 / NEMAR `nm000305` v1.0.0；SHU / Ma2022 为第二优先级，原始接入状态 `pending author access`。** NETBCI 已通过单受试者公开访问、校验和及 MNE 读取门槛；本地适配器和原始/derivative 事件对应已验收；行为 run 顺序、评分分母及科学分析仍待验收。两者都不能单独证明某种解码方法使人类学得更快、减少校准需求或产生长期保持。NETBCI 的实验有真实在线反馈，但每个 session 重新校准分类器；公开原始行为侧表按 run 汇总，不能伪造逐 trial 行为。

## 0. 当前优先级与真实读取验收

### NETBCI2026：公开来源、版本、访问与范围

| 项目 | 本轮核实结果 |
| --- | --- |
| 官方 NEMAR 入口 | https://www.nemar.org/dataset/nm000305；本环境访问网页返回 HTTP 403，但官方数据 API 和文件端点返回 200 |
| 可达元数据 | [dataset API](https://data.nemar.org/nm000305/)、[metadata.json](https://data.nemar.org/nm000305/metadata.json)、[固定版本 manifest](https://data.nemar.org/nm000305/v1.0.0/manifest.json) |
| 固定版本 | **v1.0.0**，API `created_at=2026-10-08 03:46:39`；该字段未注明时区，不换算为实验日期 |
| 版本 DOI | [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)；集合 DOI 为 `10.82901/nemar.nm000305` |
| 数据许可 | NEMAR metadata 与 dataset_description 一致为 **CC BY 4.0**；使用需署名、链接许可并注明修改。文章/代码的许可另计 |
| 发布格式 | 根 JSON 为 `DatasetType=derivative`、BIDS 1.9.0、`GeneratedBy=moabb 1.8.0dev0`；真正的信号文件是 **EDF**，README 的 BrainVision 是上游格式说明。sourcedata provenance 的上游检索层另记 `moabb_version_used=v1.7.1-11-g9c6b1cc`、retrieved `2026-10-05`。这是来源自述；该公开 Git 树未见 NETBCI loader，具体导出源码版本尚未完全解析，不混成单一已核实软件版本 |
| 公开目录 | 19 个受试者、每人 4 session × 6 feedback run；manifest 共 3,582 文件、3,884,172,685 bytes，支持单文件 URL，无需下载归档 |
| 本轮实际下载 | **仅 `sub-1`**，24 个 EEG EDF 与该受试者 sidecars，加 5 个根/出处文件，共 **169 文件、193,462,298 bytes**；数据在 Git 忽略的 `data/netbci2026/nm000305/v1.0.0/` |
| 校验 | 全部 169 文件与官方 manifest 校验一致：EDF 为 SHA-256，Git 管理的小文件为 Git blob SHA-1；另存本地 SHA-256。来源快照与收据见 [access_receipt](../research_logs/netbci2026_sources/access_receipt.json)，完整读取审计见 [subject1_audit](../research_logs/netbci2026_subject1_audit.json) |
| 读取环境 | Python 3.11.16、MNE 1.10.2、NumPy 2.2.6；现有 MOABB 1.4.3 无 NETBCI2026/Ma2022 类，本轮直接用 MNE 读公开 EDF，不把 import 成功当成数据验证 |

原始来源是 Dataverse [10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7) v2.2，包含约 49 GB 的多模态归档及独立行为/问卷侧表。NEMAR 是由该研究派生的 EEG 导出版本；`sub-1/task-imagery/EDF` 与上游 `sub-01/task-MotorImageryRest/BrainVision` 的命名、信号存储、事件映射及参与者字段不同。NEMAR `sourcedata` manifest 只有 456 个 `.vhdr` 头文件，没有配套 `.eeg/.vmrk`，不能作为完整上游 BrainVision 数据读取。**未下载原始大归档，未假定两版本信号逐点相等，不直接混用。**

### sub-1：真实通道、采样与试次数

| BIDS session | 实读 run 数 | 右手 MI | 休息 | 总 trial |
| --- | ---: | ---: | ---: | ---: |
| ses-01 | 6 | 90 | 90 | 180 |
| ses-02 | 6 | 90 | 89 | 179 |
| ses-03 | 6 | 90 | 90 | 180 |
| ses-04 | 6 | 90 | 88 | 178 |
| 合计 | **24** | **360** | **357** | **717** |

实读为 **74 个 EEG 通道、250 Hz**，包括 `C3/Cz/C4`；通道顺序从 EDF 与 channels.tsv 对照，完整名称保存在读取审计，不按推测补齐。EDF 物理单位为 **µV**，MNE 返回 **V**。四个 session 的通道约定需在适配时保持一致。实验的原始采集为 1000 Hz，公开 EEG 已降采样为 250 Hz，不能写成未经处理的采集 raw。

24 个 EDF 全部成功读取，完整信号均为有限值；EDF 与 channels.tsv 的名称、类型、物理单位及采样率相符，通道顺序跨 run/session 一致。全部 717 个 TSV 事件与 EDF annotation 的名称、onset、duration 逐项一致，`mne.events_from_annotations` 生成的 sample/value 与 TSV 相符，5 秒切片均为 1,250 点且不越界。这是格式与完整性验收，不是伪迹清理或科学分析验收。

可重放本地检查：`python scripts/check_netbci_subset.py`（已激活 README 中的冻结环境；不联网、不训练）。可执行伴随记录见 [netbci2026_access_check.ipynb](../notebooks/netbci2026_access_check.ipynb)。

本受试者各 run 实际为 29 或 30 trials，不能硬编码为设计的 32。NEMAR README 的全体 `14,431 trials` 与“375/456 run 保留 32”的陈述未通过全体事件实读验收；本轮只报告上述 **717 个实际存储事件**。后续原始元数据核查确认原始发布已经只有同样的 717 个事件，未见 NEMAR 转换额外丢失事件；原始减少原因未知，不能自动归因为坏 trial 删除。

### 事件时间、标签与格式矛盾

- **真实任务为右手抓握 MI vs 休息**。24 个 run 的 TSV 实际一致为 `trial_type=right_hand, value=2` 和 `trial_type=rest, value=1`，与 README 的 `right_hand=1, rest=2` 相反。事件名与 EDF annotation 对照后使用；数值编码属于文件约定，不能从 README 直接硬编码。
- NEMAR events JSON 明确 `onset/duration` 单位 **s**、`sample` 索引**以 0 为起点**。首个事件实际为 `onset=12.332 s, sample=3083`，与 EDF **250 Hz** 的 `onset × sfreq` 一致；不是毫秒，也不是 SHU 的 1 起始索引。核验时检查所有事件的样本对齐、递增、持续时间及信号边界。
- 实际事件 duration 为 **5 s**，对应发布的 target/任务时段。EDF annotation 与 TSV 的名称、onset、duration 可逐 trial 对照；保留 session/run/trial 身份。需要 5 秒切片时按文件采样率得到半开区间，不盲目用包含端点的 `tmax=5` 读取 1,251 点或跨越 run。
- 事件只有 `right_hand/rest`，**没有已核实的 feedback-onset、逐 trial hit/miss、光标轨迹或响应时间**。论文的反馈时段为 trial 第 3–6 s，不等于文件单独记录了反馈事件；不能生成这些缺失字段。
- NEMAR 元数据存在额外风险：参与者表把群体均龄 `27.47` 重复给每人且 sex 为 `n/a`，不可用于个体年龄/性别分析；EEG JSON 的 Manufacturer 为 Electrical Geodesics，model/README 却描述 Easycap+MEGIN，需保留矛盾，不能据此猜测硬件改变。`status=good` 也不构成无伪迹证明。

### 后续最小接入与跨版本核查（本轮）

本地适配器输出 **717 × 74 × 1250**，单位 V，保留全部 trial 的 subject/session/run/TSV 行身份；已验证 NPZ 与元数据往返读取。审计见 [adapter audit](../research_logs/netbci2026_adapter_audit.json)。

原始 v2.2 大归档仅通过有上限的 HTTP Range 获取 sub-01 的 120 个小型头文件、事件、marker 和通道元数据：35 个范围请求、1,339,985 bytes（另有初始尾部探针 131,072 bytes），未获取原始信号。成员 CRC 与本地 SHA 保存；**未验证整个 49 GB 归档的 MD5**。见 [范围读取收据](../research_logs/netbci2026_original_metadata_receipt.json)。

24 个原始 `.vhdr` 与 NEMAR provenance 的 SHA256 一致。原始已有同样的 717 个事件；原始 marker 位置从 1 起，TSV sample 从 0 起，onset 为秒。原始 MI=1/Rest=2 与 derivative right_hand=2/rest=1 按语义对齐。原始 ses-01/run-04 为 249.89999389648438 Hz，其余为 250 Hz；导出为 250 Hz，事件样本与实际 onset 的舍入一致。原始 duration=0 的脉冲被导出为 5 秒任务窗，不能当作真实反馈持续时间，也不宣称两版信号逐点相等。

行为候选关联的 **23/24** 个百分比与对应 EEG 的 29/30 个事件作分母不相容；1–200 的候选分母中 28 的多个倍数同样相容，不能据此指定分母或重建 hit/miss。详见 [跨版本核查](../research_logs/netbci2026_behavior_link_verified.json)。[跨会话方案](netbci_cross_session_plan.md)已准备；没有执行真实 EEG 模型训练。

### 在线反馈与纵向行为记录能支持到哪一步

原论文与 NEMAR README 确认采集属于真实在线视觉光标反馈实验；每个 session 另做校准并重新选择在线分类特征。因此这些 EEG 可用于跨日/run 的观察性神经变化分析，但不能把变化直接解释为人类学习，或把离线算法分数当成历史在线行为。

**NEMAR v1.0.0 不包含行为成绩列或独立行为文件。** 其 participants.tsv 只有基本参与者字段，manifest 没有逐 trial 结果/光标文件。原始 Dataverse 的独立 participants.tsv 提供 `BCI-Performance-session1..4`，每格是六个 run 的光标击中目标百分比，并有在线 `ChannelFreq-Features-session1..4`、STAI/VMIQ 等字段。本轮重新实读该 v2.2 文件：file ID **758600**、**8,644 bytes**、19 行、MD5 **b9aa1c07015820e80bc79be6a61f30fc** 与仓储匹配；副本与访问凭证见 [behavior_receipt](../research_logs/netbci2026_sources/original_dataverse/behavior_receipt.json)。participants.json 首次请求 HTTP 503，一次重试后成功；**4,700 bytes** 与官方 MD5 匹配，其字段说明明确成绩为每 run 光标击中目标的 trial 百分比。原文件含 trailing commas，保存原字节，不静默修复或把它说成已通过严格 JSON 验证。

该表具备纵向 **run-level** 行为关联的候选价值。NEMAR sourcedata provenance 将 subject `1` 对应到上游 `sub-01`，24 run 的原始头文件校验、通道和全部事件顺序已交叉验证；行为向量的 run 顺序与评分 trial 分母仍未确认，成绩到 EEG run 的关联仅为候选。原始 `sub-01` 的四个 session 六 run 成绩向量已保存在来源文件，可与后续神经指标在 run 粒度关联；**不能反推或广播成逐 trial hit/miss**。独立训练后保持、无辅助 probe、在家练习依从性和逐 trial 在线输出仍未核实。

### SHU 的当前状态与作者访问清单

**第二优先级，`pending author access`**。MOABB Ma2022 指向 `nm000288`，官方更新注明 publication pending；本轮不继续请求该不可用接口。现有 MOABB 1.4.3 无此类。保留 SHU 五日左右手 MI 的通用接口与研究计划，不把加载器存在或 metadata 列出文件当成已公开可用。

调整优先级前已直接读取 Figshare 原论文 v1 的 `sub-001` 独立 EDF/MAT/events 与 3 个根小文件（18 文件、94,536,106 bytes，官方 MD5 全匹配）；EDF/MAT shape 探针确认 32 通道/250 Hz、MAT trials 100/100/99/99/94。这些历史探针保留，不作为原始 ZIP 解密、NEMAR 公开或 SHU 生产接入完成的证明。未请求、猜测或绕过任何 ZIP 密码；后续不再扩展 SHU 下载。

若后续确需当前原始加密 ZIP，必须向作者取得：**合法下载/使用说明与正确 ZIP 密码、授权适用版本和文件校验清单、EDF/MAT 及 label 对应关系、事件 onset/duration/sample 的真实单位与索引起点、坏 trial 排除与原始 trial/session/day 映射**。若研究需要完整 cue/rest/feedback 时间轴、实际日期或学习行为，还须明确询问这些数据是否保留、是否可提供；不能认为密码本身解决了语义缺失。密码不写入代码或 Git。

## 1. 证据与核查范围

证据等级：

- **已确认（论文）**：官方原论文 HTML 或 PDF 明确陈述；不表示已经检查发布信号文件的内容。
- **已确认（发布元数据）**：官方仓储/API 明确提供许可、版本、文件名、体积、校验和、访问限制等。
- **已确认（实读小文件）**：本轮读取的官方 README、JSON、TSV；已按仓储提供的 MD5 校验，全部匹配。MD5 在此用于核对文件一致性，不替代 TLS 与来源信任。
- **未知/待核查**：尚未读取实际信号文件、ZIP 内目录或必要原始日志，不能据摘要或文件格式补造字段。

初始元数据审计读取范围（后续真实 EEG 读取见第 0 节）：

| Dataset | 读取范围 | 明确未读取 |
| --- | --- | --- |
| A / SHU | Nature 全文 HTML；figshare 最新 v3 及原论文所引 v1 的 API；README；公共 EEG/events JSON；`sub-001_ses-01` events TSV | EDF/MAT 信号、任何 ZIP 内容、作者提供的 ZIP 密码 |
| B / NETBCI | Nature 摘要 HTML 与官方 `reference.pdf`（ARTICLE IN PRESS）；Dataverse v2.2 API/页面；README、dataset description、participants JSON/TSV；官方 GitHub README/LICENSE 与事件转换脚本 | Archive.zip/derivatives.zip 内容；EEG/MEG/MRI 信号；逐 trial 在线分类输出、光标轨迹、命中日志 |

Nature 对 B 的当前 HTML 本轮只返回摘要，正文细节来自该站点公开的官方 PDF，不能把摘要当成字段说明。官方 GitHub README 仍写“即将发布”，而数据仓储 v2.2 已发布；以实际仓储发布状态为准。

## 2. Dataset A：SHU Multi-session Dataset

原论文：Ma et al., *A large EEG dataset for studying cross-session variability in motor imagery brain-computer interface*，Scientific Data，2022。

| 项目 | 已确认事实 | 依据/限制 |
| --- | --- | --- |
| 论文 DOI | `10.1038/s41597-022-01647-1` | [官方全文](https://www.nature.com/articles/s41597-022-01647-1) |
| 官方数据 | [figshare 发布页](https://figshare.com/articles/software/shu_dataset/19228725) | 发布标题为 SHU Multi-session Dataset；页面类别 software 不代表只有代码 |
| 数据 DOI/版本 | 论文引用 `10.6084/m9.figshare.19228725.v1`；核查时最新 `10.6084/m9.figshare.19228725.v3` | [v1 API](https://api.figshare.com/v2/articles/19228725/versions/1)、[最新 API](https://api.figshare.com/v2/articles/19228725)；版本文件集合不同 |
| 人数 | 25 名健康、无 MI-BCI 经验受试者，20–24 岁，12 名女性 | 论文 Methods；不是临床/卒中队列 |
| session/day | 每人 5 个 session，分别在 5 个不同日，间隔 2–3 天 | 不等于独立的保持/复测实验 |
| task | 左手 vs 右手抓握的运动想象 | 指令标签；不是实际运动、成功与失败标签 |
| EEG | 32 通道，250 Hz，论文单位 μV | 小型 EEG JSON 也给出 32/250；真实 MAT/EDF 的实际单位、轴顺序仍待核查 |
| trial 数 | 设计每 session 100，理论 12,500；坏段/坏 trial 删除后部分 session 少于 100 | 应按实际文件计数，不能固定假定每 session 100 |
| 释放内容 | 预处理 EDF、按 trial 保存 MAT、events/元数据与验证代码 | 论文使用 EEG-BIDS 组织；不是完整未经处理的采集记录 |
| MAT 描述 | `data` 轴为 trial × channel × sample，典型 100 × 32 × 1000；另有标签 | 论文 Data Records；1000/250 = 4 s MI 片段；实际文件键/标签轴尚未核对 |
| 预处理 | 坏段评估/删除、baseline removal、0.5–40 Hz FIR；保留 4 s MI | 不应再声称保留完整 cue/rest/feedback 时间轴 |
| 数据许可 | **CC BY 4.0** | v1/v3 API `license` 都明确；[许可](https://creativecommons.org/licenses/by/4.0/)；文章也为 CC BY 4.0 |
| 访问限制 | v3 描述与 README 明确要求联系作者获取 ZIP 密码 | 官方写明 “ask for the passworld of .zip files”；本轮没有请求密码、没有测试解密，不声称压缩信号已可直接使用 |

### 下载入口、体积与版本

v3 文件元数据共 139 个文件，总计 **2,227,787,569 bytes（约 2.23 GB / 2.07 GiB）**，包括可重复的独立事件表及 ZIP 内容，不能当成去重后 EEG 体积。

| v3 文件 | 官方稳定下载 URL | 元数据大小 |
| --- | --- | --- |
| `edf_files.zip` | https://ndownloader.figshare.com/files/36728991 | 737,904,661 bytes |
| `mat_files.zip` | https://ndownloader.figshare.com/files/36728994 | 1,433,568,381 bytes |
| `code_files.zip` | https://ndownloader.figshare.com/files/36728988 | 55,659,345 bytes |
| `events.zip` | https://ndownloader.figshare.com/files/35739800 | 99,354 bytes |
| `README.txt` | https://ndownloader.figshare.com/files/36729006 | 989 bytes；实读 |
| `task-motorimagery_eeg.json` | https://ndownloader.figshare.com/files/34166160 | 1,233 bytes；实读 |
| `task-motorimagery_events.json` | https://ndownloader.figshare.com/files/34166166 | 751 bytes；实读 |
| `sub-001_ses-01_task_motorimagery_events.tsv` | https://ndownloader.figshare.com/files/34166184 | 4,578 bytes；实读 |

v1 API 仍列出 125 个独立 EDF、125 个独立 MAT，且同时提供 ZIP：125 个 EDF 合计 **768,288,000 bytes**，125 个 MAT 合计 **1,534,591,904 bytes**，全部列出文件总计 **4,530,639,029 bytes**，其中有独立文件和归档的重复内容。例如 v1 `sub-001_ses-01` EDF URL 为 https://ndownloader.figshare.com/files/34166559 （6,408,448 bytes）。**只有元数据可读已验证；没有测试该信号文件下载及读取。** 后续接入应固定版本/文件 ID/校验和，不能将 v1 独立文件与 v3 ZIP 默认为内容完全等价，也不应以历史版本绕过作者当前使用说明。

### 事件、标签、行为与时间轴

实读的 `sub-001_ses-01` events TSV 有 100 行，`left` 与 `right` 各 50 行，列为：

```text
onset  duration  trial_type  response_time  sample  value
```

已确认标签：样本 TSV 为 `trial_type=left/right`，数值标签为 `1=左手 MI`、`2=右手 MI`（events JSON）。`response_time` 全是 `n/a`，JSON 明确写“不使用该列”；不能将它解释为响应速度或训练行为表现。

必须解决的元数据矛盾：

1. 样本 TSV 中 `onset` 为 1、1001、2001…，`duration=1000`，且 `sample` 同样为 1、1001…；events JSON 却将 onset/duration 标为 millisecond。若按 250 Hz 的 1000 个点解释，这是 4 s，而非 1 s。**当前不能确认该表的 onset/duration 单位，也不能直接按 BIDS 秒单位读取。**
2. events JSON `trial_type.Levels` 写 `hand/elbow`，实际 TSV 写 `left/right`；应以真实数值/任务核对，而非把 elbow 创建为第三种实验任务。
3. JSON 对 sample 的描述同时提到从 0 起与 MATLAB 从 1 起，样本表从 1 起；原始文件对齐需实测。
4. 论文描述完整 trial 7.5 s，但发布 README 描述 0–2 s 休息、2–4 s cue、4–8 s MI；释放 epoch 是 4 s。完整 trial 时间不能只凭其中一种描述硬编码。
5. EEG JSON 写 `SoftwareFilters=n/a` 和 continuous，但论文明确说明公开数据已滤波及保留 MI 段；JSON montage 为 10–20，论文为 10–10。实际头信息及导联映射需要单独验证。

反馈/学习判定：原论文描述提示驱动的 MI 采集与离线 WS/CS/CSA 解码验证，没有明确提供闭环在线反馈、逐 trial 成功/失败或训练效果记录。本轮实读文件也没有这些字段。因此**“已确认存在真实学习反馈”不成立**；目前只能写“未记录/未验证”，不能以 5 天重复实验或 CSA 算法精度上升证明人类学习。

## 3. Dataset B：NETBCI

原论文：Corsi et al., *Understanding Brain-Computer Interfaces training:a longitudinal and multimodal dataset*，Scientific Data，2026。用户给出的 NETBCI 名称对应此论文，而非另一套同名数据。

| 项目 | 已确认事实 | 依据/限制 |
| --- | --- | --- |
| 论文 DOI | `10.1038/s41597-026-08237-5` | [Nature 页面](https://www.nature.com/articles/s41597-026-08237-5)、[官方正文 PDF](https://www.nature.com/articles/s41597-026-08237-5_reference.pdf) |
| 官方数据 DOI | **`10.57745/RBJRC7`** | https://doi.org/10.57745/RBJRC7 |
| 发布平台/版本 | CNRS Research Data / Recherche Data Gouv Dataverse，核查时 **v2.2，RELEASED**，发布时间 2026-08-24 | [发布页](https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/RBJRC7)、[API](https://entrepot.recherche.data.gouv.fr/api/datasets/:persistentId/?persistentId=doi:10.57745/RBJRC7) |
| 人数 | 19 名健康、右利手、BCI 初学者；7 女、12 男，19–35 岁 | 论文；实读 participants TSV 为 19 行 |
| session/day | 每人 4 个不同日的 session，两周内每周两次 | 论文；匿名化移除了真实记录日期，精确日间间隔需数据/日志核对 |
| task | 持续右手抓握 MI vs 睁眼静息，控制一维光标上下位置 | 不是 SHU 的左右手分类，不宜直接合并标签定义 |
| EEG/MEG | EEG 74 通道；MEG 102 magnetometers + 204 gradiometers | 论文及发布 description 支持 EEG74/MEG306 |
| sfreq | 采集 1000 Hz；发布 description 标示 EEG/MEG **250 Hz** | 降采样/MaxFilter 过程见论文；实际信号文件头尚未读取 |
| session 内容 | 前/后各 3 min 睁眼静息；BCI testing 6 run × 32 trial，MI/rest 各半 | 论文；设计 192 trial/session 不等于发布文件事件计数已核实 |
| 校准数据 | 实验先有无反馈 calibration：5 run × 32 trial = 160；随后反馈 testing 6 run = 192 | 论文明确分析 testing phase；不能假定 calibration 信号也已公开 |
| 释放格式 | EEG `.eeg`、MEG `.fif`，BIDS sidecars；个体化 warped-template MRI `.nii` 在 derivatives | 论文；ZIP 内实际目录/EEG header 配对尚未查看；不是原始可识别 MRI |
| 处理状态 | MEG MaxFilter/tSSS、降采样与匿名化；未额外做清理/伪迹剔除；不提供眼眨/运动伪迹标注 | 按论文陈述；需自行质量控制 |
| **数据许可** | **CC BY 4.0** | 仓储 v2.2 `termsOfUse` 的 Custom Dataset Terms 明确链接 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；API `license` 为空不能解释为无许可 |
| 文章/代码许可 | 文章 **CC BY-NC-ND 4.0**；官方 GitHub 代码 **GPL-3.0** | [文章许可](https://creativecommons.org/licenses/by-nc-nd/4.0/) 与[代码 LICENSE](https://github.com/mccorsi/NETBCI_data/blob/main/LICENSE)；三种许可作用域不同，本项目不复制 GPL 源代码 |
| 访问状态 | v2.2 列出的 6 个文件均 `restricted=false`；4 个小文件实际读取成功 | 不能等同于大型归档下载/解压/信号读取已验证 |

### 下载入口与规模

原论文报告完整数据约 **64 GB**（每人 EEG/MEG/warped MRI 平均约 3.3 GB）。仓储 v2.2 实际列出的压缩下载总量为 **49,394,064,394 bytes（约 49.39 GB / 46.00 GiB）**；论文规模与 ZIP 压缩体积不是同一计量口径，不需将其中之一改写为错误。大型文件没有下载。

| 文件 | 官方稳定 URL | 元数据大小 |
| --- | --- | --- |
| `Archive.zip` | https://entrepot.recherche.data.gouv.fr/api/access/datafile/744565 | **49,016,733,269 bytes**；MD5 `e7324cd60c711713dc6bf62ac70aedf8` |
| `derivatives.zip` | https://entrepot.recherche.data.gouv.fr/api/access/datafile/744564 | 377,315,650 bytes；warped MRI 等 derivatives |
| `dataset_description.json` | https://entrepot.recherche.data.gouv.fr/api/access/datafile/743365 | 1,064 bytes；实读 |
| `participants.json` | https://entrepot.recherche.data.gouv.fr/api/access/datafile/758595 | 4,700 bytes；实读 |
| `participants.tsv` | https://entrepot.recherche.data.gouv.fr/api/access/datafile/758600 | 8,644 bytes；实读 |
| `README` | https://entrepot.recherche.data.gouv.fr/api/access/datafile/743364 | 1,067 bytes；实读 |

公开入口是单个约 49 GB 的 Archive ZIP，本轮未发现并验证可直接单独下载受试者信号的接口。后续下载前应检查磁盘、预计解压空间、ZIP 内文件列表与是否支持受控分段读取，不自动拉取完整归档。

### 真实反馈、事件与行为字段

**已确认（论文）存在真正的在线反馈训练过程**：每个 session 的无反馈校准后，在线 LDA 使用所选 channel/frequency 特征控制光标，反馈时段为 trial 第 3–6 s；MI 对应 up target，rest 对应 down target。首秒为 ISI，随后 5 s target presentation。在线特征使用 0.5 s 窗、每 28 ms 更新的 autoregressive/Maximum Entropy 功率；每个 session 重新选择特征并校准分类器。因此历史在线行为成绩不能被称作“全程固定解码器下的学习效果”。

**已确认（论文）事件表定义**：`_events.tsv` 描述 trigger onset、data sample、trigger channel、trigger value，并由 `event_type` 描述触发含义。**已确认（官方脚本）** [BIDSify.py](https://github.com/mccorsi/NETBCI_data/blob/main/scripts/bidsify/BIDSify.py) 使用 `event_dict={"MI":1,"Rest":2}`。这只是公开转换脚本的映射，**初始审计尚未核查 Archive 事件；后续已核查 sub-01 全部 24 run，结果见第 0 节。未核查其他受试者及逐 trial 行为日志**。脚本注释中还提及相对 target onset 的 0–5 s 与结果时段，不能代替对归档事件的检查。

**已确认（实读小文件）participants TSV**：一行对应一名受试者；含 age/sex/hand、Rosenberg 自尊、EMG28 动机分量表、VMIQ2 三种运动想象能力、各 session `STAI_YA` 焦虑、`BCI-Performance-session1..4`、`ChannelFreq-Features-session1..4`。BCI performance 单元格为 6 个 run 百分比的列表，字典明确含义为每个 run 光标击中目标的 trial 百分比。**不是每个 trial 的 hit/miss、分类输出或光标轨迹。** 应以实际列名为准（官方表格/字典对 `STAI-YA` 与 `STAI_YA` 存在命名差异）。

论文也描述 session 间每日 10 min 的无反馈在家视频练习；**练习是否完成、剂量、依从性与家庭练习效果日志本轮未知**。四个 session 展示训练过程，不等于独立的训练后无练习保持测试。

实读发现的接入风险：

- `participants.json` 含 trailing commas；严格 `json.loads` 失败（line 26）。`dataset_description.json` 含未转义控制字符；严格 JSON 解析失败（line 18）。下载内容 MD5 与仓储完全匹配，所以不能归因为本地传输损坏。
- `dataset_description.json` 使用嵌套配置式结构，不能仅凭名称认定它是标准 BIDS 根文件；实际 Archive 中根文件仍待核查。不得宣称已通过 BIDS validator。
- 样本 BCI percentage 列表包含 3.57% 附近的步进；是否有排除试次、评分分母如何定义，需核对原始日志/作者说明。不能按设计每 run 32 trial 强行反推出逐 trial 行为。
- 数据匿名化、事后 BIDS 转换、已降采样/MEG MaxFilter 应记录为处理历史；不存在纯未处理 MRI 或完整原始采集的保证。

## 4. 研究问题能支持到哪一步

| 拟检验主张 | A / SHU | B / NETBCI | 可报告边界 |
| --- | --- | --- | --- |
| 离线 few-shot 标签预算、跨 session 泛化、固定模型测试 | 支持；信号接入后按时间顺序实现 | 支持 EEG MI/rest 的离线重放；标签/事件需核查 | fixed/offline decoding；所有归一化、特征、模型与阈值仅用允许的 source/support 数据 |
| 跨日 neural dynamics / 表征稳定性 | 可做 MI epoch 表征变化；完整 rest/cue 可能缺失 | 可做前后静息、MI/rest、跨 run/day 的观察性变化 | neural dynamics / stability / association；避免暗示神经重组已被验证 |
| 神经指标关联真实反馈表现/训练阶段 | 没有已确认的行为或反馈指标 | 有真实反馈与 run-level hit-rate，可做受试者内/间关联 | 注意 session、特征重选、在线解码器重校准、疲劳与家庭练习等混杂 |
| 学得更快 / 更少 trial 获得人类控制技能 | 单独不支持 | 单独不支持某新方法的因果主张 | few-shot 模型 accuracy 是算法结果；需新闭环干预与适当对照 |
| 真实的减少校准负担 | 仅离线标签预算代理 | 原实验每 session 校准，不能证明本仓库方法的实际减负 | 写“离线校准标签预算”，不要写“用户校准时间已缩短” |
| retention / consolidation | 5 次采集不构成明确保持测试 | 4 次训练、有在家练习，无独立保持测试已确认 | next-session generalization 不等于人类学习 retention；需专门无反馈复测/延迟测试 |

统计单位应以受试者为主要独立单位，避免把 thousands of trials 当成独立人数。跨数据集共同发现可增加外部支持，但 A 的左右手与 B 的右手/rest 标签、反馈机制和预处理不同；不能未经设定就 pooled training 或比较绝对 accuracy。

## 5. 接入前必须完成的检查

1. **固定合法来源和版本**：第一优先级 B/NEMAR `nm000305 v1.0.0`，保存 DOI、manifest、许可、字节数和校验结果；原始 Dataverse v2.2 单独记录。A 状态 `pending author access`，等待作者合法访问，不再请求 `nm000288` 或尝试 ZIP 密码。
2. **最小真实信号门槛**：B 的 NEMAR `sub-1` 4 session × 6 run 已实读；本地适配器及原始 `.vmrk` 已验收；伪迹质量、全体一致性及原始 BrainVision `.eeg` 信号仍未验收。A 历史探针不等于当前原始接入完成。
3. **事件对齐验收**：B 使用实读 `right_hand/rest`、秒单位与 0 起点，保留 run 边界；反馈/结果事件未提供，记录缺失，禁止生成“合理”伪字段。A 的原始事件单位矛盾仍待作者明确。
4. **行为数据使用**：B 将 run-level 百分比保留为源向量位置；其与具体EEG run尚未验证。可按明确subject/session聚合六个百分比并关联EEG会话，禁止广播后当成逐 trial 标签或 pooled hit率；真实 trial-level hit/miss 必须由原始日志或可靠事件证据证明。A 不创建反馈命中率。
5. **数据质量与无泄漏**：检查参与者/session 完整性、伪迹、类别计数、时间顺序、删除 trial 的偏差；以 source 训练、target support 校准、target query 测试的隔离评估为准，报告标签预算与随机种子，不用 query 拟合 scaler/选择窗口/阈值。
6. **主张验收**：离线 smoke/synthetic 数据只验证代码路径；真实数据分析之后才填写结果。人类学习、保持与部署结论需要独立证据，不能从 offline accuracy 倒推。

## 6. 来源索引

以下均于 2026-10-09 核查；官方大型信号归档的实际内容尚未查看，NEMAR 单受试者 EDF 已读取。

- B NEMAR 官方入口：https://www.nemar.org/dataset/nm000305
- B NEMAR 数据 API：https://data.nemar.org/nm000305/
- B NEMAR 固定版本 DOI：https://doi.org/10.82901/nemar.nm000305.v1.0.0
- B NEMAR metadata：https://data.nemar.org/nm000305/metadata.json
- B NEMAR 固定版本 manifest：https://data.nemar.org/nm000305/v1.0.0/manifest.json
- B NEMAR dataset description：https://data.nemar.org/nm000305/v1.0.0/dataset_description.json
- B NEMAR README：https://data.nemar.org/nm000305/v1.0.0/README.md
- B NEMAR 来源 provenance：https://data.nemar.org/nm000305/v1.0.0/sourcedata/sourcedata_provenance.json
- B MOABB 上游 loader：https://github.com/NeuroTechX/moabb/blob/develop/moabb/datasets/netbci2026.py；审查时 Git blob `8bb3227e06418642a48af2b22ac2e05615e12a4d`，声明 `right_hand=1/rest=2`，不等于 NEMAR 导出的存储数值

- A 原论文：https://www.nature.com/articles/s41597-022-01647-1
- A 原始数据 DOI：https://doi.org/10.6084/m9.figshare.19228725.v1
- A 最新数据 DOI：https://doi.org/10.6084/m9.figshare.19228725.v3
- A 最新发布元数据：https://api.figshare.com/v2/articles/19228725
- A v1 发布元数据：https://api.figshare.com/v2/articles/19228725/versions/1
- A README/events/EEG 小文件：见第 2 节稳定下载 URL。
- B 原论文：https://www.nature.com/articles/s41597-026-08237-5
- B 官方正文 PDF：https://www.nature.com/articles/s41597-026-08237-5_reference.pdf
- B 数据 DOI：https://doi.org/10.57745/RBJRC7
- B 发布元数据：https://entrepot.recherche.data.gouv.fr/api/datasets/:persistentId/?persistentId=doi:10.57745/RBJRC7
- B 发布页/Custom Dataset Terms：https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/RBJRC7
- B 官方代码与 README：https://github.com/mccorsi/NETBCI_data
- B 事件转换脚本：https://github.com/mccorsi/NETBCI_data/blob/main/scripts/bidsify/BIDSify.py
- B participants/description/README 小文件：见第 3 节稳定下载 URL。

## 2026-10-10 后续证据

见[stage1完整报告](netbci_stage1_evidence_and_decision.md)：169文件重验、717事件清单、原始匿名scans、两个ZIP目录审计和behavior verified-grain表。Subject/session成绩字段可定位，具体run顺序/分母和trial结果仍unresolved。实际新增CPU探索性表征与最小冻结baseline；未扩大全队列信号、未破解SHU、未修改第一篇仓库。

已有行为数据已继续分析，见[会话级报告](netbci_behavior_session_analysis.md)：19人的456成绩均完整，
仅sub-1的4个EEG会话可靠关联。无需以联系作者作为取得既有成绩的前置步骤；run/trial细节的限制仍保留。
