"""Read-only reuse of an accepted EEGNet checkpoint; no fitting or query data API.

The CLI checks metadata only.  The Python API is deliberately limited to replay
of the checkpoint's existing source-validation identities.  It cannot evaluate
target/query rows or open EEG files.  A future query evaluator needs a separately
reviewed and frozen implementation; this module does not authorize one.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import io
import json
import tarfile
from pathlib import Path

import numpy as np
import torch

from train_kumar_eegnet import canonical_sha256, validate_training_contract

ROOT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE_BYTES = 16 * 1024**2
FROZEN_CE_ABSOLUTE_TOLERANCE = 1e-7
LEGACY_JOB_ID = "17377a7cf04bfc73e25bc94d7e42fc4f1ab6f14fb6dde63c7b21e742b94b9ace"
LEGACY_JOB_NAME = "kumar-sub1-seed20261012-parent-relay-run01"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            _require(key not in value, "Duplicate JSON key")
            value[key] = item
        return value

    def invalid_constant(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def _read_checked(path, expected_sha256, snapshots):
    path = Path(path).resolve()
    raw = path.read_bytes()
    _require(_sha(raw) == expected_sha256, f"File SHA256 mismatch: {path.name}")
    snapshots[path] = expected_sha256
    return raw


def _evidence_path(root, relative):
    relative = Path(relative)
    _require(not relative.is_absolute() and ".." not in relative.parts,
             "Evidence path must stay within the evidence root")
    path = (Path(root) / relative).resolve()
    _require(path.is_relative_to(Path(root).resolve()), "Evidence symlink escapes root")
    return path


def check_reuse_identity(*, job_id, ledger_path, expected_ledger_sha256,
                         plan_path, expected_plan_sha256, evidence_root=ROOT):
    """Verify an accepted identity without reading weights, EEG, or query rows."""
    snapshots = {}
    ledger = _json(_read_checked(ledger_path, expected_ledger_sha256, snapshots))
    plan = _json(_read_checked(plan_path, expected_plan_sha256, snapshots))
    entries, jobs = ledger["accepted_jobs"], plan["jobs"]
    accepted_ids, planned_ids = [e["job_id"] for e in entries], [j["job_id"] for j in jobs]
    _require(accepted_ids == planned_ids and len(set(accepted_ids)) == len(accepted_ids),
             "Reuse requires the complete contiguous accepted ledger, without duplicates")
    _require(job_id in accepted_ids, "Checkpoint job has not been accepted")
    entry, job = entries[accepted_ids.index(job_id)], jobs[planned_ids.index(job_id)]
    for key in ("job_id", "subject", "seed", "result_key"):
        _require(entry[key] == job[key], "Accepted and frozen job identities differ")
    ack_path = _evidence_path(evidence_root, entry["parent_acknowledgement"])
    ack_raw = ack_path.read_bytes()
    snapshots[ack_path] = _sha(ack_raw)
    ack = _json(ack_raw)
    _require(ack["status"] == "parent_acknowledged", "Actual parent acknowledgement required")
    # The first legacy acknowledgement predates job_id; its receipt binds its
    # unique archive/result key.  Later acknowledgements must name their job.
    _require(ack.get("job_id", job_id if job == jobs[0] and job_id == LEGACY_JOB_ID else None)
             == job_id,
             "Acknowledgement belongs to another job")
    receipt_path = _evidence_path(evidence_root, entry["receipt"])
    receipt = _json(_read_checked(receipt_path, ack["receipt_sha256"], snapshots))
    _require(receipt["status"] == "completed" and receipt["totals"]["failed_files"] == 0,
             "Full-GET receipt incomplete or failed")
    rows = [row for row in receipt["files"] if row["key"] == entry["result_key"]]
    _require(len(rows) == 1, "Accepted result must have exactly one full-GET object")
    row = rows[0]
    _require(row["sha256"] == entry["archive_sha256"]
             and row["verification"] == "full_get_sha256_verified"
             and row["get_http_status"] == 200
             and row["bytes"] == row["readback_bytes"]
             and 0 < row["bytes"] <= MAX_ARCHIVE_BYTES,
             "Accepted archive lacks exact full-GET identity")
    return copy.deepcopy(entry), copy.deepcopy(job), row["bytes"], snapshots


def _archive(raw):
    _require(0 < len(raw) <= MAX_ARCHIVE_BYTES, "Archive exceeds size bound")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        members = tar.getmembers()
        names = [member.name for member in members]
        _require(1 < len(names) <= 64 and len(names) == len(set(names)),
                 "Duplicate or unexpected archive members")
        _require(all(member.isfile() and not Path(member.name).is_absolute()
                     and ".." not in Path(member.name).parts for member in members),
                 "Only safe regular archive members are supported")
        _require(sum(member.size for member in members) <= MAX_ARCHIVE_BYTES,
                 "Archive payload exceeds size bound")
        data = {member.name: tar.extractfile(member).read() for member in members}
    manifest = _json(data["manifest.json"])
    entries = manifest["files"]
    _require(len(entries) == len(data) - 1
             and len({item["path"] for item in entries}) == len(entries)
             and {item["path"] for item in entries} == set(data) - {"manifest.json"},
             "Archive manifest does not cover every payload exactly once")
    for item in entries:
        value = data[item["path"]]
        _require(len(value) == item["bytes"] and _sha(value) == item["sha256"],
                 "Archive member SHA256/length mismatch")
    return manifest, data


def _state_digest(model, mean, scale, classes):
    tensors = dict(model.state_dict(), channel_mean=mean, channel_scale=scale, classes=classes)
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        array = tensor.detach().cpu().contiguous().numpy()
        for value in (name.encode(), str(array.dtype).encode(),
                      json.dumps(array.shape).encode(), array.tobytes()):
            digest.update(value)
    return digest.hexdigest()


def _build_cpu_model(config, metadata):
    """Build the official architecture directly, never a training wrapper."""
    from braindecode.models import EEGNet

    validate_training_contract(config)
    dims = config["input"]
    architecture = copy.deepcopy(config["architecture"])
    _require(architecture.pop("implementation") == "braindecode.models.EEGNet"
             and architecture.pop("activation") == "ELU", "Unfrozen architecture")
    kwargs = dict(n_chans=dims["n_channels"], n_outputs=dims["n_classes"],
                  n_times=dims["n_times"], sfreq=dims["sfreq_hz"],
                  activation=torch.nn.ELU, **architecture)
    _require(all(key in inspect.signature(EEGNet).parameters for key in kwargs),
             "Official architecture constructor differs from frozen configuration")
    _require(metadata["architecture"] == "braindecode.models.EEGNet"
             and metadata["constructor_kwargs"] == {
                 key: value for key, value in kwargs.items() if key != "activation"},
             "Bound architecture constructor mismatch")
    # Random constructor initialization is discarded by strict state loading;
    # preserve the caller's random state, numerical threads and global settings.
    with torch.random.fork_rng(devices=[]), torch.device("cpu"):
        torch.random.default_generator.manual_seed(0)
        model = EEGNet(**kwargs).cpu()
    return model


def check_source_replay_authorization(authorization_path, expected_authorization_sha256,
                                      *, bindings, job_id, snapshots):
    """An absent or changed exact-hash authorization fails before array access."""
    _require(authorization_path is not None and expected_authorization_sha256 is not None,
             "Real source replay requires a separately frozen actual parent authorization")
    authorization = _json(_read_checked(
        authorization_path, expected_authorization_sha256, snapshots))
    _require(authorization["status"] == "actual_parent_authorized_checkpoint_source_validation"
             and authorization["scope"] == "existing_source_validation_replay_only"
             and authorization["query_access"] is False
             and authorization["new_fits"] == 0
             and authorization["optimizer_instances"] == 0
             and authorization["weights_and_normalization_updates"] is False,
             "Source replay authorization scope is closed or differs")
    _require(all(authorization[key] == value for key, value in bindings.items()),
             "Source replay authorization does not bind the loaded frozen inputs")
    jobs = authorization["authorized_job_ids"]
    _require(isinstance(jobs, list) and len(jobs) == len(set(jobs)) and job_id in jobs,
             "Job not authorized for source replay")


def check_replay_cross_entropy(mean_loss, metadata):
    """Preserve the original source replay tolerance; software fixtures are not fits."""
    _require(metadata["synthetic"] is metadata["software_validation_only"],
             "Source replay synthetic/software flags disagree")
    synthetic = metadata["synthetic"] and metadata["software_validation_only"]
    original = metadata["source_validation_loss"]
    error = None if synthetic else abs(mean_loss - original)
    if not synthetic:
        _require(np.isfinite(mean_loss) and np.isfinite(original)
                 and error <= FROZEN_CE_ABSOLUTE_TOLERANCE,
                 "Source replay CE exceeds the frozen 1e-7 absolute tolerance")
    return dict(original_source_validation_mean_cross_entropy=original,
                replay_ce_absolute_error=error,
                replay_ce_absolute_tolerance=FROZEN_CE_ABSOLUTE_TOLERANCE,
                replay_ce_comparison_applicable=not synthetic,
                replay_ce_within_tolerance=None if synthetic else True)


class ReadOnlyCheckpoint:
    """Inference-only handle with no fit, optimizer, or normalization-fit API."""

    def __init__(self, model, payload, metadata, entry, validation, snapshots, bindings):
        self.__model = model.eval()
        for parameter in self.__model.parameters():
            parameter.requires_grad_(False)
            parameter.grad = None
        self.__mean = payload["channel_mean"].clone()
        self.__scale = payload["channel_scale"].clone()
        self.__classes = payload["classes"].clone()
        self.__metadata = copy.deepcopy(metadata)
        self.__entry = copy.deepcopy(entry)
        self.__validation = copy.deepcopy(validation)
        self.__snapshots = dict(snapshots)
        self.__bindings = dict(bindings)
        self.__context_sha = canonical_sha256(dict(metadata=self.__metadata, entry=self.__entry,
                                                   validation=self.__validation,
                                                   bindings=self.__bindings))
        self.__initial_state = metadata["frozen_state_sha256"]
        self.assert_unchanged()

    @property
    def identity(self):
        return dict(job_id=self.__entry["job_id"], subject=self.__entry["subject"],
                    seed=self.__entry["seed"], result_key=self.__entry["result_key"],
                    archive_sha256=self.__entry["archive_sha256"],
                    checkpoint_sha256=self.__metadata["checkpoint_sha256"],
                    archived_training_device=self.__metadata["config"]["device"],
                    execution_device="cpu", new_fit=False,
                    synthetic=self.__metadata["synthetic"],
                    software_validation_only=self.__metadata["software_validation_only"])

    def assert_unchanged(self):
        """Cover parameters, all buffers/BN, classes, normalization and input files."""
        _require(not any(module.training for module in self.__model.modules()),
                 "Evaluation mode changed")
        _require(all(not parameter.requires_grad and parameter.grad is None
                     for parameter in self.__model.parameters()), "Gradient state changed")
        _require(canonical_sha256(dict(metadata=self.__metadata, entry=self.__entry,
                                       validation=self.__validation, bindings=self.__bindings))
                 == self.__context_sha, "Bound checkpoint context changed")
        _require(_state_digest(self.__model, self.__mean, self.__scale, self.__classes)
                 == self.__initial_state, "Checkpoint parameters/BN/normalization changed")
        for path, expected in self.__snapshots.items():
            _require(_sha(path.read_bytes()) == expected, f"Input evidence changed: {path.name}")
        return self.__initial_state

    def evaluate_source_validation(self, X, labels, metadata, *, authorization_path=None,
                                   expected_authorization_sha256=None):
        """Replay only archived source-validation rows; query/future rows always fail.

        Arrays and labels are supplied by a separately reviewed caller.  This
        module has no EEG reader and no query interface.  Source-validation CE
        and logits are development replay, not a new experiment or generalization
        result.  No file, ledger, training flag, or accepted status is written.
        """
        self.assert_unchanged()
        expected = self.__metadata["source_validation_ids"]
        _require(isinstance(metadata, (list, tuple)) and len(metadata) == len(expected),
                 "Source validation requires the complete archived identity sequence")
        _require([row.get("trial_id") for row in metadata] == expected,
                 "Source validation identities/order differ from the accepted checkpoint")
        for row in metadata:
            frozen = self.__validation[row["trial_id"]]
            _require(all(row.get(key) == frozen[key]
                         for key in ("subject", "session", "run", "role", "label")),
                     "Only frozen source-validation metadata/labels are allowed")
        if not self.__metadata["software_validation_only"]:
            check_source_replay_authorization(
                authorization_path, expected_authorization_sha256,
                bindings=self.__bindings, job_id=self.__entry["job_id"],
                snapshots=self.__snapshots)
        y = np.asarray(labels)
        expected_labels = np.array([
            self.__metadata["config"]["input"]["class_mapping"][self.__validation[x]["label"]]
            for x in expected], dtype=np.int64)
        _require(y.shape == expected_labels.shape and np.issubdtype(y.dtype, np.integer)
                 and np.array_equal(y, expected_labels), "Labels differ from frozen source split")
        array = np.array(X, dtype=np.float32, copy=True)
        dims = self.__metadata["config"]["input"]
        _require(array.shape == (len(expected), dims["n_channels"], dims["n_times"])
                 and np.isfinite(array).all(), "Invalid source-validation tensor")
        for trial, trial_id in zip(array, expected, strict=True):
            # Exactly Kumar numeric_hash(trial, dtype="<f4"): little-endian
            # float32 values in C order, before source normalization.
            actual = _sha(np.asarray(trial, dtype="<f4", order="C").tobytes(order="C"))
            _require(actual == self.__validation[trial_id]["processed_window_numeric_sha256"],
                     "Processed source-validation trial SHA256 differs from the frozen split")
        normalized = (torch.from_numpy(array) - self.__mean) / self.__scale
        _require(torch.isfinite(normalized).all().item(), "Nonfinite frozen normalization")
        logits = []
        batch_size = self.__metadata["config"]["optimization"]["batch_size"]
        try:
            with torch.inference_mode():
                for start in range(0, len(normalized), batch_size):
                    result = self.__model(normalized[start:start + batch_size])
                    _require(result.shape == (min(batch_size, len(normalized) - start), 2)
                             and torch.isfinite(result).all().item(), "Invalid EEGNet logits")
                    logits.append(result.cpu().numpy().copy())
            logits = np.concatenate(logits).astype(np.float64)
            loss = np.logaddexp(logits[:, 0], logits[:, 1]) - logits[np.arange(len(y)), y]
        finally:
            after = self.assert_unchanged()
        mean_loss = float(loss.mean())
        ce_comparison = check_replay_cross_entropy(mean_loss, self.__metadata)
        return dict(identity=self.identity, scope="existing_source_validation_replay_only",
                    source_validation_trial_ids=list(expected), logits=logits,
                    mean_cross_entropy=mean_loss, processed_input_hashes_verified=True,
                    **ce_comparison, optimizer_instances_created=0,
                    optimizer_steps=0, new_fit=False, query_rows_loaded=0,
                    state_before_sha256=self.__initial_state, state_after_sha256=after,
                    input_files_unchanged=True, formal_scientific_gate_passed=False)


def load_accepted_checkpoint(archive_path, *, job_id, ledger_path, expected_ledger_sha256,
                             plan_path, expected_plan_sha256, split_path,
                             expected_split_sha256, evidence_root=ROOT,
                             software_validation_only=False):
    """Verify accepted bytes/context then construct a CPU eval-only handle.

    ``software_validation_only=True`` is exclusively for synthetic, untrained
    fixtures whose bound context explicitly records both software flags.  It
    cannot relabel an accepted real checkpoint as synthetic or vice versa.
    """
    entry, job, expected_bytes, snapshots = check_reuse_identity(
        job_id=job_id, ledger_path=ledger_path, expected_ledger_sha256=expected_ledger_sha256,
        plan_path=plan_path, expected_plan_sha256=expected_plan_sha256,
        evidence_root=evidence_root)
    _require(Path(archive_path).stat().st_size == expected_bytes, "Archive length mismatch")
    raw = _read_checked(archive_path, entry["archive_sha256"], snapshots)
    manifest, data = _archive(raw)
    _require(manifest.get("result_key", manifest.get("expected_R2_key")) == entry["result_key"],
             "Archive result key mismatch")
    legacy = job_id == LEGACY_JOB_ID and "job.json" not in data
    if legacy:
        _require(manifest["job"] == LEGACY_JOB_NAME, "Legacy manifest identity mismatch")
    else:
        _require("job.json" in data, "Only the accepted first legacy archive may lack job.json")
        for key in ("subject", "seed"):
            _require(manifest.get(key) == entry[key], "Archive manifest identity mismatch")
    if "job.json" in data:
        _require(_json(data["job.json"]) == job and manifest["job_id"] == job_id,
                 "Archive frozen job mismatch")
    record, metadata, config = [_json(data[name]) for name in (
        "fit_result.json", "weights.json", "training_config.json")]
    _require(record["subject"] == entry["subject"]
             and record["seed"] == metadata["seed"] == entry["seed"]
             and (record["job"] == LEGACY_JOB_NAME if legacy else record["job_id"] == job_id),
             "Checkpoint record identity mismatch")
    _require(record["status"] == ("fit_finished_backup_pending" if legacy else "fit_saved")
             and record["query_rows_loaded"] == 0
             and record["source_train_rows"] == 40 and record["source_validation_rows"] == 20,
             "Checkpoint source scope/status mismatch")
    _require(metadata["synthetic"] is software_validation_only
             and metadata["software_validation_only"] is software_validation_only
             and record["synthetic"] is software_validation_only,
             "Synthetic/software-only context differs from requested mode")
    _require(_sha(data["training_config.json"]) == job["training_config_sha256"]
             == record["training_config_sha256"] and metadata["config"] == config
             and canonical_sha256(config) == metadata["config_canonical_sha256"],
             "Checkpoint configuration mismatch")
    _require(expected_split_sha256 == job["split_sha256"]
             == (job["split_sha256"] if legacy else record["split_sha256"]),
             "Frozen split digest mismatch")
    split = _json(_read_checked(split_path, expected_split_sha256, snapshots))["trials"]
    source = {}
    for role in ("source_train", "source_validation"):
        rows = [row for row in split if row["subject"] == entry["subject"]
                and row["role"] == role and row["included"]]
        ids = metadata[role + "_ids"]
        _require(len(ids) == len(set(ids)) == len(rows)
                 and set(ids) == {row["trial_id"] for row in rows}
                 and len(rows) == (40 if role == "source_train" else 20)
                 and all(row["session"] == "ses-0" and row["run"] in (
                     {"run-0", "run-1"} if role == "source_train" else {"run-2"}) for row in rows),
                 "Checkpoint frozen source identities differ")
        source[role] = {row["trial_id"]: row for row in rows}
    checkpoint_sha = _sha(data["weights.pt"])
    _require(checkpoint_sha == record["checkpoint_sha256"] == metadata["checkpoint_sha256"],
             "Checkpoint weights SHA256 mismatch")
    payload = torch.load(io.BytesIO(data["weights.pt"]), map_location="cpu", weights_only=True)
    _require(set(payload) == {"model_state_dict", "channel_mean", "channel_scale",
                              "classes", "context_utf8"}, "Unexpected checkpoint payload")
    encoded = payload["context_utf8"]
    _require(isinstance(encoded, torch.Tensor) and encoded.dtype == torch.uint8
             and encoded.ndim == 1 and encoded.numel() <= 1_000_000,
             "Invalid bound checkpoint context")
    _require(_json(bytes(encoded.tolist())) == {
        key: value for key, value in metadata.items() if key != "checkpoint_sha256"},
        "Checkpoint sidecar is not bound to the accepted weights")
    for name in ("channel_mean", "channel_scale"):
        tensor = payload[name]
        _require(isinstance(tensor, torch.Tensor) and tensor.dtype == torch.float32
                 and tuple(tensor.shape) == (1, 22, 1) and torch.isfinite(tensor).all().item(),
                 "Invalid frozen normalization tensor")
    _require((payload["channel_scale"] > 0).all().item()
             and isinstance(payload["classes"], torch.Tensor)
             and payload["classes"].dtype == torch.int64
             and torch.equal(payload["classes"], torch.tensor([0, 1], dtype=torch.int64,
                                                              device="cpu")),
             "Invalid frozen channel scales/classes")
    _require(all(isinstance(value, torch.Tensor) and torch.isfinite(value).all().item()
                 for value in payload["model_state_dict"].values()), "Invalid checkpoint state")
    model = _build_cpu_model(config, metadata)
    model.load_state_dict(payload["model_state_dict"], strict=True)
    return ReadOnlyCheckpoint(model, payload, metadata, entry,
                              source["source_validation"], snapshots,
                              dict(accepted_ledger_sha256=expected_ledger_sha256,
                                   frozen_plan_sha256=expected_plan_sha256,
                                   split_manifest_sha256=expected_split_sha256))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-plan", action="store_true", help="metadata only; no weights/data")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    entry, _, _, _ = check_reuse_identity(
        job_id=args.job_id, ledger_path=args.ledger, expected_ledger_sha256=args.ledger_sha256,
        plan_path=args.plan, expected_plan_sha256=args.plan_sha256)
    print(json.dumps(dict(status="accepted_identity_verified_metadata_only", identity=entry,
                          checkpoint_loaded=False, new_fits=0, query_rows_loaded=0,
                          optimizer_instances_created=0, scientific_gate_passed=False)))


if __name__ == "__main__":
    main()
