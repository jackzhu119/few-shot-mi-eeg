# S1 Data — preserved original evidence and component-analysis extension

The new [S1_Data.zip](S1_Data.zip) contains **101 files**: all **69 original members**, preserved byte-for-byte, plus **32 extension members**. The compressed archive is **2,078,150 bytes** (1.982 MiB), below 20 MB.

- New ZIP SHA-256: `c6b73502b977b7bd36e27c914bebd686d994596b99f06227131272f428aa3614`
- Preserved original ZIP SHA-256: `dccb1d88f4decae03794bc2fa81ead788cff87d2dd13b172f8b55d7e1e373416`
- Original ZIP: `manuscript/plos_one_revision_20261017/S1_Data.zip`, 1,423,505 bytes.

## Manifest and documentation roles

The original `README.md`, `MANIFEST.json`, `REPRODUCE_SAVED_RESULTS.md`, source-credit and license files inside the archive are unchanged historical documents. Their scope remains the original analyses. New instructions are in `EXTENSION_README.md`; `EXTENSION_MANIFEST.json` lists all 69 preserved originals and the added payload files with their SHA-256 hashes. `EXTENSION_LICENSE_AND_ATTRIBUTION.md` explains the added material's component-specific terms.

The accompanying [S1_Data_manifest.json](S1_Data_manifest.json) records the **complete 101-member inventory**, the final ZIP hash, preservation and CRC checks, and the actual standalone replay. This external manifest includes the hash of `EXTENSION_MANIFEST.json`, which cannot contain its own hash.

## Standalone reproduction of the new analysis

Extract the ZIP, then run this command from its root:

```bash
python code/analyze_kumar_update_mechanisms_20261017.py \
  --inputs inputs \
  --output reproduced_extension
```

The output folder must be fresh. The arithmetic was tested using **Python 3.12.14 and NumPy 2.3.5**. It requires saved tables and the included text/audit inputs; no repository checkout, raw EEG, fitted model or model inference is needed. Figure generation is optional and its additional plotting/font requirements are described in `EXTENSION_README.md`.

## Included extension

`results/update_mechanisms/` contains the 12 CSVs and six scientific JSONs for all three CPU contrasts, both true classes, all participants and all five target sessions. It supplies the class-balanced correction/new-error decomposition, participant and session profiles, bootstrap intervals, influence summaries, reconstructed endpoints and identity/budget completeness checks. Development, primary and secondary all-18 results are all retained.

`validation/update_mechanisms/` includes execution, independent replay and figure-QA records. Four new ordinary CSVs under `figures/` provide Fig5's cohort/class results and Fig6's participant, session and influence data. Figure uploads are supplied separately in the manuscript package.

## Checks actually completed

Every original member was compared with the old ZIP: **69/69 payload bytes and SHA-256 hashes matched**. Every added member was read back and matched to its source bytes. All ZIP CRC checks passed, and the source files and old archive stayed unchanged during packaging.

The actual final ZIP was then extracted into a new temporary directory and the command above executed from that extracted copy. All **18 scientific files**—**12 CSVs and six JSONs**—were **byte-identical** to their packaged counterparts. Runtime receipts retain their actual execution timestamps; those timestamps are not scientific-output equality targets. This validation performed **zero new fits and zero model forward passes**.

The added analyzer is covered by the project's MIT terms. Original added derived results, figure data and documentation are covered by CC BY 4.0 within the author's rights; source-derived identities, labels and metadata retain Kumar2024/NEMAR attribution and source terms. The archive includes no raw EEG, epoch/feature arrays, checkpoints, learned weights, fonts, credentials or installed dependencies.
