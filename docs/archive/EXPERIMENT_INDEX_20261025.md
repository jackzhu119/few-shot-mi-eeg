# 历史快照：experiments/README.md

归档日期：2026-10-25（Asia/Shanghai）。原文件固定于 `04d21b06a7acc225391958556220e7cdb2bcffbd`。
本页记录当时状态；当前入口见[仓库主页](../../README.md)与[当前状态](../../CURRENT_PROJECT_STATUS.md)。
旧文中的相对链接已指向原固定提交，旧命令和旧声明保留为历史记录。

---

# Experiment gate

The executable experiment in Phase 0 is `scripts/smoke_experiment.py`, configured
by `configs/smoke.json`. It uses synthetic data only. See `ROADMAP.md` and
`docs/research_protocol.md` for the gates before real-data longitudinal analysis.

Freeze subject/session splits and event mappings before evaluation. Select any
hyperparameters on a separate validation partition; never tune against the final
test sessions. Keep a per-subject record, input provenance, configuration, seed,
environment and source commit for each run.
