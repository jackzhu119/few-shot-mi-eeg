# 2026-10-11 历史接续快照

> 本文件保留十人完成和扩容进行中的历史状态；当前完成入口为
> [CHAT_HANDOFF_20261012.md](CHAT_HANDOFF_20261012.md)。

继续 /workspace/few-shot-mi-eeg、research/learning-preserving-bci，不重新初始化。
原 CHAT_HANDOFF_20261010.md 和 state.json 是历史冻结；旧聊天可获取的根对话、三张图片、
旧正式交接和 Git bundle 已保存在本地私有备份并上传 R2，已失效的子代理正文及工具截断
不冒称完整平台导出。

## 十人阶段真实完成范围

固定 NEMAR nm000305 v1.0.0，1,885 去重文件、2,049,560,417 bytes 官方校验通过；
10 发布身份、40 会话、240 EDF，7,577 源事件，7,576 完整5秒窗口。
sub-3 仅一条2.968秒rest源事件保留并明确排除出固定张量，没有延长/填充。
统一source-only频谱/几何和冻结CSP/LDA全部执行，40行已有真实行为会话关联完成，
模型状态/预测重放检查通过；sub-3完整refit的16件稳定输出字节一致。
75条粗QC标记保留在主分析，7次恒预测失败保留，sub-8的QC匹配不足明确unavailable。

关键发现：独立240-run数值审计发现六组四方重复：sub-7 ses01/02/03与sub-1 ses04
对应run的完整EEG数值相同；sub-7三会话EDF文件字节也相同，sub-1 EDF文件头不同。
178组重复任务窗口含712条记录，sub-7后续query有238条与source training内容重合。
所有文件仍符合官方manifest；原始BrainVision EEG未读取，原因与正确归属未知。
因此10身份EEG bootstrap与关联只保留为计算结果，不称10独立人的确认性证据。
源身份驱动、观察后的敏感性排除两者sub-1/sub-7，保留8身份；旧表不覆盖。
结果/方法/统计/图的确切值以新收据和报告为准，仍无算法保持人类技能的因果结论。

## 用户已授权的数据扩展与存储

### 2026-10-11 扩容接续运行（进行中快照，完成后更新）

旧十人 checkpoint 已提交并推送至 `4290c4061f5d35381ed684bb07f1dd52836bbee0`。
新增 NETBCI 11–19 的 1,692 文件/1,834,605,546 bytes 全部官方验证通过，
下载收据时间戳 `20261011T063742232116Z`；统一19人配置 SHA256 为
`d3de923978079cff7199c294f704a0282d3df589899df1a7f44578a5aabd2bf5`。
全部19人正重新串行审计，输出 `research_logs/netbci_cohort_all19_20261010/audits`。
首个命令仅因 CLI 传数字而被 config 门槛拒绝，未读取 EEG；修正 `sub-N` 后的
有效执行日志为 `runtime/audit_all19_run02.log`。源审计全部关闭后由独立数值脚本
审计456 EDF，再运行 `run_serial_models_20261011.py`；不能跳过这个模型前门槛。

Kumar 全部18身份/108会话/360 EDF实际下载和完整数值审计均完成，2,705文件
1,781,052,841 bytes；7,200事件、44partial全部保留。MNE整型JSON序列化的首次
失败记录保留，正确正式审计为 `kumar_ingestion/signal_audit_run02`。
PhysioNet109手MI资源使用官方archive镜像下载，原版本/654路径/SHA不变，保留慢站
中断及partial证据；不把partial上传R2。Leeuwis55资源固定 nm000327 v1.0.0 正在
下载；新增MILimbEEG60与Liu2024卒中50为独立域来源，须完成源审计后单独登记，
不能混入NETBCI健康纵向结果。所有新库尚未训练新模型。

关闭收据、独立复核、来源记录位于 `research_logs/public_data_expansion_20261010`，
R2逐库上传及库存由对应关闭收据记录。恢复时先检查进程、日志、收据状态，不重跑已有输出。

先完成上述checkpoint，再新增NETBCI编号11–19、Kumar18人六会话、PhysioNet109人
hand-imagery runs04/08/12。不把左右手、右手/rest、健康/临床或同日/跨日标签直接混为一库。
NETBCI全19仍是已见十人结果后的同源探索性扩展，科学参数不重选；全部新信号先做内容身份审计。
公开数据来源调查与固定下载计划保存在 research_logs/public_data_expansion_20261010。
仅固定官方必要子集，不下载完整几十/几百GB多模态归档，不修改第一篇，不用付费GPU或破解SHU。

Cloudflare R2已安全注入AWS_*凭据，实际put/head/GET及SHA256回读均成功。
当前已存原始十人1,885对象与20件完整窗口bundle，另有2件聊天私有备份，总约5.25GB。
后续按 few-shot-mi-eeg/数据集/版本 的不可变前缀增量上传；校验值/长度逐对象核对，
代表大文件完整GET，复用对象必须按脚本要求验证。ETag不是SHA256，不输出任何凭据。
数据与权重在R2及本地运行副本，小表/代码/报告/收据入Git；完整11MB数字指纹ledger
保存R2与本地，Git版本化compact摘要、SHA256及审计源码。

详细入口：[十人报告](netbci_cohort_results_20261010.md)、
[完整窗口规则](netbci_full_window_policy_20261010.md)、
[19人扩展协议](netbci_all19_expansion_protocol_20261010.md)、
[R2存储](r2_research_storage.md)、
[公开纵向来源调查](public_longitudinal_dataset_audit_20261010.md)。
