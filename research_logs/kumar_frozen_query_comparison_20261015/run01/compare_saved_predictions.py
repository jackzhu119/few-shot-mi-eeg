"""Compare already saved CPU/EEGNet predictions on exactly matched frozen queries.

Reads text result/metadata only. No EEG, weights, model forward, fit, new policy,
seed selection or new significance test. Different label/fit budgets are explicit.
"""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path('/workspace/few-shot-mi-eeg')
OUT = Path(__file__).parent
CPU = ROOT / 'research_logs/kumar_cross_session_20261012/baselines/cpu_run01_20261013T151445Z'
EEG = Path('/workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results')
CPUR2 = ROOT / 'research_logs/recovery_20261014/kumar_results_R2_run01.json'
EEGR2 = ROOT / 'research_logs/kumar_frozen_query_execution_audit_20261015/run01/r2_full_get_receipt.json'
SPLIT = ROOT / 'research_logs/kumar_cross_session_20261012/protocol/split_manifest.json'
PROTOCOL = ROOT / 'configs/kumar_cross_session_20261012.json'
CPUMETHODS = ['source_only','frozen_csp_lda_recalibration','refit_csp_lda']
METHODS = CPUMETHODS + ['always_frozen_eegnet']
SUBJECTS = [f'sub-{i}' for i in range(1,19)]
DEV = ['sub-1','sub-4','sub-7','sub-10','sub-13','sub-16']
TEST = [s for s in SUBJECTS if s not in DEV]
SEEDS = [20261012,20261013,20261014]
SESSIONS = [f'ses-{i}' for i in range(6)]
INPUTS, CHECKS = {}, 0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError(message)


