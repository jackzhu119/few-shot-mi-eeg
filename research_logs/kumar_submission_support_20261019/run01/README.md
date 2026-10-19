# 投稿辅助文件核验记录

科学内容基线：`a5efb6078ece84302201556b076f189e8625a577`。输入为作者提供的 `PONE-D-26-52050.pdf`，47页、1,958,883 bytes，SHA256 `7c728763d8c438334de05aba12d3197f62bd865bde4c7eea20a33a73797b5b46`。

- `clarity_comparison.json`：六张原始TIFF的像素、DPI、原件与交付副本SHA256，以及系统图件实际显示DPI。
- `independent_source_vs_preview_measurements.json`：独立测量；包含原图PDF的矢量路径、文字及栅格对象数量。测量中的小型下载图标不是科研图件。
- `delivery_verification.json`：六页合并审阅PDF与各原图PDF逐页渲染完全相同；ZIP完整性及所有成员SHA256通过。
- `manuscript_page_comparison.json`：正文31页与固定稿的文本核对；30页归一化后完全相同，另一页仅断行连字符的提取差异。
- `form_metadata_check.json`：旧系统摘要与新版正文摘要不一致、图件顺序及伦理表述核对。
- `attachment_read_check.json`：四个补充附件的读取失败范围；不将失败当作附件已通过核验。
- `source_artifact_hashes.json`：此次公开文件对应的原始核查记录SHA256；JSON仅将本机源码路径改为仓库相对路径，并更新摘要TXT路径。
- `submission_bundle_verification.json`：最新完整提交包的12份实际上传文件与现有main逐字节一致；系统摘要、作者信息及伦理声明与最新版一致。
- `published_artifact_manifest.json`：本次交付和核查文件的完整字节数及SHA256；清单自身不计入。

核查不包括新的科学实验、模型推理、原始EEG复算或期刊提交操作。实际投稿页面的访问链接、访问标识和作者提供的系统合并PDF未纳入本次公开文件；原工作区核查文件保留。
