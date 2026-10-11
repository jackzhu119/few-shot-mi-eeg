# 第二篇论文：聊天接续总结与执行入口

> 本文件及 `research_logs/handoff_20261010/state.json` 保留 2026-10-10 原聊天结束时的历史冻结状态。
> 后续十人分析已执行，并发现跨身份与会话的真实 derivative 数值重复；最新接续入口见
> [2026-10-11 状态](CHAT_HANDOFF_20261011.md)、[十人结果与来源限制](netbci_cohort_results_20261010.md)。
> R2 现已完成认证、写入和回读核验；请不要继续按下文旧的“缺少密钥”状态判断。

更新日期：2026-10-10。用途：在删除原聊天前保存研究背景、真实证据、暂停位置和下一步执行顺序。

**接续结论：继续现有第二篇项目。10 人的必要数据文件已经下载并通过官方校验；2 人的真实信号已完成读取审计，共 1,484 trials；已有正式纵向分析仍只有 sub-1。10 人队列的新分析和群体结论尚未生成。19 人的真实行为成绩已经存在，不要再次把“取得已有成绩”作为启动分析的前置条件。**

本总结以本地文件、执行收据和重新校验为依据，不以聊天中的计划当作完成记录。机器可读快照见 [state.json](../research_logs/handoff_20261010/state.json)。未完成工作必须继续标为未完成。

## 1. 项目身份、研究目标与用户要求

| 项目 | 当前值 |
| --- | --- |
| GitHub | https://github.com/jackzhu119/few-shot-mi-eeg |
| 当前目录 | /workspace/few-shot-mi-eeg |
| 科研开发分支 | research/learning-preserving-bci |
| 本接续保存前的已提交基线 | 5825e10e3eddfee2e4cb6893866da0eb9204470b |
| 已完成基线提交内容 | 单受试者审计/初步实验、文献精读、19 人行为会话分析与严格 EEG 会话关联 |
| 当前科研标题 | Learning-Preserving Co-Adaptive Brain–Computer Interfaces |
| 中文方向 | 面向神经控制学习能力保留的人机协同自适应脑机接口 |
| 核心问题 | How should brain–computer interfaces adapt without compromising human neural skill acquisition? |

用户希望研究稳定神经控制表征、跨日期变化、固定与自适应解码器，以及即时性能和长期独立控制能力的权衡。当前阶段首先建立基础证据，尚未提出或验证新的 Learning-Preserving 算法。

用户最近要求扩大参与者数量，认为单人结果说服力不足。当前将第二篇 NETBCI EEG 扩展为公开 ID 顺序的前 10 人，不按行为成绩或 EEG 结果筛选。不能据此声称 10 人已满足高水平论文的功效要求。用户提到第一篇数据量不足，不构成修改第一篇仓库的授权；第一篇继续作为只读技术参考。

持续约束：

- 继续已有仓库和云端环境，不重新初始化、创建新仓库或另开付费资源。
- 不修改第一篇 jackzhu119/cross-subject-mi-eeg；复用经验与经核验的接口，许可未确认的自定义源码不直接迁入。
- 不开展大规模复杂模型训练；当前扩展方案只有 CPU 的基础分析及冻结 CSP+LDA，不新增 EEGNet 训练。
- 不把跨天 EEG 漂移、离线准确率、几何稳定性直接解释为人类学习、技能保持或算法的因果效果。
- 事件时间、通道、单位、事件数量均从实际文件核验，不猜测、补造或把设计数当实际数。
- 不按数组顺序虚构行为和 EEG 的 trial/run 对应；不由百分比、分类结果倒推 hit/miss。
- 保留每人、session、run、trial 和源文件身份；失败、未解决字段、代码版本、参数和校验结果均保存。
- 不覆盖旧结果；新输出目录必须使用新的路径。完成适当软件检查后提交到当前科研分支。
- 不发送作者邮件、不公开密钥、不绕过 ZIP 密码。仅在真实缺失信息妨碍具体问题时考虑联系作者。

开始更改研究假设前，先读 AGENTS.md、README.md、ROADMAP.md 和 docs/research_protocol.md。

## 2. 数据来源和优先级

### 第一优先级：NETBCI2026

