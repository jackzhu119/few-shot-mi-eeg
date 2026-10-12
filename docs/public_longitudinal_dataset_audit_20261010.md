# 公开纵向 MI-EEG 扩展来源审计（2026-10-10）

核查日期采用 Asia/Shanghai；检索截止 2026-10-10。本轮接续十人任务后寻找扩大
**参与者数、跨日覆盖、真实反馈与外部验证**的公开来源。优先完成 NETBCI 的剩余九人，
其次接入 Kumar2024，再分阶段验证 Stieger2021、Yang2025 和 OpenBMI。
“最新发布”“人数最多”“与技能学习最相关”是三个不同指标，不能用数据体积替代证据质量。

本审计实际读取官方仓储/API、固定版本 manifest、根文件和每库一组事件/通道 sidecar；
还校验了 Kumar 全部 360 个事件 TSV。**本子任务未下载新库 EEG 信号、未拟合模型，
HEAD 成功不等于信号读取或模型训练验收。** 下载与分析的后续完成情况应另看各库执行收据。
原十人分析结果和配置保留，不将新增数据追溯称为原十人预设样本。

完整机器源表见 [longitudinal_sources.json](../research_logs/public_data_expansion_20261010/longitudinal_sources.json)，
网络状态、官方响应 SHA256 和 manifest 清点见
[longitudinal_receipts](../research_logs/public_data_expansion_20261010/longitudinal_receipts/)。

## 推荐次序与实际覆盖

“已列信号”人数按固定 manifest 的 subject/session 文件路径清点；它不代表已读取信号或独立生物学重复。
下面的大小均为十进制 GB，信号与完整仓储总量分开，不累计重复镜像。

