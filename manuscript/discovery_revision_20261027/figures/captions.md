# Figure captions

**Figure 1. Spatial-component effects and calibration budgets.** Panels show paired component and total effects in the original primary cohort, followed by V2 budget profiles in the six development participants. Points, cohort means and participant-bootstrap intervals show the distribution of effects. Full-minus-LDA-only compares updates using identical labels.

**Figure 2. Geometric candidate, matched controls and ablations.** Full support-budget profiles and cap-20 paired contrasts retain ordinary tangent refitting and EA-CSP as strong references. Ablations separate posterior mean estimation, prediction covariance, source-mean noise and common/contrast variation scales. All candidate-versus-ablation and strong-reference contrasts are displayed together; intervals use participant-bootstrap resampling.

**Figure 3. Neural normalization mode across support budgets.** Fixed-minus-adaptive BN contrasts are shown for both source regimes across all five caps, together with the cap-20 participant contrasts and single-class prediction counts. Fixed and adaptive BN use the same current support, initialization, optimizer budget and Dropout-off setting within each comparison. They differ in normalization during optimization and the resulting inference state. Collapse counts are nested seed/session observations; participant-level summaries define the uncertainty intervals.

**Figure 4. Mechanism simulations and predictive uncertainty.** All 384 conditions retain 50 paired repeats. Panels show candidate-minus-refit BA by source size/correlation, all generating shifts, paired scenario BA, and posterior-versus-point changes in cross entropy and BA. Synthetic results are separate from human EEG endpoints.


**Figure 5. External fixed-budget comparison.** A: participant BA and cohort means. B: participant differences and pointwise 95% bootstrap intervals. C–D: paired differences across five whole query runs. Nine participants contributed 120 query trials each. Updating methods shared 20 support labels; EA references used source/support only.