| 来源 | 已核验身份与用途 |
| --- | --- |
| 官方 NEMAR 入口 | https://www.nemar.org/dataset/nm000305 |
| 下载 API | https://data.nemar.org/nm000305/ |
| 固定版本 | NEMAR nm000305 v1.0.0 |
| 版本 DOI | https://doi.org/10.82901/nemar.nm000305.v1.0.0 |
| 数据许可 | CC BY 4.0，使用时保留引用和转换来源 |
| 原始版本 | Dataverse DOI https://doi.org/10.57745/RBJRC7 ，已检查的版本为 v2.2 |
| 原始/导出区别 | 原始 BrainVision、MEG 和行为侧表；NEMAR 是经 MOABB 转换的 EDF/BIDS derivative |
| 任务 | 右手运动想象 vs 休息；不是左右手二分类 |
| 官方目录范围 | 19 人、每人 4 sessions × 6 runs，manifest 中共 456 EDF |

不要把公开目录中的 19 人等同于已读取 19 人；也不要把 sub-1 的 717 trials 当整个数据集。

原始归档约 49 GB。本项目此前只检查目录、侧表及代表性原始事件/头文件；本次没有下载整个原始多模态归档。新增 10 人的原始头文件用于核验采样率、通道和来源，不代表已经读取所有人的原始 BrainVision 信号或原始 marker。

### 第二优先级：SHU / Ma2022

状态保持 **pending author access**。MOABB 更新说明将 NEMAR nm000288 标为 publication pending，停止反复访问。Figshare 原始加密 ZIP 仍需合法作者访问，不尝试不可靠密码或绕过加密。

保留 SHU 五日期、左右手 MI 的接口及研究计划。历史单人 Figshare 探针不等于原始数据接入完成。目前 NETBCI 的公开数据足以继续现阶段研究，不需要为 NETBCI 工作先取得 SHU ZIP 密码。

若未来确实采用 SHU，向作者确认合法下载/密码、版本与许可、subject/session/run/trial 身份、事件时间单位和锚点、通道/参考/采样率及预处理；若研究学习，还需询问真实行为、反馈/解码器变化、训练和保持实验记录。

## 3. 当前真实数据规模：下载、读取、分析必须分开

本次总结前重新读取全部 10 人下载收据，并按官方 manifest 对当前本地文件逐字节复核校验。

| 层级 | 当前完成量 | 证据范围 |
| --- | --- | --- |
| 已下载并通过官方文件校验 | sub-1 至 sub-10；240 EDF、240 原始 vhdr | 1,885 个去重文件，共 2,049,560,417 bytes，校验失败 0 |
| 已完成真实信号审计和 NPZ 适配 | sub-1、sub-2 | 2 人、8 sessions、48 runs、1,484 trials；MNE 读取与事件/通道/保存校验通过 |
| 已完成正式保存的纵向分析 | sub-1 | 717 trials；旧阶段 PSD/几何/冻结解码最小实验及行为会话分析 |
| 已完成新的 10 人协议分析 | 0 人 | results/netbci_cohort_20261010 尚不存在；不能报告 10 人 EEG 统计或模型结果 |
| 已取得并分析的公开真实行为 | 19 人、76 个会话、456 个百分比值 | 各 session 六个报告的 run 成绩；不是 456 个已映射的 EEG trial |
| 已保存的 EEG—行为会话关联 | sub-1 的 4 行 | sub-2 和后续人的正式会话分析关联尚待生成 |

每人下载 manifest 是 193 项：164 个该受试者 derivative 文件、24 个原始头文件和 5 个共享文件。合计时应去重，不能把 193 × 10 说成 1,930 个独立文件。

### 已通过真实信号审计的两人

| 受试者 | 原始 ID | 张量形状 | ses-01/02/03/04 trials | 类别总数 |
| --- | --- | --- | --- | --- |
| sub-1 | sub-01 | 717 × 74 × 1250 | 180 / 179 / 180 / 178 | right_hand 360，rest 357 |
| sub-2 | sub-02 | 767 × 74 × 1250 | 192 / 192 / 191 / 192 | right_hand 384，rest 383 |

两人 derivative 均为 74 EEG 通道、250 Hz、V 单位，4 sessions × 6 runs。**不要把 sub-1 的每 run 约 30 trials 硬编码给其他人；sub-2 已显示不同数量。**

