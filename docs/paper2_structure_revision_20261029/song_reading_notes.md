# Song and Yoon: reading scope and structural lessons

Checked 29 October 2026. No manuscript, scientific result, model or dataset was modified for this literature check.

## Requested journal article

Song X, Yoon SC. Improving brain-computer interface classification using adaptive common spatial patterns. *Comput Biol Med*. 2015;61:150–160. DOI [10.1016/j.compbiomed.2015.03.023](https://doi.org/10.1016/j.compbiomed.2015.03.023), [PMID25909828](https://pubmed.ncbi.nlm.nih.gov/25909828/).

**Reading level:** complete PubMed abstract and metadata; publisher-indexed introduction/method/result previews. Direct publisher requests returned403. OpenAlex and Semantic Scholar mark the paper closed and supply no open repository PDF. The complete journal article was not obtained; no full-text reading is claimed.

The inspected material places EEG nonstationarity before the spatial-filter update. Its adaptive CSP uses target covariance information, updates the two classes together and avoids first assigning the target trial a predicted class. Its comparison and classified-trial-recycling question connect the adaptation operation to a specific source of error. These are literature findings, not components newly invented or implemented in this project.

## Distinct same-author full text

The official [SPMB2015 proceedings PDF](https://isip.piconepress.com/conferences/ieee_spmb/2015/papers/l03_03.pdf), *Incremental Versus Non-incremental Learning in Adaptive Common Spatial Patterns*, was read completely: four pages, DOI10.1109/SPMB.2015.7405468. It cites the requested journal article as reference10; the two publications must not be merged.

Its organization proceeds from the adaptation problem to baseline CSP, the adaptive operation, controlled incremental/non-incremental variants, evaluation design, aggregate comparisons and later-block behavior. A difference in one update step gives the comparison a clear explanatory duty. The later-block display connects the aggregate outcome to the process being tested. Full copyrighted PDF/text remains outside Git; its byte identity is in song_sources.json.

## Application to the current manuscript

These are general editorial recommendations, not a reconstruction of the inaccessible journal article's full section hierarchy:

1. State the component question before mathematical or implementation details: with the same current labels, which decoder operation contributes the gain?
2. Define Frozen, LDA-only, Full and EA as explicit information/update actions. A reader should understand their shared inputs before seeing a table.
3. Give each comparison one role: total recalibration effect, spatial component beyond classifier recalibration, or additional support-only alignment.
4. Follow the cohort estimate with corrected/new errors, participant effects and chronological profiles. Use the project's own saved predictions and existing figures exclusively.
5. Put mathematical assumptions and engineering provenance in their relevant methods/supplement locations; end the discussion with the practical use of the observed component differences.

## Independent contribution and attribution

The project's evidence is its matched-label spatial-component contrast and prediction/longitudinal attribution, supplemented by its own fixed-budget external alignment comparison. It did not implement Song–Yoon target-trial ACSP or establish a new version of their algorithm. Its supervised support-only setting differs from adapting with an unlabeled incoming target trial. The current manuscript already cites Song2015 as relevant adaptive-CSP prior work; retain that attribution if its technical role is discussed. Generic article organization can be learned without copying sentences, figure designs, equations, foreign result values or distinctive uncited claims. No exhaustive search establishes a first-ever priority claim here.
