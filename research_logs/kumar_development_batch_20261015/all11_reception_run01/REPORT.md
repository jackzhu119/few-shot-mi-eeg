# 剩余11开发fit：独立审计、原字节R2归档完成，待真实父确认

执行固定18cc7be472acc6c160117bbb9145b7aa2dfd2bdf，contract SHA256 e0ffcbddeacbc1569f44272dd92a7d53e7202391e6742f96983a356d4148fd75，run_id 602bc5ffcb6e4b6eb846d0e8b3b5c6e2。本地和远端接续检查均为该固定提交；既有7项accepted账本、科学源码及原未提交CSP文件保留。18/18开发fit已训练是6开发参与者×3seed，不是18个独立参与者；其他12编号及query/formal仍关闭。

收到原handoff压缩包1495420bytes，SHA256 0988286c0602cdfa6ae94c19a572ba759397a2404b300769101d945cd3355af9，37载荷另加manifest。原最终dispatch33326bytes，SHA256 faae3d1b651fc7008cdb71bef635f318ee0e8414bdf6ed83adb00d174cc598e3，104载荷另加manifest。全部路径、成员集合、长度和SHA256独立通过；只读取包内脚本以比对证据，不执行它们。模型tar、边界、回执、进展索引、dispatch和接收总包均原字节保存，未重新打包。

## 11模型的科学审核范围

既定audit_kumar_queue_bundle.py逐一通过11个原模型：固定job/source/config/split，checkpoint安全weights_only tensor/context/state和有限值，40 TRAIN/20源validation的trial身份及标签、逐epoch历史、最早最小validation选择、原patience15、固定输入身份、保存logits独立CE及原1e-7容差。原训练和完整history保留，未筛seed、删失败、补epoch或更改阈值。新增751epochs/2253steps，11个模型均为选择epoch后连续15轮未改善停止。记录的Torch源重放差均0；本侧保存logits重算最大绝对差3.24826470166073e-8，通过事前1e-7。

| subject | seed | epochs / steps | selected epoch | 源validation CE | 本侧独立CE绝对差 |
|---|---:|---:|---:|---:|---:|
| sub-7 | 20261013 | 95 / 285 | 80 | 0.658277869225 | 3.92646e-09 |
| sub-7 | 20261014 | 84 / 252 | 69 | 0.683486628532 | 2.84555e-08 |
| sub-10 | 20261012 | 16 / 48 | 1 | 0.693756639957 | 1.35956e-08 |
| sub-10 | 20261013 | 16 / 48 | 1 | 0.694139289856 | 1.56148e-08 |
| sub-10 | 20261014 | 66 / 198 | 51 | 0.690290284157 | 6.69388e-09 |
| sub-13 | 20261012 | 73 / 219 | 58 | 0.684431481361 | 1.57406e-08 |
| sub-13 | 20261013 | 49 / 147 | 34 | 0.690992403030 | 3.24826e-08 |
| sub-13 | 20261014 | 89 / 267 | 74 | 0.650327563286 | 1.30626e-08 |
| sub-16 | 20261012 | 86 / 258 | 71 | 0.640492129326 | 2.94532e-08 |
| sub-16 | 20261013 | 86 / 258 | 71 | 0.623508632183 | 1.76095e-08 |
| sub-16 | 20261014 | 91 / 273 | 76 | 0.600650191307 | 1.00468e-08 |

精确浮点值、checkpoint/原包SHA及逐job审计见model_audits/、all11_result_audit_run01.json和selection_and_replay_audit_run01.json；CSV只为审核索引。audit_refits=0，未加载原始EEG或query样本，未执行EEG forward或产生query成绩。源validation CE只是原早停与重放审计，不是最终泛化、技能保持或临床有效结论；后续汇总保留全部seed和负结果、以参与者为统计单位，不新增实验。

## 批次、离机门和历史暂停

独立边界审阅715项检查零差异；12个原边界/12个原回执全部成员和身份通过，11个嵌套原tar逐字节等于顶级原模型。6批按2+2+2+2+2+1固定顺序，intent回执先于本批训练、results回执先于下一批；claims及journal追加前缀、原7账本、150冻结文件/148旧源码闭包、17交付hash、127输入98743492bytes和每worker91包/原线程记录一致。11个唯一worker区间无重叠，锁继承与预算/超时记录通过；不把保存的区间记录当作连续GPU监控。

首次控制器01:32:33 UTC启动，首intent等待于01:42:36退出76，之前没有训练；随后同run --resume，不是new-run。原19800秒绝对期限未刷新，保存记录总elapsed5790.752857923508秒；最终2026-10-15 03:09:06.584152 UTC退出75，complete_exported。原exit76、resume日志和原始false阶段不重写。final state中11项trained/off_Pod_exported为真，independently_audited/R2_full_GET_verified/accepted原为假，这些历史值完整保留；当前审核与存储完成状态另用本侧回执证明。

12份回执的物理离机持有属dot明确声明，代码核对整包和全部成员。首次authenticated Jupyter上传及其余11次同authenticated终端返回的保存transport、SHA和原子发布记录已交叉核对。它们不是R2证明，当前R2状态来自下述独立完整GET。03:09:17的GPU空闲/剩余45675208704bytes仅保存的postflight快照，本侧未连接或观察Pod活状态。

## 私人R2原对象清单

使用当前既有安全注入权限，实际HeadBucket200后以原前缀few-shot-mi-eeg/experiments/kumar2024/gpu-development-20261014条件创建，不覆盖。11原模型沿冻结result_key命名；共享原对象位于bounded-batch-20261015/602bc5ffcb6e4b6eb846d0e8b3b5c6e2/。完整每对象key/长度/SHA/source映射见R2_object_inventory_run01.json。

| 原始对象类别 | 数量 | bytes |
|---|---:|---:|
| 独立模型原tar | 11 | 2058240 |
| intent/results边界原tar | 12 | 4495360 |
| 离机验证原回执 | 12 | 42337 |
| 原进展索引 | 1 | 12789 |
| 最终dispatch原包 | 1 | 33326 |
| 接收handoff原包（含顶层manifest） | 1 | 1495420 |
| 合计 | 38 | 8137472 |

38/38对象均完整GET、长度/SHA256一致，失败对象0，failures=[]；PUT/HEAD/GET通过，未新增或复制凭据。原始weights/二进制/EEG不进GitHub。r2_full_get_receipt.json为38663个UTF-8字节，其完整SHA256：

a6e68f3391fa732ff2b779417a9f6efb308a4d9fba4a65c0c465d4b757ff8cd9

## 当前接受状态与交接

11独立模型审计和全部原证据R2备份闭合，**待dot真实父确认**。accepted仍原7项，SHA256 94caad4e0eec18224ee4c93834c86ae951c8dbb29902972d0645651892f4a911。parent_acknowledgement_request.json绑定完整receipt和精确11job，proposed_acceptance_entries.json只是候选；没有创建后11父确认或追加accepted8–18，也没有调用任何训练入口、操作Pod、改科学配置/数值线程/预算、打开query或操作论文1。不要因旧门控仍指向第8而重训已经完成的模型。

dot应从本次返回固定提交读取逐模型/边界/dispatch审计及完整R2回执，独立核对原包后明确确认该SHA和11job；之后才能追加真实ACK与连续18项账本。未确认前不伪造accepted，确认后也不自动打开formal/query或新策略。frozen_analysis_readiness_run01.json仅索引现有冻结协议汇总材料，没有运行新的科学分析。原审计输出中创建于R2前的backup=False是历史值，不据其或离机标志推断当前存储状态。
