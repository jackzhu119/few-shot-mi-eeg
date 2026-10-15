"""All query identities/predictions below are synthetic; no weights, EEG or fit."""
import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from learning_preserving_bci.evaluation.statistics import bootstrap_subject_mean

SPEC = importlib.util.spec_from_file_location(
    "frozen_query_aggregation", Path(__file__).parents[1] / "scripts/aggregate_kumar_frozen_queries.py")
aggregation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aggregation)


def metric_rows(predictions, subject, seed):
    rows = []
    for session in aggregation.SESSIONS:
        selected = [r for r in predictions if r['session'] == session]
        # Independent confusion construction for the synthetic output fixture.
        matrix = [[sum(r['y_true'] == y and r['y_pred'] == pred for r in selected)
                   for pred in (0, 1)] for y in (0, 1)]
        totals = [sum(row) for row in matrix]
        recalls = [matrix[k][k] / totals[k] if totals[k] else None for k in (0, 1)]
        counts = [sum(row[k] for row in matrix) for k in (0, 1)]
        rows.append(dict(subject=subject, seed=seed, session=session,
            role='source_query' if session == 'ses-0' else 'target_query', n=len(selected),
            confusion_matrix=matrix, class_recalls=recalls,
            balanced_accuracy=None if None in recalls else sum(recalls) / 2,
            balanced_accuracy_status='not_estimable_missing_class' if None in recalls else 'estimated',
            predicted_class_counts=counts, class_collapse=0 in counts))
    return rows


@pytest.fixture
def synthetic_results():
    jobs, results, ids = [], [], []
    for subject in aggregation.DEVELOPMENT + aggregation.REMAINING:
        for seed_index, seed in enumerate(aggregation.SEEDS):
            job = dict(job_id=f'synthetic-untrained-{subject}-{seed}', subject=subject, seed=seed,
                       result_key=f'synthetic/{subject}-{seed}')
            predictions = []
            for session in aggregation.SESSIONS:
                # Unequal session n detects an erroneous pooled-trial endpoint.
                n = 12 if session == 'ses-1' else 4
                for index in range(n):
                    y = index % 2
                    if session == 'ses-0':
                        pred = y
                    elif subject == 'sub-1':
                        pred = y if session == 'ses-1' else 1-y
                    else:
                        pred = y if seed_index == 0 else (0 if seed_index == 1 else 1-y)
                    trial_id = f'{subject}/{session}/' + ('run-3' if session == 'ses-0' else 'run-1') + f'/synthetic-row-{index}'
                    predictions.append(dict(trial_id=trial_id, subject=subject, seed=seed,
                        session=session, run='run-3' if session == 'ses-0' else 'run-1',
                        role='source_query' if session == 'ses-0' else 'target_query',
                        y_true=y, y_pred=pred, logit_0=float(pred == 0), logit_1=float(pred == 1)))
                    if seed_index == 0:
                        ids.append(trial_id)
            results.append(dict(identity=dict(job, synthetic=True, software_validation_only=True),
                scope=aggregation.SCOPE, optimizer_instances_created=0, optimizer_steps=0,
                new_fit=False, parameter_BN_normalization_updates=False,
                input_files_unchanged=True, processed_input_hashes_verified=True,
                source_training_context_preserved=True, state_before_sha256='a'*64,
                state_after_sha256='a'*64, query_labels_used_for='fixed_metrics_only',
                predictions=predictions, query_rows_evaluated=len(predictions), real_query_rows_loaded=0,
                session_metrics=metric_rows(predictions, subject, seed)))
            jobs.append(job)
    return results, jobs, ids


def run(fixture):
    results, jobs, ids = fixture
    return aggregation.aggregate_query_results(results, jobs, expected_query_ids=ids, synthetic=True)


