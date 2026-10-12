# All-published-identity NETBCI exploratory addendum (11 October 2026)

We extended the saved longitudinal pipeline to all 19 published NETBCI identities, comprising
76 sessions, 456 runs and 14,431 source events.
The exact-5-second input policy retained 14,429 events; 2
short source events remain explicitly documented and were neither padded nor interpreted as behavioral failures.
The extension followed observed ten-identity results and a source-copy discovery; it is exploratory.

Before expanded model fitting, all 456 EDF signals and source task windows were
numerically audited, alongside official file hashes and original-header provenance.
The audit identified 30 continuous-signal groups and
909 task-window groups with exact copies. The cross-identity
continuous-or-task-window affected union was sub-1, sub-6, sub-7, sub-15, sub-17. Deposit fidelity does not
establish biological independence. Original BrainVision EEG has not been read to determine the correct
assignment or the cause of duplication. The exact pairwise session relationships below can share a
multi-member duplicate group and must not be summed as independent duplicate groups:

| Identity/session | Exact copied identity/session | Paired runs |
| --- | --- | --- |
| sub-1/ses-01 | sub-17/ses-01 | 6 |
| sub-1/ses-02 | sub-17/ses-02 | 6 |
| sub-1/ses-03 | sub-17/ses-03 | 6 |
| sub-1/ses-04 | sub-17/ses-04 | 6 |
| sub-1/ses-04 | sub-7/ses-01 | 6 |
| sub-1/ses-04 | sub-7/ses-02 | 6 |
| sub-1/ses-04 | sub-7/ses-03 | 6 |
| sub-15/ses-01 | sub-6/ses-01 | 6 |
| sub-17/ses-04 | sub-7/ses-01 | 6 |
| sub-17/ses-04 | sub-7/ses-02 | 6 |
| sub-17/ses-04 | sub-7/ses-03 | 6 |

All-identity estimates are retained as arithmetic diagnostics.

A separately preserved, source-driven post-observation sensitivity excludes every identity in any
cross-identity continuous or task-window exact-copy group, retaining 14 published identities.
Selection does not use effect direction, presume a correct copy, refit models or overwrite earlier outputs.
No detected exact cross-identity copies among retained identities does not verify biological identity,
measurement reliability, unknown provenance errors or external replication. Within-identity repetitions
and planned train/query content overlap remain separately visible in the audit.

## Methods

The source is NEMAR nm000305 v1.0.0 (DOI 10.82901/nemar.nm000305.v1.0.0; CC BY4.0), with
original published behavior from Dataverse v2.2 (DOI 10.57745/RBJRC7). For each identity, session01
runs01–04 alone fit coarse source QC, normalization, reference PCA and CSP+LDA; runs05–06 form
ID-disjoint reference query. Session02 describes validation without model selection; sessions03/04
are exploratory evaluations. Saved model bytes are frozen and predictions replayed exactly. A raw
numerical audit additionally tests content overlap, since different IDs do not establish independent signals.

The unchanged pipeline uses 74 ordered common EEG channels at 250 Hz in V, common-average reference,
73-dimensional Helmert coordinates, 5% trace shrinkage, PCA10 and CSP4. C3/Cz/C4 task-window power
uses a 0.5–4.5-second crop, Welch 250/125, Mu 8–13/Beta 13–30 Hz and equal weighting of run-level mean
log powers. This MI−rest contrast has no validated prestimulus baseline and is not baseline ERD.
Matched sampling fixes 12 trials/class/run: 144/session across six runs and 96/session across common
QC runs 03–06. Ten draws are averaged within identity. Insufficient cells remain unavailable without
reducing the preset. Whole identity trajectories receive 10,000 percentile-bootstrap draws, seed 42;
500 run draws per identity describe conditional decoder variation. Repetitions do not increase independent n.
Published session behavior averages six reported percentages; denominators, run order and trial outcomes
remain unresolved. No trial-level success labels are reconstructed.

## Results

First-to-last mean changes and 95% intervals are:

| Metric | All-ID arithmetic change [95% interval] | Source restriction change [95% interval] | Unit |
| --- | --- | --- | --- |
| Published online score | +14.568 [10.706, 18.266]; n=19 | +15.410 [11.526, 19.332]; n=14 | pp |
| Frozen CSP+LDA BA | -4.676 [-11.884, 2.333]; n=19 | -4.202 [-11.413, 2.711]; n=14 | pp |
| Mu MI−rest task-window contrast | -0.525 [-1.017, 0.038]; n=19 | -0.529 [-1.009, -0.058]; n=14 | dB |
| Beta MI−rest task-window contrast | -0.261 [-0.562, 0.045]; n=19 | -0.275 [-0.640, 0.100]; n=14 | dB |

All-identity EEG intervals are arithmetic and cannot support independent-participant inference.
The source-restricted analysis remains conditional on unresolved biological identity and provenance.
Within retained identities, fixed six-run matching is available for 14/14
and common-QC matching for 9/14. All-ID outputs retain
456 source-QC flags and 10
identities with at least one constant-prediction session. Failures and unavailable metrics remain recorded.
The companion source-restricted associations use five predefined metric pairs with Pearson/Spearman
and paired-variable whole-identity bootstrap, without p-values or causal interpretation; their complete
intervals, available identities and degenerate draws are preserved in the report and tables.

## Interpretation and reproducibility

Online published behavior, offline frozen-decoder generalization and EEG representation are distinct
endpoints. Decoder degradation does not establish human skill loss; geometric or task-window changes
do not establish learning, retention, mapping preservation or a causal mechanism. No new algorithm,
randomized intervention, unassisted same-mapping delayed-retention probe or external confirmation is
claimed. Additional public training deposits are separately audited resources and do not increase this
longitudinal cohort's sample size.

Native editable figures and all source/output SHA-256 checks are in
`notebooks/netbci2026_all19_20261011.ipynb`. Full numeric identity ledger, source data, frozen-model
receipts and storage checks remain separately inspectable. Exact report input hashes:

| Source | Path | SHA-256 |
| --- | --- | --- |
| all19 config | `configs/netbci_cohort_all19_20261010.json` | `d3de923978079cff7199c294f704a0282d3df589899df1a7f44578a5aabd2bf5` |
| official pinned manifest | `research_logs/netbci2026_sources/manifest.json` | `7e50f5281e91bec97791a84f5f3dbe20dc443b37c10d4bc6bcda96bed08c092c` |
| compact numeric audit | `research_logs/netbci_cohort_all19_20261010/numeric_signal_identity_summary_v2.json` | `3b5c282877c256ac95ba0f60a04592c302f3b2a17c298c4be482697ce41232ae` |
| full numeric audit (local; R2 receipt separate) | `research_logs/netbci_cohort_all19_20261010/numeric_signal_identity_v2.json` | `d1c4d267baa0a6c0803037db731ebd571f0aa65be9d4d1932e3d9c237815ef45` |
| all-ID summary receipt | `research_logs/netbci_cohort_all19_20261010/summary_run01/summary_receipt.json` | `2e3ac733fbcea87dcef012e9bd3acc2bddaf4436c2a5e59ed0b9c625a0bb28da` |
| restricted summary receipt | `research_logs/netbci_cohort_all19_20261010/independence_sensitivity_run01/sensitivity_receipt.json` | `464c8d0eedd2e6cc36394bed26ccf3948192c419b90db50feb2f4bf5768dcf56` |
