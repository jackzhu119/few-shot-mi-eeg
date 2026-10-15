"""Read-only independent byte/dispatch/receipt audit; no project execution or tensors."""
import collections
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('/workspace/private_model_receipts/remaining36-audit-20261015-run01')
OUT = Path(__file__).with_name('independent_dispatch_audit_run01.json')
COMMIT = '58b154a3572d073548fa21f6f0b2bbb09fc76401'
CONTRACT_SHA = 'f1a5b94aa89f6f2d9f694f7c270e48ef2624afc06be3a08e328f500224491bd9'
RUN_ID = 'a13f6c01e04e43948fc01f6b69314cec'
START, DEADLINE = 1792047130, 1792057930
FAILURES = []
CHECKS = 0
COUNTS = collections.Counter()


def check(value, label):
    global CHECKS
    CHECKS += 1
    if not value:
        FAILURES.append(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def js(raw):
    return json.loads(raw)


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def unpack(raw, manifest_name, label):
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        check(len(names) == len(set(names)), label + ': unique members')
        check(all(member.isfile() and not Path(member.name).is_absolute() and
                  '..' not in Path(member.name).parts for member in members), label + ': safe regular members')
        data = {member.name: archive.extractfile(member).read() for member in members}
    manifest = js(data[manifest_name])
    if 'payloads' in manifest:
        records = [{'path': key, **value} for key, value in manifest['payloads'].items()]
    else:
        records = manifest['files']
    check(len(records) == len({r['path'] for r in records}), label + ': unique manifest')
    check(set(data) == {r['path'] for r in records} | {manifest_name}, label + ': exact manifest members')
    for r in records:
        member = data[r['path']]
        check(len(member) == r['bytes'] and sha(member) == r['sha256'], label + ': member ' + r['path'])
    COUNTS[label.split(':')[0] + '_payloads_hashed'] += len(records)
    return manifest, data


def boundary_identity(obj, label):
    check(obj['run_id'] == RUN_ID and obj['contract_sha256'] == CONTRACT_SHA and
          obj['fixed_commit'] == COMMIT, label + ': run/contract/commit')


def false_stages(records, label):
    check(all(r[k] is False for r in records.values() for k in
              ('independently_audited', 'R2_full_GET_verified', 'accepted')), label + ': no premature acceptance')


def main():
    original_hashes = {}
    outer = {}
    for name, dirname in [('remaining36-all-models-audit-handoff-run01.tar.gz', 'handoff'),
                          ('remaining36-final-dispatch-evidence.tar.gz', 'dispatch')]:
        raw = (BASE / name).read_bytes()
        manifest, data = unpack(raw, 'MANIFEST.json', dirname)
        check({str(p.relative_to(BASE / dirname)) for p in (BASE / dirname).rglob('*') if p.is_file()} == set(data),
              dirname + ': exact extracted files')
        for key, value in data.items():
            check((BASE / dirname / key).read_bytes() == value, dirname + ': extracted original ' + key)
        original_hashes[name] = {'bytes': len(raw), 'sha256': sha(raw), 'payloads': len(manifest['payloads'])}
        outer[dirname] = data
    h, d = outer['handoff'], outer['dispatch']
    contract_raw = (ROOT / 'configs/kumar_remaining_source_batch_20261015.json').read_bytes()
    check(sha(contract_raw) == CONTRACT_SHA, 'fixed contract digest')
    contract = js(contract_raw)
    jobs = contract['remaining_jobs']
    ids = [job['job_id'] for job in jobs]
    ledger_raw = (ROOT / contract['accepted_ledger']).read_bytes()
    ledger = js(ledger_raw)['accepted_jobs']
    check(len(jobs) == len(set(ids)) == 36 and len(ledger) == 18, 'exact 36 and original18 counts')
    check(not ({j['job_id'] for j in ledger} & set(ids)) and not
          ({j['subject'] for j in ledger} & {j['subject'] for j in jobs}), 'accepted18 exclusion')
    check(sha(ledger_raw) == contract['accepted_ledger_sha256'], 'original18 ledger frozen digest')
    for name, digest in js(d['dispatch/delivery-hashes.json']).items():
        check(sha((ROOT / name).read_bytes()) == digest, 'delivered fixed source ' + name)
    state = js(d['batch/state.json'])
    boundary_identity(state, 'final state')
    auth_raw = d['batch/authorization.json']
    auth = js(auth_raw)
    check(auth_raw == d['dispatch/authorization-copy.json'], 'authorization original copies identical')
    check(state['authorization'] == auth and state['container_identity'] == auth['authorized_container_identity'],
          'state/auth full host identity')
    check(auth['reviewed_commit'] == COMMIT and auth['contract_sha256'] == CONTRACT_SHA and
          auth['approved_job_ids'] == ids and auth['query_access'] is False and
          auth['accepted18_refitting_authorized'] is False and auth['new_resource_allocation_authorized'] is False and
          auth['financial_execution_preconditions'] == 'superseded-by-user', 'actual authorization scope')
    check(auth['not_before_unix'] == state['started_unix'] == START and
          auth['deadline_unix'] == state['deadline_unix'] == DEADLINE and
          auth['approved_wall_seconds'] == DEADLINE - START == 10800, 'unchanged absolute window')
    check(state['status'] == 'complete_exported' and state['pending_export'] is None and list(state['jobs']) == ids,
          'final complete ordered state')
    false_stages(state['jobs'], 'final state')
    check(all(r['trained'] and r['off_Pod_exported'] and r['stage'] == 'exported' for r in state['jobs'].values()),
          'all36 trained and exported only')
    journal_raw = d['batch/journal.jsonl']
    journal = [js(line) for line in journal_raw.splitlines()]
    events = collections.Counter(e['event'] for e in journal)
    expected_counts = {'independent_remaining36_run_created_authorized_absolute_deadline': 1,
        'chunk_claims_reserved': 18, 'export_ready': 36, 'export_wait_started': 36,
        'dot_export_receipt_verified': 36, 'active_chunk_started': 18, 'fit_starting': 36,
        'fit_trained_not_audited_or_accepted': 36, 'export_wait_expired_safe_pause_no_training_retry': 1,
        'all36_trained_and_exported_audit_R2_and_acceptance_pending': 1}
    check(dict(events) == expected_counts, 'complete exact journal event census; no extra fit or failed claim')
    check(all(START <= utc(e['utc']) <= DEADLINE for e in journal), 'all journal events within original window')
    check([utc(e['utc']) for e in journal] == sorted(utc(e['utc']) for e in journal), 'journal monotone times')
    check([e['job_id'] for e in journal if e['event'] == 'fit_starting'] == ids, 'all36 frozen start order once')
    check([e['job_id'] for e in journal if e['event'] == 'fit_trained_not_audited_or_accepted'] == ids,
          'all36 frozen saved order once')
    source_raw = d['source/https-remaining-source-download-run01.json']
    check(source_raw == d['dispatch/source-receipt-copy.json'], 'source receipt copies identical')
    source = js(source_raw)
    input_raw = (ROOT / contract['input_manifest']).read_bytes()
    inputs = js(input_raw)
    expected_inputs = {r['relative_path']: r for r in inputs['files']}
    check(len(expected_inputs) == 253 and sum(r['bytes'] for r in expected_inputs.values()) == 196740994,
          'source253 exact scope')
    check(source['status'] == 'all_253_full_sha256_verified' and source['query_access'] is False and
          source['real_training_executed'] is False and source['maximum_attempts_per_file'] == 1 and
          source['manifest_sha256'] == contract['https_manifest_sha256'] and
          source['source_plan_sha256'] == source['input_manifest_sha256'] == sha(input_raw), 'source receipt scope')
    check(len(source['records']) == len({r['path'] for r in source['records']}) == 253 and
          {r['path'] for r in source['records']} == set(expected_inputs), 'source receipt exact members')
    for r in source['records']:
        check(r['sha256'] == expected_inputs[r['path']]['sha256'] and
              r['status'] in {'reused_sha256_verified', 'downloaded_sha256_verified'}, 'source receipt ' + r['path'])
    inventory = js((ROOT / contract['runtime_inventory']).read_bytes())
    packages = inventory['target_environment']['linux_x86_64_python311_selected_versions']
    runtime_env = {'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}
    job_audits = []
    model_data = {}
    previous_exit = START
    for job in jobs:
        jid = job['job_id']
        raw = h['original-results/' + jid + '.tar']
        manifest, model = unpack(raw, 'manifest.json', 'model:' + jid)
        check(len(manifest['files']) == 14, jid + ': original14 payloads')
        model_data[jid] = model
        check(js(model['job.json']) == job, jid + ': original fixed job')
        check(model['queue_runtime.json'] == contract_raw and model['training_config.json'] ==
              (ROOT / contract['scientific_config']).read_bytes(), jid + ': contract/science bytes')
        check(model['input_receipt.json'] == source_raw, jid + ': original253 receipt bytes')
        for member, filename in [('run_source.py', 'scripts/run_kumar_remaining_source_batch.py'),
                                 ('train_source.py', 'scripts/train_kumar_eegnet.py'),
                                 ('adapter_source.py', 'src/learning_preserving_bci/datasets/kumar.py')]:
            check(sha(model[member]) == contract['frozen_files'][filename], jid + ': source ' + member)
        record = js(model['fit_result.json'])
        claim = js(d['batch/claims/' + jid + '.json'])
        boundary_identity(claim, jid + ': claim')
        check(claim['job'] == job and claim['job_id'] == jid and
              claim['status'] == 'immutable_reserved_intent_never_delete', jid + ': immutable claim')
        entered = js(d['batch/workers/' + jid + '.entered.json'])
        timing = js(d['batch/workers/' + jid + '.timing.json'])
        runtime = entered['fresh_runtime_verification']
        check(entered['run_id'] == RUN_ID and entered['job_id'] == jid and entered['GPU_lock_inherited'] is True,
              jid + ': worker entry/lock recorded')
        check(runtime['python'] == '3.11.16' and runtime['locked_packages_verified'] == packages and
              runtime['numerical_environment'] == runtime_env and runtime['torch_cuda'] == '12.8' and
              runtime['GPU_driver_live'] == 'NVIDIA RTX A4500, 580.159.04', jid + ': frozen runtime recorded')
        check(timing['returncode'] == 75 and timing['timed_out'] is False and timing['automatic_retries'] == 0,
              jid + ': worker successful once')
        check(previous_exit <= timing['started_unix'] <= utc(entered['utc']) <= timing['finished_unix'] <= DEADLINE,
              jid + ': nonoverlapping sequential worker interval')
        check(0 < timing['finished_unix'] - timing['started_unix'] < 1800, jid + ': fit wall limit')
        previous_exit = timing['finished_unix']
        fits = [js(line) for line in model['events.jsonl'].splitlines()]
        check([e['status'] for e in fits] == ['reserved', 'fitting', 'fit_saved'], jid + ': one fitting event')
        times = [utc(e['utc']) for e in fits]
        check(times == sorted(times) and utc(entered['utc']) <= times[0] <= times[-1] <= timing['finished_unix'],
              jid + ': consumer event timing enclosed')
        check(record['job_id'] == jid and record['query_rows_loaded'] == 0 and
              record['source_train_rows'] == 40 and record['source_validation_rows'] == 20 and
              record['provenance']['git_commit'] == COMMIT and record['provenance']['git_dirty'] is False,
              jid + ': exact source identity/provenance')
        check(record['epochs_executed'] <= 100 and record['optimizer_steps'] == 3 * record['epochs_executed'],
              jid + ': count budget')
        check(record['checkpoint_sha256'] == sha(model['weights.pt']) == js(model['weights.json'])['checkpoint_sha256'],
              jid + ': checkpoint hash binding')
        stdout = [js(line) for line in d['batch/workers/' + jid + '.stdout.log'].splitlines()]
        check(d['batch/workers/' + jid + '.stderr.log'] == b'', jid + ': worker stderr preserved empty')
        saved = [line for line in stdout if line.get('status') == 'fit_saved_private_backup_pending']
        check(len(saved) == 1 and saved[0]['job_id'] == jid and saved[0]['sha256'] == sha(raw) and
              saved[0]['bytes'] == len(raw) and saved[0]['R2_backup_verified'] is False, jid + ': saved worker stdout')
        state_record = state['jobs'][jid]
        check(state_record['archive_sha256'] == sha(raw) and state_record['archive_bytes'] == len(raw) and
              state_record['epochs'] == record['epochs_executed'] and state_record['steps'] == record['optimizer_steps'],
              jid + ': final state counts/hash')
        job_audits.append({'job_id': jid, 'subject': job['subject'], 'seed': job['seed'],
            'archive_sha256': sha(raw), 'worker_started_unix': timing['started_unix'],
            'worker_finished_unix': timing['finished_unix'], 'fitting_utc': fits[1]['utc'],
            'fit_saved_utc': fits[2]['utc'], 'epochs': record['epochs_executed'], 'steps': record['optimizer_steps']})
    boundaries = []
    for index in range(18):
        pair = ids[index * 2:index * 2 + 2]
        pair_jobs = {jid: state['jobs'][jid] for jid in pair}
        chunk = [e for e in journal if e['event'] == 'active_chunk_started' and e['job_ids'] == pair]
        check(len(chunk) == 1, f'chunk{index}: unique active event')
        chunk = chunk[0]
        check(utc(chunk['utc']) < chunk['chunk_deadline_unix'] <= min(DEADLINE, utc(chunk['utc']) + 3600),
              f'chunk{index}: bounded shared-lock interval recorded')
        for kind in ['intent', 'results']:
            name = kind + '-' + '-'.join(pair)
            raw = h['boundaries/' + name + '.tar']
            manifest, members = unpack(raw, 'manifest.json', 'boundary:' + name)
            boundary_identity(manifest, name)
            check(manifest['kind'] == kind and manifest['job_ids'] == pair, name + ': exact pair/kind')
            check(members['contract.json'] == contract_raw and members['frozen_input_manifest.json'] == input_raw and
                  members['input_receipt.json'] == source_raw and members['frozen_accepted18_ledger.json'] == ledger_raw,
                  name + ': common frozen originals')
            check(journal_raw.startswith(members['journal.jsonl']), name + ': journal is unchanged final prefix')
            snap = js(members['state_snapshot.json'])
            boundary_identity(snap, name + ': state')
            check(snap['authorization'] == auth and snap['container_identity'] == state['container_identity'] and
                  snap['started_unix'] == START and snap['deadline_unix'] == DEADLINE, name + ': immutable host/window')
            check(list(snap['jobs']) == ids[:index * 2 + 2], name + ': contiguous reservation prefix')
            false_stages(snap['jobs'], name)
            check(all(snap['jobs'][jid]['trained'] and snap['jobs'][jid]['off_Pod_exported'] for jid in ids[:index * 2]),
                  name + ': prior chunks exported before next')
            check(all(snap['jobs'][jid]['trained'] is (kind == 'results') and
                      snap['jobs'][jid]['off_Pod_exported'] is False for jid in pair), name + ': truthful snapshot stages')
            receipt_raw = h['offpod-receipts/' + name + '.receipt.json']
            check(receipt_raw == d['batch/inbox/' + name + '.receipt.json'] ==
                  d['batch/exports/' + name + '.verified-receipt.json'], name + ': exact three receipt copies')
            receipt = js(receipt_raw)
            boundary_identity(receipt, name + ': receipt')
            check(receipt['status'] == 'dot_off_Pod_full_member_SHA256_verified' and
                  receipt['physical_location_is_dot_attestation_not_machine_proof'] is True and
                  receipt['archive_bytes'] == len(raw) and receipt['archive_sha256'] == sha(raw) and
                  receipt['kind'] == kind and receipt['job_ids'] == pair and receipt['files'] == manifest['files'],
                  name + ': full receipt byte/member/identity bindings')
            ready = [e for e in journal if e['event'] == 'export_ready' and e['sha256'] == sha(raw)]
            verified = [e for e in journal if e['event'] == 'dot_export_receipt_verified' and e['archive_sha256'] == sha(raw)]
            check(len(ready) == len(verified) == 1 and ready[0]['bytes'] == len(raw) and ready[0]['job_ids'] == pair,
                  name + ': unique ready/verified journal bindings')
            check(utc(ready[0]['utc']) <= utc(receipt['verified_at_utc']) <= utc(verified[0]['utc']) <= DEADLINE,
                  name + ': exported/verified time order')
            for jid in pair:
                check(members['claims/' + jid + '.json'] == d['batch/claims/' + jid + '.json'], name + ': claim unchanged ' + jid)
                if kind == 'results':
                    check(members['results/' + jid + '.tar'] == h['original-results/' + jid + '.tar'], name + ': nested original ' + jid)
                    for suffix in ['entered.json', 'timing.json', 'stdout.log', 'stderr.log']:
                        filename = 'workers/' + jid + '.' + suffix
                        check(members[filename] == d['batch/' + filename], name + ': worker original ' + filename)
            if kind == 'intent':
                check(receipt['result_archives'] == [] and utc(verified[0]['utc']) <= utc(chunk['utc']), name + ': intent before fit')
            else:
                expected_results = [{'job_id': jid, 'archive_bytes': pair_jobs[jid]['archive_bytes'],
                    'archive_sha256': pair_jobs[jid]['archive_sha256'],
                    'checkpoint_sha256': sha(model_data[jid]['weights.pt']),
                    'all_14_payload_member_hashes_verified': True} for jid in pair]
                check(receipt['result_archives'] == expected_results, name + ': exact two result references')
                check(utc(ready[0]['utc']) < chunk['chunk_deadline_unix'], name + ': packaging before chunk deadline')
                if index < 17:
                    next_claim = next(e for e in journal if e['event'] == 'chunk_claims_reserved' and e['job_ids'] == ids[(index+1)*2:(index+2)*2])
                    check(utc(verified[0]['utc']) <= utc(next_claim['utc']), name + ': result receipt before next reservation')
            boundaries.append({'kind': kind, 'job_ids': pair, 'archive_bytes': len(raw), 'archive_sha256': sha(raw),
                'receipt_sha256': sha(receipt_raw), 'verified_at_utc': receipt['verified_at_utc'],
                'runner_verified_at_utc': verified[0]['utc'], 'payloads_hashed': len(manifest['files'])})
    initial_cmd, resume_cmd = js(d['dispatch/batch-command.json']), js(d['dispatch/resume01/command.json'])
    check([arg.replace('--new-run', '--resume') for arg in initial_cmd] == resume_cmd, 'resume command only mode changed')
    check(initial_cmd.count('--new-run') == 1 and initial_cmd[initial_cmd.index('--authorization-sha256')+1] == sha(auth_raw),
          'initial command exact authorization')
    initial, paused = js(d['dispatch/batch-start.json']), js(d['dispatch/batch-completion.json'])
    resumed, completed = js(d['dispatch/resume01/start.json']), js(d['dispatch/resume01/completion.json'])
    resume_preflight, final = js(d['dispatch/resume01/preflight.json']), js(d['dispatch/final-postflight.json'])
    check(paused['exit_code'] == 76 and completed['exit_code'] == 75 and
          initial['absolute_deadline_unix'] == paused['absolute_deadline_unix'] == resumed['original_deadline_unix'] ==
          completed['original_deadline_unix'] == DEADLINE, 'pause/resume exit and unchanged deadline')
    check(resumed['run_id'] == resume_preflight['run_id'] == RUN_ID and resume_preflight['trained'] == 30,
          'same-run30-saved resume')
    check(START <= utc(initial['utc']) < utc(paused['utc']) < utc(resumed['utc']) < utc(completed['utc']) < DEADLINE,
          'full dispatch absolute time order')
    check(sum(j['worker_finished_unix'] < utc(paused['utc']) for j in job_audits) == 30 and
          sum(j['worker_started_unix'] > utc(resumed['utc']) for j in job_audits) == 6,
          '30 before pause plus6 after resume; none during pause')
    check(final['run_id'] == RUN_ID and final['exit_code'] == 75 and final['batch_status'] == 'complete_exported' and
          final['new_trained'] == final['new_off_Pod_exported'] == 36 and final['GPU_compute'] == '' and
          final['completion_utc'] == completed['utc'], 'final point-in-time observation')
    check(final['free_bytes'] > 5368709120 + 100663296, 'final point-in-time disk reserve')
    handoff = js(h['HANDOFF_STATUS.json'])
    check(handoff['final_dispatch_evidence_pending'] is True and handoff['final_terminal_exit_observed'] is False,
          'earlier handoff historical pending flags preserved')
    report = {'schema_version': 1, 'status': 'pass' if not FAILURES else 'failed',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'audit_script_sha256': sha(Path(__file__).read_bytes()),
        'fixed_commit': COMMIT, 'contract_sha256': CONTRACT_SHA, 'run_id': RUN_ID,
        'checks': CHECKS, 'failures': FAILURES, 'failure_count': len(FAILURES), 'original_archives': original_hashes,
        'counts': dict(COUNTS), 'job_count': len(job_audits), 'boundary_count': len(boundaries),
        'source_file_count': 253, 'source_bytes': 196740994, 'runtime_locked_packages': len(packages),
        'accepted18_ledger_sha256': sha(ledger_raw), 'authorization_sha256': sha(auth_raw),
        'container_identity_recorded': state['container_identity'], 'absolute_start_unix': START,
        'absolute_deadline_unix': DEADLINE, 'initial_start': initial, 'pause_exit': paused,
        'same_run_resume': resumed, 'final_exit': completed, 'journal_event_counts': dict(events),
        'epochs_recorded': sum(j['epochs'] for j in job_audits), 'steps_recorded': sum(j['steps'] for j in job_audits),
        'query_rows_reported': 0, 'all_original_acceptance_flags_preserved_false': True,
        'jobs': job_audits, 'boundaries': boundaries,
        'evidence_limits': [
            'This audit independently hashes provided original bytes; physical historical off-Pod possession remains dot attestation, now supported by these complete received archives.',
            'Worker lock flags, exact source hashes, sequential intervals and gated journal evidence are consistent; historical OS flock ownership is not independently measurable retrospectively.',
            'Runtime, per-fit input verification and device records are historical producer evidence; this audit does not operate Pod or re-read raw EEG.',
            'Final GPU/process/disk observations are point-in-time snapshots, not continuous monitoring.',
            'Old 18-job/127-file metadata summary lines are unchanged legacy acceptance-check output; all model input receipts bind253 source files. They do not indicate old-model refitting.',
            'Earlier handoff pending flags and metadata proposal-only labels remain unmodified; final dispatch supplies later completion evidence.',
            'No independent numerical checkpoint replay or new fit occurs in this dispatch audit; numerical audits and R2 verification are separate.',
        ]}
    with OUT.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ['status', 'checks', 'failure_count', 'failures', 'counts',
        'job_count', 'boundary_count', 'epochs_recorded', 'steps_recorded']}))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    raise SystemExit(main())
