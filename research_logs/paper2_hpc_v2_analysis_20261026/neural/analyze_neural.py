"""Read saved neural metrics and text histories only; no models/EEG/inference."""
from pathlib import Path
import argparse, collections, csv, hashlib, json, statistics
import numpy as np

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('packet',type=Path)
parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
a=parser.parse_args();root=a.packet.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
summary=json.loads((root/'analysis/summary.json').read_text());tasks=sorted(p for p in (root/'results/tasks').glob('*seed*') if p.is_dir())
assert len(tasks)==18

def csvwrite(name,rows):
    if not rows:return
    with (out/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def stats(values):
    x=np.asarray(values,float)
    return {'mean':float(x.mean()),'median':float(np.median(x)),'minimum':float(x.min()),'maximum':float(x.max()),'q25':float(np.quantile(x,.25)),'q75':float(np.quantile(x,.75))}

source=[];history_rows=[];target=[];adapt=[];inputs=[]
for task in tasks:
    q=json.loads((task/'source_query.json').read_text());path=root/'training_records/results/tasks'/task.name/'source/checkpoint.pt.json';v=json.loads(path.read_text());inputs.append(path)
    h=v['history'];assert len(h)==100 and v['complete'] and v['epoch']==100
    best=min(h,key=lambda x:x['validation_loss']);assert best['epoch']==v['best_epoch'] and best['validation_loss']==v['best_loss']
    row={'participant':q['participant'],'seed':q['seed'],'best_epoch':v['best_epoch'],'first_train_ce':h[0]['train_loss'],'best_epoch_train_ce':h[v['best_epoch']-1]['train_loss'],'final_train_ce':h[-1]['train_loss'],'first_validation_ce':h[0]['validation_loss'],'best_validation_ce':v['best_loss'],'final_validation_ce':h[-1]['validation_loss'],'best_to_final_validation_increase':h[-1]['validation_loss']-v['best_loss'],'final_validation_minus_train':h[-1]['validation_loss']-h[-1]['train_loss'],'source_query_ba':q['balanced_accuracy'],'source_query_collapse':int(q['collapse']),'source_epochs':v['epoch'],'source_steps':v['step']}
    source.append(row)
    for x in h:history_rows.append({'participant':q['participant'],'seed':q['seed'],**x})
    for p in sorted((task/'evaluation').rglob('metrics.json')):
        x=json.loads(p.read_text());inputs.append(p)
        target.append({'participant':x['participant'],'seed':x['seed'],'session':x['session'],'method':x['method'],'budget':x['requested_budget'],'actual_budget':x['actual_budget'],'ba':x['balanced_accuracy'],'collapse':int(x['collapse']),'n_query':x['n_query'],'model_state_sha256':x['model_state_sha256'],'prediction_class_counts':json.dumps(x['prediction_class_counts'])})
    for p in sorted((root/'training_records/results/tasks'/task.name/'adaptation').rglob('checkpoint.pt.json')):
        x=json.loads(p.read_text());parts=p.relative_to(root/'training_records/results/tasks'/task.name/'adaptation').parts
        assert x['complete'] and x['epoch']==20 and len(x['history'])==20
        adapt.append({'participant':q['participant'],'seed':q['seed'],'session':parts[0],'method':parts[1],'budget':int(parts[2].split('-')[1]),'first_train_ce':x['history'][0]['train_loss'],'final_train_ce':x['history'][-1]['train_loss'],'epochs':x['epoch'],'steps':x['step']})
assert len(target)==1800 and len(adapt)==1350
csvwrite('source_models.csv',source);csvwrite('source_epoch_seed_history.csv',history_rows);csvwrite('target_neural_cells.csv',target);csvwrite('adaptation_training_records.csv',adapt)
# Each participant is retained; source training curves first average the 3 fixed seeds.
curves=[]
for p in sorted({x['participant'] for x in source}):
    for epoch in range(1,101):
        h=[x for x in history_rows if x['participant']==p and x['epoch']==epoch];assert len(h)==3
        curves.append({'participant':p,'epoch':epoch,'mean_train_ce':float(np.mean([x['train_loss'] for x in h])),'mean_validation_ce':float(np.mean([x['validation_loss'] for x in h]))})
csvwrite('source_epoch_participant_means.csv',curves)
# Descriptive collapse rates; one method/budget cell per participant averages exactly 3x5 evaluations.
collapse=[];participant_rates=[];seed_means=[]
for method in ('frozen','head','full','l2sp'):
    for budget in (4,8,12,16,20):
        cells=[x for x in target if x['method']==method and x['budget']==budget];assert len(cells)==90
        rates=[]
        for p in sorted({x['participant'] for x in source}):
            z=[x for x in cells if x['participant']==p];assert len(z)==15
            rates.append(sum(x['collapse'] for x in z)/len(z))
            participant_rates.append({'participant':p,'method':method,'budget':budget,'collapsed_seed_session_evaluations':sum(x['collapse'] for x in z),'seed_session_evaluations':15,'collapse_rate':rates[-1],'mean_ba':float(np.mean([x['ba'] for x in z]))})
        collapse.append({'method':method,'budget':budget,'collapsed_seed_session_evaluations':sum(x['collapse'] for x in cells),'seed_session_evaluations':90,'mean_participant_collapse_rate':float(np.mean(rates)),'participants_with_any_collapse':sum(r>0 for r in rates),'participants_with_all_collapsed':sum(r==1 for r in rates)})
        for seed in sorted({x['seed'] for x in cells}):
            z=[x for x in cells if x['seed']==seed];assert len(z)==30
            seed_means.append({'method':method,'budget':budget,'seed':seed,'cohort_mean_ba':float(np.mean([x['ba'] for x in z]))})
csvwrite('collapse_by_method_budget.csv',collapse);csvwrite('collapse_participant_method_budget.csv',participant_rates);csvwrite('seed_cohort_means.csv',seed_means)
participant=[]
for p in sorted({x['participant'] for x in source}):
    z=[x for x in source if x['participant']==p]
    row={'participant':p,'source_query_mean_ba':float(np.mean([x['source_query_ba'] for x in z])),'source_query_collapsed_seeds':sum(x['source_query_collapse'] for x in z),'best_epochs':','.join(str(x['best_epoch']) for x in sorted(z,key=lambda x:x['seed']))}
    for method in ('frozen','head','full','l2sp'):
        t=[x for x in target if x['participant']==p and x['method']==method and x['budget']==20]
        row[method+'_target_ba']=float(np.mean([x['ba'] for x in t]));row[method+'_collapse_rate']=sum(x['collapse'] for x in t)/len(t)
    participant.append(row)
csvwrite('neural_participant_budget20.csv',participant)
# Five frozen budget copies are not five independent evaluations.
fgroups=collections.defaultdict(list)
for x in target:
    if x['method']=='frozen':fgroups[(x['participant'],x['seed'],x['session'])].append(x)
assert len(fgroups)==90
assert all(len(v)==5 and len({(x['ba'],x['collapse'],x['model_state_sha256']) for x in v})==1 for v in fgroups.values())
# Preserve every fixed seed; no best-seed selection.
seed_participants=[];seed_spread=[]
for method in ('frozen','head','full','l2sp'):
    for budget in (4,8,12,16,20):
        for p in sorted({x['participant'] for x in source}):
            values=[]
            for seed in sorted({x['seed'] for x in source}):
                z=[x for x in target if x['participant']==p and x['seed']==seed and x['method']==method and x['budget']==budget];assert len(z)==5
                mean=float(np.mean([x['ba'] for x in z]));values.append(mean)
                seed_participants.append({'participant':p,'method':method,'budget':budget,'seed':seed,'five_session_mean_ba':mean})
            seed_spread.append({'participant':p,'method':method,'budget':budget,'mean_ba':float(np.mean(values)),'sample_sd_across_three_seeds':statistics.stdev(values),'minimum_seed_ba':min(values),'maximum_seed_ba':max(values)})
csvwrite('participant_seed_target.csv',seed_participants);csvwrite('participant_seed_spread.csv',seed_spread)
probability_rows=[]
for budget in (4,8,12,16,20):
    ds=[];obs=flip=anyflip=states=cells=0
    for p in (root/'results/tasks').glob(f'*seed*/evaluation/*/full/budget-{budget}/predictions.npz'):
        q=Path(str(p).replace('/full/','/l2sp/'));fm=json.loads(p.with_name('metrics.json').read_text());lm=json.loads(q.with_name('metrics.json').read_text())
        with np.load(p,allow_pickle=False) as f,np.load(q,allow_pickle=False) as l:
            assert np.array_equal(f['trial_id'],l['trial_id']) and np.array_equal(f['labels'],l['labels']) and np.array_equal(f['classes'],l['classes'])
            ds.append(np.abs(f['probabilities']-l['probabilities']).ravel());n=int(np.sum(np.argmax(f['probabilities'],axis=1)!=np.argmax(l['probabilities'],axis=1)));flip+=n;anyflip+=n>0;obs+=len(f['labels']);cells+=1;states+=fm['model_state_sha256']!=lm['model_state_sha256']
    v=np.concatenate(ds);probability_rows.append({'budget':budget,'paired_cells':cells,'cells_with_distinct_recorded_model_hashes':states,'cells_with_prediction_label_difference':anyflip,'total_paired_query_rows':obs,'changed_label_rows':flip,'maximum_probability_difference':float(v.max()),'mean_absolute_probability_difference':float(v.mean())})
csvwrite('full_l2sp_probability_differences.csv',probability_rows)
# Full vs L2-SP is a descriptive saved-output contrast; neither selects the rule.
full={(x['participant'],x['seed'],x['session'],x['budget']):x for x in target if x['method']=='full'}
l2sp=[x for x in target if x['method']=='l2sp']
l2_differences=[x['ba']-full[(x['participant'],x['seed'],x['session'],x['budget'])]['ba'] for x in l2sp]
report={'scope':'saved neural predictions/metrics and text checkpoint histories; all fixed seeds; no training/model/inference/query selection',
 'independent_participants':6,'source_models':18,'source_epochs_total':sum(x['source_epochs'] for x in source),'source_steps_total':sum(x['source_steps'] for x in source),'adaptation_stages':len(adapt),'adaptation_epochs_total':sum(x['epochs'] for x in adapt),'adaptation_steps_total':sum(x['steps'] for x in adapt),
 'source_best_epoch':stats([x['best_epoch'] for x in source]),'source_best_epoch_frequency':dict(sorted(collections.Counter(x['best_epoch'] for x in source).items())),
 'source_first_train_ce':stats([x['first_train_ce'] for x in source]),'source_final_train_ce':stats([x['final_train_ce'] for x in source]),'source_best_validation_ce':stats([x['best_validation_ce'] for x in source]),'source_final_validation_ce':stats([x['final_validation_ce'] for x in source]),'source_final_generalization_gap':stats([x['final_validation_minus_train'] for x in source]),
 'source_training_loss_decreased_models':sum(x['final_train_ce']<x['first_train_ce'] for x in source),'source_validation_final_above_best_models':sum(x['final_validation_ce']>x['best_validation_ce'] for x in source),'source_query_collapsed_models':sum(x['source_query_collapse'] for x in source),
 'source_query_cohort_ba':float(np.mean([x['source_query_mean_ba'] for x in participant])),
 'collapse_by_method_budget':collapse,'neural_participant_budget20':participant,
 'budget20_existing_comparisons':[x for x in summary['comparisons'] if x['family']=='eegnet' and x['budget']==20],
 'budget20_existing_cohorts':[x for x in summary['cohorts'] if x['family']=='eegnet' and x['budget']==20],
 'seed_variation_budget20':[{'method':m,'values':[x for x in seed_means if x['method']==m and x['budget']==20],'cohort_ba_sample_sd':statistics.stdev([x['cohort_mean_ba'] for x in seed_means if x['method']==m and x['budget']==20])} for m in ('frozen','head','full','l2sp')],
 'source_query_seed_cohort_means':[{'seed':s,'cohort_mean_ba':float(np.mean([x['source_query_ba'] for x in source if x['seed']==s]))} for s in sorted({x['seed'] for x in source})],
 'frozen_budget_copy_invariance_verified':True,'unique_frozen_target_model_session_evaluations':90,
 'full_l2sp_cell_ba_differences':{'equal_ba_cells':sum(x==0 for x in l2_differences),'cells':len(l2_differences),'all_budget_difference_stats':stats(l2_differences)},
 'full_l2sp_saved_probability_comparison':probability_rows,
 'as_implemented_mode_policy':{'head':'model.train then model.features.eval: feature BN/dropout frozen','full_l2sp':'model.train: feature BN/dropout training mode; BN running buffers may update','l2sp_scope':'named parameters only; BN running-stat buffers excluded','interpretation':'Head vsfull mixes parameter update scope and BN/dropout mode, so weight drift alone is not isolated'},
 'update_norm_available':False,'update_norm_note':'Whitelisted exported text checkpoint metadata omit parameter tensors and parameter-update norms; not reconstructed from outcomes.',
 'assumptions':'Each reported cohort mean averages all three seeds within participant/session and all five sessions within participant; collapse counts are descriptive repeated evaluation cells, not independent events. Previously exposed development participants imply exploratory conclusions.'}
(out/'neural_analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('collapse_by_method_budget','neural_participant_budget20','budget20_existing_comparisons','budget20_existing_cohorts')},indent=2))
