"""Describe saved anchoring weights; no model, signal or prediction forward."""
from pathlib import Path
import argparse,collections,csv,json,statistics

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('packet',type=Path)
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
a=parser.parse_args();root=a.packet.resolve();out=a.output;out.mkdir(parents=True,exist_ok=True)
methods=('anchored_csp','empirical_anchored_csp','ea_anchored_csp','ea_empirical_anchored_csp')
rows=[];meta={}
for p in sorted((root/'training_records/results/tasks').glob('*-classical/models/*.npz.json')):
 m=json.loads(p.read_text())['metadata'];method=m['method']
 if method not in methods:continue
 stem=p.name.removesuffix('.npz.json');session,budget_text,_=stem.split('__',2);budget=int(budget_text.removeprefix('n'));participant=p.parents[1].name.removeprefix('kumar-v2-').removesuffix('-classical')
 n=m['n_support_actual'];tau=m['settings']['anchor_tau'];assert len(m['support_trial_ids'])==n
 assert m['query_used_for_fitting'] is False
 expected=n/(n+tau)
 meta[(participant,session,budget,method)]=m
 for cls,alpha in m['classwise_update_weights'].items():
  assert 0<=alpha<=1
  if method in ('anchored_csp','ea_anchored_csp'):assert alpha==0 or alpha==expected
  rows.append({'participant':participant,'session':session,'budget':budget,'actual_support':n,'method':method,'class':cls,'target_weight':alpha,'fixed_total_n_weight':expected,'zero':alpha==0,'ea_reference_scope':m['ea_reference_scope']})
assert len(rows)==1200,len(rows)
# Fixed-tau weights identify missing classes because their implementation only
# assigns zero when the corresponding support class is absent. Empirical zeros
# have additional possible causes and are not interpreted as missing classes.
for r in rows:
 if 'empirical' in r['method']:
  control='ea_anchored_csp' if r['method'].startswith('ea_') else 'anchored_csp'
  r['missing_support_class_identified_by_fixed_control']=meta[(r['participant'],r['session'],r['budget'],control)]['classwise_update_weights'][r['class']]==0
 else:r['missing_support_class_identified_by_fixed_control']=r['zero']
for r in rows:
 if r['missing_support_class_identified_by_fixed_control']:assert r['zero']

def write_csv(name,records):
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
write_csv('classwise_weights.csv',rows)
summary=[]
for budget in (4,8,12,16,20):
 for method in methods:
  selected=[r for r in rows if r['budget']==budget and r['method']==method];groups=collections.defaultdict(list)
  for r in selected:groups[r['participant']].append(r['target_weight'])
  participant_means={p:statistics.mean(v) for p,v in sorted(groups.items())}
  weights=[r['target_weight'] for r in selected]
  summary.append({'budget':budget,'method':method,'independent_participants':len(groups),'class_weights':len(weights),'participant_balanced_mean':statistics.mean(participant_means.values()),'class_weight_median':statistics.median(weights),'class_weight_min':min(weights),'class_weight_max':max(weights),'zero_count':sum(r['zero'] for r in selected),'missing_class_count_identified_by_fixed_control':sum(r['missing_support_class_identified_by_fixed_control'] for r in selected),'participant_mean_min':min(participant_means.values()),'participant_mean_max':max(participant_means.values())})
write_csv('weight_budget_summary.csv',summary)
# Match actual update weights to already computed method BA on the exact same
# participant/session query. This is descriptive and fits/selects no strategy.
session_rows=list(csv.DictReader((root/'analysis/session_metrics.csv').open()))
performance={(r['participant'],r['session'],int(r['budget']),r['method']):float(r['balanced_accuracy']) for r in session_rows if r['family']=='classical'}
paired=[]
for participant,session,budget,method in sorted(meta):
 if method!='ea_empirical_anchored_csp':continue
 model=meta[(participant,session,budget,method)]
 alpha=statistics.mean(model['classwise_update_weights'].values())
 fixed=meta[(participant,session,budget,'ea_anchored_csp')]
 pa=performance[(participant,session,budget,method)];ea=performance[(participant,session,budget,'ea_csp')];fx=performance[(participant,session,budget,'ea_anchored_csp')]
 paired.append({'participant':participant,'session':session,'budget':budget,'actual_support':model['n_support_actual'],'mean_class_target_weight':alpha,'fixed_control_mean_class_weight':statistics.mean(fixed['classwise_update_weights'].values()),'candidate_ba':pa,'ea_ba':ea,'fixed_control_ba':fx,'candidate_minus_ea_pp':100*(pa-ea),'candidate_minus_fixed_pp':100*(pa-fx)})
write_csv('candidate_weight_and_saved_gain.csv',paired)
pgroups=collections.defaultdict(list)
for r in paired:pgroups[(r['participant'],r['budget'])].append(r)
participant_rows=[]
for (participant,budget),group in sorted(pgroups.items()):
 participant_rows.append({'participant':participant,'budget':budget,'target_sessions':len(group),**{k:statistics.mean(x[k] for x in group) for k in ('mean_class_target_weight','fixed_control_mean_class_weight','candidate_ba','ea_ba','fixed_control_ba','candidate_minus_ea_pp','candidate_minus_fixed_pp')}})
write_csv('participant_weight_and_saved_gain.csv',participant_rows)
examples=[]
for r in rows:
 if r['method']=='ea_empirical_anchored_csp' and r['zero'] and len(examples)<8:examples.append(r)
receipt={'scope':'Saved classical metadata and saved session BA; no EEG/model/fit/forward','weight_records':len(rows),'anchored_models':len(meta),'independent_participants':sorted({r['participant'] for r in rows}),'budget_summary':summary,'candidate_zero_examples':examples,'candidate_model_count':len(paired),'actual_support_counts':dict(collections.Counter(r['actual_support'] for r in paired)),'limitations':['Classwise support-label counts, variance-of-mean values, and squared source-target distance were not exported. Empirical zero weights cannot be disambiguated into n<2, variance>=distance, or nonpositive-distance conditions.','The fixed-control zero identifies an absent class under the frozen producer implementation. No n=1 fallback count is available.','Class weights/session cells are repeated within six participants; distributional counts are descriptive, not independent inference.','Support-only EA estimates query whitener from current support alone; query information is not used in these recorded fits.','The rule subtracts target-mean sampling variance divided by source-target squared difference; it does not account for finite-source uncertainty or prove negative-transfer protection.']}
(out/'mechanism_summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
