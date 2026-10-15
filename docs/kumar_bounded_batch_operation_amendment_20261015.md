# 开发队列操作修订：一次启动、最多两fit一批、离机回执后继续

本修订只涉及冻结开发队列的执行和保全流程，不新增科学方案或研究任务。用户2026-10-15 01:09:00 UTC要求“是否能一次性把需要训练的全都一次性训练了然后再进行后续分析，这么一个个做太慢了”，随后明确授权准备剩余11项有界顺序入口。本轮仅实现、测试、冻结交付；dot审核固定提交后才执行，Codex没有启动GPU或操作Pod。

## 真实接收与启动基线

第7fit `sub-7/20261012` 独立审计和两份原包R2完整GET已在固定`5e6149ffba88063598529d4a7c1d91e089d4139f`交付：2对象256000bytes、零失败，完整UTF-8回执SHA256=`b6293ab6fe6b551575f0fb2e7f1b5640f62dfc77632e838e1cf6a7a210091075`。dot于2026-10-15 01:14:06 UTC真实回读并明确确认，真实ACK和连续账本7已固定于`8aee0b63f51d631e0f66ea0e07c29def0ad60a3f`；账本SHA256=`94caad4e0eec18224ee4c93834c86ae951c8dbb29902972d0645651892f4a911`。历史pending请求/原退出75/失败证据保留，不改写历史。

首次批量启动必须核对这7项真实接受及全部回执/ACK；不存在第7真实接受就拒绝运行。前7项绝不重训；不调用旧单fit入口启动第8。旧模型、科学config、split、127输入、源标签、源validation选择规则、数值线程、原1e-7重放容差均保持。query、未来会话信号和其他12编号正式门仍关闭。

## 明确修改的操作规则

原`configs/kumar_development_queue_plan_20261014.json`、runtime、7项交付文件保持原字节。本新合同`configs/kumar_development_batch_20261015.json`显式改变以下执行规则，不能静默套用旧门：

| 原执行语义 | 本修订执行语义 | 科学接受门 |
|---|---|---|
| 每次启动最多1fit | 新parent最多顺序调度11个固定child，每child仍仅调用原`execute`一个fit | 不扩大参与者/seed/参数/正式评估 |
| 最多1个未备份完成fit | 每小批最多2个已训练但尚未离机的结果；先离机write-ahead intent，再训练 | 不把intent备份当作结果备份 |
| 下一fit须前fit完整R2+父确认 | 同批可顺序2fit；进入下一批前，必须由dot证明本批原包已离机并全字节/逐成员SHA通过 | **accepted仍须每fit独立审计、R2完整GET零失败、真实父确认**，三者均不得用trained/exported代替 |

这是用户支持的一次启动自动顺序队列，不是新科学策略。旧`fit_result.parent_dispatch_acknowledged_replay_backup=true`只说明最初重放门被确认，不等于该fit自己的R2/父确认。原入口的`maximum_new_fits_per_invocation=1`保持，新parent只在本明确合同下启动单fit child；不能以shell循环旧launcher替代。

## 固定剩余11项和批次

完整job ID、输出和R2 result_key见`research_logs/kumar_development_batch_20261015/remaining_11_jobs.json`。固定顺序不可改，最后一批只1fit：

| 批次 | 原队列项 | subject / seed |
|---|---|---|
| 1 | 8、9 | sub-7 / 20261013、20261014 |
| 2 | 10、11 | sub-10 / 20261012、20261013 |
| 3 | 12、13 | sub-10 / 20261014；sub-13 / 20261012 |
| 4 | 14、15 | sub-13 / 20261013、20261014 |
| 5 | 16、17 | sub-16 / 20261012、20261013 |
| 6 | 18 | sub-16 / 20261014 |

起点job=`1aa92ed2b84621e78c67af8bf6f1eb6482b810951b9418a9b9fb017541552c91`；终点job=`df56f563ff26909b6e0590906f305982b0e5df89520c12355f433a1cd2bd968a`。不存在第19项或自动进入formal的分支。

## 阶段账本与现有通路的实际边界

新runner只维护checkout外`/workspace/paper2-results/bounded-batch-20261015/`的state、不可变claim、append-only journal、worker原日志和导出包。逐job分别保存：

| 阶段 | 必须有的事实 |
|---|---|
| `trained` | 原执行器已保存完整原result tar，checkpoint/14载荷/manifest及长度SHA通过；不是科学独立审核 |
| `off_Pod_exported` | dot在另一机器通过现有browser/Jupyter下载完整artifact，运行全字节/逐成员核验并明确声明离机持有，runner验明匹配回执 |
| `independently_audited` | 既定独立审计器实际审核相同原包、历史、标签、checkpoint和CE |
| `R2_full_GET_verified` | 安全Codex既有R2权限条件上传原字节并完整GET/长度/SHA零失败 |
| `accepted` | 每fit上述两项科学/存储门闭合且有真实父确认，才可追加连续accepted账本 |

