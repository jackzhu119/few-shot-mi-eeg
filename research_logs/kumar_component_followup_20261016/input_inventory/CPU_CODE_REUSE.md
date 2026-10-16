

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
