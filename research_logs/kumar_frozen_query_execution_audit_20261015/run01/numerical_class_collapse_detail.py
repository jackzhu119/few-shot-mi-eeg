"""Count collapse directly from saved query predictions; no exclusion or model IO."""
import hashlib
import json
from pathlib import Path

RESULTS = Path('/workspace/private_model_receipts/frozen-query-evaluation-20261015/run01/results')
OUTPUT = Path(__file__).with_suffix('.json')
worker_raw = (RESULTS/'worker_complete.json').read_bytes()
worker = json.loads(worker_raw)
rows, checked = [], []
for job in worker['jobs']:
    raw = (RESULTS/job['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == job['sha256'] and len(raw) == job['bytes']
    result = json.loads(raw)
    for session in [f'ses-{i}' for i in range(6)]:
        predictions = [r for r in result['predictions'] if r['session'] == session]
        assert predictions
        classes = set(r['y_pred'] for r in predictions)
        assert classes <= {0,1}
        if len(classes) == 1:
            rows.append({'job_id':job['job_id'],'subject':job['subject'],'seed':job['seed'],
                         'session':session,'role':'source_query' if session=='ses-0' else 'target_query',
                         'predicted_class':next(iter(classes)),'n':len(predictions)})
    checked.append({'path':job['path'],'sha256':job['sha256']})
summary = {}
for role in ['source_query','target_query','all_queries']:
    selected = rows if role == 'all_queries' else [r for r in rows if r['role']==role]
    summary[role] = {'collapsed_job_sessions':len(selected),
                     'distinct_jobs':len({r['job_id'] for r in selected}),
                     'distinct_participants':len({r['subject'] for r in selected}),
                     'participants':sorted({r['subject'] for r in selected},key=lambda s:int(s.split('-')[1]))}
assert summary['source_query']['collapsed_job_sessions'] == 2
assert summary['target_query']['collapsed_job_sessions'] == 14
assert len(rows) == 16
report = {'schema_version':1,'status':'passed_saved_prediction_collapse_count',
          'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'worker_complete_sha256':hashlib.sha256(worker_raw).hexdigest(),
          'all_jobs_checked':len(checked),'all_job_sessions_checked':6*len(checked),
          'summary':summary,'collapsed_rows':rows,'verified_prediction_files':checked,
          'excluded_jobs_or_participants':0,'new_model_forwards':0,'raw_EEG_arrays_loaded':0,
          'interpretation':'Prediction class collapse is retained as a measured outcome, not relabelled as a failed training job or grounds for seed/participant exclusion.'}
with OUTPUT.open('x') as handle:
    json.dump(report,handle,indent=2,allow_nan=False);handle.write('\n')
print(json.dumps(summary,indent=2))
print('sha256',hashlib.sha256(OUTPUT.read_bytes()).hexdigest())
