# 下一项固定调度

父已回读f61c925并明确确认sub-4/20261012的2对象225280bytes完整GET与离机SHA。父确认及连续账本各追加一次，现4项已验收。已验证全部回执/父确认绑定、连续前缀、唯一下一任务和7项交付哈希；按指示不重跑全测试。

父对话将既有/workspace/paper2-90f674f更新至交付的固定提交，确认共享GPU空闲后执行：

    bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup

仅下一项sub-4/seed20261013；复用127输入及回执，入口逐文件验哈希，无需重下。输出/workspace/paper2-results/development-queue/sub-4/seed-20261013.tar。一次最多一fit、30分钟超时，exit75后私人回传原包SHA256/字节数及调度日志，完成完整GET与父回读确认后继续固定队列。

用户12:26 UTC已要求持续完成授权工作，不反复提问或无故暂停；后续沿现有冻结流程自动准备与交接，不跳过证据验收、不重训、不扩展query或其他12人、不提前写未取得的结果。科学配置、预算和训练入口不变；Pod保持运行，Codex本轮未启动GPU任务或停机。
