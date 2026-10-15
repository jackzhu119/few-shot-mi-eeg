"""Untrained synthetic query fixtures only; no fit, optimizer, real weights or EEG."""
import copy
import json
import time

import numpy as np
import pytest
import torch

import evaluate_kumar_frozen_queries as query
from test_kumar_checkpoint_reuse import (  # noqa: F401
    bundle as source_bundle,
    files_digest,
    forbid_training,
    raw_json,
    repack_software_fixture,
    sha,
    untrained_payload,
)

pytestmark = pytest.mark.deep


@pytest.fixture
def bundle(source_bundle):  # noqa: F811 - pytest resolves the imported fixture by name
    value = source_bundle
    rows = []
    for session in range(6):
        rows.extend(dict(trial_id=f'synthetic-query/{session}/{i}', subject='synthetic-subject',
                         session=f'ses-{session}', run='run-3' if session == 0 else 'run-1',
                         role='source_query' if session == 0 else 'target_query', included=True,
                         label='left_hand' if i % 2 == 0 else 'right_hand') for i in range(4))
    X = np.random.default_rng(432).normal(0, 1e-5, (len(rows), 22, 640)).astype(np.float32)
    for trial, row in zip(X, rows, strict=True):
        row['processed_window_numeric_sha256'] = sha(np.asarray(trial, dtype='<f4').tobytes())
    split_path = value['kwargs']['split_path']
    split = json.loads(split_path.read_text())
    split['trials'].extend(rows)
    # A frozen partial query stays excluded rather than padded or replaced.
    split['trials'].append(dict(rows[-1], trial_id='synthetic-query/partial', included=False,
                                processed_window_numeric_sha256=None))
    split_path.write_bytes(raw_json(split))
    value['job']['split_sha256'] = sha(split_path.read_bytes())
    value['kwargs']['expected_split_sha256'] = value['job']['split_sha256']
    record = json.loads(value['data']['fit_result.json'])
    record['split_sha256'] = value['job']['split_sha256']
    value['data']['fit_result.json'] = raw_json(record)
    value['data']['job.json'] = raw_json(value['job'])
    plan = value['kwargs']['plan_path']
    plan.write_bytes(raw_json({'jobs': [value['job']]}))
    value['kwargs']['expected_plan_sha256'] = sha(plan.read_bytes())
    manifest = value['path'].parent / 'query-manifest.synthetic.json'
    manifest.write_bytes(raw_json(dict(allowed_roles=['source_query', 'target_query'],
        subjects=['synthetic-subject'], included_query_trial_ids=[r['trial_id'] for r in rows])))
    value['kwargs'].update(query_manifest_path=manifest,
        expected_query_manifest_sha256=sha(manifest.read_bytes()),
        operation_contract_sha256='a' * 64, expected_commit='b' * 40)
    repack_software_fixture(value)
    value.update(X=X, labels=np.tile([0, 1], 12).astype(np.int64), rows=rows)
    return value


def load(bundle):
    return query.load_frozen_query_checkpoint(bundle['path'], **bundle['kwargs'])


class ForbiddenArray:
    def __array__(self, *args, **kwargs):
        pytest.fail('Array accessed before frozen role/identity/authorization validation')


def synthetic_authorization(tmp_path, bindings=None):
    bindings = bindings or dict(reviewed_commit='b' * 40, contract_sha256='a' * 64,
        accepted_ledger_sha256='c' * 64, source_plan_sha256='d' * 64,
        split_manifest_sha256='e' * 64, query_input_manifest_sha256='f' * 64)
    now = time.time()
    auth = dict(bindings, status=query.AUTH_STATUS, scope=query.AUTH_SCOPE,
                query_evaluation_authorized=True, training_authorized=False,
                optimizer_updates_authorized=False, target_support_access_authorized=False,
                new_strategy_authorized=False, new_resources_authorized=False,
                approved_job_ids=['synthetic-untrained-job'], not_before_unix=now - 1,
                deadline_unix=now + 30, synthetic_authorization_logic_test_only=True)
    path = tmp_path / 'synthetic-authorization.json'
    path.write_bytes(raw_json(auth))
    return path, auth, bindings


