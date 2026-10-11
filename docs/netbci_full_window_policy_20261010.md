# NETBCI 固定五秒窗的源事件保留与分析资格

日期：2026-10-10。本记录是读取新数据后产生的显式方案修订，属于探索性分析。
原十人扩展的参与者、分区、匹配数、信号参数、模型和统计单位继续按
[扩展协议](netbci_cohort_expansion_protocol.md)执行。该修订不改变源数据，也不覆盖严格审计的失败记录。

## 触发证据

严格适配器在 `sub-3` 返回 `Variable epoch length requires an explicit policy`，失败收据保存在
`research_logs/netbci_cohort_resume_20261010/audits/sub-3/failure.json`。
随后独立读取十人全部 240 个源事件 TSV，得到 7,577 个实际源事件：7,576 个为五秒，
恰有一个 duration 不足五秒。这是源数据中的一个有效事件，不是缺失事件、缺失参与者或人为生成的试次。

| 字段 | 唯一短事件的实际值 |
| --- | --- |
| NEMAR subject / session / run | sub-3 / ses-01 / run-03 |
| TSV | sub-3/ses-01/eeg/sub-3_ses-01_task-imagery_run-03_events.tsv |
| TSV 数据行 | 31（不含标题行；不是从零起的数组索引） |
| 唯一事件 ID | sub-3/ses-01/run-03/tsv-row-31 |
| 类别 / 存储值 | rest / 1 |
| onset / start sample | 224.032 秒 / 56,008（从零起） |
| duration / 样点数 | 2.968 秒 / 742（derivative 250 Hz） |
| stop sample exclusive | 56,750 |

独立以 `preload=False` 读取该 EDF 的元数据与 annotation，确认 250 Hz、`n_times=56750`，
annotation 第 31 个事件同样为 rest、onset 224.032 秒、duration 2.968 秒。
真实 stop 正好位于录制末端；强行延长到 1,250 样点会得到 57,258，越过该 EDF 边界。
这个局部核验不等于十人完整信号审计已通过。

五秒事件的 TSV 普查数量按 sub-1..sub-10 为
717 / 767 / 764 / 768 / 765 / 768 / 726 / 766 / 767 / 768。
这些数量描述事件表，不能替代随后逐人的信号、EDF annotation、边界、通道和来源校验。
短事件形成的原因尚未确认，不由它推断原始采集错误、行为失败或学习表现。

## 显式资格规则

默认适配器继续拒绝变长窗。只有显式同时设置以下两项，才启用固定窗资格：

```json
{
  "fixed_window_duration_seconds": 5.0,
  "mismatch_action": "retain_source_event_exclude_from_fixed_window_tensor"
}
```

所有源事件先通过校验和、单位、采样对齐、正 duration、标签、事件映射、非重叠顺序、
录制边界和 EDF annotation 检查；完整连续信号仍需有限。五秒必须对应实际采样率下的整样点长度。
仅源 duration 对应精确五秒的事件进入矩形 `X`，按原始半开区间 `[sample, sample + duration × sfreq)`
读取。其他源 duration 的事件保留原始身份、onset、duration、样点和类别，设置
`fixed_window_eligible=false`，原因是 `source_event_duration_does_not_match_fixed_window`。

不填充、延长、截短、合成或删除源事件；不删除 sub-3；不按行为成绩或模型表现决定资格。
事件 ID 沿用原 TSV 数据行，排除后不重排为连续的新 trial 编号。
源 duration 不一致只涉及固定窗张量资格，不能被写成行为失败或模型失败。

## 输出与计数含义

新审计目录保存以下互相可核对的文件，并记录它们的 SHA256：

- `source_events.tsv`：全部实际源事件，包含资格和排除理由。
- `events.tsv`：进入保存的五秒 `epochs.npz` 的事件，逐行身份与张量一致。
- `excluded_events.tsv`：保留源事件中的固定窗不合格记录；没有排除时仍保存带标题的空表。
- `run_inventory.tsv` 和 `audit.json`：保留原始 run/session 的 `trial_count` 与 `class_counts`；
  另外报告 source、eligible 和 excluded counts，以及实际 duration 求和。
- `metadata.json`：适配器 provenance 内保留完整 `source_event_inventory`、资格规则和计数。

每人审计的 `summary.total_source_trials` / `source_class_counts` 是全部源事件，
`summary.total_trials` / `class_counts` 是进入张量的事件，
`summary.excluded_trial_count` / `excluded_class_counts` 是仅因 duration 不符而未进入张量的事件。
run/session 的 `eligible_trial_count` / `eligible_class_counts` 另列，不改写原始源总数。
队列汇总用 `total_source_trials`、`total_trials`、`total_excluded_trials` 分开报告。
`total_source_task_window_seconds` 对全部真实 duration 求和，
`total_exact_task_window_seconds` 对实际合格窗求和；不再以最小 duration 乘整 run 事件数。

按现有 TSV 普查预期，十人仍全部保留，源事件 7,577、五秒张量事件 7,576、仅一个 rest 事件
未进入张量。实际通过人数、通道与 NPZ 形状必须由新审计收据确认，不能提前认定为已通过。

## 时序与解释范围

本规则是在 sub-3 严格失败和完整事件表普查后制定，不是读取前冻结的资格规则或外部预注册。
保留原严格失败及旧两人审计，另用新配置、新审计目录和新 bundle 目录对全部十人执行一致资格。
后续指标仍使用原先固定的每 run 每类 12 trials、10 repetitions 及 QC 共同 run-03..06 的
96/session 方案；不足时报告 unavailable，不降低数量或删参与者。

五秒集合上的离线谱、几何和冻结解码结论依然是探索性描述，不能证明在线自主控制、人类技能保持
或算法干预的因果效应。行为关联仅使用已核验的 subject/session；run 顺序、命中率分母、trial outcome
仍为 unresolved，不因本次资格规则而得到额外验证。
