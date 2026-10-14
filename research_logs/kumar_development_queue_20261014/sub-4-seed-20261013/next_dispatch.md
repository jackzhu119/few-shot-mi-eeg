# 第5项父确认后的固定调度交接

Dot于2026-10-14 14:08 UTC实际从固定e57ea2d读取原审计与R2回执并计算完整UTF-8 SHA256，明确确认第5fit sub-4/seed20261013。parent_acknowledged.json记录此真实确认；连续accepted_jobs仅追加一次至5，前四项及旧证据不变。

实际check_gate与独立复核确认唯一下一项为sub-4/seed20261014，job fe495208cd04aff921403e3e0d8c9f3e065d477deff26b28fbfe4480d9ada6c2。7项交付hash全同，科学配置/预算/数值线程未更改；query及非开发formal门继续关闭。只运行相关账本/门控测试：7通过、6未选择，没有重复全套测试。

Dot唯一RunPod操作者将既有/workspace/paper2-90f674f更新至本次返回的固定提交，按既有资源安全门调度一个fit：

    bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup

不得在旧提交重训已完成第5fit。复用127源输入并按原入口核验，不重复下载。下一输出目录/workspace/paper2-results/development-queue/sub-4/seed-20261014；一次最多一fit、30分钟超时、零自动重试。回传未改写原包后仍需独立审计、R2完整GET及明确父确认才能继续。

两篇CPU/GPU可由dot并行统筹，不取消共享资源/逐fit验收门。Codex仅交付账本，未执行上述命令、未启动训练、未改变数值线程或操作Pod。无持久卷Pod保持运行，不Stop/Terminate。
