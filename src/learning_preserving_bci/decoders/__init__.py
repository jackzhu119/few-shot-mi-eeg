"""Training baselines with a scikit-learn style interface."""

from .csp_lda import make_csp_lda

__all__ = ["make_csp_lda", "EEGNetClassifier"]


def __getattr__(name):
    if name == "EEGNetClassifier":
        from .eegnet import EEGNetClassifier

        return EEGNetClassifier
    raise AttributeError(name)
