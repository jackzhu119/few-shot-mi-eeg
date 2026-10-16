# Isolated CPU budget implementation

This is implementation and synthetic software-validation evidence for sections2,
4 and5 of the [frozen exploratory protocol](../../../docs/kumar_component_exploratory_protocol_20261016.md).
No real EEG/model loading, new fitting or query evaluation was performed while
preparing these files. Scientific execution requires the separately bound current
user authorization and the monitored `--execute` entry. The protocol remains
post-exposure exploratory; original results and their statistical identities stay
unchanged.

Entrypoint: `scripts/run_kumar_component_budget_cpu_20261016.py`. There is no
source fit. Source TRAIN40, chronological support prefixes4/8/12/16/full and
fixed target queries retain original roles and preprocessing. The original
frozen query predictions at every budget and both original updated methods at
full support are identity-joined saved results. Their provenance explicitly says
`historical_predictions_reused=true`, `fit_attempted_in_this_replay=false` and
`fit_completed_in_this_replay=false`. The old fit-audit file must prove the same
source/current-support IDs. Smaller-budget updates, the one fixed EA comparator
and half-support validation are new scientific work only when actually executed.

The EA path uses a fixed Helmert21x22 matrix, centered per-epoch covariance with
denominator T−1, separate arithmetic source40/current-prefix references, float64
eigendecomposition, positive eigenvalues and condition≤1e12, no ridge, and
re-embedding via H.T R^(-1/2) H to22 channels. CSP/LDA settings come directly from
the unchanged historical factory. Query arrays enter prediction transform only.
The drift feature separately uses a mean of individually trace-normalized
centered covariances; it is not the EA reference.

## Invocation and binding

From the existing checkout and venv, a metadata-only check is:

```bash
python scripts/run_kumar_component_budget_cpu_20261016.py \
  --config NEW_CONFIG.json --protocol docs/kumar_component_exploratory_protocol_20261016.md \
  --split-manifest research_logs/kumar_cross_session_20261012/protocol/split_manifest.json \
  --baseline-root results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z \
  --saved-predictions results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z/query_predictions.csv \
  --output /ABSOLUTE/FRESH/OUTPUT
```

This checks JSON/CSV/text/source hashes, current host/resources and actual
installed-version metadata. It imports no NumPy/SciPy/sklearn/MNE and reads no
EDF or NPZ. It writes no output/claim. To perform the authorized scientific run,
add `--authorization NEW_AUTHORIZATION.json --execute`. No cost artifact or
additional parent-ACK artifact is required.

The new config must contain `schema_version:1`, `synthetic:false`, all18 original
`subjects`, original `data_root`, `budgets:[4,8,12,16,"full"]`, `seed:42`,
`threads:1`, `max_seconds:3600`, the old config path `old_config` and its
`old_config_sha256`, `split_manifest_sha256`, `protocol_sha256`,
`baseline_execution_receipt_sha256`, `source_code_pins`, and `input_text_pins`.
The optional explicit EA block must be exactly
`{"basis":"helmert_21_reembed_22","ddof":1,"condition_limit":1e12,"ridge":0}`.
Code pins map repository-relative paths to freshly computed SHA256 and must
include this entrypoint, old resource-monitor script, old baseline runner,
unchanged Kumar loader, and unchanged CSP/LDA factory. Text-input pins must
include the old selection/source manifest, prior audit `source_events.json` and
the prior audit run JSON for every selected TRAIN/support/target-query run.
Extra ordinary text input pins may be included. No EEG or model file is opened
to prepare those two maps.

Authorization fields are `schema_version:1`, `status:"direct_user_authorized"`,
`prompt_path`, `prompt_sha256`, `config_sha256`, `protocol_sha256`, the identical
`source_code_pins`, actual `host_identity` from the existing monitor, and absolute
`output`. The original UTF8 substantive prompt SHA is recorded in the protocol;
the authorization can additionally identify the author's actual execution grant.
No expiry or new approval framework is introduced. Source arrays are freshly
file-hashed against the old output manifest, loaded with `allow_pickle=False`,
schema-checked, and bound to old before/after canonical array digests. They are
never written. Dataset/model/text/code bindings are freshly checked again after
the scientific consumer; failures stop the run.

## Consumer and failure behavior

The existing `/workspace/.locks/few-shot-mi-eeg-cpu.lock` is acquired exclusively
and inherited by one serial scientific child. Its canonical fresh
`OUTPUT.operation/claim.json` binds parent PID/start identity, actual host and
deadline. A worker checks the live parent command is this script's monitored
`--execute`, so a generic Python parent cannot invoke the private path. Numerical
threads are1. The reused procfs-safe monitor samples complete child-tree RSS at
0.25s, caps RSS at2GiB, preserves1GiB host/cgroup headroom and2GiB disk, requires
3GiB effective startup memory, and subtracts30s cleanup from a3600s monotonic
deadline. TERM/HUP, unstable/missing proc visibility, I/O, hashes and unexpected
exceptions fail closed. PID-safe cleanup and failure receipts are retained; no
automatic retry creates another claim. A zero exit is explicitly pending
independent audit, never automatically accepted.

