import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from audit_kumar_first_fit_bundle import archive
root=Path.cwd()
private=Path('/workspace/paper2-private-library-check/queue-sub1-seed20261014')
out=root/'research_logs/kumar_development_queue_20261014/sub-1-seed-20261014'
fm,fit=archive(private/'fit.tar','c31785de7b61c187ae3690a6d16cce8d89e5edf93be0bae6bcfce2b81a0fb309',194560,14)
dm,outer=archive(private/'dispatch.tar','121c956c49c2348c6c1f3381656bfcfebc5c03377f1f4eecd0906bc337472528',51200,6)
job='ba8899c0dc867baefa9a5623cccf706a82571413d63ec76e4baa7bfab613b4ca'
assert fm['job_id']==dm['job_id']==job
assert outer['paper2-results/https-development-download-run01.json']==fit['input_receipt.json']
for name in ['accepted_jobs.json','delivery_hashes.json']:
 path='research_logs/kumar_development_queue_20261014/'+name
 assert outer['paper2-90f674f/'+path]==(root/path).read_bytes()
ledger=json.loads(outer['paper2-90f674f/research_logs/kumar_development_queue_20261014/accepted_jobs.json'])
assert len(ledger['accepted_jobs'])==2 and all(x['job_id']!=job for x in ledger['accepted_jobs'])
config=json.loads((root/'configs/kumar_development_queue_https_20261014.json').read_text())
expected={e['path']:e for e in config['files']}
receipt=json.loads(fit['input_receipt.json'])
assert receipt['status']=='all_127_full_sha256_verified'
assert len(receipt['records'])==127 and {x['path'] for x in receipt['records']}==set(expected)
assert all(row['sha256']==expected[row['path']]['expected_sha256'] for row in receipt['records'])
assert fit['input_audit.json']==(root/'research_logs/kumar_first_gpu_fit_20261014/fit_text_evidence/input_audit.json').read_bytes()
log=outer['paper2-results/queue-dispatch-fqFDsVsZ.log'].decode()
for text in ['2026-10-14T11:41:41Z','2026-10-14T11:41:52Z','QUEUE_DISPATCH_EXIT_CODE=75','cc70f4274b7e14d9bd0e8d76d072aacf625bbf43']:
 assert text in log
result=next(json.loads(line) for line in log.splitlines() if line.startswith('{"status": "fit_saved'))
assert result['sha256']=='c31785de7b61c187ae3690a6d16cce8d89e5edf93be0bae6bcfce2b81a0fb309'
assert result['bytes']==194560 and result['job_id']==job and result['result_key']==fm['result_key']
r=json.loads(fit['fit_result.json'])
weights=json.loads(fit['weights.json'])
assert (r['epochs_executed'],r['optimizer_steps'],r['selected_epoch'])==(100,300,93)
assert r['replay_torch_loss']==r['selected_validation_loss']
best,stale=float('inf'),0
for row in weights['history']:
 if row['source_validation_loss']<best:best,stale=row['source_validation_loss'],0
 else:stale+=1
 assert stale<15
assert stale==7
for name in ['weights.json','fit_result.json','training.log','input_audit.json','input_receipt.json','events.jsonl','job.json','manifest.json']:
 p=out/'fit_text_evidence'/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(fit[name])
for name,value in outer.items():
 p=out/'dispatch_evidence'/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(value)
audit=dict(status='dispatch_input_identity_and_epoch_cap_crosscheck_passed',job_id=job,fit_members_verified=14,dispatch_members_verified=6,dispatch_archive_sha256='121c956c49c2348c6c1f3381656bfcfebc5c03377f1f4eecd0906bc337472528',dispatch_archive_bytes=51200,all_127_input_hashes_match=True,input_audit_identical_to_first_fit=True,accepted_predecessors=2,dispatch_start_utc='2026-10-14T11:41:41Z',dispatch_end_utc='2026-10-14T11:41:52Z',exit_code=75,epochs=100,optimizer_steps=300,selected_epoch=93,stop_reason='fixed_maximum_100_epochs_reached_not_patience_stop',consecutive_non_improving_epochs_at_cap=7,patience=15,extra_epochs_added=0,checkpoint_sha256=r['checkpoint_sha256'],torch_replay_error=0,numpy_replay_error=abs(r['replay_numpy_loss']-r['selected_validation_loss']),fits_performed_by_audit=0,query_rows_loaded=0,parent_acknowledged=False,stop_Pod=False)
(out/'dispatch_independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit))