已保存数据位置：

    /workspace/few-shot-mi-eeg/data/netbci2026/nm000305/v1.0.0/
    /workspace/few-shot-mi-eeg/data/netbci2026/cohort_v1.0.0/sub-1/
    /workspace/few-shot-mi-eeg/data/netbci2026/cohort_v1.0.0/sub-2/
    /workspace/few-shot-mi-eeg/research_logs/netbci_cohort_20261010/downloads/
    /workspace/few-shot-mi-eeg/research_logs/netbci_cohort_20261010/audits/

已读 epochs.npz 的 SHA256：

- sub-1：c7081a3ae456c75dcfdd1dfbe9ec844bd38ba3ecc9c7f0d803c81972f9cd3ba0，与原单人 bundle 一致。
- sub-2：9d93282c28c825e017660399ad1e94c3ac79bfb3fcf9c35dd275094023691166。

原始 EEG、NPZ、权重等大型文件仍由 Git 忽略，**GitHub 保存代码、文档和收据，不包含这些本地原始数据**。在新聊天里先确认仍连接同一环境并检查文件，不要假设另一个环境能看到它们。

## 4. 事件、时间单位与数据格式：已确认的结论

- 实际事件为 rest=1、right_hand=2，以事件表 trial_type 和 EDF annotation 为准；NEMAR README 示例数字映射相反，不能采用示例硬编码。
- NEMAR 事件 onset/duration 为秒；sample 从 0 起。以实际采样率检查 onset、sample、边界和 EDF annotation。
- 旧 sub-1 原始 marker 从 1 起，duration=0；NEMAR derivative 提供 5 秒任务窗。它是任务/反馈相关窗口，不是独立的“纯想象”或原始刺激持续时间证明。
- 原始采样率可能约 249.9 Hz，derivative 为 250 Hz；记录头文件 SamplingInterval 和转换版本，不能把导出率当所有原始记录的实际率。新的每人头文件审计继续逐 run 检查。
- 当前 5 秒窗口为 1,250 样点的真实 slice；保留 source file、TSV row、session/run/事件身份。未因为设计数量补造缺失 trial。
- sub-1 原始版本本身有 717 事件；少于理想设计量的事件不能自动归因于 NEMAR 导出。缺失原因仍未全部确认。
- 初步分析的谱窗口采用任务内裁剪区间，不具备已验证的事件前休息基线；不能把 MI/rest 功率对比直接叫作经典基线归一化 ERD。
- 通道名字和顺序需审计后再比较，源版本的空白 reference 字段不是“硬件参考已独立核实”的证据。
- 已有 session 顺序支持纵向比较；真实日期间隔、疲劳、当日重校准、任务/反馈改变等应继续记录，不能把 session 序号当作固定天数间隔。

完整事件清单与来源对应保存在每人 audits/sub-N/events.tsv、run_inventory.tsv、original_header_inventory.tsv 和 audit.json。

## 5. 行为记录已经存在；真正未解决的是更细的映射

用户纠正过“联系作者补齐行为数据”的说法。正确事实：**公开原始 participants.tsv 已有真实行为成绩，可以立即做 subject/session 级关联与统计。**

原始文件：

    research_logs/netbci2026_sources/original_dataverse/participants.tsv
    research_logs/netbci2026_sources/original_dataverse/participants.json

表的官方 MD5 为 b9aa1c07015820e80bc79be6a61f30fc；字典的官方 MD5 为 41b33bc709e7b36a14faa91da128aaba。字典原始 JSON 有 trailing commas，严格 JSON 解析不合法；保留原字节，不默默修复后冒充原文件。

已核验字段为 BCI-Performance-session1 至 session4，每个单元格含六个 run 百分比。数据字典说明这些是在线移动光标任务中的目标命中百分比。subject 和 session 可明确定位，因此可以对同一人同一会话的六个值作等权描述性摘要。

| 关联粒度 | 当前可用性 |
| --- | --- |
| 原始 subject → NEMAR subject | 通过 provenance 中明确映射与原始头文件核验，不只靠补零猜测 |
| subject/session 的六个成绩及其平均 | 已可靠使用，可与同会话 EEG 汇总关联 |
| 成绩向量第 k 个值 → EEG run-k | unresolved；不能仅凭列表顺序声明已证明 |
| 命中率的分母、abort/剔除规则 | unresolved；不能据百分比反推命中次数 |
| EEG trial → 成功/失败 | unresolved；缺少已验证的 trial ID/时间对应 |
| 光标轨迹、逐 trial 反馈、decoder 版本日志 | 尚未验证可用 |

