# Task-Aware Adaptive Decoding for Longitudinal Motor-Imagery EEG

## 2026年10月24日：迁移至hpc_gpu1并手动授权GitHub

[更新与迁移入口](releases/paper2-hpc-v2-20261023/README.md)按作者最新要求，
单节点、一个作业总申请2GPU/24CPU/128G，每槽计划12CPU/64G。提交或释放作业前
隐藏输入GitHub token并实际核验写权限；之后约180秒自动同步进度及已完成指标。
自动识别本项目当前活动作业；若待调度则保留编号迁移，若已运行则TERM转发保存后等待退出，
仅从持久结果和断点继续。原科学任务、输入、数值线程和已完成项不变。
截图空闲节点0不能当作即时可分配资源；学校实际队列决定何时运行。

## 2026年10月24日：历史单作业配置（已由上方替代）

[已有安装的一行更新与恢复](releases/paper2-hpc-v2-20261023/README.md)
将24数组项合为1个Slurm作业，作业内最多2个独立GPU进程逐项取任务；
总申请2GPU/36CPU/128G，每槽计划18CPU/64G。最新256G内存申请已被学校调度器
明确拒绝，按作者新要求仅调整资源数；原QoS及内存拒绝记录均保留。QoS提交数拒绝
将保留原记录并按明确负向回复追加解析，数据、断点和私有授权均复用。
不再使用作业数组，不创建新科学版本，也不取消其他论文作业。


## 2026年10月24日：历史HPC入口配置（资源已由上方更新）

[本地初始化与短命令续跑](releases/paper2-hpc-v2-20261023/README.md)
优先使用GitHub官方API、raw备用，入口先保存在学校本地；不再每次先依赖raw取代码。
当前资源为`hpc_gpu`、每任务1GPU/16CPU/128G、最多2项并行，
通过伴随运行配置提交，原科学输入和断点身份不变。token仅保存在学校私有0600文件，
公开仓库不含值；首次实际写权限仍由原授权步骤核验。46项相关测试及完整125MB
API下载/本地不启动安装已通过；学校实际网络、调度与GPU未由本环境访问。


## 2026年10月23日：学校三A100研究扩展

[学校终端一行直接下载](releases/paper2-hpc-v2-20261023/README.md)：
代码、安装脚本及125MB输入均已提供GitHub路径，自动续传、拼接与SHA核验；
无需先下载到个人电脑，下载不依赖R2。

[一行启动／断点继续](experiments/hpc_recalibration_v2/README.md) ·
[新方法比较与文献依据](docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md) ·
[交付与验证](research_logs/paper2_hpc_v2_20261023/REPORT.md)。
独立V2比较同标签预算下的空间更新强度，以已有EA为强对照；3个单卡数组任务
并行，每项24CPU/128G，GitHub进度与训练分离。代码和输入包已准备，97项
针对性测试通过；真实学校GPU检查由首次分配执行。原论文、54模型和结果
保持原样，新实验尚无科学结论。本轮R2返回401，离线输入可直接上传学校。

## 2026年10月19日：高清图件与投稿系统摘要

[最新投稿辅助文件](manuscript/plos_one_submission_support_20261019/README.md)提供最新完整提交包、六张600 dpi原始TIFF图包、可放大的图件审阅PDF和与最新版正文一致的266词系统摘要。已测得作者提供的系统合并PDF将图件降为72 dpi；正文及原图数据不变。[核查记录](research_logs/kumar_submission_support_20261019/run01/README.md)明确系统摘要待替换、图件顺序及附件可核验范围。

## 2026年10月19日：投稿稿局部修订

[本轮修改与核验](docs/kumar_limited_revision_20261019.md)基于已提交稿对应的`19a5909`，按作者最新要求将现行伦理声明统一为第32条第（一）项法规豁免，删除学校确认；同时处理九项文字/方法说明/图表格式意见。原实验、统计数值与历史审计记录保持可追溯。[现行投稿文件](manuscript/plos_one_innovation_20261017/README.md)及[英文系统伦理声明](manuscript/plos_one_innovation_20261017/Ethics_Statement_20261019.md)为当前入口；下方2026年10月17日及更早记录保留其历史范围。

## 2026年10月17日最终投稿核查

