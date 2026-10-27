"""Synthetic inputs test external fit/evaluation identity and resumability.

All fixtures are synthetic software checks. No official EEG is downloaded.
"""

import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.external_validation_20261027 import runner  # noqa: E402
from hpc_recalibration.data import Split, save_split, sha256_file  # noqa: E402


@pytest.fixture
def experiment(tmp_path):
    root = tmp_path / "synthetic-external"
    config = runner.make_config(root)
    task_id = "bnci001-sub-01"
    rng = np.random.default_rng(20261027)
    names, hashes = {}, {}
    for role, n, session, run in (("source_train", 40, "T", "1-4"),
                                  ("support", 20, "E", "1"),
                                  ("query", 24, "E", "2")):
        y = np.tile([0, 1], n // 2)
        x = rng.normal(size=(n, 6, 80)).astype(np.float32)
        x[y == 1, 0] *= 1.8
        split = Split(x, y, np.asarray([f"synthetic/1/{session}/{role}/{i}" for i in range(n)]),
                      np.full(n, f"synthetic/{session}/run-{run}"))
        name = f"{task_id}/{role}.npz"
        path = Path(config["data_root"]) / name
        save_split(path, split)
        names[role] = name
        hashes[name] = sha256_file(path)
    task = {"task_id": task_id, "dataset": "synthetic_software_validation_only",
            "participant": "1", "family": "classical", "seed": 20261027,
            "source_train": names["source_train"], "targets": [{
                "session": "E", "support": names["support"], "query": names["query"]}],
            "input_sha256": hashes, "synthetic": True}
    cache = Path(config["data_root"]) / task_id / "input_check_cache.json"
    runner.check_inputs(task, config, cache)
    assert runner.classical.run_task(task, config) == 0
    return root, config, task, cache


def models_for(root, task):
    directory = root / "results/tasks" / task["task_id"]
    return directory, {
        method: runner.classical.Decoder.load(directory / "models" / f"E__n20__{method}.npz")
        for method in runner.METHODS
    }


def test_all_arms_share_query_and_updating_arms_share_source_support_ids(experiment):
    root, _, task, _ = experiment
    directory, models = models_for(root, task)
    evaluations = [json.loads((directory / "evaluation" / f"E__n20__{method}.json").read_text())
                   for method in runner.METHODS]
    assert all(row["trial_ids"] == evaluations[0]["trial_ids"] for row in evaluations)
    assert all(row["y"] == evaluations[0]["y"] for row in evaluations)
    for method in ("lda_only", "full_csp", "ea_csp"):
        assert models[method].metadata["fit_trial_ids"] == models["full_csp"].metadata["fit_trial_ids"]
        assert models[method].metadata["support_trial_ids"] == models["full_csp"].metadata["support_trial_ids"]
        assert not set(evaluations[0]["trial_ids"]) & set(models[method].metadata["fit_trial_ids"])
    assert len(models["frozen"].metadata["fit_trial_ids"]) == 40
    assert models["frozen"].metadata["support_trial_ids"] == []
    assert models["ea_csp"].metadata["ea_reference_scope"] == "source/current_support_only"
    np.testing.assert_array_equal(models["frozen"].filters, models["lda_only"].filters)
    assert not np.array_equal(models["frozen"].filters, models["full_csp"].filters)


def test_completed_resume_does_not_refit_or_rewrite_outputs(experiment, monkeypatch):
    root, config, task, cache = experiment
    directory, _ = models_for(root, task)
    files = {str(path): sha256_file(path) for path in directory.rglob("*") if path.is_file()}

    def unexpected_fit(*args, **kwargs):
        raise AssertionError("A completed identity must not refit")

    monkeypatch.setattr(runner.classical, "fit_decoder", unexpected_fit)
    runner.check_inputs(task, config, cache)
    assert runner.classical.run_task(task, config) == 0
    assert files == {str(path): sha256_file(path) for path in directory.rglob("*") if path.is_file()}


def test_input_change_stops_before_completed_evaluation_reuse(experiment, monkeypatch):
    root, config, task, cache = experiment
    query_path = Path(config["data_root"]) / task["targets"][0]["query"]
    with np.load(query_path, allow_pickle=False) as values:
        altered = {name: values[name].copy() for name in values.files}
    altered["x"][0, 0, 0] += 1
    runner.classical.atomic_npz(query_path, **altered)
    directory, _ = models_for(root, task)
    completed_hash = sha256_file(directory / "complete.json")
    monkeypatch.setattr(runner.classical, "fit_decoder", lambda *a, **k: pytest.fail("refit"))
    with pytest.raises(ValueError, match="Prepared input changed"):
        runner.check_inputs(task, config, cache)
    assert sha256_file(directory / "complete.json") == completed_hash


def test_analyze_recomputes_saved_predictions_without_forward(experiment, monkeypatch):
    root, _, task, _ = experiment
    directory, _ = models_for(root, task)
    monkeypatch.setattr(runner.classical.Decoder, "predict", lambda *a, **k: pytest.fail("forward"))
    result = runner.analyze(root)
    assert result["status"] == "partial"  # This fixture is one of the fixed nine.
    assert result["synthetic"] and result["software_validation_only"]
    assert result["contrasts"] == {}
    assert len(result["participant_results"]) == 4
    audit = json.loads((root / "results/prediction_audit.json").read_text())
    assert audit["verified_evaluations"] == 4
    evaluation = directory / "evaluation/E__n20__full_csp.json"
    row = json.loads(evaluation.read_text())
    row["metrics"]["balanced_accuracy"] += 0.01
    runner.atomic_json(evaluation, row)
    with pytest.raises(ValueError, match="Saved prediction metrics"):
        runner.analyze(root)


@pytest.mark.parametrize("mutation", ["query_ids", "fit_ids", "frozen_filter"])
def test_analyze_rejects_arm_identity_and_component_mismatches(experiment, mutation):
    root, _, task, _ = experiment
    directory, models = models_for(root, task)
    if mutation == "query_ids":
        path = directory / "evaluation/E__n20__ea_csp.json"
        row = json.loads(path.read_text())
        row["trial_ids"][0] += "/different"
        runner.atomic_json(path, row)
    elif mutation == "fit_ids":
        model = models["lda_only"]
        model.metadata["fit_trial_ids"][0] += "/different"
        model.save(directory / "models/E__n20__lda_only.npz")
    else:
        model = models["lda_only"]
        model.filters[0, 0] += 0.01
        model.save(directory / "models/E__n20__lda_only.npz")
    with pytest.raises(ValueError):
        runner.analyze(root)


def test_scientific_settings_change_does_not_reuse_completed_outputs(experiment):
    _, config, task, _ = experiment
    config["classical"]["covariance_shrinkage"] = 0.2
    with pytest.raises(ValueError, match="completed task science changed"):
        runner.classical.run_task(task, config)


def test_analyze_rejects_different_query_labels_even_if_metrics_are_recomputed(experiment):
    root, _, task, _ = experiment
    directory, _ = models_for(root, task)
    path = directory / "evaluation/E__n20__ea_csp.json"
    row = json.loads(path.read_text())
    row["y"] = [1 - value for value in row["y"]]
    row["metrics"] = runner.classical.score_predictions(
        np.asarray(row["y"]), np.asarray(row["prediction"]), np.asarray([0, 1]))
    runner.atomic_json(path, row)
    with pytest.raises(ValueError):
        runner.analyze(root)


def test_analyze_rejects_ea_fit_trial_mismatch(experiment):
    root, _, task, _ = experiment
    directory, models = models_for(root, task)
    model = models["ea_csp"]
    model.metadata["fit_trial_ids"][0] += "/different"
    model.save(directory / "models/E__n20__ea_csp.npz")
    with pytest.raises(ValueError):
        runner.analyze(root)
