# 个人第二篇论文的研究主线与写作蓝图

工作方向：**Learning-Preserving Co-Adaptive Brain–Computer Interfaces**。日期：2026-10-10。

当前[英文论文工作稿](../manuscript/longitudinal_eeg_working_draft.md)是单受试者真实可行性研究，不是最终核心算法论文；[证据决策](netbci_stage1_evidence_and_decision.md)划定可写和不可写的结论。以核心方向发表高水平论文，还需要新证据，不能通过改标题或引用 Nature 补足。

## 三篇论文怎样进入自己的论证

| 原始研究 | 应借鉴的研究逻辑 | 自己需要检验的问题 | 当前不能直接移植 |
| --- | --- | --- | --- |
| Wang / sensory joint learning | 同时记录人的训练、decoder更新与感觉引导，安排引导撤回与长期测试 | 即时训练改善是否迁移到无额外引导及延迟控制；控制架构/更新预算后哪部分有效 | NETBCI无触觉干预；无触觉不等于旧冻结mapping；原文随机化描述冲突须保留 |
| Busch / manifold geometry | 主动扰动mapping，比较与已有可生成结构相容/不相容的条件；排除整体方差和subselection解释 | EEG中mapping兼容性是否可测，是否预测学习；新技能与旧读出表现如何分离 | rt-fMRI空间/血氧时间、T-PHATE语义不能等同EEG covariance；旧读出变差不自动等于skill丢失 |
| Rajeswaran / assistive algorithms | 将task information集中与总体variance/dimensionality分开；用干预模拟提出机制 | EEG适应是否改变task-predictive directions，变化是否带来稳定性或脆弱性 | scalp channels不是neurons；历史动物不同decoder不是随机人类对照；demo不能当完整复现 |

三者构成原创论证的起点：**算法影响表征，而表征约束可学性；好的算法目标应由人的独立技能与任务信息验证，不能由即时解码分数或低drift单独定义。** 这是待检验研究立场，不是已建立定理，也不是新的算法贡献本身。原始方法定位和公开材料矛盾见[Wang/Rajeswaran精读](nature_joint_assistive_close_reading.md)、[Busch精读](nature_geometry_close_reading.md)。

## 当前可以完成的第一层论文

科学问题：一个可追溯、控制通道/参考/取样的纵向MI-EEG体系，能否把传感器表征变化、固定读出迁移和历史行为记录分开？

现有工作稿的结果来自 sub-1 717trial，不预设学习：源/事件审计、behavior unresolved、表征敏感性、constant-rest CSP失败、短训练EEGNet流程验证。它提供可复现方法和限制，但一个人/四session不足以验证生理机制、个体差异或人群效应。

下一步若授权多参与者，先冻结源/QC/session日期协议和task-conditioned指标，再验证：同类/同run分布、任务可解码信息与总体variance是否分离、subject特异与跨subjectnull、表征变化与充分训练后的冻结解码误差是否关联。采用inner-fold特征/模式排序和outer-test评估，防止使用测试分数排名后的乐观NAC。保留零结果/常量预测/不满足QC的失败；不能只挑最好个体或seed。

## 最终 Learning-Preserving 核心论文的第二层证据

H3/H4需要改变算法政策而不是只观察历史变化。设计同架构、相同反馈与标注/更新预算的随机在线对照：固定、常规适应和待验证的mapping-compatible策略；需要记录每一次mapping与normalization变化。尚未实现或命名新策略。

区分至少三类端点：即时assisted训练成绩；无额外感觉引导、延迟的真实闭环行为技能；旧冻结mapping和公平的新mapping各自的迁移/控制表现。旧mapping差而新任务技能好是必须允许出现的反例。不能以保护旧decoder为唯一目标，阻止有益可塑性。

主终点、训练性能约束与最小有意义差异在招募前确定；样本量基于可靠先导、repeated measures与dropout模拟，不借其他模态effect编造power。所有试次需要subject/session/run/trial、同步时间、cue/feedback/cursor/hit/abort、mapping版本、辅助条件及排除原因。撤回辅助、延迟retention与transfer分别报告，避免“最后一天更高BA”冒充持久技能。

## 写作原则

引言提出证据缺口而非预告成功；方法准确报告实际执行；结果只写已保存真实输出；讨论允许几何稳定不是有益学习、旧读出衰退不是学习丧失。待做实验单独列为prospective design。作者信息、机构、伦理判定、贡献/经费/利益冲突须由作者确认，不自动填造。Nature风格指问题明确、对照严谨、机制可证伪，不指复制措辞或承诺录用。
