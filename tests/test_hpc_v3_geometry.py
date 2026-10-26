"""Synthetic-only Gaussian/tangent checks; no scientific inputs or GPU work."""
from pathlib import Path
import inspect
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v2"))
sys.path.insert(0, str(ROOT / "experiments/hpc_recalibration_v3"))
import geometry  # noqa: E402
from hpc_recalibration.data import Split  # noqa: E402


def split(prefix, n=16, seed=1, labels=None):
    rng = np.random.default_rng(seed)
    labels = np.arange(n) % 2 if labels is None else np.asarray(labels)
    x = rng.normal(size=(n, 4, 64)).astype(np.float32)
    x[labels == 0, 0] *= 2
    x[labels == 1, 1] *= 2
    return Split(x, labels.astype(np.int64), np.array([prefix+str(i) for i in range(n)]),
                 np.array([prefix]*n))


def features(seed=3):
    rng = np.random.default_rng(seed)
    source_y = np.arange(24) % 2
    target_y = np.arange(8) % 2
    source = rng.normal(size=(24, 3))*np.array([.2, 1., 2.]) + source_y[:, None]
    target = rng.normal(size=(8, 3))*np.array([1., .3, .8]) + target_y[:, None] + 6
    return source, source_y, target, target_y


def test_gaussian_update_matches_analytic_coordinate_posterior():
    mean, covariance = geometry.gaussian_update(
        np.array([1., -2.]), np.diag([4., 1.]), np.array([3., 5.]),
        np.eye(2), np.diag([1., 9.]))
    np.testing.assert_allclose(mean, [2.6, -1.3], atol=1e-14)
    np.testing.assert_allclose(covariance, np.diag([.8, .9]), atol=1e-14)


def test_halfcontrast_noise_and_masked_update_preserve_unobserved_class():
    first = np.array([[2., .3], [.3, 1.]])
    second = np.array([[3., .1], [.1, 5.]])
    transform = .5*np.block([[np.eye(2), np.eye(2)], [-np.eye(2), np.eye(2)]])
    class_noise = np.block([[first, np.zeros((2, 2))], [np.zeros((2, 2)), second]])
    joint = geometry._joint_noise([first, second])
    np.testing.assert_allclose(joint, transform @ class_noise @ transform.T)
    source_means = [np.array([1., 2.]), np.array([4., 8.])]
    design = np.concatenate([np.eye(2), -np.eye(2)], axis=1)
    posterior, covariance = geometry.gaussian_update(
        geometry._joint_theta(source_means), joint, np.array([9., 3.]), design, np.eye(2))
    np.testing.assert_allclose(posterior[:2]+posterior[2:], source_means[1], atol=1e-14)
    assert np.linalg.eigvalsh(covariance).min() > 0


def test_finite_source_scalar_plugin_equivalence_and_floor_counterexample():
    # At positive debiased D² the proposed source-noise scalar correction is
    # algebraically V2 again; tests forbid presenting that identity as novelty.
    for squared_distance in (5., 10., 25.):
        source_variance, target_variance = 2., 1.
        difference = max(squared_distance-source_variance-target_variance, 0.)
        corrected = (difference+source_variance)/(difference+source_variance+target_variance)
        old = max(0., 1-target_variance/squared_distance)
        assert corrected == pytest.approx(old)
    squared_distance = .5
    corrected = 2/(2+1)
    old = max(0., 1-1/squared_distance)
    assert corrected == pytest.approx(2/3) and old == 0


@pytest.mark.parametrize("method", geometry.METHODS)
def test_all_methods_finite_spd_probabilities_and_readonly_inputs(method):
    source, support = split("source-"), split("support-", 8, 8)
    before = source.x.copy(), support.x.copy()
    model = geometry.fit(source, support, method, {})
    result = model.predict_probabilities(support.x)
    assert result.shape == (8, 2) and np.isfinite(result).all()
    np.testing.assert_allclose(result.sum(axis=1), 1., atol=1e-15)
    assert (result >= 0).all() and (result <= 1).all()
    for covariance in model.feature_decoder.predictive_covariances:
        assert np.linalg.eigvalsh(covariance).min() > 0
    assert model.metadata["query_used_for_fitting"] is False
    assert model.metadata["class_priors"] == [.5, .5]
    assert set(model.metadata["source_trial_ids"]).isdisjoint(model.metadata["support_trial_ids"])
    np.testing.assert_array_equal(source.x, before[0])
    np.testing.assert_array_equal(support.x, before[1])


@pytest.mark.parametrize("method", geometry.METHODS)
def test_complete_numeric_serialization_without_pickle(tmp_path, method):
    source, support = split("source-"), split("support-", 8, 8)
    model = geometry.fit(source, support, method, {})
    path = tmp_path / "model.npz"
    model.save(path)
    with np.load(path, allow_pickle=False) as values:
        for name in values.files:
            assert values[name].dtype.kind != 'O'
        assert len(values["posterior_packed"]) < model.posterior_covariance.size
    repeated = geometry.Decoder.load(path)
    assert repeated.metadata == model.metadata
    np.testing.assert_array_equal(repeated.posterior_covariance, model.posterior_covariance)
    np.testing.assert_allclose(repeated.predict_probabilities(support.x),
                               model.predict_probabilities(support.x), atol=1e-14, rtol=0)


