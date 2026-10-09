# Experiment gate

The executable experiment in Phase 0 is `scripts/smoke_experiment.py`, configured
by `configs/smoke.json`. It uses synthetic data only. See `ROADMAP.md` and
`docs/research_protocol.md` for the gates before real-data longitudinal analysis.

Freeze subject/session splits and event mappings before evaluation. Select any
hyperparameters on a separate validation partition; never tune against the final
test sessions. Keep a per-subject record, input provenance, configuration, seed,
environment and source commit for each run.
