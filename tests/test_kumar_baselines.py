"""Scientific access constraints and pickle-free replay on synthetic EEG only."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("kumar_baselines", ROOT / "scripts/run_kumar_baselines.py")
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


def synthetic_input():
    rng = np.random.default_rng(42)
    rows, data, labels = [], [], []
    frequency = np.arange(128) / 128
    for session, runs in (
        ("ses-0", ("source_train", "source_train", "source_validation", "source_query")),
        ("ses-1", ("target_support", "target_query")),
        ("ses-2", ("target_support", "target_query")),
    ):
        for run, role in enumerate(runs):
            for row in range(8):
                label = row % 2
                epoch = rng.normal(scale=0.4, size=(6, 128))
                epoch[label] += 1.5 * np.sin(2 * np.pi * (10 + 4 * label) * frequency)
                labels.append(label)
                data.append(epoch)
                rows.append({"trial_id": f"sub-synthetic/{session}/run-{run}/row-{row + 1}",
                             "session": session, "run": f"run-{run}", "role": role,
                             "cohort": "development"})
    return np.asarray(data), np.asarray(labels), rows


def execute(tmp_path, X=None, y=None, rows=None):
    if X is None:
        X, y, rows = synthetic_input()
    return baseline.run_participant(X, y, rows, subject="sub-synthetic", cohort="development",
                                    output=tmp_path, synthetic=True)


def test_current_only_budget_query_isolation_and_safe_replay(tmp_path):
    X, y, rows = synthetic_input()
    result = execute(tmp_path / "valid", X, y, rows)
    assert len(result["metrics"]) == 9
    forbidden = {r["trial_id"] for r in rows
                 if r["role"] in ("source_query", "target_query", "source_validation")}
    for event in result["fit_events"]:
        assert set(event["trial_ids"]).isdisjoint(forbidden)
        assert all("/ses-0/" in identifier or f"/{event['session']}/" in identifier
                   for identifier in event["trial_ids"])
    for audit in result["audits"]:
        assert audit["parameter_sha256_before"] == audit["parameter_sha256_after"]
        with np.load(tmp_path / "valid" / audit["model_artifact"], allow_pickle=False) as archive:
            arrays = dict(archive)
        indices = [i for i, row in enumerate(rows) if row["trial_id"] in audit["query_trial_ids"]]
        replay = baseline.predict_from_arrays(arrays, X[indices])
        recorded = [p["prediction"] for p in result["predictions"]
                    if p["session"] == audit["session"] and p["method"] == audit["method"]]
        np.testing.assert_array_equal(replay, recorded)
    for session in ("ses-1", "ses-2"):
        target_rows = [r for r in result["metrics"] if r["session"] == session]
        adapted = [r for r in target_rows if r["method"] != "source_only"]
        assert len(adapted) == 2 and {r["n_fit"] for r in adapted} == {24}
        assert {r["n_target_support"] for r in adapted} == {8}
    before = np.load(tmp_path / "valid/source_before.npz", allow_pickle=False)
    after = np.load(tmp_path / "valid/source_after.npz", allow_pickle=False)
    assert baseline.array_digest(dict(before)) == baseline.array_digest(dict(after))
    receipt = json.loads((tmp_path / "valid/participant_receipt.json").read_text())
    assert receipt["synthetic"] and receipt["status"] == "software_validation_only"


def test_query_signal_and_labels_cannot_change_any_fitted_parameters(tmp_path):
    X, y, rows = synthetic_input()
    initial = execute(tmp_path / "original", X, y, rows)
    forbidden = [i for i, row in enumerate(rows)
                 if row["role"] in ("source_query", "target_query", "source_validation")]
    X[forbidden] *= 17
    y[forbidden] = 1 - y[forbidden]
    changed = execute(tmp_path / "altered", X, y, rows)
    assert [r["model_parameter_sha256"] for r in initial["metrics"]] == [
        r["model_parameter_sha256"] for r in changed["metrics"]
    ]
    assert initial["fit_events"] == changed["fit_events"]


def test_duplicate_identity_and_run_role_leakage_rejected(tmp_path):
    X, y, rows = synthetic_input()
    rows[-1]["trial_id"] = rows[0]["trial_id"]
    with pytest.raises(ValueError, match="Duplicate trial"):
        execute(tmp_path / "duplicate", X, y, rows)
    X, y, rows = synthetic_input()
    rows[0]["role"] = "source_query"
    with pytest.raises(ValueError, match="run spans"):
        execute(tmp_path / "overlap", X, y, rows)


def test_single_frozen_configuration_and_all_class_recalls(tmp_path):
    X, y, rows = synthetic_input()
    with pytest.raises(ValueError, match="one frozen CSP"):
        baseline.run_participant(X, y, rows, subject="synthetic", cohort="development",
                                 output=tmp_path / "wrong", synthetic=True, n_components=6)
    metrics = baseline.summarize_predictions(np.asarray([0, 0, 1, 1]), np.asarray([0, 0, 0, 0]))
    assert metrics["balanced_accuracy"] == 0.5
    assert metrics["recall_left_hand"] == 1
    assert metrics["recall_right_hand"] == 0
    assert metrics["class_collapse"]


def test_approval_binds_configuration_and_manifest(tmp_path):
    config = tmp_path / "config.json"
    manifest = tmp_path / "manifest.json"
    protocol = tmp_path / "protocol.md"
    source = tmp_path / "source.json"
    for path in (config, manifest, protocol, source):
        path.write_text("synthetic fixture only\n")
    approval_path = tmp_path / "approval.json"
    approval = {"status": "approved_for_baseline_execution",
                "config_sha256": baseline.file_sha256(config),
                "split_manifest_sha256": baseline.file_sha256(manifest),
                "protocol_path": str(protocol), "protocol_sha256": baseline.file_sha256(protocol),
                "source_gate_receipt_path": str(source),
                "source_gate_receipt_sha256": baseline.file_sha256(source)}
    approval_path.write_text(json.dumps(approval))
    assert baseline.approval_gate(config, manifest, approval_path) == approval
    config.write_text("changed")
    with pytest.raises(ValueError, match="config_sha256"):
        baseline.approval_gate(config, manifest, approval_path)
    arrays = {"forbidden": np.asarray([{}], dtype=object)}
    with pytest.raises(ValueError, match="Object arrays"):
        baseline.array_digest(arrays)


def test_frozen_descriptive_features_fit_source_train_and_replay(tmp_path):
    _, y, rows = synthetic_input()
    rng = np.random.default_rng(17)
    time = np.arange(640) / 128
    X = rng.normal(scale=1e-6, size=(len(rows), 22, 640))
    for index, label in enumerate(y):
        X[index, 9 + 2 * label] += 3e-6 * np.sin(2 * np.pi * (10 + 10 * label) * time)
    X -= X.mean(axis=1, keepdims=True)
    initial_path, changed_path = tmp_path / "initial", tmp_path / "changed"
    initial_path.mkdir()
    changed_path.mkdir()
    initial = baseline.descriptive_features(X, y, rows, subject="synthetic", cohort="development",
                                            output=initial_path, synthetic=True)
    nontrain = [i for i, row in enumerate(rows) if row["role"] != "source_train"]
    X[nontrain] *= 20
    y[nontrain] = 1 - y[nontrain]
    changed = baseline.descriptive_features(X, y, rows, subject="synthetic", cohort="development",
                                            output=changed_path, synthetic=True)
    assert initial["source_fit_parameter_sha256_before"] == changed[
        "source_fit_parameter_sha256_before"]
    assert initial["query_state_unchanged"] and initial["target_support_and_query_never_fitted"]
    assert all("/ses-0/run-0/" in trial or "/ses-0/run-1/" in trial
               for trial in initial["fit_trial_ids"])
    with np.load(initial_path / "fixed_features.npz", allow_pickle=False) as features:
        with np.load(initial_path / "feature_source_fit.npz", allow_pickle=False) as state:
            replay = ((features["log10_bandpower_44"] - state["scaler_mean"])
                      / state["scaler_scale"] - state["pca_mean"]) @ state["pca_components"].T
            np.testing.assert_allclose(replay, features["source_pca4"], rtol=1e-12, atol=1e-12)
            assert features["covariance_21"].shape == (len(rows), 21, 21)
            assert np.linalg.eigvalsh(features["covariance_21"]).min() > 0
            np.testing.assert_allclose(np.trace(features["covariance_21"], axis1=1, axis2=2), 1)
            np.testing.assert_allclose(state["helmert_basis"] @ np.ones(22), 0, atol=1e-14)
    assert initial["feature_order"][:4] == ["F7_mu", "F7_beta", "F3_mu", "F3_beta"]


def test_participant_endpoint_bootstrap_uses_participants_not_trials():
    rows = []
    for subject, cohort, offset in (("sub-1", "development", 0.1),
                                    ("sub-2", "final_test", 0.2),
                                    ("sub-3", "final_test", -0.1)):
        for method in baseline.METHODS:
            for session in range(6):
                gain = offset if method == "refit_csp_lda" and session else 0
                rows.append({"subject": subject, "cohort": cohort, "method": method,
                             "session": f"ses-{session}", "balanced_accuracy": 0.5 + gain,
                             "n_query": 17 + 100 * session, "class_collapse": False})
    endpoints, summary = baseline.participant_bootstrap_summary(rows, replicates=1000)
    assert len(endpoints) == 9
    final = summary["cohorts"]["final_test"]
    assert final["n_participants"] == 2
    primary = final["paired_comparisons"]["refit_csp_lda_minus_source_only"]
    assert primary["mean_difference"] == pytest.approx(0.05)
    assert primary["ci95"] == pytest.approx([-0.1, 0.2])
    assert primary["participants_positive"] == 1
    assert primary["participants_negative"] == 1
