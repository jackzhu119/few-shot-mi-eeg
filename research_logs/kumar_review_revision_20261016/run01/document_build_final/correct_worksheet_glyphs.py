"""Correct rendering of the actual Chinese author reply, without changing text."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
root=Path('/workspace/few-shot-mi-eeg')
log=root/'research_logs/kumar_review_revision_20261016/run01/document_build_final'
spec=importlib.util.spec_from_file_location('builder',log/'build_submission_package.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
pdf=b.OUT/'author_worksheet.pdf'
old_sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
shutil.move(str(pdf),'/workspace/private_model_receipts/paper2-review-revision-20261016/initial_document_exports/author_worksheet_before_CJK_fix.pdf')
source=root/'manuscript/kumar_plos_one_author_worksheet_20261016.md'
title,body=b.export_source(source,'pdf',False,False)
render=log/'author_worksheet_pdf_source_CJK_corrected.md'
with render.open('x') as f:f.write(body)
command=next(r['command'] for r in json.loads((log/'build_commands.json').read_text()) if r['command'][-1]!='x' and str(pdf) in r['command'])
command=[str(render) if x==str(log/'author_worksheet_pdf_source.md') else x for x in command]
started=datetime.now(timezone.utc).isoformat()
r=subprocess.run(command,cwd=root,capture_output=True,text=True)
(log/'author_worksheet_CJK.stdout').write_text(r.stdout)
(log/'author_worksheet_CJK.stderr').write_text(r.stderr)
receipt={'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':r.returncode,'old_pdf_sha256':old_sha,'source_unchanged_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'actual_missing_glyph_warnings':r.stderr.count('Missing character'),'new_pdf_bytes':pdf.stat().st_size if pdf.exists() else None,'new_pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else None,'scientific_changes':False}
(log/'worksheet_CJK_correction_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
if r.returncode or receipt['actual_missing_glyph_warnings']:raise RuntimeError('Rendering still failed; actual logs retained')
