"""Seal saved-result editorial artifacts, preserving all old scientific bytes."""
from __future__ import annotations
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
LOG=Path(__file__).resolve().parent
PACKAGE=ROOT/'manuscript/plos_one_submission_20261016'

def record(p):
    b=p.read_bytes()
    return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def main():
    checks=[]
    def require(ok,name,detail=None):
        checks.append({'check':name,'passed':bool(ok),'detail':detail})
        if not ok:raise ValueError(name)
    target=PACKAGE/'release_manifest.json'
    if target.exists():raise FileExistsError(target)
    protected=json.loads((ROOT/'research_logs/kumar_submission_optimization_20261015/run01/preservation_before.json').read_text())['protected_files']
    for item in protected:require(record(ROOT/item['path'])==item,'scientific_protected_byte_identity',item['path'])
    old=json.loads((ROOT/'manuscript/plos_one_submission_20261015/release_manifest.json').read_text())
    for item in old['sources']+old['artifacts']:require(record(ROOT/item['path'])==item,'old_seal_byte_identity',item['path'])
    new_main=ROOT/'manuscript/kumar_plos_one_submission_draft_20261016.md'
    text=new_main.read_text();old_text=(ROOT/'manuscript/kumar_plos_one_submission_draft_20261015.md').read_text()
    tables=lambda t:re.findall(r'(?m)(?:^\|.*\n)+',t)
    require(len(tables(text))==5,'five_new_main_tables')
    require(tables(text)[:4]==tables(old_text),'four_original_tables_exact_text')
    abstract=text.split('## Abstract\n',1)[1].split('\n## ',1)[0]
    require(len(abstract.split())<=300,'abstract_300_word_limit',len(abstract.split()))
    require(len(text.splitlines()[0][2:])<=250,'title_250_character_limit')
    bib=(ROOT/'manuscript/kumar_plos_one_references_20261016.bib').read_text()
    used=set(re.findall(r'(?<![\w.])@([A-Za-z][A-Za-z0-9_-]+)',text));keys=set(re.findall(r'@\w+\s*\{\s*([^,]+),',bib))
    require(used<=keys and len(used)==len(keys)==16,'sixteen_used_citations_resolve')
    values=list(csv.DictReader((LOG/'statistics/output/statistics_results.csv').open()))
    for v in values:
        require(f"{float(v['signflip_p_two_sided']):.5f}" in tables(text)[4],'table5_raw_matches_saved',v['contrast_id'])
        require(f"{float(v['signflip_holm_adjusted_p_family4']):.5f}" in tables(text)[4],'table5_Holm_matches_saved',v['contrast_id'])
    data=json.loads((PACKAGE/'S1_Data_manifest.json').read_text());a=record(PACKAGE/'S1_Data.zip')
    require(a['bytes']==data['archive']['bytes'] and a['sha256']==data['archive']['sha256'],'new_archive_full_hash')
    with ZipFile(PACKAGE/'S1_Data.zip') as z:
        require(z.testzip() is None,'all_archive_CRC')
        require(len(z.namelist())==len(set(z.namelist()))==69,'69_unique_archive_members')
        expected={r['path']:r for r in data['members']}
        require(set(expected)==set(z.namelist()),'exact_archive_member_set')
        for n,r in expected.items():
            b=z.read(n)
            require(len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'archive_member_full_SHA256',n)
            require(Path(n).suffix in {'.md','.json','.csv','.py','.txt'},'archive_text_code_or_license_only',n)
    figures=ROOT/'manuscript/figures/plos_submission_20261016'
    for n in range(1,5):
        new=next(figures.glob(f'Fig{n}_*source_data.csv'));old_csv=ROOT/'manuscript/figures/plos_submission_20261015'/new.name
        require(new.read_bytes()==old_csv.read_bytes(),'unchanged_figure_numeric_source',new.name)
        tif=PACKAGE/f'Fig{n}.tif';source=next(figures.glob(f'Fig{n}_*.tif'))
        require(tif.read_bytes()==source.read_bytes(),'production_alias_byte_identity',tif.name)
        with Image.open(tif) as im:
            dpi=im.info['dpi'];width=im.width/dpi[0]*2.54;height=im.height/dpi[1]*2.54
            require(im.mode=='RGB' and im.n_frames==1 and im.info['compression']=='tiff_lzw' and min(dpi)>=300 and max(dpi)<=600 and 6.68<=width<=19.051 and height<=22.23 and tif.stat().st_size<10_000_000,'TIFF_geometry_RGB_LZW',tif.name)
    required=[ROOT/n for n in ['CURRENT_PROJECT_STATUS.md','README.md','manuscript/README.md','NEXT_STAGE_HANDOFF.md','LICENSING.md']]
    required+=list(PACKAGE.glob('*.md'))+list(ROOT.glob('docs/kumar_*20261016.md'))+[LOG/'README.md']
    for doc in required:
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
            link=link.strip('<>').split('#',1)[0]
            if not link or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',link):continue
            require((doc.parent/link).exists(),'delivery_relative_link_resolves',{'source':str(doc.relative_to(ROOT)),'target':link})
    commands=json.loads((LOG/'verification/checks_receipt.json').read_text())['results']
    require([(r['stage'],r['exit_code']) for r in commands]==[('pytest',1),('ruff',0),('smoke',0),('data_stack',0)],'actual_software_status_recorded_without_green_suite_claim')
    require('13 failed, 1257 passed, 1 skipped' in (LOG/'verification/pytest.log').read_text(),'actual_full_suite_failure_counts_retained')
    # Final independent document QA is required and bound separately; it must
    # describe current output bytes, including the retained rendering corrections.
    qa=LOG/'document_QA/final_document_QA.json'
    require(qa.exists(),'independent_final_document_QA_exists')
    docqa=json.loads(qa.read_text())
    require(docqa.get('unresolved_findings')==[],'independent_document_QA_has_no_unresolved_findings')
    stable=set()
    for pattern in ['manuscript/kumar_*20261016.md','manuscript/kumar_*20261016.bib','docs/kumar_*20261016.md','scripts/*20261016.py','tests/*20261016.py','LICENSES/*','research_logs/kumar_review_revision_20261016/run01/statistics/public_inputs/*','research_logs/kumar_review_revision_20261016/run01/statistics/output/*','manuscript/figures/plos_submission_20261016/*']:
        stable.update(p for p in ROOT.glob(pattern) if p.is_file())
    # Exclude historical synchronization closeout from this content release.
    stable.discard(ROOT/'docs/kumar_submission_sync_closeout_20261016.md')
    stable.update([ROOT/'LICENSE',ROOT/'LICENSING.md',Path(__file__).resolve(),qa])
    artifacts=sorted(p for p in PACKAGE.iterdir() if p.is_file() and p.name!='release_manifest.json')
    manifest={'status':'sealed_author_review_package_not_submitted','sealed_utc':datetime.now(timezone.utc).isoformat(),'reference_base_commit':'a78372db00cd4161e713ab47aca2d93c643a52bb','source_data_tag':'paper2-plos-source-20261016','version_identity':'The published tag resolves to the content commit. This manifest records files, not its own Git commit/hash. Later sync receipts may be separate commits.','sources':[record(p) for p in sorted(stable)],'artifacts':[record(p) for p in artifacts],'protected_scientific_files_unchanged':len(protected),'old_seal_bound_files_unchanged':len(old['sources']+old['artifacts']),'full_suite_passed':False,'full_suite_counts':{'passed':1257,'failed':13,'skipped':1},'new_statistics_synthetic_tests_passed':24,'real_training_or_query_execution':False,'pending_human_facts':['actual_applicable_secondary_analysis_ethics_basis','personal_final_review_and_approval'],'font_and_word_limits':'Actual Liberation substitutions; Noto CJK for verbatim Chinese reply. Native Word layout was not rendered.','public_and_R2_sync':'Actual post-seal verification is recorded in synchronization receipts; no future sync status is assumed by this seal.'}
    with target.open('x') as f:f.write(json.dumps(manifest,indent=2)+'\n')
    receipt={'status':'artifact_checks_passed_with_explicit_full_suite_and_human_limits','completed_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'checks_count':len(checks),'failures':[],'release_manifest':record(target),'full_suite_passed':False}
    with (LOG/'final_package_validation.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'artifact_checks':len(checks),'sources':len(stable),'artifacts':len(artifacts),'full_suite_passed':False}))

if __name__=='__main__':main()
