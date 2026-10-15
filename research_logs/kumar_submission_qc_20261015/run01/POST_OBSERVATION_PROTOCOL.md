# Exploratory saved-prediction QC sensitivity: rules recorded before computation

Recorded 2026-10-15 UTC, after exposure to the original results. This is a new,
user-requested **exploratory sensitivity analysis**, not preregistration and not
a replacement for the frozen primary analysis. Its numerical outputs do not
exist at this protocol's creation. Reference checkout: 370bc94b7af3c926adeb02c38e430a53e4a64135.

1. Read only saved text predictions, saved text metadata, fixed configuration,
   existing numerical summaries and historical integrity receipts. Do not read
   EEG arrays or weights; do not fit, forward a model or change predictions.
2. The sole exclusion for this sensitivity is the existing Boolean
   `qc_peak_to_peak_over_250uv` flag in the frozen split manifest. Verify it
   against the saved raw maximum channel peak-to-peak amplitude and fixed
   0.00025 V threshold. Do not adjust the threshold or derive a new rule.
   The original 44 incomplete windows and 30 incomplete query windows retain
   their historical exclusions, independent of QC. A flag is not a certified
   artifact; an unflagged window is not certified artifact-free.
3. Join by exact `trial_id`, requiring unique complete identities, exact frozen
   labels, subject/session/run/role and full method/seed coverage. Unexpected,
   duplicate, missing or inconsistent rows fail the analysis. Preserve a join
   ledger for every query, including the historically excluded query identities.
4. Include all three CPU methods and all three fixed EEGNet seeds. Compute BA
   separately for each seed, then average the three seed BAs within each
   participant/session. Never average seeds as extra participants or choose a
   favorable seed; no majority-vote ensemble is created.
5. Preserve both `all_included` and `unflagged` versions for each participant,
   each of six sessions, all-target pooled and all-query pooled. Record each
   true-class count, predicted-class count, confusion cells and collapse.
   BA is undefined if either true class is absent; retain that row with a
   reason. A mathematical BA needs at least one observation per class; mark
   groups with fewer than five per class as low-count descriptive groups,
   but do not impose a new data-driven inclusion threshold.
6. The target endpoint remains the equally weighted mean of the five target
   session BAs, after seed averaging. A participant endpoint is undefined if
   any of the five sessions is undefined; never silently average fewer
   sessions. Report complete-case eligibility, missing sessions and all
   participant rows. Cross-subset changes use the intersection of eligible
   participants, explicitly identified. Pooled-query BA is supplementary and
   cannot replace the equal-session endpoint.
7. Keep the original remaining-12 primary comparison full CSP/LDA minus frozen
   CSP/LDA as primary in its original analysis. The full-minus-LDA-only
   contrast remains secondary. Both corresponding QC contrasts are new
   exploratory sensitivities. Report development six, remaining twelve and
   all eighteen separately; never use sensitivity results for policy selection.
8. Use participant bootstrap percentile intervals, 10,000 draws, NumPy
   default_rng(42), lexicographic participant ordering, matching the saved
   convention. No trial/bootstrap independence assumption, new hypothesis
   test, p value or multiple-comparison claim. Report eligible denominators.
   No interval if fewer than two eligible participants.
9. Report exact individual gain magnitudes and deterministic leave-one-
   participant-out means for both CPU contrasts; interpret the actual ranges,
   not every small negative difference as substantial harm. This is influence
   description, not a basis for exclusions. Record all eligibility rows.
10. Hash all numerical input bytes before and after analysis, record runtime,
    code/protocol hashes, identity coverage and reconstruction agreement with
    saved all-query primary summaries. Write new output files exclusively;
    do not overwrite frozen results. On any failure preserve completed outputs
    and an actual exception receipt, with no automatic retry.

Interpretation boundaries: conditioning the evaluated queries on an amplitude
flag changes their sample and class composition and may introduce selection;
it is not artifact removal validation. The fitted models and their training,
validation and support data stay exactly as originally used, including flagged
training examples. This sensitivity cannot establish robustness to artifacts
in fitting data, confirm continuous motor imagery, repair variable task-phase
timing, or demonstrate an effective update gate. All previously exposed test
cohort analyses remain exploratory.