def test_synthetic_query_inference_preserves_state_files_rng_threads_and_metrics(bundle, monkeypatch):
    forbid_training(monkeypatch)
    before_files = files_digest(bundle['path'].parent)
    rng = torch.random.get_rng_state().clone()
    np_rng = copy.deepcopy(np.random.get_state())
    thread_count = torch.get_num_threads()
    safe_load = torch.load
    calls = []
    def checked_load(*args, **kwargs):
        calls.append(kwargs)
        return safe_load(*args, **kwargs)
    monkeypatch.setattr(torch, 'load', checked_load)
    handle = load(bundle)
    assert calls == [dict(map_location='cpu', weights_only=True)]
    assert not any(hasattr(handle, name) for name in ['fit', 'fit_source', 'optimizer', 'model_'])
    original_x, original_y = bundle['X'].copy(), bundle['labels'].copy()
    first = handle.evaluate_queries(bundle['X'], bundle['labels'], bundle['rows'])
    second = handle.evaluate_queries(bundle['X'], bundle['labels'], bundle['rows'])
    assert first == second
    assert first['state_before_sha256'] == first['state_after_sha256'] == handle.assert_unchanged()
    assert first['query_rows_evaluated'] == 24 and first['real_query_rows_loaded'] == 0
    assert first['optimizer_instances_created'] == first['optimizer_steps'] == 0
    assert first['new_fit'] is first['parameter_BN_normalization_updates'] is False
    assert first['source_training_context_preserved'] is True
    assert first['identity']['synthetic'] is first['identity']['software_validation_only'] is True
    assert len(first['predictions']) == 24 and len(first['session_metrics']) == 6
    for metric in first['session_metrics']:
        rows = [r for r in first['predictions'] if r['session'] == metric['session']]
        confusion = [[sum(r['y_true'] == a and r['y_pred'] == b for r in rows) for b in [0, 1]]
                     for a in [0, 1]]
        assert metric['confusion_matrix'] == confusion
        assert metric['balanced_accuracy'] == (confusion[0][0] / 2 + confusion[1][1] / 2) / 2
        assert all(r['y_pred'] == (0 if r['logit_0'] >= r['logit_1'] else 1) for r in rows)
    assert torch.equal(rng, torch.random.get_rng_state()) and torch.get_num_threads() == thread_count
    after_np = np.random.get_state()
    assert np_rng[0] == after_np[0] and np.array_equal(np_rng[1], after_np[1]) and np_rng[2:] == after_np[2:]
    assert before_files == files_digest(bundle['path'].parent)
    np.testing.assert_array_equal(original_x, bundle['X'])
    np.testing.assert_array_equal(original_y, bundle['labels'])


def test_real_mode_missing_authorization_rejects_before_any_archive_or_tensor_read(bundle, monkeypatch):
    bundle['kwargs']['software_validation_only'] = False
    monkeypatch.setattr(query, 'check_reuse_identity', lambda **kw: pytest.fail('Metadata/weights before authorization'))
    monkeypatch.setattr(torch, 'load', lambda *a, **kw: pytest.fail('Tensor load before authorization'))
    with pytest.raises(ValueError, match='external authorization'):
        load(bundle)


def test_authorization_is_checked_before_query_array_conversion(bundle, monkeypatch):
    handle = load(bundle)
    def unauthorized():
        raise ValueError('synthetic expired authorization')
    monkeypatch.setattr(handle, '_check_authorization', unauthorized)
    with pytest.raises(ValueError, match='expired authorization'):
        handle.evaluate_queries(ForbiddenArray(), ForbiddenArray(), bundle['rows'])


@pytest.mark.parametrize('violation', ['support', 'source_train', 'future', 'wrong_run', 'wrong_label',
                                      'duplicate', 'missing', 'reordered', 'other_subject', 'partial'])
