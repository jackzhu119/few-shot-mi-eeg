# NETBCI 全 19 个发布身份扩展（2026-10-11）

已完成真实源审计、拟合和汇总范围：19 个**发布身份**、76 个会话、
456 个 EDF runs，来源 14,431 个事件，其中
14,429 个完整 5 秒事件纳入张量，2 个短来源事件保留明确排除。
`participants` 历史字段是发布编号数量，不是已证实独立的生物学参与者数。

来源数值审计在模型拟合前完成：456 个 EDF 全信号与全部来源任务窗口检查，
官方实际文件校验全部匹配。发现 30 个连续信号副本组、
909 个任务窗口副本组。跨编号 affected union 为 **sub-1, sub-6, sub-7, sub-15, sub-17**。
原始 BrainVision EEG 未实读，正确分配与重复原因未知。逐会话 pairwise 内容关系如下，
同一多方副本组可以出现在多行，因此此表不能求和当成独立重复组：

| Identity/session | Exact copied identity/session | Paired runs |
| --- | --- | --- |
| sub-1/ses-01 | sub-17/ses-01 | 6 |
| sub-1/ses-02 | sub-17/ses-02 | 6 |
| sub-1/ses-03 | sub-17/ses-03 | 6 |
| sub-1/ses-04 | sub-17/ses-04 | 6 |
| sub-1/ses-04 | sub-7/ses-01 | 6 |
| sub-1/ses-04 | sub-7/ses-02 | 6 |
| sub-1/ses-04 | sub-7/ses-03 | 6 |
| sub-15/ses-01 | sub-6/ses-01 | 6 |
| sub-17/ses-04 | sub-7/ses-01 | 6 |
| sub-17/ses-04 | sub-7/ses-02 | 6 |
| sub-17/ses-04 | sub-7/ses-03 | 6 |

全 19 编号结果保留为算术诊断。另存来源驱动敏感性同时排除每个跨编号连续信号**或任务窗口**
副本组的全部成员，保留 14 个编号：sub-2, sub-3, sub-4, sub-5, sub-8, sub-9, sub-10, sub-11, sub-12, sub-13, sub-14, sub-16, sub-18, sub-19。没有选择一个“正确”副本，没有依据效果方向筛选，
没有覆盖十编号或全编号输出、重新拟合或改变参数。**未发现 exact 跨编号复制不等于验证生物学独立**。
本扩展已见十编号结果与既有 19 人行为，属于观察后探索分析，不是外部确认。

## 数值结果

下表均为 ses04−ses01；均值的 95% percentile interval 对完整发布身份轨迹重采样
10,000 次，seed42。全编号 EEG 区间不支持独立参与者推断；来源排除区间仍以来源和身份真实性未验证为限制。
在线成绩是六个已发布百分比的等权均值，不是 pooled hit rate。

| Metric | All-ID arithmetic change [95% interval] | Source restriction change [95% interval] | Unit |
| --- | --- | --- | --- |
| 公开在线成绩 / Published online score | +14.568 [10.706, 18.266]; n=19 | +15.410 [11.526, 19.332]; n=14 | pp |
| 冻结 CSP+LDA BA / Frozen CSP+LDA BA | -4.676 [-11.884, 2.333]; n=19 | -4.202 [-11.413, 2.711]; n=14 | pp |
| Mu MI−rest 任务窗 / Mu MI−rest task-window contrast | -0.525 [-1.017, 0.038]; n=19 | -0.529 [-1.009, -0.058]; n=14 | dB |
| Beta MI−rest 任务窗 / Beta MI−rest task-window contrast | -0.261 [-0.562, 0.045]; n=19 | -0.275 [-0.640, 0.100]; n=14 | dB |

在线成绩、离线固定读取与表征是不同端点。不能把 BA 下降推断为人的技能丢失，不能把
Mu/Beta 任务窗口变化直接推断为经典 baseline ERD、神经学习或保持。

## 模型、窗口、QC 与缺失

