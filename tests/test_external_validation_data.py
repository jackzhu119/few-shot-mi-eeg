"""Synthetic MATLAB fixtures test external data semantics, never real EEG scores."""
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.io import savemat
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from external_validation_20261027 import data  # noqa: E402


def session_objects(seed=0):
    rng = np.random.default_rng(seed)
    classes = np.asarray(["left hand", "right hand", "feet", "tongue"], dtype=object)
    eog = {"X": rng.normal(size=(100, 25)), "trial": np.empty(0),
           "y": np.empty(0), "fs": 250, "artifacts": np.empty(0), "classes": classes}
    runs = [eog]
    # Short, overlapping synthetic epochs keep fixtures small. This only checks
    # event/sample semantics; it is not an imitation of acquisition timing.
    for index in range(6):
        trials = 1 + 20 * np.arange(48)
        labels = np.tile(np.arange(1, 5), 12)
        artifacts = np.zeros(48, dtype=np.int64)
        artifacts[[0, 1, 43]] = 1
        runs.append({"X": rng.normal(size=(2500, 25)) + index,
                     "trial": trials, "y": labels, "fs": 250,
                     "artifacts": artifacts, "classes": classes.copy()})
    return runs


def write_mat(path, objects):
    array = np.empty((1, len(objects)), dtype=object)
    array[0] = objects
    savemat(path, {"data": array})


@pytest.fixture
def files(tmp_path):
    source, target = tmp_path / "A01T.mat", tmp_path / "A01E.mat"
    write_mat(source, session_objects(1))
    write_mat(target, session_objects(2))
    return source, target


def test_matlab_one_based_trial_to_cue_epoch_and_EOG_channels(files):
    loaded = data.load_session(files[0], "sub-1", "T")
    assert len(loaded["runs"]) == 6
    assert loaded["skipped_runs"] == [{"original_object_position": 1,
                                       "reason": "no_MI_trials_EOG_calibration_object"}]
    first = loaded["runs"][0]
    assert first["x"].shape == (24, 22, 1000)
    assert first["x"].dtype == np.float32
    assert first["y"].tolist() == [0, 1] * 12
    assert first["trial_id"][0] == "bnci2014-001/sub-01/ses-T/run-01/trial-0001"
    raw = session_objects(1)[1]["X"][:, :22].T * 1e-6
    expected = sosfiltfilt(butter(4, [8, 30], fs=250, btype="bandpass", output="sos"), raw)
    np.testing.assert_array_equal(first["x"][0], expected[:, 500:1500].astype(np.float32))
    np.testing.assert_array_equal(first["x"][1], expected[:, 520:1520].astype(np.float32))
    row = loaded["manifest"][0]
    assert row["original_trial_start_matlab_1based"] == 1
    assert row["epoch_start_sample_0based"] == 500
    assert row["epoch_stop_sample_0based_exclusive"] == 1500


def test_fixed_chronological_split_counts_and_manifest(files):
    prepared = data.prepare_subject(*files, "1")
    splits = prepared["splits"]
    assert {name: len(split["y"]) for name, split in splits.items()} == {
        "source_train": 96, "source_query": 24, "support": 20, "query": 120}
    assert len(prepared["manifest"]) == 576
    assert {row["original_label"] for row in prepared["manifest"]} == {1, 2, 3, 4}
    assert sum(row["included"] for row in prepared["manifest"]) == 260
    assert sum(row["reason"] == "unused_source_run_5" for row in prepared["manifest"]) == 24
    assert sum(row["reason"] == "unused_support_run_tail" for row in prepared["manifest"]) == 4
    support_ids = splits["support"]["trial_id"].tolist()
    expected_ids = data.load_session(files[1], 1, "E")["runs"][0]["trial_id"][:20].tolist()
    assert support_ids == expected_ids
    for role, split in splits.items():
        for other, alternative in splits.items():
            if role == other:
                continue
            assert not set(split["trial_id"]) & set(alternative["trial_id"])
            assert not set(split["run_id"]) & set(alternative["run_id"])
    # Artifact-marked hand trials are retained in source, support and query.
    marked = [row for row in prepared["manifest"] if row["included"] and row["artifact_flag"]]
    assert {row["role"] for row in marked} >= {"source_train", "source_query", "support", "query"}
    assert "run-02" in splits["query"]["run_id"][0]
    assert "run-06" in splits["query"]["run_id"][-1]


def test_save_prepared_portable_no_pickle(files, tmp_path):
    prepared = data.prepare_subject(*files, "sub-01")
    saved = data.save_prepared(prepared, tmp_path / "prepared")
    assert saved["files"]["support"] == "support.npz"
    for role, filename in saved["files"].items():
        assert len(saved["input_sha256"][filename]) == 64
        with np.load(tmp_path / "prepared" / filename, allow_pickle=False) as archive:
            assert set(archive.files) == {"x", "y", "trial_id", "run_id"}
            for key in archive.files:
                np.testing.assert_array_equal(archive[key], prepared["splits"][role][key])


@pytest.mark.parametrize("corruption,match", [
    ("fs", "250 Hz"), ("trial", "positive and increasing"),
    ("end", "exceeds"), ("artifacts", "artifact flags"),
    ("channels", "22 EEG"), ("runs", "six MI"),
])
def test_bad_real_data_semantics_are_not_silently_repaired(tmp_path, corruption, match):
    objects = session_objects()
    if corruption == "fs":
        objects[1]["fs"] = 256
    elif corruption == "trial":
        objects[1]["trial"][0] = 0
    elif corruption == "end":
        objects[1]["trial"][-1] = 2000
    elif corruption == "artifacts":
        objects[1]["artifacts"] = np.zeros(47)
    elif corruption == "channels":
        objects[1]["X"] = objects[1]["X"][:, :21]
    else:
        objects.pop()
    path = tmp_path / "corrupt.mat"
    write_mat(path, objects)
    with pytest.raises(ValueError, match=match):
        data.load_session(path, "1", "T")


def test_support_is_chronological_not_label_rebalanced(files, tmp_path):
    objects = session_objects(2)
    objects[1]["y"] = np.repeat(np.arange(1, 5), 12)
    target = tmp_path / "A01E-changed.mat"
    write_mat(target, objects)
    prepared = data.prepare_subject(files[0], target, 1)
    assert prepared["splits"]["support"]["y"].tolist() == [0] * 12 + [1] * 8
    assert prepared["metadata"]["support_class_counts"] == {"0": 12, "1": 8}


@pytest.mark.parametrize("class_names", [
    ["right hand", "left hand", "feet", "tongue"],
    ["left hand", "right hand", "tongue", "feet"],
    [],
])
def test_original_class_order_must_be_explicit_and_correct(tmp_path, class_names):
    objects = session_objects()
    objects[1]["classes"] = np.asarray(class_names, dtype=object)
    path = tmp_path / "class-order.mat"
    write_mat(path, objects)
    with pytest.raises(ValueError, match="classes"):
        data.load_session(path, 1, "T")


def test_class_name_whitespace_and_underscore_normalization(tmp_path):
    objects = session_objects()
    objects[1]["classes"] = np.asarray([" left_hand ", "right   hand", "feet", "tongue"], dtype=object)
    path = tmp_path / "class-spacing.mat"
    write_mat(path, objects)
    assert len(data.load_session(path, 1, "T")["runs"]) == 6
