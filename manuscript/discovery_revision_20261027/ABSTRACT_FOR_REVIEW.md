# Spatial-filter refitting improves limited-label EEG decoding beyond classifier recalibration

Biomedical Engineering / Biomedizinische Technik — author-review draft.

**Objectives:** To quantify the added value of spatial-filter refitting beyond classifier recalibration with approximately 20 current-session labels.

**Methods:** We compared frozen common spatial patterns and linear discriminant analysis (CSP/LDA), classifier-only recalibration and full refitting in 18 participants across six Kumar2024 sessions. The predefined primary cohort contained 12 participants. The two updating methods received identical source and current-session labels. Later component experiments used the six development participants.

**Results:** Full refitting achieved 65.36% balanced accuracy, 7.42 percentage points above freezing (95% participant-bootstrap interval 2.49–12.48). The secondary, matched-label full-minus-classifier-only gain was 5.47 points (2.17–8.91), accounting for 73.7% of the mean total gain. It was positive in ten of 12 participant averages and all five target-session averages. At the 20-label cap, fixed-normalization neural adaptation was 1.50–1.91 points higher than adaptive normalization and produced fewer single-class predictions. Smaller-budget profiles differed. Strong-reference comparisons favored simpler geometric decoders; source-functional constraints changed accuracy little.

**Conclusions:** Matched-label component analysis identified spatial-filter refitting as the main contributor to the observed recalibration gain. It separates the value of updating the representation from the value of recalibrating its classifier.

**Keywords:** batch normalization; brain–computer interfaces; covariance alignment; motor imagery; transfer learning
