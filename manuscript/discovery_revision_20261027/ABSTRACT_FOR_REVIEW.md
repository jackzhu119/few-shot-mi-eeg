# Matched-label analysis identifies spatial refitting and alignment gains in motor-imagery EEG

Biomedical Engineering / Biomedizinische Technik — author-review draft.

**Objectives:** To determine which spatial update adds value beyond classifier recalibration with 20 current-session labels.

**Methods:** We compared frozen common spatial patterns and linear discriminant analysis (CSP/LDA), classifier-only recalibration and full refitting in 18 Kumar2024 participants across six sessions. The original primary cohort contained 12 participants. A fixed four-method replication added nine BNCI2014-001 participants and support-only Euclidean alignment (EA-CSP). Updating methods received identical labels within each dataset.

**Results:** In Kumar2024, full refitting achieved 65.36% balanced accuracy, 7.42 percentage points above freezing (95% participant-bootstrap interval 2.49–12.48). The secondary full-minus-classifier-only gain was 5.47 points (2.17–8.91), accounting for 73.7% of the mean total gain. In BNCI, full-minus-classifier-only was 0.19 points (−1.85 to 2.13). EA-CSP achieved 77.50%, improving on full refitting by 5.65 points (3.15–8.70; Holm-adjusted p=0.01172), with gains in all nine participants. Fixed source normalization also reduced single-class neural predictions at the 20-label cap.

**Conclusions:** Matched-label comparisons distinguish the contributions of spatial refitting and support-only alignment. Their different effects across datasets make the update operation central to limited-label recalibration.

**Keywords:** batch normalization; brain–computer interfaces; covariance alignment; motor imagery; transfer learning
