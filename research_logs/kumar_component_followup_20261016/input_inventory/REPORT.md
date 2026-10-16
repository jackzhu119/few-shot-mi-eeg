# 新组件/标签预算分析：只读输入与执行依据清单

库存时点：2026-10-16T03:01:01.743678+00:00；checkout `1a7e1ab8b6253db52544ba185abb33a6bcb4937b`。已完整读取用户新粘贴任务，保持原18身份、6开发/12主分析、原主要/次要比较和全部历史结果。当前工作仅为新探索方案的输入、代码和资源准备；未运行任何新科学统计、fit、EEGNet训练/forward或query。伦理处理由父任务优先完成。

**本地资料足够准备原cue锚定5秒窗的CPU预算入口；不能由此宣布任务活动期窗口映射成立。** 2705文件全部存在且大小相符，360 EDF共1,778,578,770 bytes；2345 metadata文件重新做字节/官方校验均通过。为遵守本次只读边界，未打开EDF/GDF/NPZ/checkpoint字节，故不声称当前原始信号/模型文件已重新全SHA验证：其完整既存哈希均可取得，未来获准执行前仍须实读字节校验。

## 文件与trial范围

原始目录：`/workspace/few-shot-mi-eeg/data/public_eeg/kumar2024/nm000177/v1.0.5/`。固定全量选择清单为`/workspace/few-shot-mi-eeg/research_logs/public_data_expansion_20261010/kumar2024_nm000177_v1.0.5_selection_manifest.json`，2705文件/1,781,052,841 bytes。逐文件绝对路径、expected/actual bytes、存储checksum、metadata fresh SHA和验证范围见`source_file_inventory.csv`；无缺失、大小错配或metadata checksum失败。

| 冻结scope | 实际manifest路径 | 文件/EDF数 | 范围bytes | manifest完整SHA256 |
| --- | --- | ---: | ---: | --- |
| development_source127 | `/workspace/few-shot-mi-eeg/research_logs/kumar_pod_rebuild_recovery_20261014/frozen_inputs_127.json` | 127/18 | 98,743,492 | `02f12e205250a0b8e1848efe32fbf9f887526b4b8dd0a58e16d3a8780c040b08` |
| remaining_source253 | `/workspace/few-shot-mi-eeg/research_logs/kumar_checkpoint_reuse_preparation_20261015/proposed_remaining_source_inputs.json` | 253/36 | 196,740,994 | `312b5bd38995aac5fd7748b64cdf5c0446b5e33fe05e3970c61b5dd73e026682` |
| query1189 | `/workspace/few-shot-mi-eeg/configs/kumar_frozen_query_inputs_20261015.json` | 1189/216 | 1,043,686,331 | `4636a83e6be52c8e06de089ec2cc866e2008f6f17412b8d820dc62234999f76f` |

127是开发6人的source ses-0/run-0,1,2：TRAIN40+validation20，18 EDF；253source是remaining12对应36 EDF，均不含source-query或任何target signal。1189query清单含216 EDF，scope为ses-0/run-3及target非run-0；不含target-support，另带全六session scans元数据。三份清单所有文件现均存在、大小匹配，其文本metadata SHA与清单一致；EDF只比stat和既存SHA，未读取原始字节。这些旧proposal/operation状态不是本轮授权，不改旧execution开关。

原split：`/workspace/few-shot-mi-eeg/research_logs/kumar_cross_session_20261012/protocol/split_manifest.json`。7200trial行，7156 included、44partial保留。metadata字段明确subject/session/run/source_row/trial_id/label/start_sample/stop_sample/role/cohort/included/raw与processed数值hash。实际角色覆盖：

| 角色 | 全部事件 | included | 固定来源 |
| --- | ---: | ---: | --- |
| source_train | 720 | 720 | ses-0 run-0/1，每人40 |
| source_validation | 360 | 360 | ses-0 run-2，每人20；CPU拟合/预算不得用 |
| source_query | 360 | 360 | ses-0 run-3；原结果可复用 |
| target_support | 1800 | 1786 | 每target session run-0，实际19或20，不替补partial |
| target_query | 3960 | 3930 | 其余target runs |

360 BIDS event TSV重新校验字节并数行：7200行；列均`onset,duration,trial_type,value,sample`，value仅1/2、trial_type为left_hand/right_hand。文件级SHA和字段见`bids_event_tables.csv`。它们不是完整原始POS/TYP阶段序列；本库存没有加载任何GDF或确认cue→task-start/end逐trial映射。原始阶段窗实验仍依赖父任务单独验证的mapping及新方案，不能用固定偏移替代。

## 现有cache、模型与保存预测

