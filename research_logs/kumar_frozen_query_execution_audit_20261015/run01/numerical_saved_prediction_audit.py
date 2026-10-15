"""Independent saved-query JSON arithmetic audit. No model, tensor or EEG IO."""
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path('/workspace/few-shot-mi-eeg')
RESULTS = Path('/workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results')
OUTPUT = Path(__file__).with_name('numerical_saved_prediction_audit.json')
PLAN = ROOT / 'research_logs/kumar_remaining36_acceptance_20261015/run01/source_model_plan_all54.json'
LEDGER = ROOT / 'research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json'
MANIFEST = ROOT / 'configs/kumar_frozen_query_inputs_20261015.json'
SPLIT = ROOT / 'research_logs/kumar_cross_session_20261012/protocol/split_manifest.json'
CONFIG = ROOT / 'configs/kumar_eegnet_gpu_development_20261014.json'
DEVELOPMENT = ['sub-1','sub-4','sub-7','sub-10','sub-13','sub-16']
REMAINING = ['sub-2','sub-3','sub-5','sub-6','sub-8','sub-9','sub-11','sub-12','sub-14','sub-15','sub-17','sub-18']
SUBJECTS = [f'sub-{n}' for n in range(1,19)]
SEEDS = [20261012,20261013,20261014]
SESSIONS = [f'ses-{n}' for n in range(6)]
SCOPE = 'accepted54_always_frozen_query_only'
CHECKS, MAX_ERROR = 0, 0.0
INPUTS = {}