def test_equal_seeds_then_sessions_then_participants_and_frozen_bootstrap(synthetic_results):
    before = copy.deepcopy(synthetic_results)
    result = run(synthetic_results)
    assert synthetic_results == before
    assert result['synthetic'] is result['software_validation_only'] is True
    assert result['job_count'] == 54 and len(result['per_job_session_metrics']) == 324
    assert result['class_collapse_job_sessions'] == 85
    first = next(r for r in result['per_participant'] if r['subject'] == 'sub-1')
    assert first['target_session_balanced_accuracies'] == [1, 0, 0, 0, 0]
    assert first['target_five_session_balanced_accuracy'] == pytest.approx(0.2)
    assert first['source_query_balanced_accuracy'] == 1
    second = next(r for r in result['per_participant_session']
                  if r['subject'] == 'sub-2' and r['session'] == 'ses-1')
    assert second['seed_balanced_accuracies'] == [1, 0.5, 0]
    assert second['mean_three_seed_balanced_accuracy'] == 0.5
    cohort = result['cohorts']['development6']
    expected = {subject: 0.2 if subject == 'sub-1' else 0.5 for subject in aggregation.DEVELOPMENT}
    assert cohort['target_query']['bootstrap'] == bootstrap_subject_mean(expected, n_resamples=10000, seed=42)
    assert cohort['target_query']['mean'] == pytest.approx(0.45)
    assert result['cohorts']['remaining12']['target_query']['mean'] == 0.5
    assert result['cohorts']['all18_secondary_exploratory']['target_query']['mean'] == pytest.approx((0.2+17*.5)/18)
    assert cohort['source_query_secondary']['mean'] == 1
    assert result['model_forwards'] == result['model_fits'] == result['checkpoint_tensor_loads'] == 0


@pytest.mark.parametrize('change,match', [
    ('missing_job', 'all54'), ('duplicate_job', 'identity/order'),
    ('missing_session', 'All six'), ('duplicate_session', 'All six'),
    ('missing_trial', 'trial scope'), ('duplicate_trial', 'trial scope'),
    ('extra_manifest_trial', 'trial scope'), ('changed_seed_label', 'labels changed'),
    ('target_support', 'Forbidden'), ('wrong_metric', 'metric arithmetic'),
    ('wrong_argmax', 'fixed argmax'), ('state_change', 'unchanged'),
    ('synthetic_relabel', 'Synthetic/real'),
])
def test_incomplete_or_changed_results_rejected_without_dropping(synthetic_results, change, match):
    results, jobs, ids = synthetic_results
    if change == 'missing_job':
        results.pop()
    elif change == 'duplicate_job':
        results[-1] = copy.deepcopy(results[-2])
    elif change == 'missing_session':
        results[0]['session_metrics'].pop()
    elif change == 'duplicate_session':
        results[0]['session_metrics'][-1] = copy.deepcopy(results[0]['session_metrics'][-2])
    elif change == 'missing_trial':
        results[0]['predictions'].pop()
    elif change == 'duplicate_trial':
        results[0]['predictions'][-1] = copy.deepcopy(results[0]['predictions'][-2])
    elif change == 'extra_manifest_trial':
        ids.append('sub-1/ses-1/run-1/synthetic-extra')
    elif change == 'changed_seed_label':
        results[1]['predictions'][0]['y_true'] = 1
    elif change == 'target_support':
        results[0]['predictions'][0]['role'] = 'target_support'
    elif change == 'wrong_metric':
        results[0]['session_metrics'][0]['balanced_accuracy'] = 0.3
    elif change == 'wrong_argmax':
        results[0]['predictions'][0]['y_pred'] = 1
    elif change == 'state_change':
        results[0]['state_after_sha256'] = 'b'*64
    elif change == 'synthetic_relabel':
        results[0]['identity']['synthetic'] = False
    with pytest.raises(ValueError, match=match):
        run(synthetic_results)


def test_missing_class_keeps_all_participants_without_partial_cohort_bootstrap(synthetic_results):
    results, _, _ = synthetic_results
    for result in results[:3]:
        for row in result['predictions']:
            if row['session'] == 'ses-2':
                row['y_true'] = 0
        result['session_metrics'] = metric_rows(result['predictions'], 'sub-1', result['identity']['seed'])
    summary = run(synthetic_results)
    assert summary['status'] == 'complete_with_explicit_unavailable_metrics'
    assert len(summary['unavailable_session_metrics']) == 3
    assert len(summary['per_participant']) == 18
    dev = summary['cohorts']['development6']['target_query']
    assert dev['status'] == 'unavailable_missing_participant_endpoint'
    assert dev['unavailable_participants'] == ['sub-1']
    assert dev['mean'] is dev['bootstrap'] is None
    assert dev['participants_dropped'] == 0
    assert summary['cohorts']['remaining12']['target_query']['status'] == 'complete'
    assert summary['cohorts']['development6']['source_query_secondary']['status'] == 'complete'


def test_fixed_argmax_tie_and_nonfinite_logits():
    rows = [dict(y_true=y, y_pred=0, logit_0=0.0, logit_1=0.0) for y in (0,1)]
    result = aggregation.fixed_metrics(rows)
    assert result['balanced_accuracy'] == 0.5 and result['class_collapse'] is True
    rows[0]['logit_1'] = np.nan
    with pytest.raises(ValueError, match='finite fixed argmax'):
        aggregation.fixed_metrics(rows)