每人 ses01/run01–04 唯一拟合粗 QC、scaler、reference PCA 和 CSP+LDA；run05–06 为按 ID
分开的 query。ses02 是不选择参数的 validation 描述，ses03/04 为探索评估；另用数值内容审计
核对 ID 不相交以外的复制。各模型记录训练 trial IDs、状态前后 hash、单次 fit 和 exact 预测重放。
74 个有序公共 EEG 通道、250 Hz、V；全公共通道 CAR，73 维 Helmert 坐标；5% trace shrinkage、
PCA10、CSP4。任务窗裁剪 0.5–4.5 秒、ROI C3/Cz/C4、Mu 8–13/Beta 13–30 Hz、Welch 250/125；
先求每 run 的 trial log-power 均值，再对 run 等权。没有验证事件前基线。

固定匹配每类/run 12 个 trial：六-run144/session、QC 共同 run03–06 为96/session，每人先平均10次抽样。
保留编号的 matching 可用数为六-run 14/14、QC四-run
9/14。不足时保留 unavailable，不降低阈值、不删参与者。
全编号保留粗 QC 标记 456 个；至少一次恒预测的编号
10/19；科学失败记录 26 条。
500 次每人 run-bootstrap 是条件变异，10 个匹配 seeds 均不增加独立样本量。

Unavailable records: sub-8/qc_common_four_runs: Insufficient preset matched cells: [{"session": "01", "run": "05", "label": "rest", "n_available": 11, "n_required": 12}, {"session": "01", "run": "06", "label": "rest", "n_available": 8, "n_required": 12}]; sub-11/qc_common_four_runs: Insufficient preset matched cells: [{"session": "02", "run": "06", "label": "rest", "n_available": 11, "n_required": 12}]; sub-13/qc_common_four_runs: Insufficient preset matched cells: [{"session": "04", "run": "04", "label": "rest", "n_available": 2, "n_required": 12}, {"session": "04", "run": "04", "label": "right_hand", "n_available": 3, "n_required": 12}, {"session": "04", "run": "05", "label": "rest", "n_available": 3, "n_required": 12}, {"session": "04", "run": "05", "label": "right_hand", "n_available": 5, "n_required": 12}, {"session": "04", "run": "06", "label": "rest", "n_available": 1, "n_required": 12}]; sub-14/qc_common_four_runs: Insufficient preset matched cells: [{"session": "02", "run": "04", "label": "rest", "n_available": 11, "n_required": 12}, {"session": "02", "run": "05", "label": "rest", "n_available": 11, "n_required": 12}, {"session": "02", "run": "06", "label": "rest", "n_available": 1, "n_required": 12}, {"session": "02", "run": "06", "label": "right_hand", "n_available": 8, "n_required": 12}]; sub-19/qc_common_four_runs: Insufficient preset matched cells: [{"session": "02", "run": "03", "label": "rest", "n_available": 2, "n_required": 12}, {"session": "02", "run": "03", "label": "right_hand", "n_available": 5, "n_required": 12}, {"session": "04", "run": "03", "label": "rest", "n_available": 7, "n_required": 12}, {"session": "04", "run": "03", "label": "right_hand", "n_available": 6, "n_required": 12}, {"session": "04", "run": "04", "label": "rest", "n_available": 4, "n_required": 12}, {"session": "04", "run": "04", "label": "right_hand", "n_available": 1, "n_required": 12}, {"session": "04", "run": "06", "label": "rest", "n_available": 8, "n_required": 12}].

实际短事件（不补齐、延长或伪造行为标签）：

- `sub-3/ses-01/run-03/tsv-row-31`: duration=2.968 s; source_event_duration_does_not_match_fixed_window.
- `sub-12/ses-02/run-02/tsv-row-32`: duration=4.976 s; source_event_duration_does_not_match_fixed_window.

来源审计保留的同编号同会话任务窗口重复 flag 共 0 个会话，其中保留编号
0 个会话。它们与跨编号复制分开记录。
本次 planned-partition 数值审计未在保留编号发现来源→后续 query exact 内容重合；这不排除非 exact 泄漏或未知来源错误。
完整位置和源→query 数量见 compact 的 `same_subject_session_task_repeat_flags` 与
`planned_partition_content_overlap`；不以官方 SHA 匹配代替来源独立。

## 来源限制后的探索关联

先计算每个保留编号 ses04−ses01 变化，只重采样完整变量对；不把 56 会话行作为独立 n。
五对指标、Pearson/Spearman、10,000 次/seed42 沿用原估计器；不可用身份和退化重采样均保留。
不报告 p 值或机制、mediation、因果学习结论。

