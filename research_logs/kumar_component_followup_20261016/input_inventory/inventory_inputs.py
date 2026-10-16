"""Read-only local inventory: no EDF/NPZ/checkpoint opening and no scientific run."""
from __future__ import annotations

import ast
import collections
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path('/workspace/few-shot-mi-eeg')
OUT = Path(__file__).resolve().parent
DATA = REPO / 'data/public_eeg/kumar2024/nm000177/v1.0.5'
FROZEN = REPO / 'research_logs/kumar_cross_session_20261012/protocol/split_manifest.json'
CPU = REPO / 'results/kumar_cross_session_20261012/cpu_run01_20261013T151445Z'
CACHE = REPO / 'research_logs/kumar_cross_session_20261012/csp_development_epochs_run01_20261014'
CSP = REPO / 'results/kumar_csp_signed_score_20261015/run02'
SOURCES = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    path = Path(path)
    if not path.is_absolute():
        path = REPO / path
    assert path.suffix not in {'.edf', '.gdf', '.npz', '.pt', '.pth', '.tar', '.gz'}, path
    raw = path.read_bytes()
    SOURCES[str(path)] = {'bytes': len(raw), 'sha256': sha(raw)}
    return raw


def js(path):
    return json.loads(read(path))


def write_csv(name, rows):
    with (OUT / name).open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    config_path = 'configs/kumar_cross_session_20261012.json'
    config = js(config_path)
    selection_path = config['source_manifest']
    selected = js(selection_path)
    source_inventory = []
    for row in selected:
        path = DATA / row['path']
        exists = path.is_file()
        size = path.stat().st_size if exists else None
        signal = path.suffix in {'.edf', '.gdf'}
        actual_sha = official_match = None
        if exists and not signal:
            data = read(path)
            actual_sha = sha(data)
            actual_official = actual_sha if row['checksum_algorithm'] == 'sha256' else hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            official_match = actual_official == row['checksum']
        source_inventory.append({'relative_path': row['path'], 'absolute_path': str(path), 'kind': 'EDF_signal_not_opened' if signal else 'metadata_text', 'exists': exists, 'expected_bytes': row['size'], 'actual_bytes': size, 'size_matches': exists and size == row['size'], 'stored_official_algorithm': row['checksum_algorithm'], 'stored_official_checksum': row['checksum'], 'fresh_metadata_sha256': actual_sha, 'fresh_metadata_official_checksum_matches': official_match, 'signal_bytes_or_numeric_values_read': False})
    write_csv('source_file_inventory.csv', source_inventory)
    by_relative = {row['relative_path']: row for row in source_inventory}

    manifests = [
        ('development_source127', 'research_logs/kumar_pod_rebuild_recovery_20261014/frozen_inputs_127.json'),
        ('remaining_source253', 'research_logs/kumar_checkpoint_reuse_preparation_20261015/proposed_remaining_source_inputs.json'),
        ('query1189', 'configs/kumar_frozen_query_inputs_20261015.json'),
    ]
    frozen_members = []
    manifest_summaries = []
    for scope, name in manifests:
        doc = js(name)
        rows = doc['files']
        expected_total = 0
        missing = mismatch = metadata_hash_fail = 0
        for row in rows:
            relative = row.get('relative_path', row.get('path'))
            observed = by_relative[relative]
            expected_total += row['bytes']
            missing += not observed['exists']
            mismatch += observed['actual_bytes'] != row['bytes']
            if observed['fresh_metadata_sha256'] is not None:
                metadata_hash_fail += observed['fresh_metadata_sha256'] != row['sha256']
            frozen_members.append({'scope': scope, 'manifest': name, 'relative_path': relative, 'absolute_path': str(DATA / relative), 'expected_bytes': row['bytes'], 'actual_bytes': observed['actual_bytes'], 'exists': observed['exists'], 'size_matches': observed['actual_bytes'] == row['bytes'], 'stored_sha256': row['sha256'], 'fresh_metadata_sha256': observed['fresh_metadata_sha256'], 'fresh_hash_matches_when_text': observed['fresh_metadata_sha256'] == row['sha256'] if observed['fresh_metadata_sha256'] else None, 'signal_not_opened': True})
        manifest_summaries.append({'scope': scope, 'path': str(REPO / name), **SOURCES[str(REPO / name)], 'files': len(rows), 'expected_bytes': expected_total, 'EDF': sum(str(r.get('relative_path', r.get('path'))).endswith('.edf') for r in rows), 'missing': missing, 'size_mismatches': mismatch, 'fresh_metadata_hash_failures': metadata_hash_fail, 'raw_EDF_hashes': 'Stored full SHA256 available; current size checked only. No EDF bytes opened/rehash performed in this inventory.'})
    write_csv('frozen_manifest_members.csv', frozen_members)

    split = js(FROZEN)
    trials = split['trials']
    role_counts = collections.Counter(row['role'] for row in trials)
    included_role_counts = collections.Counter(row['role'] for row in trials if row['included'])
    subject_counts = collections.Counter(row['subject'] for row in trials if row['included'])
    source_scope = {'all_source_events': len(trials), 'included': sum(row['included'] for row in trials), 'excluded': sum(not row['included'] for row in trials), 'roles_all': dict(role_counts), 'roles_included': dict(included_role_counts), 'included_by_subject': dict(subject_counts), 'included_target_support_sessions': [{'subject': subject, 'session': session, 'n': sum(t['included'] and t['subject'] == subject and t['session'] == session and t['role'] == 'target_support' for t in trials)} for subject in config['subjects'] for session in config['split']['target_sessions']]}
    event_rows = []
    for item in source_inventory:
        if item['relative_path'].endswith('_events.tsv'):
            data = read(Path(item['absolute_path']))
            rows = list(csv.DictReader(io.StringIO(data.decode()), delimiter='\t'))
            event_rows.append({'path': item['absolute_path'], 'bytes': len(data), 'sha256': sha(data), 'rows': len(rows), 'fields': '|'.join(rows[0]), 'values': '|'.join(sorted(set(row['value'] for row in rows))), 'trial_types': '|'.join(sorted(set(row['trial_type'] for row in rows)))})
    write_csv('bids_event_tables.csv', event_rows)

    artifacts = []
    cpu_receipt = js(CPU / 'execution_receipt.json')
    for relative, expected_sha in cpu_receipt['outputs'].items():
        path = CPU / relative
        exists = path.is_file()
        array = path.suffix == '.npz'
        observed_sha = sha(read(path)) if exists and not array else None
        artifacts.append({'family': 'CPU_original_output', 'path': str(path), 'exists': exists, 'actual_bytes': path.stat().st_size if exists else None, 'expected_bytes': None, 'stored_sha256': expected_sha, 'fresh_text_sha256': observed_sha, 'fresh_text_hash_matches': observed_sha == expected_sha if observed_sha else None, 'arrays_or_models_not_opened': True})
    cache_preparation = js(CACHE / 'preparation_receipt.json')
    cache_subjects = []
    for subject in config['development_subjects']:
        receipt = js(CACHE / subject / 'subject_receipt.json')
        path = CACHE / subject / receipt['tensor_file']
        metadata_path = CACHE / subject / 'included_trial_metadata.json'
        metadata_bytes = read(metadata_path)
        cache_subjects.append({'subject': subject, 'tensor_path': str(path), 'tensor_exists': path.is_file(), 'tensor_compressed_file_bytes': path.stat().st_size if path.is_file() else None, 'stored_tensor_sha256': receipt['tensor_sha256'], 'shape_from_saved_receipt_not_array_read': receipt['tensor_shape'], 'dtype_from_saved_receipt': receipt['tensor_dtype'], 'roles': receipt['role_counts'], 'trial_count': receipt['trial_count'], 'metadata_path': str(metadata_path), 'metadata_bytes': len(metadata_bytes), 'metadata_sha256': sha(metadata_bytes), 'metadata_matches_receipt': sha(metadata_bytes) == receipt['metadata_sha256'], 'query_windows': receipt['query_windows_read'], 'validation_windows': receipt['validation_windows_read'], 'array_not_opened': True})
    csp_manifest_path = 'research_logs/kumar_csp_signed_score_execution_20261015/run02/original_output_manifest.json'
    csp_manifest = js(csp_manifest_path)
    for row in csp_manifest['files']:
        path = REPO / row['path']
        array = path.suffix == '.npz'
        exists = path.is_file()
        observed_sha = sha(read(path)) if exists and not array else None
        artifacts.append({'family': 'CSP_run02_253_outputs_not_source253', 'path': str(path), 'exists': exists, 'actual_bytes': path.stat().st_size if exists else None, 'expected_bytes': row['bytes'], 'stored_sha256': row['sha256'], 'fresh_text_sha256': observed_sha, 'fresh_text_hash_matches': observed_sha == row['sha256'] if observed_sha else None, 'arrays_or_models_not_opened': True})
    saved_paths = [
        'research_logs/kumar_submission_qc_20261015/run01/public_inputs/saved_predictions.csv',
        'research_logs/kumar_submission_qc_20261015/run01/public_inputs/frozen_trial_metadata.json',
        'research_logs/kumar_frozen_query_comparison_20261015/run01/per_subject_session.csv',
        'research_logs/kumar_frozen_query_comparison_20261015/run01/eegnet_per_seed_session.csv',
        'research_logs/kumar_csp_signed_score_execution_20261015/run02/scientific_summary_from_saved_results.json',
        'research_logs/kumar_cross_session_20261012/lowdim_reliability_dev_run01_20261014/measurement_receipt.json',
        'research_logs/kumar_remaining36_acceptance_20261015/run01/source_model_plan_all54.json',
        'configs/kumar_frozen_query_checkpoints_20261015.json',
    ]
    saved = []
    for name in saved_paths:
        path = REPO / name
        raw = read(path)
        item = {'path': str(path), 'exists': True, 'bytes': len(raw), 'sha256': sha(raw)}
        if path.suffix == '.csv':
            rows = list(csv.DictReader(io.StringIO(raw.decode())))
            item.update(rows=len(rows), fields=list(rows[0]))
        saved.append(item)
    write_csv('saved_artifact_inventory.csv', artifacts)

    code_paths = ['src/learning_preserving_bci/datasets/kumar.py', 'src/learning_preserving_bci/decoders/csp_lda.py', 'scripts/run_kumar_baselines.py', 'scripts/prepare_kumar_development_epochs.py', 'scripts/analyze_kumar_csp_signed_score_v1.py', 'scripts/analyze_kumar_lowdim_reliability.py', 'scripts/run_kumar_csp_signed_score_operation.py', 'scripts/check_kumar_csp_signed_score_inputs.py']
    code = []
    for name in code_paths:
        raw = read(name)
        tree = ast.parse(raw.decode())
        definitions = [{'name': node.name, 'line': node.lineno, 'end_line': node.end_lineno, 'signature': ast.unparse(node).split('\n', 1)[0]} for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        code.append({'path': str(REPO / name), 'bytes': len(raw), 'sha256': sha(raw), 'definitions': definitions})
    operation = js('configs/kumar_csp_signed_score_operation_20261015.json')
    gate_keys = ['minimum_effective_available_memory_bytes', 'minimum_free_output_disk_bytes', 'maximum_sampled_consumer_rss_bytes', 'minimum_running_cgroup_headroom_bytes', 'minimum_running_host_available_bytes', 'resource_poll_seconds', 'consumer_timeout_seconds', 'term_grace_seconds', 'automatic_retries']
    old_limits = {key: operation[key] for key in gate_keys}
    binding = js('configs/kumar_csp_signed_score_input_binding_20261015.json')
    disk = shutil.disk_usage(REPO)
    tmp = shutil.disk_usage('/tmp')
    meminfo = {line.split(':', 1)[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    cgroup_limit = int(Path('/sys/fs/cgroup/memory.max').read_text())
    cgroup_current = int(Path('/sys/fs/cgroup/memory.current').read_text())
    n = max(subject_counts.values())
    memory = {'estimate_not_measured_peak': True, 'max_included_subject_trials': n, 'raw_epoch22x2560_float64_bytes': 22*2560*8, 'raw_block22x16384_float64_bytes': 22*16384*8, 'processed_subject_float32_bytes': n*22*640*4, 'two_float32_chunk_plus_stack_bytes': 2*n*22*640*4, 'runner_subject_float64_copy_bytes': n*22*640*8, 'bundle_float32_plus_runner_float64_bytes': n*22*640*12, 'descriptive_projected21x640_float64_bytes_each': n*21*640*8, 'fit_union60x22x640_float64_bytes': 60*22*640*8, 'per_epoch_filter_buffers': 'Reference/filter float64 copies about0.43MiB each; padded SOS workspace and resample buffers add small multiples. Exact SciPy/library/RSS peak not benchmarked.', 'conservative_serial_process_working_budget_bytes': 2147483648, 'qualification': '2GiB is the existing sampled-consumer RSS ceiling, retained as a guard, not an empirically proven peak or a new allocation authorization. Full descriptive_features adds Welch/projected/centered buffers; budget-only runner need not compute query-based drift features.'}
    environment = subprocess.check_output(['/workspace/.venvs/few-shot-mi-eeg/bin/python', '-c', 'import importlib.metadata as m,json,platform; print(json.dumps({"python":platform.python_version(),"versions":{n:m.version(n) for n in ["numpy","scipy","scikit-learn","mne","moabb","pyriemann","pytest","ruff"]}}))'], text=True)
    attachment = Path('/workspace/attachments/79d04740-33ab-4daa-a9b6-0d9fa93c6dbf/已粘贴的文本.txt')
    read(attachment)
    result = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'audit_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(), 'mode': 'Read-only metadata/size/hash inventory and static code inspection. EDF/GDF/NPZ/checkpoint bytes were not opened; no signal, fit, forward, query, or scientific statistics executed.', 'source_selection': {'path':str(REPO/selection_path),'files':len(source_inventory),'total_expected_bytes':sum(r['expected_bytes'] for r in source_inventory),'EDF':sum(r['kind']=='EDF_signal_not_opened' for r in source_inventory),'EDF_expected_bytes':sum(r['expected_bytes'] for r in source_inventory if r['kind']=='EDF_signal_not_opened'),'missing':sum(not r['exists'] for r in source_inventory),'size_mismatches':sum(not r['size_matches'] for r in source_inventory),'metadata_fresh_official_hash_failures':sum(r['fresh_metadata_official_checksum_matches'] is False for r in source_inventory),'raw_signal_current_hash_verification':'Not performed; official and historical SHA256 remain available; future authorized loader must recheck actual bytes.'}, 'frozen_manifests':manifest_summaries, 'source_trial_scope':source_scope, 'BIDS_event_tables':{'files':len(event_rows),'rows':sum(r['rows'] for r in event_rows),'schemas':sorted(set(r['fields'] for r in event_rows)),'value_sets':sorted(set(r['values'] for r in event_rows)),'within_trial_phase_markers':'No original GDF POS/TYP loaded. BIDS event TSVs contain released left/right cue labels, not verified task-start/end mappings.'}, 'cache_subjects':cache_subjects,'cache_preparation_scope':{k:cache_preparation[k] for k in ['status','allowed_roles','subject_count','trial_count','source_file_count','query_windows_read','validation_windows_read','final_cohort_access']},'CSP_output_manifest':{'path':str(REPO/csp_manifest_path),'files':csp_manifest['files_count'],'bytes':csp_manifest['total_bytes'],'scope':'253run02 outputs:240 fitted model NPZ,6 selected feature/score NPZ,6subject JSON,1measurement JSON. Distinct from the253source-file manifest.'},'CPU_saved_outputs':{'root':str(CPU),'listed':len(cpu_receipt['outputs']),'fresh_text_hash_failures':sum(r['fresh_text_hash_matches'] is False for r in artifacts),'missing':sum(not r['exists'] for r in artifacts),'array_content_not_loaded':True},'saved_small_result_sources':saved,'configuration':{'preprocessing':config['preprocessing'],'split':config['split'],'baseline':config['baseline'],'seed':config['seed']},'code_reuse_sources':code,'existing_gate_limits_unchanged':old_limits,'CSP_input_binding_scope':binding['scope'],'runtime':json.loads(environment),'resources':{'workspace_total_bytes':disk.total,'workspace_free_bytes':disk.free,'tmp_free_bytes':tmp.free,'tmp_note':'Separate /tmp mount; do not treat it as persistent workspace or move outputs to bypass the2GiB disk guard.','host_MemAvailable_bytes':meminfo['MemAvailable'],'cgroup_memory_limit_bytes':cgroup_limit,'cgroup_memory_current_bytes':cgroup_current,'cgroup_headroom_bytes':cgroup_limit-cgroup_current,'no_swap':meminfo.get('SwapTotal',0)==0},'memory_estimates':memory,'sources':SOURCES,'no_new_execution_authorization_asserted':True}
    (OUT/'inventory_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'files':len(source_inventory),'missing':result['source_selection']['missing'],'EDF':result['source_selection']['EDF'],'metadata_hash_failures':result['source_selection']['metadata_fresh_official_hash_failures'],'events':result['BIDS_event_tables'],'workspace_free_bytes':disk.free,'cache_subjects':len(cache_subjects),'output':str(OUT/'inventory_manifest.json')},ensure_ascii=False))


if __name__ == '__main__':
    main()
