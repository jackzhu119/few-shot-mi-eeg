"""Apply reviewed paragraph-local replacements to existing OOXML; no manuscript rebuild."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import copy,difflib,hashlib,json,re,subprocess
ROOT=Path('/workspace/few-shot-mi-eeg');BASE=ROOT/'manuscript/plos_one_innovation_20261017'
OUT=Path(__file__).parent;NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W='{'+NS['w']+'}';XML='{http://www.w3.org/XML/1998/namespace}'
DOCS=['PLOS_ONE_Manuscript_Submission','PLOS_ONE_Manuscript_Reading','S1_Supplementary_Methods','S2_Reproducibility','Cover_Letter']

def sha(b):return hashlib.sha256(b).hexdigest()
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def plain(md,kind):
 refs={'kumar2024':9,'china2023ethics':15} if kind.startswith('PLOS') else {'kumar2024':1,'china2023ethics':2} if kind.startswith('S1') else {'kumar2024':2,'china2023ethics':3}
 for ref,n in refs.items():md=md.replace('[@'+ref+']','['+str(n)+']')
 return subprocess.check_output(['pandoc','-f','markdown+smart','-t','plain','--wrap=none'],input=md.encode()).decode().strip()
def canonical(p):return etree.tostring(p,method='c14n')

def splice(p,start,end,new):
 nodes=p.xpath('.//w:t',namespaces=NS);assert nodes
 offsets=[];n=0
 for t in nodes:offsets.append((n,n+len(t.text or''),t));n=offsets[-1][1]
 if start==end:
  candidates=[(a,b,t) for a,b,t in offsets if a<=start<=b]
  a,b,t=candidates[-1] if start==n else candidates[0]
  t.text=(t.text or'')[:start-a]+new+(t.text or'')[start-a:];t.set(XML+'space','preserve');return
 hit=[(a,b,t) for a,b,t in offsets if a<end and b>start]
 assert hit,(start,end,n)
 for i,(a,b,t) in enumerate(hit):
  s=t.text or'';left=max(0,start-a);right=min(len(s),end-a)
  t.text=s[:left]+(new if i==0 else'')+s[right:];t.set(XML+'space','preserve')

def replace_span(p,old,new):
 full=text(p);assert full.count(old)==1,(old,full)
 at=full.index(old)
 for tag,a,b,c,d in reversed(difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes()):
  if tag!='equal':splice(p,at+a,at+b,new[c:d])
 assert text(p)==full.replace(old,new),(text(p),full.replace(old,new))

def main():
 prose=json.load(open(OUT.parent/'main_prose_changes.json'))['changes'];extra=json.load(open(OUT.parent/'main_ethics_final_changes.json'))['replacements'];ethics=json.load(open(OUT.parent/'ethics_text_changes.json'))['changes']
 receipt={'operation':'Reviewed exact OOXML prose/ethics edits; preserve pre-existing paragraphs, tables, formulas, styles and media','files':[]}
 (OUT/'before').mkdir(exist_ok=True);(OUT/'patched').mkdir(exist_ok=True)
 for name in DOCS:
  source=BASE/(name+'.docx');original=subprocess.check_output(['git','show','HEAD:'+str(source.relative_to(ROOT))],cwd=ROOT)
  (OUT/'before'/source.name).write_bytes(original)
  with ZipFile(__import__('io').BytesIO(original)) as z:infos=z.infolist();data={i.filename:z.read(i.filename) for i in infos}
  x=etree.fromstring(data['word/document.xml']);allp=x.xpath('//w:p',namespaces=NS);before_p={id(p):canonical(p) for p in allp};changed=set();applied=[]
  original_formulas=[canonical(m) for m in x.xpath('//m:oMath',namespaces=NS)]
  if name.startswith('PLOS'):changes=prose+extra
  else:
   key='supporting_methods' if name.startswith('S1') else 'audit_reproducibility' if name.startswith('S2') else 'cover_letter'
   entry=next(v for v in ethics if '/plos_one_' not in v['path'] and f'kumar_plos_one_{key}_' in v['path'])
   changes=entry['replacements']
  for k,v in enumerate(changes):
   old,new=plain(v['old'],name),plain(v['new'],name)
   # Tables retain every numeric cell; only the contrast label punctuation changes.
   if v.get('id','').startswith(('table5_comparison','table6_comparison')):
    rowmap={'Full refit − frozen':'Full refit – frozen','Full refit − LDA-only':'Full refit – LDA-only','LDA-only − frozen':'LDA-only – frozen'}
    # Restrict to exact labels from the corresponding table, avoiding numerical minus signs.
    tables=x.xpath('//w:tbl',namespaces=NS);table=tables[4 if v['id'].startswith('table5') else 5]
    for p in table.xpath('.//w:tc[1]//w:p',namespaces=NS):
     for a,b in rowmap.items():
      if a in text(p):replace_span(p,a,b);changed.add(id(p))
    applied.append({'id':v['id'],'table_labels_only':True});continue
   ps=[p for p in x.xpath('//w:p',namespaces=NS) if old in text(p)]
   if len(ps)!=1:raise AssertionError((name,v.get('id',k),'matching paragraphs',len(ps),old))
   p=ps[0];changed.add(id(p));before=text(p)
   if '\n\n' in new:
    assert before==old,(name,'multi-paragraph old is not whole paragraph',before,old)
    parts=new.split('\n\n');replace_span(p,old,parts[0]);prev=p
    for part in parts[1:]:
     q=etree.Element(W+'p',nsmap=p.nsmap)
     if p.find(W+'pPr') is not None:q.append(copy.deepcopy(p.find(W+'pPr')))
     r=etree.SubElement(q,W+'r');first=p.find(W+'r')
     if first is not None and first.find(W+'rPr') is not None:r.append(copy.deepcopy(first.find(W+'rPr')))
     t=etree.SubElement(r,W+'t');t.set(XML+'space','preserve');t.text=part;prev.addnext(q);prev=q
   else:replace_span(p,old,new)
   applied.append({'id':v.get('id',f'companion_{k}'),'before':before,'after':text(p),'new_paragraphs':max(0,len(new.split('\n\n'))-1)})
  # Preserve a true mathematical object for the newly stated 2^n enumeration.
  if name.startswith('PLOS'):
   ps=[p for p in x.xpath('//w:p',namespaces=NS) if text(p).startswith('All 2^(n) sign assignments')]
   assert len(ps)==1
   p=ps[0];n=next(t for t in p.xpath('.//w:t',namespaces=NS) if '2^(n)' in (t.text or''))
   formula=next(m for m in x.xpath('//m:oMath',namespaces=NS) if ''.join(m.xpath('.//m:t/text()',namespaces=NS))=='2n')
   parent=n.getparent();assert parent.tag==W+'r';a,b=n.text.split('2^(n)',1);n.text=a
   newr=copy.deepcopy(parent);newr.find(W+'t').text=b;parent.addnext(copy.deepcopy(formula));parent.getnext().addnext(newr)
  changed_p=[p for p in allp if id(p) in changed]
  untouched=[p for p in allp if id(p) not in changed]
  assert all(before_p[id(p)]==canonical(p) for p in untouched)
  after_formulas=[canonical(m) for m in x.xpath('//m:oMath',namespaces=NS)]
  assert all(after_formulas.count(b)>=original_formulas.count(b) for b in set(original_formulas))
  # Link text changed in S1; the historical URL must also change to the current statement.
  changed_members=['word/document.xml']
  if name.startswith('S1'):
   oldurl='https://github.com/jackzhu119/few-shot-mi-eeg/blob/research/learning-preserving-bci/docs/kumar_ethics_statement_revision_20261016.md'
   newurl='https://github.com/jackzhu119/few-shot-mi-eeg/blob/main/manuscript/plos_one_innovation_20261017/Ethics_Statement_20261019.md'
   rel='word/_rels/document.xml.rels';assert data[rel].decode().count(oldurl)==1
   data[rel]=data[rel].replace(oldurl.encode(),newurl.encode());changed_members.append(rel)
  # Integrity check: all numeric and non-label table cells retain exact XML.
  oldx=etree.fromstring(ZipFile(__import__('io').BytesIO(original)).read('word/document.xml'))
  for idx,(a,b) in enumerate(zip(oldx.xpath('//w:tbl',namespaces=NS),x.xpath('//w:tbl',namespaces=NS))):
   ac=a.xpath('.//w:tc',namespaces=NS);bc=b.xpath('.//w:tc',namespaces=NS);assert len(ac)==len(bc)
   for j,(aa,bb) in enumerate(zip(ac,bc)):
    ta,tb=text(aa),text(bb)
    assert ta==tb or (name.startswith('PLOS') and idx in(4,5) and ta.replace(' − ',' – ')==tb),(name,idx,j,ta,tb)
  data['word/document.xml']=etree.tostring(x,encoding='UTF-8',xml_declaration=True,standalone=True)
  dest=OUT/'patched'/source.name
  with ZipFile(dest,'w') as z:
   for i in infos:z.writestr(i,data[i.filename])
  with ZipFile(__import__('io').BytesIO(original)) as z:
   actual=[i.filename for i in infos if z.read(i.filename)!=data[i.filename]]
  assert actual==changed_members,(actual,changed_members)
  receipt['files'].append({'file':str(source.relative_to(ROOT)),'original_sha256':sha(original),'patched_sha256':sha(dest.read_bytes()),'changed_ooxml_members':actual,'unchanged_ooxml_members':len(infos)-len(actual),'changed_existing_paragraphs':len(changed_p),'untouched_paragraphs_canonical_xml_identical':len(untouched),'pre_existing_math_objects_unchanged':len(original_formulas),'new_math_objects':len(after_formulas)-len(original_formulas),'table_numeric_values_unchanged':True,'changes':applied})
  print(name,'patched',len(changed_p),'paragraphs',actual)
 (OUT/'precise_docx_patch_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
