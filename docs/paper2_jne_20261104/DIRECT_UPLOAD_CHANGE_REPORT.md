# JNE direct-file delivery — 4 November 2026

The failed ZIP upload is replaced by seven actual PDF/CSV files in `manuscript/jne_alignment_20261104/UPLOAD_FILES/`. The main manuscript uses “Complete Document for Review (PDF Only)”; the other six files use “Supplementary Data Files (incl. Multimedia)”. Replace the prior main/methods PDFs and remove the failed ZIP item.

Only delivery descriptions, data-availability pointers, file metadata and packaging changed. Scientific results, methods, inferential roles, negative findings, ethics, AI disclosure and the recorded all-author approval remain unchanged. No fitting, query forwarding or new statistical analysis was performed.

The result export reconstructs 56 source tables with 238,401 exact string cells. Saved records retain 612 parsed JSON documents and 2,340 metric rows, including all 544 completed and 32 undefined sensitivity cells. The 118,240 method-specific prediction values include repeated predictions across methods and are not independent participants or new trials.

Each CSV begins with two rectangular title/description metadata records. Its third record is the data header; readers skip the first two records. The remaining bytes equal the verified export. Original JSON objects are preserved semantically, while formatting bytes may differ. Original files and complete code remain available at fixed commit `407e6ce0a17339d5808a7acc14e9745b9dceffbd`; the original 1,471-member package and earlier neural/synthetic packets are not all embedded in the selected direct exports.

Seven upload files total 25,028,044 bytes. Independent layout/caption/metadata validation and independent source/data/approval validation passed. See `research_logs/paper2_jne_direct_upload_20261104/` for full records. The optional XLSX is a text-preserving reading mirror, not an additional required upload. Editor documents are separate PDFs in `EDITOR_FILES/` for the appropriate editorial entry.

Historical ZIP files remain in Git history at the fixed source commit; they are removed only from the current active delivery. This change creates no new author-approval requirement and does not submit the article.
