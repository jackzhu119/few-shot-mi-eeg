# JNE 投稿前核查与整改

核查日期：2026-11-04（Asia/Shanghai）。输入版本：`ff9f6c47eea2745174a233bd4310b43d59cb6f5c`；本次仅修改投稿文字、表格呈现和复现说明。

## 已直接修正

1. **补充表编号。** 原补充方法有27张表，其中18张缺少编号标题。现全部按出现顺序编为Table S1–S27，更新原有9处编号及相关文内引用。每张表的数据块SHA256与原版本一致；完整对应关系在`manuscript/jne_alignment_20261104/SUPPLEMENT_TABLE_INDEX.json`。首个章节标题与首表也已保持在同一页。
2. **query数量。** 明确3,960个既定target-query身份中，30个边界短窗被排除，最终保留3,930个完整窗口。没有再次排除30个窗口，也没有改变既有结果。
3. **LDA先验。** 补明CSP/LDA各臂按各自拟合集的类别频率估计LDA先验；冻结使用source，更新使用source/support并集。这是对已执行代码的说明，不是改参数或重新拟合。
4. **缩写。** 首次出现时补全RMS和NLL，补充方法缩写表同步更新。
5. **数据访问。** 保留BNCI原始来源网址，并补充已核验的NEMAR nm000139/v1.0.3版本化镜像。原网址在本环境返回403，不能据此断言全球失效；镜像保留原始文件身份与许可范围。
6. **作者审阅说明。** 将过时的“overlap table”改为实际存在的comparison，避免指向不存在的表。

## 核对结果

- 主稿为165词四段式摘要、5图、2表，完整Word提取约5,233词；补充方法为3图、27表。23页主稿为单栏审阅PDF，不是期刊排版页数。
- 主稿与补充文件的数值、公式、结果表、历史主要/次要角色、bootstrap区间和Holm家族保持原定义；27张补充表逐块核对一致。既有弱类、左右召回、纠正/引入错误、RMS比较和窗口分析的结论没有改变。
- 真实数据图仍为Matplotlib矢量PDF/SVG与600 dpi TIFF；底层10份图表CSV逐字节一致。PDF未发现裁切、空白页或丢失引用，Word表格和公式可编辑。
- 伦理声明继续引用2023年国家办法第32条第（一）项；原始采集伦理与本次二次分析分开，无学校确认表述。AI辅助范围、作者贡献、无资助及无利益冲突声明保留当前真实记录。
- 未新增训练、query推理、种子、策略或数据集；未操作HPC、Pod、投稿系统或main分支。

## 作者确认与投稿系统步骤

- **已完成（2026-11-04）：**三位作者已明确确认实质审阅重要学术内容、批准`79c0c53`最终版、同意投稿JNE并承担作者责任；署名顺序、贡献、单位、邮箱及AI披露均确认准确。本次仅将该确认写入声明和导出文件，不改变获批科学内容。
- 据实填写投稿系统的原创性及相关稿件问题。编辑文件中的事实性共享说明保留；没有代作者签署无相关稿件或完全全新数据的声明。
- **直接文件版：**初投稿使用`UPLOAD_FILES/`中的7个PDF/CSV文件，不再上传ZIP；具体对应关系见`DIRECT_UPLOAD_README.md`。原压缩包在固定`407e6ce`版本保留，科学内容与作者批准不变。

未发现需通过重训才能解决的新增结果或格式错误。以上检查覆盖文件与证据一致性；稿件的科学价值和录用由编辑及审稿人判断。

## 官方依据与检查记录

- [JNE文章类型与摘要要求](https://publishingsupport.iopscience.iop.org/journals/journal-of-neural-engineering/about-journal-neural-engineering/)
- [IOP初投稿格式](https://publishingsupport.iopscience.iop.org/questions/article-format/)
- [JNE作者指南：缩写、表格、图和补充材料](https://publishingsupport.iopscience.iop.org/journals/journal-of-neural-engineering/)
- [IOP作者责任](https://publishingsupport.iopscience.iop.org/questions/ethics-of-authorship/)
- [NEMAR固定版本镜像](https://nemar.org/dataset/nm000139?v=v1.0.3)

独立科学核查、格式核查及修正后回执：`research_logs/paper2_jne_presubmission_20261104/`。最终文件验证：`research_logs/paper2_jne_20261104/FINAL_VALIDATION.json`。
