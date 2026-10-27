#!/usr/bin/env python3
"""Independently audit saved V3 predictions; never load EEG or model weights.

This is post-processing of already saved predictions, not another query forward.
Every frozen prediction shard is required. Participant identity, ordered query
trials, labels, class counts and chronological support prefixes remain explicit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from collections import Counter

import numpy as np


class AuditError(ValueError):
    """A saved identity, prediction, or metric differs from its declared record."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric_match(observed, expected, name, tolerance=1e-12):
    if expected is None:
        require(observed is None, name + ': expected an undefined value')
    else:
        require(isinstance(observed, (int, float)) and not isinstance(observed, bool)
                and np.isfinite(observed) and abs(observed - expected) <= tolerance,
                name + ': saved value differs from predictions')


def audit_shard(predictions_path, metric):
    """Recompute binary argmax metrics using classes[argmax], including ties."""
    with np.load(predictions_path, allow_pickle=False) as saved:
        require(set(saved.files) == {'probabilities', 'labels', 'classes', 'trial_id', 'run_id'},
                'Unexpected prediction payload keys')
        values = {k: saved[k] for k in saved.files}
    p, y, classes, ids, runs = (values[k] for k in
                              ('probabilities', 'labels', 'classes', 'trial_id', 'run_id'))
    require(y.ndim == ids.ndim == runs.ndim == 1, 'Invalid prediction vector dimensions')
    n = len(y)
    require(p.shape == (n, 2) and len(ids) == len(runs) == n, 'Prediction lengths differ')
    require(classes.shape == (2,) and classes.dtype.kind in 'iu'
            and classes.tolist() == [0, 1], 'Frozen classes differ from [0,1]')
    require(y.dtype.kind in 'iu' and set(y.tolist()) <= {0, 1}, 'Invalid binary labels')
    require(p.dtype.kind == 'f' and np.all(np.isfinite(p)), 'Nonfinite probabilities')
    require(np.all(p >= -1e-7) and np.all(p <= 1 + 1e-7)
            and np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-6),
            'Invalid probability bounds/normalization')
    require(ids.dtype.kind in 'US' and runs.dtype.kind in 'US', 'Nontext trial/run identities')
    id_list, run_list = ids.astype(str).tolist(), runs.astype(str).tolist()
    require(len(set(id_list)) == n, 'Duplicate query trial IDs')
    require(all(t and r and t.startswith(r + '/row-') for t, r in zip(id_list, run_list)),
            'Trial/run identities disagree')
    participant, session = metric['participant'], metric['session']
    true_session = 'ses-0' if session == 'source' else session
    require(all(t.startswith(participant + '/' + true_session + '/') for t in id_list),
            'Query participant/session identity differs')
    predicted = classes[p.argmax(axis=1)] if n else np.empty(0, dtype=int)
    confusion = np.zeros((2, 2), dtype=int)
    for truth, guess in zip(y, predicted):
        confusion[int(truth), int(guess)] += 1
    counts = confusion.sum(axis=1).tolist()
    recalls = [None if count == 0 else float(confusion[c, c] / count)
               for c, count in enumerate(counts)]
    ba = float(np.mean(recalls)) if all(x is not None for x in recalls) else None
    accuracy = float(np.mean(y == predicted)) if n else None
    require(metric.get('n_query') == n, 'n_query differs')
    require(metric.get('class_counts') == counts, 'Query class counts differ')
    numeric_match(metric.get('balanced_accuracy'), ba, 'balanced_accuracy')
    if 'accuracy' in metric:
        numeric_match(metric['accuracy'], accuracy, 'accuracy')
    if 'recalls' in metric:
        require(isinstance(metric['recalls'], list) and len(metric['recalls']) == 2,
                'Invalid recall record')
        for observed, expected in zip(metric['recalls'], recalls):
            numeric_match(observed, expected, 'recall')
    if 'confusion_matrix' in metric:
        require(metric['confusion_matrix'] == confusion.tolist(), 'Confusion matrix differs')
    predicted_counts = [int(np.sum(predicted == c)) for c in classes]
    if 'prediction_class_counts' in metric:
        require(metric['prediction_class_counts'] == predicted_counts, 'Predicted class counts differ')
    collapse = bool(len(np.unique(predicted)) == 1) if n else False
    if 'collapse' in metric:
        require(metric['collapse'] is collapse, 'Class-collapse flag differs')
    require(metric.get('selection_use') is False, 'Query record permits selection use')
    require(metric.get('query_used_for_fitting', False) is False, 'Query used for fitting')
    require(metric.get('synthetic') is False and metric.get('software_validation_only') is False,
            'Real EEG prediction mislabeled as synthetic or vice versa')
    require(isinstance(metric.get('query_identity'), str) and metric['query_identity'],
            'Missing recorded query identity')
    if 'inference_state_unchanged' in metric:
        require(metric['inference_state_unchanged'] is True, 'Inference modified model state')
    signature = hashlib.sha256(json.dumps({'ids': id_list, 'labels': y.tolist(), 'runs': run_list},
                                         sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'n_query': n, 'balanced_accuracy': ba, 'accuracy': accuracy,
            'class_counts': counts, 'prediction_class_counts': predicted_counts,
            'confusion_matrix': confusion.tolist(), 'collapse': collapse,
            'query_signature': signature, 'ids': id_list}


def expected_shards(tasks, science):
    """Generate every required shard from the released frozen task/config files."""
    expected = {}
    for task in tasks:
        name, family = task['task_id'], task['family']
        if family not in ('geometry', 'neural'):
            continue
        methods = task.get('science_overrides', {}).get('neural_methods', science['neural_methods']) \
            if family == 'neural' else science['geometry_methods']
        for target in task['targets']:
            for budget in science['budgets']:
                for method in methods:
                    relative = (f'evaluation/{target["session"]}__n{budget}__{method}/metrics.json'
                                if family == 'geometry' else
                                f'evaluation/{target["session"]}/{method}/budget-{budget}/metrics.json')
                    key = f'tasks/{name}/{relative}'
                    require(key not in expected, 'Duplicate frozen shard identity')
                    expected[key] = (task, target['session'], method, int(budget), target)
        if task.get('source_query'):
            method = 'source_tangent_frozen' if family == 'geometry' else 'frozen'
            relative = ('evaluation/source__n0__source_tangent_frozen/metrics.json'
                        if family == 'geometry' else 'source_query/metrics.json')
            expected[f'tasks/{name}/{relative}'] = (task, 'source', method, 0, None)
    return expected


def audit(results_root, output=None):
    results_root = Path(results_root).resolve()
    packet = results_root.parent
    task_file, config_file = (packet / 'source_code/configs' / n
                              for n in ('tasks.json', 'discovery.json'))
    tasks = json.loads(task_file.read_text())
    tasks = tasks['tasks'] if isinstance(tasks, dict) else tasks
    config = json.loads(config_file.read_text())
    names = [t['task_id'] for t in tasks]
    require(len(names) == len(set(names)), 'Duplicate frozen task IDs')
    manifest_file = packet / 'MANIFEST.json'
    manifest = json.loads(manifest_file.read_text())
    require(set(manifest['tasks']) == set(names), 'Packet and frozen task IDs differ')
    marker_digests = {}
    for task in tasks:
        path = results_root / 'tasks' / task['task_id'] / 'complete.json'
        marker = json.loads(path.read_text())
        require(marker.get('task_id') == task['task_id'] and marker.get('status') == 'completed'
                and bool(marker.get('identity') or marker.get('task_identity')),
                'Invalid complete marker: ' + task['task_id'])
        require(marker.get('family') == task['family'], 'Completion marker family differs')
        marker_digests[task['task_id']] = digest(path)
    expected = expected_shards(tasks, config['science'])
    observed = {p.relative_to(results_root).as_posix() for p in results_root.glob('tasks/**/predictions.npz')}
    wanted = {str(Path(p).with_name('predictions.npz')) for p in expected}
    require(observed == wanted,
            f'Prediction inventory differs: missing={len(wanted-observed)}, extra={len(observed-wanted)}')
    query_groups, support_groups, diagnostics_cache = {}, {}, {}
    inventory, family_counts, max_ba_difference = [], Counter(), 0.0
    collapse_counts, all_query_rows = Counter(), 0
    for relative, (task, session, method, budget, target) in sorted(expected.items()):
        metric_path = results_root / relative
        metric = json.loads(metric_path.read_text())
        for key, value in [('task_id', task['task_id']), ('dataset', task['dataset']),
                           ('participant', task['participant']), ('session', session), ('method', method),
                           ('requested_budget', budget)]:
            require(metric.get(key) == value, f'{relative}: {key} differs')
        if 'seed' in task:
            require(metric.get('seed') == task['seed'], 'Prediction seed differs')
        if task['family'] == 'neural':
            require(metric.get('source_regime') == task['source_regime'], 'Source regime differs')
            require(metric.get('inference_state_unchanged') is True, 'Missing neural state-invariance evidence')
        prediction_path = metric_path.with_name('predictions.npz')
        scored = audit_shard(prediction_path, metric)
        key = (task['participant'], session)
        if key in query_groups:
            require(query_groups[key]['signature'] == scored['query_signature'],
                    'Ordered query IDs/labels/runs differ across methods, budgets, or seeds: ' + str(key))
            query_groups[key]['shards'] += 1
        else:
            query_groups[key] = {'signature': scored['query_signature'], 'shards': 1,
                                 'class_counts': scored['class_counts'], 'n_query': scored['n_query']}
        actual = metric.get('actual_budget')
        require(type(actual) is int and 0 <= actual <= budget, 'Invalid actual support budget')
        if method in ('source_tangent_frozen', 'frozen') or session == 'source':
            require(actual == 0, 'Frozen/source evaluation used support labels')
        else:
            require(actual > 0, 'Updating method has no support labels')
            budget_key = (task['participant'], session, budget)
            prior = support_groups.setdefault(budget_key, {'actual_budget': actual, 'ids': None})
            require(prior['actual_budget'] == actual, 'Compared support counts differ')
        if task['family'] == 'geometry':
            stem = 'source_model' if method == 'source_tangent_frozen' else f'{session}__n{budget}__{method}'
            path = results_root / 'tasks' / task['task_id'] / 'model_diagnostics' / (stem + '.json')
            if path not in diagnostics_cache:
                diagnostics_cache[path] = json.loads(path.read_text())
            diagnostic = diagnostics_cache[path]
            require(diagnostic['fit_identity'] == metric['fit_identity'], 'Geometry fit identity differs')
            require(diagnostic.get('query_used_for_fitting') is False, 'Geometry fit included query')
            fit_ids = diagnostic['fit_trial_ids']
            require(len(fit_ids) == len(set(fit_ids)), 'Duplicated fitting trial identities')
            require(not set(fit_ids) & set(scored['ids']), 'Fitting/query overlap')
            support_ids = diagnostic['support_trial_ids']
            require(len(support_ids) == actual, 'Saved support IDs differ from actual budget')
            if actual:
                row = support_groups[(task['participant'], session, budget)]
                require(row['ids'] in (None, support_ids), 'Geometry methods used different support IDs')
                row['ids'] = support_ids
        family_counts[(task['family'], 'source' if session == 'source' else 'target')] += 1
        collapse_counts[(task['family'], method, task.get('source_regime', 'within_subject'),
                         task.get('variant', 'core'), budget, session == 'source')] += scored['collapse']
        all_query_rows += scored['n_query']
        if scored['balanced_accuracy'] is not None:
            max_ba_difference = max(max_ba_difference,
                                    abs(scored['balanced_accuracy'] - metric['balanced_accuracy']))
        inventory.append({'metrics_path': relative, 'metrics_sha256': digest(metric_path),
                          'predictions_sha256': digest(prediction_path), 'task_id': task['task_id'],
                          'participant': task['participant'], 'session': session, 'method': method,
                          'budget': budget, 'actual_budget': actual, 'n_query': scored['n_query'],
                          'class_counts': ';'.join(map(str, scored['class_counts'])),
                          'balanced_accuracy': scored['balanced_accuracy'], 'collapse': scored['collapse'],
                          'query_signature': scored['query_signature']})
    for person, session in {(k[0], k[1]) for k in support_groups}:
        rows = [(k[2], v) for k, v in support_groups.items() if k[:2] == (person, session)]
        rows.sort()
        previous = []
        for _, row in rows:
            require(row['ids'] is not None, 'No saved geometric support ID reference')
            require(row['ids'][:len(previous)] == previous, 'Support budgets are not chronological prefixes')
            previous = row['ids']
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(inventory[0]))
    writer.writeheader()
    writer.writerows(inventory)
    csv_data = stream.getvalue().encode()
    report = {'schema_version': 1, 'scope': 'Saved predictions/metrics/diagnostics only; no EEG or model load, fit, or forward',
              'independent_statistical_unit': 'participant', 'source_frozen_repeat_warning':
              'Repeated frozen budgets and reused teachers are not independent observations',
              'task_count': len(tasks), 'complete_markers_verified': len(marker_digests),
              'prediction_shards_verified': len(inventory), 'source_shards':
              sum(v for (_, role), v in family_counts.items() if role == 'source'),
              'target_shards': sum(v for (_, role), v in family_counts.items() if role == 'target'),
              'family_counts': {str(k): v for k, v in family_counts.items()},
              'query_rows_including_repeated_methods_budgets_and_seeds': all_query_rows,
              'unique_query_groups': len(query_groups), 'unique_query_trials':
              sum(v['n_query'] for v in query_groups.values()),
              'max_balanced_accuracy_replay_difference': max_ba_difference,
              'cross_method_seed_budget_ordered_query_join_verified': True,
              'support_prefix_groups_verified': len(support_groups),
              'input_inventory_csv_sha256': hashlib.sha256(csv_data).hexdigest(),
              'input_inventory_rows': len(inventory),
              'packet_manifest_sha256': digest(manifest_file), 'frozen_tasks_sha256': digest(task_file),
              'frozen_config_sha256': digest(config_file), 'prediction_npz_allow_pickle': False,
              'failures': [], 'accepted': False, 'raw_weights_audited': False,
              'query_groups': [{'participant': k[0], 'session': k[1], **v} for k, v in sorted(query_groups.items())],
              'collapse_counts': [{'family': k[0], 'method': k[1], 'source_regime': k[2], 'variant': k[3],
                                   'budget': k[4], 'source_query': k[5], 'count': v}
                                  for k, v in sorted(collapse_counts.items())]}
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.with_suffix('.inputs.csv').write_bytes(csv_data)
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.results_root, args.output)
    print(json.dumps({k: v for k, v in report.items() if k not in ('query_groups', 'collapse_counts')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
