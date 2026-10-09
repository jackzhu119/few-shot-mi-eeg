"""Tests for geometry conventions, invariance, and training-only PCA."""

import numpy as np
import pytest

from learning_preserving_bci.neural_geometry import (
    covariance_distance,
    fit_pca,
    subspace_distance,
)


def test_pca_fits_only_supplied_training_data():
    train = np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]])
    original = train.copy()
    held_out = np.array([[1000.0, -500.0], [2000.0, -1000.0]])
    model = fit_pca(train, n_components=1)
    expected_mean = train.mean(axis=0)
    np.testing.assert_allclose(model.mean_, expected_mean)
    components_before = model.components_.copy()
    assert model.transform(held_out).shape == (2, 1)
    np.testing.assert_array_equal(model.mean_, expected_mean)
    np.testing.assert_array_equal(model.components_, components_before)
    np.testing.assert_array_equal(train, original)
    assert model.n_samples_ == len(train)


def test_pca_variance_target():
    train = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    assert fit_pca(train, n_components=0.95).n_components_ == 1


@pytest.mark.parametrize(
    "values,components",
    [
        ([1, 2, 3], None),
        ([[1, 2]], None),
        ([[1, np.nan], [2, 3]], None),
        ([[1, 2], [2, 3]], 0),
        ([[1, 2], [2, 3]], 3),
        ([[1, 2], [2, 3]], True),
        ([[1, 2], [2, 3]], 1.0),
    ],
)
def test_pca_invalid_input(values, components):
    with pytest.raises(ValueError):
        fit_pca(values, components)


def test_subspace_distance_basis_invariance():
    basis = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    transformed_basis = np.array([[2.0, 3.0], [-1.0, 4.0]]) @ basis
    assert subspace_distance(basis, transformed_basis) == pytest.approx(0, abs=1e-12)
    assert subspace_distance([[1, 0]], [[0, 1]]) == pytest.approx(1)
    assert subspace_distance([[1, 0]], [[1, 1]]) == pytest.approx(np.sqrt(0.5))


def test_subspace_distance_common_rotation_and_different_dimensions():
    first = np.array([[1.0, 0.0, 0.0]])
    second = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    rotation, _ = np.linalg.qr(np.random.default_rng(11).normal(size=(3, 3)))
    distance = subspace_distance(first, second)
    assert distance == pytest.approx(np.sqrt(1 / 3))
    assert subspace_distance(first @ rotation, second @ rotation) == pytest.approx(distance)
    assert subspace_distance(second, first) == pytest.approx(distance)


@pytest.mark.parametrize(
    "first,second",
    [
        ([[1, 0]], [[1, 0, 0]]),
        ([[1, 0], [2, 0]], [[1, 0]]),
        ([[0, 0]], [[1, 0]]),
        ([[np.inf, 0]], [[1, 0]]),
        ([], [[1, 0]]),
    ],
)
def test_subspace_invalid_input(first, second):
    with pytest.raises(ValueError):
        subspace_distance(first, second)


@pytest.mark.parametrize("metric", ["riemannian", "logeuclidean", "frobenius"])
def test_covariance_distance_identity_symmetry_and_rotation(metric):
    first = np.array([[2.0, 0.5], [0.5, 1.0]])
    second = np.array([[3.0, -0.2], [-0.2, 2.0]])
    rotation, _ = np.linalg.qr(np.random.default_rng(4).normal(size=(2, 2)))
    distance = covariance_distance(first, second, metric)
    assert distance > 0
    assert covariance_distance(first, first, metric) == pytest.approx(0, abs=1e-12)
    assert covariance_distance(second, first, metric) == pytest.approx(distance)
    assert covariance_distance(
        rotation @ first @ rotation.T, rotation @ second @ rotation.T, metric
    ) == pytest.approx(distance)


@pytest.mark.parametrize("metric", ["riemannian", "logeuclidean"])
def test_covariance_diagonal_closed_form(metric):
    assert covariance_distance(
        np.eye(2), np.diag([2.0, 4.0]), metric, regularization=0
    ) == pytest.approx(np.linalg.norm(np.log([2.0, 4.0])))


def test_riemannian_distance_affine_invariance_without_regularization():
    first = np.array([[2.0, 0.5], [0.5, 1.0]])
    second = np.array([[3.0, -0.2], [-0.2, 2.0]])
    transform = np.array([[2.0, 1.0], [0.0, 0.5]])
    expected = covariance_distance(first, second, regularization=0)
    actual = covariance_distance(
        transform @ first @ transform.T, transform @ second @ transform.T, regularization=0
    )
    assert actual == pytest.approx(expected)


def test_covariance_singular_regularization_and_input_preservation():
    first = np.diag([1.0, 0.0])
    original = first.copy()
    assert np.isfinite(covariance_distance(first, np.eye(2)))
    np.testing.assert_array_equal(first, original)
    with pytest.raises(ValueError, match="positive definite"):
        covariance_distance(first, np.eye(2), regularization=0)


@pytest.mark.parametrize(
    "first,second,kwargs",
    [
        (np.ones((2, 3)), np.eye(2), {}),
        (np.eye(3), np.eye(2), {}),
        ([[1.0, 1.0], [0.0, 1.0]], np.eye(2), {}),
        (np.diag([1.0, -1.0]), np.eye(2), {}),
        ([[np.nan, 0], [0, 1]], np.eye(2), {}),
        (np.eye(2), np.eye(2), {"metric": "unknown"}),
        (np.eye(2), np.eye(2), {"regularization": -1}),
        (np.eye(2), np.eye(2), {"regularization": np.inf}),
    ],
)
def test_covariance_invalid_input(first, second, kwargs):
    with pytest.raises(ValueError):
        covariance_distance(first, second, **kwargs)
