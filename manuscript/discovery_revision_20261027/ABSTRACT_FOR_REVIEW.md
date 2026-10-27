# Spatial-filter refitting improves limited-label EEG decoding beyond classifier recalibration

Draft for author review — Biomedical Engineering / Biomedizinische Technik, Research Article. The structured abstract contains181words including the four labels. This is not a submission or an author-approval record.

**Objectives:** To quantify the additional value of spatial-filter refitting beyond classifier recalibration when approximately 20 current-session labels are available.

**Methods:** We compared frozen common spatial patterns and linear discriminant analysis (CSP/LDA), classifier-only recalibration and full refitting in 18 participants across six Kumar2024 sessions. The predefined primary cohort contained 12 participants. Both updating methods used identical source and current-session labels. Later component experiments used the six previously exposed development participants.

**Results:** Full refitting achieved 65.36% balanced accuracy, exceeding freezing by 7.42 percentage points (95% participant-bootstrap interval 2.49–12.48). The secondary, matched-label full-minus-classifier-only gain was 5.47 points (2.17–8.91), accounting for 73.7% of the mean total gain. It was positive in ten of 12 participant averages and all five target-session averages. Neural adaptation with fixed normalization exceeded adaptive normalization by 1.50–1.91 points at the 20-label cap, with different smaller-budget profiles. The geometric candidate underperformed ordinary tangent refitting and Euclidean-aligned CSP; source-functional constraints added little benefit.

**Conclusions:** Spatial-filter refitting supplied most of the observed recalibration gain under matched labels. The component comparisons identify spatial updating and normalization mode as distinct design choices for limited-label longitudinal decoding.

**Keywords:** batch normalization; brain–computer interfaces; covariance alignment; motor imagery; transfer learning

Full local revision generation and the pending workspace-recovery/push status are recorded in [the handoff](../../docs/BMT_REVISION_HANDOFF_20261027.md). Required AI/ethics declarations are retained in the separate local review draft and must accompany the later complete manuscript delivery.
