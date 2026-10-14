# Supervised reliability diagnostic frozen before new fits

This is a post-freeze exploratory follow-up to the already observed null/inconclusive
power/PCA reliability results. Preserve every historical baseline and split. Use
only development sub-1/4/7/10/13/16, source TRAIN runs 0/1 and target support run 0.
The loader filters roles before opening any signal file; source validation and all
query signals are absent. All selected source bytes, continuous numerical signals
and windows must still match their historical hashes.

One fixed candidate: 4-component MNE CSP (Ledoit-Wolf, log average power,
norm_trace=false), source-only fit, shrinkage LDA. Two whole-source-run folds,
refitting CSP and LDA within each training fold, measure source transfer. Eight
seeded training-label permutations per fold refit both supervised steps; these
are descriptive sensitivity controls, not valid exchangeability p-values in a
serial cue design. Do not select a candidate or threshold using these scores.

For support geometry, fit CSP once on both source TRAIN runs, freeze its filters,
and use existing classwise chronological split halves and cyclic phase sensitivity
in that fixed four-dimensional space. Support never fits CSP/LDA. Bootstrap the
six participant means (10,000 replicates), not the 30 support sessions as independent
units. Source fit class separation is optimistic and not an independent accuracy.

Archive per-fold train/holdout IDs, predictions, null scores, support IDs, complete
hash-checked input receipts, script/config/split hashes before fitting, all subjects,
and failures. Do not claim an effective adaptation gate from reliability alone.
A gate needs a separate frozen nested development protocol and matched budgets;
no final query is opened in this diagnostic. Real execution remains distinguishable
from synthetic software tests.
