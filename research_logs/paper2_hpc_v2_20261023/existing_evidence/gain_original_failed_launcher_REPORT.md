# Audit of complete saved gain results from a failed monitored operation

The complete saved gain results passed independent integrity and arithmetic checks.
The **launcher still failed with exit1**: its original procfs monitor raised
`KeyError: VmRSS`, then stopped the process group. The actual worker return code
was not independently recorded. This report does not convert that operation to
a clean exit, accepted run or successful retry. No selector/model was refitted or
rerun, and no raw EEG or query trial records were accessed.

The private output has all seven files named by its execution receipt plus the
complete receipt itself. Every original byte SHA matches. The recorded selector
start/finish times are 04:00:40.506113/04:00:40.687192 UTC; the first cleanup signal
is at04:00:40.849363 UTC,0.162171s after the receipt's recorded finish. This is
consistent with failure near the consumer exit boundary; the exact transient
process state that lacked VmRSS is not established by the saved traceback.
A zero-byte buffered consumer log does not establish that no Python ran.

The seven saved Ridge records cover six development leave-one-participant-out
folds (five training participants/25 sessions each) and one development6→remaining12
fit (30 training sessions). Actual train/evaluation participants and rows are
separate. Recomputed training-only scaler moments, saved alpha10, fixed drift
medians, legal four-feature values and all actions match. Saved standardization
and saved linear coefficients reproduced all90 predicted gain pairs by NumPy
multiplication (maximum absolute difference2.78e-17); no coefficient solving or
new fitting was performed by the main validator. A separate independent reviewer
also checked saved-model normal-equation residuals without solving/refitting.

All630 policy rows match their90 saved outcome vectors, including exact
frequency-matched random expectations, BA changes against each always policy,
update/action rates, any-measured-decrease frequencies and mean downside
magnitudes. The126 participant endpoints are exactly equal five-session means.
All140 saved mean/CI rows match the fixed10000-draw,seed42,whole-participant
bootstrap arithmetic, and the six gain-sign tables match saved outcomes. This
arithmetic verification adds no selector attempt and replaces no original value.

The following remaining12 values are percentages for BA/frequency and percentage
points for differences/magnitude; intervals are pointwise95% participant-bootstrap
intervals, with independent n=12, not60 sessions.

| Policy | BA | Gain vs full (pp) | Lower-BA sessions vs frozen (%) | Mean downside magnitude (pp) |
| --- | ---: | ---: | ---: | ---: |
| Always frozen | 57.94 [52.62, 63.62] | -7.42 [-12.43, -2.51] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| Always LDA | 59.89 [54.27, 65.44] | -5.47 [-8.88, -2.16] | 41.67 [31.67, 53.33] | 3.49 [2.22, 4.98] |
| Always full | 65.36 [59.77, 70.83] | 0.00 [0.00, 0.00] | 30.00 [16.67, 45.00] | 2.56 [1.25, 4.08] |
| Four-feature Ridge | 60.89 [55.14, 66.71] | -4.47 [-7.94, -1.32] | 38.33 [26.67, 50.00] | 3.16 [1.87, 4.61] |
| Support-half CV | 63.14 [58.63, 67.59] | -2.22 [-5.05, 0.26] | 11.67 [3.33, 23.33] | 1.59 [0.25, 3.26] |
| Training-median drift | 65.46 [60.02, 70.87] | 0.10 [-1.77, 1.83] | 6.67 [0.00, 15.00] | 0.20 [0.00, 0.44] |
| Frequency-matched random expectation | 60.80 [55.26, 66.26] | -4.56 [-7.40, -1.80] | 39.72 [28.89, 51.94] | 3.33 [2.10, 4.78] |

The additional fixed participant-paired Ridge−frequency-matched-random control is
**+0.093189pp [−0.904104,+1.146698]** in remaining12 and
**−1.328131pp [−3.328131,0.000000]** in development6. These were calculated only
from saved participant endpoints, with10000 bootstrap replicates and seed42;
all20000 bootstrap mean differences are preserved in
`ridge_random_bootstrap_means.csv`. The three vs-full comparisons in
`paired_policy_controls.csv` copy original saved values unchanged.

Ridge provides no supported improvement over the frequency-matched random
expectation and falls below always-full adaptation in remaining12. The drift
rule's remaining12 difference from always full is only+0.097953pp
[−1.769115,+1.825347], which establishes neither superiority nor equivalence.
Its development6 BA is 61.81 [58.20, 65.95]%, with gain over frozen 1.84 [-0.39, 4.89]pp, consistent with an unstable exploratory pattern.

All18 participants' queries were previously exposed. These participant-isolated
simulations are exploratory, with no feature/hyperparameter/threshold search,
new p-value family, clinical claim or recovered independent confirmation.
Small negative changes remain measured decreases, not automatically material harm.

Public `model_fit_audit_public.json` retains only fold scope, participant/session
identities, alpha and hashes of private learned fields. The original JSON with
coefficients/scaler/threshold values remains private; it must not be committed or
included in public S1 Data. `validation.json` preserves launcher exit1, unknown
worker return code and no acceptance. Original output/monitor files are unchanged.

The saved-data four-panel figures are under
`manuscript/figures/component_followup_20261016/gain_feasibility/run01/` for both
cohorts. They show all seven policies' BA, paired vs-full gain, action/update
proportions and measured-decrease frequency. Full downside-magnitude/update
intervals are in `policy_summary_for_manuscript.csv`. The figures display the
preserved execution limitation and do not create new statistics or fits.

The numerical-zero diagnostic identifies sub12/ses2 full−LDA=−5.55e−17,
changing the remaining12 descriptive strict40+/15−/5 ties to40+/14−/6 ties
at |difference|≤1e−12. Sub15/ses1 LDA−frozen=−1.11e−16 changes the always-LDA
and frequency-matched-random descriptive decrease frequencies only; Ridge,
always-full, support-CV and drift rates are unaffected. No such numerical-zero
item is interpreted as material harm. The original strict values, selection,
intervals and Holm family are unchanged. See the four strict/tolerance CSVs.

Publication-format PDF and RGB LZW600dpi TIFF variants (with PNG/SVG companions)
are now in `gain_feasibility/publication_format/run01/`. The title uses
evaluation, and execution limitations are in `publication_caption.md`/S2; the
original figures and scientific values remain unchanged.
