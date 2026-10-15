#!/usr/bin/env python3
"""Independent read-only arithmetic audit of saved run02 artifacts; never fits."""
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path('/workspace/few-shot-mi-eeg')
RESULT = ROOT / 'results/kumar_csp_signed_score_20261015/run02'
DEST = Path(__file__).with_name('independent_numerical_audit_run01.json')
SUBJECTS = [1, 4, 7, 10, 13, 16]
CHECKS = 0
MAX_ERROR = 0.0
INPUTS = {}


def digest(path):
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    INPUTS[str(path.relative_to(ROOT))] = value
    return value


def read_json(path):
    digest(path)
    return json.loads(path.read_text())


def load_npz(path):
    digest(path)
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def equal(got, expected, label):
    global CHECKS, MAX_ERROR
    CHECKS += 1
    if isinstance(expected, dict):
        if set(got) != set(expected):
            raise ValueError(f'{label}: keys differ')
        for key in expected:
            equal(got[key], expected[key], f'{label}.{key}')
    elif isinstance(expected, (list, tuple)):
        if len(got) != len(expected):
            raise ValueError(f'{label}: lengths differ')
        for index, (left, right) in enumerate(zip(got, expected, strict=True)):
            equal(left, right, f'{label}[{index}]')
    elif isinstance(expected, (float, np.floating)):
        error = abs(float(got) - expected)
        if not np.isfinite(error) or error > 1e-12:
            raise ValueError(f'{label}: numerical difference {error}')
        MAX_ERROR = max(MAX_ERROR, float(error))
    elif got != expected:
        raise ValueError(f'{label}: {got!r} != {expected!r}')


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def array_hash(array):
    value = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(value.dtype).encode())
    h.update(json.dumps(list(value.shape)).encode())
    h.update(value.tobytes())
    return h.hexdigest()


def state_hash(arrays):
    h = hashlib.sha256()
    for key in sorted(arrays):
        a = np.ascontiguousarray(arrays[key])
        if a.dtype.hasobject:
            raise ValueError('object state')
        h.update(json.dumps([key, a.dtype.str, list(a.shape)], separators=(',', ':')).encode())
        h.update(b'\0')
        h.update(a.tobytes())
    return h.hexdigest()


def classification(prediction, y):
    recalls = [float(np.mean(prediction[y == k] == k)) if np.any(y == k) else None for k in (0, 1)]
    return {'balanced_accuracy': None if None in recalls else float(np.mean(recalls)),
            'class_recall': recalls,
            'prediction_ratio': [float(np.mean(prediction == k)) for k in (0, 1)],
            'class_collapse': len(np.unique(prediction)) < 2}


def score_summary(scores, y):
    return {**classification((scores > 0).astype(int), y),
            'score_mean': float(scores.mean()), 'score_sd_ddof1': float(scores.std(ddof=1)),
            'score_class_means': [float(scores[y == k].mean()) if np.any(y == k) else None for k in (0, 1)]}


def direction(x, y):
    if any(not np.any(y == k) for k in (0, 1)):
        return None
    return x[y == 1].mean(axis=0) - x[y == 0].mean(axis=0)


def cosine(x, y):
    if x is None or y is None:
        return None
    norm = np.linalg.norm(x) * np.linalg.norm(y)
    return float(np.clip(x @ y / norm, -1, 1)) if norm > 0 and np.isfinite(norm) else None


