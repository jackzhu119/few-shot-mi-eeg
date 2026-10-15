from pathlib import Path
import re,csv,json,hashlib,datetime
old=Path('manuscript/kumar_supplementary_methods_20261015.md').read_text()
new_path=Path('manuscript/kumar_plos_one_supporting_methods_20261015.md');new=new_path.read_text()
main_path=Path('manuscript/kumar_plos_one_submission_draft_20261015.md');main=main_path.read_text()
checks=[]
def ck(cond,label):
 checks.append({'check':label,'passed':bool(cond)})
 if not cond: raise ValueError(label)
old_science=old.split('## S7.')[0]
new_science=new.split('## S7.')[0]
old_code=re.findall(r'`[^`]+`',old_science)
new_code=re.findall(r'`[^`]+`',new_science)
ck([t for t in old_code if t!='`children`']==new_code,'All original S1-S6 scientific inline code/formulas preserved exactly; procfs token relocated to original audit only')
ck(new.startswith('# S1 Text.'),'PLOS S1 Text label')
ck(all(f'## S{i}.' in new for i in range(1,11)),'Ten scientific-method sections present')
ck('## S7. Recorded software, immutable identities' not in new,'Old engineering tables excluded')
ck('R2' not in new and 'parent acceptance' not in new and 'launcher' not in new,'No operational authority or storage logs in supplement')
ck('not 44 verified early' in new,'44 partials not called 44 early trial ends')
ck('1.5.0dev0' in new,'Exact MOABB recorded version preserved')
ck('2.5th/97.5th' in new,'Percentile notation retained')
rows=list(csv.DictReader(open('research_logs/kumar_submission_training_review_20261015/run01/results/cohort_training_review.csv')))
allrow=next(r for r in rows if r['cohort']=='all18_secondary');rem=next(r for r in rows if r['cohort']=='remaining12')
for field,want in [('epochs',2871),('optimizer_steps',8613),('selected_epoch1_fits',12),('reached_epoch100_fits',11),('train_CE_last_lower_than_first_fits',53),('validation_CE_last_higher_than_first_fits',29)]:
 ck(int(allrow[field])==want,'all54 saved table '+field)
for field,want in [('selected_epoch1_fits',8),('reached_epoch100_fits',10),('train_CE_last_lower_than_first_fits',35),('validation_CE_last_higher_than_first_fits',19)]:
 ck(int(rem[field])==want,'remaining36 saved table '+field)
for field in ['median_train_CE_first','median_train_CE_last','median_validation_CE_first','median_validation_CE_selected','median_validation_CE_last']:
 token=f'{float(rem[field]):.6f}'
 ck(token in new and token in main,'Main and S1 Text exact training median '+token)
for token in ['2,871','8,613','53/54','29/54','52.42','49.94','52.37','8.06','24.62']:
 ck(token in new and token in main,'Main and S1 Text saved count/seed summary '+token)
for token in ['source-query BA\nwas 52.92','51.58%']:
 ck(token in main,'Main weak source before transfer '+token)
for token in ['@kumar2024','@kumar2024correction','@kumarcodebook']:
 ck(token in new,'Scientific reference '+token)
for p in ['scripts/analyze_kumar_saved_query_qc_20261015.py','scripts/summarize_kumar_saved_training_curves.py','research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md','research_logs/kumar_submission_qc_20261015/run01/public_inputs','research_logs/kumar_submission_training_review_20261015/run01/archive_input_index.json']:
 ck(Path(p).exists(),'Reproduction path exists '+p)
matched=list(csv.DictReader(open('research_logs/kumar_submission_qc_20261015/run01/participant_cross_subset_changes.csv')))
for contrast,first,second in [('refit_minus_frozen',6.50,5.96),('refit_minus_lda_only',4.53,3.82)]:
 r=[x for x in matched if x['cohort']=='remaining12' and x['contrast']==contrast and x['paired_across_subsets_defined']=='True']
 ck(len(r)==10,'same10 membership '+contrast)
 ck(round(100*sum(float(x['all_included_difference']) for x in r)/10,2)==first and round(100*sum(float(x['unflagged_difference']) for x in r)/10,2)==second,'same10 reported means '+contrast)
p=Path('research_logs/kumar_submission_training_review_20261015/run01/supporting_methods_draft_validation.json')
p.write_text(json.dumps({'status':'supporting_scientific_methods_draft_checked','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':len(checks),'failures':0,'new_supplement':{'path':str(new_path),'bytes':new_path.stat().st_size,'sha256':hashlib.sha256(new_path.read_bytes()).hexdigest()},'old_supplement_sha256':hashlib.sha256(old.encode()).hexdigest(),'main_draft_sha256_at_check':hashlib.sha256(main.encode()).hexdigest(),'scope':'Preserved scientific formulas, saved training counts/medians/seeds, explicit QC class eligibility and same10 means; no science execution or document render','details':checks},indent=2)+'\n')
print('checks',len(checks),'failures',0,'bytes',new_path.stat().st_size,'sha256',hashlib.sha256(new_path.read_bytes()).hexdigest())
