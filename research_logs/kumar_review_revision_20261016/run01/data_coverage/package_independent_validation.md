# Independent new-package validation

**通过。** 只读核验，无统计/pytest/模型/推理/bootstrap运行，未改repo。

最终核验：69成员，1,423,505bytes；ZIP SHA256 `dccb1d88f4decae03794bc2fa81ead788cff87d2dd13b172f8b55d7e1e373416`；34CSV、19JSON，其余为UTF8文档/代码/许可。

- 全69成员与外部manifest的长度/SHA/CRC一致，内部manifest精确覆盖68payload；无重复名、绝对路径、path traversal或symlink成员，ZIP CRC检查通过。
- 原38成员在原路径逐字节保留；原3文档在historical目录逐字节保留。历史旧ZIP未改。
- 10新numeric候选和7postreview文件均与已审查源逐字节相同；34CSV结构正常，manifest已有行数字段均匹配。
- LICENSE、完整MIT与CCBY4文本、归档repositoryLICENSING与当前root源逐字节一致。外部S1_Data_README/字典/复现说明与ZIP当前对应文档一致。
- 新numericJSON按禁止fitted-state键检查未命中；具体credential值模式扫描未命中，未发现二进制/信号/权重成员。该检查是限定范围的证据，不是形式化完整秘密或版权证明。
- 读代码静态核对真实CLI/inputschema及不同fresh规则；确认argparse必需参数/未知参数拒绝、hash/schema/identity/nonfinite/越界/重复JSONkey/固定tail-family防线、既存或danglingsymlink输出先拒绝、验证先于首次写入。没有执行这些命令。
- 新字典已限定原QC不提供p值的旧句；复现说明已补historicalmanifest原ZIP/remap方法、scripts布局和不同output规则。
- 全部4p值、family4Holm、1070与1066边界诊断、ATOL1e−12BA/RTOL0、原CI字符串及46重复参与者contrast行范围明确。
- Reliability/drift/44partial/629137审计/runtime为saved记录；没有声称补造drift相关draw向量或重复训练/预处理。执行receipt字节比较条件于记录环境版本。

逐项机器检查：

- PASS archive_external_identity
- PASS 69_unique_safe_regular_members
- PASS external_exact_member_set
- PASS internal_exact_payload_set
- PASS all_UTF8_text
- PASS zip_crc_test
- PASS archive_total_uncompressed_matches
- PASS all69external_bytes_sha_crc
- PASS all68internal_bytes_sha
- PASS all_CSV_row_counts_declared_match
- PASS all_CSV_well_formed
- PASS 38old_same_path_same_bytes
- PASS 3historical_documents_same_bytes
- PASS 10candidates_exact_bytes
- PASS 7postreview_source_files_exact_bytes
- PASS root_license_notices_exact_bytes
- PASS external_dictionary_reproduce_match
- PASS no_forbidden_fitted_parameter_keys_in_10candidate_JSONs
- PASS no_likely_secret_values_by_specific_patterns
- PASS no_binary_or_signal_weight_members
- PASS static_invalid_parameter_and_input_guards_present
- PASS external_three_data_documents_match

无未解决finding。完整逐member/CSVschema、sourcebytes、license、staticguards、结构盘点和boundedscan结果见同名JSON。overall README属于父任务；数据README是S1_Data_README.md。
