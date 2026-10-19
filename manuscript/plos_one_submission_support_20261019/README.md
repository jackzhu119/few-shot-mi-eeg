# 论文2：高清图件与投稿系统摘要（2026-10-19）

本目录补充基于固定稿件 `a5efb6078ece84302201556b076f189e8625a577` 的投稿辅助文件。正文、补充材料、图中数值及既有归档包未修改。

| 文件 | 用途 |
| --- | --- |
| [PONE-D-26-52050_submission_20261019_run02.zip](PONE-D-26-52050_submission_20261019_run02.zip) | 最新完整提交包：12份上传文件、6份系统字段、使用说明及校验清单。主稿、S1/S2、checklist、伦理声明、六张图均与现有最新版一致。 |
| [Paper2_High_Resolution_Figures.zip](Paper2_High_Resolution_Figures.zip) | 六张600 dpi原始TIFF、六张原图PDF及高清合并审阅PDF。投稿时使用其中 `TIFF_for_upload/Fig1.tif` 至 `Fig6.tif`。 |
| [Figures_1_to_6_Clear_Review.pdf](Figures_1_to_6_Clear_Review.pdf) | 按1–6顺序合并现有图件PDF，供放大审阅；不是期刊系统生成的预览。 |
| [Abstract_for_Submission_System.txt](Abstract_for_Submission_System.txt) | 与最新版正文一致的266词摘要，可完整复制到投稿系统 Abstract 字段。 |

## 清晰度核查

作者提供的47页系统合并PDF中，六张图均被缩为JPEG，按实际像素和显示尺寸计算为72 dpi。现有原始TIFF均宽4500像素、600 × 600 dpi、RGB、单页、LZW无损压缩。图包内的TIFF是这些原件的逐字节副本；六页高清审阅PDF与原图PDF的逐页渲染相同。

原图PDF保留矢量路径；Fig1文字为轮廓，Fig2–6有可提取文字，Fig4另含栅格热图内容。没有重新绘图、插值放大或修改数据。

请确认系统中上传的是原始TIFF，而非系统合并PDF中的截图。若已经上传原件但预览仍模糊，应检查系统是否提供高质量PDF选项；没有此选项时，可请期刊办公室协助保留清晰的审阅图件。当前核查未下载系统中的实际TIFF附件，不能据预览判断其原始上传字节。

## 合并PDF的其他核查

- 正文31页与上述固定稿核对，无实质内容差异；唯一文本提取差异是 `source-training` 的断行连字符。
- 系统第1页摘要为旧版251词，正文为新版266词。旧系统摘要缺少全部18人的次要汇总：full refit相对LDA-only +3.26个百分点、相对frozen +6.03个百分点。上面的TXT提供完整替换内容；没有代作者修改系统字段。
- 伦理声明采用第32条第（一）项法规豁免依据，不含学校确认本次免审的表述。Table 6的 `9.91 [−1.46, 21.75]` 与保存结果和Fig5B一致。
- 六图齐全；系统排列为4、5、6、1、2、3，建议调整为1–6。
- 系统PDF第44–47页仅是S1、S2、S1 Data及checklist的下载占位。精确官方链接的一次有界读取未获得附件，不能据此核验这四份上传附件的实际字节。

[测量、核查及完整性证据](../../research_logs/kumar_submission_support_20261019/run01/README.md)记录实际范围和SHA256。本目录原创图件与材料沿用项目已激活的限定CC BY 4.0条款；字体、第三方资料及原始EEG不随本目录新增分发。本次未训练、未再次运行query，也未操作投稿系统。
