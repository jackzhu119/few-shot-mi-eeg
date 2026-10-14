# 下一项固定调度

父对话已回读69ac2b9并明确确认sub-1/20261014的2对象245760bytes完整GET及两个离机SHA。父确认和活动账本各追加一次；连续账本现含sub-1三个冻结seed，保留第三fit达到100轮上限的事实，不作seed筛选。

父对话将现有/workspace/paper2-90f674f更新至本次交付的固定提交，确认GPU空闲后运行：

    bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup

下一项仅sub-4/seed20261012；输出/workspace/paper2-results/development-queue/sub-4/seed-20261012.tar。复用现有127文件及下载回执，入口会逐项验哈希，无需重下。配置、预算、训练入口和7项delivery哈希保持不变。

一次最多一个新fit；30分钟超时，退出75后私人回传原包完整SHA256/字节数及调度日志，不循环启动。其他12人和query仍关闭。仅验证账本连续性、全部回执/父确认绑定、固定下一任务及入口哈希；按父要求未重跑全测试。Codex没有启动训练或停Pod。