def test_source_reference_never_uses_support_or_query():
    source = split("source-")
    a = geometry.fit(source, split("support-a-", 8, 8), "eb_predictive", {})
    b = geometry.fit(source, split("support-b-", 8, 44), "eb_predictive", {})
    frozen = geometry.fit(source, None, "source_tangent_frozen", {})
    np.testing.assert_array_equal(a.reference, b.reference)
    np.testing.assert_array_equal(a.reference, frozen.reference)
    assert list(inspect.signature(geometry.fit).parameters) == ['source','support','method','settings']
    assert not any('query' in name for name in inspect.signature(geometry.fit_features).parameters)


@pytest.mark.parametrize("method", [m for m in geometry.METHODS if m.startswith('eb_')])
def test_missing_support_class_is_masked_no_fake_zero_noise_observation(method):
    zs, ys, zt, _ = features()
    model = geometry.fit_features(zs, ys, zt[:3], np.zeros(3, dtype=int), method, {})
    assert model.metadata['support_class_counts'] == [3,0]
    assert model.metadata['target_observation_scope'] == 'observed_class_only_no_domain_shift_estimate'
    assert model.metadata['target_observation_noise']['dimension'] == zs.shape[1]
    assert model.metadata['tau_common_squared'] == model.metadata['tau_halfcontrast_squared'] == 0
    assert any(x['condition']=='domain_shift_not_identifiable' for x in model.metadata['fallback'])
    np.testing.assert_allclose(model.class_means[1], zs[ys == 1].mean(axis=0), atol=1e-12)
    assert np.isfinite(model.predict_probabilities(zt)).all()


def test_one_trial_per_class_uses_source_variance_proxy_not_zero():
    zs, ys, zt, yt = features()
    model = geometry.fit_features(zs, ys, zt[:2], yt[:2], 'eb_predictive', {})
    assert model.metadata['support_class_counts'] == [1,1]
    assert len(model.metadata['fallback']) == 2
    assert all(x['variance_proxy']=='source_class_covariance' for x in model.metadata['fallback'])
    assert model.metadata['target_observation_noise']['minimum_eigenvalue'] > 0


def test_declared_matrix_and_shift_ablations_are_distinct():
    values = features()
    models = {m:geometry.fit_features(*values, m, {}) for m in
              ('eb_point','eb_predictive','eb_isotropic','eb_coupled','eb_no_source_noise','eb_no_shift')}
    np.testing.assert_allclose(models['eb_point'].class_means, models['eb_predictive'].class_means)
    np.testing.assert_allclose(models['eb_point'].posterior_covariance, models['eb_predictive'].posterior_covariance)
    assert not np.allclose(models['eb_isotropic'].class_means, models['eb_point'].class_means)
    assert models['eb_coupled'].metadata['tau_common_squared'] == models['eb_coupled'].metadata['tau_halfcontrast_squared']
    assert models['eb_point'].metadata['tau_common_squared'] != models['eb_point'].metadata['tau_halfcontrast_squared']
    assert models['eb_no_source_noise'].metadata['used_source_mean_noise']['trace'] == 0
    for key in ('tau_common_squared','tau_halfcontrast_squared'):
        assert models['eb_no_source_noise'].metadata[key] == models['eb_point'].metadata[key]
        assert models['eb_no_shift'].metadata[key] == 0
    for c in (0,1):
        difference = (models['eb_predictive'].predictive_covariances[c]
                      - models['eb_point'].predictive_covariances[c])
        assert np.linalg.eigvalsh(difference).min() >= -1e-12
        assert np.trace(difference) > 0
    for name in ('eb_isotropic','eb_coupled','eb_no_source_noise','eb_no_shift'):
        assert models[name].metadata['predictive_uncertainty_integrated'] is True
        for c in (0,1):
            difference = models[name].predictive_covariances[c]-models[name].within_covariance
            assert np.trace(difference) > 0


def test_invalid_numeric_data_and_trial_overlap_propagate():
    source, support = split('source-'), split('support-',8,8)
    leaking = Split(support.x, support.y, source.trial_id[:8], support.run_id)
    with pytest.raises(ValueError, match='identity overlap'):
        geometry.fit(source, leaking, 'eb_predictive', {})
    bad = source.x.copy()
    bad[0,0,0] = np.nan
    with pytest.raises(ValueError):
        geometry.fit(Split(bad, source.y, source.trial_id,source.run_id), support,'eb_predictive',{})
    with pytest.raises(ValueError, match='nonempty current support'):
        geometry.fit(source,None,'eb_point',{})