def test_roles_metadata_and_complete_order_fail_before_arrays(bundle, violation):
    handle = load(bundle)
    rows = copy.deepcopy(bundle['rows'])
    if violation in {'support', 'source_train'}:
        rows[0]['role'] = 'target_support' if violation == 'support' else 'source_train'
    elif violation == 'future':
        rows[0]['session'] = 'ses-6'
    elif violation == 'wrong_run':
        rows[0]['run'] = 'run-0'
    elif violation == 'wrong_label':
        rows[0]['label'] = 'right_hand'
    elif violation == 'duplicate':
        rows[-1] = rows[0]
    elif violation == 'missing':
        rows.pop()
    elif violation == 'reordered':
        rows.reverse()
    elif violation == 'other_subject':
        rows[0]['subject'] = 'synthetic-other'
    else:
        rows[0]['included'] = False
    with pytest.raises(ValueError, match='identities/order|metadata/labels'):
        handle.evaluate_queries(ForbiddenArray(), ForbiddenArray(), rows)
    handle.assert_unchanged()


@pytest.mark.parametrize('field', ['archive', 'ledger', 'plan', 'split', 'query_manifest', 'receipt', 'ack'])
def test_changed_evidence_rejects_before_tensors(bundle, monkeypatch, field):
    if field == 'archive':
        path = bundle['path']
    elif field in {'ledger', 'plan', 'split', 'query_manifest'}:
        path = bundle['kwargs'][field + '_path']
    else:
        path = bundle['path'].parent / (field + '.json')
    path.write_bytes(raw_json({'status': 'changed'}) if field == 'ack' else path.read_bytes() + b' ')
    monkeypatch.setattr(torch, 'load', lambda *a, **kw: pytest.fail('Tensor read before evidence rejection'))
    with pytest.raises(ValueError):
        load(bundle)


@pytest.mark.parametrize('mutation', ['parameter', 'bn', 'mean', 'scale', 'classes', 'mode', 'gradient', 'context'])
def test_state_tampering_rejects_and_does_not_restore(bundle, mutation):
    handle = load(bundle)
    model = handle._FrozenQueryCheckpoint__model
    with torch.no_grad():
        if mutation == 'parameter':
            next(model.parameters()).view(-1)[0].add_(1)
        elif mutation == 'bn':
            next(m for m in model.modules() if isinstance(m, torch.nn.modules.batchnorm._BatchNorm)).running_mean[0].add_(1)
        elif mutation in {'mean', 'scale'}:
            getattr(handle, '_FrozenQueryCheckpoint__' + mutation)[0, 0, 0].add_(1)
        elif mutation == 'classes':
            handle._FrozenQueryCheckpoint__classes[0] = 1
        elif mutation == 'mode':
            model.train()
        elif mutation == 'gradient':
            next(model.parameters()).requires_grad_(True)
        else:
            handle._FrozenQueryCheckpoint__metadata['seed'] += 1
    with pytest.raises(ValueError, match='changed'):
        handle.evaluate_queries(ForbiddenArray(), ForbiddenArray(), bundle['rows'])
    with pytest.raises(ValueError, match='changed'):
        handle.assert_unchanged()


@pytest.mark.parametrize('mutation', ['parameter', 'bn', 'normalization'])
def test_during_forward_mutation_cannot_return_success(bundle, mutation):
    handle = load(bundle)
    def mutate(module, _inputs):
        if mutation == 'parameter':
            next(module.parameters()).view(-1)[0].add_(1)
        elif mutation == 'bn':
            next(m for m in module.modules() if isinstance(m, torch.nn.modules.batchnorm._BatchNorm)).num_batches_tracked.add_(1)
        else:
            handle._FrozenQueryCheckpoint__scale[0, 0, 0].mul_(2)
    handle._FrozenQueryCheckpoint__model.register_forward_pre_hook(mutate)
    before = files_digest(bundle['path'].parent)
    with pytest.raises(ValueError, match='parameters/BN/normalization changed'):
        handle.evaluate_queries(bundle['X'], bundle['labels'], bundle['rows'])
    assert before == files_digest(bundle['path'].parent)


