"""Accepted EEGNet checkpoints: authorized read-only query evaluation on CPU.

This module has no CLI, EEG reader, optimizer, fit or query-data download API.
Metadata-only dispatch and real execution authorization belong to the separately
frozen outer operation. The old source-validation reuse module stays unchanged.
"""
from __future__ import annotations

import copy
import io
import math
import re
import time
from pathlib import Path

import numpy as np
import torch

import evaluate_kumar_checkpoint_reuse as reuse
from train_kumar_eegnet import canonical_sha256

ROOT = reuse.ROOT
LEGACY_JOB_ID, LEGACY_JOB_NAME = reuse.LEGACY_JOB_ID, reuse.LEGACY_JOB_NAME
_require, _sha, _json = reuse._require, reuse._sha, reuse._json
_read_checked, _archive, _build_cpu_model = reuse._read_checked, reuse._archive, reuse._build_cpu_model
check_reuse_identity = reuse.check_reuse_identity
ALLOWED_ROLES = frozenset({'source_query', 'target_query'})
HELPERS_SHA256 = '838f3ed7b8f67c65dcf27b3ef43aace29db9464c8cdaae730be5dfebc92ba4e2'
AUTH_STATUS = 'parent_reviewed_frozen_checkpoint_query_evaluation_authorized'
AUTH_SCOPE = 'accepted54_always_frozen_query_only'


def check_query_authorization(path, expected_sha256, *, bindings, job_id, snapshots, now=None):
    """Fail before tensor loading or array conversion, including on expired scope."""
    _require(path is not None and expected_sha256 is not None,
             'Real query evaluation requires exact external authorization')
    authorization = _json(_read_checked(path, expected_sha256, snapshots))
    _require(authorization.get('status') == AUTH_STATUS and authorization.get('scope') == AUTH_SCOPE
             and authorization.get('query_evaluation_authorized') is True
             and all(authorization.get(key) is False for key in (
                 'training_authorized', 'optimizer_updates_authorized',
                 'target_support_access_authorized', 'new_strategy_authorized',
                 'new_resources_authorized')), 'Query authorization scope differs')
    _require(all(authorization.get(key) == value for key, value in bindings.items()),
             'Query authorization frozen bindings differ')
    jobs = authorization.get('approved_job_ids')
    _require(isinstance(jobs, list) and all(isinstance(j, str) for j in jobs)
             and len(jobs) == len(set(jobs)) and job_id in jobs,
             'Query checkpoint job is not uniquely authorized')
    start, deadline = authorization.get('not_before_unix'), authorization.get('deadline_unix')
    _require(all(isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)
                 for value in (start, deadline)), 'Query authorization needs finite absolute times')
    observed = time.time() if now is None else now
    _require(0 < deadline - start <= 7200 and start <= observed < deadline,
             'Query authorization window is expired, not started or exceeds7200s')
    return authorization


def query_rows_from_split(split, manifest, subject):
    """Bind every included query in original split order, never select by outcome."""
    _require(set(manifest['allowed_roles']) == ALLOWED_ROLES,
             'Query input manifest roles differ')
    subjects = manifest['subjects']
    _require(isinstance(subjects, list) and len(subjects) == len(set(subjects)) and subject in subjects,
             'Query participant absent from frozen manifest')
    all_rows = [row for row in split if row['subject'] in subjects and row['included']
                and row['role'] in ALLOWED_ROLES]
    all_ids = [row['trial_id'] for row in all_rows]
    _require(len(all_ids) == len(set(all_ids)) and all_ids == manifest['included_query_trial_ids'],
             'Input manifest and split included-query identities/order differ')
    for row in all_rows:
        valid = (row['role'] == 'source_query' and row['session'] == 'ses-0' and row['run'] == 'run-3') or (
            row['role'] == 'target_query' and row['session'] in {'ses-1', 'ses-2', 'ses-3', 'ses-4', 'ses-5'}
            and row['run'] in ({'run-1', 'run-2', 'run-3'} if row['session'] == 'ses-1' else {'run-1', 'run-2'}))
        _require(valid and row['label'] in {'left_hand', 'right_hand'}
                 and isinstance(row['processed_window_numeric_sha256'], str)
                 and len(row['processed_window_numeric_sha256']) == 64,
                 'Forbidden query run/role/label or missing processed hash')
    rows = [row for row in all_rows if row['subject'] == subject]
    _require({(r['session'], r['role']) for r in rows} == {('ses-0', 'source_query')} | {
        (f'ses-{i}', 'target_query') for i in range(1, 6)}, 'All six fixed query sessions required')
    return rows


