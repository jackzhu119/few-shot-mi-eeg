# Kumar 首次真实 GPU fit：独立验收与备份

固定训练提交：d4d2a64bb16e5f3841ecdefeb188fd8b9a121c71。sub-1，seed 20261012；科学配置及冻结划分未改变。本次复核没有重新拟合、加载 EEG 或打开 query。

## 实际结果与边界

源训练 40 trial、源验证 20 trial。实际记录 41 epoch、123 optimizer steps；最早最低源验证交叉熵为 0.6909911870956421，对应 epoch 26。其后连续 15 epoch 未改善，符合冻结 early-stopping patience。单一开发编号和种子的源验证结果不支持 query 准确率、总体性能或方法优越性结论。

内层执行报告 5.509300802834332 秒、峰值 CUDA allocated 12,099,072 bytes；这不是整个 GPU 内存或独立计费记录。外层 dispatch 为 2026-10-14 10:45:18 至 10:45:29 UTC，退出 75 表示当时等待私人归档备份，并非训练失败。实际账单未知。

## 独立验证

11 个结果成员与 4 个外层证据成员的长度和 SHA-256 全部通过；源码逐字节对比固定 Git 提交；配置、冻结 trial ID 集合、训练/验证不相交及 25 输入下载收据通过。三个源 run 的数值摘要与历史原生审计相符。检查点以 weights_only=True 在 CPU 安全读取，全部 tensor 有限，独立重算 state 摘要及绑定 context 与 sidecar 一致。逐轮历史的最早最小值、步数及 patience 独立重算通过。没有独立重算 EEG 损失，也没有重放预测。

原始 training.log 为 0 bytes，按原样保留；41 轮历史位于 weights.json 且与 weights.pt context 绑定。epoch_history.csv 仅为该历史的派生表，不补造 stdout。

## 已完成备份

使用 Codex 已有授权将两个原始归档条件写入 R2，无覆盖；2 对象共 163,840 bytes 全部完整 GET SHA-256 通过，零失败。结果固定 key：

few-shot-mi-eeg/experiments/kumar2024/gpu-source-20261014/sub-1-seed-20261012-run01.tar

结果归档 SHA-256：2a4d0dd291f1f93bc0560e39b99b2e76fbf6bcba0d3a363ceb522fb4afea0f62

外层证据同前缀 sub-1-seed-20261012-run01-dispatch-evidence.tar；SHA-256：ad73258ad41c7f7f64508ac27d5726a99d56123faf339386ab8c925048222905

原始 manifest 的 backup_pending 状态保留作为历史，不修改已校验原包。后续闭合状态见 r2_full_get_receipt.json 和 parent_acknowledgement_request.json。Git 仅保存文本证据，不包含原始 EEG 或 checkpoint 二进制。

## 交接

独立审查及 R2 备份已完成，父对话确认仍待完成。未请求或执行停 Pod；父对话须统筹两篇论文。不得重复本 fit，亦未授权自动扩展至余下 fits。后续正式统计、跨编号图表与论文结论需等待对应实际实验结果。
