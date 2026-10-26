# Upload completed school HPC results

Run the single line in [UPLOAD_SAVED_RESULTS.txt](UPLOAD_SAVED_RESULTS.txt) on `login1`.
It reuses the installed `paper2_start.py` only as a trusted download helper, then executes the pinned, SHA256-verified uploader. It never calls the training start/submit entry. No Git clone, dependency installation or Slurm submission is needed.

The school project is `/public/home/zhuziyuan/projects/paper2-recalibration-v2`; the configuration is `configs/kumar_dev_hpc_gpu1_24cpu.json`; saved results are `outputs/kumar-dev-v2`. The supplied configuration retains its existing GitHub repository, research branch and dedicated status prefix. The script reuses `~/.config/paper2-hpc/github-token` (or the configuration's existing token file). If it is absent, an interactive hidden prompt requests a token with Contents read/write. To replace an expired token, append ` --reauthorize` to the one-line command. No token is embedded in code, command history, output or the export package.

## Published result scope

- All saved classical/neural metric shards, original per-trial neural prediction NPZ files, and classical JSON trial predictions.
- Current/previous saved neural checkpoint histories, best epoch, step, source-validation history and whitelisted fit identity. CPU-only deserialization of the project's own checkpoints creates no model or optimizer and performs no forward/backward pass.
- Classical model metadata read without loading filter/weight arrays, including recorded fit/support identities.
- Completion/progress/failure records, runtime/Slurm logs, configurations and reproducibility source.
- Existing analysis plus participant/session/method/budget summaries produced from saved metrics with the existing summarizer. Its statistical settings and missing-cell handling are unchanged.
- Explicit per-file length/SHA256 inventory, source-data attribution and applicable project licenses.

For the completed 24-task development queue, the expected canonical results are 3,024 metric shards (3,000 target and 24 source), 1,818 neural prediction files, 1,368 current neural fit-stage checkpoints represented by metadata/history, and 1,206 classical model archives represented by metadata. Previous checkpoint generations and logs are included when present. These are expected counts from the declared queue, not a claim that the school originals have already been uploaded or independently audited.

Raw EEG, model/checkpoint binaries, optimizer tensors, normalization arrays, private token files, credential values and caches stay local. Their relevant model hashes/size and exclusion reasons are recorded. Config/log credential redaction does not change school originals. This result export is a publication of saved outputs, not a replacement for private model backup.

## Publication and resumption

The local packet/cache is under `exports/paper2-saved-results-v1-20261026/`. Each packet is split into at most 16MiB files. The uploader publishes all packet files atomically through the supported GitHub Git Data API to:

`training_status/paper2-recalibration-v2/result_exports/<packet_id>/`

It preserves the branch's other files, rejects force pushes, handles concurrent progress commits, and fully GETs every uploaded blob to verify length, Git SHA1 and SHA256. A separate timestamped readback receipt is published and itself fully read back. GitHub network failures retry at most three times per request, never affect training, and leave the local packet/cache intact. Repeat the same command to resume; unchanged metadata is not extracted again and already published blobs are reused. No scientific attempt is repeated.

Completion requires an `upload_complete` event with both `failed_objects: []` and `history_errors: []`, and exit code 0. Save the returned `url`, `data_commit` and `receipt_commit`. A packet with missing/unreadable expected outputs may still be uploaded for inspection, but is flagged incomplete and returns a nonzero exit status. An HTTP401/403 authorization failure needs a valid local token; repeated network retries cannot fix missing permissions.

To inspect the exported files, concatenate the archive `.partNNN` files in the manifest's numeric order, check the combined archive length/SHA256 against `packet_manifest.json`, extract, and check each member against `paper2_results/MANIFEST.json`. Do not mix packets.

## Fixed delivery and checks

- Source commit: `989696e626de6bf44b4101265c8258bd56d1d8d2`.
- Single-file artifact commit: `c355a5b259401b1b4945a1e95fa76639e9ffccdf`.
- Artifact: `paper2-results-uploader-20261026.pyz`, 20,831 bytes.
- Artifact SHA256: `545b2691e6ee49bd6bad08aee4198b5127927accaaa77e87965d63d956d97a1d`.
- 28 focused synthetic tests passed. The actual `.pyz` also passed an end-to-end synthetic saved-file export and repeat run with the original summarizer, zero export errors and unchanged originals. A full download from the pinned public GitHub artifact matched its bytes/SHA256.
- These checks did not upload school data, train/infer a model, access EEG or operate any HPC job.

Details: [validation report](../../research_logs/paper2_result_export_20261026/REPORT.md).
