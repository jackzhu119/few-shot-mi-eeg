# sub-1 / seed20261014：实际fit审计及备份

固定训练提交cc70f4274b7e14d9bd0e8d76d072aacf625bbf43；调度11:41:41–11:41:52 UTC退出75（当时备份待验收）。14结果成员、6外层成员、127输入哈希、冻结划分/源码、checkpoint安全tensor context及state摘要通过。输入审计与首fit逐字节一致。实际40 TRAIN、20源验证、0 query。

实际100epochs、300updates，选择epoch93。**停止原因是达到固定100轮上限，不是patience早停**；末尾连续7轮未改善，未达到15轮。没有延长训练、重训或按seed表现筛选。源验证CE=0.6714189291000366；Torch重放差0，Codex从保存logits独立重算CE=0.671418904013481，绝对误差2.5086555610620564e-8，符合事前1e-7。Codex没有加载EEG或拟合模型。达到上限不等于已证明收敛；不以单编号三seed推断总体或query性能，三seed均保留。

原结果194560bytes SHA256 c31785de7b61c187ae3690a6d16cce8d89e5edf93be0bae6bcfce2b81a0fb309。
外层51200bytes SHA256 121c956c49c2348c6c1f3381656bfcfebc5c03377f1f4eecd0906bc337472528。
两原包条件写入few-shot-mi-eeg/experiments/kumar2024/gpu-development-20261014前缀，2对象245760bytes完整GET SHA256通过、零失败。原包/原始pending状态未改写。
回执SHA256：f7fd70269f10175ed7f93372500518cd18d642f49751ad77ebdc2e202413f4af

待父独立回读确认。活动账本仍只有前两项，本项proposal不是验收。确认后另行追加parent_acknowledged与活动账本、发布新的固定提交，才能释放sub-4/20261012。没有执行下一项、改科学配置/预算或停Pod；实际账单未知。
