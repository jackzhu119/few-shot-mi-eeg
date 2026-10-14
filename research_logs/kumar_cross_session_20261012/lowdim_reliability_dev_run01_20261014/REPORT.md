# Low-dimensional task measurement: development-only results

已在运行前冻结三个候选和循环标签移位方案；实际科学代码commit 3709fcc5f249dd48cb80463ca2805c42e79b5d4c。
只使用6个开发发布编号，实际输入物理移除了query行及最终编号。源TRAIN40与当前support19/20保持原身份/QC；不改变完整窗口或标签预算。

| 测量 | 源run双向探针BA；6编号95%区间 | 五会话分半cosine均值；6编号95%区间 | 分半方向相反 | 源轴两半均正 / 均负 |
| --- | --- | --- | --- | --- |
| standardized44 | 51.67% [44.17, 58.33] | 0.109 [-0.165, 0.382] | 12/30 | 16/30 / 1/30 |
| pca4 | 50.00% [43.75, 55.83] | 0.093 [-0.261, 0.459] | 13/30 | 11/30 / 3/30 |
| motor6 | 54.17% [47.50, 60.83] | 0.153 [-0.142, 0.459] | 11/30 | 18/30 / 0/30 |

这里的统计独立单位为6个发布编号：先平均两source folds或五support会话，再按编号bootstrap10000次(seed42)。原始编号不独立证明生物学身份；6编号区间探索性。不能把30会话当30人。

TRAIN20源run probe中的scaler/PCA只在训练run拟合，目标support坐标仅在40源训练trial拟合。原保存40-trial变换没有用于源fold；没有query更新变换。36个观测centroid probes与14400次(含观测身份)循环控制probe重建均属诊断，不是新CSP/LDA主baseline或适配门控。实际耗时79.14秒；运行时和完整源码/config/plan哈希、IDs、预测、所有移位与全部bootstrap抽样值在measurement_receipt.json。

源控制对每编号使用20×20相同移位组合跨两个fold及三候选；support枚举全部19/20循环移位。无效single-class/零轴控制均保留并明确分母。移位仅作保持标签序列的phase-alignment敏感性，未知时间平稳性/循环边界/cue顺序混杂不支持正式p值或神经特异性。

三个候选的源探针BA区间均覆盖50%，分半方向均值区间均覆盖0；不以C3/Cz/C4点估计最高就选胜者。正的两半乘积也可能来自两半同时反向，不能当作源任务方向保持。

决定：本轮不据这些功率指标搜索或命名有效任务感知门控。结果限制的是这些特定测量及centroid探针，不是否定所有EEG任务信息；此前全CSP/LDA重校准的真实主要提升保持原结论。下一步另冻结源TRAIN监督CSP4空间滤波或源标签判别分数的分组可靠性方案，再考虑同预算的嵌套开发策略比较；不得回看query选择规则。EEGNet正式训练仍Pending，未新购算力。

完整验证679 tests通过（15弃用警告），Ruff/smoke/MOABB合成验收通过。独立执行结果核对另见lowdim_independent_numeric_review_run01_20261014，不将静态代码审查混称数值验证。

独立NumPy数值重放已通过：18坐标状态、36源fold/720预测、7200双向控制值、90support与3576移位half-method评估、六个10000-draw编号bootstrap完全一致；完整最大误差及复核源码在../lowdim_independent_numeric_review_run01_20261014/receipt.json。
