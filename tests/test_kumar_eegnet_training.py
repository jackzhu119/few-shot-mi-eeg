"""CPU EEGNet software safeguards on synthetic inputs; no scientific accuracy tests."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("braindecode")
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("kumar_eegnet", ROOT / "scripts/train_kumar_eegnet.py")
training = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(training)
pytestmark = pytest.mark.deep


@pytest.fixture
def config():
    torch.set_num_threads(1)
    value = json.loads(training.DEFAULT_CONFIG.read_text())
    value["optimization"]["max_epochs"] = 2
    value["optimization"]["early_stopping"]["patience"] = 2
    return value


@pytest.fixture
def source(config):
    return training.synthetic_source(config)


@pytest.fixture
def fitted(config, source):
    return training.SourceOnlyEEGNet(config, 123).fit_source(*source)


def test_cpu_forward_backward_source_normalizer_and_query_eval_are_frozen(fitted, source):
    X_train, _, X_validation, _, train_rows, validation_rows = source
    assert fitted.architecture_ == "braindecode.models.EEGNet"
    assert next(fitted.model_.parameters()).device.type == "cpu"
    assert fitted.optimizer_steps_ == 2
    assert all(np.isfinite(row["source_train_loss"]) for row in fitted.history_)
    assert any(p.grad is not None and torch.isfinite(p.grad).all()
               and torch.count_nonzero(p.grad) > 0 for p in fitted.model_.parameters())
    np.testing.assert_array_equal(fitted.channel_mean_, X_train.mean(axis=(0, 2), keepdims=True))
    np.testing.assert_array_equal(fitted.channel_scale_, X_train.std(axis=(0, 2), keepdims=True)
                                  .clip(min=1e-8))
    assert fitted.source_train_ids_ == [row["trial_id"] for row in train_rows]
    assert fitted.source_validation_ids_ == [row["trial_id"] for row in validation_rows]
    before = training.state_digest(fitted)
    steps = fitted.optimizer_steps_
    query = X_validation * 50 + 0.005
    first = fitted.predict_proba(query)
    second = fitted.predict_proba(query)
    assert first.shape == (8, 2) and np.isfinite(first).all()
    np.testing.assert_allclose(first.sum(axis=1), 1, atol=1e-6)
    np.testing.assert_array_equal(first, second)
    assert not fitted.model_.training
    assert all(not layer.training for layer in fitted.model_.modules()
               if isinstance(layer, torch.nn.modules.batchnorm._BatchNorm))
    assert fitted.optimizer_steps_ == steps
    assert training.state_digest(fitted) == before


@pytest.mark.parametrize("violation", ["query_role", "validation_run", "duplicate_id", "subject"])
def test_leaking_source_metadata_is_rejected_before_model_or_optimizer(config, source, monkeypatch,
                                                                     violation):
    parts = list(copy.deepcopy(source))
    if violation == "query_role":
        parts[4][0]["role"] = "source_query"
    elif violation == "validation_run":
        parts[5][0]["run"] = "run-0"
    elif violation == "duplicate_id":
        parts[5][0]["trial_id"] = parts[4][0]["trial_id"]
    else:
        parts[5][0]["subject"] = "synthetic-sub-2"
    model = training.SourceOnlyEEGNet(config, 123)
    monkeypatch.setattr(model, "_build_model", lambda: pytest.fail("Model built before split guard"))
    with pytest.raises(ValueError):
        model.fit_source(*parts)


def test_query_arrays_and_labels_are_absent_from_source_fit(config, source):
    X_train, y_train, X_validation, y_validation, train_rows, validation_rows = source
    query_rows = [dict(train_rows[0], role="target_query", session="ses-1", run="run-1",
                       trial_id="synthetic/target/query-0")]
    subject = SimpleNamespace(X=np.concatenate([X_train, X_validation, X_train[:1]]),
                              y=np.concatenate([y_train, y_validation, y_train[:1]]),
                              metadata=train_rows + validation_rows + query_rows)
    original = training.source_arrays(subject)
    subject.X[-1] += 100
    subject.y[-1] = 1 - subject.y[-1]
    changed = training.source_arrays(subject)
    for before, after in zip(original[:4], changed[:4]):
        np.testing.assert_array_equal(before, after)
    first = training.SourceOnlyEEGNet(config, 123).fit_source(*original)
    second = training.SourceOnlyEEGNet(config, 123).fit_source(*changed)
    assert training.state_digest(first) == training.state_digest(second)
    assert query_rows[0]["trial_id"] not in first.source_train_ids_ + first.source_validation_ids_


def test_validation_can_select_epoch_but_never_updates_optimizer_bn_or_normalizer(config, source,
                                                                                monkeypatch):
    config["optimization"]["max_epochs"] = 7
    config["optimization"]["early_stopping"]["patience"] = 2
    model = training.SourceOnlyEEGNet(config, 123)
    original_validation = model._validation_loss
    losses = iter([0.7, 0.8, 0.9])
    validation_states = []

    def validation_loss(X, y):
        state, steps = training.state_digest(model), model.optimizer_steps_
        gradients = [None if p.grad is None else p.grad.clone() for p in model.model_.parameters()]
        assert np.isfinite(original_validation(X, y))
        assert training.state_digest(model) == state and model.optimizer_steps_ == steps
        for param, previous in zip(model.model_.parameters(), gradients):
            assert previous is None and param.grad is None or torch.equal(param.grad, previous)
        validation_states.append(state)
        return next(losses)

    monkeypatch.setattr(model, "_validation_loss", validation_loss)
    model.fit_source(*source)
    assert len(model.history_) == 3 and model.selected_epoch_ == 1
    assert model.selected_validation_loss_ == 0.7
    assert model.optimizer_steps_ == 3 * math.ceil(len(source[0]) / model.batch_size)
    assert training.state_digest(model) == validation_states[0]
    changed = list(source)
    changed[2] = source[2] + 0.001
    changed[3] = 1 - source[3]
    replica = training.SourceOnlyEEGNet(config, 123).fit_source(*changed)
    np.testing.assert_array_equal(model.channel_mean_, replica.channel_mean_)
    np.testing.assert_array_equal(model.channel_scale_, replica.channel_scale_)


def test_same_seed_and_safe_checkpoint_replay_bind_configuration_and_selection(config, source,
                                                                             fitted, tmp_path,
                                                                             monkeypatch):
    replica = training.SourceOnlyEEGNet(config, 123).fit_source(*source)
    assert training.state_digest(fitted) == training.state_digest(replica)
    path = tmp_path / "weights.pt"
    receipt = training.save_checkpoint(fitted, path, synthetic=True, software_validation_only=True)
    safe_load = torch.load
    calls = []

    def checked_load(*args, **kwargs):
        calls.append(kwargs)
        return safe_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", checked_load)
    monkeypatch.setattr(torch.optim, "Adam", lambda *a, **k: pytest.fail("Optimizer created on load"))
    restored = training.load_checkpoint(path, expected_sha256=receipt["checkpoint_sha256"])
    assert calls == [{"map_location": "cpu", "weights_only": True}]
    assert restored.config == config and restored.seed == 123
    assert restored.selected_epoch_ == fitted.selected_epoch_
    assert restored.source_train_ids_ == fitted.source_train_ids_
    assert restored.history_ == fitted.history_
    assert receipt["synthetic"] and receipt["software_validation_only"]
    assert receipt["config_canonical_sha256"] == training.canonical_sha256(config)
    assert training.state_digest(restored) == training.state_digest(fitted)
    np.testing.assert_array_equal(restored.predict_proba(source[2]), fitted.predict_proba(source[2]))
    with pytest.raises(FileExistsError):
        training.save_checkpoint(fitted, path, synthetic=True, software_validation_only=True)


@pytest.mark.parametrize("tamper", ["bytes", "config", "seed", "selected_epoch", "source_ids"])
def test_checkpoint_or_sidecar_tampering_is_rejected(fitted, tmp_path, monkeypatch, tamper):
    path = tmp_path / "weights.pt"
    saved = training.save_checkpoint(fitted, path, synthetic=True, software_validation_only=True)
    if tamper == "bytes":
        path.write_bytes(path.read_bytes() + b"changed")
        monkeypatch.setattr(torch, "load", lambda *a, **k: pytest.fail("Loaded before SHA guard"))
        expected_message = "SHA256 mismatch"
    else:
        receipt = json.loads(path.with_suffix(".json").read_text())
        if tamper == "config":
            receipt["config"]["optimization"]["learning_rate"] = 0.02
        elif tamper == "source_ids":
            receipt["source_train_ids"][0] = "forbidden-query-id"
        else:
            receipt[tamper] += 1
        path.with_suffix(".json").write_text(json.dumps(receipt))
        expected_message = "context mismatch"
    with pytest.raises(ValueError, match=expected_message):
        training.load_checkpoint(path, expected_sha256=saved["checkpoint_sha256"])


@pytest.mark.parametrize("setting", ["normalizer", "BN", "optimizer", "learning_rate", "labels"])
def test_promised_frozen_settings_and_class_labels_are_enforced(config, source, setting):
    if setting == "normalizer":
        config["normalization"]["target_fit"] = True
    elif setting == "BN":
        config["inference"]["batch_norm_updates"] = True
    elif setting == "optimizer":
        config["optimization"]["scheduler"] = "unsupported"
    elif setting == "learning_rate":
        config["optimization"]["learning_rate"] = -1
    else:
        parts = list(source)
        parts[1] = parts[1].astype(float) + 0.1
        with pytest.raises(ValueError, match="frozen classes"):
            training.SourceOnlyEEGNet(config, 123).fit_source(*parts)
        return
    with pytest.raises(ValueError):
        training.SourceOnlyEEGNet(config, 123)


def test_formal_training_is_pending_and_blocked_before_any_output(config, tmp_path):
    assert config["freeze"]["ready_for_formal_training"] is False
    output = tmp_path / "formal"
    with pytest.raises(ValueError, match="Formal training is Pending"):
        training.formal_train(config, training.DEFAULT_CONFIG, tmp_path / "missing_data", output)
    assert not output.exists()


def test_freeze_receipts_bind_protocol_manifest_and_non_self_referential_configuration(config,
                                                                                     tmp_path,
                                                                                     monkeypatch):
    monkeypatch.setattr(training, "ROOT", tmp_path)
    config["freeze"]["ready_for_formal_training"] = True
    config["protocol_config"] = "protocol.json"
    config["split_manifest"] = "splits.json"
    (tmp_path / "protocol.json").write_text('{"frozen": true}')
    (tmp_path / "splits.json").write_text('{"trials": []}')
    config["freeze"]["protocol_config_sha256"] = training.sha256_file(tmp_path / "protocol.json")
    config["freeze"]["split_manifest_sha256"] = training.sha256_file(tmp_path / "splits.json")
    config["freeze"]["frozen_training_config_sha256"] = training.canonical_sha256(config)
    path = tmp_path / "test_config.json"
    path.write_text(json.dumps(config))
    path.with_suffix(".sha256").write_text(training.sha256_file(path))
    # Validate the gate only: this test never executes formal training.
    training.check_formal_freeze(config, path)
    config["optimization"]["learning_rate"] = 0.02
    with pytest.raises(ValueError, match="detached SHA256"):
        training.check_formal_freeze(config, path)
    (tmp_path / "splits.json").write_text('{"changed": true}')
    with pytest.raises(ValueError, match="split_manifest_sha256"):
        training.check_formal_freeze(config, path)


def test_real_adapter_inspection_uses_source_shapes_without_training_predictions_or_scores(config,
                                                                                        source,
                                                                                        tmp_path,
                                                                                        monkeypatch):
    from learning_preserving_bci.datasets import kumar

    monkeypatch.setattr(training, "ROOT", tmp_path)
    protocol = {"development_subjects": ["sub-1"], "preprocessing": {"learned": False}}
    protocol_path = tmp_path / config["protocol_config"]
    manifest_path = tmp_path / config["split_manifest"]
    protocol_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    protocol_path.write_text(json.dumps(protocol))
    manifest_path.write_text('{"trials": []}')
    X_train, y_train, X_validation, y_validation, train_rows, validation_rows = source
    train_rows, validation_rows = copy.deepcopy((train_rows, validation_rows))
    for row in train_rows + validation_rows:
        row["subject"] = "sub-1"
    query = dict(train_rows[0], role="target_query", session="ses-1", run="run-1",
                 trial_id="query-must-not-be-inspected")
    subject = SimpleNamespace(X=np.concatenate([X_train, X_validation, X_train[:1] * 10000]),
                              y=np.concatenate([y_train, y_validation, [1]]),
                              metadata=train_rows + validation_rows + [query], sfreq=128.0,
                              channel_names=kumar.CHANNEL_NAMES,
                              provenance={"numeric_unit": "V", "raw_reference": "CPz",
                                          "processed_reference": "average_all22",
                                          "learned_preprocessing": False})
    monkeypatch.setattr(kumar, "load_subject", lambda *a, **k: subject)
    monkeypatch.setattr(training.SourceOnlyEEGNet, "fit_source",
                        lambda *a, **k: pytest.fail("Real EEGNet training ran"))
    monkeypatch.setattr(training.SourceOnlyEEGNet, "predict_proba",
                        lambda *a, **k: pytest.fail("Real predictions computed"))
    result = training.inspect_real_source_inputs(config, tmp_path / "local_only")
    assert result["synthetic"] is False and result["software_validation_only"]
    assert not result["training_executed"] and result["optimizer_steps"] == 0
    assert not result["predictions_computed"] and not result["performance_metrics_computed"]
    assert [part["shape"] for part in result["partitions"]] == [[16, 22, 640], [8, 22, 640]]
    assert "query-must-not-be-inspected" not in json.dumps(result)