class FrozenQueryCheckpoint:
    """Only fixed-query inference; no training or update interface."""

    def __init__(self, model, payload, metadata, entry, rows, snapshots, bindings,
                 authorization_path, expected_authorization_sha256):
        self.__model = model.eval()
        for parameter in self.__model.parameters():
            parameter.requires_grad_(False)
            parameter.grad = None
        self.__mean = payload['channel_mean'].clone()
        self.__scale = payload['channel_scale'].clone()
        self.__classes = payload['classes'].clone()
        self.__metadata = copy.deepcopy(metadata)
        self.__entry = copy.deepcopy(entry)
        self.__rows = copy.deepcopy(rows)
        self.__snapshots = dict(snapshots)
        self.__bindings = dict(bindings)
        self.__authorization_path = authorization_path
        self.__authorization_sha256 = expected_authorization_sha256
        self.__context_sha = canonical_sha256(dict(metadata=self.__metadata, entry=self.__entry,
                                                   rows=self.__rows, bindings=self.__bindings))
        self.__initial_state = metadata['frozen_state_sha256']
        self.assert_unchanged()

    @property
    def identity(self):
        return dict(job_id=self.__entry['job_id'], subject=self.__entry['subject'], seed=self.__entry['seed'],
                    result_key=self.__entry['result_key'], archive_sha256=self.__entry['archive_sha256'],
                    checkpoint_sha256=self.__metadata['checkpoint_sha256'],
                    archived_training_device=self.__metadata['config']['device'], execution_device='cpu',
                    synthetic=self.__metadata['synthetic'],
                    software_validation_only=self.__metadata['software_validation_only'], new_fit=False)

    def assert_unchanged(self):
        _require(not any(module.training for module in self.__model.modules()), 'Evaluation mode changed')
        _require(all(not parameter.requires_grad and parameter.grad is None
                     for parameter in self.__model.parameters()), 'Gradient state changed')
        _require(canonical_sha256(dict(metadata=self.__metadata, entry=self.__entry,
                                      rows=self.__rows, bindings=self.__bindings)) == self.__context_sha,
                 'Bound query checkpoint context changed')
        _require(reuse._state_digest(self.__model, self.__mean, self.__scale, self.__classes)
                 == self.__initial_state, 'Checkpoint parameters/BN/normalization changed')
        for path, expected in self.__snapshots.items():
            _require(_sha(path.read_bytes()) == expected, 'Input evidence changed: ' + path.name)
        return self.__initial_state

    def _check_authorization(self):
        if not self.__metadata['software_validation_only']:
            check_query_authorization(self.__authorization_path, self.__authorization_sha256,
                                      bindings=self.__bindings, job_id=self.__entry['job_id'],
                                      snapshots=self.__snapshots)

    def evaluate_queries(self, X, labels, metadata):
        """One subject's complete query sequence, fixed hashes and argmax only."""
        self._check_authorization()
        before = self.assert_unchanged()
        _require(isinstance(metadata, (list, tuple)) and len(metadata) == len(self.__rows)
                 and [row.get('trial_id') for row in metadata] == [row['trial_id'] for row in self.__rows],
                 'Query identities/order differ from the complete frozen subject sequence')
        for actual, frozen in zip(metadata, self.__rows, strict=True):
            _require(all(actual.get(key) == frozen[key] for key in (
                'subject', 'session', 'run', 'role', 'label', 'included',
                'processed_window_numeric_sha256')), 'Query metadata/labels differ from frozen split')
        y = np.asarray(labels)
        expected_labels = np.asarray([self.__metadata['config']['input']['class_mapping'][r['label']]
                                      for r in self.__rows], dtype=np.int64)
        _require(y.shape == expected_labels.shape and np.issubdtype(y.dtype, np.integer)
                 and np.array_equal(y, expected_labels), 'Query labels differ from frozen split')
        array = np.array(X, dtype=np.float32, copy=True)
        dims = self.__metadata['config']['input']
        _require(array.shape == (len(self.__rows), dims['n_channels'], dims['n_times'])
                 and np.isfinite(array).all(), 'Invalid query tensor')
        for trial, row in zip(array, self.__rows, strict=True):
            actual = _sha(np.asarray(trial, dtype='<f4', order='C').tobytes(order='C'))
            _require(actual == row['processed_window_numeric_sha256'], 'Processed query trial SHA256 differs')
        normalized = (torch.from_numpy(array) - self.__mean) / self.__scale
        _require(torch.isfinite(normalized).all().item(), 'Nonfinite frozen normalization')
        batch_size = self.__metadata['config']['optimization']['batch_size']
        logits = []
        try:
            with torch.inference_mode():
                for start in range(0, len(normalized), batch_size):
                    self._check_authorization()
                    result = self.__model(normalized[start:start + batch_size])
                    _require(result.shape == (min(batch_size, len(normalized) - start), 2)
                             and torch.isfinite(result).all().item(), 'Invalid EEGNet logits')
                    logits.append(result.cpu().numpy().copy())
        finally:
            after = self.assert_unchanged()
        self._check_authorization()
        values = np.concatenate(logits).astype(np.float64)
        predicted = values.argmax(axis=1)
        predictions = [dict(trial_id=row['trial_id'], subject=row['subject'], seed=self.__entry['seed'],
                            session=row['session'], run=row['run'], role=row['role'],
                            y_true=int(y[i]), y_pred=int(predicted[i]),
                            logit_0=float(values[i, 0]), logit_1=float(values[i, 1]))
                       for i, row in enumerate(self.__rows)]
        metrics = []
        for session, role in sorted({(r['session'], r['role']) for r in self.__rows}):
            indices = [i for i, r in enumerate(self.__rows) if (r['session'], r['role']) == (session, role)]
            matrix = np.bincount(2 * y[indices] + predicted[indices], minlength=4).reshape(2, 2)
            totals = matrix.sum(axis=1)
            recalls = [float(matrix[k, k] / totals[k]) if totals[k] else None for k in range(2)]
            metrics.append(dict(subject=self.__entry['subject'], seed=self.__entry['seed'], session=session,
                                role=role, n=len(indices), confusion_matrix=matrix.tolist(), class_recalls=recalls,
                                balanced_accuracy=None if None in recalls else float(np.mean(recalls)),
                                balanced_accuracy_status='not_estimable_missing_class' if None in recalls else 'estimated',
                                predicted_class_counts=matrix.sum(axis=0).tolist(),
                                class_collapse=bool(np.any(matrix.sum(axis=0) == 0))))
        return dict(identity=self.identity, scope=AUTH_SCOPE, predictions=predictions, session_metrics=metrics,
                    optimizer_instances_created=0, optimizer_steps=0, new_fit=False,
                    query_rows_evaluated=len(self.__rows),
                    real_query_rows_loaded=0 if self.__metadata['software_validation_only'] else len(self.__rows),
                    processed_input_hashes_verified=True, source_training_context_preserved=True,
                    state_before_sha256=before, state_after_sha256=after, input_files_unchanged=True,
                    parameter_BN_normalization_updates=False, query_labels_used_for='fixed_metrics_only',
                    scientific_acceptance_pending=True)


