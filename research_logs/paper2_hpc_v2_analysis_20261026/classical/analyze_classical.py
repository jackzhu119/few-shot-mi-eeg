"""Descriptive analysis of saved V2 classical metrics; no model/data loading."""
from pathlib import Path
import argparse, csv, hashlib, json
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('packet_root',type=Path)
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
a=p.parse_args(); root=a.packet_root.resolve(); out=a.output.resolve(); out.mkdir(parents=True,exist_ok=True)
def read(name):
 with (root/'analysis'/name).open(newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary=json.loads((root/'analysis/summary.json').read_text())
participant=[r for r in read('participant_metrics.csv') if r['family']=='classical']
session=[r for r in read('session_metrics.csv') if r['family']=='classical']
people=sorted({r['participant'] for r in participant}); assert len(people)==6
methods=sorted({r['method'] for r in participant}); budgets=[4,8,12,16,20]
index={(r['participant'],r['method'],int(r['budget'])):float(r['balanced_accuracy']) for r in participant}
sindex={(r['participant'],r['session'],r['method'],int(r['budget'])):float(r['balanced_accuracy']) for r in session}
assert len(index)==6*8*5 and len(sindex)==6*5*8*5
cohorts=[r for r in summary['cohorts'] if r['family']=='classical']
write('classical_budget_curves.csv',[{'method':r['method'],'budget':r['budget'],'participants':r['complete_participants'],'mean_ba_percent':r['mean_balanced_accuracy']*100,'ci_low_percent':r['ci_low']*100,'ci_high_percent':r['ci_high']*100} for r in cohorts])
def interval(x):
 rng=np.random.default_rng(20261023); v=np.asarray(x); draws=rng.integers(0,len(v),size=(10000,len(v))); return np.quantile(v[draws].mean(axis=1),[.025,.975]).tolist()
contrasts=[('ea_empirical_anchored_csp','ea_csp','prespecified_primary_at_budget20'),('ea_empirical_anchored_csp','frozen','prespecified_secondary'),('ea_empirical_anchored_csp','full_csp','prespecified_secondary'),('ea_empirical_anchored_csp','ea_anchored_csp','prespecified_fixed_weight_ablation'),('ea_empirical_anchored_csp','empirical_anchored_csp','prespecified_alignment_ablation'),('ea_csp','full_csp','posthoc_descriptive'),('full_csp','lda_only','posthoc_descriptive'),('full_csp','frozen','protocol_secondary_additional_summary')]
allcontrasts=[]; individuals=[]; longitudinal=[]
for left,right,role in contrasts:
 for budget in budgets:
  vals=[100*(index[q,left,budget]-index[q,right,budget]) for q in people]
  lo,hi=interval(vals); loo=[float(np.mean([v for j,v in enumerate(vals) if j!=i])) for i in range(6)]
  row={'method':left,'reference':right,'budget':budget,'role':role if budget==20 else 'descriptive_budget_curve','n_participants':6,'mean_difference_pp':float(np.mean(vals)),'ci_low_pp':lo,'ci_high_pp':hi,'positive_participants':sum(v>0 for v in vals),'negative_participants':sum(v<0 for v in vals),'decline_at_least_5pp':sum(v<=-5 for v in vals),'min_participant_difference_pp':min(vals),'max_participant_difference_pp':max(vals),'leave_one_out_min_mean_pp':min(loo),'leave_one_out_max_mean_pp':max(loo)}
  allcontrasts.append(row)
  if role!='posthoc_descriptive' and (left,right) in [('ea_empirical_anchored_csp','ea_csp'),('ea_empirical_anchored_csp','frozen'),('ea_empirical_anchored_csp','full_csp'),('ea_empirical_anchored_csp','ea_anchored_csp'),('ea_empirical_anchored_csp','empirical_anchored_csp')]:
   fixed=next(r for r in summary['comparisons'] if r['family']=='classical' and r['method']==left and r['reference']==right and r['budget']==budget)
   assert np.allclose([row['mean_difference_pp'],lo,hi],[fixed['mean_difference_pp'],fixed['ci_low_pp'],fixed['ci_high_pp']],atol=1e-12,rtol=0)
  if budget==20:
   for person,value,leave in zip(people,vals,loo):individuals.append({'participant':person,'method':left,'reference':right,'difference_pp':value,'leave_this_participant_out_mean_pp':leave})
  for s in ['ses-1','ses-2','ses-3','ses-4','ses-5']:
   svals=[100*(sindex[q,s,left,budget]-sindex[q,s,right,budget]) for q in people]
   slo,shi=interval(svals)
   longitudinal.append({'session':s,'method':left,'reference':right,'budget':budget,'n_participants':6,'mean_difference_pp':float(np.mean(svals)),'ci_low_pp':slo,'ci_high_pp':shi,'negative_participants':sum(v<0 for v in svals),'decline_at_least_5pp':sum(v<=-5 for v in svals),'analysis_role':'posthoc_descriptive_session_slice'})
write('classical_contrasts.csv',allcontrasts); write('classical_individual_budget20.csv',individuals);write('classical_session_contrasts.csv',longitudinal)
wide=[{'participant':q,**{m:100*index[q,m,20] for m in methods}} for q in people];write('classical_individual_ba_budget20.csv',wide)
heat=[]
for q in people:
 for s in ['ses-1','ses-2','ses-3','ses-4','ses-5']:
  heat.append({'participant':q,'session':s,'candidate_vs_ea_pp':100*(sindex[q,s,'ea_empirical_anchored_csp',20]-sindex[q,s,'ea_csp',20]),'candidate_vs_frozen_pp':100*(sindex[q,s,'ea_empirical_anchored_csp',20]-sindex[q,s,'frozen',20])})
write('classical_participant_session_budget20.csv',heat)
record={'scope':'Saved metric postprocessing only, 6 previously exposed development participants; not independent validation','bootstrap':'10000 participant draws, seed20261023; pointwise exploratory intervals, no multiplicity correction','leave_one_out':'descriptive influence check; no policy/participant selection','inputs':[{'path':'analysis/'+name,'sha256':hashlib.sha256((root/'analysis'/name).read_bytes()).hexdigest()} for name in ['summary.json','participant_metrics.csv','session_metrics.csv']],'participants':people,'budget20_contrasts':[r for r in allcontrasts if r['budget']==20],'budget20_session_candidate_vs_ea':[r for r in longitudinal if r['budget']==20 and r['method']=='ea_empirical_anchored_csp' and r['reference']=='ea_csp'],'budget20_session_candidate_vs_frozen':[r for r in longitudinal if r['budget']==20 and r['method']=='ea_empirical_anchored_csp' and r['reference']=='frozen'],'budget20_individuals':wide,'budget20_candidate_ea_session_cells_declining':sum(r['candidate_vs_ea_pp']<0 for r in heat),'budget20_candidate_ea_session_cells_declining_5pp':sum(r['candidate_vs_ea_pp']<=-5 for r in heat),'budget20_candidate_frozen_session_cells_declining':sum(r['candidate_vs_frozen_pp']<0 for r in heat),'budget20_candidate_frozen_session_cells_declining_5pp':sum(r['candidate_vs_frozen_pp']<=-5 for r in heat)}
(out/'classical_analysis.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
