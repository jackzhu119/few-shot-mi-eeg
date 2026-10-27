# Reproduce the external replication

The scientific execution version is `457e7bdaad96e84782b6fe968f88925a1200c4b3`.
Protocol: `docs/paper2_external_validation_protocol_20261027.md`.
This analysis adds BNCI predictions; it does not refit Kumar models.

## Public saved-prediction reconstruction

From the repository root, using an existing Python environment with NumPy:

```bash
python scripts/replay_paper2_external_saved_predictions_20261027.py --output-dir /tmp/paper2-external-replay-01
```

Use a new output directory on subsequent checks. This reads the 36 public JSON
prediction files and nine trial-role manifests, verifies labels/identities/budget,
recomputes BA and the fixed participant inference, and writes
`replayed_aggregate.json`. No EEG, model tensors, network, fit or forward is used.
All numerical cohort/contrast fields match `aggregate.json` exactly.

```bash
python scripts/render_paper2_external_validation_20261027.py
```

This renders Fig5 from the saved participant/run records. The original four V3
figure exports need not be regenerated. Document exports use:

```bash
python scripts/build_paper2_discovery_revision_20261027.py
```

The document builder needs its existing Pandoc/XeLaTeX/python-docx/PyMuPDF stack;
these document tools are not training dependencies.

## Raw-data acquisition, execution and resumption

The fixed raw manifest contains eighteen official URLs' basenames, byte lengths
and versioned NEMAR SHA256 values. The original-source license is CC BY-ND4.0.
The data adapter requires NumPy and SciPy; the existing V2 comparator is reused.
One CPU process and one BLAS thread suffice. Keep raw/prepared/model files
outside the Git checkout, with at least about1.2GiB initially free.

```bash
python -u scripts/run_paper2_external_validation_20261027.py --root /absolute/private/path/bnci001-v1-20261027
```

That same command resumes completed models/evaluations instead of refitting.
This is a reproduction command, not a request to rerun the completed study.
The actual invocation/exit and immutable science hashes are recorded beside this
README. The school GPU environment is not needed and was not operated.

## R2 durability

The existing uploader was actually invoked with full readback selection. Its
original run01 receipt recordsHTTP401 on all208 objects: no successful upload or
remote GET. Do not interpret the planned keys or runtime credential-ready status
as backup. After the existing secure R2 permission is restored, a new receipt
filename can resume immutable transfers with the existing `sync_research_r2.py`;
no scientific fit needs to be rerun. Do not overwrite the failed receipt.
