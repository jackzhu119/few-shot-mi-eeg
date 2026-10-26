# School HPC V2 result receipt and saved-prediction audit — 26 October 2026

The completed development queue has been received from fixed GitHub receipt commit `0050449a0e61cc357a497dc9939adc4fd1d7519b`, data commit `0bfa581ea948cb8a4546d840e076a9aff1ace466`, packet `f1689db3941ae31757442698`. The server re-run reused the original packet and existing uploaded data; it added another timestamped verification receipt. Both historical receipts remain intact.

## Receipt and completeness

Independent full downloads of README, packet manifest and archive part verified **3/3 objects, 3,575,270 bytes**, all length/Git SHA1/SHA256 checks passed. The compressed archive is **3,573,333 bytes**, SHA256 `a96e2dca20cd654ec6bff236a4fdd85bcab7c8324e9acbb370d8f338ee769af5`. Its **8,983 payload files plus MANIFEST.json** are unique, safe regular-file paths and all listed member lengths/SHA256 match. No failed objects, missing payloads or history errors were recorded. Evidence: `independent_readback.json`.

The canonical originals contain **3,024 metric shards** (1,206 classical +1,818 neural), **1,818 neural prediction NPZ files**, **1,368 current neural fit-stage history/metadata records** (18 source +1,350 adaptations), their 1,368 previous generations, and **1,206 classical model metadata records**. The progress snapshot had omitted 18 neural source-query rows; these originals are now included. Raw EEG/model binaries remain at school; public inventories contain their relevant model metadata/hash rather than weights.

## Independent numerical checks

All 3,024 BAs were recomputed from saved predictions; maximum absolute difference is **0**. Recorded accuracy, where present, also differs by **0**. Query counts, class counts, recalls, collapse flags and probability validity passed. Ordered trial IDs/labels matched across methods/budgets/seeds/families within all 36 participant/session groups. There are 130,980 repeated prediction-evaluation rows, not that many independent observations. Eighteen duplicate neural source-query JSON files exactly match their canonical shards. Evidence and reproducible code: `independent_predictions_audit.json`, `audit_saved_predictions.py`.

The original summarizer was rerun against only these saved metrics with the unchanged configuration; all seven CSVs were byte-identical and summary.json matched apart from its generation timestamp. All 3,000 target cells and 24 tasks are complete, with no missing source-query cells. Every current recorded checkpoint is complete with the prescribed 100 source /20 adaptation epochs; source best epochs/losses equal the minimum recorded validation loss. Recorded totals are **28,800 epochs /37,800 optimizer steps**. This checks exported histories; it is not an independent replay of school weight binaries. Evidence: `independent_summary_audit.json`.

## Scientific reading of the fixed endpoints

These are **six previously exposed development participants**, not 24 independent participants. Neural tasks use all three fixed seeds. The original source54 model ledger, prior scientific results and frozen protocol remain unchanged; this report does not act as any new parent acknowledgement or held-out evaluation release.

At the maximum20-label budget (actual support19–20), participant/session/seed-aggregated target BA is:

| Method | Mean BA |
| --- | ---: |
| Classical frozen | 62.15% |
| Full CSP/LDA refit | 68.65% |
| EA-CSP full update | 70.37% |
| EA + empirical anchored CSP | 69.24% |
| EEGNet frozen | 56.74% |
| EEGNet head update | 56.81% |
| EEGNet full update | 55.89% |
| EEGNet L2-SP update | 55.83% |

The **prespecified V2 primary contrast**, EA+empirical anchoring minus EA-CSP at budget20, is **−1.14pp [−3.52,+1.14]**. The present development evidence does not establish an improvement over that strong comparator. Its secondary contrast against frozen is **+7.09pp [+4.12,+11.55]**, with all six participant-average differences positive. This secondary improvement cannot be substituted for the primary endpoint. Against full CSP/LDA refit the difference is **+0.59pp [−4.77,+6.52]**. Neural head/full/L2-SP differences against frozen are respectively **+0.07 [−0.34,+0.50]**, **−0.85 [−2.45,+0.64]**, **−0.91 [−2.49,+0.57]pp**. All intervals follow the existing 10,000-draw participant bootstrap, seed20261023, and are exploratory pointwise intervals without multiplicity correction.

Both source and target EEGNet query BA are about56% (source participant average56.11%, target56.74%); target weakness cannot be attributed mainly to longitudinal drift. No seed was selected, original predictions/parameters were not changed, and no new fit/forward/query or HPC/Pod operation was performed. Next interpretation should retain the primary negative result and evaluate scientific implications before proposing a separately versioned follow-up; this receipt authorizes no additional experiment.

## Reproduction

Download the original README, packet_manifest and archive part from the fixed commit directory linked below, retaining the supplied receipt basename. Run `python audit_export_integrity.py <download_directory>` before extracting the single archive part. Extract its contents into a local directory containing `paper2_results/`; run `python audit_saved_predictions.py <path/to/paper2_results>` and `python audit_saved_summary.py <path/to/paper2_results>`. These checks read saved outputs only and need NumPy, with no Torch/model/EEG/GPU requirement. They write their own JSON/temporary analysis beside the scripts or extracted result folder; originals remain unchanged. Source code used by the summary check is the exported original `source_code/hpc_recalibration`.

[Fixed original packet and server receipts](https://github.com/jackzhu119/few-shot-mi-eeg/tree/0050449a0e61cc357a497dc9939adc4fd1d7519b/training_status/paper2-recalibration-v2/result_exports/f1689db3941ae31757442698).
