# Working instructions

This checkout is for **Learning-Preserving Co-Adaptive Brain–Computer Interfaces**.
Read `README.md`, `ROADMAP.md` and `docs/research_protocol.md` before changing
research assumptions. Use the existing isolated cloud checkout; do not create a
worktree unless explicitly requested. Develop on `research/learning-preserving-bci`.

- Keep decoder adaptation, representation drift, human learning and behavior distinct.
- Synthetic outputs must retain `synthetic=true` and `software_validation_only`.
- Never call offline decoding or geometric stability proven human skill retention.
- Fit learned transformations on training data only. Keep subjects/sessions/runs
  and trial identity explicit; use participants as the independent statistical unit.
- Preserve prior result files. Record configuration, seed, source commit/hashes and
  actual runtime versions. Do not record credentials.
- Do not download complete large EEG archives without inspecting access, license,
  file metadata, volume, disk space and a representative subset first.
- The first-paper repository is a read-only reference. Its frozen identity and
  migration decisions are in `docs/code_reuse_audit.md`; do not modify it.
- Do not create paid compute resources. Current verified target is Python 3.11 CPU.

For this cloud machine, activate `/workspace/.venvs/few-shot-mi-eeg` and use writable
cache paths described in `README.md`. Required software validation:

```bash
python -m pytest -q
ruff check src tests scripts
python scripts/smoke_experiment.py --config configs/smoke.json
```

The full environment also verifies `python scripts/check_data_stack.py` on MOABB
synthetic data. Real EEG adapters, full training and online studies remain separate
validated research milestones, not assumed consequences of these software checks.
