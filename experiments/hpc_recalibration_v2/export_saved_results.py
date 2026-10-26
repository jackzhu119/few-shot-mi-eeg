"""Export saved paper2 results and publish a resumable packet; no fit or inference."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import gzip
import getpass
import hashlib
import json
import math
import os
import pickle
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import zipfile

from github_result_upload import GitResultPublisher
from result_history_export import ResultChangedError, extract_checkpoint, extract_classical_metadata

VERSION = 'paper2-saved-results-v1-20261026'
PART_BYTES = 16 * 1024 * 1024
SECRET_KEY = re.compile(r'(password|secret|credential|authorization|access.?key|(?:^|_)token(?:$|_))', re.I)
SECRET_TEXT = re.compile(r'github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}')


def emit(event, **values):
    print(json.dumps({'event': event, **values}, ensure_ascii=False), flush=True)


def stamp(path):
    value = path.stat()
    return {'bytes': value.st_size, 'mtime_ns': value.st_mtime_ns, 'inode': value.st_ino}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_bytes(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                                  allow_nan=False) + '\n').encode())


def public_json(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if SECRET_KEY.search(k) else public_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [public_json(v) for v in value]
    if isinstance(value, str):
        return SECRET_TEXT.sub('[REDACTED]', value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Nonfinite value in saved JSON; original file retained')
    return value


def source_inventory(config):
    """Only result, provenance and scientific-code paths; never traverse data_root."""
    project, output = Path(config['project_dir']), Path(config['output_root'])
    task_value = json.loads(Path(config['tasks_file']).read_text())
    tasks = task_value['tasks'] if isinstance(task_value, dict) else task_value
    entries = []
    for task in tasks:
        task_id = task['task_id']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', task_id) or task_id in ('.', '..'):
            raise ValueError('Unsafe task identity')
        folder = output / 'tasks' / task_id
        complete = folder / 'complete.json'
        if not complete.is_file() or json.loads(complete.read_text()).get('status') != 'completed':
            raise ValueError('Task is not complete; existing output retained: ' + task_id)
        for path in sorted(folder.rglob('*')):
            if not path.is_file():
                continue
            if path.is_symlink():
                raise ValueError('Result symlink is not followed: ' + str(path))
            relative = path.relative_to(folder)
            first = relative.parts[0]
            kind = 'excluded'
            if path.suffix == '.json' and (len(relative.parts) == 1 or first in
                    ('evaluation', 'source_query', 'runtime', 'failures', 'source', 'adaptation')):
                kind = 'json'
            elif path.name == 'predictions.npz' and first in ('evaluation', 'source_query'):
                kind = 'predictions'
            elif path.name.startswith('checkpoint') and path.suffix == '.pt' and first in ('source', 'adaptation'):
                kind = 'checkpoint'
            elif path.suffix == '.npz' and (path.name == 'source_model.npz' or first == 'models'):
                kind = 'classical_model'
            entries.append({'path': str(path), 'target': 'results/tasks/' + task_id + '/' + relative.as_posix(),
                            'kind': kind, 'stat': stamp(path)})
    for directory, suffixes in [('logs', ('.out', '.err', '.log')), ('.runtime', ('.json',)),
                                ('analysis', ('.json', '.csv', '.md', '.txt'))]:
        for path in sorted((output / directory).rglob('*')):
            if path.is_file() and path.suffix in suffixes:
                if path.is_symlink():
                    raise ValueError('Result symlink is not followed')
                entries.append({'path': str(path), 'target': 'results/' + path.relative_to(output).as_posix(),
                                'kind': 'json' if path.suffix == '.json' else 'text', 'stat': stamp(path)})
    sources = [project / name for name in ('bootstrap.py', 'PACKAGE_MANIFEST.json', 'NOTICE.md', 'LICENSE')]
    sources += sorted((project / 'hpc_recalibration').glob('*.py'))
    sources += sorted((project / 'configs').glob('*.json'))
    sources += [Path(config['_config_path'])]
    for directory in ('LICENSES', '.hpc_runtime'):
        sources += [p for p in (project / directory).rglob('*') if p.is_file() and p.suffix in ('.py', '.sh', '.json', '.md', '.txt')]
    for path in sorted(set(sources)):
        if path.is_file():
            if path.is_symlink() or not path.resolve().is_relative_to(project.resolve()):
                raise ValueError('Unexpected provenance path')
            entries.append({'path': str(path), 'target': 'source_code/' + path.relative_to(project).as_posix(),
                            'kind': 'json' if path.suffix == '.json' else 'text', 'stat': stamp(path)})
    return tasks, entries


def copy_public(entry, target):
    source = Path(entry['path'])
    if stamp(source) != entry['stat']:
        raise RuntimeError('Result changed during export: ' + str(source))
    body = source.read_bytes()
    original_sha = hashlib.sha256(body).hexdigest()
    if entry['kind'] == 'json':
        value = json.loads(body)
        cleaned = public_json(value)
        if cleaned != value:
            body = (json.dumps(cleaned, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    elif entry['kind'] == 'text':
        text = body.decode('utf-8', errors='replace')
        body = SECRET_TEXT.sub('[REDACTED]', text).encode()
        body = re.sub(rb'(?im)(authorization\s*:\s*bearer\s+)\S+', rb'\1[REDACTED]', body)
    elif entry['kind'] == 'predictions':
        import numpy as np
        with np.load(source, allow_pickle=False) as values:
            if set(values.files) != {'probabilities', 'labels', 'classes', 'trial_id', 'run_id'}:
                raise ValueError('Unexpected prediction archive; not uploaded as EEG: ' + str(source))
            for name in values.files:
                values[name]  # Reject object/pickle arrays without evaluating a model.
    if stamp(source) != entry['stat']:
        raise RuntimeError('Result changed while being read: ' + str(source))
    atomic_bytes(target, body)
    return {'path': entry['target'], 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
            'source_path': entry['path'], 'source_sha256': original_sha if original_sha == hashlib.sha256(body).hexdigest() else None,
            'redacted': original_sha != hashlib.sha256(body).hexdigest()}


def required_paths(config, tasks):
    required = set()
    budgets = config.get('budgets', [4, 8, 12, 16, 20])
    for task in tasks:
        folder = 'results/tasks/' + task['task_id'] + '/'
        classical = task.get('family', 'eegnet') == 'classical'
        methods = config.get('classical_methods', ['frozen', 'lda_only', 'full_csp', 'ea_csp',
            'anchored_csp', 'empirical_anchored_csp', 'ea_anchored_csp', 'ea_empirical_anchored_csp']) if classical else config.get('methods', ['frozen', 'head', 'full', 'l2sp'])
        if classical:
            required.add(folder + 'source_model.npz')
        elif config.get('source_mode', 'new_source') == 'new_source':
            required.add(folder + 'source/checkpoint.pt')
        if task.get('source_query'):
            required.add(folder + ('evaluation/source__n0__frozen.json' if classical else 'source_query.json'))
            if not classical:
                required.add(folder + 'source_query/predictions.npz')
        for target in task.get('targets', []):
            session = target['session']
            for budget in budgets:
                for method in methods:
                    if classical:
                        stem = session + '__n' + str(budget) + '__' + method
                        required.update((folder + 'evaluation/' + stem + '.json', folder + 'models/' + stem + '.npz'))
                    else:
                        stem = session + '/' + method + '/budget-' + str(budget)
                        required.update((folder + 'evaluation/' + stem + '/metrics.json',
                                         folder + 'evaluation/' + stem + '/predictions.npz'))
                        if method != 'frozen':
                            required.add(folder + 'adaptation/' + stem + '/checkpoint.pt')
    return required


def make_packet(payload, destination, manifest):
    body = json.dumps(manifest, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    packet_id = hashlib.sha256(body).hexdigest()[:24]
    atomic_json(payload / 'MANIFEST.json', manifest)
    archive = destination / ('paper2-results-' + packet_id + '.tar.gz')
    temporary = archive.with_suffix(archive.suffix + '.part')
    with temporary.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|') as tar:
                for path in sorted(payload.rglob('*')):
                    if not path.is_file():
                        continue
                    info = tarfile.TarInfo('paper2_results/' + path.relative_to(payload).as_posix())
                    info.size = path.stat().st_size
                    info.mode = 0o644
                    info.mtime = 0
                    with path.open('rb') as stream:
                        tar.addfile(info, stream)
        raw.flush()
        os.fsync(raw.fileno())
    os.replace(temporary, archive)
    parts = []
    with archive.open('rb') as stream:
        for index, block in enumerate(iter(lambda: stream.read(PART_BYTES), b'')):
            name = archive.name + '.part' + str(index).zfill(3)
            atomic_bytes(destination / name, block)
            parts.append({'file': name, 'bytes': len(block), 'sha256': hashlib.sha256(block).hexdigest()})
    index = {'schema_version': 1, 'packet_id': packet_id, 'archive': archive.name,
             'archive_bytes': archive.stat().st_size, 'archive_sha256': digest(archive),
             'parts': parts, 'payload_files': len(manifest['files']), 'tasks': manifest['tasks'],
             'history_errors': manifest['history_errors'], 'weights_and_eeg_uploaded': False}
    atomic_json(destination / 'packet_manifest.json', index)
    readme = ('# Saved paper2 results\n\nPacket `' + packet_id + '`. Existing outputs only; no training or model forward.\n'
              'Join the listed parts in numeric order, verify archive SHA256 from packet_manifest.json, then extract.\n'
              'MANIFEST.json lists every published payload and excluded model/cache file. Model weights, EEG inputs and credentials remain local.\n'
              'Training histories and classical fit metadata were extracted read-only from trusted local model files.\n'
              'Full raw metrics include the18neural source-query results omitted from the progress snapshot.\n')
    atomic_bytes(destination / 'README.md', readme.encode())
    index['upload_files'] = ['packet_manifest.json', 'README.md'] + [row['file'] for row in parts]
    return index


def prepare_bundle(config, destination, *, summarizer=None, tool_identity=VERSION):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    tasks, entries = source_inventory(config)
    identity = {'version': VERSION, 'tool': tool_identity, 'entries': entries}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache_path = destination / 'prepared_packet.json'
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text())
        if cached['fingerprint'] == fingerprint:
            for row in cached['packet']['parts']:
                path = destination / row['file']
                if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
                    raise RuntimeError('Prepared packet changed; retained for diagnosis')
            emit('prepared_packet_reused', packet_id=cached['packet']['packet_id'])
            return cached['packet']
    payload = Path(tempfile.mkdtemp(prefix='payload-', dir=destination))
    files, excluded = [], []
    executable = Path(sys.argv[0])
    if executable.is_file() and zipfile.is_zipfile(executable):
        with zipfile.ZipFile(executable) as package:
            assets = {name.removeprefix('assets/'): package.read(name)
                      for name in package.namelist() if name.startswith('assets/') and not name.endswith('/')}
    else:
        repository = Path(__file__).resolve().parents[2]
        assets = {'SOURCE_DATA_ATTRIBUTION.txt': (repository / 'releases/paper2-hpc-v2-20261023/DATA_ATTRIBUTION.txt').read_bytes(),
                  'LICENSES/MIT.txt': (repository / 'LICENSES/MIT.txt').read_bytes(),
                  'LICENSES/CC-BY-4.0.txt': (repository / 'LICENSES/CC-BY-4.0.txt').read_bytes()}
    for name, body in assets.items():
        atomic_bytes(payload / name, body)
        files.append({'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                      'source_attribution_or_license': True})
    missing = sorted(required_paths(config, tasks) - {entry['target'] for entry in entries})
    errors = [{'path': path, 'error_type': 'missing_expected_result'} for path in missing]
    for number, entry in enumerate(entries, 1):
        path = Path(entry['path'])
        kind = entry['kind']
        if kind in ('checkpoint', 'classical_model'):
            cache_key = hashlib.sha256(json.dumps({'entry': entry, 'tool': tool_identity}, sort_keys=True).encode()).hexdigest()
            derived = destination / 'derived_cache' / (cache_key + '.json')
            if derived.is_file():
                value = json.loads(derived.read_text())
            else:
                try:
                    value = extract_checkpoint(path) if kind == 'checkpoint' else extract_classical_metadata(path)
                except ResultChangedError:
                    raise
                except (ValueError, RuntimeError, EOFError, pickle.UnpicklingError) as error:
                    errors.append({'path': entry['target'], 'error_type': type(error).__name__})
                    excluded.append({'path': entry['target'], 'reason': 'unreadable_model_retained_locally',
                                     'bytes': path.stat().st_size, 'sha256': digest(path)})
                    continue
                atomic_json(derived, value)
            if stamp(path) != entry['stat']:
                raise ResultChangedError('Source result changed during export: ' + str(path))
            if kind == 'checkpoint' and path.name == 'checkpoint.pt' and not value.get('complete'):
                errors.append({'path': entry['target'], 'error_type': 'current_checkpoint_incomplete'})
            relative = 'training_records/' + entry['target'] + '.json'
            public = public_json(value)
            atomic_json(payload / relative, public)
            files.append({'path': relative, 'bytes': (payload / relative).stat().st_size,
                          'sha256': digest(payload / relative), 'source_path': str(path),
                          'source_sha256': value['source_file']['sha256'], 'metadata_only': True})
            excluded.append({'path': entry['target'], 'bytes': value['source_file']['bytes'],
                             'sha256': value['source_file']['sha256'], 'reason': 'model_binary_stays_local'})
        elif kind == 'excluded':
            excluded.append({'path': entry['target'], 'bytes': entry['stat']['bytes'],
                             'reason': 'lock_partial_or_nonpublic_binary'})
        else:
            files.append(copy_public(entry, payload / entry['target']))
        if number % 50 == 0:
            emit('export_progress', processed=number, total=len(entries))
    if summarizer is None:
        from hpc_recalibration.summarize import summarize
        summarizer = summarize
    summary = summarizer(config, destination=payload / 'analysis')
    if summary['cells_expected'] != summary['cells_with_defined_ba']:
        errors.append({'path': 'analysis/summary.json', 'error_type': 'incomplete_or_undefined_target_cells'})
    if summary.get('missing_source_query_cells'):
        errors.append({'path': 'analysis/source_query.csv', 'error_type': 'missing_source_query_cells'})
    for path in sorted((payload / 'analysis').rglob('*')):
        if path.is_file():
            files.append({'path': path.relative_to(payload).as_posix(), 'bytes': path.stat().st_size,
                          'sha256': digest(path), 'generated_from_saved_metrics': True})
    manifest = {'schema_version': 1, 'version': VERSION, 'experiment_id': config['experiment_id'],
                'tasks': [task['task_id'] for task in tasks], 'files': files, 'excluded': excluded,
                'history_errors': errors, 'analysis_counts': {k: summary[k] for k in
                    ('tasks_expected', 'tasks_complete', 'cells_expected', 'cells_with_defined_ba')},
                'no_training_or_inference': True, 'source_data': 'Kumar2024 / NEMAR nm000177 v1.0.5; source rights/attribution retained'}
    packet = make_packet(payload, destination, manifest)
    atomic_json(cache_path, {'fingerprint': fingerprint, 'packet': packet})
    emit('packet_prepared', packet_id=packet['packet_id'], archive_bytes=packet['archive_bytes'],
         files=packet['payload_files'], history_errors=len(errors))
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', default='/public/home/zhuziyuan/projects/paper2-recalibration-v2')
    parser.add_argument('--config')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--reauthorize', action='store_true', help='Hidden token input instead of the existing private token file')
    args = parser.parse_args()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    project = Path(args.project_dir).expanduser().resolve()
    sys.path.insert(0, str(project))
    from hpc_recalibration.preflight import load_config
    from hpc_recalibration.github_sync import _load_token, _settings, _store_token
    config = load_config(args.config or project / 'configs/kumar_dev_hpc_gpu1_24cpu.json')
    destination = project / 'exports' / VERSION
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / 'export.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        tool = Path(sys.argv[0])
        identity = digest(tool) if tool.is_file() else VERSION
        packet = prepare_bundle(config, destination, tool_identity=identity)
        if args.prepare_only:
            emit('prepared_only', directory=str(destination), packet_id=packet['packet_id'])
            return 0
        options = _settings(config)
        entered = args.reauthorize or not options['token_file'].is_file()
        if entered and not sys.stdin.isatty():
            raise ValueError('Use the school interactive terminal for hidden GitHub token input')
        token = getpass.getpass('GitHub token (hidden; Contents read/write): ').strip() if entered else _load_token(options['token_file'])
        if not token or any(c.isspace() or ord(c) < 32 for c in token):
            raise ValueError('No valid GitHub authorization supplied')
        publisher = GitResultPublisher(token, options['repository'], options['branch'])
        prefix = options['status_prefix'] + '/result_exports/' + packet['packet_id']
        files = {prefix + '/' + name: destination / name for name in packet['upload_files']}
        emit('upload_begin', objects=len(files), bytes=sum(p.stat().st_size for p in files.values()), branch=options['branch'])
        receipt = publisher.publish(files, 'Publish completed paper2 saved results ' + packet['packet_id'])
        receipt_name = 'github_full_get_receipt_' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
        receipt_path = destination / receipt_name
        atomic_json(receipt_path, receipt)
        if receipt['failed_objects']:
            emit('verification_failed', failed_objects=receipt['failed_objects'], local_receipt=str(receipt_path))
            return 1
        if entered:
            _store_token(options['token_file'], token)
        closing = publisher.publish({prefix + '/' + receipt_name: receipt_path},
                                    'Record full GitHub readback for paper2 result packet')
        atomic_json(destination / ('readback_' + receipt_name), closing)
        emit('upload_complete', packet_id=packet['packet_id'], data_commit=receipt['commit'],
             receipt_commit=closing['commit'], verified_objects=receipt['verified_objects'],
             failed_objects=closing['failed_objects'], url='https://github.com/' + options['repository'] + '/tree/' + options['branch'] + '/' + prefix,
             local_directory=str(destination), history_errors=packet['history_errors'])
        return 1 if closing['failed_objects'] or packet['history_errors'] else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        emit('export_failed', error_type=type(error).__name__, detail=str(error))
        raise SystemExit(1)
