# 论文2：学校 HPC 实验扩展 V2

**当前运行配置：`hpc_gpu`、2个单卡任务并行，每项16核CPU、128GB。**
[本地启动入口](../../releases/paper2-hpc-v2-20261023/README.md)已替代旧的单次raw下载命令。
封存代码包仍保留原始模板，实际提交前会生成并使用`kumar_dev_hpc_gpu.json`，
原科学配置、断点和输入不改。

本目录是独立实验版本。已投稿论文、54个已验收模型及其预测保持原样。
本交付完成代码、输入准备和软件测试；学校 A100 上的真实检查与科学结果由
首次 Slurm 作业产生。不要把本地合成测试写成已完成的科学实验。

## 直接启动

现在可以在学校终端**直接从GitHub下载**，无需先下载到个人电脑。
[完整入口与一行命令](../../releases/paper2-hpc-v2-20261023/README.md)
使用固定版本分片下载、断点续传及原包SHA校验，随后调用本安装器。
下载公开文件无需token；首次提交训练时仍在终端隐藏输入GitHub token。
下面保留手动离线上传方式，作为网络不可达时的替代路径。
若学校Python报证书签发链错误，请使用上述入口的新版一行命令；它选择已有系统
CA并传给后续进程，TLS验证保持开启。新SSH登录后也可用该命令安全续跑。

将下列三个文件上传到 `/public/home/zhuziyuan/incoming/`：

1. `install_offline.sh`
2. `paper2-hpc-v2-code.tar.gz`
3. `paper2-hpc-v2-kumar-dev-inputs.tar.gz`

在学校 **login1 网页终端**执行这一行：

```bash
bash /public/home/zhuziyuan/incoming/install_offline.sh
```

脚本安装到 `/public/home/zhuziyuan/projects/paper2-recalibration-v2`，校验
离线包和输入，然后要求在终端**隐藏输入 GitHub token**，验证本仓库 Contents
读写权限，再提交数组。不要把 token 发进聊天、命令行参数、脚本或 Git。
默认保存到自己账户的 `~/.config/paper2-hpc/github-token`，权限0600；已授权
的续跑复用该配置。无需在计算节点下载任何代码、依赖、模型或数据。

