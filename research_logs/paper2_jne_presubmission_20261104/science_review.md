# Scientific pre-submission review

Reviewed commit: `ff9f6c47eea2745174a233bd4310b43d59cb6f5c`. Read-only review; no EEG or weights loaded, no new model fit, prediction or scientific run.

No new result or statistical error requiring an experiment was found. The saved tables support the reported EA/weak-class gains, participant distributions, corrected/introduced errors, matched controls and paired phase effect. Historical/current intervals, participant-level units and separate multiplicity families remain distinct. Established EA is attributed; the manuscript does not claim a new transform, isolated imagery-duration mechanism or clinical efficacy.

## Minor clarifications

1. **MAIN.md:51 — count after exclusions.** Clarify that 3,930 is the included target-query count after 30 partial exclusions, from 3,960 scheduled identities. Evidence: frozen split-manifest role/inclusion flags; original QC REPORT.md:14–17,25–31; frozen query protocol:41–50; window-timing review:16 establishes recording-boundary truncation. Suggested sentence: “The target-query endpoint retained 3,930 complete windows after excluding the 30 recording-boundary partial events from 3,960 scheduled target-query identities.” No count or exclusion changes.
2. **MAIN.md:65 / SUPPLEMENT.md:229 — LDA priors.** The text specifies shrinkage but omits that LDA class priors follow empirical fitting-set frequencies. NumPy `_fit_lda` explicitly uses counts at classical.py:104–114; Kumar LDA constructors leave sklearn priors at their empirical default. Suggested sentence: “All CSP/LDA arms estimated LDA class priors from the class frequencies in their own fitting set: source training alone for frozen decoding, and the source/support union for updating arms.” This sentence does not apply to the separate geometric candidates’ equal priors. No refitting is needed.

## Existing final-submission item

SUBMISSION_STATUS.json:11–16 correctly records three-author reading and AI-disclosure accuracy, while leaving individual all-four ICMJE criteria and final JNE-file approval unconfirmed. The latest actual code-validation/training-supervision and design/code contributions are included. Complete the final journal declarations from actual author facts; do not invent signatures or writing roles. This is an existing author-declaration item, not a newly discovered scientific defect.

AI disclosure, national-law exemption wording, original Kumar ethics/consent scope and the absence of a fabricated BNCI committee statement are consistent with the supplied record. Detailed evidence paths and fixed-source hashes are in science_review.json.
