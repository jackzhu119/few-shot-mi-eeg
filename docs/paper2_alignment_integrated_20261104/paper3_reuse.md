# Paper3 reuse audit


审计实际时间见 SOURCE_SNAPSHOTS.json。论文3未作任何写入，未运行其分析器、训练器或预测器。来源正文/代码仅在 /tmp 阅读；仓库内保存来源身份、SHA、查重与重用账本。

## 固定版本与分支差异

- main：`0365324ebc244f947926a6d544f5fddd7a1bffd5`，与附件历史定位一致，包含两份整合稿。
- 默认协议分支：`research/paper3-protocol-v2-w0` → `ee733f364cbb93e7d1a7fd7edce94c49ea4e3a27`，无 manuscripts 目录。只读默认README会漏掉整合稿。
- R4：`c73778ff5d806bbc9db083d06ce3a34f900d4fb1`；R8：`8f922f765c0c8f87a4aba783cfd58c700ad73af2`；R9：`9a2f394b88c31d3e34934a8e629d18b2c73271d5`。
- results：`741b00e42a89b2dab5588183fb1397dc7192c8e6`。R9最新PAPER_DATA_LATEST指向29970df…快照，原比较表仍由manifest定位到3e799d…内容地址。指针、归档完成和科学完成字段保持不同身份。

## 已存在的论文2分析：A类

`manuscripts/bmte-error-redistribution-20261029` 已从论文2固定 `da2a3acee24746981bbcdd779ab88132da6e24c4` 导入传统管线结果。其manifest声明的Kumar预算预测gzip为262906字节，SHA256 `4a78be7079ac9104042afbb13b2ef0b906b41590ca93a7205616c67f2b59e3fa`。本轮已实际完整GET该远端原件，与论文2本地原件逐字节一致；36份BNCI原预测JSON也逐件完整GET并与本地原件逐字节一致。另三份预算/phase gzip的本地SHA与远端原始manifest一致；未把仅manifest匹配说成三份远端原件也已下载。

既存 EA−Full 错误转移：Kumar原主要12人，C=14.61477pp、I=9.31670pp、净增益5.29807pp；BNCI9人，C=12.77778pp、I=7.12963pp、净增益5.64815pp。此处仅记录已存在表格作为查重锚点，未重新计算科学结果。原表及代码包含每预算、会话、参与者结果。它们应在论文2被称为保存预测重放/扩展解释，不能称额外独立发现。新的W/H/两类召回/联合受益在所查BMTE分析器和schema中未实现，可由论文2自己的预测补算。

BMTE表为新增描述性bootstrap，seed20261029、10000次、Kumar ID按字符串字典序排列，且抽样流先经过其他神经队列。其CI与论文2历史seed42或数字顺序CI稍异是不同抽样身份，不应挑更有利者或覆盖历史CI。该脚本将D置为C+I；论文2新独立核查应从预测不同直接计算D再验证恒等式。

## 可迁移定义和机制辨析：B类

1. 可借鉴普通类别平衡C/I权重、participant-first汇总、概率与硬标签变化分离；本轮不复制代码，论文2可独立实现标准数学定义并引用来源。
2. R4清楚区分支持内交叉拟合、重代入及后续query，概率混合不等于logit或参数插值。作为未来方案；未在论文2执行。
3. R8区分映射强度alpha与协方差收缩eta；固定有效坐标系非常关键。Paper3的目标白化+源重着色服务于冻结EEGNet，论文2分别白化源/目标后重拟合CSP/LDA，两者不是同一处理路径。不得平移其矩阵参数或准确率。
4. Paper3 neural输入为clinic11/CAR10、128Hz、任务锚定[0.25,1.25)s及[0,1.5)s滤波上下文、采集位置预算。论文2Kumar为22通道/CAR21、5s cue窗；BNCI为记录参考22EEG、250Hz、cue[0,4)s和固定0.1收缩。任何实际预处理以论文2本地执行代码为准，不从整合稿的概括句推断；尤其Paper3补充材料跨四管线的通用RMS措辞不是论文2RMS已执行的证据。

## 不转为论文2新结果：D/E类

- BMTE整合稿的56人/5队列包含其他神经评估；Dreyer85人是单列源模型更替，不是EA目标校准验证，不能扩进论文2独立人数。
- ERFC、GP、Lie、Schur等贡献保留在各自论文；不拼入本稿。
- 已取得并按manifest SHA核验的R6/R8/R9原主要表分别16/40/24行。R6有NLL正向证据但BA方向并不随之改善；R8和R9所列原族没有p_holm<.05项。只作原方案的背景核对，不把其数值导入论文2。
- Paper3 source EEGNet曾使用BNCI源数据；不能把其同一BNCI参与者当未见外部验证。论文2单独CSP外部比较按原输入与划分解释。
- 两份整合稿与本稿之间有数据/分析重叠。相关稿件关系应透明保存在revision审计或编辑材料，不把同一预测再分析包装成首次结果。历史作者批准不转移为新整合稿批准。

## 许可与实际验收范围

GitHub metadata license为空，main/default根目录、两整合稿子树及pyproject未发现明确项目许可；本轮未复制论文3代码/文字，不给其虚构MIT或CC BY许可。论文2自己的原预测与工具继续按自己的许可范围使用；独立实现通用指标不以等待新许可作为阻碍。

实际通过：所取得文件完整SHA/已给Git blob核查、37个远端原预测文件对论文2原件的逐字节查重、其他3份本地输入对远端manifest核查、原比较表字段/行数/族身份检查。本轮没有运行来源保存的PASS脚本；其PASS仅作为历史记录读取，没有把旧PASS当成本轮实验通过。

Detailed [source ledger](../../research_logs/paper2_alignment_integrated_20261104/source_audit/paper3/reuse_ledger_fragment.csv) and [exact retrieval identities](../../research_logs/paper2_alignment_integrated_20261104/source_audit/paper3/SOURCE_MANIFEST.json).