| 优先级与来源 | 已核实或论文陈述的范围 | 格式、大小和本轮访问 | 对本论文的作用与限制 |
|---|---|---|---|
| 1. [NETBCI2026](https://www.nature.com/articles/s41597-026-08237-5)，[NEMAR nm000305 v1.0.0](https://data.nemar.org/nm000305/) | manifest 19 人、76 人会话、456 EDF；当前十人之外尚有九个编号。74 EEG、250 Hz、右手 MI/rest | 全部 EDF 3.879 GB，整个 manifest 3.884 GB；官方 HTTPS/校验可用，数据 CC BY 4.0 | 首先完成同源队列和现有行为 join；每会话在线模型重校准、无明确撤回/延迟无辅助 probe，不支持候选算法保留技能的因果结论 |
| 2. [Kumar2024](https://doi.org/10.1093/pnasnexus/pgae076)，[nm000177 v1.0.5](https://data.nemar.org/nm000177/) | manifest 18 人、108 人会话、360 EDF；六日会话（一次离线校准、五次在线），22 EEG、512 Hz、左右手 MI；GR/PAR 各九人由原研究说明 | EDF 1.779 GB；去重选择含 sidecar/provenance 共 1.781 GB；全仓储 15.493 GB 包含上游重复。NEMAR 信号 HEAD 200；NEMAR 与 [原始 Zenodo](https://zenodo.org/records/10694880) 数据均 CC BY 4.0 | 首个独立外部纵向库。NEMAR 仅 bar task，原始另有 racing；不能把标签 TSV 当 hit/miss，不把历史两组当本仓库随机试验 |
| 3. [Stieger2021](https://www.nature.com/articles/s41597-021-00883-1)，[原始 Figshare v1](https://api.figshare.com/v2/articles/13123148) | 原始文件名实数 62 人、598 会话：41 人各 11、21 人各 7；论文报告 >600 小时、>250,000 trials，在线一维/二维光标，含轨迹和 TrialData | 598 MAT+README 共 376.894 GB；[nm000339 v1.0.4](https://data.nemar.org/nm000339/) 列同样 62/598，BDF 信号 398.831 GB。原始数据 CC BY 4.0，NEMAR 元数据另写 CC-BY-NC-4.0 | 大样本真实学习过程最有价值；应按参与者/会话按需取用，不能全量堆进当前 CPU 内存。原始 mindfulness 干预、停顿和反馈需保留；不是本算法的无辅助保持实验 |
| 4. [Yang2025 / WBCIC-SHU](https://www.nature.com/articles/s41597-025-04826-y)，[Figshare+ v5](https://api.figshare.com/v2/articles/22671172) | 论文 62 人×3 日：51 人左右手、11 人三类；59 原始 EEG，处理后 58，1000 Hz。两个 NEMAR 镜像都只列 51 人/153 会话 | 原始 ZIP 65.631 GB；[nm000246 v1.0.0](https://data.nemar.org/nm000246/) 信号 62.731 GB，[nm000348 v1.0.5](https://data.nemar.org/nm000348/) 信号 68.046 GB；CC BY 4.0 | 大样本跨日外部验证；选择单一版本，二镜像不能算 102 人。采集在 2019 年、文章在 2025 年，区别于既有受阻 Ma2022 SHU；没有核实逐 trial 在线成功/保持 |
| 5. [Lee2019 / OpenBMI](https://doi.org/10.1093/gigascience/giz002)，[GigaDB DOI](https://api.datacite.org/dois/10.5524/100542) | [nm000338 v1.0.5](https://data.nemar.org/nm000338/) 实数 54 人、108 人会话、216 BDF；两日左右手 MI、62 EEG+4 EMG、1000 Hz | BDF 65.266 GB；全仓储 130.116 GB 含 108 原始 MAT 重复。原始 DataCite 权利为 CC0-1.0，NEMAR 元数据写 GPL-3.0，范围不能混写 | 适合较大训练主体和跨日泛化；两个 session 不构成学习/保持试验。保留 train/test acquisition 和 EMG，不能把 ERP/SSVEP 同一参与者另算新人 |
| 6. [Forenzo2023](https://doi.org/10.1109/TBME.2023.3298957)，[原始 KiltHub/Figshare](https://api.figshare.com/v2/articles/23677098) | 原始说明 25 人×5 会话、2,025 runs，MI 与 overt spatial attention/MIOSA；64 EEG、1000 Hz，含 targets/event/outcomes | 25 subject ZIP+说明共 94.186 GB，CC BY 4.0；[nm000209 v1.0.4](https://data.nemar.org/nm000209/) 派生仅 25 人×2 会话、150 BDF、5.252 GB | 原始可研究反馈与注意条件，不能把二日 derivative 称完整五日。MI、视觉空间注意和混合条件必须分开；原始事件/行为尚未实读 |
| 7. [Forenzo2024 连续追踪](https://www.nature.com/articles/s41597-024-04090-6)，[原始数据](https://api.figshare.com/v2/articles/25360300) | 论文 28 独立人、两个各 14 人子研究、4 或 8 会话、约 168 小时；不同传统/DL decoder 与二维连续目标 | 28 subject ZIP+说明共 130.013 GB，CC BY 4.0 | 可加强连续控制的外部相关性，但这不是固定左右手离散 cue 分类；应采用轨迹误差/连续控制端点，不能生成伪类别标签或直接合并 BA |
| 8. [Alawieh2025 / TESS](https://doi.org/10.1073/pnas.2418920122)，[Zenodo v1](https://zenodo.org/records/15454355) | 25 健康+2 SCI；主组 20（TESS/Rest 各十）、single-pulse 五；四名 crossover 是原 Rest 人群的重复，非新增四人。512 Hz，32/64 EEG | 五 ZIP 共 18.288 GB，其中 MRI 0.078 GB；CC BY 4.0。正文与条目记录在线反馈、随访和结果字段，原始文件未实读 | 与神经训练/随访高度相关，但刺激是不同干预。当前 MOABB 只载一次离线 cue session，遗漏 online 和 d2 随访；保留原始纵向时间，不将刺激组效应称 decoder-policy 效应 |
| 9. [Wang/Liu2026 临床随访](https://www.nature.com/articles/s41597-026-07787-y)，[Figshare v11](https://api.figshare.com/v2/articles/30509165) | 2026-07-30 文章；24 卒中患者、14 BCI/10 conventional；前/后/一个月随访，19 完成全部三期、五缺随访；rest、affected-hand、sixth-finger MI | 11 文件共 8.687 GB，raw SET/FDT、processed MAT 和临床侧表，CC BY 4.0；固定 v11 元数据可读 | 最新有实际随访的独立临床候选；八次治疗不等于八个公开训练 EEG session。任务、偏瘫侧和临床干预须单独建模，随访分类/疗效不是本算法保持技能的因果证据 |
| 10. [BCI IV 2a / BNCI2014-001](https://bnci-horizon-2020.eu/database/data-sets) | 原始九人×两日、22 EEG+3 EOG、250 Hz；四类（左右手/feet/tongue）。[nm000139 v1.0.3](https://data.nemar.org/nm000139/) 实数九人/18 会话/108 BDF | 派生信号 0.692 GB，含原始 MAT 总 1.485 GB；官方数据 CC BY-ND 4.0 | 成熟小型可复现跨日基准；左右手子任务可比较，不能声称训练保持，也不复用第一篇的现成结果 |
| 11. [BCI IV 2b / BNCI2014-004](https://bnci-horizon-2020.eu/database/data-sets) | 原始九人×五会话、三 bipolar EEG、250 Hz、左右手；前两无反馈、后三有反馈。[nm000135 v1.0.3](https://data.nemar.org/nm000135/) 派生仅一人/五会话，但 sourcedata 列完整 18 个 B01–09 T/E MAT | 一人 BDF 0.024 GB；完整 manifest 0.502 GB。CC BY-ND 4.0 | 采用原始九人并审计 T/E 内 session 边界；三 bipolar 导联不能套用 NETBCI 的 73 维 CAR geometry，镜像不补出不存在的通道 |
| 12. [BNCI2015-001](https://bnci-horizon-2020.eu/database/data-sets) | 官方十二人，八人两会话、四人三会话；[nm000140 v1.0.2](https://data.nemar.org/nm000140/) 实数十二人/28 会话；13 EEG、512 Hz、right_hand/feet、在线自校准/再适应 | BDF 信号 1.203 GB、全仓储 3.043 GB；CC BY-NC-ND 4.0 | 可验证不同历史 decoder 更新条件的观察性关联；任务不是左右手，日期语义与行为须进一步核验 |

## 已发现的重复、差异和接入阻断

1. NEMAR 版本创建于 2026 年不表示采集于 2026 年。版本时间字段未注明时区时保留原字符串；
   精确采集日期/间隔只使用原研究日志，不把版本时间当训练时间。
2. Yang 的两个镜像是同一 51 人子集；OpenBMI 的三个 paradigms 是同一 54 人；
   每个数据集的 raw/processed/derivative、同一人的多会话和 TESS crossover 都不增加独立人数。
   Stieger 原论文的 62 人与后来解码文章选择的 61 人不能混称。不同研究之间是否有人重叠尚未知，
   不报告未经验证的 pooled 独立总 n。
3. Stieger 原始 CC BY 与 NEMAR 的 CC BY-NC、OpenBMI 原始 CC0 与 NEMAR GPL 元数据不一致。
   各自按具体来源记录，优先原始权利登记；在未明确 derivative 许可范围前，不再发布变换后的数据。
   文章、工具代码和数据的许可证分别保存。
4. NEMAR 每库代表信号 HEAD 返回 200 且 Content-Length 与 manifest 的代表条目相符。
   Figshare 五个代表大文件的 HEAD 返回 403；这只说明该探测方法未通过，可能与签名/请求方法有关，
   **不能据此称原始数据需付费、被限制或 GET 无法下载**。仓储公开 API 与文件/校验字段已可读。
   已保留失败收据，不反复请求或下载巨大归档。Zenodo 原始 Kumar ZIP 的 HEAD 200。
5. 不重试 Ma2022 SHU / nm000288 的受阻接口，不索取或破解 ZIP 密码。
   Yang2025 是另一个合法公开来源，不以历史 SHU 版本绕过当前授权说明。

## Kumar：可直接复核的第一批下载计划

[选择清单](../research_logs/public_data_expansion_20261010/kumar2024_nm000177_v1.0.5_selection_manifest.json)
保存固定版本每个必要条目的 path/bytes_url/size/checksum_algorithm/checksum，
[接入计划](../research_logs/public_data_expansion_20261010/kumar2024_ingestion_plan.json)保存来源和许可。
2,705 个必要文件、1,781,052,841 bytes，包含 360 EDF、所有 subject sidecar、四个根文件及
`sourcedata_provenance.json`，不下载其余重复上游文件。选择清单 SHA256：
`377eb25e0938fde905b023a309b8b7adebd1a4779fd48c3d2a2d6ce22cb16750`。
完整官方 manifest SHA256：
`1fe0fe2dbf002614dc38c54b5cd25fcb68b65c6c18b348343307d9d4668d420f`。

360 个事件 TSV 已与官方 Git blob 校验一致：7,200 条源事件、左右手各 3,600；
7,156 条 duration=5 秒，44 条较短，最短 4.146484 秒。不能沿用 NETBCI 的固定 5 秒矩阵
并填充/延长事件；应先完成 EDF 单位、有限值、完整边界与 annotation 对齐，再在新库模型拟合前
锁定适合本库的统一窗口、排除规则和全部原始身份记录。当前这个事件清点不是 EDF 边界验收。

`participants.tsv` 中 age 均为 2020，明显不应当成人的年龄。2026-10-11 完整下载实读
确认原文件为真实制表符/换行，不含字面转义分隔符；此前元数据呈现中的转义不是源文件损坏。
详见 [完整接入审计](kumar2024_ingestion_audit_20261011.md)。论文提供的年龄分布不替代每人的实际年龄。不能按其通用 `group=healthy`
推断 GR/PAR；应追溯原始 subject 目录/provenance。bar-only 事件文件是任务标签，不是命中率。
原论文另有 [正式勘误](https://doi.org/10.1093/pnasnexus/pgae137)，引用方法和既有结果时一并核查。

## 本轮扩展能改善什么

第一层是扩充同源 NETBCI 样本、报告逐人/逐会话有效计数及重复信号。
第二层是 Kumar、Stieger 等独立来源的冻结模型跨日性能、任务信息与 geometry 敏感性复核。
第三层是原始闭环行为或临床随访的来源特定关联；其事件语义和结果日志另行验收。
训练与外部评估数据预先隔离：每库用独立参与者 ID，按时间划分，不把外部 test 会话用于
scaler/PCA/CSP、窗口、阈值或模型选择，不把同一人的 derivative 放进另一个分区。

左右手、right_hand/rest、right_hand/feet、连续二维追踪和患者 affected-hand/sixth-finger
不是可互换标签。可分别估计效应、再按可比科学端点做跨库综合；不能未经协议把原始张量
拼接训练并以更大的 trial 数声称独立样本更多。更多 offline 样本可加强模型泛化的证据，
更多真实反馈可加强训练关联；二者仍不能证明新 decoder policy 保留了无辅助长期技能。

## 已检索但不优先进入共同 MI 训练的较新 BNCI 来源

官方 BNCI 当前目录还列 2024-001（20 人手写字母）、2025-001（20 人实际 reaching 的
速度/距离/方向）和 2025-002（连续 attempted movement、反馈比例变化）。年份编号不是
纯 MI 的保证。[2025-002 文档](https://moabb.neurotechx.com/docs/generated/moabb.datasets.BNCI2025_002.html)
与官方目录还出现 10/20 人及“只有两人可用”的不一致，实际可下载覆盖未完成验收。
这些来源适合另外的 motor execution/attempted movement 问题，不能冒充同构左右手 MI 大库。
