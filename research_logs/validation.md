# Phase 0 验证记录

执行日期：2026-10-09（Asia/Shanghai）。本记录对应科研实现 commit
`2e1f785285de4b23560ffe3c203a4d25f61d9f85`，不是文档记录提交的自引用 SHA。
默认分支初始化 commit 为 `78ca1a2173c2ce43b9b6f80ee1b177c311b51739`；
完整代码位于 `research/learning-preserving-bci`。GitHub 最终分支 HEAD 以推送后重新读取结果为准。

## 实际验证结果

| 检查 | 本轮结果 |
| --- | --- |
| Python 3.11.16 独立环境、`uv sync --locked --all-extras` | 成功；独立于系统 Python 3.12.14 |
| 再执行 `bash scripts/setup_environment.sh` | 成功复用安装；源码和 uv.lock 未被安装改变 |
| `uv pip check` / 指定依赖 import | 成功；实际版本见 `environment.json` |
| `python -m pytest -q --junitxml=/tmp/bci-pytest.xml` | **99 passed, 0 failures, 0 errors, 0 skipped**；2 条上游弃用警告 |
| `ruff check src tests scripts` | 通过 |
| wheel build + frozen-hash base dependencies + 独立 wheel venv | 通过；从 `/tmp` 运行，未使用 editable checkout 导入 |
| 未安装 deep/data extras 的 wheel 合成完整流程 | 通过；基础包不隐式依赖 Torch/Braindecode/MOABB |
| MNE + MOABB `FakeDataset` → `MotorImagery.get_data` | 20 个合成 epochs、3 通道、2 sessions；没有下载公共 EEG |
| 合成 EEG preprocessing → spectra/covariance/PCA → fixed CSP+LDA | 3 模拟受试者 × 2 held-out sessions，完成6条评估记录 |
| clean source commit、试次索引、配置与源码哈希 | 已核对，训练/测试索引无交集、标签与预测一一对应 |

EEGNet 测试实际执行 Braindecode 官方模型的 CPU 前向、一个小训练 epoch、概率输出、
推理前后完整 state 不变，以及相同 seed 的训练输出一致。它不是大规模 EEGNet 训练，
也不说明真实 EEG 上的有效性。统计测试验证参与者配对、顺序不变性和 CI/置换结果；
受试者标识字符串碰撞会明确拒绝。随机 decoder 的评估实际固定随机状态。

2 条 warning 来自 Braindecode 1.2.0 的 `final_layer_with_constraint` 参数弃用；
没有跳过 EEGNet 测试，也没有关闭包签名、下载哈希或 TLS 验证。

## 实际命令与工作目录

安装与完整验证在 `/workspace/few-shot-mi-eeg`：

```bash
bash scripts/setup_environment.sh
export UV_PROJECT_ENVIRONMENT=/workspace/.venvs/few-shot-mi-eeg
export UV_CACHE_DIR=/workspace/.cache/uv
export XDG_CACHE_HOME=/workspace/.cache
export MPLCONFIGDIR=/workspace/.cache/matplotlib
export MNE_DONTWRITE_HOME=true
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
source /workspace/.venvs/few-shot-mi-eeg/bin/activate
python -m pytest -q --junitxml=/tmp/bci-pytest.xml
ruff check src tests scripts
python scripts/environment_report.py --output research_logs/environment.json
python scripts/check_data_stack.py
uv run --locked --all-extras python scripts/smoke_experiment.py --config configs/smoke.json --output results/validated-code/report.json
```

环境报告是本轮采集记录。后续运行应省略 `--output` 或指定新的结果路径，
不要覆写已提交的环境证据。同样，smoke 实验默认生成唯一结果目录；指定现有输出会拒绝覆盖。

wheel 验证在 `/tmp` 的独立 `/tmp/bci-wheel-env`；该环境先安装由 `uv export --locked
--no-emit-project --no-dev` 导出的 base requirements（`--require-hashes`），再以 `--no-deps`
安装本轮构建 wheel，运行同一 smoke script。完整轮和锁文件 SHA256 在 `validation.json`。
`synthetic_validation.json` 保存 clean-code smoke 的完整配置、逐模拟受试者/试次结果、
有效模型参数和源码哈希；其中分数全部是软件 fixture，不能用于论文真实结果。

## 初始化中已修复的问题

首次 GitHub 推送因 GH007 邮箱隐私保护被拒绝。通过官方账号 API 核实账号 ID 后，
仅修改本仓库 local email 为账号的 GitHub noreply 地址，保留原始历史备份，
重建尚未发布的三个提交；源码树逐字不变。新历史上重新执行99项测试与clean-source smoke
均通过。未关闭 GitHub 隐私保护，也未改全局 Git 身份。


- 默认 uv 缓存位于只读 home：改用 `/workspace/.cache/uv` 和独立工具目录。
- 最初 editable build 时 README 尚未创建：完成项目元数据后重建成功。
- MOABB synthetic provider 尝试写只读 `.mne`：使用 MNE 支持的
  `MNE_DONTWRITE_HOME=true`，其配置写入临时目录，不改写 `HOME`。