之后启动或恢复都使用同一行：

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/paper2_start.py
```

已完成项跳过；正在排队/运行的数组不重复提交；失败或中断项从持久断点恢复。
一个数组仍活动时不会另开第二个数组，使全项目最多3项并行。一个任务失败
不取消其他独立任务；修复后再次执行上面一行，补跑未完成项。

## 首批具体运行什么

固定输入：Kumar2024 / NEMAR nm000177 v1.0.5，原开发参与者
`sub-1/4/7/10/13/16`，原cue对齐5秒窗口、22通道、128Hz、640样本，
原CAR、8–30Hz滤波和whole-run分配。窗口完整不等于全程持续运动想象。
沿用原排除及事件身份，不将partial事件解释成提前结束。预处理在打包环境
一次完成，学校只读准备好的float32 NPZ。

每人 source run0/1约40例训练、run2约20例验证、run3独立source query；
目标session1–5的run0为support，其余完整run为query。每个预算取support
原时序前4/8/12/16/20例，上限实际19或20，不用后续标签补齐或平衡类别。
精确数量、trial/run ID及SHA见 `configs/input_manifest.json` 与任务文件。

任务共24项：6个参与者级经典方法任务，以及6人×3固定新种子
`20261023/20261024/20261025` 的18个神经任务。每个神经任务训练一个新V2
source模型，复用于全部target session、预算与更新方法；另有每task
3更新方法×5预算×5目标会话的support适配阶段（全队列1350阶段）。
冻结方法不拟合目标标签。经典任务每人一次，结果不按神经种子重复计数。

经典8臂：`frozen`, `lda_only`, `full_csp`, `ea_csp`, `anchored_csp`,
`empirical_anchored_csp`, `ea_anchored_csp`, `ea_empirical_anchored_csp`。
采用统一NumPy固定收缩CSP/LDA；这是新比较器，不声称数值复制旧MNE模型。
主比较预先指定为20标签上限下 **EA+经验源协方差约束 − EA全更新**。
同EA下的固定强度规则及未对齐经验规则分别构成权重规则、EA的消融。
参数、估计公式、文献来源和局限见交付的 `docs/` 科研设计文件。

神经4臂：`frozen/head/full/l2sp`。源训练100epochs，源validation CE选择
保存的最佳epoch；目标更新固定20epochs，query不选择epoch、学习率、种子
或方法。head保持特征层和BN状态；full和L2-SP允许用当前support更新BN，
均沿用source TRAIN的通道归一化。L2-SP是已知对照，不当成新算法。

这是明确命名的新 `compact_eegnet_hpc_v2_1` 架构，不能加载原Braindecode
54份权重冒充复用。旧54份不改写、不重启旧任务；新V2训练结果可在运行层
修复后直接续用。改变算法、输入、支持预算或科学参数须使用新版本目录。
现有Kumar数据已暴露，首批均为开发/探索分析；6人×3种子不等于18个独立样本。
BNCI九人whole-run外部验证及Lee/OpenBMI 54人block验证有具体方案，尚未
打包或运行，当前启动命令不暗中增加外部任务。

## 资源与环境

当前操作层覆盖为`hpc_gpu/gpu:1`、16CPU/128G、`%2`，取消旧gpu3排除。
以下三A100/24CPU/%3是封存模板的原始配置，由上述伴随文件覆盖；
不能从新分区截图推断实际卡型。

默认Slurm数组 `%3`，每项1张 `NVIDIAA100-SXM4-80GB`、24CPU、128G内存，
账户 `zhuziyuan`、分区 `hpc_gpu1`；总上限3GPU/72CPU/384G。
任务使用Slurm分配的 `CUDA_VISIBLE_DEVICES` 和逻辑 `cuda:0`。
Torch计算线程4、BLAS/OpenMP线程1、DataLoader workers0。小型经典任务
也使用已知GPU分区以避免假设另有CPU分区，实际只运行NumPy CPU计算。

沿用 `/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python`；
仅依赖现有NumPy与PyTorch及标准库，不安装本仓库旧pyproject依赖，不升级
这个共享环境。记录实际Python/Torch/NumPy、CUDA构建和GPU信息；用户报告
版本不是已验证的驱动或nvcc版本，也不强制同一物理GPU UUID续跑。

`--time=5-03:00:00` 是采用用户过去用过的单作业候选值，**不是已查明的
分区最大时限**，也没有人为累计12小时截止。若调度器明确拒绝时限，只改
config中 `slurm.time_limit` 为学校允许值再运行原命令；科学断点不作废。
暂时 `--exclude=gpu3`，原因是历史启动异常未查清，不代表硬件已判坏。

首次launch只做一次版本/文件/身份准备；未变输入续跑只查文件统计。
每个实际软件/GPU能力组合首次分配后自动进行极小GPU前向、反向、保存、
恢复检查，通过后立刻执行正式任务。相同环境后续不重复pilot/pytest。
这次真实GPU检查目前尚未发生。`-I -S`兼容入口已测试，但默认仅使用 `-u`。

## 中断、故障和进度

模型、optimizer/动量、scheduler、AMP scaler、epoch/step、样本游标/
排列、Python/NumPy/Torch/CUDA RNG、最佳权重和验证历史一并保存。
每120秒、阶段完成和信号中断保存，两代checkpoint保留。使用同目录临时
文件、文件fsync、os.replace；不用硬链接、renameat2或目录fsync。
评价按方法/预算/会话分片，评价失败后续跑直接复用模型，不重训。

Slurm提前180秒发USR1，shell转发给Python；保存后返回75，shell才尝试
重排队该数组项。学校拒绝requeue则保留断点，手动执行原命令继续。
TERM/INT或用户scancel保存退出且不自动复活。数值/数据/磁盘错误保留
traceback和已有文件，零自动科学重试；修复后用户显式恢复。
跨硬件/软件版本不承诺逐位一致。损坏的当前checkpoint可读上一代，损坏
文件保留；身份不匹配或存储错误不伪装完成。

持久文件在 `outputs/kumar-dev-v2/`：

| 路径 | 含义 |
| --- | --- |
| `logs/` | Slurm预先创建的绝对日志目录；首行shell job/task/host/time |
| `tasks/<task_id>/progress.json` | 当前阶段、真实step/样本数/保存时间 |
| `tasks/<task_id>/` | 两代断点、逐阶段模型、预测分片、统计和异常 |
| `tasks/<task_id>/complete.json` | 该任务实际完成证据 |
| `.runtime/` | 一次准备、GPU微型检查、Slurm提交记录 |
| `github_sync/monitor.log` | 独立登录节点同步器及重试结果 |

每30秒输出真实阶段/step；短阶段完成也会记录。squeue的RUNNING、控制器
在线或运行时间增长不单独构成训练证据。GitHub每约180秒同步各任务进度
及已完成指标至本研究分支 `training_status/paper2-recalibration-v2/`；
网络、限流或报告故障自动重试，训练继续。同步器与GPU工作进程分离。
若登录节点清理了后台监控，训练不受影响，可单独恢复监控：

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/projects/paper2-recalibration-v2/hpc_recalibration/github_sync.py monitor --config /public/home/zhuziyuan/projects/paper2-recalibration-v2/configs/kumar_dev.json
```

## 汇总和R2

汇总入口只读已保存分片，无forward/fit；先同参与者同会话平均全部种子，
再按参与者平均会话。缺失任务/种子/类别明确列出，未完成的参与者不冒充
完整主终点。以参与者bootstrap10000次，保留全部个体配对差、类别塌缩与
负结果。−5个百分点仅是描述性下降阈值，不代表临床损害。

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/projects/paper2-recalibration-v2/bootstrap.py summarize --config /public/home/zhuziyuan/projects/paper2-recalibration-v2/configs/kumar_dev.json
```

Cloudflare R2原数据前缀为
`few-shot-mi-eeg/datasets/kumar2024/nm000177/v1.0.5`；本次离线输入与源码
使用新的版本前缀和完整GET/SHA回执，不重复下载整套原EDF。
云端已有R2权限不等于学校已配置R2权限；没有把云凭据放进包或复制到学校。
作者2026-10-23明确要求直接GitHub下载后，同一输入包以四个小于100MB的
分片发布到仓库，保留原CC BY 4.0及完整来源署名；输入字节未改动。
此下载路径不依赖R2。
学校checkpoint首先持久保存 `/public/home`，GitHub只传进度/指标。后续
R2归档可在已有安全权限的控制环境使用仓库 `scripts/sync_research_r2.py`
上传已完成原件并完整GET校验；当前不声称学校已实现自动R2上传。

## 软件验证与科学范围

交付记录包含本地CPU合成测试、真实输入SHA/角色检查、Bash语法及打包
端到端检查。它们证明实现的恢复与隔离行为，不代替学校Slurm/A100实测，
也不产生新论文结果。新方案首先检验强EA对照和更新强度，外部数据验证
是进一步提高科学说服力所需的独立阶段；不承诺期刊档次或算法一定获益。
