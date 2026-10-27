# BMT manuscript revision — recovery handoff, 27 October 2026

**Recovery update:** The execution workspace returned, its local files were retained, and document building resumed. The completed delivery is indexed at [the BMT review folder](../manuscript/discovery_revision_20261027/README.md). The outage record below is historical; it does not describe the later completed commit.

This records actual completed analysis and local document generation before the Codex execution workspace became unavailable. **It is not a claim that the new manuscript/PDF/Word files have been pushed.** GitHub result data remain safe at the fixed commit below. The current research branch is `research/paper2-hpc-v2-20261023`; preserve existing uncommitted files. Do not reset, initialize, retrain, forward any model, read raw EEG, or operate the school Slurm/Pod.

## User's current objective

Prepare the second paper for **Biomedical Engineering / Biomedizinische Technik**, using the completed V3 discoveries. Focus the paper on the same-label-budget component result: approximately20 current-session labels allow spatial-filter refitting to add value beyond classifier recalibration. Use direct, natural scientific prose and remove repetitive defensive qualifiers, while preserving material sample/budget/endpoint facts and required AI disclosure.

New review title:
**Spatial-filter refitting improves limited-label EEG decoding beyond classifier recalibration**

Original primary full-CSP/LDA-minus-frozen contrast: **+7.42pp [2.49,12.48]** in12participants.
Original same-label full-minus-LDA-only secondary contrast: **+5.47pp [2.17,8.91]**,73.7% of the mean total gain. It remains the original secondary endpoint even though it is the central narrative. Full and LDA-only use the identical40source and19/20current-support labels. Original manuscript/data versions must remain preserved.

## Verified V3 results

Source result commit: `500831c086d9e1d1e8412cf8ebca5fb6a288db76`.
Packet: `83cbdfdcfa541b3ab3addfc3`, under `training_status/paper2-discovery-v3/result_exports/`.
Three-part archive:40,194,093bytes, SHA256 `e509c2591efa21fff4dd47236e613ed6b611ca10ad20bac3da37e66e34a9d170`.
All49,984payloads matched member lengths/SHA;126unique completion markers verified.
All10,392saved prediction NPZ files independently reproduced BA/accuracy/recalls/collapse, maximum BA error0; ordered query IDs/labels/run IDs agree across methods/budgets/seeds. These are42source and10,350target files,1,425unique query trials, not independent participant repetitions.
900participant endpoints,150cohort endpoints and165original comparisons/intervals reconstructed; maximum contrast/CI difference1.78e-15pp. Participants, not seeds/sessions, are independent units. TargetV3cohort remains the six already exposed development participants.

V3 useful positive mechanism: at20-label cap, fixed-BN full updates exceed adaptive-BN full updates by1.50pp[0.33,2.74] with individual sources and1.91pp[0.76,3.24] with pooled sources. BA57.51/56.01 and56.22/54.31%; collapse8/90vs16/90 and0/90vs18/90. Each90is nested6people×3seeds×5sessions. This is BN-mode sensitivity, involving optimization-time batch normalization and resulting buffers/weight trajectories, not a pure buffers-only intervention. Individual-source contrasts at4/8/12/16labels are−0.18/−0.34/−0.46/−0.04pp. batch16 gives one minibatch for≤16labels and two for19/20, so show all budgets.

V3 new algorithm primary results were negative: geometric predictive candidate64.68%, tangent refit67.01%, saved EA70.37%; differences−2.33pp[−4.41,−0.24] and−5.69pp[−9.30,−2.22]. CoreKLconstraint-minus-fullFixed essentially zero. Keep all outcomes.
Synthetic384×50×9=172,800saved results: candidate70.36%BA versus refit76.19%,376/384scenario means worse. Posterior-predictive vs identical posterior-mean point classifier improves mean CE0.34094 and Brier0.00191, not BA (about−0.04pp). No real-data algorithm-superiority claim follows.
Three school slotjobs775309/775310/775311 actually ran sequentially, not simultaneously.

## Official journal sources read

- Journal: https://www.degruyterbrill.com/journal/key/bmte/html
- Instructions: https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Instructions%20for%20Authors.pdf
- Research template: https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Template%20for%20Research%20Articles.docx
- Ethical/legal template: https://www.degruyterbrill.com/publication/journal_key/BMTE/downloadAsset/BMTE_Template%20for%20Ethical%20and%20Legal%20Declarations.docx
- AI policy: https://www.degruyterbrill.com/publishing/for-authors/author-policies/artificial-intelligence
- Data policy: https://www.degruyterbrill.com/publishing/for-authors/author-policies/data-sharing-policy

Research Article:6000words; abstract≤200, structured Objectives/Methods/Results/Conclusions;3–6alphabetical lowercase keywords; running head≤75characters; figures+tables≤8; references≤35Vancouver sequential bracketed citations; editable Word tables/equations; separate figure PNG/TIFF etc;600dpi combination figures,min6pt at intended size; supplementary files≤10MB each. Single-blind review. Mandatory separate ethical/legal declarations and cover letter; at least5real reviewer suggestions. Institutional email is recommended, not mandatory. Current volume S2O/no-author-charge is time-bound, not a future guarantee.