原始百分比可保留为“报告的 run 成绩向量”，但在 run 顺序未核实时不得关联到指定 EEG run 或广播成逐 trial 标签。未解决 run/trial 映射并不阻塞会话级工作。

19 人行为会话均值：54.1125% → 56.7445% → 62.1505% → 68.6809%。末次减首次平均 +14.5684 个百分点，参与者配对 bootstrap 95% CI [10.7063, 18.2662]。18 人增加，1 人下降；只有 4 人严格每次增加，14 人至少有一次下降，采用 0.01 pp 舍入敏感性时为 13 人。

以上是已通过真实记录验证的**观察性行为变化**，不是随机化算法干预效应。每个 session 可能重选在线特征/重校准；不能据此分离“人学会了”和“系统变化了”。

sub-1 的四会话行为平均为 73.8 / 90.4833 / 85.0833 / 89.2833%，每日在这 19 人中排名第一。单人 pilot 偏向高表现，不代表一般人群。

权威分析目录是 research_logs/netbci_behavior_sessions_20261010/run03_verified，精确重放为 run04_replay。早期 run01/run02 将“至少一次下降”误计为 15，已经修正为 14，并保留旧结果和原因，不引用旧错误计数。

实现模块 src/learning_preserving_bci/datasets/netbci_behavior.py 拒绝重复关联键和不可靠 trial/run 广播。

## 6. 已完成的单人 EEG 结果：可以引用的范围

旧报告见 [stage1 证据与决策](netbci_stage1_evidence_and_decision.md) 和 [行为—EEG 会话分析](netbci_behavior_session_analysis.md)。这些是 sub-1 的探索性观察，不能冒充新 10 人队列结果。

| 指标 | 旧 sub-1 四会话结果/解释 |
| --- | --- |
| 冻结 CSP+LDA Balanced Accuracy | 60% / 50% / 50% / 50%；后续会话恒预测 rest，失败案例已保留 |
| EEGNet 最小 CPU 验证 | 仅 3 epoch；50% / 55.67% / 54% / 45%；用于验证流程，不代表充分优化的深度 baseline |
| 会话 02/03/04 相对参考的匹配协方差 AIRM | 约 6.682 / 6.503 / 8.719，属于描述性距离 |
| PCA 子空间距离 | 约 0.675 / 0.664 / 0.671，不证明神经技能丧失 |
| 每会话 QC 标记数 | 0 / 0 / 2 / 53；后期伪迹敏感性不可忽略 |
| C3/Cz/C4 Mu 的 MI−rest 对数功率差 | 约 −0.792 / −1.058 / −1.857 / −2.197 dB；QC/等 trial 敏感性已保存 |

绝对功率与类别差异不是同一问题：该 pilot 的 Mu rest 和 MI 绝对功率均可能上升，而相对任务对比更负。因此不能只按某个功率差异讲预设的学习故事。

旧冻结模型划分和新的队列协议不同。旧后续 query 仅 run-02 至 run-06；新协议用后续全部六个 run。QC 拟合分区也不同。**新队列必须按统一新协议重新运行 sub-1；不得直接拼入旧数字。**

精确计算重放说明软件结果可复现，不代表已证明跨参与者或独立实验中的生物学重复性。run bootstrap 区间是给定个体和模型条件下的区间，不是人口置信区间。

## 7. 三篇 Nature 系列论文：已经阅读与尚未完成的内容

用户要求精读三篇、借鉴实验和论证逻辑写个人论文。已保存精读资料与英文工作稿，**尚未达到投稿证据门槛**。没有复制原文结构来填造结果，也没有重跑作者完整实验。