def raw(path):
    value = path.read_bytes()
    INPUTS[str(path)] = {'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
    return value


def read(path):
    return json.loads(raw(path))


def read_csv(path):
    return list(csv.DictReader(io.StringIO(raw(path).decode('utf-8'))))


def r2_entries(path):
    receipt = read(path)
    check(receipt['status']=='completed' and receipt['readback_mode']=='all','Unclosed historical R2 receipt')
    records = {r['relative_path']:r for r in receipt['files']}
    check(len(records)==len(receipt['files']),'Duplicate R2 object entry')
    return records


def verify_r2(path, relative, entries):
    check(relative in entries,'R2 object absent: '+relative)
    entry = entries[relative]
    value = raw(path)
    check(entry['bytes']==len(value) and entry['sha256']==hashlib.sha256(value).hexdigest()
          and entry['readback_bytes']==len(value) and entry['verification']=='full_get_sha256_verified'
          and entry['get_http_status']==200 and entry['head_http_status']==200,'Historical full GET mismatch: '+relative)



def validate_exact_query_join(rows, expected_by_id, label_key):
    ids = [r['trial_id'] for r in rows]
    check(len(ids)==len(set(ids))==len(expected_by_id) and set(ids)==set(expected_by_id),
          'Duplicate/missing/unexpected query identity')
    check(all(int(r[label_key])==int(expected_by_id[r['trial_id']]['label']=='right_hand') for r in rows),
          'Mismatched frozen query label')


def synthetic_join_checks():
    expected = {'synthetic-a':{'label':'left_hand'},'synthetic-b':{'label':'right_hand'}}
    valid = [{'trial_id':'synthetic-a','label':0},{'trial_id':'synthetic-b','label':1}]
    validate_exact_query_join(valid,expected,'label')
    rejected=[]
    for name,rows in [('duplicate',[valid[0],valid[0]]),('missing',[valid[0]]),
                      ('mismatched_label',[valid[0],{'trial_id':'synthetic-b','label':0}])]:
        try:
            validate_exact_query_join(rows,expected,'label')
        except ValueError as error:
            rejected.append({'case':name,'rejected':True,'message':str(error)})
        else:
            raise AssertionError('Synthetic bad join was accepted: '+name)
    with (OUT/'synthetic_join_validation.json').open('x') as handle:
        json.dump({'synthetic':True,'software_validation_only':True,'valid_join_passed':True,
                   'rejected_cases':rejected,'tests':4,'raw_signals_or_models_used':False},handle,indent=2)
        handle.write('\n')


def scores(labels,predictions):
    check(len(labels)==len(predictions)>0,'Missing predictions')
    matrix = [[sum(y==a and p==b for y,p in zip(labels,predictions,strict=True)) for b in (0,1)] for a in (0,1)]
    check(all(sum(row)>0 for row in matrix),'Missing true class; no silent drop')
    recalls = [matrix[k][k]/sum(matrix[k]) for k in (0,1)]
    counts = [sum(row[k] for row in matrix) for k in (0,1)]
    return {'BA':float(np.mean(recalls)),'recalls':recalls,'matrix':matrix,'counts':counts,'collapse':0 in counts}


def bootstrap(values):
    ordered = np.asarray([values[s] for s in sorted(values)],dtype=np.float64)
    rng = np.random.default_rng(42)
    means = ordered[rng.integers(0,len(ordered),size=(10000,len(ordered)))].mean(axis=1)
    return {'mean':float(ordered.mean()),'median':float(np.median(ordered)),
            'ci95':np.quantile(means,[.025,.975]).tolist()}


def write_csv(name,rows):
    with (OUT/name).open('x',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def main():
    started = datetime.now(timezone.utc).isoformat()
    synthetic_join_checks()
    protocol = read(PROTOCOL)
    check(protocol['statistics']['primary_comparison']=='refit_csp_lda_minus_source_only_on_same_target_queries'
          and protocol['statistics']['bootstrap_replicates']==10000 and protocol['statistics']['seed']==42,'Frozen statistics changed')
    for path in ['KUMAR_FROZEN_EXPERIMENT_PROTOCOL.md','EEGNET_TRAINING_PLAN.md','docs/kumar_frozen_checkpoint_query_protocol_20261015.md']:
        raw(ROOT/path)
    split = read(SPLIT)['trials']
    cpu_r2,eeg_r2 = r2_entries(CPUR2),r2_entries(EEGR2)
    for name in ['execution_receipt.json','failures.json','participant_bootstrap_summary.json']:
        verify_r2(CPU/name,name,cpu_r2)
    cpu_execution,failures,old_summary = read(CPU/'execution_receipt.json'),read(CPU/'failures.json'),read(CPU/'participant_bootstrap_summary.json')
    check(failures==[] and cpu_execution['failures']==[],'Historical CPU failures must be retained; complete comparison unavailable')
    check(cpu_execution['source_validation_used_for_selection'] is False and cpu_execution['target_query_never_fitted'] is True,'CPU source/query policy differs')
    check(cpu_execution['config_sha256']==INPUTS[str(PROTOCOL)]['sha256'] and cpu_execution['split_manifest_sha256']==INPUTS[str(SPLIT)]['sha256'],'CPU config/split hash mismatch')
    for name in ['worker_complete.json','aggregate_summary.json']:
        verify_r2(EEG/name,'results/'+name,eeg_r2)
    worker,aggregate = read(EEG/'worker_complete.json'),read(EEG/'aggregate_summary.json')
    check(worker['job_count']==54 and len(worker['jobs'])==54,'Incomplete EEGNet jobs')
    check(aggregate['job_count']==54 and aggregate['unique_query_trial_count']==4290,'EEGNet scope differs')
    query_rows = [r for r in split if r['role'] in ('source_query','target_query')]
    included = [r for r in query_rows if r['included']]
    excluded = [r for r in query_rows if not r['included']]
    check(len(query_rows)==4320 and len(included)==4290 and len(excluded)==30,'Frozen query exclusions differ')
    check(len({r['trial_id'] for r in included})==4290,'Duplicate frozen query identity')
    sessions,per_seed,budgets,join_receipts = [],[],[],[]
    cpu_predictions_count,eeg_predictions_count = 0,0
    cpu_collapsed,eeg_collapsed = 0,0
    for subject in SUBJECTS:
        cohort = 'development' if subject in DEV else 'final_test'
        all_subject = [r for r in split if r['subject']==subject]
        allowed = [r for r in all_subject if r['included']]
        queries = [r for r in allowed if r['role'] in ('source_query','target_query')]
        query_map = {r['trial_id']:r for r in queries}
        train = [r['trial_id'] for r in allowed if r['role']=='source_train']
        validation = [r['trial_id'] for r in allowed if r['role']=='source_validation']
        check(len(train)==40 and len(validation)==20,'Source fit/validation count differs')
        support = {session:[r['trial_id'] for r in allowed if r['role']=='target_support' and r['session']==session] for session in SESSIONS[1:]}
        names = ['query_predictions.csv','metrics.csv','included_trial_metadata.json','source_event_metadata.json','fit_access_audit.json','model_audit.json','participant_receipt.json','source_validation.json']
        for name in names:
            verify_r2(CPU/subject/name,subject+'/'+name,cpu_r2)
        events,meta = read(CPU/subject/'source_event_metadata.json'),read(CPU/subject/'included_trial_metadata.json')
        check([r['trial_id'] for r in events]==[r['trial_id'] for r in all_subject],'CPU full event order differs')
        check([r['trial_id'] for r in meta]==[r['trial_id'] for r in allowed],'CPU included/excluded identity differs')
        keys = ('trial_id','subject','session','run','role','label','included','exclusion_reason','raw_file_sha256','raw_window_numeric_sha256','processed_window_numeric_sha256')
        check(all(all(a.get(k)==b.get(k) for k in keys) for a,b in zip(events,all_subject,strict=True)),'CPU/frozen metadata labels/exclusions/numeric hashes differ')
        check(all(isinstance(r.get('processed_window_numeric_sha256'),str) and len(r['processed_window_numeric_sha256'])==64 for r in allowed)
              and all(r.get('processed_window_numeric_sha256') is None for r in all_subject if not r['included']),
              'Processed hash availability differs from frozen inclusion')
        fit_audit = read(CPU/subject/'fit_access_audit.json')
        check(len(fit_audit)==11,'CPU fit event count differs')
        source_fit = [r for r in fit_audit if r['method']=='source_only']
        check(len(source_fit)==1 and source_fit[0]['trial_ids']==train and source_fit[0]['n_fit']==40
              and source_fit[0]['csp_fit'] is True and source_fit[0]['lda_fit'] is True,'CPU source fit budget differs')
        for session in SESSIONS[1:]:
            check(len(support[session]) in (19,20),'Current support count differs')
            for method in CPUMETHODS[1:]:
                fits = [r for r in fit_audit if r['method']==method and r['session']==session]
                check(len(fits)==1,'Missing/duplicate CPU adaptation fit')
                fit = fits[0]
                check(fit['trial_ids']==train+support[session] and fit['n_fit']==40+len(support[session])
                      and fit['csp_fit']==(method=='refit_csp_lda') and fit['lda_fit'] is True
                      and fit['query_and_validation_disjoint'] is True and fit['target_access']=='current_session_support_only','CPU current-only support/fit budget differs')
        receipt,val = read(CPU/subject/'participant_receipt.json'),read(CPU/subject/'source_validation.json')
        check(receipt['source_frozen'] is True and receipt['source_parameter_sha256_before']==receipt['source_parameter_sha256_after']
              and receipt['query_never_used_for_fit'] is True and receipt['source_validation_trial_ids']==validation,'CPU participant read-only source evidence differs')
        check(val['validation_trial_ids']==validation and val['validation_never_refitted'] is True
              and val['configuration_selection']=='none_single_prefixed_config','CPU validation only descriptive differs')
        cpu_pred,cpu_metrics,model_audit = read_csv(CPU/subject/'query_predictions.csv'),read_csv(CPU/subject/'metrics.csv'),read(CPU/subject/'model_audit.json')
        check(len(cpu_pred)==3*len(queries) and len(cpu_metrics)==len(model_audit)==18,'CPU complete prediction/session coverage differs')
        cpu_predictions_count += len(cpu_pred)
        method_keys = set()
        for method in CPUMETHODS:
            selected = [r for r in cpu_pred if r['method']==method]
            check(len(selected)==len(queries) and len({r['trial_id'] for r in selected})==len(queries)
                  and {r['trial_id'] for r in selected}==set(query_map),'CPU/query exact join differs')
            validate_exact_query_join(selected,query_map,'label')
            for row in selected:
                frozen = query_map[row['trial_id']]
                check(row['subject']==subject and row['cohort']==cohort and row['session']==frozen['session']
                      and row['run']==frozen['run'] and row['synthetic']=='False'
                      and int(row['label'])==int(frozen['label']=='right_hand')
                      and row['label_name']==frozen['label'] and int(row['prediction']) in (0,1),'CPU label/query identity differs')
            for session in SESSIONS:
                pred = [r for r in selected if r['session']==session]
                true = [int(r['label']) for r in pred]
                measured = scores(true,[int(r['prediction']) for r in pred])
                saved = [r for r in cpu_metrics if r['method']==method and r['session']==session]
                check(len(saved)==1,'Missing CPU session metric')
                m=saved[0]
                support_n = 0 if method=='source_only' or session=='ses-0' else len(support[session])
                check(int(m['n_query'])==len(pred) and float(m['balanced_accuracy'])==measured['BA']
                      and [float(m['recall_left_hand']),float(m['recall_right_hand'])]==measured['recalls']
                      and [[int(m[f'confusion_{a}{b}']) for b in (0,1)] for a in (0,1)]==measured['matrix']
                      and (m['class_collapse']=='True')==measured['collapse']
                      and int(m['n_source_train'])==40 and int(m['n_target_support'])==support_n and int(m['n_fit'])==40+support_n,'CPU saved metric/budget arithmetic differs')
                audit = [r for r in model_audit if r['method']==method and r['session']==session]
                check(len(audit)==1,'Missing model text audit')
                audit=audit[0]
                check(set(audit['query_trial_ids'])=={r['trial_id'] for r in pred}
                      and audit['target_support_trial_ids']==([] if support_n==0 else support[session])
                      and audit['fit_trial_ids']==train+([] if support_n==0 else support[session])
                      and audit['parameter_sha256_before']==audit['parameter_sha256_after']
                      and audit['query_state_unchanged'] is True and audit['query_never_used_for_fit'] is True,'CPU stored fit/query/unchanged evidence differs')
                sessions.append({'subject':subject,'cohort':cohort,'method':method,'session':session,'n_unique_query_trials':len(pred),
                    'balanced_accuracy':measured['BA'],'seeds_included':1,'class_collapsed_seed_sessions':int(measured['collapse']),
                    'source_train_labels':40,'validation_labels_used_for_checkpoint_selection':0,'target_support_labels':support_n})
                cpu_collapsed += int(measured['collapse'])
                method_keys.add((method,session))
        check(len(method_keys)==18,'Missing CPU method/session')
        jobs = [j for j in worker['jobs'] if j['subject']==subject]
        check([j['seed'] for j in jobs]==SEEDS,'EEGNet seed coverage/order differs')
        seeded = {session:[] for session in SESSIONS}
        seeded_collapses = {session:0 for session in SESSIONS}
        for job in jobs:
            verify_r2(EEG/job['path'],'results/'+job['path'],eeg_r2)
            result = read(EEG/job['path'])
            check(INPUTS[str(EEG/job['path'])]['sha256']==job['sha256'] and result['identity']['job_id']==job['job_id'],'EEGNet result identity hash differs')
            check(result['new_fit'] is False and result['optimizer_steps']==0
                  and result['parameter_BN_normalization_updates'] is False
                  and result['state_before_sha256']==result['state_after_sha256'],'EEGNet read-only inference differs')
            pred = result['predictions']
            check([r['trial_id'] for r in pred]==[r['trial_id'] for r in queries],'EEGNet/frozen trial order differs')
            check(len({r['trial_id'] for r in pred})==len(queries),'EEGNet duplicate query')
            validate_exact_query_join(pred,query_map,'y_true')
            for row in pred:
                frozen = query_map[row['trial_id']]
                check(row['subject']==subject and row['seed']==job['seed'] and row['session']==frozen['session']
                      and row['run']==frozen['run'] and row['role']==frozen['role']
                      and row['y_true']==int(frozen['label']=='right_hand')
                      and row['y_pred']==int(row['logit_1']>row['logit_0']),'EEGNet exact identity/label/fixed argmax differs')
            eeg_predictions_count += len(pred)
            for session in SESSIONS:
                selected = [r for r in pred if r['session']==session]
                measured = scores([r['y_true'] for r in selected],[r['y_pred'] for r in selected])
                saved = [r for r in result['session_metrics'] if r['session']==session]
                check(len(saved)==1 and saved[0]['balanced_accuracy']==measured['BA']
                      and saved[0]['confusion_matrix']==measured['matrix'] and saved[0]['class_collapse']==measured['collapse'],'EEGNet saved session arithmetic differs')
                seeded[session].append(measured['BA'])
                seeded_collapses[session]+=int(measured['collapse'])
                per_seed.append({'subject':subject,'cohort':cohort,'seed':job['seed'],'session':session,
                    'balanced_accuracy':measured['BA'],'n_query_trials':len(selected),'class_collapse':measured['collapse']})
                eeg_collapsed += int(measured['collapse'])
        for session in SESSIONS:
            sessions.append({'subject':subject,'cohort':cohort,'method':'always_frozen_eegnet','session':session,
                'n_unique_query_trials':sum(r['session']==session for r in queries),'balanced_accuracy':float(np.mean(seeded[session])),
                'seeds_included':3,'class_collapsed_seed_sessions':seeded_collapses[session],
                'source_train_labels':40,'validation_labels_used_for_checkpoint_selection':20,'target_support_labels':0})
        budgets.append({'subject':subject,'source_train':40,'source_validation':20,
                        'included_current_support_by_session':{s:len(ids) for s,ids in support.items()},
                        'CPU_actual_fit_events':len(fit_audit),'CPU_validation_selection':False,
                        'EEGNet_validation_checkpoint_selection':True,'EEGNet_target_support_access':0})
        join_receipts.append({'subject':subject,'included_query_trials':len(queries),
            'excluded_query_trials':sum(r['subject']==subject for r in excluded),'CPU_methods':3,'EEGNet_seeds':3,
            'query_ids_labels_roles_sessions_runs_exactly_equal':True,'CPU_metadata_exclusions_numeric_hashes_match_frozen_split':True})
    check(cpu_predictions_count==eeg_predictions_count==12870,'Complete joined prediction count differs')
    endpoints=[]
    for subject in SUBJECTS:
        for method in METHODS:
            chosen = [r for r in sessions if r['subject']==subject and r['method']==method]
            check(len(chosen)==6 and {r['session'] for r in chosen}==set(SESSIONS),'Missing final participant sessions')
            source = next(r for r in chosen if r['session']=='ses-0')
            target = [r for r in chosen if r['session']!='ses-0']
            endpoints.append({'subject':subject,'cohort':'development' if subject in DEV else 'final_test','method':method,
                'source_query_BA':source['balanced_accuracy'],'target_five_session_mean_BA':float(np.mean([r['balanced_accuracy'] for r in target])),
                'source_query_trials':source['n_unique_query_trials'],'target_query_trials':sum(r['n_unique_query_trials'] for r in target),
                'target_class_collapsed_seed_sessions':sum(r['class_collapsed_seed_sessions'] for r in target),
                'source_class_collapsed_seed_sessions':source['class_collapsed_seed_sessions'],'seeds_included':source['seeds_included']})
    groups={'development6':DEV,'remaining12':TEST,'all18_secondary_exploratory':SUBJECTS}
    summary_rows,descriptive_differences,participant_differences,primary_checks=[],[],[],[]
    old_names={'development6':'development','remaining12':'final_test','all18_secondary_exploratory':'all_published_ids_descriptive'}
    for group,subjects in groups.items():
        selected={method:{r['subject']:r for r in endpoints if r['method']==method and r['subject'] in subjects} for method in METHODS}
        for method in METHODS:
            for endpoint in ('source_query_BA','target_five_session_mean_BA'):
                value=bootstrap({s:r[endpoint] for s,r in selected[method].items()})
                summary_rows.append({'cohort':group,'n_participants':len(subjects),'method':method,'endpoint':endpoint,
                    'mean_BA':value['mean'],'median_BA':value['median'],'descriptive_ci95_low':value['ci95'][0],
                    'descriptive_ci95_high':value['ci95'][1],'bootstrap_replicates':10000,'bootstrap_seed':42,
                    'inference':'descriptive participant uncertainty; no new significance test'})
        ordered=sorted(subjects)
        cpu_values=np.asarray([[selected[m][s]['target_five_session_mean_BA'] for m in CPUMETHODS] for s in ordered])
        rng=np.random.default_rng(42)
        indices=rng.integers(0,len(ordered),size=(10000,len(ordered)))
        means=cpu_values[indices].mean(axis=1)
        preserved=old_summary['cohorts'][old_names[group]]
        for i,method in enumerate(CPUMETHODS):
            prior=preserved['methods'][method]
            check(np.allclose(cpu_values[:,i],prior['participant_values'],rtol=0,atol=1e-14)
                  and abs(float(cpu_values[:,i].mean())-prior['mean_balanced_accuracy'])<1e-14
                  and np.allclose(np.quantile(means[:,i],[.025,.975]),prior['ci95'],rtol=0,atol=1e-14),'Historical CPU endpoint/bootstrap changed')
        difference=cpu_values[:,2]-cpu_values[:,0]
        ci=np.quantile(means[:,2]-means[:,0],[.025,.975]).tolist()
        prior=preserved['paired_comparisons']['refit_csp_lda_minus_source_only']
        check(abs(float(difference.mean())-prior['mean_difference'])<1e-14
              and np.allclose(ci,prior['ci95'],rtol=0,atol=1e-14)
              and np.allclose(difference,prior['participant_differences'],rtol=0,atol=1e-14),'Frozen CPU primary contrast changed')
        primary_checks.append({'cohort':group,'original_primary_cohort':group=='remaining12',
            'contrast':'refit_csp_lda_minus_source_only','mean_difference':float(difference.mean()),'ci95':ci,
            'participant_differences':difference.tolist(),'subjects':ordered,'matches_saved_frozen_CPU_summary':True})
        for cpu_method in CPUMETHODS:
            for endpoint in ('source_query_BA','target_five_session_mean_BA'):
                differences=[selected['always_frozen_eegnet'][s][endpoint]-selected[cpu_method][s][endpoint] for s in ordered]
                descriptive_differences.append({'cohort':group,'n_participants':len(ordered),'contrast':'always_frozen_eegnet_minus_'+cpu_method,
                    'endpoint':endpoint,'mean_paired_difference':float(np.mean(differences)),'median_paired_difference':float(np.median(differences)),
                    'participants_positive':sum(x>0 for x in differences),'participants_zero':sum(x==0 for x in differences),
                    'participants_negative':sum(x<0 for x in differences),'CI_or_p_value':'not computed; additional descriptive contrast only',
                    'budget_comparability':'not a matched-label-and-compute-budget comparison'})
                if group=='all18_secondary_exploratory':
                    participant_differences.extend({'subject':s,'contrast':'always_frozen_eegnet_minus_'+cpu_method,
                        'endpoint':endpoint,'paired_difference':d} for s,d in zip(ordered,differences,strict=True))
    # Existing EEGNet target/source output is independently recovered from the join.
    for group,subjects in groups.items():
        for name,key in [('target_query','target_five_session_mean_BA'),('source_query_secondary','source_query_BA')]:
            values={r['subject']:r[key] for r in endpoints if r['method']=='always_frozen_eegnet' and r['subject'] in subjects}
            check(values==aggregate['cohorts'][group][name]['participant_values'],'EEGNet prior participant endpoints differ')
    check(all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==r['sha256'] for p,r in INPUTS.items()),'Original saved evidence changed during comparison')
    write_csv('per_subject_session.csv',sessions)
    write_csv('eegnet_per_seed_session.csv',per_seed)
    write_csv('per_participant_endpoints.csv',endpoints)
    write_csv('cohort_method_endpoint_summary.csv',summary_rows)
    write_csv('descriptive_eegnet_minus_cpu.csv',descriptive_differences)
    write_csv('per_participant_descriptive_differences.csv',participant_differences)
    report={'schema_version':1,'status':'saved_results_exact_query_join_and_descriptive_comparison_complete',
        'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks_completed':CHECKS,
        'query_identity_scope':{'recorded_query_events':4320,'included_unique_queries':4290,'excluded_partial_queries':30,
            'CPU_prediction_rows_three_methods':cpu_predictions_count,'EEGNet_prediction_rows_three_seeds':eeg_predictions_count,
            'source_query_unique':sum(r['role']=='source_query' for r in included),'target_query_unique':sum(r['role']=='target_query' for r in included),
            'exact_trial_label_role_session_run_join':True,'metadata_raw_processed_hashes_and_original_exclusions_verified':True,
            'exclusions_revised':False,'join_dropped_rows':0,'participants':18},
        'query_excluded_trial_ids':[r['trial_id'] for r in excluded],'per_subject_join':join_receipts,
        'budget_interpretation':{
            'CPU_source_only':'40 source TRAIN labels fit CSP and LDA; 20 source validation labels reported only, never selected/refitted; target support0.',
            'CPU_frozen_CSP_LDA_recalibration':'CSP remains source40; LDA fits source40 plus current target19/20 labels, no past/future support accumulation.',
            'CPU_refit_CSP_LDA':'Both CSP and LDA fit source40 plus current target19/20 labels, no past/future support accumulation.',
            'EEGNet_always_frozen':'40 source TRAIN labels fit parameters/normalization; separate20 source validation labels select checkpoint epoch; three fixed seeds; target support0.',
            'same_budget_ranking_supported':False,'source_query_CPU_methods_share_same_source_model':True,
            'per_participant':budgets},
        'retained_class_collapse':{'CPU_method_session_records':cpu_collapsed,'EEGNet_seed_session_records':eeg_collapsed,
                                  'denominators_not_equivalent':'CPU324 method/sessions, EEGNet324 seed/sessions; no removal'},
        'cohort_method_endpoint_summary':summary_rows,'descriptive_EEGNet_minus_CPU':descriptive_differences,
        'preserved_original_CPU_primary_contrast':primary_checks,
        'statistics_policy':{'independent_unit':'published participant identity','EEGNet_seeds':'all three equally averaged within participant/session',
            'target_sessions':'all five equally averaged within participant','source_query':'separate secondary',
            'bootstrap':'existing percentile95 participant resampling,10000,seed42,lexicographic subject order',
            'new_EEGNet_contrasts':'descriptive differences only; no new CI,p-value,hypothesis or selected winner',
            'original_CPU_primary':'refit_csp_lda minus source_only on remaining12 target-query participant means; preserved exactly'},
        'limitations':['Same query trials do not imply matched information or compute budgets; EEGNet uses source validation for epoch selection, while CPU fixed methods do not.',
            'Adaptive CPU baselines additionally access current target support labels, unlike always-frozen EEGNet.',
            'Later comparisons on the already exposed cohort are exploratory; all18 is secondary and does not replace the fixed12 primary CPU contrast.',
            'This comparison cannot attribute architecture superiority, validate a new gate, demonstrate human skill retention or establish clinical efficacy.'],
        'execution':{'raw_EEG_reads':0,'checkpoint_tensor_loads':0,'model_forward_passes':0,'fits':0,'new_strategy_or_thresholds':0,'new_significance_tests':0},
        'inputs_unchanged_after_readback':True,'inputs':[{'path':p,**r} for p,r in sorted(INPUTS.items())],
        'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.csv')}}
    with (OUT/'comparison_receipt.json').open('x') as handle:
        json.dump(report,handle,indent=2,allow_nan=False);handle.write('\n')
    print(json.dumps({'status':report['status'],'checks':CHECKS,'collapsed':report['retained_class_collapse'],
                      'summary':summary_rows,'primary_remaining12':primary_checks[1]},indent=2))


if __name__=='__main__':
    main()
