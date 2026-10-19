from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import fitz,re,unicodedata,json,hashlib
OUT=Path(__file__).parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def norm(x):return re.sub(r'\s+','',unicodedata.normalize('NFKC',x).replace('\u00ad','')).replace('\u200b','').replace('-','')
report=[]
for path in sorted((OUT/'patched').glob('*.docx')):
 pdf=OUT/'rendered'/path.stem/(path.stem+'.pdf');d=fitz.open(pdf);alltext='\n'.join(p.get_text() for p in d); bodytext='\n'.join(''.join(sp['text'] for sp in ln['spans'] if not (sp['text'].strip().isdigit() and ((sp['bbox'][0]<65 and path.stem.endswith('Submission')) or sp['bbox'][1]>page.rect.height-65))) for page in d for b in page.get_text('dict')['blocks'] for ln in b.get('lines',[]));textnorm=norm(bodytext)
 fonts=sorted({f[3] for page in d for f in page.get_fonts()});missing=[];bounds=[];ps=0
 with ZipFile(path) as z:
  x=etree.fromstring(z.read('word/document.xml'))
  for p in x.xpath('//w:p',namespaces=NS):
   t=''.join(p.xpath('.//w:t/text()',namespaces=NS))
   if len(t)<10 or p.xpath('.//m:oMath',namespaces=NS):continue
   ps+=1
   if norm(t) not in textnorm:missing.append(t)
 for i,page in enumerate(d):
  for b in page.get_text('dict')['blocks']:
   for ln in b.get('lines',[]):
    for sp in ln['spans']:
     r=fitz.Rect(sp['bbox'])
     if r.x0<-1 or r.y0<-1 or r.x1>page.rect.width+1 or r.y1>page.rect.height+1:bounds.append({'page':i+1,'text':sp['text'],'bbox':list(r)})
 q={'document':path.name,'pdf_path':str(pdf),'pages':len(d),'bytes':pdf.stat().st_size,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'fonts':fonts,'checked_text_paragraphs':ps,'unmatched_paragraphs':missing,'text_spans_outside_page':bounds,'no_institutional_ethics_confirmation':not any(s in alltext.lower() for s in ['office at chongqing','confirmed on 16 october','confirmation carried','institutional secondary-use','author-reported secondary-use exemption'])}
 report.append(q)
 (OUT/'rendered'/path.stem/'extracted_text.txt').write_text(alltext)
 print(path.name,len(d),'pages','missing',len(missing),'outside',len(bounds),'fonts',fonts)
(OUT/'document_export_QA.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
