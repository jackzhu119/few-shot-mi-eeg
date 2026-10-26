# Anchoring mechanism from saved metadata

Only exported text metadata and already saved session-level BA were used. No EEG, model arrays, fit, forward pass, tuning or gate fitting occurred. There are six participants, five target sessions and five budgets. The class-weight distribution contains repeated class/session observations, not 300 independent participants.

The candidate's mean target covariance weight (average classes/sessions within each participant, then participants) was:

| Label cap | EA + empirical alpha | Zero class weights | EA + fixed-tau alpha |
| --- | ---: | ---: | ---: |
| 4 | 0.0301 | 48/60 | 0.1639 |
| 8 | 0.1534 | 27/60 | 0.2857 |
| 12 | 0.2157 | 16/60 | 0.3750 |
| 16 | 0.2901 | 10/60 | 0.4444 |
| 20 | 0.5413 | 3/60 | 0.4983 |

Without EA, the corresponding empirical means were0.4652/0.6834/0.7399/0.7929/0.7682. Thus alignment and empirical anchoring interact strongly: adding EA changes the source/target covariance representations on which the noise-to-distance ratio is evaluated. Lower alpha could reflect smaller source–target distance and/or a changed variance estimate; those components were not exported and the present evidence does not identify which term caused the change.

Zero alpha is a **classwise covariance source-retention behavior**, not a wholly frozen decoder. Support-only EA still defines the target/query whitener and LDA is still refitted on source plus support. It must not be described as skipping adaptation or as a proven safety gate.

The fixed-tau arm identifies one missing support class: sub-13, ses-5, cap4, class1. Its class weight is0 in both empirical and fixed controls. The remaining empirical zeros cannot be attributed to missing classes: the producer also uses0 when a represented class has only one observation, when estimated mean variance is at least squared source–target distance, or when distance is nonpositive. Classwise support counts, variance estimates and distances were not exported, so n=1 and the exact variance/distance fallback frequencies cannot be recovered from this result packet. No extra input-data access was performed to fill that gap.

At cap20, actual support is19 in four participant/session cells and20 in26 cells. Candidate class weights span0–0.9945, while participant-average weights span0.3797–0.7584. More target weight is not a demonstrated performance predictor: sub-1 and sub-7 have similarly high mean weights(0.7584/0.7414) but candidate−EA differences+0.58/−5.67pp; sub-4 has mean weight0.4048 and gain+2.85pp. These are descriptive examples, not a fitted relationship.

The frozen code estimates variance of the class covariance **mean**, sum_i||C_i−T||²/[n(n−1)], and uses max(0,1−variance/distance). This is a transparent support-data calculation. It is not a physiological task-reliability measurement, does not incorporate uncertainty in the finite source mean, and has no established negative-transfer guarantee. The fixed primary outcome does not show benefit over EA-CSP; distributional evidence of adaptive weights cannot substitute for that outcome.

Files: `classwise_weights.csv`, `weight_budget_summary.csv`, `candidate_weight_and_saved_gain.csv`, `participant_weight_and_saved_gain.csv`, `mechanism_summary.json`. Reproduce with `python analyze_anchor_metadata.py <path/to/paper2_results> --output <output_directory>`.