| 文献 | 已核验的方法启发 | 迁移限制/核验问题 |
| --- | --- | --- |
| Wang et al., Sensory-guided human-machine joint learning accelerates the acquisition of motor imagery brain computer interface control，Nature Communications，DOI 10.1038/s41467-026-75435-5 | 人体 MI-EEG、感觉引导、run 间 EEGNet 更新；无触觉 probes 和延迟测量；分开系统性能与用户学习 | 主试验最终 31 人，另有 8 人 EEGNet 对照，长期子集更小；触觉、训练政策和模型更新成分未完全分离；长期测试重新 calibration 不等于同一冻结映射保持。主文随机化与 Reporting Summary 表述冲突，当前源码与文中参数也有差异，保留 unresolved |
| Busch et al., Human learning of noninvasive brain–computer interfaces via manifold geometry，Nature Neuroscience，DOI 10.1038/s41593-026-02311-2 | 初期参考流形、不同控制映射、方向特异变化、竞争机制、旧 decoder 与新映射学习可能分离 | 是实时 fMRI，不是 EEG；主要 neurofeedback 分析 n=18；订阅主文完整 Methods 未取得，阅读公开摘要、完整补充方法、Reporting Summary、source tables 和作者实现。S14 符号、代码平均/最小距离、工作表名称不一致已记录 |
| Rajeswaran et al., Assistive algorithms influence neural representations in motor brain-computer interfaces，Nature Communications，DOI 10.1038/s41467-026-76109-y | 辅助政策可能影响任务信息如何分配；信息、总体方差、维数、参与贡献分别分析 | 两只猴子的侵入式 motor BCI，多 learning series 不是多个独立动物；不能把 EEG 传感器贡献称为神经元压缩，或把辅助撤回的动物结果当人体 EEG 因果证据 |

精读文件：

- docs/nature_joint_assistive_close_reading.md：Wang/Rajeswaran 主文、补充方法、报告表和限定范围的公开代码核验。
- docs/nature_geometry_close_reading.md：Busch 公开补充方法、行为/source tables、有限逐人统计重算及代码来源差异。
- docs/literature_review.md：文献身份、Data/Code Availability 与迁移边界。
- research_logs/nature_joint_assistive_source_checks.json 等收据：阅读范围和未解决问题，不等于作者实验复现。
- manuscript/longitudinal_eeg_working_draft.md：当前英文探索性单人工作稿。
- manuscript/README.md：稿件状态与证据入口。

独立切入点应是一个可证伪问题及明确对照：任务信息、几何变化、旧参考可读性和真实自主控制可能分离。使用 EEGNet、PCA、Riemannian geometry、Nature 方法或增加人数本身不构成创新。简单惩罚全部 drift 也可能限制有益学习。

## 8. 正在扩展的 10 人方案：已冻结的选择与参数

配置 configs/netbci_cohort.json，SHA256：
396c684415fe861301634a5089f3065bf036cb550aa7e90ec9d9178117642411。

协议 docs/netbci_cohort_expansion_protocol.md，SHA256：
1705e533179e0347b9c69989f568644b35c81c8d316829921eadb4fc9cfa7d5c。

新 EEG 读取前已保存配置/协议快照和 source_plan.json。已见过单人 pilot 和全 19 人行为，所以属于 pilot 后预先固定的探索性扩展，不是盲法确认性分析或外部预注册。

- 公开 ID sub-1 至 sub-10，每人四会话六 runs。下载预算新增约 1.86 GB，不扩到剩余 9 人/完整原始归档。
- 每人 source = ses-01 run-01–04 全部真实 trials；参考 query = ses-01 run-05/06；后续 query = ses-02/03/04 全部六 runs。
- ses-02 是 validation descriptor，不用于改超参数；ses-03/04 为探索性 test。保持明确时间顺序和不同日期角色。
- source-only 拟合 QC 阈值、scaler、PCA、CSP、LDA。平均参考使用审计通过的共同 EEG 通道；Helmert 坐标用于降秩参考空间；目标会话几何仅作描述。
- 谱参数：C3/Cz/C4；Mu 8–13 Hz、Beta 13–30 Hz；Welch 250 样点、125 重叠；任务内裁剪 0.5–4.5 秒。
- 几何：8–30 Hz、每 epoch 四阶零相位 Butterworth、协方差 trace shrinkage 0.05、PCA 10。
- primary 匹配：每 run 每类 12 trials，六 runs 得 144/session，10 seeds；QC 敏感性共同 run-03–06，96/session。
- 若任一预设匹配单元不足，则该指标 unavailable；不偷偷降数量、不按失败删除受试者。
- 冻结 CSP 4 components + LDA；记录模型前后 hash、constant predictions、每人每日期 BA、真实样本量和失败。
- 每人条件 run-bootstrap 500；群体参与者配对 bootstrap 10,000。参与者是独立单位，不用 trials、runs、日期或随机 seeds 虚增 n。
- 主要描述对比为 ses-04−ses-01 的 BA 和等 run Mu 任务差异；神经—行为变化关联为探索性参与者级分析。
- 不新增 EEGNet、复杂新算法、GPU、付费资源或人体实验。

## 9. 暂停位置与未完成代码

