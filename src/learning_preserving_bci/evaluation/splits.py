"""Explicit subject and session partitions, without assuming label chronology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

import numpy as np


@dataclass(frozen=True)
class TrialSplit:
    train_indices: np.ndarray
    test_indices: np.ndarray
    subject: Any
    reference_session: Any = None
    evaluation_session: Any = None

    def __post_init__(self):
        train = np.asarray(self.train_indices, dtype=int)
        test = np.asarray(self.test_indices, dtype=int)
        if not len(train) or not len(test):
            raise ValueError("Both train and test partitions must be nonempty")
        if np.intersect1d(train, test).size:
            raise ValueError("Train and test trials overlap")
        train.setflags(write=False)
        test.setflags(write=False)
        object.__setattr__(self, "train_indices", train)
        object.__setattr__(self, "test_indices", test)


def _groups(dataset):
    subjects, sessions = np.asarray(dataset.subjects), np.asarray(dataset.sessions)
    n_trials = len(dataset.y)
    if subjects.shape != (n_trials,) or sessions.shape != (n_trials,):
        raise ValueError("subjects and sessions must each contain one label per trial")
    return subjects, sessions


def leave_one_subject_out(dataset) -> Iterator[TrialSplit]:
    """Keep every session of the held-out subject outside training.

    Hyperparameter selection must use training subjects only; this iterator
    provides outer folds and does not perform or authorize test-set tuning.
    """
    subjects, _ = _groups(dataset)
    unique = np.unique(subjects)
    if len(unique) < 2:
        raise ValueError("Leave-one-subject-out evaluation needs at least two subjects")
    for subject in unique:
        yield TrialSplit(
            np.flatnonzero(subjects != subject), np.flatnonzero(subjects == subject), subject
        )


def within_subject_session_split(
    dataset, subject, reference_session, evaluation_session
) -> TrialSplit:
    """Partition two explicit session labels for one subject.

    Session labels have no implied global or chronological ordering. The caller
    must select the reference session from protocol metadata, not held-out scores.
    """
    if reference_session == evaluation_session:
        raise ValueError("Reference and evaluation sessions must differ")
    subjects, sessions = _groups(dataset)
    selected = subjects == subject
    return TrialSplit(
        np.flatnonzero(selected & (sessions == reference_session)),
        np.flatnonzero(selected & (sessions == evaluation_session)),
        subject,
        reference_session,
        evaluation_session,
    )
