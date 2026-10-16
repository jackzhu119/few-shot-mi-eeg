# 论文2稿件与备份同步收尾

这份记录覆盖原封存稿中的“尚未推送／R2代理阻塞”当前状态，保留其历史事实。
文件名按科研证据的UTC日期编号；主备份实际结束于当地时间2026-10-15
17:37:52（America/Los_Angeles），对应2026-10-16 00:37:52 UTC。

## 已实际完成

- 研究分支 `research/learning-preserving-bci` 已通过正常、非强制Git推送更新到
  [f735ffd1e49915e41f28b727f5d3279ad337c692](https://github.com/jackzhu119/few-shot-mi-eeg/commit/f735ffd1e49915e41f28b727f5d3279ad337c692)。
  支持的GitHub读取工具随后读回相同分支SHA。该固定提交包含完整投稿前优化，
  本次状态／回执追加另行提交，不把旧SHA说成已包含这些后续记录。
- GitHub固定提交的投稿目录23文件、9,233,407 bytes，均已按远端目录元数据的
  length/Git blob SHA与本地原件匹配；本地SHA256也记录在回执中。
  这项核对不是再次HTTP下载全部GitHub二进制，更没有执行模型。
- 私有R2主备份434唯一对象、82,392,690 bytes全部上传，并完整GET／SHA256通过，
  失败0。内容包括284个版本变更文件、整套审阅ZIP、增量Git bundle，以及148项
  私有阅读／排版／实际预览证据。原始EEG、权重、凭据和传输SDK未加入本次备份。
- 主回执为382,673个UTF-8 bytes，完整文件SHA256：
  `7968542cb16687bdeb5670a8372e2054e865ce90278dec8401ec7da4e3171874`。
  [原字节回执](../research_logs/kumar_submission_sync_closeout_20261016/run01/r2_full_get_receipt.json)
  列出每个对象、长度、内容hash、HTTP与完整回读状态。
- [独立回执复核](../research_logs/kumar_submission_sync_closeout_20261016/run01/independent_R2_receipt_review.json)
  逐项重算全部434行及totals，22项汇总检查通过；所有66个seal成员及816个受保护
  历史文件字节不变。这次独立复核没有另发远端GET，也没有写父确认或科研接受。

## 审阅入口

- [带图审阅PDF](../manuscript/plos_one_submission_20261015/manuscript_for_review.pdf) /
  [可编辑Word](../manuscript/plos_one_submission_20261015/manuscript_for_review.docx)。
- [无图投稿格式PDF](../manuscript/plos_one_submission_20261015/manuscript_for_submission.pdf) /
  [Word](../manuscript/plos_one_submission_20261015/manuscript_for_submission.docx)。
- [S1科学方法](../manuscript/plos_one_submission_20261015/S1_Text.pdf)、
  [S2审计复现](../manuscript/plos_one_submission_20261015/S2_Text.pdf)、
  [S1 Data](../manuscript/plos_one_submission_20261015/S1_Data.zip)、
  [图表与其余文件](../manuscript/plos_one_submission_20261015/README.md)。
- [科学整改报告](kumar_submission_revision_report_20261015.md)及
  [本次同步证据](../research_logs/kumar_submission_sync_closeout_20261016/run01/README.md)。

整套离线ZIP为14,732,251 bytes，SHA256
`c9e0cf2ae7138fb0aa1832ee9e23e8fbf1ee0555ed536bc2c2dfdca0b0e370d2`；
增量bundle为9,984,354 bytes，SHA256
`420a5c7a2df4e1ffdf92b466dbf6c9c8598b7c071026331963b35cc2adc5e240`。
两者已纳入上述私有R2主备份；本地副本位于
`/workspace/private_model_receipts/paper2-plos-final-review-20261015/`。

## 保留的边界

原代理失败、MCP审批拒绝、初次缺少boto3及全部原回执均保留。网络恢复后使用
已有认证完成正常Git推送；没有消费、复制或保存聊天中暴露的GitHub令牌。
传输专用boto3按此前真实备份使用的1.43.111版本放入私有依赖目录，实际传递依赖
版本另记；没有安装新虚拟环境或修改科研CPU venv，也不声称所有SDK依赖与旧环境相同。

封存稿、release manifest、PDF／Word、旧整改报告及科学账本没有因同步改写。
包内README的“未同步”末段是当时的真实快照，当前状态以本记录及根状态页为准。
本次没有重训54模型、再次query、追加分析、操作Pod、购买资源或影响论文1。

用户“授予权限继续”支持完成同步，不构成具体MIT／CC BY许可选择、机构二次分析
认定或作者本人完成AI输出核验的证明。这些集中待办与生产字体／原生Word版面限制
仍按[作者核对表](../manuscript/kumar_plos_one_author_worksheet_20261015.md)保留。
稿件仍供作者最终审阅，未代作者投稿，没有写入新的科研父ACK或接受账本。
