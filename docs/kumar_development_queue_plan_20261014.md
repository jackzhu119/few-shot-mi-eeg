# 冻结开发源域 EEGNet 队列方案（不执行）

操作配置：configs/kumar_development_queue_plan_20261014.json。科学配置保持SHA256 14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d 不变；配置内旧budget运行状态作为历史保留，本次调度状态另存操作配置，不改训练参数。复核命令：

    python scripts/check_kumar_development_queue_plan.py

固定顺序为 sub-1、sub-4、sub-7、sub-10、sub-13、sub-16，每人 seeds 20261012、20261013、20261014。18个身份组合中首个复用已经备份且父确认的结果，不重训，其余17个为尚未执行。编号和种子来自先前冻结配置，不按首fit损失筛选。非开发组正式门保持false，支持集和query不参与本队列训练或选择，不形成完整EEGNet基线结论。

## 释放条件及去重状态

当前 execution_enabled=false。先收到首次无拟合重放，按预设容差通过、R2完整GET并父确认，然后父对话才能排期。当前文件为操作规范与静态检查器，不是已获执行授权的训练队列runner；下一版本单fit执行器必须落实以下约束后固定提交供审阅。禁止用旧run_kumar_gpu_source.py或旧首fit入口绕过本次释放条件。

每个job_id由subject、seed、科学config SHA256及split SHA256的排序canonical JSON计算；已完成sub-1/20261012的key及完整权重身份继承旧记录。共享 /workspace/research-gpu.lock 使用非阻塞flock，确认nvidia-smi无其他计算进程；父对话的跨论文排期仍是必要条件。获取锁后，独占创建job_id预约，不以临时PID消失为重训依据。一个Pod同时最多一个fit，不循环自动重试。

单fit状态依次为 planned → reserved → fitting → fit_saved → archive_local → R2_full_GET_verified → parent_acknowledged。每步追加不可覆盖事件，包含UTC时间、固定Git commit、config/split/input哈希、job_id及本地输出路径。失败记录保留在对应状态，不能伪造后续状态。state文件和结果只能在持锁时独占创建/原子落盘；不删除原预约来解锁任务。

每fit保存weights.pt、绑定context的weights.json、fit_result、原始stdout、输入审计、冻结配置/源码、源验证重放结果及逐成员manifest。fit_result只代表拟合已落盘，不能代表备份闭合。首次完成的选中权重用于后续复用。当前训练函数不保存中途optimizer/RNG状态，因而没有宣称支持中途精确续训；中断需保留所有文件并审查，不自动从头重跑。

## 数据与空间

已有冻结R2数据清单为 research_logs/gpu_preparation_20261014/eegnet_data_plan.json，含127文件98,743,492bytes：18 EDF仅为六开发编号的ses-0/run-0、1、2及适配器必要元数据。来源是NEMAR nm000177 v1.0.5既有授权官方字节，保留CC-BY-4.0归属说明。适配器仍限制allowed_roles={source_train,source_validation}。

Pod首fit的25文件中22项在该清单内，可逐项SHA256复用；另外3项元数据保留。只需补105项82,322,754bytes，不重复下载已有文件，不打开任何query EEG。传输优先沿用私人短期逐对象能力或已核验官方HTTPS；不得创建或复制持久R2凭据。每项同时核对官方清单身份、长度及历史SHA256，partial和冲突保留，零自动重试；本次仅形成计划，没有下载。

训练环境已经安装，新增数据不足100MB。单归档上限16MiB，保留目录加tar的17份最坏占用约544MiB；启动前至少2GiB剩余空间，额外为日志/诊断保留余量。实时磁盘不足则停止，不能假定30GB容器盘为持久盘或自动删除历史结果。

## 超时与分批私有备份

每fit上限100epoch/300步，17个新fit合计最多5100步；1800秒硬超时及30秒TERM宽限。最坏17次超时为8.5计算小时，仅为操作上界，不是耗时预测或账单；不得把首fit5.5秒外推整队列。实际计费待父对话核查，现有Pod由两篇共用，不新建资源。

一fit为一批，最多一个已完成但未R2验收的fit。Pod本地完整归档经Jupyter→私人Library→Codex，使用Codex已有授权对配置中的固定result_key条件创建，禁止覆盖。检查全部成员、配置、split、选中epoch及checkpoint绑定，随后每包完整GET长度与SHA256核验；回执与父确认关闭此批后才释放下一任务。退出码或单独HEAD/ETag都不能替代完整GET。公共Git只提交文本审计及汇总，不包含原始EEG、权重或凭据。

发生传输失败，仅重新传输/验收已有包，不重新fit；同key已有对象必须全GET并与原包一致才能复用，冲突停止不覆盖。Pod文件丢失则从已验证R2对象恢复。部分fit/超时保留预约及日志，调查后另立明确恢复方案，不将partial当成功或自动重复。重放差异不放宽容差，继续阻断队列。两篇均完成可靠备份且父对话批准前不停止Pod。
