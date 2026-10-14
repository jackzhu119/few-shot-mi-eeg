# Independent numerical replay of development measurements

Status: **passed**, 2026-10-14 (Asia/Shanghai). The independent verifier uses
NumPy arithmetic and the six physically restricted development inputs. It does
not import or call producer functions, open original full/query/final-cohort
containers, fit primary decoders or perform adaptation. Runtime was 4.50 seconds.

The reviewed producer SHA-256 is
`c3f19cac305cb72fdbfb539172b198bc67836ec6499730fad8829fe16f27a964`;
the result receipt SHA-256 is
`823dacd72811eba0988fc7adc9decd6f0a7c79264ab21dc8c5f1bb3c29fefff3`.
Executed verifier SHA-256:
`0b0114d03a16f26e04ebb3adae4bba1951e198a506c0ae771c8388f92830294f`.
Exact inputs, endpoint errors and successful check counts are in `receipt.json`.

## Verified scope

- All 12 restricted input files match the actual execution hashes. Metadata,
  feature identities and labels contain only the six fixed development subjects
  and allowed source TRAIN/current-support roles. Producer, configuration and
  plan hashes match the execution receipt.
- All 18 source coordinate states were checked against their declared source
  trials: means, population variances, scales, fit counts, fitted-state hashes,
  PCA centering, orthonormal bases, leading eigenvalues and eigenvector residuals.
  Independent covariance eigendecomposition confirms the saved bases span the
  leading source-only PCA modes. PCA sign choices are not treated as evidence.
- All 36 observed source-fold centroid predictions were reconstructed: all 720
  predictions agree exactly. Source BA, class recalls, thresholds, task axes,
  twofold means and the duplicate identity-control numerical endpoints agree.
- All 7,200 twofold source phase-control values were checked, including their
  14,400 constituent centroid reconstructions. The same 400 shift pairs appear
  across candidates and both folds. Distinct label-assignment counts, pair hashes,
  attempted-fit counts and conditional tail-fraction denominators agree.
- All 90 support rows were checked: current trial identities, label/class counts,
  retained QC flags, source-state bindings, raw-feature hashes, source projection
  SD, signed half contrasts, scalar products and both direction cosines.
  All 3,576 cyclic-control measurements across the two half methods were replayed.
  Original and recomputed half indices, single-class/zero-direction cases and
  per-metric valid/unavailable denominators agree.
- All six 10,000-draw participant-bootstrap arrays were independently regenerated
  from participant means with seed 42. Participant order, cohort means and 95%
  intervals agree. Six participants remain the independent units.

The largest absolute numerical discrepancy was **1.2834e-13**, in a PCA
eigenvector residual comparison, below the declared **1e-9** absolute tolerance.
Source observed and phase-control BA agree exactly. The largest support endpoint
error was 7.55e-15; the largest bootstrap-draw error was 3.33e-16. No discrepancy
requires changing the frozen producer or published numerical results.

## Interpretation limits

This verifies stored-feature measurement arithmetic and provenance. It does not
reconstruct Mu/Beta features from original EEG, establish biological independence,
validate figures, or convert phase controls into formal randomization tests.
Circular wraparound, stationarity and cue-order confounding remain unresolved.
The small six-participant intervals remain exploratory.

The source-transfer intervals include chance and the support-reliability intervals
include zero for all three fixed candidates. These results provide no basis for
selecting a winning candidate, automatically passing a gate-development threshold,
or claiming an effective task-aware adaptation algorithm. The already seen
final-cohort baseline results remain seen; researcher blindness is not restored.
No human-learning or skill-retention conclusion follows from this replay.

The reusable `verify_lowdim_results.py` requires `--inputs`, `--result` and
`--output`; its input scope explicitly restricts development metadata and feature
keys. It writes a new receipt with exclusive creation and does not overwrite
prior verification receipts.
