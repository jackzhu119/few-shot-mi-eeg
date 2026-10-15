# Focused related-work and source-reading audit

Source checkout: `370bc94b7af3c926adeb02c38e430a53e4a64135`.
Prepared on 2026-10-15 UTC for the existing submission revision. This pass read
literature and metadata only. It did not download EEG, run inference, fit models,
change scientific configuration, operate the Pod, or alter existing references.

New bibliography: `manuscript/kumar_submission_additional_references_20261015.bib`.
Five primary references were selected for a specific interpretive purpose,
rather than a claim to exhaustively review the literature or to implement these
methods. This is a targeted relevance review, not a systematic review.

## What was actually read

| Reference | Verified bibliographic identity | Actual reading scope | Appropriate use and limit |
|---|---|---|---|
| He and Wu, `he2020alignment` | IEEE TBME **67(2):399–410, 2020**, DOI `10.1109/TBME.2019.2913914`; online publication 2019 | PubMed indexed bibliographic record/abstract; author preprint **arXiv:1808.05464v2**, HTML abstract, introduction and sections II–III, including the alignment formula and reference-matrix distinction | Euclidean alignment transforms signals using an unlabeled covariance reference. Cite as a distinct untested alternative, not an evaluated baseline. Full journal text and appendices were not independently compared with the preprint. |
| Zanini et al., `zanini2018alignment` | IEEE TBME **65(5):1107–1116, 2018**, DOI `10.1109/TBME.2017.2742541` | Complete PubMed structured abstract and bibliographic record | Riemannian affine recentering across sessions/participants is existing work. Abstract-level reading supports that broad comparison; no full-text parameter, label-budget or performance claim is imported. |
| Vidaurre et al., `vidaurre2011coadaptive` | Neural Computation **23(3):791–816, 2011**, DOI `10.1162/NECO_a_00089` | Complete PubMed abstract and bibliographic record | Supervised initial coadaptation followed by unsupervised adaptation was studied online. This is historical adaptation context; our offline results cannot establish online user learning. |
| Lotte and Jeunet, `lotte2018skills` | J Neural Eng **15(4):046030, 2018**, DOI `10.1088/1741-2552/aac577` | Complete PubMed abstract and bibliographic record; institution/author-publication index checked | Decoder accuracy does not alone establish users' self-modulation skill. Their classDis/restDist/classStab are not silently equated to our existing source-score/half-support probes. The full author manuscript was not retrieved. |
| Hedge et al., `hedge2018reliability` | Behavior Research Methods **50(3):1166–1186, 2018**, DOI `10.3758/s13428-017-0935-1`; online publication 2017 | Publisher open-access HTML: abstract, reliability definitions, participants/design, data-analysis and initial task-reliability results; rights statement | Group effects and reliable individual differences are different properties. This is a general behavioral-measurement argument, not an EEG- or MI-specific empirical result. Supplements and every later discussion passage were not read. |

The reading scopes above deliberately distinguish abstract, selected full-text
sections and bibliographic metadata. No entry means that every paragraph,
supplement, implementation or underlying dataset was independently reviewed.
The exact tool reference IDs, requested URLs, selected fields and access
failures are in `source_reading_audit.json`. That file is an agent-authored
reading record, **not original HTTP-response bytes or an independently archived
copy of a paper**. No source-article body is republished here.

## Original Kumar article: new verified scope

The original official OUP article's **indexed full-text** Methods/Participants
and Fig. 1 passages were actually returned and read through the supported web
search tool. They report UT Austin protocol **2020-03-0073**, written informed
consent, and supervised use of first-run labels followed by a fixed decoder in
the remaining runs. Indexed original-paper passages also identify fixed and
adaptive CSP comparisons. These are source-study statements only; they do not
resolve the present secondary analysis's institutional determination.

The user-provided Europe PMC XML endpoint was inaccessible through the supported
tool, direct PMC HTML showed a browser challenge, and direct OUP opens failed.
Those failures were retained. Therefore the new scope is **relevant indexed
full-text passages read**, not a successful complete XML download. In
particular, later work must not retain the old blanket statement that only the
original abstract was read, or replace it with an unsupported whole-article
reading claim. The source-study correction remains separately cited.

## Suggested manuscript wording

Introduction contribution paragraph:

> Recalibration and first-run supervised updating are established approaches,
> including in the original acquisition study [@kumar2024;
> @kumar2024correction]. Our narrower question is what is gained by updating both
> the spatial filters and classifier rather than the classifier alone when
> both receive the same approximately 20 target-session labels. We also examine
> whether the available task measurements are sufficiently reliable to motivate
> a future updating decision. These are offline comparisons of cue-anchored
> task-label windows, not evidence that the entire window contains sustained
> motor imagery or that a task-aware updating policy has been validated.

Discussion, closest adaptation alternatives:

> Earlier coadaptive work combined supervised initialization with subsequent
> unsupervised adaptation [@vidaurre2011coadaptive]. Riemannian recentering and
> Euclidean signal alignment address session or participant differences using
> different covariance references [@zanini2018alignment; @he2020alignment]. We
> did not evaluate those methods; consequently, the present contrasts locate
> the benefit of full versus classifier-only supervised recalibration within
> the tested pipeline, rather than establish superiority over alignment-based
> adaptation.

Discussion, task-measurement boundary:

> Classification performance depends on the decoder and its training data, so
> it cannot by itself identify users' ability to self-modulate EEG
> [@lotte2018skills]. More generally, a cohort-average effect does not establish
> reliable individual differences [@hedge2018reliability]. The present
> half-support results describe agreement under the available sample budget;
> they neither demonstrate longitudinal test–retest reliability nor validate a
> rule for deciding when adaptation will help.

These paragraphs are proposals for integration by the manuscript owner. They
do not change primary/secondary endpoint status, authorize a new method or
claim the cited metrics/alignment methods were run. The timing audit's
cue-anchored-window qualification must also be carried into Methods/Limitations.

## Minimal future comparison, outside this revision's execution scope

If a later protocol is separately approved, a source-only fixed pipeline with
covariance alignment estimated solely from the existing 19/20 target support
trials would give an inductive, label-budget-compatible comparator. It would
require a new explicit fit/evaluation protocol and runtime/evidence budget.
Estimating alignment from all held-out query signals would instead be
transductive and is not automatically permissible under the present frozen
query protocol. Neither option was implemented or executed in this pass.
