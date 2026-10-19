from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import json,hashlib,io
OUT=Path(__file__).parent;ROOT=Path('/workspace/few-shot-mi-eeg');BASE=ROOT/'manuscript/plos_one_innovation_20261017'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
old='Dataset_Description.pdf. Author-supplied codebook in the TransLearning repository; Available: https://github.com/neurosatya/TransLearning/blob/548470542e63f97ab777684c1f5e4f1cace4b8ed/Dataset_Description.pdf'
new='EEG event codebook: Dataset_Description.pdf. TransLearning repository [Internet]; GitHub; [cited 19 Oct 2026]. Available: https://github.com/neurosatya/TransLearning/blob/548470542e63f97ab777684c1f5e4f1cace4b8ed/Dataset_Description.pdf'
import sys;sys.path.insert(0,str(OUT));from patch_precise_docx import replace_span,canonical
receipt=json.load(open(OUT/'precise_docx_patch_receipt.json'))
for entry in receipt['files']:
 name=Path(entry['file']).name;path=OUT/'patched'/name
 with ZipFile(path) as z:infos=z.infolist();data={i.filename:z.read(i.filename) for i in infos}
 x=etree.fromstring(data['word/document.xml'])
 if name.startswith(('PLOS','S1')):
  ps=[p for p in x.xpath('//w:p',namespaces=NS) if old in ''.join(p.xpath('.//w:t/text()',namespaces=NS))];assert len(ps)==1
  replace_span(ps[0],old,new);entry['reference_codebook_updated_only']=True;entry['changed_existing_paragraphs']+=1;entry['untouched_paragraphs_canonical_xml_identical']-=1
  entry['changes'].append({'id':'reference_codebook','old':old,'new':new})
 if name=='PLOS_ONE_Manuscript_Reading.docx':
  data['word/media/rId45.png']=(BASE/'Figures/Fig4_longitudinal_paired_changes.png').read_bytes();entry['changed_ooxml_members'].append('word/media/rId45.png');entry['unchanged_ooxml_members']-=1
  entry['changes'].append({'id':'fig4_cohort_label','media':'word/media/rId45.png','new_label':'Primary cohort (n = 12)','other_media_unchanged':True})
 data['word/document.xml']=etree.tostring(x,encoding='UTF-8',xml_declaration=True,standalone=True)
 with ZipFile(path,'w') as z:
  for i in infos:z.writestr(i,data[i.filename])
 with ZipFile(OUT/'before'/name) as z:actual=[i.filename for i in infos if z.read(i.filename)!=data[i.filename]]
 assert sorted(actual)==sorted(entry['changed_ooxml_members']),(name,actual,entry['changed_ooxml_members'])
 entry['patched_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
receipt['font_rendering']='Original complete Times/Arial fonts restored and SHA matched to the 20261017 receipt; process-private Fontconfig only. Reconstructed PDF subsets not used.'
(OUT/'precise_docx_patch_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print('Precise final changes verified for',len(receipt['files']),'DOCX files')
