"""Validated epoched EEG containers, safe local storage, and synthetic fixtures.

Label values are preserved verbatim. Neither this module nor its NPZ format
infers the motor-imagery task represented by an event code.
"""

from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Sequence

import numpy as np


def _validate_identifiers(values: Sequence, name: str, n_trials: int) -> np.ndarray:
    array = np.asarray(values)
    if array.shape != (n_trials,):
        raise ValueError(f"{name} must have shape ({n_trials},)")
    if array.dtype.kind not in "biufUS":
        raise ValueError(f"{name} must contain numeric or string values, not objects")
    if array.dtype.kind in "f" and not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    if array.dtype.kind in "US" and np.any(np.char.str_len(np.char.strip(array.astype(str))) == 0):
        raise ValueError(f"{name} must not contain empty identifiers")
    return array.copy()


def _validate_positive_scalar(value: float, name: str) -> float:
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, Real)
        or not np.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a positive finite scalar")
    return float(value)


@dataclass(frozen=True)
class EEGDataset:
    """EEG epochs and trial-level identity information.

    ``X`` has axes ``(trial, channel, time)`` and ``sfreq`` is in Hz.
    Labels may be numeric or strings. Units of ``X`` are the caller's
    responsibility; real MNE recordings conventionally use volts.
    """

    X: np.ndarray
    y: np.ndarray
    subjects: np.ndarray
    sessions: np.ndarray
    sfreq: float
    channel_names: tuple[str, ...] | None = None
    is_synthetic: bool = False

    def __post_init__(self) -> None:
        raw = np.asarray(self.X)
        if raw.dtype.kind not in "biuf":
            raise ValueError("X must contain real numeric values")
        X = np.asarray(raw, dtype=float)
        if X.ndim != 3 or any(size == 0 for size in X.shape):
            raise ValueError("X must have nonempty shape (n_trials, n_channels, n_times)")
        if not np.isfinite(X).all():
            raise ValueError("X must contain only finite values")
        sfreq = _validate_positive_scalar(self.sfreq, "sfreq")
        if not isinstance(self.is_synthetic, (bool, np.bool_)):
            raise ValueError("is_synthetic must be a boolean")
        n_trials, n_channels, _ = X.shape
        for name in ("y", "subjects", "sessions"):
            object.__setattr__(
                self, name, _validate_identifiers(getattr(self, name), name, n_trials)
            )
        names = self.channel_names
        if names is not None:
            names = tuple(names)
            if len(names) != n_channels or any(
                not isinstance(name, str) or not name.strip() for name in names
            ):
                raise ValueError("channel_names must contain one nonempty string per channel")
            if len(set(names)) != len(names):
                raise ValueError("channel_names must be unique")
        object.__setattr__(self, "X", X.copy())
        object.__setattr__(self, "sfreq", sfreq)
        object.__setattr__(self, "channel_names", names)
        object.__setattr__(self, "is_synthetic", bool(self.is_synthetic))

    @property
    def n_trials(self) -> int:
        return self.X.shape[0]

    @property
    def classes(self) -> np.ndarray:
        return np.unique(self.y)

    def subset(self, indices: Sequence[int] | np.ndarray) -> "EEGDataset":
        """Return selected trials while retaining subject, session, and label values."""
        index = np.asarray(indices)
        if index.ndim != 1 or index.dtype.kind not in "biu":
            raise ValueError("indices must be a one-dimensional integer or boolean array")
        if index.dtype.kind == "b" and index.size != self.n_trials:
            raise ValueError("boolean indices must match the number of trials")
        return EEGDataset(
            self.X[index],
            self.y[index],
            self.subjects[index],
            self.sessions[index],
            self.sfreq,
            self.channel_names,
            self.is_synthetic,
        )


def save_npz(path: str | Path, dataset: EEGDataset) -> None:
    """Save a validated dataset without object arrays or pickled metadata.

    The path is used exactly as given; existing files follow normal filesystem
    write semantics. Channel names and the schema version are explicit fields.
    """
    if not isinstance(dataset, EEGDataset):
        raise TypeError("dataset must be an EEGDataset")
    # Revalidation catches accidental in-place modifications of ndarray fields.
    checked = EEGDataset(
        dataset.X,
        dataset.y,
        dataset.subjects,
        dataset.sessions,
        dataset.sfreq,
        dataset.channel_names,
        dataset.is_synthetic,
    )
    with Path(path).open("wb") as handle:
        np.savez_compressed(
            handle,
            schema_version=np.asarray(1, dtype=np.int64),
            X=checked.X,
            y=checked.y,
            subjects=checked.subjects,
            sessions=checked.sessions,
            sfreq=np.asarray(checked.sfreq),
            channel_names=np.asarray(checked.channel_names or (), dtype=str),
            is_synthetic=np.asarray(checked.is_synthetic, dtype=bool),
        )