def test_changed_signal_hash_and_fractional_labels_reject_without_forward(bundle, monkeypatch):
    handle = load(bundle)
    monkeypatch.setattr(handle._FrozenQueryCheckpoint__model, 'forward', lambda *a: pytest.fail('Invalid input reached forward'))
    changed = bundle['X'].copy()
    changed[0, 0, 0] = np.nextafter(changed[0, 0, 0], np.float32(np.inf))
    with pytest.raises(ValueError, match='Processed query trial SHA256'):
        handle.evaluate_queries(changed, bundle['labels'], bundle['rows'])
    with pytest.raises(ValueError, match='Query labels'):
        handle.evaluate_queries(bundle['X'], bundle['labels'].astype(float), bundle['rows'])
    handle.assert_unchanged()


@pytest.mark.parametrize('field,value', [
    ('status', 'proposal_only'), ('scope', 'source_validation'), ('query_evaluation_authorized', False),
    ('training_authorized', True), ('optimizer_updates_authorized', True),
    ('target_support_access_authorized', True), ('new_strategy_authorized', True), ('new_resources_authorized', True),
    ('accepted_ledger_sha256', 'changed'), ('source_plan_sha256', 'changed'), ('split_manifest_sha256', 'changed'),
    ('query_input_manifest_sha256', 'changed'), ('contract_sha256', 'changed'), ('reviewed_commit', 'changed'),
    ('approved_job_ids', []), ('approved_job_ids', ['synthetic-untrained-job'] * 2),
    ('not_before_unix', float('inf')), ('deadline_unix', 0),
])
def test_authorization_scope_binding_and_absolute_window_reject(tmp_path, field, value):
    path, auth, bindings = synthetic_authorization(tmp_path)
    auth[field] = value
    # Nonfinite values are encoded explicitly to test the strict JSON reader.
    path.write_text(json.dumps(auth))
    with pytest.raises(ValueError):
        query.check_query_authorization(path, sha(path.read_bytes()), bindings=bindings,
                                       job_id='synthetic-untrained-job', snapshots={})


def test_valid_authorization_logic_and_expiry_are_rechecked(tmp_path):
    path, auth, bindings = synthetic_authorization(tmp_path)
    snapshots = {}
    query.check_query_authorization(path, sha(path.read_bytes()), bindings=bindings,
                                   job_id='synthetic-untrained-job', snapshots=snapshots)
    assert snapshots == {path.resolve(): sha(path.read_bytes())}
    with pytest.raises(ValueError, match='window'):
        query.check_query_authorization(path, sha(path.read_bytes()), bindings=bindings,
            job_id='synthetic-untrained-job', snapshots={}, now=auth['deadline_unix'])
    auth['deadline_unix'] = auth['not_before_unix'] + 7201
    path.write_bytes(raw_json(auth))
    with pytest.raises(ValueError, match='7200s'):
        query.check_query_authorization(path, sha(path.read_bytes()), bindings=bindings,
            job_id='synthetic-untrained-job', snapshots={})


def test_synthetic_checkpoint_cannot_be_relabelled_real_even_with_scope_record(bundle, monkeypatch):
    bundle['kwargs']['software_validation_only'] = False
    bindings = dict(reviewed_commit=bundle['kwargs']['expected_commit'],
        contract_sha256=bundle['kwargs']['operation_contract_sha256'],
        accepted_ledger_sha256=bundle['kwargs']['expected_ledger_sha256'],
        source_plan_sha256=bundle['kwargs']['expected_plan_sha256'],
        split_manifest_sha256=bundle['kwargs']['expected_split_sha256'],
        query_input_manifest_sha256=bundle['kwargs']['expected_query_manifest_sha256'])
    path, _, _ = synthetic_authorization(bundle['path'].parent, bindings)
    bundle['kwargs'].update(authorization_path=path, expected_authorization_sha256=sha(path.read_bytes()))
    monkeypatch.setattr(torch, 'load', lambda *a, **kw: pytest.fail('Relabelled fixture reached tensors'))
    with pytest.raises(ValueError, match='Synthetic/software-only'):
        load(bundle)


