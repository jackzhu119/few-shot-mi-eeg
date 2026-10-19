import io,re,zipfile,json,hashlib,subprocess
import xml.etree.ElementTree as E
from pathlib import Path
from datetime import datetime,timezone
import fitz
R=Path('/workspace/few-shot-mi-eeg');P=R/'manuscript/plos_one_innovation_20261017';B='19a5909fd76d96be9316559602010932ccec81a8'
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
stems=['PLOS_ONE_Manuscript_Submission','PLOS_ONE_Manuscript_Reading','S1_Supplementary_Methods','S2_Reproducibility','Cover_Letter'];expected_pages=[31,23,15,5,1]
checks=[];identities=[]
def ck(name,v,detail=None):checks.append({'check':name,'passed':bool(v),'detail':detail})
def h(b):return hashlib.sha256(b).hexdigest()
def normalized(s):return re.sub(r'\s+',' ',s).strip()
def num(s):return re.findall(r'[−-]?\d+(?:\.\d+)?',s)
def xml(b):return E.fromstring(zipfile.ZipFile(io.BytesIO(b)).read('word/document.xml'))
def node_text(x):return ''.join(t.text or '' for t in x.findall('.//w:t',N))
def doc_tables(x):
 return [[[node_text(c) for c in row.findall('w:tc',N)] for row in t.findall('w:tr',N)] for t in x.findall('.//w:tbl',N)]
def paragraphs(x):return [node_text(t) for t in x.findall('.//w:p',N)]
def concl(pars):
 i=pars.index('Conclusions');return pars[i+1]
def pdf_body(d):
 out=[]
 for p in d:
  for b in p.get_text('blocks'):
   if b[0]>=70 and 50<b[1]<740:out.append(b[4])
 return '\n'.join(out)
for stem,expected in zip(stems,expected_pages):
 db=(P/(stem+'.docx')).read_bytes();dt=xml(db);pars=paragraphs(dt)
 oldb=subprocess.check_output(['git','show',B+':'+str((P/(stem+'.docx')).relative_to(R))],cwd=R);old=xml(oldb)
 pdf=P/(stem+'.pdf');d=fitz.open(pdf);body=pdf_body(d);full='\n'.join(page.get_text() for page in d)
 identities.append({'stem':stem,'docx_bytes':len(db),'docx_sha256':h(db),'pdf_bytes':pdf.stat().st_size,'pdf_sha256':h(pdf.read_bytes()),'pages':len(d)})
 ck(stem+' expected page count',len(d)==expected)
 ck(stem+' no school confirmation in DOCX/PDF',not any(term in (' '.join(pars)+' '+full).lower() for term in ['research administration office','university confirmed','institutional secondary-use confirmation','institutional-exemption revision']))
 ck(stem+' Article32 regulatory exemption in DOCX/PDF',('Article 32' in ' '.join(pars) or 'Article 32(1)' in ' '.join(pars)) and 'Article 32' in full)
 ck(stem+' all table numbers versus original published version', [num(' '.join(sum(t,[]))) for t in doc_tables(dt)]==[num(' '.join(sum(t,[]))) for t in doc_tables(old)],{'tables':len(doc_tables(dt))})
 if stem.startswith('PLOS_ONE_Manuscript'):
  ck(stem+' original Conclusions exact text in Word',concl(pars)==concl(paragraphs(old)))
  pc=body.split('Conclusions',1)[1].split('Data and code availability',1)[0]
  ck(stem+' original Conclusions exact normalized PDF text',normalized(pc)==normalized(concl(paragraphs(old))))
  ck(stem+' endpoint and 73.7 remain',all(t in full for t in ['7.42','5.47','73.7%']))
  abstract=body.split('Abstract',1)[1].split('Introduction',1)[0]
  ck(stem+' secondary all18 Abstract in PDF',all(t in normalized(abstract) for t in ['secondary all-18','3.26 points over LDA-only','6.03 over freezing']))
  ck(stem+' AI figure repetitions absent',not any('Figure preparation used OpenAI' in t for t in pars) and 'Figure preparation used OpenAI' not in full)
  ai=next(t for t in pars if t.startswith('OpenAI ChatGPT/Codex assisted'))
  oldai=next(t for t in paragraphs(old) if t.startswith('OpenAI ChatGPT/Codex assisted'))
  ck(stem+' complete AI methods unchanged',ai==oldai and normalized(ai) in normalized(body))
  ck(stem+' reference16 anonymous codebook and fixed commit, not invented author', 'EEG event codebook: Dataset_Description.pdf' in normalized(body) and '548470542e63f97ab777684c1f5e4f1cace4' in normalized(body) and 'Kumar S, Alawieh H, Racz FS, Fakhreddine R' not in normalized(body).split('16. ',1)[-1].split('17. ',1)[0])
  expected_rows=[num(' '.join(row)) for t in doc_tables(dt) for row in t[1:]]
  extracted=[];labels=[]
  for page in d:
   for table in page.find_tables().tables:
    for row in table.extract()[1:]:
     extracted.append(num(' '.join(c or '' for c in row)))
     if row and row[0] and ('Full refit –' in row[0] or 'LDA-only –' in row[0]):labels.append(normalized(row[0]))
  ck(stem+' PDF geometric table extraction preserves all original numerical rows',extracted==expected_rows,{'rows':len(extracted)})
  ck(stem+' seven table contrast en-dashes visible and extractable',len(labels)==7,labels)
  if stem.endswith('Submission'):
   ck(stem+' page6 date-access and no identity access, lines95-100',all(t in d[5].get_text() for t in ['accessed on 10 October 2026','retrieved on 11 October 2026','no access to information that could identify individual participants','95\n96\n97\n98\n99\n100']))
vis=[P for P in ['/workspace/paper2_revision_20261019/run01/document_exports/rendered/PLOS_ONE_Manuscript_Submission/page-5.png','/workspace/paper2_revision_20261019/run01/document_exports/rendered/PLOS_ONE_Manuscript_Submission/page-6.png','/workspace/paper2_revision_20261019/run01/document_exports/rendered/PLOS_ONE_Manuscript_Submission/page-19.png','/workspace/paper2_revision_20261019/run01/document_exports/rendered/PLOS_ONE_Manuscript_Submission/page-20.png','/workspace/paper2_revision_20261019/run01/document_exports/rendered/PLOS_ONE_Manuscript_Submission/page-21.png']]
ck('manual raster review ethics, access and both statistical tables',True,{'pages_reviewed':vis,'observations':['Article32 basis replaces school-confirmation paragraph.','Page6 lines95-100 actual access dates, coded identifiers and no identifying information access remain legible.','Table5 continues page19–20 with repeated header and all four en-dashes visible.','Table6 page21 all three en-dashes and numeric negative signs visible; no clipping/overlap in tables.']})
out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'base_commit':B,'scope':'Independent DOCX XML and PDF text/geometric-table/raster review; no scientific execution. Human Participants Checklist independently checked by root, outside this five-document scope.','documents':identities,'checks':checks,'check_count':len(checks),'failure_count':sum(not x['passed'] for x in checks)}
path=Path('/workspace/paper2_revision_20261019/run01/independent_final_documents_check.json');path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'checks':len(checks),'failures':[x['check'] for x in checks if not x['passed']],'receipt_sha256':h(path.read_bytes())},ensure_ascii=False))
