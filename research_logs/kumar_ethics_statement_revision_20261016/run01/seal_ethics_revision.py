"""Seal only the new administrative revision; verify historical byte identity."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent
OUT = ROOT / 'manuscript/plos_one_submission_ethics_20261016'


def rec(p):
    b = p.read_bytes()
    return {'path': p.relative_to(ROOT).as_posix(), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def main():
    checks = []
    def require(ok, name, detail=None):
        checks.append({'check': name, 'passed': bool(ok), 'detail': detail})
        if not ok:
            raise ValueError(name)
    target = OUT / 'release_manifest.json'
    if target.exists():
        raise FileExistsError(target)
    protected = json.loads((ROOT/'research_logs/kumar_submission_optimization_20261015/run01/preservation_before.json').read_text())['protected_files']
    for row in protected:
        require(rec(ROOT/row['path']) == row, '816_scientific_bytes_preserved', row['path'])
    oldcounts = []
    for date in ['20261015', '20261016']:
        old = json.loads((ROOT/f'manuscript/plos_one_submission_{date}/release_manifest.json').read_text())
        rows = old['sources']+old['artifacts']
        for row in rows:
            require(rec(ROOT/row['path']) == row, 'historical_seal_unchanged', row['path'])
        oldcounts.append(len(rows))
    text = (ROOT/'manuscript/kumar_plos_one_submission_draft_ethics_20261016.md').read_text()
    oldtext = (ROOT/'manuscript/kumar_plos_one_submission_draft_20261016.md').read_text()
    tables = lambda t: re.findall(r'(?m)(?:^\|.*\n)+', t)
    require(tables(text) == tables(oldtext) and len(tables(text)) == 5, 'five_tables_exact')
    abstract = lambda t: t.split('## Abstract\n',1)[1].split('\n## ',1)[0]
    require(abstract(text) == abstract(oldtext), 'abstract_exact')
    oldbib = (ROOT/'manuscript/kumar_plos_one_references_20261016.bib').read_bytes()
    bib = (ROOT/'manuscript/kumar_plos_one_references_ethics_20261016.bib').read_bytes()
    require(bib.startswith(oldbib), 'all_16_old_references_exact_prefix')
    keys = set(re.findall(r'@\w+\s*\{\s*([^,]+),', bib.decode()))
    require(len(keys) == 17 and 'china2023ethics' in keys, 'one_legal_reference_added')
    used = set(re.findall(r'(?<![\w.])@([A-Za-z][A-Za-z0-9_-]+)', text))
    require(used <= keys, 'main_citations_resolve')
    for name in ['S1_Data.zip','S1_Data_manifest.json','S1_Data_README.md','DATA_DICTIONARY.md','REPRODUCE_SAVED_RESULTS.md','figure_upload_manifest.json','Fig1.tif','Fig2.tif','Fig3.tif','Fig4.tif']:
        require((OUT/name).read_bytes() == (ROOT/'manuscript/plos_one_submission_20261016'/name).read_bytes(), 'data_and_figures_byte_identical', name)
    with ZipFile(OUT/'S1_Data.zip') as z:
        require(len(z.namelist()) == len(set(z.namelist())) == 69 and z.testzip() is None, '69_data_members_CRC')
    qa = json.loads((LOG/'document_QA/final_document_QA.json').read_text())
    require(qa.get('unresolved_findings') == [], 'independent_document_QA_passed')
    sources = [p for p in (ROOT/'manuscript').glob('*ethics_20261016.*') if p.is_file()]
    sources += [ROOT/'manuscript/kumar_china_ethics_reference_20261016.bib', ROOT/'LICENSES/scope-addendum-paper2-exports-20261016.md', ROOT/'docs/kumar_ethics_statement_revision_20261016.md']
    sources += [p for p in LOG.rglob('*') if p.is_file() and p.name not in {'final_package_validation.json'} and p.suffix not in {'.png','.jpg','.pyc'}]
    sources = sorted(set(sources))
    artifacts = sorted(p for p in OUT.iterdir() if p.is_file() and p != target)
    for p in [OUT/'README.md',ROOT/'docs/kumar_ethics_statement_revision_20261016.md',LOG/'README.md']:
        for link in re.findall(r'\]\(([^)]+)\)', p.read_text()):
            link=link.strip('<>').split('#',1)[0]
            if not link or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link == 'release_manifest.json':
                continue
            require((p.parent/link).exists(), 'new_relative_link_resolves', {'source':str(p.relative_to(ROOT)), 'link':link})
    manifest = {'status':'sealed_ethics_statement_revision_not_submitted', 'sealed_utc':datetime.now(timezone.utc).isoformat(), 'base_commit':'1a7e1ab8b6253db52544ba185abb33a6bcb4937b','source_data_tag':'paper2-plos-ethics-20261016', 'version_identity':'The immutable tag resolves to the content commit; this manifest does not hash itself or predict its Git commit. Later sync receipts are separate.', 'sources':[rec(p) for p in sources], 'artifacts':[rec(p) for p in artifacts], 'protected_scientific_files_unchanged':len(protected), 'historical_seal_file_counts_preserved':oldcounts, 'real_model_fits_query_forwards_or_EEG_decodes':0, 'ethics_basis':'author-reported institutional confirmation of exemption; no independently authenticated institutional document supplied', 'author_approval':'prior actual scientific-content approval preserved, not extrapolated to personal inspection of these new export bytes', 'native_Word_layout_rendered':False, 'full_software_suite_rerun':False, 'reason_no_suite_rerun':'Administrative documents and citations only; historical full-suite failures preserved, new document and metadata QA completed', 'sync_status':'Actual Git/R2 full-GET receipts are appended separately; no local export is proof of synchronization'}
    target.write_text(json.dumps(manifest,indent=2)+'\n')
    (LOG/'final_package_validation.json').write_text(json.dumps({'status':'passed','checks':checks,'checks_count':len(checks),'failures':[],'release_manifest':rec(target)},indent=2)+'\n')
    print(json.dumps({'status':'passed','checks':len(checks),'sources':len(sources),'artifacts':len(artifacts)}))


if __name__ == '__main__':
    main()
