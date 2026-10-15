"""Independent opaque-byte identity audit; no scientific execution/deserialization."""
from __future__ import annotations

import hashlib
import json
import tarfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path('/workspace/few-shot-mi-eeg')
PRIVATE = Path('/workspace/private_model_receipts/frozen-query-evaluation-20261015')
ARCHIVES = Path('/workspace/private_model_receipts/frozen-query-originals-54')
RESULTS = PRIVATE / 'run01/results'
DATA = ROOT / 'data/public_eeg/kumar2024/nm000177/v1.0.5'
OUTPUT = Path(__file__).with_name('identity_archive_input_audit.json')


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve prior audit; no automatic overwrite')
    report = {
        'schema_version': 1, 'status': 'started',
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'script_sha256': digest_file(Path(__file__)), 'checks_passed': 0,
        'failures': [], 'archive_records': [], 'input_records': [], 'metadata_records': [],
        'checkpoint_tensor_deserialization_performed': False,
        'model_forward_or_training_performed': False, 'raw_EEG_decoded': False,
        'R2_actions_performed': False, 'parent_acknowledgement_written': False,
    }

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        report['checks_passed'] += 1

    try:
        checkpoint_path = ROOT / 'configs/kumar_frozen_query_checkpoints_20261015.json'
        inputs_path = ROOT / 'configs/kumar_frozen_query_inputs_20261015.json'
        contract_path = ROOT / 'configs/kumar_frozen_query_operation_20261015.json'
        checkpoint = json.loads(checkpoint_path.read_bytes())
        inputs = json.loads(inputs_path.read_bytes())
        contract = json.loads(contract_path.read_bytes())
        claim_path = ROOT / 'research_logs/kumar_frozen_query_evaluation_20261015/run01/claim.json'
        claim = json.loads(claim_path.read_bytes())
        report['reviewed_execution_commit'] = claim['reviewed_commit']
        report['operation_contract_sha256'] = digest_file(contract_path)
        check(digest_file(contract_path) == claim['contract_sha256'], 'Claim contract binding')
        expected_metadata = {}
        for manifest in (inputs, checkpoint):
            for dep in manifest['dependencies']:
                if dep['path'] in expected_metadata:
                    check(expected_metadata[dep['path']]['sha256'] == dep['sha256'], 'Shared metadata pin identity')
                expected_metadata[dep['path']] = dep
        for name, sha in contract['frozen_files'].items():
            if name in expected_metadata:
                check(expected_metadata[name]['sha256'] == sha, 'Operation and metadata pin agree')
            expected_metadata[name] = {'path': name, 'sha256': sha}
        for name, pin in sorted(expected_metadata.items()):
            path = ROOT / name
            check(path.is_file() and not path.is_symlink(), 'Metadata regular file: ' + name)
            actual = digest_file(path)
            check(actual == pin['sha256'], 'Frozen metadata/source unchanged: ' + name)
            if 'bytes' in pin:
                check(path.stat().st_size == pin['bytes'], 'Metadata size unchanged: ' + name)
            report['metadata_records'].append({'path': name, 'bytes': path.stat().st_size, 'sha256': actual})

        ledger = json.loads((ROOT / checkpoint['accepted_ledger_path']).read_bytes())['accepted_jobs']
        check([m['job_id'] for m in checkpoint['models']] == [j['job_id'] for j in ledger], 'Exact accepted54 order')
        check(len(ledger) == 54, 'Accepted54 count')
        stage = json.loads((PRIVATE / 'checkpoint_staging_full_get_receipt.json').read_bytes())
        before = json.loads((RESULTS / 'checkpoint_archive_full_sha256_before.json').read_bytes())
        worker = json.loads((RESULTS / 'worker_complete.json').read_bytes())
        stage_by_job = {item['job_id']: item for item in stage['files']}
        before_by_job = {item['job_id']: item for item in before['files']}
        worker_by_job = {item['job_id']: item for item in worker['jobs']}
        all_ids = {j['job_id'] for j in ledger}
        check(len(stage['files']) == len(before['files']) == len(worker['jobs']) == 54, '54 original staging and worker records')
        check(set(stage_by_job) == set(before_by_job) == set(worker_by_job) == all_ids, 'All checkpoint record identities')
        check(stage['status'] == 'all54_original_archives_full_GET_SHA256_verified'
              and stage['failed_files'] == [] and stage['verified_objects'] == 54,
              'Original staging full GET completed')
        check(before['verification'] == 'local_original_full_bytes_sha256', 'Worker original before verification type')
        check(worker['status'] == 'all54_evaluated_pending_independent_audit'
              and worker['new_fits'] == worker['optimizer_instances'] == 0
              and worker['query_input_bytes_unchanged'] is True,
              'Worker actual completion and no update declarations')
        expected_files = {m['filename'] for m in checkpoint['models']}
        check({p.name for p in ARCHIVES.iterdir() if p.is_file()} == expected_files, 'Exact original archive file set')
        payload_count = 0
        total_members = 0
        layout_counts = Counter()
        training_config = (ROOT / 'configs/kumar_eegnet_gpu_development_20261014.json').read_bytes()
        for model, accepted in zip(checkpoint['models'], ledger):
            path = ARCHIVES / model['filename']
            check(path.is_file() and not path.is_symlink(), 'Original archive regular file')
            raw_size, raw_sha = path.stat().st_size, digest_file(path)
            check((raw_size, raw_sha) == (model['archive_bytes'], model['archive_sha256']), 'Original archive frozen size/SHA')
            check(raw_sha == accepted['archive_sha256'] and model['result_key'] == accepted['result_key'], 'Original accepted identity')
            for observed in (stage_by_job[model['job_id']], before_by_job[model['job_id']]):
                check((observed['filename'], observed['bytes'], observed['sha256'], observed['result_key'])
                      == (model['filename'], raw_size, raw_sha, model['result_key']), 'Original archive matches prelaunch and worker record')
            with tarfile.open(path, 'r:*') as tar:
                members = tar.getmembers()
                check(len({m.name for m in members}) == len(members), 'No duplicate tar members')
                for member in members:
                    name = PurePosixPath(member.name)
                    check(member.isfile() and not name.is_absolute() and '..' not in name.parts
                          and str(name) == member.name, 'Only regular safe tar members')
                contents = {m.name: tar.extractfile(m).read() for m in members}
            manifest = json.loads(contents['manifest.json'])
            specs = manifest['files']
            check(len({s['path'] for s in specs}) == len(specs), 'No duplicate archive manifest paths')
            check(set(contents) == {s['path'] for s in specs} | {'manifest.json'}, 'Complete tar manifest coverage')
            member_records = []
            for spec in specs:
                content = contents[spec['path']]
                actual_sha = digest_bytes(content)
                check(len(content) == spec['bytes'], 'Tar member length: ' + spec['path'])
                check(actual_sha == spec['sha256'], 'Tar member SHA: ' + spec['path'])
                member_records.append({'path': spec['path'], 'bytes': len(content), 'sha256': actual_sha})
            if model['accepted_position'] == 1:
                check(len(specs) == 11 and manifest['expected_R2_key'] == model['result_key'], 'Original first-model legacy layout')
                check(raw_sha == '2a4d0dd291f1f93bc0560e39b99b2e76fbf6bcba0d3a363ceb522fb4afea0f62', 'Original first model, never replay replacement')
                layout = 'original_first_model_11_payload_legacy'
            else:
                check(len(specs) == 14 and manifest['job_id'] == model['job_id']
                      and manifest['result_key'] == model['result_key'], 'Remaining original model 14 payload identity')
                layout = 'original_model_14_payload'
            weights = json.loads(contents['weights.json'])
            check(digest_bytes(contents['weights.pt']) == model['checkpoint_sha256'] == weights['checkpoint_sha256'], 'Opaque checkpoint bytes match both pins')
            check(contents['training_config.json'] == training_config, 'Archived scientific config unchanged')
            result_path = RESULTS / worker_by_job[model['job_id']]['path']
            result_raw = result_path.read_bytes()
            item = worker_by_job[model['job_id']]
            check(len(result_raw) == item['bytes'] and digest_bytes(result_raw) == item['sha256'], 'Worker result actual bytes')
            result = json.loads(result_raw)
            for key in ('job_id', 'subject', 'seed', 'result_key', 'archive_sha256', 'checkpoint_sha256'):
                check(result['identity'][key] == model[key], 'Result/checkpoint identity: ' + key)
            state = weights['frozen_state_sha256']
            check(result['state_before_sha256'] == result['state_after_sha256'] == state, 'Recorded before/after state equals archived frozen state')
            check(result['optimizer_instances_created'] == result['optimizer_steps'] == 0
                  and result['new_fit'] is False and result['parameter_BN_normalization_updates'] is False
                  and result['input_files_unchanged'] is True and result['processed_input_hashes_verified'] is True
                  and result['source_training_context_preserved'] is True,
                  'Frozen state/no fit declarations')
            report['archive_records'].append({
                'job_id': model['job_id'], 'filename': model['filename'], 'bytes': raw_size, 'sha256': raw_sha,
                'result_key': model['result_key'], 'checkpoint_sha256': model['checkpoint_sha256'],
                'archived_frozen_state_sha256': state, 'recorded_state_before_sha256': result['state_before_sha256'],
                'recorded_state_after_sha256': result['state_after_sha256'], 'layout': layout,
                'payload_member_count': len(specs), 'total_tar_member_count': len(contents),
                'manifest_bytes': len(contents['manifest.json']), 'manifest_sha256': digest_bytes(contents['manifest.json']),
                'result_path': str(result_path), 'result_bytes': len(result_raw), 'result_sha256': digest_bytes(result_raw),
                'payload_members': member_records,
            })
            payload_count += len(specs)
            total_members += len(contents)
            layout_counts[layout] += 1

        prelaunch_path = PRIVATE / 'input_full_sha256_prelaunch.json'
        worker_before_path = RESULTS / 'input_full_sha256_before.json'
        prelaunch = json.loads(prelaunch_path.read_bytes())
        worker_before = json.loads(worker_before_path.read_bytes())
        check(prelaunch == worker_before, 'Prelaunch and worker-before complete input receipt equality')
        check(prelaunch['file_count'] == len(prelaunch['files']) == 1189
              and prelaunch['bytes'] == 1043686331
              and prelaunch['verification'] == 'local_full_bytes_sha256', 'Exact input receipt coverage')
        recorded_inputs = {entry['relative_path']: entry for entry in prelaunch['files']}
        check(len(recorded_inputs) == 1189 and set(recorded_inputs)
              == {entry['relative_path'] for entry in inputs['files']}, 'Exact frozen input identities')
        for entry in inputs['files']:
            path = DATA / entry['relative_path']
            check(path.is_file() and not path.is_symlink(), 'Input regular file: ' + entry['relative_path'])
            size, sha = path.stat().st_size, digest_file(path)
            check((size, sha) == (entry['bytes'], entry['sha256']), 'Actual postrun input size/SHA: ' + entry['relative_path'])
            expected_record = {'relative_path': entry['relative_path'], 'bytes': size, 'sha256': sha}
            check(recorded_inputs[entry['relative_path']] == expected_record, 'Actual postrun input equals prelaunch/before record')
            report['input_records'].append(expected_record)
        report.update(
            status='independent_opaque_archive_input_and_recorded_state_identity_audit_passed',
            archive_count=len(report['archive_records']), archive_bytes=sum(x['bytes'] for x in report['archive_records']),
            archive_payload_members_hashed=payload_count, archive_total_members_including_manifests=total_members,
            archive_layout_counts=dict(layout_counts), input_file_count=len(report['input_records']),
            input_bytes=sum(x['bytes'] for x in report['input_records']),
            frozen_metadata_source_count=len(report['metadata_records']), recorded_state_equal_count=54,
            input_prelaunch_receipt_sha256=digest_file(prelaunch_path),
            input_worker_before_receipt_sha256=digest_file(worker_before_path),
            checkpoint_staging_receipt_sha256=digest_file(PRIVATE / 'checkpoint_staging_full_get_receipt.json'),
            checkpoint_worker_before_receipt_sha256=digest_file(RESULTS / 'checkpoint_archive_full_sha256_before.json'),
            worker_completion_sha256=digest_file(RESULTS / 'worker_complete.json'),
            limitations=[
                'Checkpoint tensors are opaque bytes here; tensor-state hashes were not recomputed by this reviewer.',
                'Recorded query before/after hashes were independently compared with the original archived weights.json frozen-state hash.',
                'Input identities were fully rehashed as bytes; no EDF decoding, event parsing or predictions were rerun.',
                'Scientific numerical/metric audit, new-result R2 backup and parent acceptance are separate checks.',
            ],
        )
    except Exception as error:
        report['status'] = 'failed_preserved_audit'
        report['failures'].append({'type': type(error).__name__, 'message': str(error)})
        raise
    finally:
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        report['failure_count'] = len(report['failures'])
        with OUTPUT.open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps({key: report[key] for key in (
        'status', 'checks_passed', 'archive_count', 'archive_bytes', 'archive_payload_members_hashed',
        'archive_total_members_including_manifests', 'input_file_count', 'input_bytes',
        'frozen_metadata_source_count', 'recorded_state_equal_count', 'failure_count')}))


if __name__ == '__main__':
    main()
