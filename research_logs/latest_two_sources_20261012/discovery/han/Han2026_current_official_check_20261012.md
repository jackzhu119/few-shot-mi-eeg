# Han2026 官方源复核（2026-10-12 UTC）

当前官方 OpenNeuro 数据集为 [ds007327 v1.1.0](https://openneuro.org/datasets/ds007327/versions/1.1.0)，对应 DOI `10.18112/openneuro.ds007327.v1.1.0`。本次重新读取官方 GitHub 镜像标签、完整树、元数据、公开 S3 对象列表，以及一个原始 EEG 文件的 HEAD 和 1024 字节 Range。未下载完整 EEG，未训练。

- 固定版本 Git commit：`9f9f541115dfd6cbf05ef66ccadb40a9b3450efe`；当前官方镜像公开标签最高版本为 1.1.0。CHANGES 明示该版本日期 2026-06-22，只增加同内容 PLV CSV；原始数据 v1.0.0 在 2026-01-28 已公开。
- 官方 `dataset_description.json` 为 `License: CC0`、BIDS 1.8.0、DatasetType raw。DataCite 本身未填写 rights，不代替该文件的许可证据。
- participants.tsv 实际有 35 个唯一 ID：sub-001 至 sub-035；20 女、15 男，年龄 17–26，均值 21.5429、样本 SD 1.8840。三个 raw task 每个都实际有 35 个 `.set`，不是将同人三任务当 105 人。
- 官方 task 分为 dribble、ballpass、passing。dribble 含 MO、MI、MO+MI、rest、static；只有 A11/MO 与 A22/MI 可形成这里讨论的纯观察/纯想象条件。ballpass/passing 为不同复合条件，不能合并为左右手或四肢 MI 类别。
- sub-001 官方 eeg.json 明示 ANT Neuro、64 EEG 通道、1000 Hz、CPz reference、AFz ground、1 秒 task duration。此前根据二级 loader 说官方未注明 reference/ground，需要更正。channels.tsv 有 88 行，包含 24 个 BIP 通道；实际 EEG 选择应由官方 channel 类型和 adapter 检查确定。

完整 S3 列表共 2039 文件（含 derivatives 和临时文件），合计 75,606,275,845 bytes = 70.4138 GiB；正文不将这一总量作下载目标。三个必要 raw task 合计 58,169,043,728 bytes = 54.1741 GiB。仅 dribble 的 35 个信号为 11,492,252,024 bytes = 10.7030 GiB；加本次固定版本的 180 个必要 metadata 文件，11,492,759,998 bytes。

代表文件 `sub-001/sub-001_task-dribble_eeg.set`：公开 HEAD 200，Content-Length 312,176,992；Range GET `bytes=0-1023` 返回 206、Content-Range `bytes 0-1023/312176992`，实际读 1024 字节，开头为 MATLAB 5.0 MAT-file。105 个 raw signal 的 S3 对象大小全部与固定 commit 的 git-annex SHA256E 指针相同。完整 SHA256 仍必须在未来完整下载后检验；大小与 1KiB 检查不能证明全文件完整。

本次读取全部 35 人官方 dribble events.tsv，验证以下数据质量情况：

- sub-020、sub-025、sub-027 各有一条完全相同 onset/duration/trial_type/value 的 A11/MO 重复行。
- 另发现 sub-017 有一条 A88/MO_MI 重复行；仅选择 A11/A22 时该行不进入分析。
- 唯一 A22/MI 事件实际合计 4195；sub-018 为 119、sub-030 为 116，其余各 120。唯一 A11/MO 合计 4197。
- sub-025 的 A66 有 240 行且 A44 缺失。这里保留原始标签，仅提示混合/rest/static 条件需要独立核查；这些情况不支持断言作者造假。

固定 manifests：

- `download_manifest_all_raw_1.1.0.json`：完整三个 raw task 的 105 信号，含每文件真实大小、SHA256、S3 下载 URL、原始 blob hash 和对应 subject/task。
- `download_manifest_dribble35_1.1.0.json`：35 个 dribble signal + 全部必要的 180 个固定 commit 元数据。元数据 URL 固定 commit；S3 signal 当前 URL 可变，未来下载必须符合 manifest SHA256 后才能接受为该 snapshot。
- `download_manifest_stage1_10subjects_1.1.0.json`：工程接入的预先选择 10 人，5 女 5 男，包含 20/25/27 三个纯条件重复问题。总预算 3,414,670,500 bytes = 3.1802 GiB，留空间给第二数据源和处理。它是工程子集，不能报告为已经接入完整 35 人。

推荐：若需要容易直接接入、许可公开可信的 2026 healthy 候选，Han 有完整可审计 inventory、可校验下载 manifest 与公开 signal。但它用于单独 sports MI/MO 域的离线表征或域迁移探索，不是传统 hand-MI 多类库，没有纵向随访，也不能支持 human learning/skill retention 结论。12 GiB 空间不能把全35 dribble和另一大型源同时放入后再留出合理处理空间。

复现证据均在同目录：`github_tree.raw`、`official_mirror_tags.raw.json`、`dataset_description.raw`、`participants.raw`、S3 三页 XML、`metadata/`、`metadata_access_receipts.json`、`all35_dribble_event_check.json`、`official_exact_duplicates_all35.json` 及 representative HEAD/Range receipts。`metadata/` 下的 `.set` 是约205字节 git-annex 指针文本，用来保存固定版本的大小和 SHA256；它们不是 EEG 信号文件。
