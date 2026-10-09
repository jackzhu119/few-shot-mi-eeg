"""Run a synthetic CPU pipeline; outputs are software checks, not neuroscience."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from learning_preserving_bci.datasets import make_synthetic_dataset
from learning_preserving_bci.decoders import make_csp_lda
from learning_preserving_bci.evaluation import bootstrap_subject_mean, evaluate_fixed_decoder
from learning_preserving_bci.neural_geometry import covariance_distance, fit_pca
from learning_preserving_bci.preprocessing import preprocess_epochs
from learning_preserving_bci.signal_processing import (
    bandpower,
    fft_spectrum,
    spatial_covariance,
    welch_psd,
)
from learning_preserving_bci.utils import write_result_json


def run(config: dict, repository: Path) -> dict:
    if config.get("scientific_use") != "software_validation_only":
        raise ValueError("This runner accepts only software_validation_only configurations")
    if config["decoder"]["type"] != "csp_lda":
        raise ValueError("This small smoke workflow implements CSP+LDA only")
    seed = config["seed"]
    dataset = make_synthetic_dataset(seed=seed, **config["data"])
    filtered = preprocess_epochs(dataset, **config["preprocessing"])
    frequencies, spectrum = fft_spectrum(dataset.X, dataset.sfreq)
    psd_frequencies, psd = welch_psd(dataset.X, dataset.sfreq)
    # Physiological diagnostics use the original signal; decoder filtering is separate.
    mu = bandpower(dataset.X, dataset.sfreq, (8.0, 13.0))
    beta = bandpower(dataset.X, dataset.sfreq, (13.0, 30.0))
    covariance = spatial_covariance(dataset.X)
    reference = config["evaluation"]["reference_session"]
    reference_mask = dataset.sessions == reference
    if not reference_mask.any() or reference_mask.all():
        raise ValueError("Configuration must define both reference and held-out sessions")
    pca = fit_pca(mu[reference_mask], n_components=3, random_state=seed)
    heldout_projection = pca.transform(mu[~reference_mask])
    drift = covariance_distance(
        covariance[reference_mask].mean(axis=0), covariance[~reference_mask].mean(axis=0)
    )
    decoder = make_csp_lda(n_components=config["decoder"]["n_components"], random_state=seed)
    result = evaluate_fixed_decoder(
        filtered,
        decoder,
        seed=seed,
        repository=repository,
        config=config,
        **config["evaluation"],
    )
    expected_records = config["data"]["n_subjects"] * len(
        config["evaluation"]["evaluation_sessions"]
    )
    if len(result["per_subject_session"]) != expected_records:
        raise RuntimeError("Not all configured subject/session evaluations executed")
    for values in (spectrum, psd, mu, beta, covariance, heldout_projection):
        if not np.isfinite(values).all():
            raise RuntimeError("Pipeline produced nonfinite diagnostics")
    result["software_validation_only"] = True
    result["subject_bootstrap"] = bootstrap_subject_mean(
        result["subject_balanced_accuracy"],
        n_resamples=1000,
        seed=seed,
    )
    result["signal_geometry_checks"] = {
        "input_shape": list(dataset.X.shape),
        "fft_bins": len(frequencies),
        "welch_bins": len(psd_frequencies),
        "mu_shape": list(mu.shape),
        "beta_shape": list(beta.shape),
        "covariance_shape": list(covariance.shape),
        "heldout_pca_shape": list(heldout_projection.shape),
        "covariance_distance": drift,
        "all_finite": True,
        "pca_fit_partition": "reference_session_only",
        "diagnostic_scope": "pooled synthetic software fixture; not a study analysis",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/smoke.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%dT%H%M%S%f+0800")
    output = args.output or Path("results") / "smoke" / stamp / "report.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite previous experiment: {output}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = run(config, Path(__file__).resolve().parents[1])
    write_result_json(output, result)
    print(
        json.dumps(
            {
                "status": "software_validation_passed",
                "synthetic": True,
                "subject_session_evaluations": len(result["per_subject_session"]),
                "report": str(output),
                "scientific_result_claimed": False,
            }
        )
    )


if __name__ == "__main__":
    main()
