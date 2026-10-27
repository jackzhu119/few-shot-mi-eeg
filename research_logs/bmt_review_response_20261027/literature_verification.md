# Parallel-work and probability-score verification

Official arXiv abstract, experimental HTML and complete10-page PDF of2610.07420v1 were read. The actual submission is5October2026, with Bogdan Kozyrskiy, Artem Grachev and AbrahamI.CameloGuerrero. It is a preprint; publication/peer-review status was not inferred.

The review correctly identifies a relevant omitted in-text citation. Their four datasets are BCICompetitionIV2a, AlexMI, OpenBMI/Lee2019 and Schirrmeister2017; the last is executed movement, the other three motor imagery. Their benchmark compares CSP/FBCSP and covariance/tangent pipelines under frozen, expanding-history, rolling-history and cold-start regimes. Each incoming trial is scored before its label enters subsequent complete-pipeline refitting. The feature extractor and classifier are both updated. This checked article does not include our fixed-CSP/LDA-only versus fullCSP/LDA matched-current-support component contrast.

The novelty claim should be this precise protocol/component distinction, not an unsupported claim that no previous paper has ever matched labels or conducted component ablations. Their text itself discusses an equal-training-size window comparison, so merely matching sample counts is not unique. Our distinction is identical source/support trial identities and an explicitly different component-update action, plus a fixed whole-run query that never enters a later fit in that execution.

The review's “three months earlier” line is incorrect:5October is22days before27October and18days before23October. Dates alone do not establish originality. The existing bib metadata is accurate; optionally add official arXiv DOI and update the access date to27October following this full-text check.

## Suggested introduction paragraph

Kozyrskiy et al. benchmarked CSP- and covariance-based pipelines under time-ordered, label-revealed prequential evaluation across four EEG datasets [@kozyrskiy2026updates]. Their expanding- and rolling-history schemes refitted complete pipelines after each newly revealed trial, addressing update timing, memory and cold-start calibration. Here, each target session receives one fixed source-plus-current-support fit before the later whole runs are scored. The full-refit and classifier-only arms use identical source and current-session trial identities and identical query trials. Their difference quantifies the added spatial-representation update after the classifier has already received the same calibration labels.

## Probability-score wording

A decrease in cross entropy or Brier score does not by itself demonstrate improved calibration: proper scores reflect discrimination/refinement and calibration together. No reliability-curve/ECE or explicit calibration component was estimated in the saved analysis. Use “probability scoring” instead of “calibration.” The synthetic P-versus-point ablation improved CE/Brier with almost unchanged BA, while the actual EEG P-versus-point Brier and BA were worse. Keep both settings explicit and avoid a universal recommendation to suppress posterior uncertainty.

Suggested heading: **Posterior covariance changed probability scores and classification differently.**

## Exact source records

See literature_sources.json forURLs, full downloaded-byteSHA256 and sizes, and literature_verification.json for page locations and decisions. Full copyrighted source files remain outside the repository; facts and metadata may be incorporated into the revision audit. No repository files or experiments were modified.