| 文件/阶段 | 当前状态 |
| --- | --- |
| scripts/fetch_netbci_cohort.py | 已实际完成 10 人下载；成功和失败收据均保留 |
| scripts/audit_netbci_cohort.py | 已实际完成 sub-1/sub-2；sub-3 至 sub-10 未执行 |
| scripts/analyze_netbci_cohort_subject.py | 代码和 9 项相关软件测试已准备；没有运行真实队列分析 |
| scripts/summarize_netbci_cohort.py | 初版存在，尚无真实 10 人汇总；当前没有专门的 summary 测试文件，需要补充关键统计/关联校验并核读 |
| tests/test_netbci_download.py | 15 项下载安全/校验测试 |
| tests/test_netbci_cohort_audit.py | 10 项审计测试 |
| tests/test_netbci_cohort_analysis.py | 9 项分区/冻结/QC/匹配测试 |
| README / ROADMAP 的队列进展 | 尚未更新为完整 10 人结果；旧段落记录历史单人阶段，不能据其忽略本接续中的最新下载/两人审计 |
| 新 10 人科研日志、图表、notebook、决策与稿件改写 | 未完成，应在真实分析完成后生成 |

当前本接续核验的软件检查：156 tests 通过，2 个已有 Braindecode deprecation warnings；ruff check src tests scripts 通过。软件检查不是新的真实 EEG 分析或科学结论。其余 smoke/stack 与归档校验记录见 research_logs/handoff_20261010/software_validation.json。

失败记录与注意事项：

- 首次下载严格比较 redirect URL 字符串而拒绝合法签名重定向，保留失败；后来只接受同一官方对象路径/hash 和受限 AWS 签名参数，收据不保存签名 query 值。
- 下载第一轮中断记录以及初始/修正客户端源码快照保存在 downloads/；不要删除这些失败。
- /usr/bin/time 不存在，曾 exit 127 且未运行审计；实际资源使用改由 Python resource.getrusage 记录。
- 新队列独立方法审阅代理遇到使用限额，未完成；不得称该审阅已通过。先前单人/行为阶段的审阅记录不自动覆盖队列扩展。
- 原生图与已执行 notebook 已核验；全页浏览器截图失败，不宣称浏览器截图验证完成。
- 交接核查曾误把下载 manifest 列表当字典，随后依据实际 schema 修正只读检查；这没有改变数据或产生分析结果。

用户要求总结后没有新启动真实信号审计、队列训练或下载。检查进程时未见这些后台科研任务运行。旧代理名/终端 session ID 不能当新聊天可继续执行的进程。

## 10. 新聊天接续的执行顺序

1. 先读本文件、state.json、AGENTS.md 和协议；核实分支、当前 HEAD、文件存在及 Git 状态。不要重建项目，不清理未确认的工作文件。
2. 确认仍能访问原云端数据。若数据目录缺失，明确区分“历史校验已通过”和“当前环境文件不存在”；从已提交 manifest 按同一版本重新获取必要子集，不虚报本地已有。
3. 串行完成 sub-3 至 sub-10 的真实审计，保存每人事件、run/会话计数、原始头文件映射、采样率、NPZ 和 hash；失败留下日志。不预设总 trial 数或所有人都是 717。
4. 所有 10 人审计通过后生成共同通道和计数汇总；确认列身份、单位、参考、缺失和各预处理差异。
5. 检查/完善汇总脚本的参与者配对统计、缺失指标、唯一关联、来源 hash 与失败处理测试，再串行按统一新协议运行所有 10 人（含 sub-1）。
6. 将 EEG 会话摘要与已有真实行为按明确 subject/session 关联；生成 40 行队列会话记录。run/trial outcome 仍 unresolved，不为继续项目制造标签。
7. 汇总逐人/逐会话结果及参与者级 CI，报告失败与离群、QC/等样本敏感性、within/between-session 可靠性。对新观察与计算重放、跨人一致性分别作判断。
8. 原生图、已执行 notebook、校验收据和科研日志形成来源闭环；保存小型结果和代码版本，原始数据/权重不入 Git。
9. 更新 dataset_feasibility、README、ROADMAP、研究决策和工作稿，并按 Q1–Q7 回答实际证据。完成必要软件检查后提交并推送当前科研开发分支，验证远端 SHA。
10. 只有离线基础证据稳定后，评估外部验证、充分训练的 baseline 和未来在线干预设计；不在本阶段直接实现/宣称 Learning-Preserving 新算法。

