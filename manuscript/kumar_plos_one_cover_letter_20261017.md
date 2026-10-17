# Cover letter

Dear PLOS ONE Editors,

Please consider the Research Article “Updating spatial filters improves limited-label recalibration in a longitudinal motor-imagery EEG dataset” for publication in PLOS ONE.

This manuscript examines how a small current-session label budget improves longitudinal EEG decoding, and what is gained by updating spatial filters alongside the classifier. Using 18 participants across six sessions of the public Kumar2024 dataset, it compares a frozen CSP/LDA decoder, LDA-only recalibration and full CSP/LDA refitting. The two update methods use the same 19 or 20 current-session support labels, allowing a direct component comparison within a fixed chronological evaluation.

In the predefined 12-participant primary cohort, full refitting improved balanced accuracy over frozen decoding by 7.42 percentage points (95% participant-bootstrap interval 2.49–12.48). The predefined secondary comparison showed a 5.47-point advantage over LDA-only recalibration (2.17–8.91). The practical contribution is evidence that spatial-filter refitting can add value even with a small calibration set. Participant and session profiles further characterize how these gains vary, providing a basis for evaluating selective updating.

The study complements the acquisition study’s covariance-recentering and Riemannian class-prototype framework by quantifying the incremental performance associated with updating the CSP representation under an identical label budget. It provides a reproducible longitudinal comparison for BCI researchers working with limited calibration data. An always-frozen EEGNet reference, support-consistency diagnostics and amplitude-QC sensitivity give context for the component result. The reported endpoint is decoding of the released cue-anchored task-label windows.

The supporting materials provide detailed methods, saved predictions, participant/session summaries, training histories, figure data and scripts for reproducing the reported numerical summaries. Original code is MIT licensed; original manuscript, figures and derived results are CC BY 4.0 within the documented scope.

The author reports that the research administration office at Chongqing Medical University confirmed on 16 October 2026 that this Kumar2024/NEMAR secondary analysis qualified for exemption from additional ethical review under Article 32, item (1), of the 2023 Chinese ethics-review measures. No reference number was issued. The main Methods distinguishes this exemption from the original study’s ethical approval and informed consent.

OpenAI ChatGPT/Codex assisted with software and validation, saved-result aggregation, figures, source and reference checks, manuscript drafting and editing, and document exports. The manuscript and supplements disclose this scope and document the author’s review of the scientific content.

Sincerely,

Ziyuan Zhu

College of Artificial Intelligence Medicine, Chongqing Medical University

Chongqing, China

zzy2630816871@gmail.com