本runner永远不把后三项置True，不写活动accepted_jobs或parent_acknowledged。训练完成数和离机数由新state记录，正式接受仍以原Git连续账本为准。离机回执包含run/固定commit/合同/整包SHA/长度/精确job集合/每成员长度SHA；物理上位于另一机器是dot的明确声明，代码本身无法证明地理位置或替dot下载。

**本版没有后台上传实现。** 不调用未验证Jupyter内部API，不给Pod复制R2凭据，不创建token、密钥、capability或额外权限。每批有两个边界：训练前的intent包、训练后的results包；6批最多12次dot下载及回执。单runner在边界最多等600秒，验证后自动顺序继续；若dot未及时递送回执则安全暂停。一次启动可覆盖全部11项，但仍需要这12个实际离机动作，不是无人值守网络传输。

## 精确启动和离机回执命令

先由dot审核本轮返回的完整固定提交和`research_logs/kumar_development_batch_20261015/delivery_hashes.json`。将既有科学checkout安全更新到该固定提交，不能reset或覆盖未提交修改。新的运行路径仍须实际存在且通过核验，不能从旧容器路径推断已恢复。第7真实ACK基线必须随该版本到位。

将本轮固定交付回执中的完整提交与合同SHA填入变量，不能用移动分支或自行重新解析/重写JSON生成另一hash：

```bash
cd /workspace/paper2-90f674f
PAPER2_BATCH_COMMIT='<本轮返回的40位固定批量交付提交>'
PAPER2_BATCH_CONTRACT_SHA256='<本轮返回的完整合同SHA256>'
test "$(git rev-parse HEAD)" = "$PAPER2_BATCH_COMMIT"
test -z "$(git status --porcelain)"
PYTHONPATH="$PWD/src:$PWD/scripts" /workspace/.venvs/paper2-gpu/bin/python -B \
  scripts/run_kumar_development_batch.py --plan-only

bash scripts/launch_kumar_development_batch.sh \
  --execute --new-run --expected-commit "$PAPER2_BATCH_COMMIT" \
  --reviewed-contract-sha256 "$PAPER2_BATCH_CONTRACT_SHA256" --wait-seconds 600
```

第一条plan-only不建state/claim、不查GPU、不训练。真正执行要求精确版本/合同、干净checkout、7接受基线、当前容器身份与父核验的`a7d3f0e408a4`一致、实时Python3.11.16/91锁定包/Torch2.8.0+cu128及GPU/原线程门通过。launcher只设置既有OMP=1、OPENBLAS=1、CUBLAS=:4096:8和原缓存路径，不新增MKL或科学线程覆盖。

runner打印`awaiting_dot_export_receipt` JSON，其中`export.archive`、`bytes`、`sha256`、`job_ids`和`receipt`是本边界精确身份。dot通过现有Jupyter文件浏览器下载这个原tar至另一机器，先对比打印的整包长度/SHA，再使用**同一固定版本源码**的stdlib verifier（不需要GPU或R2授权）：

```bash
python3 scripts/run_kumar_development_batch.py \
  --verify-export /absolute/off-pod/downloaded-boundary.tar \
  --receipt-output /absolute/off-pod/NEW-boundary.receipt.json \
  --attest-off-pod-possession
python3 -B - /absolute/off-pod/NEW-boundary.receipt.json <<'PY'
import hashlib, sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
```

tar必须原字节、全部manifest成员长度SHA一致。仅在dot确实离机下载并核对了打印身份后使用此attestation；不能在Pod上运行verifier并声称离机。原下载和receipt都保留在离机机器。通过既有browser/Jupyter上传receipt至打印`receipt`路径旁的临时文件（例如追加`.uploaded`），在browser终端核对完整receipt SHA后原子发布，避免runner读到上传半文件：

```bash
python3 -B - /absolute/Pod/inbox/name.receipt.json.uploaded \
  /absolute/Pod/inbox/name.receipt.json '<离机receipt完整SHA256>' <<'PY'
import hashlib, os, sys
from pathlib import Path
source, target = Path(sys.argv[1]), Path(sys.argv[2])
assert hashlib.sha256(source.read_bytes()).hexdigest() == sys.argv[3]
assert source.parent == target.parent and not target.exists()
os.link(source, target)  # 完整文件的独占原子发布；不覆盖旧回执，保留上传源。
PY
```