- 独立 review 发现配对 ID 排序歧义、seed 仅记录未实际设定、非 cloneable 模板
  可能继承已训练状态：全部修正并加回归断言。

这些是已修复的开发/环境问题。最终必需软件检查无失败。没有把仅语法检查或零测试运行
称为科研工作流验收。

## 未验证与仅规划范围

以下为初始基础验证的历史范围；最新 NETBCI2026 单受试者真实读取补充见文末。

实际容器为 Debian 13，5 个可用 CPU，约33.3 GiB RAM；没有 NVIDIA device、
`nvidia-smi` 或可用 CUDA。Torch 是 `2.8.0+cpu`。没有创建付费资源。

本轮读取了官方小型元数据，但没有下载真实 EEG 信号、大 ZIP 或模型权重；
没有运行真实数据实验、完整 EEGNet 训练、GPU 计算、在线闭环、人类学习或 retention 实验。
SHU ZIP 密码与事件单位矛盾、NETBCI 大归档/实际事件、订阅论文主文、对外源码许可选择，
均保留明确未解决状态。原始数据 adapter、候选协同自适应优化、非线性 manifold 和
前瞻人体实验属于后续阶段。

本机运行验证、云环境配置草稿、GitHub 提交和产品中的环境发布是四个不同状态。
保存草稿不执行安装，也不证明新任务恢复已验证；环境发布由用户在产品中完成。

## NETBCI2026 访问与最小真实样本检查（2026-10-09）

- 第一优先级为 NEMAR `nm000305 v1.0.0`，数据 CC BY 4.0，版本 DOI
  `10.82901/nemar.nm000305.v1.0.0`。官方网页 HTTP 403，数据 API、manifest 与
  单文件下载均成功。未下载归档或整个数据集。
- 仅下载 `sub-1` 的 4 session × 6 run：24 EDF 与必要元数据，共 169 文件、
  193,462,298 bytes。全部与官方 manifest 的 SHA-256/Git blob 校验匹配。
- `scripts/check_netbci_subset.py` 实际读取所有 24 EDF 和全部信号，验证 74 EEG
  通道、250 Hz、µV 物理单位/MNE V、跨 run 通道顺序、有限值、717 个事件的
  annotation/TSV/sample 对齐与持续时间边界。session trials 为 180/179/180/178；
  右手 MI 360、rest 357；实读 `right_hand=2/rest=1`，不用 README 相反的数字。
- 固定版为 EDF/BIDS derivative；原始 Dataverse v2.2 BrainVision/MEG/MRI 不混入。
  NEMAR 无行为成绩字段；原始 participants.tsv（758600）已重新下载并验证 MD5，
  四 session 各六 run hit-rate 是 run-level。跨版本 join、评分分母、试次排除来源、
  逐 trial hit/miss/光标、家庭练习剂量与保持指标仍未验收。
- 审计 JSON：`research_logs/netbci2026_subject1_audit.json`；版本/manifest/文件校验与
  原始行为出处：`research_logs/netbci2026_sources/`；伴随 notebook 仅重放本地检查。
  `notebooks/netbci2026_access_check.ipynb` 的 8 个代码单元顺序执行通过、无错误；
  已保存输出并完成 HTML 渲染检查。Notebook 工具依赖安装在项目外，未改锁定环境。
- SHU 原始接入为 `pending author access`。调整优先级前的 Figshare v1 单受试者
  直接文件探针保留在 `research_logs/shu_historical_probe/`，不作为原始 ZIP/NEMAR
  接入验收。停止 `nm000288` 请求，不尝试解压密码。
- 本轮没有使用真实 EEG 训练模型、启动大型训练、付费资源或在线人体实验。
  第一篇 EEG 论文仓库保持只读。
- 修改后必需软件检查通过：99 项 pytest、`ruff check src tests scripts`、合成 CPU
  smoke 与 MNE/MOABB synthetic provider；合成输出保留 `synthetic=true` 和
  `software_validation_only`，不当作 NETBCI 的模型或神经学习结果。

### NETBCI 后续适配与分析方案验收（2026-10-09）

- 本地适配器实际输出 717 × 74 × 1250（V），保留 subject/session/run/TSV 行身份；NPZ 与强制元数据往返校验通过。未过滤、丢弃 trial 或训练模型。
- 原始 v2.2 归档仅以 HTTP Range 获取 sub-01 的 120 个小型元数据文件，35 个请求合计 1,339,985 bytes，另有初始尾部探针 131,072 bytes。未读取原始信号或完整归档；成员 CRC 已验证，整包 MD5 未验证。
- 24 个原始头文件 SHA256 与 NEMAR provenance 一致；717 个事件在原始发布已经存在，未见转换额外丢失。原始单 run 249.89999389648438 Hz，其余 250 Hz；事件按实际时间与采样率对齐。原始脉冲 duration=0，derivative 的 5 秒为任务窗约定。
- 原始成绩与 EEG run 为候选关联：run 向量顺序、评分分母未确认；23/24 个百分比不兼容实际 EEG 事件数作为分母。禁止反推出逐 trial 成功/失败。
- 跨会话方案及配置已准备，划分覆盖全部 717 trial 且组间无重叠；参考训练/验证/query 为 90/30/60，后续 calibration pool/query 为 90/447。方案没有执行真实模型实验，也没有对外预注册。
- 软件验证：108 项 pytest 通过（2 个上游弃用警告），ruff 和 git diff --check 通过；合成 CPU smoke 与 MNE/MOABB synthetic provider 通过。合成结果不作为 NETBCI 科学结果。
- SHU 保持 pending author access，未请求 nm000288、尝试密码或发送邮件；未下载其他受试者信号，未启动付费资源，未修改第一篇仓库。

