import concurrent.futures,datetime,hashlib,json,re,requests
from pathlib import Path
ROOT=Path(__file__).parent
API='https://www.scidb.cn/api/gin-sdb-filetree/public/file/childrenFileListByPath'
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
SEED=json.loads((ROOT/'inventory_MIND_BIDS.json').read_text())['data']
records=list(SEED)
queue=[x['path'] for x in SEED if x['dir']]
(ROOT/'inventory_pages').mkdir(exist_ok=True)
def fetch(path):
 collected=[]; evidence=[]; last=0
 while True:
  body={'dataSetId':'d0f67f38c5bc4416bdcce619f33e57da','version':'V4','path':path,'lastIndex':last,'pageSize':200}
  r=requests.post(API,json=body,timeout=25)
  name=hashlib.sha256((path+':'+str(last)).encode()).hexdigest()[:20]
  (ROOT/'inventory_pages'/f'{name}.json').write_text(r.text)
  obj=r.json()
  evidence.append({'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'endpoint':API,'method':'POST','request_body':body,'status':r.status_code,'bytes':len(r.content),'response_sha256':hashlib.sha256(r.content).hexdigest(),'response_file':f'inventory_pages/{name}.json','code':obj.get('code')})
  if obj.get('code')!=20000:raise RuntimeError(f'inventory API returned {obj.get("code")}')
  data=obj.get('data') or [];collected.extend(data)
  if len(data)<200:break
  last=max(x.get('index',last+i) for i,x in enumerate(data))+1
 return collected,evidence
http=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
 while queue:
  next_queue=[]
  for rows,evidence in ex.map(fetch,queue):
   records.extend(rows);http.extend(evidence)
   next_queue.extend(x['path'] for x in rows if x['dir'])
  queue=next_queue
  print('records',len(records),'next directories',len(queue),flush=True)
(ROOT/'inventory_http_manifest.json').write_text(json.dumps(http,ensure_ascii=False,indent=2))
(ROOT/'inventory_manifest.json').write_text(json.dumps({'checked_at_utc':NOW,'official_endpoint':API,'version':'V4','root':'/V4/MIND_BIDS','complete':True,'records':records},ensure_ascii=False,indent=2))
files=[x for x in records if not x['dir']]
summary={'checked_at_utc':NOW,'complete':True,'file_count':len(files),'directory_count':len(records)-len(files),'sum_file_bytes':sum(x.get('size',0) for x in files),'actual_subject_count':len({m.group(1) for x in records if (m:=re.match(r'/V4/MIND_BIDS/(sub-\d+)(?:/|$)',x['path']))}),'suffix_counts':{suffix:sum(x['fileName'].endswith(suffix) for x in files) for suffix in ['.set','.fdt','.edf','.bdf','.fif','.snirf','.tsv','.json','.mat']}}
(ROOT/'inventory_summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
for filename in ['README.md','participants.tsv','dataset_description.json']:
 record=next(x for x in SEED if x['fileName']==filename)
 url='https://china.scidb.cn/download?fileId='+record['id']
 try:
  r=requests.get(url,stream=True,allow_redirects=False,timeout=20)
  headers={k:('[REDACTED signed redirect]' if k.lower()=='location' and '?' in v else v) for k,v in r.headers.items() if k.lower()!='set-cookie'}
  evidence={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request_url':url,'method':'GET','status':r.status_code,'headers':headers,'record_name':filename,'metadata_size':record['size'],'redirect_followed':False}
  if r.is_redirect:
   target=r.headers['Location'];rr=requests.head(target,timeout=20,allow_redirects=False)
   evidence['redirect_target_head']={'status':rr.status_code,'headers':{k:v for k,v in rr.headers.items() if k.lower() not in ['set-cookie','location']},'signed_url_recorded':False}
  elif r.status_code==200:
   content=r.raw.read(100000)
   (ROOT/('sample_'+filename)).write_bytes(content)
   evidence['sample_bytes']=len(content);evidence['sha256']=hashlib.sha256(content).hexdigest()
  r.close();(ROOT/(filename.replace('.','_')+'_download_probe.json')).write_text(json.dumps(evidence,indent=2));print(filename,'download',r.status_code,evidence.get('redirect_target_head',{}).get('status'),flush=True)
 except Exception as exc:
  (ROOT/(filename.replace('.','_')+'_download_probe.json')).write_text(json.dumps({'record_name':filename,'error_type':type(exc).__name__,'error':str(exc).split('?')[0]},indent=2));print(filename,type(exc).__name__,flush=True)