实际路径必须来自该边界打印JSON，不能复用上一批回执。runner机械验证所有身份和成员，只有intent回执通过才开始本批；只有results回执通过才开始下一批。等待期间释放GPU锁，dot可在不影响论文2的前提下安排其他工作；重新取得锁失败则停，不抢占。

## 时间、磁盘、预算和独占

- 同时最多1个GPU fit；parent在**整个active小批次**持有原`/workspace/research-gpu.lock`非阻塞独占flock，覆盖两fit间隙、原输入重验、checkpoint/成员核对和results打包；worker继承并验证同一锁。另有supervisor锁避免两个parent并发修改同一state。
- 每fit30分钟；每active小批次总上限3600秒，包含批内核验/两worker/打包；全队列绝对上限19800秒，包含等待离机回执，resume不能刷新起点/到期时间。实际child限额取逐fit、批次和全局剩余时间最小值，保留原TERM30秒清理余量，之后KILL整个进程组；GNU timeout额外保护父进程突然丢失的worker。
- 剩余最多11fit、1100epochs、3300steps；原17新fit/5100steps总预算和逐fit100epoch/300steps不变。没有增加付费资源或推断真实账单；绝对时限提前耗尽即停，不能靠重启扩大预算。
- 每fit和打包前分别核对数据、state及各输出实际文件系统，至少5GiB加2个16MiB原包和64MiB导出包余量；单fit原包≤16MiB，批次导出包≤64MiB，本地尚未离机的完成fit≤2。
- 每fit原执行器重新验证全部127输入、长度/官方checksum/历史SHA，检查GPU空闲，保持40 TRAIN/20源validation/query0、固定选择/容差；零自动重试。错误、冲突、超时、预算不足、磁盘不足或回执身份不一致都停队列，保留原包、claim、日志和诊断。

## 暂停、失败与再次容器丢失

退出76只表示边界等待回执的安全暂停，不表示fit验收。若还是**同一容器、同一state、同一版本**，先完成该边界离机回执，然后只用resume命令；不要new-run、换state目录或删除claim：

```bash
bash scripts/launch_kumar_development_batch.sh \
  --execute --resume --expected-commit "$PAPER2_BATCH_COMMIT" \
  --reviewed-contract-sha256 "$PAPER2_BATCH_CONTRACT_SHA256" --wait-seconds 600
```

原600秒等待期限不刷新；receipt已到则先验证，没到仍立即暂停。原19800秒总期限始终保留。完成11fit并离机后返回75且状态`complete_exported`，仅表示等待科学独立审核/R2/父接受，不能宣称accepted18或继续formal。

任一worker开始后失败/partial/进程状态不明，或中途只有第一fit完成而没有本批results导出，自动resume拒绝；只允许先离机保全已完成原tar和原日志，再由dot/Codex独立审阅恢复，不重新调用训练。原claim、原失败、原退出码不可删；源码没有optimizer/RNG中途精确恢复承诺。

如果容器再次重建，即使本地state丢失，新的hostname也不能fresh-start；若旧state被恢复，container identity不符仍拒绝resume。之前的intent已在离机机器保存了本批可能执行的job，必须与结果/日志一并核对。已完整离机的原包可继续审核和R2入库；有intent/claim却缺结果者可能已经完成，**不得自动重训或跳过**。本版不提供更换容器后自动执行恢复，必须先恢复并审核离机state/journal/claim/receipt身份，仍不能抹除未知状态。最多2个已训练但尚未离机结果有损失暴露，不保证零损失；小批次把这个风险限制在2，不能等11项全跑完才下载。

## 后续科学审核与R2接受

dot把离机的原intent/results包和回执交给Codex。先验证整包及全部成员，然后取出其中**未经改写的每fit原tar**，逐个调用既定`audit_kumar_queue_bundle.py`，保留所有正负结果、原失败、checkpoint和选择历史。使用安全Codex既有R2注入授权，原fit tar按冻结result_key归档；原intent/results批次包作为共同dispatch证据归档，并对每个对象完整GET/长度/SHA零失败。两个模型可共用同一个批次证据对象，但每个模型的原result身份、独立审计、R2回执和真实父确认必须分别绑定，不借共享回执冒充另一个job通过。

Codex提交逐fit文本审计及待父确认请求，dot可一次审核这一批的精确job集合/receipt SHA并明确确认；之后才按原顺序追加accepted连续前缀。没有独立审核或R2全GET的结果永不置accepted。此修订仅放宽**运行推进**的离机门，不取消**科学接受**的审计/R2/父确认门。论文2绝对优先，dot唯一操作Pod；论文1仅在不影响论文2时并行。Pod不Stop/Terminate，不新增凭据或延长SSH授权。