One-class support prefixes remain included because the union contains source40
with both classes. Predefined unestimable fits, numerical linear-algebra failures
and EA positivity/condition failures fall back to the saved frozen query action;
the row records the fallback and never claims a completed updated fit. Unexpected
ValueError and storage/hash failures propagate. If the chronological validation
holdout lacks a true class, its three BAs remain empty and
`holdout_defined=false,holdout_fallback_frozen=true`; the selector fixes both CV
gain features to0. A numerical failure of one otherwise-defined validation
candidate only falls back that candidate, with separate candidate flags/reasons;
the other candidate remains evaluable.

## Derived-file interface

Each subject directory and the combined output have:

- `query_predictions.csv`: subject/cohort/session/run/budget/k/method/trial ID,
  true/predicted class, historical-reuse/fallback and synthetic flags.
- `session_metrics.csv`: the same action/budget identity, BA and query identity
  hash/count, support class counts/missing-class flag, prediction class counts and
  collapse, historical-reuse/fallback flags and reason.
- `full_support_features.csv`: subject/cohort/session, source/support ID hashes,
  counts, `frozen_source_BA_all_support`,
  `source40_to_support_trace_normalized_cov_frobenius`, chronological-half counts,
  `holdout_BA_frozen`, `holdout_BA_lda_only`, `holdout_BA_full_refit`, defined/whole
  fallback flag and the separate two candidate fallback flags/reasons.
  Explicit `support_cv_lda_gain` and `support_cv_full_gain` are the defined BA
  differences, or0 for an undefined holdout; the consumer independently recomputes
  and checks them to absolute tolerance1e-12.
- `full_support_outcomes.csv`: subject/cohort/session/n_support/n_query,
  `query_trial_ids_sha256`, `BA_frozen`, `BA_lda_only`, `BA_full_refit`,
  `frozen_source_query_BA`, synthetic flags. Source-query BA comes only from old
  source-only saved predictions; it is an explanatory outcome, never a feature.
- `source_support_trial_provenance.json`: version1, actual chronological source,
  full-support, first-half, holdout and both validation fit ID lists, no query IDs.
  The two fit lists exactly equal source40+first-half. Actual intersections and
  prefix order can therefore be checked independently by the selector.
- `fit_access_audit.json`: every budget/validation action's actual allowed fit
  IDs, query or holdout evaluation IDs, reference scopes, attempts/completion,
  reuse/fallback flags and private-checkpoint file/array hashes.
  `subject_receipt.json` binds unchanged source array state.

Per-subject loader provenance, original full-fit verification and after-input
verification are retained. The combined `input_before_after_manifest.json` lists
all read dataset/model/text hashes; the final execution receipt records code
pins, actual Git HEAD/versions and every derived output SHA. Every successful new
budget/validation fit also persists a private pickle-free NPZ under
`OUTPUT/model_states/SUBJECT/`; LDA-only states retain source CSP plus new LDA,
full refits use the original `model_arrays` helper, and EA additionally retains
H, both references and both inverse roots. A fresh file SHA and pickle-free reload
must reproduce the canonical array digest before the next fit. Historical reuse
creates no new checkpoint. These NPZs remain in private storage/R2 and are
excluded from Git/public packages; no EEG, fitted arrays, credentials or
third-party text is publicly exported. The pure synthetic engine permits a
missing sink; the actual monitored worker always provides one.

`cohort` is `development6` or `remaining12`. Identity SHA is SHA256 of UTF8
`json.dumps(chronological_ID_list,ensure_ascii=False,separators=(",",":"))`.
No budget/bootstrap significance or policy inference is produced by this CPU
entrypoint; those use saved derived outputs in separately audited analyses.

## Actual software validation

The final entrypoint SHA256 is
`381bc4739698d7be7c76b2b8c4d05d4d944d0c6e3c3b570f1c2fb60a5cceb5d1`.
The two budget test files passed79 synthetic tests, including one real MNE
CSP/LDA fit on generated CAR22/EA arrays,30 independent checkpoint replays
(including4 chronological-half holdouts), actual MNE state replay, and fail-stop
storage/hash tests. Targeted Ruff passed. This validation read no historical EEG
or model NPZ. The separately tested selector passed30 synthetic tests.

The always-synthetic script `synthetic_producer_consumer_check.py` actually ran
the producer for18 generated participants×5 sessions, wrote the three CSV/JSON
interfaces, and ran the selector on those saved files. Its output is
`synthetic_selector_integration/run01/`; all90 rows were accepted, including one
undefined true-class holdout. The receipt marks `synthetic=true`,
`software_validation_only=true` and no scientific-result claim. The synthetic
producer used fixed four-power features plus real shrinkage LDA; the separate
MNE test validates the actual CSP/EA path. This is a software contract check,
not a real decoding result.

The fixed phase consumer is dispatched only for
`analysis_mode:"phase_window"`, with its own mandatory phase-script code pin and
separate configuration/claim; default `budget` mode neither imports nor requires
that file. Only the fixed `execute_bound_inputs(args,config)` interface is
available; arbitrary consumer paths are not accepted.
