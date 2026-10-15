"""Read-only closing check of saved paper2 publication artifacts; no science run."""
import csv
import hashlib
import io
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path('/workspace/few-shot-mi-eeg')
OUT = ROOT / 'research_logs/kumar_submission_optimization_20261015/run01/closing_independent_review'
PACKAGE = ROOT / 'manuscript/plos_one_submission_20261015'
checks, inputs, documents = [], {}, []

def check(ok, name, detail=None):
    checks.append({'check': name, 'passed': bool(ok), 'detail': detail})

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    path = Path(path)
    raw = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': sha(raw)}
    return raw

main_path = ROOT / 'manuscript/kumar_plos_one_submission_draft_20261015.md'
main = read(main_path).decode()
supp = read(ROOT / 'manuscript/kumar_plos_one_supporting_methods_20261015.md').decode()
worksheet = read(ROOT / 'manuscript/kumar_plos_one_author_worksheet_20261015.md').decode()
revision = read(ROOT / 'docs/kumar_submission_revision_report_20261015.md').decode()
package_readme = read(PACKAGE / 'README.md').decode()
dictionary = read(PACKAGE / 'DATA_DICTIONARY.md').decode()
reproduce = read(PACKAGE / 'REPRODUCE_SAVED_RESULTS.md').decode()
oldmain = read(ROOT / 'manuscript/kumar_longitudinal_decoding_working_draft_20261015.md').decode()

# Read stored endpoint/contrast summaries; no new estimates, bootstraps or inference.
qcbase = ROOT / 'research_logs/kumar_submission_qc_20261015/run01'
qc_rows = list(csv.DictReader(io.StringIO(read(qcbase / 'cohort_method_sensitivity_summary.csv').decode())))
contrasts = list(csv.DictReader(io.StringIO(read(qcbase / 'cohort_paired_contrasts.csv').decode())))
for row in qc_rows:
    if row['cohort'] == 'remaining12' and row['endpoint'] == 'target_five_session_mean_BA':
        formatted = f"{100*float(row['mean']):.2f} [{100*float(row['ci95_low']):.2f}, {100*float(row['ci95_high']):.2f}]"
        check(formatted in main, 'main QC table exact stored values: ' + row['method'] + '/' + row['subset'], formatted)
for contrast, subset, expected in [('refit_minus_frozen', 'all_included', (7.42, 2.49, 12.48)), ('refit_minus_lda_only', 'all_included', (5.47, 2.17, 8.91)), ('refit_minus_frozen', 'unflagged', (5.96, 0.99, 11.24)), ('refit_minus_lda_only', 'unflagged', (3.82, 1.11, 6.72))]:
    row = next(r for r in contrasts if r['cohort'] == 'remaining12' and r['contrast'] == contrast and r['subset'] == subset)
    actual = tuple(round(100*float(row[k]), 2) for k in ('mean', 'ci95_low', 'ci95_high'))
    check(actual == expected, 'original/sensitivity contrast exact stored rounding ' + contrast + '/' + subset, actual)
    check(int(row['n_eligible_participants']) == (12 if subset == 'all_included' else 10), 'correct contrast participant denominator ' + contrast + '/' + subset)

# Exact original tables stay intact; the fourth table is the new sensitivity.
tables = lambda text: re.findall(r'(?m)^\|[^\n]+\n\|[ :|\-]+\n(?:\|[^\n]+\n)+', text)
old_tables, new_tables = tables(oldmain), tables(main)
check(len(old_tables) == 3 and len(new_tables) == 4 and all(table in new_tables for table in old_tables), 'all three original Markdown tables unchanged')
for phrase in ['cue-anchored task-label windows', 'not evidence\nthat exactly 44 tasks ended early', 'no approval, exemption, waiver or no-review conclusion', 'same ten', 'not artifact-free', 'No source fit was repeated', '54 completed source fits', 'not 54 independent participants', 'activation remain pending']:
    text = main.replace('**', '')
    found = phrase in text
    # Equivalent explicit phrasing is read directly rather than inferred from a negation scanner.
    if phrase == 'same ten': found = 'same ten' in text or 'same-ten' in text
    if phrase == 'not artifact-free': found = 'unflagged does not mean artifact-free' in text
    check(found, 'main required interpretation boundary: ' + phrase)
for phrase in ['52.92%', '51.58%', '−1.34', '2,871', '8,613', '53/54', '29/54', '0.704246', '0.596543', '0.693048', '0.691847', '0.692351', '52.42%', '49.94%', '52.37%', '8.06', '24.62']:
    check(phrase in main, 'main saved neural-review value ' + phrase)
