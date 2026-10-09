"""Train/inference checks for CPU baselines on clearly marked synthetic data."""

import numpy as np
import pytest
from sklearn.exceptions import NotFittedError
from sklearn.metrics import balanced_accuracy_score

from learning_preserving_bci.decoders import make_csp_lda


def variance_trials(seed, n_per_class=16, n_times=128):
    rng = np.random.default_rng(seed)
    y = np.repeat([0, 1], n_per_class)
    X = rng.normal(size=(len(y), 4, n_times))
    X[y == 0, 0] *= 3
    X[y == 1, 1] *= 3
    return X, y


def test_csp_lda_learns_spatial_variance_without_refitting_on_test():
    X_train, y_train = variance_trials(1)
    X_test, y_test = variance_trials(2)
    decoder = make_csp_lda(n_components=2)
    decoder.fit(X_train, y_train)
    filters = decoder.named_steps["csp"].filters_.copy()
    predictions = decoder.predict(X_test)
    assert balanced_accuracy_score(y_test, predictions) > 0.9
    assert np.array_equal(filters, decoder.named_steps["csp"].filters_)


def test_eegnet_official_cpu_model_small_step_and_frozen_inference():
    torch = pytest.importorskip("torch")
    pytest.importorskip("braindecode")
    from learning_preserving_bci.decoders import EEGNetClassifier

    torch.set_num_threads(1)
    X, y = variance_trials(4, n_per_class=4)
    model = EEGNetClassifier(4, 2, 128, 128.0, epochs=1, batch_size=4, seed=12)
    with pytest.raises(NotFittedError):
        model.predict(X)
    model.fit(X, y)
    assert model.architecture_.startswith("braindecode.models.EEGNet")
    state = {key: value.clone() for key, value in model.model_.state_dict().items()}
    probabilities = model.predict_proba(X)
    assert probabilities.shape == (8, 2)
    assert np.isfinite(probabilities).all()
    assert np.allclose(probabilities.sum(axis=1), 1, atol=1e-6)
    assert model.predict(X).shape == y.shape
    assert len(model.loss_history_) == 1
    for key, value in model.model_.state_dict().items():
        assert torch.equal(value, state[key])
    replica = EEGNetClassifier(4, 2, 128, 128.0, epochs=1, batch_size=4, seed=12).fit(X, y)
    assert np.array_equal(model.predict_proba(X), replica.predict_proba(X))