@pytest.mark.parametrize('mutation', ['sidecar', 'source_ids', 'manifest_order', 'manifest_role'])
def test_bound_context_source_scope_and_manifest_reject_before_weights(bundle, monkeypatch, mutation):
    if mutation in {'sidecar', 'source_ids'}:
        metadata = json.loads(bundle['data']['weights.json'])
        if mutation == 'sidecar':
            metadata['selected_epoch'] += 1
        else:
            metadata['source_train_ids'] = metadata['source_train_ids'][1:]
        bundle['data']['weights.json'] = raw_json(metadata)
        repack_software_fixture(bundle)
    else:
        path = bundle['kwargs']['query_manifest_path']
        value = json.loads(path.read_text())
        if mutation == 'manifest_order':
            value['included_query_trial_ids'].reverse()
        else:
            value['allowed_roles'].append('target_support')
        path.write_bytes(raw_json(value))
        bundle['kwargs']['expected_query_manifest_sha256'] = sha(path.read_bytes())
    if mutation != 'sidecar':
        monkeypatch.setattr(torch, 'load', lambda *a, **kw: pytest.fail('Invalid source/manifest reached tensors'))
    with pytest.raises(ValueError, match='sidecar is not bound|source identities|identities/order|manifest roles'):
        load(bundle)


def test_legacy_first_layout_has_same_readonly_query_path(bundle):
    bundle['legacy'] = True
    bundle['job']['job_id'] = query.LEGACY_JOB_ID
    bundle['kwargs']['job_id'] = query.LEGACY_JOB_ID
    plan = bundle['kwargs']['plan_path']
    plan.write_bytes(raw_json({'jobs': [bundle['job']]}))
    bundle['kwargs']['expected_plan_sha256'] = sha(plan.read_bytes())
    del bundle['data']['job.json']
    record = json.loads(bundle['data']['fit_result.json'])
    record.pop('job_id')
    record.pop('split_sha256')
    record.update(job=query.LEGACY_JOB_NAME, status='fit_finished_backup_pending')
    bundle['data']['fit_result.json'] = raw_json(record)
    path = bundle['kwargs']['ledger_path']
    ledger = json.loads(path.read_text())
    ledger['accepted_jobs'][0]['job_id'] = query.LEGACY_JOB_ID
    path.write_bytes(raw_json(ledger))
    path = bundle['path'].parent / 'ack.json'
    ack = json.loads(path.read_text())
    ack.pop('job_id')
    path.write_bytes(raw_json(ack))
    repack_software_fixture(bundle)
    handle = load(bundle)
    result = handle.evaluate_queries(bundle['X'], bundle['labels'], bundle['rows'])
    assert result['identity']['job_id'] == query.LEGACY_JOB_ID
    assert result['state_before_sha256'] == result['state_after_sha256']


def test_all_original_loading_guards_remain_in_new_loader():
    """The immutable loader's sensitive validation block stays text-identical."""
    import inspect
    old = inspect.getsource(query.reuse.load_accepted_checkpoint)
    new = inspect.getsource(query.load_frozen_query_checkpoint)
    start = '    entry, job, expected_bytes, snapshots = check_reuse_identity('
    end = '    checkpoint_sha = _sha(data["weights.pt"])'
    old_block = old[old.index(start):old.index(end)]
    new_block = new[new.index(start):new.index('    query_manifest = _json(')]
    assert old_block == new_block
    old_tensor = old[old.index('    payload = torch.load('):old.index('    return ReadOnlyCheckpoint(')]
    new_tensor = new[new.index('    payload = torch.load('):new.index('    snapshots.update(auth_snapshots)')]
    assert old_tensor == new_tensor