- 六人restricted cache根：`/workspace/few-shot-mi-eeg/research_logs/kumar_cross_session_20261012/csp_development_epochs_run01_20261014/`。每人`restricted_epochs.npz`、`included_trial_metadata.json`、`subject_receipt.json`及根preparation receipt均在。六tensor压缩文件共43,786,391 bytes；保存shape为139/140×22×640 float32。总836trial=240sourceTRAIN+596support，零validation/query/remaining身份。六metadata fresh SHA均匹配receipt，tensor只stat+引用原SHA、不打开数组。它们可用于原5秒窗开发support信息，不能作为18人/所有query或新活动窗cache。
- 原CPU output根：`/workspace/few-shot-mi-eeg/results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z/`。execution receipt列617 outputs，均存在；文本CSV/JSON已fresh hash匹配原receipt，NPZ只stat+引用原SHA。每人`source_before.npz`/`source_after.npz`保存source CSP/LDA状态；`fixed_features.npz`保存trial IDs、label、44power/PCA4/covariance diagnostics；`feature_source_fit.npz`含拟合变换参数，保持私有。**source arrays具备可复用接口和完整原哈希，但本库存未打开或重新认证其数组内容；新入口必须先校验文件SHA、array keys/shape/classes、before/after绑定再用。**
- CPU三法原预测直接读`/workspace/few-shot-mi-eeg/results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z/query_predictions.csv`，同字节mirror在`research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z/`。原窗口/相同trial及参数下，完全冻结和两更新法full-support可复用已有逐trial预测，避免新forward或重fit；新k分支与EA不能假称已有结果。必须对trial ID、标签、session/run/role及query集合做严格join；不能只按行号或summary近似值拼接。
- 全方法/seed已保存公开预测：`/workspace/few-shot-mi-eeg/research_logs/kumar_submission_qc_20261015/run01/public_inputs/saved_predictions.csv`，2,749,957 bytes，SHA`1e9353d684d45897ded23de11d79fa4a4d2f4be7f70b2b0c1cf1ed388762f148`，25740行=4290query×(3CPU+3EEGNet seeds)。EEGNet54保持复用这些预测，不重训或再query。配套frozen_trial_metadata 4,154,981 bytes/hash`405706d70ab51027aeaadf02d0b54a2ee4b89cb09eab7ce15ebf68e20b82693a`。
- CSP run02根：`/workspace/few-shot-mi-eeg/results/kumar_csp_signed_score_20261015/run02/`。其**253输出**（26,108,327 bytes）与上表253源输入不是同一scope：240fit NPZ、6selected feature/score NPZ、6subject JSON、1measurement JSON，均存在。每人`selected_CSP_features_and_frozen_scores.npz`已存trial IDs/labels/log_CSP_power4/source_standardized_CSP4/frozen_source_LDA_scores，亦混有scaler参数；只在原836-trial开发范围有效。本次没有打开数组。公开`scientific_summary_from_saved_results.json`与既有measurement文本可检查phase/source/support诊断，不能当新gate输入的确认性证据。

全部617CPU+253CSP输出的存在/大小/既存SHA及文本freshhash在`saved_artifact_inventory.csv`；新增保存预测与accepted54 plan/checkpoint-metadata的精确路径/bytes/SHA在`inventory_manifest.json`。未解包或加载任何54模型权重。

## 可直接复用的代码与不可绕过的限制

| 功能 | 函数/文件与当前行号 | 静态事实/复用条件 |
| --- | --- | --- |
| 固定角色 | `datasets/kumar.py:57 role_for` | 源TRAIN/validation/query及target support/query按whole-run固定。 |
| 预处理 | `datasets/kumar.py:68 preprocess_epoch` | 硬限制22×2560/5s/512Hz；CAR→4th-order8–30Hz Butterworth SOS zero-phase default odd→resample_poly(1,4)/Kaiser5→22×640 float32，单位V；不拟合跨trial状态。 |
| 学习访问许可 | `datasets/kumar.py:122 allowed_fit_trial_ids` | 仅sourceTRAIN与当前session support；不同component规则；排除validation/query。预算前缀需在这个允许集合内再严格取时序subset，不能扩集合。 |
| 实际loader | `datasets/kumar.py:146 load_subject(...,allowed_roles=...)` | 每文件官方字节校验、MNE preload=False、完整连续信号16384-sample blocks审计，再取trial窗/核raw与processed hash；同人串行，末尾与split每字段匹配。新预算可限制roles到TRAIN/support/target-query，不能让source validation20进入fit。 |
| CSP/LDA factory | `decoders/csp_lda.py:8 make_csp_lda` | CSP4/Ledoit-Wolf/log=True/norm_trace=False/average_power；LDA lsqr/shrinkage=auto；factory random_state只留API、不驱动随机抽样。 |
| 原三法 | `run_kumar_baselines.py:329 run_participant`、nested`guarded_fit:354` | sourceTRAIN40; LDA-only保留source filters并在40+当前support重fit LDA；full同集合重fit两段；forbidden含全部query+validation，禁止过去/未来support。函数同时进行所有旧预测/审计，不适合作为新budget循环直接调用。 |
| pickle-free source复用 | `run_kumar_baselines.py:87 model_arrays`、`:101 predict_from_arrays`；`analyze_kumar_csp_signed_score_v1.py:127 csp_features_and_scores` | 原source NPZ具备filters/coef/classes等；feature为ln(mean squared projected amplitude)，score=f@coef+intercept，阈值0。未来可只读已核SHA的arrays，对support/TRAIN变换；不要反序列化pickle或手改旧CSP状态。 |
| 时序支持/phase | `analyze_kumar_lowdim_reliability.py`的`chronological_indices`；signed-score`:155 source_phase_alignment_control`、`:310 support_measure`、`:339 support_phase_alignment_control` | 可复用严格时间排序和只读signed-score定义；旧phase诊断不是新预算/EA/门控模型授权。 |
| 旧执行门 | `run_kumar_baselines.py:484 approval_gate`、`:516 validate_effective_configuration`、`:621 main` | approval必须绑定原config/split/protocol/source_gate hashes，输出/mirror必须新建；硬常数不容新窗口预算偷偷复用。新独立脚本应绑定新冻结方案、原输入/模型/预测SHA，保留旧门与原输出。 |

