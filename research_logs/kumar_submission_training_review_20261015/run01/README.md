# Saved training-curve review: portable inputs and outputs

Primary writing evidence: [REPORT.md](REPORT.md).

| Public text output | Content |
| --- | --- |
| `archive_input_index.json` |54 accepted job identities, relative original filenames and full SHA256; no private path or credential |
| `results/all_saved_epoch_curves.csv` |All2,871 recorded epochs, subject/cohort/seed/job, training CE and validation CE |
| `results/per_fit_training_review.csv` |54 fits: stopping/selection/loss endpoints and saved source/target metrics |
| `results/per_seed_source_target_query.csv` |54 model-seed endpoints, all fixed seeds retained |
| `results/per_participant_source_target_query.csv` |18 equal-seed endpoints and descriptive seed ranges |
| `results/cohort_training_review.csv` |Separate development6/remaining12/secondary all18 summaries |
| `results/cohort_per_seed_query.csv` |All three seeds separately, without selection |
| `results/review_receipt.json` |Complete text-input/archive/member/output hashes and zero new model operations |
| `related_checks.json` |Actual seven synthetic tests and scoped lint outcome |

The original model archives are private backups; their old acquisition paths are
historical local placement, not a public data URL. Provide an authorized local
directory containing the54 unmodified archives named exactly as this portable
index. From a repository checkout with the existing analysis dependencies:

```bash
python scripts/summarize_kumar_saved_training_curves.py \
  --archive-index research_logs/kumar_submission_training_review_20261015/run01/archive_input_index.json \
  --archives /absolute/path/to/54_original_archives \
  --output /absolute/path/to/new_text_only_review
```

The output must not exist. This command performs descriptive saved-text
postprocessing only. It does not load model tensors or EEG, rerun query,
construct an optimizer, choose a seed, or change any scientific result. Full
archive hashing reads binary bytes only for integrity. Public readers can use
the supplied CSVs and hashes without downloading private checkpoint binaries;
revalidating the full original archive requires lawful access to those originals.

Relevant software tests (synthetic archive/metadata fixtures only):

```bash
python -m pytest -q tests/test_kumar_saved_training_review.py
ruff check scripts/summarize_kumar_saved_training_curves.py tests/test_kumar_saved_training_review.py
```

Actual final local execution used the existing
`/workspace/.venvs/few-shot-mi-eeg/bin/python` and local immutable originals under
`/workspace/private_model_receipts/frozen-query-originals-54`. These are local
runtime observations, not portable data acquisition instructions. The input
index itself uses relative filenames and matches the accepted54 ledger exactly.
