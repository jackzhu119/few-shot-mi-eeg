# 仓库主页与文件导航整理（2026-10-25）

本次整理将主页改为“当前稿件、学校HPC扩展、结果与复现”三个入口，目录按用途建立索引。现行科学结果、稿件内容、程序、固定下载地址、模型身份和训练行为不变。

## 完成内容

- 精简根目录`README.md`与`CURRENT_PROJECT_STATUS.md`，突出2026-10-19投稿文件、现行伦理声明、原54模型结果，以及单节点2GPU/24CPU/128G的学校入口。
- 更新`manuscript/README.md`、`experiments/README.md`与`results/README.md`，去除将早期行政/Phase0状态当作当前入口的混淆。
- 新增`docs/README.md`、`research_logs/README.md`、`releases/README.md`和`training_status/README.md`，按协议、验收、下载、实时状态分组。
- 将原main/研究分支主页与状态页、早期目录说明保存到`docs/archive/`，共7份快照；旧相对链接改为原固定提交链接，来源与SHA256写入清单。

## 文件与发布边界

原论文PDF/Word、图件、补充材料、原始/派生数据、模型、脚本、配置、锁文件、旧审计回执以及实际训练状态JSON均保留原路径和内容。没有重训、再次query、下载EEG或启动/停止学校任务。此前未提交的组件工作保持未提交状态。

`main`只接收本次导航文档。HPC代码、数据分片与实时训练JSON继续位于`research/paper2-hpc-v2-20261023`；main页面使用明确的跨分支链接，不将整个实验分支合入main。研究分支同步相同导航，保留学校同步器并行写入的进度提交。

## 核验

核验范围为活跃导航页的相对路径、main与研究分支的文件可用性、归档来源/内容SHA256，以及文档专用提交的变更清单。没有因文档整理重跑科学测试或实验。历史快照保留当时的旧声明/命令，实际使用时以当前入口为准。

机器可读核验见[repository_organization_validation_20261025.json](repository_organization_validation_20261025.json)；归档来源见[archive/SOURCE_MANIFEST_20261025.json](archive/SOURCE_MANIFEST_20261025.json)。
