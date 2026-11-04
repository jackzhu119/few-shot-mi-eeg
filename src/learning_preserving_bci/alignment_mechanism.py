"""Fixed four-arm covariance-information sensitivity for Paper2.

All learned quantities use source TRAIN/current support. Query arrays are accepted
only by the returned decoder's read-only prediction methods. The Kumar path uses
one fixed orthonormal CAR coordinate system for every arm; the BNCI path retains
the original NumPy comparator's covariance and LDA estimators.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

METHODS = ("full", "rms_full", "diagonal_ea", "ea")


def helmert(channels: int) -> np.ndarray:
    if channels < 2:
        raise ValueError("At least two channels required")
    result = np.zeros((channels - 1, channels), dtype=np.float64)
    for row in range(channels - 1):
        denominator = np.sqrt((row + 1) * (row + 2))
        result[row, :row + 1] = 1 / denominator
        result[row, row + 1] = -(row + 1) / denominator
    return result


def epochs(value: np.ndarray) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if (result.ndim != 3 or min(result.shape) < 1 or result.shape[1] < 2
            or result.shape[2] < 2 or not np.isfinite(result).all()):
        raise ValueError("Expected nonempty finite N,C,T epochs")
    return result


def project(value: np.ndarray, basis: np.ndarray) -> np.ndarray:
    value = epochs(value)
    if value.shape[1] != basis.shape[1]:
        raise ValueError("Channel/basis mismatch")
    return np.einsum("kc,nct->nkt", basis, value)


def common_rms(value: np.ndarray) -> np.ndarray:
    """One scalar per complete trial, not channel-wise normalization."""
    value = epochs(value)
    scale = np.sqrt(np.square(value).mean(axis=(1, 2)))
    if np.any(scale <= 0) or not np.isfinite(scale).all():
        raise ValueError("Zero/nonfinite RMS trial")
    return value / scale[:, None, None]


def reference(value: np.ndarray, shrinkage: float = 0.0, *, diagonal=False) -> tuple[np.ndarray, np.ndarray, dict]:
    value = epochs(value)
    if not 0 <= shrinkage < 1:
        raise ValueError("Reference shrinkage outside [0,1)")
    centered = value - value.mean(axis=-1, keepdims=True)
    covariance = np.einsum("nct,ndt->ncd", centered, centered) / (value.shape[-1] - 1)
    matrix = covariance.mean(axis=0)
    scale = float(np.trace(matrix) / len(matrix))
    matrix = (1 - shrinkage) * matrix + shrinkage * scale * np.eye(len(matrix))
    if diagonal:
        matrix = np.diag(np.diag(matrix))
    matrix = (matrix + matrix.T) * 0.5
    values, vectors = np.linalg.eigh(matrix)
    if (not np.isfinite(values).all() or values[0] <= 0
            or values[-1] / values[0] > 1e12):
        raise ValueError("Nonpositive reference or condition number above 1e12")
    inverse = (vectors * values ** -0.5) @ vectors.T
    return matrix, inverse, {
        "eigenvalues": values.tolist(), "condition_number": float(values[-1] / values[0]),
        "dimension": len(matrix), "n_reference_trials": len(value),
        "shrinkage": float(shrinkage), "diagonal_in_fixed_effective_coordinates": bool(diagonal),
    }


def numeric_digest(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(arrays.items()):
        value = np.ascontiguousarray(value)
        if value.dtype.hasobject or not np.isfinite(value).all():
            raise ValueError("Invalid model state array")
        digest.update(json.dumps([name, value.dtype.str, list(value.shape)], separators=(",", ":")).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


@dataclass
class MechanismDecoder:
    basis: np.ndarray
    target_transform: np.ndarray
    use_rms: bool
    core: object
    dataset: str
    metadata: dict

    def _features_input(self, query: np.ndarray) -> np.ndarray:
        value = project(query, self.basis)
        if self.use_rms:
            value = common_rms(value)
        return np.einsum("cd,ndt->nct", self.target_transform, value)

    def predict(self, query: np.ndarray) -> np.ndarray:
        return self.core.predict(self._features_input(query))

    def predict_probability(self, query: np.ndarray) -> np.ndarray:
        value = self._features_input(query)
        if self.dataset == "kumar":
            probability = self.core.predict_proba(value)
            classes = self.core.named_steps["lda"].classes_
        else:
            from experiments.hpc_recalibration_v2.hpc_recalibration.classical import log_variance
            features = log_variance(value, self.core.filters)
            logits = features @ self.core.weights.T + self.core.bias
            logits -= logits.max(axis=1, keepdims=True)
            probability = np.exp(logits)
            probability /= probability.sum(axis=1, keepdims=True)
            classes = self.core.classes
        if not np.array_equal(classes, [0, 1]) or not np.isfinite(probability).all():
            raise ValueError("Unexpected probability class order or nonfinite values")
        return probability[:, 1]

    def state_arrays(self) -> dict[str, np.ndarray]:
        result = {"basis": self.basis, "target_transform": self.target_transform,
                  "use_rms": np.asarray(self.use_rms, dtype=np.int8)}
        if self.dataset == "kumar":
            for prefix, obj, fields in [
                ("csp", self.core.named_steps["csp"], ("filters_", "patterns_", "mean_", "std_")),
                ("lda", self.core.named_steps["lda"], ("classes_", "coef_", "intercept_", "means_", "priors_", "covariance_")),
            ]:
                for field in fields:
                    result[prefix + "_" + field.rstrip("_")] = np.asarray(getattr(obj, field))
        else:
            for field in ["filters", "weights", "bias", "classes", "query_whitener"]:
                result["core_" + field] = np.asarray(getattr(self.core, field))
        return result


def fit_mechanism(source_x, source_y, support_x, support_y, method: str, dataset: str) -> MechanismDecoder:
    """Exactly one fitted arm; no query signal, query labels, or tuning input."""
    if method not in METHODS or dataset not in {"kumar", "bnci"}:
        raise ValueError("Unknown fixed dataset/method")
    source_x, support_x = epochs(source_x), epochs(support_x)
    source_y, support_y = np.asarray(source_y), np.asarray(support_y)
    if source_x.shape[1:] != support_x.shape[1:]:
        raise ValueError("Source/support epoch shape mismatch")
    if (source_y.shape != (len(source_x),) or support_y.shape != (len(support_x),)
            or not np.isin(support_y, [0, 1]).all()
            or not np.array_equal(np.unique(source_y), [0, 1])
            or min(np.sum(source_y == c) for c in [0, 1]) < 2):
        raise ValueError("Binary source classes need >=2 each; support labels must be binary")
    basis = helmert(source_x.shape[1]) if dataset == "kumar" else np.eye(source_x.shape[1])
    source, support = project(source_x, basis), project(support_x, basis)
    source_transform = np.eye(len(basis))
    target_transform = np.eye(len(basis))
    diagnostics = {}
    if method == "rms_full":
        source, support = common_rms(source), common_rms(support)
    if method in {"diagonal_ea", "ea"}:
        shrinkage = 0.0 if dataset == "kumar" else 0.1
        for name, value in [("source", source), ("support", support)]:
            _, inverse, info = reference(value, shrinkage, diagonal=method == "diagonal_ea")
            diagnostics[name] = info
            if name == "source":
                source_transform = inverse
            else:
                target_transform = inverse
        source = np.einsum("cd,ndt->nct", source_transform, source)
        support = np.einsum("cd,ndt->nct", target_transform, support)
    if dataset == "kumar":
        from mne.decoding import CSP
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.pipeline import Pipeline
        core = Pipeline([
            ("csp", CSP(n_components=4, reg="ledoit_wolf", log=True, norm_trace=False,
                        transform_into="average_power", rank="full")),
            ("lda", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ])
        core.fit(np.concatenate([source, support]), np.concatenate([source_y, support_y]))
    else:
        from experiments.hpc_recalibration_v2.hpc_recalibration.classical import fit_decoder
        from experiments.hpc_recalibration_v2.hpc_recalibration.data import Split
        def split(x, y, role):
            return Split(x, y, np.asarray([f"{role}:{i}" for i in range(len(y))]),
                         np.asarray([role] * len(y)))
        core = fit_decoder(split(source, source_y, "source"), split(support, support_y, "support"),
                           "full_csp", {"classical": {"n_components": 4,
                           "covariance_shrinkage": 0.1, "lda_shrinkage": 0.1}})
    metadata = {"dataset": dataset, "method": method, "n_source": len(source), "n_support": len(support),
                "effective_dimension": len(basis), "query_used_for_fitting": False,
                "reference_diagnostics": diagnostics, "probability_classes": [0, 1],
                "probability_class_1": "right_hand", "fixed_full_support_only": True,
                "scope": "new_coordinate_matched_mechanism_sensitivity"}
    return MechanismDecoder(basis, target_transform, method == "rms_full", core, dataset, metadata)


def score(y, prediction, p_right=None) -> dict:
    y, prediction = np.asarray(y), np.asarray(prediction)
    if y.shape != prediction.shape or y.ndim != 1 or not np.isin(y, [0, 1]).all() or not np.isin(prediction, [0, 1]).all():
        raise ValueError("Binary aligned predictions required")
    counts = [int(np.sum(y == c)) for c in [0, 1]]
    recall = [float(np.mean(prediction[y == c] == c)) if counts[c] else None for c in [0, 1]]
    result = {"n_query": len(y), "n_left": counts[0], "n_right": counts[1],
              "recall_left": recall[0], "recall_right": recall[1],
              "balanced_accuracy": None if None in recall else sum(recall) / 2,
              "weak_recall": None if None in recall else min(recall),
              "recall_gap": None if None in recall else abs(recall[0] - recall[1]),
              "status": "undefined_missing_query_class" if None in recall else "ok"}
    if p_right is not None:
        p_right = np.asarray(p_right, dtype=np.float64)
        if p_right.shape != y.shape or not np.isfinite(p_right).all() or np.any((p_right < 0) | (p_right > 1)):
            raise ValueError("Actual aligned probabilities in [0,1] required")
        p = np.clip(p_right, 1e-7, 1 - 1e-7)
        nll = -(y * np.log(p) + (1 - y) * np.log1p(-p))
        brier = np.square(p_right - y)
        result.update(balanced_nll=None if not all(counts) else float(np.mean([nll[y == c].mean() for c in [0, 1]])),
                      balanced_brier_single_coordinate=None if not all(counts) else float(np.mean([brier[y == c].mean() for c in [0, 1]])),
                      nll_clip=1e-7, brier_definition="single_coordinate_binary_class_balanced")
    return result
