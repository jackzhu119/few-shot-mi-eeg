# Figure captions

**Fig 1. Target-query decoding by participant.**

\(A) Six development participants. (B) Twelve primary participants. Each colored point represents one participant's mean BA over five target sessions; faint lines connect the same participant across methods. EEGNet averages three seeds within session. Diamonds and bars show cohort means and 95% participant-bootstrap intervals (10,000 resamples, seed 42). All methods were evaluated on the same query identities. The two CPU updating methods used identical source-training and current-support labels; the other information budgets are given in Table 1.

**Fig 2. Full-refit gain over frozen decoding in the primary cohort.**

Each value is a participant's mean paired BA difference across five target sessions. Participants appear in numeric order. Nine differences are positive and three negative, with a cohort mean of +7.42 percentage points and a 95% participant-bootstrap interval of +2.49 to +12.48. Full refitting used 19/20 current-session support labels in addition to the 40 source training labels. The figure displays observed individual differences; statistical checks concern participant-level cohort contrasts.

**Fig 3. Task-score orientation across chronological support halves.**

Each development participant contributes five target support sessions. Circles and squares represent the first and second halves within class. Values are class-balanced contrasts of frozen source-LDA scores divided by twice their source-score standard deviation. The shared zero line separates positive and reversed class orientation. Nineteen sessions have two positive margins, two have two negative margins and nine have opposite signs. The analysis uses source/support data to describe calibration-measurement reliability.

**Fig 4. Session-level gains from full CSP/LDA refitting.**

Cells show BA differences on identical query trials: (A) full refitting minus freezing and (B) full refitting minus LDA-only recalibration. Both panels include 18 participants and five target sessions. A horizontal line separates development and primary cohorts. Participants remain in numeric order within each cohort. The symmetric color scale is shared, and values are displayed in percentage points to one decimal. Exact differences and query counts are supplied in the figure source-data CSV. Participant-level averages define the inferential endpoints.

**Fig 5. Prediction changes underlying recalibration gains.**

Rows show the primary cohort (12 participants), development cohort (six), and their all-participant union (18). (A, C, E) Blue bars show class-balanced correction contributions and hatched orange bars show introduced errors with negative sign; their sum is the net BA change. Diamonds and bars indicate the net means and 95% participant-bootstrap intervals. (B, D, F) Left- and right-class recall changes use the same weighting. All three contrasts are displayed. Each participant contributes the equal mean of five target sessions; intervals use 10,000 resamples with seed 42. These are exploratory analyses of saved predictions.

**Fig 6. Consistency of the spatial-update advantage.**

(A) Each point gives one participant’s mean LDA-only-minus-frozen gain (horizontal) and full-minus-LDA-only gain (vertical) across five sessions. Circles show the primary cohort and open squares the development cohort; numbers identify participants. The dashed line marks zero total gain. (B) Primary-cohort session means for the full-minus-frozen and full-minus-LDA-only contrasts, with 95% participant-bootstrap intervals (12 participants; 10,000 resamples; seed 42). (C) Cohort means after deleting each indicated primary participant, with 11 participants per point; dashed lines give the original 12-participant means. The session profiles and deletion summaries describe repeated-session variation and participant influence. All values are supplied in S1 Data.
