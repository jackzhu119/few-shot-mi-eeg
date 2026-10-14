import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from audit_kumar_first_fit_bundle import archive
root=Path.cwd()
private=Path('/workspace/paper2-private-library-check/queue-sub1-seed20261013')
out=root/'research_logs/kumar_development_queue_20261014/sub-1-seed-20261013'
fm,fit=archive(private/'fit.tar','d3a7858c54aab0295954be6a6431509d5acdea687171474d5d406a211d7dd2dc',184320,14)
dm,outer=archive(private/'dispatch.tar','881fdcf9eb1fc22a80430635b8a22fb05f59d2b2e7077a9653d67dee9d3dc748',112640,8)
job='5be2fc9499d4ec3916e5191c822c205e195c0e25655c39ec0f84e5aa2c091470'
assert fm['job_id']==dm['job_id']==job
receipt=outer['paper2-results/https-development-download-run01.json']
assert receipt==fit['input_receipt.json']
config_path='configs/kumar_development_queue_https_20261014.json'
assert outer['paper2-90f674f/'+config_path]==(root/config_path).read_bytes()
delivery='research_logs/kumar_development_queue_20261014/delivery_hashes.json'
assert outer['paper2-90f674f/'+delivery]==(root/delivery).read_bytes()
expected={e['path']:e for e in json.loads((root/config_path).read_text())['files']}
r=json.loads(receipt)
assert r['status']=='all_127_full_sha256_verified'
assert len(r['records'])==127 and {x['path'] for x in r['records']}==set(expected)
for row in r['records']:
 assert row['sha256']==expected[row['path']]['expected_sha256']
assert sum(x['status']=='reused_sha256_verified' for x in r['records'])==22
assert sum(x['status']=='downloaded_sha256_verified' for x in r['records'])==105
assert fit['input_audit.json']==(root/'research_logs/kumar_first_gpu_fit_20261014/fit_text_evidence/input_audit.json').read_bytes()
dispatch=outer['paper2-results/queue-dispatch-2oGFvGLt.log'].decode()
for text in ['2026-10-14T11:27:04Z','2026-10-14T11:27:14Z','QUEUE_DISPATCH_EXIT_CODE=75','ec56058dc4d2716330db052aec6036cc845b39ba']:
 assert text in dispatch
result=next(json.loads(line) for line in dispatch.splitlines() if line.startswith('{"status": "fit_saved'))
assert result['sha256']=='d3a7858c54aab0295954be6a6431509d5acdea687171474d5d406a211d7dd2dc'
assert result['bytes']==184320 and result['job_id']==job and result['result_key']==fm['result_key']
fit_result=json.loads(fit['fit_result.json'])
assert fit_result['optimizer_steps']==177 and fit_result['epochs_executed']==59 and fit_result['selected_epoch']==44
assert fit_result['replay_torch_loss']==fit_result['selected_validation_loss']
for name in ['weights.json','fit_result.json','training.log','input_audit.json','input_receipt.json','events.jsonl','job.json','manifest.json']:
 p=out/'fit_text_evidence'/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(fit[name])
for name,value in outer.items():
 p=out/'dispatch_evidence'/name
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(value)
audit=dict(status='dispatch_input_identity_crosscheck_passed',job_id=job,fit_members_verified=14,dispatch_members_verified=8,dispatch_archive_sha256='881fdcf9eb1fc22a80430635b8a22fb05f59d2b2e7077a9653d67dee9d3dc748',dispatch_archive_bytes=112640,all_127_input_hashes_match=True,reused_input_files=22,new_input_files=105,input_audit_identical_to_first_fit=True,dispatch_start_utc='2026-10-14T11:27:04Z',dispatch_end_utc='2026-10-14T11:27:14Z',exit_code=75,optimizer_steps=177,checkpoint_sha256=fit_result['checkpoint_sha256'],torch_replay_error=0,numpy_replay_error=abs(fit_result['replay_numpy_loss']-fit_result['selected_validation_loss']),fits_performed_by_audit=0,query_rows_loaded=0,parent_acknowledged=False,stop_Pod=False)
(out/'dispatch_independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit))
