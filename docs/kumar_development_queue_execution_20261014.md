# 实际可执行开发队列：固定源域、最多17新fit

本操作版接续既有冻结计划，不修改科学配置、18人总体计划、预算或种子。此前计划中的execution_enabled=false保留为历史；新增runtime配置是执行入口，只允许父对话明确确认重放备份并排期后单步推进。实际已完成的EEGNet只有sub-1/20261012首fit及其无拟合重放，不代表整套基线已完成。

## 重放闭合证据

收到重放原包51200bytes，SHA256 394b934c18c1d814fa46de7d6f0e6bb82311be62205c310b9fdef8675841ea71；
外层包71680bytes，SHA256 7396bfed6aefd58485175ee0e84dbd29fa6d62762c843846c0b6d073710a0f36。
外层11:07:17–11:07:22 UTC退出0。原checkpoint/sidecar与首fit逐字节一致；20个冻结源验证trial ID和标签通过。Codex从保存logits使用独立logaddexp重算CE为0.690991198601597，比原0.6909911870956421差1.1505954855550726e-8，在事前1e-7容差内；没有放宽容差。实际EEG forward在Pod执行，Codex没有重拟合或重新加载EEG。2对象122880bytes均完整GET SHA256通过，回执research_logs/kumar_first_fit_replay_20261014/r2_full_get_receipt.json。

父对话应核对这份新备份回执；以下--parent-acknowledge-replay-backup明确记录其确认及调度，不提前伪造父确认记录。原重放包及原始pending状态不改写。Pod供两篇共用，不能停机。

## 现有Pod执行命令

将既有/workspace/paper2-90f674f以git fetch/checkout更新到本次交付的固定提交，要求工作区干净。代码可通过现有GitHub HTTPS读取，不使用新凭据、不连接SSH。源码及配置哈希见research_logs/kumar_development_queue_20261014/delivery_hashes.json。

先仅恢复源域数据；失败停止，不接着训练：

    cd /workspace/paper2-90f674f
    PYTHONPATH="$PWD/src:$PWD/scripts"       timeout --signal=TERM --kill-after=30s 1800s       /workspace/.venvs/paper2-gpu/bin/python scripts/fetch_kumar_development_queue_https.py       --data-root /workspace/paper2-data/kumar       --receipt /workspace/paper2-results/https-development-download-run01.json --execute

固定127文件/98,743,492bytes、18 EDF；原有25文件中22项复用，额外3项元数据不删除。新增105文件/82,322,754bytes；NEMAR nm000177 v1.0.5/CC-BY-4.0。元数据先于EDF，官方文件身份、长度与历史SHA256同时校验；没有support/query EDF。仅单路、每文件一次请求，无自动重试。完整收据再次调用会逐项验哈希并复用；部分失败收据保留且阻止自动重试。全部输入加2GiB余量为下载空间门；不需要新付费资源或R2凭据。

确认论文1已让出GPU，再显式执行一个新fit：

    bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup

当前唯一下一任务：sub-1/seed20261013。后续固定按sub-1、sub-4、sub-7、sub-10、sub-13、sub-16和20261012/13/14顺序，仅跳过已验收首fit。不得自行改subject/seed、使用旧formal入口或评估其他12人。

1800秒超时、TERM宽限30秒，非阻塞共享/workspace/research-gpu.lock及nvidia-smi检查。一次调用最多一个新fit；调用时先核对原科学config/split、重放审计和完整GET回执、验收账本。40源TRAIN/20源validation，最多100epoch/300步；全部17新fit最多5100步。实际时长和账单未知，不外推首fit耗时。

输出目录为/workspace/paper2-results/development-queue/<subject>/seed-<seed>，独占mkdir即持久预约。保存状态事件、源输入审计、配置/源码、完整checkpoint与绑定history、源验证logits/loss及checkpoint无拟合重放。验证绝对容差保持1e-7。成功stdout列出tar路径/字节数/SHA256/result_key。退出75是本地拟合已存、私人备份待完成，不是端到端成功。外层时间与退出码保存于打印的queue-dispatch-XXXXXXXX.log。

已有完整结果只核验并打包，无新fit；已有部分结果立即阻断。每次调用只挑第一个未验收任务，所以反复启动同版本只会返回同一待验收包或失败，不会训练第二个种子。checkpoint/hash/归档冲突均保留，不覆盖。一次失败不自动重试。当前不保存中途optimizer/RNG状态，因此不宣称支持中途精确续训；失败恢复需要单独审查，不删预约重跑。

## 私人逐fit证据闭合

1. 从Jupyter下载stdout指出的原tar，以及本次queue-dispatch日志；经私人Library交付。不要复制R2持久凭据到Pod。归档最大16MiB，不含原始EEG；最多一fit未备份，验收前不推进。
2. Codex取回原包后，按父对话提供的完整SHA256和字节数执行：

       PYTHONPATH=src:scripts /workspace/.venvs/few-shot-mi-eeg/bin/python          scripts/audit_kumar_queue_bundle.py          --archive /absolute/private/received.tar --sha256 EXACT_SHA256          --bytes EXACT_BYTES --output /absolute/private/new_independent_audit.json

   审核14成员、job ID、科学config/split、checkpoint安全tensor context/state、全部有限值、冻结trial标签、逐epoch选择/patience及源验证logits的独立CE；对比执行Git源码及输入历史哈希。失败保留诊断，不补算/改阈值。若某任务失败，不按表现跳过人或seed。
3. 将不修改的原包以job.result_key最后一段命名放入专用private staging目录，只包含本次包；外层日志另作只含日志/固定manifest的dispatch证据包。用Codex已有授权执行sync_research_r2.py，--key-prefix为few-shot-mi-eeg/experiments/kumar2024/gpu-development-20261014，--execute --readback-mode all --workers 1，并将新回执写入对应job证据目录。条件创建不覆盖；同key已存在必须全GET相同比特才可复用。每份对象长度与SHA256全GET通过且零失败才算备份完成。
4. 父对话核对并确认本job回执后，追加独立parent_acknowledgement JSON：status=parent_acknowledged、job_id、receipt_sha256及确认来源。向research_logs/kumar_development_queue_20261014/accepted_jobs.json的accepted_jobs数组追加该job的job_id/subject/seed/archive_sha256/result_key/receipt/parent_acknowledgement。只追加，首fit不改写。Git提交文本审计、回执与确认；不上传原始EEG或二进制权重。
5. 父对话将Pod更新到包含新验收账本的固定提交，重新同一launcher命令才会释放下一项。账本必须是固定顺序的连续前缀，缺回执、缺父确认、非完整GET、乱序或hash冲突均阻断。严禁shell循环17次代替这个验收过程。

全部开发任务完成后入口返回all_18_development_fits_accepted而不训练；正式query和其他12人门仍关闭。模型和证据可靠备份、两篇共同依赖解除并由父对话确认前不关Pod。训练结果回来后才更新总体统计、图表及论文。
