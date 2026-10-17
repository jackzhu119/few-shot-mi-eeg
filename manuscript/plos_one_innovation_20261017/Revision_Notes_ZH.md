# 论文2：创新分析与投稿文件修订说明

## 本轮版本

本轮基于研究分支 `30f23ed3c9afd271a3821fceaa99ab932bf25e5f`，完成主稿、S1 方法、S2 复现说明、附信、六张图及扩展 S1 Data。当前入口为[完整文件包](README.md)。原稿、原预测、原主次终点及原封存包保留在各自日期目录。

新题目为 **Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**。全文围绕“相同校准标签应该更新解码器的哪一部分”展开，引言明确列出四项贡献：等标签组件增益、预测错误转移分解、纵向一致性与参与者影响分析，以及校准子集一致性和任务方向的区分。

## 新增结果及其在论文中的作用

下表均以预定义主队列的12名参与者为单位，先在每人内部等权平均五次目标会话，再计算队列均值；百分点指 balanced accuracy 或对应类别 recall 的变化。

| 新增呈现 | 复算结果 | 对创新论证的作用 |
| --- | --- | --- |
| 组件增益占总均值增益的比例 | 5.4716 / 7.4214 = **73.7%** | 将空间滤波重拟合的增量价值前置到摘要、引言和讨论 |
| Full 相对 LDA-only 的错误转移 | 纠错贡献 **16.04** 点，新增错误贡献 **10.57** 点，净增益 **5.47** 点 | 从每条预测说明总体增益如何产生，对应新 Fig 5 |
| 两类平均 recall | 左类 **+6.16** 点，右类 **+4.78** 点 | 表明增益同时覆盖两类的队列平均表现；Table 6 保留每类完整区间 |
| 五次目标会话的组件均值 | **+3.52、+5.20、+4.13、+4.18、+10.33** 点 | 展示会话序列中的平均优势，对应新 Fig 6B |
| 删除任意一名主队列参与者 | 剩余11人组件均值 **+4.39 至 +6.28** 点 | 检查单个参与者对队列估计的影响，对应新 Fig 6C |
| 参与者联合增益 | 10/12 的组件均值为正；开发组与主队列完整展示 | 对比 classifier-only 增益与额外空间增益，对应新 Fig 6A |

73.7% 是两项队列均值的算术比值。两类结果使用“平均 recall 提高”的准确表述；Table 6 中左、右类区间分别为 −0.51 至 +13.42、−3.21 至 +12.44 点。Fig 5 同时展示主队列、开发组和全18人次级汇总，保留完整的纠错与新增错误信息。

原核心效果保持一致：Full 相对 frozen 为 **+7.42** 点，95% 参与者 bootstrap 区间 **2.49–12.48**；相对使用相同标签的 LDA-only 为 **+5.47** 点，区间 **2.17–8.91**。原四项配对符号翻转检验和 Holm 校正已重新枚举，数值不变。

结果依据：[新增结果表](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/research_logs/kumar_update_mechanisms_20261017/run01/cohort_transition_bootstrap.csv)、[会话曲线](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/research_logs/kumar_update_mechanisms_20261017/run01/session_contrast_profiles.csv)、[参与者影响分析](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/research_logs/kumar_update_mechanisms_20261017/run01/leave_one_participant_out.csv)。

## 实验与复现完整性

| 检查对象 | 实际覆盖与核验 |
| --- | --- |
| 原始事件及排除 | 7,200 个事件身份；7,156 个完整窗口，44 个边界窗口排除 |
| 查询与方法配对 | 4,290 个完整 query；三种 CPU 方法和三个 EEGNet seed 对应25,740行预测，身份一致 |
| 等标签组件对照 | 90组更新对照；198条历史 CPU 拟合记录及324条 query-state 记录完成核对 |
| 原始端点重建 | 72个参与者/方法行、144个源与目标端点完成复算 |
| 独立算术检查 | 从原始 CPU CSV 以整数计数和有理数运算检查54个 CPU 端点及324项转移率 |
| 神经参考完整性 | 原54次拟合、三种子、2,871个 epoch、8,613个优化步及全部训练记录纳入说明 |
| 校准测量 | 原240个 source-run fold/rotation 流程及30个开发组 support 会话完整保留 |
| 新增结果的独立重放 | 从实际新 S1 Data.zip 解压后，12张 CSV 与6个科学 JSON 全部逐字节复现 |
| 旧数据包保护 | 新包101成员；其中原69成员逐字节一致，新增32成员 |

