# Exploratory update-gain feasibility

synthetic=true; software_validation_only=true

All 18 participants were previously exposed. Development leave-one-participant-out and remaining12 evaluation after training on six development participants are exploratory; this is not independent confirmation or a validated gate.

Four source/support features, training-fold StandardScaler and two-target Ridge (alpha=10) are fixed. Ties prefer frozen, LDA, full. Missing holdout classes set both CV gains to zero and force the support-CV selector to frozen. Drift uses the training-participant session median, without query tuning.

| Cohort | Policy | Mean BA (%) | Gain vs frozen (pp; participant 95% CI) | Decline frequency (%) | Mean downside (pp) | Update rate (%) |
|---|---|---:|---:|---:|---:|---:|
| development6 | always_frozen | 50.00 | 0.00 [0.00, 0.00] | 0.00 | 0.00 | 0.00 |
| development6 | always_full_refit | 100.00 | 50.00 [50.00, 50.00] | 0.00 | 0.00 | 100.00 |
| development6 | always_lda_only | 0.00 | -50.00 [-50.00, -50.00] | 100.00 | 50.00 | 100.00 |
| development6 | drift_median | 75.00 | 25.00 [16.67, 31.67] | 0.00 | 0.00 | 50.00 |
| development6 | matched_random_expectation | 100.00 | 50.00 [50.00, 50.00] | 0.00 | 0.00 | 100.00 |
| development6 | ridge | 100.00 | 50.00 [50.00, 50.00] | 0.00 | 0.00 | 100.00 |
| development6 | support_cv | 50.00 | 0.00 [0.00, 0.00] | 0.00 | 0.00 | 0.00 |
| remaining12 | always_frozen | 50.00 | 0.00 [0.00, 0.00] | 0.00 | 0.00 | 0.00 |
| remaining12 | always_full_refit | 100.00 | 50.00 [50.00, 50.00] | 0.00 | 0.00 | 100.00 |
| remaining12 | always_lda_only | 0.00 | -50.00 [-50.00, -50.00] | 100.00 | 50.00 | 100.00 |
| remaining12 | drift_median | 67.50 | 17.50 [10.83, 24.17] | 0.00 | 0.00 | 35.00 |
| remaining12 | matched_random_expectation | 100.00 | 50.00 [50.00, 50.00] | 0.00 | 0.00 | 100.00 |
| remaining12 | ridge | 100.00 | 50.00 [50.00, 50.00] | 0.00 | 0.00 | 100.00 |
| remaining12 | support_cv | 50.00 | 0.00 [0.00, 0.00] | 0.00 | 0.00 | 0.00 |

Participant endpoints average the five sessions equally. All confidence intervals resample whole participants (10,000 draws, seed 42). Downside magnitude is max(frozen BA minus selected BA, 0), including zero for non-declining sessions. The random control is an exact action-mixture expectation within each development LOPO fold or the remaining12 group; its downside is the expectation of action-wise loss, rather than the loss of its mean BA.

The complete CSV summary includes paired differences against each always-action baseline, action rates and participant intervals. Predicted-negative-gain versus actual-decline counts are descriptive session diagnostics, with participants retained as the independent unit. Frozen source-query to target-query decline is an explanatory outcome only. No external validation or novelty claim follows.

Source/support fit disjointness is verified from upstream legal trial-ID provenance. Chronological order is an upstream assertion. Query-set hashes are pairing metadata, and no query trial records, EEG or decoder weights are loaded.