def load_frozen_query_checkpoint(archive_path, *, job_id, ledger_path, expected_ledger_sha256,
                                 plan_path, expected_plan_sha256, split_path, expected_split_sha256,
                                 query_manifest_path, expected_query_manifest_sha256,
                                 operation_contract_sha256, expected_commit, authorization_path=None,
                                 expected_authorization_sha256=None, evidence_root=ROOT,
                                 software_validation_only=False):
    """Original accepted-loading guards plus query authorization before torch.load.

    The archive/context/source/tensor checks below retain the old accepted loader's
    guards; no private handle access or mutation of its frozen module is needed.
    Software mode accepts only cryptographically bound synthetic untrained weights.
    """
    _require(type(software_validation_only) is bool, 'Explicit boolean software mode required')
    _require(isinstance(expected_commit, str) and re.fullmatch(r'[0-9a-f]{40}', expected_commit)
             and isinstance(operation_contract_sha256, str)
             and re.fullmatch(r'[0-9a-f]{64}', operation_contract_sha256),
             'Exact execution commit and operation contract SHA256 required')
    _require(_sha(Path(reuse.__file__).read_bytes()) == HELPERS_SHA256,
             'Frozen source-reuse helpers changed')
    bindings = dict(reviewed_commit=expected_commit, contract_sha256=operation_contract_sha256,
                    accepted_ledger_sha256=expected_ledger_sha256, source_plan_sha256=expected_plan_sha256,
                    split_manifest_sha256=expected_split_sha256,
                    query_input_manifest_sha256=expected_query_manifest_sha256)
    auth_snapshots = {}
    if not software_validation_only:
        check_query_authorization(authorization_path, expected_authorization_sha256,
                                  bindings=bindings, job_id=job_id, snapshots=auth_snapshots)
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
    query_manifest = _json(_read_checked(query_manifest_path, expected_query_manifest_sha256, snapshots))
    query_rows = query_rows_from_split(split, query_manifest, entry["subject"])
    checkpoint_sha = _sha(data["weights.pt"])
    _require(checkpoint_sha == record["checkpoint_sha256"] == metadata["checkpoint_sha256"],
             "Checkpoint weights SHA256 mismatch")
    if not software_validation_only:
        check_query_authorization(authorization_path, expected_authorization_sha256,
                                  bindings=bindings, job_id=job_id, snapshots=auth_snapshots)
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
    snapshots.update(auth_snapshots)
    return FrozenQueryCheckpoint(model, payload, metadata, entry, query_rows, snapshots, bindings,
                                 authorization_path, expected_authorization_sha256)
