# Matched-label analysis identifies spatial refitting and alignment gains in motor-imagery EEG

Biomedical Engineering / Biomedizinische Technik — author-review draft.

**Objectives:** To quantify gains from spatial refitting and alignment with up to 20 current-session calibration labels.

**Methods:** We compared frozen common spatial patterns and linear discriminant analysis (CSP/LDA), classifier-only recalibration and full refitting in Kumar2024 (18 participants, six sessions; 12-participant primary cohort). A fixed-budget external comparison in nine BNCI2014-001 participants added support-only Euclidean alignment (EA-CSP). Updating methods received identical labels within each dataset.

**Results:** In the Kumar2024 primary cohort, full refitting achieved 65.36% balanced accuracy, 7.42 percentage points above freezing (95% participant-bootstrap interval 2.49–12.48). The secondary full-minus-classifier-only gain was 5.47 points (2.17–8.91), accounting for 73.7% of the mean total gain. In BNCI, EA-CSP achieved 77.50%, improving on full refitting by 5.65 points in the secondary comparison (3.15–8.70; Holm-adjusted p=0.01172), with gains in all nine participants. Full-minus-classifier-only was 0.19 points (−1.85 to 2.13). Fixed source normalization also reduced single-class neural predictions at the 20-label cap.

**Conclusions:** Spatial refitting in Kumar2024 and support-only alignment in BNCI2014-001 improved recalibration under matched labels.

**Keywords:** batch normalization; brain–computer interfaces; covariance alignment; motor imagery; transfer learning
