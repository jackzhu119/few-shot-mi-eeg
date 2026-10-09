"""A frozen-reference-decoder offline proxy with explicit interpretation limits."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from sklearn.base import clone
from sklearn.metrics import accuracy_score, balanced_accuracy_score, cohen_kappa_score

from ..utils.reproducibility import collect_provenance, seed_everything
from .splits import _groups, within_subject_session_split


def _scalar(value):
    return value.item() if isinstance(value, np.generic) else value


def _decoder_configuration(decoder):
    configuration = {}
    if hasattr(decoder, "get_params"):
        for key, value in decoder.get_params(deep=True).items():
            value = _scalar(value)
            if value is None or isinstance(value, (str, bool, int, float)):
                configuration[key] = value
    return configuration


def evaluate_fixed_decoder(
    dataset,
    decoder,
    reference_session,
    evaluation_sessions=None,
    seed: int = 42,
    repository=None,
    config: dict | None = None,
) -> dict:
    """Fit once per subject on a reference session and evaluate frozen predictions.

    ``reference_session`` may be a label or a mapping from subject to label.
    ``evaluation_sessions`` optionally specifies held-out labels explicitly;
    otherwise all other sessions are used, without assigning a time order.
    Every model and preprocessing step is fitted on that subject's reference
    trials only. Test labels are used only for scoring and class-coverage checks.
    ``decoder`` must implement a cloneable sklearn-style estimator interface;
    cloning discards fitted state, including state in warm-start templates.
    Global RNGs are reset independently for each subject. Unset sklearn-style
    ``random_state`` parameters receive ``seed``; explicit estimator seeds are
    preserved and the effective parameters are logged with each record.

    This is an offline fixed-reference decoding diagnostic. It cannot establish online independent
    control, user learning, longitudinal causality, or adaptation effectiveness.
    """
    seed_everything(seed)
    X, y = np.asarray(dataset.X, dtype=np.float64), np.asarray(dataset.y)
    if X.ndim != 3 or y.shape != (len(X),) or not np.isfinite(X).all():
        raise ValueError("Expected finite X(trials, channels, times) and y(trials)")
    subjects, sessions = _groups(dataset)
    records = []
    subject_scores = {}
    for subject in np.unique(subjects):
        reference = (
            reference_session[subject]
            if isinstance(reference_session, Mapping)
            else reference_session
        )
        available = np.unique(sessions[subjects == subject])
        selected = (
            [session for session in available if session != reference]
            if evaluation_sessions is None
            else list(evaluation_sessions)
        )
        if reference not in available:
            raise ValueError(f"Reference session {reference!r} absent for subject {subject!r}")
        if not selected:
            raise ValueError(f"No held-out session for subject {subject!r}")
        if reference in selected:
            raise ValueError("Evaluation sessions must exclude the reference session")
        if len(set(selected)) != len(selected):
            raise ValueError("Evaluation session labels must be unique")
        splits = [
            within_subject_session_split(dataset, subject, reference, session)
            for session in selected
        ]
        train = splits[0].train_indices
        train_classes, train_counts = np.unique(y[train], return_counts=True)
        if len(train_classes) < 2:
            raise ValueError("Reference session must contain at least two classes")
        # The unfitted template remains intact and cannot carry a previous
        # subject's learned spatial filters, normalization, or weights.
        try:
            fitted = clone(decoder)
        except (TypeError, RuntimeError) as error:
            raise TypeError("decoder must be a cloneable sklearn-style estimator") from error
        unset_random_states = {
            key: seed
            for key, value in fitted.get_params(deep=True).items()
            if (key == "random_state" or key.endswith("__random_state")) and value is None
        }
        if unset_random_states:
            fitted.set_params(**unset_random_states)
        seed_everything(seed)
        fitted.fit(X[train], y[train])
        scores = []
        for split in splits:
            test = split.test_indices
            if not np.array_equal(np.unique(y[test]), train_classes):
                raise ValueError("Held-out and reference sessions must contain the same classes")
            prediction = np.asarray(fitted.predict(X[test]))
            if prediction.shape != y[test].shape or not np.isin(prediction, train_classes).all():
                raise ValueError("Decoder returned invalid predictions")
            balanced = float(balanced_accuracy_score(y[test], prediction))
            scores.append(balanced)
            records.append(
                {
                    "subject": _scalar(subject),
                    "reference_session": _scalar(reference),
                    "evaluation_session": _scalar(split.evaluation_session),
                    "training_seed": int(seed),
                    "effective_decoder_configuration": _decoder_configuration(fitted),
                    "n_training_trials": int(len(train)),
                    "n_evaluation_trials": int(len(test)),
                    "training_trial_indices": train.tolist(),
                    "evaluation_trial_indices": test.tolist(),
                    "y_true": [_scalar(label) for label in y[test]],
                    "y_pred": [_scalar(label) for label in prediction],
                    "training_class_counts": {
                        str(_scalar(label)): int(count)
                        for label, count in zip(train_classes, train_counts)
                    },
                    "balanced_accuracy": balanced,
                    "accuracy": float(accuracy_score(y[test], prediction)),
                    "cohen_kappa": float(cohen_kappa_score(y[test], prediction)),
                }
            )
        key = str(_scalar(subject))
        if key in subject_scores:
            raise ValueError("Subject labels are ambiguous when converted to JSON keys")
        subject_scores[key] = float(np.mean(scores))
    if not subject_scores:
        raise ValueError("No subjects to evaluate")
    return {
        "schema_version": 1,
        "protocol": "within_subject_frozen_reference_decoder",
        "synthetic": bool(getattr(dataset, "is_synthetic", False)),
        "decoder": type(decoder).__name__,
        "decoder_configuration": _decoder_configuration(decoder),
        "configuration": dict(config or {}),
        "n_subjects": len(subject_scores),
        "per_subject_session": records,
        "subject_balanced_accuracy": subject_scores,
        "mean_subject_balanced_accuracy": float(np.mean(list(subject_scores.values()))),
        "aggregation": "equal weight per session within subject, then equal weight per subject",
        "interpretation": (
            "Offline fixed-reference decoding diagnostic only; not evidence of online independent "
            "control, user learning, causal longitudinal improvement, or validated adaptation."
        ),
        "provenance": collect_provenance(seed, repository),
    }