for phrase in ['BA needs both true classes', 'all five', '10/12', 'after seeing', 'not an active MIT grant', '18 identities', '54 participants', '30 historical partial']:
    check(phrase in dictionary, 'data dictionary scope: ' + phrase)
for phrase in ['No model weights or raw EEG', '--portable-inputs inputs', '--output new_qc_output', '13 scientific CSV tables', 'MIT plan\npending author approval']:
    check(phrase in reproduce, 'public reproduction statement: ' + phrase)
check(not any((ROOT / name).exists() for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt')), 'no newly active root LICENSE file')
check('No operative grant is active' in worksheet and 'pending author account' in worksheet and 'no conclusion yet' in worksheet, 'remaining ethics/license/personal-review items truthful')
check('new_scientific' not in main, 'no accidentally inserted operation-status identifier')

external = json.loads(read(PACKAGE / 'S1_Data_manifest.json'))
rawzip = read(PACKAGE / 'S1_Data.zip')
check(len(rawzip) == external['archive']['bytes'] == 591742 and sha(rawzip) == external['archive']['sha256'], 'S1 Data complete ZIP byte hash')
with zipfile.ZipFile(io.BytesIO(rawzip)) as archive:
    names = archive.namelist()
    check(len(names) == len(set(names)) == 41, 'S1 Data actual 41 unique members')
    check(archive.testzip() is None, 'S1 Data CRC integrity')
    internal = json.loads(archive.read('MANIFEST.json'))
    check(set(internal['files']) == set(names) - {'MANIFEST.json'}, 'internal manifest exact 40 payload coverage')
    by_external = {r['path']: r for r in external['members']}
    check(set(by_external) == set(names), 'external manifest exact 41 member coverage')
    for name in names:
        raw = archive.read(name)
        item = by_external[name]
        check(len(raw) == item['bytes'] and sha(raw) == item['sha256'], 'external member length/SHA ' + name)
        if name in internal['files']:
            item = internal['files'][name]
            check(len(raw) == item['bytes'] and sha(raw) == item['sha256'], 'internal payload length/SHA ' + name)
        check(Path(name).suffix in {'.md', '.json', '.csv', '.py'}, 'text-only public member ' + name)
    check(archive.read('DATA_DICTIONARY.md') == (PACKAGE / 'DATA_DICTIONARY.md').read_bytes() and archive.read('REPRODUCE_SAVED_RESULTS.md') == (PACKAGE / 'REPRODUCE_SAVED_RESULTS.md').read_bytes(), 'standalone dictionary/reproduction identical to bundled bytes')
    for name, count, rest in re.findall(r'### `([^`]+\.csv)` — ([\d,]+) data rows\n\n([^\n]+)', dictionary):
        with io.StringIO(archive.read(name).decode()) as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            columns = reader.fieldnames
        check(len(rows) == int(count.replace(',', '')), 'dictionary exact CSV row count ' + name)
        check(columns == re.findall(r'`([^`]+)`', rest), 'dictionary exact CSV column order ' + name)
    check(len(json.loads(archive.read('inputs/frozen_trial_metadata.json'))['trials']) == 7200, 'bundled fixed 7200 event metadata identities')
    check(len(list(csv.DictReader(io.StringIO(archive.read('results/training/all_saved_epoch_curves.csv').decode())))) == 2871, 'bundled all2871 recorded epochs')
    check(len(list(csv.DictReader(io.StringIO(archive.read('results/training/per_fit_training_review.csv').decode())))) == 54, 'bundled all54 fit summaries')
    check(len(list(csv.DictReader(io.StringIO(archive.read('figures/Fig4_longitudinal_paired_changes_source_data.csv').decode())))) == 180, 'bundled all180 longitudinal figure cells')

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for stem in ['manuscript_for_submission', 'manuscript_for_review', 'S1_Text', 'S2_Text', 'author_worksheet', 'cover_letter_draft']:
    pdf = PACKAGE / (stem + '.pdf')
    docx = PACKAGE / (stem + '.docx')
    pdfr = read(pdf)
    docxr = read(docx)
    process = subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, check=True)
    pdftext = process.stdout.decode()
    with zipfile.ZipFile(io.BytesIO(docxr)) as archive:
        xml = ET.fromstring(archive.read('word/document.xml'))
        wordtext = ' '.join(node.text or '' for node in xml.findall('.//w:t', NS))
        images = [name for name in archive.namelist() if name.startswith('word/media/')]
        table_count = len(xml.findall('.//w:tbl', NS))
    if stem.startswith('manuscript_for_'):
        for token in ['7.42', '5.47', '5.96', '52.92', '51.58', '2,871', '8,613', '0.704246', '0.596543', '0.691847']:
            check(token in pdftext and token in wordtext, stem + ' saved claim in actual PDF/Word ' + token)
        check(table_count == 4 and len(images) == (4 if stem.endswith('review') else 0), stem + ' actual editable tables/image separation')
        check('pending' in wordtext and 'approval' in wordtext and 'not public release' in wordtext, stem + ' ethics/release limitations in actual Word text')
    if stem == 'S1_Text':
        for token in ['2,871', '5.96', '6.50', '−0.54', '0.691847', '7691/7701', '1.5.0dev0']:
            check(token in pdftext and token in wordtext, 'actual S1 PDF/Word scientific detail ' + token)
    if stem == 'author_worksheet':
        check('pending' in wordtext and 'No operative grant is active' in wordtext and 'no conclusion yet' in wordtext, 'actual worksheet Word retains unresolved choices')
    documents.append({'name': stem, 'PDF_bytes': len(pdfr), 'PDF_sha256': sha(pdfr), 'DOCX_bytes': len(docxr), 'DOCX_sha256': sha(docxr), 'DOCX_tables': table_count, 'DOCX_images': len(images), 'PDF_text_extraction_exit': process.returncode, 'native_Word_visual_review': False})

# No new network call is made; carry only actual existing blocked-action records.
network = {}
for name in ['github_write_blocker.json', 'r2_connectivity_observation.json']:
    network[name] = json.loads(read(ROOT / 'research_logs/kumar_submission_optimization_20261015/run01' / name))
check(network['github_write_blocker.json']['remote_write_completed'] is False, 'actual GitHub write blocked; no new remote commit claimed')
check(network['r2_connectivity_observation.json']['status'] == 'read_probe_failed_no_upload_or_fullGET', 'actual R2 probe failed; no new upload/fullGET receipt')
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
observations = []
if not (PACKAGE / 'release_manifest.json').exists():
    observations.append({'severity': 'transient_delivery_state', 'finding': 'Package README names release_manifest.json; it had not yet been generated at this review snapshot. Parent is sealing it before delivery.'})
if head == '370bc94b7af3c926adeb02c38e430a53e4a64135' and '本轮形成真实本地Git提交和离线交付包' in revision:
    observations.append({'severity': 'transient_delivery_state', 'finding': 'Revision report anticipates a real new local commit/offline delivery; HEAD was still reference370bc94 at initial review. Parent reports local Git mutation is now verified allowed and is preparing that commit. Recheck actual fixed commit before final handoff.'})
if 'figure reproduction command' in (ROOT / 'docs/plos_one_submission_check_20261015.md').read_text() and 'render_kumar_submission_figures' not in package_readme:
    observations.append({'severity': 'documentation_advisory', 'finding': 'Compliance document says final package README records figure reproduction command; package README currently has no plotting command. Actual figure directory README provides the command; link that location precisely if editing documentation.'})
unchanged = []
for name, original in inputs.items():
    path = ROOT / name
    if path.exists() and sha(path.read_bytes()) == original['sha256']:
        unchanged.append(name)
    else:
        observations.append({'severity': 'concurrent_edit_observation', 'finding': name + ' changed while parent sealed delivery; scientific snapshot hashes above identify actual read bytes.'})
failures = [item for item in checks if not item['passed']]
result = {'status': 'read_only_final_consistency_passed_with_delivery_observations' if not failures else 'read_only_final_consistency_check_has_failures', 'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'current_local_HEAD_observed': head, 'scope': 'Actual manuscript/supplement/author files, PDF extracted text, Word XML, saved numeric tables, S1 Data dictionaries/commands/ZIP integrity; no science/statistics execution or independent native Word rendering', 'checks': len(checks), 'failures': failures, 'inputs': inputs, 'unchanged_input_files_at_closing': len(unchanged), 'documents': documents, 'new_fits': 0, 'new_model_forwards': 0, 'new_bootstraps': 0, 'new_query_array_reads': 0, 'Pod_or_first_paper_actions': 0, 'new_network_actions': 0, 'Git_or_R2_mutations_by_reviewer': 0, 'remote_GitHub_write': 'blocked by actual approval-policy rejection record; current revision not remotely pushed', 'new_R2_upload_fullGET': 'not completed; existing proxy failure record; no fabricated receipt', 'local_Git_status': 'Read-only HEAD snapshot; parent independently reports local Git writes verified allowed and is sealing local commit/offline delivery', 'remaining_human_items': ['Actual institutional determination and basis for this secondary analysis', 'Specific scoped code/content license choice and activation', 'Final personal review, actual human verification account and approval', 'Actual portal-only fields including prior PLOS contact/editor-reviewer suggestions if relevant'], 'observations': observations, 'details': checks}
(OUT / 'final_consistency_review.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'checks': len(checks), 'failures': failures, 'observations': observations}, ensure_ascii=False, indent=2))