现有环境采用 Python 3.11 CPU、8 GiB 内存上限；审计和分析都串行，避免同时读取多个完整人的张量。下载流和小型表格工作可独立安排。两个已审计人的峰值 RSS 约 1.67/1.78 GiB，不把该数当后续模型运行的已验证内存占用。

可复用命令（执行前检查输出是否已存在，失败后选择新输出名）：

    cd /workspace/few-shot-mi-eeg
    export MNE_DONTWRITE_HOME=true
    export XDG_CACHE_HOME=/workspace/.cache
    export MPLCONFIGDIR=/workspace/.cache/matplotlib
    export OPENBLAS_NUM_THREADS=2
    export OMP_NUM_THREADS=2
    export MKL_NUM_THREADS=2

    /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/audit_netbci_cohort.py --config configs/netbci_cohort.json --subjects sub-3 sub-4 sub-5 sub-6 sub-7 sub-8 sub-9 sub-10

    /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/audit_netbci_cohort.py --config configs/netbci_cohort.json --subjects sub-1 sub-2 sub-3 sub-4 sub-5 sub-6 sub-7 sub-8 sub-9 sub-10 --aggregate-only --aggregate-output research_logs/netbci_cohort_20261010/audits/cohort_audit.json

    /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/analyze_netbci_cohort_subject.py --config configs/netbci_cohort.json --bundle data/netbci2026/cohort_v1.0.0/sub-1 --output results/netbci_cohort_20261010/sub-1/run01

最后一条需要对 10 人逐个运行，禁止并行加载。完成后才调用：

    /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/summarize_netbci_cohort.py --config configs/netbci_cohort.json --analysis-root results/netbci_cohort_20261010 --audit-root research_logs/netbci_cohort_20261010/audits --output research_logs/netbci_cohort_20261010/summary_run01

常规软件验证：

    /workspace/.venvs/few-shot-mi-eeg/bin/python -m pytest -q
    /workspace/.venvs/few-shot-mi-eeg/bin/ruff check src tests scripts
    /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/smoke_experiment.py --config configs/smoke.json --output results/NEW_UNIQUE_DIRECTORY/software_smoke.json
    /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/check_data_stack.py

当前实际依赖：Python 3.11.16、NumPy 2.2.6、SciPy 1.15.3、scikit-learn 1.7.2、MNE 1.10.2、Torch 2.8.0+cpu、Braindecode 1.2.0、MOABB 1.4.3。不能把论文/其他仓库的版本填进本机运行记录。uv.lock 与环境报告保存于仓库。

## 11. Q1–Q7：当前阶段性回答与下一步证据

| 问题 | 当前回答及证据等级 |
| --- | --- |
| Q1 可靠真实 EEG 到底多少？ | 已通过真实读取审计：2 人共 1,484 trials；已通过官方文件校验但待完整信号审计：另 8 人；已有纵向科学分析仍为 1 人。总队列实际 trial 数待审计，不猜测 |
| Q2 能否关联真实行为？ | 已验证 subject/session 粒度可用；已有 19 人行为、sub-1 四行正式 EEG join。run/trial 级仍无法核实 |
| Q3 NETBCI 能研究学习吗？ | 可研究观察性训练期行为轨迹、纵向 EEG 与固定读出关系；不能分离人和解码器学习，也不能证明保留策略的因果效果 |
| Q4 有可重复纵向神经变化吗？ | 单人指标及计算重放已验证；跨人的一致性、生物学重复性与伪迹独立性当前无法判断，10 人分析尚未运行 |
| Q5 固定解码器跨天如何？ | 旧单人 CSP 后续 50% 且恒预测 rest；3 epoch EEGNet 仅流程验证。新队列结果未知，需统一协议运行 |
| Q6 距真正创新还缺什么？ | 多参与者可靠神经指标、充分 source-only baseline、任务信息与噪声分离、明确反事实和独立行为端点；H1–H4 仍是假设，不是结论 |
| Q7 是否需要新在线人体实验？ | 若主张算法保留/促进人类技能并作因果结论，需要适当前瞻性在线对照证据；当前公开离线 EEG 不够。可先发表范围诚实且足够验证的纵向观察研究 |

H1：表征变化不完全等同分类准确率变化；H2：部分漂移与独立读出变化可能关联；H3：即时 accuracy 优化未必同时优化后续固定参考表现；H4：与已有可控表征一致的映射可能有利于长期稳定性。它们必须可被反证。

