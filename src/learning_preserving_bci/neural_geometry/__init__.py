"""Training-only PCA and distances between neural representations.

Samples are rows for :func:`fit_pca`. Subspace bases use a separate convention:
each row is an axis in a common feature space. Fit PCA on the training split,
then call the returned estimator's ``transform`` on held-out samples.
"""

from __future__ import annotations

from numbers import Integral, Real

import numpy as np
from scipy.linalg import eigh, orth, subspace_angles
from sklearn.decomposition import PCA

__all__ = ["fit_pca", "subspace_distance", "covariance_distance"]


def _finite_matrix(value: object, name: str) -> np.ndarray:
    """Validate a real, nonempty, finite matrix without mutating input."""
    if np.iscomplexobj(value):
        raise ValueError(f"{name} must be real-valued")
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a numeric matrix") from exc
    if matrix.ndim != 2 or 0 in matrix.shape:
        raise ValueError(f"{name} must be a nonempty two-dimensional matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must contain only finite values")
    return matrix


def fit_pca(
    X: object,
    n_components: int | float | None = None,
    *,
    whiten: bool = False,
    random_state: int | None = 0,
) -> PCA:
    """Fit PCA to exactly the supplied samples and return its estimator.

    ``X`` has shape ``(n_samples, n_features)`` and needs at least two samples.
    An integer selects a component count; a float strictly between zero and
    one selects a cumulative explained-variance target. ``None`` retains all
    available components. The full SVD makes the fit deterministic. This
    function neither merges datasets nor refits during held-out transforms.
    """
    matrix = _finite_matrix(X, "X")
    if matrix.shape[0] < 2:
        raise ValueError("PCA requires at least two samples")
    if n_components is not None:
        if isinstance(n_components, bool) or not isinstance(n_components, Real):
            raise ValueError("n_components must be an integer, variance fraction, or None")
        if isinstance(n_components, Integral):
            if not 1 <= n_components <= min(matrix.shape):
                raise ValueError("n_components must be between 1 and min(X.shape)")
        elif not 0 < n_components < 1:
            raise ValueError("a fractional n_components must be strictly between 0 and 1")
    model = PCA(
        n_components=n_components,
        whiten=whiten,
        svd_solver="full",
        random_state=random_state,
        copy=True,
    )
    return model.fit(matrix)


def subspace_distance(basis_a: object, basis_b: object) -> float:
    """Return the normalized projection distance between two subspaces.

    Inputs have shape ``(n_axes, n_features)``: **rows are basis axes**, and
    the feature coordinates must match. Any full-row-rank basis is accepted;
    internal orthonormalization makes scale and within-subspace rotations
    irrelevant. If the ranks are ``r`` and ``s`` and principal angles are
    ``theta``, the distance is

    ``sqrt((2 * sum(sin(theta)**2) + abs(r - s)) / (r + s))``.

    This is zero for the same subspace and one for orthogonal subspaces.
    Unmatched dimensions contribute to distance, so nested subspaces of
    unequal dimension do not incorrectly have zero distance. No alignment
    or feature rescaling is learned from either input.
    """
    a = _finite_matrix(basis_a, "basis_a")
    b = _finite_matrix(basis_b, "basis_b")
    if a.shape[1] != b.shape[1]:
        raise ValueError("bases must use the same number of features")
    qa, qb = orth(a.T), orth(b.T)
    if qa.shape[1] != a.shape[0] or qb.shape[1] != b.shape[0]:
        raise ValueError("each basis must have linearly independent rows")
    angles = subspace_angles(qa, qb)
    r, s = qa.shape[1], qb.shape[1]
    squared_distance = (2 * np.sum(np.sin(angles) ** 2) + abs(r - s)) / (r + s)
    return float(np.sqrt(np.clip(squared_distance, 0.0, 1.0)))


def _regularized_covariance(value: object, name: str, regularization: float) -> np.ndarray:
    matrix = _finite_matrix(value, name)
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"{name} must be square")
    if not np.allclose(matrix, matrix.T, rtol=1e-7, atol=1e-10):
        raise ValueError(f"{name} must be symmetric")
    symmetric = (matrix + matrix.T) / 2
    eigenvalues = eigh(symmetric, eigvals_only=True)
    tolerance = 1e-10 * max(1.0, float(np.max(np.abs(eigenvalues))))
    if eigenvalues[0] < -tolerance:
        raise ValueError(f"{name} must be positive semidefinite")
    regularized = symmetric + regularization * np.eye(matrix.shape[0])
    if eigh(regularized, eigvals_only=True)[0] <= 0:
        raise ValueError(f"{name} must be positive definite after regularization")
    return regularized


def _symmetric_log(matrix: np.ndarray) -> np.ndarray:
    eigenvalues, eigenvectors = eigh(matrix)
    return (eigenvectors * np.log(eigenvalues)) @ eigenvectors.T


def covariance_distance(
    A: object,
    B: object,
    metric: str = "riemannian",
    regularization: float = 1e-8,
) -> float:
    """Measure distance between covariance matrices in a common feature space.

    ``metric='riemannian'`` uses the affine-invariant SPD distance, the
    Euclidean norm of log generalized eigenvalues. ``'logeuclidean'`` uses
    the Frobenius norm of the difference of symmetric matrix logarithms;
    ``'frobenius'`` uses the Frobenius norm of the covariance difference.

    Inputs must be finite, symmetric, positive semidefinite square matrices
    of equal shape. ``regularization`` adds that nonnegative scalar to both
    diagonals before comparison; the resulting matrices must be positive
    definite. Set it to zero for the exact affine-invariant distance between
    already-SPD inputs. Regularization is fixed, not estimated from test data.
    """
    if metric not in {"riemannian", "logeuclidean", "frobenius"}:
        raise ValueError("metric must be 'riemannian', 'logeuclidean', or 'frobenius'")
    if (
        isinstance(regularization, bool)
        or not isinstance(regularization, Real)
        or not np.isfinite(regularization)
        or regularization < 0
    ):
        raise ValueError("regularization must be a finite nonnegative scalar")
    a = _regularized_covariance(A, "A", float(regularization))
    b = _regularized_covariance(B, "B", float(regularization))
    if a.shape != b.shape:
        raise ValueError("covariances must have the same shape")
    if metric == "riemannian":
        eigenvalues = eigh(a, b, eigvals_only=True)
        if not np.all(np.isfinite(eigenvalues)) or np.any(eigenvalues <= 0):
            raise ValueError("generalized covariance eigenvalues must be finite and positive")
        return float(np.linalg.norm(np.log(eigenvalues)))
    if metric == "logeuclidean":
        return float(np.linalg.norm(_symmetric_log(a) - _symmetric_log(b), ord="fro"))
    return float(np.linalg.norm(a - b, ord="fro"))
