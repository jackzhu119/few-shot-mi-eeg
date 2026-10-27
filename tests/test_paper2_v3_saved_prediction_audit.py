"""Synthetic checks for the independent saved-prediction post-processor."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    'v3_saved_audit', Path(__file__).parents[1] / 'scripts/audit_paper2_v3_saved_predictions_20261027.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def sample_metric(task, session='ses-1', method='tangent_refit', budget=4, actual=4):
    return {'task_id': task['task_id'], 'dataset': 'Kumar2024', 'participant': 'sub-1',
            'family': task['family'], 'session': session, 'method': method,
            'requested_budget': budget, 'actual_budget': actual, 'n_query': 4,
            'class_counts': [2, 2], 'balanced_accuracy': .75, 'accuracy': .75,
            'recalls': [1., .5], 'prediction_class_counts': [3, 1], 'collapse': False,
            'fit_identity': 'fit-' + method + '-' + str(budget), 'query_identity': 'declared-query-id',
            'selection_use': False, 'query_used_for_fitting': False,
            'synthetic': False, 'software_validation_only': False}


def write_prediction(path, *, session='ses-1', ids=None, labels=None, probability=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    actual = 'ses-0' if session == 'source' else session
    runs = np.array([f'sub-1/{actual}/run-1'] * 4)
    if ids is None:
        ids = np.array([str(r) + f'/row-{i+1}' for i, r in enumerate(runs)])
    np.savez_compressed(path,
                        probabilities=np.array([[.8, .2], [.7, .3], [.6, .4], [.1, .9]])
                        if probability is None else probability,
                        labels=np.array([0, 0, 1, 1]) if labels is None else labels,
                        classes=np.array([0, 1]), trial_id=np.asarray(ids), run_id=runs)


@pytest.fixture
def packet(tmp_path):
    root = tmp_path / 'paper2_results/results'
    common = {'dataset': 'Kumar2024', 'participant': 'sub-1',
              'targets': [{'session': 'ses-1', 'support': 'support.npz', 'query': 'query.npz'}]}
    tasks = [{'task_id': 'geo', 'family': 'geometry', **common},
             {'task_id': 'neural', 'family': 'neural', 'source_regime': 'reuse_v2', 'seed': 1,
              **common}]
    science = {'budgets': [2, 4], 'geometry_methods': ['source_tangent_frozen', 'tangent_refit'],
               'neural_methods': ['frozen', 'full_fixed']}
    write_json(root.parent / 'source_code/configs/tasks.json', tasks)
    write_json(root.parent / 'source_code/configs/discovery.json', {'science': science})
    write_json(root.parent / 'MANIFEST.json', {'tasks': ['geo', 'neural']})
    for task in tasks:
        write_json(root / 'tasks' / task['task_id'] / 'complete.json',
                   {'task_id': task['task_id'], 'family': task['family'],
                    'identity': 'fixed-task-identity', 'status': 'completed'})
    for path, (task, session, method, budget, _) in AUDIT.expected_shards(tasks, science).items():
        actual = 0 if method in ('source_tangent_frozen', 'frozen') else budget
        metric = sample_metric(task, method=method, budget=budget, actual=actual)
        if task['family'] == 'neural':
            metric.update(seed=1, source_regime='reuse_v2', inference_state_unchanged=True)
        write_json(root / path, metric)
        write_prediction((root / path).with_name('predictions.npz'))
        if task['family'] == 'geometry':
            stem = 'source_model' if method == 'source_tangent_frozen' else f'{session}__n{budget}__{method}'
            if method == 'source_tangent_frozen':
                metric['fit_identity'] = 'source-fit'
                write_json(root / path, metric)
            support = [f'sub-1/ses-1/run-0/row-{i+1}' for i in range(actual)]
            write_json(root / 'tasks/geo/model_diagnostics' / (stem + '.json'),
                       {'fit_identity': metric['fit_identity'], 'query_used_for_fitting': False,
                        'support_trial_ids': support,
                        'fit_trial_ids': ['sub-1/ses-0/run-0/row-1'] + support})
    return root


def test_complete_packet_replay_and_input_inventory(packet, tmp_path):
    output = tmp_path / 'audit.json'
    report = AUDIT.audit(packet, output)
    assert report['prediction_shards_verified'] == 8
    assert report['unique_query_groups'] == 1
    assert report['unique_query_trials'] == 4
    assert report['query_rows_including_repeated_methods_budgets_and_seeds'] == 32
    assert report['support_prefix_groups_verified'] == 2
    assert report['max_balanced_accuracy_replay_difference'] == 0
    assert report['failures'] == []
    assert output.with_suffix('.inputs.csv').is_file()
    assert report['accepted'] is False


def test_metric_discrepancy_stops(packet):
    path = next(packet.glob('tasks/**/metrics.json'))
    metric = json.loads(path.read_text())
    metric['accuracy'] = .5
    write_json(path, metric)
    with pytest.raises(AUDIT.AuditError, match='accuracy'):
        AUDIT.audit(packet)


def test_missing_prediction_is_not_silently_dropped(packet):
    next(packet.glob('tasks/**/predictions.npz')).unlink()
    with pytest.raises(AUDIT.AuditError, match='inventory differs'):
        AUDIT.audit(packet)


def test_ordered_ids_must_match_across_methods_and_families(packet):
    path = next((packet / 'tasks/neural').glob('**/predictions.npz'))
    ids = [f'sub-1/ses-1/run-1/row-{i}' for i in (2, 1, 3, 4)]
    write_prediction(path, ids=ids)
    with pytest.raises(AUDIT.AuditError, match='Ordered query'):
        AUDIT.audit(packet)


def test_fitting_overlap_stops(packet):
    path = packet / 'tasks/geo/model_diagnostics/ses-1__n2__tangent_refit.json'
    value = json.loads(path.read_text())
    value['fit_trial_ids'].append('sub-1/ses-1/run-1/row-1')
    write_json(path, value)
    with pytest.raises(AUDIT.AuditError, match='overlap'):
        AUDIT.audit(packet)


def test_nonprefix_support_budget_stops(packet):
    path = packet / 'tasks/geo/model_diagnostics/ses-1__n4__tangent_refit.json'
    value = json.loads(path.read_text())
    value['support_trial_ids'] = value['support_trial_ids'][::-1]
    write_json(path, value)
    with pytest.raises(AUDIT.AuditError, match='chronological prefixes'):
        AUDIT.audit(packet)


def test_duplicate_query_ids_stops(tmp_path):
    path = tmp_path / 'predictions.npz'
    write_prediction(path, ids=['sub-1/ses-1/run-1/row-1'] * 4)
    with pytest.raises(AUDIT.AuditError, match='Duplicate'):
        AUDIT.audit_shard(path, sample_metric({'task_id': 't', 'family': 'geometry'}))


def test_nonfinite_probabilities_stops(tmp_path):
    path = tmp_path / 'predictions.npz'
    write_prediction(path, probability=np.full((4, 2), np.nan))
    with pytest.raises(AUDIT.AuditError, match='Nonfinite'):
        AUDIT.audit_shard(path, sample_metric({'task_id': 't', 'family': 'geometry'}))


def test_missing_query_class_remains_undefined(tmp_path):
    path = tmp_path / 'predictions.npz'
    write_prediction(path, labels=np.zeros(4, dtype=int), probability=np.array([[.8, .2]] * 4))
    metric = sample_metric({'task_id': 't', 'family': 'geometry'})
    metric.update(class_counts=[4, 0], recalls=[1., None], balanced_accuracy=None,
                  accuracy=1., prediction_class_counts=[4, 0], collapse=True)
    result = AUDIT.audit_shard(path, metric)
    assert result['balanced_accuracy'] is None
    assert result['class_counts'] == [4, 0]


def test_ties_follow_classes_argmax_first_class(tmp_path):
    path = tmp_path / 'predictions.npz'
    write_prediction(path, probability=np.array([[.5, .5]] * 4))
    metric = sample_metric({'task_id': 't', 'family': 'geometry'})
    metric.update(recalls=[1., 0.], balanced_accuracy=.5, accuracy=.5,
                  prediction_class_counts=[4, 0], collapse=True)
    assert AUDIT.audit_shard(path, metric)['confusion_matrix'] == [[2, 0], [2, 0]]


def test_state_mutation_evidence_stops(packet):
    path = next((packet / 'tasks/neural').glob('**/metrics.json'))
    metric = json.loads(path.read_text())
    metric['inference_state_unchanged'] = False
    write_json(path, metric)
    with pytest.raises(AUDIT.AuditError, match='state-invariance'):
        AUDIT.audit(packet)


def test_wrong_completion_marker_stops(packet):
    path = packet / 'tasks/neural/complete.json'
    metric = json.loads(path.read_text())
    metric['task_id'] = 'other'
    write_json(path, metric)
    with pytest.raises(AUDIT.AuditError, match='complete marker'):
        AUDIT.audit(packet)
