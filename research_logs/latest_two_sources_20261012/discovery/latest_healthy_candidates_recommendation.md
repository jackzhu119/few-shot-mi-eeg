# 两个 2026 healthy 候选的当前官方核查

2026-10-12 UTC 重新联网获取官方数据页、公开接口、文件清单与轻量元数据。只对 Han 读取一个原始信号的 1024 字节、对 MIND 做一个原始信号 HEAD；未下载完整 EEG，未训练，未联系作者。

| 项目 | Han / OpenNeuro ds007327 v1.1.0 | MIND / ScienceDB PUBLIC V4 |
|---|---|---|
| 官方来源 | https://openneuro.org/datasets/ds007327/versions/1.1.0 | https://doi.org/10.57760/sciencedb.34326 |
| 实际发布人数 | 35 个唯一 ID，participants 和全部三个 task 的 raw signal inventory 均对应 35 人 | 30 个唯一 ID，participants 与实际 30 个 BIDS sub-* 目录一致，每人三 EEG runs |
| 当前固定版本 | 1.1.0 / Git commit 9f9f541115dfd6cbf05ef66ccadb40a9b3450efe；当前公开标签最高为 1.1.0 | V4 / 4.0.0；public4 是页面标识，公开文件 API 的 version 参数需要 V4 |
| 实际许可 | 官方 dataset_description 为 CC0 | 仓储 landing/details CC BY-NC 4.0；BIDS dataset_description CC BY 4.0，内部许可冲突尚未解决 |
| 公开可访问性 | 无需登录的官方镜像固定 metadata GET200；公开 S3 inventory200；代表信号 HEAD200/Range206 | 无需登录的 public tree API code20000；participants/metadata GET200；代表信号 HEAD200 |
| 实际任务 | dribble 纯 MO 与 MI，另有静态/休息/混合；ballpass、passing 另计 | 右上肢四方向 MI（水平、垂直、两对角方向），每次 10s |
| 必要 EEG 体积 | 35 人 dribble 10.7030GiB；105 raw 三任务 54.1741GiB | 90 BrainVision EEG runs 及其侧车 29.777GiB；完整仓库 92.286GiB |
| 工程优先方案 | 预先平衡选择 10 人 dribble + 固定元数据 3.1802GiB | 先保留完整公开 manifest，完整 EEG 超当前预算 |

推荐从 **Han** 开始工程接入：许可文件明确、固定版本可保存 SHA256、公开信号接口经过实际 Range 检查，工程 10 人子集还能给另一套新源与处理留出空间。完整 35 人名单与 manifest 仍保留；没有把工程 10 人子集说成已接入完整 35 人。

Han 必须保持独立 sports MO/MI 域。A11 与 A22 是观察/想象条件，不是传统左右手 MI 类别。全部 35 人 dribble 官方事件去重后，A22/MI 实际 4195、A11/MO 实际 4197；20/25/27 各一条 A11 完全重复已验证，另有17的一条混合 A88重复。缺失/重复和25的静态/休息标记异常保留为质量检查，不作作者造假推断。

MIND 的四方向更接近实际 MI 分类，但不是 longitudinal retention 数据。官方论文明确每个 session group 内第一 MI session 固定为水平/垂直，第二固定为两对角，三个 session groups 共六个 within-visit MI sessions、120 MI trials。当前 run-01 events.tsv 也实际先出现20条水平/垂直、后出现对角事件。因此四类标签的方向对与 acquisition half 混杂，普通随机 trial CV 不能消除。应使用明确 subject/run/session/half 边界，并独立报告方向对内的可比结果。不能把该离线数据或 Han 的 KVIQ 问卷当作 human skill retention 的证明。

ScienceDB 当前仓库确实公开，旧“直接 inventory 待核”已由本次实际公开 API 解消；不能继续说 signal 不公开。尚未优先选用是体积与内部许可文本不一致，而不是假定 ScienceDB 受限。README 详细段与 participants 一致为28右手、2无明确偏好；abstract 的全右手表述是简化，优先使用真实 participant table。

下载清单与 HTTP 原始证据：

- Han：`han/download_manifest_dribble35_1.1.0.json`、`han/download_manifest_stage1_10subjects_1.1.0.json`、`han/download_manifest_all_raw_1.1.0.json`；原始 tree、S3 三页 XML、180份 metadata、Range1024B、HEAD/Range receipts、校验和均在 `han/`。
- MIND：`mind/all_files_manifest.tsv`（1772 files）与 `mind/eeg_only_manifest.tsv`（690 files），含官方 fileId、path、size、MD5和公开下载 endpoint；目录全部 inventory 原始结果与 HTTP receipts 在 `mind/`。
- MIND 官方论文：本目录 `mind_official_descriptor.html`、`mind_official_descriptor_text.txt`、`mind_official_descriptor_http.json`，官方 URL https://www.nature.com/articles/s41597-026-07807-x 。

OpenNeuro、GitHub、S3是同一个 ds007327 source 的镜像和下载通道，人数只计一次；ScienceDB 的 BIDS、sourcedata、derivatives 也不重复计 MIND 人数。两个数据集均未开始实际大下载。
