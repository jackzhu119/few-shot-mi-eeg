# Development-only support task-direction reliability

2026-10-14探索性新诊断，配置在运行前保存；6个固定开发编号、30后续会话。
沿用源TRAIN40样本拟合的44维标准化Mu/Beta功率，仅取当前run-0 support19/20样本。
不使用query行、不打开12个最终编号、不重新拟合解码器、不选择阈值。
现有NPZ容器包含query，但计算只切出明确允许的source_train/target_support行；输入整文件SHA为来源绑定。

每类按原时间顺序分成前floor(n/2)与剩余两半，估计右减左44维类均值方向。
30会话中12个split-half方向cosine为负，中位数0.2223。
源训练与support方向cosine的1000次类内bootstrap区间在21/30会话跨零。
此区间是给定少量support的条件测量不确定性，不是人群区间；会话不是独立参与者。
44维方向仅约10样本/类，高维抽样噪声、时间内漂移及伪迹可能影响测量。
不把方向不稳解释为神经技能变化，不据此声称不存在任务信息。

决定：尚无可靠性证据支持新门控实现。本轮不搜索阈值、不回看query选规则。
后续应先冻结源TRAIN内降维或空间滤波的测量候选、源run分组验证及负对照；
只在开发组检验可靠性后才能决定是否进入嵌套策略验证。已有最终基线已见，后续同库算法仍属探索。
正式EEGNet仍未训练；没有新购算力。

完整30行、允许trial IDs、输入SHA、配置与执行源码SHA见measurement_receipt.json。
