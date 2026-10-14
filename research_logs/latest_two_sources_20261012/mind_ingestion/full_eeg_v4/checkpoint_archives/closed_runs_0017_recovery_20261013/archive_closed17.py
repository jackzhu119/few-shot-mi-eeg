"""Freeze and fully verify the first seventeen immutable MIND run closures."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path('/workspace/few-shot-mi-eeg')
LOG = REPO / 'research_logs/latest_two_sources_20261012/mind_ingestion/full_eeg_v4'
BASE = LOG / 'checkpoint_archives/closed_runs_0017_recovery_20261013'
PAYLOAD = BASE / 'payload'
PREFIX = 'few-shot-mi-eeg/datasets/mind2026/sciencedb34326/V4/eeg-only/audit_checkpoints/closed_runs_0017_recovery_20261013'
LAUNCHED_VERSION = '1791904057367078765'
sys.path.insert(0, str(REPO / 'scripts'))
from fetch_mind2026_r2 import checked_audit_pair, load_json, now, run_closed, safe_error_code
from sync_research_r2 import build_client, file_digest, make_plan, response_status, transfer_file, write_receipt


def immutable(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2).encode() + b'\n'
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def freeze() -> dict:
    if PAYLOAD.exists():
        raise FileExistsError('Prior checkpoint payload is preserved')
    expected = [f'sub-{subject:02d}_task-mi2d_run-{run:02d}'
                for subject in range(1, 7) for run in range(1, 4)][:17]
    selected = []
    guards = []
    events_total = 0
    signal_bytes = 0
    for name in expected:
        run_log = LOG / 'runs' / name
        closed = load_json(run_log / 'closed.json')
        if (closed.get('run_name') != name or closed.get('status') != 'completed'
                or not closed.get('all_sources_official_size_md5_pass')
                or not closed.get('all_objects_head_and_full_get_sha256_pass')):
            raise ValueError('Closed-run completion flags differ')
        sources = {relative: load_json(LOG / 'source_receipts' / (relative + '.json'))
                   for relative in closed['source_relative_paths']}
        remotes = {relative: load_json(LOG / 'r2_receipts' / (relative + '.json'))
                   for relative in closed['source_relative_paths']}
        signal_paths = [relative for relative in sources if relative.endswith('_eeg.eeg')]
        if len(signal_paths) != 1 or not run_closed(closed, sources, remotes):
            raise ValueError('Run source/R2 closure guard failed')
        signal = signal_paths[0]
        pair = checked_audit_pair(run_log, sources[signal], publish_receipt=False)
        if closed.get('source_audit_pair') and closed['source_audit_pair'] != pair:
            raise ValueError('Closed run differs from audit/event completion pair')
        if closed.get('files') != [remotes[relative] for relative in closed['source_relative_paths']]:
            raise ValueError('Embedded closure receipts differ from immutable R2 receipts')
        owner = load_json(LOG / 'cache_ownership' / (signal + '.json'))
        if (owner.get('relative_path') != signal
                or owner.get('source_record') != sources[signal]['record']
                or owner.get('cache_created_by_this_task') is not True):
            raise ValueError('Closed signal ownership identity differs')
        for artifact in ['closed.json', 'audit.json', 'source_events.json', 'audit_pair_closed.json']:
            selected.append((run_log / artifact, 'ingestion/runs/' + name + '/' + artifact))
        for kind in ['source_receipts', 'r2_receipts', 'cache_ownership']:
            selected.append((LOG / kind / (signal + '.json'), 'ingestion/' + kind + '/' + signal + '.json'))
        guards.append({'run_name': name, 'closed_at_utc': closed['closed_at_utc'],
                       'run_closed_guard_pass': True, 'checked_audit_pair_pass': True,
                       'pair_embedded_in_legacy_closure': bool(closed.get('source_audit_pair')),
                       'pair_equals_closed_pair_when_present': True, 'embedded_r2_receipts_equal': True,
                       'closed_signal_ownership_pass': True, 'source_binary_sha256': sources[signal]['sha256'],
                       'source_signal_bytes': sources[signal]['bytes'],
                       'source_event_count': pair['source_event_count'],
                       'source_relative_paths': closed['source_relative_paths']})
        signal_bytes += sources[signal]['bytes']
        events_total += pair['source_event_count']
    launch = load_json(LOG / 'provenance/detached_recovery_restart_1791904056597373246.json')
    for relative, field in [('scripts/fetch_mind2026_r2.py', 'fetch_sha256'),
                            ('scripts/audit_mind_source.py', 'audit_sha256'),
                            ('tests/test_mind_source_ingestion.py', 'test_sha256')]:
        if file_digest(REPO / relative)[0] != launch[field]:
            raise ValueError('Current executable differs from launched recovery identity')
        selected.append((REPO / relative, relative))
    supervisor = LOG / 'provenance/supervise_transport_retries_recovery_1791904056597373246.py'
    if file_digest(supervisor)[0] != launch['supervisor_sha256']:
        raise ValueError('Recovery supervisor differs from launch identity')
    selected.append((REPO / 'scripts/sync_research_r2.py', 'scripts/sync_research_r2.py'))
    for fixed in ['plan.json', 'supervisor_output_1791810777628224831.jsonl']:
        selected.append((LOG / fixed, 'ingestion/' + fixed))
    for kind in ['provenance', 'failures', 'supervisor_journal']:
        for path in sorted((LOG / kind).glob('*')):
            if path.is_file():
                selected.append((path, 'ingestion/' + path.relative_to(LOG).as_posix()))
    versions = sorted(p for p in (LOG / 'execution_versions').iterdir()
                      if p.is_dir() and p.name <= LAUNCHED_VERSION)
    if not versions or versions[-1].name != LAUNCHED_VERSION:
        raise ValueError('Launched execution snapshot is missing')
    for version in versions:
        for path in sorted(version.iterdir()):
            if path.is_file():
                selected.append((path, 'ingestion/' + path.relative_to(LOG).as_posix()))
    representative = REPO / 'research_logs/latest_two_sources_20261012/mind_ingestion/representative_gate_v3/audit.json'
    selected.append((representative, 'representative_gate_v3/audit.json'))
    selected.append((Path(__file__), 'archive_helpers/archive_closed17.py'))
    if len({relative for _, relative in selected}) != len(selected):
        raise ValueError('Snapshot selection has duplicate paths')
    manifest = []
    for source, relative in selected:
        if source.is_symlink() or not source.is_file():
            raise ValueError('Snapshot source must be a regular file')
        before = file_digest(source)
        target = PAYLOAD / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            with source.open('rb') as reader:
                shutil.copyfileobj(reader, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if file_digest(source) != before or file_digest(target) != before:
            raise ValueError('Snapshot source changed during freeze')
        manifest.append({'source_repo_relative_path': source.relative_to(REPO).as_posix(),
                         'archive_relative_path': relative, 'sha256': before[0], 'bytes': before[1]})
    validation = {'schema_version': 1, 'validated_at_utc': now(), 'status': 'closed_17_guards_passed',
                  'scope': 'exact first 17 closed runs; not the complete 90-run census',
                  'closed_runs': 17, 'planned_census_runs': 90, 'source_events': events_total,
                  'closed_signal_bytes': signal_bytes, 'closed_run_names': expected,
                  'launched_execution_version': LAUNCHED_VERSION,
                  'execution_versions_frozen': [p.name for p in versions], 'run_guards': guards,
                  'active_state_or_partial_read': False, 'live_supervisor_output_read': False,
                  'source_or_cache_deleted': False, 'original_artifacts_overwritten': False,
                  'credential_values_logged': False}
    immutable(PAYLOAD / 'snapshot_validation.json', validation)
    immutable(PAYLOAD / 'source_hash_manifest.json',
              {'schema_version': 1, 'frozen_at_utc': now(), 'source_files': manifest,
               'source_files_count': len(manifest), 'source_bytes': sum(x['bytes'] for x in manifest),
               'all_source_and_copy_hashes_equal': True, 'credential_values_logged': False})
    immutable(PAYLOAD / 'archive_launch.json',
              {'schema_version': 1, 'launched_at_utc': now(), 'operation': 'immutable closed17 checkpoint archive',
               'helper_sha256': file_digest(Path(__file__))[0], 'uploader_sha256': file_digest(REPO / 'scripts/sync_research_r2.py')[0],
               'source_git_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, check=True,
                                                    capture_output=True, text=True).stdout.strip(),
               'python_version': sys.version, 'workers': 4, 'full_get_every_object': True,
               'remote_overwrite_enabled': False, 'credential_values_logged': False})
    return validation


def transfer_one(client, bucket, entry: dict) -> dict:
    try:
        result = transfer_file(client, bucket, PAYLOAD / entry['relative_path'], entry)
        if (result.get('verification') != 'full_get_sha256_verified'
                or result.get('get_http_status') != 200
                or result.get('readback_bytes') != entry['bytes']):
            raise ValueError('Checkpoint full GET did not close')
    except Exception as error:
        result = {**entry, 'status': 'failed', 'error_type': type(error).__name__,
                  'error_code': safe_error_code(error), 'finished_at_utc': now(),
                  'credential_values_logged': False}
    immutable(BASE / 'object_receipts' / (entry['relative_path'] + '.json'), result)
    return result


def main() -> int:
    try:
        validation = freeze()
        client, bucket, sdk = build_client()
        head_time = now()
        head = client.head_bucket(Bucket=bucket)
        status = response_status(head)
        prerequisite = {'checked_at_utc': head_time, 'operation': 'HeadBucket', 'http_status': status,
                        'boto3_version': sdk, 'credential_values_logged': False, 'tls_verification_enabled': True}
        immutable(PAYLOAD / 'r2_prerequisite.json', prerequisite)
        if status != 200:
            raise ValueError('Fresh actual HeadBucket HTTP 200 required')
        records = make_plan(PAYLOAD, PREFIX, 'all')
        receipt = {'schema_version': 1, 'started_at_utc': now(), 'source_root': str(PAYLOAD),
                   'key_prefix': PREFIX, 'status': 'transferring', 'workers': 4,
                   'script_sha256': file_digest(REPO / 'scripts/sync_research_r2.py')[0],
                   'helper_sha256': file_digest(Path(__file__))[0], 'boto3_version': sdk,
                   'readback_mode': 'all', 'full_readback_selection': 'all files',
                   'immutable_create': 'IfNoneMatch=* on PutObject and CompleteMultipartUpload',
                   'existing_reuse_requires': 'HEAD length/SHA256 metadata plus full GET SHA256',
                   'etag_is_not_a_sha256': True, 'credential_values_logged': False,
                   'remote_overwrite_enabled': False, 'closed_runs': 17,
                   'planned_census_runs': 90, 'census_complete': False,
                   'r2_head_bucket_prerequisite': prerequisite, 'files': records}
        receipt_path = BASE / 'checkpoint_archive_receipt.json'
        write_receipt(receipt_path, receipt)
        indexes = {entry['key']: i for i, entry in enumerate(records)}
        with ThreadPoolExecutor(max_workers=4) as pool:
            tasks = [pool.submit(transfer_one, client, bucket, entry) for entry in records]
            for number, task in enumerate(as_completed(tasks), 1):
                result = task.result()
                records[indexes[result['key']]] = result
                write_receipt(receipt_path, receipt)
                if number % 50 == 0 or number == len(records) or result['status'] == 'failed':
                    print(json.dumps({'completed_objects': number, **receipt['totals']}), flush=True)
        receipt['status'] = 'failed' if receipt['totals']['failed_files'] else 'completed'
        receipt['finished_at_utc'] = now()
        receipt['planned_files'] = receipt['totals']['planned_files']
        receipt['verified_files'] = receipt['totals']['verified_files']
        write_receipt(receipt_path, receipt)
        if receipt['status'] != 'completed':
            return 1
        digest, size = file_digest(receipt_path)
        entry = {'relative_path': receipt_path.name, 'key': PREFIX + '/' + receipt_path.name,
                 'sha256': digest, 'bytes': size, 'selected_for_full_readback': True, 'status': 'planned'}
        closing = transfer_file(client, bucket, receipt_path, entry)
        if closing.get('verification') != 'full_get_sha256_verified' or closing.get('readback_bytes') != size:
            raise ValueError('Closing envelope full GET did not close')
        closing_path = BASE / 'closing_envelope_full_get_receipt.json'
        immutable(closing_path, closing)
        digest, size = file_digest(closing_path)
        entry = {'relative_path': closing_path.name, 'key': PREFIX + '/' + closing_path.name,
                 'sha256': digest, 'bytes': size, 'selected_for_full_readback': True, 'status': 'planned'}
        closing_receipt_archive = transfer_file(client, bucket, closing_path, entry)
        if closing_receipt_archive.get('verification') != 'full_get_sha256_verified' or closing_receipt_archive.get('readback_bytes') != size:
            raise ValueError('Closing full-GET receipt archive did not close')
        immutable(BASE / 'closing_full_get_receipt_archive_receipt.json', closing_receipt_archive)
        print(json.dumps({'status': 'completed', 'closed_runs': validation['closed_runs'],
                          'source_events': validation['source_events'], 'finished_at_utc': now(),
                          **receipt['totals'], 'closing_envelope_full_get_verified': True,
                          'closing_full_get_receipt_archived': True}), flush=True)
        return 0
    except Exception as error:
        failure = {'status': 'failed_preserved_snapshot', 'failed_at_utc': now(),
                   'error_type': type(error).__name__, 'error_code': safe_error_code(error),
                   'exception_message_logged': False, 'credential_values_logged': False,
                   'source_or_cache_deleted': False, 'original_artifacts_overwritten': False}
        failure_path = BASE / ('archive_failure_' + str(os.getpid()) + '.json')
        if not failure_path.exists():
            immutable(failure_path, failure)
        print(json.dumps(failure), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
