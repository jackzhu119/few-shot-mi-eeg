# 本次直接上传的文件

压缩包已改成真实的PDF、CSV文件。请使用`UPLOAD_FILES/`目录中的7个文件，逐个选择上传，不需要解压或上传任何ZIP。

1. `JNE_Manuscript.pdf`：Complete Document for Review (PDF Only)。数据可用性声明已更新，请用本次版本替换页面里原先的主稿。
2. `Supplementary_Methods.pdf`：Supplementary Data Files (incl. Multimedia)，替换原先版本。
3. `Supplementary_Results.csv`：Supplementary Data Files (incl. Multimedia)。
4. `Supplementary_Budget_Predictions.csv`：Supplementary Data Files (incl. Multimedia)。
5. `Supplementary_Phase_Predictions.csv`：Supplementary Data Files (incl. Multimedia)。
6. `Supplementary_Saved_Records.csv`：Supplementary Data Files (incl. Multimedia)。
7. `Supplementary_Code_and_Reproduction.pdf`：Supplementary Data Files (incl. Multimedia)。

删除页面里失败的ZIP条目后，确认这7项均显示上传成功，再继续。这里只是文件准备，未代操作投稿系统。

## 文件内容

结果CSV含2张主表、27张补表、17份完整统计表及10份图源数据的可逆长格式转录。预算和phase预测文件保留78,600和11,460个既有预测行。Saved Records含612份JSON文档（36份原BNCI和576个敏感性cell，包括544完成及32未定义）及2,340条原始metric行。它们共包含118,240个重复的方法特定CSP/LDA预测值，不是新增独立试次或参与者。代码和完整原始文件继续由固定GitHub版本提供。

每个CSV开头2行是文件标题和说明，第3行是数据列名；读取时跳过前2行。预测CSV在这2条元数据之后的数据字节与原始解压CSV完全相同。JSON记录保留解析后的数值和嵌套结构，格式字节可以改变。所有CSV原小数字符串、空值、未定义状态保留。

`READABLE_COPY/Supplementary_Results.xlsx`是可选阅读副本，不必重复上传；源码数字在其中按文本保存，避免Excel自动舍入。编辑信和声明的独立PDF在`EDITOR_FILES/`中，按后续相应入口使用。

源版本固定为`407e6ce0a17339d5808a7acc14e9745b9dceffbd`。作者批准、科学结果、统计检验、伦理及AI披露均不因这一格式调整而改变。历史ZIP保留在该固定版本，当前上传目录不含ZIP。每个直接文件小于50MB，7个文件合计小于150MB；实际上传成功状态由投稿页面返回。
