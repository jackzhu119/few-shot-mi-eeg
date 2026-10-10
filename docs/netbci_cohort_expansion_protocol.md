# NETBCI 十人扩展：读取新 EEG 前固定的规则

日期：2026-10-10。基于已观察的单人先导研究，属于探索性队列扩展，不是外部预注册。
第一篇仓库保持只读；继续当前第二篇仓库和现有 CPU 环境。

## 样本与来源

纳入 NEMAR nm000305 v1.0.0 的 sub-1 至 sub-10，按发布编号决定，未按行为改善、
分类准确率或神经结果挑选。sub-1 已有结果，原始19人的行为表已经看过；
sub-2..10 的新EEG在本方案保存前尚未读取。目标10个独立参与者、各4 session/6 run；
真实trial数由事件审计确定，不按设计值填补。当前扩展不获取原始49GB多模态归档，也不下载余下9人的EEG。

使用已核验CC BY 4.0的固定公开derivative和官方manifest，
DOI [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)。
复用sub-1已验证数据，流式按文件获取sub-2..10及各原始vhdr元数据，
每个文件必须匹配官方大小和校验和。不会把下载成功当作读取/科学验收。

逐人检查MNE完整信号有限性、通道和顺序、采样率、单位、事件时间、样本基点、
标签、duration、重复/越界和session/run覆盖。通过NEMAR sourcedata provenance的显式
subject→upstream文件映射，并实际核验源vhdr hash，对应原始行为表subject/session。
源header的采样率与derivative分别记录；未获取的源markers/信号不声称已一致。
匿名日期不能作为已验证真实时间间隔。不同来源数据不直接混用。

## 冻结分析

所有变换/质控拟合仅使用每人的session01 run01–04。run05–06为同会话独立query。
session02为日期隔离的validation descriptor，本轮参数已固定，不作模型选择；
session03/04为探索性测试，所有后续会话六run都评估。旧单人实验的后续run01保留划分
与本次不同，因此保留原结果，新配置单独执行，不能拼接成一个统一baseline。

仅运行轻量CSP+LDA冻结baseline，带通8–30Hz、4个CSP、Ledoit–Wolf与LDA自动收缩；
模型状态/训练ID/参数hash在query前后核验。无新EEGNet训练、适应策略或付费GPU。
CAR、窗口[0.5,4.5)秒、C3/Cz/C4、Mu8–13/Beta13–30和Welch250/125参数固定。
先按trial取ROI log功率，分别按任务/run平均，然后run等权；另记录算术功率。
task-window对比不是prestimulus ERD，也不被预设为学习指标。

协方差使用统一CAR坐标、trace normalization及5% shrinkage；PCA维数10和source scaler冻结。
会话独立PCA只作描述，不参与decoder拟合/选择。各类每run12个trial、六run144/session、
10种抽样的几何敏感性；QC共同run03–06尝试96/session。某人不满足条件，明确该指标不可用，
保留其已验证数据和其他指标，不临时减少trial数、删受试者或调整阈值。

## 统计与失败

参与者是独立单位。报告所有人的每session BA、confusion matrix、人数、trial数、
QC标记及失败；恒预测不能静默删除。run-bootstrap只是单人条件区间，群体摘要
重采样完整受试者四会话轨迹，10,000次(seed42)。主描述对比为session04−01的
BA和Mu任务差异变化，保留个体差异、零/负结果。

可探索每人首末神经变化与会话行为变化的关联，但10人不支持复杂混杂调整或因果解释；
不能把40个会话或几千trial当成独立n。多频段/几何检验是探索性family，报告不确定性，
不按显著性选结果。人类学习、历史在线decoder、总体漂移和固定读出分开解释。

行为已有明确subject/session、每session六个run百分比；均值不是pooled hit rate。
run顺序/分母/trial hit未核验，继续unresolved，不从百分比或分类输出造标签。
数据量扩大能检验跨人一致性，但不自动建立Learning-Preserving策略的因果证据。

失败下载、校验、读取、匹配、模型均保留记录。新输出目录禁止覆盖旧先导结果。
保存source/config/data/artifact SHA、实际runtime、Git状态、实验参数和纳入流图。

配置：[netbci_cohort.json](../configs/netbci_cohort.json)。实际验收以随后真实审计/结果为准。
