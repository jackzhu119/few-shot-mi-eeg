"""Read-only audit of one completed frozen query operation; no EEG/tensor API."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/workspace/few-shot-mi-eeg')
BASE = Path('/workspace/private_model_receipts/frozen-query-evaluation-20261015')
STATE = ROOT / 'research_logs/kumar_frozen_query_evaluation_20261015/run01'
OUTPUT = BASE / 'run01/results'
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp(value):
    return dt.datetime.fromisoformat(value).timestamp()


def file_row(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def main():
    contract_path = ROOT / 'configs/kumar_frozen_query_operation_20261015.json'
    contract = read(contract_path)
    claim, launch = read(STATE / 'claim.json'), read(STATE / 'launcher_receipt.json')
    start = read(STATE / 'worker_start.json')
    auth_path = BASE / 'actual_external_authorization.json'
    auth, preflight = read(auth_path), read(BASE / 'metadata_check_before_execute.json')
    host = read(BASE / 'host_resource_preflight.json')
    dispatch, exit_record = read(BASE / 'launcher_dispatch_start.json'), read(BASE / 'launcher_dispatch_exit.json')
    ledger = read(ROOT / 'research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json')
    plan = read(ROOT / 'research_logs/kumar_remaining36_acceptance_20261015/run01/source_model_plan_all54.json')
    originals = read(ROOT / 'configs/kumar_frozen_query_checkpoints_20261015.json')
    inputs = read(ROOT / 'configs/kumar_frozen_query_inputs_20261015.json')
    stage = read(BASE / 'checkpoint_staging_full_get_receipt.json')
    archive_before = read(OUTPUT / 'checkpoint_archive_full_sha256_before.json')
    input_before = read(OUTPUT / 'input_full_sha256_before.json')
    complete, aggregate = read(OUTPUT / 'worker_complete.json'), read(OUTPUT / 'aggregate_summary.json')

    assert sha(contract_path) == claim['contract_sha256'] == auth['contract_sha256'] == 'fb3a429776e77a4ee8de96c8c7f2a833a4d311cedd8f0a9bcec3d0c6e8df225a'
    assert sha(auth_path) == claim['authorization_sha256'] == dispatch['actual_authorization_sha256'] == stage['authorization_sha256'] == '137c42df93f99992e2a04603f0107fb6e02554ed3150566b6a57446069649dca'
    assert auth['reviewed_commit'] == claim['reviewed_commit'] == host['head'] == 'd34703ca5bccf7a5b88a91c2ffb2cba893f7cec8'
    assert auth['status'] == 'parent_reviewed_frozen_checkpoint_query_evaluation_authorized'
    assert auth['scope'] == 'accepted54_always_frozen_query_only' and auth['query_evaluation_authorized'] is True
    assert auth['actual_parent_decision_at_utc'] == '2026-10-15T09:14:00Z'
    assert auth['not_before_unix'] == stamp('2026-10-15T09:14:00Z')
    assert auth['deadline_unix'] == claim['deadline_unix'] == start['deadline_unix'] == stamp('2026-10-15T11:14:00Z')
    assert auth['deadline_unix'] - auth['not_before_unix'] == 7200
    for key in ('training_authorized', 'optimizer_updates_authorized', 'target_support_access_authorized',
                'new_strategy_authorized', 'new_resources_authorized', 'parameter_updates_authorized',
                'BN_updates_authorized', 'normalization_updates_authorized'):
        assert auth[key] is False
    current_host = {'hostname': os.uname().nodename,
                    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    'pid1_start_ticks': Path('/proc/1/stat').read_text().rsplit(')', 1)[1].split()[19]}
    assert current_host == auth['authorized_container_identity'] == claim['container_identity'] == host['identity']
    assert current_host == {'hostname': '94346a2083c4', 'boot_id': '02e1dd56-6faf-45ed-b710-a28705535fb6', 'pid1_start_ticks': '54'}
    assert host['actual_query_state_absent'] and host['actual_output_absent']
    assert preflight['problems'] == [] and preflight['runtime'] == contract['runtime']
    assert preflight['thread_environment'] == contract['thread_environment']
    assert not any(preflight[k] for k in ('query_files_opened', 'checkpoint_archives_opened', 'models_constructed'))
    assert preflight['accepted_models'] == 54 and preflight['query_included_rows'] == 4290
    assert claim['automatic_retries'] == dispatch['automatic_retries'] == 0
    assert claim['output'] == str(OUTPUT)
    assert claim['resource_preflight']['memory']['effective_available_bytes'] >= 3 * 1024**3
    assert claim['resource_preflight']['free_output_disk_bytes'] >= 2 * 1024**3
    for relative, digest in contract['frozen_files'].items():
        assert sha(ROOT / relative) == digest, relative
    for item in inputs['dependencies'] + originals['dependencies']:
        assert (ROOT / item['path']).stat().st_size == item['bytes'] and sha(ROOT / item['path']) == item['sha256']
    assert sha(ROOT / 'research_logs/kumar_development_queue_20261014/accepted_jobs.json') == '1ee1868b97e6ff7ea2e42327fe64337cafbb0f8ee6aff19cc24fba5265f9aaa9'
    assert sha(ROOT / 'research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json') == auth['accepted_ledger_sha256'] == '013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670'

    ids = [j['job_id'] for j in plan['jobs']]
    assert len(ids) == len(set(ids)) == 54
    assert ids == auth['approved_job_ids'] == [e['job_id'] for e in ledger['accepted_jobs']]
    assert ids == [r['job_id'] for r in stage['files']] == [r['job_id'] for r in archive_before['files']]
    assert stage['verified_objects'] == 54 and stage['failed_files'] == []
    assert stage['verified_bytes'] == 12636160 and stage['remote_GET_attempts_per_object_maximum'] == 1
    for entry, manifest, staged, before in zip(ledger['accepted_jobs'], originals['models'], stage['files'], archive_before['files'], strict=True):
        for key in ('job_id', 'result_key', 'sha256', 'bytes'):
            wanted = entry['archive_sha256'] if key == 'sha256' else manifest['archive_bytes'] if key == 'bytes' else entry[key]
            assert staged[key] == before[key] == wanted
        assert staged['get_http_status'] == 200 and staged['verification'] == 'full_GET_original_bytes_SHA256_verified'
        archive = Path(claim['archive_root']) / staged['filename']
        assert archive.stat().st_size == staged['bytes'] and sha(archive) == staged['sha256']
    assert input_before == read(BASE / 'input_full_sha256_prelaunch.json')
    assert input_before['file_count'] == 1189 and input_before['bytes'] == 1043686331
    assert input_before['files'] == [{k: row[k] for k in ('relative_path', 'bytes', 'sha256')} for row in inputs['files']]

    assert launch['status'] == complete['status'] == exit_record['status'] == 'all54_evaluated_pending_independent_audit'
    assert launch['returncode'] == exit_record['actual_exit_code'] == 0 and exit_record['failure'] is None
    assert launch['query_evaluation_completed'] is True and launch['signals'] == [] and launch['new_fits'] == 0
    assert launch['pid'] == start['pid'] == exit_record['worker_pid'] == 23678
    assert claim['launcher_pid'] == dispatch['launcher_pid'] == exit_record['launcher_pid'] == 23665
    assert launch['started_at_utc'] == start['started_at_utc'] == exit_record['worker_start_utc']
    assert read(BASE / 'launcher_stdout.json') == launch
    assert sha(STATE / 'worker.log') == launch['log_sha256'] and (STATE / 'worker.log').stat().st_size == 0
    assert (BASE / 'launcher_stderr.log').stat().st_size == 0
    assert auth['not_before_unix'] <= stamp(auth['published_at_utc']) < stamp(stage['started_at_utc']) < stamp(stage['finished_at_utc']) < stamp(dispatch['launched_at_utc']) < stamp(claim['claimed_at_utc']) <= stamp(launch['launch_attempt_at_utc']) <= stamp(launch['started_at_utc']) < stamp(launch['finished_at_utc']) <= stamp(exit_record['observed_exit_at_utc']) < auth['deadline_unix'] - 30
    for record in (launch, complete):
        assert all(record[k] is False for k in ('accepted', 'independently_audited', 'R2_full_GET_verified'))
    assert complete['new_fits'] == complete['optimizer_instances'] == 0 and complete['query_input_bytes_unchanged']
    assert complete['job_count'] == len(complete['jobs']) == 54 and [r['job_id'] for r in complete['jobs']] == ids

    output_members = {r['path']: r for r in launch['output_members']}
    actual_paths = {str(p.relative_to(OUTPUT)): p for p in OUTPUT.rglob('*') if p.is_file()}
    assert len(output_members) == len(actual_paths) == 76 and output_members.keys() == actual_paths.keys()
    for relative, path in actual_paths.items():
        assert not path.is_symlink() and path.stat().st_size == output_members[relative]['bytes'] and sha(path) == output_members[relative]['sha256']
    assert not list(OUTPUT.rglob('*.partial'))
    observed_query_rows, job_rows = 0, []
    for entry, item, original in zip(ledger['accepted_jobs'], complete['jobs'], originals['models'], strict=True):
        path = OUTPUT / item['path']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
        result = read(path)
        identity = result['identity']
        assert all(identity[key] == entry[key] for key in ('job_id', 'subject', 'seed', 'result_key', 'archive_sha256'))
        assert identity['checkpoint_sha256'] == original['checkpoint_sha256']
        assert result['scope'] == 'accepted54_always_frozen_query_only'
        assert identity['execution_device'] == 'cpu' and identity['synthetic'] is identity['software_validation_only'] is False
        assert result['optimizer_instances_created'] == result['optimizer_steps'] == 0
        assert result['new_fit'] is identity['new_fit'] is result['parameter_BN_normalization_updates'] is False
        assert result['processed_input_hashes_verified'] and result['source_training_context_preserved'] and result['input_files_unchanged']
        assert result['state_before_sha256'] == result['state_after_sha256'] and result['scientific_acceptance_pending']
        assert result['query_labels_used_for'] == 'fixed_metrics_only'
        assert len(result['session_metrics']) == 6
        assert result['query_rows_evaluated'] == result['real_query_rows_loaded'] == len(result['predictions'])
        observed_query_rows += result['query_rows_evaluated']
        job_rows.append({'job_id': identity['job_id'], 'subject': identity['subject'], 'seed': identity['seed'],
                         'checkpoint_sha256': identity['checkpoint_sha256'], 'query_rows': result['query_rows_evaluated'],
                         'state_before_and_after_sha256': result['state_before_sha256'], 'result_sha256': sha(path)})
    for subject in dict.fromkeys(j['subject'] for j in plan['jobs']):
        subject_record = read(OUTPUT / (subject + '-complete.json'))
        assert subject_record['subject'] == subject and subject_record['jobs'] == [r for r in complete['jobs'] if r['subject'] == subject]
    assert observed_query_rows == aggregate['prediction_rows_with_repeated_seeds'] == 12870
    assert aggregate['unique_query_trial_count'] == 4290 and aggregate['job_count'] == 54
    assert len(aggregate['per_participant']) == 18 and len(aggregate['per_participant_session']) == 108 and len(aggregate['per_job_session_metrics']) == 324
    assert aggregate['missing_jobs_or_sessions_dropped'] == 0 and aggregate['seed_selection_performed'] is False

    samples = launch['resource_samples']
    assert len(samples) == 312
    sample_times = [stamp(s['at_utc']) for s in samples]
    assert sample_times == sorted(sample_times) and len(set(sample_times)) == 312
    assert stamp(launch['started_at_utc']) <= sample_times[0] < sample_times[-1] <= stamp(launch['finished_at_utc'])
    for sample in samples:
        assert sample['process_snapshot_method'] == 'visible_procfs_ppid_and_dedicated_session_two_snapshots'
        members = sample['process_tree_members']
        assert sample['process_tree_pids'] == [m['pid'] for m in members] == [23678]
        assert len({m['tgid'] for m in members}) == len(members) == 1
        assert sample['consumer_rss_bytes'] == sum(m['rss_bytes'] for m in members) < 2 * 1024**3
        assert sample['host_available_bytes'] > 1024**3 and sample['cgroup_headroom_bytes'] > 1024**3
        assert sample['proc_visibility']['observer_pid'] == 23665
        for member in members:
            assert member['pid'] == member['tgid'] == member['pgrp'] == member['session'] == 23678
            assert member['ppid'] == 23665 and member['start_ticks'] == 3143298
        assert sample['previously_observed_stably_absent_pids'] == []
    assert not Path('/proc/23665').exists() and not Path('/proc/23678').exists()
    intervals = [b - a for a, b in zip(sample_times, sample_times[1:])]
    resources = {'sample_count': len(samples), 'requested_poll_seconds': 0.25,
                 'actual_sample_interval_seconds_min': min(intervals), 'actual_sample_interval_seconds_max': max(intervals),
                 'maximum_observed_process_tree_RSS_bytes': max(s['consumer_rss_bytes'] for s in samples),
                 'minimum_observed_cgroup_headroom_bytes': min(s['cgroup_headroom_bytes'] for s in samples),
                 'minimum_observed_host_available_bytes': min(s['host_available_bytes'] for s in samples),
                 'worker_start_to_launcher_receipt_finished_seconds': (dt.datetime.fromisoformat(launch['finished_at_utc']) - dt.datetime.fromisoformat(launch['started_at_utc'])).total_seconds(),
                 'launcher_observed_elapsed_seconds': stamp(exit_record['observed_exit_at_utc']) - stamp(dispatch['launched_at_utc']),
                 'observed_process_identities': [{'pid': 23678, 'start_ticks': 3143298, 'tgid': 23678}],
                 'post_exit_launcher_and_worker_absent': True, 'signals_sent': [], 'failure_or_limit_stop_recorded': False}
    evidence = [file_row(p) for p in sorted(STATE.iterdir()) if p.is_file()]
    evidence += [file_row(p) for p in sorted(BASE.iterdir()) if p.is_file()]
    report = {'schema_version': 1, 'status': 'passed_independent_operation_and_saved_output_integrity_audit',
              'reviewer': '/root/run02_result_review', 'audited_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'audit_script_sha256': sha(Path(__file__)), 'execution_commit': claim['reviewed_commit'],
              'operation_contract_sha256': sha(contract_path), 'actual_authorization_sha256': sha(auth_path),
              'launcher_receipt_sha256': sha(STATE / 'launcher_receipt.json'),
              'worker_complete_sha256': sha(OUTPUT / 'worker_complete.json'),
              'authorized_window_utc': ['2026-10-15T09:14:00Z', '2026-10-15T11:14:00Z'],
              'actual_host_identity': current_host, 'actual_worker_start_utc': launch['started_at_utc'],
              'actual_launcher_receipt_finished_utc': launch['finished_at_utc'], 'actual_launcher_exit_utc': exit_record['observed_exit_at_utc'],
              'actual_exit_code': 0, 'automatic_retries': 0, 'original_all54_acceptance_and_old18_ledger_unchanged': True,
              'all_frozen_code_and_metadata_pins_match': True,
              'input_evidence': {'query_files': 1189, 'query_bytes': 1043686331,
                                 'prelaunch_and_worker_full_SHA_records_equal_manifest': True,
                                 'original_archives': 54, 'original_archive_bytes': 12636160,
                                 'all_original_archive_bytes_independently_rehashed_without_unpacking': True,
                                 'staging_full_GET_receipt_matches_exact_accepted_keys': True,
                                 'raw_EEG_or_event_files_opened_by_this_audit': False,
                                 'post_evaluation_input_unchanged_proof': 'Frozen worker repeats full-byte verification and requires equality before writing worker_complete; no separate post-hash receipt was emitted.'},
              'output_evidence': {'files': 76, 'bytes': sum(r['bytes'] for r in output_members.values()),
                                  'model_result_files': 54, 'participant_completion_files': 18,
                                  'summaries_and_input_inventories': 4, 'hash_or_size_failures': 0,
                                  'incomplete_partial_files': 0, 'unique_query_trials': 4290,
                                  'prediction_rows_across_three_seeds': 12870, 'participant_sessions': 108,
                                  'job_session_metrics': 324, 'all_model_state_hashes_before_after_equal': True,
                                  'all54_checkpoint_hashes_match_frozen_original_manifest': True,
                                  'original_pending_audit_R2_and_acceptance_false_flags_preserved': True},
              'resources': resources, 'jobs': job_rows, 'original_evidence_files': evidence,
              'scope_limits': ['This audit performs opaque archive hashing and saved JSON integrity/identity checks, not model tensor loading, raw EEG decoding, new forward passes or training.',
                               'The 312 recorded stable visible procfs snapshots and identity-bound cleanup are audited evidence, not continuous observation of every transient process or independent reconstruction of historical lock ownership.',
                               'Runtime disk checks are enforced by the pinned launcher/worker; per-sample disk values are not persisted, so only explicit preflight disk bytes are numerically rechecked here.',
                               'An empty worker log does not imply no Python execution; 54 model results and complete subject/output receipts provide the execution evidence. The launcher receipt finished_at is an observed completion bound, not a separately sampled exact worker-exit timestamp.',
                               'Scientific metric recalculation and result R2 backup are separate reviews; this operation audit grants no parent acceptance or additional execution.'],
              'audit_new_fits': 0, 'audit_model_forwards': 0, 'audit_tensor_loads': 0,
              'R2_result_backup_verified_by_this_audit': False, 'parent_confirmation_written': False, 'accepted': False}
    destination = HERE / 'operation_independent_review_run01.json'
    with destination.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'audit_file': str(destination), 'audit_sha256': sha(destination),
                      'output_files': 76, 'output_bytes': report['output_evidence']['bytes'], 'resources': resources}))


if __name__ == '__main__':
    main()
