"""Synthetic-only checks for the new independent NumPy comparators."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"))
from hpc_recalibration import classical, data  # noqa: E402


def split(prefix, n=12, seed=0, labels=None):
    rng = np.random.default_rng(seed)
    y = np.asarray([i % 2 for i in range(n)] if labels is None else labels, dtype=np.int64)
    x = rng.normal(size=(n, 4, 96)).astype(np.float32)
    x[y == 0, 0] *= 3
    x[y == 1, 1] *= 3
    return data.Split(x, y, np.asarray([f"{prefix}/trial-{i}" for i in range(n)]),
                      np.asarray([prefix] * n))


def task_files(tmp_path):
    datasets = {"train": split("sub-1/ses-0/run-0", 12, 1),
                "validation": split("sub-1/ses-0/run-1", 6, 2),
                "source_query": split("sub-1/ses-0/run-2", 8, 3),
                "support": split("sub-1/ses-1/run-0", 8, 4),
                "query": split("sub-1/ses-1/run-1", 10, 5)}
    for name, value in datasets.items():
        data.save_split(tmp_path / f"{name}.npz", value)
    task = {"task_id": "synthetic-classical", "dataset": "synthetic", "participant": "sub-1",
            "seed": 1, "family": "classical", "synthetic": True,
            "source_train": "train.npz", "source_validation": "validation.npz",
            "source_query": "source_query.npz",
            "targets": [{"session": "ses-1", "support": "support.npz", "query": "query.npz"}]}
    config = {"experiment_id": "synthetic-only", "data_root": str(tmp_path),
              "output_root": str(tmp_path / "outputs"), "budgets": [4, 8],
              "heartbeat_seconds": 30, "classical_methods": list(classical.METHODS)}
    return task, config, datasets


def test_generic_data_and_once_hash_preflight(tmp_path):
    task, _, _ = task_files(tmp_path)
    report = data.validate_task_inputs(task, tmp_path)
    assert report["channels"] == 4
    assert report["class_count"] == 2
    assert len(report["files"]) == 5
    assert all(len(f["sha256"]) == 64 and f["size"] > 0 for f in report["files"])
    assert report["whole_run_disjoint"]
    assert not data.validate_task_inputs(task, tmp_path, full_sha=False)["files"][0].get("sha256")


def test_first_preflight_rejects_changed_valid_npz_against_frozen_hash(tmp_path):
    task, _, datasets = task_files(tmp_path)
    task["input_sha256"] = {name: data.sha256_file(tmp_path / name)
                            for _, _, name in data.task_inputs(task)}
    data.validate_task_inputs(task, tmp_path)
    original = datasets["train"]
    altered = original.x.copy()
    altered[0, 0, 0] += np.float32(0.125)
    data.save_split(tmp_path / "train.npz", data.Split(
        altered, original.y, original.trial_id, original.run_id))
    with pytest.raises(ValueError, match="Frozen input SHA256 mismatch: train.npz"):
        data.validate_task_inputs(task, tmp_path)


def test_frozen_hash_map_requires_every_task_role(tmp_path):
    task, _, _ = task_files(tmp_path)
    task["input_sha256"] = {name: data.sha256_file(tmp_path / name)
                            for _, _, name in data.task_inputs(task) if name != "query.npz"}
    with pytest.raises(ValueError, match="Missing frozen SHA256.*query.npz"):
        data.validate_task_inputs(task, tmp_path)


def test_whole_run_leakage_rejected(tmp_path):
    task, _, datasets = task_files(tmp_path)
    q = datasets["query"]
    q = data.Split(q.x, q.y, q.trial_id, np.asarray(["sub-1/ses-1/run-0"] * len(q)))
    data.save_split(tmp_path / "query.npz", q)
    with pytest.raises(ValueError, match="whole-run leakage"):
        data.validate_task_inputs(task, tmp_path)


def test_duplicate_trial_and_unknown_class_rejected(tmp_path):
    task, _, datasets = task_files(tmp_path)
    q = datasets["query"]
    ids = q.trial_id.copy()
    ids[0] = datasets["train"].trial_id[0]
    data.save_split(tmp_path / "query.npz", data.Split(q.x, q.y, ids, q.run_id))
    with pytest.raises(ValueError, match="trial leakage"):
        data.validate_task_inputs(task, tmp_path)
    data.save_split(tmp_path / "query.npz", data.Split(q.x, np.full(len(q), 2), q.trial_id, q.run_id))
    with pytest.raises(ValueError, match="class absent"):
        data.validate_task_inputs(task, tmp_path)


@pytest.mark.parametrize("method", classical.METHODS)
def test_fit_no_query_inputs_and_saved_state(method, tmp_path):
    source, support, query = split("source"), split("support", 8, 6), split("query", 10, 7)
    model = classical.fit_decoder(source, support, method, {})
    before = {k: v.copy() for k, v in vars(model).items() if isinstance(v, np.ndarray)}
    prediction = model.predict(query.x)
    reversed_y = query.y[::-1]
    classical.score_predictions(reversed_y, prediction, model.classes)
    for key, value in before.items():
        np.testing.assert_array_equal(getattr(model, key), value)
    assert not set(model.metadata["fit_trial_ids"]) & set(query.trial_id.tolist())
    assert model.metadata["query_used_for_fitting"] is False
    assert model.metadata["historical_MNE_model_reproduction"] is False
    model.save(tmp_path / "model.npz")
    np.testing.assert_array_equal(classical.Decoder.load(tmp_path / "model.npz").predict(query.x), prediction)


def test_single_class_support_retained_and_empirical_returns_source_when_n1():
    source = split("source", 20, 4)
    support = split("support", 1, 5, labels=[0])
    for method in classical.METHODS:
        model = classical.fit_decoder(source, support, method, {})
        assert len(model.predict(source.x)) == len(source)
        if method in ("empirical_anchored_csp", "ea_empirical_anchored_csp"):
            assert model.metadata["classwise_update_weights"] == {"0": 0.0, "1": 0.0}


def test_empirical_variance_has_n_times_nminus1_denominator():
    source, support = split("source", 20, 7), split("support", 8, 8)
    model = classical.fit_decoder(source, support, "empirical_anchored_csp", {})
    sc, tc = classical.trial_covariances(source.x), classical.trial_covariances(support.x)
    for c in (0, 1):
        values = tc[support.y == c]
        mean = values.mean(0)
        n = len(values)
        variance = np.sum((values - mean) ** 2) / (n * (n - 1))
        difference = np.sum((mean - sc[source.y == c].mean(0)) ** 2)
        expected = max(0.0, 1 - variance / difference) if difference > 0 else 0
        assert model.metadata["classwise_update_weights"][str(c)] == pytest.approx(expected)


def test_ea_candidate_and_comparator_have_identical_alignment():
    source, support = split("source", 20, 13), split("support", 8, 14)
    reference = classical.fit_decoder(source, support, "ea_csp", {})
    candidate = classical.fit_decoder(source, support, "ea_empirical_anchored_csp", {})
    np.testing.assert_array_equal(reference.query_whitener, candidate.query_whitener)
    assert candidate.metadata["ea_reference_scope"] == "source/current_support_only"


def test_missing_query_class_undefined_not_silently_dropped():
    result = classical.score_predictions(np.array([0, 0]), np.array([0, 1]), np.array([0, 1]))
    assert result["balanced_accuracy"] is None
    assert result["class_counts"] == {"0": 2, "1": 0}
    assert result["status"] == "undefined_missing_query_class"


def test_evaluation_failure_resumes_without_any_refit(tmp_path, monkeypatch):
    task, config, _ = task_files(tmp_path)
    original_json = classical.atomic_json
    failed = False

    def fail_first_evaluation(path, value):
        nonlocal failed
        if Path(path).parent.name == "evaluation" and not failed:
            failed = True
            raise OSError("synthetic write failure")
        original_json(path, value)

    monkeypatch.setattr(classical, "atomic_json", fail_first_evaluation)
    with pytest.raises(OSError, match="synthetic write failure"):
        classical.run_task(task, config)
    task_root = Path(config["output_root"]) / "tasks" / task["task_id"]
    assert list(task_root.glob("failure_*.json"))
    assert len(list((task_root / "models").glob("*.npz"))) == 16
    assert not (task_root / "complete.json").exists()
    monkeypatch.setattr(classical, "atomic_json", original_json)
    monkeypatch.setattr(classical, "fit_decoder", lambda *a, **k: pytest.fail("must reuse saved fit"))
    assert classical.run_task(task, config) == 0
    completion = json.loads((task_root / "complete.json").read_text())
    assert len(completion["summary"]) == 17
    assert completion["software_validation_only"]
    assert classical.run_task(task, config) == 0


def test_all_fits_precede_first_query_array_load(tmp_path, monkeypatch):
    task, config, _ = task_files(tmp_path)
    original_load, original_fit = classical.load_split, classical.fit_decoder
    seen_query = False

    def load(path):
        nonlocal seen_query
        if Path(path).name in ("query.npz", "source_query.npz"):
            seen_query = True
        return original_load(path)

    def fit(*args, **kwargs):
        assert not seen_query, "No fits may follow a query-array load in the same task"
        return original_fit(*args, **kwargs)

    monkeypatch.setattr(classical, "load_split", load)
    monkeypatch.setattr(classical, "fit_decoder", fit)
    assert classical.run_task(task, config) == 0
    assert seen_query


def test_legacy_cache_export_exact_manifest_join_and_resume(tmp_path):
    role_groups = [("ses-0", "run-0", "source_train", 8),
                   ("ses-0", "run-1", "source_validation", 4),
                   ("ses-0", "run-2", "source_query", 4),
                   ("ses-1", "run-0", "target_support", 4),
                   ("ses-1", "run-1", "target_query", 4)]
    records, xs, ys, ids = [], [], [], []
    for index, (session, run, role, n) in enumerate(role_groups):
        block = split(f"sub-1/{session}/{run}", n, index)
        for j in range(n):
            trial_id = str(block.trial_id[j])
            epoch = block.x[j]
            records.append({"included": True, "subject": "sub-1", "session": session,
                            "run": run, "role": role, "trial_id": trial_id,
                            "source_row": j + 1, "start_sample": j * 100,
                            "label": "left_hand" if block.y[j] == 0 else "right_hand",
                            "processed_window_numeric_sha256": hashlib.sha256(epoch.astype("<f4").tobytes()).hexdigest()})
            xs.append(epoch)
            ys.append(block.y[j])
            ids.append(trial_id)
    manifest = tmp_path / "split.json"
    manifest.write_text(json.dumps({"trials": records}))
    cache = tmp_path / "old_cache.npz"
    # Deliberately reverse cache order; manifest controls chronology.
    np.savez_compressed(cache, X=np.stack(xs[::-1]), y=np.array(ys[::-1]), trial_ids=np.array(ids[::-1]))
    output = tmp_path / "prepared"
    tasks = data.export_legacy_cache(manifest, [cache], output)
    assert len(tasks) == 1
    report = data.validate_task_inputs(tasks[0], output)
    assert report["channels"] == 4
    prepared = data.load_split(output / tasks[0]["source_train"])
    assert prepared.trial_id.tolist() == ids[:8]
    assert data.export_legacy_cache(manifest, [cache], output) == tasks


def test_missing_legacy_roles_never_fabricated(tmp_path):
    manifest = tmp_path / "split.json"
    manifest.write_text(json.dumps({"trials": [{"included": True, "subject": "sub-1", "session": "ses-0",
        "run": "run-0", "role": "source_train", "trial_id": "wanted", "label": "left_hand"}]}))
    cache = tmp_path / "incomplete.npz"
    np.savez_compressed(cache, X=np.ones((1, 4, 10), np.float32), y=np.array([0]), trial_ids=np.array(["different"]))
    with pytest.raises(ValueError, match="Caches lack"):
        data.export_legacy_cache(manifest, [cache], tmp_path / "prepared")
    assert not (tmp_path / "prepared").exists()


@pytest.mark.parametrize("stop_signal,expected_code", [(10, 75), (15, 130)])
def test_signal_after_source_fit_does_not_start_an_extra_fit(tmp_path, monkeypatch, stop_signal, expected_code):
    import os
    import signal
    task, config, _ = task_files(tmp_path)
    original = classical.fit_decoder
    calls = []

    def fit(*args, **kwargs):
        calls.append(args[2])
        model = original(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGUSR1 if stop_signal == 10 else signal.SIGTERM)
        return model

    monkeypatch.setattr(classical, "fit_decoder", fit)
    assert classical.run_task(task, config) == expected_code
    root = Path(config["output_root"]) / "tasks" / task["task_id"]
    assert calls == ["frozen"]
    assert (root / "source_model.npz").is_file()
    assert not list((root / "models").glob("*.npz"))
    assert not (root / "complete.json").exists()
    assert json.loads((root / "progress.json").read_text())["exit_code"] == expected_code


def test_fixed_ea_anchor_is_same_alignment_single_factor_control():
    source, support = split("source", 20, 23), split("support", 8, 24)
    fixed = classical.fit_decoder(source, support, "ea_anchored_csp", {})
    empirical = classical.fit_decoder(source, support, "ea_empirical_anchored_csp", {})
    reference = classical.fit_decoder(source, support, "ea_csp", {})
    np.testing.assert_array_equal(fixed.query_whitener, empirical.query_whitener)
    np.testing.assert_array_equal(fixed.query_whitener, reference.query_whitener)
    assert fixed.metadata["classwise_update_weights"] == {"0": 8 / 28, "1": 8 / 28}
    assert fixed.metadata["ea_reference_scope"] == "source/current_support_only"


def test_completion_schema_matches_progress_monitor(tmp_path):
    task, config, _ = task_files(tmp_path)
    config["classical_methods"] = ["frozen"]
    config["budgets"] = [4]
    assert classical.run_task(task, config) == 0
    root = Path(config["output_root"]) / "tasks" / task["task_id"]
    assert json.loads((root / "complete.json").read_text())["status"] == "completed"
    assert json.loads((root / "progress.json").read_text())["phase"] == "completed"
    assert json.loads((root / "progress.json").read_text())["updated_at"]
    assert len(json.loads((root / "summary.json").read_text())["results"]) == 2
