#!/usr/bin/env python3
"""Independent pinned-source crosscheck; no production helpers are imported.

Run only after full source download and full production source audit complete.
All source bytes and original task tables are recomputed. Full signal scans are
independently repeated for numeric-first/last native files, serially in blocks.
This is source acceptance evidence, not modeling or a biological-ID guarantee.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import mne
import numpy as np

ROOT = Path('/workspace/few-shot-mi-eeg')
LOG = ROOT / 'research_logs/public_data_expansion_20261010'
POLICIES = {
    'leeuwis': {'id': 'nm000327', 'version': 'v1.0.0', 'n': 55, 'signals': 220,
                'bytes': 568544461, 'files': 2095, 'sfreq': 250, 'suffix': '.edf',
                'plan_sha': '9c237adc6a1fbed3c918309bbf7b5957da5d2b31b0f21c0616aa422bac90719b',
                'channels': ['F3', 'Fz', 'F4', 'FC5', 'FC1', 'FC2', 'FC6', 'T7',
                             'C3', 'C4', 'Cz', 'T8', 'CP5', 'CP1', 'CP2', 'CP6'],
                'labels': {'EDGE boundary': 1, 'left_hand': 2, 'right_hand': 3},
                'native_unit': 'µV', 'sidecar_unit': 'µV'},
    'liu2024': {'id': 'nm000158', 'version': 'v1.0.3', 'n': 50, 'signals': 50,
                'bytes': 697479742, 'files': 556, 'sfreq': 500, 'suffix': '.bdf',
                'plan_sha': '8934f650f7adf7b2e64406cfb5b29bdaca893042c29acd271a95f08c7b4b8a2d',
                'channels': ['FP1', 'FP2', 'Fz', 'F3', 'F4', 'F7', 'F8', 'FCz',
                             'FC3', 'FC4', 'FT7', 'FT8', 'Cz', 'C3', 'C4', 'T3',
                             'T4', 'CP3', 'CP4', 'TP7', 'TP8', 'Pz', 'P3', 'P4',
                             'T5', 'T6', 'Oz', 'O1', 'O2'],
                'labels': {'left_hand': 1, 'right_hand': 2},
                'native_unit': 'µV', 'sidecar_unit': 'V'},
}


def check(condition, description):
    if not condition:
        raise ValueError(description)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def table(path, delimiter='\t'):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


def source_bytes(path, declared):
    check(path.is_file(), f'Missing selected official source: {path}')
    size = path.stat().st_size
    check(size == declared['size'], f'Official length differs: {path}')
    algorithm = declared['checksum_algorithm']
    actual = hashlib.sha256()
    if algorithm == 'git':
        official = hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
    else:
        check(algorithm in {'sha256', 'sha1'}, 'Unsupported official hash algorithm')
        official = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            actual.update(block)
            official.update(block)
    check(official.hexdigest() == declared['checksum'], f'Official hash differs: {path}')
    return {'path': declared['path'], 'bytes': size, 'actual_sha256': actual.hexdigest(),
            'official_algorithm': algorithm, 'official_hash': official.hexdigest()}


def header(path, policy):
    # Parse original EDF/BDF header independently of MNE and production receipts.
    with path.open('rb') as stream:
        initial = stream.read(256)
        count = int(initial[252:256])
        extra = stream.read(256 * count)
    check(int(initial[184:192]) == 256 * (count + 1), 'Unexpected native header bytes')
    records, record_seconds = int(initial[236:244]), Decimal(initial[244:252].decode().strip())
    check(records > 0 and record_seconds > 0, 'Undefined native record length/count')
    labels = [extra[16*i:16*(i+1)].decode().strip() for i in range(count)]
    units = [extra[96*count+8*i:96*count+8*(i+1)].decode().strip().replace('uV', 'µV')
             for i in range(count)]
    samples = [int(extra[216*count+8*i:216*count+8*(i+1)]) for i in range(count)]
    eeg = [i for i, label in enumerate(labels) if label not in {'EDF Annotations', 'BDF Annotations'}]
    check([labels[i] for i in eeg] == policy['channels'], 'Native EEG order/count differs')
    check({units[i] for i in eeg} == {policy['native_unit']}, 'Unexpected physical header unit')
    check(all(Decimal(samples[i]) / record_seconds == policy['sfreq'] for i in eeg),
          'Native EEG sample rate differs')
    check(len({samples[i] for i in eeg}) == 1, 'Native EEG channel sample counts differ')
    return {'n_times': records * samples[eeg[0]], 'n_channels': len(eeg),
            'sfreq': policy['sfreq'], 'native_units': sorted({units[i] for i in eeg}),
            'data_records': records, 'record_seconds': str(record_seconds)}


def original_events(root, relative, native, policy, resource):
    prefix = relative.removesuffix('_eeg' + policy['suffix'])
    rows = table(root / (prefix + '_events.tsv'))
    meta = load(root / (prefix + '_events.json'))
    eeg_meta = load(root / (prefix + '_eeg.json'))
    channels = table(root / (prefix + '_channels.tsv'))
    check(meta['onset']['Units'] == meta['duration']['Units'] == 's'
          and 'First sample is 0' in meta['sample']['Description'], 'Source time units/origin differ')
    check(eeg_meta['SamplingFrequency'] == policy['sfreq']
          and eeg_meta['EEGChannelCount'] == len(policy['channels']), 'Metadata rate/count differs')
    check([c['name'] for c in channels] == policy['channels'], 'TSV channel order differs')
    check(all(c['type'] == 'EEG' and float(c['sampling_frequency']) == policy['sfreq']
              and c['units'] == policy['sidecar_unit'] for c in channels), 'TSV unit/rate/type differs')
    subject, session = relative.split('/')[:2]
    parsed = []
    for rownum, row in enumerate(rows, 1):
        label, value = row['trial_type'], int(row['value'])
        check(label in policy['labels'] and policy['labels'][label] == value, 'Source label/code differs')
        onset, duration = Decimal(row['onset']), Decimal(row['duration'])
        sample = int(row['sample'])
        n_duration = duration * policy['sfreq']
        check(onset.is_finite() and duration.is_finite() and onset >= 0 and duration >= 0,
              'Invalid source time')
        check(onset * policy['sfreq'] == sample and n_duration == n_duration.to_integral_value(),
              'Source times do not identify integer samples')
        stop = sample + int(n_duration)
        check(0 <= sample < native['n_times'] and stop <= native['n_times'], 'Source event out of native bounds')
        check((label == 'EDGE boundary') == (duration == 0), 'Unexpected zero duration/boundary')
        if parsed:
            check(sample > parsed[-1]['start_sample'], 'Source samples not strictly ordered')
        parsed.append({'source_file': relative, 'source_row': rownum, 'subject': subject,
                       'session': session, 'label': label, 'stored_value': value,
                       'onset_seconds': float(onset), 'duration_seconds': float(duration),
                       'start_sample': sample, 'stop_sample_exclusive': stop,
                       'duration_samples': int(n_duration)})
    tasks = [e for e in parsed if e['duration_samples'] > 0]
    check(len(tasks) == 40 and Counter(e['label'] for e in tasks) == {'left_hand': 20, 'right_hand': 20},
          'Expected source tasks/classes differ')
    for first, following in zip(tasks, tasks[1:]):
        check(first['stop_sample_exclusive'] <= following['start_sample'], 'Task windows overlap')
    if resource == 'leeuwis':
        edges = [e['start_sample'] for e in parsed if e['label'] == 'EDGE boundary']
        check(len(edges) == 39 and len(parsed) == 79, 'Expected concatenation boundary count differs')
        boundaries = [0] + edges + [native['n_times']]
        for trialnum, (task, begin, end) in enumerate(zip(tasks, boundaries, boundaries[1:]), 1):
            check(end - begin == 2000 and task['start_sample'] - begin == 749
                  and task['duration_samples'] == 1249 and task['duration_seconds'] == 4.996
                  and task['stop_sample_exclusive'] <= end, 'Stored segment/cue/window differs')
            task.update(trial_number_in_run=trialnum, segment_start_sample=begin,
                        segment_stop_sample_exclusive=end, segment_sample_count=end-begin,
                        cue_sample_within_segment=task['start_sample']-begin,
                        samples_after_source_event=end-task['stop_sample_exclusive'])
    else:
        check(len(parsed) == 40 and all(e['duration_samples'] == 2000
                                       and e['duration_seconds'] == 4 for e in tasks), 'Liu task lengths differ')
        check(all(a['label'] != b['label'] for a, b in zip(tasks, tasks[1:])),
              'Liu temporal alternation differs')
    return parsed


def regroup(records, hash_field, identity):
    by_hash = defaultdict(list)
    for item in records:
        if item.get(hash_field):
            by_hash[item[hash_field]].append(item)
    return [{'numeric_sha256': digest, 'identities': sorted(e[identity] for e in group),
             'subjects': sorted({e.get('subject', e['source_file'].split('/')[0]) for e in group}),
             'cross_subject': len({e.get('subject', e['source_file'].split('/')[0]) for e in group}) > 1,
             'labels': sorted({e.get('label', 'continuous') for e in group})}
            for digest, group in sorted(by_hash.items()) if len(group) > 1]


def native_repeat(root, relative, events, run, policy, resource):
    reader = mne.io.read_raw_edf if resource == 'leeuwis' else mne.io.read_raw_bdf
    raw = reader(root / relative, preload=False, verbose='ERROR')
    try:
        check(raw.n_times == run['n_times'] and raw.info['sfreq'] == policy['sfreq']
              and raw.ch_names == policy['channels'] and raw.first_samp == 0, 'MNE/header/run identity differs')
        check(raw.get_channel_types() == ['eeg'] * len(policy['channels']), 'MNE EEG types differ')
        check(set(raw._orig_units.values()) == {policy['native_unit']}, 'MNE physical unit differs')
        check(len(raw.annotations) == len(events), 'Native annotation row count differs')
        check(list(raw.annotations.description) == [e['label'] for e in events], 'Native labels differ')
        for i, e in enumerate(events):
            check(abs(raw.annotations.onset[i] - e['onset_seconds']) <= 1e-6
                  and abs(raw.annotations.duration[i] - e['duration_seconds']) <= 1e-6,
                  'Native annotation time differs')
        full = hashlib.sha256()
        count = 0
        for begin in range(0, raw.n_times, 16384):
            block = raw.get_data(start=begin, stop=min(begin + 16384, raw.n_times))
            check(np.isfinite(block).all(), 'Nonfinite native continuous value')
            full.update(np.array(block, dtype='<f8', order='C').tobytes())
            count += int(block.size)
        center = max(0, raw.n_times // 2 - 128)
        central = raw.get_data(picks=[0, 1], start=center, stop=center + 256)
        fingerprint = hashlib.sha256(np.array(central, dtype='<f8', order='C').tobytes()).hexdigest()
        central_field = 'central_4KiB_numeric_sha256' if resource == 'leeuwis' else 'central4KiB_numeric_sha256'
        check(full.hexdigest() == run['whole_signal_numeric_sha256'] and fingerprint == run[central_field],
              'Independent native signal hash differs')
        check(count == run['continuous_numeric_values'] and run['all_continuous_samples_finite'],
              'Independent continuous scan count/status differs')
        task_hashes = {}
        for e in events:
            if e['duration_samples']:
                block = raw.get_data(start=e['start_sample'], stop=e['stop_sample_exclusive'])
                digest = hashlib.sha256(np.array(block, dtype='<f8', order='C').tobytes()).hexdigest()
                if e.get('published_task_hash'):
                    check(digest == e['published_task_hash'], 'Independent task numeric hash differs')
                task_hashes[str(e['source_row'])] = digest
        return {'source_file': relative, 'n_times': int(raw.n_times), 'channel_count': len(raw.ch_names),
                'whole_signal_numeric_sha256': full.hexdigest(), 'central4KiB_numeric_sha256': fingerprint,
                'continuous_numeric_values': count, 'all_continuous_samples_finite': True,
                'annotations_equal_original_TSV': True, 'task_window_hashes': task_hashes,
                'native_physical_unit': policy['native_unit'], 'MNE_numeric_unit': 'V',
                'automatic_MNE_unit_factor_to_V': 1e-6, 'manual_rescaling_performed': False}
    finally:
        raw.close()


def original_sidecars():
    resource_log = LOG / 'leeuwis_ingestion'
    receipt = load(resource_log / 'original_non_eeg_sidecars_download_receipt.json')
    official_path = resource_log / 'original_dataverse_dataset_metadata.json'
    check(sha(official_path) == receipt['official_metadata_sha256'], 'Original Dataverse metadata changed')
    official = load(official_path)['data']['latestVersion']
    check((official['versionNumber'], official['versionMinorNumber']) == (1, 0)
          and 'https://creativecommons.org/licenses/by/4.0/' in official['termsOfUse'],
          'Original release/license differs')
    official_files = {item['dataFile']['id']: item['dataFile'] for item in official['files']}
    root = ROOT / receipt['raw_root']
    checked = []
    for item in receipt['files']:
        source = official_files[item['datafile_id']]
        data = (root / source['filename']).read_bytes()
        check(len(data) == source['filesize'] == item['official_size']
              and source['checksum']['type'] == 'SHA-1'
              and hashlib.sha1(data).hexdigest() == source['checksum']['value'] == item['official_checksum']
              and hashlib.sha256(data).hexdigest() == item['actual_sha256'], 'Original sidecar bytes differ')
        checked.append({'path': source['filename'], 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    check(len(checked) == 4 and sum(e['bytes'] for e in checked) == 10508553, 'Original sidecar scope differs')
    adapter = LOG / 'large_training_metadata/leeuwis2021_upstream_adapter.py'
    assignments = [node for node in ast.parse(adapter.read_text()).body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == '_FILE_IDS' for t in node.targets)]
    check(len(assignments) == 1, 'Explicit upstream original ID map unavailable')
    ids = ast.literal_eval(assignments[0].value)
    mapping = []
    for index, (original, fileids) in enumerate(ids.items(), 1):
        check(len(fileids) == 4, 'Expected original run file count differs')
        filenames = [official_files[fileid]['filename'] for fileid in fileids]
        for name in filenames:
            match = re.match(r'(?:Subject|S)(\d+)_eeg_', name)
            check(match is not None and int(match[1]) == original, 'Exact original filename ID differs')
        mapping.append({'nemar_subject': f'sub-{index}', 'original_subject_id': original,
                        'original_filenames': filenames})
    questionnaires = table(root / 'Questionnaires.csv', ',')
    check(len(questionnaires) == 55 and {int(e['ppnr']) for e in questionnaires} == set(ids),
          'Questionnaire original IDs differ from mapped resource')
    ages = [float(e['Age']) for e in questionnaires]
    check(all(np.isfinite(ages)) and min(ages) == 18 and max(ages) == 39, 'Original individual ages differ')
    curves = table(root / 'BCI_OnlineClassificationErrors.csv', ',')
    keys = {(e['subject'], e['run'], e['lr']) for e in curves}
    check(len(curves) == len(keys) == 480, 'Online curve unique keys/count differs')
    subjects = {int(re.fullmatch(r'Subject (\d+)', e['subject'])[1]) for e in curves}
    check(len(subjects) == 60 and subjects - set(ids) == {2, 6, 20, 35, 64}, 'Online extra ID set differs')
    check({e['run'] for e in curves} == {'Calibration', 'Run1', 'Run2', 'Run3'}
          and {e['lr'] for e in curves} == {'L', 'R'}, 'Online curve run/hand labels differ')
    total, low, high = 0, float('inf'), float('-inf')
    for row in curves:
        values = [float(value) for field, value in row.items() if field not in {'subject', 'run', 'lr'}]
        check(len(values) == 2000 and np.isfinite(values).all() and 0 <= min(values) <= max(values) <= 100,
              'Online source percentage values invalid')
        total += len(values)
        low, high = min(low, min(values)), max(high, max(values))
    original_readme = (root / 'readme.txt').read_text()
    check('average of the 20 trials' in original_readme and '2000 datapoints' in original_readme
          and 'no feedback was provided' in original_readme, 'Original curve/calibration definition differs')
    return {'files': checked, 'original_id_mapping': mapping, 'questionnaire_rows': len(questionnaires),
            'original_individual_age_range': [min(ages), max(ages)],
            'original_gender_counts': dict(Counter(e['Gender'] for e in questionnaires)),
            'online_curve_rows': len(curves), 'online_curve_resource_IDs': len(subjects),
            'selected_EEG_matching_curve_rows': sum(int(e['subject'].split()[1]) in ids for e in curves),
            'extra_non_EEG_original_IDs': sorted(subjects - set(ids)),
            'online_curve_values': total, 'online_curve_percent_range': [low, high],
            'curves_are_trial_outcomes': False, 'original_signals_or_markers_read': False,
            'calibration_feedback_mapping_from_source_readme': {'Calibration': 'no feedback',
                                                               '2': 'feedback1', '3': 'feedback2', '4': 'feedback3'},
            'adapter_sha256': sha(adapter), 'official_metadata_sha256': sha(official_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resource', choices=POLICIES, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--audit-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.data_root = args.data_root.resolve()
    args.audit_root = args.audit_root.resolve()
    args.output = args.output.resolve()
    started = datetime.now(timezone.utc).isoformat()
    policy = POLICIES[args.resource]
    resource_log = LOG / (args.resource + '_ingestion')
    plan_path = resource_log / 'ingestion_plan.json'
    check(sha(plan_path) == policy['plan_sha'], 'Pinned ingestion plan changed')
    plan = load(plan_path)
    check((plan['nemar_id'], plan['version'], plan['license']) == (policy['id'], policy['version'], 'CC-BY-4.0'),
          'Pinned resource identity/license changed')
    selection_path = ROOT / plan['selection_manifest_path']
    official_path = LOG / 'large_training_metadata' / policy['id'] / 'manifest.json'
    check(sha(selection_path) == plan['selection_manifest_sha256']
          and sha(official_path) == plan['official_manifest_sha256'], 'Pinned manifest changed')
    selection, official = load(selection_path), load(official_path)
    official_by_path = {e['path']: e for e in official}
    check(len(official_by_path) == len(official), 'Duplicate official source path')
    check(len(selection) == policy['files'] and sum(e['size'] for e in selection) == policy['bytes']
          and len({e['path'] for e in selection}) == len(selection), 'Planned selection count/bytes differs')
    check(all(e == official_by_path.get(e['path']) for e in selection), 'Selection differs from full official manifest')
    inventory = []
    for item in selection:
        relative = Path(item['path'])
        check(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe source path')
        inventory.append(source_bytes(args.data_root / relative, item))
    signals = [e['path'] for e in selection if e['path'].endswith(policy['suffix'])]
    check(len(signals) == policy['signals'], 'Signal scope differs')
    subjects = {name.split('/')[0] for name in signals}
    check(subjects == {f'sub-{i}' for i in range(1, policy['n'] + 1)}, 'Published resource IDs differ')
    participants = table(args.data_root / 'participants.tsv')
    check(len(participants) == policy['n'] and {e['participant_id'] for e in participants} == subjects,
          'Participant source rows do not match resource IDs')
    description = load(args.data_root / 'dataset_description.json')
    check(description['License'] == 'CC-BY-4.0', 'Actual source license differs')
    if args.resource == 'leeuwis':
        summary_path = args.audit_root / 'source_audit_summary.json'
        summary = load(summary_path)
        check(summary['source_acceptance_complete'] and summary['passed_run_count'] == 220
              and summary['verified_source_file_count'] == policy['files']
              and summary['verified_source_bytes'] == policy['bytes'], 'Production full resource gate incomplete')
        runs = load(args.audit_root / 'continuous_run_ledger.json')
        published_events = load(args.audit_root / 'source_event_ledger.json')
        task_identity_field = 'event_id'
    else:
        summary_path = args.audit_root / 'aggregate.json'
        summary = load(summary_path)
        check(summary['complete'] and not summary['representative_only']
              and summary['passed_signal_files'] == 50, 'Production full Liu resource gate incomplete')
        runs = [load(p) for p in sorted((args.audit_root / 'runs').glob('*.json'))]
        published_events = load(args.audit_root / 'source_events.json')
        task_identity_field = 'source_event_id'
    check(summary['plan_sha256'] == sha(plan_path)
          and summary['selection_manifest_sha256'] == sha(selection_path), 'Production source plan differs')
    run_by_path = {r['source_file']: r for r in runs}
    check(len(run_by_path) == len(signals) and set(run_by_path) == set(signals)
          and all(r['status'] == 'passed' and r['all_continuous_samples_finite'] for r in runs),
          'Production run coverage/status differs')
    published_by_key = {(e['source_file'], e['source_row']): e for e in published_events}
    check(len(published_by_key) == len(published_events), 'Published event IDs duplicated')
    expected_events, header_records, source_by_path = [], [], {}
    for relative in sorted(signals):
        if args.resource == 'leeuwis':
            match = re.fullmatch(r'(sub-\d+)/ses-0/eeg/\1_ses-0_task-imagery_acq-(calib|feedback[123])_run-([0-3])_eeg.edf', relative)
            check(match is not None and {'calib': '0', 'feedback1': '1', 'feedback2': '2', 'feedback3': '3'}[match[2]] == match[3],
                  'Lee run/acquisition identity differs')
        else:
            check(re.fullmatch(r'(sub-\d+)/ses-0/eeg/\1_ses-0_task-imagery_run-0_eeg.bdf', relative),
                  'Liu run/visit identity differs')
        native = header(args.data_root / relative, policy)
        check(native['n_times'] == run_by_path[relative]['n_times'], 'Native header length differs from run ledger')
        header_records.append({'source_file': relative, **native})
        expected = original_events(args.data_root, relative, native, policy, args.resource)
        for e in expected:
            p = published_by_key.get((relative, e['source_row']))
            check(p is not None, 'Original source row missing from published ledger')
            for field in ['source_file', 'source_row', 'subject', 'session', 'label', 'stored_value',
                          'onset_seconds', 'duration_seconds', 'start_sample', 'stop_sample_exclusive']:
                check(p[field] == e[field], f'Original source event field differs: {field}')
            length_field = 'source_duration_sample_count' if args.resource == 'leeuwis' else 'duration_samples_as_stored'
            check(p[length_field] == e['duration_samples'], 'Original source duration sample count differs')
            if e['duration_samples']:
                check(p.get('source_task_numeric_sha256') is not None, 'Full source task numeric ledger unavailable')
                e['published_task_hash'] = p['source_task_numeric_sha256']
                if args.resource == 'leeuwis':
                    for field in ['trial_number_in_run', 'segment_start_sample', 'segment_stop_sample_exclusive',
                                  'segment_sample_count', 'cue_sample_within_segment', 'samples_after_source_event']:
                        check(p[field] == e[field], f'Original segment field differs: {field}')
            expected_events.append(e)
        source_by_path[relative] = expected
    check(len(expected_events) == len(published_events), 'Published event ledger has added or omitted source rows')
    labels = dict(Counter(e['label'] for e in expected_events))
    tasks = [e for e in published_events if e['duration_seconds'] > 0]
    continuous_duplicates = regroup(runs, 'whole_signal_numeric_sha256', 'source_file')
    task_duplicates = regroup(tasks, 'source_task_numeric_sha256', task_identity_field)
    if args.resource == 'leeuwis':
        def normalized(groups):
            return [{**g, 'identities': sorted(g['identities'])} for g in sorted(groups, key=lambda g: g['numeric_sha256'])]
        check(continuous_duplicates == normalized(summary['whole_signal_exact_duplicate_groups'])
              and task_duplicates == normalized(summary['task_window_exact_duplicate_groups']),
              'Published duplicate groups/classification differ')
        check(labels == summary['source_class_counts']
              and len(tasks) == summary['task_event_count'] == 8800, 'Published task counts differ')
    else:
        check(labels == summary['source_label_counts'] and len(expected_events) == summary['source_event_count'] == 2000,
              'Published Liu event counts differ')
        for field in ['whole_signal_numeric_sha256', 'central4KiB_numeric_sha256']:
            actual = [sorted(g['identities']) for g in regroup(runs, field, 'source_file')]
            check(sorted(actual) == sorted(sorted(g) for g in summary['exact_numeric_duplicate_groups'][field]),
                  'Published Liu numeric duplicate groups differ')
        if 'task_window_exact_duplicate_groups' in summary:
            check(sorted(tuple(g['identities']) for g in task_duplicates)
                  == sorted(tuple(sorted(g['identities'])) for g in summary['task_window_exact_duplicate_groups']),
                  'Published Liu source task duplicate groups differ')
    ordered = sorted(signals, key=lambda name: (int(name.split('/')[0].split('-')[1]), name))
    selected = [ordered[0], ordered[-1]]
    repeats = [native_repeat(args.data_root, name, source_by_path[name], run_by_path[name], policy, args.resource)
               for name in selected]
    demographics = {'mirror_age_counts': dict(Counter(e['age'] for e in participants)),
                    'mirror_sex_counts': dict(Counter(e['sex'] for e in participants)),
                    'mirror_age_individual_covariate_usable': False}
    if args.resource == 'leeuwis':
        check(demographics['mirror_age_counts'] == {'20.71': 55}, 'Mirror group-mean placeholder differs')
        demographics['original_sidecars'] = original_sidecars()
    else:
        check(demographics['mirror_age_counts'] == {'71': 50}, 'Mirror repeated age placeholder differs')
    check(not args.output.exists(), 'Independent output must use a new immutable path')
    args.output.mkdir(parents=True)
    write_new(args.output / 'verified_source_files.json', inventory)
    write_new(args.output / 'native_headers.json', header_records)
    review = {'resource': args.resource, 'nemar_id': policy['id'], 'version': policy['version'],
              'complete_independent_source_crosscheck': True,
              'started_at_utc': started, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
              'script_sha256': sha(__file__), 'plan_sha256': sha(plan_path),
              'official_manifest_sha256': sha(official_path), 'selection_manifest_sha256': sha(selection_path),
              'production_summary_sha256': sha(summary_path),
              'production_summary_path': str(summary_path.relative_to(ROOT)),
              'verified_source_files': len(inventory), 'verified_source_bytes': sum(e['bytes'] for e in inventory),
              'verified_signal_native_headers': len(header_records), 'published_resource_IDs': len(subjects),
              'all_original_TSV_rows_independently_compared': len(expected_events), 'source_label_counts': labels,
              'native_signal_full_scan_repeat_selection_rule': 'numeric first ID/first run and last ID/last run',
              'native_signal_full_scan_repeat_files': repeats,
              'native_physical_unit': policy['native_unit'], 'sidecar_declared_unit': policy['sidecar_unit'],
              'known_native_sidecar_unit_conflict': policy['native_unit'] != policy['sidecar_unit'],
              'unit_reconciliation_for_modeling_validated': False,
              'continuous_exact_duplicate_groups_independently_regrouped': continuous_duplicates,
              'task_exact_duplicate_groups_independently_regrouped': task_duplicates,
              'demographics': demographics, 'no_production_helpers_imported': True,
              'native_numeric_finite_scope': 'production all files; independently repeat complete first/last files only',
              'no_models_or_analysis_windows_selected': True,
              'biological_participant_independence_established': False,
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'runtime_versions': {'python': sys.version.split()[0], 'mne': mne.__version__, 'numpy': np.__version__}}
    write_new(args.output / 'independent_source_crosscheck.json', review)
    print(json.dumps({k: review[k] for k in ['resource', 'complete_independent_source_crosscheck',
                                           'verified_source_files', 'verified_source_bytes',
                                           'all_original_TSV_rows_independently_compared',
                                           'known_native_sidecar_unit_conflict']}), flush=True)


if __name__ == '__main__':
    main()
