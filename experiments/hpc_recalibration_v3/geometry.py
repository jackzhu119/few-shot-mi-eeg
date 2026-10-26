"""Source-reference tangent classifiers and joint mean/contrast EB adaptation.

All estimates use source and the current labeled support only. Query covariates
enter only ``predict_probabilities`` after fitting. The Gaussian posterior is a
candidate model, not a guaranteed improvement in EEG balanced accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from hpc_recalibration.classical import trial_covariances
from hpc_recalibration.data import atomic_npz


METHODS = (
    "source_tangent_frozen", "tangent_pooled", "tangent_refit", "eb_point",
    "eb_predictive", "eb_isotropic", "eb_coupled", "eb_no_source_noise",
    "eb_no_shift",
)
IMPLEMENTATION = "source_tangent_halfcontrast_joint_eb_v3_1"


def _settings(settings):
    value = {
        "covariance_shrinkage": float(settings.get("covariance_shrinkage", settings.get("rho", .1))),
        "feature_shrinkage": float(settings.get("feature_shrinkage", settings.get("lda_shrinkage", .1))),
        "numerical_floor": float(settings.get("numerical_floor", 1e-8)),
    }
    if (not 0 < value["covariance_shrinkage"] < 1
            or not 0 < value["feature_shrinkage"] < 1
            or not 0 < value["numerical_floor"] < 1):
        raise ValueError("Invalid fixed tangent covariance settings")
    return value


def _sym(matrix):
    return (matrix + matrix.T) * .5


def _regularize(matrix, rho, floor):
    matrix = _sym(np.asarray(matrix, dtype=np.float64))
    scale = float(np.trace(matrix) / len(matrix))
    if not np.isfinite(matrix).all() or not scale > 0:
        raise ValueError("Nonfinite or zero-scale covariance")
    value = (1-rho) * matrix + rho * scale * np.eye(len(matrix))
    values, vectors = np.linalg.eigh(value)
    return _sym((vectors * np.maximum(values, floor*scale)) @ vectors.T)


def _matrix_function(matrix, operation):
    values, vectors = np.linalg.eigh(_sym(matrix))
    if not np.isfinite(values).all() or np.min(values) <= 0:
        raise ValueError("Covariance must be finite positive definite")
    return _sym((vectors * operation(values)) @ vectors.T)


def _vech(matrix):
    indices = np.triu_indices(matrix.shape[-1])
    value = matrix[..., indices[0], indices[1]].copy()
    value[..., indices[0] != indices[1]] *= np.sqrt(2)
    return value


def _pack(matrix):
    return matrix[np.triu_indices(len(matrix))]


def _unpack(value, size):
    matrix = np.zeros((size, size), dtype=np.float64)
    indices = np.triu_indices(size)
    if value.shape != (len(indices[0]),):
        raise ValueError("Malformed packed symmetric model matrix")
    matrix[indices] = value
    matrix[(indices[1], indices[0])] = value
    return matrix


def _features(x, inverse_reference, settings):
    covariances = trial_covariances(x, trace_normalize=True)
    channels = covariances.shape[1]
    if inverse_reference.shape != (channels, channels):
        raise ValueError("Input channels differ from the saved source reference")
    rho, floor = settings["covariance_shrinkage"], settings["numerical_floor"]
    covariances = np.stack([_regularize(c, rho, floor) for c in covariances])
    tangent = []
    for covariance in covariances:
        aligned = _sym(inverse_reference @ covariance @ inverse_reference.T)
        tangent.append(_vech(_matrix_function(aligned, np.log)))
    return np.asarray(tangent, dtype=np.float64)


def _covariance(features):
    centered = features - features.mean(axis=0)
    return centered.T @ centered / (len(features)-1)


def _class_statistics(features, labels, source_covariances, settings):
    means, covariances, counts, fallback = [], [], [], []
    for c in (0, 1):
        selected = features[labels == c]
        count = len(selected)
        counts.append(count)
        means.append(selected.mean(axis=0) if count else None)
        if count >= 2:
            covariance = _regularize(_covariance(selected), settings["feature_shrinkage"],
                                     settings["numerical_floor"])
        elif source_covariances is not None:
            covariance = source_covariances[c].copy()
            fallback.append({"class": c, "condition": "one_support_trial" if count else "missing_support_class",
                             "variance_proxy": "source_class_covariance" if count else "no_observation"})
        else:
            raise ValueError("Each source class needs at least two trials")
        covariances.append(covariance)
    return means, covariances, counts, fallback


def _joint_theta(means):
    return np.concatenate([(means[0]+means[1])*.5, (means[1]-means[0])*.5])


def _joint_noise(class_mean_covariances):
    first, second = class_mean_covariances
    total, difference = first+second, second-first
    return _sym(np.block([[total, difference], [difference, total]])*.25)


def gaussian_update(prior_mean, prior_covariance, observation, design, observation_covariance):
    """Exact linear-Gaussian update, with only the supplied observed classes."""
    prior_mean = np.asarray(prior_mean, dtype=np.float64)
    prior_covariance = _sym(np.asarray(prior_covariance, dtype=np.float64))
    observation, design = np.asarray(observation), np.asarray(design)
    innovation_covariance = _sym(design @ prior_covariance @ design.T + observation_covariance)
    cross = prior_covariance @ design.T
    gain = np.linalg.solve(innovation_covariance, cross.T).T
    mean = prior_mean + gain @ (observation-design @ prior_mean)
    # Joseph form is PSD and more stable than subtracting nearly equal matrices.
    residual = np.eye(len(prior_mean))-gain @ design
    covariance = _sym(residual @ prior_covariance @ residual.T
                      + gain @ observation_covariance @ gain.T)
    if not np.isfinite(mean).all() or not np.isfinite(covariance).all():
        raise ValueError("Nonfinite Gaussian posterior")
    return mean, covariance


def _domain_shift(source_theta, target_theta, source_noise, target_noise, mode):
    p = len(source_theta)//2
    difference = target_theta-source_theta
    unbiased = [float(np.sum(difference[j*p:(j+1)*p]**2)
                      - np.trace(source_noise[j*p:(j+1)*p, j*p:(j+1)*p]
                                 + target_noise[j*p:(j+1)*p, j*p:(j+1)*p])) / p
                for j in (0, 1)]
    tau = [max(value, 0.) for value in unbiased]
    if mode == "coupled":
        tau = [max(float(np.mean(unbiased)), 0.)]*2
    elif mode == "none":
        tau = [0., 0.]
    matrix = np.diag(np.repeat(tau, p))
    return matrix, tau, unbiased


def _noise_summary(matrix):
    eigenvalues = np.linalg.eigvalsh(_sym(matrix))
    return {"dimension": len(matrix), "trace": float(np.trace(matrix)),
            "minimum_eigenvalue": float(eigenvalues.min()),
            "maximum_eigenvalue": float(eigenvalues.max())}


def _split_identity(split):
    digest = hashlib.sha256()
    for value in (split.x, split.y, split.trial_id, split.run_id):
        digest.update(str(value.dtype).encode())
        digest.update(str(value.shape).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


@dataclass
class FeatureDecoder:
    """The same frozen Gaussian estimator, operating directly on feature rows."""
    within_covariance: np.ndarray
    class_means: np.ndarray
    posterior_theta: np.ndarray
    posterior_covariance: np.ndarray
    settings: dict
    metadata: dict

    def __post_init__(self):
        self.within_covariance = np.asarray(self.within_covariance, dtype=np.float64)
        self.class_means = np.asarray(self.class_means, dtype=np.float64)
        self.posterior_theta = np.asarray(self.posterior_theta, dtype=np.float64)
        self.posterior_covariance = np.asarray(self.posterior_covariance, dtype=np.float64)
        self.classes = np.array([0, 1], dtype=np.int64)
        p = self.within_covariance.shape[0]
        if (self.class_means.shape != (2, p) or self.posterior_theta.shape != (2*p,)
                or self.posterior_covariance.shape != (2*p, 2*p)):
            raise ValueError("Malformed saved tangent model shapes")
        self.predictive_covariances = []
        self.log_determinants = []
        for c in (0, 1):
            q = self.within_covariance.copy()
            if self.metadata["method"].startswith("eb_") and self.metadata["method"] != "eb_point":
                design = np.concatenate([np.eye(p), (1 if c else -1)*np.eye(p)], axis=1)
                q += design @ self.posterior_covariance @ design.T
            q = _sym(q)
            sign, logdet = np.linalg.slogdet(q)
            if sign != 1 or not np.isfinite(q).all() or not np.isfinite(logdet):
                raise ValueError("Invalid predictive covariance")
            self.predictive_covariances.append(q)
            self.log_determinants.append(float(logdet))

    def predict_probabilities(self, features):
        features = np.asarray(features, dtype=np.float64)
        if features.ndim != 2 or features.shape[1] != self.class_means.shape[1] or not np.isfinite(features).all():
            raise ValueError("Invalid tangent feature input")
        scores = []
        for c in (0, 1):
            residual = features-self.class_means[c]
            solved = np.linalg.solve(self.predictive_covariances[c], residual.T).T
            scores.append(-.5*(np.sum(residual*solved, axis=1)+self.log_determinants[c]))
        scores = np.stack(scores, axis=1)
        scores -= scores.max(axis=1, keepdims=True)
        probabilities = np.exp(scores)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        if not np.isfinite(probabilities).all():
            raise ValueError("Nonfinite saved-decoder probabilities")
        return probabilities

    def predict(self, x):
        return self.classes[np.argmax(self.predict_probabilities(x), axis=1)]

@dataclass
class Decoder:
    reference: np.ndarray
    within_covariance: np.ndarray
    class_means: np.ndarray
    posterior_theta: np.ndarray
    posterior_covariance: np.ndarray
    settings: dict
    metadata: dict

    def __post_init__(self):
        self.reference = np.asarray(self.reference, dtype=np.float64)
        self.inverse_reference = _matrix_function(self.reference, lambda v: v**-.5)
        self.feature_decoder = FeatureDecoder(self.within_covariance, self.class_means,
                                             self.posterior_theta, self.posterior_covariance,
                                             self.settings, self.metadata)
        self.classes = self.feature_decoder.classes

    def predict_probabilities(self, x):
        features = _features(x, self.inverse_reference, self.settings)
        return self.feature_decoder.predict_probabilities(features)

    def predict(self, x):
        return self.classes[np.argmax(self.predict_probabilities(x), axis=1)]

    def save(self, path):
        # Symmetric packing halves persistent posterior storage, without reducing
        # float64 precision or depending on a separate source-model file.
        atomic_npz(path, reference=self.reference, class_means=self.class_means,
                   within_packed=_pack(self.within_covariance),
                   posterior_theta=self.posterior_theta,
                   posterior_packed=_pack(self.posterior_covariance),
                   metadata_json=np.asarray(json.dumps(self.metadata, sort_keys=True, allow_nan=False)))

    @classmethod
    def load(cls, path: str | Path):
        with np.load(path, allow_pickle=False) as values:
            saved = json.loads(str(values["metadata_json"].item()))
            means = values["class_means"].copy()
            p = means.shape[1]
            arrays = [values["reference"].copy(), _unpack(values["within_packed"], p), means,
                      values["posterior_theta"].copy(), _unpack(values["posterior_packed"], 2*p)]
        if not all(np.isfinite(value).all() for value in arrays):
            raise ValueError("Nonfinite persisted geometry model")
        return cls(*arrays, saved["settings"], saved)


def fit(source, support, method: str, settings: dict):
    """Fit from source/current support only; deliberately no query argument."""
    if method not in METHODS:
        raise ValueError("Unknown tangent method: " + str(method))
    settings = _settings(settings)
    labels = np.asarray(source.y)
    if not np.array_equal(np.unique(labels), [0, 1]):
        raise ValueError("Source labels must be 0 and 1")
    source_ids = source.trial_id.tolist()
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("Duplicate source trial identity")
    if support is not None:
        if (support.x.shape[1:] != source.x.shape[1:]
                or not set(support.y.tolist()) <= {0, 1}):
            raise ValueError("Support dimensions/classes differ from source")
        support_ids = support.trial_id.tolist()
        if len(set(support_ids)) != len(support_ids) or set(support_ids) & set(source_ids):
            raise ValueError("Source/support trial identity overlap")
    else:
        support_ids = []
    if method != "source_tangent_frozen" and (support is None or not len(support.y)):
        raise ValueError("Adaptive tangent method needs nonempty current support")
    source_covariances = trial_covariances(source.x, trace_normalize=True)
    reference = np.mean([_regularize(c, settings["covariance_shrinkage"], settings["numerical_floor"])
                         for c in source_covariances], axis=0)
    inverse_reference = _matrix_function(reference, lambda v: v**-.5)
    source_features = _features(source.x, inverse_reference, settings)
    model = fit_features(source_features, labels,
                         None if method == "source_tangent_frozen" else _features(support.x, inverse_reference, settings),
                         None if method == "source_tangent_frozen" else support.y, method, settings)
    model.metadata.update({"source_reference_scope": "source_train_only_fixed_for_all_supports_and_queries",
                           "representation_scope": "fixed_source_reference_log_spd_vech_sqrt2",
                           "source_reference_uncertainty_propagated": False,
                           "source_trial_ids": source_ids,
                           "support_trial_ids": support_ids if method != "source_tangent_frozen" else [],
                           "fit_trial_ids": source_ids + (support_ids if method != "source_tangent_frozen" else []),
                           "source_identity": _split_identity(source),
                           "support_identity": None if method == "source_tangent_frozen" else _split_identity(support)})
    return Decoder(reference, model.within_covariance, model.class_means, model.posterior_theta,
                   model.posterior_covariance, settings, model.metadata)


def _feature_identity(features, labels):
    digest = hashlib.sha256()
    for value in (features, labels):
        digest.update(str(value.shape).encode())
        digest.update(str(value.dtype).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def fit_features(source_features, source_labels, target_features, support_labels, method: str, settings: dict):
    """The exact estimator used by ``fit``; useful for declared Gaussian simulations.

    No test/query features or labels enter this fitting interface. Simulations
    should retain their own synthetic/software validation identity in outputs.
    """
    if method not in METHODS:
        raise ValueError("Unknown tangent method: " + str(method))
    settings = _settings(settings)
    source_features = np.asarray(source_features, dtype=np.float64)
    labels = np.asarray(source_labels)
    if (source_features.ndim != 2 or source_features.shape[1] < 1
            or labels.shape != (len(source_features),) or not np.isfinite(source_features).all()
            or not np.array_equal(np.unique(labels), [0, 1])):
        raise ValueError("Invalid binary source feature/label arrays")
    source_ids = ["source-feature-row-"+str(i) for i in range(len(labels))]
    if method != "source_tangent_frozen":
        target_features, support_labels = np.asarray(target_features, dtype=np.float64), np.asarray(support_labels)
        if (target_features.ndim != 2 or target_features.shape[1] != source_features.shape[1]
                or not len(target_features) or support_labels.shape != (len(target_features),)
                or not np.isfinite(target_features).all() or not set(support_labels.tolist()) <= {0, 1}):
            raise ValueError("Invalid current support feature/label arrays")
        support_ids = ["support-feature-row-"+str(i) for i in range(len(support_labels))]
    else:
        support_ids = []
    means_s, covs_s, counts_s, _ = _class_statistics(source_features, labels, None, settings)
    p = source_features.shape[1]
    residuals = np.concatenate([source_features[labels == c]-means_s[c] for c in (0, 1)])
    within = _regularize(residuals.T @ residuals/(len(labels)-2),
                         settings["feature_shrinkage"], settings["numerical_floor"])
    theta_s = _joint_theta(means_s)
    noise_s = _joint_noise([covs_s[c]/counts_s[c] for c in (0, 1)])
    posterior, posterior_covariance = theta_s.copy(), np.zeros((2*p, 2*p))
    class_means = np.stack(means_s)
    tau, raw_tau, counts_t, fallback = [0., 0.], [0., 0.], [0, 0], []
    target_noise_summary = None
    used_noise_s = noise_s
    observation_scope = "source_only"
    if method != "source_tangent_frozen":
        means_t, covs_t, counts_t, fallback = _class_statistics(
            target_features, support_labels, covs_s, settings)
        if method in ("tangent_pooled", "tangent_refit"):
            combined = np.concatenate([source_features, target_features])
            combined_y = np.concatenate([labels, support_labels])
            class_means = np.stack([combined[combined_y == c].mean(axis=0) for c in (0, 1)])
            posterior = _joint_theta(class_means)
            if method == "tangent_refit":
                residuals = np.concatenate([combined[combined_y == c]-class_means[c] for c in (0, 1)])
                within = _regularize(residuals.T @ residuals/(len(combined)-2),
                                     settings["feature_shrinkage"], settings["numerical_floor"])
        else:
            if all(counts_t):
                theta_t = _joint_theta(means_t)
                noise_t = _joint_noise([covs_t[c]/counts_t[c] for c in (0, 1)])
                if method == "eb_isotropic":
                    used_noise_s = np.eye(2*p)*np.trace(noise_s)/(2*p)
                    noise_t = np.eye(2*p)*np.trace(noise_t)/(2*p)
                mode = "coupled" if method == "eb_coupled" else "none" if method == "eb_no_shift" else "separate"
                shift, tau, raw_tau = _domain_shift(theta_s, theta_t, used_noise_s, noise_t, mode)
                if method == "eb_no_source_noise":
                    used_noise_s = np.zeros_like(noise_s)  # T is kept identical to the main estimator.
                posterior, posterior_covariance = gaussian_update(
                    theta_s, used_noise_s+shift, theta_t, np.eye(2*p), noise_t)
                target_noise_summary = _noise_summary(noise_t)
                observation_scope = "joint_mean_halfcontrast"
            else:
                # No imputed class observations and no query-derived variance.
                # Domain-shift components are not identifiable with one class.
                observed = next(c for c in (0, 1) if counts_t[c])
                design = np.concatenate([np.eye(p), (1 if observed else -1)*np.eye(p)], axis=1)
                noise_t = covs_t[observed]/counts_t[observed]
                if method == "eb_isotropic":
                    used_noise_s = np.eye(2*p)*np.trace(noise_s)/(2*p)
                    noise_t = np.eye(p)*np.trace(noise_t)/p
                elif method == "eb_no_source_noise":
                    used_noise_s = np.zeros_like(noise_s)
                posterior, posterior_covariance = gaussian_update(
                    theta_s, used_noise_s, means_t[observed], design, noise_t)
                target_noise_summary = _noise_summary(noise_t)
                observation_scope = "observed_class_only_no_domain_shift_estimate"
                fallback.append({"condition": "domain_shift_not_identifiable", "domain_shift_variance": 0.})
            class_means = np.stack([posterior[:p]-posterior[p:], posterior[:p]+posterior[p:]])
    metadata = {
        "implementation": IMPLEMENTATION, "method": method, "settings": settings,
        "representation_scope": "caller_supplied_source_and_support_features_only",
        "feature_dimension": p, "class_priors": [.5, .5],
        "source_class_counts": counts_s, "support_class_counts": counts_t,
        "source_trial_ids": source_ids,
        "support_trial_ids": support_ids if method != "source_tangent_frozen" else [],
        "fit_trial_ids": source_ids + (support_ids if method != "source_tangent_frozen" else []),
        "source_identity": _feature_identity(source_features, labels),
        "support_identity": None if method == "source_tangent_frozen" else _feature_identity(target_features, support_labels),
        "query_used_for_fitting": False, "fallback": fallback,
        "source_mean_noise": _noise_summary(noise_s),
        "used_source_mean_noise": _noise_summary(used_noise_s),
        "target_observation_noise": target_noise_summary,
        "target_observation_scope": observation_scope,
        "tau_common_squared": float(tau[0]), "tau_halfcontrast_squared": float(tau[1]),
        "debiased_shift_before_positive_part": raw_tau,
        "posterior_trace": float(np.trace(posterior_covariance)),
        "posterior_kind": "joint_gaussian_mean_halfcontrast" if method.startswith("eb_") else "not_applicable_point_classifier",
        "predictive_uncertainty_integrated": method.startswith("eb_") and method != "eb_point",
        "assumption": "estimated Gaussian feature/mean-noise model; no guaranteed EEG BA improvement",
        "noise_model_scope": "class-mean sampling uncertainty conditional on plug-in representation and within-class covariances",
        "exact_affine_invariance_claimed": False,
    }
    return FeatureDecoder(within, class_means, posterior, posterior_covariance, settings, metadata)
