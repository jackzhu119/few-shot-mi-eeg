"""Independently check saved predictions/metrics; no EEG, model or forward pass."""
from pathlib import Path
import collections, hashlib, json, sys
import numpy as np

BASE=Path(__file__).resolve().parent
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else BASE/'paper2_results'
issues=[]
counts=collections.Counter()
query_groups={}
family_query_ids={}
max_ba_error=0.0
max_accuracy_error=0.0
rows=[]

def issue(path, check, detail):
    issues.append({'path':str(path.relative_to(ROOT)), 'check':check,'detail':str(detail)})

def need(condition, name):
    if not condition: raise ValueError(name)

def verify(path, record, labels, predictions, trial_ids, classes, run_ids=None):
    global max_ba_error,max_accuracy_error
    vals=record.get('metrics',record)
    labels=np.asarray(labels);predictions=np.asarray(predictions);trial_ids=np.asarray(trial_ids).astype(str);classes=np.asarray(classes)
    need(labels.ndim==predictions.ndim==trial_ids.ndim==1,'1D labels/predictions/trial IDs')
    need(len(labels)==len(predictions)==len(trial_ids)>0,'equal nonempty lengths')
    need(len(set(trial_ids))==len(trial_ids),'unique trial IDs within shard')
    need(len(classes)==2 and len(set(classes.tolist()))==2,'two distinct declared classes')
    need(set(labels.tolist())==set(classes.tolist()),'both true classes represented')
    need(set(predictions.tolist())<=set(classes.tolist()),'predictions use declared labels')
    n=len(labels); need(vals['n_query']==n,'recorded query count')
    true_counts=[int(np.sum(labels==c)) for c in classes]
    saved_counts=vals['class_counts'];saved_counts=[saved_counts[str(c)] for c in classes] if isinstance(saved_counts,dict) else saved_counts
    need(saved_counts==true_counts,'recorded true class counts')
    recalls=[float(np.mean(predictions[labels==c]==c)) for c in classes]
    ba=float(np.mean(recalls));error=abs(float(vals['balanced_accuracy'])-ba)
    max_ba_error=max(max_ba_error,error);need(error<=1e-12,'stored BA equals independent recomputation')
    if 'accuracy' in vals:
        err=abs(float(vals['accuracy'])-float(np.mean(labels==predictions)));max_accuracy_error=max(max_accuracy_error,err);need(err<=1e-12,'recorded accuracy')
    if 'prediction_class_counts' in vals:need(vals['prediction_class_counts']==[int(np.sum(predictions==c)) for c in classes],'recorded predicted counts')
    if 'collapse' in vals:need(vals['collapse']==(len(np.unique(predictions))==1),'recorded collapse')
    if 'recalls' in vals:need(np.allclose(vals['recalls'],recalls,atol=1e-12,rtol=0),'recorded recalls')
    if 'class_recall' in vals:need(np.allclose([vals['class_recall'][str(c)] for c in classes],recalls,atol=1e-12,rtol=0),'recorded class recalls')
    need(not record.get('synthetic',False) and not record.get('software_validation_only',False),'real data flags')
    if 'inference_state_unchanged' in record:need(record['inference_state_unchanged'] is True,'recorded unchanged inference state')
    if 'query_used_for_fitting' in record:need(record['query_used_for_fitting'] is False,'recorded query not fitted')
    if record['session']=='source' and 'selection_use' in record:need(record['selection_use'] is False,'source query selection flag false')
    group=(record['dataset'],record['participant'],record['session'])
    truth=tuple(zip(trial_ids.tolist(),labels.tolist()))
    if group in query_groups:
        need(query_groups[group]==truth,'same ordered trial IDs/labels across methods, budgets, seeds and families')
    else:query_groups[group]=truth
    family='classical' if 'classical' in record['task_id'] else 'eegnet'
    identity_group=group+(family,)
    need(bool(record.get('query_identity')),'nonempty query identity')
    if identity_group in family_query_ids:need(family_query_ids[identity_group]==record['query_identity'],'same saved query identity within family across seeds/methods/budgets')
    else:family_query_ids[identity_group]=record['query_identity']
    if run_ids is not None:need(np.asarray(run_ids).shape==labels.shape,'run ID length')
    rows.append({'path':str(path.relative_to(ROOT)),'family':family,'participant':record['participant'],'session':record['session'],'seed':record.get('seed'),'method':record['method'],'budget':record.get('requested_budget',record.get('budget_requested')),'n_query':n,'balanced_accuracy':ba,'absolute_error':error})
    counts[family+'_source' if record['session']=='source' else family+'_target']+=1
    counts['prediction_rows']+=n

for p in sorted((ROOT/'results/tasks').glob('*/evaluation/*.json')):
    try:
        r=json.loads(p.read_text());verify(p,r,r['y'],r['prediction'],r['trial_ids'],np.array([0,1]));counts['classical_shards']+=1
    except Exception as e:issue(p,'classical_prediction_metric_validation',e)
for p in sorted((ROOT/'results/tasks').rglob('predictions.npz')):
    try:
        r=json.loads(p.with_name('metrics.json').read_text())
        with np.load(p,allow_pickle=False) as z:
            need(set(z.files)=={'probabilities','labels','classes','trial_id','run_id'},'exact prediction schema')
            probabilities=z['probabilities'];labels=z['labels'];classes=z['classes'];ids=z['trial_id'];runs=z['run_id']
        need(probabilities.shape==(len(labels),len(classes)),'probability shape')
        need(np.isfinite(probabilities).all(),'finite probabilities')
        need(np.all((probabilities>=-1e-7)&(probabilities<=1+1e-7)),'probability range')
        need(np.allclose(probabilities.sum(axis=1),1,atol=1e-6,rtol=0),'normalized probabilities')
        predictions=classes[np.argmax(probabilities,axis=1)]
        verify(p,r,labels,predictions,ids,classes,runs);counts['neural_shards']+=1
        if p.parent.name=='source_query':
            parent=json.loads(p.parent.parent.joinpath('source_query.json').read_text())
            need(parent==r,'source_query.json equals canonical source-query metric file')
            counts['neural_source_duplicate_json_matched']+=1
    except Exception as e:issue(p,'neural_prediction_metric_validation',e)

expected={'classical_shards':1206,'neural_shards':1818,'classical_source':6,'classical_target':1200,'eegnet_source':18,'eegnet_target':1800,'neural_source_duplicate_json_matched':18}
for key,n in expected.items():
    if counts[key]!=n: issues.append({'check':'expected_shard_count','detail':key,'actual':counts[key],'expected':n})
receipt={'scope':'Saved predictions/labels and recorded metrics only; no model, EEG, fit or forward','packet_id':'f1689db3941ae31757442698','counts':dict(counts),'independent_participants':sorted({r['participant'] for r in rows}),'matched_participant_session_query_groups':len(query_groups),'matched_family_query_identity_groups':len(family_query_ids),'expected_counts':expected,'max_absolute_ba_difference':max_ba_error,'max_absolute_accuracy_difference':max_accuracy_error,'issues':issues,'all_checks_passed':not issues,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(BASE/'independent_predictions_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
(BASE/'independent_prediction_cells.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
