# 下一项固定调度

父对话已确认sub-1/20261013的2对象296960bytes完整GET及离机包hash，parent_acknowledged.json已追加，活动账本仅新增该任务一次。初查本地/远端均停在62e1378，无此前UNKNOWN发送造成的重复追加。

父对话将现有/workspace/paper2-90f674f更新至本次交付的固定提交，确认GPU空闲后只运行：

    bash scripts/launch_kumar_development_next.sh --parent-acknowledge-replay-backup

下一项为sub-1/seed20261014，job_id ba8899c0dc867baefa9a5623cccf706a82571413d63ec76e4baa7bfab613b4ca。复用既有127文件及下载回执；入口训练前会全哈希核验，无需重下数据。没有修改科学配置、预算、执行入口或传输配置，所有7项delivery哈希仍匹配。

依旧一次最多一个fit；30分钟超时，exit75表示需要私人回传验证，不自动推进。预期结果/workspace/paper2-results/development-queue/sub-1/seed-20261014.tar，固定R2 key为few-shot-mi-eeg/experiments/kumar2024/gpu-development-20261014/sub-1-seed-20261014-run01.tar。回传原包完整SHA256/字节数和调度日志，不循环调用。query及其他12人门仍关闭。Codex本轮未启动训练或停Pod。
