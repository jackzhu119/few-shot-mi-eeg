# 论文1只读来源审计与最小迁移

实际固定来源：`jackzhu119/cross-subject-mi-eeg` main `c4ea1f4ee1d078bcb015922f8092f05e263f2399`。按README及research_runs索引精确取得小型许可、设计、执行身份、指标代码和来源表；未克隆历史、下载原始EEG、权重或完整预测包。

## 可用于论文2的内容

- **B：指标与核验工具定义。** 执行来源一致的`p1_train.py:88`和`p1_select.py:321`提供左右召回、BA、较弱类W、完整试次ID/标签覆盖检查、概率/logit一致性和左类平局规则。两个代码文件的完整SHA均与eligible-v3实际执行code_manifest一致。
- **B：联合受益的描述方式。** 先在参与者×种子（论文2还需会话）上计算非线性W/H，再按论文2原权重汇总。保留ΔBA/ΔW的正、零、负全分布，不把更弱类身份改变解释为两类均改善。
- **C：逐试次RMS的有限替代解释对照。** 来源只提供公式与许可；论文2必须用自己的通道/时间窗/分割实现，经既有V2/V3查重后决定是否拟合。未将论文1的18通道160Hz数组、源选择器或模型导入论文2。

**概率指标适配要点：** 论文1的CE是按试次普通平均，因外评固定每类40例而与等类平均一致；论文2类数可能不等，balanced NLL须显式按真实类别等权，不能只把该CE改名。论文1没有提供一个可直接宣称为论文2新算法的W/H方法。

## 已有结果不搬入论文2

- eligible-v3：108神经轨迹、9传统拟合，来源冻结`040956085499ed788948de0d5a09cddd9eabca56`；实际标签资格执行代码`0539379578818b3d71f995192e5e8a81cf4d5aef`。W+21.17pp/BA+5.85pp/66人联合改善是旧跨被试研究结果，不是EA效果。
- source-risk-v1：固定结果`2afb6c3eddbe2c3c82664b683f01970f95d4db39`。此路径在最新main不存在，但历史结果commit可读。只取得README及原归档SHA说明，未重新读取全部预测或从权重forward。
- 两者都用同85名Dreyer外评，不能算两批独立复现；Paper1的BNCI9源参与者也不是Paper2新增外部队列。
- composition-v2的630任务是不同后续设计。本次最新版本索引仅给出29October的189/630旧进度快照；未取得完整结果，不写成已完成或额外支持EA。

## 版本与缺口核对

最新IJBET README/RELEASE明确匿名全文另行交付；本次没有该完整最新稿，不能声称审阅了最新全文。取得的20October公开稿仅是历史方法参考。`version_inventory.md`与`.json`均已取得并核对。

预设SOURCE_EXPANSION设计计数2592/14592/33192与实际eligible-v3的2592/14590/33183不同，原因是已获批准的native1/2标签资格修订；实际study.json、registry及execution_identity已取得。不存在把设计清单人数/试次数当已验证输入的理由。Paper2继续按自己的冻结资格与20标签预算。

## 许可与实际验证范围

作者原创代码MIT；自有文稿、图表与派生输出CC BY4.0；原始EEG及第三方材料保留原许可。镜像小文件位于`files/`并保持原始字节，MIT及许可范围随来源保留。生产分析如采用实质代码，应注明来源commit/路径及变更；本审计本身未把外部代码导入训练或评分。

`retrieval_manifest.json`逐文件记录固定commit、SHA256、Git blob SHA1、实际取得状态；`reuse_ledger_paper1.csv/json`给出A–E分类和完整协议上下文；`protocol_context.json`记录数据、采样、参考、窗口、归一化和统计权重。`VALIDATION.json`为本次实际字节检查，不把读取旧PASS当成新科学重放。

附：Paper1版本清单自身记录了可选S29−S9 BA受益/平局计数在两张旧表间的阈值差异未独立解决；该项不用于Paper2，也不把它改写为已解决。较弱类定义与主要S60来源映射不受该可选计数问题影响。

## Public delivery boundary

The acquired source bodies remain in the local `files/` audit cache. This revision publishes their immutable URLs/commits, byte hashes, scope and reuse records, rather than redistributing whole source manuscripts or foreign training scripts. Actual local retrieval/SHA validation is distinct from public archive contents.
