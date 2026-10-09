"""Inspectable EEG spectra, band power, and spatial covariance features."""

from numbers import Real

import numpy as np
from scipy.integrate import trapezoid
from scipy.signal import welch


def _signal_array(X: np.ndarray, *, minimum_samples: int = 2) -> np.ndarray:
    raw = np.asarray(X)
    if raw.dtype.kind not in "biuf":
        raise ValueError("signals must contain real numeric values")
    array = np.asarray(raw, dtype=float)
    if (
        array.ndim < 1
        or any(size == 0 for size in array.shape)
        or array.shape[-1] < minimum_samples
    ):
        raise ValueError(
            f"signals require at least {minimum_samples} time samples on the last axis"
        )
    if not np.isfinite(array).all():
        raise ValueError("signals must contain only finite values")
    return array


def _sampling_frequency(sfreq: float) -> float:
    if (
        isinstance(sfreq, (bool, np.bool_))
        or not isinstance(sfreq, Real)
        or not np.isfinite(sfreq)
        or sfreq <= 0
    ):
        raise ValueError("sfreq must be a positive finite scalar")
    return float(sfreq)


def fft_spectrum(
    X: np.ndarray, sfreq: float, *, detrend: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Return frequencies (Hz) and one-sided amplitude on the last axis.

    Non-DC, non-Nyquist bins are doubled so an integer-bin sinusoid of amplitude
    one has peak amplitude one. This is an amplitude spectrum, not a PSD.
    """
    array = _signal_array(X)
    sfreq = _sampling_frequency(sfreq)
    if detrend:
        array = array - array.mean(axis=-1, keepdims=True)
    n_times = array.shape[-1]
    amplitudes = np.abs(np.fft.rfft(array, axis=-1)) / n_times
    if n_times % 2 == 0:
        amplitudes[..., 1:-1] *= 2
    else:
        amplitudes[..., 1:] *= 2
    return np.fft.rfftfreq(n_times, d=1 / sfreq), amplitudes


def welch_psd(
    X: np.ndarray,
    sfreq: float,
    *,
    nperseg: int | None = None,
    noverlap: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return Welch frequencies and density (signal units squared per Hz).

    Uses a Hann window and per-segment constant detrending. No pooling or
    parameter fitting occurs across trials or subjects.
    """
    array = _signal_array(X)
    sfreq = _sampling_frequency(sfreq)
    if nperseg is None:
        nperseg = min(256, array.shape[-1])
    if (
        isinstance(nperseg, bool)
        or not isinstance(nperseg, (int, np.integer))
        or not 2 <= nperseg <= array.shape[-1]
    ):
        raise ValueError("nperseg must be an integer between 2 and the number of samples")
    if noverlap is not None and (
        isinstance(noverlap, bool)
        or not isinstance(noverlap, (int, np.integer))
        or not 0 <= noverlap < nperseg
    ):
        raise ValueError("noverlap must be an integer in [0, nperseg)")
    return welch(
        array,
        fs=sfreq,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        detrend="constant",
        return_onesided=True,
        scaling="density",
        axis=-1,
    )


def _integrate_band(
    frequencies: np.ndarray, psd: np.ndarray, low: float, high: float
) -> np.ndarray:
    """Integrate including interpolated exact band boundaries."""
    inner = (frequencies > low) & (frequencies < high)
    low_index = np.clip(
        np.searchsorted(frequencies, low, side="right") - 1, 0, len(frequencies) - 2
    )
    high_index = np.clip(
        np.searchsorted(frequencies, high, side="right") - 1, 0, len(frequencies) - 2
    )

    def interpolate(value: float, index: int) -> np.ndarray:
        ratio = (value - frequencies[index]) / (frequencies[index + 1] - frequencies[index])
        return psd[..., index] * (1 - ratio) + psd[..., index + 1] * ratio

    points = np.concatenate(([low], frequencies[inner], [high]))
    values = np.concatenate(
        (
            interpolate(low, low_index)[..., None],
            psd[..., inner],
            interpolate(high, high_index)[..., None],
        ),
        axis=-1,
    )
    return trapezoid(values, x=points, axis=-1)


def bandpower(
    X: np.ndarray,
    sfreq: float,
    band: tuple[float, float] = (8.0, 13.0),
    *,
    relative: bool = False,
    nperseg: int | None = None,
) -> np.ndarray:
    """Integrate Welch PSD between two frequencies, retaining leading axes.

    Relative power divides by the integral across all available Welch bins.
    Zero-power signals have zero relative band power. For odd segment lengths,
    the final Welch bin is below Nyquist, so bands must lie within that bin.
    """
    sfreq = _sampling_frequency(sfreq)
    limits = np.asarray(band, dtype=float)
    if (
        limits.shape != (2,)
        or not np.isfinite(limits).all()
        or not 0 <= limits[0] < limits[1] <= sfreq / 2
    ):
        raise ValueError("band must satisfy 0 <= low < high <= Nyquist")
    frequencies, psd = welch_psd(X, sfreq, nperseg=nperseg)
    if limits[1] > frequencies[-1]:
        raise ValueError("band upper edge exceeds the final Welch frequency bin")
    power = _integrate_band(frequencies, psd, float(limits[0]), float(limits[1]))
    if relative:
        total = trapezoid(psd, x=frequencies, axis=-1)
        power = np.divide(power, total, out=np.zeros_like(power), where=total > 0)
    return power


def spatial_covariance(
    X: np.ndarray,
    *,
    regularization: float = 1e-6,
    normalize_trace: bool = False,
) -> np.ndarray:
    """Return centered, unbiased covariance across channels for each epoch.

    Input axes end in ``(channel, time)``. ``regularization`` is a nonnegative
    diagonal ridge in squared signal units, added before optional trace
    normalization. No information is shared between epochs.
    """
    array = _signal_array(X)
    if array.ndim < 2:
        raise ValueError("spatial_covariance requires (..., channels, time)")
    if (
        isinstance(regularization, (bool, np.bool_))
        or not isinstance(regularization, Real)
        or not np.isfinite(regularization)
        or regularization < 0
    ):
        raise ValueError("regularization must be nonnegative and finite")
    centered = array - array.mean(axis=-1, keepdims=True)
    covariance = centered @ np.swapaxes(centered, -1, -2) / (array.shape[-1] - 1)
    covariance = covariance + regularization * np.eye(array.shape[-2])
    if normalize_trace:
        trace = np.trace(covariance, axis1=-2, axis2=-1)
        if np.any(trace <= 0):
            raise ValueError("cannot normalize covariance with zero trace")
        covariance = covariance / trace[..., None, None]
    return covariance


__all__ = ["fft_spectrum", "welch_psd", "bandpower", "spatial_covariance"]
