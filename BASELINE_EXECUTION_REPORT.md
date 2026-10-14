# Kumar CPU baseline: actual execution

18个发布编号的真实EEG计算已经完成，状态为
`completed_frozen_offline_protocol`，没有执行失败。原始版本为Kumar2024/NEMAR
nm000177 v1.0.5。新实验没有复用NETBCI分数或模型，未重新下载六库，未运行正式EEGNet。

性能计算前完成2,705文件官方校验、360连续信号复核、7,200源事件和全窗口数值副本审计。
7,156条完整5秒窗口进入张量，44条短事件保留身份并排除，不填充。源训练720条、
源验证360条、独立源query360条；后续support1,786条、query3,930条。1,512条完整
窗口超过固定250µV p2p标记，全部留在主分析。资格带有伪迹、年龄、群组与身份来源限制，
不等于专家认定的无伪迹神经信号。

在性能出现前冻结6个开发编号和12个最终测试编号、5秒/CAR/8–30Hz/128Hz处理、
CSP4/Ledoit–Wolf与LDA lsqr/auto。每个后续会话首run仅允许19或20个完整标记样本，
不借用过去或未来目标support；两种重校准看到相同的源训练及当前support。
参考和目标query、源验证从未参与任何拟合或参数选择。

根审查实际复核试次分区、官方来源、数值副本和freeze修订AST后，生成SHA绑定的
`protocol/independent_baseline_approval_20261013_run01.json`。实际串行CPU运行耗时
143.4927秒，OMP/BLAS线程数为1，seed42。18人×6会话×3方法共324行结果、12,870条
query预测，包含18个源模型及每人每个后续会话两种更新拟合。权重采用无pickle NPZ。

实际运行目录：`results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z`。
小型JSON/CSV镜像：`research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z`。
精确执行源码、配置、适配器、分区和核准回执的快照保留于该镜像`source_snapshot`。
源码祖先commit为`9aa580e5800245a1107b060fcdcba9807666ddca`，执行器SHA256为
`bf6bc4de396300c2f2430c8d42960eefdfaf50382d17e083a4c1846dabf736ac`；未提交工作并非
该祖先commit的全部内容，实际执行身份由冻结源码快照与逐文件SHA共同定义。

模型参数、trial角色、支持预算、源前后状态、预测、类别比例、召回和混淆矩阵均已保存。
三次目标会话类别坍缩保留，其中最终测试冻结模型两次；不是软件错误或删除理由。
独立复核使用另写的NumPy/einsum模型重放、混淆矩阵和参与者bootstrap，另行核实固定
功率/PCA/协方差变换，详情以`independent_review_run01_20261014`完成回执为准。

新增结果全部对象执行R2完整GET SHA256回验，固定前缀为
`few-shot-mi-eeg/experiments/kumar2024/nm000177/v1.0.5/cpu-baselines-20261013-run01`。
上传完成与目录计数以`R2_RECOVERY_AND_COMPLETENESS_REPORT.md`及不可变回执为准。
没有购买/创建付费算力；既有云服务与R2账号的实际账单未查询，不保证存储或请求零费用。
