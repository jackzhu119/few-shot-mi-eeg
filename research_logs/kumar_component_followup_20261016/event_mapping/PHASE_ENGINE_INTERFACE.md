# Phase-window engine: tested implementation, not a completed scientific run

The pure engine is `scripts/run_kumar_phase_window_cpu_20261016.py`. It implements
sections 3 and 5 of `docs/kumar_component_exploratory_protocol_20261016.md`
(SHA256 `1c3e87ad634148bde031579cd8efb976e75643635d452a2ea69d911ccc9b09fc`).
Its `__main__` refuses standalone scientific execution. Reuse the existing
guarded CPU operation for host authorization, immutable input/source-state
verification, claim, global lock, deadline, RAM/disk and 0.25-s complete-tree
monitoring. Do not invoke the old generic formal-training route.

The caller supplies:

1. All frozen trial rows and all corresponding original-phase rows, including
   missing rows. `select_common_trials` preserves the original partial exclusion,
   checks exact identity/class/512-Hz clock and a two-second interval within the
   verified same-class phase and recording extent.
2. A reader verifying each original EDF/hash/22-channel order before returning
   volts for the precise requested interval. `materialize_window_arrays` reads
   only eligible source TRAIN, original current support and target query. Its
   activity filter sees only the 1,024 extracted samples. A verified float32
   frozen cue cache may replace repeated cue-window preprocessing.
3. Read-only original cue source arrays, exact original fit provenance and saved
   frozen predictions restricted by trial ID to the common queries. Original
   source SHA256 and predictions must be tied to their original receipt, never
   relabeled as a new fit. The engine verifies saved frozen predictions against
   the original state, preserves its parameter hash, and fits a separate new
   activity2s CPU source CSP/LDA. No EEGNet checkpoint is fitted or loaded.
4. Persistent `emit(record)` and private `model_sink(arrays, context)` callbacks.
   The former preserves fit attempts, fit completions and every metric partial;
   the latter exclusively writes the new source/update NPZ and verifies its
   bytes/hash before returning. Storage, permission, hash and unexpected errors
   propagate and stop before the next fit. Only an explicitly caught estimator
   `numpy.linalg.LinAlgError` has the predeclared scientific fallback.

`evaluate_participant` always returns 30 target cells: five sessions × two
windows × three original actions. Exactly 18 calls give 540 cells, including
undefined cells. A one-class current support is allowed in the same source40+
support union as the original pipeline; its class counts/flag remain explicit.
An entirely known but zero-eligible support triggers a labeled frozen fallback
without a redundant source-only update fit. Unknown support makes updated
actions undefined, rather than pretending no labels were available. Frozen
inference on a known query subset remains described with its missing counts.
Empty/one-class query BA is null. No query label enters fitting.

The parent operational clarification permits descriptions of a known common
query subset while other query trials have unknown phases. Every metric records
the unknown count and subset scope. A participant endpoint requires five defined
sessions and separately flags whether all original query phases were known;
these selected subsets cannot replace the original 12-person endpoint. Both
windows must receive identical fit/support/query identities. Any later metadata
recovery updates only those missing records under the same fixed eligibility,
not the two-second rule.

`aggregate_participants` uses equal session means before participant aggregation,
the existing development/remaining cohorts, paired complete participants and
10,000 bootstrap replicates with seed42. It reports within-window component
contrasts, paired task2s−cue5s contrasts and the paired change in full-update
gain. These are exploratory pointwise intervals, not a new significance family.

Relevant synthetic tests cover exact extraction, frozen exclusions, identity
matching, all missing cells, source/query fit isolation, support-class handling,
source-state immutability, no next fit after partial/model write or hash failure,
unexpected-error propagation, participant rather than trial resampling, and the
actual CSP/LDA API on synthetic arrays only. Running those tests is not evidence
that real phase decoding has been executed.

The thin real-data consumer is now `execute_bound_inputs(args, config)`, called
only by the canonical existing guarded worker. It reuses that worker's source
verification, private NPZ checkpoint readback and persistence helpers; it has
no separate launcher. Bind `phase_mapping`, `phase_mapping_sha256` and the
exact `PHASE_SETTINGS` dict, add the mapping to `input_text_pins`, and pin the
phase script in `source_code_pins`. All per-subject/root CSV, JSON and JSONL
outputs contain identities, derived predictions/metrics or hashes and can be
reviewed for public release; `private_models/**/*.npz` remain private and must
never be staged to Git. The default scientific input uses the final mapping
file identified by `final_related_test_gate.json`; prior mapping/failed transfer
versions are historical evidence, not a replacement execution command.