[最新PLOS ONE核查与上传文件说明](docs/kumar_main_submission_check_20261017.md)：主稿声明位置、数据访问日期、图件及公开数据已核查。作者于2026年10月17日确认无法访问可识别参与者身份的信息；该事实已补入方法部分，官方Human Participants Checklist第3项已完成。当前提供正式主稿、完成版清单与短名图件上传包。

## 论文2：新增创新分析与完整投稿文件（2026-10-17）

[当前完整文件索引](manuscript/plos_one_innovation_20261017/README.md) · [带图阅读 PDF](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Reading.pdf) · [投稿 Word](manuscript/plos_one_innovation_20261017/PLOS_ONE_Manuscript_Submission.docx) · [中文修订与实验核验说明](docs/kumar_innovation_revision_20261017.md)。

当前题目为 **Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG**。引言明确列出四项贡献；新增逐试次错误转移、两类 recall、五会话均值及删除单个参与者的影响分析，形成6图6表。主队列额外空间增益为5.47个百分点，占总均值增益73.7%；所有新增数值均由保存预测复算。扩展S1 Data保留原69成员，并从实际新ZIP完成独立重放。下方日期版本作为历史材料保留，最新阅读与投稿文件以本入口为准。

## 论文2最新写作修订（2026-10-17）

[完整修订包与文件索引](manuscript/plos_one_revision_20261017/README.md) · [主稿 PDF](manuscript/plos_one_revision_20261017/PLOS_ONE_Manuscript_Revised.pdf) · [主稿 Word](manuscript/plos_one_revision_20261017/PLOS_ONE_Manuscript_Revised.docx) · [中文修改说明](docs/kumar_editorial_revision_20261017.md)。

新版题目为 **Updating spatial filters improves limited-label recalibration in a longitudinal motor-imagery EEG dataset**。主稿、S1 方法、S2 复现说明和附信突出同标签预算下空间滤波器更新的额外价值、纵向收益差异与短校准测量稳定性。现有结果表、图件和数据包保留。下方保留历史日期记录；当前写作版本以本入口为准。

[伦理版实际同步收尾](docs/kumar_ethics_sync_closeout_20261016.md)：固定`d03b5a3`已到main/研究分支/tag；5关键文件完整公开读回，324私有R2对象完整GET。

**2026-10-16伦理更新：**作者报告重庆医科大学科研处于2026-10-16确认本次二次分析免予额外伦理审查，无编号。新版[伦理声明/PDF/Word完整包](manuscript/plos_one_submission_ethics_20261016/README.md)与[实际确认和法规依据](docs/kumar_ethics_statement_revision_20261016.md)已形成；下方日期明确的“伦理待补”为历史状态，原科学结果与旧封存材料保持不变。尚未投稿。

## 最新论文审阅稿（2026-10-16 UTC）

[实际 main/R2 同步收尾](docs/kumar_review_revision_sync_closeout_20261016.md)：固定内容 `f2901de` 已公开；
本轮692个私有对象共89,459,262 bytes完整GET/SHA256通过，零失败。

[新版 PLOS ONE 完整包](manuscript/plos_one_submission_20261016/README.md) /
[带图 PDF](manuscript/plos_one_submission_20261016/manuscript_for_review.pdf) /
[Word](manuscript/plos_one_submission_20261016/manuscript_for_review.docx)。
已核验并逐条回应审稿意见，保留原科学结果，补充探索性配对检验、事件查找依据及支持数据。
[修订报告](docs/kumar_submission_revision_report_20261016.md)与
[当前状态](CURRENT_PROJECT_STATUS.md)说明真实完成和剩余事项。
限定 MIT/CC BY 4.0 已激活；作者已报告2026-10-16亲自核对并批准当前稿。
伦理批准已由作者报告，委员会/日期/编号与范围待补；见[状态补充](manuscript/kumar_author_review_addendum_20261016.md)。
冻结内容版本为 `paper2-plos-source-20261016`；旧稿及失败记录保留，未新训练或再次 query，未投稿。
下列早期进度按日期保留，不是新的执行授权。

**面向纵向运动想象 EEG 的任务信息感知跨会话自适应解码**

核心问题：**When should a decoder adapt to cross-session EEG changes, and does
task-relevant information explain performance changes better than total signal drift?**

