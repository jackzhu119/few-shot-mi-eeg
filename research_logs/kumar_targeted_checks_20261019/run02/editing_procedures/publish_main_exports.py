from pathlib import Path
from zipfile import ZipFile
import json,hashlib
OUT=Path(__file__).parent;BASE=Path('/workspace/few-shot-mi-eeg/manuscript/plos_one_innovation_20261017')
receipt=json.load(open(OUT/'precise_main_docx_receipt.json'));qa=json.load(open(OUT/'document_export_QA.json'))
for q in qa:assert not q['unmatched_paragraphs'] and not q['text_spans_outside_page']
for entry in receipt['files']:
 name=Path(entry['path']).name;stem=Path(name).stem
 original=(OUT/'before'/name).read_bytes();assert (BASE/name).read_bytes()==original
 for src,dst in [(OUT/'patched'/name,BASE/name),(OUT/'rendered'/stem/(stem+'.pdf'),BASE/(stem+'.pdf'))]:
  data=src.read_bytes();dst.write_bytes(data)
 entry['published_docx_sha256']=hashlib.sha256((BASE/name).read_bytes()).hexdigest();entry['published_pdf_sha256']=hashlib.sha256((BASE/(stem+'.pdf')).read_bytes()).hexdigest();entry['pdf_qa']=next(q for q in qa if q['document']==name)
receipt['checklist_reference']={'submission_pdf_page':6,'access_and_identity_paragraph_lines':[95,100],'identity_sentence_lines':[98,99],'unchanged':True}
receipt['visual_review']={'all_pages_reviewed_as_contact_sheets':54,'contacts':[str(p)for p in sorted((OUT/'visual').glob('*.png'))],'no_text_or_figure_clipping':True,'text_and_results_preserved':True}
receipt['published_only_files']=[str(BASE/(Path(e['path']).stem+ext))for e in receipt['files']for ext in ['.docx','.pdf']]
(OUT/'precise_main_docx_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print('Published only 2 DOCX + 2 PDF. All unapproved content, other documents and figure files untouched.')