| Association | Estimator | Estimate | 95% interval | Complete paired IDs | Degenerate draws |
| --- | --- | --- | --- | --- | --- |
| BA_change_vs_behavior_change | Pearson_r | 0.272 | [-0.478, 0.668] | 14 | 0 |
| BA_change_vs_behavior_change | Spearman_rho | 0.079 | [-0.603, 0.639] | 14 | 0 |
| Mu_change_vs_behavior_change | Pearson_r | -0.344 | [-0.784, 0.166] | 14 | 0 |
| Mu_change_vs_behavior_change | Spearman_rho | -0.473 | [-0.794, 0.070] | 14 | 0 |
| Mu_change_vs_BA_change | Pearson_r | -0.197 | [-0.689, 0.326] | 14 | 0 |
| Mu_change_vs_BA_change | Spearman_rho | -0.227 | [-0.762, 0.394] | 14 | 0 |
| all_six_runs_AIRM_session04_vs_BA_change | Pearson_r | -0.145 | [-0.598, 0.424] | 14 | 0 |
| all_six_runs_AIRM_session04_vs_BA_change | Spearman_rho | -0.249 | [-0.709, 0.369] | 14 | 0 |
| all_six_runs_PCA_session04_vs_BA_change | Pearson_r | 0.339 | [-0.336, 0.771] | 14 | 0 |
| all_six_runs_PCA_session04_vs_BA_change | Spearman_rho | 0.255 | [-0.400, 0.769] | 14 | 0 |

## 出处、复核与可重运行成果

固定 derivative DOI [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)，
CC BY4.0；原行为 Dataverse v2.2 [10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7)。
正式扩展时机与固定参数见 [扩展协议](netbci_all19_expansion_protocol_20261010.md)。
全部来源、排除、冻结模型及统计 receipt 可重查；完整数值 ledger 本地单独保留。
R2 实际同步、上传接收和 full GET 验证状态另见逐文件存储收据，HEAD/ETag 不当成内容 hash 证明。

| Source | Path | SHA-256 |
| --- | --- | --- |
| all19 config | `configs/netbci_cohort_all19_20261010.json` | `d3de923978079cff7199c294f704a0282d3df589899df1a7f44578a5aabd2bf5` |
| official pinned manifest | `research_logs/netbci2026_sources/manifest.json` | `7e50f5281e91bec97791a84f5f3dbe20dc443b37c10d4bc6bcda96bed08c092c` |
| compact numeric audit | `research_logs/netbci_cohort_all19_20261010/numeric_signal_identity_summary_v2.json` | `3b5c282877c256ac95ba0f60a04592c302f3b2a17c298c4be482697ce41232ae` |
| full numeric audit (local; R2 receipt separate) | `research_logs/netbci_cohort_all19_20261010/numeric_signal_identity_v2.json` | `d1c4d267baa0a6c0803037db731ebd571f0aa65be9d4d1932e3d9c237815ef45` |
| all-ID summary receipt | `research_logs/netbci_cohort_all19_20261010/summary_run01/summary_receipt.json` | `2e3ac733fbcea87dcef012e9bd3acc2bddaf4436c2a5e59ed0b9c625a0bb28da` |
| restricted summary receipt | `research_logs/netbci_cohort_all19_20261010/independence_sensitivity_run01/sensitivity_receipt.json` | `464c8d0eedd2e6cc36394bed26ccf3948192c419b90db50feb2f4bf5768dcf56` |

可编辑 native figures 位于 `notebooks/netbci2026_all19_20261011.ipynb`，HTML 同名导出。
生产表和生成图在 `research_logs/netbci_cohort_all19_20261010/summary_run01`；来源敏感性在 `research_logs/netbci_cohort_all19_20261010/independence_sensitivity_run01`。
独立方法审计与 bootstrap 重算在该扩展日志目录单独保留；生产报告不代替独立复核。

H1/H2 的当前证据是固定读取、任务窗口和几何的观察性描述；within-session run AIRM 不等于
测量可靠性，跨编号结果不等于生物学重复。H3/H4 的干预归因、人的无辅助同 mapping 保持和
延迟 retention、新算法与外部独立确认均仍未完成。公共训练资源接入单列，不混入本纵向分析人数。
