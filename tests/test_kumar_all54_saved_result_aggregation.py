"""Focused all54 identity and descriptive participant aggregation protections."""
import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('all54_saved', ROOT / 'scripts/aggregate_kumar_all54_saved_results.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_identity():
    def jobs(subjects):
        return [{'subject': subject, 'seed': seed, 'job_id': f'{subject}-{seed}',
                 'result_key': f'private/{subject}-{seed}'} for subject in subjects for seed in MODULE.SEEDS]
    old = jobs(MODULE.DEVELOPMENT)
    remaining = jobs(MODULE.REMAINING)
    accepted = [{**j, 'archive_sha256': 'a' * 64} for j in old + remaining]
    plan = {'jobs': old + remaining, 'development_subjects': MODULE.DEVELOPMENT,
            'remaining_subjects': MODULE.REMAINING, 'seeds': MODULE.SEEDS}
    return plan, {'accepted_jobs': accepted}, {'jobs': old}, {'accepted_jobs': copy.deepcopy(accepted[:18])}, remaining


def test_exact54_acceptance_and_frozen18_prefix_required():
    args = fixture_identity()
    assert len(MODULE.validate_complete_identity(*args)) == 54
    changed = copy.deepcopy(args)
    changed[1]['accepted_jobs'][0]['archive_sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='Original accepted18'):
        MODULE.validate_complete_identity(*changed)
    changed = copy.deepcopy(args)
    changed[1]['accepted_jobs'][18:20] = changed[1]['accepted_jobs'][18:20][::-1]
    with pytest.raises(ValueError, match='acceptance order'):
        MODULE.validate_complete_identity(*changed)
    changed = copy.deepcopy(args)
    changed[0]['jobs'][18] = changed[0]['jobs'][0]
    with pytest.raises(ValueError, match='plan order'):
        MODULE.validate_complete_identity(*changed)


def test_equal_participant_descriptives_retain_all_seeds_and_no_ci():
    rows = []
    for subject, scores in [('a', [0.2, 0.4, 0.6]), ('b', [0.7, 0.8, 0.9])]:
        for seed, score in zip(MODULE.SEEDS, scores):
            rows.append({'subject': subject, 'seed': seed, 'source_validation_CE_recorded': 0.7,
                         'source_validation_balanced_accuracy': score, 'source_validation_accuracy': score,
                         'single_class_prediction': False, 'epochs': 16, 'selected_epoch': 1, 'optimizer_steps': 48})
    participants, summary = MODULE.summarize_cohort(rows, ['a', 'b'])
    assert summary['participants'] == 2 and summary['fits'] == 6
    assert summary['mean_participant_source_validation_balanced_accuracy'] == pytest.approx(0.6)
    assert participants[0]['seed_balanced_accuracy_range'] == pytest.approx(0.4)
    assert summary['inference'] == 'descriptive only; no hypothesis test or CI on epoch-selected validation'
    assert not any('bootstrap' in key or 'interval' in key for key in summary)
    with pytest.raises(ValueError, match='Incomplete'):
        MODULE.summarize_cohort(rows[:-1], ['a', 'b'])