本轮新增的是基于已保存预测的分解、类别、会话和影响分析，未新增 EEG 训练或模型推理。任务阶段映射已有311/360 runs、6,220/7,200 events；标签预算、对齐方法及阶段解码保留在各自后续方案中，没有混写为本稿已经完成的新实验。依据见[完整性审计](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/research_logs/kumar_update_mechanisms_20261017/run01/input_completeness_audit.json)与[实际新ZIP重放记录](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/research_logs/kumar_update_mechanisms_20261017/run01/final_zip_replay_validation.json)。

## 表达与结构

引言直接呈现贡献及对应数值，讨论集中解释组件比较、逐试次增益来源和校准测量的意义。重复的文献回顾、训练日志细节和反复限定已压缩或移至补充材料；讨论末尾以一句话集中说明研究范围和后续验证目标。方法中的样本定义、等标签条件、会话权重、参与者推断单位和新增分析的探索性定位保留，使强结论能够由实验定义直接支持。

文字修订重点是具体动词、清楚的因果与比较关系、减少模板化过渡和重复总结。未运行外部“AI率”检测，也未宣称某个检测分数。正文与图注保留本轮实际分析、图件和写作使用的 AI 辅助披露。

## PLOS ONE 文件准备

已按截至本轮检查的官方[投稿要求](https://journals.plos.org/plosone/s/submission-guidelines)、[图件要求](https://journals.plos.org/plosone/s/figures)和[AI披露政策](https://journals.plos.org/plosone/s/ethical-publishing-practice)整理。

主标题95字符、短标题55字符、摘要251词；投稿版单栏、12 pt、双倍行距，包含参考文献双倍行距、连续行号和页码。六张表保持可编辑，图和表按首次引用顺序编号，图注位于首次引用附近。正文结尾为致谢、参考文献及补充信息说明；Funding 转入投稿系统字段。主稿与图件分开提供，并另附带图阅读版。六张 TIFF 均为600 dpi、RGB，采用真正 Arial 字体及8–12 pt 图内文字；附信一页。

本轮相关软件验证：三个新脚本通过 Ruff；原质控与配对统计后处理的39项测试通过。完整旧仓库测试在当前 Python 3.12 环境因缺少 MNE、Torch、Requests 等依赖而于收集阶段停止；旧 smoke/MOABB 检查同样未完成。全仓 Ruff 的8项错误来自已有的上一版排版脚本。原 Python 3.11 科学环境与当前导出/保存结果分析环境分别记录，未把本机这些未完成的软件检查记为通过。详细状态见[软件验证记录](https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/research_logs/kumar_plos_innovation_20261017/software_validation_20261017.json)。

本轮交付包括已生成文件和对应来源、复现记录及格式核验；投稿平台中的提交操作仍由作者执行。

## 2026年10月17日最终投稿核查补充

本轮再次对照PLOS官方要求检查实际文件，删除两份主稿中的独立利益冲突句并保留系统字段，依据原始收据在方法部分补入10月10日元数据访问、10月11日EEG及配套元数据取得日期。主稿数值、所有表格和科学结果未改动。

已补官方2026版Human Participants Checklist及短名图件上传包。作者于2026年10月17日15:29及15:31（北京时间）明确确认无法访问可识别具体参与者身份的信息；方法部分新增相应声明，正式稿第6页第99–100行报告该事实。完成版清单第3项引用第96–100行，覆盖数据访问日期和身份信息访问情况。完整判断与提交文件对应关系见 [最终投稿核查](Final_Submission_Check_20261017_ZH.md)。
