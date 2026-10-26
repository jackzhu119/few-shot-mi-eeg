# Saved-result exporter validation — 2026-10-26

The school completion snapshot reports 24/24 planned tasks complete; the export/upload of original result files must still be run on the school login node. This delivery only supplies and validates that operation. No scientific result is newly accepted by this report.

The original progress snapshot contained 3,006 metric rows, omitting 18 neural source-query shards. The exporter traverses the declared original result paths and records any missing expected artifact explicitly; it does not treat the snapshot as a substitute for originals. Model weights and EEG are excluded; model size/SHA256 and textual histories/metadata are exported.

Focused verification: `python -m pytest -q tests/test_hpc_v2_result_history.py tests/test_hpc_v2_result_upload.py tests/test_hpc_v2_result_bundle.py` → **28 passed**. Tests cover read-only CPU checkpoint metadata, no model/optimizer construction, nonfinite/incomplete history handling, classical metadata-only reads, original prediction bytes, secret redaction, input exclusion, packet reuse, changed-source refusal, atomic Git tree publication, branch races, bounded network retries and full GET hash mismatch reporting. The API transport tests use injected simulated GitHub responses; they do not claim an actual school upload.

The actual distributable also passed a separate synthetic end-to-end run with minimal saved source/adaptation checkpoints, classical metadata and per-trial predictions using the original saved-metric summarizer. Its 37 payload files were verified against the package inventory; both first and repeat exited0, no history errors were recorded, and every source output retained its original SHA256. See `synthetic_end_to_end.json`.

The pinned 20,831-byte artifact was pushed to GitHub and fully downloaded via the same official endpoint downloader used by the school bootstrap. Length/SHA256 matched; see `delivery_full_get.json`. This verifies the downloadable tool, not school result publication.

The exact published one-line command was also executed with a synthetic school home/project and `--prepare-only`: its actual pinned remote download and saved-result preparation both passed without invoking training or upload. See `one_line_entry_validation.json`.

Existing unrelated local component/manuscript files were left untouched. No Slurm/GPU/Pod action, training, inference, new dependency environment or credential copying was performed.
