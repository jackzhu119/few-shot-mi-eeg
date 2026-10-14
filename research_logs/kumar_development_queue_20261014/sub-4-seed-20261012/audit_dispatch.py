import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from audit_kumar_first_fit_bundle import archive
root=Path.cwd()
private=Path('/workspace/paper2-private-library-check/queue-sub4-seed20261012')
out=root/'research_logs/kumar_development_queue_20261014/sub-4-seed-20261012'
fm,fit=archive(private/'fit.tar','f889999e47b3d4f4d58604c0d4daca95578dac83d0776ba3bac629e23a3268a1',174080,14)
dm,outer=archive(private/'dispatch.tar','67cd0808f8bb9d1edd75baac460a482db54f35f8bdefc2ddeabf9e0597393c74',51200,6)
job='e1b092f93db8c972cb59403814c73eb1ba2273b1aa82351f0205c390a28b9faa'
assert fm['job_id']==dm['job_id']==job
assert outer['paper2-results/https-development-download-run01.json']==fit['input_receipt.json']
for name in ['accepted_jobs.json','delivery_hashes.json']:
 path='research_logs/kumar_development_queue_20261014/'+name
 assert outer['paper2-90f674f/'+path]==(root/path).read_bytes()
ledger=json.loads(outer['paper2-90f674f/research_logs/kumar_development_queue_20261014/accepted_jobs.json'])
assert len(ledger['accepted_jobs'])==3 and all(x['job_id']!=job for x in ledger['accepted_jobs'])
config=json.loads((root/'configs/kumar_development_queue_https_20261014.json').read_text())
expected={e['path']:e for e in config['files']}
receipt=json.loads(fit['input_receipt.json'])
assert receipt['status']=='all_127_full_sha256_verified'
assert len(receipt['records'])==127 and {x['path'] for x in receipt['records']}==set(expected)
assert all(row['sha256']==expected[row['path']]['expected_sha256'] for row in receipt['records'])
inputs=json.loads(fit['input_audit.json'])
assert inputs['subject']=='sub-4' and len(inputs['runs'])==3
assert all(run['role'] in {'source_train','source_validation'} for run in inputs['runs'])
assert all(run['raw_file_sha256']==expected[run['source_file']]['expected_sha256'] for run in inputs['runs'])
log=outer['paper2-results/queue-dispatch-CEwGnI2r.log'].decode()
for text in ['2026-10-14T11:53:38Z','2026-10-14T11:53:47Z','QUEUE_DISPATCH_EXIT_CODE=75','e79338eba02f0d4e4889eca089fff9767295a5b9']:
 assert text in log
result=next(json.loads(line) for line in log.splitlines() if line.startswith('{"status": "fit_saved'))
assert result['sha256']=='f889999e47b3d4f4d58604c0d4daca95578dac83d0776ba3bac629e23a3268a1'
assert result['bytes']==174080 and result['job_id']==job and result['result_key']==fm['result_key']
r=json.loads(fit['fit_result.json'])
weights=json.loads(fit['weights.json'])
assert (r['epochs_executed'],r['optimizer_steps'],r['selected_epoch'])==(19,57,4)
assert r['replay_torch_loss']==r['selected_validation_loss']
best,stale=float('inf'),0
for row in weights['history']:
 if row['source_validation_loss']<best:best,stale=row['source_validation_loss'],0
 else:stale+=1
 assert stale<15 or row["epoch"]==19
assert stale==15
for name in ['weights.json','fit_result.json','training.log','input_audit.json','input_receipt.json','events.jsonl','job.json','manifest.json']:
 p=out/'fit_text_evidence'/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(fit[name])
for name,value in outer.items():
 p=out/'dispatch_evidence'/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(value)
audit=dict(status='dispatch_input_identity_and_patience_crosscheck_passed',job_id=job,fit_members_verified=14,dispatch_members_verified=6,dispatch_archive_sha256='67cd0808f8bb9d1edd75baac460a482db54f35f8bdefc2ddeabf9e0597393c74',dispatch_archive_bytes=51200,all_127_input_hashes_match=True,source_run_hashes_match_frozen_manifest=True,accepted_predecessors=3,dispatch_start_utc='2026-10-14T11:53:38Z',dispatch_end_utc='2026-10-14T11:53:47Z',exit_code=75,epochs=19,optimizer_steps=57,selected_epoch=4,stop_reason='frozen_patience_15_reached',consecutive_non_improving_epochs=15,patience=15,extra_epochs_added=0,checkpoint_sha256=r['checkpoint_sha256'],torch_replay_error=0,numpy_replay_error=abs(r['replay_numpy_loss']-r['selected_validation_loss']),fits_performed_by_audit=0,query_rows_loaded=0,parent_acknowledged=False,stop_Pod=False)
(out/'dispatch_independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit))
