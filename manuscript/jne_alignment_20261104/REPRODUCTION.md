# Reproduce the standalone upload files

Scientific results and author declarations are fixed at `407e6ce0a17339d5808a7acc14e9745b9dceffbd`; the approved scientific base is `79c0c53803efe226088b35991326904254e05023`. This delivery changes only containers and availability wording.

From the repository root, using the existing document/data-formatting dependencies:

```bash
python scripts/build_paper2_jne_direct_upload_20261104.py
```

The data exporter reads the SHA256-pinned historical archive from Git history when the active archive is absent; it requires no network download, EEG, checkpoint, model fit or inference. To export only the unchanged data into another directory:

```bash
python scripts/export_paper2_jne_direct_data_20261104.py --output /tmp/paper2-direct-data-new
```

The exporter creates four raw CSV exports, the optional 58-sheet workbook, INPUT_INDEX.json and DATA_EXPORT_VALIDATION.json. Every result cell, decimal string and empty field is roundtripped; saved JSON objects and vector counts are checked, retaining 32 undefined cells. It performs no scientific metric calculation.

The direct-file builder inserts two metadata records before each CSV header, retaining the entire verified export as the byte-identical following data section. It exports the code/reproduction PDF, rebuilds the main/methods files, copies the seven final files into UPLOAD_FILES, and writes their complete byte/SHA256 manifest. Read delivered CSVs with two metadata records skipped. XLSX source fields are text, with formulas and numeric coercion disabled. The optional workbook is a readable mirror, not all historical raw outputs.

Original source CSV/JSON/GZ files, all code and historical packets stay publicly available at their fixed versions. The earlier 1,471-member archive is preserved in Git history at `407e6ce0a17339d5808a7acc14e9745b9dceffbd`; it is no longer required as a journal upload. The original 1,392-member scientific archive and reproduction checks also remain preserved in their earlier paths. No raw EEG, model weights or credentials are placed in the direct upload files.

Current export inputs and validation: research_logs/paper2_jne_direct_upload_20261104/. The approved numerical reproduction command and dependencies are documented in Supplementary_Code_and_Reproduction.pdf. The current delivery does not rerun that analysis or claim a new experiment.
