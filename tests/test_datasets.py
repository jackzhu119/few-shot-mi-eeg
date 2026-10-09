"""Dataset safety and identity contracts independent of empirical EEG."""

import numpy as np
import pytest

from learning_preserving_bci.datasets import EEGDataset, load_npz, make_synthetic_dataset, save_npz


def test_npz_roundtrip_preserves_event_and_group_identity(tmp_path):
    dataset = EEGDataset(
        np.arange(48).reshape(4, 2, 6),
        np.array([769, 770, 769, 770]),
        np.array(["S01", "S01", "S02", "S02"]),
        np.array(["T", "E", "T", "E"]),
        250.0,
        ("C3", "C4"),
        True,
    )
    path = tmp_path / "epochs.npz"
    save_npz(path, dataset)
    restored = load_npz(path)
    for name in ("X", "y", "subjects", "sessions"):
        np.testing.assert_array_equal(getattr(restored, name), getattr(dataset, name))
    assert restored.sfreq == 250.0
    assert restored.channel_names == ("C3", "C4")
    assert restored.is_synthetic is True
    with np.load(path, allow_pickle=False) as stored:
        assert all(stored[name].dtype.kind != "O" for name in stored.files)


def test_string_labels_and_missing_channel_names_roundtrip(tmp_path):
    dataset = EEGDataset(
        np.ones((2, 1, 8)),
        np.array(["left hand", "right hand"]),
        np.array([1, 1]),
        np.array([1, 2]),
        100,
    )
    save_npz(tmp_path / "strings.npz", dataset)
    restored = load_npz(tmp_path / "strings.npz")
    np.testing.assert_array_equal(restored.y, dataset.y)
    assert restored.channel_names is None
    assert restored.is_synthetic is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"X": np.zeros((2, 8))},
        {"X": np.zeros((0, 2, 8))},
        {"X": np.full((2, 2, 8), np.nan)},
        {"y": np.array([0])},
        {"y": np.array([0, np.inf])},
        {"y": np.array([{"event": 1}, {"event": 2}], dtype=object)},
        {"subjects": np.array(["", "S2"])},
        {"sessions": np.array([1, np.nan])},
        {"sfreq": 0},
        {"sfreq": np.inf},
        {"channel_names": ("C3",)},
        {"channel_names": ("C3", "C3")},
        {"is_synthetic": "yes"},
    ],
)
def test_dataset_rejects_invalid_data(overrides):
    fields = dict(
        X=np.zeros((2, 2, 8)),
        y=np.array([0, 1]),
        subjects=np.array([1, 2]),
        sessions=np.array([1, 1]),
        sfreq=100,
    )
    fields.update(overrides)
    with pytest.raises(ValueError):
        EEGDataset(**fields)


def test_constructor_copies_input_arrays():
    X = np.ones((2, 2, 8))
    y = np.array([0, 1])
    dataset = EEGDataset(X, y, np.array([1, 1]), np.array([1, 1]), 100)
    X[:] = 9
    y[:] = 9
    np.testing.assert_array_equal(dataset.X, np.ones_like(X))
    np.testing.assert_array_equal(dataset.y, [0, 1])


def test_subset_preserves_identity_without_relabelling():
    dataset = make_synthetic_dataset(n_subjects=2, n_sessions=2, trials_per_class=2, seed=7)
    indices = np.array([1, 9, 4])
    subset = dataset.subset(indices)
    np.testing.assert_array_equal(subset.X, dataset.X[indices])
    for name in ("y", "subjects", "sessions"):
        np.testing.assert_array_equal(getattr(subset, name), getattr(dataset, name)[indices])
    assert subset.is_synthetic is True
    assert subset.channel_names == dataset.channel_names


def test_npz_rejects_untrusted_object_arrays(tmp_path):
    path = tmp_path / "untrusted.npz"
    np.savez(
        path,
        schema_version=np.array(1),
        X=np.ones((2, 2, 8)),
        y=np.array([{}, {}], dtype=object),
        subjects=np.array([1, 1]),
        sessions=np.array([1, 1]),
        sfreq=np.array(100),
        channel_names=np.array([], dtype=str),
        is_synthetic=np.array(False),
    )
    with pytest.raises(ValueError, match="Object arrays cannot be loaded"):
        load_npz(path)


def test_npz_rejects_unrecognized_schema(tmp_path):
    np.savez(tmp_path / "partial.npz", X=np.ones((2, 2, 8)))
    with pytest.raises(ValueError, match="fields"):
        load_npz(tmp_path / "partial.npz")


def test_synthetic_dataset_is_repeatable_and_balanced_per_subject_session():
    first = make_synthetic_dataset(n_subjects=3, n_sessions=2, trials_per_class=3, seed=19)
    second = make_synthetic_dataset(n_subjects=3, n_sessions=2, trials_per_class=3, seed=19)
    np.testing.assert_array_equal(first.X, second.X)
    assert first.is_synthetic is True
    for subject in np.unique(first.subjects):
        for session in np.unique(first.sessions):
            labels = first.y[(first.subjects == subject) & (first.sessions == session)]
            assert np.count_nonzero(labels == 0) == np.count_nonzero(labels == 1) == 3
    other = make_synthetic_dataset(n_subjects=3, n_sessions=2, trials_per_class=3, seed=20)
    assert not np.array_equal(first.X, other.X)


def test_synthetic_mu_control_has_expected_spatial_pattern():
    from learning_preserving_bci.signal_processing import bandpower

    dataset = make_synthetic_dataset(
        n_subjects=1, n_sessions=1, trials_per_class=4, noise_std=0, seed=6
    )
    power = bandpower(dataset.X, dataset.sfreq)
    assert power[dataset.y == 0, 0].mean() > power[dataset.y == 0, -1].mean()
    assert power[dataset.y == 1, -1].mean() > power[dataset.y == 1, 0].mean()


@pytest.mark.parametrize(
    "overrides",
    [
        {"n_subjects": 0},
        {"trials_per_class": True},
        {"n_channels": 1},
        {"mu_frequency": 64},
        {"noise_std": -1},
    ],
)
def test_synthetic_invalid_parameters(overrides):
    with pytest.raises(ValueError):
        make_synthetic_dataset(**overrides)
