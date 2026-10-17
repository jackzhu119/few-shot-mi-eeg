# Reproduce saved numeric text — 2026-10-16 revision

This package uses saved predictions/participant endpoints. Python 3.11 and the
recorded NumPy 2.2.6 support the two producers; pytest is required only for the
optional synthetic tests. No model weights, raw EEG, adapter, GPU, cloud account,
private transport or new dependency installation is required by these commands.
Packaging did not run either producer again: the copied QC and paired-check
validation receipts document their already completed text-only replays.

Unzip into a fresh directory. First verify every payload from that directory:

```bash
python - <<'PYCODE'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('MANIFEST.json').read_text())
for name, item in manifest['files'].items():
    data = Path(name).read_bytes()
    assert len(data) == item['bytes'], name
    assert hashlib.sha256(data).hexdigest() == item['sha256'], name
print(f"Verified {len(manifest['files'])} payload members")
PYCODE
```

The external `S1_Data_manifest.json` additionally hashes the ZIP and every
actual member including `MANIFEST.json`, without circular self-hashing.
The manifest under `provenance/historical_20261015/` describes the original
sealed41-member archive, not the current root. Validate it against that original
archive, or reconstruct its tree using the38 unchanged members and remap the
three historical documentation snapshots to their original root names.

## Optional replay A — the original thirteen QC tables

The QC producer expects an output directory already containing its protocol:

```bash
mkdir new_qc_output
cp POST_OBSERVATION_PROTOCOL.md new_qc_output/
python -B code/analyze_kumar_saved_query_qc_20261015.py \
  --portable-inputs inputs \
  --output new_qc_output
```

Choose another fresh name if needed. The original saved public-input replay
already reproduced all thirteen scientific CSVs byte-for-byte. To compare a
reader's optional replay:

```bash
python - <<'PYCODE'
from pathlib import Path
tables = sorted(Path('results/qc').glob('*.csv'))
assert len(tables) == 13
for original in tables:
    assert original.read_bytes() == (Path('new_qc_output') / original.name).read_bytes()
print('All13 scientific QC CSVs match byte-for-byte')
PYCODE
```

Timestamp/provenance receipts are not expected to match. This is saved-result
arithmetic, not new training, inference, cleaning of fitting data or validation
of task-phase meaning. Undefined/partial/class-missing groups remain retained.

## Optional replay B — the four post-review paired checks

This producer instead creates its output directory exclusively. Do **not**
create `new_postreview_output` beforehand:

```bash
python -B code/analyze_kumar_postreview_statistics_20261016.py \
  --inputs inputs/postreview \
  --output new_postreview_output
```

The already completed portable replay used actual Python3.11.16/NumPy2.2.6 and
matched both saved output files byte-for-byte. With those recorded versions:

```bash
python - <<'PYCODE'
from pathlib import Path
for name in ('statistics_results.csv', 'execution_receipt.json'):
    assert (Path('results/postreview') / name).read_bytes() == (Path('new_postreview_output') / name).read_bytes()
print('Both saved paired-check files match byte-for-byte')
PYCODE
```

The inputs contain 46 repeated-participant contrast rows, not46 independent
people. Full sign enumeration uses the declared inclusive `atol1e-12` BA,
`rtol0` boundary. The strict exact-decimal diagnostic remains separate, including
1070 versus1066 tail assignments for LDA-only minus frozen. Holm adjustment is
only across the four declared checks. Original CI strings are copied, not
regenerated. The review-triggered results remain exploratory and assume a
sign-symmetric participant-level null; there was no randomized allocation.

## Optional software-only tests

The unchanged tests locate their producers in `scripts/`; create that layout
from the identical packaged code, then run the two synthetic suites:

```bash
mkdir scripts
cp code/analyze_kumar_saved_query_qc_20261015.py scripts/
cp code/analyze_kumar_postreview_statistics_20261016.py scripts/
python -m pytest -q tests/test_kumar_saved_query_qc_20261015.py tests/test_kumar_postreview_statistics_20261016.py
```

Existing records show 15 QC and24 paired-check synthetic cases passed. These
tests use `synthetic=true`/`software_validation_only`; they do not validate EEG
physiology, an adaptation policy or human skill retention.

## Reliability/drift data and limits

The six reliability JSONs preserve already saved fold/phase/session metrics and
the original participant-bootstrap draw arrays. The drift CSV and JSON are exact
copies of saved90-session inputs and original association summaries. Their
2000 participant-block correlation vectors were not saved and are not supplied
or regenerated. Source-path/field/SHA provenance is in `SOURCE_PROVENANCE.json`;
the dictionary distinguishes vector contrasts from signed LDA margins and
participant means from session observations. This package does not claim a
portable reimplementation of EEG projection or the historical model fits.

The original comparison, training and plotted tables are saved results for
inspection. Original and added data remain qualified by sample eligibility,
prior result exposure, unmatched cross-architecture budgets and cue-anchored
window semantics. Full raw-signal/preprocessing/training/inference reproduction
requires the original versioned data and separate frozen scientific code.

Use the current `LICENSING.md` and full texts in `LICENSES/`. The three old
documentation snapshots under `provenance/historical_20261015/` preserve earlier
statements verbatim and do not override current licensing or these commands.