## 当前进度：完整稿件与R2已同步

[最新同步收尾及审阅入口](docs/kumar_submission_sync_closeout_20261016.md)：
稿件固定提交`f735ffd1e49915e41f28b727f5d3279ad337c692`已实际推送并读回；
434个私有R2对象共82,392,690 bytes已完整GET／SHA256通过，失败0。
下列封存时的网络／审批阻塞保留为历史，当前状态以顶部入口及
[CURRENT_PROJECT_STATUS.md](CURRENT_PROJECT_STATUS.md)为准。未新训、未再次query、未投稿。

## 历史封存快照：论文入口（2026-10-15）

**[当前进度、论文状态及剩余事项](CURRENT_PROJECT_STATUS.md)**。
**[新PLOS ONE最终作者审阅包](manuscript/plos_one_submission_20261015/README.md)**
已完成主文PDF/Word、科学方法、审计复现、4张图、41成员最小数据包和未发送附信。
原54fit及一次query验收不变；本轮只对保存结果做探索性QC、任务时序及训练曲线核查。
已确认现有5秒窗是cue锚定，不能宣称全程持续MI；缺失类别后的QC敏感性仅10/12人。
机构认定、具体许可、最终作者批准仍待完成，未代作者投稿。当前GitHub写入审批策略
及Git/R2代理阻塞使新稿尚未实际同步远端；本地固定版本和离线交付包如实记录。
下文历史条目不作为新实验授权。

## 2026-10-15：冻结基线结果与query真实验收

Kumar的54项源模型和一次只读query评估已完成并获真实父侧确认，原源模型账本不变。
冻结EEGNet在固定剩余12人的目标BA为51.58%（参与者bootstrap95%区间49.08–54.51%），
接近机会水平；不据此生成门控或追选种子。现有CPU结果与EEGNet按相同query核对，
源validation选择及当前support标签预算差异明确列示，不能当成公平架构排名。
当前结果表见[CROSS_SESSION_RESULTS.md](CROSS_SESSION_RESULTS.md)，
英文事实性工作稿见[Kumar working draft](manuscript/kumar_longitudinal_decoding_working_draft_20261015.md)，
验收范围见[真实ACK](research_logs/kumar_frozen_query_acceptance_20261015/run01/REPORT.md)。
完整英文作者审阅包（PDF、Word、补充方法、三张图和核验文献）见
[manuscript/review_package_author_confirmed_20261015](manuscript/review_package_author_confirmed_20261015/README.md)。
作者已确认8项事实性声明；二次分析机构结论仍为尚无结论，不冒称批准或豁免。
下文历史状态按其日期保留；不存在待启动的已冻结源训练队列。

## 2026-10-13：转入 Kumar 跨会话基线研究

用户已将第二篇论文限定为公开多会话 EEG 的离线自适应解码研究，不依赖在线人体实验。
使用既有 Kumar2024 / NEMAR nm000177 v1.0.5，先冻结资格、预处理与时间顺序划分，
再实际执行 CPU 冻结 CSP/LDA、相同标签预算的读出重校准及 CSP/LDA 全部重校准。
正式性能、训练资格和失败记录分别以仓库根目录的
`KUMAR_MODEL_ELIGIBILITY_REPORT.md`、`KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md`、
`BASELINE_EXECUTION_REPORT.md`、`CROSS_SESSION_RESULTS.md` 为准。
EEGNet 的软件验收与充分训练分开报告；本项目不购买算力，不将离线结果称为神经技能保持。

现有六库、NETBCI 全19分析和已验证 R2 对象保持历史冻结。仅恢复已经授权的 MIND V4
未完成下载；Wang/Liu2026 原始归档和源审计已完成。新旧对象、断点、真实校验范围见
`DOWNLOAD_RECOVERY_AUDIT.md` 和 `R2_RECOVERY_AND_COMPLETENESS_REPORT.md`。
原 learning-preserving 方向及下文进展是历史研究记录，不是当前论文必须完成在线实验的要求。

本项目在现有科研分支上开展可复现的纵向 EEG 审计与探索性分析。仓库名称
`few-shot-mi-eeg` 不限定科学问题为 few-shot 分类，也不代表已提出或验证新算法。

