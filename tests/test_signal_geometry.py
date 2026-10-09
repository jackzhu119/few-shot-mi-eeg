"""Numerical signal and epoch-preprocessing contracts."""

import numpy as np
import pytest
from scipy.integrate import trapezoid

from learning_preserving_bci.datasets import EEGDataset, make_synthetic_dataset
from learning_preserving_bci.preprocessing import preprocess_epochs
from learning_preserving_bci.signal_processing import (
    bandpower,
    fft_spectrum,
    spatial_covariance,
    welch_psd,
)


def _sine(frequency=10, sfreq=128, n_times=512):
    return np.sin(2 * np.pi * frequency * np.arange(n_times) / sfreq)


def test_fft_amplitude_and_welch_power_have_distinct_correct_units():
    signal = 2 * _sine()
    frequencies, amplitude = fft_spectrum(signal, 128)
    peak = np.argmax(amplitude)
    assert frequencies[peak] == 10
    assert amplitude[peak] == pytest.approx(2.0)
    frequencies, psd = welch_psd(signal, 128, nperseg=512)
    assert trapezoid(psd, x=frequencies) == pytest.approx(2.0, rel=1e-6)


def test_fft_does_not_double_dc_or_nyquist_bins():
    _, dc = fft_spectrum(np.full(32, 3.0), 64, detrend=False)
    _, nyquist = fft_spectrum((-1.0) ** np.arange(32), 64)
    assert dc[0] == pytest.approx(3)
    assert nyquist[-1] == pytest.approx(1)


def test_bandpower_distinguishes_mu_and_beta_and_preserves_epochs():
    X = np.stack((_sine(10), _sine(20)))[None, ...]
    mu_power = bandpower(X, 128, (8, 13))
    beta_power = bandpower(X, 128, (18, 23))
    assert mu_power.shape == (1, 2)
    assert mu_power[0, 0] > 1_000 * mu_power[0, 1]
    assert beta_power[0, 1] > 1_000 * beta_power[0, 0]
    relative = bandpower(X, 128, (8, 13), relative=True)
    assert relative[0, 0] == pytest.approx(1, abs=1e-10)
    np.testing.assert_array_equal(bandpower(np.zeros((2, 64)), 128, relative=True), np.zeros(2))


def test_covariance_is_centered_symmetric_and_regularized():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(3, 4, 100))
    covariance = spatial_covariance(X, regularization=0)
    shifted = spatial_covariance(X + np.arange(4)[None, :, None], regularization=0)
    np.testing.assert_allclose(covariance, shifted, atol=1e-14)
    np.testing.assert_allclose(covariance[0], np.cov(X[0]))
    np.testing.assert_allclose(covariance, covariance.swapaxes(-1, -2))
    ridge = spatial_covariance(np.ones((2, 3, 32)), regularization=0.1)
    np.testing.assert_allclose(np.linalg.eigvalsh(ridge), 0.1)
    normalized = spatial_covariance(X, normalize_trace=True)
    np.testing.assert_allclose(np.trace(normalized, axis1=-2, axis2=-1), 1)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: fft_spectrum(np.array([1, np.nan]), 100),
        lambda: fft_spectrum(np.ones(1), 100),
        lambda: fft_spectrum(np.ones(8), 0),
        lambda: welch_psd(np.ones(8), 100, nperseg=9),
        lambda: welch_psd(np.ones(8), 100, nperseg=4, noverlap=4),
        lambda: bandpower(np.ones(32), 100, (13, 8)),
        lambda: bandpower(np.ones(32), 100, (8, 51)),
        lambda: spatial_covariance(np.ones(32)),
        lambda: spatial_covariance(np.ones((2, 32)), regularization=-1),
        lambda: spatial_covariance(np.ones((2, 32)), regularization=0, normalize_trace=True),
    ],
)
def test_signal_functions_reject_invalid_inputs(operation):
    with pytest.raises(ValueError):
        operation()


def test_preprocessing_preserves_identity_and_does_not_pool_trials():
    dataset = make_synthetic_dataset(n_subjects=2, n_sessions=1, trials_per_class=2)
    original = dataset.X.copy()
    processed = preprocess_epochs(dataset)
    np.testing.assert_array_equal(dataset.X, original)
    np.testing.assert_allclose(processed.X.mean(axis=1), 0, atol=1e-15)
    independent = np.concatenate(
        [preprocess_epochs(dataset.subset(np.array([i]))).X for i in range(dataset.n_trials)]
    )
    np.testing.assert_allclose(processed.X, independent)
    for name in ("y", "subjects", "sessions"):
        np.testing.assert_array_equal(getattr(processed, name), getattr(dataset, name))
    assert processed.channel_names == dataset.channel_names
    assert processed.is_synthetic is True


def test_bandpass_suppresses_out_of_band_content():
    X = (_sine(10) + _sine(40))[None, None, :]
    dataset = EEGDataset(X, np.array([0]), np.array(["S1"]), np.array(["session1"]), 128)
    filtered = preprocess_epochs(dataset, reference=None)
    before = bandpower(X, 128, (35, 45)).item()
    after = bandpower(filtered.X, 128, (35, 45)).item()
    assert after < before / 100
    assert bandpower(filtered.X, 128, (8, 13)).item() > 0.4


def test_explicit_baseline_uses_epoch_relative_seconds():
    X = np.arange(12.0).reshape(1, 2, 6)
    dataset = EEGDataset(X, np.array([0]), np.array([1]), np.array([1]), 10)
    processed = preprocess_epochs(
        dataset, l_freq=None, h_freq=None, reference=None, baseline=(0, 0.2)
    )
    np.testing.assert_allclose(processed.X[..., :3].mean(axis=-1), 0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"l_freq": 40, "h_freq": 30},
        {"h_freq": 64},
        {"reference": "Cz"},
        {"baseline": (-0.1, 0.2)},
        {"baseline": (0, 5)},
    ],
)
def test_preprocess_invalid_options(overrides):
    dataset = make_synthetic_dataset(n_subjects=1, n_sessions=1, trials_per_class=1)
    with pytest.raises(ValueError):
        preprocess_epochs(dataset, **overrides)


def test_preprocess_rejects_short_zero_phase_epochs():
    dataset = EEGDataset(
        np.zeros((2, 2, 8)), np.array([0, 1]), np.array([1, 1]), np.array([1, 1]), 128
    )
    with pytest.raises(ValueError, match="too short"):
        preprocess_epochs(dataset)
