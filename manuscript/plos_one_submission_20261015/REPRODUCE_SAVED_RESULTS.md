# Reproduce saved results from S1 Data

This companion uses already saved text predictions. No model weights or raw EEG
are needed. Do not start any historical training/query command. It supports
Python 3.11 + NumPy 2.2.6; the remaining imports are Python standard library.
The code performs no optimizer construction, fitting or model forward.

Unzip `S1_Data.zip` into a fresh directory and enter it. From its root:

```bash
mkdir new_qc_output
cp POST_OBSERVATION_PROTOCOL.md new_qc_output/
python -B code/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs inputs \
  --output new_qc_output
```

Choose a different fresh output directory if the name already exists. The code
opens result files exclusively; it does not overwrite originals or silently retry.
The metadata/provenance hash check, exact trial-label joins and method/seed
coverage checks occur before scoring. The 13 output CSVs must be byte-identical
to `results/qc/`. The actual current-code/current-input portable proof already
performed that comparison; packaging checked those exact bytes again rather
than needlessly repeating any computation. Timestamps/provenance receipts differ
by execution and are not expected to be byte-identical.

Check the thirteen tables, after this optional text-only reproduction:

```bash
python - <<'PYCODE'
from pathlib import Path
original = Path('results/qc')
reproduced = Path('new_qc_output')
tables = sorted(original.glob('*.csv'))
assert len(tables) == 13
for source in tables:
    assert source.read_bytes() == (reproduced / source.name).read_bytes(), source.name
print('13 scientific CSV tables match byte-for-byte')
PYCODE
```

For software-only synthetic checks, pytest is needed in addition to NumPy.
The repository test locates its script in `scripts/`. The minimal archive keeps
that identical script in `code/`, so copy it to the expected location first:

```bash
mkdir scripts
cp code/analyze_kumar_saved_query_qc_20261015.py scripts/
python -m pytest -q tests/test_kumar_saved_query_qc_20261015.py
```

The tests do not need data or weights. They cover duplicate/missing/mismatched
joins; absent classes; low class counts; all-seed BA averaging; completeness of
five-session endpoints; participant bootstrap behavior; and changed public QC
flags. Fifteen tests passed in the existing environment; no new environment was
installed. Both script locations contain the same hash-verified code. This copy
changes no scientific input.

To verify bundle-member integrity from the archive root:

```bash
python - <<'PYCODE'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('MANIFEST.json').read_text())
for name, expected in manifest['files'].items():
    payload = Path(name).read_bytes()
    assert len(payload) == expected['bytes'], name
    assert hashlib.sha256(payload).hexdigest() == expected['sha256'], name
print(f"Verified {len(manifest['files'])} payload files")
PYCODE
```

The original frozen source/query protocol and source hashes are in the complete
Git repository; this minimal bundle reconstructs saved-result arithmetic without
weights. It does not independently rerun model training/inference or reproduce
EEG pre-processing. Training curves and plotted-data CSVs are exact existing
saved values for inspection. Software licensing remains the proposed MIT plan
pending author approval; source data keep their original CC BY 4.0 attribution.