### 第二篇真实科研阶段与原始方法精读（2026-10-10）

- 重新执行本地信号审计和跨版本事件核查：169文件官方校验、24EDF、717 unique trial，四session180/179/180/178，74通道250Hz。完整事件/源文件清单和run数量表保存于 `research_logs/netbci_stage1_20261010/run01/`。
- 原始Archive/derivatives仅做有上限Range目录读取，补充4个scans元数据，共1,123,661HTTPbytes，未读取新信号；原始匿名1916日期不当真实日历日期。Behaviour subject/session向量可定位，run顺序/denominator/trial outcome仍unresolved；原始百分比没有转换成hit/miss。
- 实际执行单受试者PSD/Mu/Beta、协方差/PCA、等类/run数量和粗QC敏感性；55标记trial不等于专家伪迹排除。事件相对PSD没有prestimulus baseline，不命名ERD/ERS。
- 冻结CSP-LDA及3epoch CPU EEGNet实际执行两次；逐trial预测、特征、几何和结果SHA一致，query前后模型状态不变。CSP后续全rest作为失败保留；EEGNet仅最小流程验证。conditional run-bootstrap不作participant CI。
- 原pilot validation与train同session不同run；追加独立validation session02/test03–04的角色审计使用同一冻结预测，没有新拟合/选参，但因pilot已观察结果，不冒称前瞻性未查看test。未来完整baseline仍须先冻结新记录的日期分区。
- 三篇Nature原始方法精读：L1/L3主文、补充/Reporting Summary及小型作者源码，L2订阅预览、完整公开补充和source tables。未绕订阅。L1随机化文字矛盾、长期EEGNet重训；L2符号/源码口径差异；L3demo与完整pipeline边界均保存定位。精读不等于原实验复现。
- 原创英文工作稿保存于 `manuscript/longitudinal_eeg_working_draft.md`，约6000词，仅单受试者探索性feasibility；作者/机构/伦理secondary-use判定等缺项明确。`docs/personal_paper_research_blueprint.md`区分现在可写的观察层和未来在线因果证据层。
- 新notebook的4代码单元顺序执行、零error，PSD/几何/BA数值与保存结果一致；两幅实际渲染图已视检，HTML已导出。全页Chromium截图尝试未完成，不能声明HTML全页截图验收。命令入口/template路径失败与恢复记录在notebook_validation.json。
- 112项pytest通过（2个上游弃用警告），ruff和git diff --check通过；合成CPU smoke、MNE/MOABB synthetic provider通过。没有大型训练、全队列信号下载、付费资源、在线人体试验或第一篇仓库修改。
- 执行时Git基准/dirty、脚本/配置/数据SHA与实际软件版本保留；新增post-execution source_closure补充脚本依赖，明确不是回填成执行时记录。

- 最终新增文件的Git whitespace检查初次将20,477个合法TSV CRLF行尾报为空白；追加`.gitattributes`保留TSV原字节并启用cr-at-eol，提交diff复查零问题。没有重写或归一化校验文件字节。

### 2026-10-11 十身份接续检查点

- 同一固定版本1885文件校验、240 EDF信号/7577源事件读取通过，7576个5秒窗口及1条显式源事件排除。
- 十身份全员source-only频谱/几何/冻结CSP-LDA、40行行为join与统计实际执行；sub3完整refit16文件byte一致。
- 独立算术复算通过，随后独立完整数值审计发现sub1/sub7跨身份/会话精确重复；238条source training→later query内容重合。
  官方checksum通过不保证独立采集，原十身份EEG区间不作为独立人的推断；源驱动排除两者后的八身份敏感性另存并独立重算通过。
- pytest279项通过、2个既有上游deprecation warnings；ruff和Git whitespace检查通过。合成smoke/data-stack在接续preflight已通过且明确software_validation_only。
- R2实际写入、逐对象HEAD及代表/小结果全GET校验通过；截至本检查点存原始数据/eligible bundles/模型结果/来源ledger/私有聊天备份，具体字节以storage_catalog_ten_20261011.json为准。
- 新19身份与外部公开资源按用户授权准备，检查点前未下载新增EEG信号，后续独立收据记录实际完成范围。第一篇未修改，未启动付费GPU或在线人体实验。
