#!/usr/bin/env python3
"""Read original 36 source-fit tar bytes; audit saved predictions without forward/fit."""
import hashlib
import io
import json
import math
import tarfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional

ROOT = Path('/workspace/few-shot-mi-eeg')
ORIGINALS = Path('/workspace/private_model_receipts/remaining36-audit-20261015-run01/handoff/original-results')
OUTPUT = Path(__file__).with_suffix('.json')
CONTRACT = ROOT / 'configs/kumar_remaining_source_batch_20261015.json'
LEDGER = ROOT / 'research_logs/kumar_development_queue_20261014/accepted_jobs.json'
MEMBERS = {'weights.pt', 'weights.json', 'fit_result.json', 'training.log', 'input_audit.json',
           'training_config.json', 'input_receipt.json', 'queue_runtime.json', 'job.json',
           'run_source.py', 'train_source.py', 'adapter_source.py', 'events.jsonl',
           'source_validation_predictions.npz'}
SUBJECTS = [2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18]
SEEDS = [20261012, 20261013, 20261014]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def state_hash(payload):
    tensors = dict(payload['model_state_dict'])
    tensors.update({key: payload[key] for key in ('channel_mean', 'channel_scale', 'classes')})
    h = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        require(torch.isfinite(tensor).all().item(), 'nonfinite checkpoint tensor')
        value = tensor.detach().cpu().contiguous().numpy()
        for part in (name.encode(), str(value.dtype).encode(), json.dumps(value.shape).encode(), value.tobytes()):
            h.update(part)
    return h.hexdigest()


