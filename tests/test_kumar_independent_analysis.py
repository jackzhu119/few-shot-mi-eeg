"""Scientific unit and repeated-measure checks for the independent diagnostics."""
import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("kumar_independent_analysis", Path(__file__).resolve().parents[1] / "scripts/verify_analyze_kumar_results.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_absolute_mu_beta_power_of_known_voltage_sinusoids():
    time = np.arange(640) / 128
    amplitude = 20e-6
    signal = np.asarray([[amplitude * np.sin(2 * np.pi * 10 * time),
                          amplitude * np.sin(2 * np.pi * 20 * time)]])
    power = module.epoch_power(signal)
    np.testing.assert_allclose(power[0, [0, 1], [0, 1]], amplitude ** 2 / 2, rtol=1e-10)
    assert power[0, 0, 1] < 1e-25 and power[0, 1, 0] < 1e-25


def test_participant_block_uncertainty_keeps_declared_independent_unit():
    rows = [{"subject": f"sub-{subject}", "delta_frozen_BA": subject + session / 10,
             "drift": subject + session / 10} for subject in range(4) for session in range(5)]
    result = module.block_correlation(rows, "drift", replicates=40)
    assert result["participants"] == 4 and result["sessions"] == 20
    np.testing.assert_allclose(result["participant_block_bootstrap_ci95"], [1, 1])
    assert module.rank_correlation([1, 1, 1], [1, 2, 3]) is None
