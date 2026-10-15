# Kumar2024 manuscript review package

Current title: **Longitudinal Motor-Imagery EEG Decoding: Frozen Baselines,
Supervised Recalibration, and Task-Measurement Reliability**.

| File | Use |
| --- | --- |
| [manuscript.pdf](manuscript.pdf) | Complete 12-page English author-review copy, resolved numbered references and three figures |
| [manuscript.docx](manuscript.docx) | Editable Word version of the same main text and figures |
| [supplement.pdf](supplement.pdf) / [supplement.docx](supplement.docx) | Seven-page detailed methods and evidence supplement |
| [author_checklist.pdf](author_checklist.pdf) / [author_checklist.docx](author_checklist.docx) | Two-page author-specific completion and review checklist |
| [Figure originals](../figures/kumar2024_20261015/CAPTIONS.md) | Full-size PNG, SVG and PDF exports with source-backed captions |
| [BibTeX](../kumar_references_20261015.bib) / [reference map](../reference_map.md) | Ten verified core references, access scope and source correction |

The source manuscript, supplement and checklist remain one level above this
folder. Main Results and the three original tables are unchanged. All negative,
collapsed and participant-worsening outcomes are retained. Same-query scores
are explicitly distinguished from unequal source-validation/target-label and
compute budgets. The existing primary CPU contrast is unchanged; this package
introduces no fit, query inference, threshold selection or hypothesis test.

The author byline and correspondence were retrieved at the user's request
from first-paper commit `d9a11926076bd348696f6e690078955921dac3f8`:
Ziyuan Zhu, College of Artificial Intelligence Medicine, Chongqing Medical
University, Chongqing, China; `zzy2630816871@gmail.com`.
The supplied ORCID remains subject to the profile check recorded in that source.
Funding, conflicts, contributions, institutional secondary-use determination
and approval to submit this second paper remain author-specific pending items.

PLOS ONE / Research Article was carried forward as a **working format** from
those materials. Numbered references use the unchanged Citation Style Language
PLOS parent style. Its source and license are retained in `plos.csl` and the
PLOS ONE dependent style in `plos-one.csl` (CC BY-SA 3.0, as stated in the files).
That style license does not license the project's scientific code. This PDF is
a compact review layout, not a claim of compliance with every current journal
submission rule. Final journal declarations, formatting checks and author
approval are listed in the checklist. No submission was made.

## Reproducibility and checks

`research_logs/kumar_manuscript_completion_20261015/run01/` contains exact Pandoc
commands, UTC build times, input/output SHA256, the source-date epoch, source
preservation checks, rendered-page checks and scientific reporting review.
Pandoc 3.1.11.1, the existing XeLaTeX and installed DejaVu/Noto fonts rendered
these documents; no environment or resource was purchased or installed.
The scripts use only saved text, figures and document tools. To reproduce the
rendering, use the command arrays in `build_commands.json` with fresh output
paths or an archival copy of the rendered-output directory. Existing exported
files are protected against silent overwriting by the builder.

All 21 PDF pages were rendered for contact-sheet review; representative dense
tables, reference and hash pages were inspected at higher resolution. Bounding
boxes show no text outside physical pages. The DOCX XML, numerical text and
three embedded main figures were checked; native Word layout was not rendered.
Final exports have no missing-character warnings. Preliminary typesetting and
metadata-parser errors, their logs and the superseded export hashes are
preserved separately; they were editorial checks, not scientific reruns.
