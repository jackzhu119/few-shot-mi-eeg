# Research journal: existing NETBCI behavioral records

2026-10-10, existing research/learning-preserving-bci checkout and CPU environment.
The user corrected a premature suggestion to obtain behavioral data that are
already public. We reverified the official 19-person source table and dictionary,
then executed the supported session-level analysis instead of treating run/trial
mapping as a blanket blocker. No author email was sent.

Actual scope: 456 published percentages/76 behavior sessions, but only one EEG
participant with 717 windows. Four subject/session joins; run/trial outcomes and
scoring denominators unresolved. Cohort observed last-minus-first change +14.5684pp,
paired subject-bootstrap CI [10.7063,18.2662]. No causal learning inference.
Pilot task-window Mu contrast, global geometry and frozen readout behave
differently; changes in absolute rest/imagery power are also retained. Additional
96-trial sampling tests count sensitivity. Neither baseline ERD nor a neural
learning effect was established. The pilot is highest-scoring in every session,
so broad EEG inference is especially unjustified.

An independent methods/code/numerical review identified floating-point zero as
an erroneous decline count. Corrected 15 to14, separately showed rounding
sensitivity13, preserved old runs and exact code snapshots. Final analyses replay
exactly (11 computational files), 122 tests pass, Ruff/synthetic smoke/MOABB checks
pass. Three native scientific figures visually inspected; notebook 5 executed
cells/zero errors/3 figures. HTML structural checks pass; no full-browser
screenshot claim. Initial plot relative-path failure retained and recorded.

Decision: supported session-level neurobehavioral preparation continues now.
Next validate multiple participants, acquisition/QC, task information and source-
only decoder training under fixed temporal partitions. Learning-preserving policy
claims still require controlled online intervention and independent delayed probes.
No extra EEG downloads, real model training, paid compute, new repository or
first-paper changes occurred in this phase.
