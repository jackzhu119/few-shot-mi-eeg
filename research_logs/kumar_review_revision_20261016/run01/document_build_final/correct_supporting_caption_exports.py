"""Re-export four main documents after shortening the supporting-data caption."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
root=Path('/workspace/few-shot-mi-eeg');log=root/'research_logs/kumar_review_revision_20261016/run01/document_build_final'
spec=importlib.util.spec_from_file_location('builder',log/'build_submission_package.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
prior=json.loads((log/'build_commands.json').read_text());rows=[]
for name in ['manuscript_for_submission','manuscript_for_review']:
  for kind in ['pdf','docx']:
    target=b.OUT/f'{name}.{kind}';old=hashlib.sha256(target.read_bytes()).hexdigest()
    shutil.move(str(target),f'/workspace/private_model_receipts/paper2-review-revision-20261016/initial_document_exports/{name}_before_support_caption_fix.{kind}')
    source=root/'manuscript/kumar_plos_one_submission_draft_20261016.md'
    title,body=b.export_source(source,kind,name.endswith('review'),True)
    render=log/f'{name}_{kind}_source_caption_corrected.md'
    with render.open('x') as f:f.write(body)
    cmd=next(r['command'] for r in prior if str(target) in r['command']);cmd=[str(render) if x==str(log/f'{name}_{kind}_source.md') else x for x in cmd]
    start=datetime.now(timezone.utc).isoformat();r=subprocess.run(cmd,cwd=root,capture_output=True,text=True)
    (log/f'{name}_{kind}_caption_correction.stdout').write_text(r.stdout);(log/f'{name}_{kind}_caption_correction.stderr').write_text(r.stderr)
    if r.returncode:raise RuntimeError('Actual export failure; logs retained')
    if kind=='docx':b.patch_word(target,True)
    rows.append({'path':str(target.relative_to(root)),'command':cmd,'started_utc':start,'finished_utc':datetime.now(timezone.utc).isoformat(),'exit_code':r.returncode,'old_sha256':old,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'missing_glyph_warnings':r.stderr.count('Missing character')})
    (log/'supporting_caption_export_correction_receipt.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'reason':'Concise supporting-data caption removes last-page widow; explicit reliability/drift/check coverage; no scientific text/table changes','outputs':rows},indent=2)+'\n')
print(json.dumps(rows))
