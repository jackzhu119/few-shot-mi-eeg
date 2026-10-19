# 2026年10月19日第二轮问题核实与局部修正

基线：`3a806d210cc8c4f25f5d24f9dca61059588616f5`。按作者要求，仅核实本次意见指出的位置；成立的文字可读性问题作局部修订，原科学结果不变。

## 不成立的数值更正要求：Table6下界

Table6的 full refit − frozen / right recall 正确值是 **9.91 [−1.46, 21.75]**。保存的原始精度是均值9.911423674127848、95%区间[−1.4625630167372448, 21.7535503629764]。

S1 Data中的 `results/update_mechanisms/cohort_transition_bootstrap.csv` 和 `figures/Fig5_source_data.csv` 逐字节相同并给出同一数值。初始创新稿`1d78ceb`、`19a5909`、原已提交PONE-D-26-52050.pdf第26页及本轮基线Word/PDF均有该负号；Fig5B也按同一下界绘制。它不是批量替换时引入的错误，不能改成+1.46。原正文报告右类召回均值提高，没有宣称该单独区间排除零。所有表格数字、原主/次比较、原结论、图5和底表保持不变。

## 采纳的局部文字改进

- Scope三段改用连贯表达；含混的“earlier test-result exposure remains part of the study history”改为明确说明：主终点层级与分组预定，四类后处理在观察原结果之后进行。保留实际事后分析性质、单队列、验证标签预算和训练/support潜在伪迹边界。
- Data and code availability第二段删除正文中的伦理文字变更历史和内部目录路径，保留公开代码、版本定位README及S1 Data完整结果包说明。审计记录继续保留在原位置。
- 正文8处把CPU作为算法名称的用法改为CSP/LDA；同步Fig1独立图注和Table3表头。补充材料中的真实硬件、包版本和原代码标识不改。
- AI核验一句改用清晰的trial identifier/file checksum和共享保存预测/metadata复现表述，其余完整AI披露不变。

## 未采用的其它不准确建议

- 21.1%对应1,512/7,156个全部完整窗口，不是query窗口比例；query为922/4,290。Scope保留正确分母。
- 既有公开输入复现是使用共享的已保存预测与trial metadata，不写成“从公开原始EEG端到端重新运行”。
- 代码本未列独立作者署名或出版年，不按所引用原论文的作者名单或PDF元数据日期补造文献16作者和2024年。

本轮不改伦理声明、Abstract、Introduction、Conclusions、统计表数字、文献16、图件或原科学数据；不做新拟合、query前向或bootstrap重算。仅两份主稿Word/PDF按获准文字精准同步，文件manifest/投稿归档相应更新。原S1/S2、附信、checklist及所有图片保持完整字节不变；checklist行号由新PDF实测核对后沿用。

独立证据和逐字替换映射见 `research_logs/kumar_targeted_checks_20261019/run02/`。本轮字节不变检查以基线3a806d2为准；历史证据不被回写成新的结果。


## 导出文件的针对性验收

两份Word均仅修改`word/document.xml`，其余ZIP成员、图片及原数学对象完整字节不变。Table6整表的规范XML与3a806d2逐字节相同；Table3只改方法名称表头，全部数值不变。正式PDF31页、阅读版23页，54页完成文字覆盖、边界和版面检查。正式稿第6页95–100行仍正确涵盖数据访问与身份信息访问事实，因此不改现有checklist。源文18项不变性检查通过；本轮不重复无关全套软件或科学实验。


最终独立核查259项全部通过（0失败），另有83份保护材料共23,467,971字节逐份SHA与基线相同，覆盖S1/S2、附信、checklist、bibliography、全部图源及S1 Data。Table6整表、Abstract、Conclusions和身份访问说明保持原样。具体原精度与历史PDF/图件证据见本轮 `recall_ci_audit.json`；完整文件核验见 `final_independent_check.json`。