## 2026-10-11：全部19个发布身份与公开资源扩容

全部19个发布身份、76会话、456 EDF 已完成官方校验、源事件/原始头文件审计和
冻结 CSP/LDA 分析。14,431源事件中14,429条满足完整5秒规则；两条末尾短事件保留。
全部信号数值审计发现跨身份复制涉及 sub-1、sub-6、sub-7、sub-15、sub-17。
原19身份诊断结果保留，另作排除全部五个受影响身份的14身份来源敏感性；
未发现 exact copy 不能证明实际生物学身份独立。

14身份末次−首次在线成绩均值变化 +15.41个百分点（bootstrap95%CI 11.53–19.33），
固定CSP/LDA BA变化 −4.20个百分点（−11.41–2.71）。两者不是同一端点，
不据此宣称人类技能保持或新算法因果效果。前十身份的新配置完整重拟合与历史16项
稳定产物逐字节一致。科学参数未重选，扩展属于观察十人结果后的探索性分析。

完整结果以[全19身份报告](docs/netbci_all19_results_20261011.md)、
[独立复核](docs/netbci_all19_methods_review_20261011.md)及
[执行配置](configs/netbci_cohort_all19_20261010.json)为准。
六库必要子集已实读审计和保存：10,253文件、7.83GB原始资源、1,473 EEG录制。
311只是逐库发布编号总和；来源资格、重复、人群和任务限制见
[扩容清单](docs/expanded_data_resources_20261011.md)。新库资源接入不等于模型训练。
实际Cloudflare R2上传及回读见[存储记录](docs/r2_research_storage.md)，
恢复入口为[当前交接](docs/CHAT_HANDOFF_20261014.md)。

## 2026-10-10 历史接续：十人队列

已沿用现有云端环境与 `research/learning-preserving-bci` 分支，完整读取旧聊天交接及其
状态快照后恢复相同的固定版本子集。十人信号审计已通过：40 会话、240 个 EDF、
7,577 条原始事件，其中 7,576 条满足完整 5 秒窗口，74 个通道的顺序跨人一致。
一条 2.968 秒 rest 事件保留在原始清单，按明确的
[分析窗口修订](docs/netbci_full_window_policy_20261010.md)排除出固定长度张量。
原始配置和失败记录保留；科学参数未重选，修订不称外部预注册。

十人阶段冻结证据以[十人报告](docs/netbci_cohort_results_20261010.md)、
[统一执行配置](configs/netbci_cohort_full_windows_20261010.json)及
[接续日志](research_logs/netbci_cohort_resume_20261010/)为准。
下文单人记录保留为历史先导阶段，不能与新队列拼接计算。

完整数值身份审计发现 sub-7 前三个会话与 sub-1 第四会话的六个对应 run 信号相同；
文件校验通过不保证采集独立。原十身份统计保留为算术结果，另有排除两个受影响身份的
八身份敏感性分析，不能把原区间直接用于论文的人群结论。
2026-10-11 接续将扩展公开数据并保存至已验证的 Cloudflare R2；
[存储记录](docs/r2_research_storage.md)区分对象核对与完整读取校验。

## 科学边界

区分解码器参数自适应、EEG 表征漂移、人类神经控制学习和行为表现。
离线分类准确率、PCA 子空间距离、协方差变化都不能单独证明人类学习或技能保持。
固定模型的跨会话 EEG 分类性能是 **fixed-reference decoding performance**，
不能直接称为在线无辅助独立控制能力。合成数据输出仅用于软件正确性验证。

## 当前基础

- 多受试者、多会话、显式采样率/通道的数据接口，以及不使用 pickle 的 NPZ 读写。
- 每 epoch 的平均参考与带通处理，FFT、Welch PSD、Mu/Beta bandpower、空间协方差。
- 训练分区拟合的 PCA、共同通道坐标中的子空间及协方差距离。
- MNE CSP + scikit-learn LDA；Braindecode 官方 EEGNet 的 CPU 基线封装。
- 受试者/会话隔离与固定参考会话解码评估；参与者级配对统计。
- 随机种子、配置、依赖版本、源码 commit 和逐受试者结果日志。

