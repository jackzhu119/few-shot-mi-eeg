from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import difflib,json,hashlib,subprocess
OUT=Path(__file__).parent;ROOT=Path('/workspace/few-shot-mi-eeg');BASE=ROOT/'manuscript/plos_one_innovation_20261017'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
qa=json.load(open(OUT/'document_export_QA.json'));receipt=json.load(open(OUT/'precise_docx_patch_receipt.json'))
for x in qa:assert not x['unmatched_paragraphs'] and not x['text_spans_outside_page'] and x['no_institutional_ethics_confirmation']
for entry in receipt['files']:
 name=Path(entry['file']).name
 with ZipFile(OUT/'before'/name) as z:a=etree.fromstring(z.read('word/document.xml'))
 with ZipFile(OUT/'patched'/name) as z:b=etree.fromstring(z.read('word/document.xml'))
 aa=[etree.tostring(p,method='c14n') for p in a.xpath('//w:p',namespaces=NS)];bb=[etree.tostring(p,method='c14n') for p in b.xpath('//w:p',namespaces=NS)]
 matched=sum(k for i,j,k in difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_matching_blocks())
 assert matched==entry['untouched_paragraphs_canonical_xml_identical'],(name,matched,entry)
 entry['canonical_xml_final_crosscheck']={'original_paragraphs':len(aa),'new_paragraphs':len(bb),'old_paragraphs_exactly_preserved':matched,'changed_old_paragraphs':len(aa)-matched,'inserted_paragraphs':len(bb)-len(aa)}
 pdfname=Path(name).stem+'.pdf';target=BASE/pdfname
 original=subprocess.check_output(['git','show','HEAD:'+str(target.relative_to(ROOT))],cwd=ROOT);(OUT/'before'/pdfname).write_bytes(original)
 for src,dst in [(OUT/'patched'/name,BASE/name),(OUT/'rendered'/Path(name).stem/pdfname,target)]:
  dst.write_bytes(src.read_bytes())
 entry['pdf_export']={'original_sha256':hashlib.sha256(original).hexdigest(),**next(x for x in qa if x['document']==name)}
receipt['visual_review']={'all_pages_reviewed_as_contact_sheets':75,'contacts':[str(p) for p in sorted((OUT/'visual').glob('contact_*.png'))],'updated_figure4_visible':True,'page_layout':'Existing formatting retained; natural pagination changed with the reviewed added prose. Tables remain editable. Figure labels and full caption text checked.'}
receipt['checklist_reference']={'submission_pdf_page':6,'access_and_identity_paragraph_lines':[95,100],'identity_no_access_sentence_lines':[98,99]}
receipt['font_rendering_note']='Main body uses the original SHA-matched Times New Roman family. Existing math/code fallbacks remain; the renderer uses Caladea for generated submission line numbers. OOXML font/style definitions were not changed.'
receipt['published_files']=[str(BASE/(Path(e['file']).name)) for e in receipt['files']]+[str(BASE/(Path(e['file']).stem+'.pdf')) for e in receipt['files']]
(OUT/'precise_docx_patch_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print('Published 5 verified DOCX and 5 PDF to existing package paths; no other files modified by this publisher.')
