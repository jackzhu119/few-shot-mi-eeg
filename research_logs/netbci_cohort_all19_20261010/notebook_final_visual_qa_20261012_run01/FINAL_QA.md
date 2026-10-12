# 最终 notebook / 报告 / 图形 QA（2026-10-12）

结论：在本次检查范围内通过；现有 notebook、报告和科学模型输出没有改写。

- 当前 run03 notebook：16 个单元、12 个代码单元，执行序号1–12，无 error 输出；未重复执行。
- 七幅原生导出 PNG、七幅 notebook 内嵌 PNG、七份 PDF 页面预览均逐一使用 view_image 检查；标题、坐标、单位、图例、注释和局限脚注可读。几何图原点标记邻近样本数注释，数字仍可读，无需改写已关闭工件。
- 21 个 PNG/SVG/PDF 导出与 native_figure_export_index.json 的 SHA/字节数一致。SVG XML 和 viewBox 验证通过；SVG 浏览器渲染未检查。
- HTML 的七幅内嵌 PNG 字节与 notebook 输出逐幅一致；只做结构及字节检查，没有整页浏览器视觉验收。
- summary_run01 和 independence_sensitivity_run01 的所有已登记输入、输出 SHA 均验证；十编号原结果 SHA 仍匹配原收据。独立方法、敏感性与160文件重放复核见引用的原关闭收据，未重新计算。
- 19/14 均指发布编号，不宣称生物学独立；来源复制原因及正确归属未知。观察后来源排除不属于外部确认；行为、固定读取、任务窗口和几何端点保持区分，人类学习、技能保持与新政策因果结论仍不受支持。
- run01 路径显示错误、run02 被替代图形、run03原验证脚本全部保留。此次最终验证 attempt01 的 HTML 字面标题断言错误另存脚本和日志，修正验证器匹配实际 HTML 说明后 attempt02通过；未更改任何科学结果。
- R2 上传、GET及Git提交由根任务和存储关闭任务单独记录，此回执不扩大它们的证明范围。

主要机器回执：`notebook_validation_receipt.json`；逐图观察：`visual_observations.json`；HTML 字节检查：`html_embedded_sha_check.json`。
