# Figure captions for the PLOS ONE author-review version

## Fig 1. Target-query decoding by participant.

(A) Six development participants. (B) Twelve remaining participants. Each colored
point is one participant's balanced accuracy (BA), with equal weight for five
target sessions. EEGNet averages all three fixed seeds within session before the
session mean; CPU methods use their single frozen execution. Faint lines connect
the same participant across methods. Diamonds and bars reproduce saved means and
95% descriptive participant-bootstrap intervals (10,000 resamples, seed 42), not
new intervals. All methods use the same query trial identities, but information
budgets differ: each learns from 40 source TRAIN labels; EEGNet also uses 20 source
validation labels for epoch selection, while the two updating CPU baselines use
19 or 20 labeled support trials from the current target session. This is not a
matched-budget architecture ranking. The follow-up comparison is exploratory;
all seeds, participants and class-collapsed predictions are retained.

## Fig 2. Original primary CPU contrast by participant.

Full CSP/LDA refitting minus frozen CSP/LDA for the original remaining-12 primary
cohort, after equal averaging of five target sessions. Numeric participant order
is retained. Nine differences are positive and three negative. The negative
changes are sub-6 −5.82, sub-14 −0.67 and sub-15 −0.20 percentage points; these
descriptive decreases differ in magnitude and are not individual significance
claims. The mean and original 95% participant-bootstrap interval are +7.42
[+2.49, +12.48] percentage points. Refit has access to current-session support
labels whereas frozen does not. This figure adds no hypothesis test and does
not establish learning, skill retention or clinical efficacy.

## Fig 3. Signed-score consistency across target support halves.

Each development participant contributes five target support sessions. Circles
and squares show the first and second chronological halves within class. Values
are the saved class-balanced contrast of frozen source-LDA scores divided by
twice their source-score standard deviation. All 60 values use shared axes.
Of 30 sessions, 19 have two positive margins, two have two negative margins and
nine have opposite signs. The zero line indicates score orientation, not a
selected gate. These support-only diagnostics do not validate an update policy.

## Fig 4. Longitudinal paired changes for every participant and target session.

Each cell is a difference in balanced accuracy for identical saved query trials:
(A) full CSP/LDA refit minus frozen CSP/LDA (the original primary contrast);
(B) full refit minus LDA-only recalibration (the secondary same-support-label
contrast). Both panels contain all 18 participants and five target sessions.
Development and remaining cohorts are separated by a horizontal line; participant
identities are numeric within each cohort, without effect-size sorting. The
symmetric color scale is shared, and every signed cell value is displayed in
percentage points to one decimal. Exact values and trial counts are in the
matching source-data CSV. These session values describe heterogeneity; sessions
are not treated as independent participants. The original primary endpoint and
all inferential comparisons remain unchanged. No new model, query inference,
gate, bootstrap or significance test is performed to produce this figure.

## Export and font status

Each figure has PNG/PDF/SVG review exports and a flattened, single-frame RGB TIFF
with LZW compression at 600 dpi; dimensions and complete byte hashes are in the
generation receipt. Captions and figure titles are outside the images. The
existing host does not contain Arial or Times New Roman; all labels actually use
Liberation Sans, a metric-compatible substitute, at 8–12 pt. Thus strict requested
font-family compliance is **not claimed**. No font or environment was installed.
The editable vector files support later conversion if the journal requires an
exact font family. Content, dimensions, resolution and flattened TIFF checks
were performed on the actual exported bytes, not inferred from source settings.