def halves(y):
    groups = [np.flatnonzero(y == k) for k in (0, 1)]
    if min(map(len, groups)) < 4:
        raise ValueError('invalid original class budget')
    return [np.sort(np.concatenate([g[:len(g) // 2] for g in groups])),
            np.sort(np.concatenate([g[len(g) // 2:] for g in groups]))]


def support_measure(source, source_y, x, y, scores, source_sd, indices):
    axis = direction(source, source_y)
    valid = axis is not None and np.linalg.norm(axis) > 0
    unit = axis / np.linalg.norm(axis) if valid else None
    proj_sd = float(np.std(source @ unit, ddof=1)) if valid else None
    vectors = [direction(x[h], y[h]) for h in indices]
    scalar = [None if vector is None or not valid or proj_sd <= 0 else float(vector @ unit / proj_sd) for vector in vectors]
    sd_valid = bool(np.isfinite(source_sd) and source_sd > 0)
    half_rows = []
    for h in indices:
        summary = score_summary(scores[h], y[h])
        left, right = summary['score_class_means']
        contrast = None if left is None or right is None or not sd_valid else (right-left)/2/source_sd
        half_rows.append({'indices': h.tolist(), 'class_counts': [int(np.sum(y[h] == k)) for k in (0, 1)],
                          'class_balanced_true_class_signed_margin_source_sd': contrast,
                          'right_signed_score_mean_source_sd': None if right is None or not sd_valid else right/source_sd,
                          'left_signed_score_mean_source_sd': None if left is None or not sd_valid else -left/source_sd,
                          'score_bias_mean_source_sd': None if not sd_valid else float(scores[h].mean()/source_sd), **summary})
    contrasts = [row['class_balanced_true_class_signed_margin_source_sd'] for row in half_rows]
    return {'valid_halves': all(v is not None for v in vectors),
            'single_class_half_count': sum(v is None for v in vectors),
            'zero_direction_half_count': sum(v is not None and np.linalg.norm(v) == 0 for v in vectors),
            'source_direction_valid': bool(valid), 'source_projection_sd_ddof1': proj_sd,
            'source_support_direction_cosine': cosine(axis, direction(x, y)),
            'support_split_half_direction_cosine': cosine(*vectors),
            'half_scalar_signed_contrasts_source_sd': scalar,
            'half_scalar_product': None if None in scalar else float(np.prod(scalar)),
            'half_indices': [h.tolist() for h in indices],
            'source_LDA_score_sd_ddof1': source_sd, 'source_LDA_score_sd_valid': sd_valid,
            'half_score_diagnostics': half_rows, 'half_LDA_signed_contrasts_source_sd': contrasts,
            'half_LDA_signed_contrast_product': None if None in contrasts else float(np.prod(contrasts)),
            'full_support_score_diagnostics': score_summary(scores, y),
            'source_intercept_preserved': True, 'target_score_centering_or_scaling': False}


def comparison(observed, values):
    good = [v for v in values if v is not None]
    return {'observed': observed, 'total_control_count': len(values), 'valid_control_count': len(good),
            'unavailable_control_count': len(values)-len(good),
            'upper_tail_fraction_descriptive': None if observed is None or not good else float(np.mean(np.asarray(good) >= observed)),
            'interpretation': 'conditional cyclic phase-alignment sensitivity, not a formal p-value'}


def main():
    started = datetime.now(timezone.utc).isoformat()
    receipt = read_json(RESULT / 'measurement_receipt.json')
    equal(list(receipt['subjects']), [str(s) for s in SUBJECTS], 'subjects')
    summaries, source_values, support_values = [], [], []
    counts = {'model_npz_verified': 0, 'heldout_scores_replayed': 0, 'source_twofold_rotation_rows_recomputed': 0,
              'support_rotation_rows_recomputed_both_modes': 0, 'selected_saved_rows': 0,
              'support_sessions_both_LDA_contrasts_positive': 0, 'support_sessions_both_LDA_contrasts_negative': 0,
              'support_sessions_opposite_LDA_contrast_signs': 0, 'support_full_score_class_collapse_sessions': 0}
    for subject in SUBJECTS:
        folder = RESULT / f'sub-{subject}'
        row = read_json(folder / 'subject_measurement.json')
        equal(row, receipt['subjects'][str(subject)], f'sub-{subject}: receipt embedded copy')
        a = load_npz(folder / 'selected_CSP_features_and_frozen_scores.npz')
        ids, y = a['trial_ids'].tolist(), a['labels']
        equal(len(set(ids)), len(ids), 'unique selected IDs')
        equal(json_hash(ids), row['selected_trial_ids_sha256'], 'selected ID hash')
        for trial_id in ids:
            parts = trial_id.split('/')
            equal(parts[0], f'sub-{subject}', 'subject identity')
            if not ((parts[1] == 'ses-0' and parts[2] in ('run-0', 'run-1')) or
                    (parts[1] in ('ses-1','ses-2','ses-3','ses-4','ses-5') and parts[2] == 'run-0')):
                raise ValueError('forbidden selected trial identity')
        equal(set(y.tolist()), {0, 1}, 'binary saved labels')
        lookup = {trial_id: i for i, trial_id in enumerate(ids)}
        src = np.asarray([lookup[t] for t in row['source_fit_access_ids']], dtype=int)
        equal(len(src), 40, 'source fit count')
        state = dict(row['source_coordinate_fit_state'])
        bound = state.pop('state_sha256')
        equal(json_hash(state), bound, 'coordinate state hash')
        features = a['log_CSP_power4']
        equal(array_hash(features[src]), state['fit_source_CSP_features_sha256'], 'source feature hash')
        # Direct arithmetic only: no estimator/scaler objects or fit calls.
        mean, var = features[src].mean(axis=0), features[src].var(axis=0)
        equal(a['scaler_mean'].tolist(), mean.tolist(), 'source mean')
        equal(a['scaler_var'].tolist(), var.tolist(), 'source variance')
        equal(a['scaler_scale'].tolist(), np.sqrt(var).tolist(), 'source scale')
        equal(a['source_standardized_CSP4'].tolist(), ((features-mean)/np.sqrt(var)).tolist(), 'standardized feature replay')
        scores = a['frozen_source_LDA_scores']
        source_sd = float(scores[src].std(ddof=1))
        equal(state['source_LDA_score_sd_ddof1'], source_sd, 'source score sd')
        equal(state['source_LDA_score_mean'], float(scores[src].mean()), 'source score mean')
        control = row['source_phase_alignment_control']
        run_ids = [next(f['train_trial_ids'] for f in control['fit_rows'] if f['train_run_index'] == run) for run in (0, 1)]
        run_y = [y[[lookup[t] for t in group]] for group in run_ids]
        equal([a.tolist() for a in run_y], control['original_labels_by_run'], 'original run labels')
        equal(len(set(run_ids[0]) & set(run_ids[1])), 0, 'disjoint runs')
        equal(set(run_ids[0]+run_ids[1]), set(row['source_fit_access_ids']), 'run coverage')
        for run, group in enumerate(run_ids):
            equal(len(group), 20, 'run trial count')
            equal([int(np.sum(run_y[run] == k)) for k in (0,1)], [10,10], 'run class counts')
            equal(all(f'/ses-0/run-{run}/' in t for t in group), True, 'run IDs')
        cache = {}
        equal(len(control['fit_rows']), 40, 'fit rows')
        for i, fitrow in enumerate(control['fit_rows']):
            fold, shift = divmod(i, 20)
            equal((fitrow['fold'], fitrow['train_shift']), (fold, shift), 'ordered fit identity')
            equal((fitrow['train_run_index'], fitrow['holdout_run_index']), (fold, 1-fold), 'fold identity')
            equal(fitrow['train_trial_ids'], run_ids[fold], 'train IDs')
            equal(fitrow['heldout_trial_ids'], run_ids[1-fold], 'heldout IDs')
            shifted = np.roll(run_y[fold], shift)
            equal(fitrow['shifted_train_labels'], shifted.tolist(), 'train rotation labels')
            equal(fitrow['train_labels_sha256'], array_hash(shifted), 'train label digest')
            equal(fitrow['fit_status'], 'completed', 'completed fit')
            equal(fitrow['failure'], None, 'fit error')
            model_path = folder / 'source_loro_models' / f'fold-{fold}_train-shift-{shift:02d}.npz'
            model = load_npz(model_path)
            equal(str(model_path), fitrow['model_artifact'], 'artifact identity')
            equal(INPUTS[str(model_path.relative_to(ROOT))], fitrow['model_artifact_sha256'], 'model byte hash')
            equal(state_hash(model), fitrow['model_parameter_sha256'], 'model numeric state hash')
            equal(model['lda_classes'].tolist(), [0,1], 'LDA class order')
            equal(int(model['n_components']), 4, 'CSP components')
            logpower = np.asarray(fitrow['heldout_CSP_log_power4'])
            replay = (logpower @ model['lda_coef'].T + model['lda_intercept']).reshape(-1)
            equal(replay.tolist(), fitrow['heldout_scores'], 'LDA signed-score replay')
            equal((replay > 0).astype(int).tolist(), fitrow['heldout_predictions'], 'zero-threshold prediction replay')
            cache[(fold, shift)] = fitrow
            counts['model_npz_verified'] += 1
            counts['heldout_scores_replayed'] += len(replay)
        pairs = list(itertools.product(range(20), repeat=2))
        equal(control['pairs'], [list(pair) for pair in pairs], 'rotation grid')
        equal(control['shared_shift_pairs_sha256'], json_hash(pairs), 'rotation grid hash')
        recomputed_ba = []
        for n, shifts in enumerate(pairs):
            fold_summaries = []
            for fold in (0,1):
                saved = cache[(fold, shifts[fold])]
                prediction = np.asarray(saved['heldout_predictions'])
                labels = np.roll(run_y[1-fold], shifts[1-fold])
                fold_summaries.append({'fold': fold, 'train_shift': shifts[fold], 'heldout_shift': shifts[1-fold],
                                       'model_parameter_sha256': saved['model_parameter_sha256'], 'fit_status': 'completed',
                                       **classification(prediction, labels)})
            bas = [f['balanced_accuracy'] for f in fold_summaries]
            value = float(np.mean(bas))
            expected = {'run0_shift': shifts[0], 'run1_shift': shifts[1], 'fold_balanced_accuracy': bas,
                        'fold_diagnostics': fold_summaries, 'twofold_balanced_accuracy': value}
            equal(control['null'][n], expected, 'full paired rotation row')
            if n == 0:
                equal(control['observed'], fold_summaries, 'identity observed source fold')
                equal(row['source_twofold_balanced_accuracy'], value, 'observed source BA')
            recomputed_ba.append(value)
        equal(row['source_phase_alignment_comparison'], comparison(recomputed_ba[0], recomputed_ba), 'source comparison')
        counts['source_twofold_rotation_rows_recomputed'] += len(pairs)
        support_details, vector_values = [], []
        for session, support in enumerate(row['support_rows'], start=1):
            equal(support['session'], f'ses-{session}', 'support session')
            index = np.asarray([lookup[t] for t in support['support_trial_ids']])
            equal(all(f'/ses-{session}/run-0/' in t for t in support['support_trial_ids']), True, 'support IDs')
            labels = y[index]
            equal(support['support_labels'], labels.tolist(), 'support labels')
            equal(support['support_n'], len(index), 'support count')
            equal(support['source_coordinate_state_sha256'], bound, 'support coordinate binding')
            original_halves = halves(labels)
            expected_null = []
            for shift in range(len(index)):
                rotated = np.roll(labels, shift)
                recomputed = support_measure(a['source_standardized_CSP4'][src], y[src], a['source_standardized_CSP4'][index], rotated, scores[index], source_sd, halves(rotated))
                fixed = support_measure(a['source_standardized_CSP4'][src], y[src], a['source_standardized_CSP4'][index], rotated, scores[index], source_sd, original_halves)
                expected_null.append({'shift': shift, 'shifted_labels': rotated.tolist(), 'recomputed_classwise_halves': recomputed, 'fixed_original_half_indices': fixed})
            equal(support['null'], expected_null, 'full support rotation rows')
            observed = expected_null[0]['recomputed_classwise_halves']
            equal(support['observed'], observed, 'support observed')
            for mode in ('recomputed_classwise_halves','fixed_original_half_indices'):
                for metric in ('source_support_direction_cosine','support_split_half_direction_cosine','half_scalar_product','half_LDA_signed_contrast_product'):
                    equal(support['comparisons'][mode][metric], comparison(observed[metric], [v[mode][metric] for v in expected_null]), 'support comparison')
            contrasts = observed['half_LDA_signed_contrasts_source_sd']
            counts['support_sessions_both_LDA_contrasts_positive'] += int(all(v > 0 for v in contrasts))
            counts['support_sessions_both_LDA_contrasts_negative'] += int(all(v < 0 for v in contrasts))
            counts['support_sessions_opposite_LDA_contrast_signs'] += int(np.prod(contrasts) < 0)
            counts['support_full_score_class_collapse_sessions'] += int(observed['full_support_score_diagnostics']['class_collapse'])
            counts['support_rotation_rows_recomputed_both_modes'] += len(index)
            vector_values.append(observed['support_split_half_direction_cosine'])
            support_details.append({'session': f'ses-{session}', 'n': len(index),
                                    'split_half_vector_cosine': vector_values[-1],
                                    'half_LDA_signed_contrasts_source_sd': contrasts,
                                    'full_frozen_score_BA': observed['full_support_score_diagnostics']['balanced_accuracy'],
                                    'source_support_direction_cosine': observed['source_support_direction_cosine'],
                                    'signed_contrast_product_upper_tail_fraction_recomputed_halves': support['comparisons']['recomputed_classwise_halves']['half_LDA_signed_contrast_product']['upper_tail_fraction_descriptive']})
        source_values.append(recomputed_ba[0])
        support_values.append(float(np.mean(vector_values)))
        counts['selected_saved_rows'] += len(ids)
        summaries.append({'subject': subject, 'source_LORO_BA': recomputed_ba[0],
                          'source_rotation_upper_tail_fraction_descriptive': row['source_phase_alignment_comparison']['upper_tail_fraction_descriptive'],
                          'source_rotation_BA_range': [min(recomputed_ba),max(recomputed_ba)],
                          'mean_five_support_split_half_vector_cosine': support_values[-1], 'support_sessions': support_details})
    aggregates = {}
    for name, values in [('source_twofold_balanced_accuracy',source_values),('mean_five_support_split_half_vector_cosine',support_values)]:
        rng = np.random.default_rng(42)
        values = np.asarray(values)
        draws = values[rng.integers(0,6,size=(10000,6))].mean(axis=1)
        expected = {'participant_values': [{'subject':s,'value':float(v)} for s,v in zip(SUBJECTS,values,strict=True)],
                    'mean':float(values.mean()),'interval95':np.quantile(draws,[.025,.975]).tolist(),
                    'bootstrap_draws':draws.tolist(),'replicates':10000,'seed':42,'independent_unit':'participant','status':'completed'}
        equal(receipt['participant_summaries'][name], expected, 'participant bootstrap all saved draws')
        aggregates[name] = {k:v for k,v in expected.items() if k != 'bootstrap_draws'}
        aggregates[name]['bootstrap_draws_numeric_sha256'] = array_hash(draws)
    for name, value in [('pipeline_fit_attempts',240),('pipeline_fit_successes',240),('pipeline_fit_failures',0),('query_rows_used',0),('final_subjects_opened',0),('new_adaptation_fits',0),('new_full40_source_decoder_fits',0)]:
        equal(receipt[name],value,'receipt '+name)
    # Hash the same result bytes after all reads; do not write a result artifact.
    unchanged = all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == sha for path,sha in INPUTS.items())
    equal(unchanged, True, 'saved result unchanged')
    report = {'schema_version':1,'status':'passed','audit_started_at_utc':started,
              'audit_finished_at_utc':datetime.now(timezone.utc).isoformat(),
              'scope':'Independent saved-output arithmetic; no scientific consumer imported, estimator constructed, fit called, EEG loaded, or query opened',
              'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'checks_completed':CHECKS,'audit_numerical_comparison_absolute_tolerance':1e-12,
              'maximum_observed_absolute_difference':MAX_ERROR,
              'frozen_scientific_tolerance_unchanged':True,'result_bytes_unchanged_after_audit':unchanged,
              'counts':counts,'participant_summaries':aggregates,'subjects':summaries,
              'new_fits_performed_by_audit':0,'query_rows_read_by_audit':0,
              'scientific_interpretation':['Source LORO mean 0.6292 is heterogeneous across six participants; individual values range 0.425 to 0.750.',
                'Cyclic rotations are phase-sensitivity controls, not exchangeable formal permutation p-values.',
                'Support split-half and signed-score consistency are measurement diagnostics; this audit selects no gate or strategy.',
                'Participant bootstrap uses six participants, not trials or seeds as independent units.',
                'No target-query efficacy, human skill retention or clinical conclusion follows from these results.'],
              'limits':['This saved-output arithmetic audit does not re-project EEG through CSP filters or rerun any fit.',
                'LDA replay uses saved heldout log-CSP powers; source/support score and feature arrays are checked internally but are not rederived from EEG here.',
                'Input metadata/data identity and actual launcher execution evidence are audited separately.'],
              'saved_artifacts_verified':[{'path':path,'sha256':sha} for path,sha in sorted(INPUTS.items())]}
    with DEST.open('x') as handle:
        json.dump(report,handle,indent=2,allow_nan=False)
        handle.write('\n')
    print(json.dumps({k:report[k] for k in ('status','checks_completed','maximum_observed_absolute_difference','counts','participant_summaries')},indent=2))


if __name__ == '__main__':
    main()