所有源码完整SHA及AST函数签名/行号见`cpu_code_sources.json`。本次只parse源码，没有import执行这些scientific模块。

## 资源与单subject内存预算

资源实测：workspace可用4,625,616,896 bytes（约4.31GiB）；cgroup上限8,589,934,592 bytes（8GiB），当前1,551,851,520，headroom约6.55GiB；host MemAvailable约8.77GiB，swap0。/tmp为单独挂载，不能拿它绕持久输出空间门。已安装Python3.11.16/NumPy2.2.6/SciPy1.15.3/sklearn1.7.2/MNE1.10.2/pyriemann0.12，无需为库存安装依赖。

以下是shape×dtype的静态估算，**不是新的实测peak RSS或可直接开跑证明**：

- 单raw epoch22×2560 float64=450,560 bytes≈0.43MiB，reference/filter各再一份；SOS padded workspace及resample另需小倍数。
- loader完整连续审计block22×16384 float64=2,883,584 bytes≈2.75MiB，不preload整run。
- 最大400trial subject processed float32=22,528,000 bytes≈21.48MiB；chunks+stack短时约42.97MiB。runner上转float64再45,056,000 bytes，与caller tensor共约64.45MiB。
- 原descriptive_features的21channel projected和centered每份43,008,000 bytes≈41.02MiB，另Welch/covariance临时数组；预算runner无须为了门控新计算query-based drift。
- 最大union40+20的float64 fit input约6.45MiB，另CSP/LDA线性代数buffer与Python/MNE库开销。串行一subject、thread1，2GiB consumer RSS guard仍应保留；不能把上面数组加法当进程峰值上界。

旧操作门为：启动effective available≥3GiB、output free≥2GiB；运行consumer RSS≤2GiB、cgroup与host余量各≥1GiB；poll0.25s、timeout7200s、TERM grace30s、automatic retries0。它们属于旧冻结operation，**不修改、不重开旧claim、不禁用**；新CPU合同须显式承接这些限制。当前库存判断新输入不缺盘，但预计输出/备份必须先列大小并在未来执行时重新检查。

## 给父任务冻结新CPU方案的直接依据

1. 原5s窗口下预算prefix只能来自当前session既定included support，按真实acquisition/start_sample/source_row顺序取前4/8/12/16/full；full逐session记19或20。sourceTRAIN40始终两类，故support前k缺类只记录flag/counts，继续在40+k union拟合，不补query标签、不重采样、不移除这些预算点。仅明确union不可估/缺类或预先列出的科学数值失败才可fallback原sourcefrozen；存储/hash/意外ValueError必须停。
2. 完全冻结与两旧更新法full-support从保存预测直接复用；sourcearrays从原NPZ只读复用之前仍做完整字节hash/schema/原source-frozen绑定，避免重做source fit。新label budgets与EA结果本次尚未生成。
3. 父任务最新建议EA只固定一种实现：H=Helmert21×22；centered covariance/ddof1、不trace normalize/learnedstandardize；在21basis估source40与当前prefix各自mean covariance，float64 eigh/invroot，回嵌`H.T @ R21^-1/2 @ H @ X`保持22channel CSP输入。source对R_s，target support/query对R_t；query只transform，不进入reference。eig≤0或condition>1e12为预定义EA数值fallback，不能调ridge或按结果换21/22。此处只是拟冻结接口依据，未实现/实算或宣称等价复现原论文。
4. 任务阶段mapping成立后的新窗必须另newloader/newmetadata/newfrozen hashes，不能修改旧adapter5秒常数或把旧cache裁一下就宣称phase验证。

这是一份输入/资源/代码inventory，不是新科学运行授权或新结果。父任务确认方案和接口后才接最小独立入口及synthetic tests；没有任何实际新CPU拟合/query被本报告释放。
