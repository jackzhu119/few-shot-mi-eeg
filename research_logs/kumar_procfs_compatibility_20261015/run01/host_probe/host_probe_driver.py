"""Current-host inert process-tree/RSS proof only; never invokes execute or CSP."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path('/workspace/few-shot-mi-eeg')
folder = Path(__file__).resolve().parent
entry = root / 'scripts/run_kumar_csp_signed_score_operation.py'
expected = sys.argv[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(entry) == expected
spec = importlib.util.spec_from_file_location('actual_procfs_monitor_under_test', entry)
operation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operation)
state = root / 'research_logs/kumar_next_source_operations_20261015/csp_signed_score_operation_run01'
protected = {str(path): sha(path) for path in state.iterdir() if path.is_file()}
protected[str(root / 'research_logs/kumar_development_queue_20261014/accepted_jobs.json')] = sha(root / 'research_logs/kumar_development_queue_20261014/accepted_jobs.json')
record = {'schema_version': 1, 'synthetic': True, 'software_validation_only': True,
          'started_at_utc': datetime.now(timezone.utc).isoformat(),
          'tested_launcher_sha256': expected, 'container_identity': operation.container_identity(),
          'scientific_consumer_launched': False, 'science_data_loaded': False,
          'query_access': False, 'Pod_operated': False, 'samples': []}
process, history, pidfds, nodes = None, {}, {}, []
failed = False

def load_ready(path, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                pass
        if process.poll() is not None:
            raise RuntimeError('Inert fixture exited before readiness')
        time.sleep(0.025)
    raise TimeoutError('Inert fixture readiness timeout')

try:
    with (folder / 'inert_fixture_stdout.log').open('x') as out, (folder / 'inert_fixture_stderr.log').open('x') as err:
        process = subprocess.Popen([sys.executable, '-B', str(folder / 'inert_three_generation_fixture.py'), str(folder), '0'],
                                   stdout=out, stderr=err, start_new_session=True)
    record['inert_root_pid'] = process.pid
    nodes = [load_ready(folder / ('node-' + str(depth) + '-ready.json')) for depth in range(3)]
    record['fixture_nodes'] = nodes
    expected_pids = {node['pid'] for node in nodes}
    assert nodes[0]['pid'] == process.pid and nodes[1]['ppid'] == process.pid and nodes[2]['ppid'] == nodes[1]['pid']
    for node in nodes:
        pidfds[node['pid']] = os.pidfd_open(node['pid'])
    for index in range(3):
        observed = operation.running_memory(process.pid, observed_descendants=history)
        assert set(observed['process_tree_pids']) == expected_pids
        assert observed['consumer_rss_bytes'] == sum(item['rss_bytes'] for item in observed['process_tree_members'])
        assert all(item['rss_bytes'] >= next(node['allocated_and_touched_bytes'] for node in nodes if node['pid'] == item['pid']) for item in observed['process_tree_members'])
        record['samples'].append({'sample_index': index, 'state': 'live_three_generation_tree', 'at_utc': datetime.now(timezone.utc).isoformat(), **observed})
        time.sleep(0.25)
    grandchild = nodes[2]['pid']
    signal.pidfd_send_signal(pidfds[grandchild], signal.SIGUSR1)
    transition = load_ready(folder / 'grandchild-independent-session.json')
    assert transition['session'] == transition['pgrp'] == grandchild and transition['ppid'] == nodes[1]['pid']
    escaped = operation.running_memory(process.pid, observed_descendants=history)
    assert set(escaped['process_tree_pids']) == expected_pids
    record['samples'].append({'state': 'live_grandchild_independent_session_and_group', 'at_utc': datetime.now(timezone.utc).isoformat(), **escaped})
    record['grandchild_session_transition'] = transition
    for handle in pidfds.values():
        signal.pidfd_send_signal(handle, signal.SIGSTOP)
    time.sleep(0.05)
    frozen = operation.running_memory(process.pid, observed_descendants=history)
    independently_read = []
    for node in nodes:
        values = dict(line.split(':', 1) for line in Path('/proc', str(node['pid']), 'status').read_text().splitlines() if ':' in line)
        assert int(values['Tgid']) == node['pid'] and values['State'].strip().startswith('T')
        independently_read.append({'pid': node['pid'], 'TGID': int(values['Tgid']), 'rss_bytes': int(values['VmRSS'].split()[0]) * 1024})
    assert set(frozen['process_tree_pids']) == expected_pids
    assert frozen['consumer_rss_bytes'] == sum(row['rss_bytes'] for row in independently_read)
    record['stable_RSS_independent_check'] = {'observed': frozen, 'independent_proc_status': independently_read,
        'summed_RSS_matches_exactly': True, 'TGID_deduplicated_count': len(independently_read)}
    for handle in pidfds.values():
        signal.pidfd_send_signal(handle, signal.SIGCONT)
    record['missing_legacy_children_paths'] = [str(Path('/proc', str(node['pid']), 'task', str(node['pid']), 'children')) for node in nodes if not Path('/proc', str(node['pid']), 'task', str(node['pid']), 'children').exists()]
    assert len(record['missing_legacy_children_paths']) == 3
    code, events = operation.stop_process(process, 2, observed_descendants=history)
    record['identity_bound_cleanup'] = {'root_returncode': code, 'events': events}
    assert code == 0
    deadline = time.monotonic() + 3
    while any(Path('/proc', str(pid)).exists() for pid in expected_pids) and time.monotonic() < deadline:
        time.sleep(0.025)
    assert all(not Path('/proc', str(pid)).exists() for pid in expected_pids)
    record['all_fixture_pids_reaped'] = True
    assert sha(entry) == expected
    assert all(sha(Path(name)) == value for name, value in protected.items())
    record['original_failed_claim_receipts_and_accepted18_preserved'] = True
    record['status'] = 'actual_host_inert_tree_and_RSS_proof_passed'
except BaseException as error:
    failed = True
    record['status'] = 'actual_host_inert_proof_failed_preserved'
    record['failure'] = {'type': type(error).__name__, 'message': str(error)}
finally:
    # Only these explicitly created inert test identities may be cleaned up.
    for handle in pidfds.values():
        try:
            signal.pidfd_send_signal(handle, signal.SIGCONT)
            signal.pidfd_send_signal(handle, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if process is not None and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            for handle in pidfds.values():
                try:
                    signal.pidfd_send_signal(handle, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
    for handle in pidfds.values():
        os.close(handle)
    record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    with (folder / 'actual_host_process_tree_proof.json').open('x') as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write('\n')
print(json.dumps({'status': record['status'], 'inert_root_pid': record.get('inert_root_pid'), 'sample_count': len(record['samples']), 'failure': record.get('failure')}))
raise SystemExit(1 if failed else 0)
