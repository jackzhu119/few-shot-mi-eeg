# 首次真实 fit 的无拟合重放

父对话已确认首次训练的2对象163840bytes R2完整GET验收；追加记录为 research_logs/kumar_first_gpu_fit_20261014/parent_acknowledged.json，原包与旧回执未修改。Pod继续供两篇论文调度。

本入口只复用现有25文件、原始归档中的权重和冻结源TRAIN/validation。训练代码、数据哈希及完整输入审计均核对；重新计算TRAIN均值/标准差后逐位对比权重内统计量，不更新模型统计量。eval/inference_mode 下按原16批量重算交叉熵，再使用独立NumPy float64 logsumexp计算逐trial损失。两项均与原选择epoch26的记录比较，预先固定绝对容差1e-7、相对容差0。全部参数、BN buffer及归一化前后state SHA256必须完全一致。没有optimizer或fit调用，没有query。仍复用冻结适配器/官方架构，属于独立损失计算及状态重放，不宣称独立实现整套EEG预处理。

父对话先更新既有 /workspace/paper2-90f674f 到交付的固定提交并确认git工作区干净，待论文1让出GPU后执行：

    cd /workspace/paper2-90f674f
    bash scripts/launch_kumar_first_fit_replay.sh

不可调用旧first-fit launcher。600秒超时、30秒TERM宽限；共享 /workspace/research-gpu.lock 非阻塞锁及GPU进程检查，任一忙则失败关闭。现有输出、日志或tar均阻止重跑。预计只需要原输入16,425,499 bytes及少量证据空间；不下载、不申请资源、不连接R2。源码和配置通过Git固定版本交付。

完成后收回以下私人归档，并提供launcher打印的完整SHA256及字节数：

    /workspace/paper2-results/kumar-first-fit-replay-run01.tar

归档包括原样checkpoint副本、sidecar、逐trial源验证logits/标签/float64 loss、结果JSON、stdout和可能的traceback；不上传公共Git二进制或受限原始数据。超时/故障同样打包现有诊断。不得把exit0单独当作端到端闭合：父对话经Jupyter→私人Library交付，Codex核验成员及阈值后使用已有R2授权条件写入固定key：

    few-shot-mi-eeg/experiments/kumar2024/gpu-source-20261014/sub-1-seed-20261012-replay-run01.tar

要求完整GET长度及SHA256，并追加独立验收和父确认记录。失败不覆盖、不自动重试、不调整容差、不放行队列；先审查原因，需要修复则用新编号保留失败证据。通过重放及私人备份验收后才可由父对话安排后续开发队列，当前未执行重放或新fit。论文1尚待调度，不能停Pod。