AI policy asofSeptember2026 requires substantive research/code/text assistance disclosure and says AI-generated papers are not accepted. Do not reclassify this project's substantial assistance as mere proofreading or conceal it. This remains an author-review draft requiring substantive human review, revision and responsibility. Graphs are deterministic plots of recorded numbers; no generative-image synthesis or experimental-data alteration occurred.

Ethics: retain the author-provided Article32(1) secondary-public-data exemption basis; do not restore a school/ethics-office confirmation claim. UT Austin2020-03-0073 and original written consent refer to original collection.
Do not claim new author approval or exclusive submission: original16Octoberapproval covered older content; current status of prior PLOS ONE manuscript PONE-D-26-52050 is not known.

## Local work that existed before workspace outage

Repository: `/workspace/few-shot-mi-eeg`.

New draft folder:
`manuscript/discovery_revision_20261027/`
- MAIN.md, SUPPLEMENT.md, references.bib.
- BMT_Manuscript_Review.docx/pdf; BMT_Manuscript_Submission.docx.
- Supplementary_Methods.docx/pdf.
- ETHICAL_AND_LEGAL_DECLARATIONS_DRAFT.md/docx.
- COVER_LETTER_DRAFT.md/docx; README.md.
- Four600dpiPNG/SVG/vectorPDF figures with all underlyingCSV and manifests.
- Third_Party/bmt_vancouver.csl, CC BY-SA3.0 attribution retained.
- JOURNAL_FORMAT_CHECKS.json, DOCUMENT_BUILD.json.

Last successful build checks: abstract181words; conservative whole-manuscript count4813words including title/abstract/tables/legends/references;5keywords; running head49characters;4figures+3tables;22cited references. ReadingPDF16pages, supplement11pages; no empty pages. Main Word has3editable tables/4embedded figures; submission Word has3tables/0embedded figures with end legends. Four figures at170mm width have minimum text7.49/6.74/6.63/7.71pt.
Last observed sources/documents were locally written, **not committed**.

Saved-result code (all newly created locally):
- scripts/audit_paper2_v3_saved_predictions_20261027.py
- scripts/summarize_paper2_v3_discovery_20261027.py
- scripts/analyze_paper2_v3_geometry_20261027.py
- scripts/analyze_paper2_v3_neural_mechanisms_20261027.py
- scripts/analyze_paper2_v3_simulations_20261027.py
- scripts/render_paper2_v3_discovery_figures_20261027.py
- scripts/build_paper2_discovery_revision_20261027.py

Analysis outputs: `research_logs/paper2_v3_analysis_20261027/` with REPORT.md, REPRODUCE.md, audit/, tables/, geometry/, neural/, simulation/. Two focused testfiles gave18passed; Ruffpassed. Full scientific experiments were not rerun.
Official-source reading record: `docs/bmt_journal_requirements_20261027.md`.
README.md, CURRENT_PROJECT_STATUS.md, CROSS_SESSION_RESULTS.md, manuscript/README.md have local navigation updates.

Input extraction:
`/workspace/paper2_hpc_v3_delivery/received_83cbdfdcfa541b3ab3addfc3/paper2_results/results`.
Independent notes and checks:
`/workspace/paper2_hpc_v3_delivery/analysis_notes/`.
Policy downloads:
`/workspace/bmt_policy_20261027/`.
Official-source metadata hashes are in sources.json there; do not redistribute complete publisher guideline/template files under project MIT/CC BY licensing.

## Precise remaining work after environment recovery

1. Check branch, git status and latest remote without resetting. Preserve older unrelated untracked component-paper files. This handoff was created through the GitHub connector after the execution workspace went offline; fetch/reconcile that commit safely.
2. The final source edit fixed supplementary table readable labels (canonical IDs remain inCSV), restored malformed `reuse_v2` spacing, explicitly documented simulation CE floor1e-15, and sharpened “posterior expected squared error.” Main acknowledgment now says AI-assisted *plotting code* precisely.
3. Figure rerender after formatting/caption changes succeeded. A subsequent final document build was dispatched but its tool return is unavailable; do not assume that last build completed. Rebuild only documents as needed; inspect supplement page5 and long all-budget tables for wrapping. Earlier readingPDF/Word builds had passed before these final source-only edits.
4. Remove only obsolete files created in this new folder during failed early build, if still present (Review_Manuscript.docx/pdf); do not touch historical submissions.
5. Verify mandatory declaration consistency, produce the publisher-order editable declaration table if desired, run relevant18tests/Ruff (do not restart broader research), record final QA/hashes, and create a compact review package if useful. No raw EEG/checkpoint upload.
6. Stage only new analysis/manuscript/scripts/tests and the four deliberate navigation updates. Commit and push to the current research branch; return actual commit and working PDF/Word links. Do not claim this handoff is a full manuscript delivery.
7. Author still needs to personally review/approve new version and AI-use scope, confirm prior PLOS status, and provide≥5appropriate reviewer suggestions. No actual journal submission is authorized or performed.
