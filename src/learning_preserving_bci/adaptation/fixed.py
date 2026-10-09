"""A fixed policy and parameter-distance diagnostic for future experiments."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

import numpy as np


class FixedDecoderPolicy:
    """Freeze a private copy of a fitted decoder; evaluation has no update API.

    Keeping a baseline fixed provides a fixed-reference decoding diagnostic.
    It does not model user learning or establish an adaptation algorithm.
    """

    def __init__(self, fitted_decoder):
        self._decoder = deepcopy(fitted_decoder)

    def predict(self, X):
        return self._decoder.predict(X)

    def predict_proba(self, X):
        return self._decoder.predict_proba(X)


def parameter_distance(reference: Mapping, candidate: Mapping) -> dict:
    """Return relative L2 weight distance as a diagnostic, not a loss bound.

    Supply matching named numeric arrays or Torch state dictionaries. Ignore
    non-floating integer counters such as batch-normalization update counts.
    Geometry of weights does not prove accuracy retention or user benefit.
    """
    if set(reference) != set(candidate):
        raise ValueError("Parameter dictionaries must have identical keys")
    squared_change = 0.0
    squared_reference = 0.0
    n_parameters = 0
    for key in reference:
        first, second = reference[key], candidate[key]
        if hasattr(first, "detach"):
            first = first.detach().cpu().numpy()
        if hasattr(second, "detach"):
            second = second.detach().cpu().numpy()
        first, second = np.asarray(first), np.asarray(second)
        if first.shape != second.shape:
            raise ValueError(f"Parameter shape mismatch for {key}")
        if first.dtype.kind not in "fc" or second.dtype.kind not in "fc":
            continue
        if not np.isfinite(first).all() or not np.isfinite(second).all():
            raise ValueError(f"Nonfinite parameters for {key}")
        delta = second.astype(np.complex128) - first.astype(np.complex128)
        squared_change += float(np.sum(np.abs(delta) ** 2))
        squared_reference += float(np.sum(np.abs(first.astype(np.complex128)) ** 2))
        n_parameters += first.size
    if not n_parameters:
        raise ValueError("No floating-point parameters to compare")
    absolute = float(np.sqrt(squared_change))
    reference_norm = float(np.sqrt(squared_reference))
    # Relative distance is undefined at a zero reference; keep strict JSON valid.
    relative = absolute / reference_norm if reference_norm else None
    return {
        "l2_distance": absolute,
        "reference_l2_norm": reference_norm,
        "relative_l2_distance": relative,
        "n_parameters": int(n_parameters),
        "interpretation": "Diagnostic only; does not establish retained accuracy or user benefit.",
    }
