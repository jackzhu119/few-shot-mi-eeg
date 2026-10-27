# External cohort selection for the spatial-update component question

Date: 27 October 2026. This is a source and acquisition review, before reading
new replication outcomes. No EEG was downloaded or scientific model fitted for
this review. A separate protocol and execution record distinguish those actions.

## Choice

Use **BNCI2014-001 / BCI Competition IV 2a**, restricted to left/right hand
imagery, for the first executable external-data replication. Its 22 EEG channels
support the four-component CSP comparison already used in this project; its
recorded run boundaries permit a whole-run support/query separation. The source
files contain nine people recorded on two different days. This addresses
cross-dataset reproducibility of the update-component contrast, rather than
adding architectures to the already observed Kumar2024 cohort.

The first-paper project previously analyzed BNCI2014-001 in Q15/Q16. Accordingly,
this is an **independent dataset replication of the current fixed contrast**, not
a claim that these participants' outcomes have never been seen by the project
or a new externally preregistered study. The present protocol should be fixed
before evaluating this particular comparison, and the historical exposure should
remain recorded once in Methods/Scope. Do not pool the nine people with the 12
Kumar primary participants as one homogeneous primary cohort.

## Primary-source verification

The following sources were actually read or queried on this date:

| Source | Reading / check performed | Finding used here |
|---|---|---|
| [Official BNCI dataset directory](https://bnci-horizon-2020.eu/database/data-sets) | Dataset 001-2014 and 004-2014 sections and linked data/license records read | 001-2014 has nine people, 22 EEG plus three EOG channels; official A01T–A09E MAT links; CC BY-ND 4.0. |
| [Original six-page dataset-A protocol](https://bnci-horizon-2020.eu/database/data-sets/001-2014/description.pdf) | Experimental paradigm, recording, file/events and evaluation sections read | Two different-day sessions; six runs/session; 48 four-class trials/run, 12 per class; cue at trial second 2, imagery requested until second 6; EOG excluded from classification. |
| [NEMAR frozen v1.0.3 manifest](https://data.nemar.org/nm000139/v1.0.3/manifest.json) | Reused versioned manifest already archived in the repository | Eighteen original MAT files have exact byte lengths and SHA256 values; converted signals and metadata are separate objects. |
| [NEMAR original-file provenance](https://data.nemar.org/nm000139/v1.0.3/sourcedata/sourcedata_provenance.json) | Actual HTTPS GET 200, complete JSON read | Eighteen upstream filenames restored, nine recorded subjects, total 779,873,919 bytes; upstream acquisition used MOABB 1.5.0 on 11 August 2026. |
| Official eighteen MAT URLs | Actual HTTPS HEAD, all 18 returned 200 after redirects | Every Content-Length matches the frozen manifest. The redirect destination is `https://lampx.tugraz.at/~bci/database/001-2014/<filename>`. HEAD checks length/access, not full content SHA. |
| Installed MOABB source `moabb/datasets/bnci.py` | `_load_data_001_2014`, `_convert_mi`, `_convert_run`, `BNCI2014_001.__init__` read | MAT `trial` indices become triggers at `trial - 1`; class names follow `classes`; the dataset interval is `[2, 6]` seconds relative to that trigger. |

The original GDF event table defines trial-start 768, cue-left 769, cue-right 770,
feet 771, tongue 772, unknown-cue 783, expert-rejected trial 1023 and new-run
32766. In the released MAT adapter, `trial` is the one-based **trial-start** sample,
and `y` is the one-based class label: left hand 1 and right hand 2, verified against
`classes`. The separately converted NEMAR BIDS event integers may be recoded;
they must not be substituted for these MAT codes without checking the mapping.

At 250 Hz, the intended complete imagery epoch is therefore
`X[trial - 1 + 500 : trial - 1 + 1500, :22]`, transposed to channels × time:
1,000 samples covering trial time `[2, 6)`, equivalently cue time `[0, 4)`.
Do not interpret MAT `trial` as cue onset and then take trial time `[0, 4)`.
The final adapter must inspect the actual `fs`, `classes`, per-run `trial`, `y`
and `artifacts` fields; this document does not assert raw-field inspection from a
HEAD request. Expert artifact flags remain per-trial metadata and are not class
labels or automatic reasons to alter the frozen support prefix. The original
competition's artifact-free scoring rule and this new replication's all-trial
scoring rule are distinct; this fixed protocol retains every original flag.

In original GDF files, runs are separated by missing-value blocks. The MAT
distribution exposes separate recording structures, including baseline/EOG
structures without task trials. An adapter must count the six **task** runs,
retain their chronological array order and original structure identities, skip
empty-trial baseline structures, and filter within each retained recording rather
than through missing-value separators. A source/target role cannot be inferred
from an arbitrary sorted BIDS event value or an empty-run-adjusted integer alone.

## Concrete acquisition scope

Only original MATs are required, not the NEMAR converted BDF files or a full
dataset archive:

`https://bnci-horizon-2020.eu/database/data-sets/001-2014/A{subject:02d}{T_or_E}.mat`

for subjects 1–9 and session letters T then E. Direct verified redirect URLs use
the same basename under `https://lampx.tugraz.at/~bci/database/001-2014/`.
The frozen NEMAR file entries offer a versioned content-addressed fallback. Their
bytes must match the same SHA256 rather than creating a new dataset version.

The eighteen-file total is **779,873,919 bytes**. The smallest complete
representative person is A01T/A01E, 42,806,453 + 43,772,146 = 86,578,599 bytes.
Inspect one complete person's structure and sample boundaries before acquiring
all people. Full downloads should stream to a same-directory temporary file,
hash while downloading, and publish only after length and SHA256 match; cached
verified originals should be reused on restart. Neither the original upstream
HTTP ETag nor Last-Modified is a substitute for SHA256.

The SHA256 expectations come from the **versioned NEMAR complete-byte manifest
and upstream-file provenance**. The BNCI webpage itself does not publish eighteen
cryptographic hashes; do not attribute the hash list to a nonexistent upstream
checksum file. Full acquisition will establish whether the currently served
upstream bytes still match that frozen mirror.

## Fixed-information split suitable for the proposed replication

Use session T as source and E as target. Number task runs chronologically from
one, independently of empty baseline structures:

| Role | Trials before any documented data exclusions |
|---|---|
| Source fit | Source runs 1–4: 96 left/right trials, 48 per class |
| Reserved source validation | Source run 5: 24 trials; unused for this fixed four-arm classical comparison |
| Source-only query | Source run 6: 24 trials, disjoint from source fit |
| Current-session support | First 20 left/right trials in target run 1, in acquisition order |
| Unused target-run-1 remainder | Last four left/right trials; never moved into query or used to balance support |
| Target query | Whole target runs 2–6: 120 left/right trials |

The updating methods receive identical source and support identities. Frozen
CSP/LDA deliberately receives zero target labels; the equal-label component
contrast is **full CSP/LDA minus LDA-only**, not a claim that frozen receives
the same target information. EA must estimate the target whitening reference
from current support only, never from future query signals. No source-validation
or target-query tuning is needed for the four fixed methods. Any smaller-budget
analysis, if included in the separate frozen protocol, must use chronological
prefixes of the same support run and the same complete query set.

This source-label budget is 96, rather than Kumar's 40; the task window is a
four-second documented MI interval rather than Kumar's five-second export.
Within-dataset paired contrasts remain matched. Cross-dataset absolute accuracy
should retain these acquisition and source-budget differences.

## Why the other two immediate candidates are not the minimal first experiment

**BNCI2014-004 / IV 2b** has nine people and five sessions, an attractive
longitudinal complement. However, the [original dataset-B protocol](https://www.bbci.de/competition/iv/desc_2b.pdf)
actually specifies only three bipolar EEG channels (plus three EOG), screening
sessions 1–2 without feedback and sessions 3–5 with feedback. Screening runs
contain 20 trials; feedback runs contain 40. The original four-component CSP
configuration cannot be copied unchanged into three channels. Different feedback
and amplifier dynamic ranges also affect the longitudinal comparison. The
archived NEMAR v1.0.3 converted BDF view contains only one participant, while its
18 original B01–B09 T/E MATs cover all nine: 477,981,271 bytes. It is a useful
separately specified follow-up, rather than an unnoticed adapter substitution.
The current MOABB documentation repeats a two-screening-session description
alongside a five-session summary; the original protocol takes precedence for
feedback/session timing.

**Lee2019 / OpenBMI** supplies 54 people on two days and richer EEG. Its original
publication is [GigaScience 2019, giz002](https://doi.org/10.1093/gigascience/giz002);
the [GigaDB data record](https://doi.org/10.5524/100542) declares CC0 1.0. The
OpenBMI toolbox's GPL license is a separate code license. The repository's
previous full-text and adapter audit found the labeled offline block contains
100 trials/session and the online test block lacks the labels needed for the
usual adapter. Twenty early support trials versus 80 later query trials would
be a **chronological block split**, not whole-run isolation. The 108 original MI
MATs in NEMAR nm000338 v1.0.5 total 64,847,432,285 bytes and include continuous
signals outside the minimal labeled epochs. This cohort needs a separate bounded
acquisition and block protocol; it should not silently replace the run-isolated
replication. The original data-recording ethics and current secondary-analysis
legal basis must be documented for that dataset when it is actually added.

## License and ethics handling

Keep the BNCI originals under **CC BY-ND 4.0**, with attribution to Graz University
of Technology and the original dataset authors. Do not redistribute cropped,
filtered or otherwise transformed EEG under the project's MIT/CC BY licenses.
Original-file hashes, sample identities, derived statistical summaries, software
and reproducibility instructions can be distributed with their appropriate
scope and source attribution. This review does not confer new redistribution
rights beyond the dataset license.

The checked competition description establishes no new institution-specific
approval or waiver for this project. The paper's current Chinese national-law
secondary-analysis basis remains distinct from original data-collection ethics.
Before final manuscript inclusion, cite actual original-study ethics evidence
where available; never fill an unverified approval number or reintroduce the
removed school-confirmation claim. These source checks involved no recruitment,
contact, intervention, identification or private participant records.

## Inspectable evidence paths

Existing committed records reused:

- `research_logs/public_data_expansion_20261010/longitudinal_receipts/nm000139_manifest.json`
- `research_logs/public_data_expansion_20261010/longitudinal_receipts/nm000135_manifest.json`
- `research_logs/public_data_expansion_20261010/longitudinal_receipts/nm000338_manifest.json`
- `docs/code_reuse_audit.md` (first-paper prior-exposure record)
- `docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md` (earlier proposal)

Fresh complete read-only acquisition observations, prepared for inclusion in the
execution evidence package:

- `/workspace/paper2_external_official_heads_20261027.json` — all 18 official HEADs,
  status, resolved URL, length comparison and frozen expected hash.
- `/workspace/paper2_external_sourcedata_provenance_20261027.json` — actual complete
  NEMAR provenance GET. Its `sourcedata/` path is required; a root-level request
  returned 404 and was corrected rather than treated as missing provenance.

HEAD observations establish current accessibility and length only. Raw download,
actual MAT-field validation, numerical execution and prediction reconstruction
must be reported from their own subsequent records.
