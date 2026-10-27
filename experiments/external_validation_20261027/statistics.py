"""Fixed participant-level analysis for the external four-arm replication.

Balanced accuracy enters as a proportion. Effect estimates and confidence
intervals leave as percentage points. Incomplete cohorts have descriptive
records only; they never inherit the complete-cohort inferential label.
"""

from __future__ import annotations

import itertools
import math

import numpy as np


METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
CONTRASTS = (
    ("full_csp_minus_lda_only", "full_csp", "lda_only", "primary"),
    ("full_csp_minus_frozen", "full_csp", "frozen", "secondary"),
    ("lda_only_minus_frozen", "lda_only", "frozen", "secondary"),
    ("ea_csp_minus_full_csp", "ea_csp", "full_csp", "secondary"),
)


def exact_sign_flip(differences: np.ndarray) -> dict:
    """Enumerate the sign-symmetric null with observed magnitudes retained."""
    values = np.asarray(differences, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("sign-flip differences must be a nonempty finite vector")
    if len(values) > 20:
        raise ValueError("exact enumeration is bounded to 20 participants")
    observed = abs(float(np.mean(values)))
    extreme = sum(
        abs(float(np.mean(values * signs))) >= observed - 1e-12
        for signs in itertools.product((-1.0, 1.0), repeat=len(values))
    )
    return {
        "p_value": extreme / (2 ** len(values)),
        "extreme_assignments": extreme,
        "total_assignments": 2 ** len(values),
        "alternative": "two_sided_absolute_mean",
        "inclusive_tolerance_balanced_accuracy": 1e-12,
        "observed_magnitudes_retained": True,
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    """Return monotone Holm adjusted p-values in the input order."""
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in p_values):
        raise ValueError("p values must be finite probabilities")
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, index in enumerate(order):
        previous = max(previous, (len(p_values) - rank) * p_values[index])
        adjusted[index] = min(1.0, previous)
    return adjusted


def summarize(
    records: list[dict],
    expected_participants: tuple[str, ...] = tuple(str(i) for i in range(1, 10)),
    bootstrap_repetitions: int = 10000,
    seed: int = 20261027,
) -> dict:
    """Analyze the fixed target-session endpoint, preserving missingness.

    The input has one row per participant and method, for one target session.
    Extra or duplicate identities are errors. Null BA, empty query or an
    explicitly missing query class keep that participant incomplete.
    """
    participants = tuple(str(value) for value in expected_participants)
    if not participants or len(participants) != len(set(participants)):
        raise ValueError("expected participant identities must be nonempty and unique")
    if len(participants) > 20:
        raise ValueError("exact enumeration is bounded to 20 participants")
    if isinstance(bootstrap_repetitions, bool) or bootstrap_repetitions < 1:
        raise ValueError("bootstrap_repetitions must be positive")
    if int(bootstrap_repetitions) != bootstrap_repetitions:
        raise ValueError("bootstrap_repetitions must be an integer")

    indexed, sessions, invalid = {}, {}, []
    for row in records:
        participant = str(row["participant"])
        method = str(row["method"])
        session = str(row["session"])
        if participant not in participants or method not in METHODS:
            raise ValueError("record identity is outside the frozen cohort or methods")
        key = (participant, method)
        if key in indexed:
            raise ValueError("duplicate participant/method endpoint")
        if not session or (participant in sessions and sessions[participant] != session):
            raise ValueError("all methods must evaluate the same target session")
        sessions[participant] = session
        indexed[key] = dict(row)
        value = row.get("balanced_accuracy")
        n_query = row.get("n_query")
        reasons = []
        if value is None or not isinstance(value, (float, int, np.number)):
            reasons.append("balanced_accuracy_missing_or_nonnumeric")
        elif not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
            reasons.append("balanced_accuracy_not_finite_probability")
        if isinstance(n_query, bool) or not isinstance(n_query, (int, np.integer)) or n_query < 1:
            reasons.append("query_count_missing_or_empty")
        counts = row.get("class_counts")
        if counts is not None:
            values = list(counts.values()) if isinstance(counts, dict) else list(counts)
            if len(values) != 2 or any(int(count) <= 0 for count in values):
                reasons.append("missing_query_class")
            elif isinstance(n_query, (int, np.integer)) and sum(values) != n_query:
                reasons.append("class_counts_do_not_sum_to_query_count")
        if reasons:
            invalid.append({"participant": participant, "method": method, "reasons": reasons})

    missing = [
        {"participant": participant, "method": method}
        for participant in participants for method in METHODS
        if (participant, method) not in indexed
    ]
    invalid_keys = {(row["participant"], row["method"]) for row in invalid}
    complete = [
        participant for participant in participants
        if all((participant, method) in indexed and (participant, method) not in invalid_keys
               for method in METHODS)
    ]
    # Equal query counts are necessary for the intended matched-trial contrast;
    # the runner independently verifies the actual query trial IDs.
    for participant in complete[:]:
        counts = {int(indexed[(participant, method)]["n_query"]) for method in METHODS}
        if len(counts) != 1:
            complete.remove(participant)
            invalid.append({"participant": participant, "method": "all",
                            "reasons": ["methods_have_different_query_counts"]})

    result = {
        "status": "complete" if not missing and not invalid else "partial",
        "independent_unit": "participant",
        "expected_participants": list(participants),
        "complete_participants": complete,
        "missing_cells": missing,
        "invalid_records": invalid,
        "participant_results": [indexed[(participant, method)] for participant in participants
                                for method in METHODS if (participant, method) in indexed],
        "cohort_balanced_accuracy": {},
        "contrasts": {},
        "analysis": {
            "effect_unit": "percentage_points",
            "input_balanced_accuracy_unit": "proportion",
            "bootstrap_repetitions": int(bootstrap_repetitions),
            "bootstrap_seed": int(seed),
            "bootstrap_resampling_unit": "paired_participant",
            "bootstrap_interval": "pointwise_percentile_95_percent",
            "participant_order": list(participants),
            "primary_test": "two_sided_exact_sign_flip_full_csp_minus_lda_only",
            "primary_multiplicity": "single_fixed_primary_contrast",
            "secondary_family": [name for name, _, _, role in CONTRASTS if role == "secondary"],
            "secondary_multiplicity": "Holm_three_secondary_contrasts",
            "inference_requires_complete_expected_cohort": True,
        },
    }
    if result["status"] != "complete":
        return result

    values = {
        method: np.asarray([indexed[(participant, method)]["balanced_accuracy"]
                            for participant in participants], dtype=float)
        for method in METHODS
    }
    result["cohort_balanced_accuracy"] = {
        method: {"mean": float(np.mean(value)), "mean_percent": float(np.mean(value) * 100),
                 "n_participants": len(participants)}
        for method, value in values.items()
    }
    # Reuse identical participant resampling indices for every paired contrast.
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(participants), size=(int(bootstrap_repetitions), len(participants)))
    for name, newer, reference, role in CONTRASTS:
        difference = values[newer] - values[reference]
        bootstrapped = np.mean(difference[indices], axis=1) * 100
        ci = np.percentile(bootstrapped, [2.5, 97.5])
        exact = exact_sign_flip(difference)
        loo = ([float(np.mean(np.delete(difference, index)) * 100)
                for index in range(len(participants))] if len(participants) > 1 else [])
        result["contrasts"][name] = {
            "role": role,
            "mean_difference_pp": float(np.mean(difference) * 100),
            "bootstrap_ci95_pp": ci.tolist(),
            "p_exact_sign_flip": exact["p_value"],
            "exact_sign_flip": exact,
            "p_holm_secondary": None,
            "n_participants": len(participants),
            "participant_differences_pp": dict(zip(participants, (difference * 100).tolist())),
            "positive_participants": int(np.sum(difference > 0)),
            "negative_participants": int(np.sum(difference < 0)),
            "zero_participants": int(np.sum(difference == 0)),
            "leave_one_out_mean_pp": dict(zip(participants, loo)) if loo else {},
            "leave_one_out_mean_range_pp": [min(loo), max(loo)] if loo else None,
        }
    secondary = [name for name, _, _, role in CONTRASTS if role == "secondary"]
    adjusted = holm_adjust([result["contrasts"][name]["p_exact_sign_flip"] for name in secondary])
    for name, p_value in zip(secondary, adjusted):
        result["contrasts"][name]["p_holm_secondary"] = p_value
    return result
