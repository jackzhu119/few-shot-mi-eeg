# Kumar cross-session decoding results

**2026-10-27新增结果：**[V3全部126项的保存结果分析与新论文主线](research_logs/paper2_v3_analysis_20261027/REPORT.md)，[BMT新审阅稿](manuscript/discovery_revision_20261027/README.md)。下文原12人终点、角色和数值保持不变；V2/V3仍属原6名已暴露参与者的发现研究。

真实CPU三基线已完成。下面均为每个参与者五个目标会话BA的等权均值，再对参与者
取平均；不是将会话或trial作为独立样本。主要比较和测试编号均在性能计算前冻结。

| Cohort | Published IDs | Frozen CSP/LDA | Frozen CSP + LDA recalibration | CSP/LDA refit |
| --- | ---: | ---: | ---: | ---: |
| Development | 6 | 59.97% | 64.37% | 63.22% |
| Fixed final test | 12 | 57.94% | 59.89% | 65.36% |

最终测试的主要配对比较为全重校准减冻结：**+7.42个百分点**，10,000次参与者
bootstrap、seed42、95%百分位区间**[+2.49,+12.48]个百分点**。
12编号中9个提高、3个降低；下降也保留。开发组相同差值为+3.25个百分点，区间
[-0.90,+7.14]，不以开发结果重新选择配置或改主终点。

最终测试的次要描述中，固定CSP仅重校准LDA较冻结为+1.95个百分点，区间
[-0.98,+5.09]；全重校准较仅LDA更新为+5.47，区间[+2.17,+8.91]。
这些次要比较没有确认性多重检验结论。源query20trial、后续query39–60trial的真实
类别计数和不等量情况在逐行结果中保留，主统计给予每个会话相同权重。

全部324行和12,870预测见运行目录`cpu_run01_20261013T151445Z`。
参与者端点、混淆矩阵、左右召回、类别比例、冻结状态及支持标签预算均可重放。
最终测试冻结模型有两次目标会话恒定预测，两种更新没有该情况；全部队列冻结模型
共三次，均未删除。逐人反应不一致说明不能默认任何会话都必须更新。

这是已经探索性审计过的同库固定留出，不是完全未接触的外部确认。未核实跨库生物学
身份、年龄2020为无效占位值、GR/PAR归属未确认，不能依此报告人群亚组效果。
1,512/7,156完整窗口具有固定幅度QC标记，主分析保留它们；分类性能可能利用伪迹。
现有结果支持该固定离线标签预算下的解码比较，不证明神经学习、可塑性、无辅助控制、
人类技能保持或新任务感知算法有效。普通CSP/LDA更新本身不是原创算法贡献。

固定Mu/Beta、Riemann距离、源PCA及任务轴解释分析和QC/通道/样本数/参考诊断另存
`research_logs/kumar_cross_session_20261012/independent_review_run01_20261014`。
任务轴只由source_train的类别信息定义，目标标签只用于BA或明确标注的描述性类统计。
新的任务感知门控策略仍Pending，条件、同预算控制与防泄漏要求见
`TASK_AWARE_ADAPTATION_RESEARCH_PLAN.md`。EEGNet的历史CPU软件验收和源数据形状检查已由后续54项源模型训练、独立审计及一次冻结query评估补齐；最新结果和预算差异见本文下方2026-10-15更新。

独立解释分析的固定测试60会话中，协方差形状代理与BA变化Spearman为-0.007，
参与者块bootstrap95%CI[-0.505,0.438]；源任务轴Wasserstein为0.197，CI[-0.240,0.518]。
两区间跨零，不支持可靠预测或任务特征更优的结论。source-only特征、功率单位、PCA
投影及Riemann距离均已独立复算，未重新训练解码器。

科学图在`figures_run01_20261014/participant_baseline_comparison`（PNG/SVG/PDF）。
灰线为个体，蓝点为队列均值，误差条为参与者bootstrap95%CI；右侧保留三个负差值。
PNG已实看，SVG/PDF仅出口hash验证。固定QC/数量/通道与as-stored/CAR功率诊断已经
计算；as-stored并不独立证实物理CPz身份。额外support-only PCA/SVD的90个子空间距离
只作post-freeze描述，不拟合query、不反馈模型，不改变性能前主要比较。


## 2026-10-15：54项冻结EEGNet及真实query验收

54个源模型（18参与者×3固定种子）及一次always-frozen query评估均已完成。
dot于09:49:05 UTC真实确认固定ac5a1f6的query结果；确认范围与独立query接受记录见
`research_logs/kumar_frozen_query_acceptance_20261015/run01/`。原source54账本不改。
EEGNet目标BA：开发6人52.3087%（参与者bootstrap95%区间48.4301–57.3582%）；
固定剩余12人51.5783%（49.0800–54.5125%）；18人次要汇总51.8218%
（49.5930–54.3590%）。全部目标队列区间含50%，没有新增机会水平假设检验。
16个种子×会话单类预测结果全部保留（14目标、2源query；涉及7模型/7参与者）。

四种基线使用同一4290个完整query（源360、目标3930）及原30个短query排除，
但不能将同query误称为同标签预算。EEGNet和CPU都用40个source TRAIN；
EEGNet还用20个有标签source validation选epoch，CPU不以validation选模型。
冻结两法均用0个目标support；两种CPU更新各用同一当前会话19或20个support，
不累积前后会话。CPU两更新之间标签预算相同，更新计算量不同；EEGNet与CPU更新
之间仅作明确预算不匹配的描述。原CPU主要比较及其负差参与者均不改变。

逐样本/标签核对、逐人/逐会话表、预算矩阵及复算回执见
`research_logs/kumar_frozen_query_comparison_20261015/run01/`。英文当前稿见
`manuscript/kumar_longitudinal_decoding_working_draft_20261015.md`。这些是已见测试后的
探索性结果，不证明架构普遍优劣、自适应因果收益、人类学习或任务感知门控有效。
没有剩余已冻结EEGNet fit或更新实验需要启动；不为匹配预算重训或补造更新规则。
