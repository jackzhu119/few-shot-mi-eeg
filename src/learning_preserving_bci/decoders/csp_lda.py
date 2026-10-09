"""Common spatial patterns followed by regularized LDA."""

from mne.decoding import CSP
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import Pipeline


def make_csp_lda(n_components: int = 4, random_state: int = 42) -> Pipeline:
    """Return an unfitted CSP + LDA pipeline.

    Pass trials as ``(trial, channel, time)`` arrays. CSP and LDA are fitted
    together on training trials only. ``random_state`` is retained for a
    consistent factory API; neither of these estimators samples randomness.
    """
    if n_components < 1:
        raise ValueError("n_components must be positive")
    return Pipeline(
        [
            (
                "csp",
                CSP(
                    n_components=n_components,
                    reg="ledoit_wolf",
                    log=True,
                    norm_trace=False,
                    transform_into="average_power",
                ),
            ),
            ("lda", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ]
    )