def main():
    started = datetime.now(timezone.utc).isoformat()
    ledger_raw = LEDGER.read_bytes()
    accepted = json.loads(ledger_raw)['accepted_jobs']
    require(len(accepted) == 18, 'baseline accepted ledger changed')
    accepted_jobs = {row['job_id'] for row in accepted}
    contract_raw = CONTRACT.read_bytes()
    contract = json.loads(contract_raw)
    expected = {row['job_id']: row for row in contract['remaining_jobs']}
    require(len(expected) == 36, 'wrong remaining queue length')
    archives = sorted(ORIGINALS.glob('*.tar'))
    require(len(archives) == 36, 'wrong original archive count')
    jobs, originals, seen = [], [], set()
    split_cache, total_tensors = {}, 0
    parameter_schema = None
    for path in archives:
        raw = path.read_bytes()
        require(0 < len(raw) <= 16 * 1024**2, 'archive byte bound')
        original_sha = sha(raw)
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as tar:
            members = tar.getmembers()
            require(len(members) == 15 and {m.name for m in members} == MEMBERS | {'manifest.json'}
                    and all(m.isfile() for m in members), 'archive member layout')
            blobs = {m.name: tar.extractfile(m).read() for m in members}
        manifest = json.loads(blobs['manifest.json'])
        entries = manifest['files']
        require(len(entries) == 14 and {row['path'] for row in entries} == MEMBERS, 'manifest scope')
        for entry in entries:
            value = blobs[entry['path']]
            require(len(value) == entry['bytes'] and sha(value) == entry['sha256'], 'member byte hash')
        job = json.loads(blobs['job.json'])
        require(job['job_id'] in expected and job == expected[job['job_id']], 'unexpected queue job')
        require(job['job_id'] not in seen and job['job_id'] not in accepted_jobs, 'repeated or previously accepted job')
        seen.add(job['job_id'])
        record, weights, config = [json.loads(blobs[name]) for name in ('fit_result.json','weights.json','training_config.json')]
        require(record['job_id'] == job['job_id'] and record['subject'] == job['subject']
                and record['seed'] == weights['seed'] == job['seed'], 'fit identity mismatch')
        require(record['source_train_rows'] == 40 and record['source_validation_rows'] == 20
                and record['query_rows_loaded'] == 0 and record['synthetic'] is False, 'source fit scope')
        require(sha(blobs['training_config.json']) == job['training_config_sha256'] == record['training_config_sha256']
                and config == weights['config'], 'scientific config binding')
        checkpoint_sha = sha(blobs['weights.pt'])
        require(checkpoint_sha == record['checkpoint_sha256'] == weights['checkpoint_sha256'], 'checkpoint byte hash')
        payload = torch.load(io.BytesIO(blobs['weights.pt']), map_location='cpu', weights_only=True)
        require(set(payload) == {'model_state_dict','channel_mean','channel_scale','classes','context_utf8'}, 'checkpoint fields')
        context = json.loads(bytes(payload['context_utf8'].tolist()).decode('utf-8'))
        require(context == {key:value for key,value in weights.items() if key != 'checkpoint_sha256'}, 'checkpoint embedded context')
        numeric_sha = state_hash(payload)
        require(numeric_sha == weights['frozen_state_sha256'], 'checkpoint numeric state hash')
        require(tuple(payload['channel_mean'].shape) == tuple(payload['channel_scale'].shape) == (1,22,1)
                and bool((payload['channel_scale'] > 0).all()) and payload['classes'].tolist() == [0,1], 'normalization and classes')
        schema = [(name, list(tensor.shape), str(tensor.dtype)) for name,tensor in sorted(payload['model_state_dict'].items())]
        if parameter_schema is None:
            parameter_schema = schema
        require(schema == parameter_schema, 'inconsistent checkpoint tensor schema')
        total_tensors += len(payload['model_state_dict']) + 3
        split_path = ROOT / config['split_manifest']
        if str(split_path) not in split_cache:
            split_raw = split_path.read_bytes()
            split_cache[str(split_path)] = (sha(split_raw), json.loads(split_raw)['trials'])
        split_sha, split_rows = split_cache[str(split_path)]
        require(split_sha == job['split_sha256'] == record['split_sha256'], 'split metadata binding')
        source_roles = {}
        for role, key in [('source_train','source_train_ids'),('source_validation','source_validation_ids')]:
            rows = {r['trial_id']:r for r in split_rows if r['subject'] == job['subject'] and r['role'] == role and r['included']}
            require(len(weights[key]) == len(rows) and set(weights[key]) == set(rows), 'source trial identity')
            source_roles[role] = rows
        require(set(weights['source_train_ids']).isdisjoint(weights['source_validation_ids']), 'train/validation overlap')
        history = weights['history']
        require(1 <= len(history) <= 100 and [r['epoch'] for r in history] == list(range(1,len(history)+1)), 'epoch history sequence')
        require(all(math.isfinite(r['source_train_loss']) and math.isfinite(r['source_validation_loss']) for r in history), 'nonfinite history')
        selected = min(range(len(history)), key=lambda i:history[i]['source_validation_loss'])
        best = history[selected]['source_validation_loss']
        require(weights['selected_epoch'] == record['selected_epoch'] == selected+1
                and weights['source_validation_loss'] == record['selected_validation_loss'] == best, 'earliest validation minimum selection')
        require(record['epochs_executed'] == len(history) and record['optimizer_steps'] == weights['optimizer_steps'] == len(history)*3, 'epoch/step accounting')
        stale, current, stop = 0, float('inf'), None
        for row in history:
            if row['source_validation_loss'] < current:
                current, stale = row['source_validation_loss'], 0
            else:
                stale += 1
            if stale >= 15:
                stop = row['epoch']
                break
        require((stop == len(history)) if stop is not None else len(history) == 100, 'frozen early stopping')
        with np.load(io.BytesIO(blobs['source_validation_predictions.npz']), allow_pickle=False) as data:
            require(set(data.files) == {'logits','labels','loss_float64','trial_ids'}, 'prediction field schema')
            logits, labels, ids, saved_losses = data['logits'].copy(), data['labels'].copy(), data['trial_ids'].tolist(), data['loss_float64'].copy()
        require(logits.shape == (20,2) and logits.dtype == np.float32 and labels.shape == (20,), 'saved logits shape/dtype')
        require(ids == weights['source_validation_ids'], 'saved logit trial order')
        expected_labels = np.asarray([config['input']['class_mapping'][source_roles['source_validation'][trial]['label']] for trial in ids])
        require(np.array_equal(labels, expected_labels), 'saved source labels')
        log64 = logits.astype(np.float64)
        ce = np.logaddexp(log64[:,0], log64[:,1]) - log64[np.arange(20), labels]
        require(np.isfinite(ce).all() and np.max(np.abs(ce-saved_losses)) < 1e-14, 'per-row float64 CE arithmetic')
        numpy_loss = float(ce.mean())
        require(record['replay_absolute_tolerance'] == 1e-7 and abs(numpy_loss-best) <= 1e-7
                and abs(record['replay_torch_loss']-best) <= 1e-7, 'original frozen CE replay gate')
        require(abs(numpy_loss-record['replay_numpy_loss']) < 1e-14, 'recorded numpy replay')
        # These are loss computations on already saved logits, not model forward passes.
        with torch.inference_mode():
            cpu_loss32 = float(functional.cross_entropy(torch.from_numpy(logits), torch.from_numpy(labels)).item())
            cpu_loss64 = float(functional.cross_entropy(torch.from_numpy(log64), torch.from_numpy(labels)).item())
        require(abs(cpu_loss64-numpy_loss) < 1e-14, 'independent CPU torch float64 CE')
        pred = logits.argmax(axis=1)
        recalls = [float(np.mean(pred[labels==k] == k)) for k in (0,1)]
        jobs.append({'job_id':job['job_id'],'subject':job['subject'],'seed':job['seed'],'result_key':job['result_key'],
                     'archive_filename':path.name,'archive_sha256':original_sha,'archive_bytes':len(raw),
                     'checkpoint_sha256':checkpoint_sha,'checkpoint_state_sha256':numeric_sha,
                     'epochs':len(history),'optimizer_steps':record['optimizer_steps'],'selected_epoch':selected+1,
                     'selected_source_validation_CE':best,'independent_saved_logits_numpy_float64_CE':numpy_loss,
                     'recorded_training_torch_replay_CE':record['replay_torch_loss'],
                     'independent_saved_logits_cpu_torch_float32_CE':cpu_loss32,
                     'independent_saved_logits_cpu_torch_float64_CE':cpu_loss64,
                     'numpy_CE_absolute_difference_from_selected':abs(numpy_loss-best),
                     'recorded_torch_CE_absolute_difference_from_selected':abs(record['replay_torch_loss']-best),
                     'cpu_torch_float32_CE_absolute_difference_from_selected':abs(cpu_loss32-best),
                     'source_validation_balanced_accuracy':float(np.mean(recalls)),
                     'source_validation_class_recall':recalls,'predicted_class_counts':[int(np.sum(pred==k)) for k in (0,1)],
                     'class_collapse':len(set(pred.tolist()))==1,
                     'source_train_rows':40,'source_validation_rows':20,'query_rows_loaded':0,
                     'max_epoch_cap_reached':len(history)==100})
        originals.append({'path':str(path),'sha256':original_sha,'bytes':len(raw)})
    require(seen == set(expected), 'queue coverage differs')
    by_key = {row['job_id']:row for row in jobs}
    jobs = [by_key[job['job_id']] for job in contract['remaining_jobs']]
    grouped = defaultdict(list)
    for row in jobs:
        grouped[row['subject']].append(row)
    participants = []
    for subject in SUBJECTS:
        rows = grouped[f'sub-{subject}']
        require([r['seed'] for r in rows] == SEEDS, 'fixed three-seed order')
        participants.append({'subject':f'sub-{subject}','seeds':SEEDS,
                             'source_validation_BA_all_seeds':[r['source_validation_balanced_accuracy'] for r in rows],
                             'source_validation_BA_mean_all_three_seeds':float(np.mean([r['source_validation_balanced_accuracy'] for r in rows])),
                             'source_validation_CE_mean_all_three_seeds':float(np.mean([r['selected_source_validation_CE'] for r in rows])),
                             'epochs_all_seeds':[r['epochs'] for r in rows],
                             'selected_epochs_all_seeds':[r['selected_epoch'] for r in rows],
                             'collapsed_seed_count':sum(r['class_collapse'] for r in rows)})
    total_epochs = sum(r['epochs'] for r in jobs)
    total_steps = sum(r['optimizer_steps'] for r in jobs)
    require((total_epochs,total_steps)==(1844,5532), 'claimed aggregate epochs/steps mismatch')
    require(LEDGER.read_bytes() == ledger_raw, 'accepted18 ledger modified during audit')
    require(all(sha(Path(row['path']).read_bytes()) == row['sha256'] for row in originals), 'archive modified during audit')
    report = {'schema_version':1,'status':'passed_saved_prediction_and_checkpoint_integrity_audit',
              'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
              'audit_script_sha256':sha(Path(__file__).read_bytes()),'operation_contract_sha256':sha(contract_raw),
              'accepted18_ledger_sha256_before_and_after':sha(ledger_raw),'accepted18_ledger_changed':False,
              'runtime':{'numpy':np.__version__,'torch':torch.__version__},
              'counts':{'models':36,'participants':12,'seeds_per_participant':3,'epochs':total_epochs,'optimizer_steps':total_steps,
                        'source_validation_prediction_rows_across_seeds':720,'distinct_source_validation_trials':240,
                        'checkpoint_tensors_checked_including_normalization_and_classes':total_tensors,
                        'class_collapsed_models':sum(r['class_collapse'] for r in jobs),
                        'max_epoch_cap_reached_models':sum(r['max_epoch_cap_reached'] for r in jobs),
                        'query_rows_read_by_audit':0,'EEG_arrays_loaded_by_audit':0,'model_forward_passes_by_audit':0,'fits_by_audit':0,'optimizers_created_by_audit':0},
              'replay':{'frozen_absolute_tolerance':1e-7,
                        'maximum_numpy_float64_CE_difference_from_selected':max(r['numpy_CE_absolute_difference_from_selected'] for r in jobs),
                        'maximum_recorded_torch_replay_difference_from_selected':max(r['recorded_torch_CE_absolute_difference_from_selected'] for r in jobs),
                        'maximum_cpu_torch_float32_saved_logit_CE_difference_from_selected':max(r['cpu_torch_float32_CE_absolute_difference_from_selected'] for r in jobs),
                        'cpu_torch_float32_saved_logit_differences_above_original_tolerance':sum(r['cpu_torch_float32_CE_absolute_difference_from_selected']>1e-7 for r in jobs),
                        'scope':'Independent CPU CE uses saved validation logits only; recorded training torch replay is preserved evidence, not a new checkpoint forward replay.'},
              'descriptive_summary':{'independent_unit':'participant','seed_handling':'all three frozen seeds averaged within each participant; no selection',
                 'equal_participant_mean_source_validation_BA':float(np.mean([r['source_validation_BA_mean_all_three_seeds'] for r in participants])),
                 'participant_mean_BA_range':[min(r['source_validation_BA_mean_all_three_seeds'] for r in participants),max(r['source_validation_BA_mean_all_three_seeds'] for r in participants)],
                 'equal_participant_mean_source_validation_CE':float(np.mean([r['source_validation_CE_mean_all_three_seeds'] for r in participants])),
                 'participants':participants},
              'numeric_audit_coverage':{'history':'all 36 histories, earliest minimum, patience15 or epoch100 bound, epochs and steps',
                'labels':'source-validation saved IDs/order/labels checked against frozen split metadata; TRAIN/validation disjoint',
                'checkpoint':'raw SHA, weights-only CPU tensor loading, embedded context, all finite tensors/state hash, positive source normalization, common tensor schema',
                'saved_predictions':'20x2 float32 logits, per-row float64 CE, numpy reduction, CPU torch float32 and float64 CE, fixed argmax BA',
                'not_performed':'checkpoint model construction/forward, EEG loading, retraining, optimizer construction, query evaluation'},
              'scientific_limits':['These source-validation labels selected the checkpoint. BA and CE are descriptive selected-checkpoint statistics, not untouched held-out generalization evidence.',
                'Seeds share the same participant trials and are not 36 independent participants. All fixed seeds are retained.',
                'No inference of adaptation effectiveness, longitudinal skill retention, clinical benefit or valid gating follows from these source summaries.'],
              'next_frozen_analysis_readiness':{'all_36_saved_source_packages_available':True,'scientific_evaluation_released':False,
                'R2_full_GET_and_parent_acceptance_required':'handled separately; this summary supplies neither acceptance nor R2 proof',
                'checkpoint_reuse_path':'retain all 18+36 identities; only separately frozen, reviewed read-only checkpoint reuse could later evaluate a query; do not call generic formal_train',
                'source_only_claim':'no new strategy, seed search, source refit, query adapter or query access authorized by this audit'},
              'checkpoint_parameter_schema':parameter_schema,'jobs':jobs,'original_archives':originals}
    with OUTPUT.open('x') as handle:
        json.dump(report,handle,indent=2,allow_nan=False)
        handle.write('\n')
    print(json.dumps({'status':report['status'],'counts':report['counts'],'replay':report['replay'],
                      'descriptive_BA':report['descriptive_summary']['equal_participant_mean_source_validation_BA'],
                      'descriptive_CE':report['descriptive_summary']['equal_participant_mean_source_validation_CE']},indent=2))


if __name__ == '__main__':
    main()