def read(path):
    raw = path.read_bytes()
    INPUTS[str(path)] = {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return json.loads(raw)


def equal(actual, expected, label):
    global CHECKS, MAX_ERROR
    CHECKS += 1
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ValueError(label + ': mapping keys differ')
        for key, value in expected.items():
            equal(actual[key], value, label+'.'+key)
    elif isinstance(expected, (list,tuple)):
        if len(actual) != len(expected):
            raise ValueError(label + ': length differs')
        for i,(a,b) in enumerate(zip(actual,expected,strict=True)):
            equal(a,b,f'{label}[{i}]')
    elif isinstance(expected, (float,np.floating)):
        difference = abs(float(actual)-expected)
        if not np.isfinite(difference) or difference > 1e-12:
            raise ValueError(f'{label}: numerical difference {difference}')
        MAX_ERROR = max(MAX_ERROR,float(difference))
    elif actual != expected:
        raise ValueError(label + ': value differs')


def endpoint(values):
    # Match the frozen subject ordering explicitly, without importing its code.
    ordered = np.asarray([values[s] for s in sorted(values,key=str)], dtype=np.float64)
    rng = np.random.default_rng(42)
    drawn = ordered[rng.integers(0,len(ordered),size=(10000,len(ordered)))].mean(axis=1)
    alpha = (1-0.95)/2
    interval = np.quantile(drawn,[alpha,1-alpha]).tolist()
    bootstrap = {'unit':'subject','n_subjects':len(values),'mean':float(ordered.mean()),
                 'confidence':0.95,'confidence_interval':interval,
                 'interval_method':'subject_percentile_bootstrap','n_resamples':10000,'seed':42}
    return {'status':'complete','participant_values':values,'unavailable_participants':[],
            'mean':bootstrap['mean'],'bootstrap':bootstrap,'participants_dropped':0}, hashlib.sha256(drawn.tobytes()).hexdigest()


def main():
    start = datetime.now(timezone.utc).isoformat()
    plan, ledger, manifest, split, config = read(PLAN), read(LEDGER), read(MANIFEST), read(SPLIT), read(CONFIG)
    jobs, accepted = plan['jobs'], ledger['accepted_jobs']
    equal(len(jobs),54,'job count')
    equal([r['job_id'] for r in accepted],[r['job_id'] for r in jobs],'accepted job sequence')
    equal({(j['subject'],j['seed']) for j in jobs},{(s,k) for s in SUBJECTS for k in SEEDS},'fixed cohort')
    frozen = [r for r in split['trials'] if r['included'] and r['role'] in ('source_query','target_query')]
    expected_ids = [r['trial_id'] for r in frozen]
    equal(expected_ids,manifest['included_query_trial_ids'],'manifest/split exact order')
    equal(len(expected_ids),4290,'unique frozen trial count')
    equal(len(set(expected_ids)),4290,'unique frozen identities')
    worker = read(RESULTS/'worker_complete.json')
    aggregate = read(RESULTS/'aggregate_summary.json')
    equal(worker['status'],'all54_evaluated_pending_independent_audit','worker completed')
    equal(worker['job_count'],54,'worker job count')
    equal([r['job_id'] for r in worker['jobs']],[j['job_id'] for j in jobs],'worker job order')
    for key in ('accepted','independently_audited','R2_full_GET_verified'):
        equal(worker[key],False,'original pending '+key)
    equal(worker['new_fits'],0,'worker no new fits')
    equal(worker['optimizer_instances'],0,'worker no optimizer')
    equal(worker['query_input_bytes_unchanged'],True,'worker input state')
    session_metrics, saved_states, participant_session_scores = [], [], {}
    total_predictions = 0
    identities_by_subject = {}
    for job,accepted_entry,member in zip(jobs,accepted,worker['jobs'],strict=True):
        subject,seed = job['subject'],job['seed']
        path = RESULTS/member['path']
        equal(path.parent,RESULTS,'local result path')
        result = read(path)
        equal(INPUTS[str(path)]['bytes'],member['bytes'],'saved result size')
        equal(INPUTS[str(path)]['sha256'],member['sha256'],'saved result hash')
        identity = result['identity']
        for key in ('job_id','subject','seed','result_key'):
            equal(identity[key],job[key],'result identity '+key)
        equal(identity['archive_sha256'],accepted_entry['archive_sha256'],'accepted archive identity')
        for key in ('synthetic','software_validation_only','new_fit'):
            equal(identity[key],False,'real unchanged checkpoint '+key)
        equal(identity['execution_device'],'cpu','actual evaluation device')
        for key,value in {'scope':SCOPE,'optimizer_instances_created':0,'optimizer_steps':0,'new_fit':False,
                          'processed_input_hashes_verified':True,'source_training_context_preserved':True,
                          'input_files_unchanged':True,'parameter_BN_normalization_updates':False,
                          'query_labels_used_for':'fixed_metrics_only','scientific_acceptance_pending':True}.items():
            equal(result[key],value,'readonly result '+key)
        before,after = result['state_before_sha256'],result['state_after_sha256']
        equal(bool(re.fullmatch('[0-9a-f]{64}',before)),True,'state digest format')
        equal(before,after,'parameter BN normalization state unchanged')
        equal(bool(re.fullmatch('[0-9a-f]{64}',identity['checkpoint_sha256'])),True,'checkpoint hash format')
        rows = result['predictions']
        frozen_subject = [r for r in frozen if r['subject']==subject]
        equal([r['trial_id'] for r in rows],[r['trial_id'] for r in frozen_subject],'complete ordered subject queries')
        equal(result['query_rows_evaluated'],len(rows),'evaluated rows')
        equal(result['real_query_rows_loaded'],len(rows),'real saved query row count')
        for row,source in zip(rows,frozen_subject,strict=True):
            for key in ('subject','session','run','role','trial_id'):
                equal(row[key],source[key],'frozen query identity '+key)
            equal(row['seed'],seed,'query seed')
            equal(row['y_true'],config['input']['class_mapping'][source['label']],'frozen query label')
            logits = (row['logit_0'],row['logit_1'])
            equal(all(math.isfinite(x) for x in logits),True,'finite logits')
            equal(row['y_pred'],int(logits[1] > logits[0]),'fixed argmax including left-class tie')
        triple = [(r['trial_id'],r['y_true'],r['session'],r['run'],r['role']) for r in rows]
        if subject in identities_by_subject:
            equal(triple,identities_by_subject[subject],'same identities labels across seeds')
        identities_by_subject[subject] = triple
        measured = []
        for session in SESSIONS:
            selected = [r for r in rows if r['session']==session]
            matrix = [[sum(r['y_true']==y and r['y_pred']==p for r in selected) for p in (0,1)] for y in (0,1)]
            totals = [sum(r) for r in matrix]
            equal(all(n>0 for n in totals),True,'both query classes available')
            recall = [float(matrix[k][k]/totals[k]) for k in (0,1)]
            counts = [sum(r[k] for r in matrix) for k in (0,1)]
            metrics = {'subject':subject,'seed':seed,'session':session,
                'role':'source_query' if session=='ses-0' else 'target_query',
                'n':len(selected),'confusion_matrix':matrix,'class_recalls':recall,
                'balanced_accuracy':float(np.mean(recall)),'balanced_accuracy_status':'estimated',
                'predicted_class_counts':counts,'class_collapse':0 in counts}
            measured.append(metrics)
            session_metrics.append({'job_id':job['job_id'],**metrics})
            participant_session_scores[(subject,seed,session)] = metrics['balanced_accuracy']
        equal(result['session_metrics'],measured,'all six independently recomputed metrics')
        saved_states.append({'job_id':job['job_id'],'subject':subject,'seed':seed,
                             'archive_sha256':identity['archive_sha256'],'checkpoint_sha256':identity['checkpoint_sha256'],
                             'state_before_sha256':before,'state_after_sha256':after})
        total_predictions += len(rows)
    equal(total_predictions,12870,'all saved prediction rows')
    equal(len(session_metrics),324,'all saved session metrics')
    for subject in SUBJECTS:
        complete = read(RESULTS/f'{subject}-complete.json')
        equal(complete,{'subject':subject,'jobs':[r for r in worker['jobs'] if r['subject']==subject]},'subject completion receipt')
    per_session,per_participant,variation = [],[],[]
    for subject in SUBJECTS:
        values = []
        for session in SESSIONS:
            seed_values = [participant_session_scores[(subject,seed,session)] for seed in SEEDS]
            mean = float(np.mean(seed_values))
            values.append(mean)
            per_session.append({'subject':subject,'session':session,
                'role':'source_query' if session=='ses-0' else 'target_query','seeds':SEEDS,
                'seed_balanced_accuracies':seed_values,'mean_three_seed_balanced_accuracy':mean})
        per_participant.append({'subject':subject,'source_query_balanced_accuracy':values[0],
            'target_five_session_balanced_accuracy':float(np.mean(values[1:])),
            'target_session_balanced_accuracies':values[1:]})
        target_seed_means = [float(np.mean([participant_session_scores[(subject,seed,s)] for s in SESSIONS[1:]])) for seed in SEEDS]
        variation.append({'subject':subject,'target_five_session_BA_per_seed':target_seed_means,
                          'within_participant_seed_range':max(target_seed_means)-min(target_seed_means),
                          'target_session_BA_range_after_all_seed_mean':max(values[1:])-min(values[1:])})
    cohorts,bootstrap_digests = {},{}
    for name,subjects in {'development6':DEVELOPMENT,'remaining12':REMAINING,'all18_secondary_exploratory':SUBJECTS}.items():
        selected = [r for r in per_participant if r['subject'] in subjects]
        target,digest_target = endpoint({r['subject']:r['target_five_session_balanced_accuracy'] for r in selected})
        source,digest_source = endpoint({r['subject']:r['source_query_balanced_accuracy'] for r in selected})
        cohorts[name] = {'subjects':subjects,'independent_participants':len(subjects),'target_query':target,'source_query_secondary':source}
        bootstrap_digests[name] = {'target_query':digest_target,'source_query_secondary':digest_source}
    expected_aggregate = {'schema_version':1,'status':'complete','scope':SCOPE,'synthetic':False,'software_validation_only':False,
        'job_count':54,'jobs':[j['job_id'] for j in jobs],'unique_query_trial_count':4290,'prediction_rows_with_repeated_seeds':12870,
        'aggregation_rule':'equal mean of all three seeds within participant/session, then equal mean of five target sessions within participant',
        'source_query_separate_secondary':True,'cohorts':cohorts,'per_participant':per_participant,
        'per_participant_session':per_session,'per_job_session_metrics':session_metrics,'unavailable_session_metrics':[],
        'class_collapse_job_sessions':sum(r['class_collapse'] for r in session_metrics),
        'missing_jobs_or_sessions_dropped':0,'seed_selection_performed':False,'model_fits':0,'model_forwards':0,
        'checkpoint_tensor_loads':0,'comparison_with_CPU_baselines_computed':False,'scientific_acceptance_pending':True,
        'limits':['Synthetic results are software validation only when flagged synthetic.',
            'Later strategy claims on the previously exposed cohort remain exploratory; no strategy or threshold is selected.',
            'This baseline extension does not replace the frozen CPU primary comparison.',
            'Offline query decoding cannot establish human learning, skill retention or clinical effect.']}
    equal(aggregate,expected_aggregate,'every aggregate summary field')
    equal(all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==value['sha256'] for path,value in INPUTS.items()),True,'input bytes unchanged after audit')
    report = {'schema_version':1,'status':'passed_independent_saved_prediction_arithmetic_audit',
        'started_at_utc':start,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Only saved prediction/completion/aggregate JSON and frozen plan/ledger/manifest/split metadata; no model, tensor or raw EEG reads',
        'independent_implementation':'Manual confusion/argmax/identity arithmetic and NumPy participant bootstrap; original aggregation/statistics functions are not imported or called',
        'checks_completed':CHECKS,'maximum_observed_absolute_difference':MAX_ERROR,'arithmetic_comparison_tolerance':1e-12,
        'counts':{'jobs':54,'participants':18,'seeds_each':3,'participant_seed_session_metrics':324,
                  'prediction_rows':12870,'unique_query_trials':4290,
                  'unique_source_query_trials':sum(r['role']=='source_query' for r in frozen),
                  'unique_target_query_trials':sum(r['role']=='target_query' for r in frozen),
                  'recorded_state_before_after_hash_equal':54,'unavailable_sessions':0,
                  'class_collapse_job_sessions':sum(r['class_collapse'] for r in session_metrics),
                  'source_query_class_collapse_job_sessions':sum(r['class_collapse'] for r in session_metrics if r['role']=='source_query'),
                  'target_query_class_collapse_job_sessions':sum(r['class_collapse'] for r in session_metrics if r['role']=='target_query'),
                  'target_endpoint_participants_above_0_5':sum(r['target_five_session_balanced_accuracy']>0.5 for r in per_participant),
                  'new_forward_passes_in_audit':0,'raw_EEG_arrays_loaded_in_audit':0,'checkpoint_tensors_loaded_in_audit':0,'fits_in_audit':0},
        'cohorts':cohorts,'participant_endpoints':per_participant,'seed_session_variability_descriptive':variation,
        'bootstrap_draws_float64_sha256':bootstrap_digests,'state_evidence':saved_states,
        'scientific_findings':['The frozen target-query baseline is close to 0.5 at the participant aggregate; all reported cohort target bootstrap intervals include 0.5.',
            'All three frozen seeds and all five target sessions are included with equal weights at their prescribed aggregation levels.',
            'Source-query is separate and secondary; no new comparison with CPU baselines or adaptive policy is computed.',
            'Class-collapse and participant/seed/session variation remain visible; no best seed, threshold or strategy is chosen.',
            'The all18 result is secondary/exploratory, and prior cohort exposure remains relevant to later strategy claims.',
            'Offline decoding provides no evidence of human skill retention or clinical benefit.'],
        'limitations':['Saved predictions are independently checked against frozen query identity/label metadata and arithmetic; logits are not regenerated from EEG or checkpoint weights in this audit.',
            'The 54 before/after model-state digests are checked as saved execution evidence, not recomputed by a second model evaluation.',
            'Input/launcher/resource/authorization and R2 original-byte closure are separate audits; this report does not grant scientific acceptance or further execution.'],
        'saved_inputs_unchanged_after_audit':True,'inputs':[{'path':path,**value} for path,value in sorted(INPUTS.items())]}
    with OUTPUT.open('x') as handle:
        json.dump(report,handle,indent=2,allow_nan=False);handle.write('\n')
    print(json.dumps({'status':report['status'],'checks':CHECKS,'max_error':MAX_ERROR,'counts':report['counts'],
        'cohort_means':{name:{'target':row['target_query']['mean'],'source':row['source_query_secondary']['mean']} for name,row in cohorts.items()},
        'maximum_participant_seed_target_BA_range':max(r['within_participant_seed_range'] for r in variation)},indent=2))


if __name__ == '__main__':
    main()
