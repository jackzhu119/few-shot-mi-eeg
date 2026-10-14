#!/usr/bin/env python3
"""Prepare a source-only official EEGNet baseline; software checks are not formal fits.

Formal execution is blocked until the configuration's freeze gate and immutable
protocol/split hashes are filled. This script never downloads data or uses R2.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import inspect
import json
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from torch.utils.data import DataLoader, TensorDataset

from learning_preserving_bci.decoders.eegnet import EEGNetClassifier
from learning_preserving_bci.utils.reproducibility import (
    collect_provenance,
    seed_everything,
    write_result_json,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/kumar_eegnet_20261012.json"


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def state_digest(model):
    """Hash every parameter, BN buffer, class and learned channel statistic."""
    digest = hashlib.sha256()
    tensors = dict(model.model_.state_dict())
    tensors.update(channel_mean=torch.from_numpy(model.channel_mean_),
                   channel_scale=torch.from_numpy(model.channel_scale_),
                   classes=torch.from_numpy(model.classes_))
    for name, value in sorted(tensors.items()):
        array = value.detach().cpu().contiguous().numpy()
        digest.update(name.encode())
        digest.update(str(array.dtype).encode())
        digest.update(json.dumps(array.shape).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def validate_training_contract(config):
    """Reject settings whose names promise source-only behavior the code cannot honor."""
    dims, settings = config["input"], config["optimization"]
    if (config["device"] != "cpu" or dims != {
        "n_channels": 22, "n_classes": 2, "n_times": 640, "sfreq_hz": 128.0,
        "units": "V", "class_mapping": {"left_hand": 0, "right_hand": 1},
    }):
        raise ValueError("Frozen input contract is CPU, 22 channels, 640 samples, 128 Hz, volts")
    if config["normalization"] != {
        "fit_partition": "source_train", "axis": [0, 2], "scale_floor_volts": 1e-8,
        "target_fit": False,
    } or config["inference"] != {
        "mode": "eval", "batch_norm_updates": False, "optimizer_steps": 0,
        "threshold": "argmax_no_tuning",
    }:
        raise ValueError("Normalization and inference must remain source-only and frozen")
    expected = {"optimizer": "Adam", "loss": "CrossEntropyLoss", "scheduler": "none",
                "label_smoothing": 0.0, "class_weights": "none", "shuffle_training": True,
                "drop_last": False, "num_workers": 0}
    if any(settings[key] != value for key, value in expected.items()):
        raise ValueError("Unsupported optimization setting; freeze a new implementation first")
    stop = settings["early_stopping"]
    if any(stop[key] != value for key, value in {
        "partition": "source_validation", "metric": "mean_cross_entropy", "mode": "min",
        "ties": "earliest_epoch",
    }.items()):
        raise ValueError("Epoch selection must use source validation loss with earliest ties")
    if (settings["max_epochs"] < 1 or settings["batch_size"] < 1 or stop["patience"] < 1
            or not np.isfinite(stop["min_delta"]) or stop["min_delta"] < 0
            or not np.isfinite(settings["learning_rate"])
            or settings["learning_rate"] <= 0):
        raise ValueError("Training/stopping budgets and learning rate must be positive")


def validate_source_partitions(train_metadata, validation_metadata):
    """Only the frozen source train/validation runs may reach the optimizer/stopper."""
    allowed = {"source_train": {"run-0", "run-1"}, "source_validation": {"run-2"}}
    subjects = set()
    identities = set()
    for role, metadata in (("source_train", train_metadata),
                           ("source_validation", validation_metadata)):
        if not metadata:
            raise ValueError(f"Empty {role} metadata")
        for item in metadata:
            if item["role"] != role or item["session"] != "ses-0" or (
                item["run"] not in allowed[role]
            ):
                raise ValueError("Optimizer/epoch selection must use frozen source roles/runs only")
            if item["trial_id"] in identities:
                raise ValueError("Duplicate or overlapping source trial identity")
            identities.add(item["trial_id"])
            subjects.add(item["subject"])
            if not isinstance(item["trial_id"], str) or not item["trial_id"]:
                raise ValueError("Source trial identity must be a nonempty string")
    if len(subjects) != 1:
        raise ValueError("Within-subject training must contain exactly one subject")


class SourceOnlyEEGNet(EEGNetClassifier):
    """Reuse the existing EEGNet input/logit contract and official architecture.

    The fit method accepts only two source partitions. Target arrays/labels are
    absent from its API. Validation uses eval mode and never updates BN/weights.
    """

    def __init__(self, config, seed):
        validate_training_contract(config)
        self.config = copy.deepcopy(config)
        dims = config["input"]
        optim = config["optimization"]
        super().__init__(dims["n_channels"], dims["n_classes"], dims["n_times"],
                         dims["sfreq_hz"], epochs=optim["max_epochs"],
                         batch_size=optim["batch_size"], learning_rate=optim["learning_rate"],
                         seed=seed, device=config["device"])

    def _build_model(self):
        from braindecode.models import EEGNet

        architecture = copy.deepcopy(self.config["architecture"])
        if architecture.pop("implementation") != "braindecode.models.EEGNet":
            raise ValueError("Only the official Braindecode EEGNet is permitted")
        if architecture.pop("activation") != "ELU":
            raise ValueError("Frozen baseline activation is ELU")
        kwargs = dict(n_chans=self.n_channels, n_outputs=self.n_classes,
                      n_times=self.n_times, sfreq=self.sfreq, activation=torch.nn.ELU,
                      **architecture)
        parameters = inspect.signature(EEGNet).parameters
        if any(name not in parameters for name in kwargs):
            raise RuntimeError("Installed official EEGNet API differs from the frozen architecture")
        self.architecture_ = "braindecode.models.EEGNet"
        self.constructor_kwargs_ = {key: value for key, value in kwargs.items()
                                    if key != "activation"}
        return EEGNet(**kwargs).to("cpu")

    def _normalized(self, X):
        return np.asarray((self._array(X) - self.channel_mean_) / self.channel_scale_,
                          dtype=np.float32)

    def _validation_loss(self, X, y):
        before = state_digest(self)
        self.model_.eval()
        total = 0.0
        with torch.no_grad():
            for start in range(0, len(X), self.batch_size):
                batch = torch.from_numpy(X[start:start + self.batch_size])
                labels = torch.as_tensor(y[start:start + self.batch_size], dtype=torch.long)
                loss = torch.nn.functional.cross_entropy(self._logits(self.model_, batch), labels,
                                                        reduction="sum")
                total += loss.item()
        if state_digest(self) != before:
            raise RuntimeError("Source validation changed model or normalization state")
        return total / len(X)

    def fit_source(self, X_train, y_train, X_validation, y_validation,
                   train_metadata, validation_metadata):
        validate_source_partitions(train_metadata, validation_metadata)
        if self.device != "cpu":
            raise ValueError("This preparation supports existing CPU resources only")
        settings = self.config["optimization"]
        stopping = settings["early_stopping"]
        if stopping["partition"] != "source_validation" or stopping["mode"] != "min":
            raise ValueError("Epoch selection must minimize source validation loss")
        if settings["optimizer"] != "Adam" or settings["loss"] != "CrossEntropyLoss":
            raise ValueError("Unsupported optimizer/loss; freeze a new configuration first")
        if self.epochs < 1 or self.batch_size < 1 or stopping["patience"] < 1:
            raise ValueError("Training/stopping budgets must be positive")
        seed_everything(self.seed)
        X_train, X_validation = self._array(X_train), self._array(X_validation)
        y_train = np.asarray(y_train)
        y_validation = np.asarray(y_validation)
        for X, y, metadata in ((X_train, y_train, train_metadata),
                               (X_validation, y_validation, validation_metadata)):
            if y.shape != (len(X),) or len(metadata) != len(X) or set(y.tolist()) != {0, 1}:
                raise ValueError("Each source partition needs matching rows and both frozen classes")
        y_train, y_validation = y_train.astype(np.int64), y_validation.astype(np.int64)
        self.classes_ = np.array([0, 1], dtype=np.int64)
        self.channel_mean_ = X_train.mean(axis=(0, 2), keepdims=True)
        floor = self.config["normalization"]["scale_floor_volts"]
        self.channel_scale_ = X_train.std(axis=(0, 2), keepdims=True).clip(min=floor)
        self.model_ = self._build_model()
        train = self._normalized(X_train)
        validation = self._normalized(X_validation)
        loader = DataLoader(TensorDataset(torch.from_numpy(train), torch.from_numpy(y_train)),
                            batch_size=self.batch_size, shuffle=True, drop_last=False,
                            generator=torch.Generator().manual_seed(self.seed), num_workers=0)
        optimizer = torch.optim.Adam(self.model_.parameters(), lr=self.learning_rate,
                                     betas=tuple(settings["betas"]), eps=settings["epsilon"],
                                     weight_decay=settings["weight_decay"],
                                     amsgrad=settings["amsgrad"])
        criterion = torch.nn.CrossEntropyLoss(label_smoothing=settings["label_smoothing"])
        best_loss, best_state, stale = float("inf"), None, 0
        self.history_, self.optimizer_steps_ = [], 0
        for epoch in range(1, self.epochs + 1):
            self.model_.train()
            loss_sum = 0.0
            for batch, labels in loader:
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(self._logits(self.model_, batch), labels)
                if not torch.isfinite(loss):
                    raise RuntimeError("Nonfinite source training loss")
                loss.backward()
                optimizer.step()
                self.optimizer_steps_ += 1
                loss_sum += loss.item() * len(batch)
            validation_loss = self._validation_loss(validation, y_validation)
            if not np.isfinite(validation_loss):
                raise RuntimeError("Nonfinite source validation loss")
            self.history_.append(dict(epoch=epoch, source_train_loss=loss_sum / len(train),
                                      source_validation_loss=validation_loss))
            if validation_loss < best_loss - stopping["min_delta"]:
                best_loss, stale = validation_loss, 0
                self.selected_epoch_ = epoch
                best_state = {key: value.detach().cpu().clone()
                              for key, value in self.model_.state_dict().items()}
            else:
                stale += 1
            if stale >= stopping["patience"]:
                break
        self.model_.load_state_dict(best_state, strict=True)
        self.model_.eval()
        self.source_train_ids_ = [item["trial_id"] for item in train_metadata]
        self.source_validation_ids_ = [item["trial_id"] for item in validation_metadata]
        self.selected_validation_loss_ = best_loss
        self.frozen_state_sha256_ = state_digest(self)
        return self

    def fit(self, X, y):
        raise ValueError("Use fit_source with explicit frozen source train and validation identities")

    def predict_proba(self, X):
        before = state_digest(self)
        result = super().predict_proba(X)
        if before != state_digest(self):
            raise RuntimeError("Inference changed model/BN/normalization state")
        return result


def save_checkpoint(model, path, *, synthetic, software_validation_only):
    """Save tensor-only weights/statistics plus strict JSON, refusing overwrites."""
    path = Path(path)
    metadata_path = path.with_suffix(".json")
    if path.exists() or metadata_path.exists():
        raise FileExistsError("Checkpoint already exists; choose a new output path")
    path.parent.mkdir(parents=True, exist_ok=True)
    context = dict(synthetic=synthetic, software_validation_only=software_validation_only,
                    config=model.config, seed=model.seed, selected_epoch=model.selected_epoch_,
                    source_validation_loss=model.selected_validation_loss_, history=model.history_,
                    optimizer_steps=model.optimizer_steps_, source_train_ids=model.source_train_ids_,
                    source_validation_ids=model.source_validation_ids_,
                    config_canonical_sha256=canonical_sha256(model.config),
                    frozen_state_sha256=state_digest(model),
                    checkpoint_format="tensor_state_only_torch_load_weights_only_true",
                    architecture=model.architecture_, constructor_kwargs=model.constructor_kwargs_)
    # Bind configuration, seed, identities and selection metadata to the verified
    # checkpoint bytes rather than trusting an independently editable JSON sidecar.
    encoded = json.dumps(context, sort_keys=True, allow_nan=False).encode()
    payload = {"model_state_dict": model.model_.state_dict(),
               "channel_mean": torch.from_numpy(model.channel_mean_.copy()),
               "channel_scale": torch.from_numpy(model.channel_scale_.copy()),
               "classes": torch.from_numpy(model.classes_.copy()),
               "context_utf8": torch.tensor(list(encoded), dtype=torch.uint8)}
    with path.open("xb") as stream:
        torch.save(payload, stream)
    metadata = dict(context, checkpoint_sha256=sha256_file(path))
    write_result_json(metadata_path, metadata)
    return metadata


def load_checkpoint(path, *, expected_sha256):
    """Verify bytes before safe loading; build no optimizer and restore eval mode."""
    path = Path(path)
    if sha256_file(path) != expected_sha256:
        raise ValueError("Checkpoint SHA256 mismatch")
    metadata = json.loads(path.with_suffix(".json").read_text())
    if metadata["checkpoint_sha256"] != expected_sha256:
        raise ValueError("Checkpoint sidecar SHA256 mismatch")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if set(payload) != {"model_state_dict", "channel_mean", "channel_scale", "classes",
                        "context_utf8"}:
        raise ValueError("Unexpected checkpoint payload")
    encoded = payload["context_utf8"]
    if (not isinstance(encoded, torch.Tensor) or encoded.dtype != torch.uint8
            or encoded.ndim != 1 or encoded.numel() > 1_000_000):
        raise ValueError("Invalid checkpoint metadata tensor")
    context = json.loads(bytes(encoded.tolist()).decode())
    if context != {key: value for key, value in metadata.items() if key != "checkpoint_sha256"}:
        raise ValueError("Checkpoint sidecar context mismatch")
    if canonical_sha256(metadata["config"]) != metadata["config_canonical_sha256"]:
        raise ValueError("Checkpoint configuration digest mismatch")
    model = SourceOnlyEEGNet(metadata["config"], metadata["seed"])
    model.model_ = model._build_model()
    model.model_.load_state_dict(payload["model_state_dict"], strict=True)
    for key in ("channel_mean", "channel_scale"):
        tensor = payload[key]
        if tensor.dtype != torch.float32 or tuple(tensor.shape) != (1, model.n_channels, 1):
            raise ValueError("Invalid channel normalization tensor")
        if not torch.isfinite(tensor).all():
            raise ValueError("Nonfinite checkpoint normalization")
        setattr(model, key + "_", tensor.numpy().copy())
    if (model.channel_scale_ <= 0).any() or not torch.equal(
        payload["classes"], torch.tensor([0, 1], dtype=torch.int64)
    ):
        raise ValueError("Invalid checkpoint scale/classes")
    model.classes_ = payload["classes"].numpy().copy()
    model.model_.eval()
    model.frozen_state_sha256_ = state_digest(model)
    if model.frozen_state_sha256_ != metadata["frozen_state_sha256"]:
        raise ValueError("Restored frozen state digest mismatch")
    model.history_ = metadata["history"]
    model.optimizer_steps_ = metadata["optimizer_steps"]
    model.selected_epoch_ = metadata["selected_epoch"]
    model.selected_validation_loss_ = metadata["source_validation_loss"]
    model.source_train_ids_ = metadata["source_train_ids"]
    model.source_validation_ids_ = metadata["source_validation_ids"]
    return model


def source_arrays(subject):
    train = np.array([i for i, item in enumerate(subject.metadata)
                      if item["role"] == "source_train"], dtype=int)
    validation = np.array([i for i, item in enumerate(subject.metadata)
                           if item["role"] == "source_validation"], dtype=int)
    return (subject.X[train], subject.y[train], subject.X[validation], subject.y[validation],
            [subject.metadata[i] for i in train], [subject.metadata[i] for i in validation])


def synthetic_source(config):
    rng = np.random.default_rng(11)
    shape = config["input"]
    arrays = []
    metadata = []
    check = config["software_validation"]
    for role, n, run in (("source_train", check["synthetic_source_train_rows"], "run-0"),
                         ("source_validation", check["synthetic_source_validation_rows"], "run-2")):
        if n < 2 or n % 2:
            raise ValueError("Synthetic checks require small even class-balanced source partitions")
        y = np.tile([0, 1], n // 2).astype(np.int64)
        X = rng.normal(0, 1e-5, (n, shape["n_channels"], shape["n_times"])).astype(np.float32)
        X[y == 0, 0] *= 2
        X[y == 1, 1] *= 2
        arrays.extend([X, y])
        metadata.append([dict(subject="synthetic-sub-1", session="ses-0", run=run, role=role,
                              cohort="development", trial_id=f"synthetic/{run}/{i}")
                         for i in range(n)])
    return (*arrays, *metadata)


def inspect_real_source_inputs(config, data_root):
    """Inspect development source tensors, without model fit, predictions or scores."""
    from learning_preserving_bci.datasets.kumar import CHANNEL_NAMES, load_subject

    protocol_path, manifest_path = ROOT / config["protocol_config"], ROOT / config["split_manifest"]
    protocol = json.loads(protocol_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if "sub-1" not in protocol["development_subjects"]:
        raise ValueError("Real software inspection is limited to development sub-1")
    subject = load_subject(data_root, "sub-1", protocol, split_manifest=manifest)
    source = source_arrays(subject)
    validate_source_partitions(source[4], source[5])
    if tuple(subject.channel_names) != CHANNEL_NAMES:
        raise ValueError("Adapter channel order differs from the frozen preprocessing")
    if subject.sfreq != config["input"]["sfreq_hz"] or subject.provenance["numeric_unit"] != "V":
        raise ValueError("Adapter sampling frequency or units changed")
    partitions = []
    for offset, role in ((0, "source_train"), (2, "source_validation")):
        X, y, metadata = source[offset], source[offset + 1], source[4 + offset // 2]
        if (X.dtype != np.float32 or X.shape[1:] != (22, 640) or not np.isfinite(X).all()
                or y.shape != (len(X),) or set(y.tolist()) != {0, 1}
                or len(metadata) != len(X) or any(t["cohort"] != "development"
                                                or t["subject"] != "sub-1" for t in metadata)):
            raise ValueError("Real source tensor/identity/class contract failed")
        partitions.append(dict(role=role, shape=list(X.shape), dtype=str(X.dtype),
                               units="V", all_finite=True,
                               class_counts={str(c): int(np.sum(y == c)) for c in (0, 1)},
                               trial_ids=[t["trial_id"] for t in metadata],
                               processed_numeric_sha256=hashlib.sha256(X.tobytes()).hexdigest(),
                               maximum_absolute_volts=float(np.abs(X).max())))
    return dict(case="real_source_adapter_inspection", synthetic=False,
                software_validation_only=True, subject="sub-1", cohort="development",
                training_executed=False, optimizer_steps=0, predictions_computed=False,
                target_query_predictions_computed=False, performance_metrics_computed=False,
                normalization_fitted=False, partitions=partitions,
                channel_names=list(subject.channel_names), sfreq_hz=subject.sfreq,
                preprocessing=protocol["preprocessing"],
                adapter_load_scope="full participant identity/preprocessing audit; source tensors only",
                protocol_config_sha256=sha256_file(protocol_path),
                split_manifest_sha256=sha256_file(manifest_path),
                raw_reference=subject.provenance["raw_reference"],
                processed_reference=subject.provenance["processed_reference"],
                learned_preprocessing=subject.provenance["learned_preprocessing"])


def software_check(config, output, *, data_root=None):
    """Synthetic two-epoch fit plus optional real source shape check; no query scores."""
    validate_training_contract(config)
    check = config["software_validation"]
    if (check["synthetic_max_epochs"] != 2 or check["synthetic_source_train_rows"] != 16
            or check["synthetic_source_validation_rows"] != 8 or check["real_training"]
            or check["query_predictions"] or check["formal_performance_claims"]):
        raise ValueError("Software checks are bounded synthetic fits and real source shape checks only")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    check_config = copy.deepcopy(config)
    check_config["optimization"]["max_epochs"] = check["synthetic_max_epochs"]
    check_config["optimization"]["early_stopping"]["patience"] = 2
    checks = []
    for name, synthetic, source in [("synthetic", True, synthetic_source(check_config))]:
        model = SourceOnlyEEGNet(check_config, config["seeds"][0]).fit_source(*source)
        replica = SourceOnlyEEGNet(check_config, config["seeds"][0]).fit_source(*source)
        before = state_digest(model)
        probabilities = model.predict_proba(source[2])
        if not np.array_equal(probabilities, replica.predict_proba(source[2])):
            raise RuntimeError("Deterministic same-seed source replay failed")
        checkpoint = output / f"{name}_weights.pt"
        saved = save_checkpoint(model, checkpoint, synthetic=synthetic,
                                software_validation_only=True)
        restored = load_checkpoint(checkpoint, expected_sha256=saved["checkpoint_sha256"])
        if not np.array_equal(probabilities, restored.predict_proba(source[2])):
            raise RuntimeError("Safe checkpoint prediction replay failed")
        if before != state_digest(model):
            raise RuntimeError("Software inference changed frozen state")
        checks.append(dict(case=name, synthetic=synthetic, software_validation_only=True,
                           source_train_rows=len(source[0]), source_validation_rows=len(source[2]),
                           epochs_executed=len(model.history_), optimizer_steps=model.optimizer_steps_,
                           selected_epoch=model.selected_epoch_, forward_backward_finite=True,
                           normalization_fit_partition="source_train_only", source_only_stopping=True,
                           target_query_predictions_computed=False, same_seed_exact_replay=True,
                           eval_state_unchanged=True, safe_checkpoint_exact_replay=True,
                           checkpoint_sha256=saved["checkpoint_sha256"],
                           frozen_state_sha256=before, training_executed=True,
                           performance_metrics_computed=False))
    if data_root is not None:
        checks.append(inspect_real_source_inputs(config, data_root))
    summary = dict(synthetic=True, software_validation_only=True,
                   formal_training_status="pending_not_executed", checks=checks,
                   runtime_seconds=time.monotonic() - start,
                   provenance=collect_provenance(config["seeds"][0], ROOT),
                   training_config_canonical_sha256=canonical_sha256(config),
                   runtime_device=dict(requested="cpu", torch_build=torch.__version__,
                                       cuda_build=torch.version.cuda,
                                       cuda_available=torch.cuda.is_available(),
                                       cuda_device_count=torch.cuda.device_count(),
                                       torch_threads=torch.get_num_threads()),
                   script_sha256=sha256_file(__file__))
    write_result_json(output / "software_validation.json", summary)
    return summary


def check_formal_freeze(config, config_path):
    freeze = config["freeze"]
    if not freeze["ready_for_formal_training"]:
        raise ValueError("Formal training is Pending: CPU software checks only in this round")
    for key, path in (("protocol_config_sha256", config["protocol_config"]),
                      ("split_manifest_sha256", config["split_manifest"])):
        if freeze[key] != sha256_file(ROOT / path):
            raise ValueError(f"Freeze hash missing or changed: {key}")
    # Canonical content excludes the embedded hash value itself. A detached
    # receipt additionally binds the exact final bytes, including that value.
    frozen_hash = config["freeze"]["frozen_training_config_sha256"]
    hash_content = copy.deepcopy(config)
    hash_content["freeze"]["frozen_training_config_sha256"] = None
    detached = Path(config_path).with_suffix(".sha256")
    if (frozen_hash != canonical_sha256(hash_content) or not detached.is_file()
            or detached.read_text().strip() != sha256_file(config_path)):
        raise ValueError("Final training configuration needs its detached SHA256 freeze receipt")


def formal_train(config, config_path, data_root, output):
    """Future serial source-only fits; blocked by the explicit preparation gate."""
    from learning_preserving_bci.datasets.kumar import load_subject

    check_formal_freeze(config, config_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads((ROOT / config["protocol_config"]).read_text())
    manifest = json.loads((ROOT / config["split_manifest"]).read_text())
    results = []
    for subject_id in [f"sub-{i}" for i in range(1, 19)]:
        subject = load_subject(data_root, subject_id, protocol, split_manifest=manifest)
        source = source_arrays(subject)
        for seed in config["seeds"]:
            started = time.monotonic()
            model = SourceOnlyEEGNet(config, seed).fit_source(*source)
            checkpoint = output / subject_id / f"seed-{seed}" / "weights.pt"
            saved = save_checkpoint(model, checkpoint, synthetic=False,
                                    software_validation_only=False)
            rows = []
            metrics = []
            # Query is opened only after the full pipeline and selected source epoch are frozen.
            groups = sorted({(item["session"], item["role"]) for item in subject.metadata
                             if item["role"] in {"source_query", "target_query"}})
            for session, role in groups:
                idx = [i for i, item in enumerate(subject.metadata)
                       if (item["session"], item["role"]) == (session, role)]
                proba = model.predict_proba(subject.X[idx])
                prediction = proba.argmax(axis=1)
                metrics.append(dict(session=session, role=role, n=len(idx),
                                    balanced_accuracy=balanced_accuracy_score(subject.y[idx], prediction),
                                    confusion_matrix=confusion_matrix(subject.y[idx], prediction,
                                                                      labels=[0, 1]).tolist()))
                rows.extend(dict(subject.metadata[i], seed=seed, y_true=int(subject.y[i]),
                                 y_pred=int(prediction[j]), p_right=float(proba[j, 1]))
                            for j, i in enumerate(idx))
            with (checkpoint.parent / "query_predictions.tsv").open("x", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            record = dict(synthetic=False, software_validation_only=False, subject=subject_id,
                          seed=seed, selected_epoch=model.selected_epoch_, metrics=metrics,
                          frozen_state_sha256=state_digest(model),
                          checkpoint_sha256=saved["checkpoint_sha256"],
                          runtime_seconds=time.monotonic() - started,
                          provenance=collect_provenance(seed, ROOT),
                          training_config_sha256=sha256_file(config_path),
                          script_sha256=sha256_file(__file__))
            write_result_json(checkpoint.parent / "evaluation.json", record)
            results.append(record)
    summary = dict(synthetic=False, software_validation_only=False, results=results,
                   independent_unit="published_subject_identity; seeds are repeated fits",
                   training_config_sha256=sha256_file(config_path))
    write_result_json(output / "formal_training.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--software-check", action="store_true")
    modes.add_argument("--execute-formal-training", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    torch.set_num_threads(config["threads"])
    if args.software_check:
        summary = software_check(config, args.output, data_root=args.data_root)
        print(json.dumps(dict(status="software_validation_only", output=str(args.output),
                              checks=len(summary["checks"]),
                              formal_training="pending_not_executed")))
    else:
        if args.data_root is None:
            parser.error("--execute-formal-training requires --data-root")
        formal_train(config, args.config, args.data_root, args.output)


if __name__ == "__main__":
    main()
