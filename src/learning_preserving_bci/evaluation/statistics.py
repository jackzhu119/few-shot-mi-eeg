"""Inference uses subjects as the independent unit, never pooled trials."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

import numpy as np


def _subject_values(scores: Mapping) -> tuple[list, np.ndarray]:
    if not isinstance(scores, Mapping):
        raise TypeError("Supply a mapping with one aggregated score per independent subject")
    if len({str(subject) for subject in scores}) != len(scores):
        raise ValueError("Subject identifiers are ambiguous when converted to JSON keys")
    subjects = sorted(scores, key=str)
    values = np.asarray([scores[subject] for subject in subjects], dtype=float)
    if len(subjects) < 2 or values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("At least two finite subject-level scalar scores are required")
    return subjects, values


def _settings(confidence, n_resamples):
    if not 0 < confidence < 1 or n_resamples < 1:
        raise ValueError("confidence must be in (0, 1) and n_resamples positive")


def bootstrap_subject_mean(
    subject_scores: Mapping,
    confidence: float = 0.95,
    n_resamples: int = 10000,
    seed: int = 42,
) -> dict:
    """Percentile CI from resampling independent subjects with replacement."""
    subjects, values = _subject_values(subject_scores)
    _settings(confidence, n_resamples)
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), size=(n_resamples, len(values)))].mean(axis=1)
    alpha = (1 - confidence) / 2
    low, high = np.quantile(means, [alpha, 1 - alpha])
    return {
        "unit": "subject",
        "n_subjects": len(subjects),
        "mean": float(values.mean()),
        "confidence": confidence,
        "confidence_interval": [float(low), float(high)],
        "interval_method": "subject_percentile_bootstrap",
        "n_resamples": n_resamples,
        "seed": seed,
    }


def paired_subject_statistics(
    scores_a: Mapping,
    scores_b: Mapping,
    confidence: float = 0.95,
    n_resamples: int = 10000,
    n_permutations: int = 10000,
    seed: int = 42,
) -> dict:
    """Paired mean difference, sign-flip test, and paired subject-bootstrap CI.

    The sign-flip null requires exchangeable method labels within subjects.
    Independent subjects, predeclared comparisons and representative sampling
    are assumptions, not established by this function. Small-cohort intervals
    are descriptive and can be unstable. Repeated trials or seeds must first be
    aggregated within each subject, not supplied as extra independent subjects.
    """
    subjects, values_a = _subject_values(scores_a)
    if not isinstance(scores_b, Mapping) or set(subjects) != set(scores_b):
        raise ValueError("Paired comparisons require exactly matching subject identifiers")
    _subject_values(scores_b)
    # Retrieve each paired score by identity, not by an independently sorted
    # mapping: the input insertion order must never influence pairing.
    values_b = np.asarray([scores_b[subject] for subject in subjects], dtype=float)
    _settings(confidence, n_resamples)
    if n_permutations < 1:
        raise ValueError("n_permutations must be positive")
    differences = values_a - values_b
    observed = float(differences.mean())
    rng = np.random.default_rng(seed)
    if len(subjects) <= 16:
        flips = np.asarray(list(product((-1.0, 1.0), repeat=len(subjects))))
        null = (flips * differences).mean(axis=1)
        p_value = float(np.mean(np.abs(null) >= abs(observed) - 1e-12))
        method = "exact_paired_subject_sign_flip"
        n_tested = len(null)
    else:
        signs = rng.choice((-1.0, 1.0), size=(n_permutations, len(subjects)))
        null = (signs * differences).mean(axis=1)
        p_value = float(
            (1 + np.count_nonzero(np.abs(null) >= abs(observed) - 1e-12)) / (1 + len(null))
        )
        method = "monte_carlo_paired_subject_sign_flip_plus_one"
        n_tested = len(null)
    intervals = bootstrap_subject_mean(
        dict(zip(subjects, differences)), confidence, n_resamples, seed
    )
    return {
        "unit": "subject",
        "n_subjects": len(subjects),
        "subjects": [str(subject) for subject in subjects],
        "mean_difference_a_minus_b": observed,
        "confidence": confidence,
        "confidence_interval": intervals["confidence_interval"],
        "interval_method": intervals["interval_method"],
        "p_value_two_sided": p_value,
        "permutation_method": method,
        "n_permutations_tested": n_tested,
        "n_bootstrap_resamples": n_resamples,
        "seed": seed,
        "assumptions": "Independent subjects; paired exchangeability; predeclared comparison.",
    }