H3/H4 的人体因果验证至少需要：固定/常规自适应/候选策略的平衡随机分配或合适设计；匹配模型架构、更新/标签预算和反馈；在线 trial ID、真实轨迹/outcome、decoder 版本和辅助强度；立即和延迟关闭辅助/更新的 probes、transfer tests，以及伦理和事前样本量规划。

保持训练结束时“当前已学 mapping”的 retention，与回到最初 reference mapping 的 transfer/readout，应分别测量。旧 reference 分数下降可能伴随新 mapping 学习，不能自动叫作技能丧失。

## 12. Cloudflare R2：设置和真实连接测试

用户已创建 research2 桶；截图显示 S3 地址。程序使用的账号级 endpoint 为：

    https://aa9737d0102b08e0e7b25c9fac645f2f.r2.cloudflarestorage.com

Bucket 单独填 research2，region 用 auto。SDK endpoint 不附加 /research2。不需要启用 Public Development URL 来连接私有桶。

截至 2026-10-10 07:52:58 UTC，实际测试如下：

- 当前环境没有 R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY，也没有 ready 的云端 secrets/outbound identity。
- 使用保持代理和 TLS 验证的只读 unsigned ListObjectsV2 请求，max-keys=1。
- HTTPS 可达；实际 HTTP 400，R2 XML code=InvalidArgument，message=Authorization。
- **这是网络可达而认证未完成，不是已连接桶，也不验证桶对象或凭据权限。**
- 未上传、删除或列出真实对象；没有保存任何密钥。完整收据见 research_logs/handoff_20261010/r2_connection_check.json。

后续用户配置：Cloudflare R2 → Manage R2 API Tokens → 创建仅限 research2 的 Object Read & Write（只读需求可用 read-only）→ 在云端环境安全 Secrets 中配置 R2_ACCESS_KEY_ID 和 R2_SECRET_ACCESS_KEY。不要将密钥发到聊天、提交 Git，或用普通 Cloudflare API token 替代 S3 Access Key/Secret。

配置后先重新检查环境是否 ready，再用签名 SDK 请求测试 ListObjectsV2/HeadBucket；明确区分网络、认证、桶权限。是否上传 EEG/结果仍需根据用户实际指令和数据许可处理，本次没有上传任务。当前科研虚拟环境是否有 boto3 应重新检查；此前未安装。

## 13. 给新聊天的接续提示词

将下面这一段复制到新聊天，并连接现有仓库/云端环境：

> 请继续第二篇项目 jackzhu119/few-shot-mi-eeg，使用现有 /workspace/few-shot-mi-eeg、research/learning-preserving-bci 分支。先完整读取 docs/CHAT_HANDOFF_20261010.md、research_logs/handoff_20261010/state.json、AGENTS.md、README、ROADMAP 和研究协议，核查当前 Git 与本地文件，不重新初始化项目。当前 sub-1 至 sub-10 的必要文件已下载且官方校验通过，但真实信号审计只完成 sub-1/sub-2 共 1,484 trials；已有正式纵向分析只有 sub-1。请先串行完成其余 8 人审计，再按 configs/netbci_cohort.json 对全部 10 人运行基础表征和冻结 CSP+LDA，核验汇总统计与行为 subject/session 关联，保存失败、来源/hash、代码/配置及真实结果，更新 README/ROADMAP/可行性/研究决策后测试并提交当前分支。原始 19 人行为成绩已经存在，不要再次说需要联系作者取得已有成绩；run/trial 映射尚未解决，禁止按顺序、百分比或分类结果补造行为标签。三篇 Nature 方法精读和单人英文工作稿已保存，先读后继续，不能把借用技术视为创新或将 EEG 漂移当人类学习。不修改第一篇，不训练大型模型，不开启付费 GPU，不破解 SHU ZIP。R2 research2 只有 HTTPS 可达，缺少密钥，签名认证尚未完成；如用户已安全配置凭据，再做只读连接测试，禁止输出密钥。每一步区分真实已验证、探索性观察、理论假设和无法判断。

本文件与科研收据会保存到当前开发分支。删除聊天不会自动把其完整历史带入新聊天；接续依靠这份文档、GitHub 文件和仍可访问的现有云端数据。请先保存本文件链接或下载副本，再删除原聊天。
