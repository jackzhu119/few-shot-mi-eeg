# Research roadmap

工作题目：**Learning-Preserving Co-Adaptive Brain–Computer Interfaces**。
下列阶段是证据门槛，不是已经完成的科学发现。Phase 0 的完成范围以实际验证记录为准。

## Phase 0 — Infrastructure

建立 main 与 `research/learning-preserving-bci`；固定 Python/依赖；完成可安装包、
CPU 基线、自动化测试、文献/许可/数据审计与可重放配置。

验收：测试确实执行，EEGNet CPU 前向/反向与固定 CSP 跨会话软件验证通过，
配置和逐受试者记录可读取，推送 SHA 与 GitHub 重新读取一致。
合成数据不能通过任何真实数据科学验收门槛。数据集专用原始文件适配仍待下一阶段审计。

## Phase 1 — Longitudinal Neural Dynamics

取得一个许可允许、规模可控的 SHU 或 NETBCI 子集；核实原始通道、事件、采样、
单位、会话时间与反馈语义。冻结事件映射与质量检查，再研究跨天 Mu/Beta PSD、
协方差和试次质量变化。

验收：公开数据审计可重放；报告逐受试者/逐会话样本数、缺失和排除原因；
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