具体已运行检查及版本见 [环境报告](research_logs/environment.json) 和
[验证记录](research_logs/validation.md)。已完成 NETBCI2026 前十人的真实 EEG 访问、
MNE 读取检查及本地数据适配器验收；完整 EEGNet 训练、候选协同自适应方法以及在线人体实验
仍须通过 [路线图](ROADMAP.md) 的相应阶段。

## 数据接入优先级与实际验收

1. **NETBCI2026 / NEMAR `nm000305` 为第一优先级。**
   [官方入口](https://www.nemar.org/dataset/nm000305)、
   [可达下载 API](https://data.nemar.org/nm000305/)，固定公开快照 **v1.0.0**，
   DOI [10.82901/nemar.nm000305.v1.0.0](https://doi.org/10.82901/nemar.nm000305.v1.0.0)，
   数据许可 **CC BY 4.0**。公开目录支持按文件/受试者下载。历史首次访问仅下载 `sub-1` 的
   24 个 EDF（4 个 session × 6 个 run）及配套元数据，169 个文件共 **193,462,298 bytes**；
   校验和全部与官方 manifest 匹配。MNE 实读为 **74 EEG 通道、250 Hz**，
   事件为 **右手运动想象 vs 休息**，四个 session 分别 **180 / 179 / 180 / 178 trials**，
   合计 **717 trials**。随后扩展为公开编号前十人：**1,885 个去重文件、2,049,560,417 bytes**，
   官方校验全部通过。新协议重新分析十人，旧单人 3 epoch CPU EEGNet 只保留为最小软件验证。
2. **SHU / Ma2022 为第二优先级，原始接入状态 `pending author access`。**
   NEMAR `nm000288` publication pending；不继续请求该接口，不尝试破解 ZIP。
   保留左右手 MI、五日 session 的研究计划与通用数据接口。调整优先级前读取的
   Figshare v1 单受试者文件保留为历史探针，不作为 SHU 接入验收完成的依据。

NEMAR NETBCI 是经 MOABB 转换的 **EDF/BIDS derivative**，与原始 Dataverse
[10.57745/RBJRC7](https://doi.org/10.57745/RBJRC7) v2.2 的 BrainVision/MEG/行为侧表
必须分开记录。实际事件表是 `rest=1, right_hand=2`，与 NEMAR README 中的示例数字
映射相反；按真实 `trial_type` 与 EDF annotation 验证，不能硬编码 README 的数字。
`onset/duration` 为秒、`sample` 从 0 起，已按实际采样率与信号边界核验。
NEMAR 参与者表没有行为成绩；原始官方侧表提供每 session 的六个 run 命中率，
原始 sub-01 的 24 run 事件对应及十人的 240 个原始头文件来源已验证；未实读其余九人的原始 BrainVision 信号或 marker。成绩向量的 run 顺序、评分分母、逐 trial 命中和光标轨迹仍需确认。在线反馈实验及 EEG 跨天变化
不能单独证明人类学习、保持或新算法的因果效果。

详细来源、差异和检查结果见 [数据可行性](docs/dataset_feasibility.md)、
[来源与校验收据](research_logs/netbci2026_sources/access_receipt.json)、
[真实读取审计](research_logs/netbci2026_subject1_audit.json) 和
[可执行核查 notebook](notebooks/netbci2026_access_check.ipynb)。
本地复核入口为 `python scripts/check_netbci_subset.py --help`；默认不下载整个数据集。

## 安装与验证

当前冻结目标为 Python **3.11.16**，Linux x86_64，CPU PyTorch。
`pyproject.toml` 声明直接依赖，`uv.lock` 冻结解析结果和下载校验信息。
先安装可用的 [uv](https://docs.astral.sh/uv/)；本机已提供 uv。

```bash
cd /workspace/few-shot-mi-eeg
bash scripts/setup_environment.sh
export UV_PROJECT_ENVIRONMENT=/workspace/.venvs/few-shot-mi-eeg
export UV_CACHE_DIR=/workspace/.cache/uv
export XDG_CACHE_HOME=/workspace/.cache
export MPLCONFIGDIR=/workspace/.cache/matplotlib
export MNE_DONTWRITE_HOME=true
uv run --locked --all-extras pytest -q
uv run --locked --all-extras python scripts/environment_report.py
uv run --locked --all-extras python scripts/smoke_experiment.py --config configs/smoke.json
uv run --locked --all-extras python scripts/check_data_stack.py
```

一般本地 checkout 会使用 `.venv`；脚本自动选择路径，也可通过 `BCI_ENV_DIR` 指定。
直接使用 `uv sync --locked` 可安装核心依赖；`--extra deep` 增加 EEGNet，
`--extra data` 增加 MOABB，`--extra dev` 增加测试工具。完整验证使用 `--all-extras`。
所有训练变换仅在训练分区拟合。烟雾实验不访问外部 EEG 数据、不需要 GPU。

## 结构与资料

```text
configs/                     完整软件验证配置
src/learning_preserving_bci/  datasets, preprocessing, signal_processing,
                             neural_geometry, decoders, adaptation, evaluation, utils
scripts/                     环境安装、实际环境报告、端到端软件验证
tests/                       数据/频谱/几何/划分/基线/统计/日志的自动化测试
docs/                        研究协议、数据可行性、文献核验、代码复用审计
experiments/ notebooks/      实验门槛与探索工作约定
research_logs/               小型可审计环境与验证记录
results/                     本地结果（除说明外不入 Git）
paper/                       写作范围与证据门槛
```

- [研究协议](docs/research_protocol.md)：可检验假设、控制、端点、泄漏防范与统计单位。
- [数据可行性](docs/dataset_feasibility.md)：SHU 与 NETBCI 官方来源、许可、字段与访问限制。
- [文献核验](docs/literature_review.md)：EEG、fMRI 与侵入式动物记录的迁移边界。
- [复用审计](docs/code_reuse_audit.md)：第一篇冻结 commit、核实的依赖与许可限制。

第一篇仓库只用于只读技术参考；不会复制第一篇结果为第二篇发现。
未确认旧源码授权前不迁入旧源码。本仓库尚未选择对外源码许可证；
依赖与数据遵守各自许可证，公开可访问不等于无条件可再分发。
数据、权重、密钥和大型产物由 `.gitignore` 排除。

## 下一步

十人分析在同一新协议下重新运行，源端 ses-01/run-01–04 训练，run-05–06 为独立参考 query，
后续会话只评估冻结模型。已有行为按 subject/session 关联；具体 run/trial 研究仍待
评分分母、顺序和缺失原因验证。后续需专门验证测量可靠性、任务信息、伪迹/参考敏感性和
充分训练的 source-only baseline，再评估独立确认样本；SHU 保留 `pending author access`。
算法影响人类学习与 retention 的因果问题仍需前瞻性在线对照和独立保持探测。

## 历史单人先导证据（2026-10-10）

[完整审计、行为映射、Q1–Q7及下一步决策](docs/netbci_stage1_evidence_and_decision.md)；
[可执行分析](scripts/run_netbci_stage1.py)、[配置](configs/netbci_stage1.json)、
[已执行 notebook](notebooks/netbci2026_longitudinal_stage1.ipynb)。
仅1人717trial：会话几何差异可计算重放；CSP后续恒预测rest；短训练EEGNet只验流程。
行为subject/session可定位，run顺序/分母/trial outcome仍unresolved；不作人类学习因果结论。
论文工作稿与三篇原始方法精读见 manuscript/README.md（探索性工作稿，未达到投稿证据门槛）。

## 已有行为成绩的实际分析（2026-10-10）

[会话层行为—EEG报告](docs/netbci_behavior_session_analysis.md)已完成：原始19人×4会话×6成绩共456值，
均值54.11%→56.74%→62.15%→68.68%；末次−首次平均+14.57个百分点，配对受试者bootstrap
95%区间[10.71,18.27]，属于观察性行为变化。该历史阶段仅sub-1有已读EEG，四行会话级join已完成；十人队列另行汇总。
Mu任务差异与冻结解码结果已分别对照、计数/QC敏感性和精确重放已保存；不作学习因果或算法保留结论。
可运行入口为[分析脚本](scripts/analyze_netbci_behavior_sessions.py)、[配置](configs/netbci_behavior_sessions.json)
和[已执行notebook](notebooks/netbci2026_behavior_sessions.ipynb)。没有新增信号下载或模型拟合。
