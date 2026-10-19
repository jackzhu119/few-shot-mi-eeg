from pathlib import Path
from lxml import etree
import subprocess,io,zipfile,hashlib,json,re,fitz
ROOT=Path('/workspace/few-shot-mi-eeg');PKG=ROOT/'manuscript/plos_one_innovation_20261017';BASE='3a806d210cc8c4f25f5d24f9dca61059588616f5';OUT=Path('/workspace/paper2_targeted_check_20261019/run02/final_independent_check.json')
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def old(p):return subprocess.check_output(['git','show',BASE+':'+str(p.relative_to(ROOT))],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def xml(data):
 with zipfile.ZipFile(io.BytesIO(data)) as z:return etree.fromstring(z.read('word/document.xml'))
def text(e):return ''.join(e.xpath('.//w:t/text()',namespaces=NS))
def canon(e):return etree.tostring(e,method='c14n')
checks=[]
def ck(name,okay,details=None):
 checks.append({'check':name,'passed':bool(okay),'details':details})
def section(x,a,b):
 body=list(x.find('w:body',NS));i=next(i for i,e in enumerate(body) if text(e)==a);j=next(j for j,e in enumerate(body[i+1:],i+1) if text(e)==b)
 return b''.join(canon(e) for e in body[i:j])
for name in ['PLOS_ONE_Manuscript_Submission','PLOS_ONE_Manuscript_Reading']:
 p=PKG/(name+'.docx');before=old(p);after=p.read_bytes();a=xml(before);b=xml(after)
 at=a.xpath('//w:tbl',namespaces=NS);bt=b.xpath('//w:tbl',namespaces=NS)
 ck(name+': six tables',len(at)==len(bt)==6)
 ck(name+': Table 6 full canonical OOXML unchanged',canon(at[5])==canon(bt[5]),{'before_sha256':sha(canon(at[5])),'after_sha256':sha(canon(bt[5])),'full_table_text':text(bt[5])})
 ck(name+': Table 6 true negative CI lower bound', '9.91 [−1.46, 21.75]' in text(bt[5]))
 alltable=[]
 for i,(ot,nt) in enumerate(zip(at,bt),1):
  oc=ot.xpath('.//w:tc',namespaces=NS);nc=nt.xpath('.//w:tc',namespaces=NS)
  for j,(oe,ne) in enumerate(zip(oc,nc)):
   o=text(oe);n=text(ne)
   if o!=n:alltable.append({'table':i,'zero_based_cell':j,'before':o,'after':n})
   ck(name+': Table '+str(i)+' cell '+str(j)+' numeric text unchanged',re.findall(r'[−+]?[0-9]+(?:\.[0-9]+)?',o)==re.findall(r'[−+]?[0-9]+(?:\.[0-9]+)?',n))
  if i!=3:ck(name+': Table '+str(i)+' full canonical OOXML unchanged',canon(ot)==canon(nt))
 ck(name+': Table 3 has exactly CPU-to-CSP/LDA header edit',len(alltable)==1 and alltable[0]['table']==3 and alltable[0]['before'].replace('CPU source model','CSP/LDA source model')==alltable[0]['after'],alltable)
 for title,nxt in [('Abstract','Introduction'),('Conclusions','Data and code availability')]:
  o=section(a,title,nxt);n=section(b,title,nxt);ck(name+': '+title+' exact canonical OOXML unchanged',o==n,{'before_sha256':sha(o),'after_sha256':sha(n)})
 ot=[e for e in a.xpath('//w:p',namespaces=NS) if text(e).startswith('Dataset metadata were accessed')];nt=[e for e in b.xpath('//w:p',namespaces=NS) if text(e).startswith('Dataset metadata were accessed')]
 ck(name+': data-access/identity paragraph unchanged',len(ot)==len(nt)==1 and canon(ot[0])==canon(nt[0]))
 with zipfile.ZipFile(io.BytesIO(before)) as z,zipfile.ZipFile(io.BytesIO(after)) as w:
  changed=[n for n in z.namelist() if z.read(n)!=w.read(n)]
  ck(name+': only document.xml modified',changed==['word/document.xml'],changed)
for name in ['PLOS_ONE_Manuscript_Submission','PLOS_ONE_Manuscript_Reading']:
 p=PKG/(name+'.pdf');matches=[]
 with fitz.open(p) as d:
  for i,page in enumerate(d):
   t=page.get_text();m=re.search(r'9\.91\s*\[−1\.46,\s*21\.75\]',t)
   if m:matches.append({'page':i+1,'literal_text':m.group()})
 ck(name+': PDF correct Table 6 interval',len(matches)==1,{'sha256':sha(p.read_bytes()),'matches':matches})
# Check all protected attachments, supplemental source texts, references and both figure trees against baseline Git bytes.
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines();protected=[]
for rel in paths:
 include=False
 if rel.startswith('manuscript/plos_one_innovation_20261017/'):
  suffix=rel.split('/')[-1]
  include=suffix.startswith(('S1_','S2_','Cover_','Human_')) or '/Figures/' in rel or suffix.endswith('.bib') or ('/Sources/' in rel and 'submission_draft' not in suffix)
 if rel.startswith('manuscript/figures/plos_innovation_20261017/'):include=True
 if rel.startswith('manuscript/kumar_plos_one_') and any(k in rel for k in ['supporting_methods_innovation_20261017','audit_reproducibility_innovation_20261017','cover_letter_innovation_20261017','references_innovation_20261017']):include=True
 if include:
  p=ROOT/rel;baseline=old(p);actual=p.read_bytes();protected.append({'path':rel,'before_sha256':sha(baseline),'after_sha256':sha(actual),'size_bytes':len(actual),'unchanged':baseline==actual})
ck('All protected supplements, cover, checklist, bibliography, figure inputs/exports and S1 Data unchanged',all(p['unchanged'] for p in protected),{'count':len(protected),'total_bytes':sum(p['size_bytes'] for p in protected),'files':protected})
src=ROOT/'manuscript/kumar_plos_one_submission_draft_innovation_20261017.md';before=old(src).decode();after=src.read_text()
ck('Primary manuscript source equals packaged source',src.read_bytes()==(PKG/'Sources'/src.name).read_bytes())
for title,nxt in [('Abstract','Introduction'),('Conclusions','Data and code availability')]:
 get=lambda s:s.split('## '+title+'\n',1)[1].split('## '+nxt+'\n',1)[0]
 ck('Markdown '+title+' exact unchanged',get(before)==get(after),{'sha256':sha(get(after).encode())})
ck('Main-body CPU hardware labels replaced by CSP/LDA algorithm name','CPU' not in after,{'remaining_CPU_occurrences':re.findall('.{0,25}CPU.{0,25}',after)})
ck('Scope retains explicit post-original-result exploratory status','post-hoc exploratory analyses after observing the original decoding results' in after)
ck('AI verification wording accurately references saved-result reconstruction','reproduction of saved-result calculations from the shared predictions and trial metadata' in after and 'end-to-end re-execution from the public dataset' not in after)
ck('Known false reviewer 21.1%-of-query statement was not introduced','1,512 of 7,156 complete windows (21.1%)' in after and '21.1% of query' not in after)
with fitz.open(PKG/'PLOS_ONE_Manuscript_Submission.pdf') as d:
 page=d[5];t=page.get_text();lines=[]
 for block in page.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   s=''.join(sp['text'] for sp in line['spans']).strip()
   if s:lines.append({'text':s,'y':line['bbox'][1]})
 numbered=[]
 for number in range(95,101):
  num=next((x for x in lines if x['text']==str(number)),None)
  body=[x for x in lines if x['text']!=str(number) and num and abs(x['y']-num['y'])<2]
  numbered.append({'line':number,'texts':[x['text'] for x in body]})
 ck('Checklist Q3 metadata/access/identity reference still submission page 6 lines 95–100',all(x['texts'] for x in numbered) and '10 October 2026' in t and '11 October 2026' in t and 'The author had no access to information that could identify individual participants' in t,numbered)
report={'baseline_commit':BASE,'actual_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'method':'Independent read-only comparisons of existing Git baseline bytes, OOXML canonical trees, saved PDF text and protected artifact SHA256. No scientific execution, bootstrap, figure rendering or source edits. Only this external report and audit script were written.','checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'all_passed':all(c['passed'] for c in checks)}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'report':str(OUT),'sha256':sha(OUT.read_bytes()),'passed':report['passed'],'failed':report['failed'],'failures':[c for c in checks if not c['passed']]},ensure_ascii=False,indent=2))