def load_npz(path: str | Path) -> EEGDataset:
    """Read only the documented NPZ schema with pickle explicitly disabled."""
    required = {
        "schema_version",
        "X",
        "y",
        "subjects",
        "sessions",
        "sfreq",
        "channel_names",
        "is_synthetic",
    }
    with np.load(Path(path), allow_pickle=False) as stored:
        if set(stored.files) != required:
            raise ValueError(f"NPZ fields must be exactly {sorted(required)}")
        version = stored["schema_version"]
        if version.shape != () or version.dtype.kind not in "iu" or int(version) != 1:
            raise ValueError("unsupported NPZ schema version")
        sfreq = stored["sfreq"]
        if sfreq.shape != () or sfreq.dtype.kind not in "biuf":
            raise ValueError("sfreq must be a numeric scalar")
        names = stored["channel_names"]
        if names.ndim != 1 or names.dtype.kind not in "US":
            raise ValueError("channel_names must be a one-dimensional string array")
        synthetic = stored["is_synthetic"]
        if synthetic.shape != () or synthetic.dtype.kind != "b":
            raise ValueError("is_synthetic must be a boolean scalar")
        return EEGDataset(
            X=stored["X"],
            y=stored["y"],
            subjects=stored["subjects"],
            sessions=stored["sessions"],
            sfreq=float(sfreq),
            channel_names=tuple(str(name) for name in names) if names.size else None,
            is_synthetic=bool(synthetic),
        )


def make_synthetic_dataset(
    *,
    n_subjects: int = 4,
    n_sessions: int = 2,
    trials_per_class: int = 12,
    n_channels: int = 8,
    n_times: int = 512,
    sfreq: float = 128.0,
    mu_frequency: float = 10.0,
    mu_amplitude: float = 1.2,
    noise_std: float = 1.0,
    seed: int | None = 42,
) -> EEGDataset:
    """Generate balanced two-class mu-band fixtures for software validation.

    Each subject/session contains both classes. Classes differ in the spatial
    strength of a mu rhythm; subject/session nuisance patterns and independent
    noise are added. These are arbitrary-unit simulations, not empirical EEG
    or evidence for physiological learning preservation.
    """
    for name, value in {
        "n_subjects": n_subjects,
        "n_sessions": n_sessions,
        "trials_per_class": trials_per_class,
        "n_channels": n_channels,
        "n_times": n_times,
    }.items():
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if n_channels < 2 or n_times < 4:
        raise ValueError("synthetic fixtures require at least two channels and four samples")
    sfreq = _validate_positive_scalar(sfreq, "sfreq")
    mu_frequency = _validate_positive_scalar(mu_frequency, "mu_frequency")
    if not mu_frequency < sfreq / 2:
        raise ValueError("mu_frequency must be between zero and the Nyquist frequency")
    for name, value in {"mu_amplitude": mu_amplitude, "noise_std": noise_std}.items():
        if (
            isinstance(value, (bool, np.bool_))
            or not isinstance(value, Real)
            or not np.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{name} must be nonnegative and finite")
    rng = np.random.default_rng(seed)
    time = np.arange(n_times) / sfreq
    patterns = np.stack((np.linspace(1.0, 0.15, n_channels), np.linspace(0.15, 1.0, n_channels)))
    all_epochs, labels, subjects, sessions = [], [], [], []
    for subject in range(n_subjects):
        gains = rng.uniform(0.8, 1.2, size=(n_channels, 1))
        for session in range(n_sessions):
            session_offset = rng.normal(0, 0.05, size=(n_channels, 1))
            for label in range(2):
                for _ in range(trials_per_class):
                    phase = rng.uniform(0, 2 * np.pi)
                    rhythm = np.sin(2 * np.pi * mu_frequency * time + phase)
                    noise = rng.normal(0, noise_std, size=(n_channels, n_times))
                    epoch = (
                        mu_amplitude * patterns[label, :, None] * gains * rhythm[None, :]
                        + noise
                        + session_offset
                    )
                    all_epochs.append(epoch)
                    labels.append(label)
                    subjects.append(f"subject_{subject + 1:02d}")
                    sessions.append(f"session_{session + 1}")
    return EEGDataset(
        np.stack(all_epochs),
        np.asarray(labels),
        np.asarray(subjects),
        np.asarray(sessions),
        sfreq,
        tuple(f"EEG{index + 1:02d}" for index in range(n_channels)),
        True,
    )


__all__ = ["EEGDataset", "save_npz", "load_npz", "make_synthetic_dataset"]
