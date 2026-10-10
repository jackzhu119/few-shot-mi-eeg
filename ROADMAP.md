# Research roadmap

工作题目：**Learning-Preserving Co-Adaptive Brain–Computer Interfaces**。
下列阶段是证据门槛，不是已经完成的科学发现。Phase 0 的完成范围以实际验证记录为准。

## Phase 0 — Infrastructure

建立 main 与 `research/learning-preserving-bci`；固定 Python/依赖；完成可安装包、
CPU 基线、自动化测试、文献/许可/数据审计与可重放配置。

验收：测试确实执行，EEGNet CPU 前向/反向与固定 CSP 跨会话软件验证通过，
配置和逐受试者记录可读取，推送 SHA 与 GitHub 重新读取一致。
合成数据不能通过任何真实数据科学验收门槛。NETBCI 单受试者本地适配已验收，科学分析仍需下一阶段质量控制。

## Phase 1 — Longitudinal Neural Dynamics

优先 **NETBCI2026 / NEMAR `nm000305` v1.0.0（CC BY 4.0）**，
版本 DOI [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)。
访问与最小样本门槛已通过：仅 `sub-1`、4 session × 6 run、24 EDF，
74 EEG 通道、250 Hz、717 个真实事件；所有下载文件均通过官方 manifest 校验。
详细验收见 [dataset_feasibility](docs/dataset_feasibility.md)。此句记录2026-10-09访问验收范围；2026-10-10实际最小baseline见文末。

已完成本地适配器、24 run 原始/derivative 事件对齐及分析前分组冻结，见
[跨会话方案](docs/netbci_cross_session_plan.md)。划分覆盖全部 717 trial：参考训练 90、
验证 30、参考 query 60、后续 calibration pool 90、后续 query 447；划分准备阶段未训练模型，后续最小验证见文末。
下一步仍待验收：伪迹质量、原始缺失 trial 原因、行为向量 run 顺序与评分分母。
原始版本已经只有 717 个事件，不能把相对设计数量的缺失归因于 NEMAR 导出。
事件使用实际 `trial_type=right_hand/rest` 与 `value=2/1`，不采用 README 相反的数字；
时间单位和边界从实际文件核验，不固定假定每 run 32 trials。
逐 trial 成功、光标轨迹和真实日期间隔尚未验证，不能补造。

**第二优先级 SHU / Ma2022：`pending author access`。** 保留五日左右手 MI 的通用
接口与研究计划；`nm000288` 尚待公开，停止请求该接口，原始 ZIP 等待作者合法访问。
历史 Figshare v1 单受试者探针不标记为原始接入完成，不尝试猜测或绕过 ZIP 密码。

完成上述门槛后再研究跨天 Mu/Beta PSD、协方差和试次质量变化；EEG 漂移不能直接
解释为人类学习。NEMAR 的 EDF 转换版本与原始多模态版本不直接混用。

验收：公开数据审计可重放；报告逐受试者/逐会话/逐 run 样本数、缺失和排除原因；
与会话、硬件、疲劳和任务变化的混杂区分。此阶段只形成纵向离线关联证据。

## Phase 2 — Neural Representation Geometry

在同一可比特征坐标中分析 PCA、主角度/子空间距离、协方差距离与表示稳定性；
训练参考投影冻结，测试分区不用于选择维数、对齐或归一化。

验收：预注册特征、维数、对齐约定；与置换/负对照及可靠性比较，
报告通道/reference与信噪比敏感性。不将 EEG 几何无条件等同 fMRI 或 spiking manifold。

## Phase 3 — Fixed-Decoder Generalization

冻结早期会话 CSP+LDA 与 EEGNet，在后续会话评估，分开 within-subject longitudinal
与 held-out subject 问题。验证集选择超参数，最终测试只运行预设分析。

验收：模型、BN状态、训练归一化冻结，逐受试者 balanced accuracy及参与者级CI，
报告类别/试次数与会话时序。称固定参考解码性能，不能替代在线无辅助行为表现。

## Phase 4 — Co-Adaptive Learning

设计固定模型、常规 decoder adaptation、候选 learning-preserving policy 的比较。
离线回放只评价模型更新策略与稳定性代理；必须区分监督标签可获得条件。

验收：相同训练预算、数据访问和调参空间；历史标签不能伪装在线可获得标签；
未有人的反馈交互时不宣称已验证人机协同学习。

## Phase 5 — Learning-Preserving Optimization

规划即时性能与长期稳定性的多目标优化，独立指定性能/稳定性/更新成本端点，
研究 Pareto tradeoff 与敏感性。当前没有已经验证的新优化算法。

验收：候选目标与无更新/常规更新控制有可复现比较，离线代理端点保留其代理名称；
若声称 skill retention，必须有独立在线训练与无辅助 delayed-retention 证据。

## Phase 6 — External and Prospective Validation

先跨数据集验证离线可迁移性；再评估在线人体实验可行性、伦理/同意、反馈控制与统计功效。
前瞻实验需平衡随机分组、固定/常规/候选条件、独立无辅助 probes、延迟 retention
和 transfer tests，并冻结端点与排除规则。

验收：只能对实际设计支持的因果问题作结论；动物侵入式、fMRI 和 EEG 的差异需单独讨论。
不得用合成数据、离线分类或稳定性代理替代人类学习结论。

## 2026-10-10 实际进展与门槛

数据和事件重新核查通过，新增原始scans/两归档目录；行为映射仍受run顺序和分母限制。
单受试者PSD/协方差/PCA、匹配/QC敏感性及冻结CSP/3epoch CPU EEGNet已实际执行并重放；
这不使cohort、人类学习、H3/H4或online阶段自动通过。最新阶段决策见
[真实证据报告](docs/netbci_stage1_evidence_and_decision.md)。先完善QC、行为和多参与者方案，再决定扩展；无新算法或新人体干预。
