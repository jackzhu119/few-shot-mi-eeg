"""Stateless epoch preprocessing with explicit filtering and reference choices."""

from numbers import Real

import numpy as np
from scipy.signal import butter, sosfiltfilt

from learning_preserving_bci.datasets import EEGDataset


def preprocess_epochs(
    dataset: EEGDataset,
    *,
    l_freq: float | None = 8.0,
    h_freq: float | None = 30.0,
    filter_order: int = 4,
    reference: str | None = "average",
    baseline: tuple[float, float] | None = None,
) -> EEGDataset:
    """Filter each epoch, optionally subtract baseline, and re-reference.

    Filtering uses a zero-phase Butterworth SOS filter along each trial's time
    axis. This is suitable for offline analysis and cannot establish causal
    online decoder performance. Baseline bounds are seconds from epoch sample
    zero and include samples on both boundaries. No statistics are fit across
    trials; learned normalization and feature transforms must be fit on the
    training partition separately.
    """
    if not isinstance(dataset, EEGDataset):
        raise TypeError("dataset must be an EEGDataset")
    if (
        isinstance(filter_order, bool)
        or not isinstance(filter_order, (int, np.integer))
        or filter_order < 1
    ):
        raise ValueError("filter_order must be a positive integer")
    if reference not in (None, "average"):
        raise ValueError("reference must be None or 'average'")
    nyquist = dataset.sfreq / 2
    for name, cutoff in (("l_freq", l_freq), ("h_freq", h_freq)):
        if cutoff is not None and (
            isinstance(cutoff, (bool, np.bool_))
            or not isinstance(cutoff, Real)
            or not np.isfinite(cutoff)
            or not 0 < cutoff < nyquist
        ):
            raise ValueError(f"{name} must be between zero and Nyquist, or None")
    if l_freq is not None and h_freq is not None and l_freq >= h_freq:
        raise ValueError("l_freq must be less than h_freq")
    X = dataset.X.copy()
    if l_freq is not None or h_freq is not None:
        if l_freq is not None and h_freq is not None:
            cutoff, filter_type = (l_freq, h_freq), "bandpass"
        elif l_freq is not None:
            cutoff, filter_type = l_freq, "highpass"
        else:
            cutoff, filter_type = h_freq, "lowpass"
        sos = butter(filter_order, cutoff, btype=filter_type, fs=dataset.sfreq, output="sos")
        try:
            X = sosfiltfilt(sos, X, axis=-1)
        except ValueError as error:
            raise ValueError(
                "epochs are too short for this zero-phase filter; use longer epochs or disable filtering"
            ) from error
    if baseline is not None:
        limits = np.asarray(baseline, dtype=float)
        if (
            limits.shape != (2,)
            or not np.isfinite(limits).all()
            or limits[0] < 0
            or limits[0] > limits[1]
        ):
            raise ValueError("baseline must be ordered finite nonnegative seconds")
        times = np.arange(X.shape[-1]) / dataset.sfreq
        if limits[1] > times[-1]:
            raise ValueError("baseline lies outside the epoch")
        mask = (times >= limits[0]) & (times <= limits[1])
        if not mask.any():
            raise ValueError("baseline interval contains no samples")
        X = X - X[..., mask].mean(axis=-1, keepdims=True)
    if reference == "average":
        if X.shape[1] < 2:
            raise ValueError("average reference requires at least two channels")
        X = X - X.mean(axis=1, keepdims=True)
    return EEGDataset(
        X,
        dataset.y,
        dataset.subjects,
        dataset.sessions,
        dataset.sfreq,
        dataset.channel_names,
        dataset.is_synthetic,
    )


__all__ = ["preprocess_epochs"]
