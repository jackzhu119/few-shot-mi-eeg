"""Apply only approved run02 exact replacements to baseline Word OOXML."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import sys,json,subprocess,hashlib,difflib,re
sys.path.insert(0,'/workspace/paper2_revision_20261019/run01/document_exports')
from patch_precise_docx import replace_span,plain,canonical
ROOT=Path('/workspace/few-shot-mi-eeg');BASE=ROOT/'manuscript/plos_one_innovation_20261017';OUT=Path(__file__).parent
PIN='3a806d210cc8c4f25f5d24f9dca61059588616f5';NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
(OUT/'before').mkdir(exist_ok=True);(OUT/'patched').mkdir(exist_ok=True)
mapping=json.load(open(OUT.parent/'main_wording_changes.json'))['files'][0]['changes'];receipt={'baseline_commit':PIN,'files':[]}
for name in ['PLOS_ONE_Manuscript_Submission','PLOS_ONE_Manuscript_Reading']:
 src=BASE/(name+'.docx');old=subprocess.check_output(['git','show',PIN+':'+str(src.relative_to(ROOT))],cwd=ROOT);assert src.read_bytes()==old
 (OUT/'before'/src.name).write_bytes(old)
 pdf=BASE/(name+'.pdf');(OUT/'before'/pdf.name).write_bytes(subprocess.check_output(['git','show',PIN+':'+str(pdf.relative_to(ROOT))],cwd=ROOT))
 import io
 with ZipFile(io.BytesIO(old)) as z:infos=z.infolist();data={i.filename:z.read(i.filename) for i in infos}
 x=etree.fromstring(data['word/document.xml']);original=etree.fromstring(data['word/document.xml']);original_pars=x.xpath('//w:p',namespaces=NS);before_c14n={id(p):canonical(p) for p in original_pars};changed=set();changes=[]
 for entry in mapping:
  a,b=plain(entry['old'],name),plain(entry['new'],name)
  ps=[p for p in x.xpath('//w:p',namespaces=NS) if a in ''.join(p.xpath('.//w:t/text()',namespaces=NS))]
  assert len(ps)==entry['occurrences'],(name,a,len(ps),entry['occurrences'])
  for p in ps:replace_span(p,a,b);changed.add(id(p))
  changes.append({'old':a,'new':b,'occurrences':len(ps)})
 untouched=[p for p in original_pars if id(p) not in changed];assert all(canonical(p)==before_c14n[id(p)] for p in untouched)
 old_tables=original.xpath('//w:tbl',namespaces=NS);new_tables=x.xpath('//w:tbl',namespaces=NS);assert len(old_tables)==len(new_tables)==6
 assert canonical(old_tables[5])==canonical(new_tables[5]),'Table 6 XML changed'
 table6=''.join(new_tables[5].xpath('.//w:t/text()',namespaces=NS));assert '9.91 [−1.46, 21.75]' in table6
 tablechanges=[]
 for i,(a,b) in enumerate(zip(old_tables,new_tables)):
  ac=a.xpath('.//w:tc',namespaces=NS);bc=b.xpath('.//w:tc',namespaces=NS);assert len(ac)==len(bc)
  for j,(aa,bb) in enumerate(zip(ac,bc)):
   ta=''.join(aa.xpath('.//w:t/text()',namespaces=NS));tb=''.join(bb.xpath('.//w:t/text()',namespaces=NS))
   if ta!=tb:
    assert i==2 and ta.replace('CPU source model','CSP/LDA source model')==tb,(i,j,ta,tb)
    tablechanges.append({'table':i+1,'cell':j,'old':ta,'new':tb})
   assert re.findall(r'[−+]?\d+(?:\.\d+)?',ta)==re.findall(r'[−+]?\d+(?:\.\d+)?',tb)
  if i!=2:assert canonical(a)==canonical(b),(name,'other table changed',i)
 assert len(tablechanges)==1
 oldmath=[canonical(m)for m in original.xpath('//m:oMath',namespaces=NS)];newmath=[canonical(m)for m in x.xpath('//m:oMath',namespaces=NS)];assert oldmath==newmath
 data['word/document.xml']=etree.tostring(x,encoding='UTF-8',xml_declaration=True,standalone=True)
 dest=OUT/'patched'/src.name
 with ZipFile(dest,'w') as z:
  for info in infos:z.writestr(info,data[info.filename])
 with ZipFile(io.BytesIO(old)) as z:actual=[i.filename for i in infos if z.read(i.filename)!=data[i.filename]]
 assert actual==['word/document.xml'];alltext=''.join(x.xpath('//w:t/text()',namespaces=NS))
 for s in ['7.42','5.47','73.7%']:assert s in alltext
 receipt['files'].append({'path':str(src.relative_to(ROOT)),'baseline_sha256':hashlib.sha256(old).hexdigest(),'new_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'changed_ooxml_members':actual,'all_other_members_byte_identical':len(infos)-1,'changed_paragraphs':len(changed),'unchanged_paragraphs_exact_canonical_xml':len(untouched),'table6_c14n_sha256_unchanged':hashlib.sha256(canonical(new_tables[5])).hexdigest(),'table6_correct_lower_bound_preserved':'−1.46','table_values_all_unchanged':True,'table_changes':tablechanges,'all_math_objects_byte_identical':len(oldmath),'all_media_byte_identical':True,'changes':changes})
 print(name,'exact XML patch complete;',len(changed),'paragraphs')
(OUT/'precise_main_docx_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
