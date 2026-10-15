"""Untrained synthetic checkpoint fixtures only: no fit, backward, optimizer or EEG."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import tarfile
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("braindecode")
from braindecode.models import EEGNet  # noqa: E402

import evaluate_kumar_checkpoint_reuse as reuse  # noqa: E402
import train_kumar_eegnet as training  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.deep


def raw_json(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def untrained_payload():
    """Random initialization plus stipulated statistics; never call a fit API."""
    config = json.loads((ROOT / "configs/kumar_eegnet_gpu_development_20261014.json").read_text())
    architecture = copy.deepcopy(config["architecture"])
    architecture.pop("implementation")
    architecture.pop("activation")
    kwargs = dict(n_chans=22, n_outputs=2, n_times=640, sfreq=128.0, **architecture)
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(218)
        model = EEGNet(activation=torch.nn.ELU, **kwargs).cpu().eval()
    mean = torch.full((1, 22, 1), 2e-6, dtype=torch.float32)
    scale = torch.full((1, 22, 1), 3e-5, dtype=torch.float32)
    classes = torch.tensor([0, 1], dtype=torch.int64)
    rows = []
    for role, count, run in (("source_train", 40, "run-0"),
                             ("source_validation", 20, "run-2")):
        rows.extend(dict(trial_id=f"synthetic-untrained/{role}/{index}",
                         subject="synthetic-subject", role=role, session="ses-0", run=run,
                         included=True, label="left_hand" if index % 2 == 0 else "right_hand")
                    for index in range(count))
    context = dict(config=config, seed=20261012, synthetic=True, software_validation_only=True,
                   selected_epoch=0, history=[], optimizer_steps=0,
                   source_validation_loss=float(np.log(2)),
                   source_train_ids=[row["trial_id"] for row in rows[:40]],
                   source_validation_ids=[row["trial_id"] for row in rows[40:]],
                   config_canonical_sha256=training.canonical_sha256(config),
                   frozen_state_sha256=reuse._state_digest(model, mean, scale, classes),
                   checkpoint_format="tensor_state_only_torch_load_weights_only_true",
                   architecture="braindecode.models.EEGNet", constructor_kwargs=kwargs)
    payload = dict(model_state_dict=model.state_dict(), channel_mean=mean, channel_scale=scale,
                   classes=classes, context_utf8=torch.tensor(list(raw_json(context)),
                                                             dtype=torch.uint8))
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    weights = buffer.getvalue()
    return config, rows, context, weights


def build_archive(path, data, job, legacy=False):
    manifest = dict(job_id=job["job_id"], subject=job["subject"], seed=job["seed"],
                    result_key=job["result_key"], files=[dict(path=name, bytes=len(raw),
                    sha256=sha(raw)) for name, raw in sorted(data.items())])
    if legacy:
        manifest = dict(job=reuse.LEGACY_JOB_NAME, expected_R2_key=job["result_key"],
                        files=manifest["files"], synthetic=True, software_validation_only=True)
    with path.open("wb") as stream, tarfile.open(fileobj=stream, mode="w") as archive:
        for name, raw in dict(data, **{"manifest.json": raw_json(manifest)}).items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))


@pytest.fixture
def bundle(tmp_path, untrained_payload):
    config, rows, context, weights = copy.deepcopy(untrained_payload)
    X = np.random.default_rng(821).normal(0, 1e-5, (20, 22, 640)).astype(np.float32)
    for row, trial in zip(rows[40:], X, strict=True):
        row["processed_window_numeric_sha256"] = sha(
            np.asarray(trial, dtype="<f4", order="C").tobytes(order="C"))
    split_path = tmp_path / "split.json"
    split_path.write_bytes(raw_json(dict(trials=rows)))
    config_raw = raw_json(config)
    job = dict(subject="synthetic-subject", seed=20261012, job_id="synthetic-untrained-job",
               result_key="synthetic/software-validation-only.tar",
               training_config_sha256=sha(config_raw), split_sha256=sha(split_path.read_bytes()))
    plan_path = tmp_path / "plan.json"
    plan_path.write_bytes(raw_json(dict(jobs=[job])))
    metadata = dict(context, checkpoint_sha256=sha(weights))
    record = dict(subject=job["subject"], seed=job["seed"], job_id=job["job_id"],
                  status="fit_saved", synthetic=True, query_rows_loaded=0,
                  source_train_rows=40, source_validation_rows=20,
                  training_config_sha256=job["training_config_sha256"],
                  split_sha256=job["split_sha256"], checkpoint_sha256=sha(weights))
    data = {"weights.pt": weights, "weights.json": raw_json(metadata),
            "training_config.json": config_raw, "fit_result.json": raw_json(record),
            "job.json": raw_json(job)}
    archive_path = tmp_path / "untrained-software-validation.tar"
    build_archive(archive_path, data, job)
    entry = dict(job_id=job["job_id"], subject=job["subject"], seed=job["seed"],
                 archive_sha256=sha(archive_path.read_bytes()), result_key=job["result_key"],
                 receipt="receipt.json", parent_acknowledgement="ack.json")
    ledger_path = tmp_path / "accepted-software-fixtures.json"
    ledger_path.write_bytes(raw_json(dict(accepted_jobs=[entry])))
    receipt = dict(status="completed", totals=dict(failed_files=0), files=[
        dict(key=job["result_key"], sha256=entry["archive_sha256"],
             verification="full_get_sha256_verified", get_http_status=200,
             bytes=archive_path.stat().st_size, readback_bytes=archive_path.stat().st_size)])
    (tmp_path / "receipt.json").write_bytes(raw_json(receipt))
    (tmp_path / "ack.json").write_bytes(raw_json(dict(
        status="parent_acknowledged", job_id=job["job_id"],
        receipt_sha256=sha((tmp_path / "receipt.json").read_bytes()),
        synthetic=True, software_validation_only=True)))
    kwargs = dict(job_id=job["job_id"], ledger_path=ledger_path,
                  expected_ledger_sha256=sha(ledger_path.read_bytes()), plan_path=plan_path,
                  expected_plan_sha256=sha(plan_path.read_bytes()), split_path=split_path,
                  expected_split_sha256=sha(split_path.read_bytes()), evidence_root=tmp_path,
                  software_validation_only=True)
    labels = np.tile([0, 1], 10).astype(np.int64)
    return dict(path=archive_path, kwargs=kwargs, data=data, job=job, metadata=metadata,
                X=X, labels=labels, rows=rows[40:])


def load(bundle):
    return reuse.load_accepted_checkpoint(bundle["path"], **bundle["kwargs"])


def files_digest(path):
    return {str(file.relative_to(path)): sha(file.read_bytes())
            for file in path.rglob("*") if file.is_file()}


def forbid_training(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Read-only reuse attempted optimizer, fitting, backward, or thread mutation")

    monkeypatch.setattr(torch.optim, "Adam", forbidden)
    monkeypatch.setattr(torch.optim.Optimizer, "__init__", forbidden)
    monkeypatch.setattr(torch.Tensor, "backward", forbidden)
    monkeypatch.setattr(torch.autograd, "backward", forbidden)
    monkeypatch.setattr(training.SourceOnlyEEGNet, "fit", forbidden)
    monkeypatch.setattr(training.SourceOnlyEEGNet, "fit_source", forbidden)
    monkeypatch.setattr(torch, "set_num_threads", forbidden)
    monkeypatch.setattr(torch, "manual_seed", forbidden)
    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)


def test_untrained_software_replay_preserves_every_state_and_file(bundle, monkeypatch):
    forbid_training(monkeypatch)
    before_files = files_digest(bundle["path"].parent)
    before_rng = torch.random.get_rng_state().clone()
    safe_load_calls = []
    original_load = torch.load

    def safe_load(*args, **kwargs):
        safe_load_calls.append(kwargs)
        return original_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", safe_load)
    handle = load(bundle)
    assert not hasattr(handle, "fit") and not hasattr(handle, "fit_source")
    assert not hasattr(handle, "optimizer") and not hasattr(handle, "model_")
    assert torch.equal(before_rng, torch.random.get_rng_state())
    assert safe_load_calls == [dict(map_location="cpu", weights_only=True)]
    X_before, y_before, rows_before = bundle["X"].copy(), bundle["labels"].copy(), copy.deepcopy(
        bundle["rows"])
    first = handle.evaluate_source_validation(bundle["X"], bundle["labels"], bundle["rows"])
    second = handle.evaluate_source_validation(bundle["X"], bundle["labels"], bundle["rows"])
    np.testing.assert_array_equal(first["logits"], second["logits"])
    assert first["state_before_sha256"] == first["state_after_sha256"] == handle.assert_unchanged()
    assert np.isfinite(first["mean_cross_entropy"])
    assert first["optimizer_instances_created"] == first["optimizer_steps"] == 0
    assert first["new_fit"] is False and first["query_rows_loaded"] == 0
    assert first["identity"]["archived_training_device"] == "cuda"
    assert first["identity"]["execution_device"] == "cpu"
    assert first["identity"]["synthetic"] is first["identity"]["software_validation_only"] is True
    assert first["formal_scientific_gate_passed"] is False
    assert first["processed_input_hashes_verified"] is True
    assert first["replay_ce_absolute_tolerance"] == 1e-7
    assert first["replay_ce_comparison_applicable"] is False
    assert first["replay_ce_absolute_error"] is first["replay_ce_within_tolerance"] is None
    assert before_files == files_digest(bundle["path"].parent)
    np.testing.assert_array_equal(bundle["X"], X_before)
    np.testing.assert_array_equal(bundle["labels"], y_before)
    assert bundle["rows"] == rows_before


@pytest.mark.parametrize("violation", ["query", "future", "wrong_label", "wrong_run", "duplicate"])
def test_forbidden_roles_and_ids_reject_before_signal_or_labels(bundle, violation):
    handle = load(bundle)
    rows = copy.deepcopy(bundle["rows"])
    if violation == "query":
        rows[0]["role"] = "target_query"
    elif violation == "future":
        rows[0]["session"] = "ses-1"
    elif violation == "wrong_label":
        rows[0]["label"] = "right_hand"
    elif violation == "wrong_run":
        rows[0]["run"] = "run-0"
    else:
        rows[-1]["trial_id"] = rows[0]["trial_id"]

    class ForbiddenArray:
        def __array__(self, *args, **kwargs):
            pytest.fail("Signal or labels accessed before identity/role rejection")

    with pytest.raises(ValueError, match="identities/order|metadata/labels"):
        handle.evaluate_source_validation(ForbiddenArray(), ForbiddenArray(), rows)
    handle.assert_unchanged()


@pytest.mark.parametrize("violation", ["bytes", "ledger", "plan", "split", "ack", "receipt"])
def test_unaccepted_or_changed_evidence_rejects_before_safe_load(bundle, monkeypatch, violation):
    if violation == "bytes":
        path = bundle["path"]
    elif violation in {"ledger", "plan", "split"}:
        path = bundle["kwargs"][violation + "_path"]
    else:
        path = bundle["path"].parent / (violation + ".json")
    path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(torch, "load", lambda *args, **kwargs: pytest.fail("Unsafe premature load"))
    if violation == "ack":
        # ACK content is meaningful; whitespace alone is valid and has no prior
        # detached ACK hash, so exercise its actual status rather than formatting.
        path.write_bytes(raw_json(dict(status="pending")))
    with pytest.raises(ValueError):
        load(bundle)


def test_bound_synthetic_flags_cannot_be_used_to_relabel_real_checkpoint(bundle, monkeypatch):
    bundle["kwargs"]["software_validation_only"] = False
    monkeypatch.setattr(torch, "load", lambda *args, **kwargs: pytest.fail("Unsafe premature load"))
    with pytest.raises(ValueError, match="Synthetic/software-only"):
        load(bundle)


@pytest.mark.parametrize("mutation", ["parameter", "bn", "normalizer", "train_mode", "gradient",
                                     "context"])
def test_tampering_is_rejected_without_restoring_or_rewriting(bundle, mutation):
    handle = load(bundle)
    model = handle._ReadOnlyCheckpoint__model
    if mutation == "parameter":
        with torch.no_grad():
            next(model.parameters()).view(-1)[0].add_(1)
    elif mutation == "bn":
        layer = next(module for module in model.modules()
                     if isinstance(module, torch.nn.modules.batchnorm._BatchNorm))
        layer.num_batches_tracked.add_(1)
    elif mutation == "normalizer":
        handle._ReadOnlyCheckpoint__scale[0, 0, 0] *= 2
    elif mutation == "train_mode":
        model.train()
    elif mutation == "gradient":
        next(model.parameters()).requires_grad_(True)
    else:
        handle._ReadOnlyCheckpoint__metadata["seed"] += 1
    with pytest.raises(ValueError, match="changed"):
        handle.evaluate_source_validation(bundle["X"], bundle["labels"], bundle["rows"])
    # The guard never pretends that restoring state erases an invalid evaluation.
    with pytest.raises(ValueError, match="changed"):
        handle.assert_unchanged()


@pytest.mark.parametrize("mutation", ["parameter", "bn", "normalizer"])
def test_during_forward_mutation_produces_no_success_result(bundle, mutation):
    handle = load(bundle)
    model = handle._ReadOnlyCheckpoint__model

    def mutate(module, inputs):
        if mutation == "parameter":
            next(module.parameters()).view(-1)[0].add_(1)
        elif mutation == "bn":
            layer = next(item for item in module.modules()
                         if isinstance(item, torch.nn.modules.batchnorm._BatchNorm))
            layer.running_mean[0].add_(1)
        else:
            handle._ReadOnlyCheckpoint__mean[0, 0, 0].add_(1e-5)

    model.register_forward_pre_hook(mutate)
    before_files = files_digest(bundle["path"].parent)
    with pytest.raises(ValueError, match="parameters/BN/normalization changed"):
        handle.evaluate_source_validation(bundle["X"], bundle["labels"], bundle["rows"])
    assert files_digest(bundle["path"].parent) == before_files


def test_source_files_changed_after_load_are_rejected(bundle):
    handle = load(bundle)
    bundle["kwargs"]["ledger_path"].write_bytes(b"changed historical ledger")
    with pytest.raises(ValueError, match="Input evidence changed"):
        handle.evaluate_source_validation(bundle["X"], bundle["labels"], bundle["rows"])


def test_invalid_source_tensor_and_fractional_labels_reject_without_updates(bundle):
    handle = load(bundle)
    for X, labels in ((bundle["X"], bundle["labels"].astype(float)),
                      (bundle["X"][:, :, :-1], bundle["labels"]),
                      (np.full_like(bundle["X"], np.nan), bundle["labels"])):
        with pytest.raises(ValueError):
            handle.evaluate_source_validation(X, labels, bundle["rows"])
        handle.assert_unchanged()


def test_changed_processed_signal_rejects_before_forward_even_with_correct_ids(bundle, monkeypatch):
    handle = load(bundle)
    changed = bundle["X"].copy()
    changed[0, 0, 0] = np.nextafter(changed[0, 0, 0], np.float32(np.inf))
    metadata = copy.deepcopy(bundle["rows"])
    # An editable caller assertion cannot replace the immutable split digest.
    metadata[0]["processed_window_numeric_sha256"] = sha(changed[0].tobytes())
    monkeypatch.setattr(handle._ReadOnlyCheckpoint__model, "forward",
                        lambda *args: pytest.fail("Forward before processed-trial identity check"))
    with pytest.raises(ValueError, match="Processed source-validation trial SHA256"):
        handle.evaluate_source_validation(changed, bundle["labels"], metadata)
    handle.assert_unchanged()


def test_processed_hash_serialization_matches_existing_adapter(bundle):
    from learning_preserving_bci.datasets.kumar import numeric_hash

    for trial, row in zip(bundle["X"], bundle["rows"], strict=True):
        assert numeric_hash(trial, dtype="<f4") == row["processed_window_numeric_sha256"]
    handle = load(bundle)
    # Memory layout and host byte order cannot change the stipulated numeric
    # serialization; float32 trial values remain identical.
    result = handle.evaluate_source_validation(np.asfortranarray(bundle["X"].astype(">f4")),
                                               bundle["labels"], bundle["rows"])
    assert result["processed_input_hashes_verified"] is True


@pytest.mark.parametrize("mean_loss", [0.0, 0.5e-7, 1e-7])
def test_frozen_real_ce_guard_accepts_only_original_bound(mean_loss):
    # Pure numerical guard, not a real checkpoint or fit; zero is a boundary
    # fixture so the exact unchanged 1e-7 tolerance is representable here.
    metadata = dict(synthetic=False, software_validation_only=False, source_validation_loss=0.0)
    result = reuse.check_replay_cross_entropy(mean_loss, metadata)
    assert result["replay_ce_comparison_applicable"] is True
    assert result["replay_ce_absolute_error"] == mean_loss
    assert result["replay_ce_absolute_tolerance"] == 1e-7
    assert result["replay_ce_within_tolerance"] is True


@pytest.mark.parametrize("mean_loss", [1.01e-7, -1.01e-7, np.nan, np.inf])
def test_excess_or_nonfinite_real_ce_cannot_return_success(mean_loss):
    metadata = dict(synthetic=False, software_validation_only=False, source_validation_loss=0.0)
    with pytest.raises(ValueError, match="frozen 1e-7"):
        reuse.check_replay_cross_entropy(mean_loss, metadata)


def test_untrained_software_ce_comparison_is_explicitly_not_applicable():
    metadata = dict(synthetic=True, software_validation_only=True, source_validation_loss=0.1)
    result = reuse.check_replay_cross_entropy(10.0, metadata)
    assert result["original_source_validation_mean_cross_entropy"] == 0.1
    assert result["replay_ce_absolute_tolerance"] == 1e-7
    assert result["replay_ce_comparison_applicable"] is False
    assert result["replay_ce_absolute_error"] is result["replay_ce_within_tolerance"] is None


@pytest.mark.parametrize("violation", ["absent", "status", "query", "new_fit", "optimizer",
                                       "updates", "ledger", "plan", "split", "job", "hash"])
def test_real_authorization_guard_defaults_closed_or_rejects_changed_scope(tmp_path, violation):
    """Pure authorization logic; no checkpoint, signal, real result, or forward."""
    bindings = dict(accepted_ledger_sha256="a" * 64, frozen_plan_sha256="b" * 64,
                    split_manifest_sha256="c" * 64)
    authorization = dict(bindings, status="actual_parent_authorized_checkpoint_source_validation",
                         scope="existing_source_validation_replay_only", query_access=False,
                         new_fits=0, optimizer_instances=0, weights_and_normalization_updates=False,
                         authorized_job_ids=["synthetic-untrained-job"])
    fields = dict(status="status", query="query_access", new_fit="new_fits",
                  optimizer="optimizer_instances", updates="weights_and_normalization_updates",
                  ledger="accepted_ledger_sha256", plan="frozen_plan_sha256",
                  split="split_manifest_sha256", job="authorized_job_ids")
    if violation in fields:
        authorization[fields[violation]] = {
            "status": "proposal_only", "query": True, "new_fit": 1, "optimizer": 1,
            "updates": True, "ledger": "changed", "plan": "changed", "split": "changed",
            "job": ["another-job"],
        }[violation]
    path = tmp_path / "synthetic-authorization-logic-only.json"
    path.write_bytes(raw_json(authorization))
    expected = sha(path.read_bytes()) if violation != "hash" else "d" * 64
    with pytest.raises(ValueError):
        reuse.check_source_replay_authorization(
            path if violation != "absent" else None, expected,
            bindings=bindings, job_id="synthetic-untrained-job", snapshots={})


def test_exact_authorization_logic_pins_receipt_bytes_and_job(tmp_path):
    bindings = dict(accepted_ledger_sha256="a" * 64, frozen_plan_sha256="b" * 64,
                    split_manifest_sha256="c" * 64)
    authorization = dict(bindings, status="actual_parent_authorized_checkpoint_source_validation",
                         scope="existing_source_validation_replay_only", query_access=False,
                         new_fits=0, optimizer_instances=0, weights_and_normalization_updates=False,
                         authorized_job_ids=["synthetic-untrained-job"])
    path = tmp_path / "synthetic-authorization-logic-only.json"
    path.write_bytes(raw_json(authorization))
    snapshots = {}
    reuse.check_source_replay_authorization(path, sha(path.read_bytes()), bindings=bindings,
                                            job_id="synthetic-untrained-job", snapshots=snapshots)
    assert snapshots == {path.resolve(): sha(path.read_bytes())}


def repack_software_fixture(bundle):
    """Rebind a synthetic envelope so inner guards are reached; never touch real evidence."""
    build_archive(bundle["path"], bundle["data"], bundle["job"], legacy=bundle.get("legacy", False))
    ledger_path = bundle["kwargs"]["ledger_path"]
    ledger = json.loads(ledger_path.read_text())
    ledger["accepted_jobs"][0]["archive_sha256"] = sha(bundle["path"].read_bytes())
    ledger_path.write_bytes(raw_json(ledger))
    bundle["kwargs"]["expected_ledger_sha256"] = sha(ledger_path.read_bytes())
    receipt_path = bundle["path"].parent / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["files"][0].update(sha256=sha(bundle["path"].read_bytes()),
                                bytes=bundle["path"].stat().st_size,
                                readback_bytes=bundle["path"].stat().st_size)
    receipt_path.write_bytes(raw_json(receipt))
    ack_path = bundle["path"].parent / "ack.json"
    ack = json.loads(ack_path.read_text())
    ack["receipt_sha256"] = sha(receipt_path.read_bytes())
    ack_path.write_bytes(raw_json(ack))


def test_editable_sidecar_cannot_replace_tensor_bound_context(bundle):
    metadata = json.loads(bundle["data"]["weights.json"])
    metadata["selected_epoch"] = 99
    bundle["data"]["weights.json"] = raw_json(metadata)
    repack_software_fixture(bundle)
    with pytest.raises(ValueError, match="sidecar is not bound"):
        load(bundle)


def test_first_legacy_layout_is_supported_without_rewriting_it(bundle):
    """Legacy-shaped random-weight software fixture, not the real first checkpoint."""
    bundle["legacy"] = True
    bundle["job"]["job_id"] = reuse.LEGACY_JOB_ID
    bundle["kwargs"]["job_id"] = reuse.LEGACY_JOB_ID
    plan_path = bundle["kwargs"]["plan_path"]
    plan_path.write_bytes(raw_json(dict(jobs=[bundle["job"]])))
    bundle["kwargs"]["expected_plan_sha256"] = sha(plan_path.read_bytes())
    del bundle["data"]["job.json"]
    record = json.loads(bundle["data"]["fit_result.json"])
    record.pop("job_id")
    record.pop("split_sha256")
    record.update(job=reuse.LEGACY_JOB_NAME, status="fit_finished_backup_pending")
    bundle["data"]["fit_result.json"] = raw_json(record)
    ledger_path = bundle["kwargs"]["ledger_path"]
    ledger = json.loads(ledger_path.read_text())
    ledger["accepted_jobs"][0]["job_id"] = reuse.LEGACY_JOB_ID
    ledger_path.write_bytes(raw_json(ledger))
    ack_path = bundle["path"].parent / "ack.json"
    ack = json.loads(ack_path.read_text())
    ack.pop("job_id")
    ack_path.write_bytes(raw_json(ack))
    repack_software_fixture(bundle)
    before_files = files_digest(bundle["path"].parent)
    handle = load(bundle)
    assert handle.identity["job_id"] == reuse.LEGACY_JOB_ID
    handle.assert_unchanged()
    assert files_digest(bundle["path"].parent) == before_files


@pytest.mark.parametrize("violation", ["weight", "scale", "class", "context", "payload"])
def test_tensor_state_and_normalization_tampering_is_rejected(bundle, violation):
    payload = torch.load(io.BytesIO(bundle["data"]["weights.pt"]),
                         map_location="cpu", weights_only=True)
    if violation == "weight":
        next(iter(payload["model_state_dict"].values())).view(-1)[0] += 1
    elif violation == "scale":
        payload["channel_scale"][0, 0, 0] = -1
    elif violation == "class":
        payload["classes"] = torch.tensor([1, 0], dtype=torch.int64)
    elif violation == "context":
        payload["context_utf8"] = payload["context_utf8"].float()
    else:
        payload["optimizer_state_dict"] = {}
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    bundle["data"]["weights.pt"] = buffer.getvalue()
    for name in ("weights.json", "fit_result.json"):
        value = json.loads(bundle["data"][name])
        value["checkpoint_sha256"] = sha(buffer.getvalue())
        bundle["data"][name] = raw_json(value)
    repack_software_fixture(bundle)
    with pytest.raises(ValueError):
        load(bundle)
