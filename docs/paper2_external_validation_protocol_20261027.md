# 固定外部数据集复核：空间滤波更新的同标签预算贡献

版本：`paper2-bnci001-component-replication-v1-20261027`。在读取本次外部预测结果前写定。
这是本仓库的带时间戳方案冻结，未声称外部注册。

## 问题与终点

在第二天只有20个当前会话标签时，重新学习CSP是否比只重学LDA提供额外解码收益？
本次唯一主要比较是 **Full CSP/LDA − LDA-only**。原Kumar研究的终点身份不变；
其+5.47个百分点仍为原次要比较，不能改称原预设主要终点。

数据为BNCI2014-001 / BCI Competition IV 2a，9名参与者、两天、每会话6个运动想象run。
仅左右手（原标签1/2），使用22个EEG通道，排除3个EOG通道，不重新参考。
它与Kumar是独立采集的数据集；论文1曾使用BNCI，故不称作者完全未接触的数据集。
本次9人逐一保留，不按解码分数挑参与者。

## 输入与固定分区

- 官方18份MAT：779,873,919 bytes。完整文件清单、长度及NEMAR冻结SHA在
  `experiments/external_validation_20261027/raw_manifest.json`。
- 第一天T的前4个MI run：96个左右手试次用于source fitting。
- T的第5个run：24个左右手试次留置，不调参；第6个run另存24个source-query，
  本轮不计算此额外终点。未将这48个试次拟合进source。
- 第二天E的第1个MI run：按采集顺序取前20个左右手试次作support；余4个左右手
  试次留置，不能转入query。第2–6个完整run的120个左右手试次为query。
- 每个原MI run有48个四分类试次、其中左右手24个。其余类别不进入拟合/评估；
  576个四分类事件/人的身份、角色和排除理由全部记入manifest。EOG校准run不计入MI编号。
- 先核实MAT结构，再分配身份。任何不符均保留异常，不静默少取标签或重排试次。

## 时间窗与信号处理

MAT的`trial`为1起始索引的试次开始，cue在其后2秒。固定取
`trial - 1 + 500 : trial - 1 + 1500`，250Hz下1000点，即cue后0–4秒。
这是本数据集自身说明中的MI阶段，未把Kumar的5秒导出窗搬来。
记录连续run上4阶Butterworth 8–30Hz SOS双向滤波，然后切窗；不跨run过滤。
双向滤波属于离线分析，不声称实时因果实现。原MAT微伏乘1e-6转伏，再存float32。
保留官方artifact标记，不按它删除试次、不按结果增加QC阈值。

## 四种固定方法

直接复用V2 `hpc_recalibration.classical`，不新写/搜索算法。
4个CSP分量、协方差固定收缩0.1、LDA固定收缩0.1、float64内部运算、固定log-variance。

| 方法 | CSP训练 | LDA训练 | 当前目标标签 |
| --- | --- | --- | ---: |
| Frozen CSP/LDA | source 96 | source 96 | 0 |
| LDA-only | source冻结 | source 96 + support 20 | 20 |
| Full CSP/LDA | source 96 + support 20 | 同一116试次 | 20 |
| EA-CSP/LDA | source/support各自EA后，同一116试次 | 同一116试次 | 20 |

仅后3臂拥有相同目标标签预算。冻结臂是零目标标签参照。
EA参考仅由source及当前support分别估计；不能用未标记query协方差作转导对齐。
LDA-only直接复用source滤波器数组；其与Full的拟合trial-ID列表必须逐项一致。
所有模型保存后才载入query评估。query只用于固定推理与预设统计。

**实现范围：** 本轮采用已完成V2的NumPy固定收缩实现，非原Kumar12人MNE/
Ledoit–Wolf实现的数值复现。source样本量、任务与传感器也不同。
所以检验的是组件问题在另一固定实现/数据集中的复核，不能把数据集差异单独解释为原因。
只运行这套指定实现，不在看到结果后切换到另一实现。

## 统计与完整性

每个参与者一份第二天query BA（两类各60；如实际缺类则记undefined）。
参与者为独立单位，不能把9×4方法或1080个试次当独立样本。

- 唯一主要比较：Full − LDA-only，双侧精确sign-flip，枚举2^9=512种符号，
  保留实际差值幅度；绝对均值统计量，包含边界容差1e-12 BA。
- 报告参与者配对bootstrap 10,000次、seed20261027、数值1–9顺序、百分位95%区间。
  该区间为逐比较区间，和精确检验分别报告，不互相替代。
- 次要族仅3项：Full − Frozen、LDA-only − Frozen、EA − Full；3项精确p用Holm校正。
  主要比较单独固定，不把原Kumar或已见V3比较补进本次新检验族。
- 报告9人各方法BA、各run的类别数/BA、个体配对差、正负人数及留一参与者均值范围。
- 9人未齐时只输出partial及已有记录；不对删减后的队列生成“完整验证”推断。
  所有负差、缺类、数值/存储失败保留。没有按结果选种子或新模型。
- 结果后用保存的label/prediction逐项重算BA，严格核对四臂query trial ID一致；
  不再forward。检查source与support和query整run隔离、模型fit-ID与输入hash。

## 运行、恢复和证据

经典线性模型使用现有CPU环境即可，不占用学校GPU，不操作Pod或已有学校作业。
使用单CPU库线程，现有内存；预期每次只载入1人的两份MAT。
18份raw约744MiB；准备输入约200MiB，首次需约1.2GiB可用盘。每份下载前保留100MiB余量。
先查看官方文件、许可、磁盘和一份原始样本结构；不下载完整未检查大归档。

```bash
/workspace/.venvs/few-shot-mi-eeg/bin/python -u scripts/run_paper2_external_validation_20261027.py --root /workspace/private_external_validation/bnci001-v1-20261027
```

同一命令为恢复入口；全局flock阻止重复并行启动。输入第一次SHA、后续仅改变文件重查，
不重复全套测试或全库扫描。来源与处理代码身份改变须独立版本目录。
源模型、每臂CSP/LDA及每评估分片均原子保存；已完成分片跳过。
USR1在当前原子工作后暂停；TERM/INT保留现场，无自动训练重试、不自动复活。
下载传输可重试/续传，SHA失败保留原件并停止；所有真实异常、运行时间及版本落盘。
本实现不设人工累计12小时限制；本轮是当前CPU的一次指定实验，不是无限搜索任务。

结果、模型、运行日志留在checkout外；Git只存派生预测/统计/图表与来源manifest，
不提交原始EEG或权重。R2只使用现有注入权限，上传原始证据包后完整GET/SHA核验；
不能把本地完成标志写成R2验证或父确认。尚未产生的结果不填到稿件中。

原始数据遵循其来源CC BY-ND 4.0，原创统计表/代码的许可不覆盖这些原件。
本次二次分析伦理声明沿用中国2023年《办法》第32条第（一）项的法规依据；
原数据采集伦理和法条适用是不同事项，不写学校确认或新增审批号。
