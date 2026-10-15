# Verified reference map

Bibliography: `kumar_references_20261015.bib`. Evidence, exact retrieved bytes,
access outcomes and SHA256 values:
`research_logs/kumar_manuscript_references_20261015/run01/`.

| Citation key | Appropriate use in this manuscript | Verification and boundary |
|---|---|---|
| `kumar2024` | Original acquisition study and longitudinal BCI context; *Transfer learning promotes acquisition of individual BCI skills*, PNAS Nexus 3(2), pgae076. | DOI/title/authors/journal/year verified against publisher-deposited Crossref metadata and Europe PMC. Published abstract inspected; original full text not read here. Its online skill-acquisition claim is not a conclusion of our offline analysis. Cite with the correction below. |
| `kumar2024correction` | Acknowledge the published correction to the original Kumar article. | Crossref metadata, Europe PMC index, and the complete public correction XML (PMC10989871) verified. The correction names original DOI `10.1093/pnasnexus/pgae076`. No author was supplied for the correction in Crossref; none is invented in the bibliography. |
| `nemar177` | The exact NEMAR BIDS derivative actually used, nm000177 version 1.0.5, CC BY 4.0. | Version DOI `10.82901/nemar.nm000177.v1.0.5` exists in DataCite, identifies version 1.0.5, and links to the collection DOI and original study. DataCite repository publication year is **2026**; the original paper and dataset-description `PublicationYear` are **2024**. The fresh official dataset-description bytes exactly match the existing local file. Do not conflate derivative publication year, original study year, or README trial totals with the audited analysis sample. |
| `ramoser2000` | Foundational common spatial patterns / spatial filtering for imagined hand movements. | Bibliographic metadata verified by exact DOI and title. Does not establish validity of a new adaptive gate in this study. |
| `blankertz2008` | CSP/spatial-filtering methodological background and robust single-trial EEG analysis. | Bibliographic metadata verified by exact DOI and title. Our frozen four-component implementation and parameters are established by repository evidence, not inferred from the citation. |
| `ledoit2004` | Ledoit–Wolf covariance shrinkage used in the fixed CSP covariance estimator. | Exact original estimator paper, DOI/title/authors/volume/pages verified. The citation does not authorize changing the estimator or regularization. |
| `lawhern2018` | EEGNet architecture lineage and compact convolutional EEG decoding. | Exact original EEGNet paper, authors, volume 15(5), article 056013 and DOI verified. The current model sizes, stopping, seeds and software behavior come from frozen configuration/audits. |
| `schirrmeister2017` | Convolutional EEG decoding and Braindecode software lineage/context. | Exact paper and author list verified. This is not the original EEGNet architecture paper; cite Lawhern for EEGNet and execution records for the installed implementation/version. |
| `lotte2018` | Review context: EEG classification, adaptation, transfer learning and small-sample methods. | Exact review metadata and publisher-deposited abstract inspected. Use for broad methodological motivation, not as direct proof that nonstationarity caused a particular participant's result or as a current universal ranking of deep models. |
| `jayaram2018` | Optional: MOABB benchmarking framework / derivative conversion lineage, if discussed. | Correct DOI is `10.1088/1741-2552/aadea0`, J. Neural Engineering 15(6), **066011**. This analysis used its own frozen adapter, so do not claim the real evaluation was run through MOABB. |

## Resolved correction

The publicly accessible correction, DOI `10.1093/pnasnexus/pgae137`, changes the
original paper's paragraph headed “GR transfer learning with common spatial
patterns.” It removes duplicated comparison values: CSP-Expert-Subject remains
0.3727 ± 0.2924; CSP-Subject-Specific-Fix is corrected to 0.2120 ± 0.2815 and
CSP-Subject-Specific-Adapt to 0.2515 ± 0.3082, each with N = 144. The reported
P values remain. These are source-paper reported scores, not this repository's
outcomes. The correction does not indicate a change to the frozen inputs,
accepted checkpoints or evaluation identities used here. The manuscript should
cite the correction and avoid importing these original-paper values into its
own results.

## Provenance and remaining limits

- Original data provenance was independently resolved through the official
  Zenodo record 10694880: DOI `10.5281/zenodo.10694880`, publication date
  2024-02-22. No original signal archive was downloaded during this work.
- The registered OUP article page returned HTTP 403. This was retained as an
  access failure; no bypass was attempted. The correction's independently
  indexed open-access Europe PMC XML was read through its normal public API.
- The candidate DOI `10.3389/fninf.2018.00008` was rejected: it resolves to an
  unrelated hippocampal-neuron paper, not MOABB. Its failed bibliographic match
  is retained in evidence and excluded from the bibliography.
- Crossref/DataCite metadata verification is not a claim of full-text review.
  This pass read the correction full text, selected deposited abstracts and
  official dataset metadata. It did not verify an original-study informed-consent
  sentence or independently assess clinical efficacy or human skill retention.
- The official dataset metadata records the UT Austin ethics protocol
  2020-03-0073. Cite that as original-dataset metadata; this is not a new ethics
  approval for the present secondary analysis.
- All ten bibliography entries contain verified fields only. Final author
  review of claim placement and journal formatting remains appropriate.
