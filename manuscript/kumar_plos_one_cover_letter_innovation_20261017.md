# Cover letter

Dear PLOS ONE Editors,

Please consider the Research Article “Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG” for publication in PLOS ONE.

This study asks which decoder components should receive a short current-session calibration set. Across 18 participants and six sessions of Kumar2024, it compares frozen CSP/LDA, classifier-only recalibration and full spatial-filter/classifier refitting. Both update actions receive identical source-training and current-session labels, providing a direct test of the added spatial update.

In the predefined 12-participant primary cohort, full refitting improved balanced accuracy by 7.42 percentage points over freezing (95% participant-bootstrap interval 2.49–12.48) and by 5.47 points over LDA-only recalibration (2.17–8.91). The spatial-update contrast accounted for 73.7% of the mean total gain. Added prediction-transition analysis traced this advantage to net error correction and higher mean recall for both task classes; the component mean remained positive in all five target sessions and every single-participant deletion summary. These findings identify update location as a practical design choice when approximately 20 new labels are available.

The work complements covariance-recentering, adaptive spatial-filtering and continual-learning studies by isolating the component comparison under matched labels. Calibration-subset measurements additionally distinguish agreement from correct task-score orientation. Chronological partitions, participant-level inference, amplitude sensitivity, complete neural-reference histories and public saved-result reconstruction provide a consistent experimental foundation.

The submission includes detailed methods, saved predictions, complete cohort and class-specific tables, six figures and reproduction code. Original software is MIT licensed, and original manuscript content, figures and derived results are CC BY 4.0. The manuscript reports the original collection ethics and the exemption of this public-data secondary analysis from additional ethical review under Article 32(1) of China's 2023 ethics-review measures. It also discloses OpenAI ChatGPT/Codex assistance with software, analysis, figures and writing.

Sincerely,

Ziyuan Zhu

College of Artificial Intelligence Medicine, Chongqing Medical University

Chongqing, China

zzy2630816871@gmail.com